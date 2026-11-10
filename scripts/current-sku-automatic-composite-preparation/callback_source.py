"""Import every Native callback donor before setup; execute no business case."""
from pathlib import Path
import inspect
import json


def check(entry, fixture):
    entry.actual_inputs()
    root = entry.FROZEN_SKU
    business = entry.load('automatic_actual_money19_source_before_database',
                          root / 'scripts/current-sku-cost-money-qualification/native_cases.py')
    retained = entry.load('automatic_actual_money_prerequisites_before_database',
                          root / 'scripts/current-sku-cost-money-qualification/native_preflight.py')
    suite = entry.load('automatic_actual_native25_source_before_database',
                      entry.HERE / 'native_suite.py')
    ids = list(business.IDS + suite.native.IDS + suite.invoices.IDS)
    entry.require(len(ids) == 25 and len(set(ids)) == 25
                  and ids == json.loads(entry.PLAN_FILE.read_bytes())['case_ids'],
                  'AUTOMATIC_EXACT_ACTUAL_NATIVE25_IMPORT_PLAN_REQUIRED')
    inspect.signature(business.cases).bind(None, None)
    inspect.signature(retained.check).bind(None, None, business)
    # Money cases deliberately need the location-aware constructor. Browser
    # cases use their different, byte-pinned historical constructor.
    inspect.signature(business.f.opening).bind(None, None, 1, '1.00', None, location=None)
    inspect.signature(business.f.reserve).bind(None, {}, None, 1, location=None)
    modules, domain_proof = fixture.domain_modules()
    upstream = suite.native.source_contract(fixture, modules)
    invoices = suite.invoices.source_contract(modules)
    filenames = [Path(business.__file__), Path(business.f.__file__), Path(retained.__file__)]
    for path in filenames:
        entry.require(path.is_relative_to(root) and path.is_file()
                      and not any(p.is_symlink() for p in (path, *path.parents)),
                      'AUTOMATIC_EXACT_MONEY_CALLBACK_SOURCE_CHECKOUT_REQUIRED')
    return dict(status='NATIVE25_ACTUAL_CALLBACK_IMPORTS_AND_SIGNATURES_PASS_NOT_ERP',
                actual_case_ids=ids, money_native_cases=19, added_native_cases=6,
                money_location_aware_constructor_preserved=True,
                source_files={str(p.relative_to(root)): entry.admission.pin(p.read_bytes()) for p in filenames},
                current_parent_domain_source=domain_proof, upstream=upstream, invoices=invoices,
                business_callbacks_executed=0, actual_SQL_executed=0, actual_ERP_cases=0)
