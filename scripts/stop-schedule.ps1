# Stops the scheduled sync, sort and backup. A run that is busy is allowed to finish first,
# so no card is left without its gear reaction and no move is left half done.

$ErrorActionPreference = 'Stop'
$taskNames = @('DarkSwarm Bug Sync', 'DarkSwarm Bug Sort', 'DarkSwarm Board Backup')

$tasks = @($taskNames | ForEach-Object { Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue } | Where-Object { $_ })
if ($tasks.Count -eq 0) {
    Write-Host 'No schedule is set up. Nothing to stop.'
    exit 0
}

# Disabling first means no new run can start while we wait.
foreach ($task in $tasks) {
    Disable-ScheduledTask -TaskName $task.TaskName | Out-Null
}

foreach ($task in $tasks) {
    if ((Get-ScheduledTask -TaskName $task.TaskName).State -eq 'Running') {
        Write-Host "$($task.TaskName) is busy. Waiting for it to finish (this can take a few minutes)..."
        while ((Get-ScheduledTask -TaskName $task.TaskName).State -eq 'Running') {
            Start-Sleep -Seconds 5
        }
    }
    Unregister-ScheduledTask -TaskName $task.TaskName -Confirm:$false
    Write-Host "Stopped: $($task.TaskName)"
}
Write-Host 'Nothing runs on a schedule any more. Run start-schedule.cmd to start it again.'
