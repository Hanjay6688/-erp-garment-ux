"""Open both admitted synthetic cluster images on isolated Unix sockets and verify each independent origin."""
import argparse
import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from zipfile import ZipFile

import access
from close11 import checkpoint, frozen

WORK = Path(os.environ["RUNNER_TEMP"]) / "cp75-originals"
RESULT = Path(os.environ["RUNNER_TEMP"]) / "cp75-original-observations"
ROOT = Path(os.environ["GITHUB_WORKSPACE"])
PINS = json.loads((ROOT/"source/qualification/cp75-global-pair/origins.json").read_text())["inputs"]
REPO = "repos/"+access.SOURCE+"/"
KEY = WORK/"receiver.pem"
REQUEST = RESULT/"request.json"


def obtain(which, member, dest):
    pin=PINS[which]
    info=json.loads(subprocess.check_output(["gh","api",REPO+"actions/artifacts/"+str(pin["artifact"])]))
    assert (info["workflow_run"]["head_sha"],info["workflow_run"]["id"],info["digest"]) == (pin["head"],pin["run"],pin["digest"])
    with tempfile.TemporaryDirectory(dir=WORK) as root:
        path=Path(root)/"original.zip"
        with path.open("xb") as handle:
            subprocess.run(["gh","api",REPO+"actions/artifacts/"+str(pin["artifact"])+"/zip"],stdout=handle,check=True,timeout=300)
        assert "sha256:"+checkpoint.digest(path)==pin["digest"]
        with ZipFile(path) as zipfile:
            entry,=[item for item in zipfile.infolist() if Path(item.filename).name==member]
            with zipfile.open(entry) as inp,dest.open("xb") as out:
                shutil.copyfileobj(inp,out,2**20)


def prepare():
    WORK.mkdir(mode=0o700)
    RESULT.mkdir(mode=0o700)
    for key,file,output in [("bf_proof","clean-bf.json","clean.json"),("bf_archive","clean-bf.cp75","clean.cp"),
                            ("old_proof","installed.json","upgrade.json"),("old_archive","global-ffda.cp7","upgrade.cp")]:
        obtain(key,file,WORK/output)
    request=access.make_request({l:WORK/(l+".cp") for l in access.ORIGINS},access.ORIGINS,
                                os.environ["GITHUB_RUN_ID"],os.environ["GITHUB_SHA"],KEY)
    access.write(REQUEST,request)
    print("CP75_RECEIVER "+request.decode().strip(),flush=True)


def response():
    run=os.environ["GITHUB_RUN_ID"]
    deadline=time.monotonic()+50*60
    path=REPO+"contents/qualification/cp75-grants/"+run+".json?ref=writer-a/cp75-baseline-public"
    while time.monotonic()<deadline:
        p=subprocess.run(["gh","api",path],capture_output=True,timeout=30)
        if p.returncode==0:
            obj=json.loads(p.stdout)
            assert obj["size"] < 4000
            return base64.b64decode(obj["content"])
        if b"404" not in p.stderr and b"Not Found" not in p.stderr:
            raise RuntimeError("GitHub could not read the grant destination")
        time.sleep(15)
    raise TimeoutError("No original-checkpoint grant was issued for this run")


def docker(*args,**kw):
    env={k:v for k,v in os.environ.items() if k!="GH_TOKEN"}
    env["POSTGRES_PASSWORD"]=secrets.token_urlsafe(32)
    return subprocess.run(["docker",*args],check=True,env=env,**kw)


def start(lane,archive,image,metadata,cron,*,factory_source=False):
    run=os.environ["GITHUB_RUN_ID"]
    name="supabase_db_cp5-local" if factory_source else "cp75-"+lane+"-"+run
    if factory_source and (lane!="clean" or os.environ.get("CP75_FACTORY_ORIGINAL")!="1"):
        raise ValueError("Only the original clean factory can occupy its fixed local endpoint")
    data,config=name+"-data",name+"-config"
    sock=WORK/(lane+"-socket")
    sock.mkdir(mode=0o755)
    assert "@sha256:" in image
    docker("pull",image,stdout=subprocess.DEVNULL)
    for v in (data,config):
        docker("volume","create",v,stdout=subprocess.DEVNULL)
    args=["-v",data+":/restore/data","-v",config+":/restore/config","-v",str(sock)+":/socket"]
    with archive.open("rb") as stream:
        docker("run","--rm","-i","--network","none","--user","0",*args,"--entrypoint","sh",image,"-ec",
               "tar -C /restore -xzf -; chmod 700 /restore/data; chown postgres:postgres /restore/data /socket; chmod 755 /socket; "+frozen.verify_files(metadata),stdin=stream)
    network_args=["--network","none"]
    if factory_source:
        network="cp75-factory-source-"+run
        docker("network","create","--internal",network,stdout=subprocess.DEVNULL)
        network_args=["--network",network,"--publish","127.0.0.1:54322:5432"]
    docker("run","-d","--name",name,"--label","cp75.run="+run,*network_args,"-e","POSTGRES_PASSWORD","-v",data+":/var/lib/postgresql/data",
           "-v",config+":/etc/postgresql-custom","-v",str(sock)+":/var/run/postgresql",image,"postgres","-c",
           "config_file=/etc/postgresql/postgresql.conf",*(["-c","listen_addresses=*"] if factory_source else []),"-c","cron.database_name="+cron,"-c","cron.launch_active_jobs=off",stdout=subprocess.DEVNULL)
    for n in range(120):
        proc=subprocess.run(["docker","exec","-u","postgres",name,"pg_isready","-q","-U","supabase_admin","-d","cp6_rollback"],capture_output=True)
        if proc.returncode==0:
            return name,sock
        time.sleep(1)
    raise RuntimeError("restored database was not ready")


def query(container,stmt):
    return json.loads(docker("exec","-u","postgres",container,"psql","-U","supabase_admin","-d","cp6_rollback",
                             "-XAtq","-v","ON_ERROR_STOP=1","-c",stmt,capture_output=True,text=True).stdout)


def opened():
    from cryptography.hazmat.primitives import serialization
    receipt=response()
    private=serialization.load_pem_private_key(KEY.read_bytes(),None)
    keys=access.receive(REQUEST.read_bytes(),receipt,private,access.ORIGINS,os.environ["GITHUB_RUN_ID"],os.environ["GITHUB_SHA"])
    KEY.unlink()
    os.environ.pop("GH_TOKEN",None)
    import cp6_g01_fingerprint as bf
    for lane in ("clean","upgrade"):
        meta=json.loads((WORK/(lane+".json")).read_text())
        clean=lane=="clean"
        expected=meta["plaintext_sha256"] if clean else meta["checkpoint"]["plaintext_sha256"]
        image=meta["image"] if clean else meta["postgres_image"]
        with tempfile.TemporaryDirectory(dir=WORK) as root:
            raw=Path(root)/"cluster.tar.gz"
            checkpoint.unseal(WORK/(lane+".cp"),raw,transferred_key=keys.pop(lane))
            assert checkpoint.digest(raw)==expected
            src=meta["copy"] if clean else meta
            cron="cp6_rollback" if src.get("audit_baseline")=="COLD_GLOBAL_WITH_INACTIVE_NATIVE_JOBS" else "postgres"
            container,socket=start(lane,raw,image,src,cron,factory_source=clean and os.environ.get("CP75_FACTORY_ORIGINAL")=="1")
        assert query(container,"select to_jsonb(current_setting('cron.launch_active_jobs'))")=="off"
        if clean:
            groups=query(container,"set search_path=pg_catalog,public; "+bf.SUMMARY)
            seal=hashlib.sha256(json.dumps(groups,sort_keys=True,separators=(",",":")).encode()).hexdigest()
            assert seal==meta["source"]["cp6_rollback"]["catalogue_sha256"]=="b036261ee8902fc3be5307d54cf2b021dd2e2b419e24100655a7a338b70bad0a"
        else:
            actual=query(container,"select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()")
            assert actual==meta["server_catalogue_fingerprint"]
            seal=actual["sha256"]
        observed={"lane":lane,"origin_run":access.ORIGINS[lane]["source_run"],"sha256":expected,"catalogue":seal,
                  "container":container,"scheduler_enabled":False,"disposable":True,"production_go":False}
        (RESULT/(lane+"-opened.json")).write_text(json.dumps(observed,indent=2)+"\n")
        print("CP75_OPENED "+json.dumps(observed),flush=True)


if __name__=="__main__":
    arg=argparse.ArgumentParser()
    arg.add_argument("op",choices=["prepare","open"])
    op=arg.parse_args().op
    if op=="prepare":
        prepare()
    else:
        opened()
