#!/usr/bin/env python3
"""Real two-connection races for CP4.5 v2.6.17a pattern binding."""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import psycopg


PGURL = os.environ.get('PGURL', 'postgresql://postgres:postgres@127.0.0.1:54322/postgres')
REPORT = Path(os.environ.get('CP45_PATTERN_ASSIGNMENT_RACE_REPORT', 'cp45-pattern-assignment-concurrency.json'))
HOLD_SECONDS = 1.0
WAIT_FLOOR_SECONDS = 0.5

OWNER_APP = 'c4580000-0000-4000-8000-000000000001'
OWNER_AUTH = 'c4580000-0000-4000-8000-000000000101'
MODEL = 'c4580000-0000-4000-8000-000000000201'
PO = 'c4580000-0000-4000-8000-000000000202'
BATCH = 'c4580000-0000-4000-8000-000000000203'
GROUP_ASSIGN = 'c4580000-0000-4000-8000-000000000301'
GROUP_DOWNSTREAM = 'c4580000-0000-4000-8000-000000000302'
PATTERN_A = 'c4580000-0000-4000-8000-000000000401'
PATTERN_B = 'c4580000-0000-4000-8000-000000000402'
VENDOR = 'c4580000-0000-4000-8000-000000000501'
DELIVERY = 'c4580000-0000-4000-8000-000000000502'
DELIVERY_LINE = 'c4580000-0000-4000-8000-000000000503'
REQUEST_A = 'c4580000-0000-4000-8000-000000000601'
REQUEST_B = 'c4580000-0000-4000-8000-000000000602'
REQUEST_DOWNSTREAM = 'c4580000-0000-4000-8000-000000000603'


def connect():
    return psycopg.connect(PGURL, autocommit=False)


def set_owner_context(cur):
    claims = json.dumps({'sub': OWNER_AUTH, 'role': 'authenticated'})
    cur.execute("select set_config('request.jwt.claims',%s,true)", (claims,))
    cur.execute('set local role authenticated')


def scalar(query: str, params=()):
    with connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None


def setup():
    with connect() as conn, conn.cursor() as cur:
        cur.execute("set local lock_timeout='10s'")
        cur.execute(
            """
            insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
            select %s::uuid,%s::uuid,'CP45A Race Owner','OWNER',id,true
            from erp.app_roles where role_code='OWNER'
            """,
            (OWNER_APP, OWNER_AUTH),
        )
        cur.execute(
            "insert into erp.product_models(id,model_code,model_name) "
            "values(%s::uuid,'CP45A-RACE-MODEL','CP45A Race Model')",
            (MODEL,),
        )
        cur.execute(
            """
            insert into erp.production_orders(
              id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at
            ) values(%s::uuid,'CP45A-RACE-PO',%s::uuid,2,'DRAFT','CUTTING',clock_timestamp())
            """,
            (PO, MODEL),
        )
        cur.execute(
            """
            insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes)
            values(%s::uuid,%s::uuid,'CP45A-RACE-BATCH',clock_timestamp(),'OPEN','CP45A race')
            """,
            (BATCH, PO),
        )
        cur.execute(
            """
            insert into erp.cutting_groups(
              id,po_id,group_number,cut_at,status,cutting_batch_id,notes
            ) values
              (%s::uuid,%s::uuid,'CP45A-RACE-ASSIGN',clock_timestamp(),'CUT',%s::uuid,'assignment race'),
              (%s::uuid,%s::uuid,'CP45A-RACE-DOWNSTREAM',clock_timestamp(),'CUT',%s::uuid,'downstream race')
            """,
            (GROUP_ASSIGN, PO, BATCH, GROUP_DOWNSTREAM, PO, BATCH),
        )
        cur.execute(
            """
            insert into erp.production_patterns(
              id,pattern_code,revision,pattern_name,sort_order,is_active,created_by,updated_by
            ) values
              (%s::uuid,'CP45A-RACE-A','R1','CP45A Race Pattern A',10,true,%s::uuid,%s::uuid),
              (%s::uuid,'CP45A-RACE-B','R1','CP45A Race Pattern B',20,true,%s::uuid,%s::uuid)
            """,
            (PATTERN_A, OWNER_APP, OWNER_APP, PATTERN_B, OWNER_APP, OWNER_APP),
        )
        cur.execute(
            "insert into erp.laundry_vendors(id,vendor_code,vendor_name) "
            "values(%s::uuid,'CP45A-RACE-L','CP45A Race Laundry')",
            (VENDOR,),
        )
        cur.execute(
            """
            insert into erp.laundry_deliveries(
              id,delivery_number,po_id,vendor_id,target_dyeing_color,physical_at,status
            ) values(%s::uuid,'CP45A-RACE-DELIVERY',%s::uuid,%s::uuid,'N/A',clock_timestamp(),'DRAFT')
            """,
            (DELIVERY, PO, VENDOR),
        )
        conn.commit()


def cleanup():
    all_ids = [
        OWNER_APP, MODEL, PO, BATCH, GROUP_ASSIGN, GROUP_DOWNSTREAM,
        PATTERN_A, PATTERN_B, VENDOR, DELIVERY, DELIVERY_LINE,
    ]
    request_ids = [REQUEST_A, REQUEST_B, REQUEST_DOWNSTREAM]
    with connect() as conn, conn.cursor() as cur:
        cur.execute("set local lock_timeout='10s'")
        cur.execute("select set_config('erp.cp45_allow_synthetic_cleanup','on',true)")
        cur.execute(
            "delete from erp.idempotency_requests where client_request_id=any(%s::uuid[])",
            (request_ids,),
        )
        cur.execute(
            "delete from erp.production_pattern_audit where entity_id=any(%s::uuid[]) or pattern_id=any(%s::uuid[])",
            (all_ids, [PATTERN_A, PATTERN_B]),
        )
        cur.execute("delete from erp.laundry_delivery_lines where id=%s::uuid", (DELIVERY_LINE,))
        cur.execute("delete from erp.laundry_deliveries where id=%s::uuid", (DELIVERY,))
        cur.execute("delete from erp.laundry_vendors where id=%s::uuid", (VENDOR,))
        cur.execute("delete from erp.cutting_groups where id=any(%s::uuid[])", ([GROUP_ASSIGN, GROUP_DOWNSTREAM],))
        cur.execute("delete from erp.cutting_batches where id=%s::uuid", (BATCH,))
        cur.execute("delete from erp.production_orders where id=%s::uuid", (PO,))
        cur.execute("delete from erp.product_models where id=%s::uuid", (MODEL,))
        cur.execute("delete from erp.production_patterns where id=any(%s::uuid[])", ([PATTERN_A, PATTERN_B],))
        cur.execute(
            "delete from erp.app_access_audit where actor_app_user_id=%s::uuid or entity_id=any(%s::uuid[])",
            (OWNER_APP, all_ids),
        )
        cur.execute(
            "delete from erp.audit_logs where changed_by=%s::uuid or entity_id=any(%s::uuid[])",
            (OWNER_APP, all_ids),
        )
        cur.execute("delete from erp.app_users where id=%s::uuid", (OWNER_APP,))
        conn.commit()


def assignment_holder(started: threading.Event, result: dict):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute('select id from erp.cutting_groups where id=%s::uuid for update', (GROUP_ASSIGN,))
            started.set()
            time.sleep(HOLD_SECONDS)
            set_owner_context(cur)
            cur.execute(
                'select public.erp_assign_pattern_v1(%s::uuid,%s::uuid,%s,%s::uuid,%s)',
                (GROUP_ASSIGN, PATTERN_A, 'CP45A assignment race winner', REQUEST_A, 1),
            )
            result['response'] = cur.fetchone()[0]
        conn.commit()
        result['status'] = 'PASS'
    except Exception as exc:  # pragma: no cover - reported to CI artifact
        conn.rollback()
        result['status'] = 'FAIL'
        result['error'] = str(exc)
        started.set()
    finally:
        conn.close()


def assignment_waiter(started: threading.Event, result: dict):
    started.wait(timeout=10)
    began = time.monotonic()
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            set_owner_context(cur)
            cur.execute(
                'select public.erp_assign_pattern_v1(%s::uuid,%s::uuid,%s,%s::uuid,%s)',
                (GROUP_ASSIGN, PATTERN_B, 'CP45A assignment race loser', REQUEST_B, 1),
            )
            result['unexpected_response'] = cur.fetchone()[0]
        conn.commit()
        result['status'] = 'UNEXPECTED_SUCCESS'
    except Exception as exc:
        conn.rollback()
        result['error'] = str(exc)
        result['status'] = 'EXPECTED_REJECTION' if 'STALE_VERSION' in str(exc) else 'WRONG_ERROR'
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - began, 3)
        conn.close()


def run_assignment_race():
    started = threading.Event()
    winner = {}
    loser = {}
    first = threading.Thread(target=assignment_holder, args=(started, winner), daemon=True)
    second = threading.Thread(target=assignment_waiter, args=(started, loser), daemon=True)
    first.start(); second.start(); first.join(timeout=20); second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('assignment race thread timeout')
    if winner.get('status') != 'PASS' or loser.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'assignment race mismatch: winner={winner}, loser={loser}')
    if loser.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'assignment race did not observe serialization wait: {loser}')
    evidence = scalar(
        """
        select jsonb_build_object(
          'pattern_id',pattern_id,
          'code_snapshot',pattern_code_snapshot,
          'revision_snapshot',pattern_revision_snapshot,
          'name_snapshot',pattern_name_snapshot,
          'row_version',row_version,
          'assignment_audit_rows',(select count(*) from erp.production_pattern_audit
            where entity_type='ASSIGNMENT' and entity_id=erp.cutting_groups.id and action='ASSIGN')
        ) from erp.cutting_groups where id=%s::uuid
        """,
        (GROUP_ASSIGN,),
    )
    if evidence != {
        'pattern_id': PATTERN_A,
        'code_snapshot': 'CP45A-RACE-A',
        'revision_snapshot': 'R1',
        'name_snapshot': 'CP45A Race Pattern A',
        'row_version': 2,
        'assignment_audit_rows': 1,
    }:
        raise RuntimeError(f'assignment race final identity mismatch: {evidence}')
    return {'winner': winner, 'loser': loser, 'final': evidence}


def downstream_holder(started: threading.Event, result: dict):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute(
                """
                insert into erp.laundry_delivery_lines(id,delivery_id,cutting_group_id,qty_sent_pcs)
                values(%s::uuid,%s::uuid,%s::uuid,1)
                """,
                (DELIVERY_LINE, DELIVERY, GROUP_DOWNSTREAM),
            )
            started.set()
            time.sleep(HOLD_SECONDS)
        conn.commit()
        result['status'] = 'PASS'
    except Exception as exc:  # pragma: no cover - reported to CI artifact
        conn.rollback()
        result['status'] = 'FAIL'
        result['error'] = str(exc)
        started.set()
    finally:
        conn.close()


def downstream_assignment_waiter(started: threading.Event, result: dict):
    started.wait(timeout=10)
    began = time.monotonic()
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            set_owner_context(cur)
            cur.execute(
                'select public.erp_assign_pattern_v1(%s::uuid,%s::uuid,%s,%s::uuid,%s)',
                (GROUP_DOWNSTREAM, PATTERN_A, 'CP45A downstream race', REQUEST_DOWNSTREAM, 1),
            )
            result['unexpected_response'] = cur.fetchone()[0]
        conn.commit()
        result['status'] = 'UNEXPECTED_SUCCESS'
    except Exception as exc:
        conn.rollback()
        result['error'] = str(exc)
        result['status'] = (
            'EXPECTED_REJECTION'
            if 'PATTERN_INITIAL_ASSIGNMENT_REQUIRES_PRISTINE_CUTTING' in str(exc)
            else 'WRONG_ERROR'
        )
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - began, 3)
        conn.close()


def run_downstream_race():
    started = threading.Event()
    child = {}
    assignment = {}
    first = threading.Thread(target=downstream_holder, args=(started, child), daemon=True)
    second = threading.Thread(target=downstream_assignment_waiter, args=(started, assignment), daemon=True)
    first.start(); second.start(); first.join(timeout=20); second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('downstream race thread timeout')
    if child.get('status') != 'PASS' or assignment.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'downstream race mismatch: child={child}, assignment={assignment}')
    if assignment.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'downstream race did not observe FK/parent serialization wait: {assignment}')
    evidence = scalar(
        """
        select jsonb_build_object(
          'pattern_id',g.pattern_id,
          'code_snapshot',g.pattern_code_snapshot,
          'row_version',g.row_version,
          'laundry_lines',(select count(*) from erp.laundry_delivery_lines l where l.cutting_group_id=g.id),
          'assignment_audit_rows',(select count(*) from erp.production_pattern_audit a
            where a.entity_type='ASSIGNMENT' and a.entity_id=g.id and a.action='ASSIGN')
        ) from erp.cutting_groups g where g.id=%s::uuid
        """,
        (GROUP_DOWNSTREAM,),
    )
    if evidence != {
        'pattern_id': None,
        'code_snapshot': None,
        'row_version': 1,
        'laundry_lines': 1,
        'assignment_audit_rows': 0,
    }:
        raise RuntimeError(f'downstream race final identity mismatch: {evidence}')
    return {'child': child, 'assignment': assignment, 'final': evidence}


report = {'status': 'FAIL', 'production_go': False}
failure = None
try:
    setup()
    report['assignment_vs_assignment'] = run_assignment_race()
    report['downstream_vs_assignment'] = run_downstream_race()
    report['assertions'] = {
        'exactly_one_assignment_winner': True,
        'loser_cannot_overwrite_snapshot': True,
        'downstream_fk_first_blocks_assignment': True,
        'real_two_connection_wait_observed': True,
    }
    report['status'] = 'PASS'
except Exception as exc:  # pragma: no cover - emitted as proof
    failure = exc
    report['failure'] = str(exc)
finally:
    try:
        cleanup()
    except Exception as exc:  # pragma: no cover - emitted as proof
        failure = failure or exc
        report['status'] = 'FAIL'
        report['cleanup_failure'] = str(exc)

try:
    residue = scalar(
        """
        select jsonb_build_object(
          'app_users',(select count(*) from erp.app_users where id=%s::uuid),
          'models',(select count(*) from erp.product_models where id=%s::uuid),
          'production_orders',(select count(*) from erp.production_orders where id=%s::uuid),
          'cutting_batches',(select count(*) from erp.cutting_batches where id=%s::uuid),
          'cutting_groups',(select count(*) from erp.cutting_groups where id=any(%s::uuid[])),
          'patterns',(select count(*) from erp.production_patterns where id=any(%s::uuid[])),
          'pattern_audit',(select count(*) from erp.production_pattern_audit
            where entity_id=any(%s::uuid[]) or pattern_id=any(%s::uuid[])),
          'idempotency',(select count(*) from erp.idempotency_requests where client_request_id=any(%s::uuid[])),
          'laundry_vendors',(select count(*) from erp.laundry_vendors where id=%s::uuid),
          'laundry_deliveries',(select count(*) from erp.laundry_deliveries where id=%s::uuid),
          'laundry_lines',(select count(*) from erp.laundry_delivery_lines where id=%s::uuid)
        )
        """,
        (
            OWNER_APP, MODEL, PO, BATCH,
            [GROUP_ASSIGN, GROUP_DOWNSTREAM], [PATTERN_A, PATTERN_B],
            [GROUP_ASSIGN, GROUP_DOWNSTREAM, PATTERN_A, PATTERN_B], [PATTERN_A, PATTERN_B],
            [REQUEST_A, REQUEST_B, REQUEST_DOWNSTREAM],
            VENDOR, DELIVERY, DELIVERY_LINE,
        ),
    )
except Exception as exc:  # pragma: no cover - emitted as proof
    residue = {'query_failed': str(exc)}
    failure = failure or exc
    report['status'] = 'FAIL'

report['residue'] = residue
if any(value != 0 for value in residue.values()):
    report['status'] = 'FAIL'
    failure = failure or RuntimeError(f'CP45A concurrency residue: {residue}')

REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf8')
if report['status'] != 'PASS':
    raise failure or RuntimeError(f'CP45A concurrency failed: {report}')

print('CP4.5 v2.6.17a pattern assignment concurrency passed: two races, zero residue.')
