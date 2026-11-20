"""Measure a reconstructed BF route on disposable PostgreSQL copies, alongside the archived absolute identities."""
import argparse
import json
import os
from pathlib import Path
import traceback

import psycopg
import factory
import history
from handoff import main as compare_lanes
from close11 import checkpoint, frozen
from live import WORK as PRIVATE, start


OUT=Path(os.environ["STAGE_PATH"])
ROOT=Path(os.environ["GITHUB_WORKSPACE"])
RAW=PRIVATE/"reconstructed-ffda.tar.gz"
REFERENCE=(history.OLD,history.MIDDLE,history.TARGET)
STAGES=("ffda","g14","current")


def save(label, value):
    path=OUT/(label+".json")
    interim=path.with_suffix(".part")
    interim.write_text(json.dumps(value,sort_keys=True,indent=2,default=str)+"\n")
    interim.replace(path)
    print("CP75_PORTABILITY",label,flush=True)


def load(label):
    return json.loads((OUT/(label+".json")).read_text())


def open_lane(name):
    archive=load("ffda-recovery")
    if checkpoint.digest(RAW)!=archive["physical_sha256"]:
        raise ValueError("Reconstructed FFDA physical checkpoint differs")
    container,socket=start("factory-"+name,RAW,archive["image"],archive["copy"],"cp6_rollback")
    factory.socket(socket)
    if history.seal()!=load("clean-ffda")["seal"]:
        raise ValueError("Restored FFDA catalogue differs from the source connection")
    return container,archive["image"]


def prepare():
    PRIVATE.mkdir(mode=0o700,exist_ok=True)
    source=load("clean-ffda")
    image_id=frozen.docker("local PostgreSQL image",["inspect","-f","{{.Image}}",frozen.SOURCE])
    tags=json.loads(frozen.docker("source image tags",["image","inspect","-f","{{json .RepoDigests}}",image_id]))
    image=next(value for value in tags if "@sha256:" in value)
    proof=frozen.freeze(RAW,image_id)
    save("ffda-recovery",{"origin":"independently rebuilt BF continued to FFDA",
         "physical_sha256":checkpoint.digest(RAW),"copy":proof,"image":image,"source_seal":source["seal"]["sha256"],
         "archive":checkpoint.seal(RAW,OUT/"ffda-source.cp75",ROOT/"capture/qualification/close11/auditor-public.pem"),
         "archived_catalogue_equal":source["archived_catalogue_equal"],"production_go":False})


def reference():
    open_lane("reference")
    measurements=[history.seal()]
    releases=[
        ("hpp",ROOT/"g14/qualification/close12/product","77cc2c35a78c1fde725e37199a80f87a5f9965e3"),
        ("order",ROOT/"rig/qualification/cp75-order","7a6d8ec30f17ddada5941c9a923f699a1367656a")]
    observations=[]
    for name,path,oid in releases:
        module=history.load_installer(name,path,oid)
        with psycopg.connect(**history.db()) as c:
            detail=module.apply(c,"up")
        if detail.get("changed") is not True:
            raise ValueError("The supported release did not make its declared change: "+name)
        observations.append(detail)
        measurements.append(history.seal())
    if len({value["sha256"] for value in measurements})!=3 or not all(v["groups"]==len(v["counts"])==25 for v in measurements):
        raise ValueError("The three full catalogue readbacks are incomplete")
    route={key:{"measured":v["sha256"],"archived":expected,"equal":v["sha256"]==expected,"catalogue":v}
           for key,v,expected in zip(STAGES,measurements,REFERENCE,strict=True)}
    save("reference-route",{"stages":route,"installers":observations,"origin":"third physical copy of reconstructed FFDA",
         "source_product":"48858590a361343e73a7f16f6646363dc155c04e","original_BF_used":False,"production_go":False})


def run_lane(name):
    container,image=open_lane(name)
    route=load("reference-route")["stages"]
    values=tuple(route[key]["measured"] for key in STAGES)
    folder=OUT/name
    folder.mkdir(exist_ok=True)
    history.OUT=folder
    if name=="clean":
        factory.finish(container,image,"factory SQL on independent reconstructed BF to FFDA",catalogues=values)
    else:
        history.exercise_upgrade(container,image,"separate FFDA with history posted before the supported upgrades",
                                 "factory-history-restore",catalogues=values)


def finish():
    route=load("reference-route")["stages"]
    compare_lanes(OUT/"clean",OUT/"upgrade",OUT/"comparison.json",
                  target=route["current"]["measured"],predecessor=route["ffda"]["measured"])
    results=load("comparison")
    results.update(archived_target=history.TARGET,original_BF_used=False,archived_catalogue_equal=all(s["equal"] for s in route.values()),
                   current_product="48858590a361343e73a7f16f6646363dc155c04e",path="reconstructed supplementary profile",
                   formal_acceptance="OPEN",production_go=False)
    save("comparison",results)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=["prepare","reference","clean","upgrade","compare"])
    stage=parser.parse_args().stage
    if os.environ.get("CP75_REBUILT_DIAGNOSTIC")!="1" or os.environ.get("CP75_FACTORY_ORIGINAL")=="1":
        raise ValueError("This profile is reserved for the disposable reconstructed installation")
    try:
        if stage=="prepare":
            prepare()
        elif stage=="reference":
            reference()
        elif stage=="compare":
            finish()
        else:
            run_lane(stage)
    except Exception as error:
        frames=traceback.extract_tb(error.__traceback__)
        details={"type":type(error).__name__,"reason":(str(error).splitlines() or [type(error).__name__])[0][:450],
                 "sqlstate":getattr(error,"sqlstate",None),"frames":[[Path(f.filename).name,f.name,f.lineno] for f in frames[-12:]],
                 "failed_line":frames[-1].line if frames else None,"production_go":False}
        save(stage+"-error",details)
        print("CP75_LANE_ERROR",json.dumps(details),flush=True)
        raise
