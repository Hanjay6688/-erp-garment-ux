"""Read complete per-job Original JSON. Names such as 'transport11' are labels, not case counts."""
from pathlib import Path
from collections import Counter
import json,hashlib
ROOT=Path(__file__).resolve().parent
E=ROOT/'evidence';reports=[];executions=[];smoke=[];diagnostics=[]
for folder in sorted(E.glob('cp7retest-astra-7a0b4a90-*-json')):
    if '-own-' in folder.name:continue
    suite=folder.name.removeprefix('cp7retest-astra-7a0b4a90-').removesuffix('-json')
    primary=[]
    for f in folder.glob('CP7*.json'):
        d=json.loads(f.read_text())
        if 'expected_case_count' in d or f.name in ('CP7_P21_FULL_REHEARSAL.json','CP7_P12_SETTLEMENT.json'):primary.append((f,d))
    assert len(primary)==1,(suite,[f.name for f,d in primary])
    f,d=primary[0];case_rows=[];smoke_rows=[]
    assert d.get('status')=='PASS' and not d.get('error'),(suite,'TOP_LEVEL_NOT_PASS')
    assert d.get('cp6_restored') is True and d.get('advisor_gate') is True,(suite,'RESTORE_OR_ADVISOR_GATE')
    groups=d.get('groups') or {k:v for k,v in d.items() if isinstance(v,dict) and 'counts' in v and ('cases'in v or 'races'in v)}
    smoke_keys={g['key'] for g in d.get('predeclared_groups',[])if g.get('smoke')}
    group_gates=[]
    for group,g in groups.items():
        rows=g.get('cases',g.get('races',{}))
        assert isinstance(rows,dict),(suite,group)
        assert dict(Counter(r.get('status')for r in rows.values()))==g.get('counts'),(suite,group,'COUNTS_MISMATCH')
        planned=g.get('planned_case_ids',g.get('planned_race_ids'))
        if planned is not None:
            assert len(planned)==len(set(planned)) and set(planned)==set(rows),(suite,group,'PLANNED_IDS_MISMATCH')
        # The Original explicitly gives these admission controls zero required-case credit.
        # Preserve their complete results separately; do not inflate the family total.
        if d.get(group+'_required_case_credit') == 0:
            diagnostics.append(dict(suite=suite,name=group,classification='SOURCE_ADMISSION_ZERO_CREDIT',product_case_credit=0,counts=g.get('counts'),original=g))
            continue
        assert g.get('status') in ('PASS','RUN_COMPLETE') and not g.get('error') and not g.get('missing'),(suite,group,'GROUP_GATE')
        for flag in ('complete_boundary_restored',):
            if flag in g:assert g[flag] is True,(suite,group,flag)
        assert not g.get('database_remaining',0) and not g.get('cleanup_failures') and not g.get('auth_cleanup_failures') and not g.get('console_errors'),(suite,group,'CLEANUP_GATE')
        if 'restored' in g.get('auth_counts',{}):assert g['auth_counts']['restored'] is True
        if group in d.get('required_case_counts',{}):assert g['counts']=={'PASS':d['required_case_counts'][group]},(suite,group,'REQUIRED_COUNTS')
        group_gates.append(dict(group=group,status=g.get('status'),error=g.get('error'),missing=g.get('missing',[]),complete_boundary_restored=g.get('complete_boundary_restored'),database_remaining=g.get('database_remaining'),cleanup_failures=g.get('cleanup_failures'),auth_restored=g.get('auth_counts',{}).get('restored'),business_day_retried=g.get('business_day_retried',False)))
        for case,r in rows.items():
            assert r.get('status')=='PASS' and not r.get('error'),(suite,group,case,'CASE_NOT_PASS')
            for flag in ('full_boundary_restored','public_schema_unchanged'):
                if flag in r:assert r[flag] is True,(suite,group,case,flag)
            leaks=r.get('session_leaks')
            assert leaks is None or leaks==[] or leaks=={'advisory_locks':0,'advisory_lock_keys':[],'other_sessions':[]},(suite,group,case,'SESSION_LEAKS')
            row=dict(suite=suite,group=group,id=case,status=r.get('status'),error=r.get('error'),business_day_rollover=r.get('business_day_rollover',False),full_boundary_restored=r.get('full_boundary_restored'),public_schema_unchanged=r.get('public_schema_unchanged'),session_leaks=r.get('session_leaks'))
            (smoke_rows if group in smoke_keys else case_rows).append(row)
    if 'expected_case_count' in d:
        assert len(case_rows)==d['observed_case_count']==d['expected_case_count'],(suite,'EXECUTIONS_MISMATCH',len(case_rows),d.get('observed_case_count'),d['expected_case_count'])
        if 'expected_smoke_count'in d:assert len(smoke_rows)==d['observed_smoke_count']==d['expected_smoke_count']
    elif f.name=='CP7_P12_SETTLEMENT.json':
        # This pinned writer probe declares group/ID inventories, not an aggregate count.
        declared=('native','http','notes','note_races','note_http','admission_regression','browser','payroll_review','payroll_review_http','payroll_review_browser','settlement','settlement_races','settlement_http','settlement_browser')
        assert set(groups)==set(declared),(suite,'PAYROLL_GROUP_INVENTORY')
        assert all(g.get('planned_case_ids',g.get('planned_race_ids')) is not None for g in groups.values())
    for name,observation in d.get('runtime_diagnostics',{}).items():
        v=observation.get('result',{});diagnostics.append(dict(suite=suite,name=name,classification=observation.get('classification'),product_case_credit=observation.get('product_case_credit'),counts=v.get('counts'),original=v))
    reports.append(dict(suite=suite,file=str(f.relative_to(ROOT)),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),status=d.get('status'),case_executions=len(case_rows),smoke_executions=len(smoke_rows),counts=dict(Counter(r['status']for r in case_rows)),cp6_restored=d.get('cp6_restored'),advisor_gate=d.get('advisor_gate'),error=d.get('error'),groups=group_gates,rehearsal_phases=[{k:v for k,v in s.items()if k in ('step','status','restored_exactly','identical_to_first','catalog_restored')}for s in d.get('steps',[])]))
    executions.extend(case_rows);smoke.extend(smoke_rows)
summary=dict(product_sha='7a0b4a90af234a906d3cda7fc8ec9fd411a15dd2',origin='INDEPENDENT_NATIVE_RERUN',oracle_origin='WRITER_UNCHANGED',fixture_origin='WRITER_UNCHANGED',reports=len(reports),counts=dict(Counter(r['status']for r in executions)),case_executions=len(executions),unique_case_ids=len({r['id']for r in executions}),smoke_executions=len(smoke),diagnostic_executions=sum(sum(d.get('counts',{}).values())for d in diagnostics),rehearsal_phases=sum(len(r['rehearsal_phases'])for r in reports),production_go=False)
(ROOT/'REGRESSION_RESULTS.json').write_text(json.dumps(dict(summary=summary,reports=reports,case_executions=executions,smoke=smoke,diagnostics=diagnostics),indent=2)+'\n')
print(json.dumps(summary))
print(json.dumps([dict(suite=r['suite'],status=r['status'],count=r['case_executions'],restore=r['cp6_restored'],advisor=r['advisor_gate'])for r in reports]))
