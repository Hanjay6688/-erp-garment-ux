"""Exercise the released SKU installation on an independent database whose BF catalogue matches the certified source."""
from datetime import date
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import traceback
import tempfile

from close11 import frozen, checkpoint
from sku_credit_seal import prepare as prepare_credit
from sku_parent import CATALOGUE_PIN, SKU, retained, source_engine
from sku_progress import before_mandor, observe as stage
from realtime_comparator import prepare as catalogue_check
from snapshot_prerequisites import observe as observe_prerequisites

WORK = Path(os.environ["GITHUB_WORKSPACE"])
ROOT = WORK / "sku-build"
TEMP = Path(os.environ["RUNNER_TEMP"])
OUT = Path(os.environ["STAGE_PATH"])
BF = "b036261ee8902fc3be5307d54cf2b021dd2e2b419e24100655a7a338b70bad0a"


def save(report, name):
    report["phases"].append(name)
    tmp = OUT / "progress.new"
    tmp.write_text(json.dumps(report, sort_keys=True, indent=2, default=str)+"\n")
    tmp.replace(OUT / "progress.json")
    print("CP75_SKU_STAGE", name, flush=True)


def load_bf():
    spec = importlib.util.spec_from_file_location("bf_observer", WORK/"qualification-source/qualification/cp75-clean-bf/checkpoint.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    report = {"product_goal":"48858590","production_go":False,"original_checkpoint_used":False,
              "carrier":"independent factory reproduction certified against BF","phases":[]}
    try:
        bf = load_bf()
        source = bf.readback(frozen.SOURCE)
        measured = source["cp6_rollback"]
        assert measured["catalogue_sha256"] == BF and measured["platform_migrations"] == 128 and measured["application_migrations"] == 113
        report["BF"] = source
        save(report, "BF_CONFIRMED")
        cat, mark, expected = retained(TEMP/"cp75-original-sku.zip")
        for k,v in json.loads((TEMP/"cp75-sku-settings.json").read_text()).items():
            if k.startswith("GITHUB_") or k=="GH_TOKEN":
                raise ValueError("Unexpected inherited credential or workflow identity")
            os.environ[k]=v
        os.environ["CP6_FIXTURE_SCHEMA_PROFILE"]="HOSTED_USAGE"
        with source_engine(ROOT, expected, full_check=False, use_reviewed_digest=True) as (entry, engine):
            save(report,"QUALIFIED_SOURCE_GRAPH")
            capture, fingerprint, groups = entry.load("qualified_sku_catalogue",ROOT/"auditor"/SKU/"global_parent_catalogue.py").exact_readers()
            comparator = entry.load("qualified_sku_comparator",WORK/"released/qualification/parent_catalogue.py")
            reviewed = comparator.reviewed_fields(cat,CATALOGUE_PIN)
            compare = catalogue_check(comparator,cat,CATALOGUE_PIN,archived_startup_day=date(2026,11,13))
            inputs = {"parent_catalogue_fingerprint":mark,"parent_catalogue_equivalence":reviewed}
            credit = prepare_credit(entry)
            engine.runner.scheduler_quiet(engine.package.boundary.ADMIN)
            with engine.trusted_installer_connection() as conn,conn.cursor() as cur:
                engine.current_native.acquire_boundary(cur)
                with before_mandor(lambda:credit.record_baseline(cur)):
                    prior=engine._sku_install_parent(cur)
                save(report,"SKU_PREDECESSORS_INSTALLED_IN_TRANSACTION")
                with stage("SKU_AUTOMATIC_DELTA"):
                    state=engine._sku_install_delta(cur,prior)
                engine._sku_verify_installed(cur,state)
                data=engine.predecessor.catalog._data(cur)
                credit.install_final(cur)
                assert engine.predecessor.catalog._data(cur)==data
                actual=capture(cur)
                assert set(actual)==groups
                with credit.owning._postgres_reader(cur):
                    proof=compare(cur,actual,inputs,fingerprint)
                assert proof["status"]=="GLOBAL_ACTUAL_PARENT_CATALOGUE_AND_CENSUS_VERIFIED"
                assert observe_prerequisites(cur)["status"]=="PASS"
                report["sku_receipt"] = proof
                conn.commit()
            with engine.trusted_installer_connection() as conn,conn.cursor() as cur:
                again=capture(cur)
                with credit.owning._postgres_reader(cur):
                    assert compare(cur,again,inputs,fingerprint)["status"]==proof["status"]
            save(report,"SKU_COMMITTED_AND_READ_BACK")
        image=frozen.docker("installed image",["inspect","-f","{{.Image}}",frozen.SOURCE])
        public=WORK/"capture/qualification/close11/auditor-public.pem"
        with tempfile.TemporaryDirectory(dir=TEMP) as root:
            raw=Path(root)/"sku.tar.gz"
            metadata=frozen.freeze(raw,image)
            before=bf.readback(frozen.SOURCE)
            after=bf.boot(raw,metadata,image)
            assert before==after
            report["recovery"]={"before":before,"after":after,"copy":metadata,"plaintext_sha256":checkpoint.digest(raw),
                                "archive":checkpoint.seal(raw,OUT/"sku.cp75",public)}
        save(report,"SKU_PHYSICAL_RESTORE")
    except Exception as err:
        report["error"]={"class":type(err).__name__,"reason":str(err).splitlines()[0][:440],
                         "frames":[[Path(t.filename).name,t.name,t.lineno] for t in traceback.extract_tb(err.__traceback__)[-8:]]}
        print("CP75_SKU_ERROR",json.dumps(report["error"]),flush=True)
        save(report,"STOPPED")
        raise


if __name__=="__main__":
    main()
