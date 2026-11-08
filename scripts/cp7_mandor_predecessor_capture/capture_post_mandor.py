#!/usr/bin/env python3
"""Capture the installed post-Mandor predecessor without mutating it."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def function_row(cur: Any, signature: str) -> dict[str, Any] | None:
    oid = cur.execute("select to_regprocedure(%s)::oid", (signature,)).fetchone()[0]
    if oid is None:
        return None
    row = cur.execute(
        """
        select p.oid::bigint,
               pg_get_functiondef(p.oid),
               r.rolname,
               l.lanname,
               p.prokind,
               p.prosecdef,
               p.proleakproof,
               p.proisstrict,
               p.proretset,
               p.provolatile,
               p.proparallel,
               p.procost::text,
               p.prorows::text,
               coalesce(p.proconfig, array[]::text[]),
               pg_get_function_identity_arguments(p.oid),
               pg_get_function_result(p.oid),
               p.proacl is null,
               coalesce(p.proacl::text, ''),
               coalesce((
                 select jsonb_agg(jsonb_build_object(
                   'grantor', grantor.rolname,
                   'grantee', case when a.grantee=0 then 'PUBLIC' else grantee.rolname end,
                   'privilege', a.privilege_type,
                   'grantable', a.is_grantable
                 ) order by grantor.rolname,
                            case when a.grantee=0 then 'PUBLIC' else grantee.rolname end,
                            a.privilege_type,
                            a.is_grantable)
                 from aclexplode(coalesce(p.proacl, acldefault('f',p.proowner))) a
                 join pg_roles grantor on grantor.oid=a.grantor
                 left join pg_roles grantee on grantee.oid=a.grantee
               ), '[]'::jsonb)
          from pg_proc p
          join pg_roles r on r.oid=p.proowner
          join pg_language l on l.oid=p.prolang
         where p.oid=%s
        """,
        (oid,),
    ).fetchone()
    keys = [
        "oid", "function_definition", "owner", "language", "kind",
        "security_definer", "leakproof", "strict", "returns_set",
        "volatility", "parallel", "cost", "rows", "config",
        "identity_arguments", "result", "acl_is_null", "raw_acl",
        "effective_acl",
    ]
    result = dict(zip(keys, row))
    result["signature"] = signature
    result["definition_sha256"] = hashlib.sha256(result["function_definition"].encode()).hexdigest()
    return result


def relation_row(cur: Any, name: str) -> dict[str, Any] | None:
    oid = cur.execute("select to_regclass(%s)::oid", (name,)).fetchone()[0]
    if oid is None:
        return None
    rel = cur.execute(
        """
        select c.oid::bigint,r.rolname,c.relkind,c.relpersistence,
               c.relrowsecurity,c.relforcerowsecurity,c.relacl is null,
               coalesce(c.relacl::text,''),
               coalesce((select jsonb_agg(jsonb_build_object(
                 'name',a.attname,'type',format_type(a.atttypid,a.atttypmod),
                 'not_null',a.attnotnull,'generated',a.attgenerated,'identity',a.attidentity,
                 'default',pg_get_expr(d.adbin,d.adrelid)) order by a.attnum)
                 from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
                 where a.attrelid=c.oid and a.attnum>0 and not a.attisdropped),'[]'::jsonb),
               coalesce((select jsonb_agg(jsonb_build_object(
                 'name',con.conname,'type',con.contype,'definition',pg_get_constraintdef(con.oid,true),
                 'deferrable',con.condeferrable,'deferred',con.condeferred,'validated',con.convalidated)
                 order by con.conname) from pg_constraint con where con.conrelid=c.oid),'[]'::jsonb),
               coalesce((select jsonb_agg(jsonb_build_object(
                 'name',t.tgname,'definition',pg_get_triggerdef(t.oid,true),'enabled',t.tgenabled,
                 'constraint_oid',t.tgconstraint::bigint) order by t.tgname)
                 from pg_trigger t where t.tgrelid=c.oid and not t.tgisinternal),'[]'::jsonb),
               coalesce((select jsonb_agg(jsonb_build_object(
                 'name',i.relname,'definition',pg_get_indexdef(i.oid)) order by i.relname)
                 from pg_index x join pg_class i on i.oid=x.indexrelid where x.indrelid=c.oid),'[]'::jsonb)
          from pg_class c join pg_roles r on r.oid=c.relowner where c.oid=%s
        """,
        (oid,),
    ).fetchone()
    keys = ["oid", "owner", "kind", "persistence", "rls", "force_rls", "acl_is_null", "raw_acl", "columns", "constraints", "triggers", "indexes"]
    result = dict(zip(keys, rel))
    result["name"] = name
    return result


def capture_cursor(cur: Any, scope: dict[str, Any], *, transaction_mode: str) -> dict[str, Any]:
    db = cur.execute("select current_database(), current_user, current_setting('server_version_num'), current_setting('TimeZone')").fetchone()
    routines = {s: function_row(cur, s) for s in scope["required_routines"]}
    relations = {n: relation_row(cur, n) for n in scope["required_relations"]}
    body = {
        "classification": scope["classification"],
        "candidate_head": scope["candidate_head"],
        "source_failure_run_id": scope["source_failure_run_id"],
        "capture_github_run_id": int(os.environ["GITHUB_RUN_ID"]) if os.environ.get("GITHUB_RUN_ID", "").isdigit() else None,
        "capture_github_run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]) if os.environ.get("GITHUB_RUN_ATTEMPT", "").isdigit() else None,
        "capture_github_ref": os.environ.get("GITHUB_REF"),
        "database": {"name": db[0], "user": db[1], "server_version_num": db[2], "timezone": db[3]},
        "routines": routines,
        "relations": relations,
        "missing_routines": sorted(k for k, v in routines.items() if v is None),
        "missing_relations": sorted(k for k, v in relations.items() if v is None),
        "transaction_mode": transaction_mode,
        "read_only_transaction": transaction_mode == "READ_ONLY_TRANSACTION",
        "rollback_verified": False,
        "production_go": False,
        "acceptance_credit": 0,
    }
    body["capture_sha256"] = hashlib.sha256(canonical(body)).hexdigest()
    return body


def capture(conn: Any, scope: dict[str, Any]) -> dict[str, Any]:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("set transaction read only")
            return capture_cursor(cur, scope, transaction_mode="READ_ONLY_TRANSACTION")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", required=True)
    parser.add_argument("--scope", type=Path, default=ROOT / "CAPTURE_SCOPE.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parsed = urlparse(args.dsn)
    if (parsed.scheme, parsed.hostname, parsed.port, parsed.path) != (
        "postgresql", "127.0.0.1", 54322, "/cp6_rollback"
    ) or parsed.query or parsed.fragment:
        parser.error("an explicit local cp6_rollback DSN on port 54322 is required")
    import psycopg
    scope = json.loads(args.scope.read_text())
    with psycopg.connect(args.dsn, autocommit=False) as conn:
        result = capture(conn, scope)
    args.output.write_bytes(canonical(result))
    print(json.dumps({"status": "CAPTURED", "output": str(args.output), "capture_sha256": result["capture_sha256"], "missing_routines": result["missing_routines"], "missing_relations": result["missing_relations"]}, sort_keys=True))
    return 0 if not result["missing_routines"] and not result["missing_relations"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
