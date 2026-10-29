"""Local source/master-SQL doubles only; no Native/Auth/browser PASS credit."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import ast
import gzip
import importlib.util
import json
import sys
import tempfile
import unittest
import uuid
import yaml

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


d = load('unit_sku_unique_derivations', HERE / 'derive.py')
recovery = load('unit_sku_unique_recovery', HERE / 'recovery.py')
closure = load('unit_sku_unique_closure', HERE / 'closure.py')
workflow = load('unit_sku_unique_workflow', HERE / 'workflow.py')
old = ROOT / 'scripts/current-sku-combined-followup-qualification'
gate = load('unit_sku_unique_unchanged_gate', old / 'gate.py')
plan = load('unit_sku_unique_unchanged_plan', old / 'plan.py')


class MasterCursor:
    """Only administrative INSERT recording and the observed name uniqueness."""
    def __init__(self):
        self.names = set()
        self.codes = set()
        self.calls = []

    def execute(self, sql, args):
        self.calls.append((sql, args))
        table = sql.split('insert into erp.', 1)[1].split('(', 1)[0]
        assert table in ('product_models', 'brands', 'sizes', 'product_model_sizes', 'products', 'accessory_bom_versions')
        if table == 'brands':
            name = args[2] if len(args) == 3 else 'SKU29 different brand'
            if name in self.names:
                raise ValueError('brands_brand_name_key:' + name)
            assert args[1] not in self.codes
            self.names.add(name)
            self.codes.add(args[1])


def master_function(text):
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == 'custom_group_products')
    seq = iter(uuid.UUID(int=n) for n in range(100000001, 100000100))
    # Use a deterministic existing tag with all ten leading hex digits varying
    # by namespace. This double checks the actual function SQL/parameters.
    namespace = dict(admin=lambda cur: None, BASE=SimpleNamespace(BASE_PRODUCT='EXISTING'),
                     uuid=SimpleNamespace(uuid4=lambda: next(seq)))
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<actual-master-function>', 'exec'), namespace)
    return namespace['custom_group_products']


class Derivation(unittest.TestCase):
    def test_complete_twelve_module_sources_are_reversible_one_name_sixteen_routes(self):
        inventory = d.inventory()
        self.assertEqual(len(inventory), 12)
        self.assertEqual(sum(x['counted_changes'] for x in inventory.values()), 17)
        self.assertEqual(sum(x['administrative_name_changes'] for x in inventory.values()), 1)
        for key, (relative, _) in d.SOURCES.items():
            original = (ROOT / relative).read_bytes()
            text, proof = d.derive(key)
            for before, after in reversed(d.REPLACEMENTS[key]):
                self.assertEqual(text.count(after), 1)
                text = text.replace(after, before, 1)
            self.assertEqual(text.encode(), original)
            self.assertTrue(proof['byte_exact_reversible'])
            self.assertEqual(proof['assertions_removed'], 0)

    def test_unknown_byte_and_ambiguous_anchor_refuse_without_rebinding(self):
        original = (ROOT / d.SOURCES['fixture'][0]).read_bytes()
        with self.assertRaisesRegex(ValueError, 'FROZEN_SOURCE_CHANGED'):
            d.derive('fixture', original + b'\n')
        broken = original + d.REPLACEMENTS['fixture'][0][0].encode()
        with patch.dict(d.SOURCES, fixture=(d.SOURCES['fixture'][0], sha256(broken).hexdigest())):
            with self.assertRaisesRegex(ValueError, 'EXACT_ONE_ANCHOR'):
                d.derive('fixture', broken)

    def test_original_collision_and_derived_two_calls_coexist_with_committed_original(self):
        original = master_function((ROOT / d.SOURCES['fixture'][0]).read_text())
        cur = MasterCursor()
        original(cur)
        with self.assertRaisesRegex(ValueError, 'brands_brand_name_key'):
            original(cur)
        unique = master_function(d.derive('fixture')[0])
        # Distinct real UUID tags are exercised below through private modules;
        # this source double proves the same master SQL change and no ledger.
        original_calls = MasterCursor()
        original_again = master_function((ROOT / d.SOURCES['fixture'][0]).read_text())
        original_again(original_calls)
        after = MasterCursor()
        unique(after)
        self.assertEqual(len(after.calls), len(original_calls.calls))
        self.assertEqual(after.calls[:1] + after.calls[2:], original_calls.calls[:1] + original_calls.calls[2:])
        self.assertEqual(after.calls[1][1][:2], original_calls.calls[1][1])
        self.assertEqual(after.calls[1][1][2], 'SKU29 different brand ' + after.calls[1][1][1].removeprefix('S29B-'))
        self.assertEqual(original_calls.names, {'SKU29 different brand'})

    def test_private_cost_race_wait_browser_modules_all_use_unique_fixture(self):
        base = SimpleNamespace(BASE_PRODUCT='EXISTING', LOCATION='LOCATION', OPERATOR_APP='OPERATOR')
        b = SimpleNamespace(chain=SimpleNamespace(base=base), bcp=SimpleNamespace(), api=SimpleNamespace(admin=lambda cur: None))
        bf = ModuleType('cp6_bf_probe'); bf.b = b; bf.one = lambda *args: None
        be = ModuleType('cp6_be_probe')
        sql = ModuleType('psycopg'); sql.Error = type('NoSQL', (Exception,), {})
        sql.connect = lambda *_a, **_k: self.fail('NO_DATABASE_IMPORT_CONTROL')
        package = ModuleType('cp7_sku_pair_conversion'); package.composition = SimpleNamespace()
        chain = ModuleType('cp7_p21_current_chain_rehearsal_probe')
        auth = ModuleType('cp7_snapshot_cases')
        with patch.dict(sys.modules, {'cp6_be_probe': be, 'cp6_bf_probe': bf, 'psycopg': sql,
              'cp7_sku_pair_conversion': package, 'cp7_p21_current_chain_rehearsal_probe': chain,
              'cp7_snapshot_cases': auth}):
            cost = load('unit_unique_real_cost_module', HERE / 'cost_cases.py')
            race = load('unit_unique_real_race_module', HERE / 'races.py')
            wait = load('unit_unique_real_wait_module', HERE / 'auth_waits.py')
            browser = load('unit_unique_real_browser_fixture', HERE / 'browser_fixture.py')
            with self.assertRaisesRegex(AssertionError, 'REQUIRES_PRIOR_ACTUAL_NATIVE7'):
                cost.cases(None, None)
            modules = (cost.n.f, race.f, wait.f, browser.f)
            self.assertEqual(len({id(m) for m in modules}), 4)
            cur = MasterCursor(); cur.names.add('SKU29 different brand')
            for module, count in zip(modules, (3, 3, 6, 2)):
                self.assertEqual(module.__SKU_UNIQUE_DERIVATION__['key'], 'fixture')
                self.assertIs(module.nonpo.__globals__, module.__dict__)
                self.assertIs(module.masters.__globals__['custom_group_products'], module.custom_group_products)
                # Only master functions are invoked; no business RPC result is
                # mocked, posted, deleted or reused in this local control.
                for _ in range(count):
                    module.custom_group_products(cur)
            self.assertEqual(len(cur.names), 15)  # old witness + cost3/race3/wait6/browser2
            self.assertEqual(tuple(cost.IDS), tuple(plan.COST_IDS))
            self.assertEqual(tuple(race.IDS), tuple(plan.RACE_IDS))
            self.assertEqual(tuple(wait.IDS), tuple(plan.WAIT_IDS))

    def test_dispatch_graph_routes_every_downstream_chain_and_keeps_base_seven(self):
        runner = d.derive('runner')[0]
        self.assertIn("ROOT / 'scripts/current-sku-pair-conversion-qualification/runner.py'", runner)
        for key in ('cost_cases', 'concurrency'):
            self.assertIn(d.NS + '/' + key + '.py', runner)
        self.assertIn(d.NS + '/cases.mjs', runner)
        concurrency = d.derive('concurrency')[0]
        for key in ('races', 'auth_waits'):
            self.assertIn(d.NS + '/' + key + '.py', concurrency)
        self.assertIn("ids(CALLBACKS / 'races.py')", concurrency)
        self.assertIn("ids(CALLBACKS / 'auth_waits.py')", concurrency)
        self.assertIn("from './browser.mjs'", d.derive('cases')[0])
        self.assertIn("from '../current-staged-ai-browser-qualification/cases.mjs'", d.derive('cases')[0])
        for key in ('browser', 'cases'):
            self.assertEqual((HERE / (key + '.mjs')).read_text(), d.derive(key)[0])
        self.assertEqual(tuple(map(len, (plan.NATIVE_IDS, plan.COST_IDS, plan.RACE_IDS, plan.WAIT_IDS, plan.BROWSER_IDS))), (7, 3, 3, 6, 4))

    def test_unchanged_five_change_package_engine_and_historical_endpoint(self):
        engine = load('unit_unique_frozen_five_changes', old / 'derive.py')
        raw = (ROOT / 'scripts/current-vendor-receivable-qualification/probe.py').read_bytes()
        text, proof = engine.derive(raw)
        self.assertEqual(proof['counted_changes'], 5)
        for before, after in reversed(engine.REPLACEMENTS):
            text = text.replace(after, before, 1)
        self.assertEqual(text.encode(), raw)
        historical = d.derive('historical_admission')[0]
        self.assertIn("gate.BASE, '" + d.BASE + "'", historical)
        self.assertNotIn("gate.BASE, 'HEAD'", historical)
        self.assertIn("for path, expected in source['files'].items()", historical)
        self.assertIn('subprocess.check_output', historical)


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = recovery.originals()
        cls.values = {name: json.loads(raw) for name, raw in cls.raw.items()}

    def test_actual_first_failure_is_lossless_and_recovered_but_never_full_pass(self):
        result = recovery.observe(self.values)
        self.assertEqual(result['fresh_base_Native_counts'], {'PASS': 7})
        self.assertEqual(result['cost_Native_counts'], {'INCOMPLETE': 3})
        self.assertEqual(result['downstream_not_reached'], 13)
        self.assertFalse(result['outer_used_guard_observed'])
        self.assertFalse(result['usable_prerequisite'])

    def test_partial_restore_or_relabelled_failure_is_detected(self):
        for key, value in (('status', 'PASS'), ('baseline_full22_all_rows_all_sequences_equal', False),
                           ('used_guard_refused_before_DDL', True)):
            changed = deepcopy(self.values)
            changed['CP7_SKU_COMBINED_FOLLOWUP23.json'][key] = value
            with self.assertRaises(AssertionError):
                recovery.observe(changed)

    def test_exact_terminal21c_prerequisite_still_admits_zero_fresh_credit(self):
        folder = old / 'retained21'
        raw = gzip.decompress((folder / 'CP7_SKU_PAIR_CONVERSION_NATIVE.json.gz').read_bytes())
        pkg = gzip.decompress((folder / 'T3_PACKAGE_INSTALL.json.gz').read_bytes())
        sources = json.loads(raw)['source_declaration']['current_installation']
        proof = gate.admitted(json.loads((old / 'CONFIG.json').read_bytes()), raw, pkg, sources, plan.NATIVE_IDS)
        self.assertEqual(proof['fresh_cases_credited'], 0)
        self.assertEqual(proof['head'], gate.BASE)

    def test_c163_outer_and_fresh_seven_cannot_replace_terminal_prerequisite(self):
        cfg = json.loads((old / 'CONFIG.json').read_bytes())
        for name in ('CP7_SKU_COMBINED_FOLLOWUP23.json', 'CP7_SKU_PAIR_CONVERSION_NATIVE7.json'):
            raw = self.raw[name]; pkg = self.raw['T3_PACKAGE_INSTALL.json']
            # Negative-only pin double gets past the byte check, then the
            # unchanged semantic gate must still reject these actual bytes.
            changed = deepcopy(cfg)
            for key, value in (('original', raw), ('package', pkg)):
                changed['accepted_native7'][key].update(bytes=len(value), sha256=sha256(value).hexdigest())
            with self.assertRaisesRegex(ValueError, 'RETAINED_NATIVE7_NOT_PASS'):
                gate.admitted(changed, raw, pkg, {}, plan.NATIVE_IDS)


class ClosureAndWorkflow(unittest.TestCase):
    def test_complete_parent_inventory_and_current_bytes_not_selected_products(self):
        proof = closure.source_only(require_clean=False)
        self.assertEqual(proof['unchanged_parent_files'], 13569)
        self.assertFalse(proof['product_or_oracle_changes'])
        self.assertFalse(proof['actual_successor_execution'])

    def test_modified_frozen_file_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp); (path / 'fixture.py').write_text('original')
            pin = dict(bytes=8, sha256=sha256(b'original').hexdigest())
            closure.verify_files(path, {'fixture.py': pin})
            (path / 'fixture.py').write_text('changed!')
            with self.assertRaisesRegex(ValueError, 'DECLARED_BYTES_CHANGED'):
                closure.verify_files(path, {'fixture.py': pin})

    def test_workflow_keeps_every_install_auth_restore_artifact_step(self):
        original = yaml.safe_load((ROOT / workflow.OLD).read_text())
        current = yaml.safe_load((ROOT / workflow.NEW).read_text())
        self.assertEqual(current, workflow.derive(original))
        old_steps, new_steps = original['jobs']['p21']['steps'], current['jobs']['p21']['steps']
        self.assertEqual(len(old_steps), len(new_steps))
        changed = [i for i, (a, b) in enumerate(zip(old_steps, new_steps)) if a != b]
        self.assertEqual(changed, [59, 60, 65, 68])
        self.assertEqual(current['jobs']['p21']['env'], original['jobs']['p21']['env'])
        for i in changed[:-1]:
            self.assertEqual(old_steps[i]['name'], new_steps[i]['name'])
        self.assertEqual(current['jobs']['p21']['if'], "github.ref == 'refs/heads/" + workflow.BRANCH + "'")
        self.assertEqual(current['on']['push']['branches'], [workflow.BRANCH])
        self.assertEqual(current['on']['push']['paths'], [workflow.NEW, workflow.NS + '/**'])


if __name__ == '__main__':
    unittest.main()
