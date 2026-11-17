# 20 本地与矩池云 Git 同步

<!-- doc-nav:start -->
[00 总索引](README.md) · [01 待审决策](REVIEW_DECISIONS.md) · [上一页 19](MATPOOL_RUN.md) · [下一页 21](WINDOWS_4090_RUN.md)
<!-- doc-nav:end -->

<!-- doc-toc:start -->
**本页目录**

- [代码、结果与运行产物](#section-1)
- [第一次在矩池云获取代码](#section-2)
- [在云端修改代码或实验配置](#section-3)
- [回传 Phase I 正式结果](#section-4)
- [回传 P0 诊断结果](#section-5)
- [获取服务器回传的结果](#section-6)
<!-- doc-toc:end -->

<a id="section-1"></a>

## 代码、结果与运行产物

本地和矩池云都通过同一个 origin 同步。源码、配置、研究文档、精简实验 JSON 和分析页进入 Git。完整 checkpoint、原始查询数据和详细日志保存在网盘的 runs 目录，按 run_root 与 source SHA 关联。Git 忽略规则已覆盖 runs、pt/pth、虚拟环境和本地论文。网盘内容按 [19 矩池云运行手册](MATPOOL_RUN.md) 保存。

正式运行前确认代码已提交并记下 SHA。执行同一个六格矩阵期间固定源码版本。要试新代码或新研究配置，使用新的 run_root，逐格记录训练代码版本、配置 hash、dataset hash 和 checkpoint parent。

<a id="section-2"></a>

## 第一次在矩池云获取代码

```bash
mkdir -p /mnt/atrs-study
cd /mnt/atrs-study
git clone https://github.com/powell4322/ATRS.git
cd ATRS
git branch --show-current
git rev-parse HEAD
git status --short
```

如果仓库已存在，先检查本地改动。工作区干净后更新当前 main。

```bash
cd /mnt/atrs-study/ATRS
git status --short
git switch main
git pull --ff-only origin main
```

首次安装环境及运行顺序见 [19 矩池云手册](MATPOOL_RUN.md)。代码更新后在已激活的环境运行下面的检查。

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/smoke.py
```

<a id="section-3"></a>

## 在云端修改代码或实验配置

本地和云端都有写入需求时，用一个实验分支同步。下面以 budget-review 为例，可以替换成实际实验主题。

```bash
git switch -c codex/budget-review
```

编辑完成并通过测试后，按实际改动文件暂存。以下例子适用于已修改研究代码和新增配置的场景。

```bash
git status --short
git diff -- src/atrs/research.py configs/research/ml1m_review_seed42.json
git add src/atrs/research.py configs/research/ml1m_review_seed42.json
git diff --cached --stat
git commit -m "Configure reviewed ML-1M diagnostic experiment"
git push -u origin codex/budget-review
```

新增配置需要从现有配置派生，并设置新的 run_root。当前 checkpoint 校验绑定配置文件 hash，配置变化后，兼容权重复用方式也要核对。上述示例文件需先实际创建。

在本地取得云端分支。

```powershell
Set-Location D:\ATRS
git fetch origin
git switch codex/budget-review
git pull --ff-only origin codex/budget-review
```

在本地继续编辑、提交和推送该分支，云端在下一轮运行前 pull 同一分支。两端在切分支或 pull 前，先提交当前需要保留的修改。定稿后按组里的合并流程进入 main。

<a id="section-4"></a>

## 回传 Phase I 正式结果

六格完成后，在运行它们的同一源码版本导出。

```bash
cfg=configs/phase1/ml1m_sasrec_seed42.json
python scripts/export_results.py --config "$cfg"
git status --short
```

导出器检查矩阵完整性、配置/数据/源码身份、指标范围、查询计数及共同 clean parent。checkpoint、查询文件的重算 hash、训练收敛和原论文数值一致性仍需独立审查。审阅 result JSON 和结果分析后，提交精简产物。

```bash
git add docs/RESULTS.md result/phase1/ml1m_sasrec_seed42
git diff --cached --stat
git commit -m "Record ML-1M SASRec phase I measured results"
git push origin HEAD
```

如果本地同时在编辑 main，可在云端运行完成后先创建独立结果分支，再执行上面的 add/commit/push，并在首次 push 使用 `git push -u origin HEAD`。例如结果分支名可用 `codex/results-ml1m-seed42`。之后 fetch 到本地审阅并合并。结果 JSON 内的 git_commit 保持实际运行代码的 SHA，结果提交有自己的 SHA。

<a id="section-5"></a>

## 回传 P0 诊断结果

T1–T5 输出的 result.json、config.json 和执行日志最初在 runs/research 中。检查原始数值及相应参数后，可以把精简 JSON 和执行命令复制到 result/research 下并提交。下面以 t5 为例。

```bash
source_dir=runs/research/ml1m_sasrec_seed42/t5
archive_dir=result/research/ml1m_sasrec_seed42/t5
mkdir -p "$archive_dir"
cp "$source_dir/config.json" "$source_dir/result.json" "$archive_dir/"
git add "$archive_dir/config.json" "$archive_dir/result.json"
git diff --cached --stat
git commit -m "Record ML-1M T5 feedback diagnostic"
git push origin HEAD
```

上传前检查文件大小与内容。T2–T4 的候选级 JSON 可能较大，必要时保留紧凑摘要及原始文件 hash、网盘路径，完整原件继续保存在 runs。正式指标来自实际运行输出，每种 seed 和协议保留独立结果目录。

<a id="section-6"></a>

## 获取服务器回传的结果

当结果提交在 main 上，本地可用下面的命令获取。

```powershell
Set-Location D:\ATRS
git status --short
git pull --ff-only origin main
```

当结果在独立分支上，先 fetch，再切换到对应分支审阅。若 push 提示 non-fast-forward，先 fetch 查看两端提交，合并或 rebase 当前尚未共享的提交后再推送。遇到具体冲突时，按文件保留双方需要的代码和实验记录。访问公开仓库的 clone/pull 可直接使用 HTTPS，push 使用有仓库写入权限的 GitHub SSH key 或凭据管理器认证。
