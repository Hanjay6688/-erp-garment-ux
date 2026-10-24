"""Exact one-function successor of the qualified analog provenance overlay."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_production_stage import _row,_body
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_product_analog_provenance_stage as parent
from . import render

ROOT=Path(__file__).resolve().parent
SIGNATURE=render.SIGNATURE


def sources():
    return {p.name:sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.iterdir())if p.is_file()and p.suffix in('.sql','.py','.json')}


def verify_sources():
    parent.verify_sources()
    if (ROOT/'reader.sql').read_text()!=render.replacement()or json.loads((ROOT/'MANIFEST.json').read_text())!=render.manifest():
        raise ValueError('BASELINE_FRESHNESS_SOURCE_CHANGED')
    return sources()


def own_catalog(catalog):
    return {g:{k:v for k,v in rows.items()if g=='functions'and k==SIGNATURE}for g,rows in catalog.items()}


def verify(cur,state):
    if verify_sources()!=state['sources']or own_catalog(_catalog_rows(cur))!=state['catalog']:
        raise ValueError('BASELINE_FRESHNESS_SOURCE_OR_CATALOG_CHANGED')
    if _row(cur,SIGNATURE)!=state['new_row']or state['new_row'][2:]!=state['old_row'][2:]:
        raise ValueError('BASELINE_FRESHNESS_AUTHORITY_CHANGED')
    for sig,row in state['dependencies'].items():
        if _row(cur,sig)!=row:raise ValueError('BASELINE_FRESHNESS_DEPENDENCY_CHANGED: '+sig)
    return dict(stage='cp7.baseline-freshness-stage.v1',existing_replacements=1,
      new_private_functions=0,new_public_rpcs=0,new_tables=0,Native_ERP_DML=False,
      old_immutable_results_rewritten=False,production_go=False)


def install_delta(cur,predecessor_checker):
    pins=verify_sources()
    if not callable(predecessor_checker):raise ValueError('BASELINE_FRESHNESS_PREDECESSOR_REQUIRED')
    predecessor_checker(cur)
    if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where state='RUNNING')").fetchone()[0]:
        raise ValueError('BASELINE_FRESHNESS_QUIET_INSTALL_REQUIRED')
    before=_catalog_rows(cur);old=_row(cur,SIGNATURE)
    if old[1]!=_body(render.original())or old[2]!='cp7_capture':raise ValueError('BASELINE_FRESHNESS_PREDECESSOR_CHANGED')
    signatures=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname like 'cp7_%'and p.prokind='f'order by 1").fetchall()
    dependencies={sig:_row(cur,sig)for(sig,)in signatures if sig!=SIGNATURE}
    used=parent.consumer.usage_state(cur)
    cur.execute((ROOT/'reader.sql').read_text(),prepare=False);new=_row(cur,SIGNATURE)
    if new[1]!=_body(render.replacement()):raise ValueError('BASELINE_FRESHNESS_WRONG_BODY')
    after=_catalog_rows(cur);catalog=own_catalog(after)
    if set(before)!=set(after)or len(before)!=22:raise ValueError('BASELINE_FRESHNESS_CATALOG_GROUPS')
    for group in before:
        for key in set(before[group])|set(after[group]):
            a,b=before[group].get(key),after[group].get(key)
            if a==b:continue
            if group=='functions'and key==SIGNATURE and a is not None and b==catalog[group].get(key):continue
            raise ValueError('BASELINE_FRESHNESS_UNDECLARED_DELTA: '+group+':'+key)
    state=dict(sources=pins,old_row=old,new_row=new,dependencies=dependencies,usage_before=used,catalog=catalog)
    verify(cur,state);return state


def rollback_preuse(cur,state):
    verify(cur,state)
    if parent.consumer.usage_state(cur)!=state['usage_before']:
        raise ValueError('BASELINE_FRESHNESS_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE')
    cur.execute(state['old_row'][0],prepare=False)
