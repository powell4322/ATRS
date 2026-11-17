# 14 仓库审计

<!-- doc-nav:start -->
[00 总索引](../README.md) · [01 待审决策](../REVIEW_DECISIONS.md) · [上一页 13](../KNOWN_DEVIATIONS.md) · [下一页 15](protocol_audit.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [待确认的实现设定](#section-1)
<!-- doc-toc:end -->

复核对象为 ATRS 的统一 ML-1M + SASRec 复现框架及本轮研究入口。复用了本地 `.audit/GRO_DFME_BECOME_AUDIT_2026-10-22.md`、`.upstream` 的 DFME/BECOME 快照和 `paper/` 论文。工作区未找到名为 `Anti_Extraction_Research_Foundation_V1.2.md` 的文件。本轮理论以用户提供的研究建议为输入。复核开始时 `runs/` 下仅有 ML-1M 划分元数据，`result/` 无已发布矩阵。

| 入口 | 复核结果 |
| --- | --- |
| [data.py](../../src/atrs/data.py) `load_split`、`left_pad` | 密集物品 ID、用户块、文件哈希和按行顺序留一。0 仅作 padding。实际 ML-1M 预处理成功 |
| [model.py](../../src/atrs/model.py) `SASRec`、[training.py](../../src/atrs/training.py) `SASWindows` | 因果 mask、相对非 padding 位置、共享 item embedding、训练窗口与负采样仅取 train 数据 |
| [cli.py](../../src/atrs/cli.py) `_fit_teacher`、`_load_teacher` | 原先防御从 clean last 起步、攻击从 clean best 读取。现统一从 validation best 起步，记录 parent SHA、epoch 和 validation 指标。新初始化与 resume 分开 |
| [training.py](../../src/atrs/training.py) `save_checkpoint`、`load_checkpoint` | RNG tensor 恢复到 CPU 后再交给 RNG setter。只加载权重时跳过随机状态恢复。checkpoint 原子替换，记录 early-stop 计数。CUDA 分支由 GPU smoke 验收 |
| [api.py](../../src/atrs/api.py) `RankingOracle`、[attacks.py](../../src/atrs/attacks.py) | 攻击生成只经排序端口。新增每行、累计唯一、缓存和反馈计数。原无缓存分支的唯一前缀计数会被覆盖，现按累计维护 |
| [attacks.py](../../src/atrs/attacks.py) `generate_dfme`、`generate_become`、`pairwise_margins` | 复用原攻击，拆分 hinge 供 T1/T3 使用。Phase I 的顺序、配对方式、loss 权重及采样参数继续按冻结配置执行 |
| [gro.py](../../src/atrs/gro.py) `gro_step` | SASRec 上的 GRO 迁移实现。有推荐 BCE、内部 Student hinge、swap hinge。小目录要求 Top-$K$ 外至少 $K$ 项，入口明确报错。smoke 现在分别断言两侧权重更新 |
| [evaluation.py](../../src/atrs/evaluation.py) `evaluate` | Full / sampled 分开。候选不足 10 的用户用自己的可用候选数计算，修复旧实现取 batch 内最小值造成的 batch-size 差异 |
| [research.py](../../src/atrs/research.py)、[learning_progress.py](../../src/atrs/learning_progress.py)、[feedback_diagnostics.py](../../src/atrs/feedback_diagnostics.py) | 新增 T1、T2–T4、T5 的独立诊断入口。真实推荐数据只用于防御端参考梯度和离线评价。诊断保存完整执行参数、checkpoint 哈希、计数、原始结果和错误 |

<a id="section-1"></a>

## 待确认的实现设定

集中 review 的入口是 [01 待审决策清单](../REVIEW_DECISIONS.md)，其中逐项列出当前值、待定选择、参数依据和代码位置。

- **BECOME 口径。** 冻结配置使用论文方向的 $\beta=0.5$，官方快照内部硬编码 $\beta=1$。原始采样概率、反馈 $K$、分阶段长度、频次更新触发点均有差异。可后续独立跑 source-faithful 口径，用于敏感性检验。
- **GRO 归一化。** 当前两种 hinge 分别取均值，论文写求和。其尺度可影响 swap gradient；本轮沿用统一配置，paper-native 口径需单独冻结。当前 row-wise swap 候选会发生冲突，待记录重复率并通过 C1 完整列表约束处理新方法。
- **DFME 与源代码。** 当前统一 SASRec max length 400，原 DFME ML-1M 为 200。当前负采样严格排除 Top-$K$ 和 pad，官方快照对置零权重做过 softmax。当前达不到源码逐值一致。
- **数据来源。** 原始打分、时间戳、过滤和 ID 映射出处待补。Steam/Beauty 的短用户处理和 BERT4Rec 预处理待定义。
- **公平对照。** GRO 与 continued-clean 具有相同起点及追加 epoch allowance，各自的 validation best 可能在不同步数。若要归因到 swap 机制，再输出等步数 endpoint。正式 Random attack 的查询与蒸馏定义待定。
- **账本与恢复。** 已有汇总计数和保留样本文件。全量逐请求重放、原论文训练流程、攻击中断续跑、合成验证切分仍待实现。当前 formal 攻击按固定 epoch 训练并在 test 输出最终评价。

参见 [协议复核](protocol_audit.md)、[已知差异](../KNOWN_DEVIATIONS.md) 和 [论文到代码](../PAPER_TO_CODE_MAP.md)。
