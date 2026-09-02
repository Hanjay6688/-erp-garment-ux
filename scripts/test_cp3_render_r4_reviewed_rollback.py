#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts/cp3_render_r4_reviewed_rollback.py"
MIGRATION_REL = "supabase/migrations/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql"
ROLLBACK_REL = "supabase/rollbacks/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.rollback.sql"
MIGRATION = ROOT / MIGRATION_REL
ROLLBACK = ROOT / ROLLBACK_REL


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def manifest_for(migration: bytes, rollback: bytes) -> dict:
    return {
        "schema_fingerprint": "a0c59b96b3879edd28f3d8c57d0894a3",
        "migration_version": "v2.6.14d",
        "files": {
            MIGRATION_REL: {"sha256": digest(migration), "bytes": len(migration)},
            ROLLBACK_REL: {"sha256": digest(rollback), "bytes": len(rollback)},
        },
    }


def run_case(name: str, migration: bytes, rollback: bytes, manifest: dict, should_pass: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="cp3-r4-render-") as td:
        base = Path(td)
        migration_path = base / "migration.sql"
        rollback_path = base / "rollback.sql"
        manifest_path = base / "manifest.json"
        output_path = base / "out.sql"
        migration_path.write_bytes(migration)
        rollback_path.write_bytes(rollback)
        manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(RENDERER), "--manifest", str(manifest_path),
             "--migration", str(migration_path), "--rollback", str(rollback_path),
             "--output", str(output_path)],
            cwd=ROOT, text=True, capture_output=True,
        )
        passed = result.returncode == 0
        if passed != should_pass:
            raise AssertionError(
                f"{name}: expected pass={should_pass}, rc={result.returncode}, "
                f"stdout={result.stdout!r}, stderr={result.stderr!r}"
            )
        if should_pass and output_path.read_bytes() != rollback:
            raise AssertionError(f"{name}: rendered bytes differ")


def main() -> None:
    migration = MIGRATION.read_bytes()
    rollback = ROLLBACK.read_bytes()
    cases = 0

    valid = manifest_for(migration, rollback)
    run_case("valid", migration, rollback, valid, True); cases += 1
    run_case("migration-byte-drift", migration + b"\n-- drift", rollback, valid, False); cases += 1
    run_case("rollback-byte-drift", migration, rollback + b"\n-- drift", valid, False); cases += 1

    wrong_fingerprint = json.loads(json.dumps(valid)); wrong_fingerprint["schema_fingerprint"] = "bad"
    run_case("wrong-fingerprint", migration, rollback, wrong_fingerprint, False); cases += 1
    wrong_version = json.loads(json.dumps(valid)); wrong_version["migration_version"] = "v2.6.14x"
    run_case("wrong-version", migration, rollback, wrong_version, False); cases += 1
    missing_hash = json.loads(json.dumps(valid)); del missing_hash["files"][ROLLBACK_REL]["sha256"]
    run_case("missing-hash", migration, rollback, missing_hash, False); cases += 1

    empty = b""
    run_case("empty-rollback", migration, empty, manifest_for(migration, empty), False); cases += 1
    truncated = rollback[: max(1, len(rollback)//2)]
    run_case("truncated-rollback", migration, truncated, manifest_for(migration, truncated), False); cases += 1
    duplicate_commit = rollback + b"\ncommit;\n"
    run_case("duplicate-commit", migration, duplicate_commit, manifest_for(migration, duplicate_commit), False); cases += 1
    no_capsule_cleanup = rollback.replace(b"drop table erp.cp3_r4_rollback_capsule;", b"-- removed")
    run_case("missing-capsule-cleanup", migration, no_capsule_cleanup, manifest_for(migration, no_capsule_cleanup), False); cases += 1
    no_ledger_cleanup = rollback.replace(b"delete from erp.schema_migrations where version='v2.6.14d';", b"-- removed")
    run_case("missing-ledger-cleanup", migration, no_ledger_cleanup, manifest_for(migration, no_ledger_cleanup), False); cases += 1

    print(json.dumps({"status": "PASS", "cases": cases}, sort_keys=True))


if __name__ == "__main__":
    main()
