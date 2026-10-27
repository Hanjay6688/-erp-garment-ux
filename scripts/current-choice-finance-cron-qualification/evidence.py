"""Recheck accepted exact Originals and their package gates against current sources."""
from pathlib import Path
from hashlib import sha256
import json

def checked(repo,proof,directory,product,parent):
    directory=Path(directory);actual=None
    for row in proof['preserved_files']:
        if not row['path'].endswith('.json'):continue
        p=directory/Path(row['path']).name;raw=p.read_bytes()
        assert len(raw)==row['bytes']and sha256(raw).hexdigest()==row['sha256'],p.name
        if p.name==proof['name']:actual=json.loads(raw)
    assert actual is not None and actual['status']==proof['status']=='PASS'
    assert (actual.get('qualification_commit')or actual.get('candidate_commit'))==proof['head']
    assert actual['production_go']is actual['independent_acceptance']is False
    for flag in ('cp6_restored','advisor_gate','restore_raw_public_equal','required_case_ids_pass'):
        assert actual[flag]is True,flag
    assert actual['complete_preuse_removal']
    package=json.loads((directory/'T3_PACKAGE_INSTALL.json').read_bytes())
    assert package['gate']=={k:True for k in ('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')}
    assert package['production_go']is False
    declaration=json.loads((repo/proof['declaration']).read_bytes())
    assert actual['source_declaration']['qualification']==declaration
    for path,digest in declaration['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert actual['observed_case_count']==actual['expected_case_count']==proof['cases']
    assert actual['required_case_ids']==declaration['case_ids']
    expected=product.predecessor.predecessor.sources()if proof['kind']=='prior_cron'else product.sources()
    assert actual['source_declaration']['current_installation']==expected
    if proof['kind']=='ui':
        assert actual['source_declaration']==parent
        assert set(actual['browser_groups'])=={'desktop','mobile'}
        for group in actual['browser_groups'].values():
            assert group['counts']=={'PASS':1}and group['database_remaining']==0
            assert not group['cleanup_failures']and not group['auth_cleanup_failures']
            assert not group['console_errors']and group['auth_counts']['restored']
        assert len(actual['copy_catalog_admissions'])==2
    elif proof['kind']=='transport':
        from cp7_current_transport_original_schema import checked_group
        groups=actual['transport_groups'];assert set(groups)=={'choice_http','choice_races'}
        for name,group in groups.items():
            checked_group(group,actual['source_declaration']['focused_groups'][name],races=name.endswith('_races'))
        assert actual['baseline_role_cleanup']['baseline_roles_exact']
        assert actual['source_database_all_rows_sequences_unchanged']
        assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
    else:
        assert proof['kind']=='prior_cron'and actual['actual_cron_claim']
        assert actual['manual_steps']==0 and actual['changed_schedule']is False
        assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
        assert actual['used_guard_refused_before_DDL']and actual['scheduler_quiet_before_baseline_restore']
        case=actual['committed'][declaration['case_ids'][0]]
        assert case['status']=='PASS'and case['metric_count']==24 and 0<=case['elapsed_seconds']<300
        assert case['manual_finance_or_operational_steps']==case['page_or_test_ticks']==0
        assert case['test_schedule_override']is None
        assert case['observed_finance_state']=='READY'and set(case['observed_job_states'].values())=={'DONE'}
        for flag in ('official_sections_and_metrics_exact','independent_book_signature','unknown_never_zero',
                     'Native_money_stock_HPP_unchanged','server_runner_active','all22_catalog_exact',
                     'all_runs_recorded','schedules_removed_and_unrelated_jobs_unchanged','same_UUID_no_second_effect'):
            assert case[flag]is True,flag
        assert case['cron_runs']and all(r['status']=='succeeded'and r['end']is not None for r in case['cron_runs'])
    return dict(head=proof['head'],sha256=proof['sha256'],all_package_gates=True,actual_status='PASS')
