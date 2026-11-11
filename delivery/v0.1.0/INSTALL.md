# 安装、识别与卸载

只安装内层 bindcraft-structure-clustering 文件夹；根目录 README、验证摘要和校验文件保留在交付包中。以下路径是占位示例，先换成自己环境内的路径。安装 Skill 不等于安装 Python、依赖或 TMalign，后者见 references/setup.md。

## 方式一：直接读取，不安装

解压到自己的工具目录，在 Codex 中明确要求读取内层 SKILL.md，再提供数据路径及任务。该方式不依赖自动发现，用于首次核查或临时试用。直接读取的目录需保留完整 scripts 和 references。

## 方式二：项目内安装

在项目的 .agents/skills 下放置内层 Skill 文件夹。以下 PowerShell 与 Bash 命令二选一，目标已存在时停止，避免叠加版本。

```powershell
$Source = 'C:\path\to\bindcraft-structure-clustering-v0.1.0\bindcraft-structure-clustering'
$Project = 'C:\path\to\my-project'
$SkillsDir = Join-Path $Project '.agents/skills'
$Destination = Join-Path $SkillsDir 'bindcraft-structure-clustering'
if (-not (Test-Path -LiteralPath (Join-Path $Source 'SKILL.md'))) { throw '请核对来源目录' }
if (Test-Path -LiteralPath $Destination) { throw '目标版本已存在，请先处理原版本' }
New-Item -ItemType Directory -Path $SkillsDir -Force -ErrorAction Stop | Out-Null
Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -ErrorAction Stop
Get-Item -LiteralPath (Join-Path $Destination 'SKILL.md')
```

```bash
set -euo pipefail
SOURCE='/path/to/bindcraft-structure-clustering-v0.1.0/bindcraft-structure-clustering'
PROJECT='/path/to/my-project'
SKILLS_DIR="$PROJECT/.agents/skills"
DESTINATION="$SKILLS_DIR/bindcraft-structure-clustering"
test -f "$SOURCE/SKILL.md"
if [ -e "$DESTINATION" ]; then printf '%s\n' '目标版本已存在，请先处理原版本' >&2; exit 1; fi
mkdir -p "$SKILLS_DIR"
cp -R "$SOURCE" "$DESTINATION"
test -f "$DESTINATION/SKILL.md"
```

## 用户级安装

如需跨项目使用，采用同样的复制方式，将 SkillsDir 换成当前用户的 .agents/skills：PowerShell 可用 Join-Path $HOME '.agents/skills'；Bash 可用 "$HOME/.agents/skills"。检查项目目录、父目录及用户目录是否已有同名版本，避免重复发现。本文不自动迁移旧 .codex/skills 安装。

Codex 官方技能文档列出项目 .agents/skills 及用户 $HOME/.agents/skills 发现位置：
https://developers.openai.com/codex/skills/

核对日期 2026-11-11。同名技能可能同时出现在选择器中。更新未出现时，可重启 Codex 后再检查；不要因界面未立即更新就重复复制。

## 使用与识别

在项目里请求：使用 $bindcraft-structure-clustering，先只读检查我的配置清单。核对 Codex 实际读取的 SKILL.md 路径是否为刚安装的目录。随后按 README 配置环境与数据。

本轮只验证了复制后文件一致及六个命令入口；没有在接收者的 Codex 会话中验收自动发现。

## 升级与卸载

升级前记录旧版本安装位置并将旧 Skill 文件夹移至自己的备份位置，确认原目标已不存在后再复制新版。结果、PDB、CSV 和 Python 环境保存在 Skill 目录外。

卸载时先确认准确的安装目录，只移除本次安装的 bindcraft-structure-clustering 文件夹。既有数据、结果和单独的 Python 环境无需随 Skill 移除。需要恢复旧版时把旧文件夹放回原安装位置；核对实际读取路径。
