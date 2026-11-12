"""Verify retained Writer B evidence against A's candidate and owning catalogue."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile


B = "52b6cf93dd85bc76a713e29beb5ae6d91247f9c7"
B_TREE = "465d7baa1d2d95be3fc8a1f7f51f51c184d340dd"
A = "af6e5710c0a3265daeb14c8ccd078ea82c99c482"
A_TREE = "41aa56dc3247e7a802e8b2f48d55e15ff933954b"
AREA = "docs/cp7/review/sku-snapshot-report-focused-20261112/"
NATIVE27_CASE = "SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4"
E4EA = dict(bytes=96749933, sha256="dd9e31355a0820d1650e438a8913c49450a10dbc342789ed94f3418c1be6363b")


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def reconcile(repo, native27_file, e4ea_zip):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args])

    def b_file(name):
        return git("show", B + ":" + AREA + name)

    assert git("rev-parse", B + "^{tree}").decode().strip() == B_TREE
    assert git("rev-parse", A + "^{tree}").decode().strip() == A_TREE
    source_receipt = json.loads(b_file("SOURCE_AND_RUN_RECEIPT.json"))
    assert {name: pin(b_file(name)) for name in source_receipt["payload"]} == source_receipt["payload"]
    sources = source_receipt["source_git_blobs"] | source_receipt["current_ui"]["sources"]
    original = source_receipt["candidate"]["head"]
    assert git("rev-parse", original + "^{tree}").decode().strip() == source_receipt["candidate"]["tree"]
    for path, blob in sources.items():
        assert git("rev-parse", original + ":" + path).decode().strip() == blob, path
        assert git("rev-parse", A + ":" + path).decode().strip() == blob, path
    assert not git("diff", "--name-only", original, A, "--", "src", "package.json", "package-lock.json",
                   "supabase", "scripts/cp7-src")

    native_raw = native27_file.read_bytes()
    assert pin(native_raw) == source_receipt["native27_original"]["member"]
    native = json.loads(native_raw)["committed"][NATIVE27_CASE]["Native_to_copy_handoff"]["raw_current_catalog"]
    raw_zip = e4ea_zip.read_bytes()
    assert pin(raw_zip) == E4EA
    with ZipFile(e4ea_zip) as archive:
        assert len(archive.infolist()) == 212 and archive.testzip() is None
        e4ea_raw = archive.read("SKU_GLOBAL_PARENT_ACTUAL_FULL25.json")
    groups = json.loads(e4ea_raw)
    assert len(groups) == 25
    current = {name: dict(rows) for name, rows in groups.items()}
    snapshot = json.loads(b_file("SNAPSHOT_REPORT_RESULT.json"))
    moving = json.loads(b_file("MOVING_AVERAGE_RESULT.json"))
    rounding = json.loads(b_file("ROUNDING_SOURCE_PREFLIGHT.json"))
    observed = snapshot["source"]
    for path, expected in (observed["cp7_files"] | observed["freshness_grants_source"]).items():
        assert pin(git("show", A + ":" + path)) == expected, path

    # Carry the complete original catalogue row for future terminal comparison.
    # The model only uses the function body or view SELECT, so preserve that scope.
    retained = {}
    for group, field, entries in (
        ("functions", 0, observed["native27_bodies"]),
        ("relations", 9, observed["native27_views"]),
        ("functions", 0, moving["source"]["native_book"]),
    ):
        for signature, expected in entries.items():
            prior = native[group][signature]
            actual = current[group][signature]
            assert pin(prior[field].encode()) == pin(actual[field].encode()) == expected, signature
            retained[signature] = dict(group=group, field=field, body=expected,
                                       native27_row_equal_to_e4ea=prior == actual,
                                       e4ea_row=pin(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode()))
    for signature, changes in rounding["source"]["replacements"].items():
        actual = current["functions"][signature]
        assert sha256(actual[0].encode()).hexdigest() == changes["after_sha256"], signature
        retained[signature] = dict(group="functions", field=0, body=pin(actual[0].encode()),
                                   e4ea_row=pin(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode()))

    assert moving["active_candidate"] == original and moving["variant"]["source"] == rounding
    case, = moving["cases"]
    assert len(case["observations"]) == 7 and case["status"] == "PASS" and case["rollback"]["identical"]
    assert case["same_source_amount_replayed"]["identical"] and case["sale_and_return_snapshots_immutable"]
    assert case["original_return_values"] == ["36.51", "37.01"]
    assert moving["recovery"]["exact"] and moving["model_tables_checked"] == 75
    assert (snapshot["snapshot_stock_status"], snapshot["report_stock_archive_status"],
            snapshot["authoritative_hpp_value_status"]) == ("PASS", "PASS", "BLOCKED")
    assert snapshot["expected"] == dict(input=8, posted_fg=3, wip_before=8, wip_after=5,
                                        fg_before=0, fg_after=3, outside_filter_pcs=11)
    assert snapshot["recovery"]["exact"] and snapshot["recovery"]["disposable_db_dropped"]
    assert "set local timezone='UTC'" in git("show", source_receipt["B_branch"]["parent"] +
        ":docs/cp7/review/sku-moving-average-regression-20261111/focused_probe.mjs").decode()
    assert source_receipt["current_ui"]["passed"] == 7 and source_receipt["current_ui"]["browser"] == "historical only"

    return dict(status="WRITER_B_RETAINED_FOCUSED_EVIDENCE_BOUND_TO_A_SOURCE",
                B_head=B, B_tree=B_TREE, A_head=A, A_tree=A_TREE, B_tested_source=original,
                payload=source_receipt["payload"], identical_source_blobs=sources,
                E4EA_actual_catalogue=pin(e4ea_raw), runtime_originals=retained,
                moving_average_fixture=dict(status="PASS", transactions_checked=7, fixture_tables_restored=75,
                    caller_timezone="UTC", official_invoice_and_uuid_covered=False),
                physical_snapshot=dict(status="PASS", WIP=[8, 5], FG=[0, 3], unit="PCS"),
                deferred_report=dict(status="PASS", physical_and_available_pcs=[0, 3],
                                     old_archive_reopened=True, identity_refused=True),
                report_dom=dict(passed=7, fresh_browser_cases=0),
                official_qc_and_included_report=dict(status="BLOCKED", current_finance_fixture="MODELED",
                    expected_before=dict(WIP="288.00", FG="0.00", COGS="0.00"),
                    expected_after=dict(WIP="180.00", FG="108.00", COGS="0.00")),
                actual_af6e_catalogue_comparison_pending=True, actual_new_ERP_cases=0,
                full_SKU_or_Global_qualification_credit=0, formal_CP7="5/16",
                independent_acceptance=False, production_go=False)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    for name in ("repo", "native27", "e4ea", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    receipt = reconcile(args.repo, args.native27, args.e4ea)
    with args.output.open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({key: receipt[key] for key in ("status", "moving_average_fixture", "physical_snapshot",
                                                     "deferred_report", "official_qc_and_included_report")}))
