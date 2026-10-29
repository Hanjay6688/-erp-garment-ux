"""Offline negative controls: rebinding a digest cannot authorize wider edits."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('s05_default_acl_exact_source_transition', HERE/'transition.py')
transition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transition)


@contextmanager
def candidate():
    source = json.loads((ROOT/(transition.COMPONENT+'SOURCE.json')).read_bytes())
    with tempfile.TemporaryDirectory(prefix='s05_acl_source_control_') as name:
        repo = Path(name)
        for path in source['files']:
            target = repo/path
            target.parent.mkdir(parents=True, exist_ok=True)
            if path in (transition.COMPONENT+'stage.py', transition.COMPONENT+'report.sql'):
                target.write_bytes((ROOT/path).read_bytes())
            else:
                target.symlink_to(ROOT/path)
        (repo/(transition.COMPONENT+'SOURCE.json')).write_text(json.dumps(source))
        yield repo, source


def write_manifest(repo, source):
    (repo/(transition.COMPONENT+'SOURCE.json')).write_text(json.dumps(source))


def repin(repo, source, name):
    path = transition.COMPONENT+name
    source['files'][path] = sha256((repo/path).read_bytes()).hexdigest()
    key = 'successor_stage_sha256' if name == 'stage.py' else 'successor_report_sql_sha256'
    source['installer_transition'][key] = source['files'][path]
    write_manifest(repo, source)


class SourceTransition(unittest.TestCase):
    def test_actual_exact_transition_and_zero_fresh_credit(self):
        actual = transition.check()
        self.assertEqual(actual['unchanged_component_files'], 25)
        self.assertEqual(actual['SQL']['SQL_substitutions'], 1)
        self.assertEqual(actual['SQL']['function_bodies_changed'], 0)
        self.assertEqual(len(actual['SQL']['function_body_sha256']), 5)
        self.assertEqual(actual['installer']['changed_functions'], ['installer_function_grants'])
        self.assertEqual(actual['Native_executions'], 0)
        self.assertFalse(actual['actual_CI_extra_tuple_identity_proven'])
        self.assertFalse(actual['production_go'])

    def test_extra_sql_edit_rejected_despite_repin(self):
        with candidate() as (repo, source):
            path = repo/(transition.COMPONENT+'report.sql')
            path.write_text(path.read_text().replace("p_limit not between 1 and 50", "p_limit not between 1 and 49", 1))
            repin(repo, source, 'report.sql')
            with self.assertRaisesRegex(ValueError, 'EXACT_ONE_NEW_PUBLIC_REVOKE_ONLY'):
                transition.check(repo)

    def test_removing_new_revoke_refused_despite_repin(self):
        with candidate() as (repo, source):
            path = repo/(transition.COMPONENT+'report.sql')
            path.write_text(path.read_text().replace(transition.REPLACEMENT, transition.ANCHOR, 1))
            repin(repo, source, 'report.sql')
            with self.assertRaisesRegex(ValueError, 'EXACT_ONE_NEW_PUBLIC_REVOKE_ONLY'):
                transition.check(repo)

    def test_dynamic_privilege_cleanup_refused_despite_repin(self):
        with candidate() as (repo, source):
            path = repo/(transition.COMPONENT+'stage.py')
            path.write_text(path.read_text().replace("expected.add((owner, 'authenticated', 'EXECUTE', False))",
                "expected.add((owner, 'authenticated', 'EXECUTE', False))\n            expected.add((owner, 's05_external', 'EXECUTE', False))", 1))
            repin(repo, source, 'stage.py')
            with self.assertRaisesRegex(ValueError, 'CHECKER_CHANGED_OUTSIDE_FAILURE_DIAGNOSTIC'):
                transition.check(repo)

    def test_verifier_change_refused_despite_repin(self):
        with candidate() as (repo, source):
            path = repo/(transition.COMPONENT+'stage.py')
            path.write_text(path.read_text().replace("raise ValueError('S05_ROLE_MEMBERSHIP')",
                                                    "raise ValueError('S05_CHANGED_ROLE_MEMBERSHIP')", 1))
            repin(repo, source, 'stage.py')
            with self.assertRaisesRegex(ValueError, 'FROZEN_STAGE_FUNCTION_CHANGED: verify'):
                transition.check(repo)

    def test_diagnostic_bound_change_refused_despite_repin(self):
        with candidate() as (repo, source):
            path = repo/(transition.COMPONENT+'stage.py')
            path.write_text(path.read_text().replace('limit = 16', 'limit = 160', 1))
            repin(repo, source, 'stage.py')
            with self.assertRaisesRegex(ValueError, 'BOUNDED_FAILURE_DIAGNOSTIC_REQUIRED'):
                transition.check(repo)

    def test_unrelated_component_pin_change_refused(self):
        with candidate() as (repo, source):
            source['files']['scripts/cp7_accessory_standard_report/cases.py'] = '0'*64
            write_manifest(repo, source)
            with self.assertRaisesRegex(ValueError, 'CURRENT_COMPONENT_PIN_CHANGED'):
                transition.check(repo)

    def test_new_file_scope_refused(self):
        with candidate() as (repo, source):
            source['files']['scripts/undeclared.py'] = '0'*64
            write_manifest(repo, source)
            with self.assertRaisesRegex(ValueError, 'COMPONENT_FILE_SCOPE_CHANGED'):
                transition.check(repo)

    def test_policy_or_case_id_metadata_change_refused(self):
        with candidate() as (repo, source):
            source['Native_case_ids'][0] = 'S05_FAKE_PASS'
            write_manifest(repo, source)
            with self.assertRaisesRegex(ValueError, 'COMPONENT_METADATA_OUTSIDE_TRANSITION_CHANGED'):
                transition.check(repo)


if __name__ == '__main__':
    unittest.main(verbosity=2)
