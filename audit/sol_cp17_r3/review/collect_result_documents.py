"""Read already-collected result documents; never imports or executes product/test code.

This is an evidence index, not a new probe and not an acceptance oracle. Repeated
IDs in different suites remain execution occurrences; smoke and prior attempts
are separate. Raw result references/hashes permit review of every indexed row.
"""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "ci_receipts" / "sol_artifacts"
PIN = "b53b5acdf260b03ebac3474e9ae837fcef6f6eb1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def case_rows(node):
    if isinstance(node, dict) and node and all(isinstance(v, dict) and "status" in v for v in node.values()):
        return list(node.items())
    if isinstance(node, list) and node and all(isinstance(v, dict) and "status" in v for v in node):
        return [(str(v.get("id", v.get("case_id", v.get("case", "UNKNOWN")))), v) for v in node]
    return None


def groups(node, path=""):
    if not isinstance(node, dict):
        return
    consumed = set()
    for name in ("cases", "races"):
        rows = case_rows(node.get(name))
        if rows is not None:
            yield path or "/", node, rows
            consumed.add(name)
    for name, value in node.items():
        if name not in consumed and isinstance(value, dict):
            yield from groups(value, path + "/" + name)


def counters(rows):
    return dict(collections.Counter(row["status"] for row in rows))


def main():
    summaries, ledger, issues, identities, file_count = [], [], [], [], 0
    seen_reports, duplicate_reports = {}, []
    register=json.loads((ROOT/"RUN_REGISTER.json").read_text())
    diagnostic_run_ids={r["run_id"]for r in register["runs"]if "diagnos" in r["run_name"].lower()}
    for receipt_path in sorted(ARTIFACTS.glob("*/DOWNLOAD_RECEIPT.json")):
        receipt = json.loads(receipt_path.read_text())
        folder = receipt_path.parent / "files"
        for entry in receipt["selected_files"]:
            p = folder / entry["path"]
            file_count += 1
            if not p.is_file() or sha(p) != entry["sha256"]:
                issues.append(dict(kind="EXTRACTED_FILE_HASH_MISMATCH", artifact=receipt["artifact_id"], file=entry["path"]))
        for p in sorted(folder.rglob("*.json")):
            if p.name in ("IDENTITY.json", "SOL_RUN_IDENTITY.json"):
                x = json.loads(p.read_text())
                checks = x.get("checkouts", [])
                bad = [c for c in checks if c.get("candidate_exact") and c.get("head") != PIN]
                identities.append(dict(artifact_id=receipt["artifact_id"], run_id=receipt["run_id"],
                    path=str(p.relative_to(ROOT)), sha256=sha(p), candidate_sha=x.get("candidate_sha"),
                    workflow_sha=x.get("workflow_sha"), checkouts=len(checks), candidate_mismatch=x.get("candidate_sha") != PIN,
                    checkout_mismatch=bool(bad)))
                continue
            if not p.name.startswith("CP7"):
                continue
            x = json.loads(p.read_text())
            if not isinstance(x, dict) or not ("cp6_restored" in x or "expected_case_count" in x):
                continue
            semantic_sha = hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            report_key = (rc_run := receipt["run_id"], semantic_sha)
            if report_key in seen_reports:
                duplicate_reports.append(dict(run_id=rc_run, artifact_id=receipt["artifact_id"],
                    path=str(p.relative_to(ROOT)), sha256=sha(p), semantic_sha256=semantic_sha,
                    alias_of=seen_reports[report_key], counted_again=False))
                continue
            seen_reports[report_key] = str(p.relative_to(ROOT))
            summary = dict(run_id=receipt["run_id"], artifact_id=receipt["artifact_id"], report=p.name,
                path=str(p.relative_to(ROOT)), sha256=sha(p), status=x.get("status"),
                expected_case_count=x.get("expected_case_count"), observed_case_count=x.get("observed_case_count"),
                expected_smoke_count=x.get("expected_smoke_count"), groups=[],
                restore=x.get("cp6_restored"), restore_components=x.get("restore_components"),
                advisor_gate=x.get("advisor_gate"), summary_only=False)
            for path, node, rows in groups(x):
                history = "business_day_first_attempt" in path
                smoke = any("smoke" in part for part in path.split("/"))
                legacy_diagnostic="/runtime_diagnostics/" in path
                source_admission = path.startswith("/source_admission") and x.get("source_admission_required_case_credit") == 0
                category = "FIRST_ATTEMPT" if history else "AUXILIARY_SMOKE" if smoke else "SOURCE_ADMISSION_NO_PRODUCT_CREDIT" if source_admission else "DIAGNOSTIC_LEGACY" if legacy_diagnostic else "DIAGNOSTIC_ONLY_RUN" if receipt["run_id"] in diagnostic_run_ids else "CANONICAL_DOCUMENT_ROW"
                ids = [i for i, _ in rows]
                counts = dict(collections.Counter(c.get("status") for _, c in rows))
                plan = x.get("required_case_ids", {}).get(path[1:]) if path.count("/") == 1 else None
                plan_source = "TOP_REQUIRED_CASE_IDS" if plan is not None else "GROUP_PLANNED_IDS"
                if plan is None:
                    plan = node.get("planned_case_ids", node.get("planned_race_ids", node.get("planned")))
                errors = []
                if len(ids) != len(set(ids)): errors.append("DUPLICATE_ID")
                if plan is not None and set(plan) != set(ids): errors.append("PLANNED_IDS_DIFFER")
                if isinstance(node.get("counts"), dict) and node["counts"] != counts: errors.append("COUNTS_DIFFER")
                if node.get("missing"): errors.append("MISSING_IDS")
                for key in ("complete_boundary_restored", "public_schema_unchanged"):
                    if node.get(key) is False: errors.append(key.upper())
                if node.get("database_remaining"): errors.append("DATABASE_REMAINING")
                if node.get("cleanup_failures"): errors.append("CLEANUP_FAILURES")
                summary["groups"].append(dict(path=path, category=category, rows=len(rows), counts=counts,
                    planned_ids_available=plan is not None, plan_source=plan_source,
                    errors=errors, business_day_retried=node.get("business_day_retried", False)))
                for case_id, case in rows:
                    ledger.append(dict(run_id=receipt["run_id"], artifact_id=receipt["artifact_id"],
                        report=p.name, group=path, category=category,
                        internal_second_attempt=bool(node.get("business_day_retried")) and not history,
                        id=case_id, status=case.get("status"),
                        raw_case_sha256=hashlib.sha256(json.dumps(case, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                        business_day=case.get("business_day"), business_day_rollover=case.get("business_day_rollover", False),
                        status_before_rollover=case.get("status_before_rollover"),
                        error=case.get("error"), full_boundary_restored=case.get("full_boundary_restored"),
                        public_schema_unchanged=case.get("public_schema_unchanged"),
                        session_leaks=case.get("session_leaks"), harness_check_failed=case.get("harness_check_failed")))
            for category in ("CANONICAL_DOCUMENT_ROW", "AUXILIARY_SMOKE", "FIRST_ATTEMPT", "SOURCE_ADMISSION_NO_PRODUCT_CREDIT", "DIAGNOSTIC_LEGACY", "DIAGNOSTIC_ONLY_RUN"):
                rows = [r for r in ledger if r["artifact_id"] == receipt["artifact_id"] and r["report"] == p.name and r["category"] == category]
                summary[category.lower()] = dict(rows=len(rows), counts=counters(rows))
            n = summary["canonical_document_row"]["rows"]
            summary["summary_only"] = n == 0
            if x.get("expected_case_count") is not None and n != x["expected_case_count"]:
                summary["count_qualification"] = "DIAGNOSIS_ONLY_NO_PRODUCT_CASE_CREDIT" if receipt["run_id"] in diagnostic_run_ids else "CANONICAL_ROWS_DIFFER_FROM_TOP_LEVEL_EXPECTED"
            summaries.append(summary)
    canonical = [r for r in ledger if r["category"] == "CANONICAL_DOCUMENT_ROW"]
    first = [r for r in ledger if r["category"] == "FIRST_ATTEMPT"]
    unretried = [r for r in canonical if not r["internal_second_attempt"]]
    boundary_issues=[]
    for r in ledger:
        bad=[]
        for k in ("full_boundary_restored","public_schema_unchanged"):
            if r[k] is False: bad.append(k)
        if r["harness_check_failed"]: bad.append("harness_check_failed")
        leaks=r["session_leaks"]
        if isinstance(leaks,dict):
            if any(bool(v) for v in leaks.values()): bad.append("session_leaks")
        elif leaks: bad.append("session_leaks")
        if bad: boundary_issues.append(dict(run_id=r["run_id"],report=r["report"],group=r["group"],id=r["id"],issues=bad))
    out = dict(scope="DOCUMENT_REVIEW_OF_ALREADY_EXECUTED_OWN_CI_RESULTS_ONLY", candidate_sha=PIN,
        oracle_origin="WRITER_DECLARED_OR_RETAINED_INHERITED; EXECUTION_INDEPENDENT_SOL",
        full_audit_pass=False, new_probes_executed=False, reports=len(summaries),
        selected_files_hash_checked=file_count, file_hash_issues=issues, identities=identities,
        canonical_document_rows=len(canonical), canonical_status_counts=counters(canonical),
        canonical_unique_ids=len({r["id"] for r in canonical}),
        original_first_result_cohort_counts=counters(unretried + first),
        internal_second_attempt_counts=counters([r for r in canonical if r["internal_second_attempt"]]),
        cases_with_full_boundary_flag=sum(r["full_boundary_restored"] is not None for r in ledger),
        case_boundary_issues=boundary_issues,
        auxiliary_smoke_counts=counters([r for r in ledger if r["category"] == "AUXILIARY_SMOKE"]),
        source_admission_no_product_credit_counts=counters([r for r in ledger if r["category"] == "SOURCE_ADMISSION_NO_PRODUCT_CREDIT"]),
        legacy_diagnostic_counts=counters([r for r in ledger if r["category"] == "DIAGNOSTIC_LEGACY"]),
        diagnosis_only_run_counts=counters([r for r in ledger if r["category"] == "DIAGNOSTIC_ONLY_RUN"]),
        first_attempt_counts=counters([r for r in ledger if r["category"] == "FIRST_ATTEMPT"]),
        warnings=["Canonical means the final location in a raw document, not acceptance after an internal retry.",
            "Counts are execution occurrences, not unique independent oracles or an ERP completeness percentage.",
            "Summary-only rehearsals and job-only suites require separate narrative/log review.",
            "Archive digest was checked by mechanical collector; Sol rehashed extracted selected files."],
        duplicate_report_artifacts=duplicate_reports, summaries=summaries)
    (ROOT / "RESULT_DOCUMENT_REVIEW_PARTIAL.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    (ROOT / "CASE_LEDGER_PARTIAL.json").write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: out[k] for k in ("reports", "selected_files_hash_checked", "file_hash_issues", "canonical_document_rows", "canonical_status_counts", "canonical_unique_ids", "auxiliary_smoke_counts", "first_attempt_counts")}, ensure_ascii=False))
    print("IDENTITIES", len(identities), "MISMATCHES", len([i for i in identities if i["candidate_mismatch"] or i["checkout_mismatch"]]))
    for r in summaries:
        if r.get("count_qualification") or any(g["errors"] for g in r["groups"]):
            print("REVIEW", r["report"], r.get("count_qualification"), [(g["path"], g["errors"]) for g in r["groups"] if g["errors"]])


if __name__ == "__main__":
    main()
