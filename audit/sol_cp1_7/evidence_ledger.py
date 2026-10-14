"""Index original raw case observations, retaining red outcomes and aliases."""
import collections,hashlib,json
from pathlib import Path
E=Path(__file__).parent/'evidence';meta={str(x['id']):x for x in json.loads((E/'ARTIFACT_REGISTER.json').read_text())}
reports={};groups=[];cases=[]
for p in sorted((E/'original-reports').rglob('*')):
 if not p.is_file():continue
 raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest();rel=str(p.relative_to(E/'original-reports'));aid=rel.split('/')[0]
 reports.setdefault(sha,dict(sha256=sha,bytes=len(raw),aliases=[]))['aliases'].append(dict(path=rel,artifact_id=int(aid),run_id=meta[aid]['scan_run']))
 if len(reports[sha]['aliases'])>1:continue
 try:d=json.loads(raw)
 except:continue
 def row(cid,r,ptr):
  cases.append(dict(case_id=cid,status=r['status'],report=rel,report_sha256=sha,pointer=ptr,artifact_id=int(aid),run_id=meta[aid]['scan_run'],full_boundary_restored=r.get('full_boundary_restored'),session_leaks=r.get('session_leaks'),evidence_origin=r.get('evidence_origin','INDEPENDENT_EXECUTION; scope in original'),oracle_origin=r.get('oracle_origin','UNCHANGED_PREEXISTING_PROVIDER'),fixture_origin=r.get('fixture_origin','UNCHANGED_PREEXISTING_PROVIDER'),Native_execution_credit=None,credit_note='Observation only; reused results, repeats, kernels and controls are not a new unique-oracle total.'))
 def walk(v,ptr=''):
  if isinstance(v,dict):
   if 'case_id'in v and'status'in v and'cases'not in v and'races'not in v:row(v['case_id'],v,ptr)
   for key in ('cases','races'):
    rs=v.get(key)
    if isinstance(rs,dict):a=[(k,x)for k,x in rs.items()if isinstance(x,dict)and'status'in x]
    elif isinstance(rs,list):a=[(x.get('id',x.get('case_id',str(i))),x)for i,x in enumerate(rs)if isinstance(x,dict)and'status'in x]
    else:continue
    if not a:continue
    ids=[k for k,_ in a];plan=v.get('planned_case_ids',v.get('planned_race_ids'))
    groups.append(dict(report=rel,report_sha256=sha,pointer=ptr+'/'+key,status=v.get('status'),counts=dict(collections.Counter(x['status']for _,x in a)),planned=plan,actual=ids,exact_set=plan is not None and set(plan)==set(ids)and len(plan)==len(set(plan)),complete_boundary_restored=v.get('complete_boundary_restored'),database_remaining=v.get('database_remaining')))
    for cid,x in a:row(cid,x,ptr+'/'+key+'/'+str(cid))
   for k,x in v.items():
    if k not in ('cases','races','expected','actual','before','after','runtime_before','runtime_after','snapshot','catalog'):walk(x,ptr+'/'+k)
  elif isinstance(v,list):
   for i,x in enumerate(v):walk(x,ptr+'/'+str(i))
 walk(d)
for n,x in [('REPORT_IDENTITIES',list(reports.values())),('GROUP_LEDGER',groups),('CASE_LEDGER',cases)]: (E/(n+'.json')).write_text(json.dumps(x,indent=2)+'\n')
print(json.dumps(dict(original_files=sum(len(x['aliases'])for x in reports.values()),unique_byte_reports=len(reports),groups=len(groups),case_observations=len(cases),unique_oracle_total_claim=False,raw_statuses=dict(collections.Counter(x['status']for x in cases)))))
