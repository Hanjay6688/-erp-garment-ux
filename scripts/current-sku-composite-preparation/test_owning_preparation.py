"""Exact-source and local Git controls; no ERP/HTTP/browser qualification."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import ExitStack
from unittest.mock import patch
import ast,json,subprocess,unittest
import sku_current_parent_admission as admission
import sku_current_parent_assembly as assembly
import sku_current_parent_component as component
import sku_current_parent_package as package
import sku_current_parent_runtime as runtime

HERE=Path(__file__).resolve().parent
RAW_PACKAGE=(HERE.parents[1]/package.ORIGINAL).read_bytes()
RAW_COMPONENT=(HERE/'original_runner.py.txt').read_bytes()
GATES=('PARENT_HEAD','PARENT_TREE','PARENT_ROOT_PIN','PARENT_SOURCE_PIN','PARENT_MODULE_PIN',
    'SKU_HEAD','SKU_TREE','SKU_ROOT_PIN','SKU_SOURCE_PIN','RUNTIME_ENTRY')


class OwningPreparation(unittest.TestCase):
    def test_all_closed_entrypoints_refuse_before_files_modules_or_Git(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('premature file read')),\
            patch.object(subprocess,'check_output',side_effect=AssertionError('premature Git')):
            for operation in [runtime.actual_inputs,runtime.runtime,
                lambda:component.load_prepared(object(),b'unaccepted',b'unaccepted',object())]:
                with self.assertRaisesRegex(ValueError,'ROOT_AND_OWNING_ENTRY_PENDING'):operation()

    def test_every_one_of_ten_missing_gates_refuses_before_file_access(self):
        for missing in GATES:
            with ExitStack()as stack:
                for name in GATES:stack.enter_context(patch.object(admission,name,None if name==missing else 'explicit-model-value'))
                stack.enter_context(patch.object(Path,'read_bytes',side_effect=AssertionError('premature file read')))
                with self.subTest(missing=missing),self.assertRaisesRegex(ValueError,'ROOT_AND_OWNING_ENTRY_PENDING'):
                    runtime.actual_inputs()
        self.assertTrue(all(getattr(admission,name)is None for name in GATES))

    def test_complete_original_package_and_child_component_recovered(self):
        for module,raw in[(package,RAW_PACKAGE),(component,RAW_COMPONENT)]:
            text,proof=module.derive(raw);self.assertEqual(proof['exact_routes'],3)
            for before,after in reversed(module.REPLACEMENTS):text=text.replace(after,before,1)
            self.assertEqual(text.encode(),raw)
            with self.assertRaisesRegex(ValueError,'EXACT_.*ORIGINAL'):module.derive(raw+b'\n')

    def test_source_declaration_cannot_promote_closed_or_partial_admission(self):
        with TemporaryDirectory()as directory,patch.object(assembly,'HERE',Path(directory)):
            path=Path(directory)/'SOURCE.json'
            declaration=dict(contract='cp7.current-mandor-SKU-parent-bridge-preparation.v1',
                actual_parent_adopted=False,all_admission_values_unset=True,actual_composite_cases=0,
                production_go=False,files={})
            path.write_text(json.dumps(declaration));assembly.source_manifest()
            declaration['actual_parent_adopted']=True;path.write_text(json.dumps(declaration))
            with self.assertRaisesRegex(ValueError,'ACTUAL_PARENT_GATE_STATE'):assembly.source_manifest()
            declaration['actual_parent_adopted']=False;path.write_text(json.dumps(declaration))
            with patch.object(admission,'SKU_HEAD','unaccepted-model-head'):
                with self.assertRaisesRegex(ValueError,'NO_PARTIAL_ADMISSION'):assembly.source_manifest()
        self.assertTrue(all(getattr(admission,name)is None for name in GATES))

    def test_package_counts_only_actual_child_cases_and_preserves_restoration(self):
        text,proof=package.derive(RAW_PACKAGE)
        self.assertEqual(text.count("cases[runner.CASE]['actual_Native_cases']"),2)
        self.assertIn("report['actual_two_session_races']=0",text)
        self.assertIn("report['real_Auth_HTTP_qualified']=False",text)
        self.assertIn("report['qualification_scope']='CURRENT_PARENT_SKU_NATIVE6_ONLY'",text)
        self.assertTrue(proof['full_restore_all22_rows_sequences_roles_public_and_advisors_unchanged'])
        restored=text
        for before,after in reversed(package.REPLACEMENTS):restored=restored.replace(after,before,1)
        original=ast.parse(RAW_PACKAGE);recovered=ast.parse(restored)
        self.assertEqual(ast.dump(original),ast.dump(recovered))

    def test_only_install_connection_uses_current_parent_trusted_connector(self):
        text,_=package.derive(RAW_PACKAGE)
        self.assertEqual(text.count('with trusted_installer_connection()'),1)
        self.assertEqual(text.count('psycopg.connect(package.boundary.ADMIN)'),
            RAW_PACKAGE.decode().count('psycopg.connect(package.boundary.ADMIN)')-1)
        self.assertIn("STATE=measured(timings,'FIRST_FINANCE_DELTA',product.install_delta,cur,prior)",text)
        self.assertIn("STATE=measured(timings,'SECOND_FINANCE_DELTA',product.install_delta,cur,prior)",text)

    def test_child_cases_and_outputs_have_separate_exact_sources(self):
        text,_=component.derive(RAW_COMPONENT)
        self.assertIn("_FROZEN_SKU/'scripts/cp7_sku_moving_average/qualification_cases.py'",text)
        self.assertIn("LABEL='CP7_SKU_CURRENT_PARENT_NATIVE6'",text)
        self.assertIn("destination=ROOT/'cp6-proof/t3'",text)
        original={n.name:ast.dump(n)for n in ast.parse(RAW_COMPONENT).body if isinstance(n,ast.FunctionDef)}
        current={n.name:ast.dump(n)for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(original['require_local'],current['require_local']);self.assertEqual(original['load'],current['load'])
        # The one exercise edit only selects the frozen cases; invert it and
        # compare the whole function, including every assertion and rollback.
        inverted=text.replace(component.REPLACEMENTS[1][1],component.REPLACEMENTS[1][0],1)
        exercise=next(n for n in ast.parse(inverted).body if isinstance(n,ast.FunctionDef)and n.name=='exercise')
        self.assertEqual(ast.dump(exercise),original['exercise'])

    def test_current_parent_comes_from_its_immutable_checkout(self):
        self.assertEqual(assembly.EXPECTED_PARENT_MODULE,
            runtime.FROZEN_PARENT/'scripts/current-mandor-shop-native-qualification/assembly.py')
        self.assertNotEqual(assembly.EXPECTED_PARENT_MODULE,
            runtime.ROOT/'scripts/current-mandor-shop-native-qualification/assembly.py')
        text=(HERE/'sku_current_parent_runtime.py').read_text()
        self.assertIn('engine.current_advisor=parent_engine.current_advisor',text)
        self.assertIn('parent_proof=parent_engine.admitted()',text)
        self.assertIn('engine.trusted_installer_connection=parent_engine.trusted_installer_connection',text)

    def test_frozen_head_tree_and_changed_source_fail_before_runtime(self):
        with TemporaryDirectory(prefix='sku-composite-git-model-')as directory:
            root=Path(directory);(root/'source.py').write_text('MODEL_SOURCE=True\n')
            for args in[('init','--quiet'),('add','source.py'),('-c','user.name=ERP source prerequisite',
                '-c','user.email=source@example.invalid','commit','--quiet','-m','Explicit source model')]:
                subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True)
            head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
            tree=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD^{tree}'],text=True).strip()
            runtime.frozen(root,head,tree)
            with self.assertRaisesRegex(ValueError,'EXACT_FROZEN_HEAD_AND_TREE'):runtime.frozen(root,head,'0'*40)
            (root/'source.py').write_text('CHANGED_SOURCE=True\n')
            with self.assertRaisesRegex(ValueError,'FROZEN_TRACKED_SOURCE_CHANGED'):runtime.frozen(root,head,tree)

    def test_runtime_main_remains_closed_in_a_real_fresh_process(self):
        result=subprocess.run(['python','-B',str(HERE/'sku_current_parent_runtime.py'),'--check'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('SKU_COMPOSITE_ACTUAL_MANDOR17_SKU6_ROOT_AND_OWNING_ENTRY_PENDING',result.stderr)
        self.assertNotIn('ModuleNotFoundError',result.stderr)
        self.assertFalse((runtime.ROOT/'.github/workflows/cp7-sku-current-parent-native6.yml').exists())


if __name__=='__main__':unittest.main()
