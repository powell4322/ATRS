# Versioned experiment results

This directory holds validated, machine-readable **measured results**. It contains no training checkpoints, query logs or manually typed scores.

After the Phase I Windows or Linux launcher completes all six cells, `scripts/export_results.py` copies the six validated result JSON files into `result/phase1/ml1m_sasrec_seed42/` and writes a `manifest.json` with Git, configuration, dataset and file hashes. The corresponding descriptive tables and interpretation belong in `docs/RESULTS.md`.

No formal GPU run has been completed yet, so this directory currently has no measured result JSON files.
