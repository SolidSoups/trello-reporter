# Shows whether the scheduled sync is set up, how its last run went, and the end of the log.

$taskName = 'DarkSwarm Bug Sync'
$log = Join-Path $env:LOCALAPPDATA 'darkswarm-bug-sync\sync.log'

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Host 'Schedule: not set up. Run start-schedule.cmd to start it.'
} else {
    $info = Get-ScheduledTaskInfo -TaskName $taskName
    $result = switch ($info.LastTaskResult) {
        0          { 'OK' }
        1          { 'FAILED (see the log below)' }
        267011     { 'has not run yet' }
        267009     { 'running now' }
        default    { "code $($info.LastTaskResult)" }
    }
    Write-Host "Schedule:    $($task.State)"
    Write-Host "Last run:    $($info.LastRunTime)  ($result)"
    Write-Host "Next run:    $($info.NextRunTime)"
}

Write-Host ''
if (Test-Path $log) {
    Write-Host "Last 30 lines of $log"
    Write-Host '------------------------------------------------------------'
    Get-Content $log -Tail 30 -Encoding UTF8
} else {
    Write-Host 'No log yet. It appears after the first scheduled run.'
}
