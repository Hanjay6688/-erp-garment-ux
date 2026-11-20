"""Use the released SKU and Global installers on a new, BF-verified disposable database."""
import json
import os
import traceback
from pathlib import Path

import reviewed_ordinary as licensed
from close11 import binding
from global_owning import owning, p20_batch
from global_owning.dated_lifecycle import DatedLifecycle
from global_owning.foundation import Foundation, bind_seed
from p21.g04_catalogue import bind_switch_roll
from p21.s06_catalogue import bind as bind_s06
from sku_credit_seal import prepare as credit_seal
from sku_parent import retained, source_engine

WORK = Path(os.environ["GITHUB_WORKSPACE"])
ROOT = WORK / "sku-build"
RELEASE = WORK / "global-release"
TEMP = Path(os.environ["RUNNER_TEMP"])
OUT = Path(os.environ["STAGE_PATH"])
OLD = "a3da0ecf21909731ab8474c54a7c91afb75bb58dd8b6042cc82314b20808dbd7"
BF = "b036261ee8902fc3be5307d54cf2b021dd2e2b419e24100655a7a338b70bad0a"
SERVER = "select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()"


def write(name, detail):
    path = OUT / (name + ".json")
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(detail, sort_keys=True, indent=2, default=str) + "\n")
    temp.replace(path)
    print("CP75_GLOBAL", name, flush=True)


def active_day(cursor):
    return cursor.execute("select (current_timestamp at time zone 'Asia/Jakarta')::date").fetchone()[0]


def run():
    origin = json.loads((OUT/"bf-verified.json").read_text())["cp6_rollback"]
    assert (origin["catalogue_sha256"], origin["platform_migrations"], origin["application_migrations"]) == (BF,128,113)
    candidate = ROOT / "global-candidate"
    catalogue, _, expected_sources = retained(TEMP / "cp75-original-sku.zip")
    root_raw = (RELEASE / licensed.ROOT_PATH).read_bytes()
    profile_raw = (RELEASE / licensed.PROFILE_PATH).read_bytes()
    profile = json.loads(profile_raw)
    licensed.admit(candidate, ROOT/"auditor", root_raw, profile_raw)
    owning.verify_candidate(candidate)
    original, proof = owning.prepared_provider(candidate, root_raw, catalogue)
    assert proof["root"] == licensed.ROOT_PIN
    owning.require_gates(licensed.GATES)
    admission = owning.private_admission(owning.load("cp75_retained_admission",candidate/owning.ADMISSION), licensed.GATES)
    admission.runtime_admission(root_raw, profile_raw)
    provider = owning.private_provider(original, admission)
    with owning.candidate_imports(candidate):
        owning.reviewed_profile(provider, profile_raw, root_raw)
    provider = p20_batch.bind_provider(provider, RELEASE, candidate)
    g04 = bind_switch_roll(provider, ROOT/"g04-product")
    receipt = bind_s06(provider, ROOT/"s06-product", g04)
    # The legacy qualification writes receipts under GITHUB_WORKSPACE/close11-evidence.
    (WORK/"close11-evidence").mkdir(exist_ok=True)
    binding.bind(provider, ROOT)
    seed, identities, seed_proof = bind_seed(ROOT/"writer")
    settings = json.loads((TEMP/"cp75-sku-settings.json").read_text())
    assert all(k not in ("GH_TOKEN", "PGURL", "GITHUB_TOKEN") and not k.startswith(("GITHUB_","RUNNER_")) for k in settings)
    os.environ.update(settings)
    os.environ["CP6_FIXTURE_SCHEMA_PROFILE"] = "HOSTED_USAGE"
    with source_engine(ROOT, expected_sources, full_check=False, use_reviewed_digest=True) as (entry, engine):
        credit = credit_seal(entry)
        foundation = Foundation(seed, identities, seed_proof, provider, active_day)
        lifecycle = DatedLifecycle(engine, provider, root_raw, profile_raw, None, credit=credit,
                                   sku_catalogue=catalogue, inputs=profile, foundation=foundation)
        engine.runner.scheduler_quiet(engine.package.boundary.ADMIN)
        write("global-source", {"sku_source_checked": True, "combined_tree": owning.COMBINED,
                                "FFDA_tree":"760f38cc80ee9ca15e62a86ba358dfd8e858d895", "BF": origin, "production_go": False})
        with engine.trusted_installer_connection() as conn, conn.cursor() as cur:
            engine.current_native.acquire_boundary(cur)
            timings, report = [], {}
            state = lifecycle.install_cycle(cur, timings, report)
            lifecycle.verify(cur, state)
            receipt(state.global_installation)
            pre = cur.execute(SERVER).fetchone()[0]
            assert pre["sha256"] == OLD and pre["groups"] == len(pre["counts"]) == 25
            conn.commit()
            foundation.after_commit(cur, report)
        with engine.trusted_installer_connection() as conn, conn.cursor() as cur:
            actual = cur.execute(SERVER).fetchone()[0]
            assert actual == pre
            lifecycle.verify(cur, state)
        write("clean-ffda", {"seal": actual, "stages": list(timings), "BF": BF, "origin": "independent clean factory",
                             "inverse":report["focused_preuse_removal"], "production_go": False})


if __name__ == "__main__":
    try:
        run()
    except Exception as error:
        write("install-error", {"type":type(error).__name__, "message":str(error).splitlines()[0][:450],
                                "frames":[[Path(t.filename).name,t.name,t.lineno] for t in traceback.extract_tb(error.__traceback__)[-12:]]})
        print("CP75_GLOBAL_ERROR", type(error).__name__, str(error).splitlines()[0][:400], flush=True)
        raise
