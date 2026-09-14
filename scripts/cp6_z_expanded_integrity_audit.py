#!/usr/bin/env python3
"""Independent expanded integrity audit for frozen CP6 candidate Z.

This script is deliberately test-only. It exercises ordinary OWNER posting
paths against the exact disposable native database and rolls every case back.
Exit 1 means at least one qualified counterexample; exit 2 means incomplete
evidence. Neither result is a candidate pass.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import traceback
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_v2620e_counterexample_regression as base
import cp6_v2620x_internal_role_regression as actors
import cp6_v2620z_runtime as z_runtime
import cp6_v2620aa_runtime as aa_runtime
import cp6_v2620ab_runtime as ab_runtime
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot


HEAD_Z = '134774825dbe5ff6ffba5b82f629c1dac2a3ce8d'
TREE_Z = '3afeddbbca86f28285b1b24a002a572b34be54b7'
PHASE = os.environ.get('CP6_AA_PHASE', 'BEFORE_AA')
if PHASE not in ('BEFORE_AA', 'AFTER_AA', 'AFTER_AB'):
    raise AssertionError('UNKNOWN_AA_AUDIT_PHASE')
REPORT_DIR = Path('cp6-proof/independent-z' if PHASE == 'BEFORE_AA' else 'cp6-proof/independent-aa')
REPORT = REPORT_DIR / ('Z_EXPANDED_INTEGRITY_AUDIT.json' if PHASE == 'BEFORE_AA' else 'AA_MATERIAL_DAY_REGRESSION.json')
if PHASE == 'AFTER_AB':
    REPORT_DIR = Path('cp6-proof/independent-ab')
    REPORT = REPORT_DIR / 'AB_MATERIAL_DAY_REGRESSION.json'
PROTOCOL = Path('docs/cp6-competition-mode-audit-protocol.md')
ZONES = ('Asia/Jakarta', 'UTC', 'Etc/GMT+12', 'Pacific/Kiritimati')
JAKARTA = ZoneInfo('Asia/Jakarta')
BASE_MATERIAL = 'c8c30000-0000-4000-8000-000000000002'
BASE_SUPPLIER = 'c8c30000-0000-4000-8000-000000000001'


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], text=True).strip()


def digest(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(result: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, default=str, sort_keys=True) + '\n')


def one(cur: psycopg.Cursor, query: str, params: tuple[Any, ...] = ()) -> Any:
    return base.one(cur, query, params)


def set_zone(cur: psycopg.Cursor, value: str) -> None:
    cur.execute("select set_config('TimeZone',%s,true)", (value,))


def as_admin(cur: psycopg.Cursor) -> None:
    actors.session(cur, 'supabase_admin')


def as_owner(cur: psycopg.Cursor) -> None:
    actors.claims(cur, {'sub': base.OPERATOR_AUTH, 'role': 'authenticated'})
    actors.session(cur, 'authenticated')
    cur.execute('select current_user,session_user,erp.current_app_role()')
    if cur.fetchone() != ('authenticated', 'authenticated', 'OWNER'):
        raise AssertionError('Z_EXPANDED_REAL_OWNER_SESSION_REQUIRED')


def stable_boundary(cur: psycopg.Cursor) -> dict[str, Any]:
    previous = one(cur, "select current_setting('TimeZone')")
    set_zone(cur, 'UTC')
    try:
        return snapshot(cur)
    finally:
        set_zone(cur, previous)


def clone_material(cur: psycopg.Cursor, label: str) -> uuid.UUID:
    material_id = uuid.uuid4()
    cur.execute(
        """
        insert into erp.materials
        select (jsonb_populate_record(
          null::erp.materials,
          to_jsonb(m)||jsonb_build_object(
            'id',%s::uuid,
            'material_sku',%s::text,
            'material_name',%s::text,
            'cached_stock_qty',0,
            'moving_average_cost',0,
            'created_at',clock_timestamp(),
            'updated_at',clock_timestamp()
          )
        )).* from erp.materials m where m.id=%s::uuid
        """,
        (material_id, f'Z-AUD-{label}-{material_id}',
         f'Z isolated {label} material', BASE_MATERIAL),
    )
    if cur.rowcount != 1:
        raise AssertionError('Z_EXPANDED_BASE_MATERIAL_MISSING')
    return material_id


def set_open_period(cur: psycopg.Cursor, through: date) -> None:
    as_admin(cur)
    cur.execute(
        """
        update erp.accounting_period_control
        set closed_through=%s,updated_at=clock_timestamp(),updated_by=null,
            change_reason='Z expanded disposable fixture'
        where singleton_id=1
        """,
        (through,),
    )
    if cur.rowcount != 1:
        raise AssertionError('Z_EXPANDED_PERIOD_CONTROL_MISSING')


def checkpoint_case(cur: psycopg.Cursor, zone: str, canonical_today: date) -> dict[str, Any]:
    checkpoint_day = canonical_today - timedelta(days=2)
    set_zone(cur, 'Asia/Jakarta')
    as_admin(cur)
    material_id = clone_material(cur, 'checkpoint')
    set_open_period(cur, checkpoint_day - timedelta(days=1))
    first_at = datetime.combine(checkpoint_day, time(23, 0), tzinfo=JAKARTA)
    second_at = datetime.combine(checkpoint_day + timedelta(days=1), time(1, 0), tzinfo=JAKARTA)
    first_purchase, _, first_id = post_purchase(cur, material_id, first_at, unit_price=10)
    second_purchase, _, second_id = post_purchase(cur, material_id, second_at, unit_price=20)
    as_admin(cur)
    history = cur.execute("""
      select movement_id,stock_after,average_after from erp.material_cost_history
      where material_id=%s order by physical_at
      """, (material_id,)).fetchall()
    if history != [(first_id, Decimal('10'), Decimal('10')),
                   (second_id, Decimal('20'), Decimal('15'))]:
        raise AssertionError('Z_EXPANDED_PURCHASE_HISTORY_NOT_QUALIFIED:' + str(history))

    set_zone(cur, zone)
    as_owner(cur)
    cur.execute(
        'select erp.close_accounting_through(%s,%s)',
        (checkpoint_day, 'Z expanded checkpoint boundary'),
    )
    if one(cur, "select current_setting('TimeZone')") != zone:
        raise AssertionError('Z_EXPANDED_CLOSE_CHANGED_CALLER_ZONE')

    as_admin(cur)
    cur.execute(
        """
        select checkpoint_date::text,stock_qty::text,moving_average_cost::text,
               last_movement_id::text,last_physical_at::text
        from erp.material_cost_checkpoints where material_id=%s
        """,
        (material_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise AssertionError('Z_EXPANDED_CLOSE_DID_NOT_CREATE_CHECKPOINT')
    actual = dict(zip(
        ('checkpoint_date', 'stock_qty', 'moving_average_cost',
         'last_movement_id', 'last_physical_at'), row, strict=True
    ))
    expected = {
        'checkpoint_date': str(checkpoint_day),
        'stock_qty': '10.000000',
        'moving_average_cost': '10.000000',
        'last_movement_id': str(first_id),
        'last_physical_at': str(first_at),
    }
    # Timestamp text formatting is session-dependent. The immutable movement
    # identity plus quantity and cost form the cross-zone oracle.
    correct = (
        actual['checkpoint_date'] == expected['checkpoint_date']
        and Decimal(actual['stock_qty']) == Decimal('10')
        and Decimal(actual['moving_average_cost']) == Decimal('10')
        and actual['last_movement_id'] == str(first_id)
    )
    return {
        'status': 'CONTROL_PASS' if correct else 'NEW_Z_BUG_REPRODUCED',
        'severity': None if correct else 'P1',
        'classification': ('LAWFUL_CHECKPOINT_CONTROL' if correct
                           else 'MATERIAL_CHECKPOINT_CROSSES_BUSINESS_DAY'),
        'zone': zone,
        'canonical_today': str(canonical_today),
        'checkpoint_day': str(checkpoint_day),
        'first_business_movement': {
            'id': str(first_id), 'physical_at': first_at.isoformat(), 'cost': '10',
        },
        'following_business_movement': {
            'id': str(second_id), 'physical_at': second_at.isoformat(), 'cost': '20',
        },
        'expected': expected,
        'actual': actual,
        'ordinary_owner_close_path': True,
        'fixture_source': 'TWO_POSTED_MATERIAL_PURCHASE_V2_RECEIPTS',
        'purchase_ids': [str(first_purchase), str(second_purchase)],
        'actor': {'current_user': 'authenticated', 'app_role': 'OWNER'},
        'production_go': False,
    }


def post_purchase(
    cur: psycopg.Cursor, material_id: uuid.UUID, physical_at: datetime,
    unit_price: int = 10,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    location_id = uuid.uuid4()
    as_admin(cur)
    cur.execute(
        """
        insert into erp.locations(
          id,location_code,location_name,location_type,is_active
        ) values(%s,%s,%s,'RAW_MATERIAL_WAREHOUSE',true)
        """,
        (location_id, f'Z-LOC-{location_id.hex[:20]}', 'Z disposable material location'),
    )
    as_owner(cur)
    draft = one(
        cur,
        'select erp.save_material_purchase_draft_v2(%s::jsonb,%s::uuid,null)',
        (
            json.dumps({
                'purchase_number': f'Z-AUD-PUR-{uuid.uuid4()}',
                'supplier_id': BASE_SUPPLIER,
                'location_id': str(location_id),
                'physical_at': physical_at.isoformat(),
                'change_reason': 'Z expanded retroactive final-cost fixture',
                'lines': [{
                    'material_id': str(material_id),
                    'qty': 10,
                    'unit_price': unit_price,
                    # This correction path is lawful only for a receipt
                    # already tied directly to a final supplier invoice. An
                    # estimated receipt must use the separate invoice flow.
                    'price_state': 'FINAL',
                    'price_source': 'SUPPLIER_INVOICE',
                    'rolls': [{
                        'roll_number': f'Z-AUD-ROLL-{uuid.uuid4()}', 'qty': 10,
                    }],
                }],
            }),
            uuid.uuid4(),
        ),
    )
    if not isinstance(draft, dict) or 'purchase_id' not in draft or 'row_version' not in draft:
        raise AssertionError('Z_EXPANDED_PURCHASE_DRAFT_RESPONSE')
    purchase_id = uuid.UUID(str(draft['purchase_id']))
    cur.execute(
        'select erp.post_material_purchase_v2(%s,%s,%s,%s)',
        (purchase_id, uuid.uuid4(), int(draft['row_version']),
         'Z expanded direct-final material receipt'),
    )
    # The application owner can post through V2; movement observation uses the
    # disposable administrator because the movement table is private.
    as_admin(cur)
    cur.execute(
        """
        select i.id,m.id
        from erp.material_purchase_items i
        join erp.material_stock_movements m
          on m.material_id=i.material_id and m.movement_type='PURCHASE'
         and ((m.source_type='MATERIAL_PURCHASE_ITEM' and m.source_id=i.id)
           or (m.source_type='MATERIAL_PURCHASE_ROLL' and m.source_id in(
             select r.id from erp.material_rolls r where r.purchase_item_id=i.id
           )))
        where i.purchase_id=%s
        order by m.id
        """,
        (purchase_id,),
    )
    rows = cur.fetchall()
    if len(rows) != 1:
        raise AssertionError('Z_EXPANDED_PURCHASE_MOVEMENT_CARDINALITY:' + str(len(rows)))
    found = rows[0]
    return purchase_id, found[0], found[1]


def late_recost_case(cur: psycopg.Cursor, zone: str, canonical_today: date) -> dict[str, Any]:
    purchase_day = canonical_today - timedelta(days=1)
    physical_at = datetime.combine(purchase_day, time(23, 30), tzinfo=JAKARTA)
    set_zone(cur, 'Asia/Jakarta')
    as_admin(cur)
    material_id = clone_material(cur, 'late-recost')
    set_open_period(cur, purchase_day - timedelta(days=1))
    purchase_id, purchase_item_id, movement_id = post_purchase(
        cur, material_id, physical_at
    )

    # The ordinary owner closes the day in Jakarta first, producing a valid
    # checkpoint with the original final price.
    set_zone(cur, 'Asia/Jakarta')
    as_owner(cur)
    cur.execute(
        'select erp.close_accounting_through(%s,%s)',
        (purchase_day, 'Z expanded pre-invoice checkpoint'),
    )
    # Observe the private checkpoint as the disposable database owner, then
    # return to the ordinary application owner for the correction itself.
    as_admin(cur)
    checkpoint_before = one(
        cur,
        """
        select jsonb_build_object(
          'date',checkpoint_date,'stock',stock_qty,'average',moving_average_cost,
          'last_movement_id',last_movement_id
        ) from erp.material_cost_checkpoints where material_id=%s
        """,
        (material_id,),
    )
    if (checkpoint_before is None
            or Decimal(str(checkpoint_before['stock'])) != Decimal('10')
            or Decimal(str(checkpoint_before['average'])) != Decimal('10')
            or str(checkpoint_before['last_movement_id']) != str(movement_id)):
        raise AssertionError('Z_EXPANDED_PRE_INVOICE_CHECKPOINT_NOT_QUALIFIED')

    as_owner(cur)
    correction_id = uuid.uuid4()
    cur.execute(
        """
        insert into erp.material_purchase_cost_corrections(
          id,correction_number,purchase_id,invoice_date,reason,status
        ) values(%s,%s,%s,%s,%s,'DRAFT')
        """,
        (correction_id, f'Z-AUD-COST-{correction_id}', purchase_id,
         purchase_day, 'Z expanded retroactive final supplier price'),
    )
    cur.execute(
        """
        insert into erp.material_purchase_cost_correction_items(
          correction_id,purchase_item_id,new_unit_price
        ) values(%s,%s,20)
        """,
        (correction_id, purchase_item_id),
    )

    period_from = canonical_today.replace(day=1)
    before_confidence = one(
        cur,
        "select erp.get_owner_financial_snapshot_v2(%s,%s,%s)->'data_confidence'->>'status'",
        (period_from, canonical_today, canonical_today),
    )
    if before_confidence != 'READY':
        raise AssertionError('Z_EXPANDED_BASELINE_REPORT_NOT_READY')

    set_zone(cur, zone)
    cur.execute('select erp.post_material_purchase_cost_correction(%s)', (correction_id,))
    if one(cur, "select current_setting('TimeZone')") != zone:
        raise AssertionError('Z_EXPANDED_RECOST_CHANGED_CALLER_ZONE')

    as_admin(cur)
    cur.execute(
        """
        select m.cached_stock_qty::text,m.moving_average_cost::text,
               s.input_unit_cost::text,s.unit_cost_snapshot::text,
               s.is_cost_recalculated,
               h.movement_unit_cost::text,h.stock_after::text,h.average_after::text,
               c.status,erp.material_purchase_payable_total(%s)::text
        from erp.materials m
        join erp.material_stock_movements s on s.id=%s
        left join erp.material_cost_history h on h.movement_id=s.id
        join erp.material_purchase_cost_corrections c on c.id=%s
        where m.id=%s
        """,
        (purchase_id, movement_id, correction_id, material_id),
    )
    observed = cur.fetchone()
    if observed is None:
        raise AssertionError('Z_EXPANDED_RECOST_STATE_MISSING')
    keys = (
        'stock_qty', 'moving_average_cost', 'input_unit_cost',
        'unit_cost_snapshot', 'is_cost_recalculated', 'history_unit_cost',
        'history_stock_after', 'history_average_after', 'correction_status',
        'payable_total',
    )
    state = dict(zip(keys, observed, strict=True))
    inventory_value = Decimal(state['stock_qty']) * Decimal(state['moving_average_cost'])
    correct = (
        Decimal(state['stock_qty']) == Decimal('10')
        and Decimal(state['moving_average_cost']) == Decimal('20')
        and Decimal(state['input_unit_cost']) == Decimal('20')
        and Decimal(state['unit_cost_snapshot']) == Decimal('20')
        and state['is_cost_recalculated'] is True
        and Decimal(state['history_unit_cost']) == Decimal('20')
        and Decimal(state['history_average_after']) == Decimal('20')
        and state['correction_status'] == 'POSTED'
        and Decimal(state['payable_total']) == Decimal('200')
        and inventory_value == Decimal('200')
    )
    as_owner(cur)
    after_confidence = one(
        cur,
        "select erp.get_owner_financial_snapshot_v2(%s,%s,%s)->'data_confidence'->>'status'",
        (period_from, canonical_today, canonical_today),
    )
    return {
        'status': 'CONTROL_PASS' if correct else 'NEW_Z_BUG_REPRODUCED',
        'severity': None if correct else 'P1',
        'classification': ('LAWFUL_LATE_RECOST_CONTROL' if correct else
                           'LATE_INVOICE_MATERIAL_COST_RECALCULATION_SKIPPED'),
        'zone': zone,
        'purchase_business_day': str(purchase_day),
        'purchase_physical_at': physical_at.isoformat(),
        'zone_interpreted_date': str(physical_at.astimezone(ZoneInfo(zone)).date()),
        'checkpoint_before': checkpoint_before,
        'expected': {
            'stock_qty': '10', 'moving_average_cost': '20',
            'unit_cost_snapshot': '20', 'inventory_value': '200',
            'payable_total': '200', 'correction_status': 'POSTED',
        },
        'actual': {**state, 'inventory_value': str(inventory_value)},
        'report_confidence_before': before_confidence,
        'report_confidence_after': after_confidence,
        'silent_if_ready': (not correct and after_confidence == 'READY'),
        'ordinary_owner_purchase_close_and_correction_path': True,
        'actor': {'current_user': 'authenticated', 'app_role': 'OWNER'},
        'production_go': False,
    }


def initial_coverage() -> dict[str, dict[str, Any]]:
    return {
        'business_day_checkpoint': {
            'status': 'INCOMPLETE', 'required_level': 'NATIVE_ACCEPTED',
            'case_prefix': 'CHECKPOINT:',
        },
        'late_material_recost': {
            'status': 'INCOMPLETE', 'required_level': 'NATIVE_ACCEPTED',
            'case_prefix': 'LATE_RECOST:',
        },
        'long_transaction_midnight': {
            'status': 'INCOMPLETE', 'required_level': 'NATIVE_ACCEPTED',
            'reason': 'not executed by this bounded run',
        },
        'late_recost_wip_fg_cogs': {
            'status': 'INCOMPLETE', 'required_level': 'NATIVE_ACCEPTED',
            'reason': 'downstream WIP/FG/COGS propagation remains required',
        },
        'partial_laundry_fg_conservation': {
            'status': 'INCOMPLETE', 'required_level': 'NATIVE_ACCEPTED',
            'inherited_evidence': 'Z Auth95 and full CP6 matrix passed; expanded independent cases remain required',
        },
        'linked_corrections_and_report_confidence': {
            'status': 'INCOMPLETE', 'required_level': 'NATIVE_ACCEPTED',
            'reason': 'expanded linked-correction matrix remains required',
        },
        'permission_state_changes': {
            'status': 'INCOMPLETE', 'required_level': 'NATIVE_ACCEPTED',
            'reason': 'expanded null/inactive/revocation matrix remains required',
        },
        'concurrent_submit_reservation': {
            'status': 'INCOMPLETE', 'required_level': 'NATIVE_ACCEPTED',
            'reason': 'expanded multi-session matrix remains required',
        },
        'admission_rollback_orphans': {
            'status': 'INCOMPLETE', 'required_level': 'NATIVE_ACCEPTED',
            'inherited_evidence': 'Z 420/420 matrix passed; expanded independent cases remain required',
        },
    }


def audit() -> int:
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    required = {
        'user': 'postgres', 'password': 'postgres', 'host': '127.0.0.1',
        'port': '54322', 'dbname': 'postgres',
    }
    if params != required:
        raise AssertionError('Z_EXPANDED_EXACT_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_Z_EXPANDED_CONFIRM') != 'postgres':
        raise AssertionError('Z_EXPANDED_DISPOSABLE_CONFIRMATION_REQUIRED')
    if git('rev-parse', HEAD_Z + '^{tree}') != TREE_Z:
        raise AssertionError('Z_EXPANDED_FROZEN_Z_TREE_MISMATCH')
    if git('merge-base', HEAD_Z, 'HEAD') != HEAD_Z:
        raise AssertionError('Z_EXPANDED_HEAD_NOT_DESCENDED_FROM_Z')
    if git('diff', '--diff-filter=MDRTCUXB', '--name-only', HEAD_Z, 'HEAD', '--',
           'supabase/migrations', 'supabase/rollbacks'):
        raise AssertionError('Z_EXPANDED_FROZEN_BUSINESS_SQL_CHANGED')
    added = set(git('diff', '--diff-filter=A', '--name-only', HEAD_Z, 'HEAD', '--',
                    'supabase/migrations', 'supabase/rollbacks').splitlines())
    if added != {str(aa_runtime.MIGRATION), str(aa_runtime.ROLLBACK), str(ab_runtime.MIGRATION), str(ab_runtime.ROLLBACK)}:
        raise AssertionError('Z_EXPANDED_ONLY_REVIEWED_AA_AB_SUCCESSORS_ALLOWED')
    ab_runtime.verify_audit_source()
    if os.environ.get('GITHUB_SHA') != git('rev-parse', 'HEAD'):
        raise AssertionError('Z_EXPANDED_EXACT_CHECKOUT_REQUIRED')

    result: dict[str, Any] = {
        'format': 'CP6_Z_AA_MATERIAL_DAY_AUDIT_V2',
        'phase': PHASE,
        'runtime_generation': {'BEFORE_AA': 'Z', 'AFTER_AA': 'AA', 'AFTER_AB': 'AB'}[PHASE],
        'status': 'INCOMPLETE',
        'head': git('rev-parse', 'HEAD'),
        'tree': git('rev-parse', 'HEAD^{tree}'),
        'parents': git('show', '-s', '--format=%P', 'HEAD').split(),
        'audited_business_head': HEAD_Z if PHASE == 'BEFORE_AA' else git('rev-parse', 'HEAD'),
        'audited_business_tree': TREE_Z if PHASE == 'BEFORE_AA' else git('rev-parse', 'HEAD^{tree}'),
        'frozen_predecessor_head': HEAD_Z,
        'frozen_predecessor_tree': TREE_Z,
        'run_id': os.environ.get('GITHUB_RUN_ID'),
        'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
        'frozen_z_business_sql_unchanged': True,
        'real_authenticated_owner_session': True,
        'synthetic_fixture_only': True,
        'contains_business_rows': False,
        'contains_credentials': False,
        'hosted_database_used': False,
        'production_go': False,
        'coverage': initial_coverage(),
        'cases': {},
    }
    save(result)

    # Supabase's disposable postgres login is intentionally not the session
    # authorization owner.  Match the established native harnesses by opening
    # the local connection as supabase_admin after validating the fixed PGURL.
    with psycopg.connect(
        **dict(params, user='supabase_admin'), autocommit=False
    ) as conn, conn.cursor() as cur:
        cur.execute(
            "set local timezone='UTC';"
            "set local statement_timeout='180s';"
            "set local lock_timeout='8s';"
            "set local application_name='cp6-z-expanded-integrity-audit'"
        )
        baseline = stable_boundary(cur)
        result['engine'] = one(cur, 'select version()')
        result['server_version'] = one(cur, "select current_setting('server_version')")
        if not str(result['server_version']).startswith('17.6'):
            raise AssertionError('Z_EXPANDED_PINNED_POSTGRES_17_6_REQUIRED')
        if len(z_runtime.verified_successor(cur)) != 1:
            raise AssertionError('Z_EXPANDED_EXACT_Z_RUNTIME_REQUIRED')
        installed_aa = aa_runtime.verified_successor(cur)
        if len(installed_aa) != (0 if PHASE == 'BEFORE_AA' else 2):
            raise AssertionError('Z_AA_EXACT_PHASE_RUNTIME_REQUIRED')
        result['verified_aa_functions'] = list(installed_aa.values())
        installed_ab = ab_runtime.verified_successor(cur)
        if len(installed_ab) != (5 if PHASE == 'AFTER_AB' else 0):
            raise AssertionError('Z_AB_EXACT_PHASE_RUNTIME_REQUIRED')
        result['verified_ab_functions'] = list(installed_ab.values())

        catalog = function_catalog(cur)
        selected_names = {
            'erp.close_accounting_through(date,text)',
            'erp.refresh_material_cost_checkpoint(uuid,date)',
            'erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)',
            'erp.post_material_purchase_cost_correction(uuid)',
            'erp.finish_production_order(uuid)',
            'erp._post_cutting_qty_correction(uuid,text,text,text,jsonb,timestamp with time zone,uuid)',
        }
        selected = [row for row in catalog if row[0] in selected_names]
        if {row[0] for row in selected} != selected_names:
            raise AssertionError('Z_EXPANDED_TARGET_SOURCE_SET_MISSING')
        source_by_name = {row[0]: row[1] for row in selected}
        anchors = {
            'close_canonical_guard': 'p_closed_through>=erp._cp3_business_date(current_timestamp)',
            'checkpoint_session_cutoff': 'v_cutoff:=(p_checkpoint_date+1)::timestamptz',
            'recalc_session_date': 'p_recalc_from::date>v_cp.checkpoint_date',
            'late_recost_call': 'perform erp.recalculate_material_cost(m.material_id,p.physical_at)',
            'finish_session_date': 'perform erp.sync_po_hpp_to_gl(p_po_id,current_date)',
            'cutting_session_date': 'erp.sync_po_hpp_to_gl(v_po_id,COALESCE(p_physical_at,now())::date)',
        }
        anchor_owners = {
            'close_canonical_guard': 'erp.close_accounting_through(date,text)',
            'checkpoint_session_cutoff': 'erp.refresh_material_cost_checkpoint(uuid,date)',
            'recalc_session_date': 'erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)',
            'late_recost_call': 'erp.post_material_purchase_cost_correction(uuid)',
            'finish_session_date': 'erp.finish_production_order(uuid)',
            'cutting_session_date': 'erp._post_cutting_qty_correction(uuid,text,text,text,jsonb,timestamp with time zone,uuid)',
        }
        if PHASE in ('AFTER_AA', 'AFTER_AB'):
            anchors['checkpoint_session_cutoff'] = "v_cutoff:=((p_checkpoint_date+1)::timestamp at time zone 'Asia/Jakarta');"
            anchors['recalc_session_date'] = 'erp._cp3_business_date(p_recalc_from)>v_cp.checkpoint_date'
        for key, anchor in anchors.items():
            if source_by_name[anchor_owners[key]].count(anchor) != 1:
                raise AssertionError('Z_EXPANDED_SOURCE_ANCHOR:' + key)
        result['source_observations'] = [
            {
                'identity': row[0],
                'definition_sha256': hashlib.sha256(row[1].encode()).hexdigest(),
                'acl': row[2], 'owner': row[3],
            }
            for row in selected
        ]
        result['source_anchors'] = anchors

        schema_usage = one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        if not schema_usage:
            cur.execute('grant usage on schema erp to authenticated')
        actors.claims(cur, {'sub': base.OPERATOR_AUTH, 'role': 'authenticated'})
        base.load_fixture_foundation(cur)
        canonical_today = one(cur, 'select erp._cp3_business_date(current_timestamp)')
        if not isinstance(canonical_today, date):
            raise AssertionError('Z_EXPANDED_CANONICAL_TODAY_REQUIRED')

        case_specs = [
            (f'CHECKPOINT:{zone}', lambda value=zone: checkpoint_case(cur, value, canonical_today))
            for zone in ZONES
        ] + [
            (f'LATE_RECOST:{zone}', lambda value=zone: late_recost_case(cur, value, canonical_today))
            for zone in ZONES
        ]
        result['expected_case_count'] = len(case_specs)
        for name, operation in case_specs:
            as_admin(cur)
            set_zone(cur, 'UTC')
            cur.execute('savepoint z_expanded_case')
            before = stable_boundary(cur)
            try:
                evidence = operation()
            except Exception as exc:  # A fixture failure must remain visible.
                evidence = {
                    'status': 'INCOMPLETE',
                    'classification': 'FIXTURE_OR_ORACLE_ERROR',
                    'error': str(exc),
                    'traceback': traceback.format_exc(),
                    'sqlstate': getattr(exc, 'sqlstate', None),
                    'production_go': False,
                }
            finally:
                cur.execute('rollback to savepoint z_expanded_case')
                as_admin(cur)
                cur.execute('release savepoint z_expanded_case')
            evidence['full_boundary_restored'] = stable_boundary(cur) == before
            if not evidence['full_boundary_restored']:
                evidence['status'] = 'INCOMPLETE'
                evidence['classification'] = 'CASE_ROLLBACK_RESIDUE'
            result['cases'][name] = evidence
            save(result)
            print('Z_EXPANDED_CASE ' + json.dumps(
                {'name': name, **evidence}, default=str, sort_keys=True
            ), flush=True)

        conn.rollback()
        result['entire_unseeded_runtime_restored'] = stable_boundary(cur) == baseline
        result['schema_usage_restored'] = (
            one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
            == schema_usage
        )
        conn.rollback()

    attempted_incomplete = sum(
        case['status'] == 'INCOMPLETE' for case in result['cases'].values()
    )
    qualified = sum(
        case['status'] == 'NEW_Z_BUG_REPRODUCED' for case in result['cases'].values()
    )
    controls = sum(
        case['status'] == 'CONTROL_PASS' for case in result['cases'].values()
    )
    for area, prefix in (
        ('business_day_checkpoint', 'CHECKPOINT:'),
        ('late_material_recost', 'LATE_RECOST:'),
    ):
        rows = [v for k, v in result['cases'].items() if k.startswith(prefix)]
        if any(row['status'] == 'NEW_Z_BUG_REPRODUCED' for row in rows):
            result['coverage'][area].update(
                status='FAIL', executed_cases=len(rows), evidence_level='NATIVE_QUALIFIED'
            )
        elif rows and all(row['status'] == 'CONTROL_PASS' for row in rows):
            result['coverage'][area].update(
                status='PASS', executed_cases=len(rows), evidence_level='NATIVE_QUALIFIED'
            )
        else:
            result['coverage'][area].update(
                status='INCOMPLETE', executed_cases=len(rows), evidence_level='INCOMPLETE'
            )

    result['qualified_counterexamples'] = qualified
    result['controls_passed'] = controls
    result['incomplete_attempted_cases'] = attempted_incomplete
    result['all_attempted_cases_accounted'] = (
        len(result['cases']) == result['expected_case_count']
        and qualified + controls + attempted_incomplete == result['expected_case_count']
    )
    restoration_ok = (
        result['entire_unseeded_runtime_restored']
        and result['schema_usage_restored']
        and all(case['full_boundary_restored'] for case in result['cases'].values())
    )
    if qualified and attempted_incomplete == 0 and restoration_ok:
        result['status'] = 'FAIL_NEW_COUNTEREXAMPLE'
    elif controls == result['expected_case_count'] and attempted_incomplete == 0 and restoration_ok:
        # This passes only the bounded eight-case regression. Every wider
        # independent ledger row remains open until separately executed.
        result['status'] = 'PASS_BOUNDED_AUDIT'
    else:
        result['status'] = 'INCOMPLETE'
    result['sources'] = {
        str(path): digest(path)
        for path in (Path(__file__), PROTOCOL, Path('.github/workflows/cp6-full-schema-validation.yml'))
    }
    save(result)
    print('Z_EXPANDED_SUMMARY ' + json.dumps({
        'status': result['status'],
        'qualified_counterexamples': qualified,
        'controls_passed': controls,
        'incomplete_attempted_cases': attempted_incomplete,
        'entire_unseeded_runtime_restored': result['entire_unseeded_runtime_restored'],
        'production_go': False,
    }, sort_keys=True), flush=True)
    if result['status'] == 'PASS_BOUNDED_AUDIT':
        return 0
    return 1 if result['status'] == 'FAIL_NEW_COUNTEREXAMPLE' else 2


if __name__ == '__main__':
    try:
        exit_status = audit()
    except Exception as exc:
        previous = json.loads(REPORT.read_text()) if REPORT.exists() else {}
        previous.update(
            status='INCOMPLETE', fatal_error=str(exc),
            fatal_sqlstate=getattr(exc, 'sqlstate', None), production_go=False,
        )
        save(previous)
        print('Z_EXPANDED_FATAL ' + json.dumps({
            'status': 'INCOMPLETE', 'error': str(exc), 'production_go': False,
        }), flush=True)
        exit_status = 2
    raise SystemExit(exit_status)
