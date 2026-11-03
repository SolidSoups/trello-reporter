"""Turn DarkSwarm bug reports posted to Discord into Trello cards.

Only --dry-run exists so far. It prints the cards it would create and writes
nothing to Discord, Trello or disk.

    python sync.py --set-secrets
    python sync.py --dry-run
    python sync.py --dry-run --channel public
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

DISCORD_API = "https://discord.com/api/v10"
TIMEOUT = 30
MAX_RETRIES = 5

DANISH_TIME = ZoneInfo("Europe/Copenhagen")
CHECKMARK = "✅"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
MAX_NAME_LENGTH = 100
CHANNEL_LABELS = {"internal": "Internal", "public": "External"}


def set_secrets():
    token = getpass.getpass("Discord bot token (input hidden): ").strip()
    if not token:
        print("Empty token. Nothing stored.")
        return
    keyring.set_password(KEYRING_SERVICE, KEYRING_DISCORD_TOKEN, token)
    print(f"Stored in Windows Credential Manager under '{KEYRING_SERVICE}'.")


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


def print_card(card):
    print(f"\n--- CARD from {card['message_id']}")
    print(f"  name:   {card['name']}")
    print(f"  labels: {', '.join(card['labels'])}")
    screenshot = card["screenshot"]
    if screenshot:
        print(f"  screenshot: would upload screenshot.png ({screenshot['width']}x{screenshot['height']})")
    else:
        print("  screenshot: none")
    print("  description:")
    for line in card["desc"].splitlines():
        print(f"    {line}")


def dry_run_channel(session, config, state, channel):
    channel_id = config["channels"][channel]
    webhook_id = config.get("webhooks", {}).get(channel, "")
    after_id = state.get(channel_id, "0")
    print(f"\n##### Channel '{channel}' ({channel_id}), after message {after_id}")
    if not webhook_id:
        print(f"  No webhook ID for '{channel}' in config.json. Every message will be ignored.")

    counts = {"card": 0, "skipped": 0, "done": 0, "ignored": 0}
    for message in fetch_messages(session, channel_id, after_id):
        group, reason = classify(message, channel, webhook_id)
        counts[group] += 1
        if group == "card":
            print_card(build_card(message, channel, config))
        elif group == "skipped":
            print(f"\n--- SKIPPED {message['id']}: {reason}")

    print(f"\n'{channel}': {counts['card']} cards, {counts['skipped']} skipped,"
          f" {counts['done']} already done, {counts['ignored']} ignored")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set-secrets", action="store_true", help="store the Discord bot token in Credential Manager")
    parser.add_argument("--dry-run", action="store_true", help="print the cards it would create, write nothing")
    parser.add_argument("--channel", choices=["internal", "public"], help="process only this channel")
    args = parser.parse_args()

    # Keep Danish letters and emoji from crashing the print when output is redirected.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.set_secrets:
        set_secrets()
        return
    if not args.dry_run:
        sys.exit("Creating cards isn't written yet. Run with --dry-run.")

    token = keyring.get_password(KEYRING_SERVICE, KEYRING_DISCORD_TOKEN)
    if not token:
        sys.exit("No Discord bot token stored. Run: python sync.py --set-secrets")

    config = load_config()
    state = load_state()
    channels = [args.channel] if args.channel else list(config.get("channels", {}))

    session = requests.Session()
    session.headers["Authorization"] = f"Bot {token}"
    session.headers["User-Agent"] = "DiscordBot (darkswarm-bug-sync, 0.1)"

    for channel in channels:
        if not config["channels"].get(channel):
            print(f"\nSkipping '{channel}': no channel ID in config.json.")
            continue
        try:
            dry_run_channel(session, config, state, channel)
        except RuntimeError as error:
            print(f"  {error}")


if __name__ == "__main__":
    main()
