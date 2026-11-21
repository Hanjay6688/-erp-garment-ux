"""Check the original SKU run's artifact receipts against the current GitHub store."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import file_digest
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from zipfile import ZipFile

REPO = "Hanjay6688/-erp-garment-ux"
SKU = 14011544457
SKU_SHA = "de951319b2e9a31c490e2a2dc75a4985561e381256085c10d162264576e54c27"


def collect(path):
    with path.open("rb") as f:
        if file_digest(f,"sha256").hexdigest() != SKU_SHA:
            raise ValueError("The retained SKU fixture changed")
    entries = {}
    with ZipFile(path) as z:
        for name in z.namelist():
            if not (name.startswith("ARTIFACT_FETCH/") and name.endswith(".json")):
                continue
            receipt = json.loads(z.read(name))
            if receipt.get("exit_code") == 0:
                artifact = int(receipt["artifact_id"])
                pin = (receipt["stdout_bytes"],receipt["stdout_sha256"])
                if artifact in entries and entries[artifact] != pin:
                    raise ValueError("Conflicting receipts for the same original")
                entries[artifact] = pin
    return entries


def probe(entry):
    aid, (size, sha) = entry
    request = urllib.request.Request(f"https://api.github.com/repos/{REPO}/actions/artifacts/{aid}",
                 headers={"Authorization": "Bearer "+os.environ["GH_TOKEN"], "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            meta=json.load(response)
    except urllib.error.HTTPError as error:
        if error.code not in (404,410):
            raise
        return {"artifact":aid,"expected_bytes":size,"expected_sha256":sha,"status":str(error.code)}
    if meta["id"] != aid or meta["size_in_bytes"] != size or meta["digest"] != "sha256:"+sha:
        raise ValueError(f"Unexpected provider digest for {aid}")
    return {"artifact":aid,"expected_bytes":size,"expected_sha256":sha,
            "status":"expired" if meta["expired"] else "available","expires_at":meta["expires_at"]}


if __name__ == "__main__":
    root = Path(os.environ["RUNNER_TEMP"])
    entries=collect(root/"sku.zip")
    with ThreadPoolExecutor(max_workers=5) as pool:
        result = list(pool.map(probe, sorted(entries.items())))
    document = {"original_sku_run":43347020525,"original_sku_artifact":SKU,
                "receipts":result,"unavailable":[r["artifact"] for r in result if r["status"]!="available"],
                "production_go":False}
    (root/"intake"/"input-availability.json").write_text(json.dumps(document,indent=2)+"\n")
    print(len(result),"original SKU transport receipts checked;",document["unavailable"])
