#!/usr/bin/env python3
"""AF source and live runtime pins, with inherited AE/AD edges preserved."""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
from pathlib import Path

import cp6_v2620ac_runtime as ac
import cp6_v2620ae_runtime as ae
from cp6_v2620af_build_sql import STAMP, NAME, VERSION, MIGRATION, ROLLBACK, PINS, PREDECESSOR_HEAD, PREDECESSOR_TREE

CAPSULE = "erp.cp6_v2620af_rollback_capsule"
PINS_SHA256 = "a6a1e6fde1eb068193cca57024ade6d043f08fce4b9467ad2eb27ce063579dbe"
SOURCE_BASE = "fd904a17f88e52104e6ba89874f16bfb654245d6"
ALLOWED_CANDIDATE_FILES = {
    ".github/workflows/cp6-ac-independent-audit.yml",
    ".github/workflows/cp6-ad-roll-opening-check.yml",
    ".github/workflows/cp6-full-schema-validation.yml",
    "docs/cp6-af-competition-handoff.md",
    "docs/evidence/cp6-af-family-disposition.json",
    "docs/evidence/cp6-af-predecessor-functions.json",
    "docs/evidence/cp6-af-runtime-pins.json",
    "scripts/cp6_preuse_rollback_maintenance.py",
    "scripts/cp6_v2620af_build_sql.py",
    "scripts/cp6_v2620af_family.py",
    "scripts/cp6_v2620af_runtime.py",
    "scripts/cp6_v2620af_concurrency.py",
    "scripts/cp6_v2620af_maintenance_schedules.py",
    "scripts/cp6_v2620af_rollback_guards.py",
    str(MIGRATION), str(ROLLBACK),
}


def pins():
    raw = PINS.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PINS_SHA256:
        raise AssertionError("AF_TRUSTED_PINS_CHANGED")
    payload = json.loads(raw)
    expected = dict(format="CP6_AF_RUNTIME_PINS_V1", stamp=STAMP, name=NAME,
                    version=VERSION, predecessor_head=PREDECESSOR_HEAD,
                    predecessor_tree=PREDECESSOR_TREE, boundary_count=218,
                    predecessor_function_count=533, predecessor_table_count=220,
                    production_go=False)
    if any(payload.get(k) != v for k,v in expected.items()):
        raise AssertionError("AF_TRUSTED_PINS_SHAPE_MISMATCH")
    return payload


def verify_source_files():
    payload = pins()
    ae.verify_source_files()
    for path, expected in payload["source_pins"].items():
        raw = Path(path).read_bytes()
        if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
            raise AssertionError("AF_SOURCE_BYTES_MISMATCH:"+path)
    if {f["identity"] for f in payload["functions"]} != {
        "erp.guard_child_by_parent_status()", "erp.run_v268_financial_report_checks()"
    } or len(payload["functions"]) != 2:
        raise AssertionError("AF_TWO_FUNCTION_BOUNDARY_REQUIRED")
    return payload


def _git(*args):
    return subprocess.check_output(["git",*args],text=True).strip()


def verify_audit_source():
    verify_source_files()
    head,tree = _git("rev-parse","HEAD"),_git("rev-parse","HEAD^{tree}")
    if _git("rev-parse",PREDECESSOR_HEAD+"^{tree}") != PREDECESSOR_TREE:
        raise AssertionError("AF_AE_TREE_MISMATCH")
    if _git("merge-base",SOURCE_BASE,head) != SOURCE_BASE or _git("rev-list","--merges",SOURCE_BASE+".."+head):
        raise AssertionError("AF_LINEAR_SUCCESSOR_REQUIRED")
    changed = set(_git("diff","--name-only",SOURCE_BASE,head).splitlines())
    if changed != ALLOWED_CANDIDATE_FILES:
        raise AssertionError("AF_SOURCE_BOUNDARY_MISMATCH:"+repr(sorted(changed)))
    if _git("diff","--name-only","--diff-filter=MDRTCUXB",SOURCE_BASE,head,"--","supabase/migrations","supabase/rollbacks"):
        raise AssertionError("AF_ADMITTED_SQL_CHANGED")
    if os.environ.get("GITHUB_SHA") != head:
        raise AssertionError("AF_NATIVE_HEAD_REQUIRED")
    return head,tree


def verify_predecessor(cur):
    verify_source_files()
    inherited = ae.verified_successor(cur)
    if len(inherited) != 276:
        raise AssertionError("AF_EXACT_AE_REQUIRED")
    if cur.execute("select to_regclass(%s) is not null or exists(select 1 from erp.schema_migrations where version=%s) or exists(select 1 from supabase_migrations.schema_migrations where name=%s)",
                   (CAPSULE,VERSION,NAME)).fetchone()[0]:
        raise AssertionError("AF_PREDECESSOR_RESIDUE")
    return inherited


def verify_inherited_ae(cur, *, pre_admission=False):
    verify_source_files()
    inherited = ae.verify_inherited_ad(cur, pre_admission=pre_admission)
    payload = ae.pins()
    row = cur.execute("""select exists(select 1 from erp.schema_migrations where version=%s),
      to_regclass(%s) is not null,
      (select count(*) from supabase_migrations.schema_migrations where name=%s)""",
      (ae.VERSION,ae.CAPSULE,ae.NAME)).fetchone()
    platform = cur.execute("""select version,encode(extensions.digest(convert_to(
      array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
      from supabase_migrations.schema_migrations where name=%s""",(ae.NAME,)).fetchone()
    if row != (True,True,1) or platform != (ae.STAMP,payload["source_pins"][str(ae.MIGRATION)]["sha256"]):
        raise AssertionError("AF_INHERITED_AE_PLATFORM_MISMATCH")
    ac._capsule_security(cur,ae.CAPSULE)
    rows = cur.execute(f"""select object_regidentity,definition_sha256,
      encode(extensions.digest(convert_to(object_definition,'UTF8'),'sha256'),'hex'),
      installed_definition_sha256,owner_snapshot,acl_snapshot,boundary_snapshot
      from {ae.CAPSULE} order by object_regidentity""").fetchall()
    expected={x["identity"]:x for x in payload["functions"]}
    if len(rows)!=2 or {r[0] for r in rows}!=set(expected):
        raise AssertionError("AF_INHERITED_AE_CAPSULE_CARDINALITY")
    snapshots=[]
    for identity,old,actual,new,owner,acl,boundary in rows:
        x=expected[identity]
        if (old,actual,new,owner,acl)!=(x["predecessor_sha256"],x["predecessor_sha256"],x["installed_sha256"],x["owner"],x["acl"]):
            raise AssertionError("AF_INHERITED_AE_PIN_MISMATCH:"+identity)
        snapshots.append(boundary)
        inherited["AE_EDGE:"+identity]={**x,"kind":"FUNCTION_EDGE","edge":"AE"}
        # AF replaces the report, but post_opening_balance is still exact AE.
        if identity=="erp.post_opening_balance(uuid)":
            live=cur.execute("""select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
              pg_get_userbyid(p.proowner),array(select a::text from unnest(p.proacl) a order by a::text)
              from pg_proc p where p.oid=to_regprocedure(%s)""",(identity,)).fetchone()
            if live!=(x["installed_sha256"],x["owner"],x["acl"]):
                raise AssertionError("AF_UNCHANGED_AE_OPENING_MISMATCH")
    if snapshots[0] is None or len(snapshots[0])!=217 or snapshots[0]!=snapshots[1]:
        raise AssertionError("AF_INHERITED_AE_BOUNDARY_MISMATCH")
    return inherited


def _own_capsule(cur,payload):
    ac._capsule_security(cur,CAPSULE)
    rows=cur.execute(f"""select cap.object_regidentity,cap.definition_sha256,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex'),
      cap.installed_definition_sha256,cap.owner_snapshot,cap.acl_snapshot,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
      pg_get_userbyid(p.proowner),array(select a::text from unnest(p.proacl) a order by a::text),
      cap.boundary_snapshot from {CAPSULE} cap
      left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
      order by cap.object_regidentity""").fetchall()
    expected={x["identity"]:x for x in payload["functions"]}
    if len(rows)!=2 or {r[0] for r in rows}!=set(expected):
        raise AssertionError("AF_CAPSULE_CARDINALITY")
    snapshots=[];result={}
    for identity,old,actual,new,owner,acl,live,lowner,lacl,boundary in rows:
        x=expected[identity]
        if (old,actual,new,live,owner,lowner,acl,lacl)!=(x["predecessor_sha256"],x["predecessor_sha256"],x["installed_sha256"],x["installed_sha256"],x["owner"],x["owner"],x["acl"],x["acl"]):
            raise AssertionError("AF_CAPSULE_OR_LIVE_PIN_MISMATCH:"+identity)
        snapshots.append(boundary)
        result[identity]={**x,"kind":"FUNCTION","edge":"AF"}
    if snapshots[0] is None or len(snapshots[0])!=218 or snapshots[0]!=snapshots[1]:
        raise AssertionError("AF_CAPSULE_BOUNDARY_MISMATCH")
    return result


def verified_successor(cur):
    payload=verify_source_files()
    row=cur.execute("""select exists(select 1 from erp.schema_migrations where version=%s),
      to_regclass(%s) is not null,(select count(*) from supabase_migrations.schema_migrations where name=%s)""",
      (VERSION,CAPSULE,NAME)).fetchone()
    platform=cur.execute("""select version,encode(extensions.digest(convert_to(
      array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
      from supabase_migrations.schema_migrations where name=%s""",(NAME,)).fetchone()
    if row!=(True,True,1) or platform!=(STAMP,payload["source_pins"][str(MIGRATION)]["sha256"]):
        raise AssertionError("AF_PLATFORM_MISMATCH")
    result=verify_inherited_ae(cur)
    result.update(_own_capsule(cur,payload))
    if len(result)!=278:
        raise AssertionError("AF_RUNTIME_CARDINALITY_MISMATCH")
    return result
