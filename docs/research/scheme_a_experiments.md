# 07 Scheme A 学习进展实验

<!-- doc-nav:start -->
[00 总索引](../README.md) · [01 待审决策](../REVIEW_DECISIONS.md) · [上一页 06](research_experiment_plan.md) · [下一页 08](scheme_b_experiments.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [T2–T4 联合诊断](#section-1)
- [T1 排序监督价值](#section-2)
- [最小端到端方法](#section-3)
<!-- doc-toc:end -->

H1 假设，在同等推荐效用和编辑强度下，针对学习进展的排序编辑能减少代理的有效学习。先验证局部效应，再运行外部攻击。数学目标见 [理论基础](theory.md)。

<a id="section-1"></a>

## T2–T4 联合诊断

`python -m atrs.research t2-t4` 读取统一配置的 clean best，使用合成 DFME 前缀和独立初始化的内部 SASRec。默认读取 $K=100$，保留头部 $h=10$，每个前缀包含原列表和两类候选各最多六个。单次候选只做一个相邻交换或一个成员替换。计划中的端到端默认替换预算为 $b=10$，与此处的单步候选区分。支持不编辑。

参考损失是防御方 train-only 窗口上的下一物品 BCE。诊断以外部攻击同款 hinge 计算辅助梯度，每个前缀内固定负样本及每个负样本配对的位置。负项从所有候选列表并集之外采样，便于隔离编辑效应。实际 DFME 在每次蒸馏从当前 Top-$K$ 之外采负例。用 `--warmup-epochs 0` 和大于零的值比较训练阶段，warm-up 使用独立起始 ID 的合成查询，产物会记录这部分预算。诊断关闭 dropout。Exact 采用虚拟一步 SGD，正式外部攻击使用 AdamW，另行实测 AdamW 反事实。

| 实验 | 原始输出与读法 |
| --- | --- |
| T2 | 每候选 $J_{\mathrm{loss}}, J_{\mathrm{dev}}, J_{\mathrm{LP}}, J_{\mathrm{exact}}$，实际一步参考损失及相对基线变化。逐查询 Pearson、Spearman、选择 regret、命中最优候选，常量向量相关系数记 null。零差异的梯度偏离定义为 0 |
| T3 | 两个 hinge 分项的激活比例、损失、分项梯度范数及变化、分数梯度变化、修改位置数和替换数。先筛选修改前后均全激活且首尾固定的 swap，再查消去。其余样本按激活率报告 |
| T4 | 完整反传点积、完整 JVP 加分数系数点积、输出侧近似；原始前向/反传/系数/JVP/近似计时。对比同查询多候选的总摊销成本，多次重复预热后才能报告速度 |

<a id="section-2"></a>

## T1 排序监督价值

`python -m atrs.research t1` 在共同 Top-$K$ 生成前缀上比较 Top-5/10/20/50/100 截断监督。加 `--extended` 比较排名区间和单独的 intra/inter loss。各组共享初始化、训练样本数和步数。负样本按对应监督列表的补集重采，读结果时同时考虑这个变化。完整 Top-$h$-only adaptive attack 需在生成与蒸馏两处都限制前 $h$ 位，当前尚无该入口。

<a id="section-3"></a>

## 最小端到端方法

候选空间与 seed 固定后，比较不编辑、同数随机交换/替换、A-Loss、A-Gradient、A-LP。A-Exact 是低预算的候选最优诊断。根据 T2 在不同阶段和初始化下的相关性与 regret 决定下一步。安全效果同时检验外部代理 HR、NDCG、与 clean 及保护接口的 Agreement。在线保护端由单一接口提供响应，记录实际编辑数、有效打破约束的比例及延迟。

默认先用严格头保持。若完整 Top-$h$-only 已可高效提取，再评估折扣相关性的软预算。匹配编辑和效用之后绘制安全–效用与查询预算曲线，横坐标采用实测请求数。跨损失与跨代理的 T7 记录得分排序相关、符号一致率和选中候选的真实 regret。

运行参数及输出目录见 [矩池云运行手册](../MATPOOL_RUN.md)。
