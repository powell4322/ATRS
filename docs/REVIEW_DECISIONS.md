# 01 待审决策清单

<!-- doc-nav:start -->
[00 总索引](README.md) · [01 待审决策](REVIEW_DECISIONS.md) · [上一页 00](README.md) · [下一页 02](research/theory.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [评审顺序与记录方式](#section-1)
- [01 统一对比与论文原协议复现](#section-2)
- [02 数据来源、时间顺序与切分](#section-3)
- [03 推荐指标与候选集合](#section-4)
- [04 Agreement 的参照与定义](#section-5)
- [05 查询预算、缓存与相等预算](#section-6)
- [06 BECOME 的论文、源码与统一实现](#section-7)
- [07 GRO 归一化、候选与骨干迁移](#section-8)
- [08 DFME 负采样与实现一致性](#section-9)
- [09 当前冻结参数与选择依据](#section-10)
- [10 Checkpoint 选择与继续训练公平性](#section-11)
- [11 外部代理验证与训练预算](#section-12)
- [12 模型、数据集、种子与统计](#section-13)
- [13 A 的参考目标、优化器和效用预算](#section-14)
- [14 B 的四格、查询价值和适用攻击](#section-15)
- [15 Random、跨损失与自适应攻击](#section-16)
- [16 研究门槛、C 分支与贡献](#section-17)
<!-- doc-toc:end -->

本页集中记录论文协议、指标、模型、参数和复现口径。当前值来自代码、冻结配置与研究入口，代表可以执行的起点。研究选择仍待你 review，可按编号逐项回复，再将结论同步到配置、代码、实验命令和相关文档。

<a id="section-1"></a>

## 评审顺序与记录方式

先 review 01–08 的协议和基线定义，再看 09–12 的参数及模型选择，最后确定 13–16 的新方法和实验规模。环境预检与 CPU/CUDA smoke 可以先运行。正式结果解释依赖适用决策的最终记录。

每项可以按下面的格式填写。

> 决策 03。结论为……。理由与论文/代码依据为……。适用实验为……。落实到配置或函数……。验证方法为……。

各项初始状态均为待 review。确定后在该项末尾填写日期和理由。若改动影响已完成实验，使用新的配置和 run_root 保存下一版。

<a id="section-2"></a>

## 01 统一对比与论文原协议复现

**当前实现**是统一 ML-1M/SASRec、Top-100、20k 新前缀请求上限，支持 DFME、BECOME 和 GRO。原始论文的完整定量复现尚未完成。

**需要决定**主实验采用统一防御比较、各论文原协议复现的范围，以及如何为两类结果命名。建议先验证 clean SASRec + DFME，再完成统一六格与 P0 诊断，原协议另用独立配置。须说明目前预处理数据与论文统计的差异。

**影响位置**在 [10 复现协议](REPRODUCTION_PROTOCOL.md)、[18 基线运行计划](EXPERIMENT_PLAN.md)、[13 已知差异](KNOWN_DEVIATIONS.md)。

<a id="section-3"></a>

## 02 数据来源、时间顺序与切分

**当前实现**读取两列文本，假设用户内行序为时间顺序，末两项分别作 valid/test。物品 ID 为密集正整数，padding 为 0。ML-1M 含 6040 用户、3416 物品、999611 交互。缺少原始评分、时间戳、过滤过程和映射来源。

**需要决定**能否补齐数据出处与预处理过程。Steam/Beauty 的短用户、最小交互数与 ID 重映射规则也需确定。保留原数据字节和 SHA，派生数据使用新文件及 metadata。

**影响位置**在 [11 数据协议](DATA_PROTOCOL.md)、[15 协议审计](audits/protocol_audit.md)、[data.py](../src/atrs/data.py)。

<a id="section-4"></a>

## 03 推荐指标与候选集合

**当前实现**full ranking 为主，同时单独输出 sampled 100-negative。Full 排除输入历史并恢复重复目标。单目标留一时 HR@10 等于 Recall@10，NDCG 按目标排名计算。平局按 item ID 升序。

**需要决定**最终报告哪些 k 值，HR/Recall 的名称，是否保留 sampled 用于原论文参考，以及主表是否沿用 seen-item 过滤。当前代码只输出 k=10 的推荐指标，增加多个 k 需修改统一 evaluator。

**影响位置**在 [10 复现协议](REPRODUCTION_PROTOCOL.md)、[evaluation.py](../src/atrs/evaluation.py)。评价端与生成 API 的历史过滤差异需写入论文。

<a id="section-5"></a>

## 04 Agreement 的参照与定义

**当前实现**Agr@1 为第一项完全匹配，Agr@10 为集合交集占有效 Top-10 长度的比例。Phase I 参照该格的 teacher，T5 统一参照 clean teacher。

**需要决定**新方法是否同时报告相对 clean 与相对 protected API 的保真度。建议两者分别命名，并明确是否添加顺序敏感的指标和 Agr@100。

**影响位置**在 [15 协议审计](audits/protocol_audit.md)、[02 理论](research/theory.md)、[evaluation.py](../src/atrs/evaluation.py)。

<a id="section-6"></a>

## 05 查询预算、缓存与相等预算

**当前实现**缓存开启，B 计新原始前缀，另计所有提交行、缓存、反馈、批前向、序列数与蒸馏样本数。DFME 生成行上限 20000，BECOME 生成行上限 19920，加 664 行终端反馈，通常命中缓存。实际达成预算可能更少。

**需要决定**按原始前缀、截断后的有效上下文还是每行请求计费，允许怎样的攻击方缓存，以及预算曲线的取点。当前原始前缀身份与 max_len 截断后的模型输入可能不同。若改成每请求计费，BECOME 序列数需重算。

**影响位置**在 [12 公平性](BASELINE_FAIRNESS.md)、[15 协议审计](audits/protocol_audit.md)、[api.py](../src/atrs/api.py)。

<a id="section-7"></a>

## 06 BECOME 的论文、源码与统一实现

**当前实现**beta=0.5，alpha=0.5，initial_fraction=0.2，select_fraction=0.5，4 个追加 phase，阶段长度由归一化的绝对正态采样给出，反馈用 Top-100 重叠。已查源码 beta=1，其 sampler、频率更新事件与阶段安排也有差异。

**需要决定**论文方向或固定源码的哪个版本进入主表，另一口径是否作为敏感性对照。逐项确认 beta、alpha、频次更新事件、反馈 k、选取比例、mu/sigma 与 distillation schedule。每种口径独立配置并记录来源。

**影响位置**在 [13 已知差异](KNOWN_DEVIATIONS.md)、[05 论文到代码](PAPER_TO_CODE_MAP.md)、[attacks.py](../src/atrs/attacks.py)。

<a id="section-8"></a>

## 07 GRO 归一化、候选与骨干迁移

**当前实现**将论文 BERT4Rec 上的 GRO 迁移到 SASRec。两个 hinge 分别取 mean，论文公式为 sum。Swap 每位置独立 argmax，可出现重复候选。Teacher BCE、Student hinge 与 swap_weight 共同更新。

**需要决定**GRO baseline 是否保留当前归一化，另开 paper-native 版本需要怎样的尺度。原 GRO 的行级候选行为与 A/C 的完整合法排序约束分别记录。BERT4Rec 原生验证何时纳入，官方代码未核实时哪些结论以论文为依据。

**影响位置**在 [14 仓库审计](audits/repository_audit.md)、[09 C 可行性](research/scheme_c_feasibility.md)、[gro.py](../src/atrs/gro.py)。

<a id="section-9"></a>

## 08 DFME 负采样与实现一致性

**当前实现**相邻 hinge 和 inter-list hinge 求均值后相加，负例严格排除 Top-K 与 pad。统一 model max_len=400，生成长度为 200。已查 DFME 原 ML-1M model 长度为 200，源码 softmax 采样还有不同的排除行为。

**需要决定**统一 baseline 保留哪些修正，源码严格复现覆盖哪些行为。目录不足 jK 个独立负例时的替代采样或支持域要明确。当前小目录会限制负例数量，不整除时以首个正项配对，该分支需要在扩展前 review。

**影响位置**在 [13 已知差异](KNOWN_DEVIATIONS.md)、[14 仓库审计](audits/repository_audit.md)、[attacks.py](../src/atrs/attacks.py)。

<a id="section-10"></a>

## 09 当前冻结参数与选择依据

| 模块 | 当前值 | 待确认内容 |
| --- | --- | --- |
| SASRec | max_len 400，hidden 64，layers 2，heads 2，dropout/attention_dropout 0.1 | 统一容量、DFME 200/400 长度敏感性、论文对应参数 |
| Teacher | AdamW lr 0.001，weight_decay 0.01，batch 32，eval_batch 128，sliding_fraction 0.5 | 与上游初始化、窗口、clip、优化器分组的差异 |
| Teacher 训练 | clean 上限 1000 epochs，finetune 上限 20，patience 30 | 收敛标准、额外计算量、验证频率与早停 |
| GRO | rank/negative/swap margin 均为 0.5，swap_weight 0.01 | 归一化确定后的 lambda 范围与选择依据 |
| API | K 100，batch 64，max_requests 20000 | budget 曲线、缓存与推荐效用评价邻域 |
| DFME | M 100，length 200，generation_batch 20，train batch 128，epochs 20，lr 0.001，margins 0.5/0.5 | 原论文与代码不同参数的选择，固定步数与收敛比较 |
| BECOME | M 166，length 200，phase 4，初始比例 0.2，选取比例 0.5，alpha 0.5，epochs/phase 4，batch 128，lr 0.001，margins 0.75/1.5，beta 0.5 | 对应决策 06，实际总 step 和 achieved B |

精确值在 [统一 JSON 配置](../configs/phase1/ml1m_sasrec_seed42.json)。候选搜索先用 validation 与分层的小范围调参，明确各方法是否享有相同调参资源，再固定 test 评价。搜索范围、选择指标和最终参数表需要记录。

<a id="section-11"></a>

## 10 Checkpoint 选择与继续训练公平性

**当前实现**clean、GRO 和 continued-clean 以 valid NDCG@10 选各自 best。两种追加训练从同一 clean best 开始并保存 parent hash，相同 finetune epoch 上限。实际早停位置和被选 best 的步数可能不同。

**需要决定**主结果采用各自 valid best、相同追加 step 的 endpoint，还是二者都报告。独立记录 clean 起点、更新次数、验证开销和所选 epoch。

**影响位置**在 [12 公平性](BASELINE_FAIRNESS.md)、[cli.py](../src/atrs/cli.py)。

<a id="section-12"></a>

## 11 外部代理验证与训练预算

**当前实现**Phase I 的代理按固定 epoch 训练，最终才测真实 test，无合成 valid 选 best。BECOME 的分阶段反馈用 Student 与 Teacher 的排序差异。

**需要决定**是否保留合成验证前缀、如何避免与训练重叠，以及如何确定代理收敛和不同攻击的训练计算量。T1/T5 默认用真实 valid 做防御方分析，信息只在诊断端使用。正式攻击的选择规则需要保持可解释。

**影响位置**在 [14 仓库审计](audits/repository_audit.md)、[research.py](../src/atrs/research.py)、[cli.py](../src/atrs/cli.py)。

<a id="section-13"></a>

## 12 模型、数据集、种子与统计

**当前实现**正式入口支持 ML-1M + SASRec，phase1 配置 seed=42。研究入口可独立指定 Student/诊断 seed。

**需要决定**独立目标训练种子至少选哪三个，是否配对攻击种子，以及 BERT4Rec、Steam、Beauty 的扩展顺序。诊断 seed 改变时 target 仍来自配置中的 seed。区分目标随机性、内部 Student 随机性与外部攻击随机性，报告均值、离散程度与预算。

**影响位置**在 [06 研究计划](research/research_experiment_plan.md)、[16 实现状态](IMPLEMENTATION_STATUS.md)。

<a id="section-14"></a>

## 13 A 的参考目标、优化器和效用预算

**当前实现**T2–T4 使用 train-only next-item BCE 和固定负样本作为参考。候选内共享负例，包含 clean、单相邻 swap 和单成员替换。h=10，SGD eta=0.001。完整外部攻击用 AdamW。

**需要决定**参考窗口划分与是否独立于内部 Student warm-up，BCE 与推荐目标的匹配，实际 AdamW 反事实，以及端到端替换预算 b=10、交换预算、软效用代价的定义。保护 API 和 full-ranking 过滤若改变候选顺序，要验证 Top-h 保持的评价条件。

**影响位置**在 [02 理论](research/theory.md)、[07 A 实验](research/scheme_a_experiments.md)、[learning_progress.py](../src/atrs/learning_progress.py)。

<a id="section-15"></a>

## 14 B 的四格、查询价值和适用攻击

**当前实现**T5 随机替换尾部 10 项，四格共享对应前缀、Student 初始化和步数。不同初始 ID 保证两生成分支的 raw-prefix 请求数一致。双视图用于防御端机制诊断。

**需要决定**T5 规模、轨迹效应判据、覆盖和人气等辅助指标，以及 T6 的人气/共现、状态相似、梯度价值和短期真实收益如何比较。BECOME 的频次/反馈状态需显式建模。分布变化的方向与防御收益由实验确定。

**影响位置**在 [08 B 实验](research/scheme_b_experiments.md)、[feedback_diagnostics.py](../src/atrs/feedback_diagnostics.py)。

<a id="section-16"></a>

## 15 Random、跨损失与自适应攻击

**当前实现**有 DFME/BECOME，以及诊断中的 Random Replacement。独立 Random attack、完整 Top-h-only、自适应重复查询聚合、独立 listwise/KL 变体尚未实现。

**需要决定**Random 查询是独立随机前缀还是随机序列，以及其蒸馏目标。完整 Top-h-only 同时限制生成与监督。跨损失测试需固定产生伪监督的规则与负采样，LLM4MEA/Sim4Rec 的完整复现范围也在此确定。

**影响位置**在 [04 相关工作](RELATED_WORK.md)、[06 研究计划](research/research_experiment_plan.md)。

<a id="section-17"></a>

## 16 研究门槛、C 分支与贡献

**当前计划**先做 G0 和 T1–T5，观察 LP 是否更能预测一步效果、相同预算的定向编辑是否优于随机、查询轨迹是否有独立效应。T6/T7 和 C1 据此推进。

**需要决定**每个 gate 的样本量、重复次数、通过标准与负面结果的下一步。贡献随证据更新。C1 还需成员和顺序约束的实际恢复率，以及相同效用下的安全性与成本比较。

**影响位置**在 [03 候选贡献](research/contributions.md)、[06 研究计划](research/research_experiment_plan.md)、[17 理论验证报告](research/theory_validation_report.md)。
