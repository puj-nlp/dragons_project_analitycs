$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$reportLogDir = Join-Path $repo "logs\reports"
New-Item -ItemType Directory -Force -Path $reportLogDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stdout = Join-Path $reportLogDir "scheduled_report_$stamp.out.log"
$stderr = Join-Path $reportLogDir "scheduled_report_$stamp.err.log"

try {
    py scripts\report_processing_status.py --write *> $stdout
} catch {
    $_ | Out-String | Set-Content -Path $stderr -Encoding UTF8
    throw
}
