#!/usr/bin/env bash
# Everything that can be verified without an API key, in one command. Takes a few minutes.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
step() { printf '\n==== %s ====\n' "$1"; }

step "0. upstream repo at the pinned commit"
bash scripts/setup_upstream.sh

step "1. reproduce the paper's Table 4 from its released runs"
$PY scripts/august_audit/run_exp1.py | tail -4

step "2. measure the parser bug on the released data"
$PY scripts/phantom_codes.py | sed -n '1,26p'

step "3. the fix patch changes exactly what it should"
$PY scripts/verify_patch.py

step "4. validate the Turkish stimulus table (read-only)"
$PY scripts/validate_stimuli.py

step "5. pipeline module against a mock model"
$PY tests/test_mock.py 2>&1 | grep -E "Mean r|agreement|figure" || true

step "6. every notebook cell against a mock model"
$PY tests/test_notebook.py 2>&1 | grep -E "ALL CELLS RAN|Traceback|Error" || true
