# Codex 结构聚类 Skill

本仓库保持私有。当前交付版本为 **v0.1.0**，用于已有结构和评分数据的 TM-score 聚类、代表结构选取和三类雨云图。

## 使用自己的数据

- 从 [v0.1.0 使用入口](delivery/v0.1.0/README.md) 开始。
- 先看 [安装与卸载](delivery/v0.1.0/INSTALL.md)，再填写 [使用前配置清单](delivery/v0.1.0/使用前配置清单.md)。
- 完整交付文件位于 `delivery/v0.1.0/`；项目内可发现的 Skill 位于 `.agents/skills/bindcraft-structure-clustering/`，两处正式 Skill 内容一致。
- 默认阈值 **0.5**、主要簇至少 **5** 个成员、建议选取 **100** 个，均可配置。链 ID、命名映射、Average_dG 定义和选取容量需按自己的数据核对。
- 验证及限制见 [VALIDATION.md](delivery/v0.1.0/VALIDATION.md)。本仓库测试样例仅用于技术验收，不是使用者的默认输入。

私有仓库中的 v0.1.0 Release 提供独立 ZIP 及 SHA256 校验文件。未新增开源许可证，也未将仓库公开。测试目录与正式交付目录分开保留，研究结果不随本轮更新上传。

---

## Cloud acceptance workflow

This is a **private test repository**, not a public release or an assignment of a new open-source license.

## Contents

- `.agents/skills/bindcraft-structure-clustering/`: the unchanged delivered Skill, including the runtime scripts and configurable input/output instructions.
- `tests/fixtures/`: nine **CA-only** PDB coordinate subsets from supplied tutorial structures, a two-column metrics table, provenance hashes and a labelled verification matrix. Full-atom PDBs and full research datasets are not included.
- `external/TMalign.cpp`: the supplied TM-align source, with its original copyright, permission notice and citation header retained. Compile it inside the execution environment; no prebuilt binary is uploaded.
- `requirements-cloud.txt`: the versions chosen for this acceptance test.
- `scripts/setup_cloud.sh`: isolated dependency setup and compilation.
- `tests/run_cloud_acceptance.py`: real alignment, clustering, quota suggestion, representative selection, three plots and independent output consistency checks.

## Prepare and execute

Use Linux, Python 3.12 with a recent pip, and g++. In a Codex cloud environment setup conversation, request those tools and run from the checked-out repository:

```bash
bash scripts/setup_cloud.sh
.venv/bin/python tests/run_cloud_acceptance.py
```

The setup script uses an isolated `.venv`; it does not require ensurepip or install Python packages globally. It requires package-registry access during setup. `g++` must be available in the cloud container.

Every test creates a fresh timestamped directory under `results/`, with exact command records and a verification summary. A nonzero exit is a failure, not a request to substitute the included reference matrix. Read the summary and inspect the PNGs before declaring cloud acceptance passed.

The sample test overrides major min-n to 1 and representative total to 6. This does not alter the Skill defaults of threshold 0.5, major min-n 5 and suggested total 100. All-cluster and main-cluster figures are expected to match in this small sample because both use min-n 1.

## Cloud environment instructions

Create an environment using this repository and keep access **Only me**. During setup, install the pinned requirements and compile TMalign, then execute the test. Review actual logs and results before publishing the prepared environment. Publishing an environment snapshot is not permission to make this GitHub repository public.

For a separate fresh task after setup, ask Codex to read the Skill, run a new acceptance test, inspect the results and report actual paths, counts and limits. An environment merely being created is not evidence that the pipeline ran.

## Limits and ownership

The CA-only fixtures preserve the coordinates used by the alignment test but do not test full-atom parsing or serve as experiment-ready structures. Original full-atom examples were tested separately on the author's computer. There is no claim of new biological validation or broad-platform compatibility. The original local tutorial and research outputs remain outside this repository and unchanged. Review script ownership and redistribution permissions before any public release.
