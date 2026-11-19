# 09 实现与待确认项

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 08](08_RESULTS.md) · [下一页 10](10_REPOSITORY_AND_SYNC.md)

**本页目录**

- [已冻结的研究选择](#section-1)
- [当前实现范围](#section-2)
- [参数优先级](#section-3)
- [仍待确认](#section-4)
- [检验边界](#section-5)

<a id="section-1"></a>

## 已冻结的研究选择

主 Setting、五项指标、clean-reference Agreement、1k 名义预算、三个攻击和三种防御见 04。论文确认的 length/dropout/mask/margin 和模型层数/heads 见 03。正式配置独立于保留的旧 phase1 配置。

<a id="section-2"></a>

## 当前实现范围

可运行入口包含 ML-1M/SASRec 的 Teacher、GRO、Random、DFME、BECOME、正式 Full Ranking、checkpoint 接续与结果聚合。旧 AdamW、mean-normalized GRO、严格 Top-K 外负采样和 phase1 行为仍可通过历史配置执行。BERT4Rec、Beauty/Steam 正式入口以及 Ours 尚待实现。

| 功能 | 当前代码 |
| --- | --- |
| 数据与切分 | data.py 的 load_split、SASWindows |
| SASRec 与 BCE | model.py，2-layer/2-head 配置可用 |
| CLI 配置与执行 | cli.py |
| Ranking API 与资源 | api.py |
| 攻击独立逻辑 | attacks.py |
| GRO 联合训练 | gro.py |
| Recall / NDCG / clean Agreement | evaluation.py |
| 理论探针与双视图 | learning_progress.py、feedback_diagnostics.py、research.py |
| 正式执行与结果 | scripts/run_formal.py、scripts/export_results.py |

<a id="section-3"></a>

## 参数优先级

单个正式运行以指定 JSON 为准，日志保存配置 hash 和 resolved_config。CLI 的 device、resume 只控制运行位置和接续。正式模式拒绝 epochs 的临时覆盖，改变训练轮数需形成新配置。配置内的论文明确值优先于历史程序默认值，论文未写出的项由 configuration_sources 指向固定源码或旧配置。

每份正式配置带 seed，分别绑定 run_root。研究探针的独立诊断 seed 不改动教师 seed。默认正式启动器按 42、43、44 执行，单配置执行适合分配不同 GPU 或接续某个 seed。同一个 run_root 的同名任务按串行运行。

<a id="section-4"></a>

## 仍待确认

| 编号 | TBD | 当前处理和影响 |
| --- | --- | --- |
| 01 | 已有文本的原始来源、时间戳与过滤映射 | ML-1M 可按已冻结文本开展内部统一比较，论文需报告现有数据统计 |
| 02 | Steam/Beauty 短用户与重新映射 | 当前有 1805/1706 个短用户，确定派生协议后适配 |
| 03 | BERT4Rec 完整训练/生成/评价接入 | mask probability 已按论文冻结，mask ID 与推理语义需实现并测试 |
| 04 | BECOME 源码逐值等价 | 当前按论文参数重建，alpha/beta/频次/采样与源码冲突保留；批内选择和 RNG 的精确 parity 待核 |
| 05 | BECOME 论文 j 与负采样候选池解释 | 正式暂按源码 30 negatives/positive、source_softmax；纸面解释待作者或进一步证据 |
| 06 | 原论文缺失的训练时长、早停与 GRO 超参数 | 已记录的仓库值用于当前执行，原论文对应值标 TBD |
| 07 | 20 epoch DFME/Random 的训练充分性 | 继承已有固定设置，检查预定训练曲线；改版时统一该攻击的全部防御条件 |
| 08 | Ours 的最终机制、约束和超参数 | A/B/C 是候选，先由理论诊断与正式基线提供证据 |
| 09 | 随机保护接口的缓存/重复查询行为 | 当前冻结 teacher 确定性缓存可用，Ours 随机输出时需重新定义 |
| 10 | Ours 推理输出的历史过滤与长度 | 已提供 ranking_api 评价接口，最终保护列表的协议还需固定 |
| 11 | 攻击中断的精确 resume | 当前重启该 cell，教师可 epoch 接续；完整逐请求重放待实现 |
| 12 | 机制 gate 的统计门槛与超参数搜索范围 | TBD，候选贡献随证据更新 |

<a id="section-5"></a>

## 检验边界

本地测试覆盖的是软件和数学接口，正式防御效果需要实际 GPU 数据。当前源码保留独立评估所需的 clean reference，仅在攻击结束后用于评价。旧的 sampled 指标与 agr@1 字段用于兼容读取，正式主表按 04 的五项指标生成。

新增配置、评价与预算修改的逐项记录在 [03 核查](03_CONFIGURATION_AUDIT.md)；后续用户 review 可直接引用本页 TBD 编号或 03 的参数名称。
