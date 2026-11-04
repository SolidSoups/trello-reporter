# Starts the three scheduled jobs and runs the sync once right away:
#   DarkSwarm Bug Sync      every 15 minutes  sync.py --log         new reports become labelled, sorted cards
#   DarkSwarm Bug Sort      every hour        sort.py --sort --apply --log   cards in Incoming find new ## lists
#   DarkSwarm Board Backup  every night 03:00 backup.py --log       snapshot of the board and new screenshots
# Running it again replaces the existing schedule.

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Host 'This PC is not set up yet. Run setup.cmd first.'
    exit 1
}

$now = Get-Date
$jobs = @(
    @{ Name = 'DarkSwarm Bug Sync'; Arguments = 'sync.py --log'
       Trigger = New-ScheduledTaskTrigger -Once -At $now -RepetitionInterval (New-TimeSpan -Minutes 15)
       Limit = New-TimeSpan -Hours 2 },
    # Starts 7 minutes after the sync, so the two rarely want the board at the same time.
    @{ Name = 'DarkSwarm Bug Sort'; Arguments = 'sort.py --sort --apply --log'
       Trigger = New-ScheduledTaskTrigger -Once -At $now.AddMinutes(7) -RepetitionInterval (New-TimeSpan -Hours 1)
       Limit = New-TimeSpan -Hours 1 },
    # The first night downloads every screenshot, so it gets more time.
    @{ Name = 'DarkSwarm Board Backup'; Arguments = 'backup.py --log'
       Trigger = New-ScheduledTaskTrigger -Daily -At '03:00'
       Limit = New-TimeSpan -Hours 4 }
)

# The tasks run as you, because the secrets are in your Credential Manager.
# Storing your password lets them run while you're disconnected or signed out.
Write-Host 'Enter your Windows password in the dialog. The tasks need it to run while you are signed out.'
$cred = Get-Credential -UserName "$env:USERDOMAIN\$env:USERNAME" -Message 'Your Windows password, so the jobs can run while you are signed out'
if ($null -eq $cred) {
    Write-Host 'Cancelled. Nothing changed.'
    exit 1
}

foreach ($job in $jobs) {
    $action = New-ScheduledTaskAction -Execute $python -Argument $job.Arguments -WorkingDirectory $repo
    # Skip a start while the previous run is still busy, and stop a run that takes far too long.
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit $job.Limit -StartWhenAvailable
    try {
        Register-ScheduledTask -TaskName $job.Name -Action $action -Trigger $job.Trigger -Settings $settings `
            -User $cred.UserName -Password $cred.GetNetworkCredential().Password -Force | Out-Null
    } catch {
        Write-Host "Creating '$($job.Name)' failed: $($_.Exception.Message)"
        Write-Host 'If it says the password is wrong, run start-schedule.cmd again.'
        Write-Host 'If it says access is denied, right-click start-schedule.cmd and choose "Run as administrator".'
        exit 1
    }
    Write-Host "Scheduled: $($job.Name)  ($($job.Arguments))"
}

Start-ScheduledTask -TaskName 'DarkSwarm Bug Sync'
Write-Host ''
Write-Host 'The sync runs every 15 minutes, the sort every hour and the backup every night at 03:00.'
Write-Host 'The first sync has started. Run status.cmd in a minute to see the result. Run stop-schedule.cmd to stop everything.'
