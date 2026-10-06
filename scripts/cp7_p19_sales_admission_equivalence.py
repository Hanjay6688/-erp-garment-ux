"""Compare private admission with the unchanged Native access-document guard.

Read-only decisions, current real app profiles/permissions, exact refusal class.
This strengthens the existing P11 private-fields case; it adds no case credit.
Every temporary profile/permission change is rolled back before returning.
"""
import json
import uuid
import psycopg

ACTIONS = ('CREATE','EDIT','POST','CANCEL','PAYMENT','PAYMENT_REVERSE',
           'RETURN','RETURN_REVERSE','SALE_REVERSE',None,'INVALID')
PERMISSIONS = ('sales.invoice.view','finance.ar.view','sales.invoice.create',
               'sales.invoice.edit_draft','sales.invoice.post','sales.invoice.reverse',
               'sales.payment.view','sales.payment.create','sales.payment.post','sales.payment.reverse',
               'sales.return.view','sales.return.create','sales.return.post','sales.return.reverse')


def compare(cur, auth, api, boundary):
    api.admin(cur)
    before = boundary.snapshot(cur)
    cur.execute('savepoint p19_admission_equivalence')
    decisions = []
    protected_mutation_refusals = []
    try:
        subject, role = auth.custom_actor(cur)
        for permission in PERMISSIONS:
            cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s) on conflict do nothing',
                        (role, permission))

        def decision(signature, action):
            cur.execute('savepoint p19_admission_read')
            try:
                result = cur.execute('select '+signature+'(%s)', (action,)).fetchone()[0]
                assert result is not None
                if signature.endswith('command_allowed'):
                    assert result is True
                else:
                    assert result['allowed'] is True
                return ('ALLOW',)
            except psycopg.Error as error:
                return (error.sqlstate, error.diag.message_primary)
            finally:
                cur.execute('rollback to savepoint p19_admission_read')
                cur.execute('release savepoint p19_admission_read')

        def pair(label, subject_id=subject, jwt_role='authenticated'):
            api.admin(cur)
            cur.execute("select set_config('request.jwt.claim.sub','',true)")
            cur.execute("select set_config('request.jwt.claims',%s,true)",
                        (json.dumps(dict(sub=subject_id, role=jwt_role)),))
            for action in ACTIONS:
                old = decision('cp7_sales.command_access', action)
                new = decision('cp7_sales.command_allowed', action)
                assert old == new, ('P19_ADMISSION_DECISION_DIFFERENCE', label, action, old, new)
                decisions.append(dict(state=label, action=action, decision=list(old)))

        pair('ALL_PERMISSIONS_CUSTOM_ROLE')
        for permission in PERMISSIONS:
            api.admin(cur)
            cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s', (role,permission))
            pair('REVOKED:'+permission)
            api.admin(cur)
            cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)', (role,permission))
        pair('PERMISSIONS_RESTORED')
        api.admin(cur)
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
        pair('USER_INACTIVE')
        api.admin(cur)
        cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(subject,))
        cur.execute('update erp.app_roles set is_active=false where id=%s',(role,))
        pair('ROLE_INACTIVE')
        api.admin(cur)
        cur.execute('update erp.app_roles set is_active=true where id=%s',(role,))
        pair('SERVICE_JWT_REJECTED',jwt_role='service_role')
        pair('ANON_JWT_REJECTED',jwt_role='anon')
        pair('AUTH_SUBJECT_ABSENT',subject_id=None)
        pair('APP_USER_UNMAPPED',subject_id=str(uuid.uuid4()))
        pair('CLAIM_ROLE_OWNER_REJECTED',jwt_role='OWNER')
        api.admin(cur)
        cur.execute('update erp.app_roles set is_protected=true where id=%s',(role,))
        pair('CUSTOM_ROLE_PROTECTED_HAS_NO_UNIVERSAL_GRANT')
        api.admin(cur)
        cur.execute('update erp.app_roles set is_protected=false where id=%s',(role,))
        cur.execute("update erp.app_permissions set is_active=false where permission_key='finance.ar.view'")
        pair('PERMISSION_CATALOG_INACTIVE')
        api.admin(cur)
        cur.execute("update erp.app_permissions set is_active=true where permission_key='finance.ar.view'")
        for code in ('OWNER','ADMIN'):
            api.admin(cur)
            native_role = cur.execute('select id from erp.app_roles where role_code=%s and is_active',(code,)).fetchone()[0]
            cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(native_role,subject))
            pair('NATIVE_ROLE:'+code)
            if code == 'OWNER':
                owner_before = cur.execute('select to_jsonb(r) from erp.app_roles r where id=%s',(native_role,)).fetchone()[0]
                mapping_before = cur.execute('select permission_key from erp.app_role_permissions where role_id=%s order by permission_key',(native_role,)).fetchall()
                assert owner_before['is_protected'] and mapping_before
                def protected_refusal(label, sql, args):
                    cur.execute('savepoint p19_protected_owner_refusal')
                    try:
                        cur.execute(sql, args)
                    except psycopg.Error as error:
                        assert (error.sqlstate,error.diag.message_primary)==('42501','PROTECTED_OWNER_ROLE_CANNOT_BE_CHANGED')
                        protected_mutation_refusals.append(dict(attempt=label,sqlstate=error.sqlstate,message=error.diag.message_primary))
                    else:
                        raise AssertionError('P19_PROTECTED_OWNER_MUTATION_WAS_ALLOWED:'+label)
                    finally:
                        cur.execute('rollback to savepoint p19_protected_owner_refusal')
                        cur.execute('release savepoint p19_protected_owner_refusal')
                    assert cur.execute('select to_jsonb(r) from erp.app_roles r where id=%s',(native_role,)).fetchone()[0]==owner_before
                    assert cur.execute('select permission_key from erp.app_role_permissions where role_id=%s order by permission_key',(native_role,)).fetchall()==mapping_before
                    pair(label)
                protected_refusal('OWNER_MAPPING_DELETE_REFUSED','delete from erp.app_role_permissions where role_id=%s',(native_role,))
                cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
                pair('OWNER_USER_INACTIVE')
                cur.execute('update erp.app_users set is_active=true where auth_user_id=%s',(subject,))
                protected_refusal('OWNER_ROLE_DEACTIVATION_REFUSED','update erp.app_roles set is_active=false where id=%s',(native_role,))
                protected_refusal('OWNER_UNPROTECT_REFUSED','update erp.app_roles set is_protected=false where id=%s',(native_role,))
                protected_refusal('OWNER_AR_REVOKE_REFUSED',"delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(native_role,))
            else:
                for permission in PERMISSIONS:
                    cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s) on conflict do nothing',(native_role,permission))
                cur.execute('update erp.app_roles set is_protected=true where id=%s',(native_role,))
                pair('ADMIN_PROTECTED_HAS_NO_UNIVERSAL_GRANT')
                cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(native_role,))
                pair('ADMIN_PROTECTED_AR_REVOKED')
                cur.execute('delete from erp.app_role_permissions where role_id=%s',(native_role,))
                pair('ADMIN_NO_EXPLICIT_PERMISSIONS')
    finally:
        cur.execute('rollback to savepoint p19_admission_equivalence')
        cur.execute('release savepoint p19_admission_equivalence')
        api.admin(cur)
    assert boundary.snapshot(cur) == before, 'P19_ADMISSION_NATIVE_BOUNDARY_CHANGED'
    assert len(decisions) == 35 * len(ACTIONS) == 385
    assert len(protected_mutation_refusals) == 4
    return dict(status='EXACT_DECISIONS_AND_REFUSALS', comparisons=len(decisions), decisions=decisions,
                all_actions_and_current_revocations=True, full_boundary_restored=True,
                protected_OWNER_mutation_refusals=protected_mutation_refusals,
                protected_OWNER_guards_not_disabled=True,
                comparison_profiles=31, post_refusal_rechecks=4,
                Native_case_credit_added=0, Native_money_HPP_engines_changed=False,
                authority_cached=False)
