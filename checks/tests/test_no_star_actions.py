import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from checks import no_star_actions as nsa

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
FIX = os.path.join(HERE, "fixtures")


def run_main(*paths):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = nsa.main(["no_star_actions.py"] + list(paths))
    return rc, out.getvalue(), err.getvalue()


class CheckPolicyTest(unittest.TestCase):
    def test_full_wildcard_flagged(self):
        policy = {"Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}
        self.assertEqual(len(nsa.check_policy(policy)), 1)

    def test_service_wildcard_flagged(self):
        policy = {"Statement": {"Sid": "S3", "Effect": "Allow", "Action": ["s3:*"], "Resource": "*"}}
        findings = nsa.check_policy(policy)
        self.assertEqual(len(findings), 1)
        self.assertIn('S3: Allow "s3:*"', findings[0])

    def test_partial_wildcard_allowed(self):
        policy = {"Statement": [{"Effect": "Allow", "Action": ["s3:Get*", "s3:List*"], "Resource": "*"}]}
        self.assertEqual(nsa.check_policy(policy), [])

    def test_deny_wildcard_allowed(self):
        policy = {"Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]}
        self.assertEqual(nsa.check_policy(policy), [])

    def test_not_action_with_allow_flagged(self):
        policy = {"Statement": [{"Effect": "Allow", "NotAction": "iam:*", "Resource": "*"}]}
        self.assertIn("NotAction", nsa.check_policy(policy)[0])

    def test_intrinsic_action_skipped(self):
        policy = {"Statement": [{"Effect": "Allow", "Action": {"Ref": "ActionParam"}, "Resource": "*"}]}
        self.assertEqual(nsa.check_policy(policy), [])


class FileTest(unittest.TestCase):
    def test_good_json_policy_is_clean(self):
        self.assertEqual(nsa.check_file(os.path.join(REPO, "policies", "read-one-bucket.json")), [])

    def test_bad_json_policy_flagged(self):
        findings = nsa.check_file(os.path.join(REPO, "samples", "bad", "wildcard-policy.json"))
        self.assertEqual(len(findings), 1)

    def test_nested_cfn_json_policy_found(self):
        findings = nsa.check_file(os.path.join(FIX, "cfn-wildcard.json"))
        self.assertEqual(len(findings), 1)
        self.assertIn("Resources.Role.Properties.Policies[0].PolicyDocument", findings[0])
        self.assertIn('"sqs:*"', findings[0])

    def test_main_exit_codes(self):
        self.assertEqual(run_main(os.path.join(REPO, "policies"))[0], 0)
        rc, out, _ = run_main(os.path.join(REPO, "samples", "bad", "wildcard-policy.json"))
        self.assertEqual(rc, 1)
        self.assertIn("1 finding(s)", out)

    def test_yaml_without_pyyaml_fails_closed(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "t.yaml")
            with open(path, "w") as fh:
                fh.write("Resources: {}\n")
            with mock.patch.object(nsa, "HAVE_YAML", False):
                rc, _, err = run_main(tmp)
            self.assertEqual(rc, 3)
            self.assertIn("PyYAML", err)
        finally:
            shutil.rmtree(tmp)

    def test_usage_without_args(self):
        self.assertEqual(run_main()[0], 2)


@unittest.skipUnless(nsa.HAVE_YAML, "PyYAML not installed; CI installs it")
class YamlTemplateTest(unittest.TestCase):
    def test_bad_yaml_template_flagged(self):
        findings = nsa.check_file(os.path.join(REPO, "samples", "bad", "wildcard-role.yaml"))
        self.assertEqual(len(findings), 2)

    def test_good_templates_dir_clean(self):
        self.assertEqual(run_main(os.path.join(REPO, "templates"))[0], 0)

    def test_cfn_short_tags_parse(self):
        doc = nsa.load_document(os.path.join(REPO, "templates", "s3-reader-role.yaml"))
        resource = doc["Resources"]["ReaderRole"]["Properties"]["Policies"][0]["PolicyDocument"]
        self.assertEqual(resource["Statement"][0]["Resource"], {"Fn::Sub": "arn:${AWS::Partition}:s3:::${BucketName}"})


class SanityTest(unittest.TestCase):
    def test_fixture_is_valid_json(self):
        with open(os.path.join(FIX, "cfn-wildcard.json")) as fh:
            self.assertIn("Resources", json.load(fh))


if __name__ == "__main__":
    unittest.main()
