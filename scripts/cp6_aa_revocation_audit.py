#!/usr/bin/env python3
"""Three bounded native authorization-order cases on fresh disposable AA clones.

The blocked case uses a completed ordinary draft edit's natural receipt row
lock. No function, trigger, clock, or PostgreSQL role is modified. A separate
administrator deactivates only the synthetic application user. Synthetic JWT
claims and real authenticated sessions prove SQL behavior, not HTTP delivery.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import traceback
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_aa_invoice_partial_audit as invoice
import cp6_v2620h_maintenance_rollback_matrix as matrix


ROOT = Path('cp6-proof/independent-aa/revocation')
REPORT = ROOT / 'AA_REVOCATION_AUDIT.json'
CASES = ('ACTIVE_CONTROL', 'REVOKED_AFTER_TRANSACTION_START', 'REVOKED_WHILE_POST_WAITS')
one, base, prior = invoice.one, invoice.base, invoice.prior


def connect(label, source=False):
    target = matrix.SOURCE if source else matrix.CLONE
    params = conninfo_to_dict(target)
    expected = dict(user='postgres', password='postgres', host='127.0.0.1', port='54322',
                    dbname='postgres' if source else 'cp6_rollback')
    if params != expected:
        raise AssertionError('AA_REVOCATION_EXACT_LOOPBACK_REQUIRED')
    conn = psycopg.connect(**dict(params, user='supabase_admin'), application_name='cp6-aa-revoke-' + label)
    conn.execute("set timezone='UTC';set statement_timeout='30s';set lock_timeout='20s'")
    conn.commit()
    return conn


def operator(cur, subject):
    prior.actors.claims(cur, dict(sub=str(subject), role='authenticated'))
    prior.actors.session(cur, 'authenticated')
    row = cur.execute('select current_user,session_user,auth.uid()::text,erp.current_app_role()').fetchone()
    if row[:3] != ('authenticated', 'authenticated', str(subject)):
        raise AssertionError('AA_REVOCATION_REAL_SESSION_REQUIRED')
    return row


def setup(cur):
    if len(invoice.runtime.verified_successor(cur)) != 2:
        raise AssertionError('AA_REVOCATION_EXACT_AA_REQUIRED')
    cur.execute('grant usage on schema erp to authenticated')
    prior.actors.claims(cur, dict(sub=base.OPERATOR_AUTH, role='authenticated'))
    base.load_fixture_foundation(cur)
    app_id, subject = uuid.uuid4(), uuid.uuid4()
    cur.execute("""insert into erp.app_users select (jsonb_populate_record(null::erp.app_users,
      to_jsonb(u)||jsonb_build_object('id',%s::uuid,'auth_user_id',%s::uuid,
      'full_name','AA revocation synthetic owner','is_active',true))).*
      from erp.app_users u where id=%s""", (app_id, subject, base.OPERATOR_APP))
    if cur.rowcount != 1:
        raise AssertionError('AA_REVOCATION_ACTOR_NOT_CREATED')
    location, material = uuid.uuid4(), prior.clone_material(cur, 'revocation')
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) "
                "values(%s,%s,'AA revocation warehouse','RAW_MATERIAL_WAREHOUSE',true)",
                (location, 'AA-REV-' + location.hex[:20]))
    physical = datetime.now(prior.JAKARTA)-timedelta(days=1)
    payload = dict(purchase_number='AA-REV-PUR-' + str(uuid.uuid4()), supplier_id=prior.BASE_SUPPLIER,
                   location_id=str(location), physical_at=physical.isoformat(),
                   change_reason='AA ordinary receipt draft for authorization ordering',
                   lines=[dict(material_id=str(material), qty=10, unit_price=10,
                               price_state='ESTIMATED', price_source='MANUAL_ESTIMATE',
                               rolls=[dict(roll_number='AA-REV-ROLL-' + str(uuid.uuid4()), qty=10)])])
    draft = invoice.rpc(cur, 'erp.save_material_purchase_draft_v2', payload)
    return dict(app_id=app_id, subject=subject, material=material,
                purchase=uuid.UUID(draft['purchase_id']), version=int(draft['row_version']), payload=payload)


def deactivate(conn, actor):
    with conn.cursor() as cur:
        prior.actors.claims(cur, dict(sub=base.OPERATOR_AUTH, role='authenticated'))
        cur.execute("select set_config('app.change_reason','AA synthetic user deactivation',true)")
        cur.execute('update erp.app_users set is_active=false where id=%s and is_active', (actor,))
        if cur.rowcount != 1:
            raise AssertionError('AA_REVOCATION_DEACTIVATION_NOT_QUALIFIED')
        seen = cur.execute('select is_active,clock_timestamp() from erp.app_users where id=%s', (actor,)).fetchone()
        if seen[0] is not False:
            raise AssertionError('AA_REVOCATION_ACTIVE_STATE_PERSISTED')
    conn.commit()
    return dict(is_active=False, wall_time=seen[1], committed=True)


def posted_state(cur, fixture, request_id):
    prior.as_admin(cur)
    return one(cur, """select jsonb_build_object(
      'purchase_status',h.status,'stock',m.cached_stock_qty,
      'movements',(select count(*) from erp.material_stock_movements s where s.material_id=m.id),
      'request_rows',(select count(*) from erp.idempotency_requests
        where operation_name='post_material_purchase_v2' and client_request_id=%s),
      'completed_request_rows',(select count(*) from erp.idempotency_requests
        where operation_name='post_material_purchase_v2' and client_request_id=%s and status='COMPLETED'))
      from erp.material_purchase_headers h join erp.materials m on m.id=%s where h.id=%s""",
      (request_id, request_id, fixture['material'], fixture['purchase']))


def run_case(name, folder):
    matrix.command(['bash', 'scripts/clone-cp6-disposable-database.sh', matrix.SOURCE, matrix.MAINTENANCE,
                    matrix.CLONE, 'cp6_rollback', matrix.CONTAINER, str(folder / 'CLONE_BOUNDARY')], folder / 'clone.log')
    matrix.verify_setup_source('AA')
    with connect('setup') as conn, conn.cursor() as cur:
        fixture = setup(cur)
        conn.commit()
    subject, purchase = fixture['subject'], fixture['purchase']
    contender, holder, revoker, observer = [connect(label) for label in ('contender', 'holder', 'revoker', 'observer')]
    outcome, thread = {}, None
    request_id, expected_version = uuid.uuid4(), fixture['version']
    try:
        with contender.cursor() as cur:
            identity = operator(cur, subject)
            if identity[3] != 'OWNER':
                raise AssertionError('AA_REVOCATION_INITIAL_OWNER_NOT_QUALIFIED')
            tx_start = one(cur, 'select transaction_timestamp()')
            isolation = one(cur, "select current_setting('transaction_isolation')")
            if isolation != 'read committed':
                raise AssertionError('AA_REVOCATION_REQUIRES_READ_COMMITTED')
        blocked = None
        if name == 'REVOKED_WHILE_POST_WAITS':
            with holder.cursor() as cur:
                edit = invoice.rpc(cur, 'erp.save_material_purchase_draft_v2',
                    dict(fixture['payload'], id=str(purchase),
                         notes='AA ordinary completed draft edit holds natural row lock'),
                    expected_version=fixture['version'])
                if str(edit['purchase_id']) != str(purchase):
                    raise AssertionError('AA_REVOCATION_EDIT_DID_NOT_LOCK_SOURCE_DRAFT')
                expected_version = int(edit['row_version'])

        def invoke():
            try:
                with contender.cursor() as cur:
                    response = one(cur, 'select erp.post_material_purchase_v2(%s,%s,%s,%s)',
                                   (purchase, request_id, expected_version, 'AA authorization-order posting'))
                contender.commit()
                outcome.update(status='COMMITTED', response=response)
            except psycopg.Error as exc:
                contender.rollback()
                outcome.update(status='REJECTED', sqlstate=exc.sqlstate, message=exc.diag.message_primary)
            except Exception as exc:
                contender.rollback()
                outcome.update(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc())

        revocation = None
        if name == 'REVOKED_WHILE_POST_WAITS':
            thread = threading.Thread(target=invoke, daemon=True)
            thread.start()
            def observation():
                row = observer.execute("""select pid,state,wait_event_type,wait_event,pg_blocking_pids(pid),query
                  from pg_stat_activity where pid=%s""", (contender.info.backend_pid,)).fetchone()
                observer.commit()
                if row and row[1] == 'active' and row[2] == 'Lock' and holder.info.backend_pid in row[4]:
                    return dict(pid=row[0], state=row[1], wait_event_type=row[2], wait_event=row[3],
                                blocking_pids=row[4], ordinary_post_query='erp.post_material_purchase_v2' in row[5])
                return None
            blocked = matrix.wait_for(observation, 10)
            if outcome or not blocked['ordinary_post_query']:
                raise AssertionError('AA_REVOCATION_NATURAL_POST_WAIT_NOT_QUALIFIED')
            revocation = deactivate(revoker, fixture['app_id'])
            if outcome:
                raise AssertionError('AA_REVOCATION_POST_ENDED_BEFORE_RELEASE')
            with holder.cursor() as cur:
                prior.as_admin(cur)
                expected_boundary = prior.stable_boundary(cur)
            holder.commit()
            thread.join(25)
            if thread.is_alive():
                raise AssertionError('AA_REVOCATION_CONTENDER_DID_NOT_FINISH')
        else:
            if name == 'REVOKED_AFTER_TRANSACTION_START':
                revocation = deactivate(revoker, fixture['app_id'])
            with observer.cursor() as cur:
                expected_boundary = prior.stable_boundary(cur)
            observer.commit()
            invoke()
        with observer.cursor() as cur:
            actual = posted_state(cur, fixture, request_id)
            boundary_exact = prior.stable_boundary(cur) == expected_boundary
            active = one(cur, 'select is_active from erp.app_users where id=%s', (fixture['app_id'],))
        observer.rollback()
        control = name == 'ACTIVE_CONTROL'
        expected = (dict(purchase_status='POSTED', stock=10, movements=1, request_rows=1, completed_request_rows=1)
                    if control else dict(purchase_status='DRAFT', stock=0, movements=0, request_rows=0, completed_request_rows=0))
        auth_denial = outcome['status'] == 'REJECTED' and outcome.get('sqlstate') in ('42501', 'P0001') and any(
            token in outcome.get('message', '') for token in ('Internal ERP access required', 'OWNER or ADMIN access required', 'PERMISSION_DENIED'))
        if outcome['status'] == 'INCOMPLETE' or (not control and outcome['status'] == 'REJECTED' and not auth_denial):
            status = 'INCOMPLETE'
        elif actual == expected and active is control and ((control and outcome['status'] == 'COMMITTED') or (auth_denial and boundary_exact)):
            status = 'CONTROL_PASS'
        else:
            status = 'COUNTEREXAMPLE'
        return dict(case=name, status=status, severity='P1' if status == 'COUNTEREXAMPLE' else None,
                    transaction_start=tx_start, isolation=isolation, initial_identity=identity,
                    actor_app_id=fixture['app_id'], revocation=revocation, blocking=blocked,
                    contender_pid=contender.info.backend_pid, holder_pid=holder.info.backend_pid,
                    revoker_pid=revoker.info.backend_pid, manual_prelocks=0, outcome=outcome,
                    expected=expected, actual=actual, denial_full_boundary_exact=boundary_exact if not control else None,
                    http_ui_reachability_proven=False)
    finally:
        holder.rollback()
        if thread is not None and thread.is_alive():
            contender.cancel()
            thread.join(5)
        for conn in (contender, holder, revoker, observer):
            conn.rollback()
            conn.close()


def main():
    expected = (matrix.SOURCE, matrix.MAINTENANCE, matrix.CLONE, matrix.CONTAINER, 'cp6_rollback')
    if tuple(os.environ.get(k) for k in ('PGURL', 'CP6_MAINTENANCE_PGURL', 'CP6_ROLLBACK_RACE_PGURL',
                                        'CP6_DATABASE_CONTAINER', 'CP6_MAINTENANCE_CONFIRM_DATABASE')) != expected:
        raise AssertionError('AA_REVOCATION_DISPOSABLE_CONFIRM_REQUIRED')
    if os.environ.get('CP6_AA_REVOCATION_AUDIT_CONFIRM') != 'postgres':
        raise AssertionError('AA_REVOCATION_EXPLICIT_NATIVE_TARGET_REQUIRED')
    head = prior.git('rev-parse', 'HEAD')
    if os.environ.get('GITHUB_SHA') != head or prior.git('rev-parse', invoice.HEAD_AA + '^{tree}') != invoice.TREE_AA:
        raise AssertionError('AA_REVOCATION_EXACT_SOURCE_PIN')
    if prior.git('diff', '--name-only', invoice.HEAD_AA, 'HEAD', '--', 'supabase/migrations', 'supabase/rollbacks'):
        raise AssertionError('AA_REVOCATION_REQUIRES_FROZEN_AA_SQL')
    ROOT.mkdir(parents=True, exist_ok=True)
    result = dict(format='CP6_AA_REVOCATION_AUDIT_V1', status='INCOMPLETE', head=head,
                  tree=prior.git('rev-parse', 'HEAD^{tree}'), run_id=os.environ.get('GITHUB_RUN_ID'),
                  audited_business_head=invoice.HEAD_AA, audited_business_tree=invoice.TREE_AA, expected_cases=3, cases={},
                  production_go=False, independent_acceptance_complete=False, synthetic_fixture_only=True, hosted_database_used=False,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with connect('source-before', source=True) as conn, conn.cursor() as cur:
        source_before = prior.stable_boundary(cur)
    for name in CASES:
        folder = ROOT / name
        folder.mkdir(parents=True, exist_ok=True)
        try:
            row = run_case(name, folder)
        except Exception as exc:
            row = dict(case=name, status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc())
        finally:
            matrix.legacy.drop_clone()
        with psycopg.connect(matrix.MAINTENANCE) as conn:
            remaining = conn.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        row['remaining_clone_databases'] = remaining
        if remaining != 0:
            row['status'] = 'INCOMPLETE'
        result['cases'][name] = row
        REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
        print(json.dumps(dict(case=name, status=row['status'], remaining_clone_databases=remaining)), flush=True)
    with connect('source-after', source=True) as conn, conn.cursor() as cur:
        result['source_boundary_unchanged'] = prior.stable_boundary(cur) == source_before
    result['controls'] = sum(x['status'] == 'CONTROL_PASS' for x in result['cases'].values())
    result['counterexamples'] = sum(x['status'] == 'COUNTEREXAMPLE' for x in result['cases'].values())
    result['incomplete'] = sum(x['status'] == 'INCOMPLETE' for x in result['cases'].values())
    if result['source_boundary_unchanged'] and len(result['cases']) == 3:
        result['status'] = ('FAIL_NEW_COUNTEREXAMPLE' if result['counterexamples'] else
                            'PASS_BOUNDED_AUDIT' if result['controls'] == 3 else 'INCOMPLETE')
    REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, default=str))
    return result


if __name__ == '__main__':
    try:
        result = main()
    except Exception as exc:
        result = json.loads(REPORT.read_text()) if REPORT.exists() else {}
        result.update(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc(), production_go=False)
        ROOT.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
        print(json.dumps(dict(status='INCOMPLETE', error=str(exc), production_go=False)), flush=True)
    raise SystemExit(0 if result['status'] == 'PASS_BOUNDED_AUDIT' else
                     1 if result['status'] == 'FAIL_NEW_COUNTEREXAMPLE' else 2)
