"""Real retained artifacts plus refusal controls; zero database execution."""
from pathlib import Path
import importlib.util,json,os,unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('backend_acceptance',HERE/'verify.py')
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)

class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg=json.loads((HERE/'CONFIG.json').read_bytes())
        old=Path(os.environ['CP7_RETAINED11C_DIRECTORY']);new=Path(os.environ['CP7_FRESH3194_DIRECTORY'])
        source=json.loads(Path(os.environ['CP7_CURRENT_BACKEND_DECLARATION']).read_bytes())
        cls.inputs=[(old/cfg['retained']['name']).read_bytes(),(old/cfg['retained']['package_name']).read_bytes(),
            (new/cfg['fresh']['name']).read_bytes(),(new/cfg['fresh']['package_name']).read_bytes(),source['current_installation']]
    def test_exact_actual_pair_and_current_source_accepted(self):
        result=verify.checked(*self.inputs)
        self.assertEqual(result['status'],'PASS_BACKEND_COMPONENT_FOR_B_BINDING')
        self.assertEqual((result['retained_groups'],result['fresh_groups']),(6,1))
        self.assertEqual(result['historical_11c_status'],'INCOMPLETE')
        self.assertFalse(result['frontend_or_Auth_browser_accepted'])
    def test_changed_retained_original_refused(self):
        inputs=list(self.inputs);inputs[0]+=b'\n'
        with self.assertRaisesRegex(AssertionError,'EXACT_BYTES_REQUIRED:retained Original'):verify.checked(*inputs)
    def test_changed_fresh_original_refused(self):
        inputs=list(self.inputs);inputs[2]+=b'\n'
        with self.assertRaisesRegex(AssertionError,'EXACT_BYTES_REQUIRED:fresh Original'):verify.checked(*inputs)
    def test_missing_fresh_package_refused(self):
        inputs=list(self.inputs);inputs[3]=b''
        with self.assertRaisesRegex(AssertionError,'EXACT_BYTES_REQUIRED:fresh package'):verify.checked(*inputs)
    def test_another_backend_declared_as_current_refused(self):
        inputs=list(self.inputs);inputs[4]=dict(inputs[4],unqualified_backend_delta=True)
        with self.assertRaisesRegex(AssertionError,'CURRENT_BACKEND_SOURCE_MISMATCH'):verify.checked(*inputs)

if __name__=='__main__':unittest.main()
