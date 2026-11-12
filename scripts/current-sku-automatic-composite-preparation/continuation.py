"""Select affected Native cases and keep historical evidence bound to its origin."""

from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
SCOPE = HERE / "E4EA_CONTINUATION_SCOPE.json"
SCOPE_PIN = {"bytes": 22999, "sha256": "91a74eeda82feace3cfdc27488841306edb05ff40311c38cda6201af7215a760"}
CONTRACT = "cp7.sku.e4ea-combined-timezone-scope.v1"
MAIN_SCOPE = "CURRENT_PARENT_SKU_MONEY_AUTOMATIC_CONTINUATION_BROWSER2"
COMPONENT_SCOPE = "FRESH_SKU13_AND_CURRENT_BROWSER2"
FRESH_NATIVE = 13
RETAINED_NATIVE = 12
CALLER_TIMEZONE = "Asia/Jakarta"


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
    require(scope['contract'] == CONTRACT and scope['caller_timezone'] == CALLER_TIMEZONE,
            'SKU_COMBINED_REVIEWED_SCOPE_AND_WIB_CALLER_REQUIRED')
    plan = json.loads(plan_raw)["case_ids"]
    kept, fresh, results = (scope[key] for key in ("retained_case_ids", "fresh_case_ids", "original_case_receipts"))
    require(plan == scope["planned_case_ids"] and len(plan) == len(set(plan)) == 25
            and set(results) == set(plan), "SKU_E4EA_CONTINUATION_EXACT_NATIVE25_PLAN_REQUIRED")
    require(len(kept) == RETAINED_NATIVE and len(fresh) == FRESH_NATIVE
            and kept == [case for case in plan if case not in fresh]
            and fresh == [case for case in plan if case not in kept]
            and all(results[case]['status'] == 'PASS' for case in kept)
            and sum(results[case]['status'] == 'INCOMPLETE' for case in fresh) == 4
            and "SKU_AUTOMATIC_NATIVE_LATE_TARGET_REFUSAL_ROLLS_BACK_PARENT_AND_CHILD" in fresh,
            "SKU_E4EA_CONTINUATION_EXACT_UNAFFECTED_AND_AFFECTED_CASES_REQUIRED")
    non_po = set(scope['non_po_affected_case_ids'])
    require(len(non_po) == 8 and non_po <= set(fresh)
            and all(results[case]['status'] == 'PASS' for case in non_po),
            'SKU_COMBINED_EXACT_EIGHT_NON_PO_CASES_REQUIRED')
    return scope


def run_in_wib(cursor, callback):
    # The baseline snapshot sets UTC before the owning case savepoint.
    # The savepoint rollback also restores this transaction-local setting.
    before, = cursor.execute("select set_config('TimeZone', %s, true)", (CALLER_TIMEZONE,)).fetchone()
    require(before == CALLER_TIMEZONE, 'SKU_NON_PO_WIB_SESSION_REQUIRED')
    result = callback()
    after, = cursor.execute("select current_setting('TimeZone')").fetchone()
    require(after == before, 'SKU_NON_PO_WIB_CALLER_CHANGED_DURING_CASE')
    return dict(result, caller_timezone=before)


def select(business, scope):
    plan = tuple(scope["planned_case_ids"])
    fresh = tuple(scope["fresh_case_ids"])
    non_po = set(scope['non_po_affected_case_ids'])
    require(business.IDS == plan, "SKU_E4EA_CONTINUATION_CALLBACK_PLAN_CHANGED")

    def cases(cursor, today):
        callbacks = business.cases(cursor, today)
        require(tuple(key for key, _ in callbacks) == plan, "SKU_E4EA_CONTINUATION_CALLBACK_ORDER_CHANGED")
        selected = [(key, callback) for key, callback in callbacks if key in fresh]
        require(tuple(key for key, _ in selected) == fresh, "SKU_E4EA_CONTINUATION_FRESH_ORDER_CHANGED")
        return [(key, (lambda action=callback: run_in_wib(cursor, action)) if key in non_po else callback)
                for key, callback in selected]

    return SimpleNamespace(**dict(vars(business), IDS=fresh, cases=cases))


def catalogue_comparison(value, scope):
    expected = scope["expected_fixed_catalogue_group_pins"]
    require(len(expected) == 25 and set(value) == set(expected), "SKU_E4EA_CONTINUATION_COMPLETE_ACTUAL_FULL25_REQUIRED")
    actual = {group: pin(json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
              for group, rows in value.items()}
    differences = sorted(group for group in actual if actual[group] != expected[group])
    return dict(actual=actual, differing_groups=differences, exact_expected_groups=not differences,
                archived_comparison_still_required=True)
