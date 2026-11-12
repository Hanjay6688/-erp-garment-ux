"""Verify the focused continuations against the actual frozen derivation inputs."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    root, destination = map(Path, sys.argv[1:])
    owner = root / "scripts/current-sku-automatic-composite-preparation"
    entry = module("test_exact_focused_owning_entry", owner / "qualification.py")
    parent, money, plan, _ = entry.actual_inputs()
    focus = entry.continuation.admitted(plan)
    ids = tuple(focus["planned_case_ids"])
    executed = []
    callbacks = [(case, lambda key=case: executed.append(key)) for case in ids]
    original = SimpleNamespace(IDS=ids, cases=lambda _cursor, _today: callbacks)
    selected = entry.continuation.select(original, focus)
    for _, callback in selected.cases(None, None):
        callback()
    assert executed == focus["fresh_case_ids"]
    assert set(executed).isdisjoint(focus["retained_case_ids"])
    bad = SimpleNamespace(IDS=ids, cases=lambda _cursor, _today: callbacks[::-1])
    try:
        entry.continuation.select(bad, focus).cases(None, None)
    except ValueError as error:
        assert str(error) == "SKU_E4EA_CONTINUATION_CALLBACK_ORDER_CHANGED"
    else:
        raise AssertionError("Changed full callback order admitted")
    native_raw = (entry.FROZEN_SKU / entry.component.ORIGINAL).read_bytes()
    native, native_proof = entry.component.derive(native_raw, focused=True)
    assert native.count("business=_CONTINUATION.select(business,_FOCUS)") == 1
    assert native.count("qualification_scope='FRESH_AUTOMATIC5_AND_CURRENT_BROWSER2'") == 1
    assert native.count("SKU_MONEY_USED_INVERSE_NOT_REFUSED") == 1
    assert native.count("_BROWSER_ACCESS.run(product,state,verify,report)") == 1
    assert "business.n.capture(cursor)" in native and "prefix.strict_rollback(before,after)" in native
    donor = entry.package_source.load("focused_retained_package_source", entry.package_source.RETAINED)
    pack_raw = (entry.FROZEN_PARENT / donor.ORIGINAL).read_bytes()
    package, package_proof = entry.package_source.derive(pack_raw, focused=True)
    assert package.count("'CURRENT_PARENT_SKU_MONEY_AUTOMATIC_CONTINUATION_BROWSER2'") == 1
    assert "BASELINE_RESTORE" in package and "report['actual_browser_cases']" in package
    gate = module("test_exact_focused_gate", owner / "final_gate.py")
    code, gate_proof = gate.derive(gate.RETAINED.read_bytes(), focused=True)
    assert code.count("actual_Native_cases=5") == 3
    assert code.count("actual_business_cases=7") == 1
    assert code.count("counts={'PASS':5}") == 1
    assert "SKU_COMPOSITE_GATE_ALL_FIVE_ACTUAL_PACKAGE_GATES" in code
    assert "SKU_COMPOSITE_GATE_WORKER_REAPED_AND_FULL_RECOVERY_BUDGETS" in code
    compile(code, "exact_focused_final_gate", "exec")
    result = {
        "status": "EXACT_FOCUSED_SOURCE_AND_DERIVATIONS_PASS",
        "candidate": subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip(),
        "tree": subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD^{tree}"],text=True).strip(),
        "declared_case_count": len(ids),
        "actual_new_erp_cases": 0,
        "fresh_native_ids": executed,
        "retained_native_ids": focus["retained_case_ids"],
        "original_case_scope_pin": entry.continuation.SCOPE_PIN,
        "native_derivation": native_proof,
        "package_derivation": package_proof,
        "gate_derivation": gate_proof,
    }
    (destination / "FOCUSED_SOURCE_DERIVATION_RECEIPT.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "candidate", "tree", "declared_case_count",
                                                   "actual_new_erp_cases", "fresh_native_ids", "original_case_scope_pin")}, sort_keys=True))


if __name__ == "__main__":
    main()
