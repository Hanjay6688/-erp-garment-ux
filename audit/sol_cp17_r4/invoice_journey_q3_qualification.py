"""Once-only declared B5/B6 ordinary browser continuation, audit files only."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parent
PRODUCT = ROOT.parents[2] / "auditor"
sys.path.insert(0, str(PRODUCT / "scripts"))
import psycopg
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
import cp6_t3_package_run as package
import cp7_cp17_fix_probe as cp17
import cp7_p09_procurement_probe as p09
import cp7_p21_full_rehearsal_probe as installer
import cp7_restore_state as restore_state

OUT = PRODUCT / "cp6-proof/t3/SOL_R4_INVOICE_JOURNEY_Q3.json"
MANIFEST = ROOT / "INVOICE_JOURNEY_Q3_PREEXECUTION_MANIFEST.json"


def verify(cur):
    return {"full_composition": installer.verify(cur), "cp17": cp17.verify(cur)}


def run():
    declaration = json.loads(MANIFEST.read_text())
    for path, digest in declaration["pinned_product_sources"].items():
        assert hashlib.sha256((PRODUCT / path).read_bytes()).hexdigest() == digest
    for path, digest in declaration["audit_tools"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    report = dict(label="SOL_R4_INVOICE_JOURNEY_Q3", status="INCOMPLETE",
                  candidate_sha=declaration["candidate_sha"], candidate_tree=declaration["candidate_tree"],
                  manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                  expected_case_ids=[row["id"] for row in declaration["cases"]],
                  production_go=False, independent_acceptance=False, full_family_acceptance=False,
                  oracle_origin="SOL_CONTRACT_LITERAL_ARITHMETIC_AND_LINEAGE", fixture_origin="WRITER_NATIVE_START_ONLY_THEN_SOL_UI_CONTINUATION",
                  claim_rewash_browser_scope="Ordinary3 required-reason refill per inverse; claim1 same form-state repair and read-only DOM/console/workspace diagnostics; Q2 expected retained; free rewash PASS excluded",
                  qualification_version="Q3_GENUINE_FORM_STATE_REPAIR_AND_UNRESOLVED_CLAIM_DIAGNOSTICS",
                  original_runs=[39193178808, 39193738642, 39195171465])
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
        # Deliberately bypass run_browser's business-day retry wrapper.
        browser = report["browser"] = modes._run_browser_once(ROOT / "invoice_journey_q3_browser.mjs", verify, "sol_r4_invoice_journey_q3")
        rows = browser.get("cases", {})
        report["counts"] = dict(Counter(row["status"] for row in rows.values()))
        report["observed_case_ids"] = list(rows)
        expected_signatures = declaration["expected_signatures"]
        report["each_literal_signature_matches_declared_branch"] = bool(rows) and all(row.get("signature") == expected_signatures.get(cid) for cid, row in rows.items())
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
        b = report.get("browser", {})
        report["status"] = "PASS" if not report.get("error") and report.get("cp6_restored") is True and set(report.get("observed_case_ids", [])) == set(report["expected_case_ids"]) and report.get("counts") == {"PASS": 4} and report.get("each_literal_signature_matches_declared_branch") is True and type(b.get("database_remaining")) is int and b.get("database_remaining") == 0 and b.get("status") == "RUN_COMPLETE" and b.get("host_status") == "RUN_COMPLETE" and type(b.get("host_exit")) is int and b.get("host_exit") == 0 and type(b.get("console_errors")) is int and b.get("console_errors") == 0 and b.get("session_leaks") == [] and b.get("cleanup_failures") is False and b.get("auth_counts", {}).get("restored") is True and not b.get("error") else "INCOMPLETE"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(json.dumps({key: report.get(key) for key in ("label", "status", "counts", "cp6_restored", "error")}), flush=True)
    return {"status": report["status"], "production_go": False, "independent_acceptance": False, "full_family_acceptance": False}


if __name__ == "__main__":
    package._writer_runtime = lambda browser_mode=False: run()
    package.run("install")
