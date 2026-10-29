"""Source/current-owner ABI controls; all values here are declared local doubles."""
from copy import deepcopy
from datetime import date
from hashlib import sha256
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import importlib.util
import json
import os
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT/'scripts/current-s05-lawful-master-dates-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


binding = load('s05_AC_local_binding', HERE/'binding.py')
recipe = load('s05_AC_local_recipe', HERE/'recipe.py')
admission = load('s05_AC_local_admission', HERE/'admission.py')
workflow = load('s05_AC_local_workflow', HERE/'workflow_source.py')
historical = load('s05_AC_unchanged_historical_fixture_controls', OLD/'test_fixture.py')


class HistoricalFixtureControls(historical.RecipeControls):
    """The ten original Python fixture controls run unchanged as history."""


class CurrentCursor(historical.Cursor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        definition, _ = binding.premise()
        self.actual = (definition, 'postgres', binding.CURRENT_BODY_SHA)
        self.abi = (binding.CURRENT_BODY_SHA,)

    def execute(self, sql, args=None):
        if sql.startswith('select pg_get_functiondef'):
            self.queries.append((sql, args)); self.result = self.actual
            return self
        return super().execute(sql, args)


def current(cur):
    original, fixture, events, commands = historical.context()
    observations = []
    definition, _ = binding.premise()
    state = dict(after=dict(functions={binding.EDITOR: [definition, 'postgres']}))
    value = recipe.LawfulRecipe(original.business, historical.RAW, events,
        state=state, editor_observations=observations)
    return value, fixture, events, commands, observations, state


class CurrentACControls(unittest.TestCase):
    def test_old_guard_fails_exact_current_AC_before_editor_and_is_not_a_whitelist(self):
        value, f, _, _ = historical.context(); cur = CurrentCursor()
        with self.assertRaisesRegex(ValueError, '^S05_EXACT_NATIVE_LEGACY_EDITOR_BODY_REQUIRED$'):
            value(cur, f)
        self.assertEqual(cur.edit_calls, 0)
        self.assertNotEqual(binding.CURRENT_BODY_SHA, binding.OLD_BODY_SHA)

    def test_current_guard_keeps_same_unused_master_window_and_complete_original_items(self):
        cur = CurrentCursor(); value, f, events, commands, observed, _ = current(cur)
        result = value(cur, f)
        self.assertEqual(result['bom_version_id'], 'bom'); self.assertEqual(cur.edit_calls, 1)
        self.assertEqual(commands, []); self.assertEqual(events[0]['effective_from'], str(cur.start))
        self.assertEqual(observed[0]['observed_tuple'], list(cur.actual))
        self.assertTrue(observed[0]['admitted'])
        self.assertEqual(observed[0]['observed_prosrc_sha256'], binding.CURRENT_BODY_SHA)
        self.assertEqual(cur.queries[0][0].split(' from ')[0], "select pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')")

    def test_rogue_body_old_AB_hash_nonpostgres_owner_and_stale_parent_each_refuse_before_edit(self):
        changes = ('rogue_definition', 'old_AB_hash', 'nonpostgres_owner', 'stale_installed_parent')
        for change in changes:
            cur = CurrentCursor(); value, f, _, _, rows, state = current(cur)
            if change == 'rogue_definition': cur.actual = (cur.actual[0]+'\n-- rogue\n', *cur.actual[1:])
            elif change == 'old_AB_hash': cur.actual = (*cur.actual[:2], binding.OLD_BODY_SHA)
            elif change == 'nonpostgres_owner': cur.actual = (cur.actual[0], 'other', cur.actual[2])
            else: state['after']['functions'][binding.EDITOR][0] += '\n-- stale\n'
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'EXACT_CURRENT_AC_INSTALLED_EDITOR_AND_OWNER'):
                value(cur, f)
            self.assertEqual(cur.edit_calls, 0); self.assertFalse(rows[0]['admitted'])
            self.assertEqual(rows[0]['observed_tuple'], list(cur.actual))

    def test_current_moving_average_and_empty_recipe_shapes_remain_original(self):
        for empty, method in ((False, 'CATEGORY_MOVING_AVG'), (True, 'BOM_STANDARD')):
            cur = CurrentCursor(empty=empty, method=method); value, f, rows, commands, _, _ = current(cur)
            value(cur, f, empty=empty, method=method)
            self.assertEqual(cur.edit_calls, 1); self.assertEqual(commands, [])
            if empty: self.assertEqual(rows[0]['items'], [])
            else: self.assertIsNone(rows[0]['items'][0]['hpp_standard_rate'])

    def test_current_used_shared_future_foreign_or_duplicate_master_still_refuses(self):
        for change in ('used', 'shared', 'future', 'foreign', 'duplicate'):
            cur = CurrentCursor(); value, f, _, commands, _, _ = current(cur)
            if change == 'used': cur.row = (*cur.row[:-1], cur.current)
            elif change == 'shared': cur.counts = (0, 0, 0, 1)
            elif change == 'future': cur.row = ('bom', 'product', cur.current, None, True, None)
            elif change == 'foreign': cur.root = ('foreign',)
            else: cur.extra_row = True
            with self.subTest(change=change), self.assertRaises(ValueError): value(cur, f)
            self.assertEqual(cur.edit_calls, 0); self.assertEqual(commands, [])

    def test_only_one_ABI_constant_changes_entire_old_initial_and_BF_successor_source(self):
        raw = (OLD/'recipe.py').read_bytes(); derived, proof = binding.current_recipe(raw)
        self.assertEqual(proof['counted_ABI_constant_changes'], 1)
        self.assertEqual(derived.LawfulRecipe.__call__.__code__.co_code,
                         historical.recipe.LawfulRecipe.__call__.__code__.co_code)
        self.assertEqual(derived.LawfulRecipe.successor.__code__.co_code,
                         historical.recipe.LawfulRecipe.successor.__code__.co_code)
        for wrong in (raw+b'\n', raw.replace(binding.OLD_BODY_SHA.encode(), b'0'*64)):
            with self.assertRaisesRegex(ValueError, 'FROZEN_LAWFUL_RECIPE_ABI_ANCHOR'): binding.current_recipe(wrong)

    def test_current_AC_premise_exactly_one_WIB_expression_never_installs_Native_SQL(self):
        definition, premise = binding.premise()
        self.assertEqual(premise['counted_WIB_label_expression_changes'], 1)
        self.assertEqual(premise['Native_function_rewrites'], 0)
        self.assertFalse(premise['actual_current_catalog_capture'])
        self.assertEqual(definition, (HERE/'CURRENT_AC_EDITOR_DEFINITION.sql').read_text())

    def test_current_factory_binds_actual_state_without_mutating_retained_ten_callbacks(self):
        factory = load('s05_current_AC_actual_private_factory_control', HERE/'factory.py')
        b = SimpleNamespace(chain=SimpleNamespace(production=SimpleNamespace()))
        names = ('cp7_wip_source_cases', 'cp7_f03_e24_issue_cases', 'cp6_bf_probe', 'cp7_qc_source_cases', 'cp7_snapshot_cases')
        modules = {name: ModuleType(name) for name in names}; modules[names[0]].b = b
        package = ModuleType('cp7_accessory_standard_report'); stage = ModuleType('cp7_accessory_standard_report.stage')
        package.stage = stage; package.__path__ = []
        modules.update(cp7_accessory_standard_report=package, **{'cp7_accessory_standard_report.stage': stage})
        retained = ModuleType('cp7_accessory_standard_report.cases')
        retained.__file__ = str(ROOT/'scripts/cp7_accessory_standard_report/cases.py'); retained.__package__ = 'cp7_accessory_standard_report'
        with patch.dict(sys.modules, modules):
            exec(compile(historical.RAW, retained.__file__, 'exec'), retained.__dict__)
            original_recipe = retained.recipe; state = {'actual_installation_control': True}
            private = factory.business(retained, state)
            self.assertIs(retained.recipe, original_recipe)
            self.assertIs(private.recipe.actual_installed_parent, state)
            self.assertEqual(private.IDS, retained.IDS)
            self.assertEqual(len(private.cases(None, date(2026, 10, 30), state)), 10)
            for name, function in retained.__dict__.items():
                if callable(function) and getattr(function, '__module__', None) == retained.__name__ and name != 'recipe':
                    self.assertEqual(getattr(private, name).__code__.co_code, function.__code__.co_code)
            self.assertEqual(private.current_editor_derivation['counted_ABI_constant_changes'], 1)

    def test_actual_parent_and_editor_guard_precede_any_fixture_and_observations_are_retained(self):
        text = (HERE/'probe.py').read_text()
        self.assertLess(text.index('component.require_local(conn, cur)'), text.index('product.verify(cur, state)'))
        self.assertLess(text.index('product.verify(cur, state)'), text.index('binding.admit_editor(cur, state, observations)'))
        self.assertLess(text.index('binding.admit_editor(cur, state, observations)'), text.index('component.exercise(conn'))
        self.assertIn("observed_tuple=list(actual)", (HERE/'binding.py').read_text())
        self.assertIn('actual_observed_editor_rows=', text)

    def test_full_source_inherits_every_old_pin_original_ten_and_one_scope_binding(self):
        proof = admission.offline()
        self.assertEqual(len(proof['Native_case_ids']), 10)
        self.assertEqual(proof['source_scope_binding']['counted_private_scope_bindings'], 1)
        self.assertTrue(proof['tracked_scope']['all_other_cdbdea_tracked_files_unchanged'])
        self.assertEqual(proof['inherited']['native_source_premise']['Native_editor_prosrc_sha256'], binding.OLD_BODY_SHA)
        self.assertEqual(proof['actual_Native_credit'], 0)
        self.assertEqual(sha256((ROOT/'scripts/cp7_accessory_standard_report/cases.py').read_bytes()).hexdigest(),
                         'e025be1280630dfb89f62261163194ce072b6f6ad6d909b56ff6c82f75778e98')

    def test_first_actual_cdbdea_negative_is_retained_without_observed_hash_fabrication(self):
        first = load('s05_current_AC_first_failure_control', HERE/'first_failure.py').checked()
        self.assertEqual(first['counts'], {'INCOMPLETE': 10}); self.assertEqual(first['Native_PASS'], 0)
        self.assertFalse(first['success_prerequisite']); self.assertFalse(first['actual_editor_observed_digest_retained'])
        self.assertFalse(first['used_witness_reached']); self.assertTrue(first['full_outer_restore'])

    def test_untracked_own_source_refuses_without_arbitrary_rehash(self):
        path = HERE/'SOURCE_CONTROL_UNDECLARED.py'
        self.assertFalse(path.exists())
        try:
            path.write_text('raise RuntimeError("must not import")\n')
            with self.assertRaisesRegex(ValueError, 'UNDECLARED_OWN_SOURCE'): admission.offline()
        finally:
            path.unlink()

    def test_full_workflow_keeps64_steps_frozen_vendor_and_six_bindings_cleanup_and_upload(self):
        text = (ROOT/workflow.PATH).read_text(); proof = workflow.checked(text)
        self.assertEqual(proof['parent_steps'], 64); self.assertEqual(proof['child_steps'], 64)
        self.assertEqual(len(proof['adapted_steps']), 5)
        self.assertTrue(proof['frozen_vendor_files_and_six_existing_engine_bindings_unchanged'])
        for before, after in ((workflow.BRANCH, 'main'), ('if: always()', 'if: success()'),
                              ('Clone the aligned AB state for install', 'Skip clone')):
            changed = text.replace(before, after, 1); self.assertNotEqual(changed, text)
            with self.assertRaisesRegex(ValueError, 'WORKFLOW_CHANGED'): workflow.checked(changed)

    def test_without_confirmation_runtime_is_not_imported_or_executed(self):
        probe = load('s05_current_AC_no_runtime_control', HERE/'probe.py')
        with patch.dict(os.environ, {}, clear=True), patch.object(probe, 'runtime') as runtime:
            with self.assertRaisesRegex(ValueError, 'EXPLICIT_LOCAL_QUALIFICATION_CONFIRMATION'): probe.execute()
            runtime.assert_not_called()


if __name__ == '__main__':
    unittest.main()
