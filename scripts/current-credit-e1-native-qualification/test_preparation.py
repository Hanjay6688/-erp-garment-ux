"""Offline controls, with explicit mock proof dictionaries; zero Native credit."""
from contextlib import redirect_stdout
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import ast
import base64
import gzip
import importlib.util
import io
import json
import os
import shutil
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
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


gate = load('e1_unit_closed_gate', HERE/'gate.py')
plan = load('e1_unit_literal_plan', HERE/'plan.py')
workflow = load('e1_unit_pure_workflow', HERE/'workflow.py')
admission = load('e1_unit_source_admission', HERE/'admission.py')
component = load('e1_unit_inert_component', HERE/'component.py')


def literal(path, key):
    return next(ast.literal_eval(node.value) for node in ast.parse(path.read_text()).body
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == key for t in node.targets))


def sample(mutate=lambda a, g, p: None):
    """Synthetic unit shape only, never a runtime receipt or saved Original."""
    sources, declaration = {'LOCAL_TEST_ONLY': True}, {'LOCAL_TEST_ONLY': True}
    group = dict(status='PASS', counts={'PASS': 13}, planned_case_ids=list(plan.D1_IDS), complete_boundary_restored=True,
        cases={name: dict(status='PASS', full_boundary_restored=True, public_schema_unchanged=True) for name in plan.D1_IDS})
    actual = dict(label='CP7_CREDIT_DE_NATIVE13', status='PASS', qualification_commit='b'*40,
        expected_case_count=1, observed_case_count=1, required_case_ids=[gate.NATIVE_CASE],
        cp6_restored=True, advisor_gate=True, baseline_full22_all_rows_all_sequences_equal=True,
        baseline_advisors_equal=True, used_guard_refused_before_DDL=True, required_case_ids_pass=True,
        baseline_role_cleanup={'baseline_roles_exact': True}, focused_preuse_removal={'used_guard_before_DDL': True},
        source_declaration=dict(current_installation=sources, qualification=declaration),
        committed={gate.NATIVE_CASE: dict(status='PASS', native=group, actual_Native_cases=13,
            used_guard_refused_before_DDL=True, unchanged_physical_stock_HPP_cost_GL_and_original_sale_payment=True)})
    package = dict(gate={key: True for key in gate.GATES}, run_identity={'tool_head': 'b'*40},
        writer_runtime={'status': 'PASS'}, auth_users_before=0, auth_users_after=0)
    mutate(actual, group, package)
    raw = {key: json.dumps(value).encode() for key, value in (('original', actual), ('native_group', group), ('package', package))}
    config = json.loads((HERE/'CONFIG.json').read_bytes())
    required = dict(head='b'*40, tree='c'*40, status='ROOT_VERIFIED_TERMINAL_NATIVE13_AND_COMPLETE_PACKAGE_PASS')
    pin = dict(head='b'*40, tree='c'*40, run_id=1, job_id=2, artifact_id=3, zip_bytes=4, zip_sha256='d'*64)
    for key, name in (('original', 'CP7_CREDIT_DE_NATIVE13.json'), ('native_group', 'CP7_CREDIT_DE_NATIVE13_CASES.json'), ('package', 'T3_PACKAGE_INSTALL.json')):
        pin[key] = dict(name=name, bytes=len(raw[key]), sha256=sha256(raw[key]).hexdigest())
    config.update(frozen_parent_head=required['head'], frozen_parent_tree=required['tree'], parent_status=required['status'], required_qualified_parent=required, accepted_D1=pin)
    return config, raw, sources, declaration


class ClosedProof(unittest.TestCase):
    def test_current_configuration_stays_closed_after_real_parent_failure(self):
        cfg = json.loads((HERE/'CONFIG.json').read_bytes())
        if cfg['frozen_parent_head'] in gate.REJECTED_HEADS:
            self.assertIsNone(cfg['accepted_D1']); self.assertIsNone(cfg['required_qualified_parent'])
        elif cfg['accepted_D1'] is not None:
            self.assertEqual(gate.selected(cfg),cfg['accepted_D1'])
        with self.assertRaisesRegex(ValueError, 'E1_CLOSED_'):
            gate.selected(dict(cfg,accepted_D1=None,required_qualified_parent=None))

    def test_closed_entrypoints_refuse_before_get_or_product_import(self):
        # A real temporary closed caller has no product modules or artifacts.
        # This remains offline after root binds the repository's live pin.
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'closed-caller';path.mkdir()
            (path/'CONFIG.json').write_text(json.dumps(dict(accepted_D1=None,required_qualified_parent=None)))
            shutil.copyfile(HERE/'gate.py',path/'gate.py')
            for name in ('check.py', 'fetch_prerequisite.py', 'probe.py'):
                shutil.copyfile(HERE/name,path/name)
                run = subprocess.run([sys.executable, '-B', str(path/name)], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0, name)
                self.assertIn('E1_CLOSED_', run.stderr, name)
                self.assertNotIn('ModuleNotFoundError', run.stderr, name)
                self.assertNotIn('gh:', run.stderr, name)

    def test_mock_exact_bytes_grant_no_fresh_execution_credit(self):
        cfg, raw, current, declaration = sample()
        proof = gate.admitted(cfg, raw, current, declaration, plan.D1_IDS)
        self.assertEqual(proof['fresh_E_cases_credited'], 0)
        changed = dict(raw, original=raw['original']+b' ')
        with self.assertRaisesRegex(ValueError, 'BYTES_CHANGED'):
            gate.admitted(cfg, changed, current, declaration, plan.D1_IDS)

    def test_known_failed_heads_never_unlock_even_with_pass_shaped_mock(self):
        for head in gate.REJECTED_HEADS:
            cfg, raw, current, declaration = sample()
            cfg['accepted_D1']['head'] = head; cfg['required_qualified_parent']['head'] = head; cfg['frozen_parent_head'] = head
            with self.assertRaisesRegex(ValueError, 'KNOWN_INCOMPLETE'):
                gate.admitted(cfg, raw, current, declaration, plan.D1_IDS)

    def test_each_partial_or_restore_or_package_auth_failure_refuses(self):
        changes = [lambda a,g,p:a.update(status='INCOMPLETE'),
            lambda a,g,p:a.update(cp6_restored=False), lambda a,g,p:a.update(baseline_full22_all_rows_all_sequences_equal=False),
            lambda a,g,p:a['baseline_role_cleanup'].update(baseline_roles_exact=False),
            lambda a,g,p:a['focused_preuse_removal'].update(used_guard_before_DDL=False),
            lambda a,g,p:g.update(counts={'PASS':5,'INCOMPLETE':8}),
            lambda a,g,p:g['cases'][plan.D1_IDS[0]].update(public_schema_unchanged=False),
            lambda a,g,p:g.update(complete_boundary_restored=False),
            lambda a,g,p:p['gate'].update(writer_runtime=False), lambda a,g,p:p.update(auth_users_after=1),
            lambda a,g,p:p.pop('auth_users_before'),
            lambda a,g,p:a['committed'][gate.NATIVE_CASE].update(unchanged_physical_stock_HPP_cost_GL_and_original_sale_payment=False)]
        for change in changes:
            cfg, raw, current, declaration = sample(change)
            with self.assertRaises(ValueError):
                gate.admitted(cfg, raw, current, declaration, plan.D1_IDS)
        cfg, raw, current, declaration = sample()
        with self.assertRaisesRegex(ValueError, 'DIFFERS_FROM_ORIGINAL'):
            gate.admitted(cfg, raw, {'OTHER_SOURCE': True}, declaration, plan.D1_IDS)

    def test_actual_retained_a994_five_eight_raw_is_lossless_and_negative(self):
        cfg = json.loads((HERE/'CONFIG.json').read_bytes())
        raw = gzip.decompress((ROOT/cfg['retained_failed_D1']['path']).read_bytes())
        proof = gate.retained_failure(cfg, raw)
        self.assertFalse(proof['usable_prerequisite']); self.assertEqual(proof['fresh_E_cases_credited'], 0)
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_BYTES_CHANGED'):
            gate.retained_failure(cfg, raw+b' ')
        # A different successor label still cannot turn this real partial group into PASS.
        def reuse_partial(actual, group, package):
            group.clear(); group.update(json.loads(raw))
        test_cfg, test_raw, current, declaration = sample(reuse_partial)
        with self.assertRaisesRegex(ValueError, 'COMPLETE_EXACT_NATIVE_GROUP'):
            gate.admitted(test_cfg, test_raw, current, declaration, plan.D1_IDS)


class SourceAndRestore(unittest.TestCase):
    def test_literal_plans_equal_frozen_source_and_only_seventeen_E_execute(self):
        self.assertEqual(plan.D1_IDS, literal(ROOT/'scripts/cp7_credit_correction_de/cases.py', 'IDS'))
        self.assertEqual(plan.E_IDS, literal(ROOT/'scripts/cp7_credit_correction_de/e_cases.py', 'IDS'))
        self.assertEqual(len(plan.E_IDS), len(set(plan.E_IDS))); self.assertEqual(len(plan.E_IDS), 17)
        src = (HERE/'component.py').read_text()
        self.assertIn('native.strict_group(LABEL, business.cases, verify)', src)
        self.assertIn('fresh_D1_cases=0', src)

    def test_same_six_counted_changes_keep_every_restore_and_guard_body(self):
        original = (ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        derive = load('e1_unit_actual_exact_deriver', HERE/'derive.py')
        old = load('e1_unit_frozen_D1_deriver', ROOT/'scripts/current-credit-de-native-qualification/derive.py')
        changed, proof = derive.derive(original); ast.parse(changed)
        self.assertEqual(proof, json.loads((ROOT/'scripts/current-credit-de-native-qualification/CONFIG.json').read_bytes())['runner_derivation'])
        for before, after in reversed(old.REPLACEMENTS):
            self.assertEqual(changed.count(after), 1); changed = changed.replace(after, before, 1)
        self.assertEqual(changed.encode(), original)

    def test_one_historical_endpoint_change_keeps_old_admission_hash_oracles(self):
        path = ROOT/'scripts/current-credit-de-native-qualification/admission.py'
        raw = path.read_bytes(); parent = json.loads((HERE/'CONFIG.json').read_bytes())['frozen_parent_head']
        changed, proof = admission.historical_D1_admission(raw, parent)
        self.assertEqual(proof['counted_changes'], 1)
        self.assertEqual(changed.replace("cfg['base_head'], '"+parent+"'", "cfg['base_head'], 'HEAD'", 1).encode(), raw)
        with self.assertRaisesRegex(ValueError, 'EXACT_HISTORICAL'):
            admission.historical_D1_admission(raw+raw, parent)

    def test_failed_strict_original_is_retained_byte_exact_even_without_pass(self):
        previous_root, previous_label = component.ROOT, component.LABEL
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'strict'; source.mkdir()
            raw = b'{"status":"INCOMPLETE","cases":{"FIRST":{"status":"INCOMPLETE"}}}\n'
            (source/'UNIT.json').write_bytes(raw)
            component.ROOT, component.LABEL = root, 'UNIT'
            try:
                report = {}; component.retain_originals(SimpleNamespace(r1=SimpleNamespace(OUT=source)), report)
                self.assertEqual((root/'cp6-proof/t3/UNIT.json').read_bytes(), raw)
                self.assertEqual(report['strict_group_originals'][0]['sha256'], sha256(raw).hexdigest())
                self.assertNotIn('status', report)
            finally:
                component.ROOT, component.LABEL = previous_root, previous_label

    def test_only_declared_disposable_target_allowed(self):
        valid = SimpleNamespace(info=SimpleNamespace(host='localhost', port=54322))
        cursor = SimpleNamespace(execute=lambda _: SimpleNamespace(fetchone=lambda: ('cp6_rollback',)))
        component.require_local(valid, cursor)
        for host, port in (('remote.example',54322), ('localhost',5432)):
            with self.assertRaisesRegex(ValueError, 'LOCAL_DISPOSABLE'):
                component.require_local(SimpleNamespace(info=SimpleNamespace(host=host,port=port)), cursor)
        with self.assertRaisesRegex(ValueError, 'DISPOSABLE_DATABASE'):
            component.require_local(valid, SimpleNamespace(execute=lambda _: SimpleNamespace(fetchone=lambda: ('postgres',))))

    def test_current_source_hashes_and_frozen_parent_declaration_remain_complete(self):
        source = json.loads((HERE/'SOURCE.json').read_bytes())
        self.assertEqual(source['actual_executions'], 0)
        for name, pin in source['files'].items():
            raw = (ROOT/name).read_bytes(); self.assertEqual(len(raw), pin['bytes'], name); self.assertEqual(sha256(raw).hexdigest(), pin['sha256'], name)
        old = json.loads((ROOT/'scripts/current-credit-de-native-qualification/SOURCE.json').read_bytes())
        self.assertEqual(old, source['frozen_D1_source'])
        self.assertTrue(set(old['files']) <= set(source['frozen_parent_files']))

    def test_writer_binder_refuses_in_CI_before_any_generation(self):
        run = subprocess.run([sys.executable,'-B',str(HERE/'bind.py')],env=dict(os.environ,CI='true'),capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0); self.assertIn('SOURCE_CANNOT_BE_REGENERATED_IN_CI',run.stderr)


class Workflow(unittest.TestCase):
    def test_pure_derivation_retains_unaffected_setup_cleanup_and_package_steps(self):
        cfg = json.loads((HERE/'CONFIG.json').read_bytes())
        old = yaml.safe_load((ROOT/workflow.OLD).read_text()); new = yaml.safe_load((ROOT/workflow.NEW).read_text())
        self.assertEqual(new, workflow.derive(old,cfg['branch']))
        steps = new['jobs']['p21']['steps']
        changed = ('Admit exact vendor parent and declared D1 child before database',
                   'Run actual D1 Native13 and complete restoration',
                   'Preserve exact original JSON report bytes in a bounded compressed log receipt')
        for step in old['jobs']['p21']['steps']:
            if step.get('name') in changed or step.get('uses','').startswith('actions/upload-artifact@'):
                continue
            self.assertIn(step,steps)
        self.assertEqual(steps[1]['name'],workflow.EARLY)
        names = [s.get('name') for s in steps]
        self.assertLess(names.index(workflow.FETCH),names.index('Start disposable database'))
        self.assertLess(names.index(workflow.ADMIT),names.index('Start disposable database'))
        self.assertEqual(new['on']['push'],dict(branches=[cfg['branch']],paths=[workflow.NEW,workflow.NS+'/**']))
        for name in ('Remove disposable database','Preserve exact original JSON report bytes in a bounded compressed log receipt'):
            self.assertEqual(next(s for s in steps if s.get('name')==name)['if'],'always()')
        self.assertEqual(next(s for s in steps if s.get('uses','').startswith('actions/upload-artifact@'))['if'],'always()')

    def test_bounded_log_receipt_preserves_original_bytes_without_reserializing(self):
        module = load('e1_unit_exact_original_log',HERE/'retain_reports.py')
        with tempfile.TemporaryDirectory() as directory:
            raw = b'{"status":"INCOMPLETE", "ordered": [3,2,1]}\n'; root=Path(directory)
            (root/module.NAMES[0]).write_bytes(raw); buffer=io.StringIO()
            with redirect_stdout(buffer):module.retain(root)
            receipt=json.loads(buffer.getvalue())
            self.assertEqual(gzip.decompress(base64.b64decode(receipt['gzip_base64'])),raw)
            self.assertEqual(receipt['raw_sha256'],sha256(raw).hexdigest())


if __name__ == '__main__':
    unittest.main()
