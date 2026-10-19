"""Conditional metadata-only qualification of four existing K4/K6 cases.

Business fixtures, operations, oracles and budgets are the pinned writer sources.
No retry wrapper is used. These four IDs add no new business or race coverage.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import traceback
from urllib.parse import urlparse, urlunparse

ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT.parents[2] / "auditor"
sys.path.insert(0, str(PRODUCT / "scripts"))
import psycopg
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
import cp7_cp17_fix_probe as cp17
import cp7_k4_runner_cases as k4
import cp7_k6_proof_runner_cases as k6
import cp7_p09_procurement_probe as p09
import cp7_p21_full_rehearsal_probe as installer
import cp7_restore_state as restore_state
import cp7_schedule as schedule
from q1_state_observer import assess, copy_dropped, observe

OUTDIR = PRODUCT / "cp6-proof/t3"
OUT = OUTDIR / "SOL_R4_Q1_STATE_QUALIFICATION.json"
MANIFEST = ROOT / "Q1_STATE_PREEXECUTION_MANIFEST.json"


def verify(cur):
    return {"full_composition": installer.verify(cur), "cp17": cp17.verify(cur)}


def cron_cleanup_state(url):
    target = urlparse(url)
    assert target.hostname in ("localhost", "127.0.0.1") and target.path in ("/cp6_auditor_race", "/cp6_auditor_browser")
    cron_url = urlunparse(target._replace(path="/postgres"))
    with psycopg.connect(cron_url, autocommit=True) as conn, conn.cursor() as cur:
        return schedule.installed(cur, target.path.lstrip("/"))


def qualified_row(case_id, original_id, original_result, captured):
    assessments = [assess(row) for row in captured]
    ok = original_result.get("status") == "PASS" and len(captured) == 1 and all(r["status"] == "PASS" for r in assessments)
    return {"status": "PASS" if ok else "INCOMPLETE", "case_id": case_id,
            "original_case_id": original_id, "original_result": original_result,
            "wait_observations": captured, "metadata_assessments": assessments,
            "new_business_case_credit": 0, "new_race_credit": 0}


def server_group(declaration):
    planned = [row for row in declaration["cases"] if row["mode"] == "SERVER"]
    report = {"status": "INCOMPLETE", "cases": {}, "planned_case_ids": [row["id"] for row in planned]}
    try:
        url = modes.copy_db(modes.RACE_DB)
        setup = modes.setup_copy(url, verify, True)
        tools = modes.RaceTools(url, setup["today"])

        def run_one(index, case_id, operation):
            if index:
                modes.copy_db(modes.RACE_DB)
                modes.setup_copy(url, verify, True)
            row = operation()
            row["schedules_remaining"] = cron_cleanup_state(url)
            if row["schedules_remaining"]:
                row["status"] = "INCOMPLETE"
            return row

        def operation(spec):
            module = k4 if spec["original_case_id"].startswith("K4") else k6
            operations = dict(module.races(tools, setup["today"]))
            assert spec["original_case_id"] in operations
            with observe(schedule, spec["id"], OUTDIR / (spec["id"] + ".jsonl"), modes.RACE_DB) as captured:
                result = operations[spec["original_case_id"]]()
            return qualified_row(spec["id"], spec["original_case_id"], result, captured)

        cases = [(spec["id"], lambda spec=spec: operation(spec)) for spec in planned]
        report["cases"], refusal = modes.strict_rows("SOL_R4_Q1_SERVER_METADATA", cases, run_one, modes.RACE_DB, today=setup["today"])
        if refusal:
            report.update(refusal)
    except Exception as error:
        report.update(error=str(error), traceback=traceback.format_exc())
    finally:
        report["database_remaining"] = modes.drop_db(modes.RACE_DB)
    for row in report["cases"].values():
        row["copy_dropped"] = copy_dropped(report["database_remaining"])
        row["copy_drop_evidence"] = "Same declared database name is replaced between cases and final pg_database count is recorded after strict session checks."
        if not row["copy_dropped"]:
            row["status"] = "INCOMPLETE"
    report["status"] = "PASS" if not report.get("error") and report["database_remaining"] == 0 and set(report["cases"]) == set(report["planned_case_ids"]) and all(r["status"] == "PASS" for r in report["cases"].values()) else "INCOMPLETE"
    return report


def browser_group(declaration):
    # Direct once-only entry point: original business-day retry wrapper is not used.
    business = modes._run_browser_once(ROOT / "q1_k4_runner_browser.mjs", verify, "sol_r4_q1_metadata")
    report = {"status": "INCOMPLETE", "original_business_group": business, "cases": {}}
    for spec in (row for row in declaration["cases"] if row["mode"].startswith("BROWSER")):
        path = OUTDIR / (spec["id"] + ".jsonl")
        captured = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        original_result = business.get("cases", {}).get(spec["original_case_id"], {"status": "INCOMPLETE", "error": "ORIGINAL_CASE_MISSING"})
        row = qualified_row(spec["id"], spec["original_case_id"], original_result, captured)
        row["database_remaining"] = business.get("database_remaining")
        row["copy_dropped"] = copy_dropped(row["database_remaining"])
        row["remaining_schedule_job_count"] = captured[0].get("remaining_schedule_job_count") if len(captured) == 1 else None
        if not row["copy_dropped"] or business.get("cleanup_failures") is not False or business.get("error") or business.get("auth_counts", {}).get("restored") is not True:
            row["status"] = "INCOMPLETE"
        report["cases"][spec["id"]] = row
    report["status"] = "PASS" if len(report["cases"]) == 2 and all(r["status"] == "PASS" for r in report["cases"].values()) else "INCOMPLETE"
    return report


def run():
    declaration = json.loads(MANIFEST.read_text())
    need = json.loads((ROOT / "Q1_QUALIFICATION_NEED.json").read_text())
    assert need["own_original_reviewed"] and need["metadata_missing"] and need["initial_run_id"] == int(declaration["initial_own_run"])
    assert len(declaration["cases"]) == 4 and len({row["id"] for row in declaration["cases"]}) == 4
    for path, digest in declaration["frozen_product_sources"].items():
        assert hashlib.sha256((PRODUCT / path).read_bytes()).hexdigest() == digest, ("SOL_Q1_PINNED_SOURCE_DIFFERS", path)
    report = {"label": "SOL_R4_Q1_STATE_QUALIFICATION", "status": "INCOMPLETE",
              "candidate_sha": declaration["candidate_sha"], "candidate_tree": declaration["candidate_tree"],
              "declaration_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
              "need_sha256": hashlib.sha256((ROOT / "Q1_QUALIFICATION_NEED.json").read_bytes()).hexdigest(),
              "expected_case_ids": [row["id"] for row in declaration["cases"]], "new_business_case_credit": 0,
              "new_race_credit": 0, "production_go": False, "full_family_acceptance": False,
              "independent_acceptance": False, "original_first_results_preserved": True}
    installed = False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
            p09.wip.policy.bf.verified(cur)
            before = restore_state.capture(cur, package.boundary.snapshot, native.public_state, p09.functions)
            conn.rollback()
            originals, installation = installer.install(cur)
            conn.commit()
            installed = True
            report["installation"] = installation
            report["installed_runtime"] = verify(cur)
            conn.rollback()
        report["server"] = server_group(declaration)
        report["browser"] = browser_group(declaration)
    except Exception as error:
        report.update(error=str(error), traceback=traceback.format_exc())
    finally:
        if installed:
            with psycopg.connect(package.boundary.ADMIN) as conn, conn.cursor() as cur:
                installer.uninstall(cur, originals)
                conn.commit()
                report["cp6_restored"] = restore_state.prove(cur, before, package.boundary.snapshot, native.public_state, p09.functions, report)
                conn.rollback()
                p09.wip.policy.bf.verified(cur)
                conn.rollback()
                report["advisor_scope"] = "No additional advisor run claimed by this metadata-only qualification; full baseline/catalog restoration and existing product-case checks remain required."
        cases = {key: row for group in ("server", "browser") for key, row in report.get(group, {}).get("cases", {}).items()}
        report["counts"] = dict(Counter(row["status"] for row in cases.values()))
        report["observed_case_ids"] = list(cases)
        report["status"] = "PASS" if not report.get("error") and report.get("cp6_restored") and all(report.get(g, {}).get("status") == "PASS" for g in ("server", "browser")) and set(cases) == set(report["expected_case_ids"]) and report["counts"] == {"PASS": 4} else "INCOMPLETE"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(json.dumps({k: report.get(k) for k in ("label", "status", "counts", "cp6_restored", "error")}), flush=True)
    return {"status": report["status"], "production_go": False, "independent_acceptance": False, "full_family_acceptance": False}


if __name__ == "__main__":
    package._writer_runtime = lambda browser_mode=False: run()
    package.run("install")
