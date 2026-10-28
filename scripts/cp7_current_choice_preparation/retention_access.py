"""Two private run-reference column grants for the existing retention owner.

No schema, table, function, policy, writer or caller capability is created.
The exact 22-group transition includes the column ACLs and temporary installer
memberships must already have been removed before that census is taken.
"""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from psycopg import sql
from psycopg.pq import TransactionStatus
from cp7_ow04_restore_bundle import _catalog_rows

READER='cp7_capture'
TARGETS={'cp7_plan_native.staged_drafts':'cp7_plan_writer',
         'cp7_reminder_native.staged_condition_sets':'cp7_reminder'}
COLUMNS={table+':run_id':owner for table,owner in TARGETS.items()}
CALLERS=('anon','authenticated','service_role','cp7_alert','cp7_finance_read')


def verify_sources():
    return dict(module_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        reader=READER,select_columns=sorted(COLUMNS),new_public_rpcs=0,
        existing_retention_body_unchanged=True,production_go=False)


def own(catalog):
    return {g:{k:v for k,v in rows.items()if g=='columns'and k in COLUMNS}
            for g,rows in catalog.items()}


def expected_column(key,old):
    if key not in COLUMNS or not isinstance(old,list)or len(old)!=14 or old[0]!='run_id' or old[12]is not None:
        raise ValueError('RETENTION_REFERENCE_PARENT_COLUMN_CHANGED:'+key)
    new=deepcopy(old);new[12]=[READER+'=r/'+COLUMNS[key]]
    return new


def admit_transition(before,after):
    if set(before)!=set(after)or len(before)!=22:
        raise ValueError('RETENTION_REFERENCE_FULL22_REQUIRED')
    expected=deepcopy(before)
    for key,owner in COLUMNS.items():
        table=key.split(':')[0]
        if before['relations'][table][0]!=owner:
            raise ValueError('RETENTION_REFERENCE_TABLE_OWNER_CHANGED:'+table)
        expected['columns'][key]=expected_column(key,before['columns'][key])
    if after!=expected:
        raise ValueError('RETENTION_REFERENCE_ONLY_TWO_COLUMN_READ_GRANTS_ALLOWED')


@contextmanager
def owners(cur):
    """Same finite Native-harness handover as OW12a; DDL runs as table owners.

Normal postgres installations already have SET membership from role creation.
Only the disposable superuser harness may supply a missing membership; a
partial existing membership is refused instead of overwritten. Both grants
are revoked before the actual full catalog is read, including on inversion.
"""
    previous=cur.execute('select current_user').fetchone()[0]
    if previous not in ('postgres','supabase_admin'):
        raise ValueError('RETENTION_REFERENCE_INSTALLER_ROLE_REQUIRED')
    granted=[]
    try:
        for role in sorted(set(TARGETS.values())):
            if cur.execute("select pg_has_role('postgres',%s,'SET')",(role,)).fetchone()[0]:continue
            if (not cur.execute('select rolsuper from pg_roles where rolname=current_user').fetchone()[0]
                or cur.execute("select exists(select 1 from pg_auth_members where roleid=%s::regrole and member='postgres'::regrole)",(role,)).fetchone()[0]):
                raise ValueError('RETENTION_REFERENCE_INSTALLER_CANNOT_HAND_OVER:'+role)
            cur.execute(sql.SQL('grant {} to postgres with inherit true,set true').format(sql.Identifier(role)))
            granted.append(role)
        cur.execute('set local role postgres')
        yield
    finally:
        if cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(previous)))
            for role in reversed(granted):
                cur.execute(sql.SQL('revoke {} from postgres').format(sql.Identifier(role)))


def change(cur,grant):
    with owners(cur):
        for table,owner in TARGETS.items():
            cur.execute(sql.SQL('set local role {}').format(sql.Identifier(owner)))
            command='grant select(run_id)on {} to {}'if grant else'revoke select(run_id)on {} from {}'
            cur.execute(sql.SQL(command).format(sql.Identifier(*table.split('.')),sql.Identifier(READER)))
            cur.execute('set local role postgres')


def check_permissions(cur):
    role=cur.execute('select rolsuper,rolcanlogin,rolbypassrls from pg_roles where rolname=%s',(READER,)).fetchone()
    if role!=(False,False,True):raise ValueError('RETENTION_REFERENCE_READER_AUTHORITY_CHANGED')
    for table,owner in TARGETS.items():
        schema=table.split('.')[0]
        actual=cur.execute('select pg_get_userbyid(relowner),relrowsecurity from pg_class where oid=%s::regclass',(table,)).fetchone()
        if actual!=(owner,True):raise ValueError('RETENTION_REFERENCE_OWNER_OR_RLS_CHANGED:'+table)
        if not cur.execute("select has_schema_privilege(%s,%s,'USAGE')and not has_schema_privilege(%s,%s,'CREATE')",(READER,schema,READER,schema)).fetchone()[0]:
            raise ValueError('RETENTION_REFERENCE_SCHEMA_AUTHORITY_CHANGED:'+schema)
        if cur.execute("select has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(READER,table)).fetchone()[0]:
            raise ValueError('RETENTION_REFERENCE_TABLE_PRIVILEGE_EXPOSED:'+table)
        columns=cur.execute('select attname from pg_attribute where attrelid=%s::regclass and attnum>0 and not attisdropped order by attnum',(table,)).fetchall()
        for (column,)in columns:
            privileges=cur.execute("select has_column_privilege(%s,%s,%s,'SELECT'),has_column_privilege(%s,%s,%s,'INSERT,UPDATE,REFERENCES')",(READER,table,column,READER,table,column)).fetchone()
            if privileges!=(column=='run_id',False):raise ValueError('RETENTION_REFERENCE_COLUMN_AUTHORITY_CHANGED:'+table+':'+column)
        for caller in CALLERS:
            if cur.execute("select has_any_column_privilege(%s,%s,'SELECT,INSERT,UPDATE,REFERENCES')or has_table_privilege(%s,%s,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')",(caller,table,caller,table)).fetchone()[0]:
                raise ValueError('RETENTION_REFERENCE_CALLER_EXPOSED:'+caller+':'+table)
    return dict(private_run_id_select_columns=2,table_select_grants=0,write_grants=0,
        browser_or_finance_reader_grants=0,owners_RLS_and_reader_role_preserved=True)


def verify(cur,state):
    if (state['sources']!=verify_sources()or state['catalog']!=own(state['after'])
        or _catalog_rows(cur)!=state['after']):
        raise ValueError('RETENTION_REFERENCE_SOURCE_OR_FULL22_CHANGED')
    admit_transition(state['before'],state['after'])
    return dict(check_permissions(cur),new_public_rpcs=0,new_tables=0,
        existing_schedule_unchanged=True,unit_statement_limits_unchanged=True,production_go=False)


def install_delta(cur,predecessor_checker):
    predecessor_checker(cur);before=_catalog_rows(cur)
    for key in COLUMNS:expected_column(key,before['columns'][key])
    change(cur,True);after=_catalog_rows(cur);admit_transition(before,after)
    state=dict(sources=verify_sources(),before=before,after=after,catalog=own(after))
    verify(cur,state);return state


def rollback_preuse(cur,state):
    verify(cur,state);change(cur,False)
    if _catalog_rows(cur)!=state['before']:
        raise ValueError('RETENTION_REFERENCE_PREUSE_INVERSE_NOT_EXACT')
