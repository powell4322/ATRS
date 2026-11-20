# 08 实验结果与分析

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 07](07_PROGRESS.md) · [下一页 09](09_IMPLEMENTATION_AND_TBD.md)

**本页目录**

- [正式结果状态](#section-1)
- [结果发布与分析规则](#section-2)

<a id="section-1"></a>

## 正式结果状态

当前为 pending。首轮只完成 ML-1M + SASRec 的 GRO、seed 42、1k 名义序列和正常训练轮次。多种子复测在方案完成后再考虑。None 的攻击格暂缓，Ours 的方法稍后确定。基础 clean teacher 作为预训练和主 Agreement 的参照仍需训练。

正式报告展示五个主指标，主 Agreement 对照原始 clean Target。论文历史数值和本地软件验证只用于核查资料和实现。

| Seed | Attack | Defense | Target Recall@10 | Target NDCG@10 | Surrogate Recall@10 | Surrogate NDCG@10 | Agreement@10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | Random/DFME/BECOME | GRO | pending | pending | pending | pending | pending |

None 攻击格、多种子复测和 Ours 均未执行，不列作当前待完成的结果格。

<a id="section-2"></a>

## 结果发布与分析规则

正式导出器验证每个可运行 baseline cell 的数据、配置、源码、共同 clean parent 和 Agreement 参照，并将原始 JSON 与 manifest 归档。当前逐个攻击展示单种子的真实指标和资源消耗，不要求三种子才能发布，也不生成等待复测的空汇总表。若后续执行且凑齐三种子，再输出均值与样本标准差。

当前先看 GRO Target 效用、Surrogate 指标、clean-reference Agreement 和真实预算。None 未运行时，不计算或声称 GRO 相对无防御的收益。后续补同 seed、同攻击的 None 后才能分析配对防御效应，跨种子稳定性等待复测。运行命令统一在 [06](06_COMMANDS.md)。
