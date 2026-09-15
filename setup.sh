#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -c 'import sys; assert sys.version_info[:2] == (3,12), "Use Python 3.12 for the pinned release environment"'
python3 -m venv .venv
env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1 .venv/bin/python -m pip install -r requirements-lock.txt
