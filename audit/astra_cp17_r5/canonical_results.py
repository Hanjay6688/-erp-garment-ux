"""Keep attempt history and select explicitly qualified outcomes, with artifact cross-checks."""
from pathlib import Path
from collections import Counter,defaultdict
import json,gzip,hashlib
P=Path(__file__).resolve().parent
ROOTS={
 'cp17':('raw/cp17-full/CP7_CP17_FIXES.json','CP17_PREDECLARED.json'),
 'p19-scale':('raw/p19-scale-original/CP7_P19_SCALE.json','P19_SCALE_PREDECLARED.json'),
 'p19-transport':('raw/p19-transport-original/CP7_P19_TRANSPORT.json','P19_TRANSPORT_PREDECLARED.json'),
 'p19-report':('raw/p19-report-original/CP7_P19_REPORT_V2.json','P19_REPORT_V2_PREDECLARED.json'),
 'own-first':('raw/own-first/ASTRA_R5_OWN.json','OWN_PREDECLARED.json'),
 'own-q2':('raw/own-q2/ASTRA_R5_OWN_Q2.json','Q2_PREDECLARED.json'),
}
def main():
 ledger=[json.loads(x) for x in gzip.decompress((P/'CASE_LEDGER.jsonl.gz').read_bytes()).decode().splitlines()]
 proof=[]
 for suite,(file,manifest) in ROOTS.items():
  if not (P/file).exists():proof.append(dict(suite=suite,status='PENDING',file=file));continue
  d=json.loads((P/file).read_text());m=json.loads((P/manifest).read_text());expected={('races' if k.lower()=='race' else k.lower()):v for k,v in m['required_case_ids'].items()}
  rows=[r for r in ledger if r['suite']==suite];observed={};checks={}
  for layer,ids in expected.items():
   group=d[layer];actual=group.get('races' if layer=='races' else 'cases',{})
   assert set(actual)==set(ids),(suite,layer,'ARTIFACT_ID_MISMATCH')
   for id,row in actual.items():
    log=[x for x in rows if x['layer']==layer and x['id']==id]
    assert len(log)==1 and log[0]['original_status']==row['status'],(suite,layer,id,'LOG_ARTIFACT_MISMATCH')
    observed[layer+':'+id]=row['status']
   checks[layer]=dict(status=group.get('status'),counts=group.get('counts'),database_remaining=group.get('database_remaining'),cleanup_failures=group.get('cleanup_failures'),complete_boundary_restored=group.get('complete_boundary_restored'))
  assert len(observed)==m['expected_case_count']==d['observed_case_count'],suite
  assert d.get('cp6_restored') and d.get('advisor_gate'),(suite,'RESTORE_OR_ADVISOR')
  proof.append(dict(suite=suite,status='CROSSCHECKED',runtime_status=d['status'],file=file,file_sha256=hashlib.sha256((P/file).read_bytes()).hexdigest(),expected=m['expected_case_count'],observed=len(observed),counts=dict(Counter(observed.values())),groups=checks,restore_components=d.get('restore_components'),advisor_delta=dict(status=d['advisor_delta'].get('status'),added_count=len(d['advisor_delta'].get('added',[])),added_kinds=sorted({(x['name'],x['level']) for x in d['advisor_delta'].get('added',[])}))))
 by=defaultdict(list)
 for r in ledger:by[('own' if r['suite'].startswith('own') else r['suite'],r['layer'],r['id'])].append(r)
 canonical=[]
 for key,attempts in sorted(by.items()):
  q=[x for x in attempts if x['suite']=='own-q2'];chosen=q[0] if q else attempts[0]
  if q:
   assert len(attempts)==2 and q[0]['original_status']=='PASS'
   assert next(x for x in attempts if x['suite']=='own-first')['original_status']=='INCOMPLETE'
  else:assert len(attempts)==1,key
  canonical.append(dict(suite=key[0],layer=key[1],id=key[2],status=chosen['protocol_status'],selected_run=chosen['run_id'],selected_job=chosen['job_id'],qualification='Q2_AUDITOR_TOOL; expected/IDs unchanged; original INCOMPLETE retained' if q else None,attempts=[{k:r[k] for k in ['suite','run_id','run_attempt','job_id','original_status','protocol_status','log_file','log_line','recorded_at']} for r in attempts]))
 result=dict(candidate_sha='17fa25075ba77f0853c3c16f504288ace03eec35',expected_unique_coverage_slots=396,observed_unique_coverage_slots=len(canonical),unique_counts=dict(Counter(x['status'] for x in canonical)),expected_executions_including_new_qualification=398,observed_executions=len(ledger),raw_status_counts=dict(Counter(x['original_status'] for x in ledger)),job_reruns=0,tool_qualifications=1,oracle_origin_counts=dict(new_Astra_contract_cases=11,writer_or_inherited_oracle_coverage_slots=385),retained_r4_cases_not_added=565,status='RECONCILED' if len(canonical)==396 and all(x['status']=='CROSSCHECKED' for x in proof) else 'PENDING',artifact_crosschecks=proof,cases=canonical)
 (P/'CANONICAL_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ['cases','artifact_crosschecks']},indent=2))
if __name__=='__main__':main()
