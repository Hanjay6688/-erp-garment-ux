"""Closed source/Original/workflow controls; zero DB/Native acceptance."""
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import importlib.util
import json
import os
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


admission = load('s05_lawful_source_controls', HERE/'admission.py')
workflow = load('s05_lawful_workflow_controls', HERE/'workflow_source.py')
failure = load('s05_lawful_first_controls', HERE/'first_failure.py')


class AdmissionControls(unittest.TestCase):
    def test_full_offline_exact_original_gate_old_ten_and_all_other_911_bytes(self):
        result = admission.offline()
        self.assertEqual(len(result['Native_case_ids']), 10)
        self.assertEqual(result['inherited']['prerequisite']['fresh_S05_runtime_credit'], 0)
        self.assertTrue(result['tracked_scope']['all_other_911_tracked_files_unchanged'])
        self.assertEqual(result['component_derivation']['counted_business_import_bindings'], 1)
        self.assertEqual(result['recipe_time_derivation']['counted_time_substitutions'], 2)
        self.assertEqual(result['Native_executions'], 0)
        self.assertEqual(result['database_calls'], 0)

    def test_exact_first_runtime_ten_incomplete_is_retained_not_promoted(self):
        result = failure.checked()
        self.assertEqual(len(result['raw']), 5)
        self.assertEqual(result['observed_case_counts'], {'INCOMPLETE': 10})
        self.assertFalse(result['package_gates']['writer_runtime'])
        self.assertFalse(result['outer_used_guard_field_present'])
        self.assertFalse(result['separate_committed_witness_field_present'])
        self.assertEqual(result['reader_preuse_reinstall'], 'PASS')
        self.assertFalse(result['success_prerequisite'])

    def test_exact_native_source_premise_without_runtime_credit(self):
        result = admission.native_premise()
        self.assertEqual(result['Native_editor_prosrc_sha256'], '6c8c701395ab74874e7cb2f3e78f9912f7380a5a3199cba069b1aec6db09cd85')
        self.assertTrue(result['original_BF_five_minute_guard_unchanged'])
        self.assertEqual(result['Native_executions'], 0)

    def test_own_untracked_source_is_not_silently_imported(self):
        path = HERE/'SOURCE_CONTROL_UNDECLARED.py'
        self.assertFalse(path.exists())
        try:
            path.write_text('raise RuntimeError("untracked control must never import")\n')
            with self.assertRaisesRegex(ValueError, 'UNDECLARED_OWN_SOURCE'):
                admission.offline()
        finally:
            path.unlink()

    def test_pins_reject_altered_bytes_and_symlink(self):
        with tempfile.TemporaryDirectory(prefix='s05_lawful_pin_control_') as name:
            repo = Path(name); file = repo/'only.py'; raw = b'# source\n'; file.write_bytes(raw)
            source = {'files': {'only.py': sha256(raw).hexdigest()}}
            admission.pins(repo, source)
            file.write_bytes(raw+b'# extra\n')
            with self.assertRaisesRegex(ValueError, 'PIN_CHANGED'): admission.pins(repo, source)
            file.unlink(); target = repo/'target.py'; target.write_bytes(raw); file.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'PIN_CHANGED'): admission.pins(repo, source)

    def test_full_workflow_five_bindings_always_cleanup_upload(self):
        text = (ROOT/workflow.PATH).read_text(); result = workflow.checked(text)
        self.assertEqual(result['parent_steps'], 64); self.assertEqual(result['child_steps'], 64)
        self.assertEqual(len(result['adapted_steps']), 5)
        self.assertTrue(result['unchanged_setup_all_Original_readers_clone_cleanup_upload_and_full_restore'])
        for before, after in ((workflow.BRANCH, 'main'), ('if: always()', 'if: success()'),
                              ('Clone the aligned AB state for install', 'Skip clone')):
            altered = text.replace(before, after, 1); self.assertNotEqual(altered, text)
            with self.assertRaisesRegex(ValueError, 'LAWFUL_WORKFLOW_CHANGED'): workflow.checked(altered)

    def test_no_local_confirmation_refuses_before_runtime_import(self):
        probe = load('s05_lawful_probe_confirm_control', HERE/'probe.py')
        with patch.dict(os.environ, {}, clear=True), patch.object(probe, 'runtime') as runtime:
            with self.assertRaisesRegex(ValueError, 'EXPLICIT_LOCAL_QUALIFICATION_CONFIRMATION_REQUIRED'):
                probe.execute()
            runtime.assert_not_called()

    def test_source_acceptance_flags_require_exact_types(self):
        source = json.loads((HERE/'SOURCE.json').read_bytes())
        for field, wrong in (('production_go', 0), ('independent_acceptance', 0), ('Native_executions', False)):
            with tempfile.TemporaryDirectory(prefix='s05_lawful_typed_source_') as name:
                here = Path(name); changed = dict(source)
                changed[field] = wrong
                (here/'SOURCE.json').write_text(json.dumps(changed))
                (here/'CONFIG.json').write_bytes((HERE/'CONFIG.json').read_bytes())
                with self.assertRaisesRegex(ValueError, 'SOURCE_NOT_ACCEPTANCE'):
                    admission.offline(ROOT, here)


if __name__ == '__main__':
    unittest.main(verbosity=2)
