"""Observe complete automatic context/history over the unchanged money graph."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT / 'scripts/current-global-sku-money-preparation'
spec = importlib.util.spec_from_file_location('global_automatic_exact_money_routes', PRIOR / 'routes.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
base = prior.base
TABLES = ('automatic_context_v5', 'automatic_admissions_v5')


def sources():
    reference = json.loads((HERE / 'SOURCE_REFERENCE.json').read_bytes())
    base.require(reference['classification'] == 'EXACT_AUTOMATIC_SOURCE_NOT_ERP_OR_GLOBAL_ACCEPTANCE'
                 and reference['actual_ERP_cases'] == 0 and reference['runtime_admission'] is False
                 and reference['production_go'] is False, 'GLOBAL_AUTOMATIC_SOURCE_IS_NOT_ACCEPTANCE')
    tree = reference['automatic_source']['tree']
    for path, expected in reference['automatic_files'].items():
        raw = base.git('show', tree + ':' + path)
        base.require(base.pin(raw) == {key: expected[key] for key in ('bytes', 'sha256')}
                     and base.git('rev-parse', tree + ':' + path).decode().strip() == expected['blob'],
                     'GLOBAL_AUTOMATIC_EXACT_ADDITION_SOURCE_REQUIRED:' + path)
    base.require(len(reference['automatic_files']) == 20, 'GLOBAL_AUTOMATIC_COMPLETE_TWENTY_ADDITIONS_REQUIRED')
    for path, blob in reference['unchanged_money_product']['files'].items():
        base.require(base.git('rev-parse', tree + ':' + path).decode().strip() == blob,
                     'GLOBAL_AUTOMATIC_UNCHANGED_MONEY_PRODUCT_REQUIRED:' + path)
    base.require(len(reference['unchanged_money_product']['files']) == 44,
                 'GLOBAL_AUTOMATIC_COMPLETE_MONEY_PRODUCT_REQUIRED')
    raw = base.git('show', tree + ':scripts/cp7_sku_automatic_pending/CATALOG_ADDITIONS.json')
    base.require(base.pin(raw) == reference['profile'], 'GLOBAL_AUTOMATIC_EXACT_PREPARED_CATALOGUE_SOURCE')
    profile = json.loads(raw)
    tables = {name for name, row in profile['groups']['relations'].items() if row[1] in ('r', 'p')}
    base.require(tables == {'cp7_sku_conversion.' + name for name in TABLES}
                 and len(profile['groups']['functions']) == 10 and len(profile['replacement_functions']) == 9,
                 'GLOBAL_AUTOMATIC_EXACT_TWO_TABLE_TEN_PRIVATE_NINE_REPLACEMENT_PROFILE')
    expected, *_ = prior.expected_authority()
    base.require(not set(expected) & set(profile['replacement_functions']),
                 'GLOBAL_AUTOMATIC_EXISTING_NINETEEN_AUTHORITY_REFERENCES_MUST_BE_UNCHANGED')
    return profile, reference


def current_reference(catalog):
    prior.current_reference(catalog)
    profile, _ = sources()
    check_profile(catalog, profile)
    return dict(status='EXACT_AUTOMATIC_SOURCE_EXPECTATIONS_ONLY_NOT_ACTUAL_PARENT',
                private_functions=10, replacement_functions=9, actual_ERP_cases=0, runtime_admission=False)


def check_profile(catalog, profile):
    """Compare the complete prepared delta; this cannot admit a parent Root."""
    for signature, expected in (profile['groups']['functions'] | profile['replacement_functions']).items():
        base.require(len(expected) == 19 and catalog['functions'].get(signature) == expected,
                     'GLOBAL_AUTOMATIC_CURRENT_FULL19_FUNCTION_REQUIRED:' + signature)
    for group, entries in profile['groups'].items():
        if group == 'functions':
            continue
        base.require(group in catalog and type(catalog[group]) is dict,
                     'GLOBAL_AUTOMATIC_COMPLETE_PARENT_CATALOGUE_GROUP_REQUIRED:' + group)
        for name, expected in entries.items():
            base.require(catalog[group].get(name) == expected,
                         'GLOBAL_AUTOMATIC_CURRENT_COMPLETE_OBJECT_REQUIRED:' + group + ':' + name)


def derive():
    original, previous = prior.derive()
    profile, reference = sources()
    result = dict(original)
    routes = []

    def change(name, before, after, label):
        base.require(result[name].count(before) == 1 and after not in result[name],
                     'GLOBAL_AUTOMATIC_ONE_EXACT_OBSERVER_ROUTE_REQUIRED:' + label)
        result[name] = result[name].replace(before, after, 1)
        routes.append(dict(helper=name, before=before, after=after, label=label))

    edges = (HERE / 'automatic_edges.sql').read_text()
    base.require(edges.count('union select ') == 8, 'GLOBAL_AUTOMATIC_EXACT_EIGHT_TYPED_IDENTITY_EDGES')
    anchor = "  select 'LOT'::text,l.id,'PRODUCT'::text,l.product_id from erp.fg_lots l\n"
    change('scope', anchor, anchor + edges, 'automatic_typed_context_and_immutable_history')
    pairs = []
    for table in TABLES:
        pairs.append("'SKU_AUTOMATIC_" + table + "',coalesce((select jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text collate \"C\")"
            "from cp7_sku_conversion." + table + " t where exists(select 1 from domain d "
            "cross join lateral jsonb_array_elements(d.value->'identity_keys')i "
            "where (i->>'kind'in('CONVERSION','SKU_GROUP')and(i->>'id')::uuid=t.conversion_id)"
            "or(i->>'kind'='REWORK'and(i->>'id')::uuid=t.rework_id))),'[]')")
    anchor = "  'period',(select to_jsonb(c)from erp.accounting_period_control c where singleton_id=1))"
    change('capture', anchor, anchor + ' || jsonb_build_object(\n  ' + ',\n  '.join(pairs) + '\n )',
           'two_complete_automatic_rowsets_no_phase_or_value_projection')
    restored = dict(result)
    for route in reversed(routes):
        base.require(restored[route['helper']].count(route['after']) == 1, 'GLOBAL_AUTOMATIC_ONE_EXACT_INVERSE_ROUTE')
        restored[route['helper']] = restored[route['helper']].replace(route['after'], route['before'], 1)
    base.require(restored == original and result['authority'] == original['authority']
                 and result['inspect'] == original['inspect'], 'GLOBAL_AUTOMATIC_COMPLETE_PARENT_HELPERS_NOT_RECOVERED')
    return result, dict(status='GLOBAL_AUTOMATIC_COMPLETE_SOURCE_OBSERVATION_PREPARATION_NOT_INSTALLED',
                        source=reference, parent_helpers=previous['derived_helpers'],
                        derived_helpers={name: base.pin(text.encode()) for name, text in result.items()},
                        exact_routes=routes, new_full_rowsets=2, new_identity_edges=8,
                        all_columns_phases_times_JSON_and_multiplicity_retained=True,
                        old_nineteen_authority_and_inspector_and_Native_writers_unchanged=True,
                        actual_ERP_cases=0, runtime_admission=False, production_go=False, independent_acceptance=False)
