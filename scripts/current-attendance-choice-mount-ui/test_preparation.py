"""Local source/orchestration doubles only. No SQL, Native, Auth or browser execution."""
from contextlib import nullcontext
from copy import deepcopy
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import unittest

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = spec_from_file_location(name, HERE / filename)
    value = module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


guard = load('mounted_s03_source_tests', 'source_check.py')
adapter = load('mounted_s03_adapter_tests', 'browser_adapter.py')
derive = load('mounted_s03_derivation_tests', 'derive.py')
probe = load('mounted_s03_probe_tests', 'probe.py')


class Preparation(unittest.TestCase):
    def test_actual_source_is_closed_before_runtime(self):
        result = guard.check()
        self.assertEqual(result['status'], 'SOURCE_PASS_EXECUTION_CLOSED')
        self.assertEqual((result['fresh_Native_cases'], result['fresh_Auth_cases'], result['fresh_browser_cases']), (0, 0, 0))

    def test_execution_closes_before_touching_even_a_cursor(self):
        class Untouchable:
            def __getattr__(self, name):
                raise AssertionError('UNAUTHORIZED_RUNTIME_ACCESS:' + name)
        with self.assertRaisesRegex(ValueError, 'BACKEND11_READER3_FULL_RESTORE_ALL5_AND_CASE_SOURCE_REQUIRED'):
            adapter.exercise(Untouchable(), Untouchable(), None, None, {}, {})

    def test_full_engine_is_closed_before_runtime_imports(self):
        with self.assertRaisesRegex(ValueError, 'BACKEND11_READER3_FULL_RESTORE_ALL5_AND_CASE_SOURCE_REQUIRED'):
            probe.runtime()

    def test_complete_vendor_derivation_is_six_reversible_child_selections(self):
        raw = (HERE.parents[1] / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        code, result = derive.derive(raw)
        self.assertEqual(result['counted_changes'], 6)
        restored = code
        for before, after in reversed(derive.REPLACEMENTS):
            self.assertEqual(restored.count(after), 1)
            restored = restored.replace(after, before, 1)
        self.assertEqual(restored.encode(), raw)
        compile(code, 'declared-vendor-private-derivation-no-exec', 'exec')

    def test_missing_or_duplicate_derivation_anchor_is_refused(self):
        raw = (HERE.parents[1] / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        before = derive.REPLACEMENTS[0][0].encode()
        for changed in (raw.replace(before, b'', 1), raw + b'\n' + before):
            with self.assertRaisesRegex(ValueError, 'EXACT_VENDOR_ANCHOR_REQUIRED'):
                derive.derive(changed)

    def synthetic(self, folder):
        # Synthetic files exercise source validation, never backend acceptance.
        root = Path(folder)
        raw = b'explicit local source-validation double'
        (root / 'source.txt').write_bytes(raw)
        gate = json.loads((HERE / 'EXECUTION_GATE.json').read_text())
        (root / 'gate.json').write_text(json.dumps(gate))
        return root, dict(contract_version='cp7.s03-mounted-ui-preparation.v1', gate='gate.json',
            sources=[dict(path='source.txt', bytes=len(raw), sha256=sha256(raw).hexdigest())])

    def test_source_mutation_is_refused(self):
        with TemporaryDirectory() as folder:
            root, declaration = self.synthetic(folder)
            (root / 'source.txt').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'SOURCE_CHANGED'):
                guard.check(root, declaration)

    def test_duplicate_or_escaping_source_is_refused(self):
        with TemporaryDirectory() as folder:
            root, declaration = self.synthetic(folder)
            declaration['sources'] *= 2
            with self.assertRaisesRegex(ValueError, 'DUPLICATE_SOURCE'):
                guard.check(root, declaration)
            declaration['sources'] = [dict(path='../outside', bytes=0, sha256='0' * 64)]
            with self.assertRaisesRegex(ValueError, 'UNSAFE_SOURCE_PATH'):
                guard.check(root, declaration)

    def test_json_cannot_self_approve_missing_actual_qualification(self):
        with TemporaryDirectory() as folder:
            root, declaration = self.synthetic(folder)
            gate = json.loads((root / 'gate.json').read_text())
            gate.update(status='PASS', accepted_backend_Native11='invented')
            (root / 'gate.json').write_text(json.dumps(gate))
            with self.assertRaisesRegex(ValueError, 'REQUIRES_REVIEWED_ACTUAL_PROOF_BINDER'):
                guard.check(root, declaration)

    def bridge(self, *, fail=False, incomplete=False, malformed=False):
        calls = []
        original = lambda name: 'declared-original-copy-double:' + name
        modes = SimpleNamespace(copy_db=original)
        copy = SimpleNamespace(COPY_ADMISSIONS=[], copy_database=lambda name: 'declared-physical-copy-double:' + name)
        state = dict(after={str(i): {'exact': i} for i in range(21 if incomplete else 22)}, predecessor={'unmodified': True})
        before = deepcopy(state)
        product = SimpleNamespace(runtime=lambda: (None, None, None, None, 'declared-catalog-double'),
            verify=lambda cursor, passed: calls.append(('verify', cursor, passed is state)))
        helper = SimpleNamespace(control=SimpleNamespace(product_catalog=lambda cursor: nullcontext()))

        def run_browser(script, verify, tag):
            calls.append(('browser', script, tag, modes.copy_db is copy.copy_database))
            verify('declared-cursor-double')
            if fail:
                raise RuntimeError('declared browser orchestration failure')
            copy.COPY_ADMISSIONS.append(dict(all22_groups_equal_original_install=True))
            ids = adapter.IDS if not malformed else (*adapter.IDS[:-1], 'UNDECLARED')
            return dict(counts={'PASS': 4}, cases={case: {'status': 'PASS'} for case in ids}, database_remaining=0,
                cleanup_failures=[], auth_counts={'restored': True}, console_errors=0, session_leaks=[])

        modes.run_browser = run_browser
        conn = SimpleNamespace(rollback=lambda: calls.append(('rollback',)), close=lambda: calls.append(('conn-close',)))
        cur = SimpleNamespace(close=lambda: calls.append(('cursor-close',)))
        report = {}
        invoke = lambda: adapter._bridge(conn, cur, report, state, product=product, modes=modes, helper=helper,
            adapter=copy, script=HERE / 'cases.mjs', prerequisite={'used_inverse_guard_before_DDL': True, 'classification': 'EXPLICIT_LOCAL_DOUBLE'})
        return invoke, modes, original, copy, state, before, report, calls

    def test_complete_state_is_passed_without_projection_and_counts_are_separate(self):
        invoke, modes, original, copy, state, before, report, calls = self.bridge()
        invoke()
        self.assertEqual(state, before)
        self.assertIs(copy.STATE['installed_catalog'], state['after'])
        self.assertEqual(report['actual_Native_cases'], 0)
        self.assertEqual(report['actual_Auth_HTTP_cases'], 0)
        self.assertEqual(report['actual_two_session_races'], 0)
        self.assertEqual(report['used_guard_evidence_classification'], 'RETAINED_ACTUAL_BACKEND_NOT_RERUN')
        self.assertIn(('verify', 'declared-cursor-double', True), calls)
        self.assertIs(modes.copy_db, original)

    def test_incomplete_catalog_is_refused_before_connection_close(self):
        invoke, modes, original, copy, state, before, report, calls = self.bridge(incomplete=True)
        with self.assertRaisesRegex(ValueError, 'COMPLETE22_REQUIRED'):
            invoke()
        self.assertEqual(calls, [])
        self.assertIs(modes.copy_db, original)

    def test_copy_hook_is_restored_after_failure_without_success(self):
        invoke, modes, original, copy, state, before, report, calls = self.bridge(fail=True)
        with self.assertRaisesRegex(RuntimeError, 'declared browser orchestration failure'):
            invoke()
        self.assertIs(modes.copy_db, original)
        self.assertNotEqual(report.get('status'), 'PASS')
        self.assertEqual(state, before)

    def test_count_alone_does_not_accept_unknown_case_ids(self):
        invoke, modes, original, copy, state, before, report, calls = self.bridge(malformed=True)
        with self.assertRaises(AssertionError):
            invoke()
        self.assertIs(modes.copy_db, original)
        self.assertNotEqual(report.get('status'), 'PASS')


if __name__ == '__main__':
    unittest.main(verbosity=2)
