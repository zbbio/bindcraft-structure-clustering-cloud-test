# Structure-clustering Skill: private cloud acceptance

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
