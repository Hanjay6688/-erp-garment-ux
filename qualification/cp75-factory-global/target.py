"""Run the supported factory and populated upgrade on two separate PostgreSQL copies of the newly built FFDA predecessor."""
import json
import os
from pathlib import Path
import tempfile
import traceback

from close11 import checkpoint, frozen
from live import WORK as PRIVATE, start
import factory
import history
from handoff import main as record_pair

OUT=Path(os.environ["STAGE_PATH"])
WORK=Path(os.environ["GITHUB_WORKSPACE"])


def write(label,value):
    path=OUT/(label+".json")
    tmp=path.with_suffix(".part")
    tmp.write_text(json.dumps(value,sort_keys=True,indent=2,default=str)+"\n")
    tmp.replace(path)
    print("CP75_PAIR",label,flush=True)


def main():
    image_id=frozen.docker("current local PostgreSQL image",["inspect","-f","{{.Image}}",frozen.SOURCE])
    digests=json.loads(frozen.docker("current image digests",["image","inspect","-f","{{json .RepoDigests}}",image_id]))
    image=next(x for x in digests if "@sha256:" in x)
    PRIVATE.mkdir(mode=0o700,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=PRIVATE) as root:
        archive=Path(root)/"old-global.tar.gz"
        proof=frozen.freeze(archive,image_id)
        public=WORK/"capture/qualification/close11/auditor-public.pem"
        sealed=checkpoint.seal(archive,OUT/"ffda-source.cp75",public)
        write("ffda-recovery",{"copy":proof,"image":image,"sha256":checkpoint.digest(archive),"archive":sealed,
                               "origin":"FFDA built from an independently verified BF","production_go":False})
        errors={}
        for lane in ("clean","upgrade"):
            try:
                container,socket=start("factory-"+lane,archive,image,proof,"cp6_rollback")
                factory.socket(socket)
                history.OUT=OUT/lane
                history.OUT.mkdir(exist_ok=True)
                assert history.seal()["sha256"]==history.OLD
                if lane=="clean":
                    factory.finish(container,image,"independently reproduced and verified clean BF")
                else:
                    history.exercise_upgrade(container,image,"separate populated FFDA factory copy","factory-history-restore")
            except Exception as error:
                errors[lane]={"type":type(error).__name__,"reason":str(error).splitlines()[0][:420] if str(error) else "",
                    "frames":[[Path(frame.filename).name,frame.name,frame.lineno] for frame in traceback.extract_tb(error.__traceback__)[-10:]]}
                write(lane+"-error",errors[lane])
        if errors:
            raise ValueError("Incomplete installation evidence: "+", ".join(errors))
        record_pair(OUT/"clean",OUT/"upgrade",OUT/"comparison.json")
        print("CP75_PAIR SIX_AREAS_MATCH",flush=True)


if __name__=="__main__":
    main()
