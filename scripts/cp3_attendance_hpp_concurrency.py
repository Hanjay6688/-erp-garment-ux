#!/usr/bin/env python3
"""Real two-connection concurrency checks for the CP3 attendance HPP candidate.

This script is LOCAL/DISPOSABLE ONLY. It refuses to run unless
CP3_ALLOW_DESTRUCTIVE_LOCAL=YES. It creates tagged fixtures, runs true concurrent
transactions, reconciles journals/state, removes exact fixtures, and writes a
non-secret JSON report.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time
import uuid

import psycopg
from psycopg.rows import dict_row

PGURL = os.environ.get("PGURL", "postgresql://postgres:postgres@127.0.0.1:5432/postgres")
REPORT = Path(os.environ.get("CP3_CONCURRENCY_REPORT", "cp3-concurrency-report.json"))
USER_ID = "a0000000-0000-0000-0000-000000000001"
CONTRACTOR_ID = "a1000000-0000-0000-0000-000000000001"
PO_ID = "a2000000-0000-0000-0000-000000000001"
GROUP_ID = "a3000000-0000-0000-0000-000000000001"
COMPONENT_ID = "a4000000-0000-0000-0000-000000000001"
SNAPSHOT_ID = "a4100000-0000-0000-0000-000000000001"
WORK_ID = "a5000000-0000-0000-0000-000000000001"
WORK_LINE_ID = "a5100000-0000-0000-0000-000000000001"
PAYROLL_ID = "a6000000-0000-0000-0000-000000000001"
PAYROLL_ITEM_ID = "a6100000-0000-0000-0000-000000000001"


def connect():
    return psycopg.connect(PGURL, row_factory=dict_row)


def session_identity(conn):
    conn.execute("select set_config('app.test_user_id', %s, false)", (USER_ID,))
    conn.execute("set lock_timeout='10s'")
    conn.execute("set statement_timeout='60s'")


def call_json(conn, sql: str, params=()):
    row = conn.execute(sql, params).fetchone()
    return next(iter(row.values()))


def setup_fixture():
    with connect() as conn:
        session_identity(conn)
        conn.execute(
            "insert into erp.app_users(id,display_name,role,is_active) values(%s,'CP3 concurrency owner','OWNER',true)",
            (USER_ID,),
        )
        conn.execute(
            "insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required) values(%s,'CP3-CONC','CP3 concurrency Mandor','MANDOR',true)",
            (CONTRACTOR_ID,),
        )
        call_json(
            conn,
            "select erp.set_contractor_hpp_policy_v1(%s::jsonb,%s::uuid,null)",
            (
                json.dumps(
                    {
                        "contractor_id": CONTRACTOR_ID,
                        "effective_from": "2026-02-01",
                        "is_special": False,
                        "attendance_required": True,
                        "reason": "CP3 concurrency policy",
                    }
                ),
                str(uuid.uuid4()),
            ),
        )
        conn.execute(
            "insert into erp.production_orders(id,po_number,contractor_id,status) values(%s,'CP3-CONC-PO',%s,'IN_PROGRESS')",
            (PO_ID, CONTRACTOR_ID),
        )
        conn.execute(
            "insert into erp.cutting_groups(id,po_id,total_pcs) values(%s,%s,100)",
            (GROUP_ID, PO_ID),
        )
        conn.execute(
            "insert into erp.work_components(id,component_name,component_category) values(%s,'CP3 concurrency component','SEWING')",
            (COMPONENT_ID,),
        )
        conn.execute(
            "insert into erp.po_work_component_snapshots(id,po_id,work_component_id,rate_per_pcs_snapshot) values(%s,%s,%s,1)",
            (SNAPSHOT_ID, PO_ID, COMPONENT_ID),
        )
        conn.execute(
            "insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,created_by) values(%s,'CP3-CONC-WC',%s,%s,%s,'2026-02-10 08:00:00+07','POSTED',%s)",
            (WORK_ID, PO_ID, CONTRACTOR_ID, GROUP_ID, USER_ID),
        )
        conn.execute(
            "insert into erp.work_completion_lines(id,completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot) values(%s,%s,%s,%s,100,100,1)",
            (WORK_LINE_ID, WORK_ID, SNAPSHOT_ID, COMPONENT_ID),
        )
        terminal = call_json(
            conn,
            "select erp.record_sewing_terminal_v1(%s::jsonb,%s::uuid)",
            (
                json.dumps(
                    {
                        "work_completion_id": WORK_ID,
                        "qty_pcs": 100,
                        "reason": "CP3 concurrency terminal",
                    }
                ),
                str(uuid.uuid4()),
            ),
        )
        conn.execute(
            "insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,status,attendance_total) values(%s,'CP3-CONC-PAY',%s,'2026-02-01','2026-02-15','PAID',100)",
            (PAYROLL_ID, CONTRACTOR_ID),
        )
        conn.execute(
            "insert into erp.payroll_attendance_items(id,payroll_id,worker_id,attendance_record_id,paid_fraction_snapshot,daily_rate_snapshot) values(%s,%s,gen_random_uuid(),gen_random_uuid(),1,100)",
            (PAYROLL_ITEM_ID, PAYROLL_ID),
        )
        call_json(
            conn,
            "select erp.post_journal('PAYROLL_EXTRA_ACCRUAL',%s::uuid,'2026-02-15','CP3 concurrency payroll',jsonb_build_array(jsonb_build_object('mapping_key','LABOR_COST','debit',100,'credit',0,'contractor_id',%s::uuid),jsonb_build_object('mapping_key','WIP','debit',0,'credit',100,'contractor_id',%s::uuid)))",
            (PAYROLL_ID, CONTRACTOR_ID, CONTRACTOR_ID),
        )
        pool = call_json(
            conn,
            "select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s::uuid)",
            (
                json.dumps(
                    {
                        "period_start": "2026-02-01",
                        "period_end": "2026-02-15",
                        "reason": "CP3 concurrency pool",
                    }
                ),
                str(uuid.uuid4()),
            ),
        )
        conn.commit()
        return terminal["sewing_terminal_event_id"], pool["pool_id"]


def race(pool_id: str, operations: list[tuple[str, str, tuple]], expected_successes: int):
    barrier = threading.Barrier(len(operations))
    results: list[dict] = []
    lock = threading.Lock()

    def worker(label: str, sql: str, params: tuple):
        started = time.monotonic()
        try:
            with connect() as conn:
                session_identity(conn)
                barrier.wait(timeout=10)
                value = call_json(conn, sql, params)
                conn.commit()
                item = {"label": label, "status": "PASS", "value": value, "seconds": time.monotonic() - started}
        except Exception as exc:
            item = {
                "label": label,
                "status": "REJECTED",
                "sqlstate": getattr(exc, "sqlstate", None),
                "error": str(exc).splitlines()[0],
                "seconds": time.monotonic() - started,
            }
        with lock:
            results.append(item)

    threads = [threading.Thread(target=worker, args=operation, daemon=True) for operation in operations]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=70)
    if any(thread.is_alive() for thread in threads):
        raise RuntimeError("concurrency worker did not terminate")
    successes = sum(item["status"] == "PASS" for item in results)
    if successes != expected_successes:
        raise RuntimeError(f"race expected {expected_successes} success(es), observed {successes}: {results}")
    return sorted(results, key=lambda item: item["label"])


def pool_state(pool_id: str):
    with connect() as conn:
        row = conn.execute(
            "select status,row_version,post_journal_entry_id,cancellation_journal_entry_id from erp.attendance_hpp_pools where id=%s",
            (pool_id,),
        ).fetchone()
        return dict(row)


def cleanup(pool_ids: list[str]):
    with connect() as conn:
        session_identity(conn)
        # Capture all candidate journals before deleting pool foreign keys.
        journal_ids = [
            row["id"]
            for row in conn.execute(
                """
                with recursive target(id) as (
                  select id from erp.journal_entries
                  where source_id=any(%s::uuid[]) or source_id=%s::uuid
                  union
                  select je.id from erp.journal_entries je join target t on je.reversal_of_id=t.id
                ) select distinct id from target
                """,
                (pool_ids, PAYROLL_ID),
            ).fetchall()
        ]
        conn.execute("delete from erp.attendance_hpp_journal_line_links where pool_id=any(%s::uuid[])", (pool_ids,))
        conn.execute("delete from erp.attendance_hpp_pool_allocations where pool_id=any(%s::uuid[])", (pool_ids,))
        conn.execute("delete from erp.attendance_hpp_pool_sources where pool_id=any(%s::uuid[])", (pool_ids,))
        conn.execute("delete from erp.attendance_hpp_pools where id=any(%s::uuid[])", (pool_ids,))
        conn.execute("delete from erp.sewing_terminal_events where contractor_id=%s", (CONTRACTOR_ID,))
        conn.execute("delete from erp.contractor_hpp_policy_versions where contractor_id=%s", (CONTRACTOR_ID,))
        if journal_ids:
            conn.execute("delete from erp.journal_lines where journal_entry_id=any(%s::uuid[])", (journal_ids,))
            conn.execute("delete from erp.journal_entries where id=any(%s::uuid[]) and reversal_of_id is not null", (journal_ids,))
            conn.execute("delete from erp.journal_entries where id=any(%s::uuid[])", (journal_ids,))
        conn.execute("delete from erp.payroll_attendance_items where payroll_id=%s", (PAYROLL_ID,))
        conn.execute("delete from erp.payroll_settlements where id=%s", (PAYROLL_ID,))
        conn.execute("delete from erp.work_completion_lines where completion_id=%s", (WORK_ID,))
        conn.execute("delete from erp.work_completion_events where id=%s", (WORK_ID,))
        conn.execute("delete from erp.po_work_component_snapshots where id=%s", (SNAPSHOT_ID,))
        conn.execute("delete from erp.work_components where id=%s", (COMPONENT_ID,))
        conn.execute("delete from erp.cutting_groups where id=%s", (GROUP_ID,))
        conn.execute("delete from erp.production_orders where id=%s", (PO_ID,))
        conn.execute("delete from erp.audit_logs where changed_by=%s or entity_id=any(%s::uuid[])", (USER_ID, pool_ids))
        conn.execute("delete from erp.idempotency_requests where actor_key like %s", (f"%{USER_ID}%",))
        conn.execute("delete from erp.contractors where id=%s", (CONTRACTOR_ID,))
        conn.execute("delete from erp.app_users where id=%s", (USER_ID,))
        conn.commit()

    with connect() as conn:
        residue = conn.execute(
            """
            select
              (select count(*) from erp.contractors where id=%s) contractor_rows,
              (select count(*) from erp.attendance_hpp_pools where id=any(%s::uuid[])) pool_rows,
              (select count(*) from erp.sewing_terminal_events where contractor_id=%s) sewing_rows,
              (select count(*) from erp.idempotency_requests where actor_key like %s) idempotency_rows
            """,
            (CONTRACTOR_ID, pool_ids, CONTRACTOR_ID, f"%{USER_ID}%"),
        ).fetchone()
        if any(residue.values()):
            raise RuntimeError(f"concurrency cleanup residue: {dict(residue)}")
        return dict(residue)


def main():
    if os.environ.get("CP3_ALLOW_DESTRUCTIVE_LOCAL") != "YES":
        raise SystemExit("Refusing to run: set CP3_ALLOW_DESTRUCTIVE_LOCAL=YES only on a disposable local database")

    terminal_id, pool_id = setup_fixture()
    pool_ids = [pool_id]
    report: dict = {"status": "FAIL", "terminal_event_id": terminal_id, "pool_ids": pool_ids}
    try:
        activate_race = race(
            pool_id,
            [
                (
                    "activate-A",
                    "select erp.activate_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,1)",
                    (pool_id, "CP3 concurrent activate A", str(uuid.uuid4())),
                ),
                (
                    "activate-B",
                    "select erp.activate_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,1)",
                    (pool_id, "CP3 concurrent activate B", str(uuid.uuid4())),
                ),
            ],
            1,
        )
        after_activate = pool_state(pool_id)
        if after_activate["status"] != "ACTIVE" or after_activate["row_version"] != 2:
            raise RuntimeError(f"activation race ended in invalid state: {after_activate}")

        cancel_race = race(
            pool_id,
            [
                (
                    "cancel-A",
                    "select erp.cancel_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,2)",
                    (pool_id, "CP3 concurrent cancel A", str(uuid.uuid4())),
                ),
                (
                    "cancel-B",
                    "select erp.cancel_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,2)",
                    (pool_id, "CP3 concurrent cancel B", str(uuid.uuid4())),
                ),
            ],
            1,
        )
        after_cancel = pool_state(pool_id)
        if after_cancel["status"] != "CANCELLED" or after_cancel["row_version"] != 3:
            raise RuntimeError(f"cancel race ended in invalid state: {after_cancel}")

        with connect() as conn:
            session_identity(conn)
            replacement = call_json(
                conn,
                "select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s::uuid)",
                (
                    json.dumps(
                        {
                            "period_start": "2026-02-01",
                            "period_end": "2026-02-15",
                            "reason": "CP3 activate-vs-cancel race replacement",
                            "correction_of_pool_id": pool_id,
                        }
                    ),
                    str(uuid.uuid4()),
                ),
            )
            conn.commit()
        replacement_id = replacement["pool_id"]
        pool_ids.append(replacement_id)

        activate_cancel_race = race(
            replacement_id,
            [
                (
                    "activate",
                    "select erp.activate_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,1)",
                    (replacement_id, "CP3 activate-vs-cancel activate", str(uuid.uuid4())),
                ),
                (
                    "cancel",
                    "select erp.cancel_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,1)",
                    (replacement_id, "CP3 activate-vs-cancel cancel", str(uuid.uuid4())),
                ),
            ],
            1,
        )
        after_mixed = pool_state(replacement_id)
        if after_mixed["status"] != "ACTIVE" or after_mixed["row_version"] != 2:
            raise RuntimeError(f"activate-vs-cancel race ended in invalid state: {after_mixed}")
        with connect() as conn:
            session_identity(conn)
            call_json(
                conn,
                "select erp.cancel_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,2)",
                (replacement_id, "CP3 final cleanup cancel", str(uuid.uuid4())),
            )
            conn.commit()

        with connect() as conn:
            reconciliation = conn.execute(
                """
                select
                  count(*) filter(where status='ACTIVE') active_pools,
                  count(*) filter(where status='CANCELLED') cancelled_pools,
                  coalesce(sum(case when status='CANCELLED' and cancellation_journal_entry_id is not null then 1 else 0 end),0) reversal_links,
                  (select count(*) from erp.journal_entries where source_type='ATTENDANCE_HPP_POOL' and source_id=any(%s::uuid[])) pool_journals,
                  (select count(*) from erp.journal_entries where reversal_of_id in (select post_journal_entry_id from erp.attendance_hpp_pools where id=any(%s::uuid[]))) reversal_journals
                from erp.attendance_hpp_pools where id=any(%s::uuid[])
                """,
                (pool_ids, pool_ids, pool_ids),
            ).fetchone()
            reconciliation = dict(reconciliation)
        if reconciliation["active_pools"] != 0 or reconciliation["cancelled_pools"] != 2 or reconciliation["reversal_links"] != 2 or reconciliation["pool_journals"] != 2 or reconciliation["reversal_journals"] != 2:
            raise RuntimeError(f"journal/state reconciliation failed: {reconciliation}")

        report.update(
            {
                "status": "PASS",
                "activate_two_session": activate_race,
                "cancel_two_session": cancel_race,
                "activate_vs_cancel": activate_cancel_race,
                "states": {
                    "after_activate": after_activate,
                    "after_cancel": after_cancel,
                    "after_activate_vs_cancel": after_mixed,
                },
                "reconciliation": reconciliation,
            }
        )
    finally:
        report["cleanup"] = cleanup(pool_ids)
        REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")

    if report["status"] != "PASS":
        raise SystemExit(1)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
