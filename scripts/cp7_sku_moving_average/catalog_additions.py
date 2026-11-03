"""Exact PostgreSQL 17 DDL additions, never an ERP qualification result.

The profile was produced by the unchanged valuation.sql and original all-22
catalogue queries against an empty, isolated PostgreSQL 17 engine. Minimal
referenced tables supply UUID primary keys only. No financial function ran.
Runtime installation must match every row, including implicit indexes, row
types and both ends of foreign-key triggers; name prefixes admit nothing.
"""
from hashlib import sha256
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
GROUPS = (
    'schemas', 'relations', 'columns', 'constraints', 'indexes', 'triggers',
    'functions', 'aggregates', 'types', 'enums', 'sequences', 'policies',
    'extensions', 'roles', 'memberships', 'event_triggers', 'rules',
    'inheritance', 'default_privileges', 'database_authority',
    'type_implementation', 'sequence_ownership',
)
COUNTS = dict(relations=31, columns=183, constraints=132, indexes=19,
              triggers=202, functions=13, types=24, policies=12,
              type_implementation=24)


def expected():
    profile = json.loads((HERE / 'CATALOG_ADDITIONS.json').read_bytes())
    if (profile['contract'] != 'cp7.sku-moving-average-catalogue-additions.v1'
            or profile['classification'] != 'EXPECTED_POSTGRES17_DDL_ONLY_NOT_ERP_QUALIFICATION'
            or profile['actual_Native_cases'] != 0
            or profile['production_go'] is not False
            or profile['independent_acceptance'] is not False
            or not profile['derived_with']['engine'].startswith('PostgreSQL 17.')
            or profile['derived_with']['financial_functions_executed'] != 0):
        raise ValueError('SKU_MOVAVG_CATALOG_PROFILE_CONTRACT_CHANGED')
    raw = (HERE / 'valuation.sql').read_bytes()
    if profile['valuation_source'] != dict(bytes=len(raw), sha256=sha256(raw).hexdigest()):
        raise ValueError('SKU_MOVAVG_CATALOG_DDL_SOURCE_CHANGED')
    catalog = HERE.parent / 'cp7_ow04_restore_bundle.py'
    if sha256(catalog.read_bytes()).hexdigest() != profile['catalogue_source_sha256']:
        raise ValueError('SKU_MOVAVG_CATALOG_QUERIES_CHANGED')
    additions = profile['groups']
    if {group: len(rows) for group, rows in additions.items()} != COUNTS:
        raise ValueError('SKU_MOVAVG_CATALOG_PROFILE_INCOMPLETE')
    return {group: additions.get(group, {}) for group in GROUPS}
