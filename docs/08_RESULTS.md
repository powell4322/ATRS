# 08 实验结果与分析

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 07](07_PROGRESS.md) · [下一页 09](09_IMPLEMENTATION_AND_TBD.md)

**本页目录**

- [正式结果状态](#section-1)
- [结果发布与分析规则](#section-2)

<a id="section-1"></a>

## 正式结果状态

当前为 pending。首批 ML-1M + SASRec、三种子、1k 名义序列的 None/GRO 尚未在 GPU 上执行。Ours 的方法和实现为 TBD。

正式报告展示五个主指标，主 Agreement 对照原始 clean Target。论文历史数值和本地软件验证只用于核查资料和实现。

| Seed | Attack | Defense | Target Recall@10 | Target NDCG@10 | Surrogate Recall@10 | Surrogate NDCG@10 | Agreement@10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 42/43/44 | Random/DFME/BECOME | None/GRO | pending | pending | pending | pending | pending |
| 42/43/44 | Random/DFME/BECOME | Ours | TBD | TBD | TBD | TBD | TBD |

<a id="section-2"></a>

## 结果发布与分析规则

正式导出器验证每个可运行 baseline cell 的数据、配置、源码、共同 clean parent 和 Agreement 参照，并将原始 JSON 与 manifest 归档。页面按每个攻击分别展示防御效应和资源消耗，三种子齐全后输出均值与样本标准差。

分析顺序为 Target 效用、None 下的提取程度、同一攻击下的防御收益、真实预算与训练步数、跨种子稳定性。完整主矩阵待 Ours 完成后补齐。执行和回传命令统一在 [06](06_COMMANDS.md)。
