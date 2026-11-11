# 路径配置与逐阶段命令

这些是供使用者填写路径后执行的命令，不表示已经替你运行。所有 `C:\path\to` 与 `/path/to` 都是路径占位示例，先换成自己的绝对路径。同一运行的下游变量只指向本次 RESULT，不回退到作者示例。详见 [自己的数据](own-data.md) 和 [环境](setup.md)。

## 推荐结果结构

```text
自己的项目/
├─ input_pdb/                  仅放本批 PDB
├─ metrics.csv                 评分表单独存放
└─ runs/run_001/               每次新的运行目录
   ├─ clustering/             聚类脚本创建；不要预先创建此子目录
   │  ├─ binder_chain_B_pdbs/  名称随 --chain 变化
   │  ├─ global_tm_matrix.csv
   │  ├─ clusters.csv
   │  ├─ centers.csv
   │  ├─ clustering.txt
   │  └─ cluster_pairwise_tm_matrices/
   ├─ selection/
   │  ├─ plan.csv
   │  └─ selected.csv
   └─ visualization/
      ├─ 01_all_clusters.png
      ├─ 01_all_parsed.csv
      ├─ 02_main_clusters.png
      ├─ 02_main_parsed.csv
      └─ 03_main_selected.png
```

## PowerShell

### A. 填路径与参数，先创建后处理父目录

```powershell
$Skill = 'C:\path\to\bindcraft-structure-clustering'
$Python = 'C:\path\to\.venv\Scripts\python.exe'
$PdbDir = 'C:\path\to\my_project\input_pdb'
$Metrics = 'C:\path\to\my_project\metrics.csv'
$TMalign = 'C:\path\to\tools\TMalign.exe'
$Run = 'C:\path\to\my_project\runs\run_001'
$Chain = 'B' # 先核对自己的结构
$Threshold = 0.5
$Workers = 1
$MinN = 5
$Total = 100
$Result = Join-Path $Run 'clustering'
$Selection = Join-Path $Run 'selection'
$Figures = Join-Path $Run 'visualization'
if (Test-Path -LiteralPath $Run) { throw '请选择全新的运行目录' }
New-Item -ItemType Directory -Path $Selection, $Figures -ErrorAction Stop | Out-Null
$env:MPLBACKEND = 'Agg'
$env:PYTHONUTF8 = '1'
```

### B. 从 PDB 重新聚类（已有结果时跳过）

```powershell
& $Python (Join-Path $Skill 'scripts/tmalign_clustering.py') --pdb-dir $PdbDir --metrics $Metrics --tmalign $TMalign --output $Result --chain $Chain --threshold $Threshold --workers $Workers
if ($LASTEXITCODE -ne 0) { throw '聚类失败，停止下游' }
```

已有结果时，在继续下面步骤前将 `$Result` 设为已确认的那一次聚类目录；仍用新 `$Run` 下的 selection 和 visualization 存后处理结果，不重复执行 B，不修改旧聚类目录。

### C. 建议配额；核对后再执行 D

```powershell
& $Python (Join-Path $Skill 'scripts/suggest_quota.py') --centers (Join-Path $Result 'centers.csv') --total $Total --min-n $MinN --output (Join-Path $Selection 'plan.csv')
if ($LASTEXITCODE -ne 0) { throw '配额建议失败，停止下游' }
```

审阅 plan.csv 的名额、纳入范围和总和；用户已明确接受本次默认建议时可继续，否则先确认。自备配额表可跳过 C，D 的 `--plan` 显式指向它；字段必须是 `cluster_id,recommended_n_for_MD`。

### D. 代表结构选取

```powershell
& $Python (Join-Path $Skill 'scripts/select_representatives.py') --clustering (Join-Path $Result 'clustering.txt') --matrix (Join-Path $Result 'global_tm_matrix.csv') --plan (Join-Path $Selection 'plan.csv') --output (Join-Path $Selection 'selected.csv')
if ($LASTEXITCODE -ne 0) { throw '代表选取失败，停止下游' }
```

### E. 按“全部、主要、主要＋已选”的顺序画图

```powershell
& $Python (Join-Path $Skill 'scripts/plot_all_clusters.py') (Join-Path $Result 'clustering.txt') --min-n 1 --out-csv (Join-Path $Figures '01_all_parsed.csv') --out-png (Join-Path $Figures '01_all_clusters.png')
if ($LASTEXITCODE -ne 0) { throw '全部簇图失败' }
& $Python (Join-Path $Skill 'scripts/plot_main_clusters.py') (Join-Path $Result 'clustering.txt') --min-n $MinN --out-csv (Join-Path $Figures '02_main_parsed.csv') --out-png (Join-Path $Figures '02_main_clusters.png')
if ($LASTEXITCODE -ne 0) { throw '主要簇图失败' }
& $Python (Join-Path $Skill 'scripts/plot_selected_overlay.py') --clustering (Join-Path $Result 'clustering.txt') --selected (Join-Path $Selection 'selected.csv') --min-n $MinN --output (Join-Path $Figures '03_main_selected.png')
if ($LASTEXITCODE -ne 0) { throw '叠加图失败' }
```

## Linux / WSL Bash

以下块按阶段执行。在同一个 Bash 会话中先设置变量；已有结果时跳过聚类行并将 RESULT 指向该次现有结果。这里不会安装工具，也不会修改执行权限；TMalign 须事先已可正常运行。

```bash
set -euo pipefail
SKILL='/path/to/bindcraft-structure-clustering'
PYTHON='/path/to/venv/bin/python'
PDB_DIR='/path/to/my_project/input_pdb'
METRICS='/path/to/my_project/metrics.csv'
TMALIGN='/path/to/tools/TMalign'
RUN='/path/to/my_project/runs/run_001'
CHAIN='B'
THRESHOLD='0.5'
WORKERS='1'
MIN_N='5'
TOTAL='100'
RESULT="$RUN/clustering"
SELECTION="$RUN/selection"
FIGURES="$RUN/visualization"
if [ -e "$RUN" ]; then printf '%s\n' '请选择全新的运行目录' >&2; exit 1; fi
mkdir -p "$SELECTION" "$FIGURES"
export MPLBACKEND=Agg PYTHONUTF8=1
```

```bash
"$PYTHON" "$SKILL/scripts/tmalign_clustering.py" --pdb-dir "$PDB_DIR" --metrics "$METRICS" --tmalign "$TMALIGN" --output "$RESULT" --chain "$CHAIN" --threshold "$THRESHOLD" --workers "$WORKERS"
```

```bash
"$PYTHON" "$SKILL/scripts/suggest_quota.py" --centers "$RESULT/centers.csv" --total "$TOTAL" --min-n "$MIN_N" --output "$SELECTION/plan.csv"
```

审阅／确认配额后：

```bash
"$PYTHON" "$SKILL/scripts/select_representatives.py" --clustering "$RESULT/clustering.txt" --matrix "$RESULT/global_tm_matrix.csv" --plan "$SELECTION/plan.csv" --output "$SELECTION/selected.csv"
"$PYTHON" "$SKILL/scripts/plot_all_clusters.py" "$RESULT/clustering.txt" --min-n 1 --out-csv "$FIGURES/01_all_parsed.csv" --out-png "$FIGURES/01_all_clusters.png"
"$PYTHON" "$SKILL/scripts/plot_main_clusters.py" "$RESULT/clustering.txt" --min-n "$MIN_N" --out-csv "$FIGURES/02_main_parsed.csv" --out-png "$FIGURES/02_main_clusters.png"
"$PYTHON" "$SKILL/scripts/plot_selected_overlay.py" --clustering "$RESULT/clustering.txt" --selected "$SELECTION/selected.csv" --min-n "$MIN_N" --output "$FIGURES/03_main_selected.png"
```

## 输出核对与常见问题

- clustering 成员总数、centers 簇大小之和、矩阵行列名称应一致；全局矩阵应对称、对角线为 1。
- selected.csv 的 pdb 应唯一、来自同次结果；逐簇人数与配额相同，每个纳入簇保留中心。
- 叠加图报告名单总数、聚类匹配数、展示匹配数，图例以展示匹配数为准；范围外名单不会显示红圈。
- 两张 parsed.csv 保存全部解析成员，即使主要簇图只画人数达标的簇。单成员或恒定评分的簇不估计 KDE。
- 超额配额、总数小于纳入簇数、没有主要簇：明确调整 TOTAL 或 MIN_N，再使用新的输出文件；不静默改小总数。
- 文件已存在：换运行目录或输出文件名，不删除、覆盖旧结果。中途失败不是完整结果，停止下游。
- 评分表只控制分数匹配，不控制 PDB 筛选；名称匹配失败先核查规则，不猜测对应关系。
- 来源与使用边界见 [provenance.md](provenance.md)；本交付件不依赖安装目录外的 tests 文件。
