"""Reconcile collected own-run metadata without network or test execution."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
raw = json.loads((ROOT / "RUN_REGISTER.json").read_text())
runs = {r["run_id"]: dict(r) for r in raw["runs"]}
assert len(runs) == 81
terminal = {}
jobs = {}
for path in sorted((ROOT / "ci_receipts").glob("sol_terminal_batch_*.json")):
    entries = json.loads(path.read_text())
    for entry in entries:
        rid = entry["run_id"]
        assert entry.get("run_status", entry.get("status")) == "completed", (path, rid)
        prior = terminal.get(rid)
        assert not prior or prior["conclusion"] == entry["conclusion"], (path, rid)
        terminal[rid] = dict(entry, metadata_path=str(path.relative_to(ROOT)),
                             metadata_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        for job in entry.get("jobs", []):
            jobs[job["id"]] = job
for path in sorted((ROOT / "ci_receipts").glob("sol_partial_tail_*.json")):
    for entry in json.loads(path.read_text()):
        for job in entry.get("jobs", []):
            jobs.setdefault(job["id"], job)
artifacts = collections.defaultdict(list)
for path in sorted((ROOT / "ci_receipts/sol_artifacts").glob("*/DOWNLOAD_RECEIPT.json")):
    x = json.loads(path.read_text())
    artifacts[x["run_id"]].append(x["artifact_id"])
for rid, r in runs.items():
    t = terminal.get(rid)
    if t:
        r.update(status="completed", conclusion=t["conclusion"],
                 terminal_metadata_path=t["metadata_path"], terminal_metadata_sha256=t["metadata_sha256"])
    else:
        r.update(status="NOT_TERMINAL_IN_COLLECTED_METADATA", conclusion=None)
    r["artifacts_collected"] = artifacts[rid]
    r["jobs_collected"] = [dict(id=j["id"], name=j["name"], status=j["status"], conclusion=j["conclusion"],
                                failed_steps=[s["name"] for s in (j.get("steps") or []) if s["conclusion"] == "failure"])
                            for j in jobs.values() if j.get("run_id") == rid]
qualifications = []
for rid in (39150692618, 39150692634):
    t = terminal[rid]
    qualifications.append(dict(run_id=rid, run_name=t["run_name"], workflow_sha=t["workflow_sha"],
        status="completed", conclusion=t["conclusion"], metadata_path=t["metadata_path"],
        artifacts_collected=artifacts[rid], original_runs_preserved=True,
        result_review="METADATA_Q1_RESULT_REVIEW.json"))
out = dict(candidate_sha=raw["candidate_sha"], scope="ORIGINAL_81_PLUS_TWO_SEPARATE_METADATA_QUALIFICATIONS",
    full_audit_pass=False, new_probes_executed=False, original_run_count=81,
    original_status_counts=dict(collections.Counter(r["conclusion"] or "NOT_TERMINAL" for r in runs.values())),
    original_runs=list(runs.values()), metadata_qualifications=qualifications,
    qualification="Job conclusion is metadata only. Per-case review and first-result/retained/diagnostic boundaries are separate.")
(ROOT / "CI_RUN_DISPOSITIONS.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(out["original_status_counts"]))
print("pending", [rid for rid, r in runs.items() if r["conclusion"] is None])
