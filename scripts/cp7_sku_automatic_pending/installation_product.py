"""Exact incremental installation over the frozen money composition.

The model compiler builds the whole money successor. An installed money parent
already owns those tables and helpers: only the nine existing reader/writer
definitions and the new private admission objects belong to this delta.
"""
from hashlib import sha256
from pathlib import Path
import json
from cp7_sku_pending_accounting import derivation as accounting
from . import derivation, prepared_product

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCOPE = 'cp7_sku_conversion.cost_scope_value_v3(uuid,uuid,text)'
INPUT_FILES = (
    'scripts/cp7_sku_pending_accounting/derivation.py',
    'scripts/cp7_sku_automatic_pending/context.sql',
    'scripts/cp7_sku_automatic_pending/derivation.py',
    'scripts/cp7_sku_automatic_pending/prepared_product.py',
    'scripts/cp7_sku_automatic_pending/installation_product.py',
)


def pin(value):
    if isinstance(value, str):
        value = value.encode()
    return dict(bytes=len(value), sha256=sha256(value).hexdigest())


def derive(current_catalog, money_before, parent_originals):
    whole = prepared_product.derive(money_before, parent_originals)
    reader = accounting.derive()
    private = reader['ddl'] + '\n' + (HERE / 'context.sql').read_text()
    if not whole['ddl'].endswith(private):
        raise ValueError('AUTOMATIC_INCREMENTAL_EXACT_PRIVATE_SUFFIX_REQUIRED')
    scope = reader['definitions'][SCOPE]
    if reader['ddl'].count(scope) != 1:
        raise ValueError('AUTOMATIC_INCREMENTAL_EXACT_ACCOUNTING_SCOPE_REQUIRED')
    ddl = reader['ddl'].replace(scope, '', 1) + '\n' + (HERE / 'context.sql').read_text()
    definitions = {SCOPE: scope}
    for name in derivation.PINS:
        keys = [sig for sig in whole['definitions'] if sig.split('(')[0] == name]
        if len(keys) != 1:
            raise ValueError('AUTOMATIC_INCREMENTAL_EXACT_SIGNATURE_REQUIRED:' + name)
        definitions[keys[0]] = whole['definitions'][keys[0]]
    money = json.loads((HERE.parent / 'cp7_sku_cost_components/CATALOG_ADDITIONS.json').read_bytes())
    expected = dict(money_before['functions']) | money['groups']['functions'] | money['replacement_functions']
    for sig in definitions:
        if current_catalog['functions'].get(sig) != expected.get(sig) or sig not in expected:
            raise ValueError('AUTOMATIC_INCREMENTAL_FROZEN_MONEY_ROW_REQUIRED:' + sig)
    return dict(ddl=ddl, definitions=definitions,
                replacement_before={sig: expected[sig] for sig in definitions},
                source_files={name: pin((ROOT / name).read_bytes()) for name in INPUT_FILES},
                whole_product=pin(json.dumps(whole, sort_keys=True) + '\n'),
                original_money_product_preserved=True, actual_ERP_cases=0,
                production_go=False, independent_acceptance=False)
