"""A backend eligibility contract; B supplies its actual product.sources() result.

No database, browser execution or historical status rewriting occurs here.
"""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json
HERE=Path(__file__).resolve().parent
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def checked(retained_raw,retained_package_raw,fresh_raw,fresh_package_raw,current_installation):
    cfg=json.loads((HERE/'CONFIG.json').read_bytes())
    assert cfg['contract']=='cp7.backend-acceptance-six-retained-one-fresh.v1'
    assert cfg['production_go']is cfg['independent_acceptance']is False
    for raw,proof,label in ((retained_raw,cfg['retained'],'retained Original'),(fresh_raw,cfg['fresh'],'fresh Original')):
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],'EXACT_BYTES_REQUIRED:'+label
    for raw,proof,label in ((retained_package_raw,cfg['retained'],'retained package'),(fresh_package_raw,cfg['fresh'],'fresh package')):
        assert len(raw)==proof['package_bytes']and sha256(raw).hexdigest()==proof['package_sha256'],'EXACT_BYTES_REQUIRED:'+label
    assert sha256(canonical(current_installation)).hexdigest()==cfg['whole_backend_sha256'],'CURRENT_BACKEND_SOURCE_MISMATCH'
    old=json.loads(retained_raw);new=json.loads(fresh_raw)
    assert old['qualification_commit']==cfg['retained']['head']and new['qualification_commit']==cfg['fresh']['head']
    assert old['status']=='INCOMPLETE'and new['status']=='PASS','HISTORICAL_AND_FRESH_STATUS_REQUIRED'
    assert old['error']=='FOLLOWUP_FIRST_FAILURES_RETAINED'and not new.get('error')
    assert not old.get('restore_error')and not new.get('restore_error')
    for report in (old,new):
        assert report['production_go']is report['independent_acceptance']is report['real_Auth_browser_claim']is False
        for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal'):assert report[key]is True,key
    assert new['source_declaration']['unchanged_11c_declaration']==old['source_declaration']
    assert new['source_declaration']['current_installation']==old['source_declaration']['current_installation']==current_installation
    assert json.loads(retained_package_raw)['gate']==dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=False)
    assert json.loads(fresh_package_raw)['gate']==dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)
    cases=old['committed']['FACTORY_INITIAL_STAGE_NATIVE_SOURCE_CRON7']['cases'];factory_id=cfg['fresh_case_id']
    assert set(cases)==set(cfg['retained_case_ids'])|{factory_id}
    assert all(cases[k]['status']=='PASS'for k in cfg['retained_case_ids'])and cases[factory_id]['status']=='INCOMPLETE'
    outer=new['committed']['FACTORY_LIVE_HEARTBEAT_CLOSURE1'];assert outer['status']=='PASS'and set(outer['cases'])=={factory_id}
    factory=outer['cases'][factory_id];assert factory['status']=='PASS'
    for case in [*cases.values(),factory]:
        r=case['installed_baseline_restoration']
        for k in ('pre_restore_observation_complete','scheduler_quiet','complete_database_dump_restored','all22_all_rows_all_sequences_roles_exact','inverse_refused_before_DDL'):assert r[k]is True,k
        assert r['unexpected_catalog_change']is False and not r.get('guard_error')
        assert r['restore']['only_pg_cron_errors']is True and r['restore']['unexplained']==[]
    assert new['used_guard_refused_before_DDL']is factory['installed_baseline_restoration']['used_guard_refused_before_DDL']is True
    complete=new['complete_installed_verification'];assert complete['status']=='EXACT_FACTORY_INITIAL_STAGE_ALL22'
    assert complete['all22_transition_chain_verified']is True and complete['substituted_catalog_or_definitions']is False
    worker=complete['worker'];assert (worker['large_initial_max_ms'],worker['ordinary_statement_limit_ms'],worker['minimum_targets'])==(16000,8000,1000)
    guards=factory['initial_worker_guards'];assert guards['status']=='PASS'and guards['all22_all_rows_and_sequences_unchanged']is True
    assert Counter(c['case']for c in guards['checks'])==Counter({'PUBLIC_8S_STEP_REFUSED_WITHOUT_ATTEMPT':2,'PRIVATE_LIMIT_REFUSED':3,'ORDINARY_WORKER_SKIPS_LARGE_INITIAL':1,'EXISTING_ACCESS_CHANGE_PRECEDES_INITIAL_LIMIT_REFUSAL':1,'SECOND_CONNECTION_SKIPS_BOTH_LOCKED_JOBS':1})
    assert factory['small_job_not_taken_by_initial_worker']['status']=='PASS'
    schedules=factory['cron_runs_by_schedule'];assert set(schedules)=={'cp7-staged-runner','cp7-factory-initial-preparation'}
    assert all(r and all(x['status']=='succeeded'and x['end']is not None for x in r)for r in schedules.values())
    assert factory['all_runs_recorded']is factory['schedules_removed_and_unrelated_jobs_unchanged']is True
    live=factory['live_runner_observation'];assert live['status']=='PASS'and live['phase']=='SCHEDULE_INSTALLED_BEFORE_UNINSTALL'and live['manual_ticks']==0
    ids={factory['finance_request'],factory['bounded_request']};assert len(ids)==2 and set(live['jobs'])==set(factory['pages'])==set(factory['post_stop_public_status'])==ids
    for key in ids:
        before=live['jobs'][key];after=factory['post_stop_public_status'][key];page=factory['pages'][key]
        assert before['request_id']==after['request_id']==key and before['state']==after['state']=='DONE'
        assert before['server_runner']['active']is True and before['server_runner']['last_tick_at']is not None
        assert before['run_id']==after['run_id']==page['run_id']and page['units']==97
        coverage=page['factory_coverage'];assert coverage['complete']is coverage['all_pages_verified']is coverage['every_target_recommended_or_named']is True
        assert coverage['factory_variants']==3600 and coverage['expected_targets']==coverage['source_targets']==3604
        assert coverage['analysis_status']=='PARTIAL'and coverage['unreviewed_named_targets']==2
        assert page['page_meta']['page_count']==19
    for k in ('same_UUID_no_second_effect','official_sections_and_metrics_exact','independent_book_signature','unknown_never_zero','all22_catalog_exact','Native_money_stock_HPP_unchanged','report_and_collected_book_signatures_equal'):assert factory[k]is True,k
    assert factory['metric_count']==24 and factory['readiness']=='BLOCKED'and len(factory['unknown_metric_ids'])==11
    assert factory['manual_finance_or_operational_steps']==factory['page_or_test_ticks']==0
    return dict(status='PASS_BACKEND_COMPONENT_FOR_B_BINDING',selected_backend_head=cfg['fresh']['head'],selected_backend_tree=cfg['fresh']['tree'],whole_backend_sha256=cfg['whole_backend_sha256'],retained_groups=6,fresh_groups=1,seven_fresh_groups_claim=False,historical_11c_status='INCOMPLETE',factory_fixture_readiness='BLOCKED',factory_fixture_analysis_status='PARTIAL',all_installed_and_outer_restorations_exact=True,frontend_or_Auth_browser_accepted=False,formal_accepted='5/16',independent_acceptance=False,production_go=False)
