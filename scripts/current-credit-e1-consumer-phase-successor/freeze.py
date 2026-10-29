"""Seal this new source-only transition; never edit a predecessor manifest."""
from pathlib import Path
from hashlib import sha256
import argparse, importlib.util, json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREFIX = 'scripts/current-credit-e1-consumer-phase-successor/'
OLD = 'scripts/current-credit-e1-current-d1-native17-qualification/SOURCE.json'


def build():
    spec = importlib.util.spec_from_file_location('e_phase_freeze_counter', HERE/'check.py')
    counter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(counter)
    declaration = json.loads((ROOT/OLD).read_bytes())
    if len(declaration['files']) != 282 or sha256((ROOT/OLD).read_bytes()).hexdigest() != counter.OLD_SOURCE_SHA:
        raise ValueError('EXACT_FAILED_SOURCE282_REQUIRED')
    paths = set(declaration['files']) | set(counter.PRODUCT) | {OLD}
    paths |= {str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p.name != 'SOURCE.json'}
    result = {
        'contract': 'cp7.e1-consumer-phase-successor-source.v1',
        'state': 'CLOSED_SOURCE_REPAIR_ONLY_NOT_ACTUAL_NATIVE_QUALIFICATION',
        'base_public_head': counter.BASE,
        'base_public_tree': 'b48fb750bd6d0eeba8a2207665c6a0ba22f2780c',
        'retained_frozen_source282_sha256': counter.OLD_SOURCE_SHA,
        'product_exceptions': list(counter.PRODUCT),
        'counted_derivation': counter.derivation(),
        'product_runtime_leaves': 9,
        'private_functions_including_same_three_Native_copies': {'before': 40, 'after': 41},
        'existing_changed_function_set': 19,
        'callbacks_changed': 0,
        'Native_engine_D1_global_BE_guards_UI_money_qty_date_oracle_changes': 0,
        'new_public_RPCS_roles_tables_triggers_grants': 0,
        'retained_actual_E17': {'PASS': 15, 'INCOMPLETE': 2},
        'accepted_fresh_Native17': None,
        'actual_Native_Auth_browser_races_by_this_helper': 0,
        'production_go': False,
        'independent_acceptance': False,
        'files': {},
    }
    for relative in sorted(paths):
        path = counter.regular(ROOT, relative)
        raw = path.read_bytes()
        result['files'][relative] = dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    source = build()
    raw = (json.dumps(source, indent=2) + '\n').encode()
    if args.write:
        (HERE/'SOURCE.json').write_bytes(raw)
    print(json.dumps(dict(files=len(source['files']), bytes=len(raw), sha256=sha256(raw).hexdigest(), written=args.write)))
