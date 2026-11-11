# Private Codex cloud acceptance repository

Use `.agents/skills/bindcraft-structure-clustering/SKILL.md` for structure-analysis tasks. This repository tests existing benign structural-analysis software, not upstream design, optimization or experiments.

- Keep the repository private. Do not publish it or grant access to others.
- Formal Skill files are copied unchanged from the delivered candidate. Do not edit them to force a test to pass.
- The nine fixtures are clearly labelled CA-only coordinate subsets derived from supplied tutorial structures, with two-column metrics. They are not full-atom inputs or new independent biological data. The reference matrix is verification-only; every run must compute 36 real TMalign pairs from the PDB fixtures.
- Prepare dependencies with `bash scripts/setup_cloud.sh`, then run `.venv/bin/python tests/run_cloud_acceptance.py`. A prepared environment can skip setup. Do not silently install into the user's system environment.
- Save fresh outputs under `results/`; record exact commands, stdout, stderr and exit codes. Stop downstream if any stage fails. Never reuse saved matrices as newly calculated results.
- The test explicitly uses chain B, threshold 0.5, workers 1, min-n 1 and total 6. The Skill defaults remain 0.5/5/100. Cloud execution is only verified after the commands and output validation actually pass in the cloud environment.
- No credentials, historical logs, full research datasets, prebuilt executables or generated outputs belong in Git. Do not open a PR or push generated results unless the user asks.
