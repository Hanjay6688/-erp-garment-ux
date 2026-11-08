from __future__ import annotations

import ast
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import yaml

import focus_identity
from build_focus_workflow import derive
from focus_transaction import prepare_native_case, rollback_boundary


ROOT = Path(__file__).resolve().parent
TEST_BRANCH = "astra-a/mandor-zero-effect-focus-20261108"
WORKFLOW_SOURCE = Path(sys.argv[1])


def source(name):
    return (ROOT / name).read_text()


def expect_error(message, function):
    try:
        function()
    except ValueError as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError("missing rejection: " + message)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True,
                                   stderr=subprocess.PIPE).strip()


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


@contextmanager
def focus_repo():
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        tools = root / "focus-tools"
        tools.mkdir()
        (root / "writer").mkdir()
        git(tools, "init", "-q")
        git(tools, "config", "user.name", "CP7 Local Test")
        git(tools, "config", "user.email", "local@example.invalid")
        (tools / "product.sql").write_text("select 1;\n")
        git(tools, "add", ".")
        git(tools, "commit", "-qm", "product")
        product_head, product_tree = git(tools, "rev-parse", "HEAD", "HEAD^{tree}").splitlines()
        git(tools, "worktree", "add", "--detach", str(root / "auditor"), product_head)
        for name in focus_identity.ALLOWED_ADDITIONS:
            path = tools / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n")
        git(tools, "add", ".")
        git(tools, "commit", "-qm", "focus")
        previous_focus_head = git(tools, "rev-parse", "HEAD")
        for name in focus_identity.CORRECTED_FILES:
            (tools / name).write_text("corrected fixture\n")
        git(tools, "add", ".")
        git(tools, "commit", "-qm", "focus source-context correction")
        ref = "refs/heads/" + TEST_BRANCH
        env = dict(CP7_FOCUS_APPROVED_REF=ref, GITHUB_REF=ref, GITHUB_EVENT_NAME="push",
                   GITHUB_RUN_ID="12345", GITHUB_RUN_ATTEMPT="1", MANDOR_NATIVE_CONFIRM="cp6_rollback",
                   GITHUB_SHA=git(tools, "rev-parse", "HEAD"), GITHUB_WORKSPACE=temporary)
        with patch.multiple(focus_identity, PRODUCT_HEAD=product_head, PRODUCT_TREE=product_tree,
                            PREVIOUS_FOCUS_HEAD=previous_focus_head), working_directory(root / "writer"):
            yield root, env


def test_identity_admits_only_exact_child_and_product():
    with focus_repo() as (root, env):
        assert focus_identity.admit(env).is_relative_to(root / "auditor")
        expect_error("APPROVED_PUSH_REQUIRED", lambda: focus_identity.admit(dict(env, GITHUB_EVENT_NAME="workflow_dispatch")))
        expect_error("SINGLE_RUN_IDENTITY_REQUIRED", lambda: focus_identity.admit(dict(env, GITHUB_RUN_ATTEMPT="2")))
        expect_error("DISTINCT_WORKFLOW_COMMIT_REQUIRED", lambda: focus_identity.admit(dict(env, GITHUB_SHA=focus_identity.PRODUCT_HEAD)))
        expect_error("DISTINCT_WORKFLOW_COMMIT_REQUIRED", lambda: focus_identity.admit(dict(env, GITHUB_SHA=focus_identity.PREVIOUS_FOCUS_HEAD)))


def test_identity_refuses_original_auditor_working_directory():
    with focus_repo() as (root, env), working_directory(root / "auditor"):
        expect_error("OWNING_WRITER_WORKING_DIRECTORY_REQUIRED", lambda: focus_identity.admit(env))


def test_identity_refuses_product_or_tools_mutation():
    with focus_repo() as (root, env):
        (root / "auditor/product.sql").write_text("select 2;\n")
        expect_error("TRACKED_CHECKOUT_CHANGED", lambda: focus_identity.admit(env))
        tools = root / "focus-tools"
        (tools / "product.sql").write_text("select 3;\n")
        git(tools, "add", "product.sql")
        git(tools, "commit", "--amend", "-q", "--no-edit")
        expect_error("UNEXPECTED_WORKFLOW_COMMIT_CHANGES",
                     lambda: focus_identity.admit(dict(env, GITHUB_SHA=git(tools, "rev-parse", "HEAD"))))


def test_workflow_is_one_case_no_browser_no_qualification():
    workflow = yaml.safe_load(derive(WORKFLOW_SOURCE.read_bytes(), TEST_BRANCH))
    assert set(workflow["on"]) == {"push"}
    assert workflow["on"]["push"]["branches"] == [TEST_BRANCH]
    job = workflow["jobs"]["p21"]
    assert job["timeout-minutes"] == 240
    steps = job["steps"]
    tools = next(step["with"] for step in steps if step.get("with", {}).get("path") == "focus-tools")
    product = next(step["with"] for step in steps if step.get("with", {}).get("path") == "auditor")
    assert tools["fetch-depth"] == 3 and "ref" not in tools
    assert product["ref"] == focus_identity.PRODUCT_HEAD and product["fetch-depth"] == 0
    names = [step.get("name", "") for step in steps]
    assert sum("one exact correction case" in name.lower() for name in names) == 1
    preflight = next(step for step in steps if step.get("name", "").startswith("Admit exact focused source"))
    runtime = next(step for step in steps if step.get("name", "").startswith("Run one exact correction case"))
    owning = yaml.safe_load(WORKFLOW_SOURCE.read_bytes())
    accepted_dir = next(step["working-directory"] for step in owning["jobs"]["p21"]["steps"]
                        if step.get("name", "").startswith("Admit genuine Afui15"))
    assert preflight["working-directory"] == runtime["working-directory"] == accepted_dir == "writer"
    assert not any(x in name.lower() for name in names for x in
                   ("install pinned browser", "open actual desktop", "run current mandor17"))
    assert steps[-2]["if"] == "always()"
    assert steps[-1]["with"]["path"] == "focus-proof"


def test_runtime_uses_original_case_and_rolls_back():
    text = source("focus_transaction.py")
    for needle in (
        "run_case(native, cur, today, additional_cases.correction_return, args.output.parent)",
        "retain_originals(case, source_root.parents[1], args.output.parent)",
        "before = rollback_boundary(cur, engine.product)",
        "restored = rollback_boundary(cur, engine.product)",
        "engine.product.install_delta(cur, parent)",
        "conn.rollback()",
        "full_recovery_verified=True",
        '"qualification_credit": 0',
    ):
        assert needle in text, needle
    assert "for case in" not in text and "workflow_dispatch" not in text


def test_native_setup_and_preinstall_boundary():
    from datetime import date

    native = Mock()
    strict = Mock()
    cur = Mock()
    day = date(2026, 11, 8)
    cur.execute.return_value.fetchone.return_value = (day,)
    assert prepare_native_case(cur, native, strict) == (day, native.committed_foundation.return_value)
    native.committed_foundation.assert_called_once_with(cur)
    strict.boundary.historical.prior.set_open_period.assert_called_once_with(cur, date(2026, 8, 31))
    native.admin.assert_called_once_with(cur)

    product = Mock()
    catalogue = Mock()
    product.runtime.return_value = (catalogue,)
    assert rollback_boundary(cur, product) == {
        "catalogue": product.mandor.capture.return_value,
        "data_and_sequences": catalogue._data.return_value,
    }
    product.mandor.capture.assert_called_once_with(cur)
    catalogue._data.assert_called_once_with(cur)


def test_all_python_sources_compile():
    for name in ("focus_identity.py", "focus_preflight.py", "focus_transaction.py", "build_focus_workflow.py"):
        ast.parse(source(name), filename=name)


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print({"status": "PASS", "controls": len(tests),
           "classification": "SOURCE_ONLY_FOCUSED_ROUTE_NOT_RUNTIME_ACCEPTANCE"})
