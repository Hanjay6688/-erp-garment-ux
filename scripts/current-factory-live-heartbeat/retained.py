"""Admit six original PASS groups; the historical factory remains INCOMPLETE."""
from hashlib import sha256
from collections import Counter
import json
FACTORY='COMBINED_CURRENT_PUBLIC_FACTORY1200X3_ACTUAL_CRON'
SIX=('COMBINED_UNCHANGED_CHILD_VISIBILITY','COMBINED_NULL_SNAPSHOT_REFUSAL_AND_RECOVERY','COMBINED_UNCHANGED_NATIVE20','COMBINED_INDEPENDENT_SIGNATURE','COMBINED_CURRENT_PUBLIC_ACTUAL_CRON','COMBINED_SMALL_PRICE_FACTORY_REPORT_PAIRS')
def checked(proof,raw,package_raw,parent):
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],'RETAINED_ORIGINAL_BYTES'
    assert len(package_raw)==proof['package_bytes']and sha256(package_raw).hexdigest()==proof['package_sha256'],'RETAINED_PACKAGE_BYTES'
    value=json.loads(raw);package=json.loads(package_raw)
    assert package['gate']==dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=False),'HISTORICAL_PACKAGE_GATE_CHANGED'
    assert value['qualification_commit']==proof['head']and value['status']=='INCOMPLETE'
    assert value['source_declaration']==parent,'RETAINED_ENTIRE_SOURCE_DECLARATION'
    assert value['production_go']is value['independent_acceptance']is False
    assert value['error']=='FOLLOWUP_FIRST_FAILURES_RETAINED'and not value.get('restore_error')
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','scheduler_quiet_before_baseline_restore'):assert value[key]is True,key
    assert value['complete_installed_verification']['status']=='EXACT_FACTORY_INITIAL_STAGE_ALL22'
    cases=value['committed']['FACTORY_INITIAL_STAGE_NATIVE_SOURCE_CRON7']['cases']
    assert set(cases)==set(SIX)|{FACTORY}
    assert all(cases[n]['status']=='PASS'for n in SIX)
    for n,c in cases.items():
        r=c['installed_baseline_restoration']
        assert all(r[k]is True for k in ('pre_restore_observation_complete','scheduler_quiet','complete_database_dump_restored','all22_all_rows_all_sequences_roles_exact','inverse_refused_before_DDL')),(n,r)
        assert r['unexpected_catalog_change']is False and not r.get('guard_error')
        assert r['restore']['only_pg_cron_errors']is True and r['restore']['unexplained']==[]
    assert cases[SIX[0]]['installed_baseline_restoration']['used_guard_refused_before_DDL']is True
    f=cases[FACTORY];assert f['status']=='INCOMPLETE'and f['error']==''
    assert "assert job['state']=='DONE'and job['server_runner']['active']is True"in f['traceback']
    assert len(f['observed_job_states'])==2 and set(f['observed_job_states'].values())=={'DONE'}and f['observed_finance_state']=='READY'
    assert f['small_job_not_taken_by_initial_worker']['status']=='PASS'
    guards=f['initial_worker_guards'];assert guards['status']=='PASS'and guards['all22_all_rows_and_sequences_unchanged']is True
    assert Counter(c['case']for c in guards['checks'])==Counter({'PUBLIC_8S_STEP_REFUSED_WITHOUT_ATTEMPT':2,'PRIVATE_LIMIT_REFUSED':3,'ORDINARY_WORKER_SKIPS_LARGE_INITIAL':1,'EXISTING_ACCESS_CHANGE_PRECEDES_INITIAL_LIMIT_REFUSAL':1,'SECOND_CONNECTION_SKIPS_BOTH_LOCKED_JOBS':1})
    assert set(f['cron_runs_by_schedule'])=={'cp7-staged-runner','cp7-factory-initial-preparation'}
    assert all(r and all(e['status']=='succeeded'and e['end']is not None for e in r)for r in f['cron_runs_by_schedule'].values())
    assert f['all_runs_recorded']is f['schedules_removed_and_unrelated_jobs_unchanged']is True
    return dict(head=proof['head'],tree=proof['tree'],run_id=proof['run_id'],job_id=proof['job_id'],artifact_id=proof['artifact_id'],original_sha256=proof['sha256'],historical_status='INCOMPLETE',retained_pass_case_ids=list(SIX),factory_status='INCOMPLETE',factory_rerun_required=True,all_seven_restores_exact=True,source_declaration_exact=True,package_gate=package['gate'],eligible_for_browser=False)
