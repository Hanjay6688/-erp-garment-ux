"""Optional B caller over a verified A+B predecessor; no default installation."""
from hashlib import sha256
from pathlib import Path
import json
from cp7_production_stage import _row,_body
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_analysis_finance_bridge as legacy
import cp7_frozen_analysis_units_v2 as units
from . import patches

ROOT=Path(__file__).resolve().parent
MANIFEST=json.loads((ROOT/'MANIFEST.json').read_text())
SCHEMA,READER=legacy.SCHEMA,legacy.READER


def sources():
 return dict(files={p.name:sha256(p.read_bytes()).hexdigest()for p in sorted(ROOT.iterdir())if p.suffix in('.py','.json')},
  consumer=sha256((legacy.ROOT/'consumer.sql').read_bytes()).hexdigest(),units=units.sources())


def official_rows(cur):
 rows={}
 for signature,expected in MANIFEST['official_dependencies'].items():
  if cur.execute('select to_regprocedure(%s)is null',(signature,)).fetchone()[0]:
   raise ValueError('FROZEN_FINANCE_REQUIRES_OFFICIAL_A:'+signature)
  row=_row(cur,signature)
  if sha256(row[1].encode()).hexdigest()!=expected['body_sha256']or row[2:6]!=expected['authority']:
   raise ValueError('FROZEN_FINANCE_OFFICIAL_A_SOURCE_OR_AUTHORITY_CHANGED:'+signature)
  for role in('anon','authenticated','service_role'):
   if cur.execute("select has_function_privilege(%s,%s,'EXECUTE')",(role,signature)).fetchone()[0]:
    raise ValueError('FROZEN_FINANCE_OFFICIAL_A_API_EXPOSED:'+role+':'+signature)
  rows[signature]=row
 return rows


def usage(cur):
 return dict(jobs=[str(r[0])for r in cur.execute('select id from cp7_analysis_stage.jobs order by id').fetchall()],
  official_captures=[str(r[0])for r in cur.execute('select id from cp7_finance_capture.captures order by id').fetchall()])


def own_catalog(cur):
 catalog=_catalog_rows(cur)
 return{group:{key:value for key,value in catalog[group].items()if key==SCHEMA or key.startswith(SCHEMA+'.')}for group in('schemas','functions')}


def verify(cur,state):
 if sources()!=state['sources']:raise ValueError('FROZEN_FINANCE_SOURCE_CHANGED')
 if official_rows(cur)!=state['official']:raise ValueError('FROZEN_FINANCE_OFFICIAL_A_CHANGED')
 for signature in patches.SIGNATURES:
  row=_row(cur,signature)
  if row[0]!=state['definitions'][signature]or row[2:]!=state['originals'][signature][2:]:
   raise ValueError('FROZEN_FINANCE_CALLER_OR_AUTHORITY_CHANGED:'+signature)
 if _row(cur,READER)!=state['reader']or own_catalog(cur)!=state['own_catalog']:
  raise ValueError('FROZEN_FINANCE_PRIVATE_READER_CHANGED')
 for group,key,privileges in(('schemas',SCHEMA,('CREATE','USAGE')),('functions',READER,('EXECUTE',))):
  grants=state['own_catalog'][group][key][-1]
  expected={('cp7_capture','cp7_capture',p,False)for p in privileges}
  if len(grants)!=len(expected)or{tuple(g)for g in grants}!=expected:
   raise ValueError('FROZEN_FINANCE_PRIVATE_GRANTS_CHANGED')
 for role in('anon','authenticated','service_role'):
  if cur.execute("select has_schema_privilege(%s,%s,'USAGE')or has_function_privilege(%s,%s,'EXECUTE')",(role,SCHEMA,role,READER)).fetchone()[0]:
   raise ValueError('FROZEN_FINANCE_PRIVATE_READER_EXPOSED:'+role)
 return dict(contract=MANIFEST['contract'],official_API='cp7.finance-capture.v1',existing_consumer_SQL_reused=True,
  financial_formula_added=False,operational_Original_changed=False,actual_Native=False,default_installer=False,production_go=False)


def admit_catalog(before,after,state):
 if set(before)!=set(after)or len(before)!=22:raise ValueError('FROZEN_FINANCE_CATALOG_GROUPS_CHANGED')
 for group in before:
  for key in set(before[group])|set(after[group]):
   old,new=before[group].get(key),after[group].get(key)
   if old==new:continue
   if group=='functions'and key in patches.SIGNATURES and old is not None and new is not None:
    if old[0]==state['originals'][key][0]and new[0]==state['definitions'][key]and old[1:]==new[1:]:continue
   if old is None and new is not None and state['own_catalog'].get(group,{}).get(key)==new:continue
   raise ValueError('FROZEN_FINANCE_UNDECLARED_CATALOG_DELTA:'+group+':'+key)


def install_delta(cur,predecessor_checker):
 if not callable(predecessor_checker):raise ValueError('FROZEN_FINANCE_VERIFIED_A_B_PARENT_REQUIRED')
 predecessor_checker(cur);units.verify_sources()
 if cur.execute('select to_regnamespace(%s)is not null',(SCHEMA,)).fetchone()[0]:
  raise ValueError('FROZEN_FINANCE_LEGACY_OR_CURRENT_CALLER_ALREADY_INSTALLED')
 official=official_rows(cur);originals={sig:_row(cur,sig)for sig in patches.SIGNATURES}
 for sig,row in originals.items():
  if sha256(row[1].encode()).hexdigest()!=MANIFEST['before_body_sha256'][sig]or row[2:6]!=['cp7_capture',False,'v'if sig==patches.REQUEST else's',['search_path=""','TimeZone=UTC']]:
   raise ValueError('FROZEN_FINANCE_PREDECESSOR_CHANGED:'+sig)
 before=_catalog_rows(cur);used=usage(cur)
 replacements=patches.patched({sig:row[0]for sig,row in originals.items()})
 cur.execute((legacy.ROOT/'consumer.sql').read_text(),prepare=False)
 for definition in replacements.values():cur.execute(definition,prepare=False)
 state=dict(sources=sources(),official=official,originals=originals,definitions={sig:_row(cur,sig)[0]for sig in patches.SIGNATURES},
  reader=_row(cur,READER),own_catalog=own_catalog(cur),usage_before=used)
 if state['reader'][1]!=_body((legacy.ROOT/'consumer.sql').read_text())or state['reader'][2:6]!=['cp7_capture',False,'s',['search_path=""','TimeZone=UTC']]:
  raise ValueError('FROZEN_FINANCE_WRONG_PRIVATE_READER')
 if set(state['own_catalog']['schemas'])!={SCHEMA}or set(state['own_catalog']['functions'])!={READER}:
  raise ValueError('FROZEN_FINANCE_PRIVATE_CATALOG_CHANGED')
 admit_catalog(before,_catalog_rows(cur),state);verify(cur,state);return state


def rollback_preuse(cur,state):
 verify(cur,state)
 if usage(cur)!=state['usage_before']:raise ValueError('FROZEN_FINANCE_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE')
 for sig in reversed(patches.SIGNATURES):cur.execute(state['originals'][sig][0],prepare=False)
 cur.execute('drop function '+READER+' restrict;drop schema '+SCHEMA+' restrict',prepare=False)
 for sig,row in state['originals'].items():
  if _row(cur,sig)!=row:raise ValueError('FROZEN_FINANCE_PREDECESSOR_NOT_RESTORED:'+sig)
