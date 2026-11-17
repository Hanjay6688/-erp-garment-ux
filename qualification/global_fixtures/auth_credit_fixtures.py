"""Bind four committed credit fixtures to the existing owning Auth attempt."""

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json
import os
import re
from types import SimpleNamespace
from uuid import UUID


CASES = {
    'GLOBAL_AUTH_D1_FRESH_REPLAY': ('D1', '180.00'),
    'GLOBAL_AUTH_E_FRESH_REPLAY': ('E', '80.00'),
    'GLOBAL_AUTH_D1_ADMIN_PERMISSION_REVOKED': ('D1', '180.00'),
    'GLOBAL_AUTH_E_ADMIN_PERMISSION_REVOKED': ('E', '80.00'),
}
FRESH = ('GLOBAL_AUTH_D1_FRESH_REPLAY', 'GLOBAL_AUTH_E_FRESH_REPLAY')
DAY = 'SKU_CURRENT_AUTOMATIC_WIB_BUSINESS_DAY'
DB = 'cp6_rollback'
NATIVE = 'scripts/cp7_credit_correction_de/'
PINS = {
    NATIVE + 'cases.py': 'c530bb87f72ee6091e032d15efdb2b2e55cf9c9632b64c9e781665b70325bbdb',
    NATIVE + 'e_cases.py': '058a9c29b991b30ca4da6467cfeb2629179d3ce8f25b8dba09d6ea45f419e2ad',
    NATIVE + 'native_fixture.py': '4fbe56583ffc63473c12195ddaae6ff3e0cd0ad46b358bf7eef7b5175c67e829',
    'scripts/cp7_customer_credit/consumer/native_basic_cases.py': '24ba3f79cc01905d1289b0db08552ed2c0593138e3c83f4551b88a025ae6a567',
    'scripts/cp6_auditor_business_day.py': 'ec12307a50b0333abd1911f48cdd4ee24c31c432c28f2901d0df5a317d2341f8',
}
IDENTITY = """select current_database(),oid::bigint,(pg_control_system()).system_identifier::text
 from pg_database where datname=current_database()"""
PERIOD = """select closed_through,updated_at,updated_by,change_reason
 from erp.accounting_period_control where singleton_id=1"""
RESTORE_PERIOD = """update erp.accounting_period_control
 set closed_through=%s,updated_at=%s,updated_by=%s,change_reason=%s where singleton_id=1"""
EVENT = """select e.id::text,e.cohort_id::text,e.target_sale_id::text,e.event_kind,e.amount,
 e.request_id::text,e.journal_id::text,exists(select 1 from cp7_credit.consumption_events undo
 where undo.restores_event_id=e.id),to_jsonb(e)::text
 from cp7_credit.consumption_events e where e.id=%s::uuid"""
GLOBALS = 'cp7_global_nonpo_envelope'
NATIVE_OPS = {'D1': 'cp7_credit_correction_de.operations_v1',
              'E': 'cp7_credit_note_carry_de.operations_v1'}
WRITE_TRANSACTION = 'READ COMMITTED READ WRITE'
READ_TRANSACTION = 'REPEATABLE READ READ ONLY'
SNAPSHOT = f"""select jsonb_build_object(
 'scope_completions',coalesce((select jsonb_agg(to_jsonb(c) order by c.operation_id)
 from {GLOBALS}.scope_completions_v1 c),'[]'),
 'D1_operations',coalesce((select jsonb_agg(to_jsonb(d) order by d.operation_id) from {NATIVE_OPS['D1']} d),'[]'),
 'E_operations',coalesce((select jsonb_agg(to_jsonb(e) order by e.operation_id) from {NATIVE_OPS['E']} e),'[]'),
 'pending_Global_work',(select count(*) from {GLOBALS}.work_scopes_v1))::text"""


def require(condition, reason):
    if not condition:
        raise ValueError('GLOBAL_AUTH_CREDIT_' + reason)


def exact(observer, fn, roots, relative, name):
    path = Path(fn.__code__.co_filename).resolve()
    require(any(path == root / relative for root in roots), 'EXACT_SOURCE_ROOT_REQUIRED:' + name)
    observer.exact_function(fn, path, PINS[relative], name)


def bind(candidate, *, plan, exact_native_graph, accepted_roots=()):
    """Resolve frozen Native code using the admitted owning caller's source graph."""
    candidate = Path(candidate).resolve()
    require(tuple(plan.HTTP_CASE_IDS[:4]) == tuple(CASES), 'EXACT_APPROVED_CASES_REQUIRED')
    observer, runner, factories, _ = exact_native_graph
    roots = (candidate, *(Path(root).resolve() for root, _, _ in factories),
             *(Path(root).resolve() for root in accepted_roots))
    for relative, pin in PINS.items():
        require(sha256((candidate / relative).read_bytes()).hexdigest() == pin, 'CANDIDATE_PIN_CHANGED:' + relative)
    routes = {case: factory for _, factory, cases in factories for case in cases}
    d1 = routes['D_AFTER_ACTIVE_APPLY'].__globals__
    e = routes['E_SAME_UUID_AND_CHANGED_INTENT'].__globals__
    fixture, basic, day = d1['fixture'], d1['basic'], runner.business_day
    require(e['fixture'] is fixture and e['basic'] is basic and e['de'].__dict__ is d1
            and e['native'] is d1['native'] is fixture.native is basic.native,
            'ONE_EXACT_SHARED_NATIVE_GRAPH_REQUIRED')
    for fn, relative, name in (
        (routes['D_AFTER_ACTIVE_APPLY'], NATIVE + 'cases.py', 'cases'),
        (routes['E_SAME_UUID_AND_CHANGED_INTENT'], NATIVE + 'e_cases.py', 'cases'),
        (fixture.prepare, NATIVE + 'native_fixture.py', 'prepare'),
        (basic.apply, 'scripts/cp7_customer_credit/consumer/native_basic_cases.py', 'apply'),
        (d1['profile'], NATIVE + 'cases.py', 'profile'),
        (e['profile'], NATIVE + 'e_cases.py', 'profile'),
        (e['physical'], NATIVE + 'e_cases.py', 'physical'),
        (day.wib_day, 'scripts/cp6_auditor_business_day.py', 'wib_day'),
    ):
        exact(observer, fn, roots, relative, name)
    fixture_sources = fixture.inventory()
    native = fixture.native
    source = dict(status='SOURCE_BOUND', case_ids=list(CASES), pins=dict(PINS),
                  fixture_source_pins=fixture_sources['frozen_sources'], actual_SQL_executed=0,
                  actual_Auth_cases=0, runtime_admission=False)
    owned_cases = {}
    owning_session = None

    @contextmanager
    def transaction(conn, cur, attempt, verify, today, *, mode):
        plan.check_registry(attempt)
        info = conn.info
        require(attempt.phase == 'ACTIVE' and cur.connection is conn and not conn.autocommit
                and info.transaction_status.name == 'IDLE' and info.host in ('127.0.0.1', 'localhost')
                and info.port == 54322 and info.dbname == DB,
                'IDLE_SAME_OWNING_APPLICATION_REQUIRED')
        require(type(today) is date and today.isoformat() == os.environ.get(DAY), 'EXACT_PLANNED_WIB_DAY_REQUIRED')
        with conn.transaction():
            cur.execute('SET TRANSACTION ISOLATION LEVEL ' + mode)
            cur.execute("SET LOCAL TIME ZONE 'UTC'")
            # The exact Native helpers already switch to the disposable maintenance role.
            # Make that session-scoped transition local to this transaction boundary.
            native.b.api.admin(cur)
            try:
                identity = cur.execute(IDENTITY).fetchone()
                require(identity is not None and attempt.app == identity and identity[0] == DB
                        and attempt.issuer[1] != identity[1]
                        and attempt.issuer[2] == identity[2], 'EXACT_APPLICATION_AND_ISSUER_OIDS_REQUIRED')
                proof = verify(cur)
                require(type(proof) is dict and proof.get('full25_verified') is True,
                        'ADMITTED_OWNING_VERIFIER_REQUIRED')
                require(day.wib_day(cur) == today, 'OWNING_WIB_DAY_CHANGED')
                yield dict(application_oid=identity[1], cluster_system_id=identity[2])
                require(day.wib_day(cur) == today and cur.execute(IDENTITY).fetchone() == identity,
                        'OWNING_WIB_DAY_OR_APPLICATION_CHANGED')
            finally:
                # On an aborted transaction the transaction manager also rolls back SET SESSION.
                if conn.info.transaction_status.name == 'INTRANS':
                    cur.execute('RESET SESSION AUTHORIZATION')

    def apply_fact(cur, item):
        row = cur.execute(EVENT, (item.apply_event_id,)).fetchone()
        require(row is not None and row[:7] == (item.apply_event_id, item.cohort_id, item.target_sale_id,
                'APPLY', Decimal(item.amount), item.apply_request_id, item.apply_journal_id) and row[7] is False,
                'EXACT_ORIGINAL_APPLY_MUST_REMAIN_ACTIVE')
        return dict(event_raw=row[8], journal_sha256=native.journal(cur, item.apply_journal_id)['sha256'])

    def prepare(conn, cur, *, attempt, verify, today):
        """Commit independent fixtures on the admitted same application, once."""
        nonlocal owning_session
        require(owning_session is None, 'SINGLE_FIXTURE_PREPARATION_REQUIRED')
        prepared = {}
        with transaction(conn, cur, attempt, verify, today, mode=WRITE_TRANSACTION) as app:
            period = cur.execute(PERIOD + ' FOR UPDATE').fetchone()
            require(period is not None, 'EXISTING_PERIOD_SINGLETON_REQUIRED')
            for case, (operation, amount) in CASES.items():
                pair = fixture.prepare(cur, today)
                applied, _, request = basic.apply(cur, pair, amount)
                source_id = pair['source']['f']['sale']
                target_id = pair['target']['sale']
                item = SimpleNamespace(case_id=case, operation=operation, amount=amount, pair=pair,
                    source_sale_id=str(source_id), target_sale_id=str(target_id),
                    sale_id=str(source_id if operation == 'D1' else target_id),
                    return_id=str(pair['initial_result']['return_id']), cohort_id=str(pair['initial_result']['credit_id']),
                    apply_event_id=str(applied['consumption_event_id']), apply_operation_id=str(applied['operation_id']),
                    apply_journal_id=str(applied['journal_id']), apply_request_id=str(request))
                item.apply_fact = apply_fact(cur, item)
                if operation == 'E':
                    item.physical = e['physical'](cur, pair)
                    item.original_note = e['note'].unchanged_facts(cur, item.target_sale_id)
                require(cur.execute('select exists(select 1 from cp7_credit.consumer_completions_v1 '
                    'where operation_id=%s and consumption_event_id=%s and journal_id=%s)',
                    (item.apply_operation_id, item.apply_event_id, item.apply_journal_id)).fetchone() == (True,),
                    'NATIVE_APPLY_COMPLETION_REQUIRED')
                prepared[case] = item

            for field in ('return_id', 'cohort_id', 'apply_event_id', 'apply_operation_id', 'apply_journal_id'):
                require(len({getattr(item, field) for item in prepared.values()}) == 4,
                        'INDEPENDENT_FIXTURE_ID_REQUIRED:' + field)
            require(len({sale for item in prepared.values() for sale in (item.source_sale_id, item.target_sale_id)}) == 8,
                    'EIGHT_DISTINCT_FIXTURE_SALES_REQUIRED')
            # The retained fixture changes the administrative period row. Keep its setup-only
            # writes inside this transaction, then restore the original before HTTP runs.
            if cur.execute(PERIOD).fetchone() != period:
                cur.execute(RESTORE_PERIOD, period)
            require(cur.execute(PERIOD).fetchone() == period, 'PERIOD_BASELINE_RESTORE_REQUIRED')
            cur.execute('SET CONSTRAINTS ALL IMMEDIATE')
            for item in prepared.values():
                cur.execute('select cp7_credit.assert_consumer_closed_v1(%s)', (item.apply_operation_id,)).fetchone()

        # Report/identities only become visible to the dispatcher after COMMIT.
        owning_session = (conn, attempt, verify, today, app)
        owned_cases.update(prepared)
        return SimpleNamespace(cases=dict(prepared), report=dict(status='COMMITTED_FIXTURES', **app,
            period_restored_before_commit=True, business_day=today.isoformat(), cases={name: {
                key: value for key, value in vars(item).items()
                if key not in ('pair', 'apply_fact', 'physical', 'original_note')}
                for name, item in prepared.items()}))

    def owned(conn, attempt, verify):
        require(owning_session is not None and all(current is stored for current, stored in
                zip((conn, attempt, verify), owning_session[:3], strict=True)),
                'EXACT_PREPARED_OWNING_SESSION_REQUIRED')
        return owning_session[3:]

    def observe(conn, cur, *, attempt, verify, prepared, capture_scope):
        """Compare stable SQL facts across HTTP transactions on the same app."""
        today, original_app = owned(conn, attempt, verify)
        require(set(prepared.cases) == set(owned_cases)
                and all(prepared.cases[name] is item for name, item in owned_cases.items()),
                'EXACT_COMMITTED_FIXTURES_REQUIRED')
        with transaction(conn, cur, attempt, verify, today, mode=READ_TRANSACTION) as app:
            require(app == original_app, 'APPLICATION_CHANGED_AFTER_PREPARATION')
            raw_snapshot = cur.execute(SNAPSHOT).fetchone()[0]
            snapshot = json.loads(raw_snapshot)
            scope = capture_scope(cur)
            require(snapshot['pending_Global_work'] == 0 and type(scope) is dict
                    and all(name in scope for name in ('erp.app_role_permissions', 'erp.sales_headers',
                        'sequence:erp.audit_logs_id_seq', 'sequence:erp.fg_stock_book_order_seq')),
                    'QUIESCENT_RAW_TABLE_AND_SEQUENCE_STATE_REQUIRED')
            return dict(**app, scope=scope,
                fixtures={name: apply_fact(cur, item) for name, item in owned_cases.items()},
                completions=snapshot, completions_sha256=sha256(raw_snapshot.encode()).hexdigest())

    def verify_success(conn, cur, *, attempt, verify, prepared_case, response, request_id, actor_uid,
                       profile_id, outside_id):
        """Read a committed correction's native arithmetic and raw bound completion."""
        today, original_app = owned(conn, attempt, verify)
        item = prepared_case
        require(item.case_id in FRESH and owned_cases.get(item.case_id) is item,
                'EXACT_COMMITTED_FRESH_FIXTURE_REQUIRED')
        require(type(profile_id) is str and re.fullmatch(r'[a-f0-9]{64}', profile_id)
                and all(type(value) is str and str(UUID(value)) == value for value in (request_id, actor_uid, outside_id)),
                'EXACT_HTTP_ACTOR_REQUEST_AND_OUTSIDE_IDS_REQUIRED')
        operation = item.operation
        with transaction(conn, cur, attempt, verify, today, mode=READ_TRANSACTION) as app:
            require(app == original_app, 'APPLICATION_CHANGED_AFTER_PREPARATION')
            root_column = 'sale_id' if operation == 'D1' else 'source_sale_id'
            rows = cur.execute(f'''select to_jsonb(c)::text,to_jsonb(n)::text,
                c.outside_before is not distinct from c.outside_after,
                (n.operation_id,n.actor,n.request_id,n.{root_column}::text,n.payload,n.expected_version)
                    = (c.operation_id,c.actor,c.request_id,c.native_binding->>'root_sale_id',
                       c.native_binding->'payload',c.native_binding->>'expected_version')
                from {GLOBALS}.scope_completions_v1 c
                join {NATIVE_OPS[operation]} n on n.operation_id=c.operation_id
                where c.actor=%s::uuid and c.request_id=%s::uuid and c.operation=%s and c.profile_id=%s''',
                (actor_uid, request_id, operation, profile_id)).fetchall()
            require(len(rows) == 1 and rows[0][2:] == (True, True), 'ONE_EXACT_NATIVE_AND_GLOBAL_COMPLETION_REQUIRED')
            raw_global, raw_native = rows[0][:2]
            global_row, native_row = json.loads(raw_global), json.loads(raw_native)
            binding = global_row['native_binding']
            require(all(binding[field] == global_row[field] for field in ('operation_id', 'operation', 'actor', 'request_id'))
                    and binding['root_sale_id'] == item.sale_id
                    and native_row['response'] == response, 'EXACT_HTTP_NATIVE_RECEIPT_REQUIRED')
            proof, outside = global_row['proof'], global_row['outside_before']
            require(proof['same_actual_Native_owner_and_request'] is True
                    and proof['outside_full_identity_and_facts_equal'] is True
                    and proof['lock']['all_acquisition_NOWAIT'] is True and proof['lock']['profile'] == profile_id
                    and outside['classification'] == 'NEW_ACTUAL_OUTSIDE_GLOBAL_FACTS_NOT_NATIVE_SALE_SNAPSHOT'
                    and outside_id in outside['identity_domain']['conversion_ids']
                    and [fact['status'] for fact in outside['facts']['conversions'] if fact['id'] == outside_id] == ['POSTED']
                    and outside['facts']['BE_context_rows'] == []
                    and cur.execute('select status from erp.product_conversions where id=%s::uuid',
                                    (outside_id,)).fetchone() == ('POSTED',), 'EXACT_LIVE_OUTSIDE_CONVERSION_REQUIRED')
            require(apply_fact(cur, item) == item.apply_fact, 'ORIGINAL_APPLY_OR_JOURNAL_CHANGED')
            if operation == 'D1':
                require(native_row['return_id'] == item.return_id, 'EXACT_D1_ORIGINAL_RETURN_REQUIRED')
                profile = d1['profile'](cur, item.pair, '250.00', '70.00')
            else:
                require(e['physical'](cur, item.pair) == item.physical
                        and e['note'].unchanged_facts(cur, item.target_sale_id) == item.original_note,
                        'E_PHYSICAL_HPP_CASH_OR_ORIGINAL_NOTE_CHANGED')
                assignment = cur.execute('select event_id::text,historical_target_id::text,replacement_sale_id::text '
                    'from cp7_credit_note_carry_de.assignments_v1 where operation_id=%s::uuid',
                    (global_row['operation_id'],)).fetchall()
                require(assignment == [(item.apply_event_id, item.target_sale_id, response['sale_id'])],
                        'E_EXACT_SINGLE_APPLY_ASSIGNMENT_REQUIRED')
                profile = e['profile'](cur, item.pair, item.target_sale_id, response['sale_id'],
                                       '550.00', '80.00', '120.00')
            cur.execute('select cp7_credit.assert_consumer_closed_v1(%s)', (item.apply_operation_id,)).fetchone()
            return dict(**app, native_profile=profile, operation_id=global_row['operation_id'],
                exact_native_and_global_completion=True, outside_unchanged=True, original_apply_unchanged=True,
                native_completion_sha256=sha256(raw_native.encode()).hexdigest(),
                global_completion_sha256=sha256(raw_global.encode()).hexdigest())

    return SimpleNamespace(source=source, prepare=prepare, observe=observe, verify_success=verify_success)
