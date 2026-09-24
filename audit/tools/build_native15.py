#!/usr/bin/env python3
"""Build the self-contained CP6 fifteen-case audit payload; does not run a DB test.

Original frozen member files remain unchanged. Reconstructed members have new hashes.
Run this file from any directory; outputs are placed beside the scenario sources.
"""
from pathlib import Path
from datetime import date
from decimal import Decimal
import ast
import base64
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "scenarios"
CANDIDATE = "9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc"
FILES = (
    "stock_import_scenario.py",
    "money_dates_scenario.py",
    "business_scenarios_reconstructed.py",
    "import_selector_reconstructed.py",
)
FROZEN = {
    "stock_import_scenario.py": "ff92e8d973ebb75c05ba8ac6b47da96565c9b50760c91b247f331a765d18df81",
    "money_dates_scenario.py": "cfa1157b7ea39e6f5162d85a540ed5e22c30d8fef9ddfe840b5a9bf2f631d9ef",
}


def registration(source, filename):
    """Execute only the pure cases() registrar with literal constants; no imports/DB."""
    tree = ast.parse(source, filename=filename)
    compile(tree, filename, "exec")
    namespace = {"D": Decimal, "Decimal": Decimal}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    namespace[target.id] = value
    case_fn = next(node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == "cases")
    exec(compile(ast.Module(body=[case_fn], type_ignores=[]), filename, "exec"), namespace)
    class NoDatabase:
        def __getattr__(self, name):
            raise AssertionError("Registrar attempted database access: " + name)
    rows = namespace["cases"](NoDatabase(), date(2026, 9, 25))
    if not isinstance(rows, list) or not all(isinstance(r, tuple) and len(r) == 2
                                             and isinstance(r[0], str) and callable(r[1]) for r in rows):
        raise AssertionError("Invalid case registration in " + filename)
    return [r[0] for r in rows]


def build():
    members = []
    planned = []
    for filename in FILES:
        raw = (SCENARIOS / filename).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if filename in FROZEN and digest != FROZEN[filename]:
            raise AssertionError("Frozen source changed: " + filename)
        source = raw.decode("utf-8")
        ids = registration(source, filename)
        members.append(dict(file=filename, sha256=digest, bytes=len(raw),
                            case_ids=ids, source=source,
                            provenance="FROZEN_EXACT" if filename in FROZEN else "RECONSTRUCTED_POST_LOCK"))
        planned.extend(ids)
    if [len(m["case_ids"]) for m in members] != [4, 4, 6, 1]:
        raise AssertionError("Expected 4+4+6+1 cases")
    if len(planned) != 15 or len(set(planned)) != 15:
        raise AssertionError("Planned cases missing or duplicated")

    public_members = [{k: v for k, v in m.items() if k != "source"} for m in members]
    header = '"""CP6 reconstructed audit batch v1: 15 cases; native NOT_RUN until executed.\n'
    header += 'Original eight case sources are preserved byte-for-byte; seven are new reconstructions.\n'
    header += 'Candidate product ' + CANDIDATE + '. No race/HTTP/rollback mode is exercised.\n'
    header += 'Raw case status is a proposed-oracle result, not automatic audit acceptance.\n"""\n'
    payload = header + "import hashlib\n\n"
    payload += "CANDIDATE_PRODUCT_SHA = " + repr(CANDIDATE) + "\n"
    payload += "PLANNED_CASE_IDS = " + repr(tuple(planned)) + "\n"
    payload += "MEMBERS = " + repr(public_members) + "\n"
    payload += "MEMBER_SOURCES = " + repr(tuple(m["source"] for m in members)) + "\n\n"
    payload += '''
def _with_provenance(fn, member, case_id):
    def run():
        row = fn()
        if not isinstance(row, dict) or row.get("status") not in ("PASS", "COUNTEREXAMPLE", "INCOMPLETE", "FAIL"):
            return dict(status="INCOMPLETE", reason="Unsupported result/status",
                        case_id=case_id, member=member["file"], observed=repr(row)[:1200])
        row = dict(row)
        row["auditor_member"] = dict(file=member["file"], sha256=member["sha256"],
                                     provenance=member["provenance"], case_id=case_id)
        row["evidence_scope"] = "Native DB case if executed; no HTTP/browser/race/rollback qualification"
        if case_id.startswith("SI-01"):
            row["oracle_review_required"] = "Optional opening-product binding remains unresolved; raw status is not an accepted defect"
        if case_id.startswith("BLIND-MONEY-CENT"):
            row["rounding_oracle"] = "Original ROUND_HALF_UP endpoint oracle; compare with actual authoritative posted amounts, especially DOWN"
        if case_id.startswith("BCR1-"):
            row["oracle_inference"] = "Dated-prefix rule applied to monetary advance capacity; exact refusal remains unspecified"
        return row
    return run

def cases(cur, today):
    result = []
    for member, source in zip(MEMBERS, MEMBER_SOURCES):
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != member["sha256"]:
            raise RuntimeError("AUDITOR_MEMBER_HASH_MISMATCH")
        namespace = {"__name__": "cp6_auditor_" + member["file"].replace(".", "_")}
        exec(compile(source, "audit/scenarios/" + member["file"], "exec"), namespace)
        rows = namespace["cases"](cur, today)
        if [key for key, fn in rows] != member["case_ids"]:
            raise RuntimeError("AUDITOR_MEMBER_CASE_LIST_MISMATCH")
        result.extend((key, _with_provenance(fn, member, key)) for key, fn in rows)
    actual = [key for key, fn in result]
    if tuple(actual) != PLANNED_CASE_IDS or len(set(actual)) != 15:
        raise RuntimeError("AUDITOR_PLANNED_CASES_MISMATCH")
    return result
'''
    encoded = payload.encode("utf-8")
    compile(payload, "combined_native15_reconstructed.py", "exec")
    b64 = base64.b64encode(encoded).decode("ascii")
    if len(b64) > 64000:
        raise AssertionError("Payload exceeds the chosen 64000-character input budget")
    output = SCENARIOS / "combined_native15_reconstructed.py"
    output.write_bytes(encoded)
    manifest = dict(
        schema_version=1, candidate_product_sha=CANDIDATE, preparation_status="SOURCE_PREPARED_SYNTAX_AND_REGISTRATION_CHECKED",
        native_status="NOT_RUN", run_id=None, job_id=None,
        combined_file=output.name, combined_sha256=hashlib.sha256(encoded).hexdigest(),
        combined_bytes=len(encoded), scenario_b64_characters=len(b64),
        original_lost_combined_sha256="968cac54ac7fa7fe4e3fc1d666e257b04944faf1beec1f45a209274db00869d1",
        original_lost_bytes_recovered=False, planned_case_ids=planned, members=public_members,
        limitations=[
            "Syntax and pure registration checks do not validate database fixtures or native outcomes.",
            "SI01 optional-product oracle unresolved; original SI04 requires ordinary draft-edit privileges.",
            "Money DOWN must be assessed against canonical posted rounding, not blindly copied expectations.",
            "Advance prefix interpretation is an explicit inference; unexpected refusal remains INCOMPLETE.",
            "Selector is UI discovery through workspace data; known-UUID backend retrieval is a positive control.",
            "No side-connection, HTTP credential materialization, rollback qualification, or product fix is included.",
        ],
        dispatch=dict(workflow="cp6-auditor-scenario.yml", phase="after",
                      ref="claude/new-session-deapao",
                      require_current_ref_product_and_tool_review=True,
                      note="Do not dispatch blindly if writer branch has moved; review diff and record checkout/tool SHA separately."))
    (SCENARIOS / "native15_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: manifest[k] for k in ("combined_sha256", "combined_bytes",
                       "scenario_b64_characters", "native_status", "run_id", "job_id")}))
    return manifest


if __name__ == "__main__":
    build()

