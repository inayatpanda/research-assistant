#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/files
cd apps/api
.venv/bin/alembic upgrade head
echo "DB ready at data/research.db"
