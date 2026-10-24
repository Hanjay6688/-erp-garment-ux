"""Preserve three original READY failures and capture their missing report evidence.

No original fixture, operation, assertion or expected status is changed. This
diagnostic cannot convert a refusal or a blocked financial report into PASS.
"""
from datetime import timedelta
from pathlib import Path
import importlib.util,traceback
from psycopg.pq import TransactionStatus
import cp6_x_independent_audit as cash
import cp6_v2620h_adversarial_regression as chronology

REPO=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('cash_diagnostic_original_crossflow',REPO/'scripts/current-cp6-crossflow-qualification/cases.py')
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
IDS=('CASH_LINKED:1','CASH_LINKED:4','H_R02')
OBSERVATIONS={}


def declared_cases():
    all_cases=original.original.phase_cases('crossflow')
    result={k:v for k,v in all_cases if k in IDS}
    assert set(result)==set(IDS)
    return result


def cases(cur,today,*,current,evidence):
    stage='current'if current else'baseline'
    found=dict(original.cases(cur,today,current=current,evidence=evidence));result=[]
    for name in IDS:
        operation=found[name]
        def run(n=name,fn=operation):
            try:return fn()
            except Exception as error:
                observed=dict(original_error=str(error),original_traceback=traceback.format_exc(),
                    original_case=n,original_status='INCOMPLETE',fixture_day=str(today-timedelta(days=3)),
                    failure_relabelled=False,report_oracle_weakened=False)
                if cur.connection.info.transaction_status==TransactionStatus.INERROR:
                    observed['diagnostic_read_not_attempted']='ORIGINAL_SQL_ERROR_LEFT_TRANSACTION_FAILED'
                else:
                    try:
                        if n.startswith('CASH_LINKED:'):
                            observed['actual_same_day_reports']=cash.scrap.reports(cur,('2026-09-04','2026-09-05'))
                        else:
                            observed['actual_same_owner_report']=chronology.owner(cur)
                            observed['actual_original_targeted_issue_count']=chronology.targeted_issues(cur)
                        observed['diagnostic_reports_captured']=True
                    except Exception as diagnostic:
                        observed['diagnostic_error']=str(diagnostic)
                        observed['diagnostic_traceback']=traceback.format_exc()
                OBSERVATIONS.setdefault(stage,{})[n]=observed
                return dict(status='INCOMPLETE',error=str(error),diagnostic=observed)
        result.append((name,run))
    return result
