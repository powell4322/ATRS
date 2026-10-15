param(
  [string]$Python = ".venv\Scripts\python.exe",
  [string]$Config = "experiments/ml1m_sasrec.json",
  [string]$Device = "cuda"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
& $Python -m atrs.cli preprocess --config $Config
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m atrs.cli train-teacher --config $Config --defense none --device $Device
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m atrs.cli train-teacher --config $Config --defense gro --device $Device
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m atrs.cli train-teacher --config $Config --defense continued-clean --device $Device
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
foreach ($defense in @("none", "gro", "continued-clean")) {
  foreach ($attack in @("dfme", "become")) {
    & $Python -m atrs.cli run-attack --config $Config --defense $defense --attack $attack --device $Device
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
}
