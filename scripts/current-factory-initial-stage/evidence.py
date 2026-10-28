"""Exact diagnostic evidence supports a measured successor, never acceptance."""
from hashlib import sha256
import json
def checked(proof,raw,package_raw,declaration):
    for data,size,digest in ((raw,proof['bytes'],proof['sha256']),(package_raw,proof['package_bytes'],proof['package_sha256'])):
        assert len(data)==size and sha256(data).hexdigest()==digest
    value=json.loads(raw);package=json.loads(package_raw)
    assert value['status']==proof['status']=='PASS'and value['qualification_commit']==proof['head']
    assert value['source_declaration']==declaration
    assert package['gate']=={k:True for k in ('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')}
    for key in ('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal'):assert value[key]is True,key
    for key in ('actual_cron_claim','combined_component_qualified','performance_qualification','full_combined_final_qualification','default_adopted','production_go','independent_acceptance'):assert value[key]is False,key
    outer=value['committed'];assert set(outer)=={'CURRENT_FACTORY_OPERATIONAL_PROFILE1'}
    outer=outer['CURRENT_FACTORY_OPERATIONAL_PROFILE1'];assert outer['status']=='PASS'
    assert set(outer['cases'])=={'CURRENT_FACTORY_UNIT0_AND_COMPILER_DIAGNOSTIC'}
    c=outer['cases']['CURRENT_FACTORY_UNIT0_AND_COMPILER_DIAGNOSTIC']
    assert c['status']=='PASS'and c['diagnostic_collection_completed']is True
    restore=c['installed_baseline_restoration']
    for key in ('complete_database_dump_restored','all22_all_rows_all_sequences_roles_exact','used_guard_refused_before_DDL'):assert restore[key]is True,key
    assert restore['unexpected_catalog_change']is False and not restore.get('guard_error')
    assert c['all22_all_rows_and_sequences_unchanged_by_measurements']is c['stored_job_and_capture_progress_unchanged']is True
    assert c['manual_committed_steps']==0 and c['product_timeout_changed']is c['factory_native_finance_qualified']is False
    measurements=c['measurements']
    assert [m['name']for m in measurements]==['FIRST_OPERATIONAL_UNIT','FROZEN_INPUT_COMPILER','SMALL_STATUS_READ']
    for m,limit in zip(measurements,(30000,30000,8000)):
        assert m['status']=='COMPLETED_DIAGNOSTIC'and m['statement_limit_ms']==limit and m['retries']==0
        assert m['all_measured_effects_rolled_back']is m['diagnostic_only']is True and m['performance_qualification']is False
    return dict(head=proof['head'],original_sha256=proof['sha256'],diagnostic_only=True,backend_unlock=False,
        full_restoration_verified=True,measurements=[{k:m[k]for k in ('name','elapsed_ms','result_bytes','result_sha256')}for m in measurements])
