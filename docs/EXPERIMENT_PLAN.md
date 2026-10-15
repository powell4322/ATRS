# Experiment plan

## Order

1. Clone or update the repository on the CUDA server. The three text datasets are tracked in Git. `preprocess` checks the ML-1M SHA-256 against the frozen configuration and prints split metadata.
2. Run deterministic tests and the tiny smoke script. Do not report smoke metrics as research results.
3. Train clean SASRec to validation convergence; GRO and continued-clean both start from its best checkpoint and use the same fine-tuning epoch allowance.
4. Freeze each teacher and run DFME and BECOME independently. Use fresh students; never import the GRO local student into attacks.
5. Inspect utility retention, HR/NDCG, Agr@1/Agr@10, actual oracle requests, generated sequences and retained samples. Compare GRO with both clean and continued-clean teachers.
6. Repeat at multiple seeds only after one complete matrix passes plausibility checks. Then move to Steam/Beauty, and finally BERT4Rec-native GRO verification.

## Server commands

For the Windows RTX 4090 server, use the complete [CMD run guide](WINDOWS_4090_RUN.md). It includes `git clone`, CUDA PyTorch installation, data verification, the `scripts\run_matrix.cmd` matrix command and result publication into `docs/`.

For a Linux CUDA server, use:

```bash
python -m venv .venv
source .venv/bin/activate
# Install a PyTorch build compatible with the server CUDA environment first.
pip install -e ".[test]"
python -m pytest -q
python scripts/smoke.py
bash scripts/run_matrix.sh
```

Both launchers check that PyTorch can use CUDA before training. They execute three teacher jobs and six extraction jobs: four primary comparisons plus two continued-clean controls. On Linux, `PYTHON_BIN`, `CONFIG`, and `DEVICE` can override launcher defaults. Teacher training supports `--resume`; attack runs restart after interruption. Do not run the launcher twice against the same `run_root` without intending to overwrite attack outputs. Run individual cells with `python -m atrs.cli train-teacher --defense none|gro|continued-clean` or `python -m atrs.cli run-attack --defense none|gro|continued-clean --attack dfme|become`, replacing the choice notation with one value. Add `--config experiments/ml1m_sasrec.json --device cuda` to each command.

## Result table to populate after real runs

| Defense | Attack | Teacher HR@10 | Teacher NDCG@10 | Student HR@10 | Student NDCG@10 | Agr@1 | Agr@10 | Actual oracle requests | Seed |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| None | DFME | pending | pending | pending | pending | pending | pending | pending | 42 |
| None | BECOME | pending | pending | pending | pending | pending | pending | pending | 42 |
| GRO | DFME | pending | pending | pending | pending | pending | pending | pending | 42 |
| GRO | BECOME | pending | pending | pending | pending | pending | pending | pending | 42 |
| Continued-clean control | DFME | pending | pending | pending | pending | pending | pending | pending | 42 |
| Continued-clean control | BECOME | pending | pending | pending | pending | pending | pending | pending | 42 |

The table uses **full-ranking** metrics only. Sampled results live in separate JSON fields. Each row's checkpoint, configuration, and dataset hashes are in the machine-readable JSON result. See [related work](RELATED_WORK.md) for omitted methods.
