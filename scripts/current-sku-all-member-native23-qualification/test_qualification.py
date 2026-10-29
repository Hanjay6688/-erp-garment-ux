"""Local source, negative, formatter and import doubles; zero Native credit."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import ast
import gzip
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
import yaml

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


d = load('test_sku23_deriver', HERE / 'derive.py')
t = load('test_sku23_transition', HERE / 'transition.py')
c = load('test_sku23_closure', HERE / 'closure.py')
r = load('test_sku23_negative', HERE / 'recovery.py')
w = load('test_sku23_workflow', HERE / 'workflow.py')


def asserts(text, name=None):
    tree = ast.parse(text)
    if name:
        tree = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return [ast.dump(n, include_attributes=False) for n in ast.walk(tree) if isinstance(n, ast.Assert)]


class Derivations(unittest.TestCase):
    def test_all134_retained_asserts_survive_and_sources_reverse_exactly(self):
        inventory = d.inventory()
        self.assertEqual(sum(inventory[k]['original_asserts'] for k in d.legacy.SOURCES), 134)
        self.assertEqual(sum(inventory[k]['derived_asserts'] for k in d.legacy.SOURCES), 134)
        self.assertEqual(sum(p['new_counted_changes'] for p in inventory.values()), 31)
        self.assertTrue(all(p['byte_exact_reversible_to_retained_derivation'] and p['assertions_removed'] == 0 for p in inventory.values()))
        for key, (path, _) in d.SOURCES.items():
            with self.assertRaisesRegex(ValueError, 'FROZEN_SOURCE_CHANGED'):
                d.derive(key, (ROOT/path).read_bytes() + b'\n')

    def test_cost_three_callback_assertions_and_every_money_value_remain_exact(self):
        old = (ROOT / d.SOURCES['cost_cases'][0]).read_text()
        new, _ = d.derive('cost_cases')
        for name in ('recovery_safety', 'both_parts_recost', 'atomic_inverse'):
            self.assertEqual(asserts(old, name), asserts(new, name))
        old_tree, new_tree = ast.parse(old), ast.parse(new)
        old_both = next(n for n in old_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'both_parts_recost')
        new_both = next(n for n in new_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'both_parts_recost')
        self.assertEqual(ast.dump(old_both), ast.dump(new_both))
        # All exact money/quantity strings are retained; only declared source,
        # formatter and honest result metadata strings may differ.
        numbers = lambda tree: [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and re.fullmatch(r'-?\d+(?:\.\d+)?', n.value)]
        self.assertEqual(numbers(old_tree), numbers(new_tree))
        self.assertIn("reason='Must rollback second part before first dependant'", new)
        self.assertNotIn('earlier_second_part_DML_path_inferred_from_exact_Native_source_order_and_later_first_part_error=True', new)
        self.assertIn('unblocked_inverse_attempt_part=None', new)
        self.assertIn('all_member_preflight_before_any_child_write=True', new)

    def test_only_three_BC_calls_use_canonical_formatter_not_shared_native_at(self):
        new, _ = d.derive('cost_cases')
        self.assertEqual(new.count('_sku23.bc_at(fixture,'), 3)
        self.assertIn("physical_at=at(fixture,1)", (ROOT/d.SOURCES['cost_native'][0]).read_text())
        for at in ('2026-10-29T17:00:00.900000+00:00', '2026-10-30T02:00:00.900000+09:00', '2026-10-29T12:00:00.900000-05:00'):
            self.assertEqual(t.bc_at(dict(at=at), 20), '2026-10-30T00:00:20+07:00')
        with self.assertRaisesRegex(AssertionError, 'AWARE_FIXTURE'):
            t.bc_at(dict(at='2026-10-29T17:00:00'), 20)

    def test_complete_engine_is_still_five_substitutions(self):
        engine = load('test_sku23_five', ROOT/'scripts/current-sku-combined-followup-qualification/derive.py')
        raw = (ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        text, proof = engine.derive(raw)
        self.assertEqual(proof['counted_changes'], 5)
        for before, after in reversed(engine.REPLACEMENTS):
            self.assertEqual(text.count(after), 1)
            text = text.replace(after, before, 1)
        self.assertEqual(text.encode(), raw)

    def test_actual_private_cost_module_imports_owned_unique_fixture_without_DB(self):
        # Faithful import-only doubles for the same retained Native imports;
        # no case callback or product runtime is called or assigned PASS.
        base=SimpleNamespace(BASE_PRODUCT='EXISTING',LOCATION='LOCATION',OPERATOR_APP='OPERATOR')
        native=SimpleNamespace(chain=SimpleNamespace(base=base),bcp=SimpleNamespace(),api=SimpleNamespace(admin=lambda cur:None))
        bf=ModuleType('cp6_bf_probe');bf.b=native;bf.one=lambda *a:None
        be=ModuleType('cp6_be_probe');sql=ModuleType('psycopg');sql.Error=type('NoSQL',(Exception,),{})
        sql.connect=lambda *a,**k:self.fail('NO_DB_IMPORT_CONTROL')
        package=ModuleType('cp7_sku_pair_conversion');package.composition=SimpleNamespace()
        chain=ModuleType('cp7_p21_current_chain_rehearsal_probe');auth=ModuleType('cp7_snapshot_cases')
        with patch.dict(sys.modules,{'cp6_be_probe':be,'cp6_bf_probe':bf,'psycopg':sql,
            'cp7_sku_pair_conversion':package,'cp7_p21_current_chain_rehearsal_probe':chain,'cp7_snapshot_cases':auth}):
            module=load('sku23_actual_private_cost_module',HERE/'cost_cases.py')
            self.assertEqual(module.SKU23_PRIVATE_DERIVATION['original_asserts'],44)
            self.assertIn('current-sku-pair-conversion-qualification/fixture.py',module.n.f.__file__)
            self.assertIn("'SKU29 different brand '+tag",d.legacy.derive('fixture')[0])
            self.assertIs(module.atomic_inverse.__globals__['n'],module.n)
            self.assertEqual(module._sku23.bc_at({'at':'2026-10-29T17:00:00+00:00'},20),'2026-10-30T00:00:20+07:00')


class SourceAndEvidence(unittest.TestCase):
    def test_full_bd2_and_historical_parent_inventory_one_product_exception(self):
        proof = c.source_only(require_clean=False)
        self.assertEqual(proof['historical_parent_files'], 13569)
        self.assertEqual(proof['unchanged_parent_files'], 13611)
        self.assertEqual(proof['actually_unchanged_bd2_files'], 13610)
        self.assertEqual(proof['parent_sql_exceptions'], 1)
        self.assertFalse(proof['financial_quantity_fullcensus_oracles_changed'])
        self.assertEqual(proof['product_changed_functions'], ['cp7_sku_conversion.action_v1(text,jsonb,uuid)'])

    def test_sql_exception_does_not_allow_an_unknown_old_pin_or_another_product_byte(self):
        self.assertEqual(t.pin_for(t.SQL, t.OLD)['sha256'], t.NEW['sha256'])
        with self.assertRaisesRegex(AssertionError, 'UNREVIEWED_OLD_SQL_PIN'):
            t.pin_for(t.SQL, dict(bytes=t.OLD['bytes'], sha256='0'*64))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); file = root/t.SQL; file.parent.mkdir(parents=True)
            file.write_bytes((ROOT/t.SQL).read_bytes())
            self.assertTrue(t.verify_pin(root, t.SQL, t.OLD))
            file.write_bytes(file.read_bytes()+b'\n')
            self.assertFalse(t.verify_pin(root, t.SQL, t.OLD))

    def test_public_parent_alias_preserves_product_and_first_local_receipts_exactly(self):
        meta=json.loads((HERE/'PUBLIC_PARENT_TRANSITION.json').read_bytes())
        self.assertEqual(t.PRODUCT_HEAD,'c05e3d689e0e4b770af40b6a6b7d7e5cd659a12b')
        self.assertEqual(meta['public_product_head'],t.PRODUCT_HEAD)
        self.assertEqual(meta['public_product_tree'],t.PRODUCT_TREE)
        self.assertEqual(meta['public_product_parent'],t.BASE)
        self.assertEqual(len(meta['product8paths_byte_exact']),8)
        for name,pin in meta['product8paths_byte_exact'].items():
            value=(ROOT/name).read_bytes()
            self.assertEqual(len(value),pin['bytes']);self.assertEqual(sha256(value).hexdigest(),pin['sha256'])
        for name,pin in meta['immutable_first_receipts'].items():
            value=(HERE/name).read_bytes()
            self.assertEqual(len(value),pin['bytes']);self.assertEqual(sha256(value).hexdigest(),pin['sha256'])
        first=gzip.decompress((HERE/meta['retained_original_SOURCE']['path']).read_bytes())
        self.assertEqual(sha256(first).hexdigest(),'b209b6a1b4d8ceac394e2736753fd76eea8e8c5d6368e1418129aa027bb8b77e')
        old=(HERE/'evidence/LOCAL_E8A_transition.py.txt').read_bytes()
        self.assertEqual(old.count(meta['original_local_product_head'].encode()),1)
        self.assertEqual(old.replace(meta['original_local_product_head'].encode(),t.PRODUCT_HEAD.encode(),1),(HERE/'transition.py').read_bytes())

    def test_complete_source_closure_needs_no_explicit_private_git_object(self):
        original=c.git
        private=('e8a22138dd46d75339cd8a12bad423303e2d4a79',
                 '824ada3f736875806f6401b150027843b1800cc4',
                 'ac68e51429b7f3d9ae16c9ff1436ae9c9509e828')
        def public_only(*args):
            self.assertFalse(any(head in arg for head in private for arg in args),'PRIVATE_GIT_OBJECT_UNAVAILABLE_IN_CI')
            return original(*args)
        with patch.object(c,'git',public_only):
            proof=c.source_only(require_clean=False)
        self.assertEqual(proof['parent_sql_exceptions'],1)
        self.assertEqual(proof['unchanged_parent_files'],13611)

    def test_private_cost_browser_guards_report_actual_transition_without_rewriting_old_manifest(self):
        for name in ('cost_guard', 'browser_guard'):
            guard = load('test_sku23_'+name, HERE/(name+'.py'))
            proof = guard.admitted()
            self.assertEqual(proof['current_source_transition']['product_source_commit'], t.PRODUCT_HEAD)
            self.assertEqual(proof['current_source_transition']['actual_successor_cases'], 0)

    def test_bd2_raw_first_failures_restore_and_missing_census_are_not_relabelled(self):
        values = {name: json.loads(value) for name, value in r.originals().items()}
        proof = r.observe(values)
        self.assertEqual(proof['cost_Native_counts'], {'PASS':1, 'INCOMPLETE':2})
        self.assertFalse(proof['full_cost_before_after_census_retained'])
        self.assertFalse(proof['usable_prerequisite'])
        self.assertEqual(proof['downstream_not_reached'], 13)
        for mutate in (lambda v:v[r.NAMES[0]].update(status='PASS'),
                       lambda v:v[r.NAMES[0]].update(baseline_full22_all_rows_all_sequences_equal=False),
                       lambda v:v[r.NAMES[3]]['gate'].update(writer_runtime=True)):
            bad = deepcopy(values); mutate(bad)
            with self.assertRaises(AssertionError):
                r.observe(bad)

    def test_historical21_gate_zero_fresh_credit_and_failed_bd2_cannot_replace_it(self):
        old = ROOT/'scripts/current-sku-combined-followup-qualification'
        gate = load('test_sku23_old_gate', old/'gate.py')
        plan = load('test_sku23_ids', old/'plan.py')
        cfg = json.loads((old/'CONFIG.json').read_bytes())
        raw = gzip.decompress((old/'retained21/CP7_SKU_PAIR_CONVERSION_NATIVE.json.gz').read_bytes())
        pkg = gzip.decompress((old/'retained21/T3_PACKAGE_INSTALL.json.gz').read_bytes())
        sources = json.loads(raw)['source_declaration']['current_installation']
        self.assertEqual(gate.admitted(cfg,raw,pkg,sources,plan.NATIVE_IDS)['fresh_cases_credited'], 0)
        current = deepcopy(sources); current['files'] = t.runtime_files(sources['files'])
        with self.assertRaisesRegex(ValueError,'DIFFERS_FROM_RETAINED'):
            gate.admitted(cfg,raw,pkg,current,plan.NATIVE_IDS)
        failed = r.originals()
        cfg = deepcopy(cfg)
        for key, blob in (('original',failed[r.NAMES[0]]),('package',failed[r.NAMES[3]])):
            cfg['accepted_native7'][key].update(bytes=len(blob),sha256=sha256(blob).hexdigest())
        with self.assertRaisesRegex(ValueError,'RETAINED_NATIVE7_NOT_PASS'):
            gate.admitted(cfg,failed[r.NAMES[0]],failed[r.NAMES[3]],current,plan.NATIVE_IDS)

    def test_new_cost_dependency_rejects_old_product_failed_or_unrestored_fresh7(self):
        text, _ = d.derive('cost_cases')
        tree = ast.parse(text)
        node = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='admit_native7')
        ids = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id=='NATIVE7_IDS' for a in n.targets))
        ns = dict(re=re, _sku23=t, NATIVE7_IDS=ids, NATIVE7_ADMISSION=None)
        exec(compile(ast.Module(body=[node], type_ignores=[]),'<actual-private-cost-source-admission>','exec'),ns)
        group = dict(counts={'PASS':7}, cases={key:dict(status='PASS',full_boundary_restored=True) for key in ids})
        args = dict(original_report_sha256='a'*64,backend_commit=t.PRODUCT_HEAD)
        self.assertEqual(ns['admit_native7'](group,**args)['backend_commit'],t.PRODUCT_HEAD)
        for old_head in ('21c69cf25defcee854beb08e998062d7e883d968','e8a22138dd46d75339cd8a12bad423303e2d4a79'):
            with self.assertRaises(AssertionError):
                ns['admit_native7'](group,**dict(args,backend_commit=old_head))
        for mutate in (lambda g:g['cases'].pop(ids[0]),lambda g:g['cases'][ids[0]].update(full_boundary_restored=False),lambda g:g.update(error='failed')):
            bad=deepcopy(group);mutate(bad)
            with self.assertRaises(AssertionError):ns['admit_native7'](bad,**args)
            self.assertIsNone(ns['NATIVE7_ADMISSION'])

    def test_fresh7_hash_comes_from_exact_retained_group_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); folder=root/'cp6-proof/t3';folder.mkdir(parents=True)
            raw=b'{"counts":{"PASS":7},"cases":{}}\n';name='CP7_SKU_PAIR_CONVERSION_NATIVE7.json';(folder/name).write_bytes(raw)
            first=dict(native=json.loads(raw),strict_group_originals=[dict(name=name,bytes=len(raw),sha256=sha256(raw).hexdigest())])
            with patch.object(t,'ROOT',root):
                self.assertEqual(t.fresh_native7_sha(first),sha256(raw).hexdigest())
                first['strict_group_originals'][0]['sha256']='0'*64
                with self.assertRaisesRegex(AssertionError,'ORIGINAL_PIN_REQUIRED'):t.fresh_native7_sha(first)


class LaunchAndRetention(unittest.TestCase):
    def test_workflow_keeps_setup_restore_and_all5_gate_steps_identical(self):
        old=yaml.safe_load((ROOT/w.OLD).read_text());new=yaml.safe_load((ROOT/w.NEW).read_text())
        self.assertEqual(new,w.derive(old))
        os=old['jobs']['p21']['steps'];ns=new['jobs']['p21']['steps']
        self.assertEqual(len(ns),len(os)+1)
        changed_names={'Check combined local oracles and existing four browser preparations',
          'Admit retained Native21c and complete declared combined source before database',
          'Run one installed SKU base7 cost3 races3 Native waits6 Auth browser4 and complete restoration',
          'Preserve exact original JSON report bytes in a bounded compressed log receipt'}
        for step in os:
            if step.get('name') in changed_names or step.get('uses','').startswith('actions/upload-artifact@'):continue
            self.assertIn(step,ns)
        self.assertEqual(new['jobs']['p21']['env'],old['jobs']['p21']['env'])
        self.assertEqual(new['on']['push']['branches'],[w.BRANCH])
        retained=next(s for s in ns if s.get('name')=='Retain exact writer-CWD SKU cost full census even on failure')
        self.assertEqual(retained['if'],'always()')
        runtime=next(s for s in ns if s.get('name','').startswith('Run one installed SKU'))
        self.assertEqual(runtime['working-directory'],'writer')
        self.assertIn('--runtime',runtime['run'])

    def test_actual_writer_relative_artifacts_copy_losslessly_and_collision_refuses(self):
        copy=load('test_sku23_retention',HERE/'retain_outputs.py')
        with tempfile.TemporaryDirectory() as tmp:
            workspace=Path(tmp);p=workspace/'writer/cp6-proof/t3';p.mkdir(parents=True)
            name='SKU_COST_NEGATIVE_abc_FULL_CURRENT_CENSUS.json';raw=b'{"before":{"sequence":3},"after":{"sequence":5}}\n';(p/name).write_bytes(raw)
            receipt=copy.retain(workspace)
            self.assertEqual((workspace/'auditor/cp6-proof/t3'/name).read_bytes(),raw)
            self.assertTrue(all(row['byte_exact'] for row in receipt['files']))
            replay=copy.retain(workspace)
            self.assertFalse(any(row['source'].endswith('SKU_COST_ARTIFACT_COPY_RECEIPT.json') for row in replay['files']))
            (p/name).write_bytes(raw+b' ')
            with self.assertRaisesRegex(ValueError,'NAME_COLLISION'):copy.retain(workspace)

    def test_scoped_argv_uses_exact_retained_guard_and_restores_object_on_success_error(self):
        text=(ROOT/'scripts/cp7_consumer_ow04_probe.py').read_text()
        guard=next(n for n in ast.parse(text).body if isinstance(n,ast.If) and 'sys.argv[1:]' in ast.unparse(n.test))
        code=compile(ast.Module(body=[guard],type_ignores=[]),'<exact-retained-argument-guard>','exec')
        old=sys.argv;sys.argv=['qualifier','--runtime'];caller=sys.argv
        try:
            with self.assertRaisesRegex(SystemExit,'accepts no arguments'):exec(code,dict(sys=sys))
            with t.scoped_argv():exec(code,dict(sys=sys));sys.argv.append('--retained-mutator')
            self.assertIs(sys.argv,caller);self.assertEqual(sys.argv,['qualifier','--runtime'])
            with self.assertRaisesRegex(RuntimeError,'local'):
                with t.scoped_argv():exec(code,dict(sys=sys));raise RuntimeError('local')
            self.assertIs(sys.argv,caller);self.assertEqual(sys.argv,['qualifier','--runtime'])
        finally:sys.argv=old

    def test_outer_unknown_flags_refuse_before_runtime_imports(self):
        for script in ('probe.py','check.py'):
            args=['--runtime'] if script=='probe.py' else []
            run=subprocess.run([sys.executable,'-B',str(HERE/script),*args,'--unaccepted'],capture_output=True,text=True)
            self.assertNotEqual(run.returncode,0)
            self.assertIn('unrecognized arguments',run.stderr)
            self.assertNotIn('ModuleNotFoundError',run.stderr)

    def test_offline_CLI_does_not_import_database_or_product_modules(self):
        code="""import sys,importlib.abc,runpy,socket
class NoRuntime(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,*a):
  if fullname=='psycopg' or fullname.startswith(('cp7_sku_pair_conversion','cp7_p21_current_chain')):raise RuntimeError('FORBIDDEN_RUNTIME_IMPORT:'+fullname)
sys.meta_path.insert(0,NoRuntime())
socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('FORBIDDEN_NETWORK'))
sys.argv=[%r,'--offline']
runpy.run_path(%r,run_name='__main__')
"""%(str(HERE/'check.py'),str(HERE/'check.py'))
        run=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn('SOURCE_ONLY_NOT_NATIVE_PASS',run.stdout)


if __name__=='__main__':
    unittest.main()
