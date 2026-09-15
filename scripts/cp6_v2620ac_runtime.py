#!/usr/bin/env python3
"""Pinned AC runtime/source verifier for the CP6 successor writer."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


STAMP = "20260915031500"
VERSION = "v2.6.20ac"
NAME = "erp_v2_6_20ac_cp6_temporal_surface_closure"
MIGRATION = Path(
    "supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql"
)
ROLLBACK = Path(
    "supabase/rollbacks/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.rollback.sql"
)
PINS = Path("docs/evidence/cp6-ac-runtime-pins.json")
DISPOSITION = Path("docs/evidence/cp6-ac-temporal-disposition.json")

# Updated only when the deterministic AC generator output changes.
MIGRATION_SHA256 = "d0742ed0c465503907ae9a9136779138996403be14e96592cdbf63c81001b21f"
ROLLBACK_SHA256 = "b709de6e0849dd86720ea4620bb680aee19381622326bb3d1e5bc899148ef4a7"
PINS_SHA256 = "c18cfeae29d10cd850818a17b75e91c30e22369329e051c54e90500b2fb4358e"
DISPOSITION_SHA256 = "28c39de13bfb8707cd518207d369eab57f4b90d51308517e83f581236db22576"

AB_HEAD = "e2aa399cfc787d848c1f136e8e563c5304d09a87"
AB_TREE = "5bddd7add3296f27087ed30062c998bf20e53ac1"
AB_MIGRATION_SHA256 = "7b31f000b3ca89f4bc776d93f3211f39dce5adbc73445291b9c0e0268f2d7fe3"
AB_ROLLBACK_SHA256 = "5602fefc1b29935ccfb485635ec14e6fdea7468bd726ed440d6c5d93d12b1262"
AB_MIGRATION = Path(
    "supabase/migrations/20260914190500_erp_v2_6_20ab_cp6_operational_business_clock.sql"
)
AB_ROLLBACK = Path(
    "supabase/rollbacks/20260914190500_erp_v2_6_20ab_cp6_operational_business_clock.rollback.sql"
)

# The original writer tree is immutable. Bounded repair commits may follow it
# without weakening the exact AB ancestry or the two-file AC SQL edge.
AC_WRITER_HEAD = "41e210a4b756d26bc5fce20d59904af0fe2552fb"
AC_WRITER_TREE = "7bde10c90d29f3f3fd7787cf7064d86d828fb82b"
AC_SOURCE_ADMISSION_REPAIR_FILES = {
    "scripts/cp6_v2620ab_runtime.py",
    "scripts/cp6_v2620ac_runtime.py",
    "scripts/cp6_v2620ac_static_qualification.py",
    "scripts/cp6_v2620ac_proof.py",
    "scripts/cp6_x_independent_audit.py",
    "scripts/cp6_y_independent_audit.py",
    "scripts/cp6_z_expanded_integrity_audit.py",
}
AC_SUCCESSOR_REPAIR_FILES = AC_SOURCE_ADMISSION_REPAIR_FILES | {
    ".github/workflows/cp6-full-schema-validation.yml",
    "scripts/check-cp6-expanded-audit-closure.mjs",
    "scripts/cp6_v2620ac_build_sql.py",
    "scripts/cp6_v2620ac_install_qualification.py",
    "scripts/cp6_preuse_rollback_maintenance.py",
    "supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql",
    "supabase/rollbacks/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.rollback.sql",
}

MAIN_CAPSULE = "erp.cp6_v2620ac_rollback_capsule"
RELATION_CAPSULE = "erp.cp6_v2620ac_relation_rollback_capsule"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def pins() -> dict[str, Any]:
    return json.loads(PINS.read_text(encoding="utf-8"))


def verify_source_files() -> dict[str, str]:
    expected = {
        MIGRATION: MIGRATION_SHA256,
        ROLLBACK: ROLLBACK_SHA256,
        PINS: PINS_SHA256,
        DISPOSITION: DISPOSITION_SHA256,
        AB_MIGRATION: AB_MIGRATION_SHA256,
        AB_ROLLBACK: AB_ROLLBACK_SHA256,
    }
    observed = {str(path): sha256_file(path) for path in expected}
    for path, wanted in expected.items():
        if observed[str(path)] != wanted:
            raise AssertionError(f"AC_FROZEN_SOURCE_BYTES_MISMATCH:{path}")
    payload = pins()
    if payload["summary"] != {
        "functions": 115,
        "main_capsule_rows": 115,
        "relation_capsule_rows": 157,
        "table_defaults": 144,
        "views": 13,
    }:
        raise AssertionError("AC_RUNTIME_PIN_CARDINALITY_MISMATCH")
    disposition = json.loads(DISPOSITION.read_text(encoding="utf-8"))
    summary = disposition["summary"]
    if (
        summary["reviewed_occurrences"] != 709
        or summary["change_occurrences"] != 422
        or summary["retained_occurrences"] != 285
        or summary["explicit_exclusions"] != 2
        or summary["unresolved_occurrences"] != 0
    ):
        raise AssertionError("AC_TEMPORAL_DISPOSITION_MISMATCH")
    return observed


def _acl(value: Any) -> list[str] | None:
    return None if value is None else sorted(value)


def _applied_view_bodies() -> dict[str, str]:
    source = MIGRATION.read_text(encoding="utf-8")
    start_marker = (
        "-- Generated only from the 709/709 reviewed disposition; do not hand-edit.\n"
    )
    end_marker = "\ndo $installed_v2620ac$\n"
    if source.count(start_marker) != 1 or source.count(end_marker) != 1:
        raise AssertionError("AC_RUNTIME_VIEW_SOURCE_MARKERS")
    segment = source.split(start_marker, 1)[1].split(end_marker, 1)[0]
    first_view = segment.find("CREATE OR REPLACE VIEW erp.")
    first_default = segment.find("\nalter table erp.", first_view)
    if first_view < 0 or first_default < 0:
        raise AssertionError("AC_RUNTIME_VIEW_SOURCE_SEGMENT")
    view_source = segment[first_view:first_default]
    statements = re.findall(
        r"(?ms)^CREATE OR REPLACE VIEW erp\..*?;\n(?=\n|$)", view_source
    )
    bodies: dict[str, str] = {}
    for statement in statements:
        match = re.match(
            r"^CREATE OR REPLACE VIEW (?P<identity>erp\.[A-Za-z_][A-Za-z0-9_]*)"
            r"(?: WITH \([^\n]+\))? AS\n(?P<body>.*);\n$",
            statement,
            re.S,
        )
        if match is None or match.group("identity") in bodies:
            raise AssertionError("AC_RUNTIME_VIEW_SOURCE_PARSE")
        bodies[match.group("identity")] = match.group("body").strip()
    if len(bodies) != 13:
        raise AssertionError("AC_RUNTIME_VIEW_SOURCE_CARDINALITY")
    return bodies


def _normalized_view_sha(cur, body: str) -> str:
    cur.execute(
        "create temporary view cp6_ac_runtime_normalization_probe as\n" + body,
        prepare=False,
    )
    cur.execute(
        """select encode(extensions.digest(convert_to(btrim(pg_get_viewdef(
          'pg_temp.cp6_ac_runtime_normalization_probe'::regclass,false),
          E' \\n\\t\\r;'),'UTF8'),'sha256'),'hex')"""
    )
    result = cur.fetchone()[0]
    cur.execute("drop view pg_temp.cp6_ac_runtime_normalization_probe")
    return result


def _capsule_security(cur, identity: str) -> None:
    cur.execute(
        """select c.relrowsecurity,pg_get_userbyid(c.relowner),
          has_table_privilege('anon',%s,'SELECT'),
          has_table_privilege('authenticated',%s,'SELECT'),
          has_table_privilege('service_role',%s,'SELECT'),
          exists(select 1 from aclexplode(coalesce(
            c.relacl,acldefault('r',c.relowner))) a
            where a.grantee=0 and a.privilege_type='SELECT')
        from pg_class c where c.oid=to_regclass(%s)""",
        (identity, identity, identity, identity),
    )
    row = cur.fetchone()
    if row != (True, "postgres", False, False, False, False):
        raise AssertionError(f"AC_CAPSULE_SECURITY_MISMATCH:{identity}:{row}")


def _verify_functions(cur, payload: dict[str, Any]) -> dict[str, Any]:
    expected = {item["identity"]: item for item in payload["functions"]}
    cur.execute(
        """select cap.object_identity,cap.object_regidentity,
          cap.definition_sha256,
          encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex'),
          cap.installed_definition_sha256,cap.owner_snapshot,cap.acl_snapshot,
          encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
          pg_get_userbyid(p.proowner),
          case when p.proacl is null then null else
            array(select x::text from unnest(p.proacl) x order by x::text) end,
          cap.boundary_snapshot
        from erp.cp6_v2620ac_rollback_capsule cap
        left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
        order by cap.object_regidentity"""
    )
    rows = cur.fetchall()
    if not expected or len(rows) != len(expected):
        raise AssertionError("AC_MAIN_CAPSULE_CARDINALITY_MISMATCH")
    observations: dict[str, Any] = {}
    snapshots = []
    for row in rows:
        (
            object_identity, identity, predecessor_sha, capsule_definition_sha,
            installed_pin, capsule_owner, capsule_acl, live_sha, live_owner,
            live_acl, boundary_snapshot,
        ) = row
        item = expected.get(identity)
        if item is None or not object_identity:
            raise AssertionError(f"AC_FUNCTION_IDENTITY_MISMATCH:{identity}")
        if (
            predecessor_sha != item["before_sha"]
            or capsule_definition_sha != item["before_sha"]
            or installed_pin != item["after_sha"]
            or live_sha != item["after_sha"]
            or capsule_owner != item["owner"]
            or live_owner != item["owner"]
            or _acl(capsule_acl) != _acl(item["acl"])
            or _acl(live_acl) != _acl(item["acl"])
        ):
            raise AssertionError(f"AC_FUNCTION_PIN_MISMATCH:{identity}")
        snapshots.append(boundary_snapshot)
        observations["FUNCTION:" + identity] = {
            "kind": "FUNCTION",
            "identity": identity,
            "predecessor_sha256": predecessor_sha,
            "installed_sha256": live_sha,
            "owner": live_owner,
            "acl": _acl(live_acl),
        }
    if not snapshots or snapshots[0] is None:
        raise AssertionError("AC_BOUNDARY_SNAPSHOT_MISSING")
    if any(snapshot != snapshots[0] for snapshot in snapshots[1:]):
        raise AssertionError("AC_BOUNDARY_SNAPSHOT_NOT_IDENTICAL")
    if len(snapshots[0]) != 214:
        raise AssertionError("AC_BOUNDARY_SNAPSHOT_CARDINALITY")
    return observations


def _verify_views(cur, payload: dict[str, Any]) -> dict[str, Any]:
    observations: dict[str, Any] = {}
    applied_bodies = _applied_view_bodies()
    for item in payload["views"]:
        cur.execute(
            """select cap.definition_sha256,
              encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex'),
              cap.installed_definition_sha256,cap.owner_snapshot,cap.acl_snapshot,
              cap.reloptions_snapshot,cap.rls_snapshot,
              encode(extensions.digest(convert_to(btrim(pg_get_viewdef(v.oid,false),E' \\n\\t\\r;'),'UTF8'),'sha256'),'hex'),
              pg_get_userbyid(v.relowner),
              case when v.relacl is null then null else
                array(select x::text from unnest(v.relacl) x order by x::text) end,
              case when v.reloptions is null then null else
                array(select x from unnest(v.reloptions) x order by x) end,
              v.relrowsecurity
            from erp.cp6_v2620ac_relation_rollback_capsule cap
            left join pg_class v on v.oid=to_regclass(cap.object_identity)
            where cap.object_kind='VIEW' and cap.object_identity=%s""",
            (item["identity"],),
        )
        row = cur.fetchone()
        if row is None:
            raise AssertionError(f"AC_VIEW_CAPSULE_MISSING:{item['identity']}")
        (
            predecessor_sha, restore_sha, installed_pin, capsule_owner,
            capsule_acl, capsule_options, capsule_rls, false_sha,
            live_owner, live_acl, live_options, live_rls,
        ) = row
        applied_body = applied_bodies.get(item["identity"])
        if (
            applied_body is None
            or sha256_bytes(applied_body.encode("utf-8"))
            != item["after_body_sha"]
        ):
            raise AssertionError(f"AC_VIEW_SOURCE_PIN_MISMATCH:{item['identity']}")
        expected_engine_sha = _normalized_view_sha(cur, applied_body)
        if (
            predecessor_sha != item["before_body_sha"]
            or restore_sha != item["restore_sha"]
            or installed_pin != false_sha
            or false_sha != expected_engine_sha
            or capsule_owner != item["owner"]
            or live_owner != item["owner"]
            or _acl(capsule_acl) != _acl(item["acl"])
            or _acl(live_acl) != _acl(item["acl"])
            or _acl(capsule_options) != _acl(item["reloptions"])
            or _acl(live_options) != _acl(item["reloptions"])
            or capsule_rls != item["rls"]
            or live_rls != item["rls"]
        ):
            raise AssertionError(f"AC_VIEW_PIN_MISMATCH:{item['identity']}")
        observations["VIEW:" + item["identity"]] = {
            "kind": "VIEW", "identity": item["identity"],
            "predecessor_sha256": predecessor_sha,
            "installed_sha256": false_sha,
            "source_sha256": item["after_body_sha"],
            "owner": live_owner, "acl": _acl(live_acl),
            "reloptions": _acl(live_options),
        }
    return observations


def _verify_defaults(cur, payload: dict[str, Any]) -> dict[str, Any]:
    observations: dict[str, Any] = {}
    for item in payload["table_defaults"]:
        cur.execute(
            """select cap.definition_sha256,
              encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex'),
              cap.installed_definition_sha256,cap.owner_snapshot,cap.acl_snapshot,
              cap.rls_snapshot,
              pg_get_expr(d.adbin,d.adrelid),pg_get_userbyid(t.relowner),
              case when t.relacl is null then null else
                array(select x::text from unnest(t.relacl) x order by x::text) end,
              t.relrowsecurity
            from erp.cp6_v2620ac_relation_rollback_capsule cap
            left join pg_class t on t.oid=to_regclass(%s)
            left join pg_attribute a on a.attrelid=t.oid and a.attname=%s
            left join pg_attrdef d on d.adrelid=t.oid and d.adnum=a.attnum
            where cap.object_kind='COLUMN_DEFAULT' and cap.object_identity=%s""",
            ("erp." + item["table"], item["column"], item["identity"]),
        )
        row = cur.fetchone()
        if row is None:
            raise AssertionError(f"AC_DEFAULT_CAPSULE_MISSING:{item['identity']}")
        (
            predecessor_sha, restore_sha, installed_pin, capsule_owner,
            capsule_acl, capsule_rls, expression, live_owner, live_acl, live_rls,
        ) = row
        before_sha = sha256_bytes(item["before"].encode())
        after_sha = sha256_bytes(item["after"].encode())
        if (
            predecessor_sha != before_sha
            or restore_sha != item["restore_sha"]
            or installed_pin != after_sha
            or expression != item["after"]
            or capsule_owner != item["owner"]
            or live_owner != item["owner"]
            or _acl(capsule_acl) != _acl(item["acl"])
            or _acl(live_acl) != _acl(item["acl"])
            or capsule_rls != item["rls"]
            or live_rls != item["rls"]
        ):
            raise AssertionError(f"AC_DEFAULT_PIN_MISMATCH:{item['identity']}")
        observations["COLUMN_DEFAULT:" + item["identity"]] = {
            "kind": "COLUMN_DEFAULT", "identity": item["identity"],
            "predecessor_sha256": predecessor_sha,
            "installed_sha256": after_sha,
            "owner": live_owner, "acl": _acl(live_acl),
        }
    return observations


def verified_successor(cur) -> dict[str, Any]:
    """Verify exact AC source, markers, capsules, definitions, ACLs and owners."""
    verify_source_files()
    cur.execute(
        """select exists(select 1 from erp.schema_migrations where version=%s),
          to_regclass(%s) is not null,to_regclass(%s) is not null,
          exists(select 1 from supabase_migrations.schema_migrations where name=%s)""",
        (VERSION, MAIN_CAPSULE, RELATION_CAPSULE, NAME),
    )
    state = cur.fetchone()
    if state == (False, False, False, False):
        return {}
    if state != (True, True, True, True):
        raise AssertionError(f"AC_MARKER_CAPSULE_PLATFORM_MISMATCH:{state}")
    data = MIGRATION.read_bytes()
    cur.execute(
        """select version,encode(extensions.digest(convert_to(
          array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
        from supabase_migrations.schema_migrations where name=%s""",
        (NAME,),
    )
    rows = cur.fetchall()
    if (
        len(rows) != 1
        or rows[0][0] != STAMP
        or rows[0][1] not in {
            MIGRATION_SHA256,
            sha256_bytes(data[:-1] if data.endswith(b"\n") else data),
        }
    ):
        raise AssertionError("AC_SOURCE_PLATFORM_MISMATCH")
    _capsule_security(cur, MAIN_CAPSULE)
    _capsule_security(cur, RELATION_CAPSULE)
    payload = pins()
    observations = _verify_functions(cur, payload)
    observations.update(_verify_views(cur, payload))
    observations.update(_verify_defaults(cur, payload))
    if len(observations) != 272:
        raise AssertionError("AC_RUNTIME_OBSERVATION_CARDINALITY")
    return observations


def verify_audit_source() -> tuple[str, str]:
    """Require the immutable AC writer edge plus its bounded admission repair."""
    verify_source_files()
    git = lambda *args: subprocess.check_output(["git", *args], text=True).strip()
    if git("rev-parse", AB_HEAD + "^{tree}") != AB_TREE:
        raise AssertionError("AC_FROZEN_AB_TREE_MISMATCH")
    if git("merge-base", AB_HEAD, "HEAD") != AB_HEAD:
        raise AssertionError("AC_REQUIRES_FROZEN_AB_ANCESTRY")
    if git("rev-parse", AC_WRITER_HEAD + "^{tree}") != AC_WRITER_TREE:
        raise AssertionError("AC_FROZEN_WRITER_TREE_MISMATCH")
    if git("merge-base", AC_WRITER_HEAD, "HEAD") != AC_WRITER_HEAD:
        raise AssertionError("AC_REQUIRES_FROZEN_WRITER_ANCESTRY")
    if git("rev-list", "--merges", AC_WRITER_HEAD + "..HEAD"):
        raise AssertionError("AC_SUCCESSOR_REPAIR_MUST_BE_LINEAR")
    repaired = set(git(
        "diff", "--name-only", AC_WRITER_HEAD, "HEAD",
    ).splitlines())
    if repaired not in (
        set(), AC_SOURCE_ADMISSION_REPAIR_FILES, AC_SUCCESSOR_REPAIR_FILES,
    ):
        raise AssertionError("AC_ONLY_EXACT_SUCCESSOR_REPAIR_ALLOWED")
    modified = git(
        "diff", "--name-only", "--diff-filter=MDRTCUXB", AB_HEAD, "HEAD", "--",
        "supabase/migrations", "supabase/rollbacks",
    )
    if modified:
        raise AssertionError("AC_PREDECESSOR_SQL_CHANGED:" + modified)
    changed = set(git(
        "diff", "--name-only", AB_HEAD, "HEAD", "--",
        "supabase/migrations", "supabase/rollbacks",
    ).splitlines())
    if changed != {str(MIGRATION), str(ROLLBACK)}:
        raise AssertionError("AC_ONLY_EXACT_SUCCESSOR_SQL_ADDITIONS_ALLOWED")
    head = git("rev-parse", "HEAD")
    if os.environ.get("GITHUB_SHA") and os.environ["GITHUB_SHA"] != head:
        raise AssertionError("AC_EXACT_NATIVE_CHECKOUT_REQUIRED")
    return head, git("rev-parse", "HEAD^{tree}")
