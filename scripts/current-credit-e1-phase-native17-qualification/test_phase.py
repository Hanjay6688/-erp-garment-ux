"""Source/ABI/closed import controls; no actual DB, Native or synthetic receipts."""
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
from unittest import mock
import ast
import contextlib
import copy
import importlib.util
import io
import json
import sys
import unittest
import yaml

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD=ROOT/'scripts/current-credit-e1-native-qualification'
CURRENT=ROOT/'scripts/current-credit-e1-current-d1-native17-qualification'


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


class Phase(unittest.TestCase):
    def test_complete_public_files_modes_source319_and_new_closure_before_historical_intake(self):
        proof=load('e_phase_test_complete_source',HERE/'source_check.py').check()
        self.assertEqual(proof['historical319']['whole_public_base_files'],13696)
        self.assertEqual(proof['historical319']['source_pins'],319)
        self.assertEqual(proof['actual_new_Native'],0)
        self.assertEqual(proof['public_files'],13733)

    def test_actual_current_E_source_bridge_and_frozen_parent174(self):
        source=load('e_phase_test_source_admission',HERE/'admission.py').source_only()
        self.assertEqual(len(source['frozen_D1_source']['files']),174)
        self.assertEqual(source['actual_executions'],0)

    def test_full_current_source_failure_precedes_any_private_historical_reader(self):
        m=load('e_phase_test_order',HERE/'admission.py')
        with mock.patch.object(m,'load',return_value=SimpleNamespace(selected=lambda cfg:{})),mock.patch.object(m,'source_only',side_effect=ValueError('CURRENT_SOURCE_REFUSED')),mock.patch.object(m,'current',side_effect=AssertionError('too early')):
            with self.assertRaisesRegex(ValueError,'CURRENT_SOURCE_REFUSED'):m.admitted(object(),{})

    def test_exact_private_metadata_transitions_and_unchanged_historical_read_routes(self):
        d=load('e_phase_test_routes',HERE/'derive.py')
        text,proof=d.current_admission((CURRENT/'admission.py').read_bytes())
        self.assertEqual(proof['counted_changes'],3);self.assertIsNotNone(compile(text,'<current-source-reader>','exec'))
        _,proof=d.admission((OLD/'admission.py').read_bytes());self.assertEqual(proof['counted_source_routing_changes'],2)
        _,proof=d.prepared_check((ROOT/'scripts/current-credit-e1-consumer-phase-successor/check.py').read_bytes());self.assertEqual(proof['counted_changes'],3)
        _,proof=d.fetch((OLD/'fetch_prerequisite.py').read_bytes());self.assertEqual(proof['counted_changes'],1)

    def test_natural_current_nine_files_two_reviewed_changes_no_dependency_projection(self):
        cfg=json.loads((HERE/'CONFIG.json').read_bytes());old=cfg['E_historical_runtime_files'];now=cfg['E_runtime_files']
        self.assertEqual(set(now),set(old));self.assertEqual(len(now),9)
        self.assertEqual({k for k in now if now[k]!=old[k]},{'note_carry/06_owning.sql','note_carry/07_profile_closure.sql'})
        for name,digest in now.items():self.assertEqual(sha256((ROOT/'scripts/cp7_credit_correction_de'/name).read_bytes()).hexdigest(),digest)
        deps=json.loads((ROOT/'scripts/cp7_credit_correction_de/E_DEPENDENCIES.json').read_bytes());self.assertEqual(deps['runtime_sources'],old)
        self.assertEqual(json.loads((HERE/'PRODUCT_TRANSITION.json').read_bytes())['private_function_count'],{'before':40,'after':41})

    def test_API_and_all_original_seventeen_callback_bodies_exact(self):
        proof=load('e_phase_test_API',HERE/'api_check.py').check();self.assertGreater(proof['function_bodies'],10)
        old=json.loads((CURRENT/'API.json').read_bytes());self.assertEqual(old,json.loads((HERE/'API.json').read_bytes()))
        origin=json.loads((HERE/'ORIGIN.json').read_bytes())
        self.assertEqual(sha256((ROOT/'scripts/cp7_credit_correction_de/e_cases.py').read_bytes()).hexdigest(),origin['feba_case_sha256'])
        plan=load('e_phase_test_plan',HERE/'plan.py');self.assertEqual(len(plan.E_IDS),17)

    def test_six_substitutions_engine_and_committed80_witness_byte_exact(self):
        raw=(ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        _,proof=load('e_phase_test_full_engine',OLD/'derive.py').derive(raw)
        cfg=json.loads((HERE/'CONFIG.json').read_bytes())
        for key in ('original_sha256','derived_sha256','counted_changes'):self.assertEqual(proof[key],cfg['runner_derivation'][key])
        component=(OLD/'component.py').read_text()
        for value in ("business.basic.apply(cur, pair, '80.00')",'conn.commit()','product.rollback_delta_preuse(cur, state)','catalog._data(cur) != before_data'):
            self.assertIn(value,component)
        self.assertIn('component.py',(HERE/'probe.py').read_text())

    def test_workflow_exact_all_unaffected_steps_and_cleanup_and_artifact_scope(self):
        m=load('e_phase_test_workflow',HERE/'workflow.py');expected,proof=m.derive((ROOT/m.PARENT).read_bytes())
        self.assertEqual((ROOT/m.PATH).read_text(),expected)
        old=yaml.safe_load((ROOT/m.PARENT).read_text());new=yaml.safe_load(expected)
        steps=new['jobs']['p21']['steps'];self.assertEqual(len(steps),73)
        self.assertEqual(new['on']['push']['branches'],[m.BRANCH]);self.assertIn(m.BRANCH,new['jobs']['p21']['if'])
        self.assertIn('gate.py',steps[1]['run']);self.assertNotIn('source_check.py',steps[1]['run'])
        self.assertIn('materialize.py',steps[4]['run']);self.assertIn('source_check.py',steps[5]['run'])
        self.assertIn('fetch_prerequisite.py',steps[9]['run'])
        for i in (58,59,60,61,64,65,66,67,70):self.assertEqual(old['jobs']['p21']['steps'][i],steps[i+1])
        self.assertEqual(steps[-1]['with']['path'],'auditor/cp6-proof/t3')
        self.assertEqual(steps[-1]['if'],'always()')


class Closed(unittest.TestCase):
    def setUp(self):
        self.gate=load('e_phase_test_gate',HERE/'gate.py');self.cfg=json.loads((HERE/'CONFIG.json').read_bytes())

    def test_own_null_fresh17_is_not_a_circular_prerequisite(self):
        self.assertIsNone(self.cfg['accepted_native17']);self.assertEqual(self.gate.selected(self.cfg)['head'],self.gate.PARENT)

    def test_missing_parent_or_source_binding_refuses_before_retained_import(self):
        for key in ('accepted_D1','accepted_raw_parent','required_qualified_parent','prepared_backend'):
            cfg=copy.deepcopy(self.cfg);cfg[key]=None
            with mock.patch.object(self.gate,'original',side_effect=AssertionError('too early')):
                with self.assertRaisesRegex(ValueError,'CLOSED_QUALIFIED_PARENT'):self.gate.selected(cfg)

    def test_closed_runtime_and_fetch_refuse_before_product_GET_or_DB(self):
        pending=copy.deepcopy(self.cfg);pending['accepted_D1']=None;read=Path.read_bytes
        def read_bytes(path):return json.dumps(pending).encode()if path==HERE/'CONFIG.json'else read(path)
        probe=load('e_phase_test_probe',HERE/'probe.py');fetch=load('e_phase_test_fetch',HERE/'fetch_prerequisite.py')
        with mock.patch.object(Path,'read_bytes',read_bytes),mock.patch('subprocess.check_output',side_effect=AssertionError('too early')),mock.patch('importlib.import_module',side_effect=AssertionError('too early')):
            for entry in (probe.runtime,fetch.main):
                with self.assertRaisesRegex(ValueError,'CLOSED_QUALIFIED_PARENT'):entry()

    def test_failed_D1_or_failed_E_may_not_be_parent(self):
        for head in ('0770541c94937ee5013c8ea9ae607c99260d2993','8a8dcb8509f1d6b33600239521a9b157c81bf9bc','a99463ca3ea2f1a71b22f0354df83f1b5a42b71b','d902e4d2e65cf5b382af1ab041120611f9a61078','8be4c15a37dcfc6186e32f396df78291ff1b957c'):
            cfg=copy.deepcopy(self.cfg);cfg['accepted_D1']['head']=head
            with self.assertRaises(ValueError):self.gate.selected(cfg)

    def test_unknown_cli_flag_rejected_before_import_boundary(self):
        for name in ('probe.py','check.py'):
            m=load('e_phase_test_unknown_'+name,HERE/name)
            with mock.patch.object(m,'load',side_effect=AssertionError('too early')),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit)as got:m.main(['--unknown'])
                self.assertEqual(got.exception.code,2)

    def test_import_boundary_restores_exact_caller_object_after_BaseExceptions(self):
        m=load('e_phase_test_argv',HERE/'argv_boundary.py');caller,contents=sys.argv,sys.argv[:]
        try:
            for error in (RuntimeError('test'),SystemExit('test'),KeyboardInterrupt()):
                sys.argv=['caller','--runtime'];original=sys.argv
                try:
                    with m.inherited_imports():
                        self.assertEqual(sys.argv,['caller']);original.append('mutation');sys.argv=['replacement'];raise error
                except BaseException as got:self.assertIs(got,error)
                self.assertIs(sys.argv,original);self.assertEqual(original,['caller','--runtime'])
        finally:caller[:]=contents;sys.argv=caller


if __name__=='__main__':unittest.main()
