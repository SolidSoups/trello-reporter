"""Turn DarkSwarm bug reports posted to Discord into Trello cards, labelled and sorted.

A plain run processes every message after the saved message ID, oldest first.
For each report it asks Claude for the discipline labels and a matching "##"
theme list, creates the card there (or in Incoming) with its screenshot, puts a
gear reaction on the message, and saves the ID. Reports are handled in batches:
Claude is asked about a whole batch at once, then the cards are created in order.

If Claude can't be reached, or no Anthropic key is stored, cards are still
created, just without discipline labels. Each run first labels and places any
such cards left in Incoming.

--next N stops after N reports. --dry-run prints what it would do, including
Claude's labels and list, and writes nothing to Trello or Discord.

--latest N is a test mode: it creates cards for the newest N reports only, adds
no reactions and doesn't touch the saved message ID, so running it twice
creates the cards twice.

    python sync.py --set-secrets
    python sync.py
    python sync.py --next 5 --channel public
    python sync.py --dry-run --next 5
    python sync.py --latest 5 --channel public
    python sync.py --log                (scheduled runs: output goes to the log file)

Runs that write take a lock file, shared with sort.py, so two runs can't
overlap and create duplicate cards.
"""

import argparse
import datetime
import json
import os
import re
import sys
import time

import anthropic
import requests

from claude_board import Board, card_link, ensure_labels, log_labels, log_move, make_board
from common import (
    DANISH_TIME, DATA_DIR, KEYRING_ANTHROPIC_KEY, KEYRING_DISCORD_TOKEN, KEYRING_TRELLO_KEY,
    KEYRING_TRELLO_TOKEN, MAX_RETRIES, TIMEOUT, Trello, acquire_lock, get_secret, load_config,
    release_lock, set_secrets, start_log,
)

STATE_PATH = DATA_DIR / "state.json"
DISCORD_API = "https://discord.com/api/v10"
BATCH_SIZE = 20  # reports Claude is asked about at once; progress is saved after each batch's cards

# The bot marks processed reports with a gear. Teammates use checkmarks, so those mean nothing here.
MARKER = "⚙️"
MARKER_PATH = "%E2%9A%99%EF%B8%8F"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
MAX_NAME_LENGTH = 100
CHANNEL_LABELS = {"internal": "Internal", "public": "External"}


def load_state():
    """The last processed message ID per channel. Missing file means start from the beginning."""
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(state):
    # Write a temporary file and swap it in, so a crash mid-write can't leave a broken file.
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = STATE_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(temp_path, STATE_PATH)


def discord_request(session, method, path, params=None):
    """Send to the Discord API, sleeping and retrying on 429."""
    for _ in range(MAX_RETRIES):
        response = session.request(method, DISCORD_API + path, params=params, timeout=TIMEOUT)
        if response.status_code != 429:
            return response
        retry_after = float(response.json().get("retry_after", 1.0))
        print(f"  Rate limited. Sleeping {retry_after:.2f}s.")
        time.sleep(retry_after)
    return response


def discord_get(session, path, params=None):
    return discord_request(session, "GET", path, params)


def add_marker(session, channel_id, message_id):
    path = f"/channels/{channel_id}/messages/{message_id}/reactions/{MARKER_PATH}/@me"
    response = discord_request(session, "PUT", path)
    if response.status_code != 204:
        raise RuntimeError(f"Couldn't add the {MARKER} reaction to message {message_id}: HTTP {response.status_code}:"
                           f" {response.text[:300]}. Does the bot have Add Reactions on the channel?")


def fetch_messages(session, channel_id, after_id):
    """Yield every message after after_id, oldest first."""
    while True:
        response = discord_get(session, f"/channels/{channel_id}/messages", {"limit": 100, "after": after_id})
        if not response.ok:
            raise RuntimeError(f"HTTP {response.status_code} reading channel {channel_id}: {response.text}")
        page = sorted(response.json(), key=lambda m: int(m["id"]))
        if not page:
            return
        yield from page
        after_id = page[-1]["id"]


def fetch_latest_reports(session, channel_id, channel, webhook_id, count):
    """Return the newest count messages that would become cards, oldest first."""
    reports = []
    before_id = None
    while len(reports) < count:
        params = {"limit": 100}
        if before_id:
            params["before"] = before_id
        response = discord_get(session, f"/channels/{channel_id}/messages", params)
        if not response.ok:
            raise RuntimeError(f"HTTP {response.status_code} reading channel {channel_id}: {response.text}")
        page = sorted(response.json(), key=lambda m: int(m["id"]), reverse=True)
        if not page:
            break
        for message in page:
            if classify(message, channel, webhook_id)[0] == "card":
                reports.append(message)
                if len(reports) == count:
                    break
        before_id = page[-1]["id"]
    return sorted(reports, key=lambda m: int(m["id"]))


def download_screenshot(card):
    """Return (bytes, None), or (None, reason) when there's nothing to upload."""
    if not card["screenshot"]:
        return None, "no screenshot in the report"
    try:
        # The URL is signed, so no bot token goes with this request.
        response = requests.get(card["screenshot"]["url"], timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as error:
        return None, f"screenshot download failed ({type(error).__name__})"
    if not response.content:
        return None, "screenshot is empty"
    return response.content, None


def no_screenshot_label(config):
    return config.get("no_screenshot_label", "No screenshot")


class Organizer:
    """Claude's discipline labels and theme list for new reports. It reads the board once per run,
    for the example cards and the ## lists, and only when there's something to ask about."""

    def __init__(self, board):
        self.board = board
        self.prompts = None
        self.label_ids = None

    def prepare(self, cards=None):
        if self.prompts is None:
            self.prompts = self.board.prompts_for(cards if cards is not None else self.board.board_cards())
        return self.prompts

    def label_id(self, name):
        """The ID of one of Claude's labels. The first call makes sure they all exist, with their colours,
        so a dry run, which never gets here, writes nothing."""
        if self.label_ids is None:
            self.label_ids = ensure_labels(self.board)
        return self.label_ids[name]

    @property
    def themes(self):
        return self.prompts[2]

    def decide(self, items):
        label_prompt, theme_prompt, themes = self.prepare()
        decisions = self.board.organize(items, label_prompt, theme_prompt, themes)
        failed = [decision["error"] for decision in decisions.values() if decision["error"]]
        if failed:
            print(f"  Claude failed on {len(failed)} of {len(items)} reports, for example: {failed[0]}")
        return decisions


def create_card(trello, card, screenshot, decision, organizer, config):
    """Create the card, with Claude's labels, in its theme list or Incoming. Returns its URL."""
    label_ids = [trello.label_id(name) for name in card["labels"]]
    if screenshot is None:
        label_ids.append(trello.label_id(no_screenshot_label(config)))
    labels = decision["labels"] if decision else []
    label_ids += [organizer.label_id(name) for name in labels]
    theme = decision["theme"] if decision else None
    list_id = organizer.themes[theme] if theme else trello.list_id

    created = trello.request("POST", "/cards", data={
        "idList": list_id,
        "name": card["name"],
        "desc": card["desc"],
        "idLabels": ",".join(label_ids),
        "pos": "bottom",
    })
    if screenshot:
        try:
            trello.request("POST", f"/cards/{created['id']}/attachments",
                           data={"name": "screenshot.png", "mimeType": "image/png"},
                           files={"file": ("screenshot.png", screenshot, "image/png")})
        except (RuntimeError, requests.RequestException) as error:
            # The card exists now. Stopping here would make the next run create it a second time,
            # so keep it, mark it like any report without a screenshot, and carry on.
            print(f"  {card['message_id']}: screenshot upload failed ({error})")
            try:
                trello.request("POST", f"/cards/{created['id']}/idLabels",
                               params={"value": trello.label_id(no_screenshot_label(config))})
            except (RuntimeError, requests.RequestException) as label_error:
                print(f"  {card['message_id']}: couldn't add the label either ({label_error})")

    if labels:
        log_labels({"card": created["id"], "link": created["shortUrl"], "name": card["name"], "added_labels": labels,
                    "marked_complete": False, "source": "Claude", "reason": decision["label_reason"]})
    if theme:
        log_move({"type": "move", "card": created["id"], "link": created["shortUrl"], "name": card["name"],
                  "from": trello.list_id, "to": list_id, "to_name": theme, "model": organizer.board.model,
                  "reason": decision["theme_reason"], "by": "sync"})
    where = f" -> {theme}" if theme else ""
    print(f"  Created {created['shortUrl']}  [{', '.join(labels) or 'no discipline label'}]{where}  {card['name']}")


def embed_fields(embed):
    return {field.get("name"): field.get("value", "").strip() for field in embed.get("fields", [])}


def report_text(embed):
    # The game prefixes "## ". Discord trims trailing spaces, so a blank report arrives as just "##".
    text = embed.get("description") or ""
    return re.sub(r"^##\s*", "", text).strip()


def has_own_marker(message):
    # Discord may or may not keep the invisible variation selector after the gear, so compare without it.
    return any(r.get("me") and (r.get("emoji", {}).get("name") or "").replace("️", "") == MARKER.replace("️", "")
               for r in message.get("reactions", []))


def classify(message, channel, webhook_id):
    """Return (group, reason). Group is 'ignored', 'done', 'skipped' or 'card'."""
    if not message.get("webhook_id") or message["webhook_id"] != webhook_id:
        return "ignored", "not from the report webhook"
    if has_own_marker(message):
        return "done", "already has the bot's reaction"

    embeds = message.get("embeds", [])
    if not embeds or not report_text(embeds[0]):
        return "skipped", "no embed or empty report text"

    if channel == "public":
        version = embed_fields(embeds[0]).get("Version", "")
        if version != "Failed" and not VERSION_PATTERN.match(version):
            return "skipped", f"implausible Version {version!r}"

    return "card", ""


def card_name(text):
    name = text.splitlines()[0].strip()
    if len(name) > MAX_NAME_LENGTH:
        name = name[:MAX_NAME_LENGTH - 3].rstrip() + "..."
    return name


def reported_time(message):
    utc = datetime.datetime.fromisoformat(message["timestamp"])
    return utc.astimezone(DANISH_TIME).strftime("%Y-%m-%d %H:%M:%S")


def build_card(message, channel, config):
    embed = message["embeds"][0]
    fields = embed_fields(embed)
    text = report_text(embed)

    # Every field the game sends goes on the card in its order, so new fields need no change here.
    ignored = set(config.get("ignore_fields", []))
    lines = [text, "", "---", f"**Reported:** {reported_time(message)} (Danish time)"]
    for name, value in fields.items():
        if name not in ignored and value:
            lines.append(f"**{name}:** {value}")
    link = f"https://discord.com/channels/{config['guild_id']}/{message['channel_id']}/{message['id']}"
    lines += ["", f"[Discord message]({link})"]

    labels = [fields.get(name) for name in config.get("label_fields", [])] + [CHANNEL_LABELS[channel]]
    labels = [label for label in labels if label]

    image = embed.get("image") or {}
    url = image.get("url", "")
    screenshot = None
    if url.startswith("https://"):
        screenshot = {"url": url, "width": image.get("width"), "height": image.get("height")}

    return {
        "message_id": message["id"],
        "name": card_name(text),
        "desc": "\n".join(lines),
        "labels": labels,
        "screenshot": screenshot,
    }


def print_card(card, screenshot, decision, config, existing_labels):
    label_names = list(card["labels"])
    if screenshot is None:
        label_names.append(no_screenshot_label(config))
    labels = [name if name in existing_labels else f"{name} (new)" for name in label_names]

    print(f"\n--- CARD from {card['message_id']}")
    print(f"  name:   {card['name']}")
    print(f"  labels: {', '.join(labels)}")
    if decision:
        if decision["error"] and not decision["labels"]:
            print(f"  Claude: failed ({decision['error']})")
        else:
            print(f"  Claude labels: {', '.join(decision['labels'])}  ({decision['label_reason']})")
            if decision["theme"]:
                print(f"  Claude list:   ## {decision['theme']}  ({decision['theme_reason']})")
            else:
                print("  Claude list:   stays in Incoming")
    if screenshot:
        print(f"  screenshot: would upload screenshot.png ({card['screenshot']['width']}x{card['screenshot']['height']})")
    else:
        print("  screenshot: none")
    print("  description:")
    for line in card["desc"].splitlines():
        print(f"    {line}")


def report_items(prepared, config):
    """New reports as Claude sees them: the labels the card will have, and the screenshot already downloaded."""
    items = []
    for message_id, (card, screenshot, _) in prepared.items():
        labels = list(card["labels"]) + ([] if screenshot else [no_screenshot_label(config)])
        items.append(Board.report_item(message_id, card["name"], card["desc"], labels, screenshot))
    return items


def run_channel(discord, trello, organizer, config, state, channel, args):
    channel_id = config["channels"][channel]
    webhook_id = config.get("webhooks", {}).get(channel, "")
    if not webhook_id:
        print(f"\n  No webhook ID for '{channel}' in config.json. Every message will be ignored.")

    if args.latest:
        print(f"\n##### Channel '{channel}' ({channel_id}), newest {args.latest} reports")
        messages = fetch_latest_reports(discord, channel_id, channel, webhook_id, args.latest)
    else:
        after_id = state.get(channel_id, "0")
        print(f"\n##### Channel '{channel}' ({channel_id}), after message {after_id}")
        messages = fetch_messages(discord, channel_id, after_id)

    # Decide what happens to each message first, so Claude can be asked about a batch of reports at once.
    plan, reported = [], 0
    for message in messages:
        group, reason = classify(message, channel, webhook_id)
        plan.append((message, group, reason))
        if group in ("card", "skipped"):
            reported += 1
            if args.next and reported >= args.next:
                break

    # The test mode and the dry run never mark messages or move the saved ID.
    tracking = not args.dry_run and not args.latest
    counts = {"card": 0, "skipped": 0, "done": 0, "ignored": 0}
    for start in range(0, len(plan), BATCH_SIZE):
        batch = plan[start:start + BATCH_SIZE]
        prepared = {}  # message ID -> (card, screenshot bytes or None, why there's no screenshot)
        for message, group, _ in batch:
            if group == "card":
                card = build_card(message, channel, config)
                prepared[message["id"]] = (card, *download_screenshot(card))
        decisions = organizer.decide(report_items(prepared, config)) if organizer and prepared else {}

        for message, group, reason in batch:
            counts[group] += 1
            if group == "card":
                card, screenshot, problem = prepared[message["id"]]
                if screenshot is None:
                    print(f"  {card['message_id']}: {problem}")
                decision = decisions.get(message["id"])
                if args.dry_run:
                    print_card(card, screenshot, decision, config, trello.labels)
                else:
                    create_card(trello, card, screenshot, decision, organizer, config)
            elif group == "skipped":
                print(f"\n--- SKIPPED {message['id']}: {reason}")

            # The gear goes on only after the card and its screenshot exist, and the
            # ID moves only after that. A failure before this point retries the report next run.
            if tracking:
                if group in ("card", "skipped"):
                    add_marker(discord, channel_id, message["id"])
                state[channel_id] = message["id"]
                save_state(state)

    verb = "cards" if args.dry_run else "cards created"
    print(f"\n'{channel}': {counts['card']} {verb}, {counts['skipped']} skipped,"
          f" {counts['done']} already done, {counts['ignored']} ignored")
    if tracking:
        print(f"  Saved progress: after message {state.get(channel_id, 'none')}")


def organize_stragglers(trello, organizer):
    """Label and place cards in Incoming that have no discipline label yet: reports from runs where
    Claude couldn't be reached. Cheap when there are none: it only reads Incoming's labels."""
    board = organizer.board
    incoming = trello.request("GET", f"/lists/{trello.list_id}/cards", params={"fields": "labels,dueComplete"})
    if not any(not board.has_board_label(card) and not card.get("dueComplete") for card in incoming):
        return
    cards = board.board_cards()
    organizer.prepare(cards)
    stragglers = [card for card in cards if card["idList"] == trello.list_id
                  and not board.has_board_label(card) and not card.get("dueComplete")]
    print(f"\nLabelling {len(stragglers)} cards in Incoming that have no discipline label yet.")
    decisions = organizer.decide([board.card_item(card) for card in stragglers])
    for card in stragglers:
        decision = decisions[card["id"]]
        if not decision["labels"]:
            continue
        for name in decision["labels"]:
            trello.request("POST", f"/cards/{card['id']}/idLabels", params={"value": organizer.label_id(name)})
        log_labels({"card": card["id"], "link": card_link(card), "name": card["name"], "added_labels": decision["labels"],
                    "marked_complete": False, "source": "Claude", "reason": decision["label_reason"]})
        theme = decision["theme"]
        if theme:
            current = trello.request("GET", f"/cards/{card['id']}", params={"fields": "idList,closed"})
            if current["idList"] == trello.list_id and not current["closed"]:
                trello.request("PUT", f"/cards/{card['id']}", params={"idList": organizer.themes[theme], "pos": "bottom"})
                log_move({"type": "move", "card": card["id"], "link": card_link(card), "name": card["name"],
                          "from": trello.list_id, "to": organizer.themes[theme], "to_name": theme,
                          "model": board.model, "reason": decision["theme_reason"], "by": "sync"})
        where = f" -> {theme}" if theme else ""
        print(f"  Labelled {card_link(card)}  [{', '.join(decision['labels'])}]{where}  {card['name']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set-secrets", action="store_true", help="store the Discord, Trello and Anthropic secrets in Credential Manager")
    parser.add_argument("--dry-run", action="store_true", help="print the cards it would create, write nothing")
    parser.add_argument("--channel", choices=["internal", "public"], help="process only this channel")
    parser.add_argument("--next", type=int, metavar="N",
                        help="process only the next N reports after the saved message ID")
    parser.add_argument("--latest", type=int, metavar="N",
                        help="test: create cards for the newest N reports only, with no reactions or saved state")
    parser.add_argument("--log", action="store_true", help="write all output to sync.log instead of the screen, for scheduled runs")
    args = parser.parse_args()

    if args.log:
        start_log("sync", sys.argv[1:])
    else:
        # Keep Danish letters and emoji from crashing the print when output is redirected.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.set_secrets:
        set_secrets()
        return
    if args.next is not None and args.latest is not None:
        sys.exit("Use --next or --latest, not both.")
    for flag, value in (("--next", args.next), ("--latest", args.latest)):
        if value is not None and value < 1:
            sys.exit(f"{flag} needs a number of 1 or more.")

    # Only runs that write need the lock. Another run holding it isn't a failure, so exit 0.
    locking = not args.dry_run
    if locking and not acquire_lock("sync.py"):
        return
    try:
        sync(args)
    finally:
        if locking:
            release_lock()


def sync(args):
    needed = [(KEYRING_DISCORD_TOKEN, "Discord bot token"), (KEYRING_TRELLO_KEY, "Trello API key"),
              (KEYRING_TRELLO_TOKEN, "Trello token")]
    secrets = {name: get_secret(name) for name, _ in needed}
    missing = [prompt for name, prompt in needed if not secrets[name]]
    if missing:
        sys.exit(f"Not stored: {', '.join(missing)}. Run: python sync.py --set-secrets")

    config = load_config()
    state = load_state()
    channels = [args.channel] if args.channel else list(config.get("channels", {}))

    discord = requests.Session()
    discord.headers["Authorization"] = f"Bot {secrets[KEYRING_DISCORD_TOKEN]}"
    discord.headers["User-Agent"] = "DiscordBot (darkswarm-bug-sync, 0.1)"
    trello = Trello(secrets[KEYRING_TRELLO_KEY], secrets[KEYRING_TRELLO_TOKEN], config)

    # Without an Anthropic key, reports still become cards, just without discipline labels.
    organizer = None
    anthropic_key = get_secret(KEYRING_ANTHROPIC_KEY)
    if anthropic_key:
        organizer = Organizer(make_board(config, trello, anthropic_key))
    else:
        print("No Anthropic API key stored: new cards get no discipline labels. Run: python sync.py --set-secrets")

    try:
        trello.connect()
        if organizer and not args.dry_run and not args.latest:
            organize_stragglers(trello, organizer)
        for channel in channels:
            if not config["channels"].get(channel):
                print(f"\nSkipping '{channel}': no channel ID in config.json.")
                continue
            run_channel(discord, trello, organizer, config, state, channel, args)
    except (RuntimeError, requests.RequestException, anthropic.APIError) as error:
        # Stop at the first failure so nothing is skipped past. The next run retries it.
        sys.exit(f"\nStopped: {error}")
    finally:
        if organizer and organizer.board.usage["calls"]:
            organizer.board.save_answers()
            print(f"Claude: {organizer.board.usage['calls']} calls, ${organizer.board.cost():.3f}")


if __name__ == "__main__":
    main()
