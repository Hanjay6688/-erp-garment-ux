"""Opt-in A composition stage. No connection, commit, default install or schedule."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_production_stage import _row,_body
import cp7_ow04_restore_bundle as catalog
from . import render

ROOT=Path(__file__).resolve().parent
USED_ERROR='BOUNDED_FINANCE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'


def sources():
    return {p.name:sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.iterdir())
        if p.is_file()and p.suffix in('.sql','.py','.json')}


def verify_sources():
    if (ROOT/'bridge.sql').read_text()!=render.render()or json.loads((ROOT/'MANIFEST.json').read_bytes())!=render.manifest():
        raise ValueError('BOUNDED_FINANCE_SOURCE_CHANGED')
    return sources()


def verify(cur,state):
    if state['sources']!=verify_sources()or catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('BOUNDED_FINANCE_FULL22_OR_SOURCE_CHANGED')
    for sig,row in state['rows'].items():
        if _row(cur,sig)!=row:raise ValueError('BOUNDED_FINANCE_FUNCTION_CHANGED: '+sig)
    old=state['original'];new=state['rows'][render.REQUEST]
    if new[2:]!=old[2:]:raise ValueError('BOUNDED_FINANCE_OPERATIONAL_AUTHORITY_CHANGED')
    for sig,definer in ((render.FINANCE,False),(render.PUBLIC,True)):
        if state['rows'][sig][2:6]!=['cp7_capture',definer,'v',['search_path=""','TimeZone=UTC']]:
            raise ValueError('BOUNDED_FINANCE_NEW_AUTHORITY_CHANGED: '+sig)
        for role in ('anon','authenticated','service_role'):
            actual=cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(role,sig)).fetchone()[0]
            if actual!=(sig==render.PUBLIC and role=='authenticated'):
                raise ValueError('BOUNDED_FINANCE_EXECUTE_CHANGED: '+sig+':'+role)
    return dict(stage='cp7.bounded-official-finance-route.v1',all22_exact=True,
        private1_public1_replacement1_tables0=True,official_finance_capture_reused=True,
        financial_math_added=False,production_go=False)


def admit_catalog(before,after,state):
    if set(before)!=set(after)or len(before)!=22:raise ValueError('BOUNDED_FINANCE_CATALOG_GROUPS_CHANGED')
    for group in before:
        for key in set(before[group])|set(after[group]):
            old,new=before[group].get(key),after[group].get(key)
            if old==new:continue
            if group=='functions'and key==render.REQUEST and old is not None and new is not None:
                if old[1:]==new[1:]and new==state['after'][group][key]:continue
            if group=='functions'and key in(render.FINANCE,render.PUBLIC)and old is None:
                if new==state['after'][group][key]:continue
            raise ValueError('BOUNDED_FINANCE_UNDECLARED_DELTA: '+group+':'+key)


def install_delta(cur,predecessor_checker):
    pins=verify_sources()
    if not callable(predecessor_checker):raise ValueError('BOUNDED_FINANCE_PREDECESSOR_REQUIRED')
    catalog._authority(cur)
    cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
    cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
    catalog._lock_tables(cur)
    predecessor_checker(cur)
    for sig in(render.FINANCE,render.PUBLIC):
        if cur.execute('select to_regprocedure(%s)is not null',(sig,)).fetchone()[0]:
            raise ValueError('BOUNDED_FINANCE_ALREADY_INSTALLED')
    old=_row(cur,render.REQUEST)
    if old[1]!=_body(render.original()):raise ValueError('BOUNDED_FINANCE_PREDECESSOR_BODY_CHANGED')
    # An unused composition stage must not invalidate a running bounded job.
    if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where state='RUNNING')").fetchone()[0]:
        raise ValueError('BOUNDED_FINANCE_QUIET_INSTALL_REQUIRED')
    before=catalog._catalog_rows(cur);data=catalog._data(cur)
    cur.execute('savepoint bounded_finance_install')
    try:
        cur.execute((ROOT/'bridge.sql').read_text(),prepare=False)
        rows={sig:_row(cur,sig)for sig in render.definitions()}
        for sig,body in render.definitions().items():
            if rows[sig][1]!=_body(body):raise ValueError('BOUNDED_FINANCE_INSTALLED_BODY_CHANGED: '+sig)
        state=dict(sources=pins,original=old,before=before,after=catalog._catalog_rows(cur),rows=rows,
            preuse_data_and_sequences=data)
        admit_catalog(before,state['after'],state)
        if catalog._data(cur)!=data:raise ValueError('BOUNDED_FINANCE_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
        verify(cur,state)
        return state
    except Exception:
        cur.execute('rollback to savepoint bounded_finance_install');raise
    finally:cur.execute('release savepoint bounded_finance_install')


def rollback_preuse(cur,state):
    catalog._authority(cur)
    cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
    cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
    verify(cur,state);catalog._lock_tables(cur)
    if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
    cur.execute('savepoint bounded_finance_inverse')
    try:
        cur.execute('drop function '+render.PUBLIC+' restrict')
        cur.execute('drop function '+render.FINANCE+' restrict')
        cur.execute(state['original'][0],prepare=False)
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['preuse_data_and_sequences']:
            raise ValueError('BOUNDED_FINANCE_INVERSE_NOT_EXACT')
    except Exception:
        cur.execute('rollback to savepoint bounded_finance_inverse');raise
    finally:cur.execute('release savepoint bounded_finance_inverse')
    return dict(status='EXACT_BOUNDED_FINANCE_PREUSE_INVERSE',all22_equal=True,
        all_rows_and_sequences_equal=True,global_used_guard_before_DDL=True,production_go=False)
