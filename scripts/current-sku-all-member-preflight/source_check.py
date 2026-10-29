"""Exact one-function product transition and retained local proof admission."""
from pathlib import Path
from hashlib import sha256
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def source_only():
    source = json.loads((HERE / 'SOURCE.json').read_bytes())
    for name, pin in source['files'].items():
        raw = (ROOT / name).read_bytes()
        assert len(raw) == pin['bytes'] and sha256(raw).hexdigest() == pin['sha256'], 'SKU_PREFLIGHT_SOURCE_CHANGED:' + name
    before = (HERE / 'evidence/BEFORE_conversion.sql').read_text()
    after = (ROOT / 'scripts/cp7_sku_pair_conversion/conversion.sql').read_text()
    start = after.index('  -- Validate every member before invoking any Native inverse.')
    end = after.index("  insert into cp7_sku_conversion.execution_v1(backend_pid,transaction_id,group_id,mode)values(pg_backend_pid(),txid_current(),v_group_id,'REVERSE');", start)
    added = after[start:end]
    assert sha256(added.encode()).hexdigest() == source['added_block_sha256']
    assert after[:start] + after[end:] == before, 'SKU_PREFLIGHT_OTHER_PRODUCT_TEXT_CHANGED'
    local = json.loads((HERE / 'evidence/LOCAL_GUARD.json').read_bytes())
    assert local['status'] == 'PASS' and local['count'] == 10
    assert local['source']['conversion'] == sha256(after.encode()).hexdigest()
    assert local['source']['before_conversion'] == sha256(before.encode()).hexdigest()
    assert local['proof_kind'] == 'PGLITE_DECLARED_LOCAL_DOUBLES_NOT_NATIVE_MONEY_AUTH_OR_FULL_RESTORE'
    assert source['actual_Native_credit'] == 0
    return dict(status='EXACT_ONE_FUNCTION_PREFLIGHT_TRANSITION', files=len(source['files']), local_checks=10,
                actual_Native_credit=0, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    print(json.dumps(source_only(), sort_keys=True))
