"""Admit the exact failed factory outcome; no failed result becomes acceptance."""
from hashlib import sha256
import json
FACTORY='COMBINED_CURRENT_PUBLIC_FACTORY1200X3_ACTUAL_CRON'
def terminal(d):
    rows=d['job_rows'];assert len(rows)==2
    assert len({j['request_id']for j in rows})==2
    for j in rows:
        assert j['state']=='FAILED' and j['units_done']==0 and j['unit_count']==1
        assert j['plan_final']is False and j['failure_unit']==0 and j['unit_attempts']==3
        assert j['failure_sqlstate']=='57014' and j['failure_code']=='CP7_ANALYSIS_STAGE_STOPPED'
        assert j['failure_message']=='canceling statement due to statement timeout'
    assert len(d['finance_capture_rows'])==1
    f=d['finance_capture_rows'][0]
    assert f['state']=='READY'and f['units_done']==f['units_total']==7 and f['failure_code']is None
    assert d['read_only']is True and d['manual_steps']==0 and d['job_or_capture_state_changed']is False
    return dict(two_jobs_FAILED_at_unit0=True,three_attempts_each=True,SQLSTATE='57014',finance_READY=True)
def checked(proof,raw,package_raw,declaration):
    for data,size,digest in ((raw,proof['bytes'],proof['sha256']),(package_raw,proof['package_bytes'],proof['package_sha256'])):
        assert len(data)==size and sha256(data).hexdigest()==digest
    value=json.loads(raw);package=json.loads(package_raw)
    assert proof['status']==value['status']=='INCOMPLETE'and value['qualification_commit']==proof['head']
    assert value['source_declaration']==declaration
    assert package['gate']=={k:k!='writer_runtime'for k in ('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')}
    for k in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal'):assert value[k]is True,k
    cases=next(iter(value['committed'].values()))['cases'];assert len(cases)==7
    assert cases[FACTORY]['status']=='INCOMPLETE'and cases[FACTORY]['error']=='FACTORY_PROGRESS_JOB_TERMINAL_FAILURE'
    assert all(v['status']=='PASS'for k,v in cases.items()if k!=FACTORY)
    for v in cases.values():
        restore=v['installed_baseline_restoration']
        for k in ('pre_restore_observation_complete','all22_all_rows_all_sequences_roles_exact','complete_database_dump_restored'):assert restore[k]is True,k
        assert restore['unexpected_catalog_change']is False and not restore.get('guard_error')
    answer=terminal(cases[FACTORY]['terminal_diagnostics'])
    return dict(head=proof['head'],original_sha256=proof['sha256'],retained_status='INCOMPLETE',six_groups_PASS=True,
        seven_installed_restores_and_outer_restore_PASS=True,terminal=answer,backend_browser_unlock=False)
