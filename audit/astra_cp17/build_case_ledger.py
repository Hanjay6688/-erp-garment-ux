"""Read canonical Originals only; never infer PASS from a green GitHub job.

Rows retain per-case observations verbatim in their referenced Original. Same
case names in different groups remain distinct executions; duplicate zip copies
are excluded by choosing JSON artifacts over raw artifacts from the same run.
"""
from collections import Counter
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
rows=[];reports=[];issues=[]
def ingest(report,path,run,artifact,origin):
    groups=report.get('groups') or {k:v for k,v in report.items() if isinstance(v,dict) and isinstance(v.get('cases',v.get('races')),dict)}
    if 'cases' in report:groups={'native':report}
    count=0
    for name,g in groups.items():
        if not isinstance(g,dict):continue
        cases=g.get('cases',g.get('races',{}))
        if not isinstance(cases,dict):
            issues.append(dict(file=str(path),group=name,problem='UNRECOGNIZED_CASE_SHAPE'));continue
        planned=g.get('planned_case_ids',g.get('planned_race_ids',list(cases)))
        missing=sorted(set(planned)-set(cases));unexpected=sorted(set(cases)-set(planned))
        if missing or unexpected:issues.append(dict(file=str(path),group=name,missing=missing,unexpected=unexpected))
        for key,v in cases.items():
            status=v.get('status') if isinstance(v,dict) else None
            row=dict(run_id=run,artifact_id=artifact,original=str(path.relative_to(ROOT)),group=name,case_id=key,status=status,oracle_origin=origin,
                full_boundary_restored=v.get('full_boundary_restored'),public_schema_unchanged=v.get('public_schema_unchanged'),session_leaks=v.get('session_leaks'),business_day=v.get('business_day'))
            rows.append(row);count+=1
        declared=g.get('counts')
        if declared and dict(Counter(v.get('status') for v in cases.values()))!=declared:
            issues.append(dict(file=str(path),group=name,problem='DECLARED_COUNTS_MISMATCH',declared=declared))
    expected=report.get('expected_case_count')
    # F03 expected total includes explicitly declared smoke executions in groups.
    extra_smoke=report.get('expected_smoke_count',0)
    if not extra_smoke and 'composition_smoke' in groups:extra_smoke=len(groups['composition_smoke'].get('cases',{}))
    if expected is not None and count!=expected+extra_smoke:issues.append(dict(file=str(path),problem='TOTAL_MISMATCH',expected=expected,smoke=extra_smoke,observed=count))
    reports.append(dict(run_id=run,artifact_id=artifact,original=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),status=report.get('status'),cases=count,expected=expected,
        cp6_restored=report.get('cp6_restored'),advisor_gate=report.get('advisor_gate'),groups_complete=report.get('groups_complete')))
for run in ('38522545215','38525930341','38525930407','38527771239'):
    for directory in sorted((ROOT/'evidence'/run).glob('*')):
        if not directory.is_dir():continue
        receipt=directory/'receipt.json'
        if not receipt.exists():continue
        meta=json.loads(receipt.read_text())
        if not meta['name'].endswith('-json'):continue
        pattern='CP7*.json' if run=='38522545215' else 'CP17_OWN*.json'
        for path in sorted((directory/'original').glob(pattern)):
            if 'PREEXECUTION_PLAN' in path.name:continue
            report=json.loads(path.read_text())
            origin='WRITER_ORACLE_ASTRA_EXECUTION' if run=='38522545215' else ('ASTRA_PREEXISTING_CONTRACT' if run=='38525930341' else ('ASTRA_NEW_INTEGRATION_AND_ATTRIBUTED_LEADS' if run=='38527771239' else 'ASTRA_AFTER_FABLE_LEAD'))
            ingest(report,path,int(run),int(directory.name),origin)
result=dict(candidate_sha='0b7049d9203bac52b47a4c89f3e0d75646067a8f',partial=True,scope='Downloaded native + own + payroll canonical JSON artifacts only; legacy baseline/carry/continuations tracked separately until complete',counts=dict(Counter(r['status'] for r in rows)),executions=len(rows),unique_case_ids=len(set(r['case_id'] for r in rows)),origins=dict(Counter(r['oracle_origin'] for r in rows)),reports=reports,issues=issues,rows=rows)
(ROOT/'CASE_LEDGER_PARTIAL.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items()if k not in ('rows','reports')},indent=2))
print('NONPASS',json.dumps([r for r in rows if r['status']!='PASS'],indent=2))
