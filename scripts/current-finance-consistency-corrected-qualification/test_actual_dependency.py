from datetime import date
import importlib.util,sys,unittest
from unittest.mock import patch
from pathlib import Path
import adapters

HERE=Path(__file__).resolve().parent


class ActualNativeHelperDependency(unittest.TestCase):
    def test_real_capture_factory_resolves_accepted_helper_before_database_use(self):
        spec=importlib.util.spec_from_file_location('corrected_real_Native_operations',HERE/'cases.py')
        module=importlib.util.module_from_spec(spec)
        # Retained command-line probes reject test-discovery arguments.
        with patch.object(sys,'argv',[__file__]):spec.loader.exec_module(module)
        base=module.base
        class NoDatabase:
            def __getattr__(self,name):raise AssertionError('DEPENDENCY_CHECK_MUST_NOT_TOUCH_DATABASE:'+name)
        original=base.capture.cases
        helper=base.chain.prepare_attendance_pools
        self.assertTrue(callable(helper));self.assertEqual(helper.__name__,'prepare_attendance_pools')
        with adapters.inputs(base,None,capture=True):
            cases=base.capture.cases(NoDatabase(),date(2026,10,28))
            self.assertEqual({key for key,_ in cases},set(base.capture.IDS))
            self.assertTrue(all(callable(operation)for _,operation in cases))
        self.assertIs(base.capture.cases,original)


if __name__=='__main__':unittest.main()
