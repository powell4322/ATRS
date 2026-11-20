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
| scripts | 正式启动、结果导出、旧矩阵启动与本地 smoke |
| data/ml-1m.txt、Beauty.txt、Steam.txt | 仅三个冻结数据文件进入 Git，保持字节与 hash |
| runs/formal | 正式 checkpoint、查询集、日志、resolved_config，保存在网盘 |
| runs/gro_first | 当前 GRO 首轮 checkpoint、查询和日志，保存在网盘 |
| runs/research | 理论诊断原始产物，保存在网盘 |
| result/formal | 已验证的每 cell JSON、配置和 manifest，审查后进入 Git |
| result/gro_first | 当前 GRO 首轮已完成 cell 的 JSON 与 manifest，审查后进入 Git |
| result/research | 已审阅的精简诊断 JSON 与原始产物定位，审查后进入 Git |
| paper、.upstream、.audit | 本地论文、固定作者源码和历史核查，Git 忽略 |

<a id="section-2"></a>

## 同步与版本

本地与矩池云使用同一 origin。先提交源码、配置和文档并 push，服务器 pull 后在固定提交运行。跑完后只提交审查过的精简结果与分析，checkpoint 和完整查询日志继续放网盘。同一完整矩阵内的源码、数据和配置身份要一致，结果提交有自己的 SHA，JSON 内仍记录实际执行源码的 SHA。

本地与云端都改代码时，可使用 codex/ 前缀的实验分支。同一个分支先提交本端改动再同步另一端。需要改参数或模型时，用新配置、新 run_root，保留旧实验身份。具体命令全部集中在 06。

<a id="section-3"></a>

## 接续与结果复用

正式启动器按现有 checkpoint 接续 Teacher，读取其优化器、scheduler、随机状态和 early-stop 计数。一个攻击 cell 完成后有结果 JSON、Student 和 query 文件，启动器核对源码、配置、数据与这些文件的 hash 后才跳过该格。攻击中断后重启对应 cell。

导出器按配置或命令选择的 cell 审查一致性，支持当前只有 GRO 的结果并保留 clean-reference 身份。按 seed 归档后聚合已完成种子，未执行 None 时等待后续配对比较。正式实验日志、checkpoint 和数据在释放实例前应确认仍位于网盘挂载路径。

<a id="section-4"></a>

## 历史文档迁移

旧 theory/contributions/A/B/C 合并入 01，related work 合并入 02，paper-to-code、known deviations 和 review 中的配置项合并入 03/09，reproduction/fairness/protocol 合并入 04，data 与预算合并入 05，所有服务器和 Git 命令合并入 06，implementation status、计划与验证合并入 07/09，结果统一由 08 承载。

旧文件路径由本轮编号文件替代，历史内容仍可通过 Git 版本查看。旧阶段配置与 baseline 实现继续可用。
