#!/usr/bin/env bash
# Wildcard-action check on gating paths, plus the checker's own unit tests.
# PYTHON can point at an interpreter that has PyYAML (needed for YAML templates).
set -u
cd "$(dirname "$0")/.." || exit 1
PY="${PYTHON:-python3}"
rc=0
"$PY" checks/no_star_actions.py templates policies || rc=1
"$PY" -m unittest discover -s checks/tests -t . || rc=1
echo "policy checks exit code: $rc"
exit "$rc"
