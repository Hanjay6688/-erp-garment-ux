"""Prepare copies of existing writer qualification workflows; no business probe is authored here."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BRANCH = "audit/sol-cp1-7-r4-663f6fae-20261019"
CANDIDATE = "663f6faefcbb9c70f0f99bbc7e78164e03521329"
CHECKOUT = "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
UPLOAD = "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
SETUP_NODE = "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020"

# A repeated entrypoint is represented by the complete canonical invocation below, not rerun for a different colour.
EXCLUDED = {
    "claude-cp17-fixes": "Already requested as the complete separate CP17 wave; 341 exact IDs remain canonical there.",
    "claude-p19-capture-diagnosis": "Diagnostic 100/300 subset. The complete P19 scale5 qualification already executes capture_diagnosis at both sizes.",
    "cp7-group-end-diagnosis": "Diagnosis-only run; zero product acceptance credit. r3 source-bound diagnostic retained.",
    "cp7-native-read-diagnostic": "Diagnosis-only run; zero product acceptance credit. r3 source-bound diagnostic retained.",
    "cp7-note-command-diagnostic": "Diagnosis-only run; zero product acceptance credit. r3 source-bound diagnostic retained.",
    "cp7-note-correction": "Same complete run-step sequence and environment as claude-note-correction; canonical invocation there.",
    "cp7-supplier-payment-correction": "Same complete run-step sequence and environment as claude-supplier-payment-correction; canonical invocation there.",
    "cp7-f03-p13-regression": "Identical p13 bucket is included in all eight buckets of cp7-f03-full.",
    "cp7-f04-model": "Same model entrypoint in claude-pl-native; that runtime also pins jsonschema 4.25.1.",
    "cp7-f04-netting": "Same netting entrypoint in claude-pl-native; complete case provider unchanged.",
    "cp7-f04-schedule": "Same schedule entrypoint in claude-pl-native; complete case provider unchanged.",
    "cp7-f04-supply": "Same supply entrypoint in claude-pl-native; complete case provider unchanged.",
    "cp7-f04-plan": "Same plan39 entrypoint in claude-p08-physical; complete run-step sequence except matrix substitution.",
    "cp7-f05-analysis": "Same analysis152 entrypoint in claude-p08-physical; complete run-step sequence except matrix substitution.",
    "cp7-f05-attention": "Same attention284 entrypoint in claude-p08-physical. Extra original155 historical artifact diagnostics remain retained r3; not new candidate runtime cases.",
    "cp7-rule-lifecycle": "Same rule-lifecycle16 entrypoint in claude-p18-fabric-rule; complete run-step sequence except matrix substitution.",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(phase, workdir="auditor"):
    source = "../sol" if workdir == "auditor" else "sol"
    out = "cp6-proof/t3" if workdir == "auditor" else "audit-sol-proof"
    step = dict(name=f"Sol record exact candidate and product trees {phase}",
                run=f"python {source}/audit/sol_cp17_r4/record_candidate.py --root . --phase {phase} --out {out}/SOL_R4_IDENTITY_{phase.upper()}.json")
    if workdir == "auditor":
        step["working-directory"] = workdir
    if phase == "after":
        step["if"] = "always()"
    return step


def make(source, slug, common):
    original = yaml.safe_load(source.read_text())
    own = deepcopy(original)
    own.pop(True, None)  # YAML 1.1 reads an unquoted `on` as True.
    target = ROOT / ".github/workflows" / f"audit-sol-r4-{slug}.yml"
    own["name"] = f"AUDIT/Sol/r4/{slug}"
    own["run-name"] = f"AUDIT/r4/Sol/663f6fae/{slug}/1"
    own["on"] = {"push": {"branches": [BRANCH], "paths": [str(target.relative_to(ROOT))]}, "workflow_dispatch": {}}
    own["permissions"] = {"contents": "read", "actions": "read"}
    own["concurrency"] = {"group": f"audit-sol-r4-{slug}-${{{{ github.run_id }}}}", "cancel-in-progress": False}
    matrix_changes = []
    for key, job in own["jobs"].items():
        steps = job["steps"]
        checkouts = [s for s in steps if s.get("uses", "").startswith("actions/checkout@")]
        assert checkouts, (source, key)
        product = next((s for s in checkouts if s.get("with", {}).get("path") == "auditor"), None) if common else checkouts[0]
        assert product is not None, (source, key, "candidate checkout not found")
        product["uses"] = CHECKOUT
        product.setdefault("with", {}).update(ref=CANDIDATE, **{"persist-credentials": False})
        position = steps.index(product) + 1
        steps.insert(position, {"uses": CHECKOUT, "with": {"path": "sol", "fetch-depth": 1,
                          "sparse-checkout": "audit/sol_cp17_r4", "persist-credentials": False}})
        before = next((i for i,s in enumerate(steps) if s.get("name") == "Install pinned disposable runtime"), position + 1)
        steps.insert(before, identity("before", "auditor" if common else "."))
        after = next((i for i,s in enumerate(steps) if s.get("name") == "Remove disposable database"), len(steps))
        steps.insert(after, identity("after", "auditor" if common else "."))
        for step in steps:
            uses = step.get("uses", "")
            if uses == "actions/setup-node@v4":
                step["uses"] = SETUP_NODE
            if uses.startswith("actions/upload-artifact@"):
                step["uses"] = UPLOAD
                step["with"]["name"] = f"audit-r4-Sol-663f6fae-{slug}-" + step["with"]["name"]
        if not common:
            steps.append({"uses": UPLOAD, "if": "always()", "with": {"name": f"audit-r4-Sol-663f6fae-{slug}-identity",
                            "path": "audit-sol-proof", "retention-days": 30, "if-no-files-found": "error"}})
        if source.stem == "claude-p18-fabric-rule":
            old = job["strategy"]["matrix"]["include"]
            removed = [r for r in old if r["probe"] == "cp7_p18_e01_bridge_probe.py"]
            assert len(removed) == 1
            job["strategy"]["matrix"]["include"] = [r for r in old if r not in removed]
            matrix_changes.append({"removed": removed, "canonical": "cp7-p18-e01-bridge", "reason": "The separate workflow additionally verifies browser loading; retain that complete entrypoint once."})
    target.write_text(yaml.safe_dump(own, sort_keys=False, width=120))
    assert yaml.safe_load(target.read_text()) == own
    return dict(source=str(source.relative_to(ROOT)), source_sha256=digest(source), path=str(target.relative_to(ROOT)),
                sha256=digest(target), classification="EXISTING_WRITER_QUALIFICATION_INDEPENDENT_SOL_EXECUTION",
                oracle_origin="WRITER_SOURCE_PINNED", fixture_origin="WRITER_SYNTHETIC_DISPOSABLE",
                matrix_changes=matrix_changes, job_keys=list(own["jobs"]))


def main():
    dependency = json.loads((HERE / "STATIC_GUARD_DEPENDENCY_MAP.json").read_text())
    selected = [ROOT / row["workflow"] for row in dependency["affected_workflows"] if Path(row["workflow"]).stem not in EXCLUDED]
    records = [make(p, p.stem.removeprefix("claude-").removeprefix("cp7-"), True) for p in selected]
    records += [make(ROOT / ".github/workflows/ci.yml", "build-ux", False),
                make(ROOT / ".github/workflows/ui-phone-width.yml", "phone-census", False)]
    sources = {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / "scripts").glob("cp7*.py"))}
    sources.update({str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / "scripts").glob("cp7*.mjs"))})
    # Keep all declaration/provider bytes frozen; literal inventory is a conservative index, not a fabricated exact case budget.
    literal_ids = sorted({s for p in sorted((ROOT / "scripts").glob("cp7*")) if p.suffix in (".py", ".mjs")
                         for s in re.findall(r"['\"]([A-Z][A-Z0-9_]{7,})['\"]", p.read_text())})
    (HERE / "REGRESSION_SOURCE_FREEZE.json").write_text(json.dumps(dict(candidate_sha=CANDIDATE,
         purpose="Pre-execution immutable source/provider inventory; not all literal strings are case IDs.",
         scripts_tree="793d6ea67f482254a5baff04cfa6e83d306ca091", provider_sha256=sources,
         conservative_uppercase_literal_index=literal_ids), indent=2) + "\n")
    manifest = dict(contract="audit.sol.r4.regression.preexecution.v1", candidate_sha=CANDIDATE,
                    candidate_tree="023f3554432f80f994439f5d0b8cc164846a2041", own_branch=BRANCH,
                    classification="AUTHORIZED_EXISTING_QUALIFICATIONS_ONLY_NO_NEW_BUSINESS_OR_ACCESS_PROBES",
                    risk_basis="R4-05 changes a global guard. Conservative AST reachability identifies 57 writer workflows; execute distinct business qualifications, retain duplicate/diagnosis-only sources explicitly.",
                    existing_cp17_wave_run=39184657689, affected_writer_workflows=57,
                    workflows=records, excluded_workflows=EXCLUDED,
                    source_freeze_sha256=digest(HERE / "REGRESSION_SOURCE_FREEZE.json"),
                    expected_contract="PREEXECUTION_PLAN.md", exact_case_ids_cp17="CP17_PREEXECUTION_MANIFEST.json",
                    case_budget_rule="Regression case identities/counts are defined by pinned provider and declaration bytes; expand per group and check each result multiset. A conservative string index is not an exact mandatory-case inventory, and earns no independent-oracle credit.",
                    first_result_policy="Keep every first result and internal helper attempt; no post-case identical rerun for green.",
                    identity_deltas="Separate workflow/product checkout and SHA, read-only before/after identity hooks and prefixed artifacts; immutable candidate. Root historical checkouts untouched.",
                    product_test_edits=False, limits_or_expected_values_changed=False,
                    held_r3_probes_included=False, backup_patch_applied=False,
                    hosted_or_production_writes=False, peer_r4_evidence_read=False,
                    static_codeql="Existing candidate CodeQL Q1 gate to be prepared separately with product/workflow identities distinct.",
                    gates_before_results=dict(feature_complete=False, audit_complete=False, production_go=False))
    (HERE / "REGRESSION_PREEXECUTION_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(dict(affected=57, excluded=len(EXCLUDED), regression_workflows=len(records),
                          source_files=len(sources), literal_index=len(literal_ids), paths=[r["path"] for r in records]), indent=2))


if __name__ == "__main__":
    main()
