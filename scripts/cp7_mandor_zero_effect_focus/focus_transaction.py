#!/usr/bin/env python3
"""Run only the failed Mandor correction path and roll back the whole delta.

The exact owning product is installed in the same disposable transaction as
the focused adapter. The case uses the original Native fixture and equations;
only its catalogue observer is extended to recognize the intentionally added
private objects. No qualification, browser or production credit is emitted.
"""

import argparse
from datetime import date
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import traceback
from types import MethodType
from urllib.parse import urlparse

from focus_identity import PACKAGE_FINGERPRINT, PRODUCT_HEAD, PRODUCT_TREE, admit


HERE = Path(__file__).resolve().parent
INSTALLER_SHA256 = "33cd10071cef9979db6b40a477fcb15382a15ae401fda7404361e894135e2fc2"
RECEIPT_SHA256 = "0f4284775d052225ec5f556c985b840a1b6347b7249458cf67d71e4b5fc93d33"
CASE_ID = "FG_MANDOR_ACTIVE_OFFSET_RETURN_CORRECTION_REFUSE_THEN_LAWFUL_REVERSE_AND_REAL_RETURN_CORRECTION"


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), default=str) + "\n").encode()


def digest(value):
    return sha256(canonical(value)).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def retain_originals(case, product_root, proof_root):
    """Copy every complete Native observation referenced by the exact case."""
    records = {}

    def visit(value):
        if isinstance(value, dict):
            if (isinstance(value.get("path"), str)
                    and value["path"].startswith("MANDOR_NATIVE_ORIGINALS/")
                    and set(("raw", "compressed")).issubset(value)):
                previous = records.setdefault(value["path"], value)
                require(previous == value, "CP7_FOCUS_ORIGINAL_METADATA_CONFLICT:" + value["path"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(case)
    require(records, "CP7_FOCUS_COMPLETE_NATIVE_ORIGINALS_REQUIRED")
    retained = []
    for relative, metadata in sorted(records.items()):
        source = product_root / "cp6-proof/t3" / relative
        packed = source.read_bytes()
        raw = gzip.decompress(packed)
        require(len(packed) == metadata["compressed"]["bytes"]
                and sha256(packed).hexdigest() == metadata["compressed"]["sha256"],
                "CP7_FOCUS_COMPRESSED_ORIGINAL_CHANGED:" + relative)
        require(len(raw) == metadata["raw"]["bytes"]
                and sha256(raw).hexdigest() == metadata["raw"]["sha256"],
                "CP7_FOCUS_RAW_ORIGINAL_CHANGED:" + relative)
        target = proof_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(packed)
        retained.append(dict(path=relative, raw=metadata["raw"], compressed=metadata["compressed"]))
    return retained


def install_t3_package(engine, package_report):
    package_run = engine.package
    url = package_run.boundary.ADMIN
    parsed = urlparse(url)
    require((parsed.scheme, parsed.hostname, parsed.port, parsed.path) ==
            ("postgresql", "127.0.0.1", 54322, "/cp6_rollback")
            and not parsed.query and not parsed.fragment,
            "CP7_FOCUS_LOCAL_PACKAGE_DATABASE_REQUIRED")
    before = package_run.ledger(url)
    require(before["app"][-1:] == ["v2.6.20ab"] and before["platform_last"] == "20260914190500",
            "CP7_FOCUS_ALIGNED_AB_REQUIRED")
    require(package_run.capsule_compare(url)["equal"] is True, "CP7_FOCUS_ALIGNED_CAPSULES_REQUIRED")
    require(package_run.package.install(package_report)["status"] == "ALL_FILES_INSTALLED",
            "CP7_FOCUS_COMPLETE_T3_PACKAGE_REQUIRED")
    package_run.verify_awx()
    fingerprint = digest({
        "ledger_start": before, "ledger_final": package_run.ledger(url),
        "fingerprint_final": package_run.fingerprint(url),
    })
    require(fingerprint == PACKAGE_FINGERPRINT, "CP7_FOCUS_T3_PACKAGE_FINGERPRINT_CHANGED:" + fingerprint)
    return fingerprint


def installer_body():
    installer = HERE / "FOCUSED_INSTALLER.sql"
    receipt_path = HERE / "FOCUSED_INSTALLER_RECEIPT.json"
    raw, receipt_raw = installer.read_bytes(), receipt_path.read_bytes()
    require(sha256(raw).hexdigest() == INSTALLER_SHA256, "CP7_FOCUS_INSTALLER_BYTES_CHANGED")
    require(sha256(receipt_raw).hexdigest() == RECEIPT_SHA256, "CP7_FOCUS_INSTALLER_RECEIPT_CHANGED")
    receipt = json.loads(receipt_raw)
    require(receipt["product_head"] == PRODUCT_HEAD and receipt["product_tree"] == PRODUCT_TREE
            and receipt["postgres_version_num"] == 170006
            and receipt["installer_sha256"] == INSTALLER_SHA256,
            "CP7_FOCUS_INSTALLER_IDENTITY_CHANGED")
    lines = raw.decode().splitlines()
    require(lines[0] == "\\set ON_ERROR_STOP on" and lines[1] == "begin;"
            and lines[-1] == "commit;" and lines.count("begin;") == 1
            and lines.count("commit;") == 1,
            "CP7_FOCUS_SINGLE_TRANSACTION_WRAPPER_REQUIRED")
    return "\n".join(lines[2:-1]) + "\n", receipt


def assert_installed(cur, receipt, *, require_empty=False):
    for signature, expected in receipt["installed_pg_get_functiondef_md5"].items():
        actual = cur.execute("select md5(pg_get_functiondef(%s::regprocedure))", (signature,)).fetchone()[0]
        require(actual == expected, "CP7_FOCUS_INSTALLED_DEFINITION_CHANGED:" + signature + ":" + str(actual))
    if require_empty:
        require(cur.execute("select count(*) from cp7_note_zero_effect.preparations").fetchone() == (0,),
                "CP7_FOCUS_PREMATURE_PREPARATION")
        require(cur.execute("select count(*) from cp7_note_zero_effect.receipts").fetchone() == (0,),
                "CP7_FOCUS_PREMATURE_RECEIPT")


def focused_boundary(self, cur):
    self.admin(cur)
    assert_installed(cur, self._focus_receipt)
    with self.modules.control.product_catalog(cur):
        catalogue = self.modules.product.runtime()[-1]
        return {"actual_all22": catalogue._catalog_rows(cur), "full_data_and_sequences": catalogue._data(cur)}


def prepare_native_case(cur, native, strict_runner):
    """Apply the original Native setup within the same disposable transaction."""
    foundation = native.committed_foundation(cur)
    cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='240s';set local lock_timeout='8s'")
    today = cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
    strict_runner.boundary.historical.prior.set_open_period(cur, date(2026, 8, 31))
    native.admin(cur)
    return today, foundation


def rollback_boundary(cur, product):
    return {
        "catalogue": product.mandor.capture(cur),
        "data_and_sequences": product.runtime()[-1]._data(cur),
    }


def run_case(native, cur, today, case_runner, proof_root):
    try:
        return case_runner(native, cur, today)
    except Exception as error:
        (proof_root / "MANDOR_ZERO_EFFECT_FIRST_FAILURE.json").write_bytes(canonical({
            "status": "INCOMPLETE", "case_id": CASE_ID,
            "workflow_head": os.environ["GITHUB_SHA"], "github_run_id": os.environ["GITHUB_RUN_ID"],
            "github_run_attempt": os.environ["GITHUB_RUN_ATTEMPT"], "error_type": type(error).__name__,
            "sqlstate": getattr(error, "sqlstate", None), "error": str(error),
            "traceback": traceback.format_exc(), "qualification_credit": 0,
        }))
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case-original", type=Path, required=True)
    args = parser.parse_args()
    scope = json.loads((HERE / "FOCUS_SCOPE.json").read_text())
    require(scope["product_head"] == PRODUCT_HEAD and scope["product_tree"] == PRODUCT_TREE
            and scope["case_id"] == CASE_ID, "CP7_FOCUS_SCOPE_CHANGED")
    source_root = admit()
    sys.path.insert(0, str(source_root))
    import qualification

    args.output.parent.mkdir(parents=True, exist_ok=True)
    engine = qualification.runtime()
    with engine.inherited_admission.parent_scope():
        engine.admitted()
        package_sha = install_t3_package(engine, args.output.parent / "T3_PACKAGE_FILES_INSTALL.json")
        sql, installer_receipt = installer_body()
        with engine.trusted_installer_connection() as conn, conn.cursor() as cur:
            engine.current_native.acquire_boundary(cur)
            require(cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone() == (True,),
                    "CP7_FOCUS_EXPECTED_HOSTED_PROFILE_ON_DISPOSABLE_REQUIRED")
            before = rollback_boundary(cur, engine.product)
            parent = engine.install_qualified_parent(cur)
            state = engine.product.install_delta(cur, parent)
            engine.product.verify(cur, state)
            cur.execute(sql)
            assert_installed(cur, installer_receipt, require_empty=True)

            import component
            import additional_cases
            import cp6_auditor_runner
            native = component.context(engine.product, state, scope="NATIVE9")
            native._focus_receipt = installer_receipt
            native.boundary = MethodType(focused_boundary, native)
            today, foundation = prepare_native_case(cur, native, cp6_auditor_runner)
            findings_before = native.modules.bc.findings(cur)
            case = run_case(native, cur, today, additional_cases.correction_return, args.output.parent)
            if case is None:
                conn.rollback()
                save_recovery(engine, before, args.output.parent)
                raise ValueError("CP7_FOCUS_ORIGINAL_CASE_FAILED_SEE_FIRST_FAILURE")
            cur.execute("set constraints all immediate")
            findings_after = native.modules.bc.findings(cur)
            require(not native.modules.bc.new_findings(findings_before, findings_after),
                    "CP7_FOCUS_NEW_FINANCIAL_INTEGRITY_FINDINGS")
            require(case["status"] == "PASS" and case["correction"]["sale_id"] != case["sale"]["created"]["sale_id"],
                    "CP7_FOCUS_EXACT_CORRECTION_CASE_REQUIRED")
            preparation_count, receipt_count = cur.execute(
                "select (select count(*) from cp7_note_zero_effect.preparations),"
                "(select count(*) from cp7_note_zero_effect.receipts)"
            ).fetchone()
            require((preparation_count, receipt_count) == (1, 1), "CP7_FOCUS_ONE_OWNED_RECEIPT_REQUIRED")
            receipt = cur.execute(
                "select jsonb_build_object('actor',actor,'request_id',request_id,'correction_id',correction_id,"
                "'root_sale_id',root_sale_id,'previous_sale_id',previous_sale_id,'replacement_sale_id',replacement_sale_id,"
                "'result_sha256',result_sha256,'current_graph_sha256',current_graph_sha256,"
                "'current_profile_sha256',current_profile_sha256,'return_facts_sha256',return_facts_sha256,"
                "'effect_sha256',effect_sha256,'effect_proof',effect_proof)"
                " from cp7_note_zero_effect.receipts"
            ).fetchone()[0]
            require(str(receipt["replacement_sale_id"]) == str(case["correction"]["sale_id"]),
                    "CP7_FOCUS_RECEIPT_REPLACEMENT_CHANGED")
            retained_originals = retain_originals(case, source_root.parents[1], args.output.parent)
            case_raw = canonical(case)
            args.case_original.parent.mkdir(parents=True, exist_ok=True)
            args.case_original.write_bytes(gzip.compress(case_raw, mtime=0))
            focused = {
                "status": "FOCUSED_CASE_PASS_PENDING_ROLLBACK_PROOF",
                "classification": scope["classification"], "case_id": CASE_ID,
                "product_head": PRODUCT_HEAD, "product_tree": PRODUCT_TREE,
                "workflow_head": os.environ["GITHUB_SHA"], "github_run_id": os.environ["GITHUB_RUN_ID"],
                "github_run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
                "t3_package_sha256": package_sha, "installer_sha256": INSTALLER_SHA256,
                "fixture_foundation": foundation,
                "case_original": {"bytes": len(case_raw), "sha256": sha256(case_raw).hexdigest(),
                                  "gzip_bytes": args.case_original.stat().st_size,
                                  "gzip_sha256": sha256(args.case_original.read_bytes()).hexdigest()},
                "retained_originals": retained_originals,
                "receipt": receipt, "financial_findings_before": findings_before,
                "financial_findings_after": findings_after, "full_recovery_verified": False,
                "qualification_credit": 0, "production_go": False,
            }
            conn.rollback()

        recovery = save_recovery(engine, before, args.output.parent)
        require(all(recovery[key] for key in ("catalogue_equal", "data_and_sequences_equal", "private_schema_absent")),
                "CP7_FOCUS_ROLLBACK_BOUNDARY_NOT_IDENTICAL")
        focused.update(status="PASS", full_recovery_verified=True,
                       rollback=recovery, acceptance_credit=0)
        args.output.write_bytes(canonical(focused))
        print(json.dumps({"status": "PASS", "case_id": CASE_ID,
                          "full_recovery_verified": True, "qualification_credit": 0}, sort_keys=True))
    return 0


def save_recovery(engine, before, proof_root):
    with engine.trusted_installer_connection() as check, check.cursor() as cur:
        restored = rollback_boundary(cur, engine.product)
        private_schema_absent = cur.execute("select to_regnamespace('cp7_note_zero_effect')").fetchone() == (None,)
        check.rollback()
    recovery = {
        "catalogue_equal": restored["catalogue"] == before["catalogue"],
        "data_and_sequences_equal": restored["data_and_sequences"] == before["data_and_sequences"],
        "private_schema_absent": private_schema_absent,
        "before_sha256": digest(before), "restored_sha256": digest(restored),
    }
    (proof_root / "MANDOR_ZERO_EFFECT_ROLLBACK.json").write_bytes(canonical(recovery))
    return recovery


if __name__ == "__main__":
    raise SystemExit(main())
