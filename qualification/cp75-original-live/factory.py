"""Accept a physically identified, clean BF-to-FFDA database and bring its factory definitions to the final Global."""
import json
import os
from pathlib import Path
import tempfile

import psycopg

from close11 import checkpoint
import history
from live import WORK as PRIVATE, start
from reminder_source import apply_factory, sources

WORK=Path(os.environ["GITHUB_WORKSPACE"])
OUT=Path(os.environ["STAGE_PATH"])/"clean"


def write(name, data):
    path=OUT/(name+".json")
    tmp=path.with_suffix(".part")
    tmp.write_text(json.dumps(data,sort_keys=True,indent=2,default=str)+"\n")
    tmp.replace(path)
    print("CP75_CLEAN",name,flush=True)


def socket(path):
    os.environ["PGHOST"]=str(path)
    os.environ.pop("PGPORT",None)
    os.environ.pop("PGPASSWORD",None)


def finish(container, image, origin, *, catalogues=None):
    old,middle,target = catalogues or (history.OLD,history.MIDDLE,history.TARGET)
    OUT.mkdir(parents=True,exist_ok=True)
    history.OUT=OUT
    assert history.seal()["sha256"]==old
    install=history.load_installer("g14",WORK/"g14/qualification/close12/product","77cc2c35a78c1fde725e37199a80f87a5f9965e3")
    with psycopg.connect(**history.db()) as conn:
        changed=install.apply(conn,"up")
    midway=history.seal()
    assert changed["changed"] and midway["sha256"]==middle
    _,factory=sources(WORK/"auditor",WORK/"rig/qualification/cp75-order")
    with psycopg.connect(**history.db()) as conn:
        result=apply_factory(conn,factory)
    clean_seal=history.seal()
    assert clean_seal["sha256"]==target and clean_seal["groups"]==len(clean_seal["counts"])==25
    write("factory-target",{"origin":origin,"G14":changed,"factory_reader":result,"seal":clean_seal})
    before_rows=history.raw_state()
    pub=WORK/"capture/qualification/close11/auditor-public.pem"
    with tempfile.TemporaryDirectory(dir=PRIVATE) as directory:
        baseline=Path(directory)/"pre-events.tar.gz"
        before_meta=history.cold_copy(container,baseline,image)
        history.wait_for_seal(target)
        before_hash=checkpoint.digest(baseline)
        write("factory-baseline",{"rows_sequences":before_rows,"seal":clean_seal,"physical_sha256":before_hash,
                                 "archive":checkpoint.seal(baseline,OUT/"baseline.cp75",pub)})
        with psycopg.connect(**history.db()) as conn:
            day=conn.execute("select (current_timestamp at time zone 'Asia/Jakarta')::date").fetchone()[0]
        fixture=history.seed(day)
        observed=history.read_history(fixture)
        rows=history.raw_state()
        write("factory-posted",{"history":observed,"rows_sequences":rows,"target":target,"day":day,"origin":origin})
        posted=Path(directory)/"posted.tar.gz"
        posted_meta=history.cold_copy(container,posted,image)
        history.wait_for_seal(target)
        _,posted_socket=start("clean-posted-recovery",posted,image,posted_meta,"cp6_rollback")
        socket(posted_socket)
        restored=history.read_history(fixture)
        restored_rows=history.raw_state()
        actual=history.seal()
        assert restored==observed and restored_rows==rows and actual==clean_seal
        write("factory-restored",{"full25":actual,"raw_state_equal":True,"history_equal":True,
            "physical_sha256":checkpoint.digest(posted),"rows_sequences":len(rows),"archive":checkpoint.seal(posted,OUT/"posted.cp75",pub)})
        _,baseline_socket=start("clean-baseline-recovery",baseline,image,before_meta,"cp6_rollback")
        socket(baseline_socket)
        assert history.raw_state()==before_rows and history.seal()==clean_seal
        write("factory-baseline-restored",{"catalogue":clean_seal,"rows_sequences":len(before_rows),
             "physical_sha256":before_hash,"all_rows_and_sequences_equal":True,"production_go":False})


if __name__=="__main__":
    original=Path(os.environ["RUNNER_TEMP"])/"cp75-original-observations/clean-opened.json"
    receipt=json.loads(original.read_text())
    assert receipt["origin_run"]==44800849536 and receipt["container"]=="supabase_db_cp5-local"
    assert receipt["catalogue"]=="b036261ee8902fc3be5307d54cf2b021dd2e2b419e24100655a7a338b70bad0a"
    meta=json.loads((PRIVATE/"clean.json").read_text())
    socket(PRIVATE/"clean-socket")
    finish(receipt["container"],meta["image"],"actual BF physical archive 44800849536/14661875761")
