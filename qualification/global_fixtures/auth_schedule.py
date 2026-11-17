"""Dispatch ordinary Auth cases with the already owned application and issuer."""

from contextlib import contextmanager
from datetime import date
import re
from types import SimpleNamespace


DATABASE_ID = ('select current_database(),oid::bigint,(pg_control_system()).system_identifier::text '
               'from pg_database where datname=current_database()')
ADMIN_MAPPING = "p.role_id=r.id and r.role_code='ADMIN' and r.is_active and r.id=%s::uuid and p.permission_key=%s"
COLUMNS = 'p.role_id::text,p.permission_key,p.granted_by::text,p.granted_at'


def need(condition, reason):
    if not condition:
        raise ValueError('GLOBAL_AUTH_ORDINARY_SCHEDULE_' + reason)


def permission_window(conn, cur, *, attempt, admin, plan, verify, require_quiet, retain):
    """Restore the exact mapping row in the disposable application after ordinary refusals."""
    consumed = False

    @contextmanager
    def transaction():
        require_quiet()
        with conn.transaction():
            info = conn.info
            need(attempt.phase == 'ACTIVE' and info.user == 'supabase_admin' and cur.connection is conn
                 and info.host in ('localhost', '127.0.0.1') and info.port == 54322 and info.dbname == 'cp6_rollback'
                 and cur.execute(DATABASE_ID).fetchone() == attempt.app
                 and attempt.app[0] == 'cp6_rollback' and attempt.app[1] != attempt.issuer[1]
                 and attempt.app[2] == attempt.issuer[2] and verify(cur).get('full25_verified') is True,
                 'DISPOSABLE_APPLICATION_AND_VERIFIER_REQUIRED')
            yield

    @contextmanager
    def window(access):
        nonlocal consumed
        plan.check_registry(attempt)
        labels = dict(plan.ACTOR_PLAN)
        subject = attempt.subjects.get(('ADMIN', labels['ADMIN']))
        need(not consumed and subject is not None and any(admin is actor for actor in attempt._actors)
             and admin.role == access.get('role') == 'ADMIN' and access.get('auth_uid') == subject.uid == admin.auth_user_id
             and access.get('app_user_id') == subject.app_id and access.get('application_oid') == attempt.app[1]
             and access.get('issuer_oid') == attempt.issuer[1] and access.get('cluster_system_id') == attempt.app[2]
             and access.get('attempt') == attempt.attempt, 'EXACT_SINGLE_OWNED_ADMIN_WINDOW_REQUIRED')
        plan.require_permissions(access, {plan.REVOKED_PERMISSION})
        key = (access['role_id'], plan.REVOKED_PERMISSION)
        consumed = True
        with transaction():
            rows = cur.execute(f'delete from erp.app_role_permissions p using erp.app_roles r '
                               f'where {ADMIN_MAPPING} returning {COLUMNS}', key).fetchall()
            need(len(rows) == 1 and rows[0][:2] == key, 'DELETE_EXACT_EXISTING_ADMIN_MAPPING_REQUIRED')
        try:
            require_quiet()
            retain('GLOBAL_AUTH_ADMIN_MAPPING_REMOVED', dict(role_id=key[0], permission_key=key[1], committed=True))
            yield
        finally:
            with transaction():
                row, = rows
                restored = cur.execute('insert into erp.app_role_permissions as p(role_id,permission_key,granted_by,granted_at) '
                                       'select r.id,%s,%s::uuid,%s from erp.app_roles r '
                                       "where r.id=%s::uuid and r.role_code='ADMIN' and r.is_active "
                                       f'returning {COLUMNS}', (row[1], row[2], row[3], row[0])).fetchall()
                need(restored == rows, 'RESTORE_EXACT_ADMIN_MAPPING_REQUIRED')
            require_quiet()
            retain('GLOBAL_AUTH_ADMIN_MAPPING_RESTORED', dict(role_id=key[0], permission_key=key[1], committed=True))

    return window


def bind(*, plan, native, credit, s05, prepare_s05, capture_scope, source_identity, business_day):
    """Create the HTTP callback for the existing ordinary Global schedule."""
    started = False
    committed_s05 = None

    def prepare(attempt, *, verify, require_quiet, retain):
        nonlocal committed_s05
        plan.check_attempt(attempt, source_identity)
        need(committed_s05 is None and attempt.phase == 'ACTIVE', 'ONE_ACTIVE_REPORT_FIXTURE_REQUIRED')
        require_quiet()
        today = business_day()
        need(type(today) is date, 'PLANNED_BUSINESS_DATE_REQUIRED')
        native_report, setup = prepare_s05(attempt=attempt, verify=verify, today=today)
        require_quiet()
        original = retain('GLOBAL_AUTH_S05_COMMITTED_REPORT_FIXTURE', setup)
        committed_s05 = (attempt, verify, today, native_report)
        return dict(status='COMMITTED', original=original)

    def exercise_http(attempt, *, conn, cur, state, verify, report, require_quiet, outside_id, retain):
        nonlocal started
        plan.check_attempt(attempt, source_identity)
        need(not started and not report and attempt.phase == 'ACTIVE' and not attempt.verified_actors
             and not attempt.application_rpc_responses and committed_s05 is not None
             and committed_s05[0] is attempt and committed_s05[1] is verify, 'ONE_ACTIVE_HTTP_SEQUENCE_REQUIRED')
        profile = state.global_installation['profile_id']
        need(type(profile) is str and re.fullmatch('[a-f0-9]{64}', profile), 'INSTALLED_PROFILE_REQUIRED')
        started = True
        phase = 'BUSINESS_DAY'
        require_quiet()
        try:
            today = business_day()
            need(type(today) is date and today == committed_s05[2], 'PLANNED_BUSINESS_DATE_REQUIRED')
            phase = 'COMMITTED_FIXTURES'
            prepared = native.prepare(conn, cur, attempt=attempt, verify=verify, today=today)
            retain('GLOBAL_AUTH_CREDIT_COMMITTED_FIXTURES', prepared.report)
            require_quiet()
            phase = 'OWNED_ACTORS'
            actors = {role: plan.login_actor(attempt, role) for role, _ in plan.ACTOR_PLAN}
            require_quiet()

            def observe():
                return native.observe(conn, cur, attempt=attempt, verify=verify, prepared=prepared,
                                      capture_scope=capture_scope)

            phase = 'ORDINARY_REPORT'
            admin = actors['ADMIN']
            report_check = s05(attempt, owner=actors['OWNER'], admin=admin, finance=actors['KEUANGAN'], native=committed_s05[3],
                               observe=observe, require_quiet=require_quiet, retain=retain)
            phase = 'CREDIT_AND_ORDINARY_PERMISSION_WINDOW'
            window = permission_window(conn, cur, attempt=attempt, admin=admin, plan=plan, verify=verify,
                                       require_quiet=require_quiet, retain=retain)
            credit(attempt, admin=admin, source_identity=source_identity, conn=conn, cur=cur, prepared=prepared,
                   native=native, verify=verify, profile_id=profile, outside_id=outside_id, capture_scope=capture_scope,
                   permission_window=window, report=report, require_quiet=require_quiet, retain=retain,
                   during_revocation=report_check.during_revocation)
            phase = 'RESTORED_ADMIN_REPORT'
            report[plan.HTTP_CASE_IDS[-1]] = report_check.finish()
            need(tuple(report) == plan.HTTP_CASE_IDS, 'EXACT_ORDERED_AUTH_CASES_REQUIRED')
        except Exception as error:
            failure = dict(phase=phase, completed_cases=list(report), error_type=type(error).__name__)
            if re.fullmatch(r'[A-Z0-9_]+(?::[a-zA-Z0-9_]+)?', str(error)):
                failure['error_code'] = str(error)
            try:
                retain('GLOBAL_AUTH_ORDINARY_SCHEDULE_FIRST_FAILURE', failure)
            except Exception as recovery:
                raise error from recovery
            raise
        require_quiet()
        return report

    return SimpleNamespace(prepare=prepare, exercise=exercise_http)
