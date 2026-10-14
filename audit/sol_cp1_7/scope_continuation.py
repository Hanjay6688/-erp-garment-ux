"""Close missing AR races and C0 on final CP7; retain every first result.

First full-stack AR stopped at a CP6-only body verifier for the deliberately
declared CP7 owner-report overlay. C0 uses the same legacy verifier callback.
Qualify only those two metadata call sites for the installed CP7 catalogue;
case bodies, expected values, race schedules, limits and SQL remain unchanged.
The first 146 AR outcomes and its BC replacement are reused byte-for-byte;
they are not rerun and are not additional Native case executions.
"""
import hashlib,inspect,json,os,textwrap,zipfile
from pathlib import Path
import fullstack_probe as full
import cp6_t2_regression as t2
KIND=os.environ['SOL_SCOPE_CONTINUATION']
assert KIND in ('ar_missing_races','c0')
M=Path(__file__).with_name('SCOPE_CONTINUATION_MANIFEST.json')
manifest=json.loads(M.read_text())
full.MANIFEST=M;full.manifest=manifest
full.OUT=full.CANDIDATE/('cp6-proof/t3/SOL_SCOPE_'+KIND.upper()+'.json')

def corrected(fn,old,new,verify):
 source=textwrap.dedent(inspect.getsource(fn))
 assert source.count(old)==1,('SOL_SCOPE_CALLBACK_COUNT',fn.__name__)
 derived=source.replace(old,new)
 scope=dict(vars(t2),_sol_verify=verify)
 exec(compile(derived,'<sol-cp7-metadata-callback:'+fn.__name__+'>','exec'),scope)
 return scope[fn.__name__],dict(function=fn.__name__,original_sha256=hashlib.sha256(source.encode()).hexdigest(),
   qualified_sha256=hashlib.sha256(derived.encode()).hexdigest(),exact_old=old,exact_new=new,
   case_oracle_change=False,SQL_change=False,limits_change=False)

def continuation(verify):
 a=t2.avt;a.OUT=full.CANDIDATE/('cp6-proof/t3/SCOPE_'+KIND.upper());a.OUT.mkdir(parents=True,exist_ok=True)
 r=dict(status='INCOMPLETE',candidate_sha=manifest['candidate_sha'],
   continuation=KIND,first_fullstack_run=38574107235,
   expected_count=manifest['budgets'][KIND],production_go=False,
   source_probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 if KIND=='c0':
  fn,diff=corrected(t2.c0_oracle_group,'cases,bep.verified','cases,_sol_verify',verify)
  r['metadata_only_diff']=diff;r['summary']=fn()
  original=json.loads((a.OUT/'T2_C0_ORACLE.json').read_text())
  r['original_report']=original
  assert original['planned_case_ids']==manifest['c0_expected_ids']
  r['status']='PASS'if original.get('counts')=={'PASS':25}and original.get('complete_boundary_restored')and not original.get('missing')else'INCOMPLETE'
  r['new_Native_executions']=len(original['cases'])
 else:
  archive=Path(os.environ['SOL_FIRST_AR_ARCHIVE']);raw=archive.read_bytes()
  assert hashlib.sha256(raw).hexdigest()==manifest['first_AR_zip_sha256']
  cache={}
  with zipfile.ZipFile(archive)as z:
   assert z.testzip()is None
   for key,spec in manifest['first_AR_reports'].items():
    raw=z.read(spec['member']);assert hashlib.sha256(raw).hexdigest()==spec['sha256']
    cache[key]=json.loads(raw)
    assert cache[key]['complete_boundary_restored']is True
  assert cache['AR_SEQUENTIAL']['counts']=={'PASS':145,'INCOMPLETE':1}
  assert cache['AR_SUPERSEDING']['counts']=={'PASS':1}
  def reuse(name,factory):
   assert name in cache,('SOL_UNDECLARED_REUSE',name)
   return cache[name]
  a.group=reuse
  def installed():
   with full.psycopg.connect(a.ADMIN)as conn,conn.cursor()as cur:verify(cur);conn.rollback()
   return dict(status='PASS',context='ALREADY_INSTALLED_FINAL_CP7_VERIFIED')
  a.install_au=lambda:installed()['status']
  t2.change=lambda *args:installed()
  a.runtime.verified=verify
  fn,diff=corrected(t2.ar_phase,'bep.verified(cur)','_sol_verify(cur)',verify)
  r['metadata_only_diff']=diff;original=dict(status='INCOMPLETE',production_go=False)
  fn(original);r['original_AR_report']=original
  r['reused_original_groups']=cache;r['reused_native_execution_credit']=0
  ids=list(original['races']);assert ids==manifest['ar_expected_race_ids']
  r['status']='PASS_CONTRACT_DISPOSITIONS'if len(ids)==28 and all(x['status']=='PASS'for x in original['races'].values())else'INCOMPLETE'
  r['new_Native_executions']=len(ids)
  r['accepted_disposition']='ACCESSORY_CONNECTED_ZERO is unchanged INCOMPLETE; its same-source BC_FREE_REQUIRES_POLICY replacement is PASS under ERP-DEC02. No relabeling.'
 return r

full.legacy=continuation
def runtime(browser_mode=False):
 normal=full.probe.run(k3_cleanup=True)
 assert len(full.observed)==1
 if full.observed[0]['status']not in ('PASS','PASS_CONTRACT_DISPOSITIONS'):
  normal=dict(normal,status='INCOMPLETE',sol_scope_continuation_incomplete=True)
 return normal
full.probe.package._writer_runtime=runtime
if __name__=='__main__':full.probe.package.run('install')
