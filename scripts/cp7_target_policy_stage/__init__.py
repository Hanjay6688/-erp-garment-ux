"""Four B-owned body replacements above cp7_production_stage; A composes."""
from hashlib import sha256
from pathlib import Path
import json
from cp7_production_stage import _row, _body

ROOT=Path(__file__).resolve().parent
MANIFEST=json.loads((ROOT/'MANIFEST.json').read_text())


def sources():
    return {str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.rglob('*'))if p.is_file()and p.suffix in('.sql','.py','.json')}


def verify_sources():
    for sig,item in MANIFEST.items():
        for direction in ('forward','inverse'):
            raw=(ROOT/'sql'/item[direction]).read_bytes()
            if sha256(raw).hexdigest()!=item[direction+'_sha256']:
                raise ValueError('OW10_TARGET_POLICY_SOURCE_CHANGED: '+sig)
    return sources()


def verify(cur,state):
    if verify_sources()!=state['sources']:
        raise ValueError('OW10_TARGET_POLICY_SOURCE_CHANGED')
    for sig,item in MANIFEST.items():
        row=_row(cur,sig)
        if row[0]!=state['definitions'][sig]or row[2:]!=state['originals'][sig][2:]or sha256(row[1].encode()).hexdigest()!=item['after_body_sha256']:
            raise ValueError('OW10_TARGET_POLICY_BODY_OR_AUTHORITY_CHANGED: '+sig)
    return dict(stage='cp7.target-policy.v1',changed_functions=4,new_objects=0,
                legacy_payloads_preserved=True,full_chain_qualified=False,production_go=False)


def install_delta(cur):
    pins=verify_sources()
    original={sig:_row(cur,sig)for sig in MANIFEST}
    for sig,item in MANIFEST.items():
        if sha256(original[sig][1].encode()).hexdigest()!=item['before_body_sha256']:
            raise ValueError('OW10_TARGET_POLICY_PREDECESSOR_CHANGED: '+sig)
    for item in MANIFEST.values():
        cur.execute((ROOT/'sql'/item['forward']).read_text(),prepare=False)
    state=dict(sources=pins,originals=original,
               definitions={sig:_row(cur,sig)[0]for sig in MANIFEST})
    verify(cur,state)
    return state


def admit_catalog(before,after,state):
    if set(before)!=set(after)or len(before)!=22:
        raise ValueError('OW10_TARGET_POLICY_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:
                continue
            if group=='functions'and key in MANIFEST and old is not None and new is not None:
                if old[0]==state['originals'][key][0]and new[0]==state['definitions'][key]and old[1:]==new[1:]:
                    continue
            raise ValueError('OW10_TARGET_POLICY_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def rollback_preuse(cur,state):
    # A supplies the enclosing transaction, envelope lock and global use guard.
    verify(cur,state)
    if cur.execute("select exists(select 1 from cp7_profile.profiles where config?'buffer_mode')").fetchone()[0]:
        raise ValueError('OW10_TARGET_POLICY_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    for sig in reversed(MANIFEST):
        cur.execute(state['originals'][sig][0],prepare=False)
    for sig,row in state['originals'].items():
        if _row(cur,sig)!=row:
            raise ValueError('OW10_TARGET_POLICY_NOT_RESTORED: '+sig)
