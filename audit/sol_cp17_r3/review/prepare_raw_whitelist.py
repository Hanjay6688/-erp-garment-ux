"""List exact existing text evidence for durable packaging; never uploads files."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
ALLOWED = {".json", ".jsonl", ".md", ".txt", ".csv", ".sarif", ".log"}
paths = {}


def add(path, origin):
    path = path.resolve()
    assert path.is_relative_to(ROOT) and path.is_file() and path.suffix.lower() in ALLOWED, path
    raw = path.read_bytes()
    key = str(path.relative_to(REPO))
    paths[key] = dict(path=key, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), origin=origin)


receipts = sorted((ROOT / "ci_receipts/sol_artifacts").glob("*/DOWNLOAD_RECEIPT.json"))
for receipt_path in receipts:
    receipt = json.loads(receipt_path.read_text())
    add(receipt_path, "ROOT_MECHANICAL_ARCHIVE_DIGEST_AND_EXTRACTION_RECEIPT")
    for item in receipt["selected_files"]:
        path = receipt_path.parent / "files" / item["path"]
        assert path.suffix.lower() in ALLOWED, path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], path
        add(path, "EXISTING_OWN_CI_TEXT_RESULT_ARTIFACT")
for path in (ROOT / "ci_receipts").glob("*.json"):
    add(path, "ROOT_MECHANICAL_OWN_RUN_METADATA_OR_PUBLICATION_RECEIPT")
for path in (ROOT / "ci_receipts/sol_job_logs").glob("*.log"):
    add(path, "ORIGINAL_OWN_CI_LOG_FIRST_RESULT_PRESERVED")
for path in (ROOT / "ci_receipts/writer_b53b5acd").rglob("*"):
    if path.is_file() and path.suffix.lower() in {".json", ".log"}:
        add(path, "DECLARED_WRITER_B53_METADATA_OR_FAILURE_LOG_REUSED_EVIDENCE")
for name in ("CASE_LEDGER_PARTIAL.json", "LEGACY_CASE_LEDGER.json", "RESULT_DOCUMENT_REVIEW_PARTIAL.json"):
    add(ROOT / name, "SOL_DERIVED_DOCUMENT_INDEX_NOT_NEW_ORACLE")
registry = json.loads((ROOT / "CI_RUN_DISPOSITIONS.json").read_text())
pending = [r["run_id"] for r in registry["original_runs"] if r["conclusion"] is None]
out = dict(state="DRAFT_PENDING_ORIGINAL_RUNS" if pending else "FINAL_READY_FOR_DURABLE_ARCHIVE", whitelist_final=not pending, pending_original_run_ids=pending, candidate_sha="b53b5acdf260b03ebac3474e9ae837fcef6f6eb1",
           root_relative_paths=True, path_count=len(paths), bytes=sum(x["bytes"] for x in paths.values()),
           artifact_receipts=len(receipts), selected_text_only=True,
           excluded="archives, images, screenshots, binary/build output, SQL/dumps, local drafts/probes and unrelated files",
           qualification="Original public CI logs are retained as collected, including disposable local-runtime startup output. No credential extraction or use. Package is standalone evidence; do not stage these raw files to Git.",
           files=[paths[k] for k in sorted(paths)])
(ROOT / "RAW_EVIDENCE_WHITELIST.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({k: out[k] for k in ("state", "path_count", "bytes", "artifact_receipts")}))
