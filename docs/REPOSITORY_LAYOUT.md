# Repository layout and result lifecycle

| Path | Purpose | Git policy |
|---|---|---|
| `data/` | Original SASRec-format ML-1M, Steam and Beauty input texts | Track byte-for-byte; do not edit after hashing. |
| `configs/phase1/` | Frozen experiment JSON, including seed, API budget, data hash and run root | Track; changing a config changes its SHA-256. |
| `src/atrs/` | Models, attacks, defense, evaluation and CLI | Track. |
| `scripts/` | CMD, PowerShell and Bash launchers; validated result exporter | Track. |
| `runs/phase1/<experiment>/logs/` | Per-epoch JSONL training logs | Ignore; keep on the compute server. |
| `runs/phase1/<experiment>/checkpoints/` | Teacher and student model/optimizer states | Ignore; keep on the compute server. |
| `runs/phase1/<experiment>/queries/` | Labelled query records for auditing | Ignore; keep on the compute server. |
| `runs/phase1/<experiment>/results/` | Direct JSON outputs from each attack cell | Ignore; exporter validates these before publication. |
| `result/phase1/<experiment>/` | Six validated metric JSON files and a provenance manifest | Track after a complete run and review. |
| `docs/` | Protocol, source mapping, deviations, server commands, descriptive result tables and scientific interpretation | Track. |
| `paper/` | Local paper PDFs | Ignore. |

`runs/` is the working record of an experiment. `result/` is the compact, versioned numerical evidence. `docs/RESULTS.md` derives tables and single-seed differences from that evidence. The exporter refuses to replace the pending analysis if any expected cell is missing or has inconsistent data, configuration, Git commit, teacher identity, ranking protocol or oracle budget.

The Phase I identifier is `ml1m_sasrec_seed42`. Later seeds and datasets should receive new config files, run directories and result directories. Do not overwrite an earlier completed experiment to represent a different seed or protocol.
