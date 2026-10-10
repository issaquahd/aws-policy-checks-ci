#!/usr/bin/env bash
# Run every gating check locally, exactly as CI does. Prints one exit code per check.
set -u
cd "$(dirname "$0")/.." || exit 1
overall=0
for check in run-cfn-lint.sh run-tofu-checks.sh run-policy-checks.sh; do
  echo "################ $check"
  "scripts/$check"
  rc=$?
  echo "################ $check -> exit $rc"
  [ "$rc" -eq 0 ] || overall=1
done
echo "ALL CHECKS exit code: $overall"
exit "$overall"
