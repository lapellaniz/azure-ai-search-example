
#!/usr/bin/env bash
set -euo pipefail

cd "/workspaces/workspace" || true

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi
pip install -e .
pip install --disable-pip-version-check black ruff
