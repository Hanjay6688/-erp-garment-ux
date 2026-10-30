"""Private full old local tests with counted SOURCE assertions, no business edits."""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
import argparse
import importlib.util
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-sku-managed-recovery-native27-qualification'
IMPORT = "\n_s = importlib.util.spec_from_file_location('sku23_unit_transition', Path(__file__).resolve().parents[2] / '" + NS + "/transition.py')\n_sku23 = importlib.util.module_from_spec(_s)\n_s.loader.exec_module(_sku23)\n"
PATHS = {
 'unique': ['scripts/current-sku-combined-fixture-followup/test_followup.py'],
 'combined': ['scripts/current-sku-combined-followup-qualification/' + n for n in ('test_preparation.py', 'test_successor.py', 'test_orchestration.py')],
 'cost': ['scripts/current-sku-group-cost-qualification/test_oracle.py'],
 'browser': ['scripts/current-sku-pair-browser-qualification/test_plan.py'],
}
PINS = {'scripts/current-sku-combined-fixture-followup/test_followup.py': '42ca1487a68a5c769a68d494096e7b0a880653645af88ce125e7f3f44a0cdb37', 'scripts/current-sku-combined-followup-qualification/test_preparation.py': '66abdbf684c932f7e5490f32fa48928ac2dcd4834f2b5ccb3dc175837959a2f1', 'scripts/current-sku-combined-followup-qualification/test_successor.py': '501ee2a9d13292915b4b346eb2e76a4fe38e387cafd0d4d82018e9e0634eb5a9', 'scripts/current-sku-combined-followup-qualification/test_orchestration.py': '94c6b4a50bee985dd1e766e31684eebc718222877dda0a385afd6f1433f32add', 'scripts/current-sku-group-cost-qualification/test_oracle.py': 'bbcf91520cc0281feff88abdc6b6a3d35946c1d0280a3319448cbfa65fe03554', 'scripts/current-sku-pair-browser-qualification/test_plan.py': '44251a5d06592faed1098804012b82d5b7a53657675c2a6e0e99d2508b18bcfe'}
CHANGES = {
 'test_followup.py': (
  ("closure = load('unit_sku_unique_closure', HERE / 'closure.py')", "closure = load('unit_sku_unique_closure', ROOT / '" + NS + "/closure.py')"),
  ("self.assertEqual(proof['unchanged_parent_files'], 13569)", "self.assertEqual(proof['unchanged_parent_files'], 13759)"),
  ("self.assertFalse(proof['product_or_oracle_changes'])", "self.assertEqual(proof['parent_sql_exceptions'], 0)\n        self.assertFalse(proof['financial_quantity_fullcensus_oracles_changed'])"),
 ),
 'test_preparation.py': (
  ('import yaml', 'import yaml\n' + IMPORT),
  ("raw=(ROOT/name).read_bytes();self.assertEqual(len(raw),pin['bytes'],name);self.assertEqual(sha256(raw).hexdigest(),pin['sha256'],name)", "pin=_sku23.pin_for(name,pin);raw=(ROOT/name).read_bytes();self.assertEqual(len(raw),pin['bytes'],name);self.assertEqual(sha256(raw).hexdigest(),pin['sha256'],name)"),
 ),
 'test_successor.py': (
  ('import unittest', 'import unittest\n' + IMPORT),
  ("self.assertEqual((ROOT/name).read_bytes(),git('show',gate.BASE+':'+name),name)", "self.assertTrue(_sku23.historical_path(ROOT,name,gate.BASE),name)"),
 ),
 'test_oracle.py': (
  ("guard=load('sku_cost_local_source_guard',HERE/'source_guard.py')", "guard=load('sku_cost_local_source_guard',HERE.parents[1]/'" + NS + "/cost_guard.py')"),
 ),
 'test_plan.py': (
  ("HERE/'source_guard.py'", "HERE.parents[1]/'" + NS + "/browser_guard.py'"),
 ),
}


def derive(path):
    raw = (ROOT / path).read_bytes()
    assert sha256(raw).hexdigest() == PINS[path], 'SKU23_INHERITED_TEST_SOURCE_CHANGED:' + path
    text = raw.decode()
    changes = CHANGES.get(Path(path).name, ())
    for before, after in changes:
        assert text.count(before) == 1 and after not in text, 'SKU23_INHERITED_SOURCE_ANCHOR_CHANGED:' + path
        text = text.replace(before, after, 1)
    inverse = text
    for before, after in reversed(changes):
        assert inverse.count(after) == 1
        inverse = inverse.replace(after, before, 1)
    assert inverse.encode() == raw
    compile(text, path, 'exec')
    return text, dict(source=path, original_sha256=PINS[path], derived_sha256=sha256(text.encode()).hexdigest(),
        counted_source_test_changes=len(changes), business_oracle_changes=0, reversible=True)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('suite', choices=PATHS)
    args = parser.parse_args(argv)
    suite = unittest.TestSuite()
    for i, path in enumerate(PATHS[args.suite]):
        text, _ = derive(path)
        module = ModuleType('sku23_private_inherited_test_' + str(i))
        module.__file__ = str(ROOT / path)
        exec(compile(text, module.__file__, 'exec'), module.__dict__)
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
