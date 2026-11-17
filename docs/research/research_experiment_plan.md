# 06 多方案研究与代码实施计划

<!-- doc-nav:start -->
[00 总索引](../README.md) · [01 待审决策](../REVIEW_DECISIONS.md) · [上一页 05](../PAPER_TO_CODE_MAP.md) · [下一页 07](scheme_a_experiments.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [当前实验顺序](#section-1)
- [实验矩阵与阶段验收](#section-2)
- [实现位置与拟议增量](#section-3)
<!-- doc-toc:end -->

<a id="section-1"></a>

## 当前实验顺序

1. **先复现统一基线的关键路径。** 用矩池云单卡跑 CUDA smoke，核对数据 SHA-256，训好单个 ML-1M/SASRec clean teacher，再完成一次 clean + DFME。记录外部代理是否正常学习、实际查询数、checkpoint 验证效用和耗时。
2. **在同一 clean best 上展开小规模 A 和 B。** A 跑 T2–T4，B 跑独立的 T5，同时做低成本 T1。GRO / continued-clean 教师和其余 Phase I 攻击可以复用同一 clean best，继续完成同协议六格。A 和 B 共用数据、模型与评估代码。
3. **证据通过后实现最小候选方法。** 基于固定候选集合比较 None、Matched Random、A-Loss、A-Gradient、A-LP。小样本 A-Exact 分辨目标失效和一阶近似失效。B 先用 T5 检查轨迹信号，再以 T6 验证候选查询价值。
4. **追加迁移与成本评估。** 先 T7 独立初始化与同构代理，再测试 BECOME、跨损失、异构代理和自适应攻击。A 有效且在线成本偏高时分析 C1。最后扩展 Steam、Beauty、BERT4Rec、至少三个种子和查询预算曲线。原论文协议复现单独建配置，优先级低于统一实验的首个诊断包。

CUDA 命令、失败恢复和输出目录见 [矩池云运行手册](../MATPOOL_RUN.md)。

<a id="section-2"></a>

## 实验矩阵与阶段验收

| 编号 | 对照与交付结果 | 当前状态 |
| --- | --- | --- |
| G0 | clean / GRO / continued-clean，DFME / BECOME，checkpoint 谱系、实际请求账本、教师 HR/NDCG | 本地软件验收完成，CUDA 与正式基线待跑 |
| T1 | 固定前缀上的 Top-5/10/20/50/100、排名区间、intra/inter 消融，评估学习到的排序信息 | 前三种控制入口可跑，完整 Top-$h$-only 自适应待实现 |
| T2 / G1 | 比较 Loss、Gradient-deviation、LP 与 Exact，检查每查询相关性、选择 regret 和首选一致 | 入口可跑，真实数据待跑 |
| T3 | 记录 intra/inter 梯度和激活比例，检查固定首尾且全激活时的消去 | 入口可跑，真实数据待跑 |
| T4 | 完整反传、完整 JVP、输出侧投影，比较一致性与成本 | 入口可跑，真实数据待跑 |
| T5 / G3 | 随机成员替换的 generation × supervision，分解轨迹/监督/交互 | 入口可跑，真实数据待跑 |
| 最小 A / G2 | 同 head、编辑类型、预算与推荐效用，比较随机、Loss、Gradient-deviation、LP | 取决于 T2 / T3 |
| T6 | 比较人气、共现、状态相似、梯度对齐与实际短期学习进展 | 取决于 T5 |
| T7 / G4 | 编辑分数的跨代理/损失迁移，随后评估独立攻击 | 待实现 |
| G5 | latency、吞吐、训练开销、近似代价及 C1 feasibility | T4 有小样本计时，部署验证待做 |

H1 对应 G1/G2，H2 对应 G3，H3 对应 C1 的训练后效用和安全验证。若 A、B 均有信号，可估计联合目标与交互。若只出现一支信号，沿这一支继续。若精确 query value 有效但缓存低相关，探索按上下文分组的缓存。若两支都无法优于匹配随机，先回看候选空间、参考目标和攻击预算。

<a id="section-3"></a>

## 实现位置与拟议增量

| 需求 | 代码或待办 |
| --- | --- |
| 共享干净 API、请求计量和攻击入口 | 复用 `api.py`、`attacks.py` 和 `cli.py`。区分 prefix 行数、新请求、缓存、反馈、序列数、训练步数 |
| 防御方保护响应和查询诊断 | `feedback_diagnostics.py` 生成两种视图，`research.py t5` 复用 DFME。待实现生产 A-LP 保护入口，同一受保护 API 同时服务攻击生成和蒸馏 |
| 合法编辑与机制诊断 | `learning_progress.py` 共享 DFME hinge 分项，完整 JVP、Exact 和输出侧估计都在同一候选、同负样本上比较 |
| 查询价值与控制 | `research.py t1` 共享固定前缀。完整 Top-$h$-only 需在生成和蒸馏两处限制接口。T6 从固定前缀小样本枚举下一步候选开始 |
| 可复现与评价 | 统一留一、full ranking 主指标及 sampled 单独报告。命令、参数、版本、权重哈希、原始结果和时间写入独立目录 |
| 后续训练防御 | 在 `gro.py` 现有 BCE 与联合更新之上增加 C1 训练分支和合法列表约束，见 [C 可行性](scheme_c_feasibility.md) |

Phase I 量化范围为 DFME/BECOME 和 GRO。独立的 Random attack 尚待定义其均匀抽样粒度和蒸馏目标。它与 T5 的 Random Replacement 防御、A 的 matched random 编辑是不同的实验因素。LLM4MEA 和 Sim4Rec 暂不完整复现。

探索期间在 validation fold 上读学生指标，冻结配置后才用 test fold 验证研究结论。正式结果至少报告三种子均值及离散程度，并注明代理/防御的初始化、选中 checkpoint epoch 和实际训练步数。每次机制试验保留原始输出，包括负面结果和失败日志。
