# Shows whether the scheduled jobs are set up, how their last runs went, and the end of each log.

$dataDir = Join-Path $env:LOCALAPPDATA 'darkswarm-bug-sync'
$jobs = @(
    @{ Name = 'DarkSwarm Bug Sync'; Log = 'sync.log' },
    @{ Name = 'DarkSwarm Bug Sort'; Log = 'sort.log' },
    @{ Name = 'DarkSwarm Board Backup'; Log = 'backup.log' }
)

foreach ($job in $jobs) {
    Write-Host "== $($job.Name)"
    $task = Get-ScheduledTask -TaskName $job.Name -ErrorAction SilentlyContinue
    if ($null -eq $task) {
        Write-Host 'Schedule: not set up. Run start-schedule.cmd to start it.'
    } else {
        $info = Get-ScheduledTaskInfo -TaskName $job.Name
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

    $log = Join-Path $dataDir $job.Log
    if (Test-Path $log) {
        Write-Host "Last 15 lines of $log"
        Write-Host '------------------------------------------------------------'
        Get-Content $log -Tail 15 -Encoding UTF8
    } else {
        Write-Host 'No log yet. It appears after the first scheduled run.'
    }
    Write-Host ''
}

# A missing Anthropic key or a Claude outage doesn't fail the sync, so say it here.
$syncLog = Join-Path $dataDir 'sync.log'
if (Test-Path $syncLog) {
    $warnings = Get-Content $syncLog -Tail 300 -Encoding UTF8 | Select-String -SimpleMatch -Pattern 'No Anthropic API key', 'Claude failed on'
    if ($warnings) {
        Write-Host 'WARNING: recent reports may have arrived without discipline labels:'
        $warnings | Select-Object -Last 3 | ForEach-Object { Write-Host "  $($_.Line.Trim())" }
    }
}
