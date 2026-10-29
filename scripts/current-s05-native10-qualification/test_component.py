"""Synthetic orchestration controls. No database/product runtime is imported."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
import unittest

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


component = load('s05_test_component_control', HERE/'component.py')


class ComponentControls(unittest.TestCase):
    def complete(self):
        ids = [str(i) for i in range(10)]
        rows = {name: dict(status='PASS', full_boundary_restored=True, public_schema_unchanged=True,
                          all_reader_intervals_data_sequences_catalog_and_parent_equal=True,
                          actual_raw_reads=[{'SYNTHETIC_ORCHESTRATION_ONLY': True}]) for name in ids}
        return ids, dict(status='PASS', counts={'PASS': 10}, planned_case_ids=ids, complete_boundary_restored=True, cases=rows)

    def test_exact_ten_and_actual_boundary_proof_are_required(self):
        ids, value = self.complete(); component.exact_group(value, ids)
        for mutate in (
            lambda d: d.update(counts={'PASS': 9, 'INCOMPLETE': 1}),
            lambda d: d['cases'].pop('9'),
            lambda d: d.update(planned_case_ids=ids[:-1]+['0']),
            lambda d: d.update(complete_boundary_restored=False),
            lambda d: d['cases']['0'].update(public_schema_unchanged=False),
            lambda d: d['cases']['0'].update(actual_raw_reads=[]),
            lambda d: d['cases']['0'].update(all_reader_intervals_data_sequences_catalog_and_parent_equal=False),
        ):
            bad = deepcopy(value); mutate(bad)
            with self.assertRaises(ValueError):
                component.exact_group(bad, ids)

    def test_acl_removed_before_unchanged_stage_and_restored_after_inverse(self):
        events, state = [], {'usage': True}
        @contextmanager
        def catalog(_cursor):
            self.assertTrue(state['usage']); events.append('actual ACL checked'); state['usage'] = False
            try:
                yield
            finally:
                events.append('harness ACL restored'); state['usage'] = True
        @contextmanager
        def original(_cursor, parent):
            self.assertFalse(state['usage']); self.assertEqual(parent, 'EXACT_PARENT')
            events.append('unchanged install')
            try:
                yield {'installer_capability': {'status': 'S05_EXISTING_OUTER_SUPERUSER_ORIGINAL_DDL',
                       'outer_current_superuser': True, 'temporary_role_memberships': 0, 'persistent_authority_change': False}}
            finally:
                self.assertFalse(state['usage']); events.append('unchanged uninstall and parent verification')
        stage = SimpleNamespace(reader_only=original, verify=lambda c, s: {'SYNTHETIC_ORCHESTRATION_ONLY': True})
        observations = []
        with component.reader_binding(stage, SimpleNamespace(product_catalog=catalog), observations, {'id': 'LOCAL_CONTROL'}):
            with stage.reader_only(None, 'EXACT_PARENT'):
                self.assertFalse(state['usage']); events.append('read')
        self.assertIs(stage.reader_only, original)
        self.assertEqual(events, ['actual ACL checked', 'unchanged install', 'read', 'unchanged uninstall and parent verification', 'harness ACL restored'])
        self.assertEqual(observations[0]['status'], 'PASS')

    def test_unknown_acl_never_reaches_reader_or_weakens_source(self):
        @contextmanager
        def refused(_):
            raise ValueError('NATIVE_TEST_SCHEMA_DELTA_NOT_EXACT_DECLARED_USAGE')
            yield
        called = []
        @contextmanager
        def original(*_):
            called.append('unexpected'); yield
        stage = SimpleNamespace(reader_only=original)
        with component.reader_binding(stage, SimpleNamespace(product_catalog=refused), [], {'id': 'LOCAL_CONTROL'}):
            with self.assertRaisesRegex(ValueError, 'DELTA_NOT_EXACT'):
                with stage.reader_only(None, None):
                    pass
        self.assertEqual(called, [])
        self.assertIs(stage.reader_only, original)

    def test_missing_confirmation_stops_before_runtime_import(self):
        probe = load('s05_inert_entrypoint', HERE/'probe.py')
        with patch.dict(probe.os.environ, {}, clear=True), patch.object(probe, 'runtime', side_effect=AssertionError('RUNTIME_IMPORTED')) as runtime:
            with self.assertRaisesRegex(ValueError, 'EXPLICIT_LOCAL_QUALIFICATION'):
                probe.execute()
            runtime.assert_not_called()

    def test_database_target_is_closed_to_hosted_other_ports_and_other_names(self):
        class Cursor:
            def __init__(self, database): self.database = database
            def execute(self, _): return self
            def fetchone(self): return (self.database,)
        for host, port, db in (('example.supabase.co', 54322, 'cp6_rollback'), ('127.0.0.1', 5432, 'cp6_rollback'), ('127.0.0.1', 54322, 'postgres')):
            with self.assertRaises(ValueError):
                component.require_local(SimpleNamespace(info=SimpleNamespace(host=host, port=port)), Cursor(db))
        component.require_local(SimpleNamespace(info=SimpleNamespace(host='127.0.0.1', port=54322)), Cursor('cp6_rollback'))


if __name__ == '__main__':
    unittest.main()
