"""Two private fixture dependencies; original10 callbacks and Native stay exact."""
from contextlib import contextmanager
from hashlib import sha256
import json
import psycopg
import uuid

WIB_CASE='S05_NATIVE_WIB_COHORTS'
ACCESS_CASE='S05_NATIVE_CURRENT_ACCESS_PRIVATE_ACL'
WIB_ERROR='Waktu pengambilan wajib memakai tanggal dan jam WIB'
OWNER_ERROR='LAST_ACTIVE_OWNER_PROTECTED'


def second_active_owner(cur):
    """Add a fixture user to the existing active role without writing that role."""
    roles=cur.execute("select id from erp.app_roles where role_code='OWNER' and is_active").fetchall()
    if len(roles)!=1:
        raise ValueError('S05_EXACT_EXISTING_ACTIVE_OWNER_ROLE_REQUIRED')
    auth=str(uuid.uuid4())
    cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) values(gen_random_uuid(),%s,%s,%s,%s,true)",
                (auth,'S05 administrative backup owner','OWNER',roles[0][0]))
    return auth


def exact_supported_timestamp(day, supplied):
    transitions={str(day)+'T00:00:00.000000+07:00':str(day)+'T00:00:00+07:00',
                 str(day)+'T23:59:59.999999+07:00':str(day)+'T23:59:59+07:00'}
    if supplied not in transitions:
        raise ValueError('S05_ONLY_TWO_ORIGINAL_WIB_FIXTURE_STRINGS_ALLOWED')
    return transitions[supplied]


class FixtureAdapter:
    def __init__(self,business,state):
        self.business=business
        self.actual_installed_parent=state
        self.original_fixture=business.fixture
        self.original_issue_note=business.issue_note
        self.active=None
        self.observations=[]
        self.native_inputs=None

    @contextmanager
    def case_scope(self,name):
        if self.active is not None or name not in (WIB_CASE,ACCESS_CASE):
            raise ValueError('S05_EXACT_PRIVATE_CASE_SCOPE_REQUIRED')
        self.active=name
        try:yield
        finally:self.active=None

    def no_effect(self,cur,label,operation,expected,sqlstate):
        """Real Native refusal with full actual all22/data/ALLsequence equality."""
        from cp7_p21_current_chain_rehearsal_probe import helper
        self.business.b.api.admin(cur)
        product=self.business.stage.parent()
        _,_,_,_,catalog=product.runtime()
        with helper.control.product_catalog(cur):
            product.verify(cur,self.actual_installed_parent)
            if self.native_inputs is None:
                self.native_inputs={}
                for signature in ('erp._idempotency_begin(text,uuid,text)','erp.guard_last_active_owner()',
                                  'erp.guard_protected_role()',
                                  'erp.save_accessory_issue_action_v1(text,jsonb,uuid)'):
                    ddl=cur.execute('select pg_get_functiondef(%s::regprocedure)',(signature,)).fetchone()[0]
                    self.native_inputs[signature]=dict(definition=ddl,sha256=sha256(ddl.encode()).hexdigest())
                self.observations.append(dict(kind='ACTUAL_FRESH_VERIFIED_PARENT_NATIVE_INPUT_CAPTURE',
                    functions=self.native_inputs,claimed_actual52eed_capture=False,Native_case_credit=0))
            before_catalog=catalog._catalog_rows(cur)
            before_data=catalog._data(cur)
        cur.execute('savepoint s05_fixture_native_refusal')
        error=None
        try:
            try:operation()
            except psycopg.Error as caught:
                error=dict(message=str(caught),sqlstate=caught.sqlstate)
            cur.execute('rollback to savepoint s05_fixture_native_refusal')
            self.business.b.api.admin(cur)
            if error is None or error['sqlstate']!=sqlstate or error['message'].splitlines()[0]!=expected:
                raise AssertionError(('S05_EXACT_NATIVE_FIXTURE_REFUSAL_REQUIRED',label,expected,error))
        finally:
            cur.execute('release savepoint s05_fixture_native_refusal')
        with helper.control.product_catalog(cur):
            after_catalog=catalog._catalog_rows(cur)
            after_data=catalog._data(cur)
            if after_catalog!=before_catalog or after_data!=before_data:
                raise AssertionError('S05_NATIVE_FIXTURE_REFUSAL_CHANGED_ALL22_DATA_OR_ANY_SEQUENCE:'+label)
            product.verify(cur,self.actual_installed_parent)
        event=dict(kind='ACTUAL_NATIVE_FIXTURE_REFUSAL_NO_EFFECT',case_id=self.active,label=label,
            actual_error=error,all22_catalog_equal=True,all_rows_and_every_sequence_equal=True,
            actual_parent_verified_before_and_after=True,Native_case_credit=0,
            before_catalog_sha256=catalog.digest(before_catalog),before_data_sha256=catalog.digest(before_data))
        self.observations.append(event)
        return event

    def issue_note(self,cur,f,qty='7',*,linked=True,action='POST',previous=False,material=None,at=None):
        kwargs=dict(linked=linked,action=action,previous=previous,material=material,at=at)
        if self.active!=WIB_CASE or at is None:
            return self.original_issue_note(cur,f,qty,**kwargs)
        supported=exact_supported_timestamp(f['day'],at)
        if action!='POST' or previous or not linked or material is not None or qty not in ('2','3'):
            raise ValueError('S05_EXACT_ORIGINAL_WIB_CALL_PAYLOAD_REQUIRED')
        self.no_effect(cur,'ORIGINAL_FRACTIONAL_WIB_'+qty,
            lambda:self.original_issue_note(cur,f,qty,**kwargs),WIB_ERROR,'P0001')
        kwargs['at']=supported
        result=self.original_issue_note(cur,f,qty,**kwargs)
        self.observations.append(dict(kind='NATIVE_SUPPORTED_WIB_SECONDS_FIXTURE_POST',case_id=self.active,
            original_unsupported_value=at,actual_native_payload_value=supported,
            physical_WIB_date=str(f['day']),qty=qty,Native_case_credit=0,
            same_WIB_date_cohort=True,Native_parser_or_date_guard_changes=False))
        return result

    def fixture(self,cur,today,*,rate='2',empty=False,finish=True,previous_issue=False,method='BOM_STANDARD'):
        f=self.original_fixture(cur,today,rate=rate,empty=empty,finish=finish,previous_issue=previous_issue,method=method)
        if self.active!=ACCESS_CASE:return f
        if rate!='2' or empty is not True or finish is not True or previous_issue or method!='BOM_STANDARD':
            raise ValueError('S05_EXACT_ORIGINAL_ACCESS_FIXTURE_REQUIRED')
        self.business.prod.owner(cur)
        owner=str(cur.execute('select auth.uid()').fetchone()[0])
        self.business.b.api.admin(cur)
        session,cleanup=cur.execute("select session_user,current_setting('erp.cp45_allow_synthetic_cleanup',true)").fetchone()
        if session in ('postgres','supabase_admin') and cleanup=='on':
            raise ValueError('S05_OWNER_FIXTURE_MUST_NOT_USE_SYNTHETIC_CLEANUP_ESCAPE')
        eligible=cur.execute("select u.auth_user_id::text from erp.app_users u join erp.app_roles r on r.id=u.role_id where u.is_active and u.auth_user_id is not null and r.role_code='OWNER'and r.is_active order by u.auth_user_id").fetchall()
        if eligible!=[(owner,)]:
            raise ValueError('S05_EXACT_SINGLE_ORIGINAL_FIXTURE_OWNER_REQUIRED')
        self.no_effect(cur,'LAST_ACTIVE_OWNER_UNCHANGED',
            lambda:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner,)),OWNER_ERROR,'42501')
        self.no_effect(cur,'PROTECTED_OWNER_ROLE_UNCHANGED',
            lambda:cur.execute("update erp.app_roles set is_active=true where role_code='OWNER'"),
            'PROTECTED_OWNER_ROLE_CANNOT_BE_CHANGED','42501')
        backup=second_active_owner(cur)
        if backup==owner:raise AssertionError('S05_DISTINCT_ADMINISTRATIVE_BACKUP_OWNER_REQUIRED')
        actual=cur.execute("select u.auth_user_id::text,u.is_active,u.role,r.role_code,r.is_active from erp.app_users u join erp.app_roles r on r.id=u.role_id where u.auth_user_id in(%s,%s)order by u.auth_user_id",(owner,backup)).fetchall()
        if len(actual)!=2 or {row[0]for row in actual}!={owner,backup} or any(row[1:]!=(True,'OWNER','OWNER',True)for row in actual):
            raise AssertionError('S05_TWO_REAL_ACTIVE_OWNER_FIXTURE_ROWS_REQUIRED')
        self.observations.append(dict(kind='RETAINED_ADMINISTRATIVE_SECOND_OWNER_FIXTURE',case_id=self.active,
            original_owner_auth=owner,backup_owner_auth=backup,active_owner_rows=2,
            fixture_helper='second_active_owner(existing_active_role)',new_grants_or_roles=False,
            Native_guard_or_trigger_changes=False,Native_case_credit=0))
        return f
