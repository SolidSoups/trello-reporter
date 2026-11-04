"""Save a snapshot of the whole Trello board, so it can be put back later.

Each run writes one file named after the date and time it was taken:

    %LOCALAPPDATA%\\darkswarm-bug-sync\\snapshots\\2026-11-04_11-45-30.json.gz

It holds every card (archived ones too) with its list, position, labels,
completion, name and description, plus every list, label, checklist, custom
field and comment.

Screenshots aren't saved by default. Every card made by the sync links to its
Discord message, and fetching that message again gives a fresh link to the same
screenshot, so a restore can take it from there. That fails only if the Discord
message is deleted, or for files someone attached to a card by hand.
--attachments also saves every uploaded attachment into snapshots\\attachments\\,
once each, for a full copy now and then.

    python backup.py
    python backup.py --note before-moving-cards
    python backup.py --attachments         (also the screenshots: a few GB the first time)

Set "snapshots_dir" in config.json to keep the snapshots somewhere else, such
as a OneDrive folder. Snapshots contain player names and reports: never put
them in the git repo.
"""

import argparse
import datetime
import gzip
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from common import (
    DANISH_TIME, DATA_DIR, KEYRING_TRELLO_KEY, KEYRING_TRELLO_TOKEN, MAX_RETRIES, TIMEOUT, TRELLO_API,
    TRELLO_RATE_WINDOW, Trello, get_secret, load_config, start_log,
)

DEFAULT_SNAPSHOTS_DIR = DATA_DIR / "snapshots"
COMMENTS_PAGE = 1000  # the most Trello returns per request
DOWNLOAD_WORKERS = 4


def snapshots_dir(config):
    return Path(config["snapshots_dir"]) if config.get("snapshots_dir") else DEFAULT_SNAPSHOTS_DIR


def fetch_board(trello):
    """The board with everything on it, in one request."""
    return trello.request("GET", f"/boards/{trello.board_id}", params={
        "fields": "all",
        "cards": "all", "card_fields": "all",
        "card_attachments": "true", "card_attachment_fields": "all",
        "card_customFieldItems": "true",
        "checklists": "all",
        "lists": "all", "list_fields": "all",
        "labels": "all", "label_fields": "all", "labels_limit": 1000,
        "customFields": "true",
        "members": "all",
    })


def fetch_comments(trello):
    """Every comment on the board, newest first. Trello pages them 1000 at a time."""
    comments, before = [], None
    while True:
        params = {"filter": "commentCard", "limit": COMMENTS_PAGE}
        if before:
            params["before"] = before
        page = trello.request("GET", f"/boards/{trello.board_id}/actions", params=params)
        comments += page
        if len(page) < COMMENTS_PAGE:
            return comments
        before = page[-1]["id"]


def attachment_path(folder, attachment):
    """attachments\\<attachment id>.<extension>. The ID keeps names unique and safe on disk."""
    suffix = Path(attachment.get("name") or "").suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
        suffix = ""
    return folder / f"{attachment['id']}{suffix}"


def download(trello, card_id, attachment, path):
    url = f"{TRELLO_API}/cards/{card_id}/attachments/{attachment['id']}/download/{attachment['name']}"
    for _ in range(MAX_RETRIES):
        response = trello.session.get(url, timeout=TIMEOUT)
        if response.status_code != 429:
            break
        time.sleep(TRELLO_RATE_WINDOW)
    response.raise_for_status()
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(response.content)
    temp.replace(path)


def save_attachments(trello, board, folder):
    """Download uploaded attachments that aren't saved yet. Returns (downloaded, already saved, failed)."""
    folder.mkdir(parents=True, exist_ok=True)
    missing = []
    total = 0
    for card in board["cards"]:
        for attachment in card.get("attachments", []):
            if not attachment.get("isUpload"):
                continue  # a link, not a file stored on Trello
            total += 1
            path = attachment_path(folder, attachment)
            if not path.exists():
                missing.append((card["id"], attachment, path))
    if not missing:
        return 0, total, 0

    print(f"Downloading {len(missing)} attachments ({total - len(missing)} already saved).")
    failed = 0
    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        futures = {pool.submit(download, trello, card_id, attachment, path): attachment
                   for card_id, attachment, path in missing}
        for done, future in enumerate(as_completed(futures), 1):
            try:
                future.result()
            except Exception as error:  # one missing file shouldn't stop the backup
                failed += 1
                print(f"\n  {futures[future]['id']}: {type(error).__name__}: {error}")
            if sys.stdout.isatty():
                print(f"\r  {done}/{len(missing)}", end="", flush=True)
    if sys.stdout.isatty():
        print()
    return len(missing) - failed, total - len(missing), failed


def take_snapshot(trello, config, note="", attachments=False):
    """Save a snapshot of the board and return its path."""
    folder = snapshots_dir(config)
    folder.mkdir(parents=True, exist_ok=True)
    taken = datetime.datetime.now(DANISH_TIME)

    board = fetch_board(trello)
    comments = fetch_comments(trello)
    snapshot = {
        "taken_at": taken.isoformat(timespec="seconds"),
        "note": note,
        "board_id": trello.board_id,
        "board": board,
        "comments": comments,
    }

    name = taken.strftime("%Y-%m-%d_%H-%M-%S")
    if note:
        name += "_" + re.sub(r"[^A-Za-z0-9-]+", "-", note).strip("-")[:60]
    path = folder / f"{name}.json.gz"
    temp = path.with_name(path.name + ".tmp")
    with gzip.open(temp, "wt", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False)
    temp.replace(path)

    open_cards = sum(not card["closed"] for card in board["cards"])
    print(f"Snapshot: {path}")
    print(f"  {len(board['cards'])} cards ({open_cards} open), {len(board['lists'])} lists,"
          f" {len(board['labels'])} labels, {len(comments)} comments")

    if attachments:
        downloaded, saved, failed = save_attachments(trello, board, folder / "attachments")
        print(f"  Attachments: {downloaded} downloaded, {saved} already saved, {failed} failed")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--note", default="", help="a few words added to the file name, such as before-moving-cards")
    parser.add_argument("--attachments", action="store_true",
                        help="also save uploaded attachments (the screenshots); a few GB the first time")
    parser.add_argument("--log", action="store_true", help="write all output to backup.log, for the nightly scheduled run")
    args = parser.parse_args()
    if args.log:
        start_log("backup", sys.argv[1:])
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    key = get_secret(KEYRING_TRELLO_KEY)
    token = get_secret(KEYRING_TRELLO_TOKEN)
    if not key or not token:
        sys.exit("The Trello key and token must be stored. Run: python sync.py --set-secrets")
    config = load_config()
    try:
        take_snapshot(Trello(key, token, config), config, args.note, args.attachments)
    except RuntimeError as error:
        sys.exit(f"Stopped: {error}")


if __name__ == "__main__":
    main()
