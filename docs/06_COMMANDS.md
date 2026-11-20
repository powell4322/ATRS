# 06 连接矩池云与运行命令

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 05](05_DATA_AND_BUDGET.md) · [下一页 07](07_PROGRESS.md)

**本页目录**

- [首轮任务和正常轮次](#section-1)
- [本地软件检查](#section-2)
- [用什么连接](#section-3)
- [租卡和首次准备](#section-4)
- [在 tmux 中启动 GRO](#section-5)
- [断线、离开会话和查看进度](#section-6)
- [重启与手动接续](#section-7)
- [导出和回传结果](#section-8)

<a id="section-1"></a>

## 首轮任务和正常轮次

本轮按用户确认先完成 SASRec + ML-1M 的 GRO。None 的攻击实验格暂缓，初步改进方案之后确定。基础 clean teacher 是 GRO 的预训练起点和 clean-reference Agreement 的共同依赖，仍需训练或从同一配置的 checkpoint 接续。

使用 configs/gro_first 的独立配置，M=1000、Top-100、batch 128。旧 configs/formal 的 20-epoch 方案保留供追溯。

| 阶段 | 当前轮次 | 来源与停止方式 |
| --- | --- | --- |
| 基础 clean teacher | 最多 1000 epochs | 作者模板的最大轮次，valid NDCG@10 patience=30 |
| GRO 追加训练 | 最多 1000 epochs | 论文要求继续至收敛，1000 为本项目上限，valid NDCG@10 patience=30 |
| Random / DFME Surrogate | 固定 1000 epochs | 作者模板的正常训练轮次 |
| BECOME Surrogate | 初始 20 + 7 阶段各 20 + 最后 30 | 现有源码的阶段调度，共 190 epochs |

基础教师和 GRO 的实际轮数由早停决定。Surrogate 训练不使用真实 valid/test 标签选轮数。所有检查和 smoke 在本地完成。

<a id="section-2"></a>

## 本地软件检查

```powershell
Set-Location D:\ATRS
& .venv\Scripts\python.exe -m pytest -q
& .venv\Scripts\python.exe scripts\smoke.py
```

<a id="section-3"></a>

## 用什么连接

建议使用 Windows Terminal / PowerShell 自带的 OpenSSH，登录后在远端用 tmux 运行。当前本地机器已检测到 ssh。实例启动后，在矩池云“我的租用 / 实例详情”复制实际 SSH 命令，原样粘贴到本地 PowerShell，按该实例给出的密码或密钥登录。端口和主机名以实例详情为准。 [矩池云 SSH 连接说明](https://matpool.com/supports/doc-putty-connect-matpool)

需要边看代码边操作时，也可以把同一个 SSH 命令加入 VS Code Remote-SSH，再打开 /mnt/atrs-study/ATRS。长训练在远端终端配合 tmux。 [矩池云 VS Code 教程](https://matpool.com/supports/doc-vscode-connect-matpool)

<a id="section-4"></a>

## 租卡和首次准备

按当前模型规模，建议先用一张 RTX 4090 24GB 或同等显存的单卡实例，选择 CUDA PyTorch 镜像。代码要求 Python >=3.10、PyTorch >=2.3 且 <3。网盘和实例选同一区域，使用默认 /mnt 挂载保存代码、数据和实验产物。 [矩池云入门文档](https://www.matpool.com/supports/doc-quick-start)

首次在远端 Bash 中执行。

```bash
mkdir -p /mnt/atrs-study
cd /mnt/atrs-study
git clone https://github.com/powell4322/ATRS.git
cd ATRS
python -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -e .
nvidia-smi
```

已有仓库时用下面的更新命令，先保存已有本地修改。

```bash
cd /mnt/atrs-study/ATRS
git status --short
git pull --ff-only origin main
source .venv/bin/activate
python -m pip install -e .
```

<a id="section-5"></a>

## 在 tmux 中启动 GRO

先查看 tmux 是否可用。

```bash
tmux -V
```

如果镜像未安装 tmux，root 用户可按官方教程安装。

```bash
apt-get update
apt-get install -y tmux
```

创建持久会话。

```bash
tmux new -s atrs-gro
```

进入会话后执行首个 seed 的完整任务。

```bash
cd /mnt/atrs-study/ATRS
source .venv/bin/activate
export CUBLAS_WORKSPACE_CONFIG=:4096:8
python -u scripts/run_formal.py --configs configs/gro_first/ml1m_sasrec_seed42.json
```

该命令先训练基础教师，再训练 GRO，随后只运行 GRO 下的 Random、DFME、BECOME。M=1000 和正常训练轮次由配置固定。None 的提取格不会执行。teacher_none 文件名表示基础教师，完整配置保存在该 run_root 中。

若希望从第一轮开始顺序执行三个种子，使用默认入口替代上面的单 seed 命令。

```bash
python -u scripts/run_formal.py
```

默认配置为 gro_first 的 42、43、44，完整计划共 9 个 GRO 攻击 cell。两种启动方式按当前需要选一种，同一个 run_root 的同名任务串行执行。

<a id="section-6"></a>

## 断线、离开会话和查看进度

在 tmux 中按 Ctrl+B，松开后按 D，可暂时离开并保持任务运行。重新 SSH 登录后执行。

```bash
tmux attach -t atrs-gro
```

矩池云官方建议在本地 SSH 工具内配合 tmux，断开 SSH 后会话中的训练仍可继续。 [官方 tmux 教程](https://matpool.com/supports/doc-tmux-matpool)

另开一个 SSH 终端即可查看 GPU 和当前训练日志。

```bash
nvidia-smi
tail -f /mnt/atrs-study/ATRS/runs/gro_first/ml1m_sasrec_seed42/logs/console-teacher-none.log
```

进入 GRO 阶段后查看。

```bash
tail -f /mnt/atrs-study/ATRS/runs/gro_first/ml1m_sasrec_seed42/logs/console-teacher-gro.log
```

DFME 开始后，可以查看逐 epoch 的损失与累计 optimizer steps。

```bash
tail -f /mnt/atrs-study/ATRS/runs/gro_first/ml1m_sasrec_seed42/logs/student_gro_dfme.jsonl
```

Random 和 BECOME 的日志命名同理。tmux 的断线保持依赖实例继续运行；实例停止后需按 checkpoint 接续。

<a id="section-7"></a>

## 重启与手动接续

进程异常结束时，重新运行同一个正式入口。教师从最新 checkpoint 接续，已完成且源码/配置/文件 hash 一致的攻击结果会复用，未完成攻击从该 cell 开始重跑。

只接续 GRO 教师。

```bash
python -u -m atrs.cli train-teacher --config configs/gro_first/ml1m_sasrec_seed42.json --defense gro --device cuda --resume
```

只运行 GRO 下的 DFME。

```bash
python -u -m atrs.cli run-attack --config configs/gro_first/ml1m_sasrec_seed42.json --defense gro --attack dfme --device cuda
```

<a id="section-8"></a>

## 导出和回传结果

单 seed 三个 GRO cell 完成后自动导出，即使尚未运行 None 也可生成报告。需要重新导出时执行。

```bash
python scripts/export_results.py --config configs/gro_first/ml1m_sasrec_seed42.json
```

结果归档位于 result/gro_first/ml1m_sasrec_seed42，分析页为 docs/08_RESULTS.md。GRO 的 parent hash 与主 Agreement 的 clean reference 必须一致。未完成 None 时，报告只给已测指标，配对防御差值等相应对照完成后生成。

审阅后将精简结果回传。

```bash
git add docs/08_RESULTS.md result/gro_first
git diff --cached --stat
git commit -m "Record GRO-first ML-1M SASRec results"
git push origin HEAD
```

checkpoint、完整查询数据和逐轮日志继续保存在 /mnt 下的 runs。源码和实验配置的修改先 commit/push，下一轮服务器任务开始前 pull。同一完整运行内固定源码版本。

本地取得服务器提交的结果。

```powershell
Set-Location D:\ATRS
git status --short
git pull --ff-only origin main
```
