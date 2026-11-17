# 17 理论验证报告

<!-- doc-nav:start -->
[00 总索引](../README.md) · [01 待审决策](../REVIEW_DECISIONS.md) · [上一页 16](../IMPLEMENTATION_STATUS.md) · [下一页 18](../EXPERIMENT_PLAN.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [已推导](#section-1)
- [软件验证记录](#section-2)
- [待用真实数据检验](#section-3)
<!-- doc-toc:end -->

<a id="section-1"></a>

## 已推导

- 一步参考损失与当前 hinge 最优排序可出现反向偏好。固定首尾且全部相邻 hinge 激活时，intra 梯度望远镜消去。
- 局部光滑条件下 LP 有一步 SGD 误差界。完整分数空间 JVP 和参数空间点积等价。条件与证明见 [理论文档](theory.md)。
- DFME 均匀采样时集合替换的单步 TV 为 $m/K$。TV 只约束变化幅度，效用及提取结果需要独立测量。

<a id="section-2"></a>

## 软件验证记录

| 检查 | 观察 |
| --- | --- |
| pytest 和 smoke | 通过。GRO smoke 确认教师、内部 Student 均更新。单元测试复现全激活 intra-hinge 的端点梯度和 BECOME 反馈计数边界 |
| ML-1M 预处理 | 数据哈希与冻结配置一致，输出 6040 用户、3416 物品和 999611 行 |
| 小目录 CPU 端到端 | 两段 clean 训练和 resume，GRO 与 continued-clean，六个攻击 cell 均完成。Parent hash 一致，反馈命中缓存 |
| T1、T2–T4、T5 CLI | 合成数据入口通过。T4 完整 JVP 与参数反传最大绝对差约 $3.6\times10^{-7}$。T5 toy 两路各 12 次唯一请求，四格训练步数相同，监督交叉复用对应的前缀 |

这些检查来自 CPU 软件验证，未用于估计推荐或反提取效果。在矩池云上先确认 CUDA smoke 和 Phase I 真实数据关键路径。JVP 延迟需单独在实际 CUDA 环境测量。

<a id="section-3"></a>

## 待用真实数据检验

| 假设 | 待检验证据 |
| --- | --- |
| H1 | LP 相对 Loss/Gradient-deviation 在多个训练阶段的相关性和 regret；同效用随机控制下的外部代理提取效果 |
| H2 | T5 轨迹效应与交互效应的方向、稳定性；T6 对未来提取收益的预测 |
| H3 | 从训练输出中恢复目标排序和头部效用，比较 C1、GRO 与 continued-clean |

当前无 ML-1M 正式基线、CUDA 运行、跨代理或多种子实验结果。真数据运行顺序和命令见 [矩池云手册](../MATPOOL_RUN.md)。
