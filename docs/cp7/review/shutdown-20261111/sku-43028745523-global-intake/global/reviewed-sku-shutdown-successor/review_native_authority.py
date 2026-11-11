"""Report all Global D1/E authority differences before any installer connection."""
import argparse
import importlib.util
import json
from pathlib import Path

from compare_sku_catalogue import checked_catalogue
from prepare_global_sku_source import closed_source
from reviewed_sku_source import CANDIDATE, CANDIDATE_TREE
from review_sku_hpp_authority import corrected_rows
from verify_terminal_sku import CATALOGUE, catalogue, fields, pin, require, strict

AREA = "scripts/cp7_global_nonpo_envelope/"
ROUTES = "scripts/current-global-sku-automatic-preparation/routes.py"
NATIVE_MANIFEST = dict(bytes=8656, sha256="9dcdfea2fde027d54f2ef2888ca2d07154a89b072da458ef893cdcea5e652e09")
OWNER_FIELDS = (
    "definition", "owner", "language", "kind", "security_definer", "leakproof",
    "strict", "returns_set", "volatility", "parallel", "cost", "estimated_rows",
    "config", "argument_names", "argument_modes", "arguments", "result",
    "support", "raw_acl",
)


def load_source(path):
    spec = importlib.util.spec_from_file_location("global_exact_current_observer_for_diagnostic", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def references(checkout, sku_checkout):
    manifest = closed_source(checkout)
    native_raw = (checkout / (AREA + "SOURCE.json")).read_bytes()
    require(pin(native_raw) == NATIVE_MANIFEST, "GLOBAL_NATIVE_DIAGNOSTIC_EXACT_NATIVE_MANIFEST")
    native_manifest = strict(native_raw)

    def read(name):
        raw = (checkout / name).read_bytes()
        owner = native_manifest if name.startswith(AREA) else manifest
        require(pin(raw) == owner["files"][name], "GLOBAL_NATIVE_DIAGNOSTIC_SOURCE_CHANGED:" + name)
        return raw

    owners = strict(read(AREA + "NATIVE_OWNING_REFERENCE.json"))["functions"]
    work = strict(read(AREA + "NATIVE_SCOPE_WORK_REFERENCE.json"))["columns"]
    scope = {name: row for columns in work.values() for name, row in columns.items()}
    graph = strict(read(AREA + "graph_helpers/AUTHORITY.json"))["actual_source_profile"]
    read(ROUTES)
    routes = load_source(checkout / ROUTES)
    observed, _, _, _, _ = routes.prior.expected_authority()
    automatic, _ = routes.sources()
    require(len(owners) == 8 and len(scope) == 73 and len(observed) == 19,
            "GLOBAL_NATIVE_DIAGNOSTIC_EXACT_REFERENCE_SET")
    changed, originals, corrected = corrected_rows(sku_checkout, routes.prior)
    require(observed[changed] == originals[changed]
            and set(corrected) & set(observed) == {changed},
            "GLOBAL_NATIVE_DIAGNOSTIC_ROUNDING_AUTHORITY_PREIMAGE")
    observed = observed | corrected
    result = {"functions": {}, "columns": dict(scope), "relations": {"erp.v_current_hpp": graph["view_relation"]}}
    reasons = {}

    def add(group, name, row, reason):
        entries = result.setdefault(group, {})
        require(name not in entries or entries[name] == row, "GLOBAL_NATIVE_DIAGNOSTIC_CONFLICTING_EXPECTATIONS:" + name)
        entries[name] = row
        reasons.setdefault((group, name), []).append(reason)

    for name, row in owners.items():
        add("functions", name, row, "native_owning_hook")
    for name, row in observed.items():
        add("functions", name, row, "sku_cent_rounding" if name in corrected else "graph_authority")
    for group, rows in automatic["groups"].items():
        for name, row in rows.items():
            add(group, name, row, "automatic_addition")
    for name, row in automatic["replacement_functions"].items():
        add("functions", name, row, "automatic_replacement")
    return result, reasons


def compare(actual, expected, reasons):
    problems, counts = [], {}
    for group, rows in sorted(expected.items()):
        counts[group] = len(rows)
        for name, expected_row in sorted(rows.items()):
            actual_row = actual.get(group, {}).get(name)
            if actual_row == expected_row:
                continue
            failure = {"group": group, "identity": name, "expected_by": reasons.get((group, name), ["native_scope_or_view"])}
            if actual_row is None:
                failure["kind"] = "MISSING"
            elif group == "functions" and type(actual_row) is list and len(actual_row) == len(OWNER_FIELDS):
                failure.update(kind="METADATA_OR_DEFINITION_CHANGED",
                               fields=[field for field, old, new in zip(OWNER_FIELDS, expected_row, actual_row) if old != new])
            else:
                failure["kind"] = "ROW_CHANGED"
            failure["expected_row"] = pin(json.dumps(expected_row, ensure_ascii=False, separators=(",", ":")).encode())
            failure["actual_row"] = None if actual_row is None else pin(json.dumps(actual_row, ensure_ascii=False, separators=(",", ":")).encode())
            problems.append(failure)
    return {"compared_rows": counts, "problems": problems}


def admitted_catalogue(receipt_raw, receipt_sha256, root_raw, raw):
    require(pin(receipt_raw)["sha256"] == receipt_sha256, "GLOBAL_NATIVE_DIAGNOSTIC_RECEIPT_PIN_CHANGED")
    receipt, root = strict(receipt_raw), strict(root_raw)
    fields(receipt, dict(status="SKU_TERMINAL_ORIGINAL_BYTES_VERIFIED", head=CANDIDATE, conclusion="success",
                         attempt=1, root_pin=pin(root_raw), actual_case_credit=27, actual_all_five=True,
                         actual_outer_restore=True, actual_worker_reaped=True, all_member_crc_verified=True,
                         github_disposable_cleanup_success=True), "GLOBAL_NATIVE_DIAGNOSTIC_ACTUAL_SKU_REQUIRED")
    fields(root, dict(status="ROOT_VERIFIED_CURRENT_SKU_NATIVE25_BROWSER2_ALL5", head=CANDIDATE, tree=CANDIDATE_TREE,
                      run_id=receipt["run_id"], job_id=receipt["job_id"], artifact_id=receipt["artifact_id"],
                      actual_business_cases=27, package_all_five=True, actual_outer_restore=True,
                      mandor_evidence_mode="CUMULATIVE_15_PLUS_2", prior_runs_aggregated=False,
                      complete_global_input_review=False, production_go=False), "GLOBAL_NATIVE_DIAGNOSTIC_SAME_RUN_ROOT_REQUIRED")
    observation = root["global_parent_catalogue"]
    original_pin = pin(raw)
    require(receipt["global_parent_catalogue"] == observation
            and root["originals"][CATALOGUE] == original_pin
            and observation["original"] == dict(name=CATALOGUE, **original_pin)
            and {key: receipt["members"][CATALOGUE][key] for key in original_pin} == original_pin,
            "GLOBAL_NATIVE_DIAGNOSTIC_CANONICAL_FULL25_REQUIRED")
    catalogue(raw, dict(status="ACTUAL_FULL25_SKU_CATALOGUE_OBSERVED", head=root["head"], run_id=str(root["run_id"]),
                        attempt=1, original=observation["original"], readers=observation["exact_query_sources"],
                        fingerprint=observation["fingerprint"], actual_ERP_case_credit=0,
                        complete_input_review=False, production_go=False), root["head"], root["run_id"])
    return checked_catalogue(raw), root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("receipt", "root", "catalogue", "checkout", "sku-checkout", "output"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--receipt-sha256", required=True)
    args = parser.parse_args()
    raw = args.catalogue.read_bytes()
    actual, root = admitted_catalogue(args.receipt.read_bytes(), args.receipt_sha256, args.root.read_bytes(), raw)
    expected, reasons = references(args.checkout.resolve(), args.sku_checkout.resolve())
    result = compare(actual, expected, reasons)
    result.update(status="GLOBAL_NATIVE_AUTHORITY_DIAGNOSTIC_DIFFERENCES" if result["problems"] else "GLOBAL_NATIVE_AUTHORITY_REFERENCE_ROWS_MATCH",
                  run_id=root["run_id"], job_id=root["job_id"], sku_commit=CANDIDATE, actual_catalogue=pin(raw),
                  actual_ERP_cases=0, runtime_admission=False, complete_input_review=False, production_go=False)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
