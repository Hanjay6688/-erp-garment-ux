"""Source/workflow/refusal controls only; no DB and no fabricated product sources."""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import gzip
import importlib.util
import json
import os
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = str(HERE.relative_to(ROOT))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


admission = load('s05_acl_test_admission', HERE/'admission.py')
workflow = load('s05_acl_test_workflow', HERE/'workflow_source.py')
failure = load('s05_acl_test_retained_failure', HERE/'first_failure.py')


@contextmanager
def source_candidate():
    source = json.loads((HERE/'SOURCE.json').read_bytes())
    with tempfile.TemporaryDirectory(prefix='s05_acl_qualifier_control_') as name:
        repo = Path(name)
        for relative in source['files']:
            target = repo/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(ROOT/relative)
        here = repo/NS
        (here/'SOURCE.json').write_text(json.dumps(source))
        yield repo, here, source


class SourceAndWorkflowControls(unittest.TestCase):
    def test_actual_offline_closure_real_vendor_prerequisite_zero_credit(self):
        result = admission.offline()
        self.assertEqual(len(result['Native_case_ids']), 10)
        self.assertEqual(result['prerequisite']['fresh_S05_runtime_credit'], 0)
        self.assertEqual(result['retained_b0_failure']['actual_S05_Native_cases'], 0)
        self.assertFalse(result['retained_b0_failure']['package_gates']['writer_runtime'])
        self.assertEqual(result['engine_derivation']['counted_changes'], 6)
        self.assertTrue(result['old_qualifier_files_and_manifests_unchanged'])
        self.assertEqual(result['Native_executions'], 0)
        self.assertEqual(result['database_calls'], 0)

    def test_repinning_old_component_oracle_refused(self):
        with source_candidate() as (repo, here, source):
            relative = 'scripts/cp7_accessory_standard_report/cases.py'
            path = repo/relative
            raw = path.read_bytes()+b'\n# forbidden old callback edit\n'
            path.unlink()
            path.write_bytes(raw)
            source['files'][relative] = sha256(raw).hexdigest()
            (here/'SOURCE.json').write_text(json.dumps(source))
            with self.assertRaisesRegex(ValueError, 'B0_FROZEN_QUALIFIER_PARENT_OR_ORACLE_REPINNED'):
                admission.offline(repo, here)

    def test_repinning_old_qualifier_file_refused(self):
        with source_candidate() as (repo, here, source):
            relative = admission.OLD+'/component.py'
            path = repo/relative
            raw = path.read_bytes()+b'\n# forbidden inherited witness edit\n'
            path.unlink()
            path.write_bytes(raw)
            source['files'][relative] = sha256(raw).hexdigest()
            (here/'SOURCE.json').write_text(json.dumps(source))
            with self.assertRaisesRegex(ValueError, 'B0_FROZEN_QUALIFIER_PARENT_OR_ORACLE_REPINNED'):
                admission.offline(repo, here)

    def test_missing_pinned_file_fails_before_runtime(self):
        with source_candidate() as (repo, here, source):
            (repo/'scripts/cp7_accessory_standard_report/stage.py').unlink()
            with self.assertRaises(FileNotFoundError):
                admission.offline(repo, here)

    def test_retained_b0_is_zero_native_failure_and_exact_four_originals(self):
        result = failure.checked()
        self.assertEqual(result['observed_outer_wrapper'], 1)
        self.assertEqual(result['Native_PASS_credit'], 0)
        self.assertEqual(len(result['original_bytes']), 4)
        self.assertFalse(result['actual_CI_extra_tuple_identity_proven'])
        self.assertTrue(result['full_outer_restoration'])

    def test_mutated_b0_report_refused(self):
        with tempfile.TemporaryDirectory(prefix='s05_b0_raw_control_') as name:
            here = Path(name)
            retained = here/'retained-b0'
            retained.mkdir()
            for filename in failure.PINS:
                raw = (HERE/'retained-b0'/(filename+'.gz')).read_bytes()
                (retained/(filename+'.gz')).write_bytes(raw)
            path = retained/'CP7_S05_ACCESSORY_STANDARD_NATIVE10.json.gz'
            raw = json.loads(gzip.decompress(path.read_bytes()))
            raw['status'] = 'PASS'
            path.write_bytes(gzip.compress(json.dumps(raw).encode(), mtime=0))
            with self.assertRaisesRegex(ValueError, 'B0_ORIGINAL_BYTES_CHANGED'):
                failure.checked(here)

    def test_actual_exact_workflow_uses_narrow_leaf_and_full_restore(self):
        text = (ROOT/workflow.PATH).read_text()
        result = workflow.checked(text)
        self.assertEqual(result['parent_step_count'], result['child_step_count'])
        self.assertEqual(len(result['adapted_steps']), 5)
        self.assertEqual(result['root_publish_branch'], workflow.BRANCH)
        self.assertTrue(result['inherited_setup_source_prerequisites_clone_cleanup_package_and_full_restore_unchanged'])

    def test_workflow_other_branch_refused(self):
        text = (ROOT/workflow.PATH).read_text().replace(workflow.BRANCH, 'main', 1)
        with self.assertRaisesRegex(ValueError, 'GENERATED_WORKFLOW_CHANGED'):
            workflow.checked(text)

    def test_workflow_cleanup_or_clone_change_refused(self):
        text = (ROOT/workflow.PATH).read_text()
        for old, new in (('if: always()', 'if: success()'),
                         ('Clone the aligned AB state for install', 'Skip aligned clone')):
            changed = text.replace(old, new, 1)
            self.assertNotEqual(changed, text)
            with self.assertRaisesRegex(ValueError, 'GENERATED_WORKFLOW_CHANGED'):
                workflow.checked(changed)

    def test_no_confirm_refuses_before_runtime_import(self):
        probe = load('s05_acl_test_probe', HERE/'probe.py')
        with patch.dict(os.environ, {}, clear=True), patch.object(probe, 'runtime') as runtime:
            with self.assertRaisesRegex(ValueError, 'EXPLICIT_LOCAL_QUALIFICATION_CONFIRMATION_REQUIRED'):
                probe.execute()
            runtime.assert_not_called()

    def test_retained_cli_argument_context_restores_exact_argv_on_error(self):
        boundary = load('s05_acl_test_original_argument_boundary', ROOT/admission.OLD/'import_argv.py')
        original = sys.argv
        value = ['new-qualified-source-check', '--runtime']
        try:
            sys.argv = value
            with self.assertRaisesRegex(RuntimeError, 'LOCAL_SOURCE_IMPORT_FAILURE'):
                with boundary.source_import_arguments():
                    self.assertEqual(sys.argv, [value[0]])
                    raise RuntimeError('LOCAL_SOURCE_IMPORT_FAILURE')
            self.assertIs(sys.argv, value)
            self.assertEqual(value, ['new-qualified-source-check', '--runtime'])
        finally:
            sys.argv = original


if __name__ == '__main__':
    unittest.main(verbosity=2)
