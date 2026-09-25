"""Auditor CP6 round 9: contract oracles on frozen writer head d1bc8ad.

W8 uses the frozen independent round-8 cents oracle. The W9 and LAU-T14
fixtures reuse writer builders solely to arrange domain state; PASS is derived
from the resulting values and the ratified C0/M contract, not builder status.
"""
from decimal import Decimal
import importlib.util
from pathlib import Path

import cp6_ba_probe as fixture


def prior_business():
    path = Path(__file__).resolve().parents[1] / "round8" / "gpt_round8.py"
    spec = importlib.util.spec_from_file_location("gpt8_frozen_business", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def w9(cur, today, late):
    actual = fixture.w9_changed_since_filing(cur, today, late)
    if actual.get("status") == "INCOMPLETE" or "report_at_close" not in actual:
        return {"status": "INCOMPLETE", "fixture": actual}
    at_close = actual["report_at_close"]
    after = actual["report_after"]
    common = (
        at_close.get("changed_since_filing") is False
        and at_close.get("status") == "READY"
        and after.get("status") == "READY"
        and actual.get("filing_unchanged") is True
        and actual.get("values_unchanged") is True
    )
    if late:
        correct = (
            common
            and bool(actual.get("booked_after_filing"))
            and after.get("changed_since_filing") is True
        )
    else:
        correct = (
            common
            and not actual.get("booked_after_filing")
            and after.get("changed_since_filing") is False
        )
    return {
        "status": "PASS" if correct else "COUNTEREXAMPLE",
        "oracle": "C0 D01 section 3.4: filing and filed values are immutable; new economic corrections on filed dates remain marked after readiness returns; without new correction the marker stays false",
        "late": late,
        "builder_status_only": actual.get("status"),
        "actual": actual,
    }


def lau_t14(cur, today, later_version):
    actual = fixture.lau_t14_receipt_rate(cur, today, later_version)
    if actual.get("status") == "INCOMPLETE" or "receipt_actual_rate" not in actual:
        return {"status": "INCOMPLETE", "fixture": actual}
    correct = (
        Decimal(str(actual.get("delivery_estimate"))) == Decimal("7")
        and Decimal(str(actual.get("receipt_actual_rate"))) == Decimal("7")
        and Decimal(str(actual.get("receipt_actual_cost"))) == Decimal("70")
        and (actual.get("later_version_rate") == "9") == later_version
    )
    return {
        "status": "PASS" if correct else "COUNTEREXAMPLE",
        "oracle": "Master Pulih 4474: receiving later does not reprice a posted delivery at the return-day version; 10 PCS at the agreed send rate 7 remain 70",
        "later_version": later_version,
        "builder_status_only": actual.get("status"),
        "actual": actual,
    }


def cases(cur, today):
    frozen = dict(prior_business().cases(cur, today))
    targets = [
        "G8:MULTI_CENT_DIRECT_UP",
        "G8:MULTI_CENT_DIRECT_DOWN",
        "G8:MULTI_CENT_INVOICE_UP",
        "G8:MULTI_CENT_INVOICE_DOWN",
    ]
    assert all(name in frozen for name in targets)
    return [
        ("G9:W8:" + name, frozen[name]) for name in targets
    ] + [
        ("G9:W9:POST_FILING_CORRECTION", lambda: w9(cur, today, True)),
        ("G9:W9:NO_NEW_CORRECTION_CONTROL", lambda: w9(cur, today, False)),
        ("G9:LAU_T14:SEND_RATE_AFTER_UPDATE", lambda: lau_t14(cur, today, True)),
        ("G9:LAU_T14:UNCHANGED_RATE_CONTROL", lambda: lau_t14(cur, today, False)),
    ]
