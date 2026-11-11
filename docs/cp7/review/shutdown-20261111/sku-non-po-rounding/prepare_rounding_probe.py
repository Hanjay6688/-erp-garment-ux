"""Run the owning projection on exact retained preparation and catalogue bytes."""
import argparse
import ast
import copy
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys
from types import ModuleType


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def prepared_only(path, product, profile, *, automatic=False):
    """Load the retained pure preparation function without runtime imports."""
    tree = ast.parse(path.read_bytes())
    prepared, = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'prepared']
    module = ModuleType(path.parent.name + '_source_check')
    module.prepared_product = product
    module.catalog_additions = profile
    if automatic:
        module.installation_product = product
    exec(compile(ast.Module(body=[prepared], type_ignores=[]), str(path), 'exec'), vars(module))
    return module


def load(path):
    spec = spec_from_file_location('owning_non_po_rounding', path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_transition(profile_checker, catalogue, old, corrected):
    assert {group for group in old['groups']} == set(profile_checker.GROUPS)
    assert old['groups'] == corrected['groups']
    assert old['replacement_before'] == corrected['replacement_before']
    after = {group: catalogue[group] | rows for group, rows in corrected['groups'].items()}
    after['functions'].update(corrected['replacement_functions'])
    profile_checker.transition(catalogue, after, corrected)
    try:
        profile_checker.transition(catalogue, after, old)
    except ValueError as error:
        assert str(error).startswith('SKU_MONEY_EXACT_FUNCTION_TRANSITION_CHANGED:')
    else:
        raise AssertionError('The old profile unexpectedly accepted the new SQL')
    return after


def main(root, source, lab, output):
    money_root = root / 'qualified-sku-money/scripts'
    auto_root = root / 'qualified-sku-automatic/scripts'
    sys.path[:0] = [str(money_root), str(auto_root)]
    from cp7_sku_cost_components import catalog_additions as money_profile
    from cp7_sku_cost_components import prepared_product as money_product
    from cp7_sku_automatic_pending import catalog_additions as auto_profile
    from cp7_sku_automatic_pending import installation_product as auto_product

    rounding = load(source / 'non_po_rounding.py')
    money = prepared_only(money_root / 'cp7_sku_cost_components/composition.py', money_product, money_profile)
    money.sources = lambda: {'frozen_money': 'f1674ae84739f577571d68415beabfca3f3b832b'}
    automatic = prepared_only(auto_root / 'cp7_sku_automatic_pending/composition.py', auto_product, auto_profile,
                              automatic=True)
    automatic.money_product = money_product
    automatic.parent = lambda: money
    scope = load(source / 'module_scope.py')
    try:
        money_product.money_delta.credit_definitions({})
    except ModuleNotFoundError as error:
        assert error.name == 'financial_delta'
    else:
        raise AssertionError('The retained bare import unexpectedly resolved before binding')
    for owner in (money, automatic):
        owner.prepared = scope.bind_money_preparation(owner.prepared, money_product.financial_delta)

    historical = lab / 'native27'
    raw = (historical / rounding.ORIGINAL).read_bytes()
    assert tuple(pin(raw).values()) == rounding.ORIGINAL_PIN
    catalogue = json.loads(raw)['committed'][rounding.ORIGINAL_CASE]['Native_to_copy_handoff']['raw_current_catalog']
    originals = {sig: catalogue['functions'][sig][0] for sig in money_product.parent_original_signatures()}
    prior = dict(originals=originals)
    old, old_profile, old_tables = money.prepared(catalogue, prior)
    assert 'financial_delta' not in sys.modules
    rounding.bind(money)
    new, new_profile, new_tables = money.prepared(catalogue, prior)
    assert old_tables == new_tables
    assert old['ddl'] == new['ddl']
    assert old['source_files'] == new['source_files']
    changed = {sig for sig in old['definitions'] if old['definitions'][sig] != new['definitions'][sig]}
    assert changed == rounding.ROUTES.keys()
    for sig in changed:
        assert new_profile['replacement_functions'][sig][1:] == old_profile['replacement_functions'][sig][1:]
        assert pin(new['definitions'][sig].encode()) == new_profile['derived_replacements'][sig]
    frozen = copy.deepcopy(old)
    frozen['definitions'][rounding.NATIVE] += '\n'
    try:
        rounding.correct(frozen, old_profile)
    except ValueError as error:
        assert str(error) == 'SKU_NON_PO_ROUNDING_EXACT_PREIMAGE_REQUIRED:' + rounding.NATIVE
    else:
        raise AssertionError('Stale SQL unexpectedly accepted')
    moving = json.loads((money_root / 'cp7_sku_moving_average/CATALOG_ADDITIONS.json').read_bytes())
    moving_boundary = {group: rows | moving['groups'].get(group, {}) for group, rows in catalogue.items()}
    assert old_profile['replacement_before'].keys() <= moving_boundary['functions'].keys()
    moving_boundary['functions'].update(old_profile['replacement_before'])
    after = verify_transition(money_profile, moving_boundary, old_profile, new_profile)
    auto, auto_catalogue, _ = automatic.prepared(after, dict(before=catalogue, predecessor=prior))
    assert not changed & (auto['definitions'].keys() | auto_catalogue['groups']['functions'].keys())
    assert rounding.preflight(automatic, historical)['source'] == money.sources()['non_po_rounding']
    assert 'financial_delta' not in sys.modules
    foreign = ModuleType('financial_delta')
    sys.modules['financial_delta'] = foreign
    try:
        automatic.prepared(after, dict(before=catalogue, predecessor=prior))
    except ValueError as error:
        assert str(error) == 'SKU_AUTOMATIC_FROZEN_FINANCIAL_DELTA_COLLISION'
        assert sys.modules['financial_delta'] is foreign
    else:
        raise AssertionError('Foreign financial dependency unexpectedly accepted')
    finally:
        del sys.modules['financial_delta']
    receipt = dict(rounding.preflight(automatic, historical), projected_catalogue_groups=len(after),
                   changed_bodies=sorted(changed), no_authority_delta=True, stale_SQL_refused=True,
                   old_profile_refuses_changed_body=True,
                   frozen_financial_import_scoped=True, foreign_financial_import_refused=True,
                   owning_projection_file=pin((source / 'non_po_rounding.py').read_bytes()))
    output.mkdir(exist_ok=False)
    (output / 'ROUNDING_SOURCE_PREFLIGHT.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')

    fixture = (lab / 'focused-r6/COST_MODEL_INPUT.json').read_bytes()
    assert pin(fixture) == dict(bytes=770126, sha256='c223048920a6bc225fd1275d96c201c64a0239e56a32a511be580937f392b6ec')
    inputs = json.loads(fixture)
    assert inputs['cost_ddl'] == old['ddl']
    assert inputs['candidate_money_definitions'] == old['definitions']
    assert inputs['automatic_delta'] == {key: auto[key] for key in ('ddl', 'definitions')}
    inputs['candidate_money_definitions'] = new['definitions']
    inputs['rounding_originals'] = {sig: old['definitions'][sig] for sig in changed}
    inputs['probe_variant'] = dict(scope='OWNING_SKU_MONEY_PROJECTION', source=receipt)
    (output / 'COST_MODEL_INPUT.json').write_text(json.dumps(inputs, sort_keys=True) + '\n')
    focused = (lab / 'focused-r6/focused.mjs').read_text()
    marker = ' await runFocusedCases({db, input, engine,'
    assert focused.count(marker) == 1
    focused = focused.replace(marker, """
 const { checkRoundingCatalogue } = await import(process.env.CP7_ROUNDING_CATALOGUE_PROBE);
 await checkRoundingCatalogue(db, input);
""" + marker)
    (output / 'focused.mjs').write_text(focused)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('root', 'source', 'lab', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    main(*(path.resolve() for path in vars(args).values()))
