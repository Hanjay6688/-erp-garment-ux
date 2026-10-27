"""Retain exact84's partial outcome; reuse only its five restored PASS groups."""
from hashlib import sha256
import ast,json

NATIVE='REPORT_BOOK_UNCHANGED_NATIVE20'
CRON='REPORT_BOOK_UNCHANGED_ACTUAL_MINUTE_CRON'
FAILED=frozenset((NATIVE,CRON))
PASSED=frozenset(('REPORT_BOOK_INDEPENDENT_CANONICAL_SIGNATURE',
    'REPORT_BOOK_UNCHANGED_CHILD_VISIBILITY_COUNTEREXAMPLE',
    'REPORT_BOOK_ASSIGNED_TRANSACTION_NULL_SNAPSHOT_AND_RECOVERY',
    'REPORT_BOOK_SMALL_PRICE_FACTORY_OVERHEAD',
    'UNCHANGED_SINGLE_CHECK_DIAGNOSTIC_WITH_COMPLETE_RESTORATION'))
REPORT_IDS=frozenset(('OW12A_REPORT_V2_FINANCE_THROUGH_CAPTURE',
    'OW12A_REPORT_V2_DEFERRED_UNCHANGED','OW12A_REPORT_V2_PERIOD_COMPARISON'))


def gate(config):
    if (config.get('allow_database_execution')is not True
        or config.get('retained84',{}).get('status')!='INCOMPLETE'):
        raise ValueError('CONSISTENCY_FOCUSED_ACTUAL84_REQUIRED')


def retained(proof,raw,package_raw,source):
    for value,size,digest in ((raw,proof['bytes'],proof['sha256']),
        (package_raw,proof['package_bytes'],proof['package_sha256'])):
        if len(value)!=size or sha256(value).hexdigest()!=digest:
            raise ValueError('CONSISTENCY_FOCUSED_ACTUAL84_BYTES_CHANGED')
    actual=json.loads(raw);package=json.loads(package_raw)
    assert actual['qualification_commit']==proof['head']=='84c2c9d962173c80a7630a857b708fe441f14e9b'
    assert actual['source_declaration']==source,'CONSISTENCY_FOCUSED_ACTUAL84_SOURCE_CHANGED'
    assert actual['status']=='INCOMPLETE'
    assert package['gate']==dict(installed=True,primary_unchanged=True,
        backup_restore_drill=True,security_advisors=True,writer_runtime=False)
    assert actual['production_go']is actual['independent_acceptance']is False
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal'):
        assert actual[key]is True,key
    assert len(actual['committed'])==1
    group=next(iter(actual['committed'].values()));cases=group['cases'];first=group['baseline_null_snapshot_counterexample']
    assert group['status']=='INCOMPLETE' and set(cases)==PASSED|FAILED
    assert first['status']=='INCOMPLETE' and first['error']=='ASSIGNED_TRANSACTION_MUST_NOT_SEAL_MIXED_BOOK'
    assert first['unsafe_ready_observed']is first['mixed_signature_confirmed']is True
    assert first['observed_report_snapshot']is None and first['source_commit_after_early_chunks']is True
    assert first['installed_baseline_restoration']['used_guard_refused_before_DDL']is True
    for case in [first,*cases.values()]:
        restored=case['installed_baseline_restoration']
        assert restored['all22_all_rows_all_sequences_roles_exact']is restored['complete_database_dump_restored']is True
        assert restored['unexpected_catalog_change']is False
    assert all(cases[key]['status']=='PASS'for key in PASSED)
    assert all(cases[key]['status']=='INCOMPLETE'for key in FAILED)
    native=cases[NATIVE]['native'];assert native['counts']=={'PASS':17,'INCOMPLETE':3}
    failures={key:case for key,case in native['cases'].items()if case['status']!='PASS'}
    assert set(failures)==REPORT_IDS
    for case in failures.values():
        error=ast.literal_eval(case['error'])
        assert error[0]=='E01_REPORT_NOT_READY' and error[1]['status']=='BLOCKED'
        assert len(error[1]['blockers'])==4
        assert {row['code']for row in error[1]['blockers']}=={'ATTENDANCE_POOL_NOT_ACTIVE'}
    assert all(case['full_boundary_restored']is True for case in native['cases'].values())
    cron=cases[CRON]
    assert cron['observed_finance_state']==cron['observed_choice_state']=='READY'
    assert len(cron['observed_job_states'])==2 and set(cron['observed_job_states'].values())=={'DONE'}
    assert cron['all_runs_recorded']is True and cron['cron_runs']
    assert all(row['status']=='succeeded'and row['end']is not None for row in cron['cron_runs'])
    assert "assert work['job_id']==initial['job_id'] and work['created_at']==initial['created_at']"in cron['traceback']
    for key in ('REPORT_BOOK_SMALL_PRICE_FACTORY_OVERHEAD','UNCHANGED_SINGLE_CHECK_DIAGNOSTIC_WITH_COMPLETE_RESTORATION'):
        assert set(cases[key]['pairs'])=={'SMALL','PRICE_PERCENT','FACTORY_1200X3'}
        assert all(pair['status']=='PASS'for pair in cases[key]['pairs'].values())
    return actual,dict(head=proof['head'],actual_whole_status='INCOMPLETE',
        raw_original_sha256=proof['sha256'],raw_package_sha256=proof['package_sha256'],
        retained_pass_groups=sorted(PASSED),required_focused_groups=sorted(FAILED),
        first_mixed_book_counterexample_proven=True,all_installed_and_preinstall_boundaries_restored=True,
        Native17_pass_3_input_failures_preserved=True,cron_completed_but_identity_assertion_failed=True,
        whole_old_result_not_promoted_to_PASS=True,production_go=False,independent_acceptance=False)
