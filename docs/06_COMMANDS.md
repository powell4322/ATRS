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

默认使用 configs/gro_first，按 seed 42、43、44 运行 ML-1M + SASRec 的 GRO × Random/DFME/BECOME，共九格，采用正常训练轮次。入口自动训练基础 clean teacher 和 GRO，并导出结果。None 攻击格暂缓，改进方案稍后确定。

服务器直接运行正式实验，不执行 smoke。

<a id="section-3"></a>

## 本机检查

仅在本机项目根目录的 PowerShell 执行：

```powershell
& .venv\Scripts\python.exe -m pytest -q
& .venv\Scripts\python.exe scripts\smoke.py --device cpu
```

这些检查使用本机 CPU，不作为正式实验结果。
