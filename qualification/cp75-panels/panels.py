"""Recover the accepted UI distribution and both UI-only diffs for the three CP7.5 panels."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from zipfile import ZipFile

REPO="repos/Hanjay6688/-erp-garment-ux"
ORIGIN=44671146483
ART=14599974252
DIGEST="ac99d1d03624ac65ea0425ae2ba700733c544f4d67fab507fc5bf8ebda34f717"
TARGET="48858590a361343e73a7f16f6646363dc155c04e"
SUITES=("NativeProductionPlanningPanel.dom.test.tsx","NativePlanDraftPanel.staged.dom.test.tsx","NativeAnalysisFinancePanel.dom.test.tsx")


def blob(p):
    raw=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def prepare(root):
    meta=json.loads(subprocess.check_output(["gh","api",f"{REPO}/actions/artifacts/{ART}"]))
    assert (meta["workflow_run"]["id"],meta["digest"],meta["size_in_bytes"])==(ORIGIN,"sha256:"+DIGEST,2234848)
    with tempfile.TemporaryDirectory() as td:
        zip_path=Path(td)/"ui.zip"
        with zip_path.open("wb") as stream:
            subprocess.run(["gh","api",f"{REPO}/actions/artifacts/{ART}/zip"],check=True,stdout=stream)
        assert hashlib.sha256(zip_path.read_bytes()).hexdigest()==DIGEST
        with ZipFile(zip_path) as archive:
            assert archive.testzip() is None
            members=archive.namelist()
            packed=archive.read(next(n for n in members if n.endswith("ffda-ui.tar.gz")))
            listed=archive.read(next(n for n in members if n.endswith("ui.sha256"))).decode().split()[0]
            assert hashlib.sha256(packed).hexdigest()==listed
            tar_path=Path(td)/"ui.tar.gz"
            tar_path.write_bytes(packed)
            with tarfile.open(tar_path,"r:gz") as tar:
                assert all(m.name.rstrip("/").split("/")[0]=="product" for m in tar.getmembers())
                tar.extractall(root,filter="data")
    product=root/"product"
    transitions=[]
    for layer in ("cp75-reminders","cp75-order"):
        path=root/"rig/qualification"/layer
        release=json.loads((path/"candidate.json").read_text())
        changed={p:v for p,v in release["files"].items() if p.startswith("src/")}
        for p,v in changed.items():
            assert blob(product/p)==v["before"],p
        subprocess.run(["git","apply","--no-index",str(path/"ui.patch")],cwd=product,check=True)
        for p,v in changed.items():
            assert blob(product/p)==v["after"],p
        transitions.append(release["product"])
    assert transitions[-1]==TARGET
    pins={p:blob(product/"src"/p) for p in SUITES}
    (root/"evidence").mkdir(exist_ok=True)
    (root/"evidence/source.json").write_text(json.dumps({"origin_run":ORIGIN,"source_archive":DIGEST,"ui_layers":transitions,
        "product":TARGET,"suites":pins,"database_cases":0,"production_go":False},indent=2)+"\n")


def results(root):
    file=root/"evidence/vitest.json"
    data=json.loads(file.read_text())
    assert data["success"] and data["numFailedTests"]==data["numPendingTests"]==0
    suites={Path(s["name"]).name:s["assertionResults"] for s in data["testResults"]}
    assert set(suites)==set(SUITES) and all(v and all(t["status"]=="passed" for t in v) for v in suites.values())
    finance=[x["title"] for x in suites["NativeAnalysisFinancePanel.dom.test.tsx"]]
    assert any("unknown" in name and "zero" in name for name in finance)
    result={name:len(v) for name,v in suites.items()}
    print("CP75_PANEL_TESTS",json.dumps(result),flush=True)
    (root/"evidence/outcome.json").write_text(json.dumps({"product":TARGET,"panel_dom_cases":result,
       "finance_unknown_and_zero":True,"database_cases":0,"production_go":False},indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=["prepare","results"])
    args=p.parse_args()
    root=Path(os.environ["GITHUB_WORKSPACE"])
    (prepare if args.mode=="prepare" else results)(root)
