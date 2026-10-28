from pathlib import Path
import importlib.util,unittest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
s=importlib.util.spec_from_file_location('A_B_source_boundary',HERE/'check.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class SourceBoundary(unittest.TestCase):
 def test_exact_qualified_files(self):self.assertEqual(len(m.verify_files()['imports']),58)
 def test_changed_driver_refused(self):
  p='src/nativeStagedJob.ts'
  with self.assertRaises(AssertionError):m.verify_files({p:(ROOT/p).read_bytes()+b'\n'})
 def test_changed_finance_panel_refused(self):
  p='src/NativeAnalysisFinancePanel.tsx'
  with self.assertRaises(AssertionError):m.verify_files({p:(ROOT/p).read_bytes()+b'\n'})
if __name__=='__main__':unittest.main()
