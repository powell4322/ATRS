# 02 排序反馈的反提取理论

<!-- doc-nav:start -->
[00 总索引](../README.md) · [01 待审决策](../REVIEW_DECISIONS.md) · [上一页 01](../REVIEW_DECISIONS.md) · [下一页 03](contributions.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [威胁模型与目标](#section-1)
- [A. 一步学习进展](#section-2)
- [B. 查询生成的反馈效应](#section-3)
- [C. 训练时内化防御](#section-4)
- [代理迁移与鲁棒性](#section-5)
<!-- doc-toc:end -->

<a id="section-1"></a>

## 威胁模型与目标

任务是序列下一物品推荐。攻击者知道合法物品 ID 范围，只能提交前缀并读取有序 Top-$K$ ID。攻击者可自适应分配预算，无目标训练数据、真实人气、logits、梯度、embedding 或目标参数。防御方可用自己的训练数据、目标模型和独立内部 Student。令 $\mathbb A_B$ 为预算 $B$ 内的攻击策略，$\mathcal P$ 为合法排序保护策略。

$$
\min_{\mathcal P}\ \sup_{\mathcal A\in\mathbb A_B} E(g_{\mathcal A}^{\mathcal P})
\qquad\mathrm{s.t.}\qquad U(F_{\mathcal P})\ge U(f_{\theta_0})-\epsilon.
$$

$E$ 分别取代理真实推荐效用和排序保真度。面向保护 API 的 Agreement 与相对 clean teacher 的 Agreement 对应不同问题，应各自注明参照。全局目标的安全性通过有限攻击上的实验评估。

设 $\Omega(x)$ 中的列表均恰有 $K$ 个唯一合法 ID。头部硬约束为 $\tilde R_{1:h}=R_{1:h}$。用相同候选集合直接计算列表指标时，这精确保持 $k\le h$ 的截断效用。若先在未过滤的 API 列表应用保护，离线评价再移除历史物品，尾部可补进前 $h$，需另测效用。软约束可用折扣相关性损失 $C_U(R,\tilde R;x)\le \epsilon_x$。合法编辑包含不编辑、尾部相邻交换及尾部成员替换。

<a id="section-2"></a>

## A. 一步学习进展

### 当前蒸馏损失与一步学习效果

令 $s_H=0,\ s_A=1-2\psi,\ s_B=-0.5+\psi$，可行列表 $R_A=(H,A), R_B=(H,B)$ 均保持同一头部。用 margin 1 的相邻 hinge，在 $\psi=0$ 得到下表。参考任务损失 $V(\psi)=\frac12(\psi-1)^2$，一步 SGD 学习率 $\eta=0.1$。

| 列表 | 当前 intra loss | 梯度 | 更新后 $\psi$ | 更新后参考损失 |
| --- | ---: | ---: | ---: | ---: |
| $R_A$ | 2 | −2 | 0.2 | 0.320 |
| $R_B$ | 0.5 | 1 | −0.1 | 0.605 |

最大化当前蒸馏损失选择 $R_A$，它令参考损失从 0.5 降至 0.320。这个反例否定了两个目标的一般等价性，适用范围为这个 intra-list 损失和合法列表空间。完整 GRO 与真实数据上的预测能力由 T2 和端到端对照测量。

### 相对原始排序的一步效应

记 $V(\psi)=\mathbb E_{\mathcal D_{\mathrm{ref}}}\mathcal L_{\mathrm{rec}}(h_\psi(x),y)$，参考数据来自防御者训练集。令 $v=\nabla_\psi V$ 与 $g_R=\nabla_\psi\ell(x,R)$。

$$
J_{\mathrm{exact}}(\tilde R)=V(\psi-\eta g_{\tilde R})-V(\psi-\eta g_R),\qquad
J_{\mathrm{LP}}(\tilde R)=v^\top(g_R-g_{\tilde R}).
$$

在一阶近似中，$J_{\mathrm{LP}}>0$ 对应保护后的参考收益相对下降。参考损失仍可能下降、保持或上升，其一阶变化为 $-\eta v^\top g_{\tilde R}$。

若 $V$ 的梯度在 $\psi$ 和相关更新点的凸包内 $L$-Lipschitz，则对两个更新分别用 smoothness 界可得

$$
J_{\mathrm{exact}}\ \ge\
\eta J_{\mathrm{LP}}-\frac{L\eta^2}{2}
(\lVert g_R\rVert^2+\lVert g_{\tilde R}\rVert^2).
$$

因此 $J_{\mathrm{LP}}> L\eta(\lVert g_R\rVert^2+\lVert g_{\tilde R}\rVert^2)/2$ 足以保证 $J_{\mathrm{exact}}>0$。令 $\Delta g=g_{\tilde R}-g_R$，沿两更新点连线积分，

$$
J_{\mathrm{exact}}=-\eta\int_0^1\nabla V(\psi-\eta(g_R+t\Delta g))^\top\Delta g\,dt,\qquad
|J_{\mathrm{exact}}-\eta J_{\mathrm{LP}}|\le
\frac{L\eta^2}{2}\lVert\Delta g\rVert(\lVert g_R\rVert+\lVert g_{\tilde R}\rVert).
$$

第二个界利用梯度 Lipschitz 性和 $\lVert g_R+t\Delta g\rVert\le(1-t)\lVert g_R\rVert+t\lVert g_{\tilde R}\rVert$。以上为同一内部代理的局部 SGD 性质。AdamW 的有效更新依赖当前梯度、动量和权重衰减，诊断时应固定同一个优化器状态再分别应用两个候选更新。

### 分数空间投影及局部编辑

设 $a_R=\nabla_s\ell(s_\psi(x),R)$，$w=J_{s_\psi(x)}v$。链式法则给出

$$
J_{\mathrm{LP}}=w^\top(a_R-a_{\tilde R}).
$$

完整 $w$ 是一次 JVP，可在同一查询的候选之间复用。只保留输出层梯度的投影遗漏编码器路径，并且 SASRec 的 tied item embedding 同时参与输入和输出。量化近似误差使用 T4。

若相邻 hinge 项全部严格激活、同权重，则 intra loss 的梯度为 $(\nabla s_{r_K}-\nabla s_{r_1})/(K-1)$。保留首尾的置换在编辑前后都满足该条件时，intra 梯度完全相同。部分激活时只累计激活边，边界铰点依实现次梯度处理。Inter-list 的正负项配对、负样本和值域必须单独检查。对固定负集合的 Plackett–Luce 形式，设相邻 $i,j$ 后部和固定负候选的指数和为 $Z$。交换 $i,j$ 的损失增量是 $\log(e^{s_i}+Z)-\log(e^{s_j}+Z)$，其沿 $w$ 的方向导数可用共享后缀和增量计算。其他权重、负采样规则、pairwise logistic 或 rank-derived KL 需重新推导 $a_R$ 的编辑变化。

<a id="section-3"></a>

## B. 查询生成的反馈效应

令 $q(i\mid x,R)$ 为排序响应给出的下一物品条件分布。以 clean 下一步监督估计 $c_\psi(x')=v^\top\nabla_\psi\ell(x',R^0(x'))$，定义

$$
C_\psi(x,R)=\sum_i q(i\mid x,R)c_\psi(x\oplus i),\qquad
J_{\mathrm{query}}=C_\psi(x,R)-C_\psi(x,\tilde R).
$$

均匀选列表成员时，以 $j$ 替换 $i$ 的边际值为 $[c_\psi(x\oplus i)-c_\psi(x\oplus j)]/K$。若蒸馏梯度在局部光滑且有界，则两步 SGD 有

$$
\psi_2=\psi-\eta(g_0+g_1)+O(\eta^2),\qquad
V(\psi_2)=V(\psi)-\eta v^\top(g_0+g_1)+O(\eta^2).
$$

在固定局部状态、下一步使用 clean 监督、相同步长时，对下一查询取期望得到一阶相对效应 $\eta(J_{\mathrm{LP}}+J_{\mathrm{query}})$。更一般的候选目标 $J_{\mathrm{LP}}+\gamma J_{\mathrm{query}}$ 用 $\gamma$ 表达对后续查询的权重，由实验选定。DFME 先生成再蒸馏，这个推导只描述两个前缀的局部学习价值。下一步同样受保护及 BECOME 的预算反馈均需要扩展模型。

对于同一前缀，成员不变的重排保持均匀条件分布。替换 $m$ 项的单步 TV 为 $m/K$。从相同初始分布出发，假设每步相同历史上的 TV 均至多 $m/K$，逐步最大耦合得到长度 $T$ 的轨迹 TV 至多 $1-(1-m/K)^T$。对 $c\in[c_{\min},c_{\max}]$，期望价值差的绝对值至多 $(c_{\max}-c_{\min})m/K$。TV 给出变化幅度上界，效应方向取决于被替换物品的后续价值。

<a id="section-4"></a>

## C. 训练时内化防御

C1 在 $\Omega(x)$ 内求 $R'=\arg\max_{\tilde R}J_{\mathrm{LP}}(\tilde R)$，再用 $\mathcal L_{\mathrm{rec}}+\lambda\mathcal L_{\mathrm{def}}+\mu\mathcal L_{\mathrm{preserve}}$ 更新教师。可微 $\mathcal L_{\mathrm{def}}$ 用 margin 约束 $R'$ 的内部顺序，以及 $i\in R',j\notin R'$ 的成员得分差。完整 Top-$K$ 恢复要求同时满足成员和顺序条件。以抽样成员对训练时，需要测量实际输出的一致性及推荐效用。

C2 直接对 $v^\top\nabla_\psi\ell(x,R_\theta(x))$ 加正则，$R_\theta$ 的离散 Top-$K$ 要求处理梯度传递、松弛偏差和稳定性。C3 探索表示层的迁移正则，须用 API 层指标确认其作用。见 [C 可行性](scheme_c_feasibility.md)。

<a id="section-5"></a>

## 代理迁移与鲁棒性

若在公共 $\Omega(x)$ 上 $\sup_R|J_\psi(R)-J_\phi(R)|\le\xi$，内部代理 argmax 在外部代理局部目标上的 regret 至多 $2\xi$。证明先以 $\xi$ 将外部最优值换到内部目标，再用内部最优性，最后以 $\xi$ 换回外部目标。T7 测量可观测代理之间的候选排序一致性、符号一致率和选择 regret。

先测试单 Student，按独立初始化、异构代理、跨损失、跨查询策略及 Top-$h$-only 顺序扩展。多 Student 可比较归一化得分的均值、逐查询最小值及 $\max_{\mathcal P}\min_a\mathbb E_x[\bar J_a(x,\mathcal P)]$。这些目标覆盖预选模拟器，真实自适应攻击的效果仍需测量。
