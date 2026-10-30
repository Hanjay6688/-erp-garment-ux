"""Offline fail-closed integration controls. No ERP imports or new case credit."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast
import importlib.util
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(file):
    spec = importlib.util.spec_from_file_location('s05_outer_control_'+file, HERE/(file+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


engine, component, prerequisite, probe = map(load, ('engine', 'component', 'prerequisite', 'probe'))


class OuterControls(unittest.TestCase):
    def test_full_retained_engine_reverses_and_all_other_functions_are_exact(self):
        raw = (ROOT/'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        text, proof = engine.derive(raw)
        compile(text, 'complete_retained_engine_not_executed', 'exec')
        reverse = text
        for before, after in reversed(engine.CHANGES): reverse = reverse.replace(after, before, 1)
        self.assertEqual(reverse.encode(), raw); self.assertEqual(proof['counted_changes'], 2)
        old = {n.name: ast.dump(n) for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef)}
        new = {n.name: ast.dump(n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
        self.assertEqual(old.keys(), new.keys())
        for name in old.keys()-{'run_inner'}: self.assertEqual(old[name], new[name])
        for before, after in engine.CHANGES:
            with self.assertRaises(ValueError): engine.derive(raw.replace(before.encode(), b'CHANGED', 1))
            with self.assertRaises(ValueError): engine.derive(raw+b'\n'+before.encode())

    def test_pending_actual_parent_blocks_before_any_runtime_import(self):
        actual_load = probe.load; seen = []
        def guarded(name, path):
            seen.append(path.name)
            self.assertEqual(path, HERE/'prerequisite.py', 'RUNTIME_IMPORT_REACHED_BEFORE_ACTUAL_PARENT_ADMISSION')
            return actual_load(name, path)
        with patch.object(probe, 'source', lambda: {}), patch.object(probe, 'load', guarded):
            with self.assertRaisesRegex(ValueError, 'WAIT_FOR_ACTUAL_ROOT_INTAKE'): probe.runtime()
        self.assertEqual(seen, ['prerequisite.py'])
        for raw in ('{"x":1,"x":2}', '{"value":NaN}', '{"value":1e999}'):
            with self.assertRaises(ValueError): prerequisite.strict(raw)

    def test_native_failure_prevents_browser_and_cannot_become_pass(self):
        seen = []
        def native(*args): seen.append('native'); raise RuntimeError('actual first Native failure')
        def bridge(name, file):
            self.assertEqual(file, 'native.py')
            return SimpleNamespace(component=lambda: (SimpleNamespace(exercise=native), {}))
        report = {}
        with patch.object(component, 'load', bridge), self.assertRaisesRegex(RuntimeError, 'actual first Native failure'):
            component.exercise(None, None, None, None, report, {})
        self.assertEqual(seen, ['native']); self.assertEqual(report['status'], 'INCOMPLETE')
        self.assertNotIn('fresh_real_Auth_browser2', report)

    def test_browser_failure_keeps_native_result_and_whole_component_incomplete(self):
        seen = []
        def native(conn, cur, db, url, report, state):
            seen.append('native'); report.update(status='PASS', actual_Native_cases=10, used_guard_refused_before_DDL=True)
        def browser(url, state, report): seen.append('browser'); raise RuntimeError('actual first browser failure')
        def bridge(name, file):
            return (SimpleNamespace(component=lambda: (SimpleNamespace(exercise=native), {}))
                if file == 'native.py' else SimpleNamespace(exercise=browser))
        report = {}
        with patch.object(component, 'load', bridge), self.assertRaisesRegex(RuntimeError, 'actual first browser failure'):
            component.exercise(None, None, None, None, report, {})
        self.assertEqual(seen, ['native', 'browser']); self.assertEqual(report['status'], 'INCOMPLETE')
        self.assertEqual(report['fresh_Native10']['status'], 'PASS')
        self.assertEqual(report['fresh_real_Auth_browser2']['status'], 'INCOMPLETE')
        self.assertNotIn('business_counts', report)


if __name__ == '__main__': unittest.main()
