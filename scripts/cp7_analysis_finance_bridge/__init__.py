"""B consumer stage for A's finance capture. A owns full-chain installation."""
from hashlib import sha256
from pathlib import Path
import json
import re
from cp7_production_stage import _row, _body
from . import patches

ROOT = Path(__file__).resolve().parent
SCHEMA = 'cp7_analysis_finance'
READER = 'cp7_analysis_finance.status(uuid)'
DEPENDENCIES = ('cp7_finance_capture.start(text,uuid,jsonb,timestamp with time zone)',
                'cp7_finance_capture.status_of(text,uuid)', 'cp7_finance_capture.result(uuid)')
BEFORE = json.loads((ROOT/'BEFORE.json').read_text())


def sources():
    return {p.name:sha256(p.read_bytes()).hexdigest()for p in ROOT.iterdir()if p.is_file()and p.suffix in('.sql','.py','.json')}


def _new_catalog(cur):
    from cp7_ow04_restore_bundle import QUERIES, _catalog
    with _catalog(cur):
        return {group:dict(cur.execute(QUERIES[group]+' and n.nspname=%s',(SCHEMA,)).fetchall())
                for group in ('schemas','functions')}


def verify(cur, state):
    if sources()!=state['sources']:
        raise ValueError('OW12B_CALLER_SOURCE_CHANGED')
    for sig in patches.SIGNATURES:
        r=_row(cur,sig)
        if r[0]!=state['definitions'][sig]or r[2:]!=state['originals'][sig][2:]:
            raise ValueError('OW12B_CALLER_OR_AUTHORITY_CHANGED: '+sig)
    r=_row(cur,READER)
    text=(ROOT/'consumer.sql').read_text()
    expected=re.search(r'as\s*\$\$(.*?)\$\$;',text,re.S|re.I)[1]
    if r!=state['reader']or r[1]!=expected or r[2:6]!=['cp7_capture',False,'s',['search_path=""','TimeZone=UTC']]:
        raise ValueError('OW12B_PRIVATE_READER_CHANGED')
    catalog=_new_catalog(cur)
    if catalog!=state['new_catalog']or set(catalog['schemas'])!={SCHEMA}or set(catalog['functions'])!={READER}:
        raise ValueError('OW12B_PRIVATE_CATALOG_CHANGED')
    for group,key in (('schemas',SCHEMA),('functions',READER)):
        row=catalog[group][key]
        if row[0 if group=='schemas'else 1]!='cp7_capture'or any(acl[0]!='cp7_capture'or acl[1]!='cp7_capture'or acl[3]for acl in row[-1]):
            raise ValueError('OW12B_PRIVATE_AUTHORITY_CHANGED')
    for role in ('anon','authenticated','service_role'):
        if cur.execute("select has_schema_privilege(%s,%s,'USAGE')or has_function_privilege(%s,%s,'EXECUTE')",(role,SCHEMA,role,READER)).fetchone()[0]:
            raise ValueError('OW12B_PRIVATE_READER_EXPOSED')
    return dict(stage='cp7.analysis-finance-consumer.v1',official_source='cp7.finance-capture.v1',
                financial_math_added=False, sealed_operational_header_changed=False, full_chain_qualified=False,production_go=False)


def install_delta(cur):
    # Called in A's atomic, envelope-locked composition. No connection/commit.
    for sig in DEPENDENCIES:
        if cur.execute('select to_regprocedure(%s)is null',(sig,)).fetchone()[0]:
            raise ValueError('OW12B_REQUIRES_A_FINANCE_CAPTURE: '+sig)
    if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
        raise ValueError('OW12B_CALLER_ALREADY_INSTALLED')
    original={sig:_row(cur,sig)for sig in patches.SIGNATURES}
    for sig,row in original.items():
        if sha256(row[1].encode()).hexdigest()!=BEFORE[sig]:
            raise ValueError('OW12B_CALLER_PREDECESSOR_CHANGED: '+sig)
    definitions=patches.patched({sig:r[0]for sig,r in original.items()})
    cur.execute((ROOT/'consumer.sql').read_text(),prepare=False)
    for definition in definitions.values():
        cur.execute(definition,prepare=False)
    # pg_get_functiondef is the canonical installed representation for later
    # comparisons; the anchored replacement source itself is kept separately.
    state=dict(sources=sources(),originals=original,patches=definitions,reader=_row(cur,READER),new_catalog=_new_catalog(cur),
               definitions={sig:_row(cur,sig)[0]for sig in patches.SIGNATURES})
    verify(cur,state)
    return state


def admit_catalog(before,after,state):
    if set(before)!=set(after)or len(before)!=22:
        raise ValueError('OW12B_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:
                continue
            if group=='functions'and key in patches.SIGNATURES and old is not None and new is not None:
                if new[0]==state['definitions'][key]and old[0]==state['originals'][key][0]and old[1:]==new[1:]:
                    continue
            if old is None and new is not None and new==state['new_catalog'].get(group,{}).get(key):
                continue
            raise ValueError('OW12B_UNDECLARED_CATALOG_DELTA: '+group+':'+key)


def rollback_preuse(cur,state):
    verify(cur,state)
    if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where reference->>'finance_sidecar_mode'='STAGED')").fetchone()[0]:
        raise ValueError('OW12B_AFTER_USE_REQUIRES_BACKUP_RESTORE')
    for sig in reversed(patches.SIGNATURES):
        cur.execute(state['originals'][sig][0],prepare=False)
    cur.execute('drop function cp7_analysis_finance.status(uuid);drop schema cp7_analysis_finance',prepare=False)
    for sig,row in state['originals'].items():
        if _row(cur,sig)!=row:
            raise ValueError('OW12B_CALLER_NOT_RESTORED: '+sig)
