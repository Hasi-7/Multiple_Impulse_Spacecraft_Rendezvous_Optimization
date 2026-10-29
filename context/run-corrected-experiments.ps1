param([Parameter(Mandatory=$true)][string]$RunTag)

$ErrorActionPreference = 'Stop'
$repoPath = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repoPath
$host.UI.RawUI.WindowTitle = 'Spacecraft rendezvous - fixed Sun sweep and validation'
$pythonPath = 'C:\Python314\python.exe'
$sweepPath = "outputs/weight_sweep_fixed_sun_$RunTag"
$validationPath = "outputs/weight_validation_fixed_sun_$RunTag"
$logPath = "outputs/corrected_experiments_$RunTag.log"
$statusPath = "outputs/corrected_experiments_$RunTag.status.json"

function Save-RunStatus([string]$Stage, [string]$Message) {
    @{ stage=$Stage; message=$Message; sweep=$sweepPath; validation=$validationPath;
       log=$logPath; terminal_pid=$PID; updated_utc=[DateTime]::UtcNow.ToString('o') } |
        ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
}

Start-Transcript -LiteralPath $logPath -NoClobber
try {
    Save-RunStatus 'unit_tests' 'Running the complete code-check suite'
    Write-Host 'STAGE 1: Complete unit tests' -ForegroundColor Cyan
    & $pythonPath -B -u -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed; production experiments were not started.' }

    Save-RunStatus 'sweep' 'Running 1000 coarse combinations followed by refinement'
    Write-Host "STAGE 2: Full corrected-model weight sweep -> $sweepPath" -ForegroundColor Cyan
    & $pythonPath -B -u weight_sweep.py --output $sweepPath --initial-states-from 'outputs/weight_sweep_20261027_200627_547397/configuration.json' | Out-Default
    if ($LASTEXITCODE -ne 0) { throw 'Weight sweep failed.' }
    $summary = Get-Content -LiteralPath "$sweepPath/summary.json" -Raw | ConvertFrom-Json
    if ($summary.stop_reason -ne 'completed' -or $summary.completed_stages -notcontains 'refined') {
        throw 'Sweep is incomplete; validation will not start.'
    }

    Save-RunStatus 'validation' 'Reoptimizing four selected weight candidates on nine scenarios'
    Write-Host "STAGE 3: All 36 powered validation trials and nine coast controls -> $validationPath" -ForegroundColor Cyan
    & $pythonPath -B -u validate_sweep_weights.py --source $sweepPath --output $validationPath | Out-Default
    if ($LASTEXITCODE -ne 0) { throw 'Validation failed.' }
    $results = Get-Content -LiteralPath "$validationPath/results.json" -Raw | ConvertFrom-Json
    $report = Get-Content -LiteralPath "$validationPath/summary.txt" -Raw
    if ($results.trials.Count -ne 36 -or @($results.coasts.PSObject.Properties).Count -ne 9 -or $report -notmatch 'Complete: True') {
        throw 'Validation did not save the expected complete batch.'
    }
    Save-RunStatus 'completed' 'Sweep and 36 validation trials finished; inspect individual statuses and report'
    Write-Host "ALL EXPERIMENTS FINISHED. Report: $validationPath/summary.txt" -ForegroundColor Green
} catch {
    Save-RunStatus 'failed' $_.Exception.Message
    Write-Host $_.Exception.Message -ForegroundColor Red
} finally {
    Stop-Transcript
}
