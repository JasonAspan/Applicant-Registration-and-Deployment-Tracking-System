$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root "ats_env\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    py -3 -m venv (Join-Path $Root "ats_env")
}

& $Python -m pip install -r (Join-Path $Root "requirements.txt")
& $Python (Join-Path $Root "system_diagnostics.py")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$PortInUse = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 5000 -ErrorAction SilentlyContinue
if ($PortInUse) {
    Write-Host "System is already running at http://127.0.0.1:5000"
    exit 0
}

& $Python (Join-Path $Root "app.py")
