"""Read the current Global from a new session and after independent physical recovery."""
import json
import os
from pathlib import Path
import tempfile

import traceback
import history
from compare import compare
import psycopg
from close11 import checkpoint, frozen
from history import MIDDLE, OLD, TARGET, WORK, db, load_installer, raw_state, read_history, seal, seed
from live import start, WORK as SOCKET_DIR

OUT = Path(os.environ["STAGE_PATH"])


def save(name, value):
    path = OUT/(name + ".json")
    temp = path.with_suffix(".part")
    temp.write_text(json.dumps(value, sort_keys=True, indent=2, default=str) + "\n")
    temp.replace(path)
    print("CP75_FACTORY", name, flush=True)


def clean(container, image, temp):
    history.OUT=OUT/"clean"
    history.OUT.mkdir(exist_ok=True)
    assert seal()["sha256"] == OLD
    steps = [("G14", WORK/"g14/qualification/close12/product", "77cc2c35a78c1fde725e37199a80f87a5f9965e3", MIDDLE),
             ("reminder", WORK/"rig/qualification/cp75-order", "7a6d8ec30f17ddada5941c9a923f699a1367656a", TARGET)]
    for label, path, blob, expected in steps:
        tool = load_installer(label, path, blob)
        with psycopg.connect(**db()) as conn:
            result = tool.apply(conn, "up")
        observed = seal()
        assert result["changed"] and observed["sha256"] == expected and observed["groups"] == len(observed["counts"]) == 25
        save("clean/factory-" + label, {"product_routine":blob,"installation":result,"seal":observed,"production_go":False})
    with psycopg.connect(**db()) as conn:
        day = conn.execute("select (current_timestamp at time zone 'Asia/Jakarta')::date").fetchone()[0]
    fixture = seed(day)
    before = read_history(fixture)
    rows = raw_state()
    save("clean/factory-posted", {"history":before, "rows_sequences":rows, "target":TARGET, "day":day,
                            "origin":"independently rebuilt clean BF"})
    raw = temp/"fresh-with-history.tar.gz"
    metadata = history.cold_copy(container,raw,image)
    _, sock = start("factory-restore",raw,image,metadata,"cp6_rollback")
    select_socket(sock)
    restored, restored_rows, final = read_history(fixture), raw_state(), seal()
    assert restored == before and restored_rows == rows and final["sha256"] == TARGET
    envelope = checkpoint.seal(raw, OUT/"clean/clean-factory-target.cp75", WORK/"capture/qualification/close11/auditor-public.pem")
    save("clean/factory-restored", {"full25":final,"raw_state_equal":True,"history_equal":True,"rows_sequences":len(rows),
        "archive":envelope,"image":image,"physical_sha256":checkpoint.digest(raw),"production_go":False})


def select_socket(socket):
    os.environ["PGHOST"]=str(socket)
    os.environ.pop("PGPORT",None)
    os.environ.pop("PGPASSWORD",None)


def main():
    image_id = frozen.docker("current PostgreSQL image", ["inspect","-f","{{.Image}}",frozen.SOURCE])
    options = json.loads(frozen.docker("current image digests", ["image","inspect","-f","{{json .RepoDigests}}",image_id]))
    image = next(x for x in options if "@sha256:" in x)
    SOCKET_DIR.mkdir(mode=0o700, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SOCKET_DIR) as root:
        temp=Path(root)
        archive=temp/"ffda-start.tar.gz"
        proof=frozen.freeze(archive,image_id)
        pub=WORK/"capture/qualification/close11/auditor-public.pem"
        encrypted=checkpoint.seal(archive,OUT/"ffda-source.cp75",pub)
        save("ffda-recovery",{"copy":proof,"image":image,"sha256":checkpoint.digest(archive),"archive":encrypted,
             "factory_origin":"independently reconstructed and verified BF","production_go":False})
        errors={}
        for lane in ("clean","upgrade"):
            try:
                name,socket=start("factory-"+lane,archive,image,proof,"cp6_rollback")
                select_socket(socket)
                history.OUT=OUT/lane
                history.OUT.mkdir(exist_ok=True)
                assert seal()["sha256"]==OLD
                if lane=="clean":
                    clean(name,image,temp)
                else:
                    history.exercise_upgrade(name,image,"populated clone of a fresh verified FFDA factory","factory-history-restore")
            except Exception as error:
                errors[lane]={"type":type(error).__name__,"reason":str(error).splitlines()[0][:450] if str(error) else "",
                     "frames":[[Path(frame.filename).name,frame.name,frame.lineno] for frame in traceback.extract_tb(error.__traceback__)[-10:]]}
                save(lane+"-error",errors[lane])
        if errors:
            raise ValueError("Incomplete factory lanes: "+", ".join(errors))
        result=compare(OUT/"clean",OUT/"upgrade")
        save("comparison",result)
        assert all(result["six_areas"].values()),result["differences"]


if __name__ == "__main__":
    main()
