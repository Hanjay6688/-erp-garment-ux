"""Directed local dependency/ABI controls. No database or Native acceptance."""
from copy import deepcopy
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import patch
import importlib.util
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = (ROOT/'scripts/cp7_accessory_standard_report/cases.py').read_bytes()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


recipe = load('s05_lawful_local_recipe_controls', HERE/'recipe.py')
factory = load('s05_lawful_local_factory_controls', HERE/'factory.py')
component = load('s05_lawful_local_component_controls', HERE/'component_derivation.py')


class Cursor:
    """Explicit cursor double; these rows are never a product RPC result."""
    def __init__(self, *, empty=False, method='BOM_STANDARD'):
        self.queries = []; self.edit_calls = 0; self.last = None; self.counts = (0, 0, 0, 0)
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.row = ('bom', 'product', self.start, None, True, None)
        self.root = ('product',); self.extra_row = False
        self.abi = (recipe.EDITOR_BODY_SHA256,)
        self.current = datetime(2026, 10, 30, 2, 3, 4, tzinfo=timezone.utc)
        self.existing = None; self.members = []
        self.item_rows = [] if empty else [('category', Decimal('.5'), method, Decimal('2') if method == 'BOM_STANDARD' else None, 'PCS', Decimal('2'), 'PCS')]

    def execute(self, sql, args=None):
        self.queries.append((sql, args))
        if sql.startswith('select encode(sha256'):
            self.result = self.abi
        elif sql.startswith('select v.id::text'):
            self.result = [self.row, self.row] if self.extra_row else [self.row]
        elif sql.startswith('select identity_root_id'):
            self.result = self.root
        elif sql.startswith('select (select count(*)'):
            self.result = self.counts
        elif sql.startswith('select erp.save_accessory_bom_edit'):
            self.edit_calls += 1; self.result = ('bom',)
        elif sql.startswith('select category_id::text'):
            self.result = self.item_rows
        elif sql.startswith('select erp.accessory_bom_last_committed_at'):
            self.result = (self.last,)
        elif sql == 'select statement_timestamp()':
            self.result = (self.current,)
        elif sql.startswith('select s.id::text'):
            self.result = self.existing
        elif sql.startswith('select m.product_root::text'):
            self.result = self.members
        else:
            raise AssertionError('UNDECLARED_LOCAL_CURSOR_SQL:'+sql)
        return self

    def fetchone(self):
        return self.result

    def fetchall(self):
        return self.result

    def __iter__(self):
        return iter(self.result)


def context():
    observations = []; commands = []
    def group(cur, roots, at, **kwargs):
        commands.append(dict(roots=roots, at=at, kwargs=deepcopy(kwargs)))
        return dict(roots=roots, at=str(at), **kwargs)
    def save(cur, groups, at):
        commands[-1]['save_at'] = at
        return dict(groups=groups, local_double_only=True)
    b = SimpleNamespace(api=SimpleNamespace(admin=lambda cur: None))
    prod = SimpleNamespace(owner=lambda cur: None,
                           at=lambda day, hour: datetime.combine(day, datetime.min.time(), timezone(timedelta(hours=7)))+timedelta(hours=hour))
    business = SimpleNamespace(b=b, prod=prod, master=SimpleNamespace(group=group, save=save), deepcopy=deepcopy)
    value = recipe.LawfulRecipe(business, RAW, observations)
    f = dict(product='product', day=date(2026, 10, 10), accessory=dict(category='category', pcs='PCS'))
    return value, f, observations, commands


class RecipeControls(unittest.TestCase):
    def test_initial_native_editor_keeps_historical_window_and_never_calls_BF(self):
        value, f, rows, commands = context(); cur = Cursor()
        result = value(cur, f)
        self.assertEqual(cur.edit_calls, 1); self.assertEqual(commands, [])
        query, args = next(x for x in cur.queries if x[0].startswith('select erp.save_accessory_bom_edit'))
        self.assertIn('::jsonb,null,', query)
        self.assertEqual(result['bom_version_id'], 'bom')
        self.assertEqual(rows[0]['effective_from'], str(cur.start))
        self.assertFalse(rows[0]['historical_BF_creation_claim'])
        self.assertFalse(any('statement_timestamp' in q for q, _ in cur.queries))
        self.assertEqual(f['day'], date(2026, 10, 10))

    def test_moving_average_and_empty_recipe_keep_original_shapes(self):
        for empty, method in ((False, 'CATEGORY_MOVING_AVG'), (True, 'BOM_STANDARD')):
            value, f, rows, commands = context(); cur = Cursor(empty=empty, method=method)
            value(cur, f, empty=empty, method=method)
            self.assertEqual(commands, []); self.assertEqual(cur.edit_calls, 1)
            if empty: self.assertEqual(rows[0]['items'], [])
            else: self.assertIsNone(rows[0]['items'][0]['hpp_standard_rate'])

    def test_used_legacy_master_refuses_before_edit(self):
        value, f, _, _ = context(); cur = Cursor()
        cur.row = (*cur.row[:-1], cur.current-timedelta(days=1))
        with self.assertRaisesRegex(ValueError, 'ALREADY_USED'):
            value(cur, f)
        self.assertEqual(cur.edit_calls, 0)

    def test_duplicate_foreign_future_and_shared_master_inputs_refuse(self):
        for change, expected in (
            (lambda c: setattr(c, 'extra_row', True), 'ONE_RETAINED_EMPTY'),
            (lambda c: setattr(c, 'root', ('foreign',)), 'EXACT_OWNED'),
            (lambda c: setattr(c, 'row', ('bom', 'product', c.current, None, True, None)), 'ALREADY_COVER'),
            (lambda c: setattr(c, 'counts', (0, 0, 0, 1)), 'EMPTY_UNCOMMITTED'),
            (lambda c: setattr(c, 'counts', (1, 0, 0, 0)), 'EMPTY_UNCOMMITTED'),
            (lambda c: setattr(c, 'counts', (0, 1, 0, 0)), 'EMPTY_UNCOMMITTED')):
            with self.subTest(expected=expected):
                value, f, _, _ = context(); cur = Cursor(); change(cur)
                with self.assertRaisesRegex(ValueError, expected): value(cur, f)
                self.assertEqual(cur.edit_calls, 0)

    def test_installed_editor_body_mismatch_refuses(self):
        value, f, _, _ = context(); cur = Cursor(); cur.abi = ('0'*64,)
        with self.assertRaisesRegex(ValueError, 'EXACT_NATIVE_LEGACY_EDITOR_BODY'):
            value(cur, f)
        self.assertEqual(cur.edit_calls, 0)

    def test_later_successor_actual_statement_time_retains_complete_membership_and_settings(self):
        value, f, rows, commands = context(); cur = Cursor(); value(cur, f)
        cur.last = datetime(2026, 10, 10, 7, tzinfo=timezone.utc)
        settings = dict(price='123', bom=[], work_rates=[{'kept': 1}], laundry_rates=[{'kept': 2}])
        cur.existing = ('sku-group', 'SKU', 4, settings)
        cur.members = [('product',), ('sibling-owned',)]
        value(cur, f, qty='3', rate='9')
        self.assertEqual(cur.edit_calls, 1)
        self.assertEqual(commands[0]['roots'], ['product', 'sibling-owned'])
        self.assertEqual(commands[0]['at'], cur.current)
        self.assertEqual(commands[0]['save_at'], cur.current)
        self.assertGreater(commands[0]['at'], cur.last)
        self.assertEqual(commands[0]['kwargs']['settings']['work_rates'], settings['work_rates'])
        self.assertEqual(commands[0]['kwargs']['settings']['laundry_rates'], settings['laundry_rates'])
        self.assertEqual(commands[0]['kwargs']['settings']['bom'][0]['qty_per_good_fg_base'], '3')
        self.assertEqual(rows[1]['kind'], 'ACTUAL_NATIVE_BF_SUCCESSOR_AFTER_GOOD')

    def test_later_successor_without_good_commitment_refuses(self):
        value, f, rows, commands = context(); cur = Cursor(); value(cur, f)
        with self.assertRaisesRegex(ValueError, 'ACTUAL_PRIOR_GOOD'):
            value(cur, f)
        self.assertEqual(cur.edit_calls, 1); self.assertEqual(commands, [])

    def test_two_time_anchors_exact_and_reversible(self):
        code, proof = recipe.successor_source(RAW)
        self.assertEqual(proof['counted_time_substitutions'], 2)
        self.assertIn('master.save(cur, [group], at)', code)
        with self.assertRaisesRegex(ValueError, 'EXACT_TWO_TIME_ANCHORS'):
            recipe.successor_source(RAW.replace(recipe.OLD.encode(), b'    at = None\n'))

    def test_private_cases_dependency_only_original_module_unchanged(self):
        b = SimpleNamespace(chain=SimpleNamespace(production=SimpleNamespace()))
        names = ('cp7_wip_source_cases', 'cp7_f03_e24_issue_cases', 'cp6_bf_probe', 'cp7_qc_source_cases', 'cp7_snapshot_cases')
        modules = {n: ModuleType(n) for n in names}; modules[names[0]].b = b
        package = ModuleType('cp7_accessory_standard_report'); stage = ModuleType('cp7_accessory_standard_report.stage')
        package.stage = stage; package.__path__ = []
        modules.update(cp7_accessory_standard_report=package, **{'cp7_accessory_standard_report.stage': stage})
        retained = ModuleType('cp7_accessory_standard_report.cases')
        retained.__file__ = str(ROOT/factory.CASES); retained.__package__ = 'cp7_accessory_standard_report'
        with patch.dict(sys.modules, modules):
            exec(compile(RAW, retained.__file__, 'exec'), retained.__dict__)
            old_recipe = retained.recipe
            private = factory.business(retained)
            self.assertIs(retained.recipe, old_recipe)
            self.assertIsNot(private.recipe, old_recipe)
            self.assertEqual(private.IDS, retained.IDS)
            self.assertEqual(len(private.cases(None, date(2026, 10, 30), {})), 10)
            for name, function in retained.__dict__.items():
                if callable(function) and getattr(function, '__module__', None) == retained.__name__ and name != 'recipe':
                    self.assertEqual(getattr(private, name).__code__.co_code, function.__code__.co_code)
            self.assertEqual(private.fixture_derivation['cases_source_substitutions'], 0)

    def test_original_component_one_import_binding_reversible(self):
        raw = (ROOT/'scripts/current-s05-native10-qualification/component.py').read_bytes()
        made, proof = component.derive(raw)
        self.assertEqual(made.replace(component.NEW.encode(), component.OLD.encode(), 1), raw)
        self.assertEqual(proof['counted_business_import_bindings'], 1)
        with self.assertRaisesRegex(ValueError, 'EXACT_UNCHANGED_COMPONENT'):
            component.derive(raw+b'\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
