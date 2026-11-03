"""Original-byte and owning-callable controls; no ERP operation is executed."""
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType,SimpleNamespace
from unittest.mock import patch
import ast,io,json,sys,traceback,unittest
from cp7_accessory_nonpayable import case_output as output


class CaseOutputControls(unittest.TestCase):
    def module(self,kind):
        path=output.ROOT/output.SOURCES[kind][0]
        original,_,_=output.derive(kind,path.read_bytes())
        module=ModuleType('modeled_owning_'+kind);module.__file__=str(path)
        exec(compile(ast.Module(body=[original],type_ignores=[]),str(path),'exec'),module.__dict__)
        return module

    def test_full_original_json_bytes_and_small_console_receipt(self):
        row=dict(status='PASS',complete_all22={'unchanged_source':'\n"ERP\\x🙂'*180000},
            large_integer=900719925474099312345,cents=Decimal('123456.01'),null=None,duplicates=['same','same'])
        expected=(json.dumps(dict(group='AFUI_NATIVE9',case='FULL_BYTES',**row),default=str)+'\n').encode()
        with TemporaryDirectory()as tmp,patch.object(output,'OUT',Path(tmp)/'proof'),redirect_stdout(io.StringIO())as console:
            receipt=output.retain('AFUI_NATIVE9','FULL_BYTES',row)
            self.assertEqual((output.OUT/receipt['complete_original_file']).read_bytes(),expected)
            self.assertEqual(receipt['original_bytes'],len(expected));self.assertEqual(receipt['original_sha256'],output.sha256(expected).hexdigest())
            self.assertLess(len(console.getvalue().encode()),2048);self.assertNotIn('unchanged_source',console.getvalue())
            self.assertEqual(row['large_integer'],900719925474099312345)

    def test_first_original_conflict_path_and_symlink_are_refused(self):
        with TemporaryDirectory()as tmp,patch.object(output,'OUT',Path(tmp)/'proof'),redirect_stdout(io.StringIO()):
            receipt=output.retain('AFUI','ONE',{'status':'PASS'});target=output.OUT/receipt['complete_original_file'];before=target.read_bytes()
            with self.assertRaisesRegex(ValueError,'OVERWRITE_REFUSED'):output.retain('AFUI','ONE',{'status':'FAIL'})
            self.assertEqual(target.read_bytes(),before)
            with self.assertRaisesRegex(ValueError,'FIXED_GROUP_AND_CASE'):output.retain('AFUI','../escape',{})
            linked=Path(tmp)/'linked';linked.symlink_to(output.OUT,target_is_directory=True)
            with patch.object(output,'OUT',linked),self.assertRaisesRegex(ValueError,'REGULAR_FIXED'):output.retain('AFUI','TWO',{})

    def test_original_encoder_error_keeps_partial_and_never_emits_success(self):
        cyclic=[];cyclic.append(cyclic)
        with TemporaryDirectory()as tmp,patch.object(output,'OUT',Path(tmp)/'proof'),redirect_stdout(io.StringIO())as console:
            with self.assertRaisesRegex(ValueError,'Circular reference detected'):output.retain('AFUI','ENCODER_ERROR',{'status':'PASS','cyclic':cyclic})
            self.assertEqual(list(output.OUT.glob('*.jsonl')),[]);self.assertEqual(len(list(output.OUT.glob('*.partial'))),1)
            self.assertEqual(console.getvalue(),'')

    def test_three_exact_routes_and_altered_sources_refused_before_binding(self):
        self.assertEqual(output.sources()['routed_print_sites'],3)
        for kind,spec in output.SOURCES.items():
            raw=(output.ROOT/spec[0]).read_bytes();old,new,proof=output.derive(kind,raw)
            self.assertEqual(proof['routed_print_sites'],spec[5]);self.assertTrue(proof['complete_original_source_recovered'])
            self.assertEqual(old.name,new.name)
            with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL_SOURCE'):output.derive(kind,raw+b'\n')

    def test_owning_callable_and_helper_restored_after_success_and_original_failure(self):
        for kind in output.SOURCES:
            module=self.module(kind);name=output.SOURCES[kind][3];original=getattr(module,name)
            with output.scope(module,kind):
                self.assertIsNot(getattr(module,name),original)
                with self.assertRaisesRegex(ValueError,'UNCHANGED_ORIGINAL_CALLABLE'):
                    with output.scope(module,kind):pass
            self.assertIs(getattr(module,name),original);self.assertNotIn(output.HELPER,module.__dict__)
            with self.assertRaisesRegex(RuntimeError,'first owning error'):
                with output.scope(module,kind):raise RuntimeError('first owning error')
            self.assertIs(getattr(module,name),original);self.assertNotIn(output.HELPER,module.__dict__)
            setattr(module,name,lambda:None)
            with self.assertRaisesRegex(ValueError,'UNCHANGED_ORIGINAL_CALLABLE'):
                with output.scope(module,kind):pass

    def test_unchanged_copy_runner_results_refusals_and_cleanup_with_modeled_callbacks(self):
        module=self.module('copies');module.json=json;module.traceback=traceback
        module.VOCABULARY=('PASS','FAIL','COUNTEREXAMPLE','INCOMPLETE');module.session_leaks=lambda *args:[]
        runner=SimpleNamespace(duplicate_ids=lambda names:sorted({n for n in names if names.count(n)>1}))
        def failing():raise RuntimeError('original modeled case failure')
        planned=[('POSITIVE',lambda:{'status':'PASS','all_original_rows':[{'integer':9007199254740993}]}),('REFUSED',failing)]
        run=lambda:module.strict_rows('AFUI_HTTP2',planned,lambda i,key,operation:operation(),'MODELED_NO_DATABASE')
        with patch.dict(sys.modules,{'cp6_auditor_runner':runner}),TemporaryDirectory()as tmp,patch.object(output,'OUT',Path(tmp)/'proof'):
            with redirect_stdout(io.StringIO())as old_console:original=run()
            with output.scope(module,'copies'),redirect_stdout(io.StringIO())as new_console:adapted=run()
            self.assertEqual(original,adapted);self.assertEqual(adapted[0]['REFUSED']['status'],'INCOMPLETE')
            original_lines=[json.loads(x)for x in old_console.getvalue().splitlines()]
            receipts=[json.loads(x)for x in new_console.getvalue().splitlines()]
            for expected,receipt in zip(original_lines[:2],receipts[:2]):
                self.assertEqual(json.loads((output.OUT/receipt['complete_original_file']).read_bytes()),expected)
            self.assertEqual(original_lines[-1],receipts[-1])
            with output.scope(module,'copies'),redirect_stdout(io.StringIO()):
                duplicate=module.strict_rows('AFUI_DUPLICATE',[('SAME',None),('SAME',None)],lambda *args:self.fail('duplicate executed'),'MODELED')
            self.assertEqual(duplicate,({},dict(error='AUDITOR_DUPLICATE_CASE_IDS',duplicate_case_ids=['SAME'])))


if __name__=='__main__':unittest.main()
