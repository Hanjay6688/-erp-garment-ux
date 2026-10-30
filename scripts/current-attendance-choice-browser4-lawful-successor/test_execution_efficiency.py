"""One full admission per fixture and per-call source caches; no DB execution."""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import gzip
import importlib.util
import io
import json
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class ExecutionEfficiency(unittest.TestCase):
    def test_non_admit_operation_enters_one_full_runtime_gate_before_operation(self):
        for original, expected in [(True, 2), (False, 1)]:
            fixture = load('fixture_execution_gate_' + str(original),
                HERE / 'retained-89ab/fixture.py' if original else HERE / 'fixture.py')
            events = []
            def admitted():
                events.append('FULL_ADMISSION')
                return {'status': 'EXACT_ACTUAL_BACKEND14_AND_ALL5_ORIGINALS_ADMITTED'}
            @contextmanager
            def runtime():
                admitted(); events.append('ERP_IMPORT'); yield {'admitted': True}
            class Guard:
                pass
            guard = Guard(); guard.admitted = admitted
            def operation(r, name, payload):
                self.assertTrue(r['admitted']); events.append('OPERATION'); return name
            with patch.object(fixture, 'load', return_value=guard), patch.object(fixture, 'runtime', runtime), \
                 patch.object(fixture, 'operation_on_copy', operation), \
                 patch.object(fixture.sys, 'argv', ['fixture.py', 'observe']), \
                 patch.object(fixture.sys, 'stdin', io.StringIO('{}')), \
                 patch.dict(fixture.os.environ, {'AUDITOR_BROWSER_DB_URL': 'postgresql://127.0.0.1:54322/cp6_auditor_browser'}):
                self.assertEqual(fixture.main(), 'observe')
            self.assertEqual(events, ['FULL_ADMISSION'] * expected + ['ERP_IMPORT', 'OPERATION'])

    def test_source_refusal_never_reaches_database_operation(self):
        fixture = load('fixture_execution_refusal', HERE / 'fixture.py')
        @contextmanager
        def refused():
            raise ValueError('SOURCE_CHANGED')
            yield
        with patch.object(fixture, 'runtime', refused), patch.object(fixture, 'operation_on_copy') as op, \
             patch.object(fixture.sys, 'argv', ['fixture.py', 'observe']), \
             patch.object(fixture.sys, 'stdin', io.StringIO('{}')), \
             patch.dict(fixture.os.environ, {'AUDITOR_BROWSER_DB_URL': 'postgresql://127.0.0.1:54322/cp6_auditor_browser'}):
            with self.assertRaisesRegex(ValueError, 'SOURCE_CHANGED'):
                fixture.main()
        op.assert_not_called()

    def test_inventory_cache_is_per_invocation_and_tracks_new_changed_and_removed_imports(self):
        old = load('old_source_inventory_for_cache', HERE / 'retained-89ab/source_inventory.py')
        new = load('new_source_inventory_for_cache', HERE / 'source_inventory.py')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); scripts = root / 'scripts'; scripts.mkdir()
            (scripts / 'seed.py').write_text('import added\nimport added\n')
            for content, expected in [(None, {'scripts/seed.py'}),
                    ('import child\n', {'scripts/seed.py', 'scripts/added.py', 'scripts/child.py'}),
                    ('', {'scripts/seed.py', 'scripts/added.py'})]:
                if content is not None:
                    (scripts / 'added.py').write_text(content); (scripts / 'child.py').write_text('')
                first = old.inventory(root, {'scripts/seed.py'}, scripts)
                current = new.inventory(root, {'scripts/seed.py'}, scripts)
                self.assertEqual(first, current); self.assertEqual(current[0], expected)
            (scripts / 'added.py').unlink()
            self.assertEqual(new.inventory(root, {'scripts/seed.py'}, scripts)[0], {'scripts/seed.py'})

    def test_failure_producer_pool_history_is_required_without_qualifying_failed_evidence(self):
        output = load('output_exact_failure_producer', HERE / 'output_admission.py')
        name = 'cp6-proof/t3/S03_B4_MOBILE390_' + 'a' * 32 + '_FIRST_FAILURE.json'
        value = dict(error='ORIGINAL_FAILURE', progress={}, calls=[], observed=[], fixture=None, pool_history={})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / name; path.parent.mkdir(parents=True)
            path.write_text(json.dumps(value)); self.assertTrue(output.evidence(root, HERE, name))
            for bad in [dict(value, pool_history=[]), {k:v for k,v in value.items() if k != 'pool_history'}, dict(value, extra=True)]:
                path.write_text(json.dumps(bad))
                with self.assertRaisesRegex(ValueError, 'FIRST_FAILURE_SHAPE'):
                    output.evidence(root, HERE, name)

    def test_actual_host_field_accepts_only_loopback_and_keeps_failed_status(self):
        output = load('output_exact_loopback_producer', HERE / 'output_admission.py')
        name = 'cp6-proof/t3/S03_BROWSER4_HOST_ORIGINAL_cp6-auditor-browser-local.json.gz'
        value = dict(status='INCOMPLETE', label='AUDITOR_SCENARIO', mode='BROWSER', ui_mode='DISPOSABLE',
            phase='S03_CHOICE_MOUNTED4', planned=[], cases={}, console_errors=[], real_auth=True,
            product_responses_mocked=False, production_go=False, release_evidence=False,
            auth_cleanup_failures=[], enteng_requests_answered_by_loopback=0, enteng_route_errors=[],
            blocked_requests=0, loopback_api_origin='http://127.0.0.1:45983')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / name; path.parent.mkdir(parents=True)
            path.write_bytes(gzip.compress(json.dumps(value).encode())); self.assertTrue(output.evidence(root, HERE, name))
            self.assertEqual(value['status'], 'INCOMPLETE')
            for bad in ['https://external.invalid', 'http://127.0.0.1:65536', 'http://127.0.0.1:45983/path', 'http://127.0.0.1:0']:
                path.write_bytes(gzip.compress(json.dumps(dict(value, loopback_api_origin=bad)).encode()))
                with self.assertRaisesRegex(ValueError, 'HOST_LOOPBACK_ORIGIN'):
                    output.evidence(root, HERE, name)


if __name__ == '__main__':
    unittest.main()
