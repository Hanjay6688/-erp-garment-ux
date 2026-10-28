from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util,json,shutil,unittest
import evidence

HERE=Path(__file__).resolve().parent


class ClosedCombinedBrowserAdapter(unittest.TestCase):
    def test_incomplete_or_unbound_runtime_cannot_unlock_browser(self):
        for config in ({},{'allow_database_execution':True},
            {'allow_database_execution':True,'accepted_combined':{'status':'INCOMPLETE'}},
            {'allow_database_execution':False,'accepted_combined':{'status':'PASS'}}):
            with self.subTest(config=config),self.assertRaisesRegex(ValueError,'ACTUAL_COMBINED_RUNTIME_REQUIRED'):
                evidence.gate(config)

    def test_both_original_and_package_bytes_are_bound(self):
        raw=b'{}';package=b'{}'
        binding=dict(bytes=2,sha256=sha256(raw).hexdigest(),package_bytes=2,package_sha256=sha256(package).hexdigest())
        for key in binding:
            changed=deepcopy(binding);changed[key]='changed'
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'ORIGINAL_BYTES_CHANGED'):
                evidence.bind(changed,raw,package)

    def test_all_database_interfaces_refuse_before_loading_backend(self):
        spec=importlib.util.spec_from_file_location('closed_combined_browser_adapter',HERE/'composition.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        class NoDatabase:
            def __getattr__(self,name):raise AssertionError('UNADMITTED_BROWSER_DATABASE_TOUCH:'+name)
        with TemporaryDirectory()as folder:
            closed=Path(folder);shutil.copy2(HERE/'evidence.py',closed/'evidence.py')
            (closed/'CONFIG.json').write_text(json.dumps(dict(allow_database_execution=False,accepted_combined=None)))
            with patch.object(module,'HERE',closed),patch.object(module,'parent',side_effect=AssertionError('UNADMITTED_BACKEND_LOAD')):
                for operation in (lambda:module.install(NoDatabase()),lambda:module.verify(NoDatabase(),{}),
                    lambda:module.rollback_preuse(NoDatabase(),{}),lambda:module.sources(),lambda:getattr(module,'catalog')):
                    with self.assertRaisesRegex(ValueError,'ACTUAL_COMBINED_RUNTIME_REQUIRED'):operation()


if __name__=='__main__':unittest.main()
