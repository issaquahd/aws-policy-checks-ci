#!/usr/bin/env bash
# Run cfn-lint on every CloudFormation template (*.yaml / *.yml with
# AWSTemplateFormatVersion or a top-level Resources: key) in the repo.
set -u
cd "$(dirname "$0")/.." || exit 1
templates=()
while IFS= read -r f; do
  if grep -q -E '^(AWSTemplateFormatVersion|Resources):' "$f"; then
    templates+=("$f")
  fi
done < <(find . \( -name .git -o -name .terraform -o -name .github -o -name node_modules \) -prune -o \
  \( -name '*.yaml' -o -name '*.yml' \) ! -name '.gitlab-ci.yml' -type f -print | sort)
if [ "${#templates[@]}" -eq 0 ]; then
  echo "no CloudFormation templates found"
  exit 0
fi
printf 'cfn-lint: %s\n' "${templates[@]}"
cfn-lint "${templates[@]}"
rc=$?
echo "cfn-lint exit code: $rc"
exit "$rc"
