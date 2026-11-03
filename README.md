# DarkSwarm bug report sync

Reads the bug reports the game posts to Discord and creates a Trello card for each one, with its screenshot. Each processed report gets a ⚙️ reaction from the bot. The script also saves how far it got, so the next run starts where the last one stopped.

| Command | Does |
|---|---|
| `sync.py` | Every message after the saved progress |
| `sync.py --next N` | Only the next N reports |
| `sync.py --dry-run [--next N]` | Preview. Writes nothing |
| `sync.py --latest N` | Test mode: newest N reports, no ⚙️, no saved progress |
| `sync.py --log` | Write output to the log file instead of the screen (for scheduled runs) |
| `sync.py --set-secrets` | Store the Discord and Trello secrets |

`FINDINGS.md` explains how reports are parsed and why.

All commands below are PowerShell, run in the repo folder.

## Setting up a PC

1. Install [Git](https://git-scm.com/download/win) and [Python 3.12](https://www.python.org/downloads/windows/).

2. Get the code and install the packages:

   ```powershell
   git clone https://github.com/SolidSoups/trello-reporter.git
   cd trello-reporter
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Store the secrets: the Discord bot token, the Trello API key and the Trello token. They go into Windows Credential Manager for your Windows user, never into a file.

   ```powershell
   .\.venv\Scripts\python.exe sync.py --set-secrets
   ```

   Nothing shows on screen when you paste, not even over Remote Desktop. Press Enter after each value.

4. `config.json` comes from the repo, with the channel, webhook, board and list IDs already filled in.

## First check

```powershell
.\.venv\Scripts\python.exe sync.py --dry-run --next 3
```

A new PC has no saved progress, so the first run reads the whole channel once. Every report that already has the bot's ⚙️ counts as "already done", and the preview starts at the first report without one.

## Only one machine runs the sync

The lock that stops overlapping runs only works on one machine. Before setting up a new PC, disable the scheduled task on the old one and stop running the sync there by hand. Two PCs running at once can create duplicate cards.

## Scheduling (every 15 minutes)

Run this block in the repo folder on the machine that does the sync:

```powershell
$repo = (Get-Location).Path
$action = New-ScheduledTaskAction -Execute "$repo\.venv\Scripts\python.exe" -Argument "sync.py --log" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2) -StartWhenAvailable
$cred = Get-Credential -UserName "$env:USERDOMAIN\$env:USERNAME" -Message "Your Windows password, so the task can run while you're signed out"
Register-ScheduledTask -TaskName "DarkSwarm Bug Sync" -Action $action -Trigger $trigger -Settings $settings -User $cred.UserName -Password $cred.GetNetworkCredential().Password
```

- The task runs as **your** Windows user, because the secrets are in your Credential Manager. Storing your password lets it run while you're disconnected from Remote Desktop or signed out.
- Never switch the task to "Do not store password". In that mode it can't read Credential Manager, and every run fails.
- If you change your Windows password, update it in the task (Task Scheduler → the task → Properties → OK), or the task stops running.
- On a domain machine, your account may need the "Log on as a batch job" right. Without it, registering or running the task fails with an access error.
- A run that's still busy when the next one is due causes that start to be skipped. A run is killed after 2 hours.

## Checking it

Run it now:

```powershell
Start-ScheduledTask "DarkSwarm Bug Sync"
```

See the last result. `LastTaskResult` 0 means OK, and 1 means the run failed; the log says why:

```powershell
Get-ScheduledTaskInfo "DarkSwarm Bug Sync"
```

Read the end of the log:

```powershell
Get-Content "$env:LOCALAPPDATA\darkswarm-bug-sync\sync.log" -Tail 40
```

Each run starts with a `=====` line and its time. When the log passes 1 MB, it's renamed to `sync.log.old` and a new one starts.

"Another run is in progress" in the log means the run found the lock taken and exited without doing anything. That's normal while a long run is busy. A lock older than 2 hours is treated as left over from a crash and removed.

## Files on the machine

All in `%LOCALAPPDATA%\darkswarm-bug-sync\`:

| File | What it is |
|---|---|
| `state.json` | Saved progress: the last processed message per channel. Deleting it is safe; the next run reads the channel from the start and skips ⚙️ reports. |
| `sync.log` | Output of `--log` runs |
| `sync.lock` | Exists only while a run is busy |

## Updating

```powershell
git pull
```

The next scheduled run uses the new code. If `requirements.txt` changed, also run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Turning it off

```powershell
Disable-ScheduledTask "DarkSwarm Bug Sync"
```

To remove the task completely:

```powershell
Unregister-ScheduledTask "DarkSwarm Bug Sync"
```
