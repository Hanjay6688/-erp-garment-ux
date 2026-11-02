from pathlib import Path
import ast
import importlib.util
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class MovingAverageQualificationSource(unittest.TestCase):
    def test_complete_package_derivation_is_exact(self):
        module=load('sku_movavg_test_derive',HERE/'derive.py')
        raw=(ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        code,proof=module.derive(raw)
        self.assertEqual(proof['counted_changes'],6)
        self.assertTrue(proof['complete_install_preuse_used_guard_backup_restore_roles_data_sequences_advisors_retained'])
        self.assertIn("cases[runner.CASE]['actual_Native_cases']",code)
        compile(code,'vendor-probe-derived','exec')

    def test_five_declared_cases_and_runner_obligations(self):
        tree=ast.parse((ROOT/'scripts/cp7_sku_moving_average/qualification_cases.py').read_text())
        ids=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='IDS'for t in n.targets))
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(len(ids),5)
        runner=(HERE/'runner.py').read_text()
        for token in('native.strict_group','product.verify','rollback_delta_preuse','product.USED_ERROR','exact_public_catalog'):
            self.assertIn(token,runner)

if __name__=='__main__':unittest.main()
