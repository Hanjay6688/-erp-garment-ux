"""Local preparation/admission controls only. No actual Native/Auth execution."""
from pathlib import Path
from copy import deepcopy
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util,json,sys,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'scripts'))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
admission=load('s03_plan_admission',HERE/'admission.py')

class Preparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=admission.read_original('CP7_VENDOR_RECEIVABLE_COMBINED11.json')
        cls.package=admission.read_original('T3_PACKAGE_INSTALL.json')
        cls.sources=cls.original['source_declaration']['current_installation']
    def test_all_retained_original_bytes_and_exact_7_3_1_counts_are_verified(self):
        for name in admission.PINS:admission.read_original(name)
        result=admission.admit_documents(self.original,self.package,self.sources)
        self.assertEqual((result['historical_native'],result['historical_races'],result['historical_real_Auth_HTTP']),(7,3,1))
        self.assertEqual(result['S03_new_qualification_credit'],0)
    def test_own_exact16_files_counts_and_frozen_wire_refuse_mutation(self):
        manifest=admission.admit_prepared_sources()
        self.assertEqual(len(manifest['files']),16)
        with TemporaryDirectory()as directory:
            root=Path(directory)
            for name in admission.OWN_FILES:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((admission.ROOT/name).read_bytes())
            path=root/'SOURCE.json';path.write_text(json.dumps(manifest))
            self.assertEqual(admission.admit_prepared_sources(root,path),manifest)
            changed=root/admission.OWN_FILES[0];changed.write_text(changed.read_text()+'\n-- source mutation control\n')
            with self.assertRaisesRegex(ValueError,'PREPARED_SOURCE_CHANGED'):admission.admit_prepared_sources(root,path)
            changed.write_bytes((admission.ROOT/admission.OWN_FILES[0]).read_bytes())
            for field,value,expected in(('counts',dict(manifest['counts'],existing_private_facade=True),'EXACT_COUNTS'),
                ('files',dict(manifest['files'],unknown_file='0'*64),'EXACT_FILES'),
                ('Native_case_ids',manifest['Native_case_ids'][:-1],'NATIVE11_IDS'),
                ('accepted_current_S03_Native_original',{'fabricated':'PASS'},'CLAIMS'),
                ('runtime_parent_commit','arbitrary-rehash','PARENT')):
                bad=deepcopy(manifest);bad[field]=value;path.write_text(json.dumps(bad))
                with self.subTest(field=field),self.assertRaisesRegex(ValueError,expected):admission.admit_prepared_sources(root,path)
    def test_malformed_original_or_package_or_parent_source_is_refused(self):
        for key,value in(('status','INCOMPLETE'),('actual_Native_cases',6),('actual_two_session_races',2),('actual_Auth_HTTP_cases',0),('actual_Auth_HTTP_cases',True),('cp6_restored',False),('advisor_gate',False),('used_guard_refused_before_DDL',False)):
            bad=deepcopy(self.original);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):admission.admit_documents(bad,self.package,self.sources)
        package=deepcopy(self.package);package['gate']['backup_restore_drill']=False
        with self.assertRaisesRegex(ValueError,'PACKAGE5'):admission.admit_documents(self.original,package,self.sources)
        package=deepcopy(self.package);package['gate']['backup_restore_drill']=1
        with self.assertRaisesRegex(ValueError,'PACKAGE5'):admission.admit_documents(self.original,package,self.sources)
        with self.assertRaisesRegex(ValueError,'RUNTIME_SOURCE_CHANGED'):admission.admit_documents(self.original,self.package,{'arbitrary_rehash':True})
    def test_changed_native_case_or_original_gzip_cannot_be_substituted(self):
        bad=deepcopy(self.original);group=bad['committed']['VENDOR_RECEIVABLE_NATIVE7_RACES3_AUTH1']['fresh_native7']['native']['cases']
        group[next(iter(group))]['status']='FAIL'
        with self.assertRaisesRegex(ValueError,'EXACT_NATIVE7_IDS'):admission.admit_documents(bad,self.package,self.sources)
        name='T3_BACKUP_RESTORE_DRILL.json'
        with TemporaryDirectory()as directory:
            p=Path(directory)/(name+'.gz');raw=bytearray((admission.RETAINED/(name+'.gz')).read_bytes());raw[-1]^=1;p.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'PARENT_GZIP_CHANGED'):admission.read_original(name,Path(directory))
    def test_actual_callback_factory_has11_callbacks_and_executes_no_fixture_during_declaration(self):
        m=load('s03_Native_callbacks_declaration_only',HERE/'cases.py')
        class NoCursor:
            def __getattr__(self,key):raise AssertionError('LOCAL_PLAN_MUST_NOT_TOUCH_CURSOR:'+key)
        evidence={}
        with patch.object(m.admission,'admit',return_value={'classification':'LOCAL_PLAN_MODEL_NOT_RUNTIME'}),patch.object(m.composition.predecessor,'sources',return_value=self.sources),patch.object(m.composition,'verify',return_value={'classification':'LOCAL_PLAN_MODEL_NOT_RUNTIME'}):
            cases=m.cases(NoCursor(),None,state={},evidence=evidence)
        self.assertEqual(tuple(key for key,_ in cases),m.IDS);self.assertEqual(len(cases),11);self.assertEqual(len(set(m.IDS)),11)
        self.assertEqual(m.IDS,admission.NATIVE_IDS)
        self.assertTrue(all(callable(fn)for _,fn in cases))
        with patch.object(m.admission,'admit',side_effect=ValueError('FIRST_PARENT_REFUSAL')),patch.object(m.composition.predecessor,'sources',return_value={}):
            with self.assertRaisesRegex(ValueError,'FIRST_PARENT_REFUSAL'):m.cases(NoCursor(),None,state={},evidence={})
    def test_independent_exact_cents_oracle_handles_chronology_and_unequal_output(self):
        m=load('s03_independent_Native_fact_oracle_only',HERE/'fixtures.py')
        denominator,rows=m.expected_allocations([('A','PO-A',3,None),('B','PO-B',7,None)])
        self.assertEqual(denominator,10);self.assertEqual([rows[k]['cents']for k in('A','B')],[30000,70003])
        denominator,rows=m.expected_allocations([('A','PO-A',10,None),('B','PO-B',10,None)])
        self.assertEqual(denominator,20);self.assertEqual([rows[k]['cents']for k in('A','B')],[50001,50002])
    def test_prepared_fixture_contains_no_replica_mode_or_direct_posted_business_seed(self):
        text=(HERE/'fixtures.py').read_text()
        self.assertNotIn('session_replication_role',text);self.assertNotIn("'POSTED'",text.split('def destinations')[0])
        for table in('journal_entries','journal_lines','fg_stock_movements','fg_lots','sewing_terminal_events','attendance_hpp_pools','attendance_hpp_pool_sources','attendance_hpp_pool_allocations','payroll_attendance_items'):
            self.assertNotIn('insert into erp.'+table,text)

if __name__=='__main__':unittest.main()
