# Versioned experiment results

Validated metrics, resolved configurations and per-seed manifests belong under `result/<profile>/<experiment>/`. The current profile is `gro_first`, with seed 42 only. The corresponding analysis is generated into [08 results](../docs/08_RESULTS.md). Additional seeds are deferred until the method is ready; complete three-seed groups can still be summarized later.

Full checkpoints, query datasets and detailed logs remain in the cloud `runs/` directory. Reviewed mechanism diagnostics may be archived under `result/research/` with explicit diagnostic metadata.

No formal GPU results are available yet. See [06 commands](../docs/06_COMMANDS.md) for setup, execution and local checks, and [10 repository lifecycle](../docs/10_REPOSITORY_AND_SYNC.md) for artifact roles. Legacy phase1 configurations and their archival behavior remain available.
