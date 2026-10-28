"""Restore only remaining roles created by this qualification, fail closed."""
from psycopg import sql

def restore_roles(cur,before_roles,new_roles,read_roles):
    before=set(before_roles); created=set(new_roles); current=set(read_roles(cur))
    assert not before & created,'ROLE_BASELINE_AND_CREATED_OVERLAP'
    assert before <= current,'BASELINE_ROLE_MISSING_BEFORE_CLEANUP'
    assert current <= before | created,'UNEXPECTED_ROLE_BEFORE_CLEANUP'
    remaining=current-before
    for role in sorted(remaining):
        cur.execute(sql.SQL('drop role {}').format(sql.Identifier(role)))
    assert set(read_roles(cur))==before,'ROLE_SET_NOT_EXACTLY_RESTORED'
    return dict(already_removed_by_preuse=sorted(created-current),removed_remaining=sorted(remaining),baseline_roles_exact=True)
