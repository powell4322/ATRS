# 09 创新方案、代码现状与待确认项

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 08](08_RESULTS.md) · [下一页 10](10_REPOSITORY_AND_SYNC.md)

**本页目录**

- [供外部评审的项目摘要](#section-1)
- [当前实际运行的防御](#section-2)
- [已经修改和接入的代码](#section-3)
- [候选理论、创新与实现缺口](#section-4)
- [参数优先级与诊断配置差异](#section-5)
- [待确认和未修改清单](#section-6)
- [可直接交给其他研究者或 AI 的问题](#section-7)
- [验证与结论边界](#section-8)

<a id="section-1"></a>

## 供外部评审的项目摘要

本项目研究课题组自有序列推荐模型在公开数据集、授权离线环境中的主动模型提取防御。攻击者只知道物品 ID 目录，通过合成前缀读取有序 Top-100 ID；不能访问真实用户数据、人气、目标 logits、梯度或内部参数。防御方可以使用自己的训练数据和独立内部 Student，外部提取 Surrogate 与这个 Student 分开初始化和训练。

当前优先做 ML-1M + SASRec，只跑 seed 42、1000 条名义合成序列。2026-11-21上传快照中的 clean/GRO 教师已早停完成，分别最佳319/144轮，可复用；Random 只到77/1000轮，无最终代理结果。下一默认任务调整为 DFME × None/GRO 两格，Random 后置。代理停止规则先审阅，当前1000轮配置尚未擅自缩短。单种子探索结束、方法完成后，再考虑多种子和更多实验，不自动启动 seed43/44。快照核查与计划见 [07](07_PROGRESS.md)。

后续研究范围保留 ML-1M/Beauty/Steam、SASRec/BERT4Rec、Random/DFME/BECOME 和 None/GRO/Ours。统一 Full Ranking、Leave-one-out，主指标为 Target 与 Surrogate 的 Recall@10、NDCG@10，以及相对原始 clean Target 的 Surrogate Agreement@10。不同攻击各自保留算法机制，同一种攻击跨防御保持配置和预算规则一致。

下面的 A/B/C 是候选研究路线，尚未确定最终 Ours。本页汇总可讨论的理论、已有代码、缺口和问题；完整推导见 [01 理论与贡献](01_THEORY_AND_CONTRIBUTIONS.md)，论文及代码差异见 [03 配置核查](03_CONFIGURATION_AUDIT.md)。

<a id="section-2"></a>

## 当前实际运行的防御

当前可运行防御是 **GRO 在 SASRec 上的独立迁移实现**，不是已经实现的新 Ours，也不等于原论文 BERT4Rec 实验的逐值复现。正式启动器只接受 none/gro，下一默认任务选择两者的 DFME 配对。JSON 保留历史 gro 选择以维持 checkpoint 身份，当前任务选择以启动器参数为准。

[gro.py](../src/atrs/gro.py) 的 gro_step 保留教师推荐 BCE 和独立内部 Student。它把教师 Top-K 写成可求梯度的排名矩阵，用 Student 的 intra/inter 排序损失对矩阵求梯度，逐位置 argmax 得到 replacement，再用交换 margin 项更新教师。教师和 Student 各有优化器；内部 Student 不作为外部提取模型复用。当前正式 GRO 的损失尺度为 item-sum 后 batch-mean。

逐位置 argmax 可能多次选中同一个 replacement，这里是训练目标，不表示实际 API 返回重复 ID。部署仍由教师分数生成唯一 Top-100。未来 C1 若改成选择完整合法列表，需单独约束唯一成员、头部、编辑预算和排序恢复，不能把 GRO 现有训练目标当成已经完成的 C1。

单独 GRO 的结果可以观察教师效用和外部模型的提取程度。它不能给出 GRO 相对 None 的防御收益；主 Agreement 使用 clean teacher，也不能代替无防御条件的外部提取。本轮据此将 DFME 的配对 None/GRO 提升为下一任务。

<a id="section-3"></a>

## 已经修改和接入的代码

本表列出当前仓库已有的关键修改，不把已有 baseline、协议修正或部署工作列为学术创新。

| 类别 | 已有行为与代码位置 | 当前边界 |
| --- | --- | --- |
| 正常轮次与当前范围 | [gro_first seed42 配置](../configs/gro_first/ml1m_sasrec_seed42.json)：长度 200、hidden 64、2 层/2 heads、dropout 0.1、batch 128、Adam 0.001/0.01；教师与 GRO 最多 1000 epochs、patience 30；Random/DFME 固定 1000 epochs，BECOME 按原阶段 20/30 训练 | 保持现有正常轮次和 M=1000；当前仅 seed 42 |
| 分阶段执行 | [run_formal.py](../scripts/run_formal.py)：默认单 seed，DFME × None/GRO；教师可接续并复用，完整 cell 可复用，自动导出 | 本轮优先最小配对；Ours 不在入口选择中；Random/BECOME 和 seed43/44 不自动启动 |
| 独立攻击机制 | [attacks.py](../src/atrs/attacks.py)：Random 目录采样、DFME 自回归生成、BECOME 分阶段生成/反馈/选择及各自蒸馏；[cli.py](../src/atrs/cli.py) 传入各自配置 | 没有强制统一损失；BECOME 论文与源码冲突仍按 03 记录，未宣称完全等价 |
| 优化器与训练状态 | [training.py](../src/atrs/training.py)：source_optimizer、warmup/scheduler、checkpoint 状态；cli.py 的 _fit_teacher/_run_attack | Adam 与旧 AdamW 路径均保留，正式配置显式选择 |
| GRO baseline | [gro.py](../src/atrs/gro.py)：gro_step，新增 paper_sum 尺度并保留旧 mean 路径 | SASRec 迁移、GRO 原超参数及原仓库等价性仍有 TBD |
| 统一评价 | [evaluation.py](../src/atrs/evaluation.py)：Full Ranking、历史过滤、Recall/NDCG、clean-reference Agreement、ranking_api 保护输出效用接口 | 评价接口已备妥，尚无正式 Ours 调用它 |
| 查询账本和数据边界 | [api.py](../src/atrs/api.py) 的 RankingOracle/QueryCounts；[data.py](../src/atrs/data.py) 的 load_split；training.py 的 SASWindows | 正式攻击只读排序，真实标签用于独立评价；不同资源口径分别记录 |
| 结果与运行简化 | [export_results.py](../scripts/export_results.py) 支持所选 cell 的单种子归档；training.py/cli.py 提供简洁 epoch 进度与最终指标，完整记录仍写 JSONL；setup.sh 仅安装项目 | 本机测试和 CPU smoke，服务器直接跑完整配置；教师验证快照独立归档，尚无完整防御数值 |
| 推理计算 | [model.py](../src/atrs/model.py) 的 next_scores 只投影最后一个隐状态 | 已有测试核对其分数和梯度，属于工程优化 |

<a id="section-4"></a>

## 候选理论、创新与实现缺口

### A：从当前蒸馏损失转向一步学习进展

设内部 Student 参数为 $\psi$，防御者 train-only 参考损失为 $V$，$v=\nabla_\psi V$。原始排序为 $R$，候选保护排序为 $\tilde R$，$g_R=\nabla_\psi\ell(x,R)$。候选评分为

$$
J_{\mathrm{LP}}(\tilde R)=v^\top(g_R-g_{\tilde R}),\qquad
J_{\mathrm{exact}}(\tilde R)=V(\psi-\eta g_{\tilde R})-V(\psi-\eta g_R).
$$

一阶有 $J_{\mathrm{exact}}\approx\eta J_{\mathrm{LP}}$。正值表示该编辑相对原始排序减少参考学习收益，不保证参考损失一定上升。01 给出了当前 hinge loss 更大但一步学习反而更好的合法列表反例，以及光滑条件下的余项界。它说明两个目标一般不等价，不能据此认定完整 GRO 在真实实验中失效。

候选贡献是：在合法 Top-K、效用约束下，以相对学习方向挑选离散编辑，并证明这种选择比随机、Loss 或 Gradient-deviation 更能预测和降低提取收益。链式法则给出 $J_{\mathrm{LP}}=w^\top(a_R-a_{\tilde R})$，其中 $w=J_s v$、$a_R=\nabla_s\ell$；完整 JVP 可在同一查询的候选间复用。SGD 余项界和这个恒等式本身不足以证明新颖性或端到端有效。

**已有代码：** [learning_progress.py](../src/atrs/learning_progress.py) 的 ranking_candidates 和 LearningProgressProbe 生成保持头部的单次相邻交换/成员替换，比较 Loss、Gradient-deviation、LP 和 Exact SGD，记录相关性、选择 regret、梯度激活、完整 JVP 与输出侧近似；[research.py](../src/atrs/research.py) 提供 T2–T4 诊断。

**未修改：** 尚无逐查询实际输出保护列表的正式策略，没有面向完整攻击过程更新内部 Student 的 A 防御入口，没有多步候选搜索、Adam 同状态反事实或与 BECOME listwise/负采样设置匹配的完整诊断。输出侧近似遗漏 SASRec 输入 embedding 和编码器路径，需用已有完整投影作误差对照。

### B：区分监督变化与查询轨迹变化

DFME 从返回列表均匀取下一物品时，纯成员重排不改变给定前缀的下一步生成分布；替换 $m$ 个成员时，单步条件 TV 为 $m/K$。在各步满足相同条件时，长度 $T$ 轨迹的 TV 上界为 $1-(1-m/K)^T$。这只是分布变化幅度的上界，不保证提取变差，也不能直接推广到非均匀采样的 BECOME。

若 $c_\psi(x\oplus i)$ 衡量下一前缀的 clean 学习价值，可构造 $C_\psi(x,R)=\sum_i q(i\mid x,R)c_\psi(x\oplus i)$，并比较 $J_{\mathrm{query}}=C_\psi(x,R)-C_\psi(x,\tilde R)$。与 A 结合的候选评分为 $J_{\mathrm{LP}}+\gamma J_{\mathrm{query}}$，目前未确定 $c$ 的估计器或 $\gamma$。

候选贡献是把即时蒸馏监督和后续查询轨迹分开测量，并在保持效用与编辑量时，定向压低后续查询的学习价值。仅展示随机替换影响结果，不足以支持这个贡献。

**已有代码：** [feedback_diagnostics.py](../src/atrs/feedback_diagnostics.py) 提供随机尾部替换、FeedbackDiagnosticOracle 和配对双视图；research.py 的 T5 构造 clean/protected generation × clean/protected supervision 四格，记录监督、轨迹和交互效应。双视图仅为防御方机制诊断。

**未修改：** 尚无未来查询价值估计器、定向成员替换策略、缓存或 lookahead；没有覆盖 BECOME 自适应反馈的 B 防御。当前随机替换不是已经选定的 Ours。

### C：将有效排序机制内化进训练

C1 的候选设计是先在合法集合 $\Omega(x)$ 中选择高 $J_{\mathrm{LP}}$ 的列表 $R'$，再用推荐损失、学习目标列表的排序/成员 margin 和保持项训练教师。希望以训练成本换取较低线上成本。C2 考虑直接学习进展正则，但需处理离散 Top-K 梯度和高阶计算；C3 的表示层约束仍为开放方向。

**已有代码：** GRO 的教师/内部 Student、两套优化器和共同 clean parent 可复用；01 有 C1/C2/C3 理论设计。

**未修改：** 没有 C1 的合法列表选择、排序与成员联合训练损失、保持项、配置或命令入口；C2/C3 也未实现。完整 Ours 尚未接入正式攻击、评价与结果导出。

C1 只有在 A 的选列表机制有效、训练能恢复该列表且效用可接受时才值得进一步推进；当前未决定必须采用 C1。

### 跨代理与头部效用的共同边界

内部代理与外部代理候选评分若在共同候选集上一致误差不超过 $\xi$，可得到局部选择 regret 至多 $2\xi$。这是条件性局部界，尚未检验独立初始化之间的误差，更不能当作任意自适应攻击保证。T7 的跨代理实验未实现。

保持原始前 $h$ 个 ID 只能在相同候选集合和过滤顺序下精确保留 $k\le h$ 的列表指标。若 API 编辑后离线评价再过滤历史项，尾部可能进入可展示前十；需要以实际保护输出计算 Target Utility。GRO/C1 的训练时近似也没有天然的头部保持保证。

<a id="section-5"></a>

## 参数优先级与诊断配置差异

单个完整配置的训练超参数以指定 JSON 为准。device、resume 控制设备和教师接续，正式模式拒绝 epochs 临时覆盖。启动器的 --defenses/--attacks 控制本次选择，默认 None/GRO 和 DFME，优先于 JSON 的历史 runnable_defenses；实际选择写入结果 manifest。默认只读 gro_first 的 seed42 配置，seed43/44 不自动执行。同一个 run_root 的任务串行运行。seed 数减少不会减少单次训练轮数或查询预算。

当前教师有 valid NDCG@10/patience30 早停，外部代理没有。改代理轮数还会改变线性 scheduler 的 total_steps，并触及整份配置与教师绑定的兼容性；独立预算诊断与复用接口的待改项见 07，不能仅编辑 epochs 后强行加载旧教师。

以下差异已经从当前代码核对，先列为后续修改计划，不擅自把诊断改成最终 Ours：

| 位置 | 现状 | 影响与后续选择 |
| --- | --- | --- |
| research.py 的 --config | 默认仍是 configs/phase1/ml1m_sasrec_seed42.json | 旧诊断不会自动对应当前 gro_first 教师；若开展机制实验，先明确教师及配置版本 |
| research.py 的 _student/_distill | 直接使用 source_adamw，distill_epoch 未显式传入 negative_sampling，故采用 outside_topk | 当前完整攻击使用 Adam 与 source_softmax；诊断量不能直接声称代表当前外部攻击，要决定是否按正式配置接入 |
| LearningProgressProbe._sgd_reference_loss | 固定参数的一步 SGD，不复制外部 Adam 动量/方差状态 | Exact 指 SGD 反事实，不是完整攻击的一步 Adam；SGD 局部理论和 Adam 实证需分开或补一致状态更新 |
| T2–T4 的候选及负集合 | 同查询候选共用 outside-union 负样本，内部 Student 在诊断时固定 | 适合隔离候选差异；当前不等于完整攻击的随机负采样和持续学习过程 |
| T1/T5 的 --fold | 默认 valid，允许 test；产物标记为 defender diagnostic | 正式攻击不可读取这些真实标签作反馈；方法或超参数选择应使用防御方 train/valid，最终 test 独立保留 |

<a id="section-6"></a>

## 待确认和未修改清单

| 编号 | 待确认 / 未完成 | 当前处理和影响 |
| --- | --- | --- |
| 01 | 已有文本的原始来源、时间戳与过滤映射 | 使用冻结文本开展内部比较；来源和映射仍需补齐 |
| 02 | Steam/Beauty 短用户与重新映射 | 分别有 1805/1706 个短用户，入口待适配；当前不运行 |
| 03 | BERT4Rec 训练/生成/评价 | mask probability 已按论文记录，模型、mask ID 和推理语义尚未接入 |
| 04 | BECOME 论文与源码等价性 | 当前为论文参数优先的独立重建；alpha/beta、频次、全局/批内选择及 RNG 差异见 03 |
| 05 | BECOME 的 j 与负样本候选池解释 | 当前按源码每正例 30 个、source_softmax；纸面解释仍待确认 |
| 06 | GRO 原论文设置的精确对应 | 当前为 SASRec 迁移；margin 0.5/0.5/0.5、swap_weight 0.01、追加最多1000/patience30 有工程选择，非全部由原论文确认 |
| 07 | 代理轮数与停止标准 | 教师319/144最佳、均因patience30停止；Random每轮约63.36秒且无早停，1000轮约17.6小时；合成验证停止标准尚待固定 |
| 08 | Ours 主线和效用约束 | A、B、C 尚未选定；保持头部 h、编辑数 m、候选数、参考集与权重均需讨论 |
| 09 | Ours 正式接口与重复请求 | 尚无统一保护策略；若随机响应，需决定缓存和重复查询规则 |
| 10 | Ours 历史过滤、候选完整性与输出长度 | 评价 ranking_api 已有，但实际保护策略的行为还未固定 |
| 11 | 攻击精确中断恢复 | 教师可接续；当前攻击结束才存模型和查询，Random快照77轮无checkpoint。全状态中间保存/恢复优先于下一长任务，尚未实现 |
| 12 | 候选贡献的新颖性与证据门槛 | 相对 GRO、GRAD²/梯度重定向及相关方法的差异须进一步审查；不能以现有基础公式直接认定创新 |
| 13 | 机制诊断与当前攻击的配置一致性 | 上节已列旧配置、AdamW、负采样及 SGD/Adam 差异；暂未修改 |
| 14 | T6/T7 和完整 Top-h-only 攻击 | 未来查询估计、跨代理迁移和同时限制生成/监督的 Top-h-only 尚未实现；仅为研究计划 |
| 15 | None 配对对照与后续复测 | 下一任务已改为 DFME × None/GRO，先得单种子防御差值；多种子等方案完成后再考虑 |

<a id="section-7"></a>

## 可直接交给其他研究者或 AI 的问题

请基于本页现状评审，优先指出数学、方法和公平性上的具体问题，并区分必须修改与可选扩展。当前不要求新增数据集、模型、攻击或大规模实验，也不要求立即实现 A/B/C 全部方向。

1. **贡献是否成立？** A 的相对学习进展目标与 GRO 当前损失扰动、GRAD² 梯度重定向究竟有何可验证的差异？哪些属于已有优化工具，什么结果才能支持推荐排序场景下的方法贡献？
2. **理论与实际更新是否一致？** $J_{\mathrm{LP}}$ 的符号、参考 BCE 和 SGD 余项界是否正确？面对当前 Adam、权重衰减和梯度裁剪，最小的同状态反事实应如何设计？
3. **如何保持效用？** 应用合法列表、头部约束及历史过滤的先后顺序怎么固定？若采用训练时 C1，如何检验最终输出确实恢复了目标列表，而非只优化几个局部 margin？
4. **优先哪条主线？** 在目前只有 GRO 和 A/B 诊断代码的条件下，应先验证 A 的预测性、B 的定向价值，还是构造 C1？请给出一条最小修改路线及其失败判据，不假定 C1 已被选定。
5. **哪些现有代码需要先修？** 旧 phase1 默认、诊断 AdamW/outside_topk 与正式 Adam/source_softmax 的差异，哪些必须统一，哪些可作为明确标注的机制控制？BECOME 已记录的论文/源码冲突是否妨碍防御公平比较？
6. **最小证据是什么？** 在 seed42、ML-1M/SASRec 内，补同攻击 None 对照以及何种单种子机制证据，足以决定是否继续？请避免以单种子测试结果作跨种子稳定性或普遍防御结论，也避免用最终 test 选择超参数。

<a id="section-8"></a>

## 验证与结论边界

本机已有测试覆盖数据边界、排序 API、损失结构、Full Ranking、实际保护输出效用、next_scores 与导出一致性；CPU smoke 覆盖最小训练、GRO、提取、checkpoint 和 JVP 接口。本次上传快照已有真实 GPU 教师验证指标，尚无完成的外部提取或正式防御收益。软件通过不等于理论候选有效。

旧 sampled 和 agr@1 字段用于兼容；主表只输出冻结的五项 Full Ranking 指标。真实 test 仅用于冻结后的独立评价；探索方案使用防御方训练/验证信号，不把外部模型阶段反馈接到真实用户标签。

本轮审查上传快照，将下一默认任务改为 DFME 配对并精简终端显示；未新增 Ours，也未改变既有攻击损失、GRO 目标、每次运行预算和训练轮数。代理恢复与停止规则已列入下一修改计划。其他评审意见可按本页候选方向、问题编号或 TBD 编号归并。
