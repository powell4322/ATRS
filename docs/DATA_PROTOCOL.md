# Data protocol

## Supplied ML-1M text

`data/ml-1m.txt` contains two positive integers per line: user ID, item ID. User blocks are contiguous and line order is the only available chronology. The parser rejects malformed, interleaved, nonpositive, or nondense item IDs and users with fewer than three actions. It never rewrites the source file.

Observed on 2026-10-15:

| Field | Value |
|---|---:|
| Users | 6,040 |
| Items | 3,416 |
| Interactions | 999,611 |
| Training interactions | 987,531 |
| Validation interactions | 6,040 |
| Test interactions | 6,040 |
| SHA-256 | `b725f3acb3986fe3130bffd1e77a74d182a1f51799567a236dbd60270f95b0a2` |

The paper tables list approximately 1,000,209 ML-1M interactions. This local SASRec-format file has 598 fewer lines and no ratings or timestamps, so original filtering and tie ordering cannot be reconstructed from it alone. Absolute paper metrics should not be treated as direct reproduction targets.

## Split and candidates

Per user, the final action is test, the preceding action is validation, and all earlier actions are teacher training. IDs stay in the original 1..N mapping for every model. Zero is only a padding index. Training examples use left padding, sliding windows, and one negative per non-padding position drawn outside that user's **training** items. Validation/test items do not enter teacher training or negative-sampling exclusions.

For unified full ranking, candidate items are all 1..N except items in the current history, with the target restored. For paper-style sampled ranking, 100 negatives are drawn with seed `seed + user_id` outside the full user sequence. This use of held-out interactions is isolated to offline evaluation and never exposed to attacks or training.

The CLI rejects a source file whose SHA-256 differs from `expected_data_sha256` in the formal configuration, then writes `runs/.../data_metadata.json` with the source checksum, split sizes, and schema. The original text files for ML-1M, Steam and Beauty are tracked in Git with byte-preserving attributes; a server `git clone` obtains them directly. Steam and Beauty are present for later stages but are not processed or run in Phase I.

| Later-stage file | Bytes | SHA-256 |
|---|---:|---|
| `data/Steam.txt` | 42,541,998 | `4df1f5feac169a522008956ba5a50fee4e9ce2c0c817cabfd463ac36df05f023` |
| `data/Beauty.txt` | 4,538,161 | `3cd3d56cee682f5118f22d0443d5d27116075c719ec83bfdfa3e45df33a95e12` |
