#!/usr/bin/env python3
"""Render the exact reviewed CP3 R4 rollback only when source hashes match."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DEFAULT_MANIFEST = Path("docs/evidence/cp3_r4_source_hashes.json")
DEFAULT_MIGRATION = Path("supabase/migrations/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql")
DEFAULT_ROLLBACK = Path("supabase/rollbacks/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.rollback.sql")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_bytes(path: Path, label: str) -> bytes:
    try:
        value = path.read_bytes()
    except OSError as exc:
        raise SystemExit(f"CP3_R4_RENDER_FAIL: cannot read {label}: {path}: {exc}") from exc
    if not value:
        raise SystemExit(f"CP3_R4_RENDER_FAIL: {label} is empty: {path}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--migration", type=Path, default=DEFAULT_MIGRATION)
    parser.add_argument("--rollback", type=Path, default=DEFAULT_ROLLBACK)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"CP3_R4_RENDER_FAIL: invalid source-hash manifest: {exc}") from exc

    if manifest.get("schema_fingerprint") != "a0c59b96b3879edd28f3d8c57d0894a3":
        raise SystemExit("CP3_R4_RENDER_FAIL: unexpected ERP Enteng schema fingerprint")
    if manifest.get("migration_version") != "v2.6.14d":
        raise SystemExit("CP3_R4_RENDER_FAIL: unexpected migration version")

    migration = load_bytes(args.migration, "migration")
    rollback = load_bytes(args.rollback, "rollback")
    expected_migration = manifest.get("files", {}).get(str(DEFAULT_MIGRATION), {}).get("sha256")
    expected_rollback = manifest.get("files", {}).get(str(DEFAULT_ROLLBACK), {}).get("sha256")
    if not isinstance(expected_migration, str) or not isinstance(expected_rollback, str):
        raise SystemExit("CP3_R4_RENDER_FAIL: required fixed source hashes are missing")
    if sha256_bytes(migration) != expected_migration:
        raise SystemExit("CP3_R4_RENDER_FAIL: migration bytes differ from frozen digest")
    if sha256_bytes(rollback) != expected_rollback:
        raise SystemExit("CP3_R4_RENDER_FAIL: rollback bytes differ from frozen digest")

    text = rollback.decode("utf-8")
    stripped = text.rstrip()
    if not stripped.endswith("commit;"):
        raise SystemExit("CP3_R4_RENDER_FAIL: rollback does not terminate in COMMIT")
    if stripped.count("commit;") != 1:
        raise SystemExit("CP3_R4_RENDER_FAIL: rollback has an ambiguous COMMIT boundary")
    if "drop table erp.cp3_r4_rollback_capsule;" not in text:
        raise SystemExit("CP3_R4_RENDER_FAIL: rollback capsule cleanup is absent")
    if "delete from erp.schema_migrations where version='v2.6.14d';" not in text:
        raise SystemExit("CP3_R4_RENDER_FAIL: migration-ledger cleanup is absent")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(rollback)
    print(json.dumps({
        "status": "PASS",
        "migration_sha256": expected_migration,
        "rollback_sha256": expected_rollback,
        "rollback_bytes": len(rollback),
        "output": str(args.output),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
