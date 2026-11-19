# 05 数据与预算审计

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 04](04_EXPERIMENT_PROTOCOL.md) · [下一页 06](06_COMMANDS.md)

**本页目录**

- [三个输入文件](#section-1)
- [官方仓库如何获取数据](#section-2)
- [Data-free 边界](#section-3)
- [预算账本](#section-4)

<a id="section-1"></a>

## 三个输入文件

Git 只跟踪下表三个原始文本。Video 和 wikipedia 等其他本地文件继续受忽略规则管理。每台服务器首次 clone 会获得这三个文件，后续代码 pull 通常只传输发生变化的源码与配置。

| Dataset / 文件 | 用户 | 物品 | 事件 | 少于三次交互的用户 | 当前正式入口 |
| --- | ---: | ---: | ---: | ---: | --- |
| ML-1M / data/ml-1m.txt | 6040 | 3416 | 999611 | 0 | 支持 |
| Steam / data/Steam.txt | 334730 | 13047 | 3686172 | 1805 | 数据规则 TBD |
| Beauty / data/Beauty.txt | 52204 | 57289 | 394908 | 1706 | 数据规则 TBD |

三个文件都是按用户分块的两列 user/item，物品 ID 连续为 1..N，扫描未发现用户块交错。数据缺少时间戳和原始评分，时间顺序只能承接已有行序，原始来源、过滤和 ID 映射过程仍需补齐。

| 文件 | SHA-256 |
| --- | --- |
| ML-1M | b725f3acb3986fe3130bffd1e77a74d182a1f51799567a236dbd60270f95b0a2 |
| Steam | 4df1f5feac169a522008956ba5a50fee4e9ce2c0c817cabfd463ac36df05f023 |
| Beauty | 3cd3d56cee682f5118f22d0443d5d27116075c719ec83bfdfa3e45df33a95e12 |

ML-1M 留一后为 987531 个 train 事件，6040 个 valid 和 6040 个 test。论文数据统计与当前文本并非逐项相同，正式论文需报告本项目的实际统计。扩展 Steam/Beauty 前确定短用户与最低交互数规则，派生预处理和重映射写入新文件并保存 metadata。

<a id="section-2"></a>

## 官方仓库如何获取数据

两个作者仓库都在 datasets 子目录提供下载和预处理。ML-1M 读取 GroupLens ratings.dat，Beauty 读取 SNAP ratings_Beauty.csv，Steam 读取 UCSD steam_reviews.json.gz。预处理执行 item/user 频次过滤、密集 ID 映射，再按 timestamp 和 item ID 排序并留一，缓存为含 train/val/test/umap/smap 的 dataset.pkl。原配置 min_uc=min_sc=5。这里的单次过滤顺序和任意 set 迭代重映射也可能影响与已有文本的字节一致性。 [DFME datasets](https://github.com/Yueeeeeeee/RecSys-Extraction-Attack/tree/47f841b708eb25d3aa996aefcbdfba6b713741b3/datasets) · [BECOME datasets](https://github.com/Loche2/BECOME/tree/83355ef723e16ca826d013c23938f51f0e0b453e/datasets)

当前正式防御比较直接复用本仓库三份冻结文本，避免每个攻击反复下载和预处理。所有防御条件使用同一文本、同一 split 和目录。需要补原始来源时，下载一次、在网盘缓存原件，再生成有明确映射和 hash 的派生数据版本。

<a id="section-3"></a>

## Data-free 边界

| 流程 | 可以读取的数据 | 已核查边界 |
| --- | --- | --- |
| Target / GRO 训练 | 目标自己的 train、defender valid | 教师推荐损失和选 best 只在防御端 |
| Random / DFME 生成 | 公开物品 ID、合成前缀、ranking oracle | 不接收真实序列或人气 |
| BECOME 反馈 | 合成终端 prefix、保护 API Top-100、自身 Student 分数 | Top-10 交集用于分配，实际请求全部计数 |
| Surrogate 蒸馏 | 合成 prefix、排序标签、自身 scores、配置固定的负采样 | 不接收 Split、真实 valid/test 或 Teacher logits |
| 主 Agreement | 独立评价进程的 clean checkpoint | 参考只用于最终指标 |
| A/B 机制诊断 | 防御方 train-only 参考，或标记为诊断的真实 valid 分析 | 不进入正式攻击参数选择 |

负采样的 source_softmax 策略只由公开目录大小和返回 Top-K 构造，复现了作者源码中置零再 softmax 的分布。该分布仍会抽到 pad/Top-K，审计在 03 解释此差异。BECOME 的频次是查询中观察到的物品计数。真实用户 test 标签只在模型冻结后的离线 evaluator 读取。

作者仓库的 distill.py 会构造真实 test_loader 并把它保存在 trainer 对象里，生成和蒸馏代码与最终评价处于同一进程。已检查的阶段 validate 使用 dis_val_loader，即由合成序列终端和目标排序生成的验证集；真实 test_loader 在训练完成后的 test 函数中遍历。对象持有 test_loader 本身不足以说明发生了标签泄露，仍需逐条调用核查。当前 ATRS 正式生成与蒸馏函数只接收 oracle、公开目录、合成数据和配置，真实测试读取集中在攻击训练完成后的 evaluate。原型诊断若使用真实 valid 结果，必须保持防御方分析用途并保留相应标记。

<a id="section-4"></a>

## 预算账本

| 字段 | 定义 |
| --- | --- |
| nominal_sequences / generated_sequences | 名义配置 M 与实际初始化的序列数 |
| unique_queried_prefixes | 累计不同原始前缀数 |
| unique_model_contexts | 截断到模型 max_len 后的不同有效上下文数 |
| requested_prefixes | 所有成功提交的逻辑 prefix 行数，包含缓存与反馈 |
| feedback_prefixes | BECOME 额外阶段反馈的逻辑行数 |
| feedback_oracle_requests | 反馈中的新 API 请求数 |
| oracle_requests | cache=True 时的新原始前缀请求，cache=False 时每行均收费 |
| model_forward_calls | 底层批前向次数 |
| cache_hits | 已缓存或同批合并的行数 |
| retained_samples | 生成阶段保留过的标签行，可能含 BECOME 终端 holdout |
| retained_training_rows | 最终实际交给蒸馏训练的行数 |
| training_steps | Surrogate 实际 optimizer step 次数 |

当前 cache=True 时 requested_prefixes = oracle_requests + cache_hits。精确 raw-prefix 缓存对同一个冻结确定性 API 响应进行复用。未来若 Ours 每次响应随机，缓存与聚合行为需单独定义并冻结。

ML-1M 下 Random/DFME 的逻辑生成行为为 1000 × 200 = 200000 行，训练保留 1000 × 199 = 199000 行。重复前缀可降低收费和有效覆盖。BECOME 初始长度 20，8 个阶段只延长低一致性的半数序列，另有 8 × 1000 = 8000 行反馈。最终每条序列的长度及总生成请求依动态分配而变，不能用 1000 × 200 代替其实测消耗。

为了不改动攻击机制，本轮沿用 1k 名义序列规则并报告真实消耗。每一种攻击在 None/GRO/Ours 下保持相同规则。后续如研究同一种攻击的预算敏感性，使用明确版本的配置另行记录。
