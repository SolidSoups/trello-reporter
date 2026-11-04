"""What sync.py, sort.py and backup.py share: paths, secrets, the Trello client, the lock and log files."""

import datetime
import getpass
import json
import os
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import keyring
import requests

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "darkswarm-bug-sync"
# One lock for every run that writes to the board, so the sync and the sort never overlap.
LOCK_PATH = DATA_DIR / "sync.lock"
LOCK_MAX_AGE = 2 * 60 * 60  # seconds; an older lock was left by a run that crashed or was killed
LOG_MAX_BYTES = 1024 * 1024

KEYRING_SERVICE = "darkswarm-bug-sync"
KEYRING_DISCORD_TOKEN = "discord_bot_token"
KEYRING_TRELLO_KEY = "trello_api_key"
KEYRING_TRELLO_TOKEN = "trello_token"
KEYRING_ANTHROPIC_KEY = "anthropic_api_key"
SECRETS = [
    (KEYRING_DISCORD_TOKEN, "Discord bot token"),
    (KEYRING_TRELLO_KEY, "Trello API key"),
    (KEYRING_TRELLO_TOKEN, "Trello token"),
    (KEYRING_ANTHROPIC_KEY, "Anthropic API key"),
]

TRELLO_API = "https://api.trello.com/1"
TIMEOUT = 30
MAX_RETRIES = 5
TRELLO_RATE_WINDOW = 10  # Trello allows about 100 requests per 10 seconds per token

DANISH_TIME = ZoneInfo("Europe/Copenhagen")


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


def get_secret(name):
    return keyring.get_password(KEYRING_SERVICE, name)


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


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

    def label_id(self, name, color=None):
        """Return the ID of the label with this name, creating it the first time."""
        if name not in self.labels:
            label = self.request("POST", "/labels", json={"name": name, "color": color, "idBoard": self.board_id})
            self.labels[name] = label["id"]
            print(f"  Created label '{name}'")
        return self.labels[name]


def start_log(name, arguments):
    """Send all output, errors and tracebacks included, to <name>.log in the data folder."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{name}.log"
    if path.exists() and path.stat().st_size > LOG_MAX_BYTES:
        os.replace(path, path.with_name(f"{name}.log.old"))
    log = open(path, "a", encoding="utf-8", errors="replace", buffering=1)
    sys.stdout = sys.stderr = log
    now = datetime.datetime.now(DANISH_TIME).strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n===== {now} {name} {' '.join(arguments)}")


def lock_started(path):
    return datetime.datetime.fromtimestamp(path.stat().st_mtime, DANISH_TIME).strftime("%Y-%m-%d %H:%M:%S")


def acquire_lock(holder):
    """Return True if this run now holds the lock, False if another run holds it."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            # Exclusive create fails if the file exists, so two runs can't both get it.
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age = time.time() - LOCK_PATH.stat().st_mtime
                started = lock_started(LOCK_PATH)
                other = LOCK_PATH.read_text(encoding="utf-8").strip()
            except FileNotFoundError:
                continue  # the other run finished in between
            if age < LOCK_MAX_AGE:
                print(f"Another run is in progress ({other or 'unknown'}, started {started}). Exiting.")
                return False
            print(f"Removing a stale lock from {started}, left by a run that didn't finish.")
            LOCK_PATH.unlink(missing_ok=True)
            continue
        with os.fdopen(fd, "w") as f:
            f.write(f"{holder}, pid {os.getpid()}\n")
        return True
    print("Couldn't take the lock. Exiting.")
    return False


def release_lock():
    LOCK_PATH.unlink(missing_ok=True)
