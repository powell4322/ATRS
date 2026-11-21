# 00 研究文档导航

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [下一页 01](01_THEORY_AND_CONTRIBUTIONS.md)

| 编号 | 文档 | 用途 |
| --- | --- | --- |
| 01 | [理论与贡献](01_THEORY_AND_CONTRIBUTIONS.md) | 完整理论推导、A/B/C 候选方案、研究假设与贡献证据 |
| 02 | [相关工作](02_RELATED_WORK.md) | DFME、BECOME、GRO、梯度重定向与可选工作的定位 |
| 03 | [论文配置与代码核查](03_CONFIGURATION_AUDIT.md) | 原论文参数、固定官方代码、当前实现、差异和来源 |
| 04 | [统一实验协议](04_EXPERIMENT_PROTOCOL.md) | 冻结 Setting、指标、权限、矩阵和公平比较规则 |
| 05 | [数据与预算审计](05_DATA_AND_BUDGET.md) | 三个数据文件、原始下载流程、data-free 边界与资源账本 |
| 06 | [环境配置与运行命令](06_COMMANDS.md) | 简单环境安装、正式 GRO 运行与本机检查 |
| 07 | [实验计划与进度](07_PROGRESS.md) | 当前快照、早停与训练开销、下一完整任务和机制路线 |
| 08 | [实验结果与分析](08_RESULTS.md) | 单种子真实结果、同一攻击下的防御效应，后续再考虑复测 |
| 09 | [创新方案、代码现状与待确认项](09_IMPLEMENTATION_AND_TBD.md) | 对外评审摘要、候选贡献、已改代码、未实现防御与讨论问题 |
| 10 | [仓库与结果管理](10_REPOSITORY_AND_SYNC.md) | 目录职责、版本和结果复用 |

先核对 03 与 09，按 04 开展防御实验。所有可复制执行的命令集中于 06。2026-11-21 上传快照中的 clean/GRO 教师已完成，下一完整任务优先 ML-1M + SASRec、seed42 的 DFME × None/GRO 配对。1k 名义预算不变，代理轮数需按 07 审阅；Ours、Random 补充实验及多种子按机制证据分阶段安排。

旧版分散文档的内容已合并到上表，历史版本可由 Git 查看。
