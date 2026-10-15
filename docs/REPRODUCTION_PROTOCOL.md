# Phase I reproduction protocol

## Research question and units

Measure whether GRO changes a frozen SASRec teacher's extractability under DFME and BECOME, while preserving recommendation utility. The current code uses the same ML-1M text file, split, SASRec architecture, and evaluation inputs for every matrix cell. GRO on SASRec is an adaptation of the WSDM 2024 method, whose original experiments used BERT4Rec.

## Two protocol layers

**A. Paper-native verification.** Keep each implemented paper's generation mechanism, ranking loss, nominal generated-sequence budget, training schedule, and evaluation protocol. DFME/BECOME use sampled 100-negative recommendation evaluation; GRO uses full ranking. This repository has the relevant loss and evaluation primitives but has **not** completed quantitative paper-native reproduction. The supplied preprocessed `ml-1m.txt` differs from the rating totals in the papers and lacks original timestamps. No paper-native numbers are claimed.

**B. Unified defense comparison.** All cells use `experiments/ml1m_sasrec.json` and a 20,000-actual-request cap. Clean and defended teachers start from the same architecture and clean checkpoint; the defended teacher is then fine-tuned with GRO. Each external attack uses a fresh SASRec student. The local GRO student is separate and is discarded after training. Every attack sees only ordered Top-100 item IDs, never scores or real user training histories. Method-specific losses and generators remain separate.

## Dataset and teacher

The `user item` text is assumed chronological within each user block. IDs are already dense 1..3416. The last two items become validation and test. All teacher training batches and negative sampling depend only on each user's training part. Checkpoint metadata records the raw text SHA-256. Clean teacher uses source-aligned 400-position, 64-dimensional, 2-head, 2-block causal SASRec with BCE. GRO starts from the selected clean checkpoint and jointly optimizes teacher utility, local-student ranking, and swap loss. A continued-clean control is supported by `--defense continued-clean`.

## API and budget

The attack API is `RankingOracle.predict_topk(prefixes)`. It returns only lists of integer item IDs. It leaves already-seen items eligible during attack generation, matching the DFME/BECOME source generator's direct Top-K sort. The API deduplicates exact prefixes when caching is on. `oracle_requests` counts unseen prefixes; `model_forward_calls` counts batches; generated sequences and retained distillation samples are reported separately. A 20k cap is a hard maximum. The achieved count must be read from each result file; sequence counts are never treated as oracle counts.

## Unified evaluation

One test row per user. The input is training history plus validation item, and the answer is the last item. Full ranking considers items 1..N, removes items already in the input history, then reintroduces the answer if it repeats. Both teacher and student receive the same candidate mask. HR@10 is one if the answer is in the top 10; NDCG@10 is reciprocal log rank. Agreement@1 is exact first-item match; Agreement@10 is the size of the top-10 set intersection divided by 10. Ties break by ascending item ID. Validation follows the same logic with training history and the penultimate item.

The sampled evaluation draws a deterministic 100 negative items per user outside the full user sequence, ranks these plus the answer, and is exported separately. It is not comparable numerically to full ranking.

## Reproducibility record

Result JSON includes dataset, backbone, seed, defense, attack, Git commit, data/configuration/checkpoint/query-dataset hashes, budget definition and counts, teacher and student metrics, and wall-clock duration. Method-retained queries and rankings are exported as deterministic gzip JSONL. Teacher logs use JSONL. Teacher checkpoints save model, optimizer, epoch, random states, and local GRO student states. `--resume` resumes teacher training from the latest checkpoint. Attack generation/resume after interruption is currently incomplete and is listed in implementation status.
