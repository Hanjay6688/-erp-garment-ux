"""Admit six complete current regressions and preserve the failed factory Original."""
from hashlib import sha256
import json

LABELS=dict(native='CP7_CURRENT_VERSIONED_PERFORMANCE_NATIVE36',restore='CP7_CURRENT_VERSIONED_PERFORMANCE_USED_RESTORE8',
    finance='CP7_CURRENT_VERSIONED_PERFORMANCE_FINANCE10',cron='CP7_CURRENT_VERSIONED_PERFORMANCE_CRON1',
    browser='CP7_CURRENT_VERSIONED_PERFORMANCE_BROWSER6',transport='CP7_CURRENT_VERSIONED_PERFORMANCE_TRANSPORT28')
COUNTS=dict(native=36,finance=10,cron=1,browser=6,transport=28)


def declaration_path(kind):
    return 'scripts/current-versioned-performance-'+('used-restore'if kind=='restore'else kind)+'-qualification/SOURCE.json'


def validate_failure(config,proof,failed):
    assert failed['label']=='CP7_CURRENT_FACTORY_FINANCE1'and failed['status']==proof['status']=='INCOMPLETE'
    assert(failed.get('qualification_commit')or failed.get('candidate_commit'))==proof['head']==config['old_head']
    assert failed['cp6_restored']and failed['advisor_gate']and failed['baseline_full22_all_rows_all_sequences_equal']and failed['baseline_advisors_equal']
    assert failed['production_go']is failed['independent_acceptance']is False
    old=failed['source_declaration']['qualification']['files']
    assert old['scripts/current-factory-finance-qualification/fixture.py']==config['fixture_sha256']
    assert old['scripts/current-factory-finance-qualification/runner.py']==config['runner_sha256']
    return dict(proof,observed_status='INCOMPLETE')


def validate(repo,config,proofs,actuals,product):
    expected=set(config['followups'].values())|{config['first_failure_variable']}
    assert set(proofs)==set(actuals)==expected and len(expected)==config['required_actual_originals']==7
    current=product.sources();sources={};verified={}
    for kind,variable in config['followups'].items():
        proof,actual=proofs[variable],actuals[variable]
        assert actual['label']==LABELS[kind]and actual['status']==proof['status']=='PASS'
        assert(actual.get('qualification_commit')or actual.get('candidate_commit'))==proof['head']
        assert actual['cp6_restored']and actual['advisor_gate']and actual['restore_raw_public_equal']
        assert actual['production_go']is actual['independent_acceptance']is False
        assert actual['source_declaration']['current_installation']==current
        source=json.loads((repo/declaration_path(kind)).read_bytes())
        assert actual['source_declaration']['qualification']==source
        for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,(kind,path)
        sources[kind]=source
        if kind!='native':assert source['actual_qualification_originals'][config['native_variable']]==proofs[config['native_variable']]
        if kind in('native','restore','cron'):
            assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
        if kind=='restore':
            assert actual['required_steps_pass']and actual['required_steps']==source['required_steps']
            assert len(actual['steps'])==8 and [row['step']for row in actual['steps']]==source['required_steps']
            assert all(row['status']=='PASS'for row in actual['steps'])
            controls=actual['steps'][4]['controls']
            assert len(controls)==len({row['id']for row in controls})==34 and all(row['status']=='PASS'for row in controls)
            assert actual['steps'][2]['all_rows_sequences_and_full22_unchanged']
            assert actual['steps'][3]['all_table_hashes_equal']and actual['steps'][5]['all_table_hashes_equal']
        else:
            assert actual['required_case_ids_pass']and actual['required_case_ids']==source['case_ids']
            assert actual['observed_case_count']==COUNTS[kind]and actual['complete_preuse_removal']
            if kind=='native':
                assert actual['native']['counts']=={'PASS':36}and set(actual['native']['cases'])==set(source['case_ids'])
                assert all(row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged']for row in actual['native']['cases'].values())
            elif kind=='cron':
                assert actual['actual_cron_claim']and actual['manual_steps']==0 and not actual['changed_schedule']
                assert actual['scheduler_quiet_before_baseline_restore']and actual['used_guard_refused_before_DDL']
                assert set(actual['committed'])==set(source['case_ids'])
                case=actual['committed']['CURRENT_FINANCE_MODEL_ACTUAL_MINUTE_CRON_BOUNDED_READY_AND_DEFERRED']
                assert case['status']=='PASS'and case['official_sections_and_metrics_exact']and case['independent_book_signature']and case['metric_count']==24
                assert case['unknown_never_zero']and case['unchanged_production_minute_schedule']
            else:
                groups=actual['browser_groups'if kind=='browser'else'transport_groups'];ids=[]
                assert len(groups)=={'browser':3,'finance':2,'transport':6}[kind]
                for name,group in groups.items():
                    races=name.endswith('_races');rows=group['races'if races else'cases'];ids.extend(rows)
                    assert group['counts']=={'PASS':len(rows)}and rows and all(row['status']=='PASS'for row in rows.values())
                    assert group['database_remaining']==0 and not group.get('cleanup_failures')and not group.get('session_leaks')
                    if kind=='browser':assert group['host_status']=='RUN_COMPLETE'and group['host_exit']==0 and group['console_errors']==0 and len(rows)==2
                    else:assert group['status']=='RUN_COMPLETE'
                    if not races:
                        assert group['real_auth']and not group['jwt_signed_by_runtime']and not group['test_only_usage_grant']
                        assert group['auth_counts']['restored']and not group.get('auth_cleanup_failures')
                assert len(ids)==len(set(ids))==COUNTS[kind]and set(ids)==set(source['case_ids'])
                assert len(actual['copy_catalog_admissions'])=={'browser':3,'finance':1,'transport':3}[kind]
                if kind!='browser':assert len(actual['race_copy_catalog_admissions'])=={'finance':7,'transport':19}[kind]
                if kind=='finance':
                    observations=actual['full_capture_snapshot_observations'];assert len(observations)==7
                    assert all(row['all_fields_retained']==23 and row['session_timezone_restored']for row in observations)
        verified[variable]=dict(proof,observed_status='PASS')
    variable=config['first_failure_variable'];proof,failed=proofs[variable],actuals[variable]
    verified[variable]=validate_failure(config,proof,failed)
    return sources,verified
