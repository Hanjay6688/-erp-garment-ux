"""Offline source and selection controls. No DB, network, or product import."""
from pathlib import Path
from hashlib import sha256
import ast
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def check():
    source = json.loads((HERE / "SOURCE.json").read_bytes())
    assert source["contract"] == "cp7.cp6-attendance-day5-exact-selection.v1"
    verified = []
    for path, digest in source["files"].items():
        assert sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
        verified.append(path)
    spec = importlib.util.spec_from_file_location("offline_day5_selection", HERE / "selection.py")
    selection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selection)
    assert source["case_ids"] == list(selection.IDS)
    assert source["label"] == selection.LABEL
    expected = json.loads((ROOT / "scripts/current-cp6-crossflow-qualification/EXPECTED.json").read_bytes())
    ids = expected["phases"]["crossflow"]
    assert expected["count"] == len(ids) == len(set(ids)) == 142
    called = []
    found = [(name, lambda name=name: called.append(name)) for name in ids]
    selected = selection.select_retained(found)
    originals = dict(found)
    assert all(operation is originals[name] for name, operation in selected)
    for _, operation in selected:
        operation()
    assert called == list(selection.IDS), "UNSELECTED_CASE_EXECUTED"
    rejected = 0
    for invalid in (found[:-1], found[:-1] + [found[0]], list(reversed(found))):
        try:
            selection.select_retained(invalid)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("CHANGED_FACTORY_OR_ZONE_ORDER_ACCEPTED")
    assert rejected == 3
    for path in HERE.glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    return dict(status="PASS_OFFLINE_ONLY", source_files=len(verified),
                selected_case_ids=list(selection.IDS), unselected_case_calls=0,
                malformed_selection_controls=rejected, database_calls=0,
                runtime_executions=0, production_go=False, independent_acceptance=False)


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
