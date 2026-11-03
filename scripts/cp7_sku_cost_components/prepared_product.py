"""One deterministic definition set over the exact moving-average parent.

No database, installer or acceptance is invoked by deriving these definitions.
The caller must supply the parent's frozen original definitions and current
catalogue. Every original-source guard remains in its owning derivation.
"""
from hashlib import sha256
from pathlib import Path
import json
from . import valuation_delta,financial_delta,source_delta,money_delta,base_money_delta,private_inverse_delta,legacy_delta

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'cp7_sku_moving_average'
SQL_FILES=('costs.sql','inverse_rebalance.sql','source_rebalance.sql','money.sql','base_money.sql','legacy.sql')


def parent_original_signatures():
    return tuple(dict.fromkeys(sig for name in('consumer_delta.py','credit_delta.py','private_delta.py')
        for sig in financial_delta.parent(name).SIGNATURES))


def derive(current_catalog,parent_originals):
    required=parent_original_signatures()
    if set(parent_originals)!=set(required):raise ValueError('SKU_MONEY_EXACT_PARENT_ORIGINALS_REQUIRED')
    consumers,consumer_routes=financial_delta.derive_consumers({sig:parent_originals[sig]for sig in financial_delta.parent('consumer_delta.py').SIGNATURES})
    credit,credit_routes=financial_delta.derive_credit({sig:parent_originals[sig]for sig in financial_delta.parent('credit_delta.py').SIGNATURES})
    valuation,valuation_routes=valuation_delta.derive()
    private,private_routes=private_inverse_delta.derive({sig:parent_originals[sig]for sig in financial_delta.parent('private_delta.py').SIGNATURES})
    source,source_routes=source_delta.derive(current_catalog['functions'][source_delta.SIGNATURE][0])
    money,valuation,money_routes=money_delta.definitions(valuation)
    credit,money_credit_routes=money_delta.credit_definitions(credit)
    valuation,consumers,credit,base_routes=base_money_delta.definitions(valuation,consumers,credit)
    legacy,legacy_routes=legacy_delta.derive(current_catalog,private)
    parent_profile=json.loads((PARENT/'CATALOG_ADDITIONS.json').read_bytes())['groups']['functions']
    definitions=dict(consumers)|dict(credit)|{private_inverse_delta.SIGNATURE:private,source_delta.SIGNATURE:source}
    for name,definition in valuation.items():
        keys=[sig for sig in parent_profile if sig.startswith(name+'(')]
        if len(keys)!=1:raise ValueError('SKU_MONEY_EXACT_PARENT_SIGNATURE_REQUIRED:'+name)
        definitions[keys[0]]=definition
    definitions.update(legacy)
    ddl='\n'.join((HERE/name).read_text()for name in SQL_FILES[:4])+'\n'+'\n'.join(money.values())+'\n'+(HERE/SQL_FILES[4]).read_text()
    ddl=legacy_delta.bind_base_transition(ddl)+'\n'+(HERE/SQL_FILES[5]).read_text()
    return dict(ddl=ddl,definitions=definitions,derivations=dict(consumer=consumer_routes,credit=credit_routes,
        valuation=valuation_routes,private=private_routes,source=source_routes,money=money_routes,money_credit=money_credit_routes,base=base_routes,legacy=legacy_routes),
        source_files={name:dict(bytes=len((HERE/name).read_bytes()),sha256=sha256((HERE/name).read_bytes()).hexdigest())for name in SQL_FILES})
