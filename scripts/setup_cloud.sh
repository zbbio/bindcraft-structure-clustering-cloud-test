#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if command -v python3.12 >/dev/null 2>&1; then PYTHON=python3.12; else PYTHON=python3; fi
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 11), "Acceptance environment requires Python >=3.11; Python 3.12 preferred"'
command -v g++ >/dev/null
"$PYTHON" -m venv --without-pip --system-site-packages .venv
"$PYTHON" -m pip --python "$ROOT/.venv/bin/python" install -r requirements-cloud.txt
mkdir -p .tools
g++ -O3 -o .tools/TMalign external/TMalign.cpp
"$ROOT/.venv/bin/python" -c 'import numpy,pandas,matplotlib,scipy,tqdm,PIL; print("Python dependencies import successfully")'
printf '%s\n' 'Setup complete. Run: .venv/bin/python tests/run_cloud_acceptance.py'
