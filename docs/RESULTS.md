# Phase I results: ML-1M / SASRec

**Status: pending formal CUDA-server run. No research metrics have been produced or uploaded.**

The server launcher runs clean, GRO and continued-clean teachers, followed by DFME and BECOME against each teacher. Once all six result JSON files exist, it invokes `scripts/export_results.py`. That exporter checks the six cell identities, common data/configuration/Git provenance, evaluation protocol, metric ranges and oracle budgets before replacing this analysis page and copying the machine-readable JSON files to `result/phase1/ml1m_sasrec_seed42/`.

Server commands, source-data hashes and result-publishing commands are in [WINDOWS_4090_RUN.md](WINDOWS_4090_RUN.md). The comparison and interpretation rules are in [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md) and [REPRODUCTION_PROTOCOL.md](REPRODUCTION_PROTOCOL.md).
