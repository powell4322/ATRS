# 06 环境配置与运行命令

[00 导航](00_INDEX.md) · [06 命令](06_COMMANDS.md) · [09 待确认](09_IMPLEMENTATION_AND_TBD.md) · [上一页 05](05_DATA_AND_BUDGET.md) · [下一页 07](07_PROGRESS.md)

**本页目录**

- [服务器环境配置](#section-1)
- [服务器正式运行](#section-2)
- [本机检查](#section-3)

<a id="section-1"></a>

## 服务器环境配置

以下 Bash 命令均在服务器项目根目录 ~/workspace/ATRS 执行。使用预装 CUDA PyTorch 的镜像，要求 Python >=3.10、PyTorch >=2.3 且 <3.0。首次使用执行：

```bash
bash setup.sh
```

脚本只安装本项目，复用预装依赖。

<a id="section-2"></a>

## 服务器正式运行

```bash
python -u scripts/run_formal.py
```

默认使用 configs/gro_first/ml1m_sasrec_seed42.json，仅运行 ML-1M + SASRec、seed42 的 DFME × None/GRO 两格。基础 clean/GRO 教师可接续并复用已完成的 checkpoint，结束后自动导出配对结果。不会自动运行 Random、BECOME、Ours 或其他种子。

保留当前配置的代理 1000 轮，尚未擅自改成 200/300；下一次租卡前先按 07 审阅这一预算。基础教师与 GRO 有 patience=30 的早停，代理当前无早停。已完成的四个教师文件需放回 runs/gro_first/ml1m_sasrec_seed42/checkpoints，原配置保持不变；只有 Git clone 不会得到这些权重。

命令行 --defenses/--attacks 选择本次任务，优先于配置内的历史选择；未指定时采用启动器的 DFME × None/GRO 默认值。训练参数仍以 JSON 为准。

服务器直接运行正式实验，不执行 smoke。

<a id="section-3"></a>

## 本机检查

仅在本机项目根目录的 PowerShell 执行：

```powershell
& .venv\Scripts\python.exe -m pytest -q
& .venv\Scripts\python.exe scripts\smoke.py --device cpu
```

这些检查使用本机 CPU，不作为正式实验结果。
