#!/usr/bin/env python3
"""Install only in one disposable transaction, capture, roll back, and prove equality."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

from capture_identity import PACKAGE_FINGERPRINT, PRODUCT_HEAD, PRODUCT_TREE, admit
from capture_post_mandor import canonical, capture_cursor
from verify_capture import verify


HERE = Path(__file__).resolve().parent


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def install_t3_package(engine, package_report):
    """Use the same AC–BF installer and verification before the capture."""
    package_run = engine.package
    url = package_run.boundary.ADMIN
    parsed = urlparse(url)
    if (parsed.scheme, parsed.hostname, parsed.port, parsed.path) != (
        "postgresql", "127.0.0.1", 54322, "/cp6_rollback"
    ) or parsed.query or parsed.fragment:
        raise ValueError("CP7_CAPTURE_LOCAL_PACKAGE_DATABASE_REQUIRED")
    before = package_run.ledger(url)
    if before["app"][-1:] != ["v2.6.20ab"] or before["platform_last"] != "20260914190500":
        raise ValueError("CP7_CAPTURE_ALIGNED_AB_REQUIRED")
    if package_run.capsule_compare(url)["equal"] is not True:
        raise ValueError("CP7_CAPTURE_ALIGNED_CAPSULES_REQUIRED")
    if package_run.package.install(package_report)["status"] != "ALL_FILES_INSTALLED":
        raise ValueError("CP7_CAPTURE_COMPLETE_T3_PACKAGE_REQUIRED")
    package_run.verify_awx()
    fingerprint = digest({
        "ledger_start": before,
        "ledger_final": package_run.ledger(url),
        "fingerprint_final": package_run.fingerprint(url),
    })
    if fingerprint != PACKAGE_FINGERPRINT:
        raise ValueError(f"CP7_CAPTURE_T3_PACKAGE_FINGERPRINT_CHANGED:{fingerprint}")
    return fingerprint


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", type=Path, default=HERE / "CAPTURE_SCOPE.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    scope = json.loads(args.scope.read_text())
    sys.path.insert(0, str(admit()))
    if scope["candidate_head"] != PRODUCT_HEAD:
        raise ValueError("CP7_CAPTURE_EXACT_CANDIDATE_REQUIRED")
    import qualification

    args.output.parent.mkdir(parents=True, exist_ok=True)
    engine = qualification.runtime()
    with engine.inherited_admission.parent_scope():
        engine.admitted()
        package_sha = install_t3_package(engine, args.output.parent / "T3_PACKAGE_FILES_INSTALL.json")
        with engine.trusted_installer_connection() as conn, conn.cursor() as cur:
            engine.current_native.acquire_boundary(cur)
            if cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone() != (True,):
                raise ValueError("CP7_CAPTURE_EXPECTED_HOSTED_PROFILE_ON_DISPOSABLE_REQUIRED")
            before = engine.product.mandor.capture(cur)
            parent = engine.install_qualified_parent(cur)
            state = engine.product.install_delta(cur, parent)
            engine.product.verify(cur, state)
            result = capture_cursor(cur, scope, transaction_mode="INSTALL_TRANSACTION_QUERY_ONLY_THEN_ROLLBACK")
            result.update(
                product_tree=PRODUCT_TREE,
                capture_workflow_head=os.environ["GITHUB_SHA"],
                t3_package_sha256=package_sha,
                installed_catalog_sha256=digest(state["after"]),
                baseline_catalog_sha256=digest(before),
                rollback_verified=False,
            )
            conn.rollback()

        with engine.trusted_installer_connection() as check, check.cursor() as cur:
            restored = engine.product.mandor.capture(cur)
            if restored != before:
                raise ValueError("CP7_CAPTURE_ROLLBACK_CATALOG_NOT_IDENTICAL")
            check.rollback()
        result["rollback_verified"] = True
        result["restored_catalog_sha256"] = digest(restored)
        result.pop("capture_sha256", None)
        result["capture_sha256"] = hashlib.sha256(canonical(result)).hexdigest()
        receipt = verify(scope, result)
        if receipt["status"] != "PASS":
            raise ValueError("CP7_CAPTURE_VERIFICATION_FAILED:" + ",".join(receipt["errors"]))
        args.output.write_bytes(canonical(result))
        args.receipt.write_bytes(canonical(receipt))
        print(json.dumps({"status": "PASS", "capture_sha256": result["capture_sha256"], "rollback_verified": True, "acceptance_credit": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
