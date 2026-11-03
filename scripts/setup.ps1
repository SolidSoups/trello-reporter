# One-time setup of this PC: Python environment, packages, secrets, and a read-only check.
# Run it again any time; it skips what's already done.

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo '.venv\Scripts\python.exe'
Set-Location $repo

Write-Host '1/4  Checking for Python 3.12'
$found = $false
if (Get-Command py -ErrorAction SilentlyContinue) {
    # Avoid redirecting stderr here: PowerShell 5.1 turns it into an error and stops the script.
    & py -3.12 -c "import sys" | Out-Null
    $found = ($LASTEXITCODE -eq 0)
}
if (-not $found) {
    Write-Host 'Python 3.12 not found. Install it from https://www.python.org/downloads/windows/ and run setup.cmd again.'
    exit 1
}

Write-Host '2/4  Creating the Python environment (.venv)'
if (Test-Path $python) {
    Write-Host '     Already there.'
} else {
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Host 'Creating .venv failed.'; exit 1 }
}

Write-Host '3/4  Installing packages'
& $python -m pip install --quiet --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host 'Installing packages failed.'; exit 1 }

Write-Host '4/4  Storing secrets (Discord bot token, Trello API key, Trello token)'
& $python sync.py --set-secrets
if ($LASTEXITCODE -ne 0) { Write-Host 'Storing secrets failed.'; exit 1 }

Write-Host ''
Write-Host 'Check: previewing the next 3 reports. This writes nothing.'
& $python sync.py --dry-run --next 3 --channel public
if ($LASTEXITCODE -ne 0) {
    Write-Host ''
    Write-Host 'The check failed. Read the message above, fix it, and run setup.cmd again.'
    exit 1
}

Write-Host ''
Write-Host 'Setup done. Next: run start-schedule.cmd'
