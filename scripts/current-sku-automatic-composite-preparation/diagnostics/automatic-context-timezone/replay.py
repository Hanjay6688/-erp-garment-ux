from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
HEAD = "e4eaaecebad1f0ba11ab1542b5df89a6423a8a1e"
ARCHIVE_SIZE = 96749933
ARCHIVE_SHA256 = "dd9e31355a0820d1650e438a8913c49450a10dbc342789ed94f3418c1be6363b"
CATALOGUE_SHA256 = "5ff582717522b766c12024c1bf3299066475f14a3c6021a3543f378f829e0c07"
TABLES = (
    "erp.rework_orders", "erp.be_rework_targets_v1", "erp.bs_cases",
    "erp.fg_lots", "erp.production_orders", "erp.fg_stock_movements",
    "erp.product_conversions", "erp.be_conversion_sources_v1",
    "erp.be_execution_context_v1", "erp.hpp_versions",
    "cp7_sku_conversion.automatic_context_v5", "cp7_sku_conversion.groups_v1",
    "cp7_sku_conversion.execution_v1", "cp7_sku_conversion.base_money_events_v4",
    "cp7_sku_conversion.cost_events_v3", "cp7_sku_conversion.valuation_events_v2",
)
SIGNATURES = (
    "erp.require_internal()",
    "cp7_sku_conversion.automatic_valid_v5()",
    "cp7_sku_conversion.automatic_enter_v5(uuid,text,uuid)",
    "cp7_sku_conversion.automatic_scope_v5(uuid,uuid,text)",
    "cp7_sku_conversion.automatic_assert_native_v5(uuid,text,uuid,jsonb)",
    "cp7_sku_conversion.pool_quote_v2(uuid,uuid,text)",
)
AFFECTED = SIGNATURES[1:3]
ANCHOR = " SET search_path TO ''\nAS $function$"
PATCH = " SET search_path TO ''\n SET \"TimeZone\" TO 'UTC'\nAS $function$"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def read_original(path: Path) -> dict:
    assert path.stat().st_size == ARCHIVE_SIZE
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == ARCHIVE_SHA256
    with ZipFile(path) as archive:
        assert len(archive.infolist()) == len(set(archive.namelist())) == 212
        assert archive.testzip() is None
        report = json.loads(archive.read("CP7_SKU_CURRENT_PARENT_MONEY_AUTOMATIC_QUALIFICATION.json"))
        assert report["qualification_commit"] == HEAD and report["cp6_restored"] is True
        raw = archive.read("SKU_GLOBAL_PARENT_ACTUAL_FULL25.json")
    assert len(raw) == 16048163 and digest(raw) == CATALOGUE_SHA256
    return json.loads(raw)


def sql_for(catalogue: dict) -> tuple[str, dict]:
    functions = dict(catalogue["functions"])
    sql = ["BEGIN;", "CREATE SCHEMA erp;", "CREATE SCHEMA cp7_sku_conversion;"]
    for name in TABLES:
        cols = sorted((row for key, row in catalogue["columns"] if key.rsplit(":", 1)[0] == name),
                      key=lambda row: row[1])
        assert cols and all("." not in row[2] for row in cols), name
        sql.append(f"CREATE TABLE {name} (" + ", ".join(identifier(row[0]) + " " + row[2] for row in cols) + ");")
    sql.append((HERE / "fixture.sql").read_text())
    sql.extend(functions[signature][0] + ";" for signature in SIGNATURES)
    sql.append((HERE / "before.sql").read_text())
    updated = {}
    for signature in AFFECTED:
        original = functions[signature][0]
        assert original.count(ANCHOR) == 1 and 'SET "TimeZone"' not in original
        updated[signature] = original.replace(ANCHOR, PATCH)
        assert updated[signature].replace(PATCH, ANCHOR) == original
    sql.extend(definition + ";" for definition in updated.values())
    sql.append((HERE / "after.sql").read_text())
    sql.extend(["ROLLBACK;", "SELECT 'CP7_TZ_REPLAY_CLEAN' AS receipt WHERE NOT EXISTS "
                "(SELECT 1 FROM pg_namespace WHERE nspname IN ('erp','cp7_sku_conversion'));"])
    facts = {
        "actual_functions": {signature: {"sha256": digest(functions[signature][0].encode()),
                                        "owner": functions[signature][1], "acl": functions[signature][-1]}
                             for signature in SIGNATURES},
        "candidate_functions": {signature: digest(body.encode()) for signature, body in updated.items()},
        "actual_tz_readers": [sig for sig, row in functions.items()
                              if 'SET "TimeZone"' in row[0] and "automatic_" in row[0]],
        "table_row_type_count": len(TABLES),
    }
    return "\n\n".join(sql) + "\n\n", facts


def main() -> None:
    archive, bin_path, cluster, out = map(Path, sys.argv[1:])
    out.mkdir(parents=True, exist_ok=True)
    sql, facts = sql_for(read_original(archive))
    run = subprocess.run(
        [str(bin_path / "postgres"), "--single", "-j", "-D", str(cluster), "postgres"],
        input=sql, text=True, encoding="utf-8", capture_output=True, timeout=120,
    )
    trace = run.stdout + "\n" + run.stderr
    (out / "POSTGRES_TIMEZONE_REPLAY.log").write_text(trace)
    if run.returncode != 0 or re.search(r"(?:^|\s)(?:ERROR|FATAL|PANIC):", trace):
        raise RuntimeError(trace[-5000:])
    lines = trace.splitlines()
    old = [line.split("CP7_TZ_REPLAY_OLD_REFUSAL:", 1)[1].strip() for line in lines
           if "NOTICE:" in line and "CP7_TZ_REPLAY_OLD_REFUSAL:" in line]
    fixed = [line.split("CP7_TZ_REPLAY_FIXED:", 1)[1].strip() for line in lines
             if "NOTICE:" in line and "CP7_TZ_REPLAY_FIXED:" in line]
    assert old == ["REWORK_SKU", "REDYE_SKU"], old
    assert set(fixed) == {mode + ":" + zone for mode in old
                          for zone in ("UTC", "Asia/Jakarta", "America/Los_Angeles")}
    assert len(fixed) == 6 and 'receipt = "CP7_TZ_REPLAY_CLEAN"' in trace, trace[-1500:]
    version = subprocess.check_output([str(bin_path / "postgres"), "--version"], text=True).strip()
    assert version == "postgres (PostgreSQL) 17.6", version
    result = {
        "status": "TARGETED_TIMEZONE_REPLAY_PASS",
        "qualification_head_of_original": HEAD,
        "original_run": 43132617378,
        "original_job": 130900171009,
        "original_attempt": 1,
        "original_artifact": 13914600256,
        "original_archive_bytes": ARCHIVE_SIZE,
        "original_archive_sha256": ARCHIVE_SHA256,
        "actual_catalogue_sha256": CATALOGUE_SHA256,
        "diagnostic_head": os.environ["GITHUB_SHA"],
        "diagnostic_run": os.environ["GITHUB_RUN_ID"],
        "diagnostic_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "postgres_version": version,
        "old_reproductions": old,
        "fixed_modes_and_zones": fixed,
        "controls": ["scope", "changed rework and target", "manual refusal",
                     "missing numeric value", "non-PO pending cost", "reverse", "caller timezone"],
        "boundaries": "Exact captured function bodies and table row types with scoped local fixtures and modeled valuation readers.",
        "new_erp_cases": 0,
        "restored": True,
        **facts,
    }
    (out / "POSTGRES_TIMEZONE_REPLAY.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
