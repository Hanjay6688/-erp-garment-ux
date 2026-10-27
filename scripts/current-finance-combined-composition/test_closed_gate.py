from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util,json,unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch
import shutil
import evidence


class IndependentAdmissionBoundaries(unittest.TestCase):
    def test_prepared_or_incomplete_result_cannot_open_gate(self):
        for config in ({},{'allow_database_execution':True},
            {'allow_database_execution':True,'accepted_consistency':{'status':'INCOMPLETE'}},
            {'allow_database_execution':False,'accepted_consistency':{'status':'PASS'}}):
            with self.subTest(config=config),self.assertRaisesRegex(ValueError,'ACTUAL_CONSISTENCY_PASS_REQUIRED'):
                evidence.gate(config)

    def test_original_bytes_and_package_are_both_bound(self):
        raw=b'{}';package=b'{}'
        binding=dict(bytes=2,sha256=sha256(raw).hexdigest(),package_bytes=2,package_sha256=sha256(package).hexdigest())
        for key in binding:
            changed=deepcopy(binding);changed[key]='changed'
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'ORIGINAL_CHANGED'):
                evidence.accepted(changed,raw,package,{},{} )

    def test_installer_and_delta_refuse_before_touching_cursor(self):
        path=Path(__file__).with_name('composition.py')
        spec=importlib.util.spec_from_file_location('closed_combined_gate_subject',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        class NoDatabase:
            def __getattr__(self,name):raise AssertionError('UNQUALIFIED_DATABASE_TOUCH:'+name)
        # These negative cases keep explicit closed inputs even after a real
        # accepted prerequisite is later bound to the repository configuration.
        with TemporaryDirectory()as folder:
            closed=Path(folder)
            shutil.copy2(path.with_name('evidence.py'),closed/'evidence.py')
            (closed/'PREREQUISITES.json').write_text(json.dumps({'allow_database_execution':False,'accepted_consistency':None}))
            with patch.object(module,'HERE',closed):
                for call in (lambda:module.install(NoDatabase()),lambda:module.install_delta(NoDatabase(),{})):
                    with self.assertRaisesRegex(ValueError,'ACTUAL_CONSISTENCY_PASS_REQUIRED'):call()


if __name__=='__main__':unittest.main()
