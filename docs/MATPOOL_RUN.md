# 19 矩池云首轮运行

<!-- doc-nav:start -->
[00 总索引](README.md) · [01 待审决策](REVIEW_DECISIONS.md) · [上一页 18](EXPERIMENT_PLAN.md) · [下一页 20](GIT_WORKFLOW.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [同步代码和验收环境](#section-1)
- [1. 先验收 clean SASRec 和 DFME](#section-2)
- [2. 复用 clean best 跑 P0](#section-3)
- [3. 完成统一基线矩阵](#section-4)
<!-- doc-toc:end -->

首轮用组账号租一张 GPU，建议 RTX 4090 24 GB，选择同区域网盘及自带 CUDA PyTorch 的 Linux 镜像。当前代码为单 GPU 流程。使用实例详情的 SSH 命令进入终端，在网盘挂载的 `/mnt` 下用组内独立目录存放代码、日志和 checkpoint。释放实例前确认文件可从网盘读回。 [矩池云官方入门教程](https://www.matpool.com/supports/doc-quick-start)

<a id="section-1"></a>

## 同步代码和验收环境

在服务器的 Bash 中运行。使用包含本轮变更的代码版本。正式矩阵各格从同一固定提交运行。

日常更新用 Git pull，云端代码修改和结果回传按 [20 Git 同步流程](GIT_WORKFLOW.md) 操作。协议、指标与参数的待定项集中在 [01 待审决策清单](REVIEW_DECISIONS.md)。

```bash
mkdir -p /mnt/atrs-study
cd /mnt/atrs-study
git clone https://github.com/powell4322/ATRS.git
cd ATRS
git rev-parse HEAD
git status --short
nvidia-smi
python --version
python -m venv --system-site-packages .venv
source .venv/bin/activate
python -c 'import torch; assert torch.cuda.is_available(); print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))'
python -m pip install -e '.[test]'
export CUBLAS_WORKSPACE_CONFIG=:4096:8
python -m pytest -q
python scripts/smoke.py
python -m atrs.research t5 --help
python -m atrs.cli preprocess --config configs/phase1/ml1m_sasrec_seed42.json
```

要求 Python ≥3.10，Torch ≥2.3 且 <3。GPU smoke 会在 CUDA 上覆盖 Teacher/Student 更新和 checkpoint RNG 恢复。若 PyTorch CUDA 不可用，先核对镜像与驱动。官方 ML-1M 配置的 SHA-256 校验通过后再开始训练。

如果本机的改动仍未同步到远端，可把源文件打包，用 SFTP 上传到服务器的网盘，再解包到上面克隆的目录。下面只打包本轮运行需要的源码、配置和说明，数据由克隆获得。

```powershell
Set-Location D:\ATRS
tar.exe -czf "$env:TEMP\atrs-source.tar.gz" --exclude=__pycache__ src scripts tests configs docs README.md pyproject.toml
```

```bash
cd /mnt/atrs-study/ATRS
tar -xzf /mnt/atrs-study/atrs-source.tar.gz
git status --short
```

带工作区修改的覆盖包适合先做预检。正式实验从已提交的固定版本开始，保证输出 Git SHA 对应实际执行的代码。源码版本和环境记录如下。

```bash
cfg=configs/phase1/ml1m_sasrec_seed42.json
base=runs/phase1/ml1m_sasrec_seed42
mkdir -p "$base/logs"
git rev-parse HEAD > "$base/logs/source-commit.txt"
git status --short > "$base/logs/source-status.txt"
python -m pip freeze > "$base/logs/environment.txt"
nvidia-smi > "$base/logs/gpu.txt"
set -o pipefail
```

<a id="section-2"></a>

## 1. 先验收 clean SASRec 和 DFME

```bash
(
  set -euo pipefail
  python -u -m atrs.cli train-teacher --config "$cfg" --defense none --device cuda \
    2>&1 | tee -a "$base/logs/console-clean.log"
  python -u -m atrs.cli run-attack --config "$cfg" --defense none --attack dfme --device cuda \
    2>&1 | tee -a "$base/logs/console-clean-dfme.log"
)
```

第一次长跑建议用 `tmux` 或矩池云终端保持会话。等待 clean 的 validation 收敛或达到配置的 epoch 上限，检查 `teacher_none_best.pt`、验证曲线、DFME 训练损失和 `none_dfme.json` 的 actual requests。本轮跑统一协议，原论文逐项复现另开配置。

训练中断后用相同配置加 `--resume` 重跑对应 `train-teacher`。它读取最新 checkpoint 接续，在已达到上限或 patience 时退出。攻击中断后从该 cell 开头重跑。每个 `run_root` 的同名 job 串行执行。想改模型尺寸、训练预算或数据时，复制配置文件并设置新 `run_root`，重新生成对应 checkpoint。

<a id="section-3"></a>

## 2. 复用 clean best 跑 P0

```bash
diag=runs/research/ml1m_sasrec_seed42
mkdir -p "$diag"

python -u -m atrs.research t2-t4 --config "$cfg" --device cuda --seed 42 \
  --output "$diag/t2-t4-init" --sequences 8 --length 16 --queries 12 --head 10 \
  --candidates 6 --reference-rows 8 --reference-length 50 --eta 0.001 --warmup-epochs 0 \
  2>&1 | tee "$diag/t2-t4-init.log"

python -u -m atrs.research t2-t4 --config "$cfg" --device cuda --seed 42 \
  --output "$diag/t2-t4-warm" --sequences 8 --length 16 --queries 12 --head 10 \
  --candidates 6 --reference-rows 8 --reference-length 50 --eta 0.001 --warmup-epochs 2 \
  2>&1 | tee "$diag/t2-t4-warm.log"

python -u -m atrs.research t5 --config "$cfg" --device cuda --seed 42 \
  --output "$diag/t5" --sequences 24 --length 40 --head 10 --replacements 10 \
  --epochs 2 --batch-size 32 --fold valid \
  2>&1 | tee "$diag/t5.log"

python -u -m atrs.research t1 --config "$cfg" --device cuda --seed 42 \
  --output "$diag/t1" --sequences 24 --length 40 --epochs 2 --batch-size 32 --fold valid \
  2>&1 | tee "$diag/t1.log"
```

T2–T4 每次最多 128 个诊断请求，`warm` 独立增加 128 个 warm-up 请求。两次复用同一探针前缀。T5 每个生成分支恰有 960 次唯一请求。T1 只有一套生成前缀，最多 960 请求。T1 可用新目录加 `--extended` 评估排名区间和分项。可用独立的 `--seed` 与新目录进行复测。诊断输出目录需为新路径，重跑时加后缀。每个目录保存 `config.json`、`result.json` 和适用的 gzip 查询数据，失败时检查控制台以及目录中的 `error.log`。

<a id="section-4"></a>

## 3. 完成统一基线矩阵

已有 clean + DFME 时补齐其余五格。

```bash
(
  set -euo pipefail
  python -u -m atrs.cli run-attack --config "$cfg" --defense none --attack become --device cuda \
    2>&1 | tee -a "$base/logs/console-none-become.log"

  for defense in gro continued-clean; do
    python -u -m atrs.cli train-teacher --config "$cfg" --defense "$defense" --device cuda \
      2>&1 | tee -a "$base/logs/console-$defense.log"
    for attack in dfme become; do
      python -u -m atrs.cli run-attack --config "$cfg" --defense "$defense" --attack "$attack" --device cuda \
        2>&1 | tee -a "$base/logs/console-$defense-$attack.log"
    done
  done

  python scripts/export_results.py --config "$cfg"
)
```

从空运行目录一次性执行全部六格时，可以改用 `bash scripts/run_matrix.sh`。手动分阶段运行和矩阵启动器使用相同的默认输出目录，选择其中的启动方式。六格验证后导出到 `result/phase1/ml1m_sasrec_seed42/` 及 `docs/RESULTS.md`。分享时同时带上实验 JSON、教师 checkpoint 身份、GPU 及环境信息。网盘空间不足时优先保留 clean/GRO/continued-clean 的 best 与 latest、完整 logs、原始诊断和结果。 [矩池云保存与备份说明](https://matpool.com/supports/snapshot)
