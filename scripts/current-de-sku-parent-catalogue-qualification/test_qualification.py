"""Offline source/protocol/gate controls; no database or financial credit."""
from contextlib import nullcontext
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import ast
import importlib.util
import json
import tempfile
import unittest
import yaml

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


d=load('de_sku_test_derive','derive.py');a=load('de_sku_test_admission','admission.py')
w=load('de_sku_test_workflow','workflow.py');g=load('de_sku_test_gate','result_gate.py')


class Qualification(unittest.TestCase):
    def test_whole_engine_reversible_and_complete_finally_restore_unchanged(self):
        raw=(ROOT/d.OLD).read_bytes();text,proof=d.derive(raw)
        self.assertEqual(proof['counted_changes'],13)
        start='    finally:\n        if before is not None and pre_dumped:';end="        cases=report['committed']"
        self.assertEqual(text[text.index(start):text.index(end)],raw.decode()[raw.decode().index(start):raw.decode().index(end)])
        self.assertIn("report['actual_Native_cases']=0",text)
        self.assertIn("report['actual_business_cases']=0",text)
        self.assertIn("report['used_guard_business_witness_executed']=False",text)
        with self.assertRaises(ValueError):d.derive(b'unknown engine')

    def test_workflow_retains_original70_adds_one_gate_and_every_disposable_boundary(self):
        old=yaml.safe_load((ROOT/w.OLD).read_bytes());new=yaml.safe_load((ROOT/w.NEW).read_bytes())
        self.assertEqual(new,w.derive(old));self.assertEqual(len(old['jobs']['p21']['steps']),70)
        self.assertEqual(len(new['jobs']['p21']['steps']),71)
        for name in('Start disposable database','Rebuild to v2.6.20, align with hosted, continue the frozen path to AB',
                    'Provision isolated rollback authority','Clone the aligned AB state for install','Remove disposable database'):
            self.assertEqual(next(s for s in old['jobs']['p21']['steps']if s.get('name')==name),
                next(s for s in new['jobs']['p21']['steps']if s.get('name')==name))
        self.assertEqual(new['jobs']['p21']['steps'][-1]['if'],'always()')

    def test_six_own_hook_signatures_match_actual_imported_declarations(self):
        tree=ast.parse((HERE/'runner.py').read_bytes())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='exercise')
        hooks=next(ast.literal_eval(n.value)for n in fn.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='hooks'for t in n.targets))
        import re
        declarations=[]
        for p in (ROOT/'scripts/cp7_credit_correction_de').rglob('*.sql'):
            for name,args in re.findall(r'create function ([a-z0-9_.]+)\(([^)]*)\)',p.read_text()):
                declarations.append(name+'('+','.join(v.strip().split()[1]for v in args.split(',')if v.strip())+')')
        self.assertEqual(len(hooks),8)
        self.assertTrue(set(hooks[:6])<=set(declarations))
        self.assertEqual(hooks[-2:],('cp7_credit.source_request_enter_v1(text,jsonb,uuid,text)','cp7_credit.source_request_finish_v1(uuid)'))

    def test_natural_parent_install_and_reverse_order_never_project_lower_catalogue(self):
        log=[];cur=SimpleNamespace(actual={'layer':'Vendor'},data={'rows':0})
        digest=lambda value:sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
        cat=SimpleNamespace(_authority=lambda c:None,_catalog_rows=lambda c:deepcopy(c.actual),
            _data=lambda c:deepcopy(c.data),_lock_tables=lambda c:log.append('lock'),digest=digest)
        class Layer:
            def __init__(self,name,parent=None):self.name=name;self.parent=parent
            def verify(self,c,state):
                if c.actual!=state['after']or c.actual!={'layer':self.name}:raise ValueError('LOWER_VERIFIER_ON_WRONG_ACTUAL_CATALOGUE')
                log.append('verify '+self.name);return dict(status=self.name)
            def install_delta(self,c,prior):
                self.parent.verify(c,prior);log.append('install '+self.name)
                before=deepcopy(c.actual);c.actual={'layer':self.name}
                return dict(sources=self.name,predecessor=prior,before=before,after=deepcopy(c.actual),
                    preuse_data_and_sequences={'rows':0},preinstall_data_and_sequences={'rows':0})
            def rollback_delta_preuse(self,c,state):
                self.verify(c,state);log.append('remove '+self.name);c.actual=deepcopy(state['before']);return {'removed':self.name}
        vendor=Layer('Vendor');d1=Layer('D1',vendor);e=Layer('E',d1);sku=Layer('SKU',e)
        ns=dict(vendor=vendor,d1=d1,e=e,sku=sku,USED_ERROR='USED',sources=lambda:{'source':'fixed'},
            runtime=lambda:(None,None,None,SimpleNamespace(atomic=lambda c:nullcontext()),cat))
        tree=ast.parse((HERE/'stage.py').read_bytes())
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in('binding','verify','install_delta','rollback_delta_preuse')]
        exec(compile(ast.Module(body=funcs,type_ignores=[]),'<actual stage protocol with explicit doubles>','exec'),ns)
        prior=dict(sources='Vendor',before={'layer':'Earlier'},after={'layer':'Vendor'},preuse_data_and_sequences={'rows':0},preinstall_data_and_sequences={'rows':0})
        state=ns['install_delta'](cur,prior);self.assertEqual(cur.actual,{'layer':'SKU'})
        changed=deepcopy(state);changed['parent_binding']='wrong'
        with self.assertRaisesRegex(ValueError,'PARENT_PROOF_CHANGED'):ns['verify'](cur,changed)
        before=len(log);cur.data={'rows':1}
        with self.assertRaisesRegex(ValueError,'USED'):ns['rollback_delta_preuse'](cur,state)
        self.assertFalse(any(v.startswith('remove')for v in log[before:]))
        cur.data={'rows':0};result=ns['rollback_delta_preuse'](cur,state)
        self.assertEqual([v for v in log if v.startswith('remove')],['remove SKU','remove E','remove D1'])
        self.assertEqual(cur.actual,{'layer':'Vendor'});self.assertFalse(result['used_guard_business_witness_executed'])

    def test_same_bytes_symlink_ancestor_and_mode_cannot_change_source(self):
        with tempfile.TemporaryDirectory()as t:
            root=Path(t);p=root/'folder/file.py';p.parent.mkdir();p.write_text('exact source\n')
            expected=dict(a.pin(p.read_bytes()),mode='100644');a.checked_file('folder/file.py',expected,root)
            p.chmod(0o755)
            with self.assertRaisesRegex(ValueError,'SOURCE_MODE_CHANGED'):a.checked_file('folder/file.py',expected,root)
            p.chmod(0o644);p.parent.rename(root/'other');(root/'folder').symlink_to(root/'other',target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'SOURCE_LINK'):a.checked_file('folder/file.py',expected,root)
        with self.assertRaisesRegex(ValueError,'DUPLICATE_JSON'):a.document('{"a":1,"a":1}')


class ResultGate(unittest.TestCase):
    def fixture(self):
        # Explicit portable-catalogue double, not an actual installed database.
        c={k:{}for k in g.context_catalog.ALL22};c['roles']={'postgres':['MODEL']};names=['model.t'+str(i)for i in range(55)]
        c['schemas']['model']=['postgres',[]]
        for name in names:
            c['relations'][name]=['postgres','r','p',True,False,False,'d',None,True,None,None,None,[]]
            c['columns'][name+':transaction_id']=['transaction_id','bigint',True,None,None,None,None,None,None,None,None,None,None,None]
        ctx=g.context_catalog.select(c);before=dict(catalog=c,data_and_sequences={'sequence:model.s':['1',False]})
        privileges=[['postgres',t,p,True]for t in names for p in('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER')]
        case=dict(status='PASS',read_complete_noeffect=True,read_before=before,read_after=deepcopy(before),actual_composite_catalogue=c,
            actual_context55=ctx,actual_layer_catalogues={k:deepcopy(c)for k in('D1','E','SKU')},
            current_eight_hook_rows={str(i):[None]*19 for i in range(8)},
            actual_raw_context_authority=dict(relations=[[n]for n in names],effective_role_table_privileges=privileges))
        r=dict(status='PASS',label='CP7_D1_E_SKU_PARENT_CATALOGUE',qualification_commit='head',actual_catalogue_qualification_groups=1,
            committed={g.CASE:case},actual_business_cases=0,actual_Native_cases=0,actual_two_session_races=0,
            actual_Auth_HTTP_cases=0,actual_browser_cases=0,used_guard_business_witness_executed=False,
            full_final_composite_qualified=False,cp6_restored=True,baseline_full22_all_rows_all_sequences_equal=True,
            baseline_advisors_equal=True,advisor_gate=True,preuse_catalogue_qualified=True)
        p=dict(run_identity=dict(tool_head='head',github_sha='head'),gate={k:True for k in g.GATES},auth_users_before=0,auth_users_after=0)
        return r,p

    def test_complete_explicit_double_remains_catalogue_only(self):
        r,p=self.fixture();v=g.checked(r,p,'head');self.assertEqual(v['actual_Native_cases'],0);self.assertFalse(v['full_final_composite_qualified'])

    def test_any_restore_gate_failure_or_business_promotion_refuses(self):
        r,p=self.fixture()
        for field in('cp6_restored','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','advisor_gate','preuse_catalogue_qualified'):
            bad=deepcopy(r);bad[field]=False
            with self.subTest(field=field),self.assertRaises(ValueError):g.checked(bad,p,'head')
        for field in('actual_business_cases','actual_Native_cases','actual_two_session_races','actual_Auth_HTTP_cases','actual_browser_cases'):
            for value in(1,False):
                bad=deepcopy(r);bad[field]=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):g.checked(bad,p,'head')
        for field in g.GATES:
            bad=deepcopy(p);bad['gate'][field]=False
            with self.subTest(field=field),self.assertRaises(ValueError):g.checked(r,bad,'head')

    def test_incomplete_catalogue_privilege_census_or_sequence_mutation_refuses(self):
        r,p=self.fixture()
        bad=deepcopy(r);bad['committed'][g.CASE]['actual_layer_catalogues']['D1'].pop('triggers')
        with self.assertRaisesRegex(ValueError,'COMPLETE22'):g.checked(bad,p,'head')
        bad=deepcopy(r);bad['committed'][g.CASE]['actual_raw_context_authority']['effective_role_table_privileges'].pop()
        with self.assertRaisesRegex(ValueError,'PRIVILEGE_MATRIX'):g.checked(bad,p,'head')
        bad=deepcopy(r);bad['committed'][g.CASE]['read_after']['data_and_sequences']['sequence:model.s']=['2',True]
        with self.assertRaisesRegex(ValueError,'SEQUENCES_CHANGED'):g.checked(bad,p,'head')


if __name__=='__main__':unittest.main()
