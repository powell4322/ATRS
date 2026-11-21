# 04 统一防御实验协议

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 03](03_CONFIGURATION_AUDIT.md) · [下一页 05](05_DATA_AND_BUDGET.md)

**本页目录**

- [冻结 Setting](#section-1)
- [正式矩阵和当前可运行部分](#section-2)
- [数据和训练权限](#section-3)
- [Full Ranking 候选和指标](#section-4)
- [预算和公平性](#section-5)
- [配置选择、复用与报告](#section-6)

<a id="section-1"></a>

## 冻结 Setting

| 维度 | 冻结设置 |
| --- | --- |
| 数据 | ML-1M、Beauty、Steam |
| 模型 | SASRec、BERT4Rec |
| 模型关系 | Identical Model Architecture，同一个 cell 的 Target 与 Surrogate 使用相同架构和容量 |
| 威胁模型 | Data-free Ranking-only Black-box |
| 攻击 | Random、DFME、BECOME |
| 防御 | None、GRO、Ours |
| API | Ordered Top-100 Item IDs |
| 评价 | Full Ranking，Leave-one-out |
| 主指标 | Target Recall@10、Target NDCG@10、Surrogate Recall@10、Surrogate NDCG@10、Surrogate Agreement@10 |
| Agreement 参照 | 同一 seed 的原始未保护 clean Target |
| 随机性 | 当前探索仅 seed 42；方案完成后再考虑 42、43、44 多种子复测 |

首批执行 ML-1M + SASRec。NARM、Sim4Rec 和异构提取为可选扩展。Reverse、Random Shuffle 与 continued-clean 的旧控制不进入主矩阵。攻击策略作为各自独立的防御压力测试，逐个比较同一攻击在 None、GRO、Ours 下的表现。

<a id="section-2"></a>

## 正式矩阵和当前可运行部分

研究范围维持 3 数据 × 2 架构 × 3 攻击 × 3 防御，每 seed 为 54 个 cell；若后续确认三种子复测，则为 162 格。这是后续覆盖范围，当前不自动展开。ML-1M/SASRec 的完整防御比较为每 seed 9 格。

| Attack | None | GRO | Ours |
| --- | --- | --- | --- |
| Random | 正式入口已实现 | 正式入口已实现 | 方法与入口 TBD |
| DFME | 正式入口已实现 | 正式入口已实现 | 方法与入口 TBD |
| BECOME | 论文参数与已记录源码冲突的重建入口 | 同一攻击配置 | 方法与入口 TBD |

根据 2026-11-21 上传快照与本轮执行调整，下一任务只选择 ML-1M/SASRec、seed42 的 DFME × None/GRO，共 2 个配对 cell。Random 后置；初步改进机制先验证，再进入 Ours × DFME，随后 BECOME。已完成的基础 clean teacher 与 GRO 不重复训练，其共同参照身份保持不变。多种子及更多实验在方案完成、单种子现象清楚后再决定；Beauty/Steam 与 BERT4Rec 的入口仍待适配。

单独 GRO 的指标用于观察受保护模型效用和代理提取程度。缺少同 seed、同攻击的 None 结果时，无法计算 GRO 相对无防御的收益；clean teacher 的效用和参照身份不能代替 None 条件的外部提取实验。因此将 DFME 的配对 None 提升为下一任务。

<a id="section-3"></a>

## 数据和训练权限

每用户的最后一项作 test，倒数第二项作 valid，其他事件作 train。Teacher 可以用自有 train 训练、valid 选 best。攻击者仅知道公开物品目录、返回的有序 ID 和自己的合成前缀。

外部 Surrogate 训练、超参数选择、早停和阶段反馈均不得使用真实 train/valid/test 标签、真实人气、目标 logits、梯度或参数。BECOME 的反馈只用合成终端前缀的排序一致性。固定攻击配置适用于所有防御条件，Surrogate 使用预定训练轮数与最终权重。目标的真实 test 只在冻结模型后的独立最终评价读取。

防御方内部 Student 与攻击 Surrogate 独立初始化。A 的 train-only 参考数据只属于防御端。历史 T1/T5 的真实 valid 分析属于机制诊断，产物带诊断标记，不能回流正式攻击的配置选择。

<a id="section-4"></a>

## Full Ranking 候选和指标

候选宇宙为物品 ID 1..N，0 为 padding。BERT4Rec 的 mask ID 为 N+1，须在实现时排除。用完整训练历史加 valid 项预测 test，先标记历史物品为不可推荐，再恢复重复的真实目标。比较模型使用同一候选 mask，分数降序，平分按 item ID 升序。Source API 的合成序列生成保留历史重复候选，其差异不用于改变两种攻击的生成逻辑。

每用户只有一个真实下一物品，Recall@10 等于该目标是否进入前十，NDCG@10 为命中时的倒数对数折扣。Agreement@10 是 Surrogate 与 clean Target Top-10 的集合交集除以有效候选数 min(10, 候选数)。正式数据的有效候选数均远大于 10。代码保留 hr@10 与 agr@1 兼容字段，主表只展示已冻结的五项。

GRO 属于训练时防御，其 Target 效用来自实际部署的 GRO teacher。未来推理时 Ours 必须通过 evaluator 的 ranking_api 接口计算 Target Utility，直接使用实际返回的保护列表。该接口拿到全部合法目录生成的 Top-100 输出后，依照共同的历史 mask 选出可展示的前十，候选不足时以实际返回结果计分。评价端不从隐藏 clean 分数补入物品。请求端不会收到真实目标标签。对 protected API 的 Agreement 可作内部诊断，主 Agreement 始终指向 clean teacher。

<a id="section-5"></a>

## 预算和公平性

正式采用 BECOME Table 3 的 1k 名义序列预算，三种攻击都初始化 1000 条合成序列。保留各自的生成、蒸馏和方法特定训练参数。取消旧 20k 新前缀硬上限，真实查询消耗单独记录。BECOME 有选择性延长与反馈，同一名义序列数并不确保实际请求相等。统计定义见 [05 数据与预算](05_DATA_AND_BUDGET.md)。

同一种攻击跨防御的 nominal M、生成长度、采样策略、margin、优化器、学习率、训练 schedule 和种子映射完全一致。GRO 与未来 Ours 训练时防御从同一 clean best 出发，记录 parent SHA 和训练步数。不同攻击允许采用原有的不同损失和训练 schedule，论文按攻击分别分析防御收益。

<a id="section-6"></a>

## 配置选择、复用与报告

配置参数采用论文明确值，未公布的值追溯固定官方源码或现有仓库，来源表见 [03](03_CONFIGURATION_AUDIT.md)。无法由两者确认的参数标为 TBD。调整参数要生成新配置和 run_root，不能将历史同名运行当作新设定。原 phase1 配置和正确的旧 baseline 入口保留供回溯。

未找到可核验 GRO 官方源码时，当前实现按论文公式和明确设置迁移；未公开参数采用固定、显式记录的工程值，不能称为作者确认值。尚未实现的模型保留为后续任务，不以任意配置冒充论文复现或正式主结果。

教师与 GRO 根据防御方真实 valid NDCG@10 早停；外部代理目前固定轮数，不得直接复用真实 valid/test 的早停。训练预算若需下调，先在独立诊断中校准固定轮数或仅依赖合成 API 监督的停止规则，同一攻击跨防御统一执行。低训练 loss 不能单独证明提取效果收敛。

每次运行自动保存完整配置、seed、源码 SHA、数据 SHA、教师/代理/查询 hash、实际资源与时间，无需手动校验命令。当前逐格报告 seed 42 的真实结果，不作跨种子稳定性结论。方案完成后再考虑多种子复测；执行且齐全后逐个 Attack × Defense 报均值和样本标准差。None 同时承担正式无防御对照与检查提取效应的作用。结果只来自完整数据和完整预算的实际运行。本机软件测试与 CPU smoke 记录在进度页，服务器直接运行完整配置。
