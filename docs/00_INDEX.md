# 00 研究文档导航

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [下一页 01](01_THEORY_AND_CONTRIBUTIONS.md)

| 编号 | 文档 | 用途 |
| --- | --- | --- |
| 01 | [理论与贡献](01_THEORY_AND_CONTRIBUTIONS.md) | 完整理论推导、A/B/C 候选方案、研究假设与贡献证据 |
| 02 | [相关工作](02_RELATED_WORK.md) | DFME、BECOME、GRO、梯度重定向与可选工作的定位 |
| 03 | [论文配置与代码核查](03_CONFIGURATION_AUDIT.md) | 原论文参数、固定官方代码、当前实现、差异和来源 |
| 04 | [统一实验协议](04_EXPERIMENT_PROTOCOL.md) | 冻结 Setting、指标、权限、矩阵和公平比较规则 |
| 05 | [数据与预算审计](05_DATA_AND_BUDGET.md) | 三个数据文件、原始下载流程、data-free 边界与资源账本 |
| 06 | [全部运行命令](06_COMMANDS.md) | 本地测试、矩池云正式运行、单格接续、结果导出与 Git 同步 |
| 07 | [实验计划与进度](07_PROGRESS.md) | 已完成检查、正式实验进度、机制实验与后续工作 |
| 08 | [实验结果与分析](08_RESULTS.md) | 真实结果、同一攻击下的防御效应、三种子统计 |
| 09 | [实现与待确认项](09_IMPLEMENTATION_AND_TBD.md) | 实现入口、参数优先级、TBD、复现边界与后续修改 |
| 10 | [仓库与结果管理](10_REPOSITORY_AND_SYNC.md) | 文件职责、网盘与 Git 产物、版本和历史方案 |

先核对 03 与 09，按 04 开展防御实验。所有可复制执行的命令集中于 06。第一轮在服务器直接运行 ML-1M + SASRec 的正式 None/GRO 对照，使用完整 1k 名义序列预算。Ours 的最终机制与实现依据研究结果确定。

旧版分散文档的内容已合并到上表，历史版本可由 Git 查看。
