param(
  [string]$Python = ".venv\Scripts\python.exe",
  [string]$Config = "configs/phase1/ml1m_sasrec_seed42.json",
  [string]$Device = "cuda"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($Device -like "cuda*") {
  & $Python -c "import torch; assert torch.cuda.is_available(), 'CUDA is unavailable to PyTorch'; print(torch.__version__, torch.cuda.get_device_name(0))"
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
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
& $Python scripts\export_results.py --config $Config
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
