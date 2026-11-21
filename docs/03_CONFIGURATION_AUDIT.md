# 03 论文配置与代码核查

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 02](02_RELATED_WORK.md) · [下一页 04](04_EXPERIMENT_PROTOCOL.md)

**本页目录**

- [论文已经确认的配置](#section-1)
- [论文、官方代码与正式配置差异](#section-2)
- [未完整公开参数的来源](#section-3)
- [当前代码映射](#section-4)

核查对象为本地 DFME 论文 §5.1 / Table 3 和 BECOME 论文 §5.1 / Table 2、Table 3。已逐页检查 DFME PDF 第 9 页和 BECOME PDF 第 7 页的表格与段落。官方 Git 快照 HEAD 亦与本地固定版本一致。

| 来源 | 固定版本与入口 |
| --- | --- |
| DFME | 47f841b708eb25d3aa996aefcbdfba6b713741b3，utils.py、distill.py、trainer/distiller.py、datasets |
| BECOME | 83355ef723e16ca826d013c23938f51f0e0b453e，相同子模块及 trainer/utils.py 的 random_len |
| GRO | 论文 Eq. (4)–(6)，BERT4Rec 设置；当前代码为独立 SASRec 迁移实现，官方源码等价性 TBD |
| ATRS 历史配置 | configs/phase1/ml1m_sasrec_seed42.json，保留以供追溯 |
| ATRS 正式配置 | configs/formal/ml1m_sasrec_seed42.json、seed43.json、seed44.json |
| 当前已训练教师的配置 | configs/gro_first/ml1m_sasrec_seed42.json 保持不变以复用 checkpoint；当前启动器选择 DFME × None/GRO，seed43/44 保留但不执行 |

来源链接为 [DFME 论文](https://arxiv.org/abs/2109.01165)、[DFME 固定代码](https://github.com/Yueeeeeeee/RecSys-Extraction-Attack/tree/47f841b708eb25d3aa996aefcbdfba6b713741b3)、[BECOME 论文](https://doi.org/10.1145/3746252.3761032)、[BECOME 固定代码](https://github.com/Loche2/BECOME/tree/83355ef723e16ca826d013c23938f51f0e0b453e)、[GRO 论文](https://arxiv.org/abs/2310.16335)。

<a id="section-1"></a>

## 论文已经确认的配置

下表按 ML-1M、Steam、Beauty 排列，避免 BECOME 文本的 ML-1M、Beauty、Steam 顺序导致转录错误。

| 参数 | ML-1M | Steam | Beauty | 依据 |
| --- | ---: | ---: | ---: | --- |
| 模型与合成序列长度 | 200 | 50 | 50 | DFME §5.1.3；BECOME §5.1.5 |
| Dropout | 0.1 | 0.2 | 0.5 | DFME Table 3；BECOME §5.1.5 |
| BERT4Rec mask probability | 0.2 | 0.2 | 0.6 | DFME Table 3；BECOME Table 2 |
| Ranking margin | 0.75 | 0.5 | 0.5 | 两篇配置表 |
| Negative margin | 1.5 | 1.0 | 0.5 | 两篇配置表 |
| SASRec / BERT4Rec layers | 2 | 2 | 2 | 两篇配置表 |
| SASRec / BERT4Rec heads | 2 | 2 | 2 | 两篇配置表 |
| Optimizer | Adam | Adam | Adam | 两篇 §5.1 |
| Learning rate | 0.001 | 0.001 | 0.001 | 两篇 §5.1 |
| Weight decay | 0.01 | 0.01 | 0.01 | 两篇 §5.1 |
| Batch size | 128 | 128 | 128 | 两篇 §5.1 |
| DFME linear warmup | 100 steps | 100 steps | 100 steps | DFME §5.1.3 |

BECOME 未明确 warmup。其 §5.1.5 给出 rho_init=0.1、N=8、Gamma=0.5、alpha=0.8、beta=0.5。DFME Table 4 主实验采用 5k 序列，BECOME Table 3 在相同架构和 B=1k 下比较 Random、DFME、BECOME。统一防御协议采用后者的 1k 名义序列数。

<a id="section-2"></a>

## 论文、官方代码与正式配置差异

| 项目 | 原论文 | 作者固定代码 / ATRS 历史实现 | 正式处理与状态 |
| --- | --- | --- | --- |
| ML-1M length | 200 | DFME 200，BECOME 400，ATRS 400 | 已修改正式模型长度为 200，生成长度 200 |
| Steam / Beauty length | 50 / 50 | DFME 50/50，BECOME 100/100 | 已确认论文值，正式扩展入口 TBD |
| Steam mask probability | 0.2 | 两仓库 utils.py 为 0.4 | 已确认冲突，最终 Setting 按论文 0.2，BERT 实现 TBD |
| 优化器 | Adam | 两仓库 set_template 为 AdamW，ATRS AdamW | 已修改正式入口为 Adam，保留旧 AdamW |
| DFME warmup | 100 | set_template 与 distill.py 关闭 warmup | 正式开启 100-step linear warmup；后续 linear decay 依据原 scheduler 函数 |
| BECOME warmup/scheduler | 未明确 | warmup 关闭，StepLR gamma=1，相当于恒定 LR | 正式保留恒定 LR 和 0 warmup，注明源码依据 |
| ML-1M DFME margins | 0.75/1.5 | 原函数默认 0.5/0.5，ATRS 同默认 | 已修改正式 DFME 为论文值 |
| API / evaluation | Top-100，DFME 明确 sampled 101 | 旧 ATRS 同时输出 full/sample | 按冻结协议只在正式表输出 Full Ranking |
| Agreement 参照 | 作者模型与对应 Target | 旧 GRO cell 参照 GRO teacher | 已修改正式主 Agreement 统一参照 clean Target |
| nominal budget | DFME 5k，BECOME 1k | 上游交互输入 M，ATRS 100/166 条且 20k cap | 已修改正式全部 M=1000，取消旧硬 cap，分开报告真实账本 |
| BECOME rho / phases | 0.1 / 8 | 源码 initial+8=9 轮，ATRS 0.2+4 phase | 已修改正式 initial+8，rho=0.1 |
| BECOME alpha / beta | 0.8 / 0.5 | 源码硬编码 0.75 / 1，ATRS 0.5 / 0.5 | 正式采用论文 0.8/0.5，差异保留在配置与报告 |
| BECOME 频次 | 统计响应列表全部物品，Eq.16 | 源码只累计被选物品；旧 ATRS 在抽样事件更新列表 | 正式按新响应累计全列表，包括终端，缓存响应避免重复累加 |
| BECOME 采样概率 | Eq.17–18 正随机排名权重与逆频次的加权采样 | 源码两次 softmax，硬编码 alpha | 正式按论文直接正权重归一化抽样；源码精确输出一致性 TBD |
| BECOME phase 正态分布 | 给公式，未给 mu/sigma | random_len 默认 N(0,1)，abs/round 后分配 | 正式使用 0/1 和 round，总增量守恒；旧实现 1/0.2 与 floor 保留为默认旧路径 |
| BECOME 反馈 | Eq.8 未唯一明确 D | 源码 synthetic terminal Agr@10，旧 ATRS Top-100 | 正式改为 Top-10，反馈经过同一个 ranking oracle |
| BECOME 选择范围 | Eq.9 对序列集合排序 | 源码每生成批内筛选，旧 ATRS 全局 | 当前全局低一致性选择遵循论文描述，源码批内完全等价性 TBD |
| BECOME training | 先初始，再阶段生成/蒸馏 | 源码每轮 20，最后 30 epochs | 正式 8 次追加阶段、每阶段 20、最后 30，初始阶段 20 |
| BECOME synthetic holdout | 阶段反馈用合成数据 | 原 loader 终端作 valid，旧 ATRS 终端也进训练 | 已修改正式终端作为该阶段 holdout，只在成为非终端后进入训练 |
| DFME / BECOME negative sampler | 负样本目标的论文描述 | 源码 Top-K 权重置零再 softmax，有放回；Top-K/pad 仍有正概率 | 正式显式 source_softmax 复现作者分布，旧严格 outside_topk 入口保留 |
| BECOME negative 数量 | Eq.22 的 j 规则与候选池存在歧义 | 源码每正例 30 个；旧 ATRS 用 catalog 推导 j | 正式固定 30 取自源码，paper-native j 的解释 TBD |
| GRO student loss 尺度 | Eq.4 两项求和 | 旧 ATRS 分别 mean | 已修改正式为 item-sum 后 batch-mean，旧 mean 入口保留 |

以上选择形成论文参数优先、未公开项追溯源码/已有配置的重建方案。每一攻击的生成和损失机制独立，同一攻击跨防御使用同一套设置。对冲突项的固定选择不构成与作者源码逐值等价的声明。

<a id="section-3"></a>

## 未完整公开参数的来源

| 参数 | 当前执行值 | 来源和验证边界 |
| --- | --- | --- |
| Embedding dimension | 64 | 两官方 utils.py set_template，当前 SASRec 配置 |
| Teacher 最大 epochs | 1000 | 两官方 set_template，沿用现有值 |
| Teacher patience | 30 | 现有 ATRS 配置，论文与官方训练循环未给相同 early stopping |
| GRO 追加 epochs | 最多 1000，patience=30 | 当前用户要求正常轮次；论文继续训练至收敛，1000 为本项目上限，原论文具体轮数 TBD |
| GRO 追加训练 scheduler / warmup | constant / 0 | 现有 ATRS 追加训练行为，在正式 JSON 单独显式记录 |
| Random / DFME Surrogate epochs | 1000 | 当前 gro_first 恢复作者模板的正常轮次，原论文未明确数值 |
| Surrogate checkpoint | 固定训练后的末权重 | 沿用现有实现，选择过程不读取真实 valid/test |
| GRO rank/negative/swap margin | 0.5/0.5/0.5 | 现有 ATRS，GRO 原始超参数精确对应 TBD |
| GRO swap_weight | 0.01 | 现有 ATRS，保持可追溯工程选择 |
| Sliding fraction | 0.5 | 官方 utils.py，窗口边界与上游存在细节差异 |
| norm/bias weight decay 分组、Adam eps | 分组无衰减，eps=1e-8 | 沿用当前实现，两源码的 Adam/AdamW 分支也有分组和 eps 差异 |
| 种子 | 当前仅 42；43、44 保留 | 项目执行编号；探索阶段单种子，多种子复测延后 |
| Ours 机制与参数 | TBD | 等待研究证据，当前不生成 Ours 指标 |

旧 configs/formal 的 20-epoch 方案保留供追溯。当前 gro_first 的训练轮次独立记录在 configuration_sources，同一攻击跨未来防御条件保持这一轮次规则。真实 test 数值不作为调参依据。

2026-11-21上传快照确认：教师与 GRO 已因 patience30 在349/174轮停止，最佳319/144；Random代理无早停，1000轮成本明显高于教师。该证据不支持直接将教师硬截到300，也不能只凭代理 loss 平台改正式停止标准。独立预算诊断和下一任务计划见 [07](07_PROGRESS.md)。

<a id="section-4"></a>

## 当前代码映射

| 功能 | 入口 |
| --- | --- |
| 读取配置、教师、攻击与独立最终评价 | [cli.py](../src/atrs/cli.py) 的 _configuration、_fit_teacher、_run_attack |
| 各自生成 / 蒸馏 | [attacks.py](../src/atrs/attacks.py) 的 generate_random、generate_dfme、generate_become、pairwise_loss |
| 优化器与 warmup 接续 | [training.py](../src/atrs/training.py) 的 source_optimizer、linear_warmup_decay、save_checkpoint |
| 主指标 / 保护输出效用 | [evaluation.py](../src/atrs/evaluation.py) 的 evaluate、ranking_api 参数 |
| GRO Eq.4–6 | [gro.py](../src/atrs/gro.py) 的 gro_step 和 loss_normalization |
| 正式资源计数 | [api.py](../src/atrs/api.py) 的 QueryCounts、RankingOracle |
| 正式完整运行 / 聚合 | [run_formal.py](../scripts/run_formal.py)、[export_results.py](../scripts/export_results.py) |
