param(
    [string]$RunPrefix = "full_parallel_gliner25_multi_no_llm",
    [string[]]$Sources = @("media_cloud", "gdelt", "bluesky"),
    [string]$Model = "fastino/gliner2.5-multi-v1",
    [int]$MaxWorkers = 6,
    [switch]$WithLlm,
    [switch]$NoHf,
    [string[]]$SkipExistingRunGlob = @("full_gliner25_multi_no_llm"),
    [switch]$NoPrepareShards,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$active = Get-CimInstance Win32_Process |
    Where-Object {
        ($_.Name -match 'python|py.exe') -and
        ($_.CommandLine -match 'run_pilot_processing.py')
    }

if ($active -and -not $Force) {
    Write-Host "Prediction process already alive. Not starting new workers."
    $active | Select-Object ProcessId,Name,CreationDate,CommandLine | Format-Table -AutoSize
    py scripts\report_processing_status.py --write
    exit 0
}

$logicalProcessors = [Environment]::ProcessorCount
if ($MaxWorkers -le 0) {
    $MaxWorkers = [Math]::Max(1, [Math]::Min(6, [int][Math]::Floor($logicalProcessors / 4)))
}

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
if (-not $Sources -or $Sources.Count -eq 0) {
    throw "No sources selected."
}

$workerCount = [Math]::Max(1, $MaxWorkers)
$baseShardCount = [Math]::Floor($workerCount / $Sources.Count)
$extraWorkers = $workerCount % $Sources.Count
$runnerLogDir = Join-Path $repo "logs\variable_processing\runner"
New-Item -ItemType Directory -Force -Path $runnerLogDir | Out-Null

if (-not $NoPrepareShards) {
    $prepareArgs = @(
        "scripts\prepare_processing_shards.py",
        "--run-prefix", $RunPrefix,
        "--max-workers", "$workerCount",
        "--sources"
    )
    $prepareArgs += $Sources
    foreach ($glob in $SkipExistingRunGlob) {
        if ($glob) {
            $prepareArgs += @("--skip-existing-run-glob", $glob)
        }
    }
    $prepareArgs += @("--skip-existing-run-glob", "$RunPrefix`_*")
    Write-Host "Preparing input shards with one full parquet read..."
    py @prepareArgs | Out-Host
}

$processes = @()
for ($sourceIndex = 0; $sourceIndex -lt $Sources.Count; $sourceIndex++) {
    $source = $Sources[$sourceIndex]
    $shardCount = [Math]::Max(1, $baseShardCount)
    if ($sourceIndex -lt $extraWorkers) {
        $shardCount += 1
    }

    for ($shardIndex = 0; $shardIndex -lt $shardCount; $shardIndex++) {
        $runId = "$RunPrefix`_$source`_s$shardIndex`of$shardCount"
        $preparedShard = Join-Path $repo "data\processed\pilot_variables\_prepared_shards\$RunPrefix\$runId.parquet"
        $argsList = @(
            "scripts\run_pilot_processing.py",
            "--run-id", $runId,
            "--all-documents",
            "--resume",
            "--sources", $source
        )

        if (Test-Path $preparedShard) {
            $argsList += @("--input-parquet", $preparedShard)
        } else {
            $argsList += @("--shard-index", "$shardIndex", "--shard-count", "$shardCount")
        }

        foreach ($glob in $SkipExistingRunGlob) {
            if ($glob) {
                $argsList += @("--skip-existing-run-glob", $glob)
            }
        }
        $argsList += @("--skip-existing-run-glob", "$RunPrefix`_$source`_s*of*")

        if (-not $WithLlm) {
            $argsList += "--no-llm"
        }

        if ($NoHf) {
            $argsList += "--no-hf"
        } else {
            $argsList += @("--hf-model", $Model)
        }

        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $stdout = Join-Path $runnerLogDir "$runId-$stamp.out.log"
        $stderr = Join-Path $runnerLogDir "$runId-$stamp.err.log"

        Write-Host "Starting source '$source' shard $shardIndex/$shardCount as run '$runId'"
        $process = Start-Process -FilePath "py" `
            -ArgumentList $argsList `
            -WorkingDirectory $repo `
            -RedirectStandardOutput $stdout `
            -RedirectStandardError $stderr `
            -WindowStyle Hidden `
            -PassThru

        $processes += [pscustomobject]@{
            Source = $source
            Shard = "$shardIndex/$shardCount"
            RunId = $runId
            ProcessId = $process.Id
            Stdout = $stdout
            Stderr = $stderr
            Checkpoint = "data\processed\pilot_variables\$runId\checkpoint.json"
            IncrementalResults = "data\processed\pilot_variables\$runId\results_incremental.jsonl"
        }
    }
}

$processes | Format-Table -AutoSize
py scripts\report_processing_status.py --write
