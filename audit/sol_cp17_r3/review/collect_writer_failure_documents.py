"""Index existing writer failure logs; no network or product/test execution."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "ci_receipts/writer_b53b5acd"
index = json.loads((BASE / "failed_job_logs/INDEX.json").read_text())
reviews = []
for entry in index["retrieved"]:
    path = BASE / entry["path"]
    raw = path.read_bytes()
    lines = raw.decode().splitlines()
    traces = []
    for i, line in enumerate(lines):
        if "Traceback (most recent call last):" not in line:
            continue
        tail = lines[i:i + 14]
        assertions = [s.split("Z ", 1)[-1].strip() for s in tail if "    assert " in s]
        exceptions = [s.split("Z ", 1)[-1] for s in tail
                      if "AssertionError" in s or "FileNotFoundError:" in s]
        traces.append(dict(line=i + 1, assertions=assertions,
                           exception_kinds=[s.split(":", 1)[0] for s in exceptions],
                           original_excerpt_sha256=hashlib.sha256("\n".join(tail).encode()).hexdigest()))
    review = dict(run_id=entry["run_id"], job_id=entry["job_id"],
                  path=str(path.relative_to(ROOT)), bytes=len(raw),
                  sha256=hashlib.sha256(raw).hexdigest(), failed_steps=entry["failed_steps"],
                  traces=traces, origin="WRITER_EXECUTION_REUSED_NOT_SOL_RUNTIME")
    if entry["job_id"] == 117407251055:
        expired = [(i + 1, s.split("Z ", 1)[-1]) for i, s in enumerate(lines)
                   if "gh: Artifact has expired (HTTP 410)" in s]
        assert expired and any("FileNotFoundError" in str(t) for t in traces)
        review.update(classification="EXPIRED_INCOMING_ARTIFACT_BEFORE_AF_CASES",
                      artifact_id=10418502157, expired_lines=expired,
                      qualification="Admission file missing after incoming AE archive download failed. No AF case credit.")
    elif entry["job_id"] == 117431817166:
        objects = []
        for i, line in enumerate(lines):
            payload = line.split(" ", 1)[-1]
            if not payload.startswith("{"):
                continue
            try:
                value = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                objects.append((i + 1, value))
        summary = next(value for _, value in objects if value.get("auditor_phase") == "after")
        cases = [(no, value) for no, value in objects if "case" in value and "group" in value]
        group_counts = {group: dict(collections.Counter(value["status"] for _, value in cases
                                                       if value["group"] == group))
                        for group in sorted({value["group"] for _, value in cases})}
        assert group_counts == {
            "AUDITOR_BROWSER_AFTER": {"INCOMPLETE": 4, "PASS": 27},
            "AUDITOR_CASES_AFTER": {"PASS": 104},
            "AUDITOR_HTTP_AFTER": {"PASS": 9},
            "AUDITOR_RACES_AFTER": {"PASS": 26}}
        nonpass = [dict(line=no, id=value["case"], status=value["status"], error=value.get("error"))
                   for no, value in cases if value["status"] != "PASS"]
        review.update(classification="FROZEN_CP6_SCENARIO_FOUR_KNOWN_INCOMPLETE_RETAINED",
                      group_counts=group_counts, original_nonpass=nonpass,
                      run_identity=summary["run_identity"], primary_unchanged=summary["primary_unchanged"],
                      clone_remaining=summary["clone_remaining"],
                      qualification="Two pre-CP7 readiness readers absent; two retired SALES_MANUAL_13 selectors. Old product_ref retained; not current r3 browser proof.")
    else:
        assert traces and all(t["assertions"] for t in traces)
        expressions = [a for t in traces for a in t["assertions"]]
        assert all(any(token in a for token in ("git(", "changed", "subprocess.check_output"))
                   for a in expressions)
        review.update(classification="HISTORICAL_SOURCE_SCOPE_GUARD",
                      qualification="Scope/merge/source-path assertion on later combined candidate; no new product failure established. Preserve any predecessor qualification separately.")
    reviews.append(review)
counts = dict(collections.Counter(r["classification"] for r in reviews))
assert len(reviews) == 22 and counts["HISTORICAL_SOURCE_SCOPE_GUARD"] == 20
out = dict(scope="READ_ONLY_DOCUMENT_REVIEW_OF_WRITER_LOGS_DECLARED_IN_B53_RECEIPT",
           peer_r3_read=False, total=22, counts=counts, reviews=reviews,
           annotations_endpoint="UNAVAILABLE_HTTP400_NOT_ALLOWED_ENDPOINT_NO_ENUMERATION_CLAIM",
           all_job_failures_preserved=True)
(ROOT / "WRITER_FAILURE_LOG_REVIEW.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(dict(total=len(reviews), counts=counts), ensure_ascii=False))
