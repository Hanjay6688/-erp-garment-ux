"""Review one new private default-deny INFO after exact live authority checks.

The predecessor advisor policy remains unchanged. This does not classify any
warning, another table, permissive policy, or direct browser/worker privilege.
"""
SCHEMA='cp7_frozen_choice_preparation'
TABLE='work'
ROLES=('anon','authenticated','service_role','cp7_alert','cp7_finance_read')
PRIVILEGES=('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER')


def require_closed(proof):
    assert proof['object']==[SCHEMA,TABLE]
    assert proof['owner']=='cp7_capture' and proof['rls'] is True
    assert proof['policies']==[]
    assert proof['public_schema_acl_empty'] is proof['public_table_acl_empty'] is True
    assert proof['schema_usage']=={role:False for role in ROLES}
    assert proof['table_privileges']=={role:{p:False for p in PRIVILEGES} for role in ROLES}
    return proof


def capture(cur):
    owner,rls=cur.execute('select pg_get_userbyid(relowner),relrowsecurity '
        'from pg_class where oid=%s::regclass',(SCHEMA+'.'+TABLE,)).fetchone()
    policies=cur.execute('select polname from pg_policy where polrelid=%s::regclass order by polname',
        (SCHEMA+'.'+TABLE,)).fetchall()
    public_schema=cur.execute("select not exists(select 1 from pg_namespace n,"
        "lateral aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a "
        "where n.nspname=%s and a.grantee=0)",(SCHEMA,)).fetchone()[0]
    public_table=cur.execute("select not exists(select 1 from pg_class c,"
        "lateral aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a "
        "where c.oid=%s::regclass and a.grantee=0)",(SCHEMA+'.'+TABLE,)).fetchone()[0]
    schemas={role:cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]
             for role in ROLES}
    privileges={role:{priv:cur.execute('select has_table_privilege(%s,%s,%s)',
        (role,SCHEMA+'.'+TABLE,priv)).fetchone()[0] for priv in PRIVILEGES} for role in ROLES}
    return require_closed(dict(object=[SCHEMA,TABLE],owner=owner,rls=rls,policies=policies,
        public_schema_acl_empty=public_schema,public_table_acl_empty=public_table,
        schema_usage=schemas,table_privileges=privileges))


def review(delta,manifest,proof,predecessor_review):
    require_closed(proof)
    original=predecessor_review(delta,manifest)
    reviewed=[];unexplained=[]
    for finding in original['unexplained']:
        meta=finding.get('metadata') or {}
        exact=(finding.get('name')=='rls_enabled_no_policy' and finding.get('level')=='INFO'
               and meta.get('type')=='table' and meta.get('schema')==SCHEMA and meta.get('name')==TABLE)
        (reviewed if exact else unexplained).append(finding)
    comparable=delta.get('status') in ('NO_NEW_FINDINGS','REVIEW_REQUIRED')
    passed=comparable and not unexplained and len(reviewed)<=1
    return dict(status='VERIFIED_PRIVATE_DEFAULT_DENY_INFO' if passed and reviewed else
        original['status'],predecessor_disposition=original,reviewed_new_private_info=reviewed,
        current_private_authority=proof,unexplained=unexplained,gate=bool(passed))
