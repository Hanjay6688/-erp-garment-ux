#!/usr/bin/env python3
"""Read-only Supabase security advisors, compared on exact AJ and AK."""
import argparse,json,os,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts'))
import psycopg
import cp6_v2620ak_runtime as runtime
import cp6_v2620aj_runtime as predecessor
from cp6_v2620u_install_diagnostic import snapshot

URL='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
ROOT=Path('cp6-proof/writer-ak')

def run(phase):
 assert os.environ['PGURL']==URL and os.environ['CP6_AI_INDEPENDENT_CONFIRM']=='postgres'
 head,tree=runtime.verify_audit_source();version=predecessor if phase=='before' else runtime
 with psycopg.connect(URL.replace('postgres:postgres@','supabase_admin:postgres@')) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='UTC'");assert len(version.verified_successor(cur))==690
  before=json.loads(json.dumps(snapshot(cur),default=str));conn.rollback()
 # CLI 2.116.0's documented text-mode payload is a JSON lint array. A clean
 # result emits no stdout and an explicit "No issues found" diagnostic.
 # Pin this contract rather than treating an unknown envelope as zero issues.
 command=['supabase','db','advisors','--db-url',URL,'--type','security','--level','info','--fail-on','none','--output-format','text','--agent','no']
 process=subprocess.run(command,capture_output=True,text=True,timeout=90)
 if process.returncode:raise RuntimeError('Disposable security advisors failed: '+process.stderr[-1500:])
 if process.stdout.strip():parsed=json.loads(process.stdout)
 else:
  assert 'No issues found' in process.stderr.splitlines(),'Missing advisors result'
  parsed=[]
 assert isinstance(parsed,list) and all(isinstance(x,dict) and x.get('name') and x.get('level') for x in parsed),'Unexpected advisors response'
 observed=parsed
 with psycopg.connect(URL.replace('postgres:postgres@','supabase_admin:postgres@')) as conn,conn.cursor() as cur:
  cur.execute("set local timezone='UTC'");assert len(version.verified_successor(cur))==690
  assert json.loads(json.dumps(snapshot(cur),default=str))==before,'Advisors changed ERP data';conn.rollback()
 ROOT.mkdir(parents=True,exist_ok=True)
 result=dict(status='READ_ONLY_CAPTURED',phase=phase,writer_head=head,writer_tree=tree,
  runtime='AJ' if phase=='before' else 'AK',cli_version='2.116.0',findings=observed,raw=parsed,boundary_unchanged=True,production_go=False)
 if phase=='after':
  initial=json.loads((ROOT/'ADVISORS_BEFORE.json').read_text());assert initial['writer_head']==head
  key=lambda x:json.dumps(x,sort_keys=True)
  original={key(x) for x in initial['findings']}
  added=[x for x in observed if key(x) not in original]
  # A private rollback capsule intentionally has no user policies. Its owner,
  # RLS flag and revoked role privileges were checked by the full runtime gate.
  allowed=[];unreviewed=[]
  for finding in added:
   meta=finding.get('metadata') or {}
   if finding['name']=='rls_enabled_no_policy' and meta.get('schema')=='erp' and meta.get('name')=='cp6_v2620ak_rollback_capsule':allowed.append(finding)
   else:unreviewed.append(finding)
  result.update(status='REVIEW_REQUIRED' if unreviewed else 'PASS_REVIEWED_SECURITY_DELTA',
   prior_count=len(initial['findings']),current_count=len(observed),new_findings=unreviewed,
   reviewed_private_capsule_information=allowed,baseline_findings_not_silently_waived=initial['findings'])
 (ROOT/('ADVISORS_'+phase.upper()+'.json')).write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in('raw','findings','baseline_findings_not_silently_waived')}))
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=('before','after'),required=True)
 r=run(p.parse_args().phase);raise SystemExit(0 if r['status'] in('READ_ONLY_CAPTURED','PASS_REVIEWED_SECURITY_DELTA') else 1)
