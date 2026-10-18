"""Summarize already-read late-phase Originals, preserving scope and hashes."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = [
    (39146762696, 12144484681, "CP7_K3_CLEANUP.json"),
    (39146762696, 12144554903, "CP7_K4_RUNNER.json"),
    (39146762696, 12145483521, "CP7_K6_PROOF_RUNNER.json"),
    (39146762454, 12145686624, "CP7_F05_NATIVE_ATTENTION.json"),
    (39146763492, 12145703660, "CP7_F05_NATIVE_ATTENTION.json"),
]
reports = []
raws = {}
for run_id, artifact_id, filename in SPECS:
    path = ROOT / "ci_receipts/sol_artifacts" / str(artifact_id) / "files" / filename
    x = json.loads(path.read_text())
    raws[(run_id, filename)] = x
    groups = {}
    for g in ("source_admission", "native", "races", "http", "browser"):
        n = x.get(g)
        if not isinstance(n, dict):
            continue
        rows = n.get("cases", n.get("races", {}))
        plan = n.get("planned_case_ids", n.get("planned_race_ids"))
        assert plan is not None and set(plan) == set(rows) and len(plan) == len(rows)
        groups[g] = dict(rows=len(rows), counts=dict(collections.Counter(c["status"] for c in rows.values())),
                         required_ids_equal=True,
                         case_ids=list(rows), product_credit=0 if g == "source_admission" else len(rows),
                         boundary={k: n[k] for k in ("complete_boundary_restored", "database_remaining", "cleanup", "cleanup_failures", "auth_counts", "console_errors", "session_leaks") if k in n})
    counted = sum(v["product_credit"] for v in groups.values())
    assert counted == x["expected_case_count"] == x["observed_case_count"]
    reports.append(dict(run_id=run_id, artifact_id=artifact_id, path=str(path.relative_to(ROOT)),
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(), source_sha256=x["source_sha256"],
                        status=x["status"], expected_case_count=x["expected_case_count"], groups=groups,
                        restore=x["restore_components"], cp6_restored=x["cp6_restored"], advisor_gate=x["advisor_gate"],
                        explicit_scope_limits={k: v for k, v in x.items() if k.startswith("full_") or k == "schedule_installed"}))
k4 = raws[(39146762696, "CP7_K4_RUNNER.json")]
k6 = raws[(39146762696, "CP7_K6_PROOF_RUNNER.json")]
out = dict(scope="READ_ONLY_REVIEW_OF_EXISTING_LATE_PHASE_RESULTS", new_probes_executed=False,
           reports=reports,
           k4_observations=dict(
               page_closed=k4["native"]["cases"]["K4R_SERVER_FINISHES_WITHOUT_PAGE"],
               combined_page_server=k4["native"]["cases"]["K4R_PAGE_AND_SERVER_ONE_JOB"],
               cold_start=k4["races"]["races"]["K4R_RACE_COLD_START_TWO_TICKS"],
               authority=k4["native"]["cases"]["K4R_ACCESS_RECHECKED_EACH_UNIT"],
               limit=k4["native"]["cases"]["K4R_LIMIT_REQUIRED"],
               desktop=k4["browser"]["cases"]["K4R_BROWSER_DESKTOP_CLOSED_PAGE_FINISHES"],
               mobile=k4["browser"]["cases"]["K4R_BROWSER_MOBILE_CLOSED_PAGE_FINISHES"]),
           k6_observations=dict(
               first_pass=k6["native"]["cases"]["K6P_PASS_PROVES_FINISHED_HISTORY"],
               correction=k6["native"]["cases"]["K6P_CANCEL_CORRECT_BACKDATE_REPROVEN_BY_SERVER"],
               stopped_windows=k6["races"]["races"]["K6P_RACE_WINDOW_STOPPED_THEN_SKIPPED"]),
           qualification="Phase cases are evidence only for their declared synthetic/disposable scope. Parent P19 workflow is not terminal merely because these phases passed. pg_cron schedules were tested then removed, not installed for production. K3 replacement-write boundary is separately retained in BOUNDARY_REVIEW.json.")
(ROOT / "LATE_PHASE_RESULT_REVIEW.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print("late_phase_reports", len(reports), "counts", [r["expected_case_count"] for r in reports])
