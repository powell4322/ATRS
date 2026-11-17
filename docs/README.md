# 00 ATRS 研究文档

<!-- doc-nav:start -->
[00 总索引](README.md) · [01 待审决策](REVIEW_DECISIONS.md) · [下一页 01](REVIEW_DECISIONS.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [从哪里开始](#section-1)
- [编号总表](#section-2)
- [当前状态](#section-3)
<!-- doc-toc:end -->

<a id="section-1"></a>

## 从哪里开始

- 集中 review 协议、指标、模型与参数，打开 [01 待审决策清单](REVIEW_DECISIONS.md)。可以直接回复决策编号，确认后同步代码与配置。
- 在本地和矩池云同步代码、修改和结果，打开 [20 Git 工作流](GIT_WORKFLOW.md)。
- 租卡后的环境验收与分阶段命令，打开 [19 矩池云运行手册](MATPOOL_RUN.md)。

<a id="section-2"></a>

## 编号总表

编号出现在文档标题、导航和本表。保留原文件路径，原有链接继续可用。每页可返回总索引与待审清单，多节文档有页内目录。

| 编号 | 分类 | 文档 |
| --- | --- | --- |
| 00 | 导航 | 本页总索引 |
| 01 | Review | [待审决策清单](REVIEW_DECISIONS.md) |
| 02 | 理论 | [理论基础与威胁模型](research/theory.md) |
| 03 | 贡献 | [候选贡献与创新点](research/contributions.md) |
| 04 | 相关工作 | [论文定位与基线范围](RELATED_WORK.md) |
| 05 | 相关工作 | [论文到代码](PAPER_TO_CODE_MAP.md) |
| 06 | 多方案研究 | [研究计划与代码实施顺序](research/research_experiment_plan.md) |
| 07 | 多方案研究 | [Scheme A 实验](research/scheme_a_experiments.md) |
| 08 | 多方案研究 | [Scheme B 实验](research/scheme_b_experiments.md) |
| 09 | 多方案研究 | [Scheme C 可行性](research/scheme_c_feasibility.md) |
| 10 | 协议 | [统一复现协议](REPRODUCTION_PROTOCOL.md) |
| 11 | 协议 | [数据协议](DATA_PROTOCOL.md) |
| 12 | 协议 | [基线公平性](BASELINE_FAIRNESS.md) |
| 13 | 审计 | [已知差异](KNOWN_DEVIATIONS.md) |
| 14 | 审计 | [仓库审计](audits/repository_audit.md) |
| 15 | 审计 | [协议审计](audits/protocol_audit.md) |
| 16 | 实现与验证 | [实现状态](IMPLEMENTATION_STATUS.md) |
| 17 | 实现与验证 | [理论验证报告](research/theory_validation_report.md) |
| 18 | 运行 | [完整基线计划](EXPERIMENT_PLAN.md) |
| 19 | 运行 | [矩池云运行](MATPOOL_RUN.md) |
| 20 | 运行 | [Git 同步与结果回传](GIT_WORKFLOW.md) |
| 21 | 运行 | [Windows 4090 运行](WINDOWS_4090_RUN.md) |
| 22 | 仓库 | [目录与结果生命周期](REPOSITORY_LAYOUT.md) |
| 23 | 结果 | [Phase I 基线结果](RESULTS.md) |

<a id="section-3"></a>

## 当前状态

当前任务为 ML-1M + SASRec 上的统一基线和小规模机制诊断。本地软件检查已通过，正式 GPU 基线结果仍为 pending。待定研究选择集中在 01，已验证事实和源码位置在 14–17。
