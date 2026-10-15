# Implementation status (2026-10-15)

| Component | Current status |
|---|---|
| ML-1M text validation and chronological split | Implemented and checked on the supplied file. SHA-256 and counts recorded. |
| Shared causal SASRec and clean teacher loop | Implemented, source-structure checked, forward/backward smoke passed. Full convergence and paper utility **not measured**. |
| GRO on SASRec | Eq. 4-6 swap workflow and one optimization step implemented and smoke-tested. BERT4Rec-native reproduction and official-code parity remain open. |
| Ranking-only oracle and request ledger | Implemented; deterministic unit tests cover duplicate prefixes, batching, budget exhaustion and ID-only output. |
| DFME | Autoregressive generation and rank/negative hinge implemented; minimal extraction smoke passed. Full source-result parity open. |
| BECOME | Dynamic phase selection, rank/frequency sampler and weighted objective implemented; minimal extraction smoke passed. Paper/source discrepancies documented. |
| Evaluation | Unified full-ranking plus deterministic sampled 100-negative mode implemented and tested. Original-paper metric parity open. |
| Checkpoints, resume, logs and result publication | Teacher model/optimizer/local-student checkpointing, teacher resume, JSONL logs and compressed labelled-query export implemented. A complete six-cell matrix is validated into versioned `result/` JSON and `docs/RESULTS.md` analysis. Mid-attack resume and a CLI for controlled query-dataset reuse remain incomplete. |
| Formal ML-1M/SASRec run | **Not executed. No research metrics available.** Local work is for research and code; the user will run the formal matrix on a CUDA server. The launchers cover four primary and two continued-clean control cells. |

## Executed checks

```powershell
& .venv\Scripts\python.exe -m compileall -q src scripts tests
& .venv\Scripts\python.exe -m pytest -q
& .venv\Scripts\python.exe scripts\smoke.py
& .venv\Scripts\python.exe -m atrs.cli preprocess --config configs/phase1/ml1m_sasrec_seed42.json
```

Five deterministic unit tests passed, as did the smoke script covering one teacher forward/backward, API request, DFME/BECOME minimal generation and distillation, GRO update, evaluation, and checkpoint save/load. These checks establish software execution, not empirical defense effectiveness.

The supplied ML-1M file also passed a single real-data SASRec forward/backward check at the configured 400-token length (2 windows from 7,068 training windows, finite loss and embedding gradients). This was one batch, not an epoch or a utility measurement.

**Formal experiment readiness:** the server launcher and result schema exist, but quantitative claims are not ready. Before treating results as a paper-faithful benchmark, resolve the deviations in `KNOWN_DEVIATIONS.md`, run converged teachers and all six cells on the server, repeat with several seeds, and inspect actual query counts plus the continued-clean control.
