# ATRS Phase I

SASRec-first benchmark for DFME/BECOME model extraction and GRO defense. The checked-in code is independently implemented from the papers; private datasets and PDFs stay under `data/` and `paper/` and are ignored by Git.

## Scope

- ML-1M chronological leave-one-out; clean and GRO-fine-tuned SASRec teachers.
- Ranking-only Top-100 oracle with actual prefix-request accounting.
- DFME and BECOME as separate attack modules with separate query generation and losses.
- Full-ranking unified evaluation plus 100-negative sampled evaluation.

The scope of omitted methods is documented in [related work](docs/RELATED_WORK.md).

## Local software checks (PowerShell)

```powershell
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -e ".[test]"
& .venv\Scripts\python.exe -m pytest -q
& .venv\Scripts\python.exe scripts\smoke.py
& .venv\Scripts\python.exe -m atrs.cli preprocess --config experiments/ml1m_sasrec.json
```

## Formal matrix on the Windows 4090 server

The configuration in `experiments/ml1m_sasrec.json` caps every attack at 20,000 **actual oracle prefix requests** and preserves method-specific sequence generation. It is an integration comparison, not any paper's original budget. The CLI saves actual requests and checkpoints for every run. Formal training is intended for the user's CUDA server; local checks do not generate research results. Copy the ignored `data/ml-1m.txt` to the server unchanged. `preprocess` rejects a file whose SHA-256 differs from the frozen configuration.

Follow the [Windows RTX 4090 guide](docs/WINDOWS_4090_RUN.md) for the full `git clone`/`git pull`, CUDA PyTorch installation, data transfer, verification and run commands. Once the environment and data are ready, run:

```powershell
$PythonExe = (Resolve-Path .\.venv\Scripts\python.exe).Path
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_matrix.ps1 -Python $PythonExe -Device cuda
```

The launcher runs clean, GRO, and continued-clean teachers. DFME and BECOME produce four primary cells plus two continued-clean control cells. Teacher training supports `--resume`; attack runs restart after interruption.

## Linux CUDA alternative

```bash
python -m venv .venv
source .venv/bin/activate
# Install a PyTorch build compatible with the server CUDA environment first.
pip install -e ".[test]"
python -m pytest -q
python scripts/smoke.py
bash scripts/run_matrix.sh
```

To run a single cell, use `python -m atrs.cli train-teacher --defense none|gro|continued-clean` or `python -m atrs.cli run-attack --defense none|gro|continued-clean --attack dfme|become` with `--config` and `--device cuda`.

Read [the reproduction protocol](docs/REPRODUCTION_PROTOCOL.md), [fairness decisions](docs/BASELINE_FAIRNESS.md), and [implementation status](docs/IMPLEMENTATION_STATUS.md) before interpreting outputs. Smoke-test numbers are never research results.
