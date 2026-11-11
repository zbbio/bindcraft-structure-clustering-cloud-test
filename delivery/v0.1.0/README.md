# Codex 结构聚类 Skill

版本 **0.1.0** · 2026-11-11 · 私下交付与试用

分析你已经准备好的蛋白结构与评分数据：TM-score 聚类 → 建议配额 → 代表结构选取 → 三类雨云图。可以处理其他项目的数据，不要求使用作者示例，也不要求由 BindCraft 产生。结果解释需结合结构、链角色及评分定义。

## 从这里开始

1. 阅读 [安装与卸载](INSTALL.md)，选择直接让 Codex 读取，或安装到自己的项目／用户技能目录。
2. 阅读 [环境准备](bindcraft-structure-clustering/references/setup.md)，准备 Python 3.10+、运行依赖和兼容的 TMalign；只选取或画图时不需要 TMalign。
3. 填写 [自有数据清单](使用前配置清单.md)，按 [数据要求](bindcraft-structure-clustering/references/own-data.md) 核对名称、链和评分。
4. 把清单和任务交给 Codex；也可按 [逐阶段命令](bindcraft-structure-clustering/references/commands.md) 手动执行。
5. 在全新结果目录运行；核对成员总数、配额、名单及图中实际展示数量。

## 参数与数据要求

| 项目 | 默认值／约定 | 调整方式 |
|---|---|---|
| TM-score 阈值 | 0.5 | --threshold；改变后重新聚类 |
| 主要簇最小成员数 | 5 | --min-n；同步建议配额、主要簇图和叠加图 |
| 代表结构建议总数 | 100 | --total；须满足纳入簇数 ≤ 总数 ≤ 纳入成员总数 |
| 比较链 | 脚本默认 B | --chain；必须按自己的数据核对 |
| 聚类排序评分 | Average_dG，越小越优先 | 固定字段及方向；其他含义不能只靠改列名套用 |

全部簇图使用 min-n=1；主要簇相关图使用本次确认的 min-n。小样本可明确调整 min-n 和总数。输入目录第一层的 PDB 都会参与；CSV 不控制筛选范围。PDB 名称和评分名称的归一化规则不同，运行前需核对碰撞与匹配，详见数据要求。

## 给 Codex 的请求

先检查：

> 读取本包 bindcraft-structure-clustering/SKILL.md，并读取我填写的配置清单。先只读检查输入、名称匹配、链、评分含义、依赖和预计比对次数，报告缺项；先不运行计算。

确认后执行：

> 按我确认的路径和参数运行。我接受本次建议配额的分配方法和总数；容量满足时生成并采用建议配额，完成选取和三图。使用全新结果目录，报告各阶段命令、参数、成员数、选中数及叠加匹配数。阶段失败时停止下游。

只需已有结果的选取或绘图时，明确所需阶段，并提供同次结果，不必重新聚类。

## 包内内容

```text
bindcraft-structure-clustering-v0.1.0/
├─ README.md                  使用入口
├─ INSTALL.md                 安装、识别与卸载
├─ 使用前配置清单.md           填路径和本次参数；不是自动读取的配置
├─ VALIDATION.md              已验证内容、环境与限制
├─ VERSION                    包版本
├─ MANIFEST.json              文件大小与 SHA256
├─ SHA256SUMS.txt             内容校验清单
└─ bindcraft-structure-clustering/
   ├─ SKILL.md
   ├─ agents/openai.yaml
   ├─ requirements.txt
   ├─ scripts/                六个入口及 output_guard.py
   └─ references/             环境、数据、命令、方法、来源
```

本包不含 PDB、研究统计表、TMalign、测试结果和本机维护材料。历史云测试详情浓缩在 VALIDATION.md；该验证不代表任意新数据均可直接通过。评分标签还需与自己的 Average_dG 定义相符。

保留来源说明；本次未新增开源许可证。包外 ZIP 的 SHA256 位于同名 .zip.sha256 文件。MANIFEST.json 不包含其自身及 SHA256SUMS.txt，SHA256SUMS.txt 包含 MANIFEST.json、排除其自身，避免自引用。
