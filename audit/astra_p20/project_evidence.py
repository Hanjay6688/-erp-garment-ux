"""Read only our own run artifacts; transport complete first verdicts and compact per-case indexes."""
import base64,gzip,hashlib,io,json,pathlib,subprocess,zipfile
REPO='Hanjay6688/-erp-garment-ux';BRANCH='audit/astra-p20-2e605bb7-20261009'
def gh(path):return subprocess.check_output(['gh','api','repos/'+REPO+'/'+path])
requests=json.loads(pathlib.Path('audit/astra_p20/EVIDENCE_REQUESTS.json').read_text())
for rid in requests['run_ids']:
 meta=json.loads(gh('actions/runs/'+str(rid)))
 assert meta['head_branch']==BRANCH and meta['name'].startswith('Astra P20'),'OWN_RUNS_ONLY'
 arts=json.loads(gh(f'actions/runs/{rid}/artifacts?per_page=100'))['artifacts']
 for a in arts:
  if not a['name'].endswith('-json'):continue
  raw=gh('actions/artifacts/'+str(a['id'])+'/zip');z=zipfile.ZipFile(io.BytesIO(raw))
  rows=[]
  for name in z.namelist():
   if not name.endswith('.json'):continue
   content=z.read(name);d=json.loads(content)
   if name.startswith('ASTRA_AS20-') and 'audit_case_id' in d or name.startswith('ASTRA_AS20-') and 'case' in d:
    # Complete independent verdict, including first failure trace/witness.
    row=dict(file=name,sha256=hashlib.sha256(content).hexdigest(),complete_independent_verdict=d)
   elif isinstance(d,dict) and ('counts' in d or 'status' in d or 'gate' in d):
    row=dict(file=name,sha256=hashlib.sha256(content).hexdigest(),summary={k:d.get(k) for k in ('status','counts','expected_case_count','observed_case_count','error','traceback','restore','restore_error','cp6_restored','primary_unchanged','gate') if k in d},groups={})
    for kind in ('native','races','http','browser'):
     group=d.get(kind)
     if isinstance(group,dict):
      row['groups'][kind]={k:group.get(k) for k in ('status','counts','missing','planned_case_ids','planned_race_ids','complete_boundary_restored','database_remaining','error','traceback','cleanup_failures') if k in group}
      cases=group.get('cases') or group.get('races')
      if isinstance(cases,dict):row['groups'][kind]['cases']={k:{f:v.get(f) for f in ('status','error','counterexample','traceback') if f in v} for k,v in cases.items() if isinstance(v,dict)}
   else:continue
   rows.append(row)
  out=dict(run_id=rid,audit_sha=meta['head_sha'],product_sha='2e605bb7d9b6b7903919b8df2be1443f1740140b',artifact_id=a['id'],artifact_name=a['name'],zip_sha256=hashlib.sha256(raw).hexdigest(),records=rows)
  encoded=base64.b64encode(gzip.compress(json.dumps(out,ensure_ascii=False,default=str).encode())).decode()
  print('ASTRA_EVIDENCE_GZIP_BASE64 '+encoded,flush=True)
