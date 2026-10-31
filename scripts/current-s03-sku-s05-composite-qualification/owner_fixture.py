"""Isolate the original last-owner fixture without changing its Native guard.

Only the private ACCESS case prepares administrative app-user rows, inside
the original strict rollback boundary. No role, permission, Auth, grant,
posted record, financial source or original business callback is changed.
"""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL=ROOT/'scripts/current-s05-wib-owner-fixture-successor-qualification'
ANCHOR='''        eligible=cur.execute("select u.auth_user_id::text from erp.app_users u join erp.app_roles r on r.id=u.role_id where u.is_active and u.auth_user_id is not null and r.role_code='OWNER'and r.is_active order by u.auth_user_id").fetchall()'''
REPLACEMENT='''        __JOIN_PREPARE_SINGLE_ORIGINAL_OWNER__(cur,owner,self.observations)
'''+ANCHOR
FACTORY_BEFORE="adapter=load('s05_wib_owner_private_fixture_adapter',HERE/'fixture_adapter.py').FixtureAdapter(private,state)"
FACTORY_AFTER='adapter=__JOIN_EXACT_OWNER_ADAPTER__(private,state)'
SCOPE_BEFORE='with adapter.case_scope(name):return operation()'
SCOPE_AFTER="""with adapter.case_scope(name):
                    result=operation()
                    if name=='S05_NATIVE_CURRENT_ACCESS_PRIVATE_ACL':
                        result['original_owner_fixture_observations']=adapter.observations
                    return result"""
ROSTER="""select u.id::text,u.auth_user_id::text,u.is_active,u.role,u.role_id::text,r.role_code,r.is_active
from erp.app_users u join erp.app_roles r on r.id=u.role_id
where u.is_active and u.auth_user_id is not null and r.role_code='OWNER'and r.is_active
order by u.auth_user_id,u.id"""
ALL_TARGETS="""select u.id::text,u.auth_user_id::text,u.is_active,u.role,u.role_id::text,r.role_code,r.is_active
from erp.app_users u join erp.app_roles r on r.id=u.role_id
where u.id=any(%s::uuid[])order by u.auth_user_id,u.id"""
DEACTIVATE='update erp.app_users set is_active=false where id=%s::uuid and auth_user_id=%s::uuid and is_active returning id::text'


def prepare_single_original_owner(cur,owner,observations):
    if(cur.connection.info.host not in('localhost','127.0.0.1')or cur.connection.info.port!=54322
       or cur.execute('select current_database()').fetchone()!=('cp6_rollback',)):
        raise ValueError('JOIN_OWNER_FIXTURE_DISPOSABLE_DATABASE_ONLY')
    session,cleanup=cur.execute("select session_user,current_setting('erp.cp45_allow_synthetic_cleanup',true)").fetchone()
    if session in('postgres','supabase_admin')and cleanup=='on':
        raise ValueError('JOIN_OWNER_FIXTURE_NO_SYNTHETIC_CLEANUP_ESCAPE')
    cur.execute("select pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('erp.active_owner_roster',0))")
    before=cur.execute(ROSTER).fetchall()
    original=[row for row in before if row[1]==owner]
    if len(original)!=1 or original[0][2:]!=(True,'OWNER',original[0][4],'OWNER',True):
        raise ValueError('JOIN_EXACT_ACTIVE_ORIGINAL_FIXTURE_OWNER_REQUIRED')
    extras=[row for row in before if row[1]!=owner]
    for row in extras:
        changed=cur.execute(DEACTIVATE,(row[0],row[1])).fetchall()
        if changed!=[(row[0],)]:raise ValueError('JOIN_OWNER_FIXTURE_EXACT_EXTRA_OWNER_CHANGED')
    after=cur.execute(ROSTER).fetchall()
    rows=cur.execute(ALL_TARGETS,([row[0]for row in before],)).fetchall()
    expected=[row if row[1]==owner else(row[0],row[1],False,*row[3:])for row in before]
    if after!=original or rows!=expected:
        raise ValueError('JOIN_OWNER_FIXTURE_ONLY_OTHER_ACTIVE_FLAGS_MAY_CHANGE')
    observations.append(dict(kind='EXPLICIT_ISOLATED_ORIGINAL_LAST_OWNER_ROSTER',
        original_owner_auth=owner,before=[list(row)for row in before],after=[list(row)for row in rows],
        temporarily_inactive_other_owner_auth=[row[1]for row in extras],
        original_last_owner_precondition_retained=True,Native_guard_or_trigger_changes=False,
        roles_permissions_grants_or_Auth_changed=False,synthetic_cleanup_escape=False,Native_case_credit=0))


def force_additional_owner(cur,business,report):
    if(cur.connection.info.host not in('localhost','127.0.0.1')or cur.connection.info.port!=54322
       or cur.execute('select current_database()').fetchone()!=('cp6_rollback',)):
        raise ValueError('JOIN_FOCUSED_OWNER_DISPOSABLE_DATABASE_ONLY')
    business.prod.owner(cur)
    owner=str(cur.execute('select auth.uid()').fetchone()[0]);business.b.api.admin(cur)
    before=cur.execute(ROSTER).fetchall()
    if len([row for row in before if row[1]==owner])!=1:
        raise ValueError('JOIN_FOCUSED_ORIGINAL_ACTIVE_OWNER_REQUIRED')
    spec=importlib.util.spec_from_file_location('joined_exact_original_backup_owner_fixture',ORIGINAL/'fixture_adapter.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    backup=module.second_active_owner(cur)
    after=cur.execute(ROSTER).fetchall()
    if backup==owner or len(after)!=len(before)+1 or len(after)<2:
        raise ValueError('JOIN_FOCUSED_ADDITIONAL_REAL_OWNER_REQUIRED')
    report['focused_additional_owner_fixture']=dict(original_owner_auth=owner,backup_owner_auth=backup,
        active_owners_before=len(before),active_owners_after=len(after),administrative_fixture_only=True,
        original_second_active_owner_helper=True,Native_guard_changes=0,Native_case_credit=0)


def replace(raw,before,after,label):
    text=raw.decode()
    if text.count(before)!=1 or after in text:raise ValueError('JOIN_OWNER_EXACT_SOURCE_ANCHOR:'+label)
    result=text.replace(before,after,1)
    if result.replace(after,before,1)!=text:raise ValueError('JOIN_OWNER_ORIGINAL_SOURCE_NOT_RECOVERED:'+label)
    return result,dict(original_sha256=sha256(raw).hexdigest(),derived_sha256=sha256(result.encode()).hexdigest(),
        counted_changes=1,original_bytes_recovered=True)


def prepared_sources():
    adapter,a=replace((ORIGINAL/'fixture_adapter.py').read_bytes(),ANCHOR,REPLACEMENT,'single_owner_fixture_preparation')
    factory,f=replace((ORIGINAL/'factory.py').read_bytes(),FACTORY_BEFORE,FACTORY_AFTER,'private_adapter_constructor')
    factory,metadata=replace(factory.encode(),SCOPE_BEFORE,SCOPE_AFTER,'retain_original_owner_guard_observations')
    return adapter,factory,dict(adapter=a,factory=f,raw_observation_retention=metadata,original_Native10_callback_changes=0,
        original_last_owner_and_protected_role_refusals_unchanged=True,Native_guard_changes=0,
        actual_Native_cases=0)


def factory():
    adapter_text,factory_text,_=prepared_sources()
    adapter=ModuleType('joined_private_S05_owner_fixture_adapter')
    adapter.__file__=str(ORIGINAL/'fixture_adapter.py')
    adapter.__dict__['__JOIN_PREPARE_SINGLE_ORIGINAL_OWNER__']=prepare_single_original_owner
    exec(compile(adapter_text,adapter.__file__,'exec'),adapter.__dict__)
    module=ModuleType('joined_private_S05_owner_fixture_factory');module.__file__=str(ORIGINAL/'factory.py')
    module.__dict__['__JOIN_EXACT_OWNER_ADAPTER__']=adapter.FixtureAdapter
    exec(compile(factory_text,module.__file__,'exec'),module.__dict__)
    return module
