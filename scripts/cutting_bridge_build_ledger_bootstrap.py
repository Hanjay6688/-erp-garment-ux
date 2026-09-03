#!/usr/bin/env python3
"""Build the deterministic pre-CP3 schema-only bootstrap from UAT ledger rows.

Input is one JSON object per line on stdin with version, name, and source_b64.
The script never connects to a database and never accepts business-table data.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path


FIRST_VERSION = "20260826112217"
LAST_VERSION = "20260831032949"
EXPECTED_COUNT = 48
EXPECTED_LEDGER_MANIFEST_SHA256 = (
    "103b938b48303d75bb056db1e30265a34ccecd9c52db070f842db4d5977197b8"
)
PRE_BOOTSTRAP_MARKERS = (
    ("20260826104553", "compact_export_marker"),
    ("20260826105139", "enable_pg_net_for_compact_export"),
    ("20260826105442", "invoke_compact_export_proxy"),
    ("20260826105822", "invoke_compact_installer_dryrun_validator"),
    ("20260826105958", "create_compact_validation_snapshot_helper"),
    ("20260826110134", "enable_http_for_compact_validation"),
    ("20260826111946", "overwrite_erp_enteng_reset"),
)
FIXTURE_PATH = Path(
    "supabase/tests/fixtures/erp_enteng_pre_cp3_schema_ledger.sql.gz"
)
MANIFEST_PATH = Path(
    "supabase/tests/fixtures/erp_enteng_pre_cp3_schema_ledger.manifest.json"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def main() -> None:
    pending: dict[str, dict[str, object]] = {}
    for line in sys.stdin:
        if not line.strip():
            continue
        part = json.loads(line)
        version = str(part["version"])
        entry = pending.setdefault(
            version,
            {
                "version": version,
                "name": str(part["name"]),
                "total": int(part["total"]),
                "chunks": {},
            },
        )
        if entry["name"] != part["name"] or entry["total"] != part["total"]:
            raise SystemExit(f"inconsistent chunk metadata for {version}")
        entry["chunks"][int(part["index"])] = str(part["data"])
        complete = sum(
            len(item["chunks"]) == item["total"] for item in pending.values()
        )
        if complete == EXPECTED_COUNT:
            break
    rows = [
        {
            "version": item["version"],
            "name": item["name"],
            "source_b64": "".join(
                item["chunks"][index] for index in range(item["total"])
            ),
        }
        for item in pending.values()
        if len(item["chunks"]) == item["total"]
    ]
    rows.sort(key=lambda row: row["version"])

    versions = [row["version"] for row in rows]
    if len(rows) != EXPECTED_COUNT:
        raise SystemExit(f"expected {EXPECTED_COUNT} ledger rows, got {len(rows)}")
    if versions[0] != FIRST_VERSION or versions[-1] != LAST_VERSION:
        raise SystemExit("ledger bootstrap boundary does not match the frozen range")
    if len(set(versions)) != len(versions):
        raise SystemExit("duplicate migration version in ledger bootstrap input")

    entries: list[dict[str, object]] = []
    chunks = [
        "-- ERP Enteng schema-only bootstrap for disposable full-schema CI.\n",
        "-- Generated from immutable supabase_migrations source rows; no business data.\n",
        "\\set ON_ERROR_STOP on\n\n",
        "create schema if not exists supabase_migrations;\n",
        "create table if not exists supabase_migrations.schema_migrations(version text primary key);\n",
        "alter table supabase_migrations.schema_migrations add column if not exists statements text[];\n",
        "alter table supabase_migrations.schema_migrations add column if not exists name text;\n\n",
    ]
    for version, name in PRE_BOOTSTRAP_MARKERS:
        chunks.extend(
            [
                "insert into supabase_migrations.schema_migrations(version,name,statements)\n",
                f"values({sql_literal(version)},{sql_literal(name)},array[]::text[])\n",
                "on conflict(version) do update set name=excluded.name, statements=excluded.statements;\n",
            ]
        )
    chunks.append("\n")

    for row in rows:
        version = str(row["version"])
        name = str(row["name"])
        if not re.fullmatch(r"[0-9]{14}", version):
            raise SystemExit(f"invalid migration version: {version}")
        if not re.fullmatch(r"[a-z0-9_]+", name):
            raise SystemExit(f"invalid migration name for {version}: {name}")

        encoded_source = re.sub(r"\s+", "", row["source_b64"])
        source = base64.b64decode(encoded_source, validate=True)
        source.decode("utf-8")
        source_hash = sha256(source)
        entries.append(
            {
                "version": version,
                "name": name,
                "bytes": len(source),
                "sha256": source_hash,
            }
        )
        chunks.extend(
            [
                f"-- BEGIN PLATFORM MIGRATION {version} {name}\n",
                source.decode("utf-8").rstrip(),
                "\n",
                "insert into supabase_migrations.schema_migrations(version,name,statements)\n",
                f"values({sql_literal(version)},{sql_literal(name)},array[]::text[])\n",
                "on conflict(version) do update set name=excluded.name, statements=excluded.statements;\n",
                f"-- END PLATFORM MIGRATION {version} {name}\n\n",
            ]
        )

    ledger_lines = "\n".join(
        f"{entry['version']}\t{entry['name']}\t{entry['sha256']}" for entry in entries
    ).encode()
    if sha256(ledger_lines) != EXPECTED_LEDGER_MANIFEST_SHA256:
        raise SystemExit("ledger source identity differs from the read-only UAT manifest")

    sql = "".join(chunks).encode()
    compressed = gzip.compress(sql, compresslevel=9, mtime=0)
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_bytes(compressed)

    manifest = {
        "format": "ERP_ENTENG_PRE_CP3_SCHEMA_LEDGER_BOOTSTRAP_V1",
        "source_project_ref": "siimvrusnzxexizpyoib",
        "source_kind": "SUPABASE_PLATFORM_LEDGER_SCHEMA_SOURCE_ONLY",
        "contains_business_rows": False,
        "contains_credentials": False,
        "first_version": FIRST_VERSION,
        "last_version": LAST_VERSION,
        "executable_migration_count": len(entries),
        "platform_marker_count": len(PRE_BOOTSTRAP_MARKERS),
        "expected_platform_count": len(entries) + len(PRE_BOOTSTRAP_MARKERS),
        "ledger_manifest_sha256": sha256(ledger_lines),
        "sql_bytes": len(sql),
        "sql_sha256": sha256(sql),
        "gzip_bytes": len(compressed),
        "gzip_sha256": sha256(compressed),
        "platform_markers": [
            {"version": version, "name": name} for version, name in PRE_BOOTSTRAP_MARKERS
        ],
        "migrations": entries,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({key: manifest[key] for key in (
        "executable_migration_count", "expected_platform_count", "sql_bytes",
        "sql_sha256", "gzip_bytes", "gzip_sha256"
    )}))


if __name__ == "__main__":
    main()
