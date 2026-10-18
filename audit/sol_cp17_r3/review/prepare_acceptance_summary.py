"""Separate raw document occurrences from the original-result acceptance cohort."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "CASE_LEDGER_PARTIAL.json"
ledger = json.loads(source.read_text())
canonical = [r for r in ledger if r["category"] == "CANONICAL_DOCUMENT_ROW"]
first = [r for r in ledger if r["category"] == "FIRST_ATTEMPT"]
second = [r for r in canonical if r["internal_second_attempt"]]
cohort = [r for r in canonical if not r["internal_second_attempt"]] + first


def counts(rows):
    return dict(collections.Counter(r["status"] for r in rows))


by_layer = {}
for row in cohort:
    layer = row["group"].split("/")[1] if row["group"].startswith("/") else row["group"]
    by_layer.setdefault(layer, []).append(row)
groups = []
for run_id, path in sorted({(r["run_id"], r["group"]) for r in second}):
    original = [r for r in first if r["run_id"] == run_id and r["group"] == path + "/business_day_first_attempt"]
    final = [r for r in second if r["run_id"] == run_id and r["group"] == path]
    assert {r["id"] for r in original} == {r["id"] for r in final} and len(original) == len(final)
    groups.append(dict(run_id=run_id, group=path, first=counts(original), second=counts(final),
                       ids_equal=True, second_attempt_acceptance="OBSERVATION_ONLY_NOT_SUBSTITUTE_FOR_FIRST_RESULT"))
out = dict(candidate_sha="b53b5acdf260b03ebac3474e9ae837fcef6f6eb1",
    source_ledger_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    raw_canonical_document_occurrences=len(canonical), raw_canonical_status_counts=counts(canonical),
    raw_canonical_distinct_id_strings=len({r["id"] for r in canonical}),
    original_first_result_cohort_occurrences=len(cohort), original_first_result_status_counts=counts(cohort),
    original_first_result_by_layer={layer: counts(rows) for layer, rows in by_layer.items()},
    internal_second_attempt_occurrences=len(second), internal_second_attempt_counts=counts(second),
    internal_second_attempt_groups=groups,
    measurement_only_scale_rows=dict(run_id=39146762696, report="CP7_P19_SCALE.json", raw_counts=counts([r for r in canonical if r["report"] == "CP7_P19_SCALE.json"]),
        qualification="Included as raw execution occurrences, not latency/factory acceptance. Read P19_SCALE_RESULT_REVIEW.json for all 48 measurements, refusals and direct/finance target misses."),
    no_product_credit_categories={category: counts([r for r in ledger if r["category"] == category]) for category in
        ("AUXILIARY_SMOKE", "SOURCE_ADMISSION_NO_PRODUCT_CREDIT", "DIAGNOSTIC_LEGACY", "DIAGNOSTIC_ONLY_RUN")},
    metadata_qualifications=dict(separate_runs=[39150692618,39150692634], t3_browser_case_count=10,
        sarif_result_counts=[0,0,0,0], original_run_failures_preserved=True,
        reference="METADATA_Q1_RESULT_REVIEW.json", added_to_cp7_case_count=False),
    legacy_origin_separate=dict(reference="LEGACY_DOCUMENT_REVIEW.json", normalization="NONPASS_DISPOSITIONS.json"),
    full_audit_pass=False, feature_complete=False, audit_complete=False, production_go=False,
    qualification="Counts describe execution occurrences, not unique independent oracles, risk weights or an ERP percentage. PASS raw rows have only their declared writer/inherited-oracle scope. Internal second attempts are not used to overwrite original acceptance. No held additional probe receives credit.")
(ROOT / "RESULT_ACCEPTANCE_SUMMARY.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print("raw", counts(canonical), "original_cohort", counts(cohort), "second_groups", len(groups))
