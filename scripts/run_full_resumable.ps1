param(
    [string]$RunId = "full_gliner25_multi_no_llm",
    [string]$Model = "fastino/gliner2.5-multi-v1",
    [switch]$WithLlm,
    [switch]$NoHf,
    [int]$MaxDocuments = 0
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$argsList = @(
    "scripts\run_pilot_processing.py",
    "--run-id", $RunId,
    "--all-documents",
    "--resume"
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

Write-Host "Starting/resuming run: $RunId"
Write-Host "Command: py $($argsList -join ' ')"
py @argsList
