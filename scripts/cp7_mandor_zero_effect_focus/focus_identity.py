"""Admit only the exact focused repair chain on the pinned product."""

import os
from pathlib import Path
import re
import subprocess


PRODUCT_HEAD = "e9339f05f61b54570025012e8a5e647db0d39152"
PRODUCT_TREE = "d297449b8441a12c406b4f2024a33d004d7b69aa"
PREVIOUS_FOCUS_HEAD = "62ef0ce8cf25c227514ffc4e88fcd9b31101591c"
PRIOR_CONTEXT_FOCUS_HEAD = "18422e0515776a8f6cee74bc9071e46657a8290b"
INITIAL_FOCUS_HEAD = "e83257392f3b29d9e4787ecd117f2078060d07a5"
PACKAGE_FINGERPRINT = "25719efa7216af816f0552a6da3d9bf9e687a75ba6f39985072481fd22804ccc"
FOCUS_DIR = "scripts/cp7_mandor_zero_effect_focus"
WORKFLOW_PATH = ".github/workflows/cp7-mandor-zero-effect-focus.yml"
FILES = {
    "FOCUS_SCOPE.json", "FOCUSED_INSTALLER.sql", "FOCUSED_INSTALLER_RECEIPT.json",
    "focus_identity.py", "focus_preflight.py", "focus_transaction.py",
    "build_focus_workflow.py", "test_focus_plan.py",
}
ALLOWED_ADDITIONS = {WORKFLOW_PATH} | {f"{FOCUS_DIR}/{name}" for name in FILES}
CORRECTED_FILES = {WORKFLOW_PATH} | {f"{FOCUS_DIR}/{name}" for name in (
    "build_focus_workflow.py", "focus_identity.py", "focus_transaction.py", "test_focus_plan.py",
    "FOCUSED_INSTALLER.sql", "FOCUSED_INSTALLER_RECEIPT.json",
)}


def git(repo, *args):
    return subprocess.check_output(["/usr/bin/git", "-C", str(repo), *args], text=True).strip()


def admit(environment=os.environ):
    approved = environment.get("CP7_FOCUS_APPROVED_REF", "")
    if not re.fullmatch(r"refs/heads/astra-a/mandor-zero-effect-focus-[0-9]{8}", approved):
        raise ValueError("CP7_FOCUS_EXACT_APPROVED_DISPOSABLE_REF_REQUIRED")
    if environment.get("GITHUB_REF") != approved or environment.get("GITHUB_EVENT_NAME") != "push":
        raise ValueError("CP7_FOCUS_APPROVED_PUSH_REQUIRED")
    if not re.fullmatch(r"[1-9][0-9]*", environment.get("GITHUB_RUN_ID", "")) \
       or environment.get("GITHUB_RUN_ATTEMPT") != "1":
        raise ValueError("CP7_FOCUS_SINGLE_RUN_IDENTITY_REQUIRED")
    if environment.get("MANDOR_NATIVE_CONFIRM") != "cp6_rollback":
        raise ValueError("CP7_FOCUS_EXPLICIT_DISPOSABLE_DATABASE_REQUIRED")
    workflow_head = environment.get("GITHUB_SHA", "")
    chain = (workflow_head, PREVIOUS_FOCUS_HEAD, PRIOR_CONTEXT_FOCUS_HEAD, INITIAL_FOCUS_HEAD, PRODUCT_HEAD)
    if not re.fullmatch(r"[a-f0-9]{40}", workflow_head) or workflow_head in chain[1:]:
        raise ValueError("CP7_FOCUS_DISTINCT_WORKFLOW_COMMIT_REQUIRED")
    workspace = Path(environment["GITHUB_WORKSPACE"]).resolve(strict=True)
    if Path.cwd().resolve() != workspace / "writer":
        raise ValueError("CP7_FOCUS_OWNING_WRITER_WORKING_DIRECTORY_REQUIRED")
    product, tools = workspace / "auditor", workspace / "focus-tools"
    if git(product, "rev-parse", "HEAD", "HEAD^{tree}").splitlines() != [PRODUCT_HEAD, PRODUCT_TREE]:
        raise ValueError("CP7_FOCUS_EXACT_PRODUCT_HEAD_AND_TREE_REQUIRED")
    if git(tools, "rev-parse", "HEAD") != workflow_head:
        raise ValueError("CP7_FOCUS_EXACT_WORKFLOW_CHECKOUT_REQUIRED")
    for child, parent in zip(chain, chain[1:]):
        if git(tools, "rev-list", "--parents", "-n", "1", child).split() != [child, parent]:
            raise ValueError("CP7_FOCUS_WORKFLOW_PARENT_MISMATCH:" + child)
    corrected = set(git(tools, "diff", "--name-only", "--no-renames", PREVIOUS_FOCUS_HEAD, "HEAD").splitlines())
    if corrected != CORRECTED_FILES:
        raise ValueError("CP7_FOCUS_UNEXPECTED_WORKFLOW_COMMIT_CHANGES")
    changed = set(git(tools, "diff", "--name-only", "--no-renames", PRODUCT_HEAD, "HEAD").splitlines())
    added = set(git(tools, "diff", "--name-only", "--no-renames", "--diff-filter=A", PRODUCT_HEAD, "HEAD").splitlines())
    if changed != ALLOWED_ADDITIONS or added != ALLOWED_ADDITIONS:
        raise ValueError("CP7_FOCUS_UNEXPECTED_WORKFLOW_COMMIT_CHANGES")
    for repo in (product, tools):
        if git(repo, "status", "--porcelain", "--untracked-files=no"):
            raise ValueError("CP7_FOCUS_TRACKED_CHECKOUT_CHANGED")
    return product / "scripts/current-mandor-shop-native-qualification"
