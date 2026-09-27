"""Install frozen BE on a disposable local Supabase PostgreSQL.

This is installation plumbing, not an oracle or product modification. Keep
original migrations and their admission checks intact. Fail and report the
first refused step; do not weaken any guard to obtain a green test.
"""
from __future__ import annotations

import gzip
import json
import os
import subprocess
import tempfile
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
BASE = "2c2fd5e8e0df5f8ada44402c93f70dbaf0fbbb5b"
PGURL = os.environ["PGURL"]
RESULT = ROOT / "be-blind-chain-result.json"


def run(args: list[str], name: str, *, stdin: str | None = None) -> None:
    process = subprocess.run(args, input=stdin, capture_output=True, text=True)
    print(json.dumps({"step": name, "exit": process.returncode,
                      "stdout_tail": process.stdout[-500:], "stderr_tail": process.stderr[-2000:]}), flush=True)
    if process.returncode:
        RESULT.write_text(json.dumps({"status": "BLOCKED", "step": name,
                                      "stdout_tail": process.stdout[-2000:],
                                      "stderr_tail": process.stderr[-6000:],
                                      "production_go": False}, indent=2))
        raise SystemExit(process.returncode)


def psql_file(path: Path, name: str) -> None:
    run(["psql", PGURL, "-X", "-v", "ON_ERROR_STOP=1", "-f", str(path)], name)


def closed_file(path: Path, name: str) -> None:
    """Satisfy, rather than bypass, the package's closed/drained admission."""
    target = psycopg.connect(PGURL, autocommit=True)
    maintenance = psycopg.connect(PGURL.rsplit("/", 1)[0] + "/template1", autocommit=True)
    try:
        maintenance.execute("alter database postgres with allow_connections false")
        run(["docker", "exec", "-i", "supabase_db_cp6-be-blind-local",
             "psql", "-U", "supabase_admin", "-d", "template1", "-X",
             "-v", "ON_ERROR_STOP=1", "-c",
             "select pg_terminate_backend(pid) from pg_stat_activity "
             f"where datname='postgres' and pid<>{int(target.info.backend_pid)}"],
            name + "_DRAIN")
        try:
            target.execute(path.read_text(), prepare=False)
            print(json.dumps({"step": name, "exit": 0, "closed_and_drained": True}), flush=True)
        except psycopg.Error as error:
            RESULT.write_text(json.dumps({"status": "BLOCKED", "step": name,
                                          "message": error.diag.message_primary,
                                          "sqlstate": error.sqlstate,
                                          "production_go": False}, indent=2))
            print(RESULT.read_text(), flush=True)
            raise
    finally:
        maintenance.execute("alter database postgres with allow_connections true")
        maintenance.close()
        target.close()


def main() -> None:
    tree = subprocess.check_output(["git", "rev-parse", BASE + "^{tree}"], cwd=ROOT, text=True).strip()
    assert tree == "20826407e5f98f798b1650f520300e85aebbd2eb", tree
    run(["git", "diff", "--exit-code", BASE, "--", "scripts/cp6_bd_objects_pricing.sql",
         "scripts/cp6_bd_objects_invoice.sql", "scripts/cp6_bd_objects_router.sql",
         "supabase/dev/cp6_bd_t1_family.sql", "supabase/dev/cp6_be_t1_family.sql",
         "scripts/cp6_be_objects_conversion.sql", "scripts/cp6_be_objects_redye.sql",
         "scripts/cp6_be_objects_pocket.sql"], "FROZEN_PRODUCT_SOURCE")
    fixture = ROOT / "supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz"
    with tempfile.TemporaryDirectory() as directory:
        plain = Path(directory) / "catalog_bootstrap.sql"
        with gzip.open(fixture, "rb") as source, plain.open("wb") as destination:
            import shutil
            shutil.copyfileobj(source, destination)
        psql_file(plain, "CP45A_CATALOG")
    psql_file(ROOT / "supabase/tests/fixtures/erp_enteng_cp45a_external_application_triggers.sql", "CP45A_EXTERNAL_TRIGGERS")
    files = [file for file in sorted((ROOT / "supabase/migrations").glob("*.sql"))
             if file.name[:14] > "20260902185106"]
    for file in files:
        if "PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE" in file.read_text():
            closed_file(file, file.name)
        else:
            psql_file(file, file.name)
        stamp, name = file.stem.split("_", 1)
        with psycopg.connect(PGURL) as conn:
            conn.execute("""insert into supabase_migrations.schema_migrations(version,name,statements)
                            values(%s,%s,%s)""", (stamp, name, [file.read_text()]))
    for family in ("aw", "ax", "ay", "az", "ba", "bb", "bc", "bd", "be"):
        file = ROOT / f"supabase/dev/cp6_{family}_t1_family.sql"
        if "PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE" in file.read_text():
            closed_file(file, "T1_" + family.upper())
        else:
            psql_file(file, "T1_" + family.upper())
    with psycopg.connect(PGURL) as conn:
        check = conn.execute("select to_regclass('erp.be_redye_services_v1') is not null").fetchone()[0]
    assert check
    RESULT.write_text(json.dumps({"status": "INSTALLED_BE_DEV_T1", "candidate": BASE,
                                  "migrations": len(files), "product_source_modified": False,
                                  "production_go": False}, indent=2))
    print(RESULT.read_text(), flush=True)


if __name__ == "__main__":
    main()
