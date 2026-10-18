"""Carry sealed old dispositions forward with explicit current evidence bounds."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
SEAL = "841fce45c58b7c004d1dea2f293f57e4b1fa5ba0"
PIN = "b53b5acdf260b03ebac3474e9ae837fcef6f6eb1"
prior = json.loads(subprocess.check_output(["git", "show", SEAL + ":audit/sol_cp17_r2/RETEST_DISPOSITIONS.json"], cwd=REPO))
ledger = json.loads((ROOT / "CASE_LEDGER_PARTIAL.json").read_text())


def witness(prefix):
    return [{k: r[k] for k in ("run_id", "artifact_id", "group", "id", "status", "category")}
            for r in ledger if r["run_id"] == 39146521757 and r["id"].startswith(prefix)]


items = []
for row in prior["items"]:
    item = dict(id=row["id"], status=row["status"], retained_prior_seal=SEAL,
                retained_prior_candidate=prior["candidate_sha"], retained_prior_record=row,
                evidence_origin="RETAINED_SOL_R2_SEAL", retested_sha=PIN,
                qualification="Old independent proof stays bound to its seal; no claim that the held copies of old Sol probes ran on r3.")
    if row["id"] == "SOL-R1-001":
        item.update(current_supplement="CP17 cash/date guards and current writer/inherited correction suites executed independently by Sol; literal old 7 Native + 4 HTTP remain retained-only.",
                    auditor_bookkeeping="Stale INV-U05/INV-POL03, SKN-22/SKN-27 and B11/B13 cash FAIL text corrected; product cash finding remains CLOSED.")
    if row["id"] == "KNOWN-UI-MODE":
        item.update(status="SUPERSEDED_IMPLEMENTED_D16_1_WITH_BROWSER_BOUNDS",
                    qualification="Old D15-2 hidden-menu acceptance is historical. D16-1 now requires finished connected routes: source 46 CONNECTED + 1 NOTICE, Enteng 55 PASS; ordinary CP17 rollover remains incomplete.")
    if row["id"] in {"SOL-R1-004", "SOL-R1-005"}:
        item["current_supplement"] = "Run 39146762452 demo phone width 390: all 47 menu document widths 390. Physical devices/current connected loaded states not implied."
    if row["id"] == "SOL-002":
        item.update(current_supplement="Own BE T1 run 39146762579: 16 NO_ROUTE BEFORE retained, 16 PASS AFTER. Full F03 separately admits current 49-role/Native-delta stack; do not conflate the CP6 stage with all CP7 runtime.")
    if row["id"] == "SOL-003":
        item["qualification"] = "Prior diagnostic proof retained. Original historical first-AZ cause remains unknown and is not relabelled as an understood or current product failure."
    items.append(item)
items.extend([
    dict(id="SOL-R2-001", severity="S2", first_seen_sha="2e9d6a468c110684c278d585418eb404250d1150",
         retested_sha=PIN, status="CLOSED_TESTED_SCOPE", evidence_origin="INDEPENDENT_SOL_EXECUTION_OF_WRITER_DECLARED_CASES",
         oracle_origin="R3_WRITER_DECLARATION_REUSING_SOL_R2_BOUNDED_COUNTEREXAMPLE_AND_BOUNDARY_CONTROLS",
         fixture_origin="PUBLIC_SYNTHETIC_UNUSED_DAILY_PO_HEADERS_AND_MATERIAL_FIXTURE",
         before=dict(seal=SEAL, run_id=38934111700, job_id=117085146759, artifact_id=12059209949,
                     status="COUNTEREXAMPLE", number=1000, elapsed_seconds=3.003, deadline_seconds=3,
                     error="57014 statement timeout at truncated lpad search; original unchanged"),
         after=dict(run_id=39146521757, job_id=117731362035, artifact_id=12143844276,
                    actual_number="PO-261016-1000", elapsed_seconds=0.015, deadline_seconds=3,
                    native_cases=witness("CP17_R3_01"), race_cases=witness("CP17_RACE_R3_01")),
         cause_and_remedy="Minimum lpad width replaces fixed width; per-date lock, uniqueness and command atomics retained.",
         qualification="999/1000/1001/10000, UUID/refusal and two sessions witnessed. Not a global all-integer or factory SLA claim."),
    dict(id="KNOWN-R2-POOL-UI", retested_sha=PIN, status="CLOSED_UI_GAP_WITH_OPEN_ENTRYPOINT_BOUNDARY",
         evidence_origin="INDEPENDENT_SOL_EXECUTION_OF_WRITER_DECLARED_CASES",
         after=dict(run_id=39146521757, artifact_id=12143844276, native_cases=witness("CP17_R3_04"),
                    browser_cases=witness("CP17_BROWSER_R3_04")),
         qualification="Enteng and new facade lifecycle are witnessed. Ordinary browser rollover retained; four old public CP4 wrappers not independently reproduced and remain before-install boundary."),
    dict(id="KNOWN-RECEIPT-FIRST100", retested_sha=PIN, status="CLOSED_RUN_JOB_ENUMERATION_WITH_ANNOTATION_BOUNDARY",
         evidence_origin="INDEPENDENT_READ_ONLY_METADATA_ARITHMETIC_AND_SOURCE_REVIEW",
         after="117 exact run IDs on two pages; 182 all-attempt job rows, 181 latest IDs match receipt; source paginates runs/jobs/annotations.",
         evidence_files=["WRITER_RECEIPT_DOCUMENT_REVIEW.json", "WRITER_FAILURE_LOG_REVIEW.json"],
         qualification="Annotation endpoint unavailable HTTP400; no annotation enumeration or >100 jobs-in-one-run runtime claim.")
])
out = dict(report_state="FINAL_LIMITED_SCOPE_ASSESSMENT", candidate_sha=PIN,
           product_fixes_made=False, peer_r3_read=False, prior_seal=SEAL, items=items,
           new_product_findings=[], additional_independent_probes_executed=False,
           overall_audit_complete=False, production_go=False)
(ROOT / "RETEST_DISPOSITIONS.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print("dispositions", len(items), "new_product_findings", 0)
