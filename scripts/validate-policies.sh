#!/usr/bin/env bash
# OPTIONAL CI step: IAM Access Analyzer validate-policy on every policies/*.json.
# Needs AWS credentials (OIDC in CI). Fails on ERROR or SECURITY_WARNING findings.
set -u
cd "$(dirname "$0")/.." || exit 1
export AWS_REGION="${AWS_REGION:-us-east-2}"
export AWS_DEFAULT_REGION="$AWS_REGION"
rc=0
for f in policies/*.json; do
  [ -f "$f" ] || continue
  echo "== $f"
  aws accessanalyzer validate-policy --policy-type IDENTITY_POLICY \
    --policy-document "file://$f" \
    --query 'findings[].[findingType,issueCode,findingDetails]' --output table || { rc=1; continue; }
  # shellcheck disable=SC2016  # backticks are JMESPath literals
  blocking=$(aws accessanalyzer validate-policy --policy-type IDENTITY_POLICY \
    --policy-document "file://$f" \
    --query 'length(findings[?findingType==`ERROR` || findingType==`SECURITY_WARNING`])' --output text) || { rc=1; continue; }
  if [ "$blocking" != "0" ]; then
    echo "  $blocking blocking finding(s) in $f"
    rc=1
  fi
done
echo "validate-policy exit code: $rc"
exit "$rc"
