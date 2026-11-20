"""Run the released first CP7 installation on a clean BF carrier and preserve every boundary."""
import hashlib
import json
import os
import traceback
from pathlib import Path

import psycopg
import cp6_g01_fingerprint as fingerprints

EXPECTED = "b036261ee8902fc3be5307d54cf2b021dd2e2b419e24100655a7a338b70bad0a"
OUT = Path(os.environ["CP75_STAGE_OUT"])
OUT.mkdir(mode=0o700, exist_ok=True)
DB = dict(host="127.0.0.1", port=54322, dbname="cp6_rollback", user="postgres", password="postgres",
          connect_timeout=10, options="-c statement_timeout=120000 -c lock_timeout=8000")


def canonical(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def read():
    with psycopg.connect(**DB) as conn, conn.cursor() as cur:
        row = cur.execute("""select current_database(), current_setting('server_version_num'),
                   (select count(*) from supabase_migrations.schema_migrations),
                   (select count(*) from erp.schema_migrations), (select count(*) from auth.users),
                   (select count(*) from erp.app_users),
                   (select count(*) from erp.schema_migrations where version='v2.6.20bf')""").fetchone()
        groups = cur.execute(fingerprints.SUMMARY).fetchone()[0]
        names = cur.execute("select nspname from pg_namespace where nspname like 'cp7%' order by 1").fetchall()
        return {"server":list(row), "catalogue":canonical(groups),"groups":groups,"cp7_schemas":[x[0] for x in names]}


def save(data):
    temp = OUT / "forward.tmp"
    temp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str) + "\n")
    temp.replace(OUT / "forward.json")


def main():
    initial = read()
    assert initial["catalogue"] == EXPECTED and initial["server"] == ["cp6_rollback","170006",128,113,0,0,1]
    report = {"status":"BF_CONFIRMED", "source":"factory recreation matched to Astra BF",
              "original_checkpoint_used": False,"initial":initial,"global_parity":False,"production_go":False}
    save(report)
    try:
        import cp7_current_installation as release
        report["entry"] = release.CONTRACT
        with psycopg.connect(**DB) as conn, conn.cursor() as cur:
            state = release.install(cur)
            verified = release.verify(cur, state)
        # A second session must see the committed change.
        current = read()
        assert current["catalogue"] != initial["catalogue"] and len(current["cp7_schemas"]) > len(initial["cp7_schemas"])
        report.update(status="FIRST_RELEASE_INSTALLED", installed=current, verified=verified)
        # A physical comparison is reserved for the final handoff. This check also tests the released pre-use inverse.
        with psycopg.connect(**DB) as conn, conn.cursor() as cur:
            release.rollback_preuse(cur, state)
        after = read()
        assert after == initial
        report.update(status="FIRST_RELEASE_AND_INVERSE_CONFIRMED", after_inverse=after)
    except Exception as error:
        report.update(error_type=type(error).__name__,error=str(error).replace(DB["password"] + "@","***@")[:900],
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
