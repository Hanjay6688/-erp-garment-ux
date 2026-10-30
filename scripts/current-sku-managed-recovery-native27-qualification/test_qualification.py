"""Source/API/metadata/sequence controls; no Native DB or browser acceptance."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast
import importlib.util
import json
import tempfile
import unittest
import yaml

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

d=load('sku27_unit_deriver','derive.py');prefix=load('sku27_unit_prefix','sequence_prefix.py')

def ids(path):
    tree=ast.parse(path.read_bytes())
    return next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='IDS'for t in n.targets))

def seq(value='1',called=False):return{'sequence:local.seq_'+str(i):[value,called]for i in range(15)}

class Qualification(unittest.TestCase):
    def test_exact_original23_plus_four_distinct_ids(self):
        files=['scripts/current-sku-pair-conversion-qualification/cases.py','scripts/current-sku-group-cost-qualification/cases.py',
          'scripts/current-sku-pair-conversion-qualification/races.py','scripts/current-sku-pair-conversion-qualification/auth_waits.py']
        old=[key for file in files for key in ids(ROOT/file)]
        # Browser4 consists of the unchanged SKU2 + AI2 exported plan.
        spec=importlib.util.spec_from_file_location('sku27_unit_old_plan',ROOT/'scripts/current-sku-combined-followup-qualification/plan.py')
        plan=importlib.util.module_from_spec(spec);spec.loader.exec_module(plan)
        old+=list(plan.BROWSER_IDS);self.assertEqual(len(old),23)
        extra=list(ids(HERE/'recovery_cases.py'))+list(ids(HERE/'recovery_sessions.py'))
        self.assertEqual(len(extra),4);self.assertEqual(len(set(old+extra)),27)

    def test_complete_old_financial_callbacks_unchanged_in_private_modules(self):
        for key,names in [('cost_cases',['recovery_safety','both_parts_recost','atomic_inverse']),
                          ('auth_waits',['exercise'])]:
            before=d.legacy.derive(key)[0];after=d.derive(key)[0]
            a={n.name:ast.dump(n)for n in ast.parse(before).body if isinstance(n,ast.FunctionDef)}
            b={n.name:ast.dump(n)for n in ast.parse(after).body if isinstance(n,ast.FunctionDef)}
            for name in names:self.assertEqual(a[name],b[name],(key,name))
        before=d.legacy.derive('browser')[0];after=d.derive('browser')[0]
        after=d.browser_delta.adapt(after,'browser',reverse=True)
        self.assertEqual(before[before.index('async function journey'):before.index('export function cases')],
                         after[after.index('async function journey'):after.index('export function cases')])

    def test_every_private_derivation_has_exact_current_source_and_inverse(self):
        proof=d.inventory();self.assertEqual(len(proof),15)
        self.assertTrue(all(p['byte_exact_reversible']for p in proof.values()))
        self.assertEqual([key for key,p in proof.items()if not p['original23_financial_callback_bodies_unchanged']],['races','browser'])
        self.assertEqual(proof['browser']['explicit_browser_locator_or_route_changes'],9)
        self.assertEqual(proof['cases']['explicit_browser_locator_or_route_changes'],1)
        self.assertEqual([key for key,p in proof.items()if not p['original_financial_postcondition_assertions_unchanged']],['browser'])
        self.assertTrue(all(p['financial_expected_values_unchanged']for p in proof.values()))
        self.assertEqual(proof['browser']['explicit_currency_display_whitespace_changes'],1)
        self.assertEqual(proof['browser']['explicit_recovery_and_history_changes'],4)
        self.assertEqual(d.browser_delta.DISPLAY[0].replace('Rp60','Rp 60'),d.browser_delta.DISPLAY[1])
        with self.assertRaises(ValueError):d.derive('runner',b'unknown body')

    def test_race_only_changes_scheduling_and_retains_every_financial_postcondition(self):
        before=d.legacy.derive('races')[0];after=d.derive('races')[0]
        a=next(n for n in ast.parse(before).body if isinstance(n,ast.FunctionDef)and n.name=='exercise')
        b=next(n for n in ast.parse(after).body if isinstance(n,ast.FunctionDef)and n.name=='exercise')
        self.assertEqual(len(a.body),len(b.body))
        changed=[i for i,(old,new)in enumerate(zip(a.body,b.body))if ast.dump(old)!=ast.dump(new)]
        self.assertEqual(changed,[3,4])
        self.assertIn('tools.two_sessions',ast.unparse(a.body[3]))
        self.assertIn('schedule.run',ast.unparse(b.body[3]))
        self.assertIn('schedule.require_contention',ast.unparse(b.body[4]))
        self.assertEqual([ast.dump(n)for n in a.body[5:]],[ast.dump(n)for n in b.body[5:]])

    def test_complete_engine_six_changes_and_inverse(self):
        engine=load('sku27_unit_engine','engine_delta.py');raw=(ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        text,proof=engine.derive(raw);old,_=engine.old.derive(raw)
        self.assertEqual(text.replace(engine.AFTER,engine.BEFORE,1),old);self.assertEqual(proof['counted_changes'],6)
        self.assertIn("report['actual_business_cases']=27",text)

    def test_workflow_retains_full_seventy_step_engine_and_always_cleanup(self):
        workflow=load('sku27_unit_workflow','workflow.py');old=yaml.safe_load((ROOT/workflow.OLD).read_bytes());new=yaml.safe_load((ROOT/workflow.NEW).read_bytes())
        self.assertEqual(new,workflow.derive(old));self.assertEqual(len(new['jobs']['p21']['steps']),70)
        policy=load('sku27_unit_attempt_policy','attempt_policy.py')
        self.assertEqual(policy.JOB_BUDGET_SECONDS,new['jobs']['p21']['timeout-minutes']*60)
        check=next(s for s in new['jobs']['p21']['steps']if s.get('name')=='Check SKU delta and unchanged runner derivation before database')
        self.assertTrue(check['run'].startswith('python -B '+workflow.NS+'/attempt_policy.py --require-window\n'))
        a=old['jobs']['p21']['steps'];b=new['jobs']['p21']['steps']
        for name in('Start disposable database','Rebuild to v2.6.20, align with hosted, continue the frozen path to AB','Provision isolated rollback authority','Clone the aligned AB state for install','Remove disposable database'):
            self.assertEqual(next(s for s in a if s.get('name')==name),next(s for s in b if s.get('name')==name))
        self.assertEqual(next(s for s in b if s.get('uses','').startswith('actions/upload-artifact@'))['if'],'always()')

    def test_old_snapshot_predicate_red_and_complete_positive_prefix(self):
        before=dict(catalog={'all22':'same'},data=dict(seq(),table=['1','samehash']))
        after=deepcopy(before);after['data']['sequence:local.seq_0']=['6',True]
        self.assertNotEqual(before,after)  # Exact retained false sequence-restoration expectation.
        proof=prefix.strict_rollback(before,after);self.assertEqual(len(proof['sequence_prefix']['before']),15)
        self.assertFalse(proof['sequence_prefix']['per_case_sequence_restore_claim'])
        bad=deepcopy(after);bad['data']['table']=['2','wronghash']
        with self.assertRaisesRegex(ValueError,'ALL_TABLE_ROWS_CHANGED'):prefix.strict_rollback(before,bad)
        bad=seq();bad.pop(next(iter(bad)))
        with self.assertRaisesRegex(ValueError,'FIFTEEN'):prefix.sequences(bad)
        with self.assertRaisesRegex(ValueError,'REWIND'):prefix.prefix(seq('6',True),seq('1',True))

    def test_case_prefix_retains_all_sequences_and_original_failure(self):
        with tempfile.TemporaryDirectory()as temporary,patch.object(prefix,'ROOT',Path(temporary)):
            states=iter([dict(data_and_sequences=seq()),dict(data_and_sequences=seq('2',True))])
            native=SimpleNamespace(capture_current=lambda:next(states))
            name,call=prefix.wrap([('POSITIVE',lambda:dict(status='PASS',money='20.01'))],native)[0]
            result=call();self.assertEqual(result['money'],'20.01');self.assertEqual(len(result['complete_case_sequence_prefix']['after']),15)
            calls=0
            def observed():
                nonlocal calls
                calls+=1
                if calls==1:return dict(data_and_sequences=seq())
                raise RuntimeError('aborted observer')
            def broken():raise ValueError('ORIGINAL_BUSINESS_FAILURE')
            with self.assertRaisesRegex(ValueError,'ORIGINAL_BUSINESS_FAILURE'):
                prefix.wrap([('FAILED',broken)],SimpleNamespace(capture_current=observed))[0][1]()
            report=json.loads(next((Path(temporary)/'cp6-proof/t3').glob('*FAILED*.json')).read_bytes())
            self.assertIn('ORIGINAL_BUSINESS_FAILURE',report['first_failure']['error']);self.assertIsNone(report['after'])
            self.assertEqual(report['observation_error'],'aborted observer')

    def test_node_current_binding_keeps_all_ten_physical_leaves_and_original_pins(self):
        binding=json.loads((HERE/'BROWSER_SOURCE.json').read_bytes());self.assertEqual(len(binding['current_files']),10)
        old=json.loads((ROOT/'scripts/current-sku-pair-browser-qualification/SOURCE.json').read_bytes())
        self.assertEqual(binding['historical_files'],old['files'])
        changed=[key for key,pin in old['files'].items()if key in binding['current_files']and pin!=binding['current_files'][key]]
        self.assertEqual(set(changed),{'scripts/cp7_sku_pair_conversion/composition.py','scripts/cp7_sku_pair_conversion/conversion.sql'})
        text=d.derive('browser')[0];self.assertIn('actual.actual_current_installation.files',text)
        self.assertIn('authentic_retained_Original.original_sha256',text);self.assertIn('SKU27_SOURCE_SYMLINK',text)

    def test_busy_one_case_has_distinct_fg_and_lawful_none_material_attempts(self):
        tree=ast.parse((HERE/'recovery_sessions.py').read_bytes())
        selected=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='busy_case')
        seen=[]
        def exercise(tools,today,n,*,cache,busy):
            seen.append((cache,busy));return dict(status='PASS',local_control_only=True)
        ns={'exercise':exercise}
        exec(compile(ast.Module(body=[selected],type_ignores=[]),'<pure prepared busy registration>','exec'),ns)
        result=ns['busy_case'](None,None,None)
        self.assertEqual(seen,[(False,'FG'),(False,'MATERIAL_NONE')])
        self.assertEqual(result['declared_cases'],1)
        self.assertEqual(result['distinct_busy_attempts'],2)
        source=(HERE/'recovery_sessions.py').read_text()
        self.assertIn("n.bc.policy(cur,'ACC_DEC03'",source)
        self.assertIn("unit_value_cap='NONE'",source)
        self.assertIn('select id::text from erp.materials where id=%s for update',source)
        self.assertIn("mode='RowShareLock'and granted",source)
        self.assertIn('holder.info.transaction_status==psycopg.pq.TransactionStatus.INTRANS',source)
        self.assertLess(source.index('if not cache:before=n.capture(held)'),source.index('job=pool.submit(send)'))

    def test_actual_source_guard_rejects_identical_ancestor_then_restores(self):
        closure=load('sku27_unit_actual_closure','closure.py')
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);folder=root/'declared';folder.mkdir();p=folder/'source.py';p.write_text('exact original source\n')
            files={'declared/source.py':dict(bytes=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest())}
            closure.verify_files(root,files)
            outside=root/'same-bytes';folder.rename(outside);folder.symlink_to(outside,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'ANCESTOR_SYMLINK'):closure.verify_files(root,files)
            folder.unlink();outside.rename(folder);closure.verify_files(root,files)

    def test_source_context_uses_exact_public_DB_guard_and_restores(self):
        context=load('sku27_unit_DB_context','source_context.py')
        import psycopg
        original=psycopg.connect
        with context.fenced_source_read()as proof:
            self.assertEqual(proof['attempts'],[])
            self.assertEqual(proof['network_nonGit_attempts'],[])
            self.assertEqual(len(proof['self_controls']),3)
        self.assertIs(psycopg.connect,original)
        self.assertTrue(proof['self_controls'][-1]['original_connect_descriptors_restored'])

    def test_prepared_session_plan_keeps_seven_permissions_and_one_busy(self):
        tree=ast.parse(d.derive('concurrency')[0]);selected=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='plan')
        races=ids(ROOT/'scripts/current-sku-pair-conversion-qualification/races.py')
        waits=ids(ROOT/'scripts/current-sku-pair-conversion-qualification/auth_waits.py')
        extra=ids(HERE/'recovery_sessions.py')
        ns=dict(CALLBACKS=Path('/declared'),ROOT=ROOT,CASE='SOURCE_ONLY_PLAN',
          ids=lambda path:races if path.name=='races.py'else waits,
          load=lambda name,path:SimpleNamespace(IDS=extra))
        exec(compile(ast.Module(body=[selected],type_ignores=[]),'<pure source-only session registration>','exec'),ns)
        result=ns['plan']()
        self.assertEqual(len(result['race_ids']),3)
        self.assertEqual(result['permission_wait_ids'],list(waits)+[extra[0]])
        self.assertEqual(result['nonblocking_busy_ids'],[extra[1]])
        self.assertEqual(result['busy_subattempts'],['FG','MATERIAL_NONE'])
        self.assertEqual(result['actual_Native_cases'],0)

    def test_session_entry_checks_every_declared_id_including_busy(self):
        tree=ast.parse(d.derive('concurrency')[0])
        exercise=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='exercise')
        guard=next(n for n in exercise.body if isinstance(n,ast.Assert)
            and 'prepared_plan' in ast.unparse(n.test))
        races=ids(ROOT/'scripts/current-sku-pair-conversion-qualification/races.py')
        waits=ids(ROOT/'scripts/current-sku-pair-conversion-qualification/auth_waits.py')
        extra=ids(HERE/'recovery_sessions.py')
        expected=tuple(races)+tuple(waits)+tuple(extra)
        plan=dict(race_ids=list(races),permission_wait_ids=list(waits)+[extra[0]],
            nonblocking_busy_ids=[extra[1]])
        code=compile(ast.Module(body=[guard],type_ignores=[]),'<actual derived session-entry guard>','exec')
        exec(code,dict(expected=expected,report=dict(prepared_plan=plan)))
        self.assertEqual(len(expected),11)
        for field in ('race_ids','permission_wait_ids','nonblocking_busy_ids'):
            for change in ('missing','duplicate','foreign'):
                broken=deepcopy(plan)
                if change=='missing':broken[field].pop()
                elif change=='duplicate':broken[field].append(broken[field][0])
                else:broken[field][-1]='UNKNOWN_SESSION'
                with self.subTest(field=field,change=change),self.assertRaises(AssertionError):
                    exec(code,dict(expected=expected,report=dict(prepared_plan=broken)))

if __name__=='__main__':unittest.main()
