"""A-owned opt-in public delta on the exact full private-finance predecessor."""
from hashlib import sha256
from pathlib import Path
import json
from cp7_production_stage import _row,_body
import cp7_current_frozen_finance_installation as parent
from . import render

ROOT=Path(__file__).resolve().parent
CONTRACT='cp7.current-frozen-public-official-finance.v1'
USED_ERROR='CURRENT_FROZEN_PUBLIC_DELTA_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
catalog,atomic=parent.catalog,parent.atomic


def sources():
    return dict(contract=CONTRACT,files={p.name:sha256(p.read_bytes()).hexdigest()
        for p in sorted(ROOT.iterdir())if p.is_file()and p.suffix in('.py','.sql','.json')})


def verify_sources():
    if ((ROOT/'bridge.sql').read_text()!=render.render()
            or json.loads((ROOT/'MANIFEST.json').read_bytes())!=render.manifest()):
        raise ValueError('CURRENT_FROZEN_PUBLIC_GENERATED_SOURCE_CHANGED')
    return sources()


def admit_catalog(before,after):
    if set(before)!=set(after)or len(before)!=22:
        raise ValueError('CURRENT_FROZEN_PUBLIC_FULL22_REQUIRED')
    changed=set()
    for group in before:
        for key in set(before[group])|set(after[group]):
            left,right=before[group].get(key),after[group].get(key)
            if left==right:continue
            changed.add((group,key))
            if group=='functions'and key in render.definitions()and left is None and right is not None:
                continue
            raise ValueError('CURRENT_FROZEN_PUBLIC_UNDECLARED_DELTA:'+group+':'+key)
    if changed!={('functions',key)for key in render.definitions()}:
        raise ValueError('CURRENT_FROZEN_PUBLIC_INCOMPLETE_DELTA')


def verify(cur,state):
    catalog._authority(cur)
    if state['sources']!=verify_sources()or catalog._catalog_rows(cur)!=state['after']:
        raise ValueError('CURRENT_FROZEN_PUBLIC_SOURCE_OR_FULL22_CHANGED')
    definitions=render.definitions()
    if set(state['rows'])!=set(definitions):
        raise ValueError('CURRENT_FROZEN_PUBLIC_FUNCTION_SET_CHANGED')
    admit_catalog(state['before'],state['after'])
    grants={('cp7_capture','cp7_capture','EXECUTE',False),('authenticated','cp7_capture','EXECUTE',False)}
    for signature,definition in definitions.items():
        row=_row(cur,signature)
        if (row!=state['rows'][signature]or row[1]!=_body(definition)
                or row[0]!=state['after']['functions'][signature][0]
                or row[2:6]!=['cp7_capture',True,'v',['search_path=""','TimeZone=UTC']]):
            raise ValueError('CURRENT_FROZEN_PUBLIC_FUNCTION_OR_AUTHORITY_CHANGED:'+signature)
        acl=state['after']['functions'][signature][-1]
        if (not isinstance(acl,list)or len(acl)!=len(grants)
                or any(not isinstance(x,list)or len(x)!=4 or x[3]is not False for x in acl)
                or {tuple(x)for x in acl}!=grants):
            raise ValueError('CURRENT_FROZEN_PUBLIC_GRANTS_CHANGED:'+signature)
        for role in('anon','authenticated','service_role','cp7_alert'):
            allowed=cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',(role,signature)).fetchone()[0]
            if allowed is not(role=='authenticated'):
                raise ValueError('CURRENT_FROZEN_PUBLIC_EXECUTE_CHANGED:'+signature+':'+role)
    if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
        raise ValueError('CURRENT_FROZEN_PUBLIC_OWNER_CREATE_OPEN')
    return dict(contract=CONTRACT,exact_full22=True,new_public_rpcs=2,new_tables=0,
        existing_replacements=0,authenticated_execute_only=True,financial_math_added=False,
        actual_Auth_HTTP_credit=False,default_adopted=False,production_go=False)


def _locks(cur):
    catalog._authority(cur)
    cur.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OW15:COMPOSITION',0))")
    cur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
    catalog._lock_tables(cur)


def install_delta(cur,predecessor_checker):
    if not callable(predecessor_checker):
        raise ValueError('CURRENT_FROZEN_PUBLIC_ACTUAL_PREDECESSOR_REQUIRED')
    with atomic(cur):
        _locks(cur);predecessor_checker(cur);pins=verify_sources()
        for signature in render.definitions():
            if cur.execute('select to_regprocedure(%s)is not null',(signature,)).fetchone()[0]:
                raise ValueError('CURRENT_FROZEN_PUBLIC_ALREADY_INSTALLED:'+signature)
        before,data=catalog._catalog_rows(cur),catalog._data(cur)
        cur.execute((ROOT/'bridge.sql').read_text(),prepare=False)
        state=dict(sources=pins,before=before,after=catalog._catalog_rows(cur),
            rows={key:_row(cur,key)for key in render.definitions()},preuse_data_and_sequences=data)
        if catalog._data(cur)!=data:
            raise ValueError('CURRENT_FROZEN_PUBLIC_INSTALL_CHANGED_ROWS_OR_SEQUENCES')
        verify(cur,state);return state


def rollback_preuse(cur,state):
    with atomic(cur):
        _locks(cur);verify(cur,state)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:
            raise ValueError(USED_ERROR)
        for signature in reversed(list(render.definitions())):
            cur.execute('drop function '+signature+' restrict')
        if catalog._catalog_rows(cur)!=state['before']or catalog._data(cur)!=state['preuse_data_and_sequences']:
            raise ValueError('CURRENT_FROZEN_PUBLIC_DELTA_INVERSE_NOT_EXACT')
        return dict(status='EXACT_CURRENT_FROZEN_PUBLIC_DELTA_INVERSE',all22_equal=True,
            all_rows_and_sequences_equal=True,used_guard_before_any_DDL=True,production_go=False)
