"""Run the released first CP7 installation on a clean BF carrier and preserve every boundary."""
import hashlib
import json
import os
import traceback
import subprocess
import importlib.util
import tempfile
from pathlib import Path

import psycopg
import cp6_g01_fingerprint as fingerprints
import cp6_successor_regression as released_boundary

EXPECTED = "b036261ee8902fc3be5307d54cf2b021dd2e2b419e24100655a7a338b70bad0a"
OUT = Path(os.environ["CP75_STAGE_OUT"])
OUT.mkdir(mode=0o700, exist_ok=True)
DB = dict(conninfo=released_boundary.ADMIN, connect_timeout=10, options="-c statement_timeout=160000 -c lock_timeout=8000")


def canonical(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def administrative_query(statement):
    cmd = ["docker","exec","-u","postgres","supabase_db_cp5-local","psql","-U","supabase_admin",
           "-d","cp6_rollback","-XAtq","-v","ON_ERROR_STOP=1","-c",statement]
    return json.loads(subprocess.check_output(cmd, text=True))


def read():
    row = administrative_query("""select jsonb_build_array(current_database(), current_setting('server_version_num'),
        (select count(*) from supabase_migrations.schema_migrations),
        (select count(*) from erp.schema_migrations), (select count(*) from auth.users),
        (select count(*) from erp.app_users),
        (select count(*) from erp.schema_migrations where version='v2.6.20bf'))""")
    groups = administrative_query(fingerprints.SUMMARY)
    names = administrative_query("select coalesce(jsonb_agg(nspname order by nspname),'[]') from pg_namespace where nspname like 'cp7%'")
    return {"server":row, "catalogue":canonical(groups),"groups":groups,"cp7_schemas":names}


def save(data):
    temp = OUT / "forward.tmp"
    temp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n")
    temp.replace(OUT / "forward.json")


def preserve_verified_stage(report):
    from close11 import checkpoint, frozen
    source = Path(os.environ["GITHUB_WORKSPACE"]) / "qualification-source/qualification/cp75-clean-bf/checkpoint.py"
    spec = importlib.util.spec_from_file_location("bf_recovery", source)
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    installed = verifier.readback(frozen.SOURCE)
    image = frozen.docker("installed image", ["inspect","-f","{{.Image}}",frozen.SOURCE])
    public = Path(os.environ["GITHUB_WORKSPACE"]) / "capture/qualification/close11/auditor-public.pem"
    with tempfile.TemporaryDirectory(dir=os.environ["RUNNER_TEMP"]) as folder:
        raw = Path(folder) / "stage.tar.gz"
        metadata = frozen.freeze(raw,image)
        restored = verifier.boot(raw,metadata,image)
        assert restored == installed
        archive = checkpoint.seal(raw,OUT/"first-cp7-release.cp75",public)
        report["checkpoint"] = {"archive":archive,"archive_plaintext_sha256":checkpoint.digest(raw),
                                "source":installed,"restored":restored,"verification":metadata}
        save(report)


def main():
    initial = read()
    report = {"status":"BF_CONFIRMED", "source":"factory recreation matched to Astra BF",
              "original_checkpoint_used": False,"initial":initial,"global_parity":False,"production_go":False}
    save(report)
    try:
        assert initial["catalogue"] == EXPECTED and initial["server"] == ["cp6_rollback","170006",128,113,0,0,1], (initial["catalogue"],initial["server"])
        import cp7_current_installation as release
        report["entry"] = release.CONTRACT
        with psycopg.connect(**DB) as conn, conn.cursor() as cur:
            state = release.install(cur)
            verified = release.verify(cur, state)
        # A second session must see the committed change.
        current = read()
        assert current["catalogue"] != initial["catalogue"] and len(current["cp7_schemas"]) > len(initial["cp7_schemas"])
        report.update(status="FIRST_RELEASE_INSTALLED", installed=current, verified=verified)
        preserve_verified_stage(report)
        # The released inverse is tested after the committed boundary has been preserved.
        with psycopg.connect(**DB) as conn, conn.cursor() as cur:
            release.rollback_preuse(cur, state)
        after = read()
        assert after == initial
        report.update(status="FIRST_RELEASE_AND_INVERSE_CONFIRMED", after_inverse=after)
    except Exception as error:
        report.update(error_type=type(error).__name__,error=str(error).split("\n")[0][:700],
                      frames=[{"file":Path(x.filename).name,"line":x.lineno,"function":x.name} for x in traceback.extract_tb(error.__traceback__)[-10:]],
                      observed_after_error=read())
        report["status"]="FORWARD_STOPPED"
        raise
    finally:
        save(report)
        print("CP75_FORWARD_JSON "+json.dumps({k:v for k,v in report.items() if k not in ("initial","installed","observed_after_error","verified","after_inverse")}),flush=True)
        print("CP75_CATALOGUES "+json.dumps({k:report[k]["catalogue"] for k in ("initial","installed","observed_after_error","after_inverse") if k in report}), flush=True)


if __name__ == "__main__":
    main()
