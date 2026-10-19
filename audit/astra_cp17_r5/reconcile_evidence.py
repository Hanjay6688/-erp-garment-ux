"""Reconcile archived first-run JSON lines against the pre-run manifests.
No product execution; preserve all case attempts and original statuses.
"""
from pathlib import Path
from collections import Counter
import json,re,hashlib,gzip
ROOT=Path(__file__).resolve().parent
CONFIG=[
 ('cp17','CP17_PREDECLARED.json','cp17-118011530224.log',39237954632,118011530224),
 ('p19-scale','P19_SCALE_PREDECLARED.json','p19-scale-118011792249.log',39238034877,118011792249),
 ('p19-transport','P19_TRANSPORT_PREDECLARED.json','p19-transport-118011792307.log',39238034877,118011792307),
 ('p19-report','P19_REPORT_V2_PREDECLARED.json','p19-report-118011792477.log',39238034877,118011792477),
 ('own-first','OWN_PREDECLARED.json','own-first-118013182781.log',39238457513,118013182781),
 ('own-q2','Q2_PREDECLARED.json','own-q2-118017734464.log',39239850748,118017734464),
]
def layer_of(group):
 g=group.upper()
 if 'BROWSER' in g:return 'browser_enteng' if 'ENTENG' in g else 'browser'
 if 'HTTP' in g:return 'http'
 if 'RACES' in g:return 'races'
 return 'native'
def run():
 all_rows=[];summaries=[]
 for suite,manifest,log,run_id,job_id in CONFIG:
  m=json.loads((ROOT/manifest).read_text());required={('races' if k.lower()=='race' else k.lower()):v for k,v in m['required_case_ids'].items()}
  expected={(layer,id) for layer,ids in required.items() for id in ids};path=ROOT/'raw'/log
  if not path.exists():summaries.append(dict(suite=suite,status='PENDING',expected=len(expected)));continue
  rows=[]
  for lineno,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
   match=re.match(r'^(\d{4}-\d\d-\d\dT\S+Z) (\{.*)$',line)
   if not match:continue
   try:obj=json.loads(match[2])
   except json.JSONDecodeError:continue
   if not ('group' in obj and 'case' in obj):continue
   layer=layer_of(obj['group']);canonical_id=obj['case'];id_mapping=None
   if layer=='browser_enteng' and (layer,canonical_id) not in expected and (layer,canonical_id+'_ENTENG') in expected:
    canonical_id+='_ENTENG';id_mapping='Candidate cp7_cp17_fix_probe.py:63 appends _ENTENG in its artifact after the browser host logs the base ID; raw ID retained.'
   key=(layer,canonical_id)
   if key not in expected:continue
   own=suite.startswith('own')
   row=dict(suite=suite,layer=layer,id=canonical_id,raw_case_id=obj['case'],id_mapping=id_mapping,original_status=obj.get('status'),protocol_status=obj.get('status'),group=obj['group'],run_id=run_id,run_attempt=1,job_id=job_id,log_file='raw/'+log,log_line=lineno,recorded_at=match[1],evidence_origin='INDEPENDENT_NATIVE_RERUN',oracle_origin='ASTRA_INDEPENDENT_CONTRACT_EXPECTED' if own else 'REUSED_WRITER_OR_INHERITED_AUDITOR_ORACLE_EXECUTED_INDEPENDENTLY',fixture_origin='Accepted Native fixture builders reused; extra reader fixture copied from frozen writer; private corruption diagnostic only' if own else 'Frozen candidate fixture and oracle source',fixture_definition_identity=dict(candidate_sha='17fa25075ba77f0853c3c16f504288ace03eec35',manifest=manifest,manifest_sha256=hashlib.sha256((ROOT/manifest).read_bytes()).hexdigest(),auditor_source_hashes=m.get('source_sha256',m.get('files'))),fixture_hash_scope='Definition/predeclaration, not a claim that every generated UUID is hashed separately',raw=obj)
   rows.append(row);all_rows.append(row)
  counts=Counter((r['layer'],r['id']) for r in rows)
  missing=sorted(expected-set(counts));duplicates=[dict(layer=k[0],id=k[1],count=v) for k,v in counts.items() if v!=1]
  summaries.append(dict(suite=suite,run_id=run_id,job_id=job_id,status='RECONCILED' if not missing and not duplicates else 'INCOMPLETE',expected=len(expected),observed=len(rows),counts=dict(Counter(r['original_status'] for r in rows)),missing=missing,duplicates=duplicates,manifest_sha256=hashlib.sha256((ROOT/manifest).read_bytes()).hexdigest(),log_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
 out=dict(candidate_sha='17fa25075ba77f0853c3c16f504288ace03eec35',summaries=summaries,execution_count=len(all_rows),counts=dict(Counter(x['original_status'] for x in all_rows)),unique_coverage_key='suite family + layer + id; own-q2 is qualification of same own-first IDs, not extra product coverage',all_first_failures_preserved=True)
 (ROOT/'RECONCILIATION.json').write_text(json.dumps(out,indent=2)+'\n')
 data=''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in all_rows).encode()
 (ROOT/'CASE_LEDGER.jsonl.gz').write_bytes(gzip.compress(data,mtime=0))
 print(json.dumps(out,indent=2))
if __name__=='__main__':run()
