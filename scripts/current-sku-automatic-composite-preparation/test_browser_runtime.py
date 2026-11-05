"""Browser package preconditions cannot create ERP or admission credit."""
from pathlib import Path
import importlib.util
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sku_exact_browser_package_preflight', HERE / 'browser_runtime.py')
runtime = importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)


class BrowserRuntimeControls(unittest.TestCase):
    def test_whole_proven_child_process_and_browser_lifecycle_is_preserved(self):
        text, proof = runtime.derive()
        self.assertEqual(text.encode(), runtime.TARGET.read_bytes())
        self.assertTrue(proof['complete_original_recovered'])
        self.assertEqual(proof['reversible_routes'], 2)
        self.assertEqual(proof['actual_SQL_executed'], 0)
        self.assertEqual(proof['actual_Auth_requests'], 0)
        self.assertIn("'--single-checkout',workspace,name", text)
        self.assertIn('scripts/current-sku-automatic-composite-preparation/browser.mjs', text)
        self.assertIn(runtime.RECEIPT, text)

    def test_donor_byte_drift_is_refused_before_any_runtime_action(self):
        with self.assertRaisesRegex(ValueError, 'EXACT_PROVEN_TWO_CHECKOUT_PREFLIGHT_SOURCE'):
            runtime.derive(runtime.DONOR.read_bytes() + b'\n')


if __name__ == '__main__':
    unittest.main()
