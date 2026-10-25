"""Private opt-in v2 staged adapter. No connection, commit, facade or default route."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_production_stage import _row,_body
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_model_target_consumer_v2_stage as parent
import cp7_frozen_analysis_v2 as capsule
from . import render

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_frozen_analysis_units_v2'
FUNCTIONS={
 SCHEMA+'.binding(cp7_analysis_stage.jobs)':'i',
 SCHEMA+'.pack(cp7_analysis_stage.jobs,jsonb)':'i',
 SCHEMA+'.unpack(cp7_analysis_stage.jobs,jsonb)':'i',
 SCHEMA+'.unit_reference(cp7_analysis_stage.jobs,cp7_analysis_stage.units)':'v',
 SCHEMA+'.producer_hash()':'s',SCHEMA+'.source(jsonb,boolean)':'s',
 SCHEMA+'.coverage(uuid)':'s',SCHEMA+'.request(jsonb,uuid)':'v',
}


def sources():
 return {p.name:sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.iterdir())if p.is_file()and p.suffix in('.py','.sql','.json')}


def verify_sources():
 expected={'run-hook.prepared.sql':render.run_hook()+'\n','request.prepared.sql':render.request_candidate()+'\n',
  'hooks.prepared.sql':'\n\n'.join(render.replacements().values())+'\n'}
 for path,body in expected.items():
  if (ROOT/path).read_text()!=body:raise ValueError('FROZEN_UNITS_GENERATED_SOURCE_CHANGED:'+path)
 if json.loads((ROOT/'PREPARATION.json').read_text())!=render.manifest():raise ValueError('FROZEN_UNITS_MANIFEST_CHANGED')
 return sources()


def declared(group,key):
 return(group=='schemas'and key==SCHEMA)or(group=='functions'and key in set(FUNCTIONS)|set(render.originals()))


def own_catalog(catalog):
 return {g:{k:v for k,v in rows.items()if declared(g,k)}for g,rows in catalog.items()}


def private_definitions():
 text='\n'.join((ROOT/p).read_text()for p in('cache.sql','source.prepared.sql','request.prepared.sql'))
 return {sig:render.block(text,sig.split('(')[0])for sig in FUNCTIONS}


def verify(cur,state):
 if verify_sources()!=state['sources']or own_catalog(_catalog_rows(cur))!=state['catalog']:
  raise ValueError('FROZEN_UNITS_SOURCE_OR_CATALOG_CHANGED')
 capsule.dependencies(cur)
 for sig,row in state['new_rows'].items():
  if _row(cur,sig)!=row:raise ValueError('FROZEN_UNITS_FUNCTION_CHANGED:'+sig)
  if sig in state['old_rows']and row[2:]!=state['old_rows'][sig][2:]:
   raise ValueError('FROZEN_UNITS_EXISTING_AUTHORITY_CHANGED:'+sig)
 for sig,row in state['dependencies'].items():
  if _row(cur,sig)!=row:raise ValueError('FROZEN_UNITS_DEPENDENCY_CHANGED:'+sig)
 for sig,volatility in FUNCTIONS.items():
  if state['new_rows'][sig][2:6]!=['cp7_capture',False,volatility,['search_path=""','TimeZone=UTC']]:
   raise ValueError('FROZEN_UNITS_PRIVATE_AUTHORITY_CHANGED:'+sig)
  for role in('anon','authenticated','service_role','cp7_alert'):
   if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]:
    raise ValueError('FROZEN_UNITS_PRIVATE_EXECUTE_EXPOSED:'+sig)
 if cur.execute('select pg_get_userbyid(nspowner)from pg_namespace where nspname=%s',(SCHEMA,)).fetchone()!=('cp7_capture',):
  raise ValueError('FROZEN_UNITS_SCHEMA_OWNER_CHANGED')
 for role in('anon','authenticated','service_role','cp7_alert'):
  if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:
   raise ValueError('FROZEN_UNITS_SCHEMA_EXPOSED:'+role)
 if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:
  raise ValueError('FROZEN_UNITS_PUBLIC_CREATE_OPEN')
 for group in('schemas','functions'):
  for key,row in state['catalog'][group].items():
   if group=='functions'and key not in FUNCTIONS:continue
   for grant in row[-1]:
    if grant[0]!='cp7_capture'or grant[1]!='cp7_capture'or grant[3]is not False:
     raise ValueError('FROZEN_UNITS_UNDECLARED_GRANT:'+key)
 return dict(stage='cp7.frozen-analysis-units-stage.v2',new_private_functions=8,existing_replacements=8,
  new_public_rpcs=0,new_tables=0,Native_ERP_DML=False,actual_Native_qualified=False,
  actual_Auth_HTTP_credit=False,default_request_adopted=False,production_go=False)


def install_delta(cur,predecessor_checker):
 pins=verify_sources()
 if not callable(predecessor_checker):raise ValueError('FROZEN_UNITS_COMPOSED_PARENT_REQUIRED')
 predecessor_checker(cur);capsule.dependencies(cur)
 if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
  raise ValueError('FROZEN_UNITS_ALREADY_INSTALLED')
 if cur.execute("select exists(select 1 from cp7_analysis_stage.jobs where state='RUNNING')or exists(select 1 from cp7_analysis_jobs.jobs where state='WAITING')").fetchone()[0]:
  raise ValueError('FROZEN_UNITS_QUIET_INSTALL_REQUIRED')
 before=_catalog_rows(cur);originals=render.originals();old={sig:_row(cur,sig)for sig in originals}
 for sig,sql in originals.items():
  if old[sig][1]!=_body(sql)or old[sig][2]!='cp7_capture':raise ValueError('FROZEN_UNITS_PREDECESSOR_CHANGED:'+sig)
 signatures=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname like 'cp7_%'and p.prokind='f'order by 1").fetchall()
 dependencies={sig:_row(cur,sig)for(sig,)in signatures if sig not in old}
 used=parent.usage_state(cur)
 for path in('cache.sql','source.prepared.sql','request.prepared.sql','hooks.prepared.sql'):
  cur.execute((ROOT/path).read_text(),prepare=False)
 for sig in FUNCTIONS:
  cur.execute('alter function '+sig+' owner to cp7_capture')
  cur.execute('revoke all on function '+sig+' from public,anon,authenticated,service_role')
 new={sig:_row(cur,sig)for sig in(*old,*FUNCTIONS)}
 for sig,sql in {**render.replacements(),**private_definitions()}.items():
  if new[sig][1]!=_body(sql):raise ValueError('FROZEN_UNITS_WRONG_BODY:'+sig)
 after=_catalog_rows(cur);catalog=own_catalog(after)
 if set(before)!=set(after)or len(before)!=22:raise ValueError('FROZEN_UNITS_CATALOG_GROUPS')
 for group in before:
  for key in set(before[group])|set(after[group]):
   a,b=before[group].get(key),after[group].get(key)
   if a==b:continue
   if declared(group,key)and b==catalog[group].get(key)and(a is None or group=='functions'and key in old):continue
   raise ValueError('FROZEN_UNITS_UNDECLARED_DELTA:'+group+':'+key)
 state=dict(sources=pins,old_rows=old,new_rows=new,dependencies=dependencies,usage_before=used,catalog=catalog)
 verify(cur,state);return state


def rollback_preuse(cur,state):
 verify(cur,state)
 if parent.usage_state(cur)!=state['usage_before']:raise ValueError('FROZEN_UNITS_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE')
 external=cur.execute("select p.oid::regprocedure::text from pg_proc p where not(p.oid=any(%s::regprocedure[]))and case when p.prokind in('f','p')then position(%s in pg_get_functiondef(p.oid))>0 else false end",(list(state['new_rows']),SCHEMA+'.')).fetchall()
 if external:raise ValueError('FROZEN_UNITS_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
 cur.execute('savepoint frozen_units_inverse')
 try:
  for row in state['old_rows'].values():cur.execute(row[0],prepare=False)
  for sig in reversed(FUNCTIONS):cur.execute('drop function '+sig+' restrict')
  cur.execute('drop schema '+SCHEMA+' restrict')
 except Exception:
  cur.execute('rollback to savepoint frozen_units_inverse');raise
 finally:cur.execute('release savepoint frozen_units_inverse')
