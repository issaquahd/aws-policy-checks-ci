# aws-policy-checks-ci

Policy checks that run on every push, identically in **GitHub Actions** and **GitLab CI**, and that you can prove locally before you push.

## What it checks

| Job | What runs | Gating paths |
|---|---|---|
| `cfn-lint` | `scripts/run-cfn-lint.sh`: cfn-lint on every CloudFormation `*.yaml` / `*.yml` in the repo | all templates, including `samples/bad/` (lint-clean on purpose) |
| `no-star-actions` | `scripts/run-policy-checks.sh`: `checks/no_star_actions.py` flags `Allow` statements with `"*"`, `"service:*"` or `NotAction`; then the checker's unit tests | `templates/`, `policies/` |
| `opentofu` | `scripts/run-tofu-checks.sh`: `tofu fmt -check`, `tofu init -backend=false`, `tofu validate` in every dir with `*.tf` | `tofu/` |
| `access-analyzer` (optional, **off by default**) | `scripts/validate-policies.sh`: `aws accessanalyzer validate-policy` on `policies/*.json`; fails on ERROR or SECURITY_WARNING findings | `policies/` |

`samples/bad/wildcard-role.yaml` shows why the second job exists. It passes cfn-lint with zero findings, yet grants `"*"` and `"s3:*"`. The unit tests assert that the checker flags it. It sits outside the gating paths so the repo's own pipeline stays green.

Architecture: [`diagram.mmd`](diagram.mmd).

## Prove it locally

```bash
# needs cfn-lint, tofu, and a python with PyYAML (cfn-lint's own interpreter works)
PYTHON=python3 scripts/check-all.sh          # every gating check, one exit code each
python3 checks/no_star_actions.py samples/bad  # exit 1: 3 findings (JSON + YAML; YAML needs PyYAML)
python3 -m unittest discover -s checks/tests -t .
```

Without PyYAML the checker **fails closed** (exit 3) on YAML input rather than silently skipping it.

## Enabling the optional Access Analyzer job (OIDC, no stored keys)

Nothing here creates AWS resources. To turn the job on, create the following yourself in the target account.

1. **OIDC identity provider**
   * GitHub: URL `https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`
   * GitLab: URL `https://gitlab.com` (or your instance), audience `sts.amazonaws.com`
2. **IAM role**, permissions limited to `access-analyzer:ValidatePolicy` on `*`, with a trust policy pinned to one repo and branch:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:<owner>/<repo>:ref:refs/heads/main"
      }
    }
  }]
}
```

   For GitLab use the `gitlab.com` provider with conditions `gitlab.com:aud` = `sts.amazonaws.com` and `gitlab.com:sub` = `project_path:<group>/<project>:ref_type:branch:ref:main`.
3. **Variables**
   * GitHub (Settings > Secrets and variables > Variables): `ENABLE_ACCESS_ANALYZER=true`, `AWS_ROLE_ARN=<role arn>`, optional `AWS_REGION` (default `us-east-2`).
   * GitLab (Settings > CI/CD > Variables): `ENABLE_ACCESS_ANALYZER=true`, `AWS_ROLE_ARN=<role arn>`.

Never put a role ARN in the workflow file; it lives in a variable.

## Deploy / verify / teardown

There is nothing to deploy. Verification is `scripts/check-all.sh` locally or a pipeline run. Teardown is deleting the OIDC role and provider if you created them.

## The learning

Linters check that a template is well formed. They do not check that it is safe. A lint-clean template can still grant `"*"`. Put a cheap, unit-tested policy rule next to cfn-lint and `tofu validate` in the same pipeline, and prove it fails on a known-bad sample. Add Access Analyzer's validate-policy over OIDC when you want AWS's own policy grammar and security checks. That way no long-lived keys sit in CI.

## Notes

* `.terraform.lock.hcl` is not committed. Its provider hashes trip this repo family's 12-digit-number leak scan. CI regenerates it on each run, and the provider is pinned to `~> 5.0`.
* OpenTofu is pinned to `1.13.1` in both pipelines.

---

Independent project by Alex Alvord, CloudLab Works. MIT licensed.
