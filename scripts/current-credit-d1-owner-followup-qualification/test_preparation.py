"""Offline controls. Every constructed PASS report below is a labelled double."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from unittest import TestCase,main
from unittest.mock import patch
import ast
import builtins
import importlib.util
import json
import os
import subprocess
import sys

import psycopg
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.dont_write_bytecode = True


def load(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


gate = load('continuation_local_pure_gate',HERE/'gate.py')
argv_scope = load('continuation_local_argv_scope',HERE/'argv_scope.py')
current = json.loads((HERE/'CONFIG.json').read_bytes())
ids = json.loads((ROOT/'scripts/current-credit-de-native-qualification/CONFIG.json').read_bytes())['native_case_ids']


def report_doubles():
    cfg = deepcopy(current)
    head,tree = 'b'*40,'c'*40
    cfg.update(frozen_parent_head=head,frozen_parent_tree=tree,parent_status='ROOT_VERIFIED_TERMINAL_NATIVE13_AND_COMPLETE_PACKAGE_PASS',
        required_qualified_parent=dict(status='ROOT_VERIFIED_TERMINAL_NATIVE13_AND_COMPLETE_PACKAGE_PASS',head=head,tree=tree))
    sources = dict(classification='SYNTHETIC_LOCAL_PARENT_SOURCE_DOUBLE_ONLY')
    frozen = dict(classification='SYNTHETIC_LOCAL_DECLARATION_DOUBLE_ONLY')
    group = dict(status='PASS',counts={'PASS':13},planned_case_ids=ids,complete_boundary_restored=True,
        cases={name:dict(status='PASS',full_boundary_restored=True,public_schema_unchanged=True)for name in ids})
    witness = dict(status='PASS',native=group,actual_Native_cases=13,used_guard_refused_before_DDL=True,
        unchanged_physical_stock_HPP_cost_GL_and_original_sale_payment=True,
        committed_source_truth=dict(I='250.00',available='250.00',net='750.00',AR='0.00'))
    outer = dict(label='CP7_CREDIT_DE_NATIVE13',status='PASS',qualification_commit=head,required_case_ids=[gate.NATIVE13_CASE],
        expected_case_count=1,observed_case_count=1,cp6_restored=True,advisor_gate=True,
        baseline_full22_all_rows_all_sequences_equal=True,baseline_advisors_equal=True,used_guard_refused_before_DDL=True,
        required_case_ids_pass=True,restore_components=dict(SYNTHETIC_RESTORE_DOUBLE=True),
        baseline_role_cleanup=dict(baseline_roles_exact=True),focused_preuse_removal=dict(used_guard_before_DDL=True),
        actual_Native_cases=13,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        committed={gate.NATIVE13_CASE:witness},source_declaration=dict(current_installation=sources,qualification=frozen))
    package = dict(status='ALL_STAGES_INSTALLED',gate={key:True for key in gate.GATES},writer_runtime=dict(status='PASS'),
        backup_restore_drill='RESTORED_IDENTICAL',primary_unchanged=True,auth_users_before=['SYNTHETIC_AUTH_DOUBLE'],
        auth_users_after=['SYNTHETIC_AUTH_DOUBLE'],run_identity=dict(tool_head=head,github_sha=head,run_id='1'))
    files = dict(status='ALL_FILES_INSTALLED',files=[dict(key=str(i),status='PASS')for i in range(30)])
    drill = dict(status='RESTORED_IDENTICAL',checks=dict(SYNTHETIC_DRILL_DOUBLE=True),data=dict(differ={}),catalog=dict(differ={}),engine=dict(equal=True))
    parsed = dict(zip(gate.ORIGINALS,(outer,group,package,files,drill)))
    raw = {key:json.dumps(value).encode()for key,value in parsed.items()}
    cfg['accepted_native13'] = dict(head=head,tree=tree,run_id=1,job_id=2,artifact_id=3,zip_bytes=4,zip_sha256='d'*64,
        **{key:dict(name=gate.ORIGINALS[key],bytes=len(value),sha256=sha256(value).hexdigest())for key,value in raw.items()})
    return cfg,raw,sources,frozen


def change_report(key,operation):
    cfg,raw,sources,frozen = report_doubles(); parsed = json.loads(raw[key]); operation(parsed)
    raw[key] = json.dumps(parsed).encode()
    cfg['accepted_native13'][key].update(bytes=len(raw[key]),sha256=sha256(raw[key]).hexdigest())
    return cfg,raw,sources,frozen


class ClosedGate(TestCase):
    def test_null_and_known_failed_heads_never_admit(self):
        with self.assertRaisesRegex(ValueError,'CLOSED'):
            gate.selected(current)
        for head in gate.REJECTED_HEADS:
            cfg,*_ = report_doubles(); cfg['accepted_native13']['head'] = head
            with self.assertRaisesRegex(ValueError,'KNOWN_FAILED'):
                gate.selected(cfg)

    def test_future_pin_requires_explicit_source_and_required_proof_rebind(self):
        cfg,*_ = report_doubles(); cfg['frozen_parent_tree'] = 'e'*40
        with self.assertRaisesRegex(ValueError,'EXPLICIT_SUCCESSFUL_SOURCE_AND_PROOF_REBIND'):
            gate.selected(cfg)
        cfg,*_ = report_doubles(); cfg['required_qualified_parent'] = None
        with self.assertRaisesRegex(ValueError,'CLOSED'):
            gate.selected(cfg)

    def test_raw_gate_structure_double_earns_zero_credit(self):
        cfg,raw,sources,frozen = report_doubles(); proof,_ = gate.admitted(cfg,raw,sources,frozen,ids)
        self.assertEqual(proof['fresh_cases_credited'],0)
        self.assertEqual(proof['retained_Native_cases'],13)

    def test_rejects_changed_raw_original_without_repin(self):
        cfg,raw,sources,frozen = report_doubles(); raw['strict_native13'] += b'\n'
        with self.assertRaisesRegex(ValueError,'ORIGINAL_BYTES_CHANGED'):
            gate.admitted(cfg,raw,sources,frozen,ids)

    def test_all_five_gates_auth_and_primary_restoration_are_required(self):
        mutations = [lambda p:p['gate'].update(writer_runtime=False),lambda p:p.update(auth_users_after=[]),lambda p:p.update(primary_unchanged=False)]
        for mutate in mutations:
            cfg,raw,sources,frozen = change_report('package',mutate)
            with self.assertRaisesRegex(ValueError,'FIVE_PACKAGE_GATES_AND_PRIMARY_AUTH'):
                gate.admitted(cfg,raw,sources,frozen,ids)

    def test_full_native_case_set_and_each_restore_are_required(self):
        for mutate in (lambda g:g['planned_case_ids'].pop(),lambda g:g['cases'][ids[0]].update(full_boundary_restored=False)):
            cfg,raw,sources,frozen = change_report('strict_native13',mutate)
            with self.assertRaisesRegex(ValueError,'EXACT_NATIVE_GROUP|CASE_OR_RESTORE|COMMITTED_FINANCIAL'):
                gate.admitted(cfg,raw,sources,frozen,ids)

    def test_package_files_and_backup_full_restore_are_required(self):
        for key,mutate in (('package_files',lambda f:f['files'].pop()),('backup_drill',lambda d:d['catalog'].update(differ={'bad':'double'}))):
            cfg,raw,sources,frozen = change_report(key,mutate)
            with self.assertRaisesRegex(ValueError,'THIRTY_PACKAGE_FILES|BACKUP_RESTORE'):
                gate.admitted(cfg,raw,sources,frozen,ids)

    def test_actual_parent_source_and_original_declaration_must_match(self):
        cfg,raw,sources,frozen = report_doubles()
        with self.assertRaisesRegex(ValueError,'ACTUAL_PARENT_SOURCE_OR_DECLARATION'):
            gate.admitted(cfg,raw,dict(wrong='LOCAL_DOUBLE'),frozen,ids)

    def test_retained_failed_a994_is_not_relabelled(self):
        import gzip
        raw = gzip.decompress((ROOT/current['retained_failed_a994']['path']).read_bytes())
        gate.retained_failure(current,raw)
        with self.assertRaisesRegex(ValueError,'FAILED_A994_RAW_BYTES'):
            gate.retained_failure(current,raw+b'\n')


class ImportsAndSources(TestCase):
    def test_owned_prepare_and_unchanged_target_oracle_are_actual_bindings(self):
        with argv_scope.inherited_arguments(),patch.object(psycopg,'connect',side_effect=AssertionError('IMPORT_ATTEMPTED_DB')):
            business = load('continuation_owned_fixture_import_no_db',ROOT/'scripts/current-credit-d1-continuation-qualification/cases.py')
        from cp7_credit_correction_de import native_fixture as owned
        self.assertIs(business.n.fixture,owned)
        self.assertIs(business.n.fixture.prepare,owned.prepare)
        self.assertIs(business.n.target_document_ar,owned.retained._document_ar)
        inventory = owned.inventory()
        self.assertEqual(inventory['substitutions'],10); self.assertEqual(len(inventory['functions']),5)
        self.assertFalse(inventory['Native_execution'])

    def test_closed_check_probe_and_fetch_never_import_or_call_runtime(self):
        original = builtins.__import__
        def guard(name,*args,**kwargs):
            if name.startswith(('psycopg','cp7_','cp6_')):
                raise AssertionError('CLOSED_GATE_IMPORTED_RUNTIME:'+name)
            return original(name,*args,**kwargs)
        with patch.object(builtins,'__import__',guard),patch.object(subprocess,'check_output',side_effect=AssertionError('CLOSED_GATE_CALLED_REMOTE_OR_GIT')):
            for module,function in (('check.py','run'),('probe.py','runtime'),('fetch_prerequisite.py','main')):
                with self.assertRaisesRegex(ValueError,'CLOSED'):
                    getattr(load('continuation_closed_'+module,HERE/module),function)()

    def test_exact_f671_callbacks_and_oracles_survive_bounded_transition(self):
        transition = load('continuation_local_exact_transition',HERE/'transition.py')
        self.assertEqual(transition.check()['unchanged_callback_count'],3)
        original = Path.read_bytes; cases = ROOT/'scripts/current-credit-d1-continuation-qualification/cases.py'
        def altered(path):
            raw = original(path); return raw+b'\n'if path == cases else raw
        with patch.object(Path,'read_bytes',altered):
            with self.assertRaisesRegex(ValueError,'FROZEN_CASE_OR_ORACLE'):
                transition.check()

    def test_engine_keeps_all_six_frozen_substitutions(self):
        derive = load('continuation_local_exact_engine',HERE/'derive.py').derive
        raw = (ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        _,proof = derive(raw); self.assertEqual(proof,current['runner_derivation'])
        with self.assertRaisesRegex(ValueError,'EXACT_RUNNER_ANCHOR'):
            derive(raw.replace(b"report['actual_Native_cases']=7",b"report['actual_Native_cases']=999",1))

    def test_faithful_inherited_no_argument_guard_and_finally_restore(self):
        path = ROOT/'scripts/ow04-payment-positive-qualification/native26_probe.py'; text = path.read_text()
        node = next(n for n in ast.parse(text).body if isinstance(n,ast.If)and ast.unparse(n.test) == 'sys.argv[1:]')
        code = compile(ast.get_source_segment(text,node),str(path),'exec')
        original = ['continuation-wrapper','--runtime']
        with patch.object(sys,'argv',original):
            with self.assertRaises(SystemExit):exec(code,dict(sys=sys))
            with argv_scope.inherited_arguments():exec(code,dict(sys=sys))
            self.assertIs(sys.argv,original); self.assertEqual(sys.argv,['continuation-wrapper','--runtime'])
            with self.assertRaisesRegex(ValueError,'LOCAL_INHERITED_IMPORT_EXCEPTION'):
                with argv_scope.inherited_arguments():
                    exec(code,dict(sys=sys)); raise ValueError('LOCAL_INHERITED_IMPORT_EXCEPTION')
            self.assertIs(sys.argv,original)
            with self.assertRaises(SystemExit):exec(code,dict(sys=sys))

    def test_lazy_closed_admission_restores_outer_arguments(self):
        admission = load('continuation_local_lazy_admission',HERE/'admission.py')
        original = ['continuation-wrapper','--runtime']
        with patch.object(sys,'argv',original):
            with self.assertRaisesRegex(ValueError,'CLOSED'):admission.admitted(None,{})
            self.assertIs(sys.argv,original)

    def test_unknown_wrapper_cli_arguments_stay_rejected(self):
        for filename in ('check.py','probe.py'):
            result = subprocess.run([sys.executable,'-B',str(HERE/filename),'--unknown-control'],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('CLOSED_EXACT',result.stderr)

    def test_ci_cannot_regenerate_source(self):
        writer = load('continuation_local_bind',HERE/'bind.py')
        with patch.dict(os.environ,{'CI':'true'}):
            with self.assertRaisesRegex(ValueError,'CANNOT_BE_REGENERATED_IN_CI'):writer.bind()

    def test_workflow_preserves_unaffected_setup_cleanup_and_shell(self):
        workflow = load('continuation_local_workflow_derivation',HERE/'workflow.py')
        old = yaml.safe_load((ROOT/workflow.OLD).read_bytes()); actual = yaml.safe_load((ROOT/workflow.NEW).read_bytes())
        self.assertEqual(actual,workflow.derive(old,current['root_execution_branch']))
        self.assertEqual(actual['jobs']['p21']['steps'][1]['name'],workflow.EARLY)
        changed = {'Admit exact vendor parent and declared D1 child before database','Run actual D1 Native13 and complete restoration',
                   'Preserve exact original JSON report bytes in a bounded compressed log receipt'}
        for step in old['jobs']['p21']['steps']:
            if step.get('name')in changed or step.get('uses','').startswith('actions/upload-artifact@'):continue
            self.assertIn(step,actual['jobs']['p21']['steps'])
        for step in actual['jobs']['p21']['steps']:
            if 'run'in step:
                result = subprocess.run(['bash','-n'],input=step['run'],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,(step.get('name'),result.stderr))


if __name__ == '__main__':
    main(verbosity=2)
