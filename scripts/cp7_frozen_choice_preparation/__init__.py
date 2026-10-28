"""Optional composed delta; no default/shared registry or scheduler changes."""
from hashlib import sha256
import json
from cp7_production_stage import _row,_body
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_frozen_analysis_choice_v2 as parent
from . import render

ROOT=render.ROOT
SCHEMA=render.SCHEMA
FUNCTIONS=render.FUNCTIONS

def sources():
 return {p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.rglob('*'))if p.is_file()and p.suffix in('.py','.sql','.json','.ts','.tsx')}

def verify_sources():
 if(ROOT/'preparation.prepared.sql').read_text()!=render.render()or json.loads((ROOT/'PREPARATION.json').read_text())!=render.manifest():
  raise ValueError('CHOICE_PREPARATION_GENERATED_SOURCE_CHANGED')
 return sources()

def declared(group,key):
 if group=='schemas':return key==SCHEMA
 if group=='functions':return key in FUNCTIONS
 if group in('relations','columns','constraints','indexes','triggers','types','type_implementation'):
  return key.startswith(SCHEMA+'.')
 return False

def own(catalog):return {g:{k:v for k,v in rows.items()if declared(g,k)}for g,rows in catalog.items()}

def verify(cur,state):
 if verify_sources()!=state['sources']or parent.sources()!=state['parent_sources']or own(_catalog_rows(cur))!=state['catalog']:
  raise ValueError('CHOICE_PREPARATION_SOURCE_OR_CATALOG_CHANGED')
 for sig,row in state['dependencies'].items():
  if _row(cur,sig)!=row:raise ValueError('CHOICE_PREPARATION_DEPENDENCY_CHANGED:'+sig)
 for sig,(vol,definer)in FUNCTIONS.items():
  row=_row(cur,sig)
  if row!=state['rows'][sig]or row[2:6]!=['cp7_capture',definer,vol,['search_path=""','TimeZone=UTC']]:
   raise ValueError('CHOICE_PREPARATION_AUTHORITY_CHANGED:'+sig)
  for role in('anon','authenticated','service_role','cp7_alert'):
   if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,sig)).fetchone()[0]is not(definer and role=='authenticated'):
    raise ValueError('CHOICE_PREPARATION_EXECUTE_CHANGED:'+sig+':'+role)
 for role in('anon','authenticated','service_role','cp7_alert'):
  if cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]:raise ValueError('CHOICE_PREPARATION_SCHEMA_EXPOSED')
  for privilege in('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'):
   if cur.execute("select has_table_privilege(%s,%s,%s)",(role,SCHEMA+'.work',privilege)).fetchone()[0]:raise ValueError('CHOICE_PREPARATION_TABLE_EXPOSED')
 if cur.execute("select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass",(SCHEMA+'.work',)).fetchone()!=('cp7_capture',True):
  raise ValueError('CHOICE_PREPARATION_TABLE_AUTHORITY_CHANGED')
 if cur.execute("select has_schema_privilege('cp7_capture','public','CREATE')").fetchone()[0]:raise ValueError('CHOICE_PREPARATION_PUBLIC_CREATE_OPEN')
 for group in('schemas','functions'):
  for sig,row in state['catalog'][group].items():
   expected={('cp7_capture','cp7_capture','USAGE',False),('cp7_capture','cp7_capture','CREATE',False)}if group=='schemas'else{('cp7_capture','cp7_capture','EXECUTE',False)}
   if sig in render.PUBLIC:expected.add(('authenticated','cp7_capture','EXECUTE',False))
   if{tuple(x)for x in row[-1]}!=expected:raise ValueError('CHOICE_PREPARATION_UNDECLARED_GRANT:'+sig)
 return dict(private_functions=10,new_public_rpcs=3,new_tables=1,existing_replacements=list(render.originals()),
  actual_Native_qualified=False,actual_Auth_HTTP_credit=False,server_scheduler_installed=False,default_adopted=False,production_go=False)

def install_delta(cur,predecessor_checker):
 if not callable(predecessor_checker):raise ValueError('CHOICE_PREPARATION_COMPOSED_PARENT_REQUIRED')
 predecessor_checker(cur);parent.verify_sources();pins=verify_sources()
 if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:raise ValueError('CHOICE_PREPARATION_ALREADY_INSTALLED')
 for sig in render.PUBLIC:
  if cur.execute('select to_regprocedure(%s)is not null',(sig,)).fetchone()[0]:raise ValueError('CHOICE_PREPARATION_RPC_ALREADY_INSTALLED')
 originals=render.originals();old={sig:_row(cur,sig)for sig in originals}
 for sig,row in old.items():
  if row[1]!=_body(originals[sig]):raise ValueError('CHOICE_PREPARATION_PARENT_REVIEW_CHANGED:'+sig)
 before=_catalog_rows(cur);used=parent.units.parent.usage_state(cur)
 signatures=cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname like 'cp7_%'and p.prokind='f'order by 1").fetchall()
 dependencies={sig:_row(cur,sig)for(sig,)in signatures if sig not in originals}
 sql=(ROOT/'preparation.prepared.sql').read_text();cur.execute(sql,prepare=False)
 rows={sig:_row(cur,sig)for sig in FUNCTIONS}
 for sig,row in rows.items():
  if row[1]!=_body(parent.render.block(sql,sig.split('(')[0])):raise ValueError('CHOICE_PREPARATION_WRONG_BODY:'+sig)
 after=_catalog_rows(cur);catalog=own(after)
 if set(before)!=set(after)or len(before)!=22:raise ValueError('CHOICE_PREPARATION_CATALOG_GROUPS')
 for group in before:
  for key in set(before[group])|set(after[group]):
   a,b=before[group].get(key),after[group].get(key)
   if a==b:continue
   if group=='functions'and key in originals:continue
   if a is None and key in catalog[group]and b==catalog[group][key]:continue
   raise ValueError('CHOICE_PREPARATION_UNDECLARED_DELTA:'+group+':'+key)
 state=dict(sources=pins,parent_sources=parent.sources(),catalog=catalog,rows=rows,dependencies=dependencies,
  old_replacements=old,usage_before=used)
 verify(cur,state);return state

def rollback_preuse(cur,state):
 verify(cur,state)
 if cur.execute('select exists(select 1 from '+SCHEMA+'.work)').fetchone()[0]or parent.units.parent.usage_state(cur)!=state['usage_before']:
  raise ValueError('CHOICE_PREPARATION_AFTER_USE_REQUIRES_COMPOSED_RESTORE')
 external=cur.execute("select exists(select 1 from pg_proc p where not(p.oid=any(%s::regprocedure[]))and case when p.prokind in('f','p')then position(%s in pg_get_functiondef(p.oid))>0 or position('frozen_choice_preparation_v1' in pg_get_functiondef(p.oid))>0 else false end)",(list(FUNCTIONS),SCHEMA+'.')).fetchone()[0]
 if external:raise ValueError('CHOICE_PREPARATION_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE')
 cur.execute('savepoint choice_preparation_inverse')
 try:
  for row in state['old_replacements'].values():cur.execute(row[0],prepare=False)
  # The work row type appears in local function variables, so remove callers
  # first, then the trigger/table, then remaining functions, all with RESTRICT.
  for sig in reversed(FUNCTIONS):
   if sig not in render.originals()and sig!=SCHEMA+'.guard_work()':cur.execute('drop function '+sig+' restrict')
  cur.execute('drop table '+SCHEMA+'.work restrict')
  cur.execute('drop function '+SCHEMA+'.guard_work() restrict')
  cur.execute('drop schema '+SCHEMA+' restrict')
 except Exception:
  cur.execute('rollback to savepoint choice_preparation_inverse');raise
 finally:cur.execute('release savepoint choice_preparation_inverse')
