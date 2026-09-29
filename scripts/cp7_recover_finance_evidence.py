"""Recover verified CP7 evidence after local executor disconnection; read-only."""
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler,urlopen
from urllib.error import HTTPError
from urllib.parse import urlparse
import json,os,hashlib,io,zipfile,gzip,collections,subprocess,tempfile,tarfile,base64
REPO='Hanjay6688/-erp-garment-ux'
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
def api(path,redirect=False):
 req=Request('https://api.github.com/repos/'+REPO+path,headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
 try:
  with build_opener(NoRedirect).open(req,timeout=60)as r:return r.read()
 except HTTPError as e:
  if not redirect or e.code!=302:raise
  location=e.headers['Location'];assert urlparse(location).scheme=='https'
  # Never forward the GitHub token to the signed artifact host.
  with urlopen(Request(location),timeout=60)as r:return r.read()
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 specs=json.loads(Path('scripts/cp7_recover_finance_evidence.inputs.json').read_text());files=[]
 def add(path,raw,binary=False):
  files.append(dict(path=path,mode='100644',type='blob',git_blob_sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),sha256=digest(raw),**({'base64':base64.b64encode(raw).decode()}if binary else{'content':raw.decode()})))
 for spec in specs:
  a=spec['artifact'];sha=a['workflow_run']['head_sha']
  current=json.loads(api('/actions/artifacts/'+str(a['id'])))
  for key in ('id','digest','size_in_bytes','workflow_run'):assert current[key]==a[key],key
  archive=api('/actions/artifacts/'+str(a['id'])+'/zip',True)
  assert len(archive)==a['size_in_bytes']and digest(archive)==a['digest'].split(':')[1]
  with zipfile.ZipFile(io.BytesIO(archive))as z:
   assert all(not Path(n).is_absolute()and'..'not in Path(n).parts for n in z.namelist())
   raw=z.read(spec['file']);report=json.loads(raw);install=json.loads(z.read('T3_PACKAGE_INSTALL.json'))
   assert install['run_identity']['github_sha']==install['run_identity']['tool_head']==sha
   with tempfile.TemporaryDirectory()as source:
    tar=subprocess.check_output(['git','archive',sha,'scripts','docs/cp7/evidence/p00/CP7_P00_CATALOGUE.json.gz'])
    with tarfile.open(fileobj=io.BytesIO(tar))as t:t.extractall(source,filter='data')
    bundle=subprocess.check_output(['python','-c',f"import sys,hashlib;sys.path.insert(0,{source!r}+'/scripts');import {spec['module']} as m;print(hashlib.sha256(m.bundle().encode()).hexdigest())"],text=True).strip()
   assert bundle==report['source_sha256']
   assert report['cp6_restored']and report['advisor_gate']and all(v for k,v in install['gate'].items()if k!='writer_runtime')
   counts=collections.Counter();groups={};errors={}
   for name,g in report.items():
    if not isinstance(g,dict):continue
    assert not any(g.get(k)for k in ('database_remaining','cleanup_failures','auth_cleanup_failures','session_leaks','console_errors')),(name,'cleanup')
    if 'auth_counts'in g:assert g['auth_counts']['restored']and g['auth_counts']['before']==g['auth_counts']['after']==[0,0,0,0]
    if 'counts'not in g:continue
    rows=g.get('cases',g.get('races'));assert dict(collections.Counter(v['status']for v in rows.values()))==g['counts']
    counts.update(g['counts']);groups[name]=g['counts'];errors.update({k:dict(status=v['status'],error=v.get('error'))for k,v in rows.items()if v['status']!='PASS'})
   assert counts['PASS']==spec['passes']and counts['INCOMPLETE']==spec['total']-spec['passes']and sum(counts.values())==spec['total']==report['observed_case_count']
   if spec['passes']==spec['total']:assert report['status']=='PASS'and install['gate']['writer_runtime']
   compressed=gzip.compress(raw,mtime=0);prefix='docs/cp7/evidence/p13-finance/'+spec['stem']
   receipt=dict(status=report['status'],source_commit=sha,source_tree=subprocess.check_output(['git','rev-parse',sha+'^{tree}'],text=True).strip(),run_id=a['workflow_run']['id'],job_id=spec['job_id'],artifact_id=a['id'],artifact_bytes=len(archive),artifact_sha256=digest(archive),report_sha256=digest(raw),report_gzip_sha256=digest(compressed),source_bundle_sha256=bundle,counts={k:counts[k]for k in ('PASS','FAIL','INCOMPLETE','NOT_RUN')},observed_case_count=report['observed_case_count'],expected_cases=spec['total'],groups=groups,nonpassing_cases=errors,cp6_restored=True,advisor_gate=True,auth_database_cleanup=True,accepted_package_gate=install['gate'],run_identity=install['run_identity'],visual_review=False,independent_acceptance=False,production_go=False,full_family_acceptance=False,recovery='Original artifact re-fetched and verified in read-only GitHub Actions after the local executor disconnected; results are not a new business test execution.')
   if spec['key']=='recostQualified':
    receipt['visual_review']=dict(source='Original run36643127078 screenshots inspected by writer before executor disconnection',result='Desktop/mobile queue controls fit; existing SKU/lot tables retain their internal horizontal scrolling. Native incomplete-cost status remains visible after an empty queue.')
    receipt['amount_basis']='Native po_hpp_gl_state.hpp_total_cost85->90 is the basis of produced FG output, not the entire PO including unfinished WIP. Remaining FG51->54 and COGS34->36 are separately checked.'
    receipt['screenshots']={}
    for suffix in ('DESKTOP','MOBILE'):
     name='P13_RECOST_'+suffix+'.png';png=z.read(name);receipt['screenshots'][name]=dict(sha256=digest(png),bytes=len(png));add('docs/cp7/evidence/p13-finance/'+name,png,True)
   if spec['key']=='combinedMicro':
    paths=['src','scripts/cp7-src','supabase'];assert not subprocess.check_output(['git','diff','--name-only',sha,'55cb59dd914052f2c5a72dc535960c0aac00d65d','--',*paths],text=True)
    receipt['candidate_product_equivalence']=dict(compared_commit='55cb59dd914052f2c5a72dc535960c0aac00d65d',paths=paths,changed_files=[],scope='Product paths match; original run identity remains23f795a.')
   if spec['key']=='recostMicro':receipt['diagnosis']='24 PASS/1 INCOMPLETE: desktop strict generic alert selector matches both the legitimate recovery notice and network error. Native/race/Auth and mobile recovery pass.55cb59d repairs selector precision without changing product paths.'
   if spec['key']in ('analysisFinal','periodFinalQualified'):
    receipt['previous_inspected_visual_receipt']='ANALYSIS_QUALIFIED_RECEIPT.json'if spec['key']=='analysisFinal'else'PERIOD_VISUAL_QUALIFIED_RECEIPT.json'
    receipt['visual_review_scope']='Current-source functional regression. Earlier retained visual review preserves its own source identity.'
   add(prefix+'.json.gz',compressed,True);add(prefix+'_RECEIPT.json',(json.dumps(receipt,indent=2)+'\n').encode())
  print(json.dumps(dict(kind='CP7_EVIDENCE_VERIFIED',stem=spec['stem'],source=sha,counts=dict(counts))),flush=True)
 manifest=json.dumps(dict(version='cp7.evidence-recovery.v1',files=files),separators=(',',':'))
 chunks=[manifest[i:i+15000]for i in range(0,len(manifest),15000)]
 print(json.dumps(dict(kind='CP7_EVIDENCE_MANIFEST',sha256=digest(manifest.encode()),bytes=len(manifest.encode()),files=len(files),chunks=len(chunks))),flush=True)
 for i,chunk in enumerate(chunks):print(json.dumps(dict(kind='CP7_EVIDENCE_CHUNK',index=i,total=len(chunks),data=chunk)),flush=True)
if __name__=='__main__':main()
