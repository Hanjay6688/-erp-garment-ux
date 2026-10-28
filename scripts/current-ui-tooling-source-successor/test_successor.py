from pathlib import Path
import importlib.util,unittest
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('tested_UI_source_successor',HERE/'ui_binding.py');u=importlib.util.module_from_spec(s);s.loader.exec_module(u)
class SuccessorTests(unittest.TestCase):
    def test_exact_panel_tests_and_original_source_oracles(self):
        value=u.checked();self.assertEqual(value['current_unit_DOM_tests'],29);self.assertFalse(value['backend_or_browser_unlock']);self.assertTrue(u.derivation())
    def test_old_or_unqualified_panel_and_test_are_refused(self):
        for path in (u.PANEL,u.TEST):
            with self.subTest(path=path),self.assertRaises(AssertionError):u.checked(overrides={path:b'changed'})
        with self.assertRaises(AssertionError):u.checked(overrides={u.PANEL:u.git('show',u.BASE+':'+u.PANEL)})
    def test_changed_or_missing_actual_test_evidence_is_refused(self):
        for name in ('SOURCE_SUCCESSOR.json','LOCAL_TEST_RESULTS.json'):
            with self.subTest(name=name),self.assertRaises(AssertionError):u.checked(overrides={u.EVIDENCE+name:b'{}'})
    def test_other_source_checks_cannot_change(self):
        with self.assertRaises(AssertionError):u.derivation(actual=(HERE/'check.py').read_text()+'\n# unlisted\n')
if __name__=='__main__':unittest.main()
