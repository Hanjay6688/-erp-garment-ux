"""Real-entry closure and explicit plan controls; no Root or copy execution."""
from pathlib import Path
from unittest.mock import patch
import importlib.util
import json
import os
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('current_browser_copy_control', HERE / 'browser_access.py')
access = importlib.util.module_from_spec(spec);spec.loader.exec_module(access)


class BrowserAccessControls(unittest.TestCase):
    def test_real_closed_inputs_precede_copy_product_or_mode_inspection(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('File inspected')), \
                patch.object(access.entry, 'load', side_effect=AssertionError('Copy mode inspected')):
            with self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
                access.run(object(), object(), object(), {})
            with self.assertRaisesRegex(ValueError, 'FULL_NATIVE_LIFECYCLE_PENDING'):
                with access.copy_scope(object(), object(), object()):self.fail('Unadmitted copy entered')

    def test_native_only_plan_cannot_silently_activate_browser_copies(self):
        native_only = access.entry.PLAN_FILE.read_bytes()
        originals = (b'EXPLICIT_PROTOCOL_BYTES_NOT_A_ROOT', b'NO_SOURCE_ACCEPTANCE', native_only, {})
        with patch.object(access.entry, 'actual_inputs', return_value=originals):
            with self.assertRaisesRegex(ValueError, 'EXPLICIT_COMPLETE_PLAN_ADOPTION_REQUIRED'):
                access.actual_inputs()
        plan = json.loads(native_only)
        plan.update(required_browser_case_ids=list(access.IDS), fresh_real_Auth_browser_required=True)
        values = (*originals[:2], json.dumps(plan).encode(), {})
        with patch.object(access.entry, 'actual_inputs', return_value=values), \
                patch.dict(os.environ, GITHUB_REF=access.entry.BRANCH):
            self.assertEqual(access.actual_inputs(), values)
        self.assertTrue(all(getattr(access.entry.admission, key) is None for key in access.entry.admission.GATES))


if __name__ == '__main__':unittest.main()
