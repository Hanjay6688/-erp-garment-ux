"""Prepared explicit confirmation extension; no default installer or UI adoption."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_production_stage import _row, _body
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_frozen_analysis_units_v2 as units
import cp7_frozen_analysis_readers_v2 as readers
from . import render

ROOT=Path(__file__).resolve().parent
SCHEMA=render.SCHEMA
FUNCTIONS={SCHEMA+'.normalize_confirmed_delta(jsonb,jsonb,jsonb)':('i',False),
 SCHEMA+'.apply(jsonb,uuid)':('v',False),render.PUBLIC+'(jsonb,uuid)':('v',True)}


def sources():
 return {p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.rglob('*'))if p.is_file()and p.suffix in('.py','.sql','.json','.ts')}


def verify_sources():
 if (ROOT/'choice.prepared.sql').read_text()!=render.render()or json.loads((ROOT/'PREPARATION.json').read_text())!=render.manifest():
  raise ValueError('FROZEN_CHOICE_GENERATED_SOURCE_CHANGED')
 return sources()


def own(catalog):
 return {g:{k:v for k,v in rows.items()if g=='schemas'and k==SCHEMA or g=='functions'and k in FUNCTIONS}for g,rows in catalog.items()}


def verify(cur,state):
 if verify_sources()!=state['sources']or readers.sources()!=state['parent_sources']or own(_catalog_rows(cur))!=state['catalog']:
  raise ValueError('FROZEN_CHOICE_SOURCE_OR_CATALOG_CHANGED')
 for sig,row in state['dependencies'].items():
  if _row(cur,sig)!=row:raise ValueError('FROZEN_CHOICE_DEPENDENCY_CHANGED:'+sig)
 for sig,(volatility,definer)in FUNCTIONS.items():
  row=_row(cur,sig)
  if row!=state['rows'][sig]or row[2:6]!=['cp7_capture',definer,volatility,['search_path=""','TimeZone=UTC']]:
   raise ValueError('FROZEN_CHOICE_FUNCTION_OR_AUTHORITY_CHANGED:'+sig)
  for role in('anon','authenticated','service_role','cp7_alert'):
   if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]is not(definer and role=='authenticated'):
    raise ValueError('FROZEN_CHOICE_EXECUTE_CHANGED:'+sig+':'+role)
 for role in('anon','authenticated','service_role','cp7_alert'):
  if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:raise ValueError('FROZEN_CHOICE_SCHEMA_EXPOSED:'+role)
 if cur.execute('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',(SCHEMA,)).fetchone()!=('cp7_capture',):raise ValueError('FROZEN_CHOICE_SCHEMA_OWNER_CHANGED')
 if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:raise ValueError('FROZEN_CHOICE_PUBLIC_CREATE_OPEN')
 for group in('schemas','functions'):
  for sig,row in state['catalog'][group].items():
   allowed={'cp7_capture','authenticated'}if sig==render.PUBLIC+'(jsonb,uuid)'else{'cp7_capture'}
   for grant in row[-1]:
    if grant[0]!='cp7_capture'or grant[1]not in allowed or grant[3]is not False:raise ValueError('FROZEN_CHOICE_UNDECLARED_GRANT:'+sig)
 return dict(private_functions=2,new_public_rpcs=1,new_tables=0,existing_replacements=0,
  actual_Native_qualified=False,actual_Auth_HTTP_credit=False,default_adopted=False,production_go=False)


def install_delta(cur,predecessor_checker):
 if not callable(predecessor_checker):raise ValueError('FROZEN_CHOICE_COMPOSED_PARENT_REQUIRED')
 predecessor_checker(cur);readers.verify_sources();units.verify_sources();pins=verify_sources()
 if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:raise ValueError('FROZEN_CHOICE_ALREADY_INSTALLED')
 if cur.execute('select to_regprocedure(%s)is not null',(render.PUBLIC+'(jsonb,uuid)',)).fetchone()[0]:raise ValueError('FROZEN_CHOICE_RPC_ALREADY_INSTALLED')
 for old_sig,definition in render.originals().items():
  if _row(cur,old_sig)[1]!=_body(definition):raise ValueError('FROZEN_CHOICE_ADMITTED_PARENT_CHANGED:'+old_sig)
 before=_catalog_rows(cur);used=units.parent.usage_state(cur)
 signatures=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname like 'cp7_%'and p.prokind='f'order by 1").fetchall()
 dependencies={sig:_row(cur,sig)for(sig,)in signatures}
 sql=(ROOT/'choice.prepared.sql').read_text();cur.execute(sql,prepare=False)
 rows={sig:_row(cur,sig)for sig in FUNCTIONS}
 for sig in FUNCTIONS:
  expected=render.block(sql,sig.split('(')[0])
  if rows[sig][1]!=_body(expected):raise ValueError('FROZEN_CHOICE_WRONG_BODY:'+sig)
 after=_catalog_rows(cur);catalog=own(after)
 if set(before)!=set(after)or len(before)!=22:raise ValueError('FROZEN_CHOICE_CATALOG_GROUPS')
 for group in before:
  for key in set(before[group])|set(after[group]):
   a,b=before[group].get(key),after[group].get(key)
   if a==b:continue
   if a is None and key in catalog[group]and b==catalog[group][key]:continue
   raise ValueError('FROZEN_CHOICE_UNDECLARED_DELTA:'+group+':'+key)
 state=dict(sources=pins,parent_sources=readers.sources(),catalog=catalog,rows=rows,dependencies=dependencies,usage_before=used)
 verify(cur,state);return state


def rollback_preuse(cur,state):
 verify(cur,state)
 if units.parent.usage_state(cur)!=state['usage_before']:raise ValueError('FROZEN_CHOICE_AFTER_USE_REQUIRES_COMPOSED_RESTORE')
 external=cur.execute("select exists(select 1 from pg_proc p where not(p.oid=any(%s::regprocedure[]))and case when p.prokind in('f','p')then position(%s in pg_get_functiondef(p.oid))>0 or position(%s in pg_get_functiondef(p.oid))>0 else false end)",(list(FUNCTIONS),SCHEMA+'.',render.PUBLIC.split('.')[1])).fetchone()[0]
 if external:raise ValueError('FROZEN_CHOICE_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
 cur.execute('savepoint frozen_choice_inverse')
 try:
  for sig in reversed(FUNCTIONS):cur.execute('drop function '+sig+' restrict')
  cur.execute('drop schema '+SCHEMA+' restrict')
 except Exception:
  cur.execute('rollback to savepoint frozen_choice_inverse');raise
 finally:cur.execute('release savepoint frozen_choice_inverse')
