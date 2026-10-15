# Implementation status (2026-10-15)

| Component | Current status |
|---|---|
| ML-1M text validation and chronological split | Implemented and checked on the supplied file. SHA-256 and counts recorded. |
| Shared causal SASRec and clean teacher loop | Implemented, source-structure checked, forward/backward smoke passed. Full convergence and paper utility **not measured**. |
| GRO on SASRec | Eq. 4-6 swap workflow and one optimization step implemented and smoke-tested. BERT4Rec-native reproduction and official-code parity remain open. |
| Ranking-only oracle and request ledger | Implemented; deterministic unit tests cover duplicate prefixes, batching, budget exhaustion and ID-only output. |
| DFME | Autoregressive generation and rank/negative hinge implemented; minimal extraction smoke passed. Full source-result parity open. |
| BECOME | Dynamic phase selection, rank/frequency sampler and weighted objective implemented; minimal extraction smoke passed. Paper/source discrepancies documented. |
| Sim4Rec | CSG penalties, GRU pretraining, terminal reward policy update, memory bank, listwise loss implemented; minimal extraction smoke passed. Paper-derived, no official code equivalence. |
| Evaluation | Unified full-ranking plus deterministic sampled 100-negative mode implemented and tested. Original-paper metric parity open. |
| Checkpoints, resume, logs | Teacher model/optimizer/local-student checkpointing, teacher resume, JSONL logs, compressed labelled-query export and result JSON implemented. Mid-attack resume and a CLI for controlled query-dataset reuse remain incomplete. |
| Formal six-cell ML-1M/SASRec run | **Not executed. No research metrics available.** Current host has CPU-only PyTorch and no accessible NVIDIA GPU. |

## Executed checks

```powershell
& .venv\Scripts\python.exe -m compileall -q src scripts tests
& .venv\Scripts\python.exe -m pytest -q
& .venv\Scripts\python.exe scripts\smoke.py
& .venv\Scripts\python.exe -m atrs.cli preprocess --config experiments/ml1m_sasrec.json
```

Five deterministic unit tests passed, as did the smoke script covering one teacher forward/backward, API request, DFME/BECOME/Sim4Rec minimal generation and distillation, GRO update, evaluation, and checkpoint save/load. These checks establish software execution, not empirical defense effectiveness.

**Formal experiment readiness:** the six-cell launcher and result schema exist, but quantitative claims are not ready. Before treating results as a paper-faithful benchmark, resolve the deviations in `KNOWN_DEVIATIONS.md`, run converged teachers and all six attacks on suitable compute, repeat with several seeds, and inspect actual query counts plus the continued-clean control.
