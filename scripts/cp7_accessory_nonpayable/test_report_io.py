"""Memory and exact-byte controls, without ERP or database operations."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import FunctionType,ModuleType
from unittest.mock import patch
import json,os,subprocess,sys,unittest
from cp7_accessory_nonpayable import report_io as io


class ReportIOControls(unittest.TestCase):
    def module(self,path=None):
        path=io.ROOT/io.ORIGINAL[0]if path is None else path
        raw=path.read_bytes();old,_=io.derive(raw,path)
        module=ModuleType('modeled_original_group_save');module.__file__=str(path)
        module.json=json;module.save=FunctionType(old,module.__dict__,'save')
        return module

    def test_streamed_bytes_match_original_encoder_including_duplicate_and_nonfinite_values(self):
        shared={'same':['source','source'],'cent':Decimal('0.01')}
        value={'unicode':'ERP🙂漢字\n\\"','integer':9007199254740993123456789,
            'date':date(2026,11,4),'none':None,'truth':True,'empty':{},
            'aliases':[shared,shared],'nonfinite':[float('nan'),float('inf'),-float('inf')]}
        expected=(json.dumps(value,indent=2,default=str)+'\n').encode()
        with TemporaryDirectory()as tmp:
            path=Path(tmp)/'group.json';io.write_complete(path,value)
            self.assertEqual(path.read_bytes(),expected)
            value['new']='final report';io.write_complete(path,value)
            self.assertEqual(path.read_bytes(),(json.dumps(value,indent=2,default=str)+'\n').encode())
            self.assertEqual(list(Path(tmp).glob('*.partial')),[])

    def test_failed_encoder_preserves_last_complete_group_and_failed_partial(self):
        cyclic=[];cyclic.append(cyclic)
        with TemporaryDirectory()as tmp:
            path=Path(tmp)/'group.json';io.write_complete(path,{'original':'complete'})
            before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'Circular reference detected'):
                io.write_complete(path,{'cyclic':cyclic})
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(len(list(Path(tmp).glob('.*.partial'))),1)

    def test_only_immutable_strings_share_storage_and_captured_containers_remain_independent(self):
        text='CREATE FUNCTION x() RETURNS text AS '+('exact SQL 漢🙂'*1000)
        retained={'functions':{'erp.x()':[text,False,'v']},'rows':[{'long':text}]}
        actual=json.loads(json.dumps(retained));second=json.loads(json.dumps(retained))
        self.assertIsNot(actual['functions']['erp.x()'][0],text)
        before=json.dumps(actual);result=io.share_strings(actual,retained)
        io.share_strings(second,retained)
        self.assertIs(result,actual);self.assertEqual(json.dumps(result),before)
        self.assertIs(actual['functions']['erp.x()'][0],text)
        self.assertIs(second['rows'][0]['long'],text)
        self.assertIsNot(actual['functions'],retained['functions'])
        self.assertIsNot(actual['functions']['erp.x()'],retained['functions']['erp.x()'])
        actual['functions']['erp.x()'][0]='changed after capture'
        actual['rows'][0]['new']='only one capture'
        self.assertEqual(retained,second)
        retained['functions']['erp.x()'][1]=True
        self.assertFalse(second['functions']['erp.x()'][1])

    def test_differences_and_all_complete_catalog_members_survive_string_sharing(self):
        text='original body '*1000;changed='different body '*1000
        retained={'functions':{'erp.x()':[text]},'roles':{'actor':[False]},'data':[1,2,3]}
        actual={'functions':{'erp.x()':[changed]},'roles':{'actor':[True]},'data':[1,2,4],'new':None}
        expected=deepcopy(actual)
        self.assertEqual(io.share_strings(actual,retained),expected)
        self.assertNotEqual(actual,retained)
        self.assertEqual(set(actual),set(expected))

    def test_exact_original_module_and_complete_compiler_context_are_required(self):
        raw=(io.ROOT/io.ORIGINAL[0]).read_bytes();old,new=io.derive(raw)
        self.assertEqual(old.co_name,'save');self.assertEqual(new.co_name,'save')
        with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL_SOURCE'):
            io.derive(raw+b'\n')
        module=self.module();original=module.save
        with TemporaryDirectory()as tmp:
            module.OUT=Path(tmp)
            with io.scope(module)as proof:
                self.assertTrue(proof['complete_original_source_recovered'])
                self.assertEqual(proof['actual_case_credit'],0)
                with self.assertRaisesRegex(ValueError,'ORIGINAL_OWNING_CALLABLE'):
                    with io.scope(module):pass
                module.save('ordinary',{'all_values':['retained']})
            self.assertIs(module.save,original);self.assertNotIn(io.HELPER,module.__dict__)
            self.assertEqual((Path(tmp)/'ordinary.json').read_bytes(),
                (json.dumps({'all_values':['retained']},indent=2,default=str)+'\n').encode())
            with self.assertRaisesRegex(RuntimeError,'first owning error'):
                with io.scope(module):raise RuntimeError('first owning error')
            self.assertIs(module.save,original);self.assertNotIn(io.HELPER,module.__dict__)
            module.save=lambda *args:None
            with self.assertRaisesRegex(ValueError,'ORIGINAL_OWNING_CALLABLE'):
                with io.scope(module):pass

    def test_final_whole_packet_changes_only_one_save_expression_after_original_routes(self):
        from cp7_accessory_nonpayable import package_engine
        original=(io.ROOT/package_engine.ORIGINAL).read_bytes()
        prepared,old_proof=package_engine.derive(original)
        changed,proof=io.derive_engine(prepared)
        self.assertEqual(old_proof['exact_reversible_changes'],2)
        self.assertEqual(proof['reversible_save_expression_changes'],1)
        self.assertTrue(proof['complete_prepared_engine_recovered'])
        recovered=changed.replace(io.HELPER+'(OUT,report)',
            "OUT.write_text(json.dumps(report,indent=2,default=str)+'\\n')",1)
        self.assertEqual(recovered,prepared)
        for text in (prepared+'\n',prepared.replace("report['status']='PASS'","report['status']='FORGED'",1)):
            with self.assertRaisesRegex(ValueError,'EXACT_PREPARED_WHOLE_ENGINE'):
                io.derive_engine(text)

    def test_same_exact_owning_module_in_writer_checkout_binds_before_any_database(self):
        raw=(io.ROOT/io.ORIGINAL[0]).read_bytes()
        with TemporaryDirectory()as tmp:
            path=Path(tmp)/'writer'/io.ORIGINAL[0];path.parent.mkdir(parents=True);path.write_bytes(raw)
            module=self.module(path);module.OUT=Path(tmp)/'proof';original=module.save
            _,_,proof=io.binding(module)
            self.assertEqual(proof['actual_source_path'],str(path))
            self.assertTrue(proof['complete_owning_module_compiler_context'])
            with io.scope(module):module.save('actual_caller_copy',{'complete':'same bytes'})
            self.assertIs(module.save,original)
            self.assertEqual((module.OUT/'actual_caller_copy.json').read_bytes(),
                (json.dumps({'complete':'same bytes'},indent=2,default=str)+'\n').encode())
            wrong=path.parent/'unexpected.py';wrong.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'EXACT_OWNING_MODULE'):
                io.binding(self.module(wrong))

    @unittest.skipUnless(sys.platform=='linux','Linux resource limits required')
    def test_same_large_report_exceeds_original_memory_limit_and_streams_completely(self):
        program=r'''
import hashlib,json,pathlib,resource,sys
from cp7_accessory_nonpayable.report_io import write_complete
resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
value={'complete_catalog_snapshots':['SQL'*350000]*80}
target=pathlib.Path(sys.argv[2])
if sys.argv[1]=='original':
 try:target.write_text(json.dumps(value,indent=2,default=str)+'\n')
 except MemoryError:print('ORIGINAL_MEMORY_ERROR');sys.exit(42)
 raise AssertionError('Expected the controlled original full-string allocation to exceed 128 MiB')
write_complete(target,value)
assert target.stat().st_size>80*1024*1024
# Compute this fixture's expected original pretty JSON bytes independently.
h=hashlib.sha256();h.update(b'{\n  "complete_catalog_snapshots": [\n')
for n in range(80):h.update(b'    '+json.dumps('SQL'*350000).encode()+ (b',\n'if n<79 else b'\n'))
h.update(b'  ]\n}\n');actual=hashlib.file_digest(target.open('rb'),'sha256').hexdigest()
assert actual==h.hexdigest();print(json.dumps({'complete_bytes':target.stat().st_size,'sha256':actual}))
'''
        with TemporaryDirectory()as tmp:
            env={**os.environ,'PYTHONPATH':str(io.ROOT/'scripts'),'PYTHONDONTWRITEBYTECODE':'1'}
            first=subprocess.run([sys.executable,'-c',program,'original',str(Path(tmp)/'old.json')],
                env=env,text=True,capture_output=True,timeout=45)
            self.assertEqual(first.returncode,42,first.stderr);self.assertIn('ORIGINAL_MEMORY_ERROR',first.stdout)
            fixed=subprocess.run([sys.executable,'-c',program,'streamed',str(Path(tmp)/'new.json')],
                env=env,text=True,capture_output=True,timeout=45)
            self.assertEqual(fixed.returncode,0,fixed.stderr)
            self.assertGreater(json.loads(fixed.stdout)['complete_bytes'],80*1024*1024)


if __name__=='__main__':unittest.main()
