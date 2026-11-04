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

3. Double-click **`setup.cmd`** in the new `trello-reporter` folder. When it asks, paste the Discord bot token, the Trello API key, the Trello token and the Anthropic API key, pressing Enter after each one. The sync doesn't need the Anthropic key; press Enter to skip it if you don't have it yet. Nothing shows on screen when you paste; that's on purpose, and it works over Remote Desktop.

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

## Backups of the board

`backup.py` saves a snapshot of the whole board: every card (archived ones too) with its list, position, labels, completion, name and description, plus every list, label, checklist and comment. Each snapshot is one file named after the time it was taken, in `%LOCALAPPDATA%\darkswarm-bug-sync\snapshots\`, for example `2026-11-04_11-45-30.json.gz`.

| Command | Does |
|---|---|
| `.\.venv\Scripts\python.exe backup.py` | Snapshot plus any screenshots not saved yet |
| `.\.venv\Scripts\python.exe backup.py --note before-moving-cards` | The same, with a note in the file name |
| `.\.venv\Scripts\python.exe backup.py --no-attachments` | Board only, takes a few seconds |

- Screenshots go into `snapshots\attachments\`, once each. The first run downloads all of them (a few GB, which takes a while); later runs only fetch new ones.
- `sort.py --label --apply` takes a snapshot by itself before it writes anything (`..._before-label-apply.json.gz`).
- To keep snapshots somewhere else, such as a OneDrive folder, set `"snapshots_dir"` in `config.json`. Never put them in the git repo: they contain player names.
- There's no restore script yet. A snapshot already lets you see where every card was and which labels it had.

## Discipline labels with Claude

`sort.py` gives each report one or two discipline labels (Tech, UI, Level Design, Art, Animation, Game Design, Audio), or Uncategorized or Unactionable, following the rules in `disciplines.md`. It never moves a card. `FINDINGS.md` ("Board workflow") explains the setup.

| Command | Does |
|---|---|
| `.\.venv\Scripts\python.exe sort.py --label --limit 20` | Preview: the labels the first 20 unlabelled cards would get. Writes nothing to the board |
| `.\.venv\Scripts\python.exe sort.py --label` | Preview for every card |
| `.\.venv\Scripts\python.exe sort.py --label --apply` | Writes the labels, and marks cards in DONE complete |
| `.\.venv\Scripts\python.exe sort.py --evaluate --model haiku` | Tests Claude against the cards the team sorted into discipline lists |

Where labels come from with `--label`:
- a card in a discipline list (Incoming Tech, ...) gets that list's label, without asking Claude
- a card in Unactionable gets the Unactionable label
- every other card (Incoming, DONE, theme lists) is labelled by Claude
- a card that already has a discipline label is left alone, so running it again is safe

The labels are created with their colours the first time `--apply` runs. Every change is logged in `label_changes.jsonl`. To undo everything, delete the discipline labels on the board in Trello (board menu, Labels): that removes them from every card.

## Sorting Incoming into theme lists

`sort.py --sort` moves labelled cards from Incoming into the theme list that fits them. Run it after creating new theme lists, or when Incoming has piled up.

| Command | Does |
|---|---|
| `.\.venv\Scripts\python.exe sort.py --sort --limit 20` | Preview for the 20 oldest cards in Incoming. Moves nothing |
| `.\.venv\Scripts\python.exe sort.py --sort` | Preview for every card in Incoming |
| `.\.venv\Scripts\python.exe sort.py --sort --apply` | Moves the cards. Takes a snapshot first |
| `.\.venv\Scripts\python.exe sort.py --undo-moves --since "2026-11-04 14:30"` | Moves the bot's cards back to Incoming. Without `--since`, every logged move. Shows the count per list and only goes ahead when you type `yes` |

- **Only cards in Incoming are moved.** DONE is never touched.
- **Automatic sorting is on for a list when its name starts with `##`.** `## Soft locking` gets cards sorted into it; `UI issues` doesn't. Rename a list to turn it on or off. Claude sees the name without the `##`. Incoming, DONE and Unactionable never take part, whatever their names.
- **Cards that stay in Incoming:** no theme fits, Uncategorized or Unactionable, marked complete, or no discipline label yet.
- **How Claude knows the themes:** the list names, plus up to 3 cards already in each list as examples. The more the team sorts by hand, the better the bot gets. If a name is ambiguous, write a line about it in `themes.md` in the repo folder (for example "Soft locking: the mission can't continue. Not for doors."). The file is optional.
- **Cost:** turning a list on or off, renaming it or filling it changes what Claude is told, so every card is asked again on the next run. That's about $0.15 for 450 cards with Haiku. A rerun with no changes is free.
- **Undo** only moves a card back if it's still in the list the bot put it in. Every move and undo is logged in `moves.jsonl`.

`--model` is `haiku`, `sonnet` or `opus`. Without it, the model in `config.json` under `sorting` is used (Haiku). `--limit` with `--evaluate` picks the same cards every run, so models can be compared on the same set.

Each run prints a summary and writes a report to `%LOCALAPPDATA%\darkswarm-bug-sync\`, with the cost of the run at the top. Answers are saved in `sort_answers.json` there, so asking the same model about the same card again costs nothing until `disciplines.md` changes. A preview followed by `--apply` only pays once. Shrunk screenshots are kept in `screenshots\`.
