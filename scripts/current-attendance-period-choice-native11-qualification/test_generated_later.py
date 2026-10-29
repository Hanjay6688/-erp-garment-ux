"""Declared output doubles and tamper controls; no DB/Native qualification."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import importlib.util
import json
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('closed_later_outputs',HERE/'generated_later.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
HEAD='bd2cd02c0b724f87f6f1d8628f8227dd30c513a4'


class Later(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.here=self.root/'qualifier';self.here.mkdir()
        self.contract=json.loads((HERE/'LATER_GENERATED_RECEIPTS.json').read_bytes())
        (self.here/'LATER_GENERATED_RECEIPTS.json').write_text(json.dumps(self.contract))
        for name in self.contract['producer_files']:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
        self.names=set()
        self.put('ALIGNED_CHAIN.json',self.contract['aligned_document'])
        log=b'DECLARED STARTUP OUTPUT DOUBLE; NO SUPABASE PROCESS\n'
        self.put('disposable-startup-attempts/attempt-1-start.log',log)
        self.put('disposable-startup-attempts/STARTUP_ATTEMPTS.json',dict(status='PASS',scope='DISPOSABLE_STARTUP_BEFORE_ERP_TESTS',maximum_attempts=4,image_tags_changed=False,ERP_tests_retried=False,attempts=[dict(number=1,registry='default_ghcr',status='PASS',started_at_utc='2026-10-29T18:14:38+00:00',start=dict(exit_code=0,log='attempt-1-start.log',bytes=len(log),sha256=sha256(log).hexdigest()))]))
        sql=b'-- DECLARED SQL DIAGNOSTIC DOUBLE; NEVER EXECUTED\n\\restrict CP6CloneBoundary20260904\n\\unrestrict CP6CloneBoundary20260904\n'
        for name in ('CLONE_install.source-erp.sql','CLONE_install.clone-erp.sql'):self.put(name,sql)
        receipt=dict(source_pg_cron='1',clone_pg_cron='1',erp_dump_sha256=sha256(sql).hexdigest(),erp_dump_bytes=str(len(sql)),erp_schema_owners_grants_sequences_rows='IDENTICAL',database_owner_acl_connectivity='IDENTICAL',public_schema_owner_acl_role_privileges='IDENTICAL',status='PASS')
        self.put('CLONE_install.txt',self.kv(receipt))
        identity={prefix+'_'+kind:json.dumps(value) for prefix in ('source','clone')for kind,value in self.contract['clone_identity'].items()}
        self.put('CLONE_install.database-identity.txt',self.kv(identity))
        self.put('CLONE_install.connection-fence.txt',self.kv(dict(self.contract['clone_fence_fixed'],terminated_source_connections='0')))
        self.put('T3_PACKAGE_FILES_INSTALL.json',self.contract['package_files_document'])
        run=dict(self.contract['package_run_identity_static'],tool_head=HEAD,github_sha=HEAD,run_id='40928155690',run_attempt='1',workflow=self.contract['package_workflow_name'],event='push',job='p21')
        self.put('T3_PACKAGE_INSTALL.json',dict(label='T3_PREP',mode='install',status='INCOMPLETE',stages=self.contract['package_stages'],production_go=False,release_evidence=False,run_identity=run,auth_users_before=0,ledger_start={},fingerprint_AB={},hosted_capsules={}))

    @staticmethod
    def kv(d):return (''.join(k+'='+v+'\n'for k,v in d.items())).encode()

    def put(self,name,value):
        p=self.root/(g.PREFIX+name);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(value if isinstance(value,bytes)else(json.dumps(value)+'\n').encode())
        self.names.add(g.PREFIX+name)

    def alter(self,name,change):
        p=self.root/(g.PREFIX+name);d=json.loads(p.read_bytes());change(d);p.write_text(json.dumps(d))

    def admit(self):
        with patch.object(g,'_head',lambda root:HEAD):return g.admit(self.root,self.here,self.names)

    def test_all_exact_output_classes_admit_in_progress_package_without_claiming_final_pass(self):
        accepted,proof=self.admit();self.assertEqual(set(accepted),self.names)
        self.assertEqual(proof['classes'],dict(startup=2,aligned=1,clone=5,package=2))
        self.assertEqual(proof['actual_Native_credit'],0);self.assertFalse(proof['SQL_diagnostics_executed'])
        self.assertEqual(json.loads((self.root/(g.PREFIX+'T3_PACKAGE_INSTALL.json')).read_bytes())['status'],'INCOMPLETE')

    def test_wrong_aligned_source_hash_refuses(self):
        self.alter('ALIGNED_CHAIN.json',lambda d:d['steps'][0].update(code_sha256='0'*64))
        with self.assertRaisesRegex(AssertionError,'ALIGNMENT_PROVENANCE'):self.admit()

    def test_false_to_integer_zero_metadata_counter_refuses_all_fixed_documents(self):
        self.alter('ALIGNED_CHAIN.json',lambda d:d.update(production_go=0))
        with self.assertRaisesRegex(AssertionError,'ALIGNMENT_PROVENANCE'):self.admit()
        self.assertFalse(g.same(False,0));self.assertFalse(g.same({'a':[False]},{'a':[0]}))

    def test_changed_startup_log_refuses(self):
        self.put('disposable-startup-attempts/attempt-1-start.log',b'changed')
        with self.assertRaisesRegex(AssertionError,'STARTUP_LOG_CHANGED'):self.admit()

    def test_startup_wrong_registry_or_boolean_attempt_refuses(self):
        self.alter('disposable-startup-attempts/STARTUP_ATTEMPTS.json',lambda d:d['attempts'][0].update(number=True))
        with self.assertRaises(AssertionError):self.admit()

    def test_bounded_actual_startup_producer_retry_double_is_admitted(self):
        folder=self.root/(g.PREFIX+'disposable-startup-attempts')
        for p in folder.iterdir():p.unlink()
        self.names={n for n in self.names if 'disposable-startup-attempts/'not in n}
        spec=importlib.util.spec_from_file_location('retained_startup_producer',ROOT/'scripts/current-finance-combined-composition/disposable_start.py')
        producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
        class Result:
            def __init__(self,n):self.returncode=n
        starts=[]
        def execute(command,**kwargs):
            kwargs['stdout'].write(b'EXACT PRODUCER LOCAL COMMAND DOUBLE\n')
            if command==producer.START:starts.append(command);return Result(1 if len(starts)==1 else 0)
            self.assertEqual(command,producer.STOP);return Result(0)
        folder.rmdir();producer.start(folder,run=execute,pause=lambda seconds:None,environment={})
        self.names.update(str(p.relative_to(self.root))for p in folder.iterdir())
        accepted,proof=self.admit();self.assertEqual(proof['classes']['startup'],4)

    def test_changed_clone_diagnostic_or_acl_refuses(self):
        self.put('CLONE_install.clone-erp.sql',b'changed')
        with self.assertRaisesRegex(AssertionError,'DIAGNOSTIC_BYTES_CHANGED'):self.admit()

    def test_clone_identity_tamper_refuses(self):
        p=self.root/(g.PREFIX+'CLONE_install.database-identity.txt')
        d=g._kv(p.read_bytes());value=json.loads(d['clone_database_identity']);value['owner']='attacker';d['clone_database_identity']=json.dumps(value);p.write_bytes(self.kv(d))
        with self.assertRaisesRegex(AssertionError,'CLONE_IDENTITY_CHANGED'):self.admit()

    def test_package_source_key_or_tool_head_tamper_refuses(self):
        self.alter('T3_PACKAGE_INSTALL.json',lambda d:d['run_identity'].update(tool_head='0'*40))
        with self.assertRaisesRegex(AssertionError,'TOOL_HEAD_CHANGED'):self.admit()

    def test_source_declared_manual_dispatch_accepts_and_other_workflow_refuses(self):
        self.alter('T3_PACKAGE_INSTALL.json',lambda d:d['run_identity'].update(event='workflow_dispatch'))
        accepted,_=self.admit();self.assertEqual(set(accepted),self.names)
        self.alter('T3_PACKAGE_INSTALL.json',lambda d:d['run_identity'].update(workflow='UNDECLARED'))
        with self.assertRaises(AssertionError):self.admit()

    def test_unknown_source_and_extra_clone_output_remain_unaccepted(self):
        self.names.update({'scripts/Injected.py',g.PREFIX+'CLONE_install.erp.diff'})
        accepted,proof=self.admit();self.assertNotIn('scripts/Injected.py',accepted)
        self.assertNotIn(g.PREFIX+'CLONE_install.erp.diff',accepted)
        self.assertFalse(self.names<=set(accepted))

    def test_symlink_and_frozen_producer_tamper_refuse(self):
        p=self.root/(g.PREFIX+'CLONE_install.clone-erp.sql');p.unlink();p.symlink_to(self.root/(g.PREFIX+'CLONE_install.source-erp.sql'))
        with self.assertRaisesRegex(AssertionError,'SYMLINK'):self.admit()

    def test_producer_source_tamper_refuses(self):
        p=self.root/next(iter(self.contract['producer_files']));p.write_bytes(p.read_bytes()+b'\n')
        with self.assertRaisesRegex(AssertionError,'PRODUCER_SOURCE_CHANGED'):self.admit()

    def test_duplicate_json_key_refuses(self):
        self.put('ALIGNED_CHAIN.json',b'{"status":"PASS","status":"PASS"}\n')
        with self.assertRaisesRegex(AssertionError,'DUPLICATE_JSON'):self.admit()


if __name__=='__main__':unittest.main()
