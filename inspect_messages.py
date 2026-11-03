"""Fetch a few messages from the bug report channels and dump them for inspection.

Reads only. Adds no reactions and creates no Trello cards.

    python inspect_messages.py --set-secrets
    python inspect_messages.py --limit 5
    python inspect_messages.py --channel public
"""

import argparse
import datetime
import getpass
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import keyring
import requests

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
SAMPLES_DIR = SCRIPT_DIR / "samples"

KEYRING_SERVICE = "darkswarm-bug-sync"
KEYRING_DISCORD_TOKEN = "discord_bot_token"

DISCORD_API = "https://discord.com/api/v10"
TIMEOUT = 30
MAX_RETRIES = 5


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


def attachment_expiry(url):
    """Discord signs CDN URLs with 'ex', a hex Unix timestamp."""
    ex = parse_qs(urlparse(url).query).get("ex")
    if not ex:
        return "no 'ex' parameter"
    expires = datetime.datetime.fromtimestamp(int(ex[0], 16))
    return expires.strftime("%Y-%m-%d %H:%M:%S local")


def safe_filename(name):
    return re.sub(r"[^\w.\-]", "_", name) or "attachment"


def print_summary(message):
    author = message.get("author", {})
    webhook_id = message.get("webhook_id") or "not a webhook"
    print(f"\n=== {message['id']}  {message.get('timestamp')}")
    print(f"  webhook_id: {webhook_id}")
    print(f"  author:     {author.get('username')}")

    content = message.get("content")
    if content:
        print(f"  content:    {content!r}")

    embeds = message.get("embeds", [])
    print(f"  embeds:     {len(embeds)}")
    if embeds:
        embed = embeds[0]
        print(f"  description: {embed.get('description')!r}")
        for field in embed.get("fields", []):
            print(f"    {field.get('name')} = {field.get('value')}")

    reactions = message.get("reactions", [])
    for reaction in reactions:
        emoji = reaction.get("emoji", {}).get("name")
        print(f"  reaction:   {emoji} x{reaction.get('count')} (me={reaction.get('me')})")


def save_attachments(message, out_dir):
    attachments = message.get("attachments", [])
    if not attachments:
        print("  attachments: no attachment")
        return

    for attachment in attachments:
        filename = attachment.get("filename")
        size = attachment.get("size", 0)
        url = attachment.get("url", "")
        print(f"  attachment: {filename}  {size} bytes  {attachment.get('content_type')}"
              f"  {attachment.get('width')}x{attachment.get('height')}")
        print(f"    expires:  {attachment_expiry(url)}")

        if size == 0:
            print("    zero-byte attachment, not downloaded")
            continue

        # The URL is signed, so no bot token goes with this request.
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        path = out_dir / f"{message['id']}_{safe_filename(filename)}"
        path.write_bytes(response.content)
        print(f"    saved:    {path}  ({len(response.content)} bytes)")


def image_format(data):
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"\xff\xd8"):
        return "jpg"
    return "bin"


def save_embed_image(message, out_dir):
    """Discord moves an attachment:// file into the embed, so it isn't listed in attachments."""
    embeds = message.get("embeds", [])
    image = embeds[0].get("image") if embeds else None
    if not image:
        print("  embed image: none")
        return

    url = image.get("url", "")
    print(f"  embed image: {image.get('content_type')}  {image.get('width')}x{image.get('height')}")
    print(f"    expires:  {attachment_expiry(url)}")
    if not url.startswith("https://"):
        print(f"    not a downloadable URL: {url}")
        return

    # The URL is signed, so no bot token goes with this request.
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.content
    if not data:
        print("    zero-byte image, not saved")
        return

    # Name the file by its real format, not the .png the game puts on it.
    path = out_dir / f"{message['id']}_screenshot.{image_format(data)}"
    path.write_bytes(data)
    print(f"    saved:    {path}  ({len(data)} bytes)")


def check_intent(message):
    if (message.get("webhook_id")
            and not message.get("content")
            and not message.get("embeds")
            and not message.get("attachments")):
        print("  WARNING: webhook message with no content, embeds or attachments."
              " The Message Content intent is probably off in the Developer Portal.")


def inspect_channel(session, label, channel_id, limit):
    print(f"\n##### Channel '{label}' ({channel_id})")
    response = discord_get(session, f"/channels/{channel_id}/messages", {"limit": limit})
    if response.status_code == 403:
        print("  403 Forbidden. Is the bot in the server, and does it have View Channel"
              " and Read Message History on this channel?")
        return
    if response.status_code == 404:
        print("  404 Not Found. Check the channel ID in config.json.")
        return
    if not response.ok:
        print(f"  HTTP {response.status_code}: {response.text}")
        return

    messages = sorted(response.json(), key=lambda m: int(m["id"]))
    if not messages:
        print("  No messages.")
        return

    out_dir = SAMPLES_DIR / label
    out_dir.mkdir(parents=True, exist_ok=True)

    for message in messages:
        try:
            json_path = out_dir / f"{message['id']}.json"
            json_path.write_text(json.dumps(message, indent=2, ensure_ascii=False), encoding="utf-8")
            print_summary(message)
            save_embed_image(message, out_dir)
            save_attachments(message, out_dir)
            check_intent(message)
            print(f"  raw json:   {json_path}")
        except Exception as error:
            print(f"  ERROR on message {message.get('id')}: {error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set-secrets", action="store_true", help="store the Discord bot token in Credential Manager")
    parser.add_argument("--limit", type=int, default=5, help="messages per channel, 1-100 (default 5)")
    parser.add_argument("--channel", choices=["internal", "public"], help="inspect only this channel")
    args = parser.parse_args()

    # Keep Danish letters and emoji from crashing the print when output is redirected.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.set_secrets:
        set_secrets()
        return

    token = keyring.get_password(KEYRING_SERVICE, KEYRING_DISCORD_TOKEN)
    if not token:
        sys.exit("No Discord bot token stored. Run: python inspect_messages.py --set-secrets")

    limit = max(1, min(args.limit, 100))
    channels = load_config().get("channels", {})
    if args.channel:
        channels = {args.channel: channels.get(args.channel, "")}

    session = requests.Session()
    session.headers["Authorization"] = f"Bot {token}"
    session.headers["User-Agent"] = "DiscordBot (darkswarm-bug-sync, 0.1)"

    for label, channel_id in channels.items():
        if not channel_id:
            print(f"\nSkipping '{label}': no channel ID in config.json.")
            continue
        inspect_channel(session, label, channel_id, limit)


if __name__ == "__main__":
    main()
