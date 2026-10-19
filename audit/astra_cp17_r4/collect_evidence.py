import pathlib,json,hashlib,gzip,collections,tarfile,re
B=pathlib.Path('/workspace/scratch/67596acd38f5')
O=B/'erp-audit-r4/audit/astra_cp17_r4'
A=B/'r4-evidence/artifacts'
R=json.loads((O/'RUN_REGISTER.json').read_text())
manifest=json.loads((O/'CP17_PREDECLARED.json').read_text())
ledger=[]; checks=[]; rawindex=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gzwrite(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(d,mtime=0))
for run in R['runs']:
 for art in run['artifacts']:
  aid=art['id'];root=A/str(aid);z=A/(str(aid)+'.zip');assert sha(z)==art['digest'].split(':')[1]
  files=[p for p in root.glob('*.json')if p.name.startswith(('CP7','ASTRA'))]
  assert len(files)==1,files
  p=files[0];d=json.loads(p.read_text()); job=next((j for j in run['jobs'] if (run['suite']!='p19' or art['name'].endswith('-'+j['name']))),None); assert job
  origin='ASTRA' if run['suite'] in ('risk','paging','guard','own') else 'WRITER'
  start=len(ledger);group_checks=[]
  if run['suite']=='dom':
   for f in d['testResults']:
    ori='ASTRA' if '/audit/' in f['name'] else 'WRITER'
    for t in f['assertionResults']:
     ledger.append(dict(suite='dom',run_id=run['id'],job_id=job['id'],attempt=1,artifact_id=aid,group='dom',case=t['fullName'],raw_status=t['status'],protocol_status='PASS' if t['status']=='passed' else t['status'],oracle_origin=ori,fixture_origin=ori,evidence_kind='INDEPENDENT_DOM_RERUN',observed=t))
   assert len(ledger)-start==d['numTotalTests']==22
  else:
   for g in ('native','races','http','browser','browser_enteng'):
    if g not in d:continue
    v=d[g];cs=v.get('cases',v.get('races',{}));plan=v.get('planned_case_ids',v.get('planned_race_ids',[]))
    # Frozen harness reuses unsuffixed browser schedule, then labels Enteng observations.
    # External predeclared manifest already has the suffixed IDs: compare that as well.
    if g=='browser_enteng':plan=[x+'_ENTENG'for x in plan]
    decl=d.get('required_case_ids',{}).get(g,plan)
    assert len(cs)==len(plan)==len(set(plan)) and set(cs)==set(plan), (p,g,'runtime_plan')
    assert set(cs)==set(decl) and len(cs)==len(decl),(p,g,'declaration')
    if run['suite']=='cp17': assert set(cs)==set(manifest['required_case_ids'][g]) and len(cs)==manifest['required_case_counts'][g]
    group_checks.append(dict(group=g,count=len(cs),counts=dict(collections.Counter(x['status']for x in cs.values())),missing=[],extra=[],duplicates=[],plan_exact=True))
    for case,obs in cs.items():
     ledger.append(dict(suite=run['suite'],subsuite=d['label'],run_id=run['id'],job_id=job['id'],attempt=1,artifact_id=aid,group=g,case=case,raw_status=obs['status'],protocol_status=obs['status'],oracle_origin=origin,fixture_origin='WRITER_HELPERS_WITH_ASTRA_SCENARIO' if origin=='ASTRA' else 'WRITER',evidence_kind='INDEPENDENT_NATIVE_RERUN',source_sha256=d['source_sha256'],observed=obs))
   assert len(ledger)-start==d['expected_case_count']==d['observed_case_count'],p
   assert d['cp6_restored'] and d['advisor_gate'],p
  checks.append(dict(suite=run['suite'],artifact_id=aid,file=p.name,sha256=sha(p),run_id=run['id'],job_id=job['id'],job_conclusion=job['conclusion'],cases=len(ledger)-start,groups=group_checks,cp6_restored=d.get('cp6_restored'),advisor_gate=d.get('advisor_gate'),source_sha256=d.get('source_sha256')))
  gzwrite(O/'evidence'/f'{aid}_{p.name}.gz',p.read_bytes())
  # Keep full install/restore receipts in addition to the product scenario JSON.
  for extra in root.glob('*.json'):
   if extra!=p:gzwrite(O/'evidence'/f'{aid}_{extra.name}.gz',extra.read_bytes())
for p in sorted((B/'r4-evidence/own_logs').glob('*.log')):
 rawindex.append(dict(job_id=int(p.stem),file=p.name,bytes=p.stat().st_size,sha256=sha(p)))
assert len(rawindex)==18
with tarfile.open(O/'RAW_LOGS.tar.xz','w:xz')as tar:
 for p in sorted((B/'r4-evidence/own_logs').glob('*.log')):tar.add(p,arcname=p.name)
summary={'total_case_observations':len(ledger),'unique_ids':len(set(x['case']for x in ledger)),'by_oracle':{},'status_counts':dict(collections.Counter(x['protocol_status']for x in ledger)),'run_count':len(R['runs']),'job_count':len(rawindex),'checks':checks}
for origin in ('ASTRA','WRITER'):
 rows=[x for x in ledger if x['oracle_origin']==origin];summary['by_oracle'][origin]={'count':len(rows),'unique_ids':len(set(x['case']for x in rows)),'statuses':dict(collections.Counter(x['protocol_status']for x in rows))}
gzwrite(O/'CASE_LEDGER.json.gz',(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n').encode())
(O/'CASE_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
(O/'RAW_LOG_INDEX.json').write_text(json.dumps(rawindex,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items()if k!='checks'},indent=2))
for c in checks:print(c['file'],c['cases'],[(g['group'],g['count'],g['counts'])for g in c['groups']])
