# DarkSwarm bug report sync

Reads the bug reports the game posts to Discord and creates a Trello card for each one, with its screenshot. Claude gives each new card its discipline labels and puts it in a matching `##` theme list, or in Incoming when none fits. Each processed report gets a ⚙️ reaction from the bot. The script also saves how far it got, so the next run starts where the last one stopped.

On the build computer, three jobs run by themselves:

| Job | When | Does |
|---|---|---|
| Sync (`sync.py`) | Every 15 minutes | New reports become labelled cards, in a `##` list or Incoming |
| Sort (`sort.py --sort --apply`) | Every 15 minutes, 5 minutes after the sync | Cards waiting in Incoming move into `##` lists that fit them, including lists created since |
| Backup (`backup.py`) | Every night at 03:00 | A snapshot of the board. Screenshots stay in Discord |

These four files in the repo folder control them. Double-click them:

| File | Does |
|---|---|
| `setup.cmd` | Prepares the PC, once: Python environment, packages, secrets, and a check that writes nothing |
| `start-schedule.cmd` | Starts all three jobs, and runs the sync once right away |
| `stop-schedule.cmd` | Stops all three. A run that's busy is allowed to finish first |
| `status.cmd` | Shows each job's last run and the end of its log, plus a warning if new reports arrived unlabelled |
| `run-sync.cmd` | Runs the sync now, with its output on screen |
| `run-sort.cmd` | Runs the sort now: moves waiting cards from Incoming into `##` lists |
| `run-backup.cmd` | Takes a board snapshot now |

The `run-` files use the same lock and data folder as the scheduled jobs, so they're safe to run at any time; if a scheduled run is busy, they say so and exit. Run them on the build computer only.

Undoing the bot's moves (`sort.py --undo-moves`) is deliberately not a double-click file. It's typed in PowerShell and asks for `yes` before it moves anything.

## For the team: working with the board

- **New reports** arrive labelled, in a `##` list or in Incoming. Filter by your discipline label to find yours.
- **A list sorts automatically when its name starts with `##`.** To add a theme without the bot filling it too early:
  1. Create the list **without** `##`, for example `Aiming issues`.
  2. Drag in 2 or 3 typical reports. Claude learns the theme from these.
  3. Rename it to `## Aiming issues`. Within 15 minutes, matching cards from Incoming move in, and new reports go there directly. So add the `##` last: the bot starts filling the list almost straight away.
- **To empty a list, rename it to `!! <name>`,** for example `!! General UI`. Within 15 minutes, every card in it moves to the `##` list that fits it, or to Incoming if none does. Cards without labels get them first. Once the list is empty, it's archived (not deleted: you can bring it back from the board menu). Undo with `sort.py --undo-moves`, which also reopens the list.
- **Never combine the prefixes.** A name like `!!## Aiming` or `## !! Aiming` is refused and left alone, and the log says why. Incoming, DONE and Unactionable are never emptied, whatever you call them.
- **Reports in other languages** arrive with an English title. The player's own words stay at the top of the description, with `` [Translated] `...` `` under them. Write a translation by hand the same way and the bot leaves the card alone.
- **Fixed?** Tick the card complete and leave it in its list.
- **Archive, never delete.** Archived cards and lists can be brought back; deleted ones can't.
- **Don't rename** the nine discipline labels, Incoming, DONE or Unactionable. The scripts find them by name or ID.
- **A wrong label or list?** Just fix it by hand. The bot never touches a card again once it's out of Incoming, and your fixes become examples it learns from.

## Setting up a PC

1. Install [Git](https://git-scm.com/download/win) and [Python 3.12](https://www.python.org/downloads/windows/). Keep the Python installer's default "py launcher" option.

2. Get the code. In PowerShell, in the folder where you want it:

   ```powershell
   git clone https://github.com/SolidSoups/trello-reporter.git
   ```

3. Double-click **`setup.cmd`** in the new `trello-reporter` folder. When it asks, paste the Discord bot token, the Trello API key, the Trello token and the Anthropic API key, pressing Enter after each one. Without the Anthropic key, reports still arrive, but unlabelled and in Incoming. Nothing shows on screen when you paste; that's on purpose, and it works over Remote Desktop.

   It ends with a preview of the next 3 reports, which writes nothing. On a new PC, reports that already have the bot's ⚙️ count as "already done", so the preview only shows reports that haven't been processed yet.

4. Double-click **`start-schedule.cmd`** and enter your Windows password in the dialog.

5. Wait a minute, then double-click **`status.cmd`**. The last run should say `OK`.

That's all. The sync keeps running after you disconnect from Remote Desktop and after the PC restarts.

## Only one machine runs the jobs

Before setting up a new PC, run `stop-schedule.cmd` on the old one and stop running the scripts there by hand. Two PCs running at once can create duplicate cards. Commands that write to the board (`--apply`, `--undo-moves`) also belong on the build computer: the logs that say what the bot did, and that undo and the examples depend on, live on the PC that ran them.

## If something goes wrong

- **`start-schedule.cmd` says the password is wrong:** run it again.
- **`start-schedule.cmd` says access is denied:** right-click it and choose **Run as administrator**. On a domain machine, your account may also need the "Log on as a batch job" right.
- **`status.cmd` says FAILED:** the log below it says why. The next run tries again from the same report.
- **You changed your Windows password:** run `start-schedule.cmd` again, or every run fails.
- **"Another run is in progress" in the log:** a run found another one still busy and exited without doing anything. The sync and the sort share one lock, so this also happens when they meet. That's normal. A lock older than 2 hours is treated as left over from a crash and removed.
- **`status.cmd` warns that reports arrived without discipline labels:** Claude couldn't be reached, or no Anthropic key is stored. The sync labels those cards by itself on a later run once Claude works again. If the key is missing, run `setup.cmd` again.

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
| `sync.log`, `sort.log`, `backup.log` | Output of the scheduled runs. Past 1 MB each is renamed to `.log.old`. |
| `sync.lock` | Exists only while a sync or a writing sort run is busy |
| `label_changes.jsonl`, `moves.jsonl` | Every label and move the bot made. Undo and "which labels a person chose" depend on them |
| `sort_answers.json`, `screenshots\` | Claude's cached answers and shrunk screenshots |
| `snapshots\` | Board backups |

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
| `.\.venv\Scripts\python.exe backup.py` | Snapshot of the board, takes a few seconds |
| `.\.venv\Scripts\python.exe backup.py --note before-moving-cards` | The same, with a note in the file name |
| `.\.venv\Scripts\python.exe backup.py --attachments` | Also saves the screenshots, into `snapshots\attachments\`, once each. A few GB the first time |

- **Screenshots aren't saved by default.** Each card links to its Discord message, and fetching that message again gives a fresh link to the screenshot. That only fails if the Discord message is deleted, or for files someone attached to a card by hand. Run `--attachments` now and then for a full copy.
- The nightly backup on the build computer saves the board only.
- `sort.py --label --apply`, `sort.py --sort --apply` and `--undo-moves` take a snapshot by themselves before they write anything.
- To keep snapshots somewhere else, such as a OneDrive folder, set `"snapshots_dir"` in `config.json`. Never put them in the git repo: they contain player names.
- There's no restore script yet. A snapshot already lets you see where every card was and which labels it had.

## Discipline labels with Claude

`sort.py` gives each report one or two discipline labels (Tech, UI, Level Design, Art, Animation, Game Design, Audio), or Uncategorized or Unactionable, following the rules in `disciplines.md`. It never moves a card. `FINDINGS.md` ("Board workflow") explains the setup.

| Command | Does |
|---|---|
| `.\.venv\Scripts\python.exe sort.py --label --limit 20` | Preview: the labels the first 20 unlabelled cards would get. Writes nothing to the board |
| `.\.venv\Scripts\python.exe sort.py --label` | Preview for every card |
| `.\.venv\Scripts\python.exe sort.py --label --apply` | Writes the labels, and marks cards in DONE complete |
| `.\.venv\Scripts\python.exe sort.py --evaluate --model haiku` | Tests Claude against the labels a person chose. Reads only |

Where labels come from with `--label`:
- a card in Unactionable gets the Unactionable label
- every other card is labelled by Claude
- a card that already has a discipline label is left alone, so running it again is safe

**Which labels count as the team's:** labels the team set, and labels someone changed after Claude set them. `label_changes.jsonl` records what Claude set, so the scripts can tell the two apart. `--evaluate` tests against these, and `--label` takes its example cards from them. So when someone fixes a wrong label in Trello, Claude learns from it. On a PC without that log, every label counts as the team's.

The labels are created with their colours the first time `--apply` runs. Every change is logged in `label_changes.jsonl`. To undo everything, delete the discipline labels on the board in Trello (board menu, Labels): that removes them from every card.

## Translating cards already on the board

New reports are translated by the sync. For cards that were on the board before that:

| Command | Does |
|---|---|
| `.\.venv\Scripts\python.exe sort.py --translate` | Preview: which open cards are in another language, with their English title and translation. Changes nothing |
| `.\.venv\Scripts\python.exe sort.py --translate --apply` | Writes them. Takes a snapshot first |
| `.\.venv\Scripts\python.exe sort.py --undo-translations --since "2026-11-04 17:00"` | Puts the old title and description back. Typed, never double-clicked, and asks for `yes` |

- Cards in DONE and cards that already have a translation (`[Translated]` or `[Translate]`, from the bot or by hand) are left alone.
- Only reports mostly in another language are translated. A stray foreign word or a one-word report isn't.
- Each change is logged in `translations.jsonl` with the old text. Undo only changes cards nobody has edited since. Run `--apply` and the undo on the build computer, where the log lives.

## Sorting Incoming into theme lists

`sort.py --sort` moves labelled cards from Incoming into the theme list that fits them. On the build computer it runs by itself 5 minutes after each sync; run it by hand when you don't want to wait. New reports don't need it: the sync places them as they arrive.

| Command | Does |
|---|---|
| `.\.venv\Scripts\python.exe sort.py --sort --limit 20` | Preview for the 20 oldest cards in Incoming. Moves nothing |
| `.\.venv\Scripts\python.exe sort.py --sort` | Preview for every card in Incoming |
| `.\.venv\Scripts\python.exe sort.py --sort --apply` | Moves the cards. Takes a snapshot first |
| `.\.venv\Scripts\python.exe sort.py --undo-moves --since "2026-11-04 14:30"` | Moves the bot's cards back to Incoming. Without `--since`, every logged move. Shows the count per list and only goes ahead when you type `yes` |

- **Only cards in Incoming are moved.** DONE is never touched.
- **Automatic sorting is on for a list when its name starts with `##`.** `## Soft locking` gets cards sorted into it; `UI issues` doesn't. Rename a list to turn it on or off. Claude sees the name without the `##`. Incoming, DONE and Unactionable never take part, whatever their names.
- **Cards that stay in Incoming:** no theme fits, Uncategorized or Unactionable, or no discipline label yet.
- **Completed cards are sorted too,** and keep their tick, so each theme list shows its fixed reports next to the open ones.
- **`!!` lists are emptied in the same run:** each card goes to a fitting `##` list or Incoming, and the list is archived once it has no open cards. A card Claude fails on stays, and the list stays open until the next run gets it. The preview report has a section per `!!` list showing where each card would go.
- **How Claude knows the themes:** the list names, plus up to 3 cards already in each list as examples. Examples are cards a person put there; cards the bot moved are only used when a list has nothing else, so a wrong move doesn't teach the bot to repeat it. The more the team sorts by hand, the better the bot gets. If a name is ambiguous, write a line about it in `themes.md` in the repo folder (for example "Soft locking: the mission can't continue. Not for doors."). The file is optional.
- **Cost:** turning a list on or off, renaming it or filling it changes what Claude is told, so every card is asked again on the next run. That's about $0.15 for 450 cards with Haiku. A rerun with no changes is free.
- **Undo** only moves a card back if it's still in the list the bot put it in, checked again right before each move. Every move and undo is logged in `moves.jsonl`.
- **The logs are per PC.** `moves.jsonl` and `label_changes.jsonl` live on the PC that ran the command. Run `--apply` and `--undo-moves` on one machine, or undo and the "team's labels" check won't know what the bot did.

`--model` is `haiku`, `sonnet` or `opus`. Without it, the model in `config.json` under `sorting` is used (Haiku). `--limit` with `--evaluate` picks the same cards every run, so models can be compared on the same set.

Each run prints a summary and writes a report to `%LOCALAPPDATA%\darkswarm-bug-sync\`, with the cost of the run at the top. Answers are saved in `sort_answers.json` there, so asking the same model about the same card again costs nothing until `disciplines.md` changes. A preview followed by `--apply` only pays once. Shrunk screenshots are kept in `screenshots\`.
