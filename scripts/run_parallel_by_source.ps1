param(
    [string]$RunPrefix = "full_by_source_gliner25_multi_no_llm",
    [string[]]$Sources = @("media_cloud", "gdelt", "bluesky"),
    [string]$Model = "fastino/gliner2.5-multi-v1",
    [switch]$WithLlm,
    [switch]$NoHf,
    [int]$MaxDocuments = 0
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$runnerLogDir = Join-Path $repo "logs\variable_processing\runner"
New-Item -ItemType Directory -Force -Path $runnerLogDir | Out-Null

$normalizedSources = @()
foreach ($sourceValue in $Sources) {
    foreach ($source in ($sourceValue -split ",")) {
        $trimmed = $source.Trim()
        if ($trimmed) {
            $normalizedSources += $trimmed
        }
    }
}
$Sources = $normalizedSources | Select-Object -Unique

$processes = @()
foreach ($source in $Sources) {
    $runId = "$RunPrefix`_$source"
    $argsList = @(
        "scripts\run_pilot_processing.py",
        "--run-id", $runId,
        "--all-documents",
        "--resume",
        "--sources", $source
    )

    if (-not $WithLlm) {
        $argsList += "--no-llm"
    }

    if ($NoHf) {
        $argsList += "--no-hf"
    } else {
        $argsList += @("--hf-model", $Model)
    }

    if ($MaxDocuments -gt 0) {
        $argsList += @("--max-documents", "$MaxDocuments")
    }

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $stdout = Join-Path $runnerLogDir "$runId-$stamp.out.log"
    $stderr = Join-Path $runnerLogDir "$runId-$stamp.err.log"

    Write-Host "Starting/resuming source '$source' as run '$runId'"
    Write-Host "Command: py $($argsList -join ' ')"
    $process = Start-Process -FilePath "py" `
        -ArgumentList $argsList `
        -WorkingDirectory $repo `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -WindowStyle Hidden `
        -PassThru

    $processes += [pscustomobject]@{
        Source = $source
        RunId = $runId
        ProcessId = $process.Id
        Stdout = $stdout
        Stderr = $stderr
        PipelineLog = "logs\variable_processing\$runId\run.log"
        Checkpoint = "data\processed\pilot_variables\$runId\checkpoint.json"
        IncrementalResults = "data\processed\pilot_variables\$runId\results_incremental.jsonl"
    }
}

$processes | Format-Table -AutoSize
