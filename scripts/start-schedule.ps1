# Starts the sync every 15 minutes as a Windows scheduled task, and runs it once right away.
# Running it again replaces the existing schedule.

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo '.venv\Scripts\python.exe'
$taskName = 'DarkSwarm Bug Sync'

if (-not (Test-Path $python)) {
    Write-Host 'This PC is not set up yet. Run setup.cmd first.'
    exit 1
}

$action = New-ScheduledTaskAction -Execute $python -Argument 'sync.py --log' -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15)
# Skip a start while the previous run is still busy, and kill a run after 2 hours (the stale-lock age in sync.py).
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2) -StartWhenAvailable

# The task runs as you, because the secrets are in your Credential Manager.
# Storing your password lets it run while you're disconnected or signed out.
Write-Host 'Enter your Windows password in the dialog. The task needs it to run while you are signed out.'
$cred = Get-Credential -UserName "$env:USERDOMAIN\$env:USERNAME" -Message 'Your Windows password, so the sync can run while you are signed out'
if ($null -eq $cred) {
    Write-Host 'Cancelled. Nothing changed.'
    exit 1
}

try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
        -User $cred.UserName -Password $cred.GetNetworkCredential().Password -Force | Out-Null
} catch {
    Write-Host "Creating the schedule failed: $($_.Exception.Message)"
    Write-Host 'If it says the password is wrong, run start-schedule.cmd again.'
    Write-Host 'If it says access is denied, right-click start-schedule.cmd and choose "Run as administrator".'
    exit 1
}

Start-ScheduledTask -TaskName $taskName
Write-Host ''
Write-Host 'The sync now runs every 15 minutes, and the first run has started.'
Write-Host 'Run status.cmd in a minute to see the result. Run stop-schedule.cmd to stop it.'
