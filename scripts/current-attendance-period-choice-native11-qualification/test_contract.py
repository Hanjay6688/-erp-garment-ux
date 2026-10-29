"""Source, original-byte, CLI and synthetic guards only. No DB or Native."""
from copy import deepcopy
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import ast
import importlib.util
import json
import sys
import unittest
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


derive = load('s03_test_derivation', HERE / 'derive.py')
proofs = load('s03_test_original_inputs', HERE / 'proof_inputs.py')
boundary = load('s03_test_argv_boundary', HERE / 'argv_boundary.py')
workflow = load('s03_test_workflow_derivation', HERE / 'workflow.py')
gate = load('s03_test_result_gate', HERE / 'result_gate.py')
cfg = json.loads((HERE / 'CONFIG.json').read_bytes())


def function(name):
    """Execute only one declared pure guard, never import its DB runtime."""
    tree = ast.parse((HERE / 'native_runner.py').read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    values = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<LOCAL_PURE_GUARD>', 'exec'), values)
    return values[name]


class Contract(unittest.TestCase):
    def test_full_source_and_exact80_frozen_component_admit_no_native_claim(self):
        value = load('s03_test_source_admission', HERE / 'source_check.py').check()
        self.assertEqual((value['frozen_S03_files'], value['existing_captures'], value['private_clones']), (80, 13, 2))
        self.assertFalse(value['Native_executed'])
        self.assertFalse(value['source_base_is_runtime_prerequisite'])

    def test_source_hash_tamper_refuses_before_git_or_runtime_import(self):
        source = json.loads((HERE / 'SOURCE.json').read_bytes())
        source['files'][next(iter(source['files']))]['sha256'] = '0' * 64
        module = load('s03_test_source_tamper', HERE / 'source_check.py')
        with TemporaryDirectory() as directory:
            here = Path(directory)
            (here / 'CONFIG.json').write_bytes((HERE / 'CONFIG.json').read_bytes())
            (here / 'SOURCE.json').write_text(json.dumps(source))
            with patch.object(module.subprocess, 'check_output', side_effect=AssertionError('NO_GIT_AFTER_BAD_SOURCE')):
                with self.assertRaisesRegex(ValueError, 'SOURCE_CHANGED'):
                    module.check(ROOT, here)

    def test_inherited_untracked_workflow_proof_has_no_unverified_allowance(self):
        module = load('s03_test_inherited_workflow_input', HERE / 'source_check.py')
        source = json.loads((HERE / 'SOURCE.json').read_bytes())
        name = next(iter(source['inherited_untracked_workflow_proof_inputs']))
        target = ROOT / name
        original_read = Path.read_bytes
        original_exists = Path.exists
        def read(path):
            return b'SYNTHETIC_WRONG_INHERITED_PROOF' if path == target else original_read(path)
        def exists(path):
            return True if path == target else original_exists(path)
        with patch.object(Path, 'read_bytes', read), patch.object(Path, 'exists', exists):
            with self.assertRaisesRegex(ValueError, 'INHERITED_WORKFLOW_PROOF_CHANGED'):
                module.check()

    def test_exact_six_whole_engine_derivation_is_reversible(self):
        raw = (ROOT / cfg['vendor_probe_path']).read_bytes()
        changed, pin = derive.derive(raw)
        self.assertEqual(pin, cfg['runner_derivation'])
        self.assertEqual(pin['counted_changes'], 6)
        for before, after in reversed(derive.REPLACEMENTS):
            self.assertEqual(changed.count(after), 1)
            changed = changed.replace(after, before, 1)
        self.assertEqual(changed.encode(), raw)

    def test_missing_or_repeated_engine_anchor_refuses(self):
        raw = (ROOT / cfg['vendor_probe_path']).read_bytes()
        marker = derive.REPLACEMENTS[0][0].encode()
        for bad in (raw.replace(marker, b'MISSING', 1), raw + b'\n' + marker):
            with self.assertRaisesRegex(ValueError, 'EXACT_VENDOR_ANCHOR'):
                derive.derive(bad)

    def test_four_raw_and_compressed_originals_are_actual_exact41c_inputs(self):
        actual = proofs.documents()
        self.assertEqual(len(actual), 4)
        report = actual['CP7_VENDOR_RECEIVABLE_COMBINED11.json']['document']
        self.assertEqual(report['qualification_commit'], cfg['qualified_parent_commit'])
        self.assertEqual((report['actual_Native_cases'], report['actual_two_session_races'], report['actual_Auth_HTTP_cases']), (7, 3, 1))
        self.assertEqual(report['status'], 'PASS')

    def test_materializer_only_creates_missing_or_preserves_exact_existing_inputs(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = proofs.materialize(root)
            self.assertEqual(len(first['created']), 4)
            files = {name: ((root / name).read_bytes(), (root / name).stat().st_mtime_ns) for name in first['created']}
            second = proofs.materialize(root)
            self.assertEqual(second['created'], [])
            self.assertEqual(set(second['exact_existing_preserved']), set(files))
            for name, original in files.items():
                self.assertEqual(((root / name).read_bytes(), (root / name).stat().st_mtime_ns), original)

    def test_wrong_existing_historical_input_refuses_before_creating_other_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / proofs.HISTORICAL
            target.mkdir(parents=True)
            first = target / (next(iter(cfg['retained41c'])) + '.gz')
            first.write_bytes(b'RETAINED_BAD_INPUT_NOT_OVERWRITTEN')
            with self.assertRaisesRegex(ValueError, 'EXISTING_HISTORICAL_INPUT_CHANGED'):
                proofs.materialize(root)
            self.assertEqual(list(target.iterdir()), [first])
            self.assertEqual(first.read_bytes(), b'RETAINED_BAD_INPUT_NOT_OVERWRITTEN')

    def test_changed_stored_original_gzip_is_not_accepted(self):
        with TemporaryDirectory() as directory:
            here = Path(directory)
            (here / 'CONFIG.json').write_bytes((HERE / 'CONFIG.json').read_bytes())
            (here / 'retained41c').mkdir()
            first = next(iter(cfg['retained41c']))
            (here / 'retained41c' / (first + '.gz')).write_bytes(b'WRONG_GZIP')
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_GZIP_CHANGED'):
                proofs.documents(here)

    def test_cli_unknown_flags_refuse_before_runtime_import_or_materialization(self):
        for filename in ('probe.py', 'check.py'):
            module = load('s03_test_unknown_' + filename.replace('.', '_'), HERE / filename)
            with patch.object(module, 'load', side_effect=AssertionError('NO_RUNTIME_ON_UNKNOWN_FLAG')):
                with self.assertRaises(SystemExit) as refusal:
                    module.main(['--unknown-do-not-ignore'])
                self.assertEqual(refusal.exception.code, 2)

    def test_argv_object_and_contents_return_on_baseexception(self):
        original = sys.argv
        values = list(sys.argv)
        sys.argv = ['caller', '--check', '--literal']
        exact = sys.argv
        try:
            for exception in (ValueError, SystemExit, KeyboardInterrupt):
                with self.assertRaises(exception):
                    with boundary.inherited_imports():
                        self.assertEqual(sys.argv, ['caller'])
                        sys.argv.append('inherited-only')
                        raise exception('LOCAL_CONTROL')
                self.assertIs(sys.argv, exact)
                self.assertEqual(sys.argv, ['caller', '--check', '--literal'])
        finally:
            sys.argv = original
            self.assertEqual(sys.argv, values)

    def test_workflow_is_exact_declared_derivative_with_all_other_steps_preserved(self):
        original = yaml.safe_load((ROOT / '.github/workflows/cp7-current-vendor-receivable-native.yml').read_bytes())
        actual = yaml.safe_load((ROOT / cfg['workflow']).read_bytes())
        self.assertEqual(actual, workflow.derive(original))
        original_steps = original['jobs']['p21']['steps']
        changed_names = {'Admit exact backend3194 parent and declared vendor delta before database',
                         'Run fresh Native7 then actual race3 AuthHTTP1 and complete restoration',
                         'Preserve exact original JSON report bytes in a bounded compressed log receipt'}
        steps = actual['jobs']['p21']['steps']
        self.assertEqual(len(steps), len(original_steps) + 2)
        for step in original_steps:
            if step.get('name') not in changed_names and not step.get('uses', '').startswith('actions/upload-artifact@'):
                self.assertIn(step, steps)
        self.assertEqual(actual['jobs']['p21']['env'], original['jobs']['p21']['env'])
        self.assertEqual(actual['on']['push']['branches'], [cfg['root_execution_branch']])

    def test_workflow_admission_precedes_database_and_cleanup_is_unconditional(self):
        value = yaml.safe_load((ROOT / cfg['workflow']).read_bytes())
        job = value['jobs']['p21']
        steps = job['steps']
        admit = next(i for i, s in enumerate(steps) if s.get('name', '').startswith('Admit exact vendor41c'))
        database = next(i for i, s in enumerate(steps) if s.get('name') == 'Start disposable database')
        self.assertLess(admit, database)
        for name in ('Remove disposable database', 'Preserve exact original JSON report bytes in a bounded compressed log receipt',
                     'Require exact Native11 used guard outer restore and five package gates'):
            self.assertEqual(next(s for s in steps if s.get('name') == name)['if'], 'always()')
        self.assertEqual(job['if'], "github.ref == 'refs/heads/" + cfg['root_execution_branch'] + "'")
        checker = load('s03_test_original_step_keys', ROOT / 'scripts/current-vendor-receivable-qualification/workflow_source.py')
        checker.checked((ROOT / cfg['workflow']).read_text())

    def test_positive_sequence_prefix_is_recorded_without_row_or_keyset_exclusion(self):
        check = function('sequence_prefix')
        old = {'erp.any_table': [2, 'exact_rows'], 'sequence:erp.any_seq': ['1', False]}
        new = dict(old, **{'sequence:erp.any_seq': ['3', True]})
        self.assertEqual(set(check(old, new)), {'sequence:erp.any_seq'})
        with self.assertRaisesRegex(ValueError, 'PERSISTED_ROWS'):
            check(old, dict(new, **{'erp.any_table': [3, 'changed_rows']}))
        with self.assertRaisesRegex(ValueError, 'KEYSET_CHANGED'):
            check(old, {**new, 'sequence:rogue': ['1', True]})

    def test_actual_factory_wrapper_verifies_under_physical_context_and_returns_original_callbacks(self):
        tree = ast.parse((HERE / 'native_runner.py').read_text())
        exercise = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'exercise')
        node = next(n for n in exercise.body if isinstance(n, ast.FunctionDef) and n.name == 'cases')
        events = []
        ids = tuple(cfg['Native_case_ids'])
        callbacks = [(key, lambda: None) for key in ids]
        @contextmanager
        def product_catalog(cursor):
            events.append('EXACT_CONTEXT_ENTER')
            try:yield
            finally:events.append('EXACT_CONTEXT_EXIT')
        state, report = object(), object()
        def declared(cursor, today, **kwargs):
            self.assertEqual(events, ['EXACT_CONTEXT_ENTER'])
            self.assertEqual(kwargs, dict(state=state, evidence=report))
            events.append('UNCHANGED_FACTORY')
            return callbacks
        values = dict(control=SimpleNamespace(product_catalog=product_catalog),
                      business=SimpleNamespace(cases=declared, IDS=ids), state=state, report=report)
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<LOCAL_ACTUAL_FACTORY_WRAPPER>', 'exec'), values)
        self.assertIs(values['cases'](object(), object()), callbacks)
        self.assertEqual(events, ['EXACT_CONTEXT_ENTER', 'UNCHANGED_FACTORY', 'EXACT_CONTEXT_EXIT'])

    def test_disposable_host_port_and_database_are_exact(self):
        check = function('require_local')
        cursor = SimpleNamespace(execute=lambda *_: SimpleNamespace(fetchone=lambda: ('cp6_rollback',)))
        check(SimpleNamespace(info=SimpleNamespace(host='127.0.0.1', port=54322)), cursor)
        for host, port in (('remote.example', 54322), ('127.0.0.1', 5432)):
            with self.assertRaisesRegex(ValueError, 'LOCAL_DISPOSABLE'):
                check(SimpleNamespace(info=SimpleNamespace(host=host, port=port)), cursor)
        bad = SimpleNamespace(execute=lambda *_: SimpleNamespace(fetchone=lambda: ('postgres',)))
        with self.assertRaisesRegex(ValueError, 'DISPOSABLE_DATABASE'):
            check(SimpleNamespace(info=SimpleNamespace(host='localhost', port=54322)), bad)

    def test_result_gate_requires_every_native_id_outer_restore_and_exact_boolean_package(self):
        ids = cfg['Native_case_ids']
        native = dict(status='PASS', counts={'PASS': 11}, planned_case_ids=ids,
                      cases={key: dict(status='PASS') for key in ids}, complete_boundary_restored=True)
        # Explicit synthetic gate input, never a claimed Native observation.
        report = dict(status='PASS', label=gate.LABEL, actual_Native_cases=11, actual_two_session_races=0,
            actual_Auth_HTTP_cases=0, actual_browser_cases=0, committed={
                'S03_ATTENDANCE_NATIVE11_AND_USED_INVERSE': dict(status='PASS', used_guard_refused_before_DDL=True, native=native)})
        for field in ('cp6_restored', 'baseline_full22_all_rows_all_sequences_equal', 'baseline_advisors_equal',
                      'advisor_gate', 'used_guard_refused_before_DDL', 'required_case_ids_pass'):
            report[field] = True
        package = dict(status='ALL_STAGES_INSTALLED', gate={key: True for key in
            ('installed', 'primary_unchanged', 'backup_restore_drill', 'security_advisors', 'writer_runtime')})
        self.assertEqual(gate.checked(report, package, ids)['status'], 'PASS')
        for field, value in (('actual_Native_cases', 10), ('actual_Auth_HTTP_cases', False),
                             ('cp6_restored', False), ('baseline_full22_all_rows_all_sequences_equal', 1)):
            bad = deepcopy(report);bad[field] = value
            with self.assertRaises(ValueError):gate.checked(bad, package, ids)
        bad = deepcopy(report);del bad['committed']['S03_ATTENDANCE_NATIVE11_AND_USED_INVERSE']['native']['cases'][ids[-1]]
        with self.assertRaisesRegex(ValueError, 'ALL_ORIGINAL_IDS'):gate.checked(bad, package, ids)
        bad = deepcopy(package);bad['gate']['writer_runtime'] = 1
        with self.assertRaisesRegex(ValueError, 'FIVE_PACKAGE'):gate.checked(report, bad, ids)

    def test_no_writer_or_oracle_seed_and_no_reseal_in_runtime_workflow(self):
        source = (HERE / 'native_runner.py').read_text()
        for token in ('insert into erp.', 'update erp.', 'delete from erp.', 'setval(', 'session_replication_role'):
            self.assertNotIn(token, source.lower())
        for token in ('business.pair(cursor, today)', 'business.allocate(cursor, fixture, output)',
                      'business.original_accrual', 'business.f.assert_pool', 'connection.commit()',
                      'product.rollback_delta_preuse(cursor, state)', 'control.product_catalog(cursor)'):
            self.assertIn(token, source)
        workflow_text = (ROOT / cfg['workflow']).read_text()
        self.assertNotIn('/bind.py', workflow_text)
        self.assertIn('source_derived_local_ABI_used=False', source)


if __name__ == '__main__':
    unittest.main()
