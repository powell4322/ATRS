# 04 相关工作与基线范围

<!-- doc-nav:start -->
[00 总索引](README.md) · [01 待审决策](REVIEW_DECISIONS.md) · [上一页 03](research/contributions.md) · [下一页 05](PAPER_TO_CODE_MAP.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [序列推荐模型提取](#section-1)
- [主动防御与研究切入点](#section-2)
- [Sim4Rec 的量化比较范围](#section-3)
- [Possible reviewer response](#section-4)
<!-- doc-toc:end -->

<a id="section-1"></a>

## 序列推荐模型提取

- **DFME，RecSys 2021，Yue 等。** 攻击用 Top-K 排序自回归地生成合成序列，再用相邻排序与负样本约束蒸馏。该模式给出最直接的均匀转移核，可用于 T1–T5 的机制隔离。 [原论文](https://arxiv.org/abs/2109.01165) · [作者实现](https://github.com/Yueeeeeeee/RecSys-Extraction-Attack)
- **BECOME，CIKM 2025，Zhou 等。** 利用反馈动态分配生成预算，并用排名与频次调节下一步采样。它为 Scheme B 提供自适应压力测试。统一实现的 beta、阶段、采样和预算差异见 [已知差异](KNOWN_DEVIATIONS.md)。 [原论文](https://doi.org/10.1145/3746252.3761032) · [作者实现](https://github.com/Loche2/BECOME)
- **Sim4Rec，AAAI 2025。** 可控序列生成与对抗蒸馏提供另一条提取思路。当前只纳入相关工作。后续可独立做 listwise loss 攻击变体，标明对应蒸馏目标和生成方式。 [原论文](https://ojs.aaai.org/index.php/AAAI/article/view/33392)
- **LLM4MEA。** 使用语言模型改善合成历史的信息和分布质量，提示攻击者查询分布可能超出纯 ID 采样。本阶段评估限定于 ID 目录与排序反馈。 [原论文](https://arxiv.org/abs/2507.16969)

<a id="section-2"></a>

## 主动防御与研究切入点

- **GRO，WSDM 2024，Zhang 等。** 训练时利用内部 Student 的排序蒸馏损失梯度构造扰动目标，在使用原有预测机制服务时降低排序信号的可提取性。当前 SASRec 实现是从论文 BERT4Rec 场景迁移。A 检验当前损失与参考学习效果的目标差异，C 研究将完整合法排序内化到目标训练。 [原论文](https://arxiv.org/abs/2310.16335)
- **GRAD²，ICML 2022，Mazeika 等。** 用代理梯度重定向干预分类模型窃取。Scheme A 借鉴对优化方向的关注，研究在合法、头部约束的离散 Top-K ID 列表中用参考任务的相对投影评估候选编辑。 [原论文](https://proceedings.mlr.press/v162/mazeika22a.html)

候选研究主张及所需证据见 [贡献与创新点](research/contributions.md)。

<a id="section-3"></a>

## Sim4Rec 的量化比较范围

[Sim4Rec: Data-Free Model Extraction Attack on Sequential Recommendation](https://ojs.aaai.org/index.php/AAAI/article/view/33392) (AAAI 2025) studies controllable sequence generation and reinforced adversarial distillation for extracting sequential recommenders. It reports experiments involving NARM and SASRec, so its SASRec setting is relevant to this study.

The Phase I quantitative comparison includes DFME and BECOME. Their public author repositories permit a paper-to-source audit of generation, ranking loss and training details. In a source audit on 2026-10-15, we did not find a verifiable author implementation for the Sim4Rec extraction method. Reconstructing its generator and reinforcement training choices from the paper alone would introduce unverified choices. We therefore cite the work here and exclude it from numerical comparisons. The absence of verifiable source limits our ability to reproduce its reported results; it does not show that those results are incorrect.

The first-stage protocol also holds both victim and surrogate to SASRec. Sim4Rec's reported model-pair settings need to be read by architecture when comparing numbers. A SASRec-to-SASRec cell is conceptually possible, so architecture alone is not the exclusion reason.

<a id="section-4"></a>

## Possible reviewer response

> We thank the reviewer for pointing out Sim4Rec. We cite it in related work. Our quantitative baselines are DFME and BECOME because we could inspect their author implementations and reproduce the attack procedures under the shared SASRec and ranking-only API protocol. At the time of our source audit, we could not identify a verifiable author implementation of Sim4Rec. An independent reconstruction would require choices about its generator and adversarial training schedule that could materially change the result. We therefore excluded it from the numerical table and stated this limitation explicitly. We make no claim that its published results are invalid; we cannot independently verify their comparability to this protocol.

This is draft wording for a future response. It should be updated if an author implementation becomes available or the paper authors clarify the missing details.
