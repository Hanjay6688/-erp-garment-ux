"""Index only complete canonical Originals; preserve every first raw status."""
from pathlib import Path
import json,hashlib,collections
ROOT=Path(__file__).resolve().parent
rows=[];reports=[];issues=[];dispositions=[]
def ingest(p,run,artifact,groups,outer):
    n=0
    for group,g in groups.items():
        cases=g.get('cases',g.get('races',{}))
        if not isinstance(cases,dict):continue
        planned=g.get('planned_case_ids',g.get('planned_race_ids',list(cases)))
        if set(planned)!=set(cases):issues.append(dict(original=str(p.relative_to(ROOT)),group=group,planned=planned,observed=list(cases)))
        for key,v in cases.items():
            row=dict(run_id=run,artifact_id=artifact,original=str(p.relative_to(ROOT)),group=group,case_id=key,status=v.get('status'),
                oracle_origin=('ASTRA_AFTER_AUTHORIZED_FABLE_EXPOSURE' if key.startswith(('CP17-ASTRA-R3-','CP17-ASTRA-CLAIM-','CP17-ASTRA-POOL-')) else 'ASTRA_NEW_OBSERVATION' if key.startswith('CP17-ASTRA-FIN-07') else 'INHERITED_ORACLE_ASTRA_EXECUTION'),
                original_case_sha256=hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                full_boundary_restored=v.get('full_boundary_restored'),public_schema_unchanged=v.get('public_schema_unchanged'),
                status_outside_vocabulary=v.get('status_outside_vocabulary'))
            if row['status']!='PASS':
                if v.get('status_outside_vocabulary') in ('OBSERVED','CONTROL_PASS'):
                    row.update(disposition='Q08_ORIGINAL_OBSERVATION_OR_CONTROL_VOCABULARY_RETAINED',observation_status=v['status_outside_vocabulary'])
                elif key in ('B04:LATE_INVOICE_JAKARTA','B04:LATE_INVOICE_KIRITIMATI','P07:PROCESSED_AFTER_CLOSE'):
                    row.update(disposition='Q09_SUPERSEDED_AW_PRE_BA_FILING_ORACLE',current_contract='BA W9/C0 D01 3.4: later correction marker stays true after recost; BA W9 positive and negative controls PASS')
                elif key in ('ALL:C03_CUSTODY_STATES','ALL:C03_IMPORT_REFUSALS','C12:OPNAME_BASELINE_INCOMPLETE_SOURCE','C12:SAME_GOODS_COUNTED_ONCE'):
                    row.update(disposition='Q11_PRE_BD_FIXTURE_LACKS_REQUIRED_SOURCE_IDENTITY',current_contract='Owner D09 26Sep: pending custody requires count sheet+line or source lot; BD D09 correct/duplicate/missing-source controls PASS')
                elif key=='CP17-ASTRA-FIN-07-FULL-DETECTOR-OBSERVATION':
                    row.update(disposition='CONFIRMED_FIN01_ADDITIONAL_OBSERVATION',finding='ASTRA-CP17-FIN-01')
                elif key=='CP17-ASTRA-R3-02-REWORK-ALL-BS-SCRAP' and v.get('status')=='COUNTEREXAMPLE':
                    row.update(disposition='CONFIRMED_RWK01_ACCRUED_WORK_NOT_ELIGIBLE_AFTER_SCRAP',finding='ASTRA-CP17-RWK-01')
                elif key=='CP17-ASTRA-R3-03-CUTTING-REPOST-CHRONOLOGY' and v.get('status')=='COUNTEREXAMPLE':
                    row.update(disposition='CONFIRMED_STK01_PUBLIC_RESTATED_MATERIAL_PREFIX_DOUBLE_COUNTS',finding='ASTRA-CP17-STK-01')
                elif key=='CP17-ASTRA-CLAIM-02-BEFORE-SOURCE' and v.get('status')=='COUNTEREXAMPLE':
                    row.update(disposition='CONFIRMED_FIN02_CLAIM_SETTLEMENT_PRECEDES_SOURCE_AND_DATED_AP',finding='ASTRA-CP17-FIN-02')
                elif key=='CP17-ASTRA-POOL-03-POLICY-AFTER-ACTIVE' and v.get('status')=='COUNTEREXAMPLE':
                    row.update(disposition='CONFIRMED_HPP01_ACTIVE_POOL_STALE_AFTER_EXCLUDED_CONTRACTOR_POLICY',finding='ASTRA-CP17-HPP-01')
                elif key=='BE_REV_HTTP:PUBLIC_SEWING_AND_PERIOD_ACCESS' and run==38558702356:
                    row.update(disposition='Q12_LEGACY_POCKET_FIXTURE_REVOKED_BASELINE_SCHEMA_USAGE_BEFORE_HTTP',
                        qualification_run=38561483350,original_business_http_executed=False)
                elif key=='BF:UNUSED_ROLLBACK_EXACT':
                    row.update(disposition='Q13_CP6_ONLY_ROLLBACK_CORRECTLY_REFUSES_LATER_CP7_AUTHORITY_DELTA',
                        current_contract='CP7 supplier-credit-authority.sql intentionally changes BF function; native drift guard must remain; CP7 rollback tested by P21')
                elif key in ('BF_BROWSER:SALES_MANUAL_13_DESKTOP','BF_BROWSER:SALES_MANUAL_13_MOBILE'):
                    row.update(disposition='Q14_RETIRED_LEGACY_SALES_SCREEN_CARRIED_XC2_P11_ACCEPTANCE',
                        current_contract='D13-9c plus accepted XC2 P11 desktop/phone same-candidate proof; obsolete 3-input selector is not current sales screen')
                else:
                    row['disposition']='UNRESOLVED';issues.append(dict(original=row['original'],case_id=key,status=row['status']))
                dispositions.append(dict(row,error=v.get('error'),checks=v.get('checks')))
            rows.append(row);n+=1
        if g.get('counts') and g['counts']!=dict(collections.Counter(v.get('status') for v in cases.values())):
            issues.append(dict(original=str(p),group=group,problem='COUNT_MISMATCH'))
    admission_extra=0
    if outer.get('source_admission_required_case_credit')==0 and 'source_admission' in groups:
        admission_extra=len(groups['source_admission'].get('cases',{}))
    if outer.get('expected_case_count') is not None and outer['expected_case_count']!=n-admission_extra:
        issues.append(dict(original=str(p),problem='TOTAL_MISMATCH',expected=outer['expected_case_count'],actual=n,additional_admission_executions=admission_extra))
    reports.append(dict(run_id=run,artifact_id=artifact,original=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        cases=n,status=outer.get('status'),cp6_restored=outer.get('cp6_restored'),advisor_gate=outer.get('advisor_gate'),
        workspace_parse=outer.get('workspace_parse'),groups_complete=outer.get('groups_complete'),additional_admission_executions=admission_extra))

for directory in sorted((ROOT/'continuation').glob('*/*')):
    if not directory.is_dir() or not directory.name.isdigit() or not directory.parent.name.isdigit():continue
    run=int(directory.parent.name);artifact=int(directory.name)
    for p in sorted((directory/'original').glob('*.json')):
        if 'PREEXECUTION_PLAN' in p.name:continue
        d=json.loads(p.read_text())
        if not isinstance(d,dict):continue
        if p.name.startswith(('ASTRA_CP17_COVERAGE_MODES_','ASTRA_CP17_NATIVE_MODES_','ASTRA_CP17_SEWING_HTTP_QUALIFICATION')) and not p.stem.endswith('_CASES'):
            if 'groups' not in d and 'group' not in d:continue
            groups=d.get('groups',{'native':d['group']} if 'group'in d else {})
        elif p.name.startswith('ASTRA_CP17_COVERAGE_') and not p.stem.endswith('_CASES'):
            if 'group'not in d:continue
            groups={'native':d['group']}
        elif p.name.startswith(('CP17_OWN_CASES_FINANCE_OBSERVABILITY','CP17_OWN_CASES_FABLE_SEAMS','CP17_OWN_CASES_CLAIM_DATE','CP17_OWN_CASES_POOL_CLOSURE')):
            groups={'native':d}
        elif p.name.startswith('CP7_') and 'expected_case_count'in d:
            groups=d.get('groups') or {k:v for k,v in d.items()if isinstance(v,dict)and isinstance(v.get('cases',v.get('races')),dict)}
        else:continue
        ingest(p,run,artifact,groups,d)
for i,r in enumerate(rows,1):r['continuation_execution_index']=i
result=dict(candidate_sha='0b7049d9203bac52b47a4c89f3e0d75646067a8f',executions=len(rows),unique_case_ids=len({r['case_id']for r in rows}),
    counts=dict(collections.Counter(r['status']for r in rows)),reports=reports,rows=rows,issues=issues,
    meaning='Business/native/HTTP/browser case executions; shell/unit/kernel checks indexed separately. No raw status rewritten; repeated inherited cases in different declared suites are separate executions.')
(ROOT/'CASE_LEDGER_CONTINUATION.json').write_text(json.dumps(result,indent=2)+'\n')
(ROOT/'CONTINUATION_NONPASS.json').write_text(json.dumps(dispositions,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items()if k not in ('rows','reports')},indent=2))
