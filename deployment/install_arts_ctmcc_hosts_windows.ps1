$ErrorActionPreference = 'Stop'

$hostsPath = 'C:\Windows\System32\drivers\etc\hosts'
$entry = '172.16.9.62 arts.ctmcc'

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if (-not $isAdmin) {
    Write-Host 'This script must be run as Administrator.' -ForegroundColor Red
    Write-Host 'Right-click PowerShell and choose "Run as administrator", then run this script again.'
    exit 1
}

if (-not (Test-Path -LiteralPath $hostsPath)) {
    throw "Hosts file not found at $hostsPath"
}

$content = Get-Content -LiteralPath $hostsPath
$content = $content | Where-Object { $_ -notmatch '^\s*\d+\.\d+\.\d+\.\d+\s+arts\.ctmcc\s*$' }
$content += $entry
Set-Content -LiteralPath $hostsPath -Value $content -Encoding ASCII

ipconfig /flushdns | Out-Null

Write-Host "Added: $entry" -ForegroundColor Green
Write-Host 'Open this URL in your browser: http://arts.ctmcc'
