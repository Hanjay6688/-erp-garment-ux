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
RETURN_RECEIPT = 'c6c00000-0000-4000-8000-000000000311'
RETURN_RECEIPT_LINE = 'c6c00000-0000-4000-8000-000000000312'
CLAIM_WINS_RECEIPT = 'c6c00000-0000-4000-8000-000000000313'
CLAIM_WINS_RECEIPT_LINE = 'c6c00000-0000-4000-8000-000000000314'
REVERSAL_WINS_RECEIPT = 'c6c00000-0000-4000-8000-000000000315'
REVERSAL_WINS_RECEIPT_LINE = 'c6c00000-0000-4000-8000-000000000316'
CASH_WINS_BS_CASE = 'c6c00000-0000-4000-8000-000000000317'
CASH_WINS_CLAIM = 'c6c00000-0000-4000-8000-000000000318'
REVERSAL_WINS_BS_CASE = 'c6c00000-0000-4000-8000-000000000319'
REVERSAL_WINS_CLAIM = 'c6c00000-0000-4000-8000-000000000320'
DISPOSE_REQUEST_A = 'c6c00000-0000-4000-8000-000000000401'
DISPOSE_REQUEST_B = 'c6c00000-0000-4000-8000-000000000402'
CLAIM_REQUEST_A = 'c6c00000-0000-4000-8000-000000000403'
CLAIM_REQUEST_B = 'c6c00000-0000-4000-8000-000000000404'
CLAIM_REQUEST_C = 'c6c00000-0000-4000-8000-000000000405'
CLAIM_REQUEST_D = 'c6c00000-0000-4000-8000-000000000406'
CLAIM_REQUEST_E = 'c6c00000-0000-4000-8000-000000000407'
CASH_REQUEST_A = 'c6c00000-0000-4000-8000-000000000408'
CASH_REQUEST_B = 'c6c00000-0000-4000-8000-000000000409'


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
              10,'CUTTING','CUTTING','2026-09-03T06:00:00Z','CP5 race'
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
            ) values(%s::uuid,'CP5-RACE-DELIVERY',%s::uuid,%s::uuid,'N/A','2026-09-03T07:30:00Z','PARTIAL_RETURN',%s::uuid,'CP5 race')
            """,
            (DELIVERY, PO, VENDOR, OPERATOR_APP),
        )
        cur.execute(
            """
            insert into erp.laundry_delivery_lines(id,delivery_id,cutting_group_id,qty_sent_pcs,estimated_rate_snapshot,estimated_cost_status,notes)
            values(%s::uuid,%s::uuid,%s::uuid,10,0,'FINAL','CP5 race')
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
        cur.execute(
            "insert into erp.laundry_receipts(id,receipt_number,delivery_id,physical_at,status) "
            "values(%s::uuid,'CP5-RACE-LATE-RECEIPT',%s::uuid,'2026-09-03T09:00:00Z','DRAFT')",
            (RETURN_RECEIPT, DELIVERY),
        )
        cur.execute(
            """
            insert into erp.laundry_receipt_lines(
              id,receipt_id,delivery_line_id,qty_good_received,qty_bs_laundry,qty_stuck,qty_missing
            ) values(%s::uuid,%s::uuid,%s::uuid,5,0,0,0)
            """,
            (RETURN_RECEIPT_LINE, RETURN_RECEIPT, DELIVERY_LINE),
        )
        cur.execute(
            """
            insert into erp.laundry_receipts(id,receipt_number,delivery_id,physical_at,status)
            values
              (%s::uuid,'CP5-RACE-CLAIM-WINS',%s::uuid,'2026-09-03T08:40:00Z','POSTED'),
              (%s::uuid,'CP5-RACE-REVERSAL-WINS',%s::uuid,'2026-09-03T08:50:00Z','POSTED')
            """,
            (CLAIM_WINS_RECEIPT, DELIVERY, REVERSAL_WINS_RECEIPT, DELIVERY),
        )
        cur.execute(
            """
            insert into erp.laundry_receipt_lines(
              id,receipt_id,delivery_line_id,qty_good_received,qty_bs_laundry,qty_stuck,qty_missing
            ) values
              (%s::uuid,%s::uuid,%s::uuid,0,1,0,0),
              (%s::uuid,%s::uuid,%s::uuid,0,1,0,0)
            """,
            (
                CLAIM_WINS_RECEIPT_LINE, CLAIM_WINS_RECEIPT, DELIVERY_LINE,
                REVERSAL_WINS_RECEIPT_LINE, REVERSAL_WINS_RECEIPT, DELIVERY_LINE,
            ),
        )
        cur.execute(
            """
            insert into erp.bs_cases(
              id,bs_number,untracked_type,legacy_reference,detected_at_stage,
              cause_source,responsible_vendor_id,qty_pcs,status,physical_at,notes
            ) values
              (%s::uuid,'CP5-RACE-CASH-WINS-BS','LEGACY','CP5-RACE-CASH-WINS',
               'UNKNOWN','UNKNOWN',%s::uuid,1,'OPEN','2026-09-03T07:10:00Z','CP5 claim dependency race'),
              (%s::uuid,'CP5-RACE-REVERSAL-WINS-BS','LEGACY','CP5-RACE-REVERSAL-WINS',
               'UNKNOWN','UNKNOWN',%s::uuid,1,'OPEN','2026-09-03T07:11:00Z','CP5 claim dependency race')
            """,
            (CASH_WINS_BS_CASE, VENDOR, REVERSAL_WINS_BS_CASE, VENDOR),
        )
        cur.execute(
            """
            insert into erp.laundry_claims(
              id,claim_number,vendor_id,delivery_id,qty_claimed,claim_type,
              compensation_amount,status,opened_at,resolved_at,resolution_date,notes
            ) values
              (%s::uuid,'CP5-RACE-CASH-WINS-CLAIM',%s::uuid,%s::uuid,1,'STUCK',
               25,'SETTLED','2026-09-03T08:00:00Z','2026-09-03T08:10:00Z','2026-09-03','CP5 claim dependency race'),
              (%s::uuid,'CP5-RACE-REVERSAL-WINS-CLAIM',%s::uuid,%s::uuid,1,'STUCK',
               25,'SETTLED','2026-09-03T08:01:00Z','2026-09-03T08:11:00Z','2026-09-03','CP5 claim dependency race')
            """,
            (CASH_WINS_CLAIM, VENDOR, DELIVERY, REVERSAL_WINS_CLAIM, VENDOR, DELIVERY),
        )
        conn.commit()


def cleanup():
    request_ids = [
        DISPOSE_REQUEST_A, DISPOSE_REQUEST_B, CLAIM_REQUEST_A, CLAIM_REQUEST_B,
        CLAIM_REQUEST_C, CLAIM_REQUEST_D, CLAIM_REQUEST_E, CASH_REQUEST_A, CASH_REQUEST_B,
    ]
    entity_ids = [
        BS_CASE, PO, BATCH, GROUP, VENDOR, DELIVERY, DELIVERY_LINE,
        RECEIPT, RECEIPT_LINE, RETURN_RECEIPT, RETURN_RECEIPT_LINE,
        CLAIM_WINS_RECEIPT, CLAIM_WINS_RECEIPT_LINE,
        REVERSAL_WINS_RECEIPT, REVERSAL_WINS_RECEIPT_LINE, CONTRACTOR, MODEL,
        CASH_WINS_BS_CASE, CASH_WINS_CLAIM, REVERSAL_WINS_BS_CASE, REVERSAL_WINS_CLAIM,
    ]
    with connect() as conn, conn.cursor() as cur:
        cur.execute("set local lock_timeout='10s'")
        cur.execute("select set_config('erp.cp45_allow_synthetic_cleanup','on',true)")
        cur.execute(
            "delete from erp.bs_resolutions where bs_case_id=any(%s::uuid[]) returning id",
            ([BS_CASE, CASH_WINS_BS_CASE, REVERSAL_WINS_BS_CASE],),
        )
        entity_ids.extend(str(row[0]) for row in cur.fetchall())
        cur.execute("delete from erp.laundry_claims where claim_number like 'CP5-RACE-%%'")
        cur.execute("delete from erp.bs_case_components where bs_case_id=%s::uuid", (BS_CASE,))
        cur.execute(
            "delete from erp.bs_cases where id=any(%s::uuid[])",
            ([BS_CASE, CASH_WINS_BS_CASE, REVERSAL_WINS_BS_CASE],),
        )
        cur.execute(
            "delete from erp.idempotency_requests where client_request_id=any(%s::uuid[])",
            (request_ids,),
        )
        cur.execute(
            "delete from erp.laundry_receipt_lines where id=any(%s::uuid[])",
            ([RECEIPT_LINE, RETURN_RECEIPT_LINE, CLAIM_WINS_RECEIPT_LINE, REVERSAL_WINS_RECEIPT_LINE],),
        )
        cur.execute(
            "delete from erp.laundry_receipts where id=any(%s::uuid[])",
            ([RECEIPT, RETURN_RECEIPT, CLAIM_WINS_RECEIPT, REVERSAL_WINS_RECEIPT],),
        )
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
            cur.execute('select id from erp.laundry_receipts where id=%s::uuid for update', (RECEIPT,))
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
            if 'DAMAGE conservation failed' in str(exc)
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


def damage_source_claim_holder(started: threading.Event, result: dict):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute(
                'select id from erp.laundry_receipts where id=%s::uuid for update',
                (CLAIM_WINS_RECEIPT,),
            )
            started.set()
            time.sleep(HOLD_SECONDS)
            set_operator_context(cur)
            result['response'] = action(cur, 'SAVE_CLAIM', {
                'action': 'SAVE', 'claim_number': 'CP5-RACE-DAMAGE-SOURCE-A',
                'vendor_id': VENDOR, 'delivery_id': DELIVERY,
                'receipt_line_id': CLAIM_WINS_RECEIPT_LINE,
                'qty_claimed': 1, 'claim_type': 'DAMAGE', 'compensation_amount': 0,
                'opened_at': '2026-09-03T09:00:00Z',
                'change_reason': 'CP5 race DAMAGE source claim winner',
            }, CLAIM_REQUEST_D, None)
        conn.commit()
        result['status'] = 'PASS'
    except Exception as exc:  # pragma: no cover - emitted in proof
        conn.rollback()
        result['status'] = 'FAIL'
        result['error'] = str(exc)
        started.set()
    finally:
        conn.close()


def damage_source_reverse_waiter(started: threading.Event, result: dict):
    started.wait(timeout=10)
    began = time.monotonic()
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute(
                "update erp.laundry_receipts set status='REVERSED' where id=%s::uuid",
                (CLAIM_WINS_RECEIPT,),
            )
        conn.commit()
        result['status'] = 'UNEXPECTED_SUCCESS'
    except Exception as exc:
        conn.rollback()
        result['error'] = str(exc)
        result['status'] = (
            'EXPECTED_REJECTION'
            if 'dependent DAMAGE claims' in str(exc)
            else 'WRONG_ERROR'
        )
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - began, 3)
        conn.close()


def run_damage_source_claim_wins_race():
    started = threading.Event()
    claim_winner = {}
    reversal_loser = {}
    first = threading.Thread(target=damage_source_claim_holder, args=(started, claim_winner), daemon=True)
    second = threading.Thread(target=damage_source_reverse_waiter, args=(started, reversal_loser), daemon=True)
    first.start(); second.start(); first.join(timeout=20); second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('DAMAGE claim-wins source race thread timeout')
    if claim_winner.get('status') != 'PASS' or reversal_loser.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'DAMAGE source claim-wins mismatch: claim={claim_winner}, reversal={reversal_loser}')
    if reversal_loser.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'DAMAGE source claim-wins race did not serialize: {reversal_loser}')
    final = scalar(
        """
        select jsonb_build_object(
          'receipt_status',(select status from erp.laundry_receipts where id=%s::uuid),
          'active_claims',(select count(*) from erp.laundry_claims
            where receipt_line_id=%s::uuid and status<>'REJECTED')
        )
        """,
        (CLAIM_WINS_RECEIPT, CLAIM_WINS_RECEIPT_LINE),
    )
    if final != {'receipt_status': 'POSTED', 'active_claims': 1}:
        raise RuntimeError(f'DAMAGE source claim-wins final mismatch: {final}')
    return {'claim_winner': claim_winner, 'reversal_loser': reversal_loser, 'final': final}


def damage_source_reversal_holder(started: threading.Event, result: dict):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute(
                "update erp.laundry_receipts set status='REVERSED' where id=%s::uuid",
                (REVERSAL_WINS_RECEIPT,),
            )
            started.set()
            time.sleep(HOLD_SECONDS)
        conn.commit()
        result['status'] = 'PASS'
    except Exception as exc:  # pragma: no cover - emitted in proof
        conn.rollback()
        result['status'] = 'FAIL'
        result['error'] = str(exc)
        started.set()
    finally:
        conn.close()


def damage_source_claim_waiter(started: threading.Event, result: dict):
    started.wait(timeout=10)
    began = time.monotonic()
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            set_operator_context(cur)
            result['unexpected_response'] = action(cur, 'SAVE_CLAIM', {
                'action': 'SAVE', 'claim_number': 'CP5-RACE-DAMAGE-SOURCE-B',
                'vendor_id': VENDOR, 'delivery_id': DELIVERY,
                'receipt_line_id': REVERSAL_WINS_RECEIPT_LINE,
                'qty_claimed': 1, 'claim_type': 'DAMAGE', 'compensation_amount': 0,
                'opened_at': '2026-09-03T09:00:01Z',
                'change_reason': 'CP5 race DAMAGE source reversal winner',
            }, CLAIM_REQUEST_E, None)
        conn.commit()
        result['status'] = 'UNEXPECTED_SUCCESS'
    except Exception as exc:
        conn.rollback()
        result['error'] = str(exc)
        result['status'] = (
            'EXPECTED_REJECTION'
            if 'requires a POSTED receipt' in str(exc)
            else 'WRONG_ERROR'
        )
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - began, 3)
        conn.close()


def run_damage_source_reversal_wins_race():
    started = threading.Event()
    reversal_winner = {}
    claim_loser = {}
    first = threading.Thread(target=damage_source_reversal_holder, args=(started, reversal_winner), daemon=True)
    second = threading.Thread(target=damage_source_claim_waiter, args=(started, claim_loser), daemon=True)
    first.start(); second.start(); first.join(timeout=20); second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('DAMAGE reversal-wins source race thread timeout')
    if reversal_winner.get('status') != 'PASS' or claim_loser.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'DAMAGE source reversal-wins mismatch: reversal={reversal_winner}, claim={claim_loser}')
    if claim_loser.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'DAMAGE source reversal-wins race did not serialize: {claim_loser}')
    final = scalar(
        """
        select jsonb_build_object(
          'receipt_status',(select status from erp.laundry_receipts where id=%s::uuid),
          'active_claims',(select count(*) from erp.laundry_claims
            where receipt_line_id=%s::uuid and status<>'REJECTED')
        )
        """,
        (REVERSAL_WINS_RECEIPT, REVERSAL_WINS_RECEIPT_LINE),
    )
    if final != {'receipt_status': 'REVERSED', 'active_claims': 0}:
        raise RuntimeError(f'DAMAGE source reversal-wins final mismatch: {final}')
    return {'reversal_winner': reversal_winner, 'claim_loser': claim_loser, 'final': final}


def stuck_claim_holder(started: threading.Event, result: dict):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute('select id from erp.laundry_deliveries where id=%s::uuid for update', (DELIVERY,))
            started.set()
            time.sleep(HOLD_SECONDS)
            set_operator_context(cur)
            result['response'] = action(cur, 'SAVE_CLAIM', {
                'action': 'SAVE', 'claim_number': 'CP5-RACE-STUCK-A', 'vendor_id': VENDOR,
                'delivery_id': DELIVERY, 'receipt_line_id': None,
                'qty_claimed': 6, 'claim_type': 'STUCK', 'compensation_amount': 0,
                'opened_at': '2026-09-03T09:00:00Z',
                'change_reason': 'CP5 race STUCK winner',
            }, CLAIM_REQUEST_C, None)
        conn.commit()
        result['status'] = 'PASS'
    except Exception as exc:  # pragma: no cover - emitted in proof
        conn.rollback()
        result['status'] = 'FAIL'
        result['error'] = str(exc)
        started.set()
    finally:
        conn.close()


def receipt_post_waiter(started: threading.Event, result: dict):
    started.wait(timeout=10)
    began = time.monotonic()
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute(
                "update erp.laundry_receipts set status='POSTED' where id=%s::uuid",
                (RETURN_RECEIPT,),
            )
        conn.commit()
        result['status'] = 'UNEXPECTED_SUCCESS'
    except Exception as exc:
        conn.rollback()
        result['error'] = str(exc)
        result['status'] = (
            'EXPECTED_REJECTION'
            if 'return plus active MISSING/STUCK claims exceed sent quantity' in str(exc)
            else 'WRONG_ERROR'
        )
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - began, 3)
        conn.close()


def run_stuck_vs_return_race():
    started = threading.Event()
    claim_winner = {}
    receipt_loser = {}
    first = threading.Thread(target=stuck_claim_holder, args=(started, claim_winner), daemon=True)
    second = threading.Thread(target=receipt_post_waiter, args=(started, receipt_loser), daemon=True)
    first.start(); second.start(); first.join(timeout=20); second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('STUCK claim vs receipt-post race thread timeout')
    if claim_winner.get('status') != 'PASS' or receipt_loser.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'STUCK claim vs receipt race mismatch: claim={claim_winner}, receipt={receipt_loser}')
    if receipt_loser.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'STUCK claim vs receipt race did not observe serialization wait: {receipt_loser}')
    final = scalar(
        """
        select jsonb_build_object(
          'sent',(select sum(qty_sent_pcs) from erp.laundry_delivery_lines where delivery_id=%s::uuid),
          'posted_return',(select coalesce(sum(l.qty_good_received+l.qty_bs_laundry),0)
            from erp.laundry_receipt_lines l join erp.laundry_receipts r on r.id=l.receipt_id
            where r.delivery_id=%s::uuid and r.status='POSTED'),
          'active_stuck',(select coalesce(sum(qty_claimed),0) from erp.laundry_claims
            where delivery_id=%s::uuid and claim_type in('MISSING','STUCK') and status<>'REJECTED'),
          'late_receipt_status',(select status from erp.laundry_receipts where id=%s::uuid)
        )
        """,
        (DELIVERY, DELIVERY, DELIVERY, RETURN_RECEIPT),
    )
    if final != {'sent': 10, 'posted_return': 4, 'active_stuck': 6, 'late_receipt_status': 'DRAFT'}:
        raise RuntimeError(f'STUCK claim vs receipt final conservation mismatch: {final}')
    return {'claim_winner': claim_winner, 'receipt_loser': receipt_loser, 'final': final}


def cash_disposition_winner(started: threading.Event, result: dict):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            set_operator_context(cur)
            result['response'] = action(cur, 'DISPOSE_BS', {
                'bs_case_id': CASH_WINS_BS_CASE,
                'resolution_type': 'CASH_COMPENSATION',
                'qty_pcs': 1, 'compensation_amount': 25,
                'source_laundry_claim_id': CASH_WINS_CLAIM,
                'physical_at': '2026-09-03T08:20:00Z',
                'change_reason': 'CP5 cash disposition commits before claim reversal',
            }, CASH_REQUEST_A, 1)
            started.set()
            time.sleep(HOLD_SECONDS)
        conn.commit()
        result['status'] = 'PASS'
    except Exception as exc:  # pragma: no cover - emitted in proof
        conn.rollback()
        result['status'] = 'FAIL'
        result['error'] = str(exc)
        started.set()
    finally:
        conn.close()


def claim_reversal_loser(started: threading.Event, result: dict):
    started.wait(timeout=10)
    began = time.monotonic()
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute("select set_config('app.change_reason','CP5 dependency race reversal loser',true)")
            cur.execute(
                "update erp.laundry_claims set status='REJECTED' where id=%s::uuid",
                (CASH_WINS_CLAIM,),
            )
        conn.commit()
        result['status'] = 'UNEXPECTED_SUCCESS'
    except Exception as exc:
        conn.rollback()
        result['error'] = str(exc)
        result['status'] = (
            'EXPECTED_REJECTION'
            if 'CLAIM_RESOLUTION_IN_USE_BY_ACTIVE_BS_CASH_COMPENSATION' in str(exc)
            else 'WRONG_ERROR'
        )
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - began, 3)
        conn.close()


def claim_reversal_winner(started: threading.Event, result: dict):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute("select set_config('app.change_reason','CP5 dependency race reversal winner',true)")
            cur.execute(
                "update erp.laundry_claims set status='REJECTED' where id=%s::uuid",
                (REVERSAL_WINS_CLAIM,),
            )
            started.set()
            time.sleep(HOLD_SECONDS)
        conn.commit()
        result['status'] = 'PASS'
    except Exception as exc:  # pragma: no cover - emitted in proof
        conn.rollback()
        result['status'] = 'FAIL'
        result['error'] = str(exc)
        started.set()
    finally:
        conn.close()


def cash_disposition_loser(started: threading.Event, result: dict):
    started.wait(timeout=10)
    began = time.monotonic()
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            set_operator_context(cur)
            result['unexpected_response'] = action(cur, 'DISPOSE_BS', {
                'bs_case_id': REVERSAL_WINS_BS_CASE,
                'resolution_type': 'CASH_COMPENSATION',
                'qty_pcs': 1, 'compensation_amount': 25,
                'source_laundry_claim_id': REVERSAL_WINS_CLAIM,
                'physical_at': '2026-09-03T08:21:00Z',
                'change_reason': 'CP5 claim reversal commits before cash disposition',
            }, CASH_REQUEST_B, 1)
        conn.commit()
        result['status'] = 'UNEXPECTED_SUCCESS'
    except Exception as exc:
        conn.rollback()
        result['error'] = str(exc)
        result['status'] = (
            'EXPECTED_REJECTION'
            if 'Linked laundry claim must be SETTLED' in str(exc)
            or 'BS_CASH_COMPENSATION_REQUIRES_ACTIVE_SETTLED_CLAIM' in str(exc)
            else 'WRONG_ERROR'
        )
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - began, 3)
        conn.close()


def run_claim_cash_dependency_races():
    cash_started = threading.Event()
    cash_winner = {}
    reversal_loser = {}
    first = threading.Thread(target=cash_disposition_winner, args=(cash_started, cash_winner), daemon=True)
    second = threading.Thread(target=claim_reversal_loser, args=(cash_started, reversal_loser), daemon=True)
    first.start(); second.start(); first.join(timeout=20); second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('cash-wins claim dependency race thread timeout')
    if cash_winner.get('status') != 'PASS' or reversal_loser.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'cash-wins claim dependency mismatch: cash={cash_winner}, reversal={reversal_loser}')
    if reversal_loser.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'cash-wins claim dependency did not serialize: {reversal_loser}')
    cash_final = scalar(
        """
        select jsonb_build_object(
          'claim_status',(select status from erp.laundry_claims where id=%s::uuid),
          'cash_resolution_count',(select count(*) from erp.bs_resolutions
            where bs_case_id=%s::uuid and source_laundry_claim_id=%s::uuid
              and resolution_type='CASH_COMPENSATION')
        )
        """,
        (CASH_WINS_CLAIM, CASH_WINS_BS_CASE, CASH_WINS_CLAIM),
    )
    if cash_final != {'claim_status': 'SETTLED', 'cash_resolution_count': 1}:
        raise RuntimeError(f'cash-wins dependency final state mismatch: {cash_final}')

    reversal_started = threading.Event()
    reversal_winner = {}
    cash_loser = {}
    third = threading.Thread(target=claim_reversal_winner, args=(reversal_started, reversal_winner), daemon=True)
    fourth = threading.Thread(target=cash_disposition_loser, args=(reversal_started, cash_loser), daemon=True)
    third.start(); fourth.start(); third.join(timeout=20); fourth.join(timeout=20)
    if third.is_alive() or fourth.is_alive():
        raise RuntimeError('reversal-wins claim dependency race thread timeout')
    if reversal_winner.get('status') != 'PASS' or cash_loser.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'reversal-wins claim dependency mismatch: reversal={reversal_winner}, cash={cash_loser}')
    if cash_loser.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'reversal-wins claim dependency did not serialize: {cash_loser}')
    reversal_final = scalar(
        """
        select jsonb_build_object(
          'claim_status',(select status from erp.laundry_claims where id=%s::uuid),
          'cash_resolution_count',(select count(*) from erp.bs_resolutions
            where bs_case_id=%s::uuid or source_laundry_claim_id=%s::uuid)
        )
        """,
        (REVERSAL_WINS_CLAIM, REVERSAL_WINS_BS_CASE, REVERSAL_WINS_CLAIM),
    )
    if reversal_final != {'claim_status': 'REJECTED', 'cash_resolution_count': 0}:
        raise RuntimeError(f'reversal-wins dependency final state mismatch: {reversal_final}')
    with connect() as conn, conn.cursor() as cur:
        cur.execute("select set_config('erp.cp45_allow_synthetic_cleanup','on',true)")
        cur.execute(
            "delete from erp.bs_resolutions where bs_case_id=any(%s::uuid[]) returning id",
            ([CASH_WINS_BS_CASE, REVERSAL_WINS_BS_CASE],),
        )
        retired_resolution_ids = [str(row[0]) for row in cur.fetchall()]
        cur.execute(
            "delete from erp.laundry_claims where id=any(%s::uuid[])",
            ([CASH_WINS_CLAIM, REVERSAL_WINS_CLAIM],),
        )
        cur.execute(
            "delete from erp.bs_cases where id=any(%s::uuid[])",
            ([CASH_WINS_BS_CASE, REVERSAL_WINS_BS_CASE],),
        )
        cur.execute(
            "delete from erp.idempotency_requests where client_request_id=any(%s::uuid[])",
            ([CASH_REQUEST_A, CASH_REQUEST_B],),
        )
        if retired_resolution_ids:
            cur.execute(
                "delete from erp.audit_logs "
                "where entity_type='bs_resolutions' and entity_id=any(%s::uuid[])",
                (retired_resolution_ids,),
            )
        conn.commit()
    return {
        'cash_winner': cash_winner, 'reversal_loser': reversal_loser,
        'cash_winner_final': cash_final, 'reversal_winner': reversal_winner,
        'cash_loser': cash_loser, 'reversal_winner_final': reversal_final,
    }


report = {'status': 'FAIL', 'production_go': False}
failure = None
try:
    setup()
    report['disposition_vs_disposition'] = run_disposition_race()
    report['claim_reversal_vs_bs_cash_compensation'] = run_claim_cash_dependency_races()
    report['damage_claim_vs_capacity'] = run_claim_race()
    report['damage_claim_wins_vs_receipt_reversal'] = run_damage_source_claim_wins_race()
    report['receipt_reversal_wins_vs_damage_claim'] = run_damage_source_reversal_wins_race()
    report['stuck_claim_vs_physical_return'] = run_stuck_vs_return_race()
    report['assertions'] = {
        'exactly_one_disposition_winner': True,
        'stale_disposition_cannot_overwrite': True,
        'damage_claim_capacity_serialized': True,
        'damage_claim_and_receipt_reversal_serialize_both_directions': True,
        'stuck_claim_and_physical_return_share_one_conservation_lock': True,
        'claim_reversal_and_bs_cash_compensation_serialize_both_directions': True,
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
          'bs_cases',(select count(*) from erp.bs_cases where id=any(%s::uuid[])),
          'bs_resolutions',(select count(*) from erp.bs_resolutions where bs_case_id=any(%s::uuid[])),
          'bs_components',(select count(*) from erp.bs_case_components where bs_case_id=%s::uuid),
          'claims',(select count(*) from erp.laundry_claims where claim_number like 'CP5-RACE-%%'),
          'receipts',(select count(*) from erp.laundry_receipts where id=any(%s::uuid[])),
          'receipt_lines',(select count(*) from erp.laundry_receipt_lines where id=any(%s::uuid[])),
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
            OPERATOR_APP,
            [BS_CASE, CASH_WINS_BS_CASE, REVERSAL_WINS_BS_CASE],
            [BS_CASE, CASH_WINS_BS_CASE, REVERSAL_WINS_BS_CASE],
            BS_CASE,
            [RECEIPT, RETURN_RECEIPT, CLAIM_WINS_RECEIPT, REVERSAL_WINS_RECEIPT],
            [RECEIPT_LINE, RETURN_RECEIPT_LINE, CLAIM_WINS_RECEIPT_LINE, REVERSAL_WINS_RECEIPT_LINE],
            DELIVERY, DELIVERY_LINE, VENDOR, GROUP, BATCH, PO,
            CONTRACTOR, MODEL,
            [
                DISPOSE_REQUEST_A, DISPOSE_REQUEST_B, CLAIM_REQUEST_A, CLAIM_REQUEST_B,
                CLAIM_REQUEST_C, CLAIM_REQUEST_D, CLAIM_REQUEST_E, CASH_REQUEST_A, CASH_REQUEST_B,
            ],
            OPERATOR_APP, OPERATOR_APP, OPERATOR_APP,
            [
                BS_CASE, PO, BATCH, GROUP, VENDOR, DELIVERY, DELIVERY_LINE,
                RECEIPT, RECEIPT_LINE, RETURN_RECEIPT, RETURN_RECEIPT_LINE,
                CLAIM_WINS_RECEIPT, CLAIM_WINS_RECEIPT_LINE,
                REVERSAL_WINS_RECEIPT, REVERSAL_WINS_RECEIPT_LINE,
                CASH_WINS_BS_CASE, CASH_WINS_CLAIM,
                REVERSAL_WINS_BS_CASE, REVERSAL_WINS_CLAIM, CONTRACTOR, MODEL,
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
print('CP5 BS Resolution concurrency passed: five serialized races; zero synthetic residue.')
