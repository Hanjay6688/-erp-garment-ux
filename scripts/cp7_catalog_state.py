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

def preservation_controls(raw):
    """Read-only sensitivity controls derived from the observed full catalog.

    These copies never enter a database. Only pair order may compare equal;
    changing a signature/hash/member, relation or row observation must fail.
    """
    original=deepcopy(raw)
    baseline=canonical_public_state(raw)
    assert baseline['functions'], 'CP7_CATALOG_FUNCTION_MEMBERS_REQUIRED'
    reordered=deepcopy(raw)
    reordered['functions']=list(reversed(reordered['functions']))
    controls=dict(pair_order_only_equal=canonical_public_state(reordered)==baseline)
    candidates={}
    changed=deepcopy(raw);changed['functions'][0][1]+=':CHANGED'
    candidates['function_hash_change_refused']=changed
    changed=deepcopy(raw);changed['functions'][0][0]+=':CHANGED'
    candidates['function_signature_change_refused']=changed
    changed=deepcopy(raw);changed['functions'].pop(0)
    candidates['missing_function_member_refused']=changed
    changed=deepcopy(raw);changed['functions'].append(deepcopy(changed['functions'][0]))
    candidates['duplicate_function_member_refused']=changed
    changed=deepcopy(raw);changed['relations'].append(['__sensitivity_only__','r'])
    candidates['relation_member_change_refused']=changed
    changed=deepcopy(raw);key=next(iter(changed['rows']), '__sensitivity_only__')
    changed['rows'][key]=str(changed['rows'].get(key,''))+':CHANGED'
    candidates['public_row_hash_or_member_change_refused']=changed
    for name,changed in candidates.items():
        controls[name]=canonical_public_state(changed)!=baseline
    controls['observed_input_not_mutated']=raw==original
    assert all(controls.values()), ('CP7_CATALOG_PRESERVATION_CONTROL_FAILED',controls)
    return controls

@contextmanager
def exact_public_catalog(runner,retain_raw=False):
    original=runner.public_state
    audit=dict(policy='ALL_ORIGINAL_FIELDS_AND_FUNCTION_SIGNATURE_HASH_PAIRS_EXACT_SORTED',dropped_fields=[],physical_order_only_changes=[])
    if retain_raw:
        audit['raw_snapshots']=[]
    previous=None
    count=0
    def read(cur):
        nonlocal previous,count
        raw=original(cur);state=canonical_public_state(raw);count+=1
        fingerprint=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if retain_raw:
            if count==1:
                audit['read_only_preservation_controls']=preservation_controls(raw)
            audit['raw_snapshots'].append(dict(snapshot=count,raw=deepcopy(raw),exact_canonical_state_sha256=fingerprint(state)))
        if previous is not None and previous[1]==state and previous[0]['functions']!=raw['functions']:
            audit['physical_order_only_changes'].append(dict(before_snapshot=count-1,after_snapshot=count,exact_canonical_state_sha256=fingerprint(state),before_order_sha256=fingerprint(previous[0]['functions']),after_order_sha256=fingerprint(raw['functions'])))
        previous=(deepcopy(raw),state)
        return state
    runner.public_state=read
    try:
        yield audit
    finally:
        runner.public_state=original
        audit['snapshots_checked']=count
