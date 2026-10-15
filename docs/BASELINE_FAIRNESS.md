# Baseline fairness and attack selection

## Main comparison

The primary question is the effect of the **same GRO training procedure** on each extraction attack, relative to a clean teacher. All four cells use one data split, one SASRec implementation, ranking-only Top-100 access, equal 20k request *caps*, the same seed and full-ranking test rows. The external student is freshly initialized per cell. Attack-specific generation and loss are preserved.

| Attack | Initial generation and training | Distillation objective | Configured prefix requests before exact-prefix caching |
|---|---|---|---:|
| DFME | 100 autoregressive sequences × 200 prefixes | adjacent ranking + negative hinge | 20,000 |
| BECOME | 166 sequences, 40 initial prefixes, four feedback phases selecting 83 sequences each | weighted adjacent ranking + negative hinge | 19,920 |

These are **unified engineering settings**, not paper-native budgets. Cache collisions can reduce actual request counts. Each result records actual requests, unique prefixes, batched forwards, generated sequences, and retained samples. Report extraction utility and agreement against actual counts, and do not claim strict equal-budget superiority if actual counts differ materially. A query-matched performance curve would be stronger than one endpoint; this is still pending.

## Utility and budget controls

Report teacher HR@10/NDCG@10 before interpreting defense outcomes. GRO fine-tunes a converged clean checkpoint and receives extra updates, so also run the available `continued-clean` control for the same number of extra epochs before attributing a difference solely to GRO. Never compare full-ranking scores with sampled-ranking scores in one table. Keep the raw query ledger and teacher/student checkpoint SHA-256 in exported results.

The GRO local student sees training prefixes only during teacher defense training. An external attacker uses a new model and queries the frozen teacher checkpoint. This separation prevents local-student reuse from overstating attack performance.
