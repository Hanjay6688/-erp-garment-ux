import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('managed_recovery_prepared_guard',HERE/'source_check.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)

class SourceTests(unittest.TestCase):
    def test_complete_prepared_product_and_frozen_base(self):
        self.assertEqual(guard.admitted()['status'],'PASS')

    def test_changed_digest_and_status_are_refused(self):
        manifest=json.loads((HERE/'SOURCE.json').read_bytes())
        one=next(iter(manifest['files']));manifest['files'][one]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'SOURCE_CHANGED'):guard.admitted(manifest=manifest)
        manifest['status']='NATIVE_PASS'
        with self.assertRaisesRegex(ValueError,'PREPARED_SOURCE_REQUIRED'):guard.admitted(manifest=manifest)

if __name__=='__main__':unittest.main()
