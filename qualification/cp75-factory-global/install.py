"""Use the released SKU and Global installers on a new, BF-verified disposable database."""
import gzip
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
    os.chdir(ROOT / "writer")
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
    settings = json.loads((TEMP/"cp75-sku-settings.json").read_text())
    assert all(k not in ("GH_TOKEN", "PGURL", "GITHUB_TOKEN") and not k.startswith(("GITHUB_","RUNNER_")) for k in settings)
    os.environ.update(settings)
    os.environ["CP6_FIXTURE_SCHEMA_PROFILE"] = "HOSTED_USAGE"
    with source_engine(ROOT, expected_sources, full_check=False, use_reviewed_digest=True) as (entry, engine):
        provider = p20_batch.bind_provider(provider, RELEASE, candidate)
        g04 = bind_switch_roll(provider, ROOT/"g04-product")
        receipt = bind_s06(provider, ROOT/"s06-product", g04)
        # The legacy qualification writes receipts under GITHUB_WORKSPACE/close11-evidence.
        (WORK/"close11-evidence").mkdir(exist_ok=True)
        binding.bind(provider, ROOT)
        seed, identities, seed_proof = bind_seed(WORK/"foundation-writer")
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
            admitted = json.loads(Path(__file__).with_name("ffda-catalogue.json").read_text())
            if not (pre["contract"] == admitted["server"]["contract"] and pre["counts"] == admitted["server"]["counts"]
                    and pre["groups"] == len(pre["counts"]) == 25 and admitted["server"]["sha256"] == OLD):
                raise ValueError("FFDA catalogue object census differs from the archived reference")
            captured = provider.capture(cur)
            if captured != state.global_installation["after"] or pre != state.global_installation["sealed"]["actual_parent_root_receipt"]["catalogue_fingerprint"]:
                raise ValueError("FFDA does not match the owning release installer's captured catalogue")
            with gzip.open(OUT/"ffda-object-hashes.json.gz", "wt", encoding="utf-8") as dest:
                json.dump({group:{key:binding.pin(value) for key,value in entries} for group,entries in captured.items()},dest,sort_keys=True)
            raw_catalogue = binding.pin(captured)
            exact = pre == admitted["server"] and raw_catalogue == admitted["full25_sha256"]
            source_receipt = json.loads((WORK/"close11-evidence/preseal.json").read_text())
            if source_receipt["product"] != admitted["product"] or source_receipt["full25_installed_sha256"] != raw_catalogue:
                raise ValueError("Source-to-catalogue identity differs from the FFDA product")
            guard_name = "cp7_credit.assert_source_native_trigger_census_v1()"
            from parent_catalogue import LITERAL
            guard_text = dict(captured["functions"])[guard_name][0]
            guard, = LITERAL.findall(guard_text)
            qualified = {"server":pre,"expected":OLD,"stage_timings":timings,"archived_catalogue_equal":exact,
                         "capture_sha256":raw_catalogue,"archived_capture_sha256":admitted["full25_sha256"],
                         "group_hashes":{g:binding.pin(entries) for g,entries in captured.items()},
                         "credit_guard_literal":guard,"FFDA_source":source_receipt,
                         "sku_and_dated_proof":report["verified_SKU_and_dated_Laundry_before_Global"],
                         "source_run":admitted["origin_run"],"production_go":False}
            write("global-before-commit",qualified)
            if not exact and os.environ.get("CP75_REBUILT_DIAGNOSTIC") != "1":
                raise ValueError("FFDA_ARCHIVED_FULL25_DIFFERS")
            if not exact and (os.environ.get("CP75_FACTORY_ORIGINAL") == "1" or conn.info.dbname != "cp6_rollback"):
                raise ValueError("A reconstructed-path measurement may only use its disposable database")
            conn.commit()
            foundation.after_commit(cur, report)
        with engine.trusted_installer_connection() as conn, conn.cursor() as cur:
            actual = cur.execute(SERVER).fetchone()[0]
            assert actual == pre
            lifecycle.verify(cur, state)
        write("clean-ffda", {"seal": actual, "stages": list(timings), "BF": BF, "origin": "independent clean factory",
                             "inverse":report["focused_preuse_removal"], "archived_catalogue_equal":exact, "production_go": False})


if __name__ == "__main__":
    try:
        run()
    except Exception as error:
        message = (str(error).splitlines() or [type(error).__name__])[0][:450]
        write("install-error", {"type":type(error).__name__, "message":message,
                                "frames":[[Path(t.filename).name,t.name,t.lineno] for t in traceback.extract_tb(error.__traceback__)[-12:]]})
        print("CP75_GLOBAL_ERROR", type(error).__name__, message, flush=True)
        raise
