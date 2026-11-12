"""Read the two exact completed SKU Originals and validate the narrow source repair."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[1]
AUTO_HEAD = "9b1b0fcc9fbf477634619f07d4628d5be3a1b634"
AUTO_TREE = "14de92a9d9c321cad0a513de28c164b4ba12de77"
E4EA = "e4eaaecebad1f0ba11ab1542b5df89a6423a8a1e"
A165 = "a1652a808f5f9e7a5bcc3fe0ea0feb081075adc3"
CASE_PLAN = OWNER / "PREPARED_NATIVE25_PLAN.json"
NATIVE_FILE = "CP7_SKU_CURRENT_PARENT_MONEY_AUTOMATIC_QUALIFICATION.json"
ACTUAL_CATALOG = "SKU_GLOBAL_PARENT_ACTUAL_FULL25.json"
EXACT_CONTEXT_CASE = "SKU_AUTOMATIC_NATIVE_LATE_TARGET_REFUSAL_ROLLS_BACK_PARENT_AND_CHILD"


def pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def open_exact(path, bytes_expected, expected, crc):
    with path.open("rb") as stream:
        assert path.stat().st_size == bytes_expected and hashlib.file_digest(stream, "sha256").hexdigest() == expected
    archive = ZipFile(path)
    assert len(archive.infolist()) == len(set(archive.namelist())) == crc and archive.testzip() is None
    return archive


def catalog(archive, expected):
    raw = archive.read(ACTUAL_CATALOG)
    assert pin(raw) == {"bytes": 16048163, "sha256": expected}
    return json.loads(raw)


def changed_rows(before, after):
    assert set(before) == set(after)
    out = {}
    for group in before:
        prior = dict(before[group])
        current = dict(after[group])
        assert len(prior) == len(before[group]) and len(current) == len(after[group]), group
        changed = sorted(key for key in prior.keys() | current.keys() if prior.get(key) != current.get(key))
        if changed:
            out[group] = changed
    return out


def retained_cases(original):
    plan_raw = CASE_PLAN.read_bytes()
    assert pin(plan_raw) == {"bytes": 2762, "sha256": "df9837324b15cba9be756a27e27776fa11f1a153e01ee2ee0fa296aa9ddeb1a8"}
    plan = json.loads(plan_raw)["case_ids"]
    main = json.loads(original.read(NATIVE_FILE))
    assert main["qualification_commit"] == E4EA and main["status"] == "INCOMPLETE"
    assert main["cp6_restored"] is True and main["baseline_full22_all_rows_all_sequences_equal"] is True
    native = next(iter(main["committed"].values()))["native"]
    assert native["planned_case_ids"] == plan and native["complete_boundary_restored"] is True
    results = {}
    for case in plan:
        name = "SKU_AUTOMATIC_CASE_STDOUT/" + hashlib.sha256(case.encode()).hexdigest() + ".jsonl"
        raw = original.read(name)
        row, = map(json.loads, raw.splitlines())
        assert row["case"] == case and row["status"] == native["cases"][case]["status"]
        assert row["full_boundary_restored"] is True and row["public_schema_unchanged"] is True
        assert row["session_leaks"] == {"advisory_locks": 0, "advisory_lock_keys": [], "other_sessions": []}
        results[case] = dict(status=row["status"], original=name, **pin(raw))
    fresh = [case for case in plan if results[case]["status"] == "INCOMPLETE" or case == EXACT_CONTEXT_CASE]
    kept = [case for case in plan if case not in fresh]
    assert len(fresh) == 5 and len(kept) == 20
    assert all(results[case]["status"] == "PASS" for case in kept)
    assert kept[:19] == plan[:19] and kept[-1] == "SKU_AUTOMATIC_NATIVE_ZERO_GOOD_PARENT_HAS_NO_CONVERSION"
    dumps = [n for n in original.namelist() if n.lower().endswith((".sql", ".dump", ".pgdump", ".backup", ".tar"))]
    assert dumps == ["CLONE_install.clone-erp.sql", "CLONE_install.source-erp.sql"] or set(dumps) == {
        "CLONE_install.clone-erp.sql", "CLONE_install.source-erp.sql"
    }
    assert len(dumps) == 2
    census_name = next(n for n in original.namelist() if n.endswith("_FULL_CURRENT_CENSUS.json"))
    census = json.loads(original.read(census_name))
    example = census["before"]["data_and_sequences"]["erp.fg_lots"]
    return {"plan": plan, "fresh": fresh, "kept": kept, "results": results,
            "same_boundary_captures": True, "retained_dump_names": sorted(dumps),
            "census_fg_lots_entry_type": type(example).__name__,
            "census_fg_lots_entry_keys": list(example) if isinstance(example, dict) else len(example)}


def load_adapter():
    path = OWNER / "context_timezone.py"
    spec = importlib.util.spec_from_file_location("exact_timezone_adapter", path)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    return adapter


def verify_adapter(source, actual):
    current = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD", "HEAD^{tree}"], text=True).splitlines()
    assert current == [AUTO_HEAD, AUTO_TREE]
    sys.path.insert(0, str(source / "scripts"))
    from cp7_sku_pending_accounting import derivation
    path = source / "scripts/cp7_sku_automatic_pending"
    raw = (path / "CATALOG_ADDITIONS.json").read_bytes()
    assert pin(raw) == {"bytes": 128694, "sha256": "07824d6732540348590440bca3c8f8aef9a2b58cdcb8af9dc43c964723b0303a"}
    profile = json.loads(raw)
    reader = derivation.derive()
    scope = reader["definitions"]["cp7_sku_conversion.cost_scope_value_v3(uuid,uuid,text)"]
    assert reader["ddl"].count(scope) == 1
    ddl = reader["ddl"].replace(scope, "", 1) + "\n" + (path / "context.sql").read_text()
    adapter = load_adapter()
    product = {"ddl": ddl, "review_marker": "unchanged"}
    candidate, expected = adapter.adapt(product, profile)
    assert candidate["review_marker"] == product["review_marker"]
    assert product["ddl"] == ddl and profile["derived_ddl"] == adapter.PRIOR_DDL
    actual_functions = dict(actual["functions"])
    rows = {}
    for sig, _, _, before, after in adapter.REPAIRS:
        assert actual_functions[sig] == profile["groups"]["functions"][sig]
        a = profile["groups"]["functions"][sig]
        b = expected["groups"]["functions"][sig]
        assert pin(a[0].encode())["sha256"] == before and pin(b[0].encode())["sha256"] == after
        assert [i for i, (x, y) in enumerate(zip(a, b)) if x != y] == [0, 12]
        assert b[12] == ['search_path=""', "TimeZone=UTC"] and b[18] == a[18]
        rows[sig] = b
    assert set(rows) == {name for name, row in profile["groups"]["functions"].items()
                         if row != expected["groups"]["functions"][name]}
    assert expected["derived_ddl"] == pin(candidate["ddl"].encode())
    assert {k for k in profile if profile[k] != expected[k]} == {"derived_ddl", "groups"}
    for bad_product, bad_profile in (
        ({"ddl": ddl + " "}, profile),
        (product, dict(profile, derived_ddl={"bytes": 0, "sha256": "0" * 64})),
    ):
        try:
            adapter.adapt(bad_product, bad_profile)
        except ValueError:
            continue
        raise AssertionError("Stale adapter source admitted")
    compile((OWNER / "assembly.py").read_bytes(), "assembly.py", "exec")
    return {"frozen_head": AUTO_HEAD, "frozen_tree": AUTO_TREE, "patched_ddl": expected["derived_ddl"],
            "changed_catalogue_function_rows": sorted(rows), "no_acl_change": True,
            "stale_source_controls_refused": 2}


def main():
    old_path, prior_path, auto_source, destination = map(Path, sys.argv[1:])
    with open_exact(old_path, 96749933, "dd9e31355a0820d1650e438a8913c49450a10dbc342789ed94f3418c1be6363b", 212) as old:
        scope = retained_cases(old)
        actual = catalog(old, "5ff582717522b766c12024c1bf3299066475f14a3c6021a3543f378f829e0c07")
    with open_exact(prior_path, 3771340, "b92b23d962ab2f91fffcbdf30403140c3dbd11ff89a160c573ac64e12c1abecd", 139) as a165:
        main = json.loads(a165.read(NATIVE_FILE))
        assert main["qualification_commit"] == A165
        prior = catalog(a165, "a90c17fc625cfca373da74c588c165b26fafde21d3b51a1b62228c582ab6677f")
    snapshots = changed_rows(prior, actual)
    related = [sig for sig, row in actual["functions"]
               if re.search(r"to_jsonb\([a-zA-Z_]\w*\)\s*(?:=|<>|is\s+(?:not\s+)?distinct\s+from)", row[0], re.I)]
    out = {
        "status": "E4EA_REPAIR_SOURCE_AND_CASE_SCOPE_VERIFIED",
        "actual_erp_cases": 0,
        "original_scope": scope,
        "same_product_a165_vs_e4ea_catalogue_differences": snapshots,
        "row_json_comparison_source_review": related,
        "adapter": verify_adapter(auto_source, actual),
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "E4EA_SOURCE_SCOPE_PREFLIGHT.json").write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
