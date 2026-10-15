# Related work and baseline scope

[Sim4Rec: Data-Free Model Extraction Attack on Sequential Recommendation](https://ojs.aaai.org/index.php/AAAI/article/view/33392) (AAAI 2025) studies controllable sequence generation and reinforced adversarial distillation for extracting sequential recommenders. It reports experiments involving NARM and SASRec, so its SASRec setting is relevant to this study.

The Phase I quantitative comparison includes DFME and BECOME. Their public author repositories permit a paper-to-source audit of generation, ranking loss and training details. In a source audit on 2026-10-15, we did not find a verifiable author implementation for the Sim4Rec extraction method. Reconstructing its generator and reinforcement training choices from the paper alone would introduce unverified choices. We therefore cite the work here and exclude it from numerical comparisons. The absence of verifiable source limits our ability to reproduce its reported results; it does not show that those results are incorrect.

The first-stage protocol also holds both victim and surrogate to SASRec. Sim4Rec's reported model-pair settings need to be read by architecture when comparing numbers. A SASRec-to-SASRec cell is conceptually possible, so architecture alone is not the exclusion reason.

## Possible reviewer response

> We thank the reviewer for pointing out Sim4Rec. We cite it in related work. Our quantitative baselines are DFME and BECOME because we could inspect their author implementations and reproduce the attack procedures under the shared SASRec and ranking-only API protocol. At the time of our source audit, we could not identify a verifiable author implementation of Sim4Rec. An independent reconstruction would require choices about its generator and adversarial training schedule that could materially change the result. We therefore excluded it from the numerical table and stated this limitation explicitly. We make no claim that its published results are invalid; we cannot independently verify their comparability to this protocol.

This is draft wording for a future response. It should be updated if an author implementation becomes available or the paper authors clarify the missing details.
