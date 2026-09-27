"""Install the frozen candidate on a disposable local Supabase PostgreSQL.

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
BASE = "08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec"
PGURL = os.environ["PGURL"]
RESULT = ROOT / "bd-blind-chain-result.json"


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


def main() -> None:
    tree = subprocess.check_output(["git", "rev-parse", BASE + "^{tree}"], cwd=ROOT, text=True).strip()
    assert tree == "ba3c3fc221ee72dc521991c52cc38ee9b624d9fa", tree
    run(["git", "diff", "--exit-code", BASE, "--", "scripts/cp6_bd_objects_pricing.sql",
         "scripts/cp6_bd_objects_invoice.sql", "scripts/cp6_bd_objects_router.sql",
         "supabase/dev/cp6_bd_t1_family.sql"], "FROZEN_PRODUCT_SOURCE")
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
        psql_file(file, file.name)
        stamp, name = file.stem.split("_", 1)
        with psycopg.connect(PGURL) as conn:
            conn.execute("""insert into supabase_migrations.schema_migrations(version,name,statements)
                            values(%s,%s,%s)""", (stamp, name, [file.read_text()]))
    for family in ("aw", "ax", "ay", "az", "ba", "bb", "bc", "bd"):
        file = ROOT / f"supabase/dev/cp6_{family}_t1_family.sql"
        psql_file(file, "T1_" + family.upper())
    with psycopg.connect(PGURL) as conn:
        check = conn.execute("select to_regclass('erp.bd_laundry_invoices_v1') is not null").fetchone()[0]
    assert check
    RESULT.write_text(json.dumps({"status": "INSTALLED_DEV_T1", "candidate": BASE,
                                  "migrations": len(files), "product_source_modified": False,
                                  "production_go": False}, indent=2))
    print(RESULT.read_text(), flush=True)


if __name__ == "__main__":
    main()
