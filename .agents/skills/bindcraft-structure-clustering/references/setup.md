# 环境准备

## 1. 先选择运行位置

Python、依赖、PDB、评分表和 TMalign 必须能被同一个执行环境访问。先确认是在原生 Windows、Linux、服务器还是 WSL 内执行；不把其中一个环境里的安装当成另一个环境也已具备。

- Python 3.10 或以上；运行依赖是 numpy、pandas、matplotlib、scipy、tqdm。
- 只做代表选取或绘图时不需要 TMalign；从 PDB 重新聚类时才需要它。
- TMalign 是独立可执行文件，不是 pip 包；TMscore 不等于 TMalign。本交付件不附带任何二进制，也不自动下载编译。
- Linux ELF 需要 Linux 运行环境；原生 Windows 应提供兼容的可执行文件。若选择 WSL，推荐在 WSL 内使用 Python、依赖和 Linux TMalign，并在该环境核对路径和访问能力。此前 Windows 沙箱跨 WSL 的桥接曾遇到权限失败，不作为通用安装方式，不修改沙箱权限来迁就它。

## 2. 在独立环境准备依赖

以下是用户主动选择安装时使用的命令；Skill 不会仅因读取文档就联网安装。已有环境可直接检查，无需重新创建。`$Skill`（PowerShell）或 `SKILL`（Bash）表示正式 Skill 文件夹的实际位置。

PowerShell：

```powershell
$Skill = 'C:\path\to\bindcraft-structure-clustering' # 先换成自己的实际路径
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw '创建环境失败' }
$Python = (Resolve-Path '.venv\Scripts\python.exe').Path
& $Python -m pip install -r (Join-Path $Skill 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败' }
```

其中 `$Skill` 需先设为正式 Skill 文件夹的绝对路径，例如 `C:\tools\skills\bindcraft-structure-clustering`。按实际位置替换，不使用作者电脑上的盘符。

Linux / WSL Bash：

```bash
set -euo pipefail
SKILL='/path/to/bindcraft-structure-clustering' # 先换成自己的实际路径
python3 -m venv .venv
PYTHON="$PWD/.venv/bin/python"
"$PYTHON" -m pip install -r "$SKILL/requirements.txt"
```

其中 `SKILL` 需先设为该环境内正式 Skill 文件夹的绝对路径。安装需要适当网络访问；失败时先处理依赖，不继续分析。

## 3. 检查依赖及接口

使用所选 Python 执行：

```text
python -c "import sys,numpy,pandas,matplotlib,scipy,tqdm; print(sys.version); print('imports OK')"
python /实际Skill路径/scripts/tmalign_clustering.py --help
```

这里的 `python` 与脚本路径要换成刚才选择的解释器和实际文件路径。不要误用 PATH 上另一份 Python。无图形界面的机器可设 `MPLBACKEND=Agg`；用显式解释器路径运行即可，无需修改全局环境。

## 4. TMalign 与成本

使用者自行准备系统兼容的 TMalign，并在将要运行聚类的同一环境做一次正常比对以确认它能输出两种长度归一化的 TM-score。不要仅检查“文件存在”。路径通过 `--tmalign` 提供；没有兼容工具时可以先做输入检查或处理已有结果，不把缺工具的聚类记为成功。

N 个结构需要 N(N−1)/2 次比对，矩阵占用随 N² 增长。workers 默认 1，按实际分配核数调整，避免直接启动大规模全量任务。输出目录有残留时使用新的运行目录，不自动删掉旧结果。

## 已观察版本，不是全平台保证

来源脚本的本机测试使用 Python 3.13.1、numpy 2.3.3、pandas 2.3.3、matplotlib 3.10.7、scipy 1.17.1、tqdm 4.67.1；测试图片另用 Pillow 12.3.0 校验。requirements.txt 没有锁死这些版本，也没有证明任意组合兼容。接收者应记录自己实际通过检查的环境；安装、升级和联网由用户按环境决定。
