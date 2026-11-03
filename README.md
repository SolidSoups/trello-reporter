# DarkSwarm bug report sync

Reads the bug reports the game posts to Discord and creates a Trello card for each one, with its screenshot. Each processed report gets a ⚙️ reaction from the bot. The script also saves how far it got, so the next run starts where the last one stopped.

On the build computer it runs by itself every 15 minutes. These four files in the repo folder control it. Double-click them:

| File | Does |
|---|---|
| `setup.cmd` | Prepares the PC, once: Python environment, packages, secrets, and a check that writes nothing |
| `start-schedule.cmd` | Starts the sync every 15 minutes, and runs it once right away |
| `stop-schedule.cmd` | Stops the sync. A run that's busy is allowed to finish first |
| `status.cmd` | Shows whether the sync is running, how the last run went, and the end of the log |

## Setting up a PC

1. Install [Git](https://git-scm.com/download/win) and [Python 3.12](https://www.python.org/downloads/windows/). Keep the Python installer's default "py launcher" option.

2. Get the code. In PowerShell, in the folder where you want it:

   ```powershell
   git clone https://github.com/SolidSoups/trello-reporter.git
   ```

3. Double-click **`setup.cmd`** in the new `trello-reporter` folder. When it asks, paste the Discord bot token, the Trello API key and the Trello token, pressing Enter after each one. Nothing shows on screen when you paste; that's on purpose, and it works over Remote Desktop.

   It ends with a preview of the next 3 reports, which writes nothing. On a new PC, reports that already have the bot's ⚙️ count as "already done", so the preview only shows reports that haven't been processed yet.

4. Double-click **`start-schedule.cmd`** and enter your Windows password in the dialog.

5. Wait a minute, then double-click **`status.cmd`**. The last run should say `OK`.

That's all. The sync keeps running after you disconnect from Remote Desktop and after the PC restarts.

## Only one machine runs the sync

Before setting up a new PC, run `stop-schedule.cmd` on the old one and stop running the sync there by hand. Two PCs running at once can create duplicate cards.

## If something goes wrong

- **`start-schedule.cmd` says the password is wrong:** run it again.
- **`start-schedule.cmd` says access is denied:** right-click it and choose **Run as administrator**. On a domain machine, your account may also need the "Log on as a batch job" right.
- **`status.cmd` says FAILED:** the log below it says why. The next run tries again from the same report.
- **You changed your Windows password:** run `start-schedule.cmd` again, or every run fails.
- **"Another run is in progress" in the log:** a run found another one still busy and exited without doing anything. That's normal. A lock older than 2 hours is treated as left over from a crash and removed.

## Updating

In PowerShell, in the `trello-reporter` folder:

```powershell
git pull
```

Then double-click `setup.cmd` again in case the packages changed. Press Enter at each secret prompt to keep the stored values. The schedule picks up the new code on its next run.

## Files on the machine

All in `%LOCALAPPDATA%\darkswarm-bug-sync\`:

| File | What it is |
|---|---|
| `state.json` | Saved progress: the last processed message per channel. Deleting it is safe; the next run reads the channel from the start and skips ⚙️ reports. |
| `sync.log` | Output of the scheduled runs. Past 1 MB it's renamed to `sync.log.old`. |
| `sync.lock` | Exists only while a run is busy |

The secrets are in Windows Credential Manager under `darkswarm-bug-sync`, for the Windows user who ran `setup.cmd`. The schedule runs as that same user.

## Running it by hand

Not needed on the build computer. For testing, in PowerShell, in the repo folder:

| Command | Does |
|---|---|
| `.\.venv\Scripts\python.exe sync.py` | Every message after the saved progress |
| `.\.venv\Scripts\python.exe sync.py --next N` | Only the next N reports |
| `.\.venv\Scripts\python.exe sync.py --dry-run --next N` | Preview. Writes nothing |
| `.\.venv\Scripts\python.exe sync.py --latest N` | Test mode: newest N reports, no ⚙️, no saved progress |
| `.\.venv\Scripts\python.exe sync.py --log` | Output to the log file instead of the screen |
| `.\.venv\Scripts\python.exe sync.py --set-secrets` | Change a stored secret |

`FINDINGS.md` explains how reports are parsed and why.
