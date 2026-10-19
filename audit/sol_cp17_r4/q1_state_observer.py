"""Audit-process-only observations of the pinned wait_recorded call.

The wrapper returns the original result unchanged. It never writes to PostgreSQL,
raises an assertion inside product cleanup, changes a budget or retries a call.
The separate qualification judges the saved observations after the case ends.
"""
from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
import time

ALLOWED_DATABASES = {"cp6_auditor_race", "cp6_auditor_browser"}
FIELDS = ("jobid", "runid", "job_pid", "database", "username", "status", "return_message", "start_time", "end_time")
QUERY = """select jobid,runid,job_pid,database,username,status,return_message,start_time,end_time
    from cron.job_run_details where jobid=any(%s) order by jobid,runid"""


def snapshot(cur, ids):
    return [dict(zip(FIELDS, row)) for row in cur.execute(QUERY, (list(ids),)).fetchall()]


@contextmanager
def observe(schedule, case_id, output, target_database):
    """Temporarily wrap the imported helper in this audit interpreter only."""
    original, captured = schedule.wait_recorded, []
    output = Path(output)

    def wrapped(cur, jobids, seconds=60):
        ids = list(jobids)
        row = {"case_id": case_id, "jobids": ids, "budget_seconds": seconds, "target_database": target_database,
               "observer_sql_read_only": True, "wait_result_unchanged": True}
        try:
            row["before"] = snapshot(cur, ids)
        except Exception as error:
            row["before_observer_error"] = str(error)
        started = time.monotonic()
        try:
            result = original(cur, ids, seconds=seconds)
        except Exception as error:
            row["wait_error"] = str(error)
            raise
        else:
            row["wait_result"] = result
            return result
        finally:
            row["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
            try:
                row["after"] = snapshot(cur, ids)
            except Exception as error:
                row["after_observer_error"] = str(error)
            try:
                row["schedule_jobs_remaining"] = schedule.installed(cur, target_database)
                row["remaining_schedule_job_count"] = len(row["schedule_jobs_remaining"])
            except Exception as error:
                row["schedule_observer_error"] = str(error)
            captured.append(row)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("a") as stream:
                stream.write(json.dumps(row, default=str) + "\n")

    schedule.wait_recorded = wrapped
    try:
        yield captured
    finally:
        schedule.wait_recorded = original


def parse_time(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def assess(row):
    """Frozen metadata expected, independent of the product's finished-only filter."""
    ids, rows = row.get("jobids", []), row.get("after", [])
    checks = {
        "wait_returned_true": row.get("wait_result") is True,
        "unchanged_60_second_budget": row.get("budget_seconds") == 60,
        "observer_complete": not any(k.endswith("_error") for k in row),
        "jobids_present_unique": bool(ids) and len(ids) == len(set(ids)),
        "records_present": bool(rows),
        "every_job_recorded": bool(rows) and {r.get("jobid") for r in rows} == set(ids),
        "all_records_succeeded": bool(rows) and all(r.get("status") == "succeeded" for r in rows),
        "only_declared_disposable_databases": bool(rows) and all(r.get("database") == row.get("target_database") for r in rows),
        "unique_job_run_pairs": len(rows) == len({(r.get("jobid"), r.get("runid")) for r in rows}),
        "all_start_end_times_ordered": bool(rows),
        "target_database_declared_disposable": row.get("target_database") in ALLOWED_DATABASES,
        "schedule_observation_present": isinstance(row.get("schedule_jobs_remaining"), list) and type(row.get("remaining_schedule_job_count")) is int,
        "zero_schedules_remain": row.get("schedule_jobs_remaining") == [] and type(row.get("remaining_schedule_job_count")) is int and row["remaining_schedule_job_count"] == 0,
    }
    for record in rows:
        try:
            checks["all_start_end_times_ordered"] &= bool(record.get("start_time") and record.get("end_time")) and parse_time(record["end_time"]) >= parse_time(record["start_time"])
        except (ValueError, TypeError):
            checks["all_start_end_times_ordered"] = False
    return {"status": "PASS" if all(checks.values()) else "INCOMPLETE", "checks": checks,
            "record_count": len(rows), "new_business_case_credit": 0}


def copy_dropped(value):
    """Missing, Boolean and nonzero counts cannot stand in for a verified zero."""
    return type(value) is int and value == 0
