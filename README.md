# ATRS 主动模型提取防御研究

课题组自有序列推荐模型在公开数据集、授权离线环境中的防御实验。仓库包含独立实现的 SASRec、Random/DFME/BECOME 和 SASRec 上的 GRO 训练迁移，以及理论探针与统一评价。

文档入口为 [00 研究导航](docs/00_INDEX.md)。每篇文件以编号命名，全部可执行命令集中在 [06 运行命令](docs/06_COMMANDS.md)。

| 要查的内容 | 文档 |
| --- | --- |
| 理论推导、候选方法和贡献 | [01 理论与贡献](docs/01_THEORY_AND_CONTRIBUTIONS.md) |
| 论文与代码参数、差异和来源 | [03 配置核查](docs/03_CONFIGURATION_AUDIT.md) |
| 冻结实验设置、主指标与公平性 | [04 实验协议](docs/04_EXPERIMENT_PROTOCOL.md) |
| 数据使用、data-free 边界和预算 | [05 数据与预算](docs/05_DATA_AND_BUDGET.md) |
| 正式服务器执行、本地测试和同步 | [06 全部命令](docs/06_COMMANDS.md) |
| 进度、真实结果和待确认项 | [07 进度](docs/07_PROGRESS.md)、[08 结果](docs/08_RESULTS.md)、[09 待确认](docs/09_IMPLEMENTATION_AND_TBD.md) |

首批正式配置位于 configs/formal，ML-1M + SASRec、1000 条名义序列、三种子。当前可执行 None/GRO × Random/DFME/BECOME，Ours 待研究证据确定。完整计划为 ML-1M/Beauty/Steam 和 SASRec/BERT4Rec 的同构防御比较，扩展入口状态见 09。

Git 只跟踪 data 下 ML-1M、Beauty、Steam 三个文本。正式结果主表为 Full Ranking 的 Recall@10、NDCG@10、clean-reference Agreement@10。checkpoint、查询与详细日志留在 runs，精简结果经审查进入 result。

当前无正式 GPU 防御指标。旧 phase1 配置及 baseline 仍保留，具体与论文的差异、工程参数及 TBD 已集中到 03/09。
