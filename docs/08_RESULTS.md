# 08 实验结果与分析

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 07](07_PROGRESS.md) · [下一页 09](09_IMPLEMENTATION_AND_TBD.md)

**本页目录**

- [已取得的训练快照](#section-1)
- [完整防御结果状态](#section-2)
- [结果发布与分析规则](#section-3)

<a id="section-1"></a>

## 已取得的训练快照

下表来自2026-11-21上传的 ml1m_sasrec_seed42.zip 中真实 GPU 训练日志与最佳 checkpoint。它是 **Full Ranking / valid 的教师效用**，用于早停和内部进度分析，不是 test 结果，不是完整提取或防御收益。

| Target | 最佳 epoch | 最后 epoch | valid Recall@10 | valid NDCG@10 |
| --- | ---: | ---: | ---: | ---: |
| Clean | 319 | 349 | 0.136589 | 0.068588 |
| GRO | 144（追加） | 174（追加） | 0.137086 | 0.063756 |

同一 seed 的最佳验证 checkpoint 相比，Recall 差值为+0.000497，NDCG 差值为−0.004832，后者相对变化约−7.04%。这是当前 SASRec 迁移配置的一次验证集观察，不能据此宣称 GRO 普遍损害效用或证明新方法有效。

GRO × Random 仅记录到77/1000轮，最后 loss=0.927387、累计119735步，没有 Student checkpoint 或最终结果 JSON；不能将这段 loss 变成正式代理指标。DFME/BECOME 结果在快照中缺失。全部来源和中间数字见 [快照摘要](../result/snapshots/ml1m_sasrec_seed42_20261121.json)，训练成本见 [07](07_PROGRESS.md)。

<a id="section-2"></a>

## 完整防御结果状态

当前没有完成的外部提取 cell。下一完整任务为 seed42 的 DFME × None/GRO 配对，Ours 机制尚待确定。主表仍为五项 test 指标，Agreement 相对原始 clean Target。

| Seed | Attack | Defense | Target Recall@10 | Target NDCG@10 | Surrogate Recall@10 | Surrogate NDCG@10 | Agreement@10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | DFME | None | pending | pending | pending | pending | pending |
| 42 | DFME | GRO | pending | pending | pending | pending | pending |

Random 为未完成快照，BECOME/Ours 和多种子为后续任务。clean 教师已完成，None 条件的外部提取仍需单独运行。

<a id="section-3"></a>

## 结果发布与分析规则

完整 cell 的 JSON、配置与 manifest 审阅后可直接进入 Git，不需要等整个主矩阵或多种子齐全。本次未完成快照单独放在 result/snapshots，不能送入正式导出器冒充已完成 cell。checkpoint、原始查询和大日志保留在 runs，本地持有完整 ZIP；Git 不保存权重。

导出器核对同一任务的配置、数据、共同 clean parent 与 Agreement 参照。单种子可发布真实结果，后续若完成三种子再汇总均值和样本标准差。

先检查教师效用、None 提取程度和同攻击配对差值，再审查实际预算与训练步数。训练 loss 不等于推荐指标，valid 与 test 不混表，当前快照不支持防御收益或跨种子结论。正式导出后本页将由结果程序更新，原快照仍保留在 JSON 与07进度页。
