#!/usr/bin/env python3
from pathlib import Path

PATH = Path('scripts/cp3_concurrency_harness.py')
START = '        one(conn, "insert into erp.contractor_workers('
END = '        one(conn, "insert into erp.payroll_settlements('

REPLACEMENT = '''        roster = one(conn, "select erp.save_worker_roster_v1(%s::jsonb,%s::uuid,null)", (json.dumps({
            "contractor_id": ids["contractor"], "worker_code": f"W-{tag}",
            "worker_name": f"Worker {tag}", "job_description": "Sewing",
            "pay_scheme": "DAILY", "joined_at": "2026-01-01", "is_active": True,
            "initial_daily_rate": amount, "rate_effective_from": "2026-01-01",
            "reason": "CP3 authoritative concurrency roster"
        }), uid(f"{tag}:worker-roster")))
        roster = roster if isinstance(roster, dict) else json.loads(roster)
        ids["worker"] = str(roster["worker_id"])
        ids["rate"] = str(one(conn, "select erp.worker_daily_rate_version_id_at(%s::uuid,%s::date)", (ids["worker"], event_date)))
        policy = one(conn, "select erp.save_contractor_hpp_policy_v1(%s::jsonb,%s::uuid,null)", (json.dumps({
            "contractor_id": ids["contractor"], "effective_from": "2026-01-01",
            "attendance_required": True, "is_special": False, "change_reason": "CP3 concurrency policy"
        }), ids["policy_req"]))

        start_day = date.fromisoformat(start)
        end_day = date.fromisoformat(end)
        present_day = date.fromisoformat(event_date)
        attendance = []
        day = start_day
        while day <= end_day:
            present = day == present_day
            attendance.append({
                "worker_id": ids["worker"],
                "attendance_date": day.isoformat(),
                "status": "PRESENT" if present else "OFF",
                "paid_fraction": 1 if present else 0,
                "notes": "CP3 explicit concurrency attendance matrix",
            })
            day += timedelta(days=1)

        attendance_saved = one(conn, "select erp.save_attendance_period_v1(%s::jsonb,%s::uuid,null,false)", (json.dumps({
            "contractor_id": ids["contractor"], "period_number": f"ATT-{tag}",
            "period_start": start, "period_end": end, "pay_date": end,
            "reason": "CP3 authoritative concurrency attendance",
            "attendance": attendance,
        }), uid(f"{tag}:attendance-save")))
        attendance_saved = attendance_saved if isinstance(attendance_saved, dict) else json.loads(attendance_saved)
        ids["attendance_period"] = str(attendance_saved["period_id"])
        one(conn, "select erp.post_attendance_period_v1(%s::uuid,%s,%s::uuid,%s)", (
            ids["attendance_period"], "CP3 authoritative concurrency attendance post",
            uid(f"{tag}:attendance-post"), attendance_saved["row_version"]
        ))
        ids["attendance_record"] = str(one(conn, "select id from erp.attendance_records where attendance_period_id=%s::uuid and worker_id=%s::uuid and attendance_date=%s::date and record_lifecycle='POSTED'", (
            ids["attendance_period"], ids["worker"], event_date
        )))
'''


def main() -> None:
    text = PATH.read_text()

    # Insert imports first. Any textual edit before setup_period changes byte offsets,
    # so bootstrap anchors are intentionally resolved only after imports are final.
    if 'from datetime import date, timedelta\n' not in text:
        import_anchor = 'import uuid\n'
        if text.count(import_anchor) != 1:
            raise SystemExit('datetime import anchor is missing or ambiguous')
        text = text.replace(import_anchor, import_anchor + 'from datetime import date, timedelta\n', 1)

    if text.count(START) != 1:
        raise SystemExit('concurrency worker bootstrap anchor must appear exactly once')
    start = text.index(START)
    end = text.find(END, start)
    if end < 0:
        raise SystemExit('concurrency payroll boundary was not found after worker bootstrap')

    text = text[:start] + REPLACEMENT + text[end:]

    forbidden = (
        'insert into erp.worker_employment_periods',
        'insert into erp.worker_daily_rate_versions',
        'insert into erp.attendance_periods',
        'insert into erp.attendance_records',
    )
    for token in forbidden:
        if token in text:
            raise SystemExit(f'concurrency harness still bypasses authoritative history RPC: {token}')
    if text.count('erp.save_worker_roster_v1(') != 1:
        raise SystemExit('expected one authoritative roster bootstrap call')
    if text.count('erp.save_attendance_period_v1(') != 1:
        raise SystemExit('expected one authoritative attendance save template')
    if text.count('erp.post_attendance_period_v1(') != 1:
        raise SystemExit('expected one authoritative attendance post template')
    if 'def concurrent_calls(calls):' not in text or 'assert_exactly_one(results, "sewing capacity race")' not in text:
        raise SystemExit('concurrency race scenarios were unexpectedly changed or missing')

    PATH.write_text(text)


if __name__ == '__main__':
    main()
