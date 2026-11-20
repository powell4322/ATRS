# 07 实验计划与进度

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 06](06_COMMANDS.md) · [下一页 08](08_RESULTS.md)

**本页目录**

- [本阶段顺序](#section-1)
- [已完成的软件与资料工作](#section-2)
- [首批正式矩阵](#section-3)
- [理论机制实验与阶段决策](#section-4)

<a id="section-1"></a>

## 本阶段顺序

1. 完成论文配置、固定作者源码和当前代码的逐项核查，冻结 Full Ranking 与 clean-reference Agreement。
2. 本地执行必要的软件测试与小目录 smoke，验证 Random/DFME/BECOME、GRO、checkpoint、scheduler 与导出接口。
3. 按用户确认先完成 ML-1M + SASRec 的 GRO，1000 条名义序列、正常轮次，逐步完成三种子。None 的攻击格暂缓，基础教师仍需训练。
4. 按攻击分别检查 Target 效用、Surrogate 指标、Agreement 与预算账本，再依据理论诊断推进 Ours。
5. Ours 固定后完成同协议的对应 cell。数据和模型适配完成后再执行已冻结的 Beauty/Steam 与 BERT4Rec。

正式主矩阵维持 04 的范围。理论机制实验是研究诊断，按各自科学问题记录，不要求把每个候选都加入主矩阵。

最新部署流程使用指定实例的 ~/workspace/ATRS 容器本地目录，复用预装 PyTorch，通过 SSH 和 tmux 运行。首次部署在服务器显式执行 CUDA smoke，再开始正式任务。轻量结果取回本地后进入 Git，大产物经 SCP 和 SHA-256 校验备份，实例由用户手动释放。

<a id="section-2"></a>

## 已完成的软件与资料工作

| 项目 | 状态 |
| --- | --- |
| DFME / BECOME 论文表格与实现段落 | 已核查 |
| 作者 Git 版本 | 已核对固定 HEAD 与远端一致 |
| 三数据文件 hash、密集 ID 与用户长度 | 已扫描 |
| ML-1M 正式配置 | 已生成，纸面参数与来源在 03 |
| 主评价 clean-reference / Recall / protected-output 接口 | 已接入，12 项本地单元测试与 smoke 通过 |
| 正式服务器入口 | 完整配置直接执行，可接续教师，复用身份一致的已完成 cell |
| 服务器环境初始化 | setup.sh 检查预装环境、安装本项目并调用现有 preprocess |
| 正式 GPU 实验 | pending，仓库中尚无正式指标 |

本地临时目录完成了正式配置 schema 的六格 CLI 验证，覆盖 Adam、warmup checkpoint 接续、Random/DFME/BECOME 与 paper-sum GRO、clean-reference 指标及导出。使用的是本地玩具目录，产物已在测试结束后丢弃。服务器按完整真实数据直接运行正式配置。

<a id="section-3"></a>

## 首批正式矩阵

下表每项各有 Random、DFME、BECOME 三格。

| Seed | None | GRO | Ours |
| --- | --- | --- | --- |
| 42 | 暂缓 | pending | 稍后确定 |
| 43 | 暂缓 | pending | 稍后确定 |
| 44 | 暂缓 | pending | 稍后确定 |

真实完成后由日志与结果 manifest 更新进度，数值统一放入 [08 结果与分析](08_RESULTS.md)。

gro_first 的基础教师和 GRO 最大 1000 epochs，patience=30。Random/DFME 固定 1000 epochs，BECOME 保持 20/30 的阶段训练。日志已补充外部代理的每 epoch 损失、阶段、训练步数与时间。单独完成 GRO 后即可导出，不依赖 None 结果文件。

本地还完成了当前启动器的临时数据演练，确认会训练基础教师、跳过全部 None 攻击格、完成 GRO 三格并导出，重复启动会复用已完成结果。下一项打分改为只投影最后一个隐状态，测试确认其分数和参数梯度与完整 forward 的最后位置一致。

<a id="section-4"></a>

## 理论机制实验与阶段决策

| 编号 | 科学问题 | 证据和下一步 |
| --- | --- | --- |
| G0 | 正式对照可信度 | checkpoint 同源、无真实标签进入攻击、None 可测提取、资源账本完整 |
| T1 | 排序知识位次价值 | 固定查询下的 Top-k、位次区间、intra/inter；完整 Top-h-only 还需独立生成策略 |
| T2 / G1 | Loss 与 LP 是否预测一步参考损失 | Pearson/Spearman、候选 regret、最优候选一致率、Exact 反事实 |
| T3 | 相邻 hinge 的梯度结构 | 激活边、首尾消去、intra/inter 梯度变化 |
| T4 | 完整投影与近似 | 参数反传、JVP、输出层投影的误差和耗时 |
| G2 | 定向编辑是否有效 | 同效用和同编辑数下，A-LP 与随机、Loss、Gradient-deviation 比较 |
| T5 / G3 | 轨迹效应是否独立 | clean/protected generation × clean/protected supervision 四格 |
| T6 | 哪种查询价值可预测后续收益 | 人气/共现、状态相似、梯度价值和真实短期收益 |
| T7 / G4 | 局部编辑价值能否迁移 | 独立初始化同构代理为优先，异构只作可选扩展 |
| G5 / C1 | 计算是否可部署 | 缓存、上下文近似，必要时学习合法防御排序 |

每个 gate 的统计阈值和样本规模为 TBD。若 A、B 中只有一支显示稳定信号，沿该支推进。若精确价值有效但近似无效，先改进估计。若匹配随机编辑持续更好，复查候选空间、参考损失和假设。
