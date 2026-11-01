"""Restore only the original empty-database fixture setup, with no case credit.

The omitted Native31 included a committed fixture foundation. Its existing
seed, including its narrowly restored historical trigger compatibility, is
reused byte for byte. Partial foundations are refused rather than repaired.
No connection, commit, product DDL or financial assertion is owned here.
"""
from hashlib import sha256
from pathlib import Path
import json,re,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
REQUIRED={
    'erp.materials':'c8c30000-0000-4000-8000-000000000002',
    'erp.suppliers':'c8c30000-0000-4000-8000-000000000001',
    'erp.product_models':'a2000000-0000-0000-0000-000000000001',
    'erp.contractors':'a1000000-0000-0000-0000-000000000001',
    'erp.production_patterns':'c8c10000-0000-4000-8000-000000000001',
    'erp.sizes':'c8c10000-0000-4000-8000-000000000002',
    'erp.products':'c8c10000-0000-4000-8000-000000000004',
    'erp.locations':'c8c20000-0000-4000-8000-000000000001',
    'erp.laundry_vendors':'c8c20000-0000-4000-8000-000000000002',
    'erp.wash_processes':'c8c20000-0000-4000-8000-000000000003',
    'erp.po_work_component_snapshots':'a4100000-0000-0000-0000-000000000001',
}
OPERATOR_AUTH='c8c00000-0000-4000-8000-000000000101'
SEED='cp6_ao_ap_installed.seed'

def preflight():
    """Validate the complete original seed/include closure before ERP imports."""
    origin=json.loads((HERE/'FOUNDATION_ORIGIN.json').read_bytes())
    if origin['seed']!=SEED or origin['new_Native_case_credit']!=0:
        raise ValueError('FOCUSED_EXACT_ORIGINAL_FOUNDATION_SETUP_REQUIRED')
    for name,pin in origin['files'].items():
        raw=(ROOT/name).read_bytes()
        if dict(bytes=len(raw),sha256=sha256(raw).hexdigest())!=pin:
            raise ValueError('FOCUSED_ORIGINAL_FOUNDATION_SOURCE_CHANGED:'+name)
        original=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',origin['source_commit']+':'+name])
        if raw!=original:raise ValueError('FOCUSED_FOUNDATION_IS_NOT_ORIGINAL_SOURCE:'+name)
    seen=set()
    def includes(name):
        if name in seen:return
        seen.add(name)
        for item in re.findall(r'^\\ir\s+(.+?)\s*$',(ROOT/name).read_text(),re.M):
            path=Path(name).parent/item
            if path.is_absolute()or'..'in path.parts:raise ValueError('FOCUSED_FOUNDATION_INCLUDE_ESCAPE')
            includes(str(path))
    includes('supabase/tests/cp3_r4_full_schema_seed.sql')
    includes('supabase/tests/cp6_laundry_qc_concurrency_seed.sql')
    if seen!={n for n in origin['files']if n.endswith('.sql')}:
        raise ValueError('FOCUSED_COMPLETE_FOUNDATION_SEED_CLOSURE_REQUIRED')
    return dict(status='EXACT_ORIGINAL_FOUNDATION_SOURCE_AND_INCLUDE_CLOSURE',seed=SEED,
        source_commit=origin['source_commit'],files=origin['files'],Native_case_credit=0)

def observe(cur):
    connection=cur.connection
    if (connection.info.host not in('127.0.0.1','localhost')or connection.info.port!=54322
            or cur.execute('select current_database()').fetchone()!=('cp6_rollback',)):
        raise ValueError('FOCUSED_FOUNDATION_LOCAL_DISPOSABLE_ONLY')
    return dict(app_users=cur.execute('select count(*) from erp.app_users').fetchone()[0],
        active_owner_roles=cur.execute("select count(*) from erp.app_roles where role_code='OWNER'and is_active").fetchone()[0],
        original_owner=cur.execute("select count(*) from erp.app_users u join erp.app_roles r on r.id=u.role_id where u.auth_user_id=%s and u.is_active and r.role_code='OWNER'and r.is_active",(OPERATOR_AUTH,)).fetchone()[0],
        required={name:cur.execute('select exists(select 1 from '+name+' where id=%s)',(identity,)).fetchone()[0]
                  for name,identity in REQUIRED.items()})

def classify(value):
    if (type(value.get('app_users'))is not int or value['app_users']<0
            or type(value.get('active_owner_roles'))is not int or value['active_owner_roles']!=1
            or type(value.get('original_owner'))is not int
            or set(value.get('required',{}))!=set(REQUIRED)
            or any(type(v)is not bool for v in value['required'].values())):
        raise ValueError('FOCUSED_EXACT_TYPED_FOUNDATION_PREREQUISITES_REQUIRED')
    if value['app_users']==0 and value['original_owner']==0 and not any(value['required'].values()):
        return 'ORIGINAL_EMPTY_DATABASE_SEED_REQUIRED'
    if value['app_users']>0 and value['original_owner']==1 and all(value['required'].values()):
        return 'ORIGINAL_FOUNDATION_ALREADY_PRESENT'
    raise ValueError('FOCUSED_PARTIAL_OR_FOREIGN_FOUNDATION_REFUSED')

def check_before_install(cur):
    """Read-only fail-fast check, before the full parent installer."""
    source=preflight();initial=observe(cur)
    return dict(status='READ_ONLY_FOUNDATION_PRECHECK',mode=classify(initial),initial=initial,
        source=source,database_mutated=False,Native_case_credit=0)

def authority(cur):
    return {name:cur.execute("select coalesce(jsonb_agg(to_jsonb(r)order by to_jsonb(r)::text),'[]'::jsonb) from "+name+' r').fetchone()[0]
            for name in('erp.app_roles','erp.app_role_permissions')}

def prepare(cur,product,state,control,report):
    import cp6_ao_ap_installed as original
    original.admin(cur)
    initial=observe(cur);mode=classify(initial)
    report.update(status='INCOMPLETE',source=preflight(),mode=mode,initial=initial,seed=SEED,
        Native_case_credit=0,retained_cases_rerun=False,production_go=False)
    catalog=product.runtime()[-1]
    with control.product_catalog(cur):
        product.verify(cur,state)
        before=catalog._catalog_rows(cur)
    acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()
    roles=authority(cur)
    if mode=='ORIGINAL_EMPTY_DATABASE_SEED_REQUIRED':original.seed(cur)
    final=observe(cur)
    if classify(final)!='ORIGINAL_FOUNDATION_ALREADY_PRESENT':
        raise ValueError('FOCUSED_COMPLETE_ORIGINAL_FOUNDATION_REQUIRED_BEFORE_BROWSER')
    if cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()!=acl:
        raise ValueError('FOCUSED_ORIGINAL_SEED_CHANGED_SCHEMA_ACL')
    if authority(cur)!=roles:raise ValueError('FOCUSED_ORIGINAL_SEED_CHANGED_PROTECTED_ROLE_DATA')
    # Exactly the existing Native SQL harness overlay, never a product grant.
    if not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]:
        cur.execute('grant usage on schema erp to authenticated')
    with control.product_catalog(cur):
        product.verify(cur,state)
        after=catalog._catalog_rows(cur)
    if after!=before:raise ValueError('FOCUSED_FOUNDATION_CHANGED_ANY_PRODUCT_CATALOG_CLASS')
    report.update(status='EXACT_RETAINED_FIXTURE_FOUNDATION_READY',final=final,
        seed_called=mode=='ORIGINAL_EMPTY_DATABASE_SEED_REQUIRED',actual_all22_before=before,
        actual_all22_after=after,all22_equal=True,original_seed_schema_ACL_equal=True,
        protected_role_data_before=roles,protected_role_data_after=authority(cur),
        protected_role_data_equal=True,only_existing_Native_SQL_harness_usage_overlay=True,
        connection_and_commit_owned_by_component=True)
