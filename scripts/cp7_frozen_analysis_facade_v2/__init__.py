"""Prepared explicit facade; private-unit Native qualification is still pending."""
from pathlib import Path
from hashlib import sha256
from cp7_production_stage import _row,_body
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_frozen_analysis_units_v2 as units

ROOT=Path(__file__).resolve().parent
SIGNATURE='public.erp_cp7_request_bounded_staged_analysis_v2(jsonb,uuid)'


def sources():
 return {str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.rglob('*'))if p.is_file()and p.suffix in('.py','.sql','.json','.ts')}


def verify(cur,state):
 if sources()!=state['sources']or units.sources()!=state['parent_sources']:
  raise ValueError('FROZEN_FACADE_SOURCE_CHANGED')
 if _row(cur,SIGNATURE)!=state['row']or _row(cur,'cp7_frozen_analysis_units_v2.request(jsonb,uuid)')!=state['request_row']:
  raise ValueError('FROZEN_FACADE_FUNCTION_CHANGED')
 if state['row'][2:6]!=['cp7_capture',True,'v',['search_path=""','TimeZone=UTC']]:
  raise ValueError('FROZEN_FACADE_AUTHORITY_CHANGED')
 if _catalog_rows(cur)['functions'][SIGNATURE]!=state['catalog_row']:
  raise ValueError('FROZEN_FACADE_CATALOG_CHANGED')
 for role in('anon','authenticated','service_role','cp7_alert'):
  if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,SIGNATURE)).fetchone()[0]is not(role=='authenticated'):
   raise ValueError('FROZEN_FACADE_EXECUTE_CHANGED:'+role)
 if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
  raise ValueError('FROZEN_FACADE_OWNER_PUBLIC_CREATE_OPEN')
 expected={('cp7_capture','cp7_capture','EXECUTE',False),('cp7_capture','authenticated','EXECUTE',False)}
 if {tuple(x)for x in state['catalog_row'][-1]}!=expected:raise ValueError('FROZEN_FACADE_GRANTS_CHANGED')
 return dict(contract='cp7.frozen-analysis-facade-stage.v2',new_public_rpcs=1,new_tables=0,
  existing_replacements=0,actual_Auth_HTTP_qualified=False,default_installer=False,production_go=False)


def install_delta(cur,predecessor_checker):
 if not callable(predecessor_checker):raise ValueError('FROZEN_FACADE_COMPOSED_PARENT_REQUIRED')
 predecessor_checker(cur);units.verify_sources()
 if cur.execute('select to_regprocedure(%s)is not null',(SIGNATURE,)).fetchone()[0]:
  raise ValueError('FROZEN_FACADE_ALREADY_INSTALLED')
 before=_catalog_rows(cur);used=units.parent.usage_state(cur)
 request_row=_row(cur,'cp7_frozen_analysis_units_v2.request(jsonb,uuid)')
 if request_row[1]!=_body(units.render.request_candidate())or request_row[2:6]!=['cp7_capture',False,'v',['search_path=""','TimeZone=UTC']]:
  raise ValueError('FROZEN_FACADE_PRIVATE_REQUEST_CHANGED')
 sql=(ROOT/'facade.sql').read_text();cur.execute(sql,prepare=False)
 after=_catalog_rows(cur);row=_row(cur,SIGNATURE)
 if row[1]!=_body(units.render.block(sql,SIGNATURE.split('(')[0])):raise ValueError('FROZEN_FACADE_WRONG_BODY')
 if set(before)!=set(after)or len(before)!=22:raise ValueError('FROZEN_FACADE_CATALOG_GROUPS')
 for group in before:
  for key in set(before[group])|set(after[group]):
   a,b=before[group].get(key),after[group].get(key)
   if a==b:continue
   if group=='functions'and key==SIGNATURE and a is None and b is not None:continue
   raise ValueError('FROZEN_FACADE_UNDECLARED_DELTA:'+group+':'+key)
 state=dict(sources=sources(),parent_sources=units.sources(),row=row,request_row=request_row,catalog_row=after['functions'][SIGNATURE],usage_before=used)
 verify(cur,state);return state


def rollback_preuse(cur,state):
 verify(cur,state)
 if units.parent.usage_state(cur)!=state['usage_before']:raise ValueError('FROZEN_FACADE_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE')
 if cur.execute("select exists(select 1 from pg_proc p where p.oid<>%s::regprocedure and case when p.prokind in('f','p')then position('erp_cp7_request_bounded_staged_analysis_v2'in pg_get_functiondef(p.oid))>0 else false end)",(SIGNATURE,)).fetchone()[0]:
  raise ValueError('FROZEN_FACADE_REFERENCED_REQUIRES_COMPOSED_RESTORE')
 cur.execute('drop function '+SIGNATURE+' restrict')
