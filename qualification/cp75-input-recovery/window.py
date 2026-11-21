"""Retain the original SKU inputs whose provider links disappear during the next two days."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import file_digest, sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

BASE="repos/Hanjay6688/-erp-garment-ux/actions/artifacts/"
OW04="12407224140"
OW05="12429866259"
FIRST_MIRROR="14710966682"
FIRST_SHA="50e0b78b59ea028985de2066596f9f70609f73968cb02140ecdbfae313313591"


def check(path, size, expected):
    with path.open("rb") as stream:
        if path.stat().st_size != size or file_digest(stream,"sha256").hexdigest() != expected:
            raise ValueError(f"Original bytes differ for {path.name}")


def download(aid, dest):
    with dest.open("xb") as out:
        subprocess.run(["gh","api",BASE+aid+"/zip"],stdout=out,check=True,timeout=210)


def check_ow05(path):
    with ZipFile(path) as z:
        name="CP7_OW05_NATIVE28_GUIDANCE_WHOLE_PO_WAVE.json"
        if z.namelist().count(name)!=1:
            raise ValueError("Missing original OW05 report")
        raw=z.read(name)
    if len(raw)!=6646642 or sha256(raw).hexdigest()!="9e4732a171faff7175a03b895daca09bcb1dc54a53003cb300d979c858d1143c":
        raise ValueError("Different OW05 report")
    result=json.loads(raw)
    if not (result["status"]=="PASS" and result["native"]["counts"]=={"PASS":28} and
            result["cp6_restored"] and result["advisor_gate"] and result["required_case_ids_pass"] and
            result["production_go"] is False):
        raise ValueError("Historical OW05 acceptance differs")


def main(received):
    root=Path(os.environ["RUNNER_TEMP"])
    dest=root/"original-zips"
    dest.mkdir()
    pins=json.loads(Path(__file__).with_name("window.json").read_text())
    def preserve(entry):
        aid,pin=entry
        path=dest/(aid+".zip")
        if aid==OW05:
            shutil.copyfile(received,path)
            check_ow05(path)
        elif aid==OW04:
            with TemporaryDirectory(dir=root) as folder:
                outer=Path(folder)/"native32-mirror.zip"
                download(FIRST_MIRROR,outer)
                check(outer,2460268,FIRST_SHA)
                with ZipFile(outer) as z, z.open("accepted-native32.zip") as src, path.open("xb") as out:
                    shutil.copyfileobj(src,out)
        else:
            download(aid,path)
        check(path,pin["bytes"],pin["sha256"])
        return aid
    with ThreadPoolExecutor(max_workers=5) as pool:
        saved=list(pool.map(preserve,pins.items()))
    report={"input_count":len(saved),"source_sku_run":43347020525,"released_archive_sha256":
            "de951319b2e9a31c490e2a2dc75a4985561e381256085c10d162264576e54c27",
            "files":pins,"restored_from_retained_copies":[int(OW04),int(OW05)],"production_go":False}
    (root/"intake"/"original-input-verification.json").write_text(json.dumps(report, indent=2)+"\n")
    print(len(saved),"original ZIP digests verified")


if __name__=="__main__":
    main(Path(sys.argv[1]))
