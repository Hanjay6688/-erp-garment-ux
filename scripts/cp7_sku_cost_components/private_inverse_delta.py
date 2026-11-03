"""Retain the complete private/Native command and check economic custody first."""
from hashlib import sha256
try:
    from .valuation_delta import Derivation
    from .financial_delta import parent
except ImportError:
    from valuation_delta import Derivation
    from financial_delta import parent

SIGNATURE='cp7_sku_conversion.action_v1(text,jsonb,uuid)'
ORIGINAL_SHA256='93474ab10fcbcfe9913171790762377fad75c301611a65cb1897225a4f5824c9'


def derive(originals):
    if sha256(originals[SIGNATURE].encode()).hexdigest()!=ORIGINAL_SHA256:
        raise ValueError('SKU_COST_ORIGINAL_PRIVATE_ACTION_CHANGED')
    predecessor=parent('private_delta.py').patched(originals)[SIGNATURE]
    d=Derivation(predecessor)
    original="  insert into cp7_sku_conversion.execution_v1(backend_pid,transaction_id,group_id,mode)values(pg_backend_pid(),txid_current(),v_group_id,'REVERSE');"
    d.once(original,"  perform cp7_sku_conversion.assert_group_inverse_capacity_v3(v_group_id);\n"+original,
           'economic capacity after unchanged Native preconditions and before every Native child inverse')
    if d.inverse()!=predecessor:raise ValueError('SKU_COST_PRIVATE_INVERSE_NOT_REVERSIBLE')
    return d.source,[r[2]for r in d.routes]
