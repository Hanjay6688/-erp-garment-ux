"""Bundle only the twenty original JSON receipts from the approved synthetic pair."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

RUN=44829911983
HEAD="e6bd1db27c3a6d250d189842e326ab70e5f5e26c"
ARTIFACT=14679641825
SIZE=205144534
SHA="3191d741c32b203ed72993348c3dc54c05f0a711bb608a6fa2ccc580d4f8f344"
MEMBERS=[
    "cp75-global/bf-verified.json",
    "cp75-global/clean/factory-baseline-restored.json",
    "cp75-global/clean/factory-baseline.json",
    "cp75-global/clean/factory-posted.json",
    "cp75-global/clean/factory-restored.json",
    "cp75-global/clean/factory-target.json",
    "cp75-global/clean/old-documents.json",
    "cp75-global/clean-ffda.json",
    "cp75-global/comparison.json",
    "cp75-global/ffda-recovery.json",
    "cp75-global/global-before-commit.json",
    "cp75-global/reference-route.json",
    "cp75-global/global-source.json",
    "cp75-global/upgrade/old-documents.json",
    "cp75-global/upgrade/up-g14.json",
    "cp75-global/upgrade/up-order.json",
    "cp75-global/upgrade/upgrade-after.json",
    "cp75-global/upgrade/upgrade-before.json",
    "cp75-global/upgrade/upgrade-restored.json",
    "cp75-global/upgrade/upgrade-resume.json"
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def put(archive,name,body):
    info=ZipInfo(name,(2026,11,20,23,38,0))
    info.compress_type=ZIP_DEFLATED
    archive.writestr(info,body)


def main():
    repo=os.environ["GITHUB_REPOSITORY"]
    route=f"repos/{repo}/actions/artifacts/{ARTIFACT}"
    meta=json.loads(subprocess.check_output(["gh","api",route]))
    assert (meta["workflow_run"]["id"],meta["workflow_run"]["head_sha"],meta["size_in_bytes"],meta["digest"])==(RUN,HEAD,SIZE,"sha256:"+SHA)
    out=Path("CP75_SQL_ASLI.zip")
    manifest={}
    with tempfile.TemporaryDirectory() as temp:
        source=Path(temp)/"source.zip"
        with source.open("xb") as dest:
            subprocess.run(["gh","api",route+"/zip"],stdout=dest,check=True)
        with source.open("rb") as f:
            assert hashlib.file_digest(f,"sha256").hexdigest()==SHA
        with ZipFile(source) as original, ZipFile(out,"x",compression=ZIP_DEFLATED) as result:
            assert original.testzip() is None and len(MEMBERS)==len(set(MEMBERS))==20
            receipt=json.loads(original.read("cp75-global/comparison.json"))
            assert len(receipt["per_case"])==23 and all(x["equal"] for x in receipt["per_case"]) and all(receipt["six_areas"].values())
            assert not receipt["original_BF_used"] and not receipt["archived_catalogue_equal"] and not receipt["production_go"]
            for path in MEMBERS:
                entry=original.getinfo(path)
                assert path.startswith("cp75-global/") and path.endswith(".json") and entry.file_size<2000000
                data=original.read(entry)
                assert isinstance(json.loads(data),dict)
                name=path.removeprefix("cp75-global/")
                manifest[name]=sha(data)
                put(result,name,data)
            proof={"public_synthetic_origin_run":RUN, "source_artifact":ARTIFACT, "archive_sha256":SHA,
                   "member_sha256":manifest, "production_go":False}
            put(result,"MANIFEST.json",json.dumps(proof,sort_keys=True,indent=2).encode()+b"\n")
    with ZipFile(out) as packed:
        assert packed.testzip() is None and all(sha(packed.read(name))==digest for name,digest in manifest.items())
    data=out.read_bytes()
    assert len(data)<180000
    print("CP75_RECEIPT_PACK",json.dumps({"bytes":len(data),"sha256":sha(data),"original_members":len(manifest)}))
    coded=base64.b64encode(data).decode("ascii")
    for start in range(0,len(coded),3600):
        print("CP75_PUBLIC_RECEIPT_PART",start//3600,coded[start:start+3600],flush=True)


if __name__=="__main__":
    main()
