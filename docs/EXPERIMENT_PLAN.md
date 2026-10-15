# Experiment plan

## Order

1. Confirm the supplied ML-1M checksum and split metadata with `preprocess`.
2. Run deterministic tests and the tiny smoke script. Do not report smoke metrics.
3. Train clean SASRec to validation convergence; record best checkpoint, epoch and full-ranking validation utility.
4. Fine-tune GRO from that best checkpoint. Run `continued-clean` with the same extra-update allowance as a control.
5. Freeze each selected teacher and run DFME, BECOME, Sim4Rec independently. Use fresh students; never import the GRO local student into attacks.
6. Inspect results for utility retention, HR/NDCG, Agr@1/Agr@10, actual oracle requests, generated sequences and retained samples.
7. Repeat at multiple seeds only after one complete six-cell matrix passes plausibility checks. Then move to Steam/Beauty, and finally BERT4Rec-native GRO verification.

## Commands

```powershell
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -e ".[test]"
& .venv\Scripts\python.exe -m pytest -q
& .venv\Scripts\python.exe scripts\smoke.py
& .venv\Scripts\python.exe -m atrs.cli preprocess --config experiments/ml1m_sasrec.json
& .venv\Scripts\python.exe -m atrs.cli train-teacher --config experiments/ml1m_sasrec.json --defense none --device cuda
& .venv\Scripts\python.exe -m atrs.cli train-teacher --config experiments/ml1m_sasrec.json --defense gro --device cuda
& .venv\Scripts\python.exe -m atrs.cli train-teacher --config experiments/ml1m_sasrec.json --defense continued-clean --device cuda
& scripts\run_matrix.ps1 -Python .venv\Scripts\python.exe -Device cuda
```

`run_matrix.ps1` also trains teachers, so use either individual training commands followed by six `run-attack` commands or the matrix launcher once. Teacher training supports `--resume`; attack runs restart from the beginning. The launcher is intentionally not called by smoke tests.

## Result table to populate after real runs

| Defense | Attack | Teacher HR@10 | Teacher NDCG@10 | Student HR@10 | Student NDCG@10 | Agr@1 | Agr@10 | Actual oracle requests | Seed |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| None | DFME | pending | pending | pending | pending | pending | pending | pending | 42 |
| None | BECOME | pending | pending | pending | pending | pending | pending | pending | 42 |
| None | Sim4Rec | pending | pending | pending | pending | pending | pending | pending | 42 |
| GRO | DFME | pending | pending | pending | pending | pending | pending | pending | 42 |
| GRO | BECOME | pending | pending | pending | pending | pending | pending | pending | 42 |
| GRO | Sim4Rec | pending | pending | pending | pending | pending | pending | pending | 42 |

The table uses **full-ranking** metrics only. Sampled results live in separate JSON fields. Each row's checkpoint and dataset hashes are in the machine-readable JSON result.
