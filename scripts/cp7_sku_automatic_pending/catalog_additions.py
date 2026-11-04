"""Closed all22 catalogue transition; no observed-name or prefix admission."""
from pathlib import Path
import json
import re
from cp7_sku_cost_components.catalog_additions import GROUPS, transition as exact_transition
from .installation_product import pin

HERE = Path(__file__).resolve().parent
COUNTS = dict(columns=26, constraints=14, functions=10, indexes=2, relations=4,
              triggers=33, type_implementation=4, types=4)


def expected(product):
    profile = json.loads((HERE / 'CATALOG_ADDITIONS.json').read_bytes())
    if (profile['contract'] != 'cp7.sku-automatic-pending-catalogue-additions.v1'
            or profile['classification'] != 'EXPECTED_POSTGRES17_DDL_ONLY_NOT_ERP_QUALIFICATION'
            or not profile['engine'].startswith('PostgreSQL 17.')
            or profile['actual_ERP_cases'] != 0 or profile['financial_functions_executed'] != 0
            or profile['production_go'] is not False or profile['independent_acceptance'] is not False
            or profile.get('installer') != dict(name='postgres', rolsuper=False)
            or profile['explicit_unused_inverse_all22_exact'] is not True):
        raise ValueError('AUTOMATIC_DDL_PROFILE_CONTRACT_CHANGED')
    if (set(profile['groups']) != set(GROUPS)
            or {g: len(rows) for g, rows in profile['groups'].items() if rows} != COUNTS):
        raise ValueError('AUTOMATIC_ALL22_PROFILE_REQUIRED')
    if profile['catalog_source_sha256'] != pin((HERE.parent / 'cp7_ow04_restore_bundle.py').read_bytes())['sha256']:
        raise ValueError('AUTOMATIC_CATALOG_QUERIES_CHANGED')
    if profile['source_files'] != product['source_files'] or profile['derived_ddl'] != pin(product['ddl']):
        raise ValueError('AUTOMATIC_DDL_PRODUCT_CHANGED')
    if profile['derived_replacements'] != {sig: pin(body) for sig, body in product['definitions'].items()}:
        raise ValueError('AUTOMATIC_REPLACEMENT_SOURCE_CHANGED')
    if profile['replacement_before'] != product['replacement_before']:
        raise ValueError('AUTOMATIC_EXACT_MONEY_PREDECESSOR_CHANGED')
    if set(profile['replacement_functions']) != set(product['definitions']) or len(product['definitions']) != 9:
        raise ValueError('AUTOMATIC_NINE_REPLACEMENTS_REQUIRED')
    for sig, row in profile['replacement_functions'].items():
        if row[1:] != profile['replacement_before'][sig][1:]:
            raise ValueError('AUTOMATIC_EXISTING_FUNCTION_AUTHORITY_CHANGED:' + sig)
    tables = tuple(re.findall(r'^create table ([\w.]+)\(', product['ddl'], re.M))
    if set(tables) != {'cp7_sku_conversion.automatic_context_v5', 'cp7_sku_conversion.automatic_admissions_v5'}:
        raise ValueError('AUTOMATIC_TWO_PRIVATE_TABLES_REQUIRED')
    if set(tables) != {k for k, row in profile['groups']['relations'].items() if row[1] == 'r'}:
        raise ValueError('AUTOMATIC_EXACT_PRIVATE_RELATIONS_REQUIRED')
    if len(profile['groups']['functions']) != 10:
        raise ValueError('AUTOMATIC_TEN_PRIVATE_HELPERS_REQUIRED')
    for sig, row in profile['groups']['functions'].items():
        if (row[1] != 'postgres' or row[4] is not True or row[12] != ['search_path=""']
                or row[18] != [['postgres', 'postgres', 'EXECUTE', False]]):
            raise ValueError('AUTOMATIC_PRIVATE_HELPER_AUTHORITY_CHANGED:' + sig)
    for table in tables:
        row = profile['groups']['relations'][table]
        if row[0] != 'postgres' or row[3] is not True:
            raise ValueError('AUTOMATIC_PRIVATE_TABLE_AUTHORITY_CHANGED:' + table)
    return profile, tables


def transition(before, after, profile):
    # This frozen checker compares every row in all22 groups and all function
    # attributes. Sharing it does not amend the parent's source or old proofs.
    return exact_transition(before, after, profile)
