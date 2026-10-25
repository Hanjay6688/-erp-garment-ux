"""Read the actual Auth/race evidence schema without manufacturing absent fields."""


def checked_group(group, ids, *, races=False):
    """Require the recorded case-level sessions and the real HTTP cleanup record."""
    rows=group['races'if races else'cases']
    assert ids and len(ids)==len(set(ids))
    assert set(rows)==set(ids)and group['counts']=={'PASS':len(ids)}
    planned=group['planned_race_ids'if races else'planned_case_ids']
    assert len(planned)==len(ids)and set(planned)==set(ids)
    assert group['status']=='RUN_COMPLETE'and group['database_remaining']==0
    assert not group.get('error')
    for row in rows.values():
        assert row['status']=='PASS'
        # This field is mandatory in every actual case, not an optional group field.
        assert isinstance(row['session_leaks'],list)and row['session_leaks']==[]
    for optional in ('session_leaks','cleanup_failures','auth_cleanup_failures'):
        if optional in group:assert group[optional]in (False,[],{})
    if races:
        assert group['copy_per_race']is True and group['test_only_usage_grant']is True
    else:
        assert group['real_auth']is True and group['jwt_signed_by_runtime']is False
        assert group['test_only_usage_grant']is False
        assert group['auth_counts']==dict(before=[0]*4,after=[0]*4,restored=True)
        assert group['cleanup_failures']is False
        cleanup=group['cleanup']
        assert cleanup['cleanup_failures']==[]and cleanup['rest_remaining']is False
    return dict(status='PASS',cases=len(ids),case_level_sessions_checked=len(ids),
                real_auth_cleanup_checked=not races,database_remaining=0)
