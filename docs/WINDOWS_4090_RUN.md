# 21 Windows RTX 4090 server run (CMD)

<!-- doc-nav:start -->
[00 总索引](README.md) · [01 待审决策](REVIEW_DECISIONS.md) · [上一页 20](GIT_WORKFLOW.md) · [下一页 22](REPOSITORY_LAYOUT.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [First checkout and environment](#section-1)
- [Formal run](#section-2)
<!-- doc-toc:end -->

Run these commands in **Windows Command Prompt (`cmd.exe`)**. Python 3.11, Git, and an NVIDIA driver must already be available. The example PyTorch wheel is **2.13.0 with CUDA 12.6**, listed by the [official PyTorch installation instructions](https://pytorch.org/get-started/previous-versions/). If the server driver cannot use that wheel, choose a supported CUDA build from the [PyTorch selector](https://pytorch.org/get-started/locally/) before proceeding. The CUDA check below must succeed.

<a id="section-1"></a>

## First checkout and environment

```bat
nvidia-smi
git clone https://github.com/powell4322/ATRS.git
cd ATRS
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cu126
.venv\Scripts\python.exe -m pip install -e ".[test]"
.venv\Scripts\python.exe -c "import torch; assert torch.cuda.is_available(), 'CUDA unavailable'; print(torch.__version__, torch.cuda.get_device_name(0))"
```

The ML-1M, Steam and Beauty text datasets are included in Git. Verify the ML-1M file before training:

```bat
dir data
certutil -hashfile data\ml-1m.txt SHA256
.venv\Scripts\python.exe -m atrs.cli preprocess --config configs/phase1/ml1m_sasrec_seed42.json
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\smoke.py
```

The expected data SHA-256 is `b725f3acb3986fe3130bffd1e77a74d182a1f51799567a236dbd60270f95b0a2`. `preprocess` stops on a mismatch. Smoke checks software execution only.

<a id="section-2"></a>

## Formal run

```bat
call scripts\run_matrix.cmd
```

The script checks CUDA and the data hash, trains clean, GRO and continued-clean teachers, and then runs DFME and BECOME against each. Four cells are the primary comparison; two are continued-clean controls. Detailed logs, checkpoints and query records remain under `runs\phase1\ml1m_sasrec_seed42\` and are ignored by Git. Once all six cells pass validation, the script writes descriptive analysis to `docs\RESULTS.md` and copies six result JSON files plus `manifest.json` into `result\phase1\ml1m_sasrec_seed42\`. Inspect both the analysis and raw outputs before publishing. This full run has **not** been executed locally.

To update an existing server checkout before a first run, open CMD in the repository root and use:

```bat
git pull --ff-only origin main
.venv\Scripts\python.exe -m pip install -e ".[test]"
```

The launcher starts a fresh matrix. Resume an interrupted teacher job with an individual CLI call and `--resume`. Restart interrupted attack cells from scratch. See the [experiment plan](EXPERIMENT_PLAN.md) for individual cell arguments. Keep the Git commit, configuration hash and data hash with the server outputs.

After reviewing the generated results, publish the research summary, six machine-readable result files and provenance manifest from the server checkout:

```bat
type docs\RESULTS.md
git status --short
git add docs\RESULTS.md result\phase1\ml1m_sasrec_seed42
git commit -m "Record ML-1M SASRec phase I results"
git push origin main
```

The pending `docs\RESULTS.md` in the initial checkout contains no measured numbers. Do not publish a completed-results commit until the full run and exporter succeed.
