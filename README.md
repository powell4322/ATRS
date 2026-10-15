# ATRS Phase I

SASRec-first benchmark for model extraction attacks and GRO defense. The checked-in code is independently implemented from the four papers; private datasets and PDFs stay under `data/` and `paper/` and are ignored by Git.

## Scope

- ML-1M chronological leave-one-out; clean and GRO-fine-tuned SASRec teachers.
- Ranking-only Top-100 oracle with actual prefix-request accounting.
- DFME, BECOME, and Sim4Rec as separate attack modules with separate losses.
- Full-ranking unified evaluation plus 100-negative sampled evaluation.

Sim4Rec is an **extended comparator**, not the source repository for the benchmark. Its two evaluated backbone families still include the SASRec-to-SASRec case needed here. Its published source was not located, so the implementation is paper-derived and has documented unresolved choices.

## Install and verify (PowerShell)

```powershell
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -e ".[test]"
& .venv\Scripts\python.exe -m pytest -q
& .venv\Scripts\python.exe scripts\smoke.py
& .venv\Scripts\python.exe -m atrs.cli preprocess --config experiments/ml1m_sasrec.json
```

## Formal matrix

The configuration in `experiments/ml1m_sasrec.json` caps every attack at 20,000 **actual oracle prefix requests** and preserves method-specific sequence generation. It is an integration comparison, not any paper's original budget. The CLI saves actual requests and checkpoints for every run. Use a CUDA machine for the long runs.

```powershell
& scripts\run_matrix.ps1 -Python .venv\Scripts\python.exe -Device cuda
```

Run individual cells with `python -m atrs.cli train-teacher --defense none|gro` and `python -m atrs.cli run-attack --defense none|gro --attack dfme|become|sim4rec`; all take `--config` and `--device`.

Read [the reproduction protocol](docs/REPRODUCTION_PROTOCOL.md), [fairness decisions](docs/BASELINE_FAIRNESS.md), and [implementation status](docs/IMPLEMENTATION_STATUS.md) before interpreting outputs. Smoke-test numbers are never research results.
