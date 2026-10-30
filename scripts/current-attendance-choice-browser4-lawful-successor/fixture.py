"""Real Native setup/readback on the one committed browser copy; never posted-row seeds.

Every operation is closed before ERP/client import unless actual backend14 and
all five package/full-restore originals are admitted. Setup is not screen proof.
"""
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
import gzip
import importlib.util
import json
import os
import re
import sys
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OPERATIONS = ('admit', 'prepare', 'observe', 'assert_command', 'approve_pending', 'close_source', 'open_source', 'access_snapshot', 'assert_access_transition', 'protected_owner_refusal', 'assert_valuation', 'assert_cancelled', 'assert_ordinary_cancelled')
SCENARIOS = ('DESKTOP', 'MOBILE390', 'STALE', 'ACCESS')
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


@contextmanager
def runtime():
    proof = load('s03_browser4_fixture_source_gate', HERE / 'source_guard.py').admitted()
    loader = load('s03_browser4_fixture_actual_backend', HERE / 'backend_runtime.py')
    with loader.actual_backend(proof) as product:
        import psycopg
        from psycopg import sql
        import cp6_bd_probe as truth
        core = load('s03_browser4_retained_native_oracles', ROOT / 'scripts/current-attendance-period-choice-qualification/cases.py')
        if product.sources() != proof['current_installation']:
            raise ValueError('S03_BROWSER4_WHOLE_ACTUAL_INSTALLATION_SOURCE_CHANGED')
        declaration = json.loads((HERE / 'HELPER_SOURCE.json').read_bytes())
        helper_path = HERE / declaration['retained']
        raw = helper_path.read_bytes()
        if len(raw) != declaration['bytes'] or sha256(raw).hexdigest() != declaration['sha256']:
            raise ValueError('S03_BROWSER4_EXPLICIT_LAWFUL_HELPER_SOURCE_CHANGED')
        lawful = load('s03_browser4_explicit_lawful_fixture', helper_path)
        if lawful.API != declaration['API']:
            raise ValueError('S03_BROWSER4_EXPLICIT_LAWFUL_HELPER_API_REQUIRED')
        yield dict(proof=proof, psycopg=psycopg, sql=sql, product=product, core=core, f=core.f, truth=truth, lawful=lawful)


@contextmanager
def native_setup(cur, r):
    """Accepted Source6 fixture-only overlay, removed before commit or any browser call.

    Exact raw schema ACL plus complete all22 equality are mandatory; no normalizer
    or owner/catalog rewrite rescues a different default/null/empty ACL.
    """
    r['f'].admin(cur)
    catalog = r['product'].runtime()[4]
    before = catalog._catalog_rows(cur)
    raw_acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
    grant = not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
    if grant:
        cur.execute('grant usage on schema erp to authenticated')
    try:
        yield
    finally:
        if cur.connection.info.transaction_status.name != 'INERROR':
            r['f'].admin(cur)
            if grant:
                cur.execute('revoke usage on schema erp from authenticated')
            if cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] != raw_acl:
                raise ValueError('S03_BROWSER4_FIXTURE_RAW_SCHEMA_ACL_CHANGED')
            if catalog._catalog_rows(cur) != before:
                raise ValueError('S03_BROWSER4_FIXTURE_ALL22_CHANGED')


def cents(value):
    number = Decimal(str(value)) * 100
    if number != number.to_integral_value():
        raise ValueError('S03_BROWSER4_ORACLE_FRACTIONAL_CENT')
    return int(number)


@contextmanager
def snapshot_utc(cur, f):
    """Serialize whole raw rows in UTC; restore the caller even on query failure.

    The nested transaction rolls a failed read back to its savepoint before the
    finally restores TimeZone. No business timestamp or financial date changes.
    """
    before = f.one(cur, "select current_setting('TimeZone')")
    try:
        with cur.connection.transaction():
            cur.execute("select set_config('TimeZone','UTC',true)")
            yield
    finally:
        cur.execute("select set_config('TimeZone',%s,true)", (before,))


def source_rows(cur, payroll, f):
    f.admin(cur)
    with snapshot_utc(cur, f):
        header = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(j)order by j.id),'[]'::jsonb)from erp.journal_entries j where source_type='PAYROLL_ATTENDANCE_ACCRUAL'and source_id=%s", (payroll,))
        lines = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(l)order by l.id),'[]'::jsonb)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_type='PAYROLL_ATTENDANCE_ACCRUAL'and j.source_id=%s", (payroll,))
        audit = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]'::jsonb)from erp.audit_logs a where entity_type='payroll_settlements'and entity_id=%s and action='POST'and new_data->>'lifecycle_action'='APPROVE'", (payroll,))
        return dict(headers=header, lines=lines, approval_audit=audit)


def access_snapshot(cur, r, payload):
    f = r['f']; f.admin(cur)
    owner, controller = payload['owner'], payload['backup_owner']
    if not UUID.fullmatch(owner) or not UUID.fullmatch(controller) or owner == controller:
        raise ValueError('S03_BROWSER4_DISTINCT_REAL_AUTH_ACTORS_REQUIRED')
    policy = load('s03_current_rights_exact_actual_policy', HERE / 'rights_delta.py').policy()
    for signature, definition in policy.items():
        if f.one(cur, 'select pg_get_functiondef(%s::regprocedure)', (signature,)) != definition:
            raise ValueError('S03_BROWSER4_ACTUAL_ACCESS_POLICY_CHANGED:' + signature)
    with snapshot_utc(cur, f):
        subject = f.one(cur, 'select to_jsonb(u)from erp.app_users u where auth_user_id=%s and is_active', (owner,))
        backup = f.one(cur, "select to_jsonb(u)from erp.app_users u join erp.app_roles r on r.id=u.role_id where u.auth_user_id=%s and u.is_active and r.is_active and r.is_protected and r.role_code='OWNER'", (controller,))
        if not subject or not backup:
            raise ValueError('S03_BROWSER4_ACTIVE_SUBJECT_AND_PROTECTED_BACKUP_OWNER_REQUIRED')
        roles = f.one(cur, "select jsonb_agg(to_jsonb(r)order by r.id)from erp.app_roles r")
        permissions = f.one(cur, "select jsonb_agg(to_jsonb(p)order by p.permission_key)from erp.app_permissions p")
        assignments = f.one(cur, "select jsonb_agg(to_jsonb(p)order by p.role_id,p.permission_key)from erp.app_role_permissions p")
        request = payload.get('request')
        audit = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]'::jsonb)from erp.app_access_audit a where client_request_id=%s", (request,))
        idempotency = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(i)order by i.actor_key),'[]'::jsonb)from erp.idempotency_requests i where operation_name='save_app_user_v2'and client_request_id=%s", (request,))
        return dict(subject=subject, backup_owner=backup, roles=roles, permissions=permissions,
            assignments=assignments, audit=audit, idempotency=idempotency,
            policy_signatures=sorted(policy), classification='ACTUAL_RAW_CURRENT_ACCESS_ROWS')


def assert_access_transition(before, after, payload):
    """Check the normal public writer's exact role/version/audit/idempotency effects."""
    for key in ('backup_owner', 'roles', 'permissions', 'assignments', 'policy_signatures'):
        if before[key] != after[key]:
            raise ValueError('S03_BROWSER4_ACCESS_PROTECTED_AUTHORITY_CHANGED:' + key)
    old, new = before['subject'], after['subject']
    role = next((row for row in before['roles'] if row['role_code'] == payload['role'] and row['is_active']), None)
    if {old['role'], payload['role']} != {'ADMIN', 'OWNER'} or not role:
        raise ValueError('S03_BROWSER4_EXACT_OWNER_ADMIN_TRANSITION_REQUIRED')
    expected = dict(old, role=payload['role'], role_id=role['id'], row_version=old['row_version'] + 1,
        updated_at=new['updated_at'])
    if new != expected or new['updated_at'] == old['updated_at']:
        raise ValueError('S03_BROWSER4_EXACT_USER_VERSION_TRANSITION_REQUIRED')
    result = payload['result']
    if result != dict(app_user_id=new['id'], role_id=role['id'], role=payload['role'], is_active=True,
            mapped=True, row_version=new['row_version']):
        raise ValueError('S03_BROWSER4_EXACT_NATIVE_ACCESS_RESPONSE_REQUIRED')
    audit, request = after['audit'], after['idempotency']
    if (len(audit) != 1 or audit[0]['entity_type'] != 'USER_ACCESS' or audit[0]['entity_id'] != new['id']
            or audit[0]['action'] != 'UPDATE' or audit[0]['old_data'] != old or audit[0]['new_data'] != new
            or audit[0]['client_request_id'] != payload['request'] or audit[0]['change_reason'] != payload['reason']
            or audit[0]['actor_app_user_id'] != before['backup_owner']['id']):
        raise ValueError('S03_BROWSER4_EXACT_NATIVE_ACCESS_AUDIT_REQUIRED')
    if (len(request) != 1 or request[0]['actor_key'] != before['backup_owner']['id']
            or request[0]['client_request_id'] != payload['request'] or request[0]['status'] != 'COMPLETED'
            or request[0]['response_payload'] != result):
        raise ValueError('S03_BROWSER4_EXACT_NATIVE_ACCESS_IDEMPOTENCY_REQUIRED')
    return dict(status='ACTUAL_PUBLIC_ROLE_TRANSITION_VERIFIED', role=payload['role'],
        expected_version=old['row_version'], response=result, audit=audit, idempotency=request,
        all_roles_permissions_and_backup_owner_unchanged=True, policy_signatures=after['policy_signatures'])


def protected_owner_refusal(cur, r, payload):
    before = access_snapshot(cur, r, payload)
    if before['subject']['role'] != 'OWNER':
        raise ValueError('S03_BROWSER4_PROTECTED_OWNER_SUBJECT_REQUIRED')
    refusal = None
    cur.execute('savepoint s03_protected_owner_permission')
    try:
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.manage'", (before['subject']['role_id'],))
    except r['psycopg'].Error as error:
        refusal = dict(sqlstate=error.sqlstate, message=error.diag.message_primary)
    finally:
        cur.execute('rollback to savepoint s03_protected_owner_permission')
        cur.execute('release savepoint s03_protected_owner_permission')
    if refusal != dict(sqlstate='42501', message='PROTECTED_OWNER_ROLE_CANNOT_BE_CHANGED'):
        raise ValueError('S03_BROWSER4_ACTUAL_PROTECTED_OWNER_REFUSAL_REQUIRED')
    if before != access_snapshot(cur, r, payload):
        raise ValueError('S03_BROWSER4_PROTECTED_OWNER_REFUSAL_CHANGED_ACCESS_ROWS')
    return dict(status='ACTUAL_PROTECTED_OWNER_DELETE_REFUSED', refusal=refusal,
        raw_access_rows_unchanged=True, view_only_Owner_representable=False, actual_view_only_Owner_credit=0)


def prepare(cur, r, payload):
    f, core = r['f'], r['core']
    today = date.fromisoformat(payload['today'])
    scenario = payload['scenario']
    if scenario not in SCENARIOS or not UUID.fullmatch(payload['owner']):
        raise ValueError('S03_BROWSER4_DECLARED_FIXTURE_REQUIRED')
    f.admin(cur)
    if f.one(cur, "select(statement_timestamp()at time zone'Asia/Jakarta')::date") != today:
        raise ValueError('S03_BROWSER4_ACTUAL_WIB_DAY_CHANGED')
    if f.one(cur, "select count(*)from erp.app_users u join erp.app_roles a on a.id=u.role_id where u.auth_user_id=%s and u.is_active and a.is_active and a.role_code='OWNER'", (payload['owner'],)) != 1:
        raise ValueError('S03_BROWSER4_EXISTING_REAL_AUTH_OWNER_REQUIRED')
    truth_before = r['truth'].all_truth(cur)
    extra = {}
    with native_setup(cur, r):
        if scenario == 'MOBILE390':
            # Select a vacant cohort before any posted fixture exists. Desktop
            # payroll/choice history remains present and must never enter P2.
            expected_output = f.quiet_days(cur, today, 1)[0]
            f.hp.set_closed(cur, expected_output - timedelta(days=1))
            m = f.hp.contractor(cur, 'S03-B4-FIN-' + uuid.uuid4().hex[:10])
            prod = core.f.hp.cp17().bd.chain.production
            previous = prod.CONTRACTOR
            try:
                prod.CONTRACTOR = m
                g = f.hp.cp17().finish_fixture(cur, expected_output + timedelta(days=5), label='S03-BROWSER4-FINISHED')
            finally:
                prod.CONTRACTOR = previous
            f.admin(cur)
            days = cur.execute("select distinct erp._cp3_business_date(physical_at)from erp.sewing_terminal_events where po_id=%s and event_kind='SELESAI_DIJAHIT'order by 1", (g['po'],)).fetchall()
            if days != [(expected_output,)]:
                raise ValueError('S03_BROWSER4_EXACT_OUTPUT_PERIOD_REQUIRED')
            output = days[0][0]
            source_day = f.quiet_days(cur, today, 1, before=output)[0]
            s = f.source(cur, today, day=source_day, contractor=m)
            c = f.hp.cp17()
            c.bd.sell(cur, g, g['product'], 4, 16)
            c.finish_command(cur, c.finish_workspace(cur, g['po']), reason=f.REASON)
            f.admin(cur)
            if c.po_state(cur, g['po'])['status'] != 'FINISHED' or c.po_wip_balance(cur, g['po']) != 0:
                raise ValueError('S03_BROWSER4_REAL_FINISHED_PO_REQUIRED')
            p2 = r['lawful'].earned(cur, s, output, Decimal('20.02'), core=core, evidence=extra)
            normal = f.native(cur, 'select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s)',
                (json.dumps(dict(period_start=str(output), period_end=str(output), reason=f.REASON)), uuid.uuid4()))
            with snapshot_utc(cur, f):
                ordinary_before_native = r['lawful'].finished_facts(cur, g, core=core)
            f.native(cur, 'select erp.activate_attendance_hpp_pool_v1(%s,%s,%s,%s)',
                (normal['pool_id'], f.REASON, uuid.uuid4(), normal['row_version']))
            f.admin(cur)
            with snapshot_utc(cur, f):
                ordinary_journal = f.one(cur, 'select to_jsonb(j)from erp.journal_entries j join erp.attendance_hpp_pools p on p.post_journal_entry_id=j.id where p.id=%s', (normal['pool_id'],))
            extra.update(output=str(output), ordinary_pool=str(normal['pool_id']), ordinary_payroll=p2,
                ordinary_before_native=ordinary_before_native, ordinary_pool_journal=ordinary_journal,
                pos=[g['po']], lots=[g['lot']], sold_qty=4, produced_qty=10,
                expected_own_FG_delta_cents=60002, expected_own_COGS_delta_cents=40001)
        elif scenario == 'STALE':
            day, alternate, alternate_output = f.quiet_days(cur, today, 3)
            s = f.source(cur, today, day=day)
            other_source = f.source(cur, today, day=alternate)
            other_source['owner'] = payload['owner']
            f.hp.sewn(cur, other_source['contractor'], 'S03-B4-ALTERNATE-P2', alternate_output)
            core.choose(cur, other_source)
            other_allocation = core.allocate(cur, other_source, alternate_output)
            f.assert_pool(cur, other_source, other_allocation, alternate_output)
            f.admin(cur)
            number = f.one(cur, 'select pool_number from erp.attendance_hpp_pools where id=%s', (other_allocation['pool_id'],))
            extra.update(alternate_source_day=str(alternate), alternate_output_day=str(alternate_output),
                alternate_pool_id=other_allocation['pool_id'], alternate_pool_number=number,
                alternate_fixture_classification='ACTUAL_NATIVE_CARRY_AND_ALLOCATION_FOR_OWNER_ROUTE_NOT_SCREEN_CREATION')
        else:
            s = f.source(cur, today)
        if scenario == 'STALE':
            other = f.hp.contractor(cur, 'S03-B4-PENDING-' + uuid.uuid4().hex[:10])
            f.hp.policy(cur, other, s['day'] - timedelta(days=1))
            pending = f.earned(cur, other, s['day'], Decimal('11.01'), approve=False)
            doc = f.hp.cp17().s.doc(cur, pending)
            if doc['status'] != 'CALCULATED':
                raise ValueError('S03_BROWSER4_LAWFUL_CALCULATED_PENDING_REQUIRED')
            extra.update(pending_payroll=pending, pending_contractor=other)
        # Later-period setup may set the accepted period-control fixture to P2.
        # Reopen P1 explicitly before the UI journey; never shift a posted date.
        f.hp.set_closed(cur, s['day'] - timedelta(days=1))
    f.admin(cur)
    s['owner'] = payload['owner']  # Existing real Auth identity for independent audit expectations only.
    original_oracle = core.original_accrual(cur, s)
    if extra.get('ordinary_payroll'):
        extra['ordinary_original_accrual'] = source_rows(cur, extra['ordinary_payroll'], f)
    result = dict(s, **extra, scenario=scenario, today=str(today), run=uuid.uuid4().hex,
        fixture_source='NATIVE_ATTENDANCE_APPROVE_AND_PRODUCTION_NOT_SCREEN_CREATION',
        expected_source_cents=100003, after_pending_approval_cents=101104 if scenario == 'STALE' else None,
        original_accrual=source_rows(cur, s['payroll'], f), independent_original_accrual_oracle=original_oracle, truth_before=truth_before)
    if r['truth'].truth_quiet(truth_before, r['truth'].all_truth(cur)) is not True:
        raise ValueError('S03_BROWSER4_FIXTURE_INTRODUCED_FINANCIAL_FINDING')
    return result


def census(cur, r, label):
    if not re.fullmatch(r'S03_B4_[A-Z0-9_]{1,140}', label):
        raise ValueError('S03_BROWSER4_PRIVATE_UNIQUE_EVIDENCE_LABEL_REQUIRED')
    f, sql = r['f'], r['sql']
    f.admin(cur)
    catalog = r['product'].runtime()[4]
    before_tz = f.one(cur, "select current_setting('TimeZone')")
    cur.execute("set local timezone='UTC'")
    try:
        rows, data = catalog._catalog_rows(cur), catalog._data(cur)
        if len(rows) != 22 or catalog.digest(rows) != os.environ['S03_BROWSER_EXPECTED_CATALOG_SHA256']:
            raise ValueError('S03_BROWSER4_COMPLETE_ACTUAL22_CATALOG_REQUIRED')
        all_rows = {}
        with catalog._catalog(cur):
            tables = cur.execute("select n.nspname,c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind in('r','p','m')and " + catalog.NAMESPACE + ' order by 1,2').fetchall()
            for table in tables:
                all_rows['.'.join(table)] = cur.execute(sql.SQL("select coalesce(jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text),'[]'::jsonb)from {} t").format(sql.Identifier(*table))).fetchone()[0]
        raw = (json.dumps(dict(all22=rows, all_rows=all_rows, data_and_all_sequences=data), sort_keys=True, default=str) + '\n').encode()
        output = ROOT / 'cp6-proof/t3' / (label + '_FULL_STATE.json.gz')
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise ValueError('S03_BROWSER4_FIRST_EVIDENCE_MUST_NOT_BE_OVERWRITTEN')
        packed = gzip.compress(raw, mtime=0)
        output.write_bytes(packed)
        return dict(catalog_groups=22, catalog_sha256=catalog.digest(rows), data_and_sequences=data,
            raw_all_rows_and_sequences_sha256=digest(dict(all_rows=all_rows, data_and_sequences=data)),
            raw_evidence=dict(path=str(output.relative_to(ROOT)), raw_bytes=len(raw), raw_sha256=sha256(raw).hexdigest(), gzip_sha256=sha256(packed).hexdigest()),
            dropped_catalog_fields=[], dropped_row_columns=[], dropped_data_or_sequence_keys=[])
    finally:
        cur.execute("select set_config('TimeZone',%s,true)", (before_tz,))


def dated_wip(cur, fixture, f):
    """Independent source-line event reconstruction, no call to owning wip_check_v1."""
    payrolls = [fixture['payroll']] + [fixture[prefix + '_payroll'] for prefix in ('ordinary', 'pending')
        if fixture.get(prefix + '_original_accrual')]
    sources = cur.execute("select l.id::text,l.debit,j.economic_date,j.transaction_date from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_type='PAYROLL_ATTENDANCE_ACCRUAL'and j.source_id=any(%s::uuid[])and l.debit>0 and l.account_id=erp.account_id('WIP')", (payrolls,)).fetchall()
    result = []
    for line, amount, econ, book in sources:
        events = [(cents(amount), econ, book)]
        events += cur.execute("select -s.amount_cents,j.economic_date,j.transaction_date from cp7_attendance_choice.sources_v1 s join cp7_attendance_choice.decisions_v1 d on d.id=s.decision_id and d.choice='EXPENSE'join erp.journal_entries j on j.id=d.journal_id where s.original_debit_journal_line_id=%s", (line,)).fetchall()
        events += cur.execute("select s.amount_cents,j.economic_date,j.transaction_date from cp7_attendance_choice.sources_v1 s join cp7_attendance_choice.reversals_v1 r on r.decision_id=s.decision_id join erp.journal_entries j on j.id=r.journal_id where s.original_debit_journal_line_id=%s", (line,)).fetchall()
        events += cur.execute("select -round(s.attendance_amount*100)::bigint,j.economic_date,j.transaction_date from erp.attendance_hpp_pool_sources s join erp.attendance_hpp_pools p on p.id=s.pool_id and p.status in('ACTIVE','CANCELLED')join erp.journal_entries j on j.id=p.post_journal_entry_id where s.original_debit_journal_line_id=%s", (line,)).fetchall()
        events += cur.execute("select round(s.attendance_amount*100)::bigint,j.economic_date,j.transaction_date from erp.attendance_hpp_pool_sources s join erp.attendance_hpp_pools p on p.id=s.pool_id and p.status='CANCELLED'join erp.journal_entries j on j.id=p.cancellation_journal_entry_id where s.original_debit_journal_line_id=%s", (line,)).fetchall()
        for axis, index in (('ECONOMIC', 1), ('BOOK', 2)):
            running = 0
            for day in sorted({event[index] for event in events}):
                running += sum(int(event[0]) for event in events if event[index] == day)
                if running < 0:
                    raise ValueError('S03_BROWSER4_INDEPENDENT_NEGATIVE_DATED_SOURCE_WIP')
                result.append(dict(line_id=line, axis=axis, date=str(day), available_cents=str(running)))
    if not result:
        raise ValueError('S03_BROWSER4_NO_ORIGINAL_DEBIT_WITNESSED')
    return result


def observe(cur, r, fixture, label, pool_history=None):
    f, core = r['f'], r['core']
    pool_history = {} if pool_history is None else pool_history
    history_oracle = load('s03_browser4_cancelled_pool_history', HERE / 'pool_history.py')
    history_proofs = []
    f.admin(cur)
    if source_rows(cur, fixture['payroll'], f) != fixture['original_accrual']:
        raise ValueError('S03_BROWSER4_ORIGINAL_ACCRUAL_OR_APPROVAL_AUDIT_CHANGED')
    for prefix in ('ordinary', 'pending'):
        if fixture.get(prefix + '_original_accrual') and source_rows(cur, fixture[prefix + '_payroll'], f) != fixture[prefix + '_original_accrual']:
            raise ValueError('S03_BROWSER4_' + prefix.upper() + '_ORIGINAL_ACCRUAL_CHANGED')
    decisions = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(d)order by d.recorded_at,d.id),'[]'::jsonb)from cp7_attendance_choice.decisions_v1 d where d.period_start=%s and d.period_end=%s", (fixture['day'], fixture['day']))
    requests = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(q)order by q.recorded_at,q.request_id),'[]'::jsonb)from cp7_attendance_choice.requests_v1 q where q.payload->>'period_start'=%s and q.payload->>'period_end'=%s", (str(fixture['day']), str(fixture['day'])))
    audit_proofs = []
    actor = f.one(cur, 'select id::text from erp.app_users where auth_user_id=%s and is_active', (fixture['owner'],))
    for request in requests:
        posts = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]'::jsonb)from erp.audit_logs a where entity_type='cp7_attendance_choice'and entity_id=%s and action='POST'and new_data->>'request_id'=%s", (request['response']['decision_id'], request['request_id']))
        if (len(posts) != 1 or request['actor'] != fixture['owner'] or request['app_user'] != actor
                or posts[0]['changed_by'] != actor or posts[0]['change_reason'] != request['payload']['reason']):
            raise ValueError('S03_BROWSER4_ACTUAL_REQUEST_AUDIT_LINEAGE_CHANGED')
        audit_proofs.append(dict(request=request['request_id'], event=request['response']['event_id'], audit=posts[0]))
    f.admin(cur)
    current = f.one(cur, 'select cp7_attendance_choice.current_v1(%s,%s)::text', (fixture['day'], fixture['day']))
    reversals = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(r)order by r.id),'[]'::jsonb)from cp7_attendance_choice.reversals_v1 r where r.decision_id=any(%s::uuid[])", ([d['id'] for d in decisions],))
    pools = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(p)order by p.id),'[]'::jsonb)from erp.attendance_hpp_pools p where p.period_start=%s and p.period_end=%s", (fixture['day'], fixture['day']))
    for pool in pools:
        if pool['status'] in ('ACTIVE', 'CANCELLED') or pool['id'] in pool_history:
            history_proofs.append(history_oracle.observe(cur, f, pool, pool_history))
    ordinary = None
    if fixture.get('ordinary_pool'):
        f.admin(cur)
        ordinary = f.one(cur, 'select to_jsonb(p)from erp.attendance_hpp_pools p where id=%s', (fixture['ordinary_pool'],))
        if f.native(cur, "select erp.validate_attendance_hpp_pool_v1(%s)->>'validation'", (fixture['ordinary_pool'],)) != 'PASS':
            raise ValueError('S03_BROWSER4_ORDINARY_P2_NATIVE_POOL_VALIDATOR_REQUIRED')
        history_proofs.append(history_oracle.observe(cur, f, ordinary, pool_history))
    history_oracle.require_observed(pool_history, pools + ([ordinary] if ordinary else []))
    f.admin(cur)
    accounts = dict(cur.execute("select k,round(coalesce(sum(l.debit-l.credit),0)*100)::bigint::text from unnest(array['WIP','OTHER_EXPENSE','CONTRACTOR_PAYABLE'])k left join erp.journal_lines l on l.account_id=erp.account_id(k)and l.contractor_id=%s and l.po_id is null group by k", (fixture['contractor'],)).fetchall())
    pos = {}
    for po in fixture.get('pos', []):
        target = f.one(cur, 'select to_jsonb(t)from erp.compute_po_hpp_gl_targets_v2620d(%s)t', (po,))
        book = f.one(cur, 'select to_jsonb(t)from erp.compute_po_hpp_gl_book_v2620e(%s)t', (po,))
        if set(book) != {'fg_value', 'cogs_value', 'other_out_value'} or any(cents(book[key]) != cents(Decimal(str(target[key])).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)) for key in book):
            raise ValueError('S03_BROWSER4_ACTUAL_NATIVE_HPP_TARGETS_NOT_BOOKS')
        pos[po] = dict(target=target, book=book, wip=str(core.f.hp.cp17().po_wip_balance(cur, po)), hpp=str(core.f.hp.cp17().po_hpp(cur, po)[0]))
    physical = f.one(cur, "select coalesce(jsonb_agg(to_jsonb(m)order by m.id),'[]'::jsonb)from erp.fg_stock_movements m where m.lot_id=any(%s::uuid[])", (fixture.get('lots', []),))
    if len(fixture.get('pos', [])) != len(fixture.get('lots', [])):
        raise ValueError('S03_BROWSER4_EXPLICIT_PO_LOT_FIXTURE_REQUIRED')
    finished_native = {po:r['lawful'].finished_facts(cur, dict(po=po, lot=lot), core=core)
        for po, lot in zip(fixture.get('pos', []), fixture.get('lots', []))}
    journals = f.one(cur, "select coalesce(jsonb_agg(jsonb_build_object('header',to_jsonb(j),'lines',(select jsonb_agg(to_jsonb(l)order by l.id)from erp.journal_lines l where l.journal_entry_id=j.id))order by j.id),'[]'::jsonb)from erp.journal_entries j where j.id in(select journal_id from cp7_attendance_choice.decisions_v1 where id=any(%s::uuid[])union select journal_id from cp7_attendance_choice.reversals_v1 where decision_id=any(%s::uuid[]))", ([d['id'] for d in decisions], [d['id'] for d in decisions]))
    truth = r['truth'].all_truth(cur)
    if not r['truth'].truth_quiet(fixture['truth_before'], truth):
        raise ValueError('S03_BROWSER4_NEW_NATIVE_FINANCIAL_TRUTH_FINDING')
    f.admin(cur)
    return dict(census=census(cur, r, label), original_accrual=source_rows(cur, fixture['payroll'], f),
        decisions=decisions, reversals=reversals, requests=requests, audit_proofs=audit_proofs, current_decision=current, pools=pools,
        account_cents=accounts, po_finance=pos, physical_rows=physical, journals=journals, finished_native=finished_native,
        ordinary_pool=ordinary, dated_WIP=dated_wip(cur, fixture, f), Native_financial_truth=truth,
        pool_history=pool_history, pool_history_proofs=history_proofs)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in OPERATIONS:
        raise ValueError('S03_BROWSER4_DECLARED_FIXTURE_OPERATION_REQUIRED')
    operation = sys.argv[1]
    if operation == 'admit':
        proof = load('s03_browser4_fixture_admission_first', HERE / 'source_guard.py').admitted()
        return dict(status=proof['status'], fresh_Native_Auth_HTTP_races=0, production_go=False)
    payload = json.load(sys.stdin)
    address = urlparse(os.environ['AUDITOR_BROWSER_DB_URL'])
    if address.hostname not in ('127.0.0.1', 'localhost') or address.port != 54322 or address.path != '/cp6_auditor_browser':
        raise ValueError('S03_BROWSER4_LOCAL_COMMITTED_BROWSER_COPY_ONLY')
    # runtime() performs the complete fresh admission before any ERP import or
    # database connection. Do not perform that same full admission twice.
    with runtime() as r:
        return operation_on_copy(r, operation, payload)


def operation_on_copy(r, operation, payload):
    with r['psycopg'].connect(os.environ['AUDITOR_BROWSER_DB_URL'], connect_timeout=10) as connection, connection.cursor() as cur:
        if cur.execute('select current_database()').fetchone() != ('cp6_auditor_browser',):
            raise ValueError('S03_BROWSER4_WRONG_DATABASE')
        cur.execute("set local statement_timeout='120s';set local lock_timeout='8s'")
        r['f'].admin(cur)
        if operation == 'prepare':
            result = prepare(cur, r, payload)
        elif operation == 'observe':
            result = observe(cur, r, payload['fixture'], payload['label'], payload.get('pool_history'));connection.rollback();return result
        elif operation == 'assert_command':
            result = r['core'].choice_audit(cur, payload['fixture'], payload['result']);connection.rollback();return result
        elif operation in ('assert_valuation', 'assert_cancelled', 'assert_ordinary_cancelled'):
            fixture = payload['fixture'];g = dict(po=fixture['pos'][0], lot=fixture['lots'][0]);evidence = {}
            source = fixture['ordinary_before_native'] if operation == 'assert_ordinary_cancelled' else payload['before']
            before = dict(source, GL={key:Decimal(str(value)) for key,value in source['GL'].items()})
            if operation == 'assert_valuation':
                oracle = r['f'].assert_pool(cur, fixture, payload['made'], date.fromisoformat(fixture['output']))
                expected = dict(before['GL']);expected['FG_INVENTORY'] += Decimal('600.02');expected['COGS'] += Decimal('400.01')
                after = r['lawful'].observe_valuation(cur, g, before, Decimal('1000.03'), core=r['core'],
                    baseline_cost=r['lawful'].hpp_money(before)[0], before_gl=before['GL'], after_gl=expected, evidence=evidence)
                result = dict(evidence=evidence, owning_pool_oracle=oracle, after=after)
            else:
                ordinary = operation == 'assert_ordinary_cancelled'
                made = dict(pool_id=fixture['ordinary_pool']) if ordinary else payload['made']
                cancelled = dict(native_result=payload['cancelled']) if ordinary else payload['cancelled']
                oracle = dict(journal=fixture['ordinary_pool_journal']) if ordinary else payload['oracle']
                posted = payload['after_allocation']
                posted = dict(posted, GL={key:Decimal(str(value)) for key,value in posted['GL'].items()})
                after = r['lawful'].assert_cancelled(cur, g, before, core=r['core'], evidence=evidence,
                    made=made, cancelled=cancelled, oracle=oracle, after_allocation=posted)
                result = dict(evidence=evidence, after=after, full_FG_rows_exact=True,
                    actual_native_result_wrapper_only=ordinary, append_only_history_retained=True)
            connection.rollback();return result
        elif operation == 'approve_pending':
            with native_setup(cur, r):
                settlement = r['f'].hp.cp17().s
                document = settlement.doc(cur, payload['fixture']['pending_payroll'])
                if document['status'] != 'CALCULATED':
                    raise ValueError('S03_BROWSER4_PENDING_ALREADY_APPROVED')
                settlement.act(cur, 'APPROVE', document)
            original = source_rows(cur, payload['fixture']['pending_payroll'], r['f'])
            if len(original['headers']) != 1 or len(original['approval_audit']) != 1 or sum(cents(line['debit']) for line in original['lines']) != 1101:
                raise ValueError('S03_BROWSER4_ACTUAL_SECOND_ACCRUAL_1101_REQUIRED')
            result = dict(status='APPROVED_NATIVE_FIXTURE_NOT_SCREEN_CREATION', amount_cents='1101', pending_original_accrual=original)
        elif operation in ('close_source', 'open_source'):
            day = date.fromisoformat(payload['fixture']['day'])
            if operation == 'open_source':
                evidence = {};source = dict(payload['fixture'], day=day)
                receipt = r['lawful'].reopen_source(cur, source, core=r['core'], evidence=evidence)
                result = dict(status='REAL_OWNER_PERIOD_REOPEN_AFTER_CLOSED_REFUSAL', receipt=receipt, evidence=evidence)
            else:
                r['f'].hp.set_closed(cur, day)
                result = dict(status='EXPLICIT_PERIOD_CONTROL_FIXTURE', through=str(day))
        elif operation in ('access_snapshot', 'assert_access_transition', 'protected_owner_refusal'):
            if operation == 'protected_owner_refusal':
                result = protected_owner_refusal(cur, r, payload)
            else:
                result = access_snapshot(cur, r, payload)
                if operation == 'assert_access_transition':
                    result = assert_access_transition(payload['before'], result, payload)
            connection.rollback();return result
        else:
            raise ValueError('S03_BROWSER4_UNIMPLEMENTED_OPERATION')
        r['f'].admin(cur)
        connection.commit()
        return result


if __name__ == '__main__':
    print(json.dumps(main(), default=str))
