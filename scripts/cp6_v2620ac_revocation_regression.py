#!/usr/bin/env python3
"""Run the three authorization-order controls against exact AC clones."""
from __future__ import annotations

import json
import traceback
from pathlib import Path

import cp6_aa_revocation_audit as audit
import cp6_v2620ac_runtime as runtime


ROOT = Path("cp6-proof/writer-ac/revocation")
REPORT = ROOT / "AC_REVOCATION_REGRESSION.json"


def repository_source():
    head, tree = runtime.verify_audit_source()
    return "AC_REGRESSION", head, tree


def verified(cur):
    objects = runtime.verified_successor(cur)
    if len(objects) != 272:
        raise AssertionError("AC_REVOCATION_EXACT_AC_REQUIRED")
    return objects


def clone_source() -> None:
    with audit.connect("ac-clone-verifier") as conn, conn.cursor() as cur:
        verified(cur)


def run() -> dict:
    audit.ROOT = ROOT
    audit.REPORT = REPORT
    audit.verify_repository_source = repository_source
    audit.verify_source_runtime = verified
    audit.verify_clone_source = clone_source
    result = audit.main()
    result.update(
        format="CP6_V2620AC_REVOCATION_REGRESSION_V1",
        business_predecessor_head=runtime.AB_HEAD,
    )
    REPORT.write_text(json.dumps(result, indent=2, default=str) + "\n")
    return result


if __name__ == "__main__":
    try:
        outcome = run()
    except Exception as exc:
        outcome = {
            "status": "INCOMPLETE", "error": str(exc),
            "traceback": traceback.format_exc(), "production_go": False,
        }
        ROOT.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(outcome, indent=2, default=str) + "\n")
    raise SystemExit(
        0 if outcome.get("status") == "PASS_BOUNDED_AUDIT"
        else 1 if outcome.get("status") == "FAIL_NEW_COUNTEREXAMPLE"
        else 2
    )
