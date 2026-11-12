"""Sequence bridge controls for the existing Native fixture and retained cases."""
import ast
from copy import deepcopy
from pathlib import Path
import subprocess
import tempfile
from types import FunctionType, ModuleType, SimpleNamespace
import unittest

import component
import report_io
import setup_sequences as setup

ROOT = Path(__file__).resolve().parents[2]
AFUI = report_io.COMPLETE_ORIGINALS_HEAD
MONEY = 'f1674ae84739f577571d68415beabfca3f3b832b'
OTHER = 'sequence:erp.fg_stock_book_order_seq'


def original(head, path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', head + ':' + path])


class SetupSequenceControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = 'scripts/current-sku-managed-recovery-native27-qualification/sequence_prefix.py'
        cls.prefix = ModuleType('frozen_money_sequence_prefix')
        cls.prefix.__file__ = str(ROOT / path)
        exec(compile(original(MONEY, path), cls.prefix.__file__, 'exec'), cls.prefix.__dict__)
        path = 'scripts/cp7_accessory_nonpayable/case_boundary.py'
        cls.reader_raw = original(AFUI, path)
        cls.reader = ModuleType('frozen_afui_sequence_reader')
        exec(compile(cls.reader_raw, path, 'exec'), cls.reader.__dict__)

        derived, _ = component.derive(original(MONEY, component.ORIGINAL), focused=True)
        exercise = next(node for node in ast.parse(derived).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'exercise')
        with_connection = next(node for node in exercise.body if isinstance(node, ast.With)
                               and isinstance(node.body[0], ast.Expr)
                               and ast.unparse(node.body[0]) == 'require_local(connection, cursor)')
        cls.chain_checks = compile(ast.Module(body=with_connection.body[3:6], type_ignores=[]),
                                   'derived-owning-sequence-chain', 'exec')

    def setUp(self):
        self.cur = object()
        self.catalog = object()
        self.data = {setup.AUDIT_KEY: ['1', False], OTHER: ['1', False]}
        self.data.update({f'sequence:unaffected_{index}': ['1', False] for index in range(13)})
        self.live = deepcopy(self.data)
        self.rows = []
        self.seed_calls = []
        self.before = dict(data=self.data, catalog=dict(
            sequences={setup.AUDIT: self.reader.SEQUENCE_DEFINITION},
            sequence_ownership={setup.AUDIT: ['a', 'erp.audit_logs', 'id']},
            columns={'erp.audit_logs:id': ["nextval('erp.audit_logs_id_seq'::regclass)"]}))
        self.api = SimpleNamespace(seed=self.seed, admin=object())
        self.native = SimpleNamespace(api=self.api)
        product = SimpleNamespace(runtime=lambda: (self.catalog,))
        self.business = SimpleNamespace(n=SimpleNamespace(product=product), IDS=('FIRST', 'SECOND'))
        self.report = {}
        self.observer = SimpleNamespace(OWNED=self.reader.OWNED,
                                        SEQUENCE_DEFINITION=self.reader.SEQUENCE_DEFINITION,
                                        allocations=self.reader.allocations,
                                        capture_generated=self.observe)

    def seed(self, cur):
        self.assertIs(cur, self.cur)
        self.seed_calls.append(cur)
        self.live[setup.AUDIT_KEY] = ['222', True]
        self.rows = list(range(1, 223))

    def observe(self, cur, catalog, baseline):
        self.assertIs(cur, self.cur)
        self.assertIs(catalog, self.catalog)
        self.assertEqual(baseline, dict(full_data_and_sequences=self.data))
        return dict(sequences=deepcopy(self.live), generated_rows={
            setup.AUDIT: [dict(id=value) for value in self.rows]})

    def scope(self):
        return setup.scope(self.native, self.business, self.prefix, self.before, self.report, self.observer)

    def check_chain(self, setup_receipt, first, second, last):
        first_end = dict(first, **{setup.AUDIT_KEY: ['376', True]})
        actual = dict(cases={
            'FIRST': dict(complete_case_sequence_prefix=self.prefix.prefix(first, first_end)),
            'SECOND': dict(complete_case_sequence_prefix=self.prefix.prefix(second, first_end)),
        })
        exec(self.chain_checks, dict(setup=setup_receipt, prefix=self.prefix, business=self.business,
                                    actual=actual, after=dict(data=last)))

    def test_actual_seed_scope_bridges_all_fifteen_and_counts_first_uncalled_value(self):
        with self.scope() as receipt:
            self.assertIs(self.native.api.admin, self.api.admin)
            self.native.api.seed(self.cur)
        self.assertIs(self.native.api, self.api)
        self.assertEqual(self.seed_calls, [self.cur])
        self.assertEqual(receipt['prefix']['before'], self.data)
        self.assertEqual(receipt['prefix']['after'], self.live)
        self.assertEqual(receipt['audit_allocation_count'], 222)
        self.assertEqual(receipt['audit_row_ids'], [str(value) for value in range(1, 223)])
        self.assertEqual(set(receipt['prefix']['changed']), {setup.AUDIT_KEY})
        terminal = dict(self.live, **{setup.AUDIT_KEY: ['376', True]})
        self.check_chain(receipt, self.live, terminal, terminal)

    def test_no_seed_requires_original_start(self):
        with self.scope() as receipt:
            pass
        self.assertEqual(receipt['status'], 'SEED_NOT_INVOKED')
        self.assertEqual(receipt['prefix']['after'], self.data)
        terminal = dict(self.live, **{setup.AUDIT_KEY: ['376', True]})
        self.check_chain(receipt, self.live, terminal, terminal)

    def test_unattributed_before_seed_refuses_even_for_the_audit_sequence(self):
        self.live[setup.AUDIT_KEY] = ['1', True]
        with self.assertRaisesRegex(ValueError, 'UNATTRIBUTED_SEQUENCE_BEFORE_SEED'), self.scope():
            self.native.api.seed(self.cur)
        self.assertEqual(self.seed_calls, [])
        self.assertEqual(self.report['native_fixture_seed_sequence_prefix']['observed_before'], self.live)
        self.assertIs(self.native.api, self.api)

    def test_missing_extra_or_duplicate_audit_rows_refuse(self):
        for label, change in (
                ('missing', lambda rows: rows[1:]), ('extra', lambda rows: rows + [223]),
                ('duplicate', lambda rows: [2] + rows[1:])):
            with self.subTest(label=label):
                def altered(cur):
                    self.seed(cur)
                    self.rows = change(self.rows)
                self.api.seed = altered
                with self.assertRaisesRegex(ValueError, 'EVERY_AUDIT_ALLOCATION_REQUIRES_ITS_ROW'), self.scope():
                    self.native.api.seed(self.cur)
                self.live = deepcopy(self.data)
                self.assertIs(self.native.api, self.api)

    def test_unrelated_sequence_during_seed_refuses(self):
        def altered(cur):
            self.seed(cur)
            self.live[OTHER] = ['1', True]
        self.api.seed = altered
        with self.assertRaisesRegex(ValueError, 'ONLY_AUDIT_SEQUENCE_MAY_ADVANCE'), self.scope():
            self.native.api.seed(self.cur)
        self.assertEqual(self.report['native_fixture_seed_sequence_prefix']['observed_after'][OTHER], ['1', True])

    def test_unattributed_after_seed_between_cases_and_after_last_case_refuse(self):
        with self.scope() as receipt:
            self.native.api.seed(self.cur)
        terminal = dict(self.live, **{setup.AUDIT_KEY: ['376', True]})
        drift = dict(self.live, **{OTHER: ['1', True]})
        with self.assertRaisesRegex(AssertionError, 'UNATTRIBUTED_SEQUENCE_BEFORE_CASE.*FIRST'):
            self.check_chain(receipt, drift, terminal, terminal)
        with self.assertRaisesRegex(AssertionError, 'UNATTRIBUTED_SEQUENCE_BEFORE_CASE.*SECOND'):
            self.check_chain(receipt, self.live, self.live, terminal)
        with self.assertRaisesRegex(AssertionError, 'UNATTRIBUTED_SEQUENCE_AFTER_CASES'):
            self.check_chain(receipt, self.live, terminal, dict(terminal, **{OTHER: ['1', True]}))

    def test_first_seed_error_and_original_api_are_preserved(self):
        def refuses(_):
            raise RuntimeError('first original fixture failure')
        self.api.seed = refuses
        with self.assertRaisesRegex(RuntimeError, 'first original fixture failure'), self.scope():
            self.native.api.seed(self.cur)
        receipt = self.report['native_fixture_seed_sequence_prefix']
        self.assertEqual(receipt['status'], 'INCOMPLETE')
        self.assertIsNone(receipt['prefix'])
        self.assertNotIn('observed_after', receipt)
        self.assertIs(self.native.api, self.api)

    def test_actual_frozen_readers_and_seed_callable_required(self):
        path = 'scripts/cp6_ao_ap_installed.py'
        seed_raw = original(AFUI, path)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            seed = root / path
            boundary = root / 'scripts/cp7_accessory_nonpayable/case_boundary.py'
            boundary.parent.mkdir(parents=True)
            seed.write_bytes(seed_raw)
            boundary.write_bytes(self.reader_raw)
            api = ModuleType('frozen_seed_source_fixture')
            api.__file__ = str(seed)
            api.seed = FunctionType(report_io.function_code(seed_raw, str(seed), 'seed'), api.__dict__)
            output = SimpleNamespace(__file__=str(boundary.with_name('case_output.py')))
            reader, _ = setup.bind(api, output, report_io)
            self.assertEqual(reader.OWNED, self.reader.OWNED)
            boundary.write_bytes(self.reader_raw + b'\n')
            with self.assertRaisesRegex(ValueError, 'EXACT_SOURCE_REQUIRED:case_boundary.py'):
                setup.bind(api, output, report_io)
            api.seed = self.seed
            with self.assertRaisesRegex(ValueError, 'EXACT_SEED_CALLABLE_REQUIRED'):
                setup.bind(api, output, report_io)


if __name__ == '__main__':
    unittest.main()
