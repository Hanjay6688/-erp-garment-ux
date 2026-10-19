"""Read-only identity collection for the Sol r4 disposable qualifications."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

CANDIDATE = "663f6faefcbb9c70f0f99bbc7e78164e03521329"
TREE = "023f3554432f80f994439f5d0b8cc164846a2041"
ROOTS = ("src", "supabase", "scripts", "package.json", "package-lock.json", "index.html", "vite.config.ts")


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def collect(root):
    head = git(root, "rev-parse", "HEAD")
    tree = git(root, "rev-parse", "HEAD^{tree}")
    assert head == CANDIDATE, ("SOL_R4_WRONG_CANDIDATE", head)
    assert tree == TREE, ("SOL_R4_WRONG_TREE", tree)
    dirty = git(root, "status", "--porcelain", "--", *ROOTS)
    assert not dirty, ("SOL_R4_PRODUCT_WORKTREE_CHANGED", dirty)
    roots = {name: git(root, "rev-parse", "HEAD:" + name) for name in ROOTS}
    declaration = root / "docs/cp7/cp17/CP17_FIXES.json"
    body = declaration.read_bytes()
    data = json.loads(body)
    expected = {"native": 161, "races": 39, "http": 27, "browser": 57, "browser_enteng": 57}
    assert data["expected_case_count"] == 341 and data["required_case_counts"] == expected
    ids = data["required_case_ids"]
    assert set(ids) == set(expected)
    assert all(len(ids[k]) == expected[k] == len(set(ids[k])) for k in ids)
    assert len({x for group in ids.values() for x in group}) == 341
    return dict(candidate_sha=head, candidate_tree=tree, product_roots=roots,
                product_worktree_clean=True, declaration_sha256=hashlib.sha256(body).hexdigest(),
                required_case_counts=expected, required_unique_case_ids=341)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = collect(args.root.resolve())
    report.update(phase=args.phase, recorded_at=datetime.now(timezone.utc).isoformat(),
                  workflow_sha=os.environ.get("GITHUB_SHA"), run_id=os.environ.get("GITHUB_RUN_ID"),
                  run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
                  identity_origin="SOL_READ_ONLY_COLLECTOR", oracle_origin="WRITER_DECLARED_CASES")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("phase", "candidate_sha", "candidate_tree", "workflow_sha", "run_id", "required_unique_case_ids")}))


if __name__ == "__main__":
    main()
