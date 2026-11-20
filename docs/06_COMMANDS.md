# 06 SSH 部署、实验与本地备份

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 05](05_DATA_AND_BUDGET.md) · [下一页 07](07_PROGRESS.md)

**本页目录**

- [当前任务和运行边界](#section-1)
- [首次配置本地 SSH 别名](#section-2)
- [远端首次部署与环境初始化](#section-3)
- [服务器 GPU smoke](#section-4)
- [用 tmux 运行正式 GRO](#section-5)
- [查看进度、更新和接续](#section-6)
- [将轻量结果取回并提交 Git](#section-7)
- [通过 SCP 备份大产物并校验](#section-8)

<a id="section-1"></a>

## 当前任务和运行边界

先完成 SASRec + ML-1M 的 GRO，None 攻击格暂缓，初步改进等待后续计划。基础 clean teacher 仍是 GRO 的起点和 clean-reference Agreement 的共同依赖。

本地用 Windows 11 的 PowerShell、SSH、SCP 和 VS Code。远端为指定实例的 Linux Bash，默认项目目录为 ~/workspace/ATRS，使用容器本地存储。平台账号由课题组共享，操作限于你指定的实例和项目目录。平台资源由你手动管理，个人主私钥、账号密码和明文 Token 均不进入服务器或 Git。默认采用 Git 同步、SCP 备份的流程。

| 阶段 | 当前正常轮次 |
| --- | --- |
| 基础 clean teacher | 最多 1000 epochs，valid NDCG@10 patience=30 |
| GRO 追加训练 | 最多 1000 epochs，patience=30；1000 为工程上限，论文要求继续至收敛 |
| Random / DFME Surrogate | 固定 1000 epochs |
| BECOME Surrogate | 初始 20 + 七阶段各 20 + 最后 30，共 190 epochs |

使用 configs/gro_first，M=1000、Top-100、batch 128。服务器先做一次 GPU smoke，再启动正式运行。Smoke 的临时产物和数值仅用于验证实现。

<a id="section-2"></a>

## 首次配置本地 SSH 别名

在本地 PowerShell 打开 SSH 配置，保留现有其他 Host 条目。

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null
notepad "$env:USERPROFILE\.ssh\config"
```

加入以下条目。YOUR_INSTANCE_HOST、YOUR_INSTANCE_PORT、YOUR_INSTANCE_USER 都要换成你明确指定实例的 SSH 信息。

```sshconfig
Host matpool-anti
    HostName YOUR_INSTANCE_HOST
    Port YOUR_INSTANCE_PORT
    User YOUR_INSTANCE_USER
```

本机目前尚未配置这个别名。保存后从本地 PowerShell 连接，按实例实际认证方式登录。

```powershell
ssh matpool-anti
```

VS Code Remote-SSH 使用同一个别名，连接后打开远端 ~/workspace/ATRS。Windows 直接使用本机的 OpenSSH，连接和备份命令均在 PowerShell 执行。

<a id="section-3"></a>

## 远端首次部署与环境初始化

下面在已登录的远端 Bash 执行。先确认解析后的目录和文件系统归属符合当前指定实例的容器本地目录，再 clone。共享挂载的实际范围以实例配置为准。

```bash
mkdir -p ~/workspace
cd ~/workspace
pwd -P
findmnt -T .
git clone https://github.com/powell4322/ATRS.git
cd ATRS
nvidia-smi
python -V
bash setup.sh
```

setup.sh 使用当前激活的 python，检查 Python >=3.10、PyTorch >=2.3 且 <3、CUDA 可用性，打印 Python 路径、CUDA runtime 与 GPU。随后只安装本项目的 editable 包，复用已有依赖，并调用现有 preprocess 入口校验 ML-1M。若当前 Python 缺少兼容的 CUDA PyTorch，先激活镜像自带的相应环境再运行。

这个默认流程直接使用镜像环境，项目、依赖修改及运行产物都限于该实例的项目用途。

<a id="section-4"></a>

## 服务器 GPU smoke

在远端项目根目录执行。

```bash
python scripts/smoke.py --device cuda
```

显式指定 cuda，GPU 不可用时会失败并提示原因。这个已有 smoke 入口覆盖模型训练、排名 API、DFME/BECOME 最小蒸馏、GRO 参数更新、checkpoint、评价和 JVP。临时文件只在项目 runs/smoke 内创建并清理。

本地开发回归仍可在 PowerShell 执行。

```powershell
Set-Location D:\ATRS
& .venv\Scripts\python.exe -m pytest -q
& .venv\Scripts\python.exe scripts\smoke.py --device cpu
```

<a id="section-5"></a>

## 用 tmux 运行正式 GRO

先在远端查看 tmux。若镜像缺少该工具，可在本实例有权限的终端安装。

```bash
tmux -V
```

Ubuntu root 环境中的安装命令如下。

```bash
apt-get update
apt-get install -y tmux
```

建立持久会话。

```bash
tmux new -s anti
```

进入会话后执行。

```bash
cd ~/workspace/ATRS
python -u scripts/run_formal.py
```

默认按 42、43、44 顺序运行，每 seed 只执行 GRO 下的 Random、DFME、BECOME，共九格。先训练基础教师和 GRO，基础教师文件 teacher_none 作为共同参照，None 的攻击格暂缓。完整配置和环境写在各自 run_root，正式代码版本固定。

只执行 seed42 的完整任务时，使用下面的入口替代上面的默认命令。

```bash
python -u scripts/run_formal.py --configs configs/gro_first/ml1m_sasrec_seed42.json
```

在 tmux 内按 Ctrl+B，松开后按 D 可离开会话。重新 SSH 登录后恢复。

```bash
tmux a -t anti
```

<a id="section-6"></a>

## 查看进度、更新和接续

另一个远端 SSH 终端可查看 GPU 和已开始阶段的日志。

```bash
nvidia-smi
tail -f ~/workspace/ATRS/runs/gro_first/ml1m_sasrec_seed42/logs/console-teacher-gro.log
```

基础教师日志为 console-teacher-none.log。DFME 开始后可查看逐 epoch 损失、阶段与累计训练步数。

```bash
tail -f ~/workspace/ATRS/runs/gro_first/ml1m_sasrec_seed42/logs/student_gro_dfme.jsonl
```

下一轮运行开始前，先保存当前项目修改，再从项目根目录同步代码。

```bash
git pull --ff-only
bash setup.sh
```

tmux 断线时保持进程，实例停止或进程异常后需要接续。重新执行同一个正式入口会接续 Teacher，复用身份和 hash 一致的已完成攻击，重跑未完成的攻击 cell。

<a id="section-7"></a>

## 将轻量结果取回并提交 Git

每个 seed 的三个 GRO cell 完成后自动导出。需要重新生成页面时在远端执行。

```bash
python scripts/export_results.py --config configs/gro_first/ml1m_sasrec_seed42.json
```

结果先通过 SCP 取回本地，再用本机已有的 Git 认证提交。服务器只需通过公开仓库 clone/pull，认证材料保留在本地。

```powershell
Set-Location D:\ATRS
git pull --ff-only
scp -r matpool-anti:workspace/ATRS/result/gro_first ./result/
scp matpool-anti:workspace/ATRS/docs/08_RESULTS.md ./docs/08_RESULTS.md
git add docs/08_RESULTS.md result/gro_first
git diff --cached --stat
git commit -m "Record GRO-first ML-1M SASRec results"
git push origin HEAD
```

运行中的源码保持在同一提交。本地修改源码或实验配置后先 commit/push，下一轮服务器再 pull。取回结果前先保存本地已有修改。

下一轮在远端同步已经提交的结果和代码。

```bash
cd ~/workspace/ATRS
git pull --ff-only
```

<a id="section-8"></a>

## 通过 SCP 备份大产物并校验

实验结束或停止写入后，在远端项目根目录打包 checkpoint、完整查询、日志、配置和结果。artifacts 已受 Git 忽略。

```bash
mkdir -p artifacts/backup
tar -czf artifacts/backup/atrs-runs.tar.gz runs result configs
sha256sum artifacts/backup/atrs-runs.tar.gz > artifacts/backup/atrs-runs.tar.gz.sha256
```

回到本地 PowerShell，将压缩包和校验文件下载到仓库之外。远端路径 workspace/ATRS 相对于该 SSH 用户的 home。

```powershell
$backupDir = Join-Path $env:USERPROFILE "ATRS-backup\gro-first"
New-Item -ItemType Directory -Force $backupDir | Out-Null
scp matpool-anti:workspace/ATRS/artifacts/backup/atrs-runs.tar.gz matpool-anti:workspace/ATRS/artifacts/backup/atrs-runs.tar.gz.sha256 "$backupDir"
$archivePath = Join-Path $backupDir "atrs-runs.tar.gz"
$checksumPath = Join-Path $backupDir "atrs-runs.tar.gz.sha256"
$expectedHash = ((Get-Content $checksumPath) -split '\s+')[0]
if ((Get-FileHash $archivePath -Algorithm SHA256).Hash -ne $expectedHash) { throw "备份校验失败" }
tar -tzf $archivePath
```

确认两端 SHA-256 一致，并检查压缩包中包含预期的 checkpoint、查询文件和日志。模型权重可从这份归档恢复，源码和冻结数据可通过记录的 Git 提交恢复。你确认本地备份完整后，再手动释放指定实例。
