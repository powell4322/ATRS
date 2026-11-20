# ATRS 主动模型提取防御研究

课题组自有序列推荐模型在公开数据集、授权离线环境中的防御实验。仓库包含独立实现的 SASRec、Random/DFME/BECOME 和 SASRec 上的 GRO 训练迁移，以及理论探针与统一评价。

文档入口为 [00 研究导航](docs/00_INDEX.md)。每篇文件以编号命名，全部可执行命令集中在 [06 运行命令](docs/06_COMMANDS.md)。

| 要查的内容 | 文档 |
| --- | --- |
| 理论推导、候选方法和贡献 | [01 理论与贡献](docs/01_THEORY_AND_CONTRIBUTIONS.md) |
| 论文与代码参数、差异和来源 | [03 配置核查](docs/03_CONFIGURATION_AUDIT.md) |
| 冻结实验设置、主指标与公平性 | [04 实验协议](docs/04_EXPERIMENT_PROTOCOL.md) |
| 数据使用、data-free 边界和预算 | [05 数据与预算](docs/05_DATA_AND_BUDGET.md) |
| 环境配置、正式运行和本机检查 | [06 运行命令](docs/06_COMMANDS.md) |
| 进度、真实结果和待确认项 | [07 进度](docs/07_PROGRESS.md)、[08 结果](docs/08_RESULTS.md)、[09 待确认](docs/09_IMPLEMENTATION_AND_TBD.md) |

当前首轮配置位于 configs/gro_first，ML-1M + SASRec、1000 条名义序列、正常训练轮次、三种子。用户已确认先完成 GRO × Random/DFME/BECOME，None 的攻击格暂缓，初步改进方案之后确定。基础 clean teacher 仍作为 GRO 预训练和 Agreement 参照。完整计划及扩展入口见 04/09。

Git 只跟踪 data 下 ML-1M、Beauty、Steam 三个文本。正式结果主表为 Full Ranking 的 Recall@10、NDCG@10、clean-reference Agreement@10。指定实例的项目默认放在 ~/workspace/ATRS，复用预装依赖，直接运行正式实验。本机执行软件检查，服务器不做 smoke。checkpoint、查询与日志保存在项目 runs 内。

当前无正式 GPU 防御指标。旧 phase1 配置及 baseline 仍保留，具体与论文的差异、工程参数及 TBD 已集中到 03/09。
