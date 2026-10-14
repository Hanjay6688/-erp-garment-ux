"""Index immutable Originals. Preserve raw statuses and executed/carried provenance."""
import contextlib,io,json,pathlib,collections,runpy,hashlib
ROOT=pathlib.Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()): base=runpy.run_path(str(ROOT/'build_case_ledger.py'))
rows=base['rows']; reports=base['reports'];issues=base['issues']
def add(path,run,artifact,group,origin='INHERITED_ORACLE_ASTRA_EXECUTION',cases=None):
 p=ROOT/path;o=json.loads(p.read_text());c=cases if cases is not None else o['cases'];start=len(rows)
 carried=set(o.get('carried_case_ids',[]))
 for k,v in c.items():
  rows.append(dict(run_id=38523724159 if k in carried else run,artifact_id=11874823769 if k in carried else artifact,original=('evidence/38523724159/11874823769/original/BUSINESS.json' if k in carried else str(p.relative_to(ROOT))),canonical_report=str(p.relative_to(ROOT)),canonical_report_artifact_id=artifact,group=group,case_id=k,status=v.get('status'),oracle_origin=origin,carried_first_execution=k in carried,full_boundary_restored=v.get('full_boundary_restored'),public_schema_unchanged=v.get('public_schema_unchanged'),session_leaks=v.get('session_leaks'),business_day=v.get('business_day')))
 reports.append(dict(run_id=run,artifact_id=artifact,original=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),status=o.get('status'),cases=len(rows)-start,carried=len(carried),counts=dict(collections.Counter(v.get('status')for v in c.values()))))
 if cases is None:
  missing=set(o.get('planned_case_ids',list(c)))-set(c)
  if missing:issues.append(dict(file=str(p),missing=sorted(missing)))
r='evidence/38526619037/11876692954/original/'
for f in ['BUSINESS','IMPORTS','VALUES','NEW_CASES','AO_TRIAL','APPROVED_ORACLE_B']:add(r+f+'.json',38526619037,11876692954,f)
a='evidence/38523724159/11874359808/original/'
for f in ['AR_SEQUENTIAL','AR_SUPERSEDING']:add(a+f+'.json',38523724159,11874359808,f)
t='evidence/38523724159/raw/'
for f in ['AT_CASES','AU_CASES']:add(t+f+'.json',38523724159,11875343186,f)
p=t+'CP17_BASELINE_TEMPORAL.json';o=json.loads((ROOT/p).read_text())
for group in ['temporal_races','master_races']:add(p,38523724159,11875343186,group,cases=o[group])
add('evidence/38526619037/11876663532/original/CP17_BASELINE_AR-RACES-ONLY.json',38526619037,11876663532,'AR_RACES')
c0=list((ROOT/'evidence/38529725289/11877329725/original').glob('T2_C0_ORACLE.json'))
if len(c0)==1:add(str(c0[0].relative_to(ROOT)),38529725289,int(c0[0].parents[1].name),'C0_ORACLES','ASTRA_PINNED_C0_ORACLE_EXECUTION')
else:issues.append(dict(problem='C0_ORIGINAL_NOT_PRESENT',found=len(c0)))
reg=json.loads((ROOT/r/'CP17_BASELINE_CONTINUED-REGRESSION.json').read_text())
dispositions=[]
for i,row in enumerate(rows,1):
 row['execution_index']=i
 if row['status']=='PASS':continue
 k=row['case_id'];g=row['group'];d=dict(execution_index=i,group=g,case_id=k,raw_status=row['status'],run_id=row['run_id'],original=row['original'])
 if k.startswith('CP17-ASTRA-PAY-'):
  d.update(disposition='CONFIRMED_PRODUCT_DEFECT',finding='ASTRA-CP17-FIN-01',severity='S0')
 elif k=='AS20-39_VALIDATION_NEGATIVE':
  d.update(disposition='PREVIOUSLY_ACCEPTED_DETECTOR_BOUNDARY',reason='The old direct semantic-corruption probe remains COUNTEREXAMPLE; accepted CP7 staged-validator limitation. No new public-command defect inferred.',evidence='Prior Astra e800e016 report and current full Original')
 elif row['status']=='CONTROL_PASS':
  d.update(disposition='FROZEN_CONTROL_PASS_RETAINED',reason='Control result is successful in the frozen contract; not silently renamed PASS.')
 elif g=='BUSINESS' and row['status']=='DATE_POLICY_REVIEW_REQUIRED':
  d.update(disposition='OWNER_ACCEPTED_HOLD_RETAINED',approved_comparator=reg['calendar_policy'][k]['approved_oracle_20260924b'],reason='Owner24Sep/C6: transfer to WIP uses cutting date; historical HOLD remains.')
 elif g=='NEW_CASES' and k in reg['approved_oracle_20260924']['results']:
  d.update(disposition='APPROVED_DATE_ORACLE_MATCH_RAW_COUNTEREXAMPLE_RETAINED',approved_status=reg['approved_oracle_20260924']['results'][k],decision='Owner24Sep: dated stage-value transfer policy; not an extra execution of this case.')
 elif (g=='NEW_CASES' and k=='ADJUSTMENT_DATE:False') or g=='AO_TRIAL':
  key=('AS:' if g=='NEW_CASES' else 'AO:')+k
  d.update(disposition='EXPECTED_ORACLE_CHANGE_ORIGINAL_INCOMPLETE_RETAINED',approved_comparator=reg['approved_oracle_20260924b']['cases'][key],supplement_group='APPROVED_ORACLE_B')
 elif g=='AR_SEQUENTIAL' and k=='ACCESSORY_CONNECTED_ZERO':
  d.update(disposition='EXPECTED_CHANGE_ERP_DEC02',replacement='AR_SUPERSEDING:ACCESSORY_CONNECTED_ZERO_REFUSED_BC_FREE_POLICY',reason='Zero accessory must refuse absent explicit FREE/Special policy; replacement passed with BC_FREE_REQUIRES_POLICY.')
 else:d.update(disposition='UNRESOLVED');issues.append(d)
 row['disposition']=d['disposition'];dispositions.append(d)
result=dict(candidate_sha='0b7049d9203bac52b47a4c89f3e0d75646067a8f',partial=bool(issues),scope='Canonical current-round case executions only; no CP1/static checks/P21 steps/old-round carry counted as business cases',executions=len(rows),unique_case_ids=len(set(r['case_id']for r in rows)),counts=dict(collections.Counter(r['status']for r in rows)),origins=dict(collections.Counter(r['oracle_origin']for r in rows)),carried_without_rerun=sum(bool(r.get('carried_first_execution'))for r in rows),reports=reports,issues=issues,rows=rows)
(ROOT/'CASE_LEDGER_FINAL.json').write_text(json.dumps(result,indent=2)+'\n');(ROOT/'NONPASS_DISPOSITIONS.json').write_text(json.dumps(dispositions,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items()if k not in ('rows','reports')},indent=2));print('dispositions',len(dispositions),dict(collections.Counter(d['disposition']for d in dispositions)))
