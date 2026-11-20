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
        return fields(body, ("type", "reason", "message", "frames"))
    if name == "bf-verified":
        return {"cp6_rollback": fields(body["cp6_rollback"], ("catalogue_sha256", "platform_migrations", "application_migrations"))}
    if name == "progress":
        sku = body.get("sku_receipt", {})
        recovery = body.get("recovery", {})
        return {"phases": body["phases"], "status": sku.get("status"), "details": sorted(sku),
                "before_equals_after": bool(recovery) and recovery["before"] == recovery["after"],
                "physical_sha256": recovery.get("plaintext_sha256")}
    if name in ("global-before-commit", "clean-ffda", "factory-target"):
        seal = body.get("server", body.get("seal", {}))
        return {"catalogue": fields(seal, ("sha256", "groups", "counts")), **fields(body, ("expected", "origin"))}
    if name == "comparison":
        return {"six_areas": body["six_areas"], "per_case": [(row["case"], row["equal"]) for row in body["per_case"]],
                "panels_equal": body["panels"]["equal"], "document_ids_mapped": len(body["generated_ids"]),
                "document_dates_mapped": len(body["generated_dates"]), "production_go": body["production_go"]}
    return fields(body, ("origin","target","physical_sha256","history_equal","all_rows_sequences_equal",
                         "raw_state_equal","origin_seal","fresh_seal","changed","changed_rows_or_sequences","table_and_sequence_count"))


NAMES = {"progress", "bf-verified", "global-source", "global-before-commit", "clean-ffda", "ffda-recovery",
         "factory-target", "factory-baseline", "factory-posted", "factory-restored", "factory-baseline-restored",
         "upgrade-before", "upgrade-resume", "up-g14", "up-order", "upgrade-after", "upgrade-restored", "comparison",
         "install-error", "clean-error", "upgrade-error"}


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
                print("CP75_SOURCE_RECEIPT",json.dumps(record, sort_keys=True),flush=True)
    Path("cp75-receipts.json").write_text(json.dumps(receipts, sort_keys=True, indent=2)+"\n")


if __name__ == "__main__":
    main()
