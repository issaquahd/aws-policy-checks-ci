#!/usr/bin/env python3
"""Fail when an IAM policy statement allows "*" or "service:*" actions.

Usage: python3 checks/no_star_actions.py PATH [PATH ...]

PATH may be a file or a directory (searched recursively for .json, .yaml,
.yml). Each file can be a bare IAM policy document or a CloudFormation
template; every nested object with a "Statement" key is checked.

Flags, for Effect "Allow" statements only:
  * Action "*"                 (full wildcard)
  * Action "<service>:*"       (service-wide wildcard)
  * NotAction with Allow       (allows everything except a list)
Partial wildcards such as "s3:Get*" are allowed.

Exit codes: 0 clean, 1 findings, 3 a YAML file could not be read because
PyYAML is not installed (fails closed rather than skipping silently).
"""
import json
import os
import re
import sys

try:
    import yaml  # PyYAML; installed in CI. Optional locally for JSON-only use.
    HAVE_YAML = True
except ImportError:  # pragma: no cover - depends on environment
    yaml = None
    HAVE_YAML = False

SERVICE_WILDCARD = re.compile(r"^[A-Za-z0-9-]+:\*$")
EXTENSIONS = (".json", ".yaml", ".yml")
SKIP_DIRS = {".git", ".terraform", "node_modules", "__pycache__"}


class YamlUnavailable(Exception):
    pass


def _cfn_yaml_loader():
    """A SafeLoader that turns CloudFormation short tags (!Sub, !Ref, ...) into dicts."""
    class CfnLoader(yaml.SafeLoader):
        pass

    def construct_tag(loader, tag_suffix, node):
        key = "Fn::" + tag_suffix if tag_suffix not in ("Ref", "Condition") else tag_suffix
        if isinstance(node, yaml.ScalarNode):
            value = loader.construct_scalar(node)
        elif isinstance(node, yaml.SequenceNode):
            value = loader.construct_sequence(node, deep=True)
        else:
            value = loader.construct_mapping(node, deep=True)
        return {key: value}

    CfnLoader.add_multi_constructor("!", construct_tag)
    return CfnLoader


def load_document(path):
    with open(path) as fh:
        text = fh.read()
    if path.endswith(".json"):
        return json.loads(text)
    if not HAVE_YAML:
        raise YamlUnavailable(path)
    return yaml.load(text, Loader=_cfn_yaml_loader())  # noqa: S506 - SafeLoader subclass


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def iter_policy_documents(node, location="$"):
    """Yield (location, policy_document) for every dict that has a Statement key."""
    if isinstance(node, dict):
        if "Statement" in node and isinstance(node["Statement"], (list, dict)):
            yield location, node
        for key, value in node.items():
            yield from iter_policy_documents(value, "%s.%s" % (location, key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from iter_policy_documents(value, "%s[%d]" % (location, index))


def check_policy(policy):
    """Return a list of human-readable findings for one policy document."""
    findings = []
    for index, stmt in enumerate(_as_list(policy.get("Statement"))):
        if not isinstance(stmt, dict) or stmt.get("Effect") != "Allow":
            continue
        label = stmt.get("Sid") or "Statement[%d]" % index
        if "NotAction" in stmt:
            findings.append("%s: Allow with NotAction (allows everything not listed)" % label)
        for action in _as_list(stmt.get("Action")):
            if not isinstance(action, str):
                continue  # intrinsic function; cannot judge statically
            if action == "*":
                findings.append('%s: Allow "*" (every action in every service)' % label)
            elif SERVICE_WILDCARD.match(action):
                findings.append('%s: Allow "%s" (every action in the service)' % (label, action))
    return findings


def check_file(path):
    document = load_document(path)
    results = []
    for location, policy in iter_policy_documents(document):
        for finding in check_policy(policy):
            results.append("%s: %s: %s" % (path, location, finding))
    return results


def iter_files(paths):
    for path in paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
                for name in sorted(files):
                    if name.endswith(EXTENSIONS):
                        yield os.path.join(root, name)
        elif os.path.isfile(path):
            yield path


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    findings = []
    checked = 0
    for path in iter_files(argv[1:]):
        try:
            findings.extend(check_file(path))
        except YamlUnavailable:
            print("ERROR: %s is YAML but PyYAML is not installed (pip install pyyaml)" % path,
                  file=sys.stderr)
            return 3
        checked += 1
    for line in findings:
        print(line)
    print("no_star_actions: %d file(s) checked, %d finding(s)" % (checked, len(findings)))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
