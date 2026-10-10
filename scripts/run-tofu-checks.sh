#!/usr/bin/env bash
# For every directory holding *.tf files: tofu fmt -check, init -backend=false, validate.
set -u
cd "$(dirname "$0")/.." || exit 1
rc=0
dirs=$(find . \( -name .git -o -name .terraform \) -prune -o -name '*.tf' -type f -exec dirname {} \; | sort -u)
if [ -z "$dirs" ]; then
  echo "no OpenTofu directories found"
  exit 0
fi
for d in $dirs; do
  echo "== $d"
  tofu -chdir="$d" fmt -check -recursive -diff || { echo "fmt failed in $d"; rc=1; }
  tofu -chdir="$d" init -backend=false -input=false >/dev/null || { echo "init failed in $d"; rc=1; continue; }
  tofu -chdir="$d" validate -no-color || rc=1
done
echo "tofu checks exit code: $rc"
exit "$rc"
