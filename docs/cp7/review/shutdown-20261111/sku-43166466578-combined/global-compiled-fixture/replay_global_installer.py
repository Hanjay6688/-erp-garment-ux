"""Execute the closed Global SQL and check metadata on a disposable fixture."""

from argparse import ArgumentParser
from hashlib import file_digest, sha256
import json
from pathlib import Path
import re
import subprocess
import sys

import psycopg
from psycopg import errors, sql

from loopback_postgres import cluster
from restore_fixture_erp import original, restore


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def recreate_dependencies(cur, captured, sources, native):
    """Use archived relation types for the missing CP7 dependencies."""
    relations, columns, functions, types = (dict(captured[group])
        for group in ("relations", "columns", "functions", "types"))
    dependencies = ("cp7_credit.initial_hpp_account_facts_v1()", "cp7_credit.pg_jsonb_sha256(jsonb)")
    definitions = {name: functions[name][0] for name in dependencies}
    for name, definition in native.items():
        assert functions[name][0] == definition[0], name
        definitions[name] = definition[0]
    roles = {row[0] for name in definitions for row in functions[name][18]}
    for role in sorted(roles - {"PUBLIC"}):
        if not cur.execute("select exists(select 1 from pg_roles where rolname=%s)", (role,)).fetchone()[0]:
            cur.execute(sql.SQL("create role {} nologin").format(sql.Identifier(role)))

    references = set(re.findall(r"\b[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*\b",
                                "\n".join([*sources.values(), *definitions.values()])))
    tables = {name for name in references & relations.keys() if relations[name][1] == "r"}
    made = []
    for schema in sorted({name.split(".")[0] for name in tables | definitions.keys()} - {"erp"}):
        cur.execute(sql.SQL("create schema if not exists {}").format(sql.Identifier(schema)))
    for name in sorted(tables):
        if cur.execute("select to_regclass(%s) is not null", (name,)).fetchone()[0]:
            continue
        attrs = sorted((row for key, row in columns.items() if key.startswith(name + ":")), key=lambda row: row[1])
        assert attrs, name
        for kind in sorted({row[2].removesuffix("[]") for row in attrs} & types.keys()):
            if cur.execute("select to_regtype(%s) is not null", (kind,)).fetchone()[0]:
                continue
            meta = types[kind]
            assert meta[1] == "d" and not meta[5] and meta[7] is None, kind
            checks = [sql.SQL("constraint {} {}").format(sql.Identifier(key.split(":", 1)[1]), sql.SQL(row[10]))
                      for key, row in captured["constraints"] if key.startswith(kind + ":")]
            cur.execute(sql.SQL("create domain {} as {} {}").format(
                sql.Identifier(*kind.split(".")), sql.SQL(meta[6]), sql.SQL(" ").join(checks)))
        typed = [sql.SQL("{} {}").format(sql.Identifier(row[0]), sql.SQL(row[2])) for row in attrs]
        cur.execute(sql.SQL("create table {} ({})").format(sql.Identifier(*name.split(".")), sql.SQL(",").join(typed)))
        made.append(name)

    # These are source prerequisites. The Global installer below is compiled
    # with normal body checking, including all SQL-language queries.
    cur.execute("set local check_function_bodies=false")
    for name, definition in definitions.items():
        cur.execute(definition, prepare=False)
        identifier = sql.SQL(name)
        cur.execute(sql.SQL("revoke all on function {} from public").format(identifier))
        for grantee, _, privilege, grantable in functions[name][18]:
            if grantee == "postgres":
                continue
            assert privilege == "EXECUTE" and grantable is False, name
            role = sql.SQL("PUBLIC") if grantee == "PUBLIC" else sql.Identifier(grantee)
            cur.execute(sql.SQL("grant execute on function {} to {}").format(identifier, role))
    cur.execute("set local check_function_bodies=true")
    return made


def expect_refusal(conn, command, error, message):
    try:
        with conn.transaction():
            conn.execute(command)
    except error as exc:
        assert message in str(exc), str(exc)
        return dict(sqlstate=exc.sqlstate, first_message=str(exc).splitlines()[0])
    raise AssertionError("Expected refusal: " + message)


def run(bin_dir, archive, global_source):
    sys.path.insert(0, str(global_source / "scripts"))
    from cp7_global_nonpo_envelope import composition as c
    from cp7_global_nonpo_envelope import native_hooks

    with archive.open("rb") as stream:
        archive_pin = dict(bytes=archive.stat().st_size, sha256=file_digest(stream, "sha256").hexdigest())
    assert archive_pin == dict(bytes=96749933,
        sha256="dd9e31355a0820d1650e438a8913c49450a10dbc342789ed94f3418c1be6363b")
    global_commit = subprocess.check_output(
        ["git", "-C", str(global_source), "rev-parse", "HEAD"], text=True).strip()
    assert global_commit == "c9248b8770ec8cfe0f7e2f2fd8da26c141ea67c5"
    raw, captured = original(archive)
    native = native_hooks.originals()
    definitions, _ = native_hooks.derive(native)
    sources = c.sql_sources()
    plan = json.loads((c.HERE / "INSTALL_PLAN.json").read_bytes())
    assert {name: pin(body.encode()) for name, body in sources.items()} == plan["source_sql"]
    assert {name: pin(body.encode()) for name, body in definitions.items()} == plan["native_adapter_sources"]
    with cluster(bin_dir) as config, psycopg.connect(**config, autocommit=True) as conn:
        assert conn.execute("show server_version").fetchone() == ("17.6",)
        assert config["host"] == "127.0.0.1" and conn.execute("select inet_server_addr()::text").fetchone()[0].startswith("127.0.0.1")
        with conn.transaction():
            copies = restore(conn, raw, captured)
            conn.execute("create role supabase_admin superuser")
            made = recreate_dependencies(conn, captured, sources, native)
            conn.execute("alter default privileges grant execute on functions to anon")
            conn.execute("alter default privileges for role supabase_admin grant execute on functions to anon")
        conn.execute("set check_function_bodies=true")

        with conn.cursor() as cur, conn.transaction():
            before = c.capture(cur)
            identity = c.native_identity(cur, definitions)
            with conn.transaction(force_rollback=True):
                assert cur.execute("show check_function_bodies").fetchone() == ("on",)
                c.trusted_installer(cur)
                with c.as_role(cur, "postgres"):
                    cur.execute("create schema cp7_global_nonpo_native_graph authorization postgres")
                    for name in c.CORE_ORDER:
                        cur.execute(sources[name], prepare=False)
                for name in c.PLATFORM_ORDER:
                    with c.as_role(cur, "supabase_admin"):
                        cur.execute(sources[name], prepare=False)
                c.normalize_private(cur, plan)
                c.replace_native(cur, definitions, identity)
                observed = c.capture(cur)
                c.transition(before, observed, definitions, plan)
                metadata = c.verify_objects(cur, observed, plan)
                assert c.native_identity(cur, definitions) == identity
                assert cur.execute("select count(*) from cp7_global_nonpo_envelope.profiles").fetchone() == (0,)
                assert cur.execute("select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()").fetchone()[0] == c.fingerprint(cur, observed)
                refused_without_fence = expect_refusal(conn,
                    "select cp7_global_catalog_fence.lock_relations_v1(repeat('1',64))", errors.RaiseException,
                    "CP7_GLOBAL_COMPLETE_CATALOG_FENCE_REQUIRED_FIRST")
                locked = cur.execute("select cp7_global_catalog_fence.lock_v1()").fetchone()[0]
                assert len(locked) == cur.execute("select count(*) from pg_class c join pg_namespace n on "
                    "n.oid=c.relnamespace where n.nspname='pg_catalog' and c.relkind in ('r','p')").fetchone()[0]
                with psycopg.connect(**config, autocommit=True) as other:
                    other.execute("set lock_timeout='300ms'")
                    blocked_ddl = expect_refusal(other, "create table erp.global_fixture_ddl_attempt(id int)",
                                                errors.LockNotAvailable, "lock timeout")
                    assert other.execute("select to_regclass('erp.global_fixture_ddl_attempt')").fetchone() == (None,)
            assert c.capture(cur) == before
            assert c.native_identity(cur, definitions) == identity
        assert conn.execute("select count(*) from pg_namespace where nspname like 'cp7_global%'").fetchone() == (0,)
    return dict(status="EXACT_GLOBAL_DDL_AND_CATALOG_LOCKS_PASS_IN_POSTGRESQL_17_6",
                global_closed_base=global_commit, source_archive=archive_pin,
                CP6_disposable_source=pin(raw), archived_copy_blocks=copies, extra_typed_relations=made,
                installation_plan=pin((c.HERE / "INSTALL_PLAN.json").read_bytes()),
                sql_sources=plan["source_sql"], adapted_definitions=plan["native_adapter_sources"],
                new_object_metadata=metadata, catalog_relations_locked=len(locked), ddl_blocked=blocked_ddl,
                delegate_without_fence_refused=refused_without_fence, after_rollback_full25_equal=True,
                native_oid_acl_restored=True, profile_admission_performed=False, actual_ERP_cases=0,
                production_go=False, independent_acceptance=False)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    for name in ("pg_bin", "e4ea_original", "global_source", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    receipt = run(args.pg_bin.resolve(), args.e4ea_original.resolve(), args.global_source.resolve())
    with args.output.open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: receipt[key] for key in ("status", "archived_copy_blocks",
          "catalog_relations_locked", "after_rollback_full25_equal", "actual_ERP_cases")}))
