"""Select affected Native cases and keep historical evidence bound to its origin."""

from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "E4EA_CONTINUATION_SCOPE.json"
SCOPE_PIN = {"bytes":19120,"sha256":"ee12e4984040e6cafa5f1822e43d27c70842190f8fe3eb83bbc8e4383fd0f22c"}
MAIN_SCOPE = "CURRENT_PARENT_SKU_MONEY_AUTOMATIC_CONTINUATION_BROWSER2"
COMPONENT_SCOPE = "FRESH_AUTOMATIC5_AND_CURRENT_BROWSER2"
FRESH_NATIVE = 5
RETAINED_NATIVE = 20


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def pin(raw):
    return {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def admitted(plan_raw):
    require(SCOPE.is_file() and not any(path.is_symlink() for path in (SCOPE, *SCOPE.parents)),
            "SKU_E4EA_CONTINUATION_REQUIRES_EXACT_REGULAR_SCOPE")
    raw = SCOPE.read_bytes()
    require(pin(raw) == SCOPE_PIN, "SKU_E4EA_CONTINUATION_SCOPE_CHANGED")
    scope = json.loads(raw)
    plan = json.loads(plan_raw)["case_ids"]
    kept, fresh, results = (scope[key] for key in ("retained_case_ids", "fresh_case_ids", "original_case_receipts"))
    require(plan == scope["planned_case_ids"] and len(plan) == len(set(plan)) == 25
            and set(results) == set(plan), "SKU_E4EA_CONTINUATION_EXACT_NATIVE25_PLAN_REQUIRED")
    require(len(kept) == RETAINED_NATIVE and len(fresh) == FRESH_NATIVE
            and kept == [case for case in plan if case not in fresh]
            and fresh == [case for case in plan if case not in kept]
            and all(results[case]["status"] == "PASS" for case in kept)
            and sum(results[case]["status"] == "INCOMPLETE" for case in fresh) == 4
            and "SKU_AUTOMATIC_NATIVE_LATE_TARGET_REFUSAL_ROLLS_BACK_PARENT_AND_CHILD" in fresh,
            "SKU_E4EA_CONTINUATION_EXACT_UNAFFECTED_AND_AFFECTED_CASES_REQUIRED")
    return scope


def select(business, scope):
    plan = tuple(scope["planned_case_ids"])
    fresh = tuple(scope["fresh_case_ids"])
    require(business.IDS == plan, "SKU_E4EA_CONTINUATION_CALLBACK_PLAN_CHANGED")

    def cases(cursor, today):
        callbacks = business.cases(cursor, today)
        require(tuple(key for key, _ in callbacks) == plan, "SKU_E4EA_CONTINUATION_CALLBACK_ORDER_CHANGED")
        selected = [item for item in callbacks if item[0] in fresh]
        require(tuple(key for key, _ in selected) == fresh, "SKU_E4EA_CONTINUATION_FRESH_ORDER_CHANGED")
        return selected

    return SimpleNamespace(**dict(vars(business), IDS=fresh, cases=cases))


def catalogue_comparison(value, scope):
    expected = scope["expected_fixed_catalogue_group_pins"]
    require(len(expected) == 25 and set(value) == set(expected), "SKU_E4EA_CONTINUATION_COMPLETE_ACTUAL_FULL25_REQUIRED")
    actual = {group: pin(json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
              for group, rows in value.items()}
    differences = sorted(group for group in actual if actual[group] != expected[group])
    return dict(actual=actual, differing_groups=differences, exact_expected_groups=not differences,
                archived_comparison_still_required=True)
