"""Admit AF's exact first failure, its five PASS groups and both remaining gaps."""
from hashlib import sha256
import json

PASSED=frozenset(('COMBINED_UNCHANGED_CHILD_VISIBILITY','COMBINED_NULL_SNAPSHOT_REFUSAL_AND_RECOVERY',
    'COMBINED_UNCHANGED_NATIVE20','COMBINED_INDEPENDENT_SIGNATURE','COMBINED_CURRENT_PUBLIC_ACTUAL_CRON'))
PAIRS='COMBINED_SMALL_PRICE_FACTORY_REPORT_PAIRS'
FACTORY='COMBINED_CURRENT_PUBLIC_FACTORY1200X3_ACTUAL_CRON'
LIMIT='total size of jsonb array elements exceeds the maximum of 268435455 bytes'


def gate(config):
    if config.get('allow_database_execution')is not True or config.get('retained_af',{}).get('status')!='INCOMPLETE':
        raise ValueError('READER_STREAM_ACTUAL_AF_FIRST_FAILURE_REQUIRED')
    assert config['production_go']is config['independent_acceptance']is False
    return config['retained_af']


def retained(proof,raw,package_raw,source,current_installation,binding):
    for value,size,digest in ((raw,proof['bytes'],proof['sha256']),
        (package_raw,proof['package_bytes'],proof['package_sha256'])):
        if len(value)!=size or sha256(value).hexdigest()!=digest:raise ValueError('READER_STREAM_AF_BYTES_CHANGED')
    actual=json.loads(raw);package=json.loads(package_raw)
    assert actual['status']=='INCOMPLETE'and actual['qualification_commit']==proof['head']=='af474fe365b83651dae096f988def69e3ef7e8d7'
    assert actual['source_declaration']['qualification']==source
    assert actual['source_declaration']['current_installation']==current_installation
    assert package['gate']==dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=False)
    assert actual['production_go']is actual['independent_acceptance']is False
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal'):assert actual[key]is True
    assert actual['error']==LIMIT
    assert len(actual['committed'])==1
    group=next(iter(actual['committed'].values()));cases=group['cases']
    assert group['status']=='INCOMPLETE'and set(cases)==PASSED|{PAIRS,FACTORY}
    for key in PASSED|{PAIRS}:
        case=cases[key];restored=case['installed_baseline_restoration']
        assert case['status']==('PASS'if key in PASSED else'INCOMPLETE')
        assert restored['all22_all_rows_all_sequences_roles_exact']is restored['complete_database_dump_restored']is True
        assert restored['unexpected_catalog_change']is False
    assert cases['COMBINED_UNCHANGED_CHILD_VISIBILITY']['installed_baseline_restoration']['used_guard_refused_before_DDL']is True
    native=cases['COMBINED_UNCHANGED_NATIVE20']['native']
    assert native['counts']=={'PASS':20}and native['complete_boundary_restored']is True
    pair=cases[PAIRS]['pairs'];assert set(pair)=={'SMALL','PRICE_PERCENT'}and pair['SMALL']['status']=='PASS'
    price=pair['PRICE_PERCENT'];assert price['status']=='INCOMPLETE'
    old,new=price['accepted_reader_bodies'],price['combined_reader']
    assert old['report_sha256']==new['report_sha256']
    assert new['observed_nonstable_financial_readers']=={'erp.product_opening_physical_at(uuid,date)':'v'}
    assert new['observed_reader_catalog']['erp.product_opening_physical_at(uuid,date)']==binding['native_opening']
    assert new['observed_reader_catalog']['cp7_finance.read_opening_hpp_diagnostic_v1(uuid,date)']==binding['private_hpp']
    for row in (old,new):assert row['zero_table_write_attempts']is row['all22_data_sequences_restored']is True
    last=cases[FACTORY]
    assert last['status']=='INCOMPLETE'and last['error']==last['restore_error']==LIMIT
    assert last.get('installed_baseline_restoration')is None
    assert last['observed_finance_state']=='READY'and len(last['observed_job_states'])==2
    assert set(last['observed_job_states'].values())=={'DONE'}
    assert last['all_runs_recorded']is True and last['cron_runs']
    assert all(row['status']=='succeeded'and row['end']is not None for row in last['cron_runs'])
    return actual,dict(head=proof['head'],whole_status='INCOMPLETE',original_sha256=proof['sha256'],
        package_sha256=proof['package_sha256'],five_actual_pass_groups=sorted(PASSED),
        live_price_percent_volatile_reader_proven=True,whole_PRICE_report_equal_but_not_qualified=True,
        factory_jobs_DONE_finance_READY_but_readback_incomplete=True,last_installed_restore_not_proven=True,
        complete_outer_preinstall_restore_proven=True,first_failure_not_promoted=True,
        production_go=False,independent_acceptance=False)
