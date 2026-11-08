#!/usr/bin/env python3
"""Fail-closed verification for a post-Mandor catalog capture."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from capture_identity import PACKAGE_FINGERPRINT, PRODUCT_TREE


ROOT = Path(__file__).resolve().parent


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def verify(scope: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if capture.get("candidate_head") != scope["candidate_head"]:
        errors.append("CANDIDATE_HEAD_MISMATCH")
    if capture.get("source_failure_run_id") != scope["source_failure_run_id"]:
        errors.append("SOURCE_FAILURE_RUN_ID_MISMATCH")
    transactional = capture.get("transaction_mode") == "INSTALL_TRANSACTION_QUERY_ONLY_THEN_ROLLBACK"
    if transactional:
        safe_capture = capture.get("read_only_transaction") is False and capture.get("rollback_verified") is True
    else:
        safe_capture = capture.get("transaction_mode") == "READ_ONLY_TRANSACTION" and capture.get("read_only_transaction") is True
    if not safe_capture:
        errors.append("READ_ONLY_OR_EXACT_ROLLBACK_NOT_PROVEN")
    if transactional:
        if not isinstance(capture.get("capture_github_run_id"), int) or capture.get("capture_github_run_id") <= 0:
            errors.append("CAPTURE_GITHUB_RUN_ID_REQUIRED")
        if capture.get("capture_github_run_attempt") != 1:
            errors.append("CAPTURE_GITHUB_ATTEMPT_ONE_REQUIRED")
        if not re.fullmatch(r"refs/heads/astra-a/mandor-predecessor-capture-[0-9]{8}", capture.get("capture_github_ref") or ""):
            errors.append("CAPTURE_GITHUB_APPROVED_REF_REQUIRED")
        workflow_head = capture.get("capture_workflow_head") or ""
        if not re.fullmatch(r"[a-f0-9]{40}", workflow_head) or workflow_head == scope["candidate_head"]:
            errors.append("CAPTURE_WORKFLOW_HEAD_REQUIRED")
        if capture.get("product_tree") != PRODUCT_TREE or capture.get("t3_package_sha256") != PACKAGE_FINGERPRINT:
            errors.append("CAPTURE_PRODUCT_TREE_OR_PACKAGE_MISMATCH")
        baseline = capture.get("baseline_catalog_sha256") or ""
        installed = capture.get("installed_catalog_sha256") or ""
        if not re.fullmatch(r"[a-f0-9]{64}", baseline) or capture.get("restored_catalog_sha256") != baseline:
            errors.append("CAPTURE_RESTORE_DIGEST_MISMATCH")
        if not re.fullmatch(r"[a-f0-9]{64}", installed) or installed == baseline:
            errors.append("CAPTURE_INSTALLED_CATALOG_DIGEST_REQUIRED")
    if capture.get("production_go") is not False or capture.get("acceptance_credit") != 0:
        errors.append("CAPTURE_MUST_NOT_GRANT_ACCEPTANCE")
    routines = capture.get("routines") or {}
    relations = capture.get("relations") or {}
    if set(routines) != set(scope["required_routines"]):
        errors.append("ROUTINE_SET_MISMATCH")
    if set(relations) != set(scope["required_relations"]):
        errors.append("RELATION_SET_MISMATCH")
    seen_oids: dict[int, str] = {}
    for sig in scope["required_routines"]:
        row = routines.get(sig)
        if not isinstance(row, dict):
            errors.append(f"MISSING_ROUTINE:{sig}")
            continue
        for field in scope["required_capture_fields"]:
            if field not in row:
                errors.append(f"MISSING_FIELD:{sig}:{field}")
        if row.get("signature") != sig:
            errors.append(f"SIGNATURE_MISMATCH:{sig}")
        definition = row.get("function_definition")
        if not isinstance(definition, str) or not definition.startswith("CREATE OR REPLACE FUNCTION"):
            errors.append(f"BAD_FUNCTION_DEFINITION:{sig}")
        elif hashlib.sha256(definition.encode()).hexdigest() != row.get("definition_sha256"):
            errors.append(f"DEFINITION_HASH_MISMATCH:{sig}")
        oid = row.get("oid")
        if not isinstance(oid, int) or oid <= 0:
            errors.append(f"BAD_OID:{sig}")
        elif oid in seen_oids:
            errors.append(f"DUPLICATE_OID:{sig}:{seen_oids[oid]}")
        else:
            seen_oids[oid] = sig
        if row.get("security_definer") is not True:
            errors.append(f"SECURITY_DEFINER_CHANGED:{sig}")
        if row.get("acl_is_null") not in (True, False) or not isinstance(row.get("effective_acl"), list):
            errors.append(f"ACL_PROVENANCE_INCOMPLETE:{sig}")
    for name in scope["required_relations"]:
        row = relations.get(name)
        if not isinstance(row, dict):
            errors.append(f"MISSING_RELATION:{name}")
            continue
        for field in ("oid", "owner", "kind", "persistence", "rls", "force_rls", "acl_is_null", "raw_acl", "columns", "constraints", "triggers", "indexes"):
            if field not in row:
                errors.append(f"MISSING_RELATION_FIELD:{name}:{field}")
    saved_hash = capture.get("capture_sha256")
    unsigned = dict(capture)
    unsigned.pop("capture_sha256", None)
    if saved_hash != hashlib.sha256(canonical(unsigned)).hexdigest():
        errors.append("CAPTURE_HASH_MISMATCH")
    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "classification": "CAPTURE_COMPLETENESS_ONLY_NOT_RUNTIME_ACCEPTANCE",
        "candidate_head": scope["candidate_head"],
        "source_failure_run_id": scope["source_failure_run_id"],
        "capture_github_run_id": capture.get("capture_github_run_id"),
        "capture_workflow_head": capture.get("capture_workflow_head"),
        "product_tree": capture.get("product_tree"),
        "t3_package_sha256": capture.get("t3_package_sha256"),
        "rollback_verified": capture.get("rollback_verified"),
        "routine_count": len(routines),
        "relation_count": len(relations),
        "capture_sha256": saved_hash,
        "errors": errors,
        "production_go": False,
        "acceptance_credit": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("--scope", type=Path, default=ROOT / "CAPTURE_SCOPE.json")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    scope = json.loads(args.scope.read_text())
    capture = json.loads(args.capture.read_text())
    receipt = verify(scope, capture)
    if args.receipt:
        args.receipt.write_bytes(canonical(receipt))
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
