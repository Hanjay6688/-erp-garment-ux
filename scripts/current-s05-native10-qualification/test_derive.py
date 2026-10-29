"""Offline derivation controls only; no runtime/product imports."""
from hashlib import sha256
from pathlib import Path
import ast
import importlib.util
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('s05_test_derivation', HERE/'derive.py')
derive = importlib.util.module_from_spec(spec); spec.loader.exec_module(derive)


class Derivation(unittest.TestCase):
    def test_only_declared_source_binding_and_metadata_change(self):
        raw = (HERE/'frozen_vendor/probe.py').read_bytes()
        result, proof = derive.derive(raw)
        ast.parse(result)
        self.assertEqual(proof['original_sha256'], derive.PARENT_SHA256)
        self.assertEqual(proof['derived_sha256'], sha256(result.encode()).hexdigest())
        self.assertEqual(proof['counted_changes'], 6)
        recovered = result
        for before, after in reversed(derive.REPLACEMENTS):
            self.assertEqual(recovered.count(after), 1)
            recovered = recovered.replace(after, before, 1)
        self.assertEqual(recovered.encode(), raw)

    def test_every_restore_and_package_operation_remains(self):
        result, _ = derive.derive((HERE/'frozen_vendor/probe.py').read_bytes())
        for fragment in ("'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install", "'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta",
                         "'FIRST_FINANCE_DELTA',product.install_delta", "'FINANCE_DELTA_PREUSE_INVERSE',product.rollback_delta_preuse",
                         "'SECOND_FINANCE_DELTA',product.install_delta", 'database._restore,PRE_DUMP', 'role_cleanup.restore_roles',
                         'baseline_full22_all_rows_all_sequences_equal', 'previous.restore_state.prove', 'baseline_advisors_equal',
                         "package.run('install')"):
            self.assertIn(fragment, result)
        self.assertNotIn("report['actual_two_session_races']=3", result)
        self.assertNotIn("report['real_Auth_HTTP_qualified']=True", result)

    def test_a_modified_parent_is_rejected_before_execution(self):
        raw = (HERE/'frozen_vendor/probe.py').read_bytes()
        for changed in (raw+b'\n', raw.replace(b'baseline_advisors_equal', b'weakened_advisor_gate'), raw.replace(b'product.verify(cur,STATE)', b'None')):
            with self.assertRaisesRegex(ValueError, 'EXACT_VENDOR41C_ENGINE_BYTES'):
                derive.derive(changed)


if __name__ == '__main__':
    unittest.main()
