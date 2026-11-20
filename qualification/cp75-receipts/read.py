"""Summarize selected synthetic installation receipts from their immutable Actions artifacts."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
from zipfile import ZipFile


def fields(obj, names):
    return {name: obj[name] for name in names if name in obj}


def compact(name, body):
    if name.endswith("-error"):
        return fields(body, ("type", "reason", "message", "frames", "sqlstate", "failed_line"))
    if name == "bf-verified":
        return {"cp6_rollback": fields(body["cp6_rollback"], ("catalogue_sha256", "platform_migrations", "application_migrations"))}
    if name == "progress":
        sku = body.get("sku_receipt", {})
        recovery = body.get("recovery", {})
        return {"phases": body["phases"], "status": sku.get("status"), "details": sorted(sku),
                "installed_credit_census":sku.get("installed_census_sha256"), "archived_credit_census":sku.get("archived_census_sha256"),
                "before_equals_after": bool(recovery) and recovery["before"] == recovery["after"],
                "physical_sha256": recovery.get("plaintext_sha256")}
    if name in ("installed", "global-before-commit", "clean-ffda", "factory-target"):
        seal = body.get("server_catalogue_fingerprint", body.get("server", body.get("seal", {})))
        return {"catalogue": seal, **fields(body, ("expected", "origin", "product", "tree", "full25_sha256", "catalogue_groups",
                "archived_catalogue_equal", "capture_sha256", "archived_capture_sha256", "group_hashes", "credit_guard_literal"))}
    if name == "preseal":
        return fields(body, ("product", "tree", "full25_predecessor_sha256", "full25_installed_sha256", "changes"))
    if name == "reference-route":
        return {"stages":{k:fields(v, ("measured","archived","equal")) for k,v in body["stages"].items()},
                **fields(body, ("installers","origin","source_product","original_BF_used","production_go"))}
    if name == "old-documents":
        return fields(body, ("sku","sales","purchase","original_payment","replacement","actors","readers"))
    if name == "comparison":
        return fields(body, ("target","archived_target","original_BF_used","archived_catalogue_equal","six_areas",
                              "per_case","business_facts","panels","generated_ids","generated_dates","differences",
                              "source_factory","source_upgrade","formal_acceptance","production_go"))
    if name in ("upgrade-before","upgrade-after","factory-posted","upgrade-restored"):
        h=body.get("history",{})
        ap=h.get("accounts_payable",{})
        return {**fields(body, ("origin","target","seal","origin_seal","history_equal","all_rows_sequences_equal",
                               "physical_sha256","table_and_sequence_count","changed_rows_or_sequences")),
                "row_and_sequence_groups":len(body["rows_sequences"]) if "rows_sequences" in body else None,
                "supplier":fields(ap, ("AP","cash_delta","original_status","all_stock_and_cost_same")),
                "sales":h.get("sales",[]),"panels":h.get("panel_figures"),"planner_values":h.get("planner_values"),
                "roles":h.get("role_access"),"stored_report":h.get("published"),"stored_plan":h.get("draft")}
    return fields(body, ("origin","target","physical_sha256","history_equal","all_rows_sequences_equal",
                         "raw_state_equal","origin_seal","fresh_seal","changed","changed_rows_or_sequences","table_and_sequence_count"))


NAMES = {"installed", "preseal", "progress", "bf-verified", "global-source", "global-before-commit", "clean-ffda", "ffda-recovery",
         "factory-target", "factory-baseline", "factory-posted", "factory-restored", "factory-baseline-restored",
         "upgrade-before", "upgrade-resume", "up-g14", "up-order", "upgrade-after", "upgrade-restored", "comparison",
         "install-error", "clean-error", "upgrade-error", "reference-error", "prepare-error", "compare-error", "reference-route", "old-documents"}


def main():
    here = Path(__file__).parent
    receipts = []
    repo = os.environ["GITHUB_REPOSITORY"]
    for pin in json.loads((here / "request.json").read_text()):
        api = f"repos/{repo}/actions/artifacts/{int(pin['id'])}"
        meta = json.loads(subprocess.check_output(["gh", "api", api]))
        assert (meta["digest"], meta["size_in_bytes"], meta["workflow_run"]["id"], meta["workflow_run"]["head_sha"]) == (
            pin["digest"], pin["sz"], pin["run"], pin["head"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.zip"
            with path.open("xb") as out:
                subprocess.run(["gh", "api", api + "/zip"], stdout=out, check=True)
            with path.open("rb") as inp:
                assert path.stat().st_size == pin["sz"] and "sha256:" + hashlib.file_digest(inp, "sha256").hexdigest() == pin["digest"]
            with ZipFile(path) as archive:
                assert archive.testzip() is None
                report = {}
                for member in archive.infolist():
                    p = PurePosixPath(member.filename)
                    if p.suffix != ".json" or p.stem not in NAMES:
                        continue
                    assert member.file_size < 8_000_000 and member.filename not in report
                    report[member.filename] = compact(p.stem, json.loads(archive.read(member)))
                assert report
                record = {"run":pin["run"], "artifact":pin["id"], "digest":pin["digest"], "files":report}
                receipts.append(record)
                print("CP75_SOURCE_RECEIPT",json.dumps({k:v for k,v in record.items() if k!="files"},sort_keys=True),flush=True)
                for name,doc in report.items():
                    print("CP75_DETAIL",json.dumps({"run":pin["run"],"file":name,"observation":doc},sort_keys=True),flush=True)
    Path("cp75-receipts.json").write_text(json.dumps(receipts, sort_keys=True, indent=2)+"\n")


if __name__ == "__main__":
    main()
