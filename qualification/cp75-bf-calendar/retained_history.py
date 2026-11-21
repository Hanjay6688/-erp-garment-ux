"""Reuse Astra's immutable original historical lane for the identical CP7.5 comparison."""
from hashlib import file_digest
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

REPO = "repos/Hanjay6688/-erp-garment-ux"
RUN = 44867955170
HEAD = "8c5e51bd76cd7ebb3e944f88f7a5f753c194292d"
PRODUCT = "48858590a361343e73a7f16f6646363dc155c04e"
HISTORY = (14693070681, "cp75-historical-upgrade-44867955170",
           "3d2c2a02f3d85bec8a7353306e42540b32d84d98b61d3ce5b50b4580e58bd2f7")
OPENING = (14692239513, "cp75-original-openings-44867955170",
           "543ddb7013f3f3b358ed55c21e63d6361829ee1467ef062089dffd5889fb474c")
HISTORY_FILES = ("old-documents.json", "up-g14.json", "up-order.json", "upgrade-after.json",
                 "upgrade-before.json", "upgrade-restored.json", "upgrade-resume.json")
ORIGINAL_FILES = ("original-ffda-objects.json.gz", "native-credit-proof.json", "upgrade-opened.json",
                  "catalogue-fields.json.gz")
SCOPE = {
    "qualification/cp75-original-live/clean.py": "a43679ca976b2cdb0b6d6f88f7983611dbe6e2a3",
    "qualification/cp75-original-live/history.py": "91a47e531e7aba9d342a3f50690e1e5293afdadb",
    "qualification/cp75-original-live/profile_figures.py": "f9d6df5f7201e0a028e084454fbaeb90a1d2abf8",
    "qualification/cp75-global-pair/origins.json": "909f81d109f43c2778372b814824eefc611ba139",
    "qualification/cp75-comparison": "0800a76d9465374111266cf5912ed7b9c801a740",
    "qualification/cp75-factory-source": "70b08c394c556ce6e032364348c7d04250a017c4",
}


def retrieve(spec, members, destination):
    aid, name, digest = spec
    api = f"{REPO}/actions/artifacts/{aid}"
    meta = json.loads(subprocess.check_output(["gh", "api", api]))
    if (meta["id"], meta["name"], meta["expired"], meta["digest"],
        meta["workflow_run"]["id"], meta["workflow_run"]["head_sha"]) != (
        aid, name, False, "sha256:" + digest, RUN, HEAD
    ):
        raise ValueError("Historical receipt origin differs from Astra's retained artifact")
    with TemporaryDirectory() as temp:
        source = Path(temp) / "original.zip"
        with source.open("xb") as out:
            subprocess.run(["gh", "api", api + "/zip"], stdout=out, check=True, timeout=240)
        copy_receipts(source, digest, members, destination)


def copy_receipts(source, digest, members, destination):
    with source.open("rb") as raw:
        if file_digest(raw, "sha256").hexdigest() != digest:
            raise ValueError("Historical archive checksum mismatch")
    destination.mkdir(exist_ok=True, parents=True)
    with ZipFile(source) as archive:
        for name in members:
            if archive.namelist().count(name) != 1:
                raise ValueError("Historical receipt missing or duplicated: " + name)
            target = destination / name
            with target.open("xb") as out:
                out.write(archive.read(name))


def check_receipts(history, observed):
    recovered = json.loads((history / "upgrade-restored.json").read_text())
    origin = json.loads((observed / "upgrade-opened.json").read_text())
    if not (recovered["history_equal"] is True and recovered["all_rows_sequences_equal"] is True
            and recovered["table_and_sequence_count"] == 735
            and origin["origin_run"] == 44671146483
            and origin["catalogue"] == "a3da0ecf21909731ab8474c54a7c91afb75bb58dd8b6042cc82314b20808dbd7"):
        raise ValueError("The retained lane has no complete original Global restoration")


def main():
    source = Path(os.environ["GITHUB_WORKSPACE"]) / "source"
    for name, expected in SCOPE.items():
        actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD:" + name], text=True).strip()
        if actual != expected:
            raise ValueError("Historical comparison scope changed: " + name)
    root = Path(os.environ["RUNNER_TEMP"])
    observed, history = root/"cp75-original-observations", root/"cp75-global/upgrade"
    retrieve(HISTORY, HISTORY_FILES, history)
    retrieve(OPENING, ORIGINAL_FILES, observed)
    check_receipts(history, observed)
    info = {"prior_run": RUN, "prior_head": HEAD, "product": PRODUCT,
            "history_artifact": HISTORY[0], "history_sha256": HISTORY[2],
            "opening_artifact": OPENING[0], "opening_sha256": OPENING[2], "scope": SCOPE,
            "restored_tables_and_sequences": 735, "production_go": False}
    (history/"retained-history-origin.json").write_text(json.dumps(info, indent=2) + "\n")


if __name__ == "__main__":
    main()
