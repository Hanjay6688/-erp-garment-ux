"""Typed actual business-group checks; no source preparation earns case credit."""

def rows(report,field,ids,*,status):
    values=report.get(field,{})
    counts=report.get('counts')
    if(type(values)is not dict or type(counts)is not dict or set(counts)!={'PASS'}
        or type(counts['PASS'])is not int or counts['PASS']!=len(ids)or len(set(ids))!=len(ids)
        or report.get('status')!=status
        or report.get('planned_case_ids',report.get('planned_race_ids'))!=list(ids)
        or set(values)!=set(ids)or report.get('error')or report.get('missing')
        or report.get('business_day_retried')or report.get('business_day_first_attempt')):
        raise ValueError('NONPAYABLE_EXACT_COMPLETE_FRESH_BUSINESS_GROUP_REQUIRED:'+field)
    for name,row in values.items():
        if(row.get('status')!='PASS'or row.get('business_day_rollover')or row.get('harness_check_failed')
            or row.get('session_leaks')not in([],dict(advisory_locks=0,advisory_lock_keys=[],other_sessions=[]))):
            raise ValueError('NONPAYABLE_CASE_REQUIRES_ORIGINAL_SUCCESS_AND_EMPTY_SESSIONS:'+name)
    return values

def native(report,ids):
    values=rows(report,'cases',ids,status='PASS')
    if report.get('complete_boundary_restored')is not True:raise ValueError('NONPAYABLE_NATIVE_GROUP_BOUNDARY_NOT_RESTORED')
    for name,row in values.items():
        boundary=row.get('actual_full22_case_boundary',{});proof=boundary.get('verification',{})
        if(row.get('full_boundary_restored')is not True or row.get('public_schema_unchanged')is not True
            or proof.get('all22_catalog_exact')is not True or proof.get('all_table_rows_restored')is not True
            or proof.get('all_other_sequences_unchanged')is not True
            or proof.get('observed_sequences_unchanged_by_rollback')is not True
            or proof.get('case_sequence_reset_performed')is not False
            or proof.get('complete_outer_backup_ALL_sequence_restore_required')is not True):
            raise ValueError('NONPAYABLE_NATIVE_COMPLETE_UNPROJECTED_BOUNDARY_REQUIRED:'+name)
    return dict(status='PASS',actual_Native_cases=len(ids),prior_parent_case_credit=0)

def copies(report,ids,*,mode):
    field='races'if mode=='RACE'else'cases'
    values=rows(report,field,ids,status='RUN_COMPLETE')
    if(type(report.get('database_remaining'))is not int or report['database_remaining']!=0
        or report.get('cleanup_failures')or report.get('session_leaks')):
        raise ValueError('NONPAYABLE_COMPLETE_COPY_AND_SESSION_CLEANUP_REQUIRED:'+mode)
    if mode in('HTTP','BROWSER'):
        counts=report.get('auth_counts',{})
        def census(value):return type(value)is list and len(value)==4 and all(type(n)is int and n>=0 for n in value)
        if(report.get('real_auth')is not True or report.get('jwt_signed_by_runtime')is not False
            or report.get('test_only_usage_grant')is not False
            or counts.get('restored')is not True or not census(counts.get('before'))or not census(counts.get('after'))
            or counts['before']!=counts['after']
            or report.get('cleanup',{}).get('cleanup_failures')!=[]
            or report.get('cleanup',{}).get('rest_remaining')is not False):
            raise ValueError('NONPAYABLE_REAL_AUTH_AND_COMPLETE_PRIMARY_AUTH_RESTORATION_REQUIRED:'+mode)
    if mode=='BROWSER':
        if(report.get('host_exit')!=0 or report.get('host_status')!='RUN_COMPLETE'
            or report.get('console_errors')!=0 or report.get('auth_cleanup_failures')):
            raise ValueError('NONPAYABLE_ORIGINAL_REAL_BROWSER_HOST_AND_CLEANUP_REQUIRED')
        for name,row in values.items():
            if(row.get('normal_App_menu')is not True or row.get('real_Auth')is not True
                or not row.get('screenshots')or not row.get('visuals')or not row.get('complete_census_proofs')
                or row.get('all_stock_HPP_journals_entitlements_and_existing_history_unchanged')is not True):
                raise ValueError('NONPAYABLE_ACTUAL_NORMAL_APP_BROWSER_MONEY_CENSUS_AND_VISUALS_REQUIRED:'+name)
    elif mode=='HTTP':
        if any(row.get('real_Auth_HTTP')is not True for row in values.values()):
            raise ValueError('NONPAYABLE_ACTUAL_REAL_AUTH_HTTP_CASE_REQUIRED')
    elif mode=='RACE':
        if report.get('copy_per_race')is not True or report.get('test_only_usage_grant')is not True:
            raise ValueError('NONPAYABLE_FRESH_COPY_EACH_ACTUAL_DATABASE_RACE_REQUIRED')
        if any(row.get('actual_two_database_sessions')is not True for row in values.values()):
            raise ValueError('NONPAYABLE_TWO_ACTUAL_DATABASE_BACKENDS_REQUIRED')
    else:raise ValueError('NONPAYABLE_DECLARED_BUSINESS_COPY_MODE_REQUIRED')
    return dict(status='PASS',mode=mode,actual_cases=len(ids),full_outer_restoration_still_required=True)
