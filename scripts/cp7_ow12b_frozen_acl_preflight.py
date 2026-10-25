"""Check corrected strict ACL guards against actual PG18 serializer output."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import sys
import cp7_frozen_analysis_facade_v2 as facade
import cp7_frozen_analysis_readers_v2 as readers
import cp7_frozen_analysis_choice_v2 as choice
from cp7_ow04_restore_bundle import QUERIES

raw=json.loads(Path(sys.argv[1]).read_text());assert raw['status']=='DDL_AND_RAW_SERIALIZATION_COMPLETE'
assert raw['query_sha256']=={k:sha256(QUERIES[k].encode()).hexdigest()for k in('schemas','functions')}
for p,h in raw['DDL_source_sha256'].items():assert sha256(Path(p).read_bytes()).hexdigest()==h
actual=raw['catalog'];facade.verify_grants(actual['functions'][facade.SIGNATURE][-1])
for stage in(readers,choice):stage.verify_grants(stage.own(actual))
rejected=[]
def refuse(label,fn):
 try:fn()
 except ValueError:rejected.append(label)
 else:raise AssertionError('CHANGED_GRANT_ACCEPTED:'+label)

for name,stage,public in(('facade',facade,facade.SIGNATURE),('reader',readers,readers.render.PUBLIC+'('+readers.render.ARGS+')'),('choice',choice,choice.render.PUBLIC+'(jsonb,uuid)')):
 rows=deepcopy(actual['functions'][public][-1]);auth=next(x for x in rows if x[0]=='authenticated')
 assert auth==['authenticated','cp7_capture','EXECUTE',False]
 def check(grants):
  if stage is facade:return stage.verify_grants(grants)
  cat=stage.own(deepcopy(actual));cat['functions'][public][-1]=grants;return stage.verify_grants(cat)
 for mutation in('reversed','missing','duplicate','public','grantor','grantable','privilege','postgres'):
  changed=deepcopy(rows);index=next(i for i,x in enumerate(changed)if x[0]=='authenticated')
  if mutation=='reversed':changed[index][:2]=list(reversed(changed[index][:2]))
  if mutation=='missing':changed.pop(index)
  if mutation=='duplicate':changed.append(deepcopy(changed[index]))
  if mutation=='public':changed[index][0]='PUBLIC'
  if mutation=='grantor':changed[index][1]='postgres'
  if mutation=='grantable':changed[index][3]=True
  if mutation=='privilege':changed[index][2]='CREATE'
  if mutation=='postgres':changed.append(['postgres','cp7_capture','EXECUTE',False])
  refuse(name+':'+mutation,lambda:check(changed))
 if stage is facade:continue
 for mutation in('private_authenticated','schema_authenticated','schema_missing_create','schema_foreign_grantor'):
  cat=stage.own(deepcopy(actual))
  if mutation=='private_authenticated':
   sig=next(k for k in stage.FUNCTIONS if k!=public);cat['functions'][sig][-1].append(['authenticated','cp7_capture','EXECUTE',False])
  else:
   grants=cat['schemas'][stage.SCHEMA][-1]
   if mutation=='schema_authenticated':grants.append(['authenticated','cp7_capture','USAGE',False])
   if mutation=='schema_missing_create':grants[:]=[x for x in grants if x[2]!='CREATE']
   if mutation=='schema_foreign_grantor':grants[0][1]='postgres'
  refuse(name+':'+mutation,lambda:stage.verify_grants(cat))
assert len(rejected)==32
print(json.dumps(dict(contract='cp7.frozen-grantee-first-ACL-verification.v2',status='PASS',actual_PGlite18_DDL=True,
 actual_repository_serializer_and_catalog_context=True,positive_extension_catalogs=3,negative_grant_controls=32,creator=raw['creator'],public_schema_defaults_reproduced=raw['public_schema_defaults_reproduced'],
 rejected=rejected,actual_owned_grants={name:{g:{k:v[-1]for k,v in stage.own(actual)[g].items()}for g in('schemas','functions')}for name,stage in(('reader',readers),('choice',choice))},
 facade_grants=actual['functions'][facade.SIGNATURE][-1],DDL_source_sha256=raw['DDL_source_sha256'],query_sha256=raw['query_sha256'],
 first_local_fixture_failure='Missing reader reference.sql omitted its schema; added actual installer DDL in order. Initial raw export had default search_path; matched actual _catalog empty path and UTC before assertions.',
 actual_Native=False,actual_command_executed=False,actual_Auth_HTTP_credit=False,oracle_relaxed=False,production_go=False)))
