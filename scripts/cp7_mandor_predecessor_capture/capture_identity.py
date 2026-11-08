"""Verify the workflow and ERP checkouts before importing the installer."""

import os
from pathlib import Path
import re
import subprocess


PRODUCT_HEAD = "e9339f05f61b54570025012e8a5e647db0d39152"
PRODUCT_TREE = "d297449b8441a12c406b4f2024a33d004d7b69aa"
PACKAGE_FINGERPRINT = "25719efa7216af816f0552a6da3d9bf9e687a75ba6f39985072481fd22804ccc"
CAPTURE_DIR = "scripts/cp7_mandor_predecessor_capture"
WORKFLOW_PATH = ".github/workflows/cp7-mandor-predecessor-capture.yml"
ALLOWED_ADDITIONS = {WORKFLOW_PATH} | {
    f"{CAPTURE_DIR}/{name}"
    for name in (
        "CAPTURE_SCOPE.json", "capture_identity.py", "capture_post_mandor.py",
        "verify_capture.py", "capture_preflight.py", "capture_predecessor_transactional.py",
    )
}


def git(repo, *args):
    return subprocess.check_output(["/usr/bin/git", "-C", str(repo), *args], text=True).strip()


def admit(environment=os.environ):
    approved = environment.get("CP7_CAPTURE_APPROVED_REF", "")
    if not re.fullmatch(r"refs/heads/astra-a/mandor-predecessor-capture-[0-9]{8}", approved):
        raise ValueError("CP7_CAPTURE_EXACT_APPROVED_DISPOSABLE_REF_REQUIRED")
    if environment.get("GITHUB_REF") != approved or environment.get("GITHUB_EVENT_NAME") != "push":
        raise ValueError("CP7_CAPTURE_APPROVED_PUSH_REQUIRED")
    run_id = environment.get("GITHUB_RUN_ID", "")
    if not re.fullmatch(r"[1-9][0-9]*", run_id) or environment.get("GITHUB_RUN_ATTEMPT") != "1":
        raise ValueError("CP7_CAPTURE_SINGLE_RUN_IDENTITY_REQUIRED")
    if environment.get("MANDOR_NATIVE_CONFIRM") != "cp6_rollback":
        raise ValueError("CP7_CAPTURE_EXPLICIT_DISPOSABLE_DATABASE_REQUIRED")
    workflow_head = environment.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[a-f0-9]{40}", workflow_head) or workflow_head == PRODUCT_HEAD:
        raise ValueError("CP7_CAPTURE_DISTINCT_WORKFLOW_COMMIT_REQUIRED")
    workspace = Path(environment["GITHUB_WORKSPACE"]).resolve(strict=True)
    product = workspace / "auditor"
    tools = workspace / "capture-tools"
    if git(product, "rev-parse", "HEAD", "HEAD^{tree}").splitlines() != [PRODUCT_HEAD, PRODUCT_TREE]:
        raise ValueError("CP7_CAPTURE_EXACT_PRODUCT_HEAD_AND_TREE_REQUIRED")
    if git(tools, "rev-parse", "HEAD") != workflow_head:
        raise ValueError("CP7_CAPTURE_EXACT_WORKFLOW_CHECKOUT_REQUIRED")
    if git(tools, "rev-list", "--parents", "-n", "1", "HEAD").split() != [workflow_head, PRODUCT_HEAD]:
        raise ValueError("CP7_CAPTURE_WORKFLOW_PARENT_MISMATCH")
    changed = set(git(tools, "diff", "--name-only", "--no-renames", PRODUCT_HEAD, "HEAD").splitlines())
    added = set(git(tools, "diff", "--name-only", "--no-renames", "--diff-filter=A", PRODUCT_HEAD, "HEAD").splitlines())
    if changed != ALLOWED_ADDITIONS or added != ALLOWED_ADDITIONS:
        raise ValueError("CP7_CAPTURE_UNEXPECTED_WORKFLOW_COMMIT_CHANGES")
    for repo in (product, tools):
        if git(repo, "status", "--porcelain", "--untracked-files=no"):
            raise ValueError("CP7_CAPTURE_TRACKED_CHECKOUT_CHANGED")
    return product / "scripts/current-mandor-shop-native-qualification"
