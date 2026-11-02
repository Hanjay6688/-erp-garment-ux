"""Review exactly three Afui default-deny INFOs using actual live authority.

The existing predecessor/work-table reviewer stays unchanged. No warning,
policy, other object, public grant or worker privilege is accepted here.
"""
from pathlib import Path
import importlib.util,json

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='cp7_accessory_nonpayable'
TABLES=('category_versions_v1','date_requests_v1','good_bases_v1')
ROLES=('anon','authenticated','service_role','cp7_alert','cp7_finance_read')
PRIVILEGES=('SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER')


def parent():
    path=ROOT/'scripts/current-choice-preparation-native-qualification/advisor_review.py'
    spec=importlib.util.spec_from_file_location('afui_exact_unchanged_private_work_reviewer',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def require_closed(proof):
    parent().require_closed(proof['predecessor'])
    if set(proof['Afui'])!=set(TABLES):raise ValueError('NONPAYABLE_ADVISOR_EXACT_THREE_TABLE_AUTHORITIES_REQUIRED')
    for name,row in proof['Afui'].items():
        expected=dict(object=[SCHEMA,name],owner='postgres',rls=True,force_rls=False,policies=[],
            public_schema_acl_empty=True,public_table_acl_empty=True,
            schema_usage={role:False for role in ROLES},
            table_privileges={role:{priv:False for priv in PRIVILEGES}for role in ROLES})
        if json.dumps(row,sort_keys=True,allow_nan=False)!=json.dumps(expected,sort_keys=True,allow_nan=False):
            raise ValueError('NONPAYABLE_ADVISOR_PRIVATE_DEFAULT_DENY_AUTHORITY_CHANGED:'+name)
    return proof


def capture(cur):
    result=dict(predecessor=parent().capture(cur),Afui={})
    for name in TABLES:
        qualified=SCHEMA+'.'+name
        owner,rls,force=cur.execute('select pg_get_userbyid(relowner),relrowsecurity,relforcerowsecurity '
            'from pg_class where oid=%s::regclass',(qualified,)).fetchone()
        policies=cur.execute('select polname from pg_policy where polrelid=%s::regclass order by polname',(qualified,)).fetchall()
        public_schema=cur.execute("select not exists(select 1 from pg_namespace n,"
            "lateral aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner)))a "
            "where n.nspname=%s and a.grantee=0)",(SCHEMA,)).fetchone()[0]
        public_table=cur.execute("select not exists(select 1 from pg_class c,"
            "lateral aclexplode(coalesce(c.relacl,acldefault('r',c.relowner)))a "
            "where c.oid=%s::regclass and a.grantee=0)",(qualified,)).fetchone()[0]
        result['Afui'][name]=dict(object=[SCHEMA,name],owner=owner,rls=rls,force_rls=force,policies=policies,
            public_schema_acl_empty=public_schema,public_table_acl_empty=public_table,
            schema_usage={role:cur.execute("select has_schema_privilege(%s,%s,'USAGE')",(role,SCHEMA)).fetchone()[0]for role in ROLES},
            table_privileges={role:{priv:cur.execute('select has_table_privilege(%s,%s,%s)',(role,qualified,priv)).fetchone()[0]
                for priv in PRIVILEGES}for role in ROLES})
    return require_closed(result)


def review(delta,manifest,proof,predecessor_review):
    require_closed(proof)
    original=parent().review(delta,manifest,proof['predecessor'],predecessor_review)
    reviewed=[];unexplained=[]
    for finding in original['unexplained']:
        meta=finding.get('metadata')or{}
        exact=(finding.get('name')=='rls_enabled_no_policy'and finding.get('level')=='INFO'
            and meta.get('type')=='table'and meta.get('schema')==SCHEMA and meta.get('name')in TABLES)
        (reviewed if exact else unexplained).append(finding)
    names=[row['metadata']['name']for row in reviewed]
    passed=(delta.get('status')in('NO_NEW_FINDINGS','REVIEW_REQUIRED')and not unexplained
        and len(names)==len(set(names))and set(names).issubset(TABLES))
    return dict(status='VERIFIED_AFUI_PRIVATE_DEFAULT_DENY_INFO'if passed else'UNEXPLAINED_FINDINGS',
        predecessor_disposition=original,reviewed_Afui_private_info=reviewed,current_private_authority=proof,
        unexplained=unexplained,gate=bool(passed))
