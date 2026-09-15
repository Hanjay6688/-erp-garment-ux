#!/usr/bin/env python3
"""Exact AE source, inherited AD edge, capsule, and live runtime checks."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import cp6_v2620ac_runtime as ac
import cp6_v2620ad_runtime as ad


STAMP = "20260915201500"
NAME = "erp_v2_6_20ae_cp6_opening_roll_integrity"
VERSION = "v2.6.20ae"
MIGRATION = Path(
    "supabase/migrations/20260915201500_erp_v2_6_20ae_cp6_opening_roll_integrity.sql"
)
ROLLBACK = Path(
    "supabase/rollbacks/20260915201500_erp_v2_6_20ae_cp6_opening_roll_integrity.rollback.sql"
)
PINS = Path("docs/evidence/cp6-ae-runtime-pins.json")
CAPSULE = "erp.cp6_v2620ae_rollback_capsule"
PREDECESSOR_HEAD = "b2663a0cb490432b53ca92670a17f7a268a8e7a3"
PREDECESSOR_TREE = "12cff34f745f19930b50296d003f6e5da3127d3e"
PINS_SHA256 = "6891b006b3611debc87a0bc4928438c6db5dc1df8209d9c7d927f151494026d4"

ALLOWED_CANDIDATE_FILES = {
    ".github/workflows/cp6-ad-roll-opening-check.yml",
    ".github/workflows/cp6-full-schema-validation.yml",
    "docs/evidence/cp6-ae-runtime-pins.json",
    "scripts/cp6_preuse_rollback_maintenance.py",
    "scripts/cp6_v2620ae_build_sql.py",
    "scripts/cp6_v2620ae_family.py",
    "scripts/cp6_v2620ae_rollback_guards.py",
    "scripts/cp6_v2620ae_runtime.py",
    str(MIGRATION),
    str(ROLLBACK),
}


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def pins() -> dict[str, Any]:
    raw = PINS.read_bytes()
    if _sha(raw) != PINS_SHA256:
        raise AssertionError("AE_TRUSTED_PINS_CHANGED")
    payload = json.loads(raw)
    if (
        payload.get("format") != "CP6_AE_RUNTIME_PINS_V1"
        or payload.get("stamp") != STAMP
        or payload.get("name") != NAME
        or payload.get("version") != VERSION
        or payload.get("predecessor_head") != PREDECESSOR_HEAD
        or payload.get("predecessor_tree") != PREDECESSOR_TREE
        or payload.get("boundary_count") != 217
        or payload.get("predecessor_function_count") != 533
        or payload.get("predecessor_table_count") != 219
        or payload.get("production_go") is not False
    ):
        raise AssertionError("AE_TRUSTED_PINS_SHAPE_MISMATCH")
    return payload


def verify_source_files() -> dict[str, Any]:
    payload = pins()
    ad.verify_source_files()
    for path, expected in payload["source_pins"].items():
        raw = Path(path).read_bytes()
        if len(raw) != expected["bytes"] or _sha(raw) != expected["sha256"]:
            raise AssertionError("AE_SOURCE_BYTES_MISMATCH:" + path)
    functions = payload.get("functions", [])
    ad_identities = {item["identity"] for item in ad.pins()["functions"]}
    if len(functions) != 2 or {item["identity"] for item in functions} != ad_identities:
        raise AssertionError("AE_REQUIRES_EXACTLY_THE_TWO_AD_FUNCTIONS")
    for item in functions:
        if item["predecessor_sha256"] != next(
            prior["installed_sha256"]
            for prior in ad.pins()["functions"]
            if prior["identity"] == item["identity"]
        ):
            raise AssertionError("AE_PREDECESSOR_PIN_IS_NOT_AD:" + item["identity"])
    return payload


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def verify_audit_source() -> tuple[str, str]:
    verify_source_files()
    head = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    if _git("rev-parse", PREDECESSOR_HEAD + "^{tree}") != PREDECESSOR_TREE:
        raise AssertionError("AE_FROZEN_PREDECESSOR_TREE_MISMATCH")
    if _git("merge-base", PREDECESSOR_HEAD, head) != PREDECESSOR_HEAD:
        raise AssertionError("AE_REQUIRES_FROZEN_PREDECESSOR_ANCESTRY")
    if _git("rev-list", "--merges", PREDECESSOR_HEAD + ".." + head):
        raise AssertionError("AE_LINEAR_SUCCESSOR_REQUIRED")
    changed = set(_git("diff", "--name-only", PREDECESSOR_HEAD, head).splitlines())
    if changed != ALLOWED_CANDIDATE_FILES:
        raise AssertionError("AE_CANDIDATE_FILE_BOUNDARY_MISMATCH:" + repr(sorted(changed)))
    sql_changed = set(
        _git(
            "diff", "--name-only", PREDECESSOR_HEAD, head, "--",
            "supabase/migrations", "supabase/rollbacks",
        ).splitlines()
    )
    if sql_changed != {str(MIGRATION), str(ROLLBACK)}:
        raise AssertionError("AE_ONLY_NEW_AE_SQL_EDGE_ALLOWED")
    if _git(
        "diff", "--name-only", "--diff-filter=MDRTCUXB", PREDECESSOR_HEAD,
        head, "--", "supabase/migrations", "supabase/rollbacks",
    ):
        raise AssertionError("AE_ADMITTED_SQL_CHANGED")
    if os.environ.get("GITHUB_SHA") != head:
        raise AssertionError("AE_EXACT_NATIVE_HEAD_REQUIRED")
    return head, tree


def verify_ad_pre_admission(cur) -> dict[str, Any]:
    """Verify the full live AD runtime immediately before AE is applied."""
    verify_source_files()
    inherited = ad.verified_successor(cur)
    if len(inherited) != 274:
        raise AssertionError("AE_REQUIRES_EXACT_LIVE_AD")
    if cur.execute(
        """select to_regclass(%s) is not null
             or exists(select 1 from erp.schema_migrations where version=%s)
             or exists(select 1 from supabase_migrations.schema_migrations where name=%s)""",
        (CAPSULE, VERSION, NAME),
    ).fetchone()[0]:
        raise AssertionError("AE_PREDECESSOR_HAS_AE_RESIDUE")
    return inherited


def verify_inherited_ad(cur) -> dict[str, Any]:
    """Verify AD's stored edge while AE owns the two current definitions."""
    payload = verify_source_files()
    row = cur.execute(
        """select exists(select 1 from erp.schema_migrations where version=%s),
                  to_regclass(%s) is not null,
                  (select count(*) from supabase_migrations.schema_migrations where name=%s)""",
        (ad.VERSION, ad.CAPSULE, ad.NAME),
    ).fetchone()
    if row != (True, True, 1):
        raise AssertionError("AE_INHERITED_AD_MARKER_CAPSULE_PLATFORM_MISMATCH")
    platform = cur.execute(
        """select version,encode(extensions.digest(convert_to(
             array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
           from supabase_migrations.schema_migrations where name=%s""",
        (ad.NAME,),
    ).fetchone()
    ad_payload = ad.pins()
    if platform != (
        ad.STAMP,
        ad_payload["source_pins"][str(ad.MIGRATION)]["sha256"],
    ):
        raise AssertionError("AE_INHERITED_AD_PLATFORM_SOURCE_MISMATCH")
    ac._capsule_security(cur, ad.CAPSULE)
    inherited = ac.verified_successor(cur)
    if len(inherited) != 272:
        raise AssertionError("AE_INHERITED_AC_RUNTIME_MISMATCH")

    rows = cur.execute(
        f"""select object_regidentity,definition_sha256,
          encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex'),
          installed_definition_sha256,owner_snapshot,acl_snapshot,boundary_snapshot
          from {ad.CAPSULE} order by object_regidentity"""
    ).fetchall()
    expected = {item["identity"]: item for item in ad_payload["functions"]}
    if len(rows) != 2 or {row[0] for row in rows} != set(expected):
        raise AssertionError("AE_INHERITED_AD_CAPSULE_CARDINALITY")
    snapshots = []
    result = dict(inherited)
    for identity, stored_predecessor, actual_predecessor, stored_installed, owner, acl, boundary in rows:
        item = expected[identity]
        if (
            stored_predecessor != item["predecessor_sha256"]
            or actual_predecessor != item["predecessor_sha256"]
            or stored_installed != item["installed_sha256"]
            or owner != item["owner"]
            or acl != item["acl"]
        ):
            raise AssertionError("AE_INHERITED_AD_CAPSULE_PIN_MISMATCH:" + identity)
        snapshots.append(boundary)
        result["AD_EDGE:" + identity] = {
            **item,
            "kind": "FUNCTION_EDGE",
            "edge": "AD",
        }
    if (
        len(snapshots) != 2
        or snapshots[0] is None
        or len(snapshots[0]) != 216
        or snapshots[0] != snapshots[1]
    ):
        raise AssertionError("AE_INHERITED_AD_BOUNDARY_MISMATCH")
    if payload["predecessor_function_count"] != 533:
        raise AssertionError("AE_PREDECESSOR_FUNCTION_COUNT_PIN_MISMATCH")
    return result


def _own_capsule(cur, payload: dict[str, Any]) -> list[dict[str, Any]]:
    ac._capsule_security(cur, CAPSULE)
    rows = cur.execute(
        f"""select cap.object_regidentity,cap.definition_sha256,
          encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex'),
          cap.installed_definition_sha256,cap.owner_snapshot,cap.acl_snapshot,
          encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
          pg_get_userbyid(p.proowner),
          case when p.proacl is null then null else
            array(select a::text from unnest(p.proacl) a order by a::text) end,
          cap.boundary_snapshot
        from {CAPSULE} cap
        left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
        order by cap.object_regidentity"""
    ).fetchall()
    expected = {item["identity"]: item for item in payload["functions"]}
    if len(rows) != 2 or {row[0] for row in rows} != set(expected):
        raise AssertionError("AE_CAPSULE_CARDINALITY_MISMATCH")
    snapshots = []
    observed = []
    for row in rows:
        (
            identity, stored_predecessor, actual_predecessor, stored_installed,
            stored_owner, stored_acl, live_sha, live_owner, live_acl, boundary,
        ) = row
        item = expected[identity]
        if (
            stored_predecessor != item["predecessor_sha256"]
            or actual_predecessor != item["predecessor_sha256"]
            or stored_installed != item["installed_sha256"]
            or live_sha != item["installed_sha256"]
            or stored_owner != item["owner"]
            or live_owner != item["owner"]
            or stored_acl != item["acl"]
            or live_acl != item["acl"]
        ):
            raise AssertionError("AE_CAPSULE_OR_LIVE_PIN_MISMATCH:" + identity)
        snapshots.append(boundary)
        observed.append({**item, "kind": "FUNCTION", "edge": "AE"})
    if (
        len(snapshots) != 2
        or snapshots[0] is None
        or len(snapshots[0]) != payload["boundary_count"]
        or snapshots[0] != snapshots[1]
    ):
        raise AssertionError("AE_BOUNDARY_CAPSULE_MISMATCH")
    return observed


def verify_predecessor(cur) -> dict[str, Any]:
    return verify_ad_pre_admission(cur)


def verified_successor(cur) -> dict[str, Any]:
    payload = verify_source_files()
    row = cur.execute(
        """select exists(select 1 from erp.schema_migrations where version=%s),
                  to_regclass(%s) is not null,
                  (select count(*) from supabase_migrations.schema_migrations where name=%s)""",
        (VERSION, CAPSULE, NAME),
    ).fetchone()
    if row != (True, True, 1):
        raise AssertionError("AE_MARKER_CAPSULE_PLATFORM_MISMATCH")
    platform = cur.execute(
        """select version,encode(extensions.digest(convert_to(
             array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
           from supabase_migrations.schema_migrations where name=%s""",
        (NAME,),
    ).fetchone()
    if platform != (STAMP, payload["source_pins"][str(MIGRATION)]["sha256"]):
        raise AssertionError("AE_PLATFORM_SOURCE_MISMATCH")
    inherited = verify_inherited_ad(cur)
    own = _own_capsule(cur, payload)
    result = dict(inherited)
    for item in own:
        result[item["identity"]] = item
    if len(result) != 276:
        raise AssertionError("AE_RUNTIME_CARDINALITY_MISMATCH")
    return result
