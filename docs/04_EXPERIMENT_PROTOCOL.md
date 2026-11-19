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
| 随机性 | 正式三种子，项目运行编号 42、43、44 |

首批执行 ML-1M + SASRec。NARM、Sim4Rec 和异构提取为可选扩展。Reverse、Random Shuffle 与 continued-clean 的旧控制不进入主矩阵。攻击策略作为各自独立的防御压力测试，逐个比较同一攻击在 None、GRO、Ours 下的表现。

<a id="section-2"></a>

## 正式矩阵和当前可运行部分

完整计划为 3 数据 × 2 架构 × 3 攻击 × 3 防御 × 3 种子，共 162 个 cell，逐阶段实现和执行。首批 ML-1M/SASRec 为每 seed 9 格。

| Attack | None | GRO | Ours |
| --- | --- | --- | --- |
| Random | 正式入口已实现 | 正式入口已实现 | 方法与入口 TBD |
| DFME | 正式入口已实现 | 正式入口已实现 | 方法与入口 TBD |
| BECOME | 论文参数与已记录源码冲突的重建入口 | 同一攻击配置 | 方法与入口 TBD |

当前正式启动器执行可用的 18 格，即 ML-1M/SASRec 的 None/GRO、三个攻击、三个种子。生成的结果页明确列出 Ours 待完成。Beauty/Steam 与 BERT4Rec 的模型和数据入口仍待适配。

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

每次运行保存完整配置、seed、源码 SHA、数据 SHA、教师/代理/查询 hash、实际资源与时间。三种子齐全后逐个 Attack × Defense 报均值和样本标准差。None 同时承担正式无防御对照与检查提取效应的作用。正式结果只来自完整数据和正式预算的实际运行，运行前的本地软件测试记录在进度页。
