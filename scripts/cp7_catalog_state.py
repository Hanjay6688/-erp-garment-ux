"""Compare every public catalog member while removing only physical row order.

The frozen CP6 reader aggregates function pairs ORDER BY 1, a constant inside
jsonb_agg. Keep the frozen reader/runner untouched and bind this adapter only
around the CP7 qualification group. No field, member, hash, ACL or row is removed.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib,json

def canonical_public_state(raw):
    state=deepcopy(raw)
    state['functions']=sorted(state['functions'])
    return state

@contextmanager
def exact_public_catalog(runner):
    original=runner.public_state
    audit=dict(policy='ALL_ORIGINAL_FIELDS_AND_FUNCTION_SIGNATURE_HASH_PAIRS_EXACT_SORTED',dropped_fields=[],physical_order_only_changes=[])
    previous=None
    count=0
    def read(cur):
        nonlocal previous,count
        raw=original(cur);state=canonical_public_state(raw);count+=1
        if previous is not None and previous[1]==state and previous[0]['functions']!=raw['functions']:
            fingerprint=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            audit['physical_order_only_changes'].append(dict(before_snapshot=count-1,after_snapshot=count,exact_canonical_state_sha256=fingerprint(state),before_order_sha256=fingerprint(previous[0]['functions']),after_order_sha256=fingerprint(raw['functions'])))
        previous=(deepcopy(raw),state)
        return state
    runner.public_state=read
    try:
        yield audit
    finally:
        runner.public_state=original
        audit['snapshots_checked']=count
