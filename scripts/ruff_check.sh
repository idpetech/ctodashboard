#!/bin/bash
# Lint and format check for production Python paths.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PATHS=(
    routes
    services
    config
    tests
    integrated_dashboard.py
)

if ! command -v ruff >/dev/null 2>&1; then
    echo "ruff not found; install with: pip install ruff"
    exit 1
fi

echo "Running ruff check..."
ruff check "${PATHS[@]}"

echo "Running ruff format --check..."
ruff format --check "${PATHS[@]}"

echo "Ruff checks passed."
