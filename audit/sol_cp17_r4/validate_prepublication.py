"""Validate audit workflow edits and pure metadata binding; never executes a business or access probe."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import subprocess

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def inline(step, marker):
    code = step["run"].split("<<'" + marker + "'\n", 1)[1].rsplit("\n" + marker, 1)[0]
    compile(code, marker, "exec")
    return code


def main():
    manifest = json.loads((HERE / "REGRESSION_PREEXECUTION_MANIFEST.json").read_text())
    checks = []
    phases = 0
    for row in manifest["workflows"]:
        source = yaml.safe_load((ROOT / row["source"]).read_text())
        actual = yaml.safe_load((ROOT / row["path"]).read_text())
        assert actual["permissions"] == {"contents": "read", "actions": "read"}
        assert actual["on"]["push"] == {"branches": [manifest["own_branch"]], "paths": [row["path"]]}
        assert set(actual["jobs"]) == set(source["jobs"])
        for key, job in actual["jobs"].items():
            original = deepcopy(source["jobs"][key])
            new = deepcopy(job)
            matrix = job.get("strategy", {}).get("matrix", {})
            phases += len(matrix.get("include", [])) or max([len(x) for x in matrix.values() if isinstance(x, list)] or [1])
            hooks = [s for s in new["steps"] if s.get("name", "").startswith("Sol record exact candidate")]
            assert len(hooks) == 2 and hooks[1]["if"] == "always()"
            product = [s for s in new["steps"] if s.get("uses", "").startswith("actions/checkout@")
                       and s.get("with", {}).get("ref") == manifest["candidate_sha"]]
            assert len(product) == 1 and product[0]["with"]["persist-credentials"] is False
            new["steps"] = [s for s in new["steps"] if not
                            (s.get("with", {}).get("path") == "sol" or
                             s.get("name", "").startswith("Sol record exact candidate") or
                             s.get("with", {}).get("path") == "audit-sol-proof")]
            assert len(new["steps"]) == len(original["steps"])
            for ours, old in zip(new["steps"], original["steps"]):
                if ours.get("uses", "").startswith("actions/checkout@"):
                    ours["uses"] = old["uses"]
                    ours["with"] = old.get("with", {})
                elif ours.get("uses", "").startswith("actions/setup-node@"):
                    ours["uses"] = old["uses"]
                elif ours.get("uses", "").startswith("actions/upload-artifact@"):
                    assert ours["with"]["name"].endswith(old["with"]["name"])
                    ours["uses"] = old["uses"]
                    ours["with"]["name"] = old["with"]["name"]
            if row["matrix_changes"]:
                assert row["source"] == ".github/workflows/claude-p18-fabric-rule.yml"
                removed = row["matrix_changes"][0]["removed"]
                assert len(removed) == 1 and removed[0]["probe"] == "cp7_p18_e01_bridge_probe.py"
                assert new["strategy"]["matrix"]["include"] == [r for r in original["strategy"]["matrix"]["include"] if r not in removed]
                new["strategy"]["matrix"]["include"] = original["strategy"]["matrix"]["include"]
            assert new == original, ("UNDECLARED_JOB_DELTA", row["path"], key)
        checks.append(dict(workflow=row["path"], status="PASS_PARSED_DIFF", only_declared_changes=True))

    # Inherited successful r3 Q1 binding. Only pins/lineage change in the SARIF gate itself.
    ql = json.loads((HERE / "CODEQL_PREEXECUTION_MANIFEST.json").read_text())
    original = yaml.safe_load(subprocess.check_output(["git", "-C", str(ROOT), "show",
                    ql["source_seal"] + ":" + ql["source_path"]], text=True))
    actual = yaml.safe_load((ROOT / ql["path"]).read_text())
    old_steps = original["jobs"]["analyze"]["steps"]
    steps = actual["jobs"]["analyze"]["steps"]
    old_gate = next(s for s in old_steps if s.get("name") == "Verify analysis and bind SARIF to candidate")
    gate = next(s for s in steps if s.get("name") == "Verify analysis and bind SARIF to candidate")
    expected = old_gate["run"].replace("b53b5acdf260b03ebac3474e9ae837fcef6f6eb1", ql["product_sha"]).replace(
                    "32f54240a60e01ab8b1ffad7267d285a669be520", ql["product_tree"]).replace(
                    "'metadata_qualification':'SOL_METADATA_Q1','original_run_id':39146762479",
                    "'metadata_qualification':'SOL_R4_FRESH_SOURCE_INHERITED_Q1_BINDING','binding_source_run_id':39150692634,'historical_metadata_failure_run_id':39146762479")
    assert gate["run"] == expected, "CODEQL_ORACLE_DELTA_NOT_DECLARED"
    for name in ("Compile isolated PostgreSQL clock fixture for analysis",):
        assert next(s for s in steps if s.get("name") == name) == next(s for s in old_steps if s.get("name") == name)
    for verb in ("init", "analyze"):
        assert next(s for s in steps if s.get("uses", "").startswith("github/codeql-action/" + verb + "@")) == next(
                    s for s in old_steps if s.get("uses", "").startswith("github/codeql-action/" + verb + "@"))
    assert actual["jobs"]["analyze"]["strategy"] == original["jobs"]["analyze"]["strategy"]
    assert not any("GITHUB_SHA" in s.get("env", {}) for s in steps)
    for s in steps:
        if "SOL_IDENTITY" in s.get("run", ""):
            inline(s, "SOL_IDENTITY")
    script = inline(gate, "SOL_CODEQL_METADATA")
    parsed = ast.parse(script)
    pure_bind_module = ast.Module(body=[n for n in parsed.body if isinstance(n,
                        (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign))], type_ignores=[])
    env = {}
    exec(compile(pure_bind_module, "pure_metadata_binding_only", "exec"), env)
    bind = env["bind_identity"]
    workflow = "3eb1edd795efdbfb77a57c9165f05d5d5dc8ca13"
    bind(ql["product_sha"], ql["product_tree"], workflow)
    tests = [dict(id="CODEQL_EXACT_PRODUCT_DISTINCT_WORKFLOW", status="PASS")]
    for name, args in [("CODEQL_WRONG_PRODUCT", (workflow, ql["product_tree"], workflow)),
                       ("CODEQL_WRONG_TREE", (ql["product_sha"], "0" * 40, workflow)),
                       ("CODEQL_INVALID_WORKFLOW", (ql["product_sha"], ql["product_tree"], "bad"))]:
        try:
            bind(*args)
        except ValueError:
            tests.append(dict(id=name, status="PASS_EXPECTED_REFUSAL"))
        else:
            raise AssertionError(name)
    report = dict(scope="PARSED_WORKFLOW_AND_PURE_METADATA_VALIDATION_ONLY", workflow_checks=checks,
                  regression_workflows=len(checks), regression_job_phases=phases, codeql_matrix_phases=4,
                  codeql_scan_and_sarif_oracle_unchanged=True, codeql_metadata_tests=tests,
                  no_business_or_access_probe_executed=True,
                  prepublication_issue="One CodeQL identity comment replacement initially caused IndentationError; caught by compile before publication. Clean inline metadata script now compiles.")
    (HERE / "REGRESSION_WORKFLOW_VALIDATION.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("regression_workflows", "regression_job_phases", "codeql_matrix_phases", "codeql_metadata_tests")}))


if __name__ == "__main__":
    main()
