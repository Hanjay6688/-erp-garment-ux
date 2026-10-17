"""Retain raw observations without relabelling failures or counting summaries twice."""
from pathlib import Path
import collections, gzip, hashlib, json, re, shutil, subprocess, tarfile

ROOT=Path(__file__).resolve().parent
EVID=ROOT.parents[2]/'r3-evidence'
ANSI=re.compile(r'\x1b\[[0-9;]*m')
RUNS={
 117455268044:(39053018929,'CP17_WRITER_ORACLE'),
 117455523095:(39053104594,'ASTRA_RETAINED_NATIVE'),
 117455522676:(39053104536,'ASTRA_DOM'),
 117455736534:(39053177754,'ASTRA_MATRIX_UAT'),
 117455736684:(39053177754,'ASTRA_MATRIX_DEMO'),
 117455736702:(39053177754,'ASTRA_MATRIX_TEST'),
 117456272451:(39053360685,'ASTRA_RISK'),
 117457024810:(39053620397,'ASTRA_PAGING'),
}
def dump(path,obj):
 data=(json.dumps(obj,ensure_ascii=False,indent=2,default=str)+'\n').encode()
 if path.suffix=='.gz':path.write_bytes(gzip.compress(data,mtime=0))
 else:path.write_bytes(data)
def parse(path):
 for n,line in enumerate(path.read_text().splitlines(),1):
  s=ANSI.sub('',re.sub(r'^\S+Z ','',line))
  try:d=json.loads(s)
  except ValueError:continue
  if isinstance(d,dict):yield n,d
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

attempts=[];summaries={};logs=[]
for job,(run,family) in RUNS.items():
 path=EVID/f'{job}.log'
 if not path.exists():continue
 logs.append(dict(path=path.name,job_id=job,run_id=run,bytes=path.stat().st_size,sha256=sha(path)))
 for line,d in parse(path):
  if str(d.get('case','')).startswith('ASTRA') and d.get('status'):
   attempts.append(dict(d,run_id=run,job_id=job,family=family,log_line=line,
     source_evidence_origin=d.get('evidence_origin'),evidence_origin='INDEPENDENT_NATIVE_RERUN',oracle_origin='ASTRA'))
  if d.get('label','').startswith('ASTRA_R3') or 'cp17' in str(d.get('label','')).lower():
   summaries.setdefault(str(job),[]).append(d)
ids=[d['case']for d in attempts]
assert len(ids)==len(set(ids)),[k for k,v in collections.Counter(ids).items()if v>1]
counts=dict(collections.Counter(d['status']for d in attempts))
assert len(ids)==302 and counts=={'PASS':298,'COUNTEREXAMPLE':4},(len(ids),counts)
dump(ROOT/'INDEPENDENT_CASES.json.gz',attempts)
dump(ROOT/'CASE_COUNTS.json',dict(astra_unique_cases=len(ids),astra_observations=len(attempts),
 counts=counts,by_family={f:dict(collections.Counter(d['status']for d in attempts if d['family']==f))for f in sorted({d['family']for d in attempts})},
 note='282 entry render/menu/layout assertions; not 282 full transaction journeys. CP17 writer-oracle rerun counted separately. No after-case retry.'))
dump(ROOT/'RUNTIME_SUMMARIES.json.gz',summaries)
dump(ROOT/'RAW_LOG_INDEX.json',logs)
with tarfile.open(ROOT/'RAW_LOGS.tar.xz','w:xz')as t:
 for item in logs:t.add(EVID/item['path'],arcname=item['path'])
writer=[]
for path in sorted((EVID/'writer-logs').glob('*.log')):
 writer.append(dict(run_id=int(path.stem),bytes=path.stat().st_size,sha256=sha(path)))
dump(ROOT/'WRITER_RAW_LOG_INDEX.json',writer)
with tarfile.open(ROOT/'WRITER_RAW_LOGS.tar.xz','w:xz')as t:
 for path in sorted((EVID/'writer-logs').glob('*.log')):t.add(path,arcname=path.name)
for source,target in [('writer_receipt.json','WRITER_RECEIPT.json.gz'),('writer_failure_review.json','WRITER_FAILURE_REVIEW.json.gz'),('candidate_runs_page1.json','WRITER_API_PAGE1.json.gz'),('candidate_runs_page2.json','WRITER_API_PAGE2.json.gz')]:
 dump(ROOT/target,json.loads((EVID/source).read_text()))
for folder,name in [('retained-artifact','ASTRA_R3_RETAINED_NATIVE.json'),('risk-artifact','ASTRA_R3_RISK.json'),('paging-artifact','ASTRA_R3_AUDIT_PAGING.json'),('matrix-uat-artifact','ASTRA_R3_matrix-UAT_AUTH_SIMULATION.json')]:
 p=EVID/folder/name
 if p.exists():dump(ROOT/(name+'.gz'),json.loads(p.read_text()))
scenario=[d for _,d in parse(EVID/'writer-logs/39044984302.log')if d.get('case')and d.get('status')]
assert len(scenario)==170
dump(ROOT/'WRITER_CP6_SCENARIO_CASES.json.gz',scenario)
shutil.copyfile(EVID/'prior/audit/astra_cp17_r2/T2_DISPOSITION.json',ROOT/'RETAINED_R2_T2_DISPOSITION.json')
print(json.dumps(dict(astra_cases=len(ids),counts=counts,own_job_logs=len(logs),writer_failure_logs=len(writer),writer_scenario=dict(collections.Counter(c['status']for c in scenario)))))
