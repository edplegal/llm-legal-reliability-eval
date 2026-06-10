#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================="
echo "Phase 1: Collecting responses"
echo "=============================="
python -m ai_eval.collect "$@"

echo ""
echo "=============================="
echo "Phase 2: Blinding responses"
echo "=============================="
python -m ai_eval.blind

echo ""
echo "=============================="
echo "Phase 3: Judging responses"
echo "=============================="
python -m ai_eval.judge "$@"

echo ""
echo "=============================="
echo "Phase 4: Analyzing results"
echo "=============================="
python -m ai_eval.analyze

echo ""
echo "Pipeline complete."
