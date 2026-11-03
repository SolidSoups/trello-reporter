"""Turn DarkSwarm bug reports posted to Discord into Trello cards.

--dry-run prints the cards it would create and writes nothing anywhere.
--latest N creates cards for the newest N reports only, as a test. It adds no
reactions and doesn't touch the saved message ID, so running it twice creates
the cards twice. A plain run without either flag isn't written yet.

    python sync.py --set-secrets
    python sync.py --dry-run
    python sync.py --dry-run --latest 5 --channel public
    python sync.py --latest 5 --channel public
"""

import argparse
import datetime
import getpass
import json
import os
import re
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import keyring
import requests

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
STATE_PATH = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "darkswarm-bug-sync" / "state.json"

KEYRING_SERVICE = "darkswarm-bug-sync"
KEYRING_DISCORD_TOKEN = "discord_bot_token"
KEYRING_TRELLO_KEY = "trello_api_key"
KEYRING_TRELLO_TOKEN = "trello_token"
SECRETS = [
    (KEYRING_DISCORD_TOKEN, "Discord bot token"),
    (KEYRING_TRELLO_KEY, "Trello API key"),
    (KEYRING_TRELLO_TOKEN, "Trello token"),
]

DISCORD_API = "https://discord.com/api/v10"
TRELLO_API = "https://api.trello.com/1"
TIMEOUT = 30
MAX_RETRIES = 5
TRELLO_RATE_WINDOW = 10  # Trello allows about 100 requests per 10 seconds per token

DANISH_TIME = ZoneInfo("Europe/Copenhagen")
CHECKMARK = "✅"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
MAX_NAME_LENGTH = 100
CHANNEL_LABELS = {"internal": "Internal", "public": "External"}


def set_secrets():
    print("Input is hidden. Press Enter on an empty line to keep the stored value.")
    for name, prompt in SECRETS:
        stored = keyring.get_password(KEYRING_SERVICE, name)
        value = getpass.getpass(f"{prompt} ({'stored' if stored else 'not set'}): ").strip()
        if value:
            keyring.set_password(KEYRING_SERVICE, name, value)
            print("  Stored.")
        else:
            print("  Kept." if stored else "  Still not set.")
    print(f"Secrets live in Windows Credential Manager under '{KEYRING_SERVICE}'.")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_state():
    """The last processed message ID per channel. Missing file means start from the beginning."""
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def discord_get(session, path, params=None):
    """GET from the Discord API, sleeping and retrying on 429."""
    for _ in range(MAX_RETRIES):
        response = session.get(DISCORD_API + path, params=params, timeout=TIMEOUT)
        if response.status_code != 429:
            return response
        retry_after = float(response.json().get("retry_after", 1.0))
        print(f"  Rate limited. Sleeping {retry_after:.2f}s.")
        time.sleep(retry_after)
    return response


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


class Trello:
    def __init__(self, key, token, config):
        self.session = requests.Session()
        # The header keeps the key and token out of URLs and error messages.
        self.session.headers["Authorization"] = f'OAuth oauth_consumer_key="{key}", oauth_token="{token}"'
        self.board_id = config["trello"]["board_id"]
        self.list_id = config["trello"]["list_id"]
        self.labels = {}

    def request(self, method, path, **kwargs):
        for _ in range(MAX_RETRIES):
            response = self.session.request(method, TRELLO_API + path, timeout=TIMEOUT, **kwargs)
            if response.status_code != 429:
                break
            print(f"  Trello rate limit. Sleeping {TRELLO_RATE_WINDOW}s.")
            time.sleep(TRELLO_RATE_WINDOW)
        if not response.ok:
            raise RuntimeError(f"Trello {method} {path}: HTTP {response.status_code}: {response.text[:300]}")
        return response.json()

    def connect(self):
        """Check the board and list before writing anything, and load the board's labels."""
        board = self.request("GET", f"/boards/{self.board_id}", params={"fields": "name"})
        target_list = self.request("GET", f"/lists/{self.list_id}", params={"fields": "name,idBoard"})
        if target_list["idBoard"] != board["id"]:
            raise RuntimeError(f"List {self.list_id} isn't on board {self.board_id}. Check config.json.")
        print(f"Trello: board '{board['name']}', list '{target_list['name']}'")

        labels = self.request("GET", f"/boards/{self.board_id}/labels", params={"limit": 1000})
        self.labels = {label["name"]: label["id"] for label in labels if label["name"]}

    def label_id(self, name):
        """Return the ID of the label with this name, creating it the first time."""
        if name not in self.labels:
            label = self.request("POST", "/labels", json={"name": name, "color": None, "idBoard": self.board_id})
            self.labels[name] = label["id"]
            print(f"  Created label '{name}'")
        return self.labels[name]


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


def create_card(trello, card, config):
    screenshot, problem = download_screenshot(card)
    label_names = list(card["labels"])
    if screenshot is None:
        print(f"  {card['message_id']}: {problem}")
        label_names.append(config.get("no_screenshot_label", "No screenshot"))

    created = trello.request("POST", "/cards", data={
        "idList": trello.list_id,
        "name": card["name"],
        "desc": card["desc"],
        "idLabels": ",".join(trello.label_id(name) for name in label_names),
        "pos": "bottom",
    })
    if screenshot:
        trello.request("POST", f"/cards/{created['id']}/attachments",
                       data={"name": "screenshot.png", "mimeType": "image/png"},
                       files={"file": ("screenshot.png", screenshot, "image/png")})
    print(f"  Created {created['shortUrl']}  {card['name']}")


def embed_fields(embed):
    return {field.get("name"): field.get("value", "").strip() for field in embed.get("fields", [])}


def report_text(embed):
    # The game prefixes "## ". Discord trims trailing spaces, so a blank report arrives as just "##".
    text = embed.get("description") or ""
    return re.sub(r"^##\s*", "", text).strip()


def has_own_checkmark(message):
    return any(r.get("me") and r.get("emoji", {}).get("name") == CHECKMARK
               for r in message.get("reactions", []))


def classify(message, channel, webhook_id):
    """Return (group, reason). Group is 'ignored', 'done', 'skipped' or 'card'."""
    if not message.get("webhook_id") or message["webhook_id"] != webhook_id:
        return "ignored", "not from the report webhook"
    if has_own_checkmark(message):
        return "done", "already has the bot's checkmark"

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


def print_card(card, config, existing_labels):
    label_names = list(card["labels"])
    screenshot = card["screenshot"]
    if not screenshot:
        label_names.append(config.get("no_screenshot_label", "No screenshot"))
    labels = [name if name in existing_labels else f"{name} (new)" for name in label_names]

    print(f"\n--- CARD from {card['message_id']}")
    print(f"  name:   {card['name']}")
    print(f"  labels: {', '.join(labels)}")
    if screenshot:
        print(f"  screenshot: would upload screenshot.png ({screenshot['width']}x{screenshot['height']})")
    else:
        print("  screenshot: none")
    print("  description:")
    for line in card["desc"].splitlines():
        print(f"    {line}")


def run_channel(discord, trello, config, state, channel, args):
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

    counts = {"card": 0, "skipped": 0, "done": 0, "ignored": 0}
    for message in messages:
        group, reason = classify(message, channel, webhook_id)
        counts[group] += 1
        if group == "card":
            card = build_card(message, channel, config)
            if args.dry_run:
                print_card(card, config, trello.labels)
            else:
                create_card(trello, card, config)
        elif group == "skipped":
            print(f"\n--- SKIPPED {message['id']}: {reason}")

    verb = "cards" if args.dry_run else "cards created"
    print(f"\n'{channel}': {counts['card']} {verb}, {counts['skipped']} skipped,"
          f" {counts['done']} already done, {counts['ignored']} ignored")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set-secrets", action="store_true", help="store the Discord and Trello secrets in Credential Manager")
    parser.add_argument("--dry-run", action="store_true", help="print the cards it would create, write nothing")
    parser.add_argument("--channel", choices=["internal", "public"], help="process only this channel")
    parser.add_argument("--latest", type=int, metavar="N",
                        help="test: create cards for the newest N reports only, with no reactions or saved state")
    args = parser.parse_args()

    # Keep Danish letters and emoji from crashing the print when output is redirected.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.set_secrets:
        set_secrets()
        return
    if not args.dry_run and not args.latest:
        sys.exit("The full sync isn't written yet. Run with --dry-run or --latest N.")
    if args.latest is not None and args.latest < 1:
        sys.exit("--latest needs a number of 1 or more.")

    secrets = {name: keyring.get_password(KEYRING_SERVICE, name) for name, _ in SECRETS}
    missing = [prompt for name, prompt in SECRETS if not secrets[name]]
    if missing:
        sys.exit(f"Not stored: {', '.join(missing)}. Run: python sync.py --set-secrets")

    config = load_config()
    state = load_state()
    channels = [args.channel] if args.channel else list(config.get("channels", {}))

    discord = requests.Session()
    discord.headers["Authorization"] = f"Bot {secrets[KEYRING_DISCORD_TOKEN]}"
    discord.headers["User-Agent"] = "DiscordBot (darkswarm-bug-sync, 0.1)"
    trello = Trello(secrets[KEYRING_TRELLO_KEY], secrets[KEYRING_TRELLO_TOKEN], config)

    try:
        trello.connect()
        for channel in channels:
            if not config["channels"].get(channel):
                print(f"\nSkipping '{channel}': no channel ID in config.json.")
                continue
            run_channel(discord, trello, config, state, channel, args)
    except (RuntimeError, requests.RequestException) as error:
        # Stop at the first failure so nothing is skipped past. The next run retries it.
        sys.exit(f"\nStopped: {error}")


if __name__ == "__main__":
    main()
