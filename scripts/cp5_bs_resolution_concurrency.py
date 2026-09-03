#!/usr/bin/env python3
"""Real two-connection serialization races for CP5 BS Resolution."""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import psycopg


PGURL = os.environ.get('PGURL', 'postgresql://postgres:postgres@127.0.0.1:54322/postgres')
REPORT = Path(os.environ.get('CP5_BS_RESOLUTION_RACE_REPORT', 'cp5-bs-resolution-concurrency.json'))
HOLD_SECONDS = 1.0
WAIT_FLOOR_SECONDS = 0.5

OPERATOR_APP = 'c6c00000-0000-4000-8000-000000000001'
OPERATOR_AUTH = 'c6c00000-0000-4000-8000-000000000101'
BS_CASE = 'c6c00000-0000-4000-8000-000000000201'
PO = 'c6c00000-0000-4000-8000-000000000301'
BATCH = 'c6c00000-0000-4000-8000-000000000302'
GROUP = 'c6c00000-0000-4000-8000-000000000303'
VENDOR = 'c6c00000-0000-4000-8000-000000000304'
DELIVERY = 'c6c00000-0000-4000-8000-000000000305'
DELIVERY_LINE = 'c6c00000-0000-4000-8000-000000000306'
RECEIPT = 'c6c00000-0000-4000-8000-000000000307'
RECEIPT_LINE = 'c6c00000-0000-4000-8000-000000000308'
CONTRACTOR = 'c6c00000-0000-4000-8000-000000000309'
MODEL = 'c6c00000-0000-4000-8000-000000000310'
DISPOSE_REQUEST_A = 'c6c00000-0000-4000-8000-000000000401'
DISPOSE_REQUEST_B = 'c6c00000-0000-4000-8000-000000000402'
CLAIM_REQUEST_A = 'c6c00000-0000-4000-8000-000000000403'
CLAIM_REQUEST_B = 'c6c00000-0000-4000-8000-000000000404'


def connect():
    return psycopg.connect(PGURL, autocommit=False)


def set_operator_context(cur):
    claims = json.dumps({'sub': OPERATOR_AUTH, 'role': 'authenticated'})
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
            select %s::uuid,%s::uuid,'CP5 Race Operator','PRODUKSI_QC',id,true
            from erp.app_roles where role_code='PRODUKSI_QC'
            """,
            (OPERATOR_APP, OPERATOR_AUTH),
        )
        cur.execute(
            """
            insert into erp.bs_cases(
              id,bs_number,untracked_type,legacy_reference,detected_at_stage,
              cause_source,qty_pcs,status,physical_at,notes
            ) values(
              %s::uuid,'CP5-RACE-BS','LEGACY','CP5-RACE-BOOK','UNKNOWN',
              'UNKNOWN',2,'OPEN','2026-09-03T07:00:00Z','CP5 disposition race'
            )
            """,
            (BS_CASE,),
        )
        cur.execute(
            """
            insert into erp.contractors(
              id,contractor_code,contractor_name,contractor_type,attendance_required
            ) values(%s::uuid,'CP5-RACE-M','CP5 Race Mandor','MANDOR',true)
            """,
            (CONTRACTOR,),
        )
        cur.execute(
            """
            insert into erp.product_models(id,model_code,model_name)
            values(%s::uuid,'CP5-RACE-MODEL','CP5 Race Model')
            """,
            (MODEL,),
        )
        cur.execute(
            """
            insert into erp.production_orders(
              id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at,notes
            ) values(
              %s::uuid,'CP5-RACE-PO',%s::uuid,%s::uuid,
              3,'CUTTING','CUTTING','2026-09-03T06:00:00Z','CP5 race'
            )
            """,
            (PO, MODEL, CONTRACTOR),
        )
        cur.execute(
            "insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes) "
            "values(%s::uuid,%s::uuid,'CP5-RACE-BATCH','2026-09-03T06:15:00Z','OPEN','CP5 race')",
            (BATCH, PO),
        )
        cur.execute(
            """
            insert into erp.cutting_groups(id,po_id,group_number,cut_at,status,cutting_batch_id,notes)
            values(%s::uuid,%s::uuid,'CP5-RACE-GROUP','2026-09-03T06:15:00Z','CUT',%s::uuid,'CP5 race')
            """,
            (GROUP, PO, BATCH),
        )
        cur.execute(
            "insert into erp.laundry_vendors(id,vendor_code,vendor_name,is_active,notes) "
            "values(%s::uuid,'CP5-RACE-L','CP5 Race Laundry',true,'CP5 race')",
            (VENDOR,),
        )
        cur.execute(
            """
            insert into erp.laundry_deliveries(
              id,delivery_number,po_id,vendor_id,target_dyeing_color,physical_at,status,created_by,special_instruction
            ) values(%s::uuid,'CP5-RACE-DELIVERY',%s::uuid,%s::uuid,'N/A','2026-09-03T07:30:00Z','RETURNED',%s::uuid,'CP5 race')
            """,
            (DELIVERY, PO, VENDOR, OPERATOR_APP),
        )
        cur.execute(
            """
            insert into erp.laundry_delivery_lines(id,delivery_id,cutting_group_id,qty_sent_pcs,estimated_rate_snapshot,estimated_cost_status,notes)
            values(%s::uuid,%s::uuid,%s::uuid,3,0,'FINAL','CP5 race')
            """,
            (DELIVERY_LINE, DELIVERY, GROUP),
        )
        cur.execute(
            "insert into erp.laundry_receipts(id,receipt_number,delivery_id,physical_at,status) "
            "values(%s::uuid,'CP5-RACE-RECEIPT',%s::uuid,'2026-09-03T08:30:00Z','POSTED')",
            (RECEIPT, DELIVERY),
        )
        cur.execute(
            """
            insert into erp.laundry_receipt_lines(
              id,receipt_id,delivery_line_id,qty_good_received,qty_bs_laundry,qty_stuck,qty_missing
            ) values(%s::uuid,%s::uuid,%s::uuid,0,3,0,0)
            """,
            (RECEIPT_LINE, RECEIPT, DELIVERY_LINE),
        )
        conn.commit()


def cleanup():
    request_ids = [DISPOSE_REQUEST_A, DISPOSE_REQUEST_B, CLAIM_REQUEST_A, CLAIM_REQUEST_B]
    entity_ids = [
        BS_CASE, PO, BATCH, GROUP, VENDOR, DELIVERY, DELIVERY_LINE,
        RECEIPT, RECEIPT_LINE, CONTRACTOR, MODEL,
    ]
    with connect() as conn, conn.cursor() as cur:
        cur.execute("set local lock_timeout='10s'")
        cur.execute("select set_config('erp.cp45_allow_synthetic_cleanup','on',true)")
        cur.execute("delete from erp.laundry_claims where claim_number like 'CP5-RACE-DAMAGE-%%'")
        cur.execute("delete from erp.bs_resolutions where bs_case_id=%s::uuid", (BS_CASE,))
        cur.execute("delete from erp.bs_case_components where bs_case_id=%s::uuid", (BS_CASE,))
        cur.execute("delete from erp.bs_cases where id=%s::uuid", (BS_CASE,))
        cur.execute(
            "delete from erp.idempotency_requests where client_request_id=any(%s::uuid[])",
            (request_ids,),
        )
        cur.execute("delete from erp.laundry_receipt_lines where id=%s::uuid", (RECEIPT_LINE,))
        cur.execute("delete from erp.laundry_receipts where id=%s::uuid", (RECEIPT,))
        cur.execute("delete from erp.laundry_delivery_lines where id=%s::uuid", (DELIVERY_LINE,))
        cur.execute("delete from erp.laundry_deliveries where id=%s::uuid", (DELIVERY,))
        cur.execute("delete from erp.laundry_vendors where id=%s::uuid", (VENDOR,))
        cur.execute("delete from erp.cutting_groups where id=%s::uuid", (GROUP,))
        cur.execute("delete from erp.cutting_batches where id=%s::uuid", (BATCH,))
        cur.execute("delete from erp.production_orders where id=%s::uuid", (PO,))
        cur.execute("delete from erp.contractors where id=%s::uuid", (CONTRACTOR,))
        cur.execute("delete from erp.product_models where id=%s::uuid", (MODEL,))
        cur.execute(
            "delete from erp.audit_logs where changed_by=%s::uuid or entity_id=any(%s::uuid[]) or change_reason like 'CP5 race %%'",
            (OPERATOR_APP, entity_ids),
        )
        cur.execute(
            "delete from erp.app_access_audit where actor_app_user_id=%s::uuid or entity_id=%s::uuid",
            (OPERATOR_APP, OPERATOR_APP),
        )
        cur.execute("delete from erp.app_users where id=%s::uuid", (OPERATOR_APP,))
        conn.commit()


def action(cur, action_name: str, payload: dict, request_id: str, expected_version):
    cur.execute(
        "select public.erp_save_bs_resolution_action_v1(%s,%s::jsonb,%s::uuid,%s)",
        (action_name, json.dumps(payload), request_id, expected_version),
    )
    return cur.fetchone()[0]


def disposition_holder(started: threading.Event, result: dict):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute('select id from erp.bs_cases where id=%s::uuid for update', (BS_CASE,))
            started.set()
            time.sleep(HOLD_SECONDS)
            set_operator_context(cur)
            result['response'] = action(cur, 'DISPOSE_BS', {
                'bs_case_id': BS_CASE, 'resolution_type': 'SCRAP', 'qty_pcs': 1,
                'compensation_amount': 0, 'source_laundry_claim_id': None,
                'physical_at': '2026-09-03T08:00:00Z',
                'change_reason': 'CP5 race disposition winner',
            }, DISPOSE_REQUEST_A, 1)
        conn.commit()
        result['status'] = 'PASS'
    except Exception as exc:  # pragma: no cover - emitted in proof
        conn.rollback()
        result['status'] = 'FAIL'
        result['error'] = str(exc)
        started.set()
    finally:
        conn.close()


def disposition_waiter(started: threading.Event, result: dict):
    started.wait(timeout=10)
    began = time.monotonic()
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            set_operator_context(cur)
            result['unexpected_response'] = action(cur, 'DISPOSE_BS', {
                'bs_case_id': BS_CASE, 'resolution_type': 'WRITE_OFF', 'qty_pcs': 1,
                'compensation_amount': 0, 'source_laundry_claim_id': None,
                'physical_at': '2026-09-03T08:00:01Z',
                'change_reason': 'CP5 race disposition loser',
            }, DISPOSE_REQUEST_B, 1)
        conn.commit()
        result['status'] = 'UNEXPECTED_SUCCESS'
    except Exception as exc:
        conn.rollback()
        result['error'] = str(exc)
        result['status'] = 'EXPECTED_REJECTION' if 'STALE_VERSION' in str(exc) else 'WRONG_ERROR'
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - began, 3)
        conn.close()


def run_disposition_race():
    started = threading.Event()
    winner = {}
    loser = {}
    first = threading.Thread(target=disposition_holder, args=(started, winner), daemon=True)
    second = threading.Thread(target=disposition_waiter, args=(started, loser), daemon=True)
    first.start(); second.start(); first.join(timeout=20); second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('disposition race thread timeout')
    if winner.get('status') != 'PASS' or loser.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'disposition race mismatch: winner={winner}, loser={loser}')
    if loser.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'disposition race did not observe serialization wait: {loser}')
    final = scalar(
        """
        select jsonb_build_object(
          'status',b.status,'row_version',b.row_version,
          'resolution_count',(select count(*) from erp.bs_resolutions r where r.bs_case_id=b.id),
          'resolved_qty',(select coalesce(sum(r.qty_pcs),0) from erp.bs_resolutions r where r.bs_case_id=b.id)
        ) from erp.bs_cases b where b.id=%s::uuid
        """,
        (BS_CASE,),
    )
    if final['status'] != 'PARTIAL' or final['resolution_count'] != 1 or final['resolved_qty'] != 1:
        raise RuntimeError(f'disposition race final state mismatch: {final}')
    return {'winner': winner, 'loser': loser, 'final': final}


def claim_holder(started: threading.Event, result: dict):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute('select id from erp.laundry_deliveries where id=%s::uuid for update', (DELIVERY,))
            started.set()
            time.sleep(HOLD_SECONDS)
            set_operator_context(cur)
            result['response'] = action(cur, 'SAVE_CLAIM', {
                'action': 'SAVE', 'claim_number': 'CP5-RACE-DAMAGE-A', 'vendor_id': VENDOR,
                'delivery_id': DELIVERY, 'receipt_line_id': RECEIPT_LINE,
                'qty_claimed': 2, 'claim_type': 'DAMAGE', 'compensation_amount': 0,
                'opened_at': '2026-09-03T09:00:00Z',
                'change_reason': 'CP5 race DAMAGE winner',
            }, CLAIM_REQUEST_A, None)
        conn.commit()
        result['status'] = 'PASS'
    except Exception as exc:  # pragma: no cover - emitted in proof
        conn.rollback()
        result['status'] = 'FAIL'
        result['error'] = str(exc)
        started.set()
    finally:
        conn.close()


def claim_waiter(started: threading.Event, result: dict):
    started.wait(timeout=10)
    began = time.monotonic()
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            set_operator_context(cur)
            result['unexpected_response'] = action(cur, 'SAVE_CLAIM', {
                'action': 'SAVE', 'claim_number': 'CP5-RACE-DAMAGE-B', 'vendor_id': VENDOR,
                'delivery_id': DELIVERY, 'receipt_line_id': RECEIPT_LINE,
                'qty_claimed': 2, 'claim_type': 'DAMAGE', 'compensation_amount': 0,
                'opened_at': '2026-09-03T09:00:01Z',
                'change_reason': 'CP5 race DAMAGE loser',
            }, CLAIM_REQUEST_B, None)
        conn.commit()
        result['status'] = 'UNEXPECTED_SUCCESS'
    except Exception as exc:
        conn.rollback()
        result['error'] = str(exc)
        result['status'] = (
            'EXPECTED_REJECTION'
            if 'DAMAGE claim exceeds BS quantity' in str(exc)
            else 'WRONG_ERROR'
        )
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - began, 3)
        conn.close()


def run_claim_race():
    started = threading.Event()
    winner = {}
    loser = {}
    first = threading.Thread(target=claim_holder, args=(started, winner), daemon=True)
    second = threading.Thread(target=claim_waiter, args=(started, loser), daemon=True)
    first.start(); second.start(); first.join(timeout=20); second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('DAMAGE claim race thread timeout')
    if winner.get('status') != 'PASS' or loser.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'DAMAGE claim race mismatch: winner={winner}, loser={loser}')
    if loser.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'DAMAGE claim race did not observe serialization wait: {loser}')
    final = scalar(
        """
        select jsonb_build_object(
          'claim_count',count(*),'claimed_qty',coalesce(sum(qty_claimed),0),
          'receipt_bs',(select qty_bs_laundry from erp.laundry_receipt_lines where id=%s::uuid),
          'remaining_capacity',(select qty_bs_laundry from erp.laundry_receipt_lines where id=%s::uuid)-coalesce(sum(qty_claimed),0)
        ) from erp.laundry_claims
        where receipt_line_id=%s::uuid and claim_type='DAMAGE' and status<>'REJECTED'
        """,
        (RECEIPT_LINE, RECEIPT_LINE, RECEIPT_LINE),
    )
    if final != {'claim_count': 1, 'claimed_qty': 2, 'receipt_bs': 3, 'remaining_capacity': 1}:
        raise RuntimeError(f'DAMAGE claim race final capacity mismatch: {final}')
    return {'winner': winner, 'loser': loser, 'final': final}


report = {'status': 'FAIL', 'production_go': False}
failure = None
try:
    setup()
    report['disposition_vs_disposition'] = run_disposition_race()
    report['damage_claim_vs_capacity'] = run_claim_race()
    report['assertions'] = {
        'exactly_one_disposition_winner': True,
        'stale_disposition_cannot_overwrite': True,
        'damage_claim_capacity_serialized': True,
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
          'bs_cases',(select count(*) from erp.bs_cases where id=%s::uuid),
          'bs_resolutions',(select count(*) from erp.bs_resolutions where bs_case_id=%s::uuid),
          'bs_components',(select count(*) from erp.bs_case_components where bs_case_id=%s::uuid),
          'claims',(select count(*) from erp.laundry_claims where receipt_line_id=%s::uuid or claim_number like 'CP5-RACE-DAMAGE-%%'),
          'receipts',(select count(*) from erp.laundry_receipts where id=%s::uuid),
          'receipt_lines',(select count(*) from erp.laundry_receipt_lines where id=%s::uuid),
          'deliveries',(select count(*) from erp.laundry_deliveries where id=%s::uuid),
          'delivery_lines',(select count(*) from erp.laundry_delivery_lines where id=%s::uuid),
          'vendors',(select count(*) from erp.laundry_vendors where id=%s::uuid),
          'groups',(select count(*) from erp.cutting_groups where id=%s::uuid),
          'batches',(select count(*) from erp.cutting_batches where id=%s::uuid),
          'orders',(select count(*) from erp.production_orders where id=%s::uuid),
          'contractors',(select count(*) from erp.contractors where id=%s::uuid),
          'models',(select count(*) from erp.product_models where id=%s::uuid),
          'idempotency',(select count(*) from erp.idempotency_requests where client_request_id=any(%s::uuid[])),
          'access_audit',(select count(*) from erp.app_access_audit
            where actor_app_user_id=%s::uuid or entity_id=%s::uuid),
          'audit_logs',(select count(*) from erp.audit_logs
            where changed_by=%s::uuid or entity_id=any(%s::uuid[]) or change_reason like 'CP5 race %%'),
          'execution_context',(select count(*) from erp.bs_resolution_execution_context)
        )
        """,
        (
            OPERATOR_APP, BS_CASE, BS_CASE, BS_CASE, RECEIPT_LINE,
            RECEIPT, RECEIPT_LINE, DELIVERY, DELIVERY_LINE, VENDOR, GROUP, BATCH, PO,
            CONTRACTOR, MODEL,
            [DISPOSE_REQUEST_A, DISPOSE_REQUEST_B, CLAIM_REQUEST_A, CLAIM_REQUEST_B],
            OPERATOR_APP, OPERATOR_APP, OPERATOR_APP,
            [
                BS_CASE, PO, BATCH, GROUP, VENDOR, DELIVERY, DELIVERY_LINE,
                RECEIPT, RECEIPT_LINE, CONTRACTOR, MODEL,
            ],
        ),
    )
except Exception as exc:  # pragma: no cover - emitted as proof
    failure = failure or exc
    report['status'] = 'FAIL'
    report['residue_failure'] = str(exc)
    residue = {'residue_query_failed': True}

report['residue'] = residue
if not all(value == 0 for value in residue.values()):
    report['status'] = 'FAIL'
    failure = failure or RuntimeError(f'CP5 race cleanup residue: {residue}')

REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2) + '\n')
if failure:
    raise failure
print('CP5 BS Resolution concurrency passed: two serialized races; zero synthetic residue.')
