"""Audit metadata only: no database, HTTP client, product import or test execution."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

CANDIDATE = "b53b5acdf260b03ebac3474e9ae837fcef6f6eb1"
CANDIDATE_TREE = "32f54240a60e01ab8b1ffad7267d285a669be520"
HISTORICAL_UI = "e43e0ed4bab5ba9a803100e57ddfd7cd2647c631"
HISTORICAL_UI_TREE = "05fc26cf00a6e5253192f4bd2ec7d7f4bdf06bc1"
PRODUCT_TREES = {
    "src": "b4041b3b21b6e63a36419f9beae4de24f3a96244",
    "supabase/release": "be1e91c172ffb5c05b694a3a54c69562700c6d5e",
    "supabase/migrations": "8f6053bbd0bda80da18065418ad43371cdfd9461",
    "scripts/cp7-src": "633ef684ec2ec2c3f54c48a6ba971f8c6d70843b",
    "supabase/dev": "88759f4fc51864a1ec9e224fcb4f236204b5c853",
}


def validate_record(record, role):
    if role not in ("candidate", "historical_ui"):
        raise ValueError("AUDIT_METADATA_UNKNOWN_CHECKOUT_ROLE")
    expected_head, expected_tree = (CANDIDATE, CANDIDATE_TREE) if role == "candidate" else (HISTORICAL_UI, HISTORICAL_UI_TREE)
    if record["head"] != expected_head:
        raise ValueError("AUDIT_METADATA_CHECKOUT_HEAD_MISMATCH")
    if record["tree"] != expected_tree:
        raise ValueError("AUDIT_METADATA_CHECKOUT_TREE_MISMATCH")
    if record["tracked_product_diff"]:
        raise ValueError("AUDIT_METADATA_PRODUCT_WORKTREE_CHANGED")
    if role == "candidate":
        if record["product_trees"] != PRODUCT_TREES:
            raise ValueError("AUDIT_METADATA_CANDIDATE_PRODUCT_PATH_MISMATCH")
        if record["absent_product_paths"]:
            raise ValueError("AUDIT_METADATA_CANDIDATE_PRODUCT_PATH_ABSENT")
    else:
        # An absent path is valid only at the explicitly pinned historical commit.
        for path in PRODUCT_TREES:
            present = path in record["product_trees"]
            absent = path in record["absent_product_paths"]
            if present == absent:
                raise ValueError("AUDIT_METADATA_HISTORICAL_PATH_NOT_EXPLICIT")
    return dict(record, checkout_role=role, expected_head=expected_head, expected_tree=expected_tree,
        candidate_exact=role == "candidate", identity_verified=True)


def validate_t3_records(records, phase, workflow_sha):
    if phase not in ("install", "capture", "browser"):
        raise ValueError("AUDIT_METADATA_UNKNOWN_T3_PHASE")
    if not re.fullmatch(r"[0-9a-f]{40}", workflow_sha):
        raise ValueError("AUDIT_METADATA_WORKFLOW_SHA_INVALID")
    if set(records) != {"auditor", "chain"}:
        raise ValueError("AUDIT_METADATA_T3_CHECKOUT_SET_MISMATCH")
    roles = {"auditor": "historical_ui" if phase == "browser" else "candidate", "chain": "candidate"}
    items = [validate_record(records[path], roles[path]) for path in ("auditor", "chain")]
    if not any(item["candidate_exact"] for item in items):
        raise ValueError("AUDIT_METADATA_NO_CANDIDATE_CHECKOUT")
    return dict(candidate_sha=CANDIDATE, candidate_tree=CANDIDATE_TREE, workflow_sha=workflow_sha,
        phase=phase, checkouts=items)


def read_record(path):
    root = Path(path)
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    trees, absent = {}, []
    for product_path in PRODUCT_TREES:
        present = subprocess.run(["git", "-C", str(root), "cat-file", "-e", "HEAD:" + product_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if present:
            trees[product_path] = git("rev-parse", "HEAD:" + product_path)
        else:
            absent.append(product_path)
    return dict(path=path, head=git("rev-parse", "HEAD"), tree=git("rev-parse", "HEAD^{tree}"),
        product_trees=trees, absent_product_paths=absent,
        tracked_product_diff=git("diff", "--name-only", "--", *PRODUCT_TREES),
        lock_sha256=hashlib.sha256((root / "package-lock.json").read_bytes()).hexdigest())


def main():
    records = {path: read_record(path) for path in ("auditor", "chain")}
    out = validate_t3_records(records, os.environ["SOL_T3_PHASE"], os.environ["GITHUB_SHA"])
    out.update(run_id=os.environ["GITHUB_RUN_ID"], attempt=os.environ["GITHUB_RUN_ATTEMPT"],
        suite="cp6-t3-release-package", metadata_qualification="SOL_METADATA_Q1",
        original_run_id=39146762759, original_browser_job_id=117732074565,
        evidence_origin="INDEPENDENT_SOL_EXECUTION_IDENTITY_METADATA",
        oracle_origin="WRITER_OR_INHERITED_DECLARED", fixture_origin="PUBLIC_REPO_SYNTHETIC")
    target = Path(os.environ["RUNNER_TEMP"]) / "sol-proof"
    target.mkdir(exist_ok=True)
    (target / "IDENTITY.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
