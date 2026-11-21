# 10 仓库与结果管理

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 09](09_IMPLEMENTATION_AND_TBD.md)

**本页目录**

- [文件职责](#section-1)
- [同步与版本](#section-2)
- [接续与结果复用](#section-3)
- [历史文档迁移](#section-4)

<a id="section-1"></a>

## 文件职责

| 路径 | 用途与同步方式 |
| --- | --- |
| docs/00–10 | 每篇一种功能，带编号索引与页内目录 |
| configs/formal | 正式完整预算及每个 seed，Git 跟踪 |
| configs/gro_first | 当前 GRO 首轮、正常训练轮次和独立 run_root，Git 跟踪 |
| configs/phase1 | 旧 20k 集成实验设置，Git 保留供追溯 |
| src/atrs | 模型、API、攻击、防御、评价和诊断实现，Git 跟踪 |
| setup.sh | 仅安装本项目，复用镜像预装依赖 |
| scripts | 正式启动、结果导出、旧矩阵启动与本机 smoke |
| data/ml-1m.txt、Beauty.txt、Steam.txt | 仅三个冻结数据文件进入 Git，保持字节与 hash |
| runs/formal | 正式 checkpoint、查询集、日志、resolved_config，位于容器项目本地 |
| runs/gro_first | 当前 GRO 首轮 checkpoint、查询和日志，位于容器项目本地 |
| runs/research | 理论诊断原始产物，位于容器项目本地 |
| result/formal | 已验证的每 cell JSON、配置和 manifest，审查后进入 Git |
| result/gro_first | 当前 GRO 首轮已完成 cell 的 JSON 与 manifest，审查后进入 Git |
| result/research | 已审阅的精简诊断 JSON 与原始产物定位，审查后进入 Git |
| result/snapshots | 未完成运行的轻量日志/元数据摘要，注明 valid 与未完成状态，不能当作完整正式 cell |
| paper、.upstream、.audit | 本地论文、固定作者源码和历史核查，Git 忽略 |

<a id="section-2"></a>

## 同步与版本

本地与指定实例使用同一 origin，项目默认位于 ~/workspace/ATRS。源码、配置、文档和已审阅的轻量结果由 Git 管理，checkpoint 和完整查询日志保存在 runs，不进入 Git。同一完整矩阵内的源码、数据和配置身份要一致，运行入口自动记录实际执行版本，无需手动 SHA 操作。

需要改参数或模型时，用新配置、新 run_root，保留旧实验身份。当前以本地修改、Git 同步、指定实例计算为默认流程。账号为课题组共享账号，操作限于指定实例和项目目录，平台资源由用户手动管理。具体命令集中在 06。

已完成、核对过的轻量结果可以直接提交并 push，不必等全部实验结束；未完成运行也可以以 snapshots 的明确状态记录。本轮已将用户 ZIP 的真实摘要与验证效用归档。完整 ZIP、权重和原始查询不进入 Git，下一服务器需要另外恢复到原 run_root。训练副本执行任务时保持源码提交不变，不在同一副本边训练边 pull/commit；代码更新在下一任务前进行。

<a id="section-3"></a>

## 接续与结果复用

正式启动器按现有 checkpoint 接续 Teacher，读取其优化器、scheduler、随机状态和 early-stop 计数。一个攻击 cell 完成后有结果 JSON、Student 和 query 文件，启动器核对源码、配置、数据与这些文件的 hash 后才跳过该格。攻击中断后重启对应 cell。

2026-11-21 快照中四个教师 checkpoint 已在本机验证可复用，resume 不会重复训练已早停的模型。Random 仅有训练日志，不能恢复77轮权重。当前未提供攻击 --resume；新的 epoch 边界全状态保存与恢复需下一轮单独实现和测试。

导出器按配置或命令选择的 cell 审查一致性，支持当前只有 GRO 的结果并保留 clean-reference 身份。按 seed 归档后聚合已完成种子，未执行 None 时等待后续配对比较。

<a id="section-4"></a>

## 历史文档迁移

旧 theory/contributions/A/B/C 合并入 01，related work 合并入 02，paper-to-code、known deviations 和 review 中的配置项合并入 03/09，reproduction/fairness/protocol 合并入 04，data 与预算合并入 05，环境配置、正式运行和本机检查命令集中于 06，implementation status、计划与验证合并入 07/09，结果统一由 08 承载。

旧文件路径由本轮编号文件替代，历史内容仍可通过 Git 版本查看。旧阶段配置与 baseline 实现继续可用。
