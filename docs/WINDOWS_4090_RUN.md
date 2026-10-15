# Windows RTX 4090 server run

Run these commands in PowerShell. Python 3.11, Git, and an NVIDIA driver must already be available. The example PyTorch wheel is **2.13.0 with CUDA 12.6**, listed by the [official PyTorch installation instructions](https://pytorch.org/get-started/previous-versions/). If the server driver cannot use that wheel, choose a supported CUDA build from the [PyTorch selector](https://pytorch.org/get-started/locally/) before proceeding. The CUDA check below must succeed.

## First checkout and environment

```powershell
nvidia-smi
git clone https://github.com/powell4322/ATRS.git
Set-Location .\ATRS
py -3.11 -m venv .venv
$PythonExe = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cu126
& $PythonExe -m pip install -e ".[test]"
& $PythonExe -c "import torch; assert torch.cuda.is_available(), 'CUDA unavailable'; print(torch.__version__, torch.cuda.get_device_name(0))"
```

The dataset is ignored by Git. Transfer the exact local `ml-1m.txt` to the Windows server first, then replace `C:\TRANSFER\ml-1m.txt` in the next block with its server-side path. Copying within the server must preserve the original file bytes.

```powershell
New-Item -ItemType Directory -Force .\data | Out-Null
Copy-Item -LiteralPath 'C:\TRANSFER\ml-1m.txt' -Destination .\data\ml-1m.txt
(Get-FileHash .\data\ml-1m.txt -Algorithm SHA256).Hash.ToLowerInvariant()
& $PythonExe -m atrs.cli preprocess --config experiments/ml1m_sasrec.json
& $PythonExe -m pytest -q
& $PythonExe scripts\smoke.py
```

The expected data SHA-256 is `b725f3acb3986fe3130bffd1e77a74d182a1f51799567a236dbd60270f95b0a2`. `preprocess` stops on a mismatch. Smoke checks software execution only.

## Formal run

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_matrix.ps1 -Python $PythonExe -Device cuda
```

The script checks CUDA and the data hash, trains clean, GRO and continued-clean teachers, and then runs DFME and BECOME against each. Four cells are the primary comparison; two are continued-clean controls. Its outputs are under `runs\ml1m_sasrec_seed42\` and are ignored by Git. In particular, inspect `results\*.json`, `logs\*.jsonl`, `checkpoints\*.pt`, and `queries\*.jsonl.gz` before making research claims. This full run has **not** been executed locally.

To update an existing server checkout before a first run, open PowerShell in the repository root and use:

```powershell
git pull --ff-only origin main
$PythonExe = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $PythonExe -m pip install -e ".[test]"
```

The launcher starts attack cells from scratch and can overwrite result files if run again. Teacher jobs support the CLI's `--resume` flag when invoked individually; see [experiment plan](EXPERIMENT_PLAN.md). Keep the Git commit, configuration hash and data hash recorded in each run's result files with the server outputs.
