"""Once-only safe recost-state detector qualification, audit files only."""
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
import detector_case

OUT = PRODUCT / "cp6-proof/t3/SOL_R4_D01_DETECTOR.json"
MANIFEST = ROOT / "DETECTOR_PREEXECUTION_MANIFEST.json"


def verify(cur):
    return {"full_composition": installer.verify(cur), "cp17": cp17.verify(cur)}


def run():
    declaration = json.loads(MANIFEST.read_text())
    for path, digest in declaration["pinned_product_sources"].items():
        assert hashlib.sha256((PRODUCT / path).read_bytes()).hexdigest() == digest
    for path, digest in declaration["audit_tools"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    report = dict(label="SOL_R4_D01_DETECTOR", status="INCOMPLETE",
                  candidate_sha=declaration["candidate_sha"], candidate_tree=declaration["candidate_tree"],
                  manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                  expected_case_ids=[row["id"] for row in declaration["cases"]],
                  production_go=False, independent_acceptance=False, full_family_acceptance=False,
                  oracle_origin="SOL_DOCUMENT_LEVEL_ONE_MATERIAL_DRIFT_UNIT", fixture_origin="WRITER_ACCEPTED_NATIVE_RECEIPT_CUT_INVOICE_THEN_SOL_STATE_COUNTERFIXTURE",
                  detector_scope="One named detector and one violation unit only. Every other detector remains separately disposed; no global sensitivity claim.")
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
        # Direct once-only Native entry point; no business-day retry wrapper.
        report["native"] = native._strict_group_once("SOL_R4_D01_DETECTOR", detector_case.cases, verify)
        rows = report["native"].get("cases", {})
        report["counts"] = dict(Counter(row["status"] for row in rows.values()))
        report["observed_case_ids"] = list(rows)
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
        n = report.get("native", {})
        report["status"] = "PASS" if not report.get("error") and report.get("cp6_restored") is True and set(report.get("observed_case_ids", [])) == set(report["expected_case_ids"]) and report.get("counts") == {"PASS": 1} and n.get("status") == "PASS" and n.get("complete_boundary_restored") is True and n.get("missing") == [] and not n.get("error") else "INCOMPLETE"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(json.dumps({key: report.get(key) for key in ("label", "status", "counts", "cp6_restored", "error")}), flush=True)
    return {"status": report["status"], "production_go": False, "independent_acceptance": False, "full_family_acceptance": False}


if __name__ == "__main__":
    package._writer_runtime = lambda browser_mode=False: run()
    package.run("install")
