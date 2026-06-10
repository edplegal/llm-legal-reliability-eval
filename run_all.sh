#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Prefer the project venv if present.
PYTHON="${PYTHON:-python}"
if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
fi

usage() {
    cat <<EOF
Usage: ./run_all.sh [--resume] [--dry-run] [--samples N] [--seed N]

  --resume     Skip work already present in the output files (collect, judge)
  --dry-run    Print the plan without making API calls (collect, judge)
  --samples N  Samples per (prompt, model) cell (collect only; default 1)
  --seed N     Presentation-shuffle seed (blind only; fixed default)
EOF
    exit 1
}

COLLECT_ARGS=()
JUDGE_ARGS=()
BLIND_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --resume|--dry-run)
            COLLECT_ARGS+=("$1")
            JUDGE_ARGS+=("$1")
            shift
            ;;
        --samples)
            [[ $# -ge 2 ]] || usage
            COLLECT_ARGS+=("$1" "$2")
            shift 2
            ;;
        --seed)
            [[ $# -ge 2 ]] || usage
            BLIND_ARGS+=("$1" "$2")
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            ;;
    esac
done

phase() {
    echo ""
    echo "=============================="
    echo "$1"
    echo "=============================="
}

phase "Phase 1: Collecting responses"
"$PYTHON" -m ai_eval.collect ${COLLECT_ARGS[@]+"${COLLECT_ARGS[@]}"}

phase "Phase 2: Blinding responses"
"$PYTHON" -m ai_eval.blind ${BLIND_ARGS[@]+"${BLIND_ARGS[@]}"}

phase "Phase 3: Judging responses"
"$PYTHON" -m ai_eval.judge ${JUDGE_ARGS[@]+"${JUDGE_ARGS[@]}"}

phase "Phase 4: Analyzing results"
"$PYTHON" -m ai_eval.analyze

phase "Phase 5: Generating report"
"$PYTHON" -m ai_eval.report

echo ""
echo "Pipeline complete."
