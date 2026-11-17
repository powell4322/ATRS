# 15 协议审计

<!-- doc-nav:start -->
[00 总索引](../README.md) · [01 待审决策](../REVIEW_DECISIONS.md) · [上一页 14](repository_audit.md) · [下一页 16](../IMPLEMENTATION_STATUS.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [固定数据和 API 邻域](#section-1)
- [B、M 和训练步数](#section-2)
- [对照与验收边界](#section-3)
<!-- doc-toc:end -->

<a id="section-1"></a>

## 固定数据和 API 邻域

- ML-1M 两列文本按用户内行序切分。6040 用户、3416 物品、999611 交互，987531 条 train 事件。验证用倒数第二项，测试用最后一项。本地 SHA-256 已与冻结配置相符。原始时间戳与论文预处理仍需来源证明。
- 攻击 API 返回 $K=100$ 个唯一正整数 ID，分数降序，平局以物品 ID 升序。原始顺序前缀用于缓存身份，SASRec 编码只取末尾 `max_len`。攻击生成允许历史重复。DFME 从列表成员均匀选取，BECOME 考虑排序与历史观察频次。
- 正常攻击通过单一 `RankingOracle`。真实 train、目标模型分数与参数均未传入生成和蒸馏。防御端 T2–T4 的参考窗口仅来自 train。T5 的两视图只存在于防御诊断，读出次数另计。
- 离线 full ranking 为同一 mask，排历史，若目标重复则恢复目标。Sampled 为固定 100 个全历史外负例，单独输出。单目标留一 HR@10 等于 Recall@10。Phase I Agreement 参照相应攻击的 teacher，T5 则统一参照 clean teacher。

<a id="section-2"></a>

## B、M 和训练步数

| 量 | 记录口径 |
| --- | --- |
| `requested_prefixes` | 所有成功提交的 prefix 行，含同批重复和已缓存的反馈 |
| `oracle_requests` | 默认缓存下的新前缀请求，Phase I 的 $B$。禁用缓存时每成功行收费 |
| `unique_queried_prefixes` | 全运行覆盖的不同原始前缀数 |
| `model_forward_calls` | 底层批前向次数，单独记录 |
| `cache_hits` | 已缓存或同批被合并的行数，默认有 `requested_prefixes = oracle_requests + cache_hits` |
| `feedback_prefixes` / `feedback_oracle_requests` | BECOME 反馈提交行数与其中新增收费数 |
| `generated_sequences` / `retained_samples` | 序列数 $M$ 与保留的蒸馏行数 |
| `training_steps` | 外部代理实际 optimizer step 次数 |

冻结配置的 DFME 发出 100×200=20,000 行，保留 19,900 行。BECOME 生成行上界 166×40+83×160=19,920，另有 4×166=664 行反馈。反馈通过同一 oracle，当前每阶段末端前缀已缓存，通常只增加逻辑请求行。两法上限同为 20,000，实测收费数仍可能不同。正式安全比较需报告达成预算与预算曲线。缓存使末端反馈免费是本统一协议的选择，改成按请求行收费需要重新分配 BECOME 生成预算。

<a id="section-3"></a>

## 对照与验收边界

- None 攻击、GRO、continued-clean 共用 validation 选中的 clean teacher 作为起点。两种追加训练逐个记录起点 hash。特定 defense 的两个攻击共用该 defense 的 best。
- 同一冻结配置比较四个主格加两个 continued-clean 格。每个外部 Student 独立于 GRO 内部 Student，相同种子和共同架构。不同教师的验证选择 epoch 和不同攻击的实际步数都应随数据报告。
- G0 的接口、数据、计数与 checkpoint 路径已在 CPU 验证。真实 CUDA checkpoint 接续、收敛 utility、GRO 的安全性和原论文绝对指标均待运行。证据记录见 [理论验证报告](../research/theory_validation_report.md)。
