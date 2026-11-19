# 06 全部运行命令

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 05](05_DATA_AND_BUDGET.md) · [下一页 07](07_PROGRESS.md)

**本页目录**

- [本地检查](#section-1)
- [矩池云首次准备](#section-2)
- [直接执行正式实验](#section-3)
- [手动接续单个任务](#section-4)
- [导出与结果回传](#section-5)
- [两端修改代码或配置](#section-6)
- [本地取得服务器结果](#section-7)

<a id="section-1"></a>

## 本地检查

在本地仓库执行测试和软件 smoke。本节的临时数据只验证实现。

```powershell
Set-Location D:\ATRS
& .venv\Scripts\python.exe -m pytest -q
& .venv\Scripts\python.exe scripts\smoke.py
& .venv\Scripts\python.exe -m compileall -q src scripts tests
```

<a id="section-2"></a>

## 矩池云首次准备

选择已带 CUDA PyTorch 的 Linux 镜像，使用组账号实例详情里的 SSH 信息进入终端。代码和实验产物放在网盘挂载目录。原始数据随 Git 获取，后续代码同步复用这份数据。平台网盘对应 /mnt 的说明见 [矩池云官方文档](https://www.matpool.com/supports/doc-quick-start)。

运行依赖为 Python 3.10 或更新版本，以及已支持该实例 CUDA 的 PyTorch 2.3 至 3.0 之前版本，具体范围由 pyproject.toml 声明。虚拟环境复用镜像中已安装的 CUDA PyTorch。

```bash
mkdir -p /mnt/atrs-study
cd /mnt/atrs-study
git clone https://github.com/powell4322/ATRS.git
cd ATRS
python -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -e .
export CUBLAS_WORKSPACE_CONFIG=:4096:8
```

已克隆的机器在下一轮实验开始前更新。当前运行中的矩阵固定在其源码版本。

```bash
cd /mnt/atrs-study/ATRS
git status --short
git pull --ff-only origin main
source .venv/bin/activate
python -m pip install -e .
```

<a id="section-3"></a>

## 直接执行正式实验

默认执行三个 seed 的 ML-1M + SASRec，完整 M=1000，None/GRO × Random/DFME/BECOME。Ours 的实际方法确定后补上对应 cell。启动器会自动接续 Teacher，并校验后复用已完成的攻击结果。

```bash
python -u scripts/run_formal.py
```

每个 seed 的 stdout、stderr、环境和命令会写入其 runs/formal 目录。第一次训练从 clean 开始，随后复用该 seed 的 clean best。服务器直接使用正式配置开展训练和最终评价。

只执行 seed42，或将不同 seed 分给不同实例时使用同一入口。

```bash
python -u scripts/run_formal.py --configs configs/formal/ml1m_sasrec_seed42.json
```

查看 GPU 和训练进度。

```bash
nvidia-smi
tail -f runs/formal/ml1m_sasrec_seed42/logs/console-teacher-none.log
```

可在 tmux 等持久会话中启动正式入口。中断后重新执行同一个正式入口，已完成且 hash 一致的 cell 会被复用，未完成攻击从该 cell 开始重新生成和训练。

<a id="section-4"></a>

## 手动接续单个任务

教师接续自动读取最新 optimizer、scheduler、RNG 和 early-stop 计数。

```bash
python -u -m atrs.cli train-teacher --config configs/formal/ml1m_sasrec_seed42.json --defense none --device cuda --resume
```

同一个 seed 的某个攻击 cell 可独立执行，下例为 GRO 下的 DFME。

```bash
python -u -m atrs.cli run-attack --config configs/formal/ml1m_sasrec_seed42.json --defense gro --attack dfme --device cuda
```

正式参数优先由 JSON 定义。device、resume 是运行控制；临时 epochs 覆盖在正式协议下被拒绝。要调整方法参数，用新的配置和 run_root，再按同一攻击的所有防御条件执行。保留的 phase1 配置是历史集成实验。

<a id="section-5"></a>

## 导出与结果回传

默认启动器在每个 seed 的六个可运行 baseline cell 完成后自动导出。需要重新生成结果页时执行。

```bash
python scripts/export_results.py --config configs/formal/ml1m_sasrec_seed42.json
```

导出位置为 result/formal/ml1m_sasrec_seed42，页面为 docs/08_RESULTS.md。其他 seed 的命名同理。页面自动汇集已归档种子，逐个攻击比较防御，三种子齐全后统计均值与样本标准差。

审阅原始 JSON、配置、预算与分析后回传精简产物。

```bash
git add docs/08_RESULTS.md result/formal
git diff --cached --stat
git commit -m "Record formal ML-1M SASRec defense results"
git push origin HEAD
```

完整 checkpoint、查询数据和逐轮日志保留在 /mnt 下的 runs。结果 JSON 中的 git_commit 对应运行源码，结果提交会产生独立 SHA。

<a id="section-6"></a>

## 两端修改代码或配置

云端与本地共同编辑时，先在其中一端创建实验分支。

```bash
git switch -c codex/protocol-review
```

修改完成后，按实际变化的文件提交。下面示例为对 seed42 的正式配置进行已 review 的修订。

```bash
git add configs/formal/ml1m_sasrec_seed42.json
git diff --cached
git commit -m "Apply reviewed experimental configuration"
git push -u origin codex/protocol-review
```

在本地获取该分支。

```powershell
Set-Location D:\ATRS
git fetch origin
git switch codex/protocol-review
git pull --ff-only origin codex/protocol-review
```

两端继续在同一分支上按提交、push、pull 同步。定稿后合并至 main，正式运行从相应固定提交开始。

<a id="section-7"></a>

## 本地取得服务器结果

结果在 main 上时执行。

```powershell
Set-Location D:\ATRS
git status --short
git pull --ff-only origin main
```

结果在实验分支上时，fetch 后切换对应分支审阅。push 遇到两端新提交时，先 fetch 并处理真实冲突，再推送。Git push 使用有写入权限的账号认证。
