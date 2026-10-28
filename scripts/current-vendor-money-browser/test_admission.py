"""Local refusal controls; no database, Auth, browser or delivery claims."""
from pathlib import Path
import ast,importlib.util,json,subprocess,tempfile,unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('money_browser_admission_controls',HERE/'admission.py')
admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission)


class AdmissionControls(unittest.TestCase):
    def test_absent_complete_backend_is_closed_before_product_access(self):
        class Product:
            def sources(self):raise AssertionError('PRODUCT_MUST_NOT_BE_ACCESSED')
        with tempfile.TemporaryDirectory()as directory:
            here=Path(directory);(here/'CONFIG.json').write_text('{"accepted_backend11":null}')
            (here/'SOURCE.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'CLOSED_COMPLETE_BACKEND11_REQUIRED'):
                admission.admitted(ROOT,here,Product())

    def test_only_exact_two_label_changes_are_allowed(self):
        cfg=json.loads((HERE/'CONFIG.json').read_bytes())
        before=subprocess.check_output(['git','-C',str(ROOT),'show',cfg['base_head']+':src/LaundryBdPanel.tsx']).decode()
        after=(ROOT/'src/LaundryBdPanel.tsx').read_text()
        admission.client_label(before,after)
        with self.assertRaisesRegex(ValueError,'ONLY_DECLARED_CLIENT_LABEL'):
            admission.client_label(before,after.replace('amount: normalizeMoney(amount)','amount: "0.00"',1))
        with self.assertRaisesRegex(ValueError,'ONLY_DECLARED_CLIENT_LABEL'):
            admission.client_label(before,before)

    def test_three_case_declarations_agree(self):
        cfg=json.loads((HERE/'CONFIG.json').read_bytes())
        source=json.loads((HERE/'SOURCE.json').read_bytes())
        tree=ast.parse((HERE/'runner.py').read_text())
        ids=next(ast.literal_eval(node.value)for node in tree.body if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='IDS'for t in node.targets))
        self.assertEqual(list(ids),cfg['browser_case_ids']);self.assertEqual(list(ids),source['browser_case_ids'])
        text=(HERE/'cases.mjs').read_text()
        self.assertIn('export const IDS='+json.dumps(list(ids),separators=(',',':')).replace('"',"'"),text)


if __name__=='__main__':unittest.main()
