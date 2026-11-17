# 09 Scheme C 训练时防御可行性

<!-- doc-nav:start -->
[00 总索引](../README.md) · [01 待审决策](../REVIEW_DECISIONS.md) · [上一页 08](scheme_b_experiments.md) · [下一页 10](../REPRODUCTION_PROTOCOL.md)
<!-- doc-nav:end -->

H3 假设，训练出的目标网络能够表现出 A 的定向低可学习性排序，并保持足够推荐效用。当前只做可行性审计。

| 问题 | 代码证据和所需改动 |
| --- | --- |
| 保留推荐目标 | [gro_step](../../src/atrs/gro.py) 已计算 train-only SASRec BCE，teacher/内部 Student 各有优化器。C1 可复用 BCE、独立 checkpoint 和 clean parenting |
| 改用 A 选择的排序 | GRO 对每个位置从 swap gradient 独立 argmax，换出的 ID 可重复，也可保留原位。C1 应从完整可行列表选择 $R'$，原有行级 argmax 无法直接提供唯一成员、严格头部及编辑预算 |
| 接收外部合法排序 | C1 训练分支可接收整批 detach 后的 $R'$，并显式验证 ID、唯一性、候选集合和头部。当前 `gro_step` 尚无该入口 |
| 排序与成员约束 | 加相邻边的 margin 顺序项和列表内外的 membership 对。负候选可从 Top-$K$ 边界采样。头部可用 clean snapshot 的约束项保持。抽样训练后须实测输出约束满足率 |
| 推理与评价 | 冻结 C1 teacher 后可沿用排序 API，无需部署内部 Student。权重训练改变分数空间，实测 Top-$h$ 保持率、Agr@$K$、顺序敏感一致性、真实 HR/NDCG、攻击效果和额外训练成本 |

C1 的推进条件是 A 已验证有效，且在线计算成本达到需要优化的程度。组别为共同 clean best 的 continued-clean、GRO、C1 和冻结教师上的 A。记录相同追加步数的末轮和 validation 选中两种 checkpoint。C2 的 soft Top-$K$ 与高阶梯度、C3 的表示层正则保留作后续设计。
