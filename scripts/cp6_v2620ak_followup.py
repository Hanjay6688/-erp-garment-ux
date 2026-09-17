#!/usr/bin/env python3
"""Finish ten interrupted oracle checks; preserve every prior result/provenance."""
from pathlib import Path
from datetime import date,timedelta
import hashlib,io,json,os,re,subprocess,sys,traceback,zipfile
sys.path.insert(0,str(Path.cwd()/'scripts'))
import psycopg
import cp6_v2620ak_review as suite
runtime,actors,base,prior=suite.runtime,suite.actors,suite.base,suite.prior
SOURCE='aa010fbecb512cccf03084e7adb8c426097873e7'
TREE='84383d56a69f0ce4be64937a3df09e276c5ba87e'
ARTIFACT=10479904487
ZIP_SHA='ba89c74c015a44d5bbf40f3ad0f3a9c645786d9de5965a838230c5d0da51fbae'
PREFIX='candidate/cp6-proof/'

def git(*args):return subprocess.check_output(['git','-C',str(runtime.ROOT),*args],text=True).strip()

def inherited():
 assert git('rev-parse',SOURCE+'^{tree}')==TREE
 assert not git('diff','--name-only',SOURCE,'HEAD','--','src','supabase','package.json','package-lock.json'),'Product/runtime changed: full fresh gate required'
 allowed={'.github/workflows/cp6-final-boundary-audit.yml','docs/cp6-ak-import-repair.md',
  'docs/evidence/cp6-disposable-ui-source-pins.json','scripts/cp6_disposable_ui_scope.py',
  'scripts/cp6_v2620ak_advisors.py','scripts/cp6_v2620ak_import_review.py',
  'scripts/cp6_v2620ak_review.py','scripts/cp6_v2620ak_followup.py'}
 assert set(git('diff','--name-only',SOURCE,'HEAD').splitlines())<=allowed,'Unreviewed dependency drift'
 # Removing only the bounded replay adapter must recover the exact oracle.
 path='scripts/cp6_v2620ak_review.py';source=(runtime.ROOT/path).read_text()
 source,count=re.subn(r'# BEGIN AK POSTED IMPORT ORACLE\n.*?# END AK POSTED IMPORT ORACLE\n\n','',source,flags=re.S)
 assert count==1
 source=source.replace("lambda c,n=n,fn=fn:crossflow_case(c,day,n,fn)","lambda c,fn=fn:fn(c,day)")
 assert source==subprocess.check_output(['git','-C',str(runtime.ROOT),'show',SOURCE+':'+path],text=True),'Historical oracle changed beyond replay contract'
 raw=subprocess.check_output(['gh','api',f'repos/Hanjay6688/-erp-garment-ux/actions/artifacts/{ARTIFACT}/zip'],timeout=120)
 assert len(raw)==57373952 and hashlib.sha256(raw).hexdigest()==ZIP_SHA
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))==308
  old=json.loads(z.read(PREFIX+'writer-ak/BUSINESS.json'))
  install=json.loads(z.read(PREFIX+'writer-ak/INSTALL.json'))
  assert (old['head'],old['tree'])==(SOURCE,TREE) and install['status']=='PASS' and install['objects']==690
  assert old['counts']==dict(PASS=169,CONTROL_PASS=39,BUG_PROVEN=0,GAP_PROVEN=0,DATE_POLICY_REVIEW_REQUIRED=12,INCOMPLETE=10,FAIL=0)
  assert len(old['planned_case_ids'])==len(old['cases'])==230 and set(old['planned_case_ids'])==set(old['cases'])
  assert all(old[k] for k in ('catalog_unchanged','boundary_restored','schema_usage_restored')) and old['auth_users']==old['app_users']==0
  groups={}
  for name,wanted in {'writer-ak/CONCURRENCY.json':'PASS_REVIEWED_SCOPE',
   'writer-ak/ORIGINAL_CONCURRENCY.json':'PASS','AK_MAINTENANCE_ROLLBACK/manifest.json':'PASS',
   'final-audit/MONEY_INDEPENDENT.json':'PASS_REVIEWED_SCOPE','final-audit/INDEPENDENT_UI_GAPS.json':'PASS_REVIEWED_SCOPE',
   'final-audit/midnight/AI_MIDNIGHT_AUDIT.json':'PASS_BOUNDED_AUDIT','writer-ak/EXACT_AJ_RESTORE.json':'PASS'}.items():
   obj=json.loads(z.read(PREFIX+name));assert obj['status']==wanted,(name,obj['status'])
   groups[name]=dict(classification='REUSED_EVIDENCE',original_status=wanted,source_head=SOURCE)
 return old,groups

def run():
 assert os.environ['PGURL']==suite.URL and os.environ['CP6_AI_INDEPENDENT_CONFIRM']=='postgres'
 head,tree=runtime.verify_audit_source();old,groups=inherited()
 specs=[('CROSS:'+name,name,fn) for name,fn in suite.original.phase_cases('crossflow')
  if name.startswith(('DAY:FABRIC_ROLL:IMPORT:','DAY:ACCESSORY:IMPORT:'))]
 assert len(specs)==10 and {n for n,_,_ in specs}=={n for n,r in old['cases'].items() if r['status']=='INCOMPLETE'}
 result=dict(status='INCOMPLETE',head=head,tree=tree,source_head=SOURCE,source_tree=TREE,source_run=35180891327,
  artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,product_and_runtime_sources_identical=True,
  reused_groups=groups,planned_case_ids=[n for n,_,_ in specs],cases={},production_go=False,independent_acceptance=False)
 suite.save('BUSINESS_FOLLOWUP',result)
 with psycopg.connect(suite.ADMIN) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
  assert len(runtime.verified_successor(cur))==690
  initial,catalog=actors.boundary(cur),suite.function_catalog(cur)
  usage=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
  if not usage:cur.execute('grant usage on schema erp to authenticated')
  actors.actors.claims(cur,dict(sub=base.OPERATOR_AUTH,role='authenticated'));base.load_fixture_foundation(cur);actors.admin(cur)
  today=cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
  day=today-timedelta(days=3);prior.set_open_period(cur,date(2026,8,31))
  for name,short,fn in specs:
   actors.admin(cur);before=actors.boundary(cur);cur.execute('savepoint ak_followup')
   try:row=suite.crossflow_case(cur,day,short,fn)
   except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
   finally:cur.execute('rollback to savepoint ak_followup');actors.admin(cur);cur.execute('release savepoint ak_followup')
   row['full_boundary_restored']=actors.boundary(cur)==before
   if not row['full_boundary_restored']:row['status']='INCOMPLETE'
   result['cases'][name]=row;suite.save('BUSINESS_FOLLOWUP',result)
   print(json.dumps(dict(case=name,status=row['status'],error=row.get('error'))),flush=True)
  result['catalog_unchanged']=suite.function_catalog(cur)==catalog
  conn.rollback();cur.execute("set local timezone='Asia/Jakarta'")
  result['boundary_restored']=actors.boundary(cur)==initial
  result['schema_usage_restored']=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==usage
  result['auth_users'],result['app_users']=cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
  conn.rollback()
 clean=all(result[k] for k in ('catalog_unchanged','boundary_restored','schema_usage_restored')) and result['auth_users']==result['app_users']==0
 if clean and len(result['cases'])==10 and all(r['status']=='PASS' for r in result['cases'].values()):result['status']='WRITER_PASS'
 aggregate={n:dict(classification='REUSED_EVIDENCE',source_head=SOURCE,original_status=r['status']) for n,r in old['cases'].items() if r['status']!='INCOMPLETE'}
 aggregate.update({n:dict(classification='RECONCILED',execution='FRESH',source_head=head,original_status=r['status']) for n,r in result['cases'].items()})
 counts={s:sum(r['original_status']==s for r in aggregate.values()) for s in old['counts']}
 suite.save('RECONCILED_BUSINESS',dict(status='CP6_HOLD' if result['status']=='WRITER_PASS' else 'INCOMPLETE',
  planned=230,completed=len(aggregate),fresh=10,reused=220,counts=counts,cases=aggregate,
  date_policy_observations_still_open=12,source_artifact=ARTIFACT,source_sha256=ZIP_SHA,
  head=head,tree=tree,production_go=False,independent_acceptance=False))
 result['reconciled_counts']=counts;suite.save('BUSINESS_FOLLOWUP',result);return result

if __name__=='__main__':
 try:r=run()
 except Exception as exc:
  r=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc(),production_go=False);suite.save('BUSINESS_FOLLOWUP_FAILURE',r)
 print(json.dumps({k:v for k,v in r.items() if k not in ('cases','planned_case_ids','reused_groups')}))
 raise SystemExit(0 if r['status']=='WRITER_PASS' else 1)
