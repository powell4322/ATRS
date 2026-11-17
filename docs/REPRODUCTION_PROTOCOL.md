# 10 Phase I reproduction protocol

<!-- doc-nav:start -->
[00 总索引](README.md) · [01 待审决策](REVIEW_DECISIONS.md) · [上一页 09](research/scheme_c_feasibility.md) · [下一页 11](DATA_PROTOCOL.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [Research question and units](#section-1)
- [Two protocol layers](#section-2)
- [Dataset and teacher](#section-3)
- [API and budget](#section-4)
- [Unified evaluation](#section-5)
- [Reproducibility record](#section-6)
<!-- doc-toc:end -->

<a id="section-1"></a>

## Research question and units

Measure whether GRO changes a frozen SASRec teacher's extractability under DFME and BECOME, while preserving recommendation utility. The current code uses the same ML-1M text file, split, SASRec architecture, and evaluation inputs for every matrix cell. GRO on SASRec is an adaptation of the WSDM 2024 method, whose original experiments used BERT4Rec.

<a id="section-2"></a>

## Two protocol layers

**A. Paper-native verification.** Keep each implemented paper's generation mechanism, ranking loss, nominal generated-sequence budget, training schedule, and evaluation protocol. DFME/BECOME use sampled 100-negative recommendation evaluation; GRO uses full ranking. This repository has the relevant loss and evaluation primitives but has **not** completed quantitative paper-native reproduction. The supplied preprocessed `ml-1m.txt` differs from the rating totals in the papers and lacks original timestamps. No paper-native numbers are claimed.

**B. Unified defense comparison.** All cells use `configs/phase1/ml1m_sasrec_seed42.json` and a 20,000-actual-request cap. Clean and defended teachers start from the same architecture and clean checkpoint; the defended teacher is then fine-tuned with GRO. Each external attack uses a fresh SASRec student. The local GRO student is separate and is discarded after training. Every attack sees only ordered Top-100 item IDs, never scores or real user training histories. Method-specific losses and generators remain separate.

<a id="section-3"></a>

## Dataset and teacher

The `user item` text is assumed chronological within each user block. IDs are already dense 1..3416. The last two items become validation and test. All teacher training batches and negative sampling depend only on each user's training part. Checkpoint metadata records the raw text SHA-256. The clean teacher uses a 400-position, 64-dimensional, 2-head, 2-block causal SASRec with BCE. GRO starts from the clean validation best checkpoint and jointly optimizes teacher utility, local-student ranking, and swap loss. The `--defense continued-clean` control starts from the same checkpoint.

<a id="section-4"></a>

## API and budget

The attack API is `RankingOracle.predict_topk(prefixes)`. It returns lists of integer item IDs and leaves already-seen items eligible during attack generation, matching the DFME/BECOME source generator's direct Top-K sort. With caching on, `oracle_requests` counts unseen prefixes under the 20k cap. Each result also reports total submitted prefix rows, BECOME feedback rows and misses, batch forwards, generated sequences, retained distillation samples and actual optimizer steps. See the [protocol audit](audits/protocol_audit.md) for the accounting identities.

<a id="section-5"></a>

## Unified evaluation

One test row per user. The input is training history plus validation item, and the answer is the last item. Full ranking considers items 1..N, removes items already in the input history, then reintroduces the answer if it repeats. Both teacher and student receive the same candidate mask. HR@10 is one if the answer is in the top 10; NDCG@10 is reciprocal log rank. Agreement@1 is exact first-item match; Agreement@10 is the size of the top-10 set intersection divided by 10. Ties break by ascending item ID. Validation follows the same logic with training history and the penultimate item.

The sampled evaluation draws a deterministic 100 negative items per user outside the full user sequence, ranks these plus the answer, and is exported separately. It is not comparable numerically to full ranking.

<a id="section-6"></a>

## Reproducibility record

Result JSON includes dataset, backbone, seed, defense, attack, Git commit, data/configuration/checkpoint/query-dataset hashes, budget definition and counts, teacher and student metrics, and wall-clock duration. Method-retained queries and rankings are exported as deterministic gzip JSONL. Teacher logs use JSONL. Teacher checkpoints save model, optimizer, epoch, random states, and local GRO student states. `--resume` resumes teacher training from the latest checkpoint. Attack generation/resume after interruption is currently incomplete and is listed in implementation status.
