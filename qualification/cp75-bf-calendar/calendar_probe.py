"""Record a cold BF's Realtime calendar against two independently sourced UTC dates."""
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SOURCE_RUN = 44800849536
SOURCE_JOB = 136512294676
SOURCE_HEAD = "80aedab32c4398110d3644989ba33f3fbe87b9cf"
BF_ARCHIVE = "e9cfc68200b9a8521110eccfe6e98816b1f10939bdf367be521d309286634396"
BF_CATALOGUE = "b036261ee8902fc3be5307d54cf2b021dd2e2b419e24100655a7a338b70bad0a"


def source_window(job):
    if (job["id"], job["run_id"], job["head_sha"], job["conclusion"]) != (
        SOURCE_JOB, SOURCE_RUN, SOURCE_HEAD, "success"
    ):
        raise ValueError("Unexpected original BF job")
    boot, = (s for s in job["steps"] if s["name"] == "Start disposable database")
    start, end = (datetime.fromisoformat(boot[k]).astimezone(timezone.utc)
                  for k in ("started_at", "completed_at"))
    if boot["conclusion"] != "success" or end < start or start.date() != end.date():
        raise ValueError("Source startup cannot be attributed to one UTC day")
    return {"job": SOURCE_JOB, "run": SOURCE_RUN, "head": SOURCE_HEAD,
            "start_step_from": boot["started_at"], "start_step_to": boot["completed_at"],
            "utc_day": start.date().isoformat()}


def days(anchor):
    return [anchor + timedelta(days=i) for i in range(-1, 4)]


def names(anchor):
    return ["messages_" + d.strftime("%Y_%m_%d") for d in days(anchor)]


def evaluate(observed, source):
    anchor = date.fromisoformat(source["utc_day"])
    live = date.fromisoformat(observed["postmaster_day_utc"])
    expected = names(anchor)
    children = observed["children"]
    actual = [child["name"] for child in children]
    typed = all(ch["schema"] == "realtime" and ch["kind"] == "r" and ch["is_partition"] is True
                for ch in children)
    expected_bounds = [f"FOR VALUES FROM ('{d} 00:00:00') TO ('{d + timedelta(days=1)} 00:00:00')"
                       for d in days(anchor)]
    source_match = (actual == expected and typed and not observed["detached_daily_tables"]
                    and [ch["bound"] for ch in children] == expected_bounds)
    return {"source_boot": source, "postgresql": observed,
            "expected_from_restored_postmaster": names(live),
            "expected_from_original_boot": expected, "actual_attached": actual,
            "matches_restored_postmaster_names": actual == names(live),
            "matches_source_names_and_bounds": source_match,
            "disposable": True, "production_go": False}


def validate_opening(receipt, container):
    identity = (receipt["origin_run"], receipt["sha256"], receipt["catalogue"], receipt["container"],
                receipt["scheduler_enabled"], receipt["disposable"], receipt["production_go"])
    if identity != (SOURCE_RUN, BF_ARCHIVE, BF_CATALOGUE, container, False, True, False):
        raise ValueError("The connection is not the admitted original BF copy")


def confirmed_factory_day(folder, run, head):
    """Read the same job's independent source clock and its read-only original-BF observation."""
    result = json.loads((folder / "bf-calendar.json").read_text())
    opening = json.loads((folder / "clean-opened.json").read_text())
    validate_opening(opening, "supabase_db_cp5-local")
    if (result["probe_run"], result["probe_head"], result["original"]) != (run, head, opening):
        raise ValueError("Calendar receipt does not belong to this original BF opening")
    source = source_window(json.loads((folder / "source-start-job.json").read_text()))
    observed = result["postgresql"]
    replay = evaluate(observed, source)
    started = datetime.fromisoformat(observed["postmaster_started_utc"])
    if (started.utcoffset() != timedelta(0) or started.date().isoformat() != observed["postmaster_day_utc"]):
        raise ValueError("The PostgreSQL startup timestamp and UTC day disagree")
    if observed["database"] != "cp6_rollback" or observed["read_only"] != "on":
        raise ValueError("Original BF observation must be a read-only query on cp6_rollback")
    if not replay["matches_source_names_and_bounds"] or any(result[k] != v for k, v in replay.items()):
        raise ValueError("The original BF source window did not match the attached partitions")
    return date.fromisoformat(source["utc_day"])


def main():
    import live
    receipt = json.loads((live.RESULT / "clean-opened.json").read_text())
    container = ("supabase_db_cp5-local" if os.environ.get("CP75_FACTORY_ORIGINAL") == "1"
                 else "cp75-clean-" + os.environ["GITHUB_RUN_ID"])
    validate_opening(receipt, container)
    query = Path(__file__).with_name("observe.sql").read_text()
    observed = live.query(container, query)
    source_file = live.RESULT / "source-start-job.json"
    source = source_window(json.loads(source_file.read_text()))
    report = evaluate(observed, source)
    report["original"] = receipt
    report["probe_run"] = os.environ["GITHUB_RUN_ID"]
    report["probe_head"] = os.environ["GITHUB_SHA"]
    (live.RESULT / "bf-calendar.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True), flush=True)
    if observed["database"] != "cp6_rollback" or observed["read_only"] != "on":
        raise ValueError("Unexpected database or transaction mode")
    if not report["matches_source_names_and_bounds"]:
        raise ValueError("Original BF calendar differs from the source startup window")


if __name__ == "__main__":
    main()
