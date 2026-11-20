"""Verify the two independent installation origins and retained expectations before resuming PostgreSQL."""
import hashlib
import json
import os
import subprocess
from pathlib import Path
from zipfile import ZipFile

from sku_parent import retained

HERE = Path(__file__).resolve().parent
PINS = json.loads((HERE / "origins.json").read_text())
OUT = Path(os.environ["RUNNER_TEMP"]) / "cp75-origins"
PREFIX = "repos/" + PINS["repository"] + "/"


def api(path):
    return json.loads(subprocess.check_output(["gh", "api", PREFIX + path]))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def member(archive, basename):
    matches = [row for row in archive.infolist() if Path(row.filename).name == basename]
    if len(matches) != 1:
        raise ValueError(f"Expected one {basename}, found {len(matches)}")
    return matches[0]


def object_from(key, name):
    with ZipFile(OUT / (key + ".zip")) as archive:
        return json.loads(archive.read(member(archive, name)))


def checkpoint_header(key, name, expected):
    with ZipFile(OUT / (key + ".zip")) as archive, archive.open(member(archive, name)) as stream:
        digest = hashlib.sha256()
        header = stream.read(405)
        assert header[:7] == b"CP7G11\x01" and int.from_bytes(header[7:9], "big") == 384
        digest.update(header)
        for chunk in iter(lambda: stream.read(2**20), b""):
            digest.update(chunk)
        assert digest.hexdigest() == expected
    return {"ciphertext_sha256": expected, "envelope_sha256": sha(header)}


def persist(record):
    dest = OUT / "receipt.json"
    temp = dest.with_suffix(".new")
    temp.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    temp.replace(dest)


def collect():
    OUT.mkdir(mode=0o700)
    result = {"status": "READING", "target": PINS["product"], "tree": PINS["tree"],
              "target_seal": PINS["target_seal"], "production_go": False,
              "new_database_cases": 0, "source_run": os.environ["GITHUB_RUN_ID"], "artifacts": {}}
    persist(result)
    for key, pin in PINS["inputs"].items():
        run = api("actions/runs/" + str(pin["run"]))
        assert run["head_sha"] == pin["head"] and run["conclusion"] == "success"
        item = api("actions/artifacts/" + str(pin["artifact"]))
        assert not item["expired"] and item["workflow_run"]["id"] == pin["run"]
        assert item["name"] == pin["name"] and item["digest"] == pin["digest"]
        path = OUT / (key + ".zip")
        with path.open("xb") as dst:
            subprocess.run(["gh", "api", PREFIX + "actions/artifacts/" + str(pin["artifact"]) + "/zip"],
                           stdout=dst, check=True, timeout=360)
        assert path.stat().st_size == pin["bytes"] and "sha256:" + file_digest(path) == pin["digest"]
        with ZipFile(path) as archive:
            assert archive.testzip() is None
            names = [i.filename for i in archive.infolist() if not i.is_dir()]
        result["artifacts"][key] = {**pin, "member_count": len(names)}
        if key in ("auditor", "sale_fixture"):
            result["artifacts"][key]["members"] = names
        persist(result)
        print("VERIFIED", key, len(names), flush=True)
    base = object_from("bf_proof", "clean-bf.json")
    assert base["source_and_isolated_boot_equal"] and base["source"] == base["restored"]
    clean = base["source"]["cp6_rollback"]
    assert (clean["bf"], clean["bf_platform"], clean["platform_migrations"], clean["application_migrations"],
            clean["catalogue_sha256"], clean["auth_users"], clean["app_users"]) == (1, 1, 128, 113, PINS["bf_catalogue"], 0, 0)
    assert base["archive"]["sha256"] == PINS["clean_cipher_sha256"]
    result["clean"] = {**checkpoint_header("bf_archive", "clean-bf.cp75", base["archive"]["sha256"]),
                       "plaintext_sha256": base["plaintext_sha256"], "database": clean, "source_and_restore_equal": True}
    history = object_from("old_proof", "installed.json")
    terminal = object_from("old_terminal", "terminal.json")
    assert history["status"] == "COMMITTED" and terminal["status"] == "INSTALLED_AND_PRESERVED"
    assert history["product"] == PINS["legacy_product"] and history["full25_sha256"] == PINS["legacy_catalogue"]
    assert history["catalogue_verified_after_scheduler"] is True
    envelope = checkpoint_header("old_archive", "global-ffda.cp7", history["checkpoint"]["sha256"])
    if history.get("envelope_sha256"):
        assert history["envelope_sha256"] == envelope["envelope_sha256"]
    result["upgrade"] = {**envelope, "product": history["product"], "tree": history["tree"], "catalogue": history["full25_sha256"]}
    catalogue, fingerprint, sources = retained(OUT / "sku_release.zip")
    result["sku_parent"] = {"catalogue_bytes": len(catalogue), "catalogue_sha256": sha(catalogue),
                            "fingerprint_groups": fingerprint["groups"], "source_components": len(sources)}
    result["status"] = "VERIFIED_ORIGINS"
    persist(result)
    print("CP75_ORIGINS " + json.dumps(result, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    collect()
