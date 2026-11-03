# Stops the scheduled sync. A run that is busy is allowed to finish first,
# so no card is left without its gear reaction.

$ErrorActionPreference = 'Stop'
$taskName = 'DarkSwarm Bug Sync'

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Host 'No schedule is set up. Nothing to stop.'
    exit 0
}

# Disabling first means no new run can start while we wait.
Disable-ScheduledTask -TaskName $taskName | Out-Null

if ((Get-ScheduledTask -TaskName $taskName).State -eq 'Running') {
    Write-Host 'A run is busy. Waiting for it to finish (this can take a few minutes)...'
    while ((Get-ScheduledTask -TaskName $taskName).State -eq 'Running') {
        Start-Sleep -Seconds 5
    }
}

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Host 'Stopped. The sync no longer runs. Run start-schedule.cmd to start it again.'
