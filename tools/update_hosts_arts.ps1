$hostsPath = 'C:\Windows\System32\drivers\etc\hosts'
$defaultLines = @(
    '# Copyright (c) Microsoft Corp.',
    '#',
    '# This is a sample HOSTS file used by Microsoft TCP/IP for Windows.',
    '#',
    '# IP address and host name entries should be kept on individual lines.',
    '#',
    '127.0.0.1 localhost',
    '::1 localhost',
    '172.16.9.62 arts.ctmcc'
)

$existing = @()
if (Test-Path -LiteralPath $hostsPath) {
    $existing = Get-Content -LiteralPath $hostsPath
}

if ($existing.Count -gt 0) {
    $lines = $existing | Where-Object { $_ -notmatch 'arts\.ctmcc' }
    $lines += '172.16.9.62 arts.ctmcc'
} else {
    $lines = $defaultLines
}

Set-Content -LiteralPath $hostsPath -Value $lines -Encoding ASCII
ipconfig /flushdns | Out-Null
Write-Host 'Updated hosts entry: 172.16.9.62 arts.ctmcc'
Start-Sleep -Seconds 3
