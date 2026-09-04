#!/usr/bin/env python3
"""Build a deterministic CP4.5a schema/config bootstrap from read-only catalog rows.

The extractor streams base64-encoded JSON records on stdin.  This program never
connects to UAT.  It accepts only catalog metadata, migration identities, and a
small allowlist of non-business configuration tables.  The output is a gzip SQL
fixture for the disposable full-schema job plus a non-secret identity manifest.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


FIXTURE_PATH = Path("supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz")
MANIFEST_PATH = Path("supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.manifest.json")
EXTERNAL_TRIGGER_PATH = Path("supabase/tests/fixtures/erp_enteng_cp45a_external_application_triggers.sql")
SOURCE_PROJECT = "siimvrusnzxexizpyoib"
EXPECTED_COUNTS = {
    "sequences": 6,
    "tables": 159,
    "views": 51,
    "functions": 500,
    "triggers": 398,
    "constraints": 1064,
    # Constraint-owned indexes are recreated by PRIMARY/UNIQUE/EXCLUDE
    # constraints.  Only the 202 standalone index definitions are replayed.
    "indexes": 202,
    "policies": 190,
    "platform_migrations": 63,
}
SAFE_DATA_TABLES = (
    "app_roles",
    "app_permissions",
    "app_role_permissions",
    "chart_accounts",
    "accounting_account_mappings",
    "uom_definitions",
    "misc_finance_categories",
    "accounting_period_control",
    "cash_accounts",
    "system_release_info",
    "schema_migrations",
    "cp3_r4_rollback_capsule",
    "cp4_v2616_rollback_capsule",
    "cp45_v2617_rollback_capsule",
    "cp45_v2617a_rollback_capsule",
)
EXPECTED_SAFE_ROWS = {
    "app_roles": 9,
    "app_permissions": 111,
    "app_role_permissions": 329,
    "chart_accounts": 24,
    "accounting_account_mappings": 24,
    "uom_definitions": 8,
    "misc_finance_categories": 2,
    "accounting_period_control": 1,
    "cash_accounts": 1,
    "system_release_info": 1,
    "schema_migrations": 48,
    "cp3_r4_rollback_capsule": 7,
    "cp4_v2616_rollback_capsule": 4,
    "cp45_v2617_rollback_capsule": 3,
    "cp45_v2617a_rollback_capsule": 2,
}
FORBIDDEN_DATA_TABLES = {
    "app_users",
    "audit_logs",
    "production_patterns",
    "production_pattern_audit",
    "cutting_groups",
    "production_orders",
}
EXPECTED_EXTERNAL_TRIGGER = {
    "schema_name": "auth",
    "table_name": "users",
    "trigger_name": "trg_cp45_guard_last_owner_auth_delete",
    "function_schema": "erp",
    "function_name": "guard_last_owner_auth_delete",
    "definition": (
        "CREATE TRIGGER trg_cp45_guard_last_owner_auth_delete BEFORE DELETE ON auth.users "
        "FOR EACH ROW EXECUTE FUNCTION erp.guard_last_owner_auth_delete()"
    ),
    "enabled": "O",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def qi(value: object) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def ql(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def statement(text: object) -> str:
    value = str(text).rstrip()
    return value if value.endswith(";") else value + ";"


def extract_language(definition: str) -> str:
    match = re.search(r"\bLANGUAGE\s+([A-Za-z0-9_]+)", definition, re.I)
    if not match:
        raise ValueError("function language not found")
    return match.group(1).lower()


def extract_body(definition: str) -> str:
    match = re.search(r"\bAS\s+(\$[A-Za-z0-9_]*\$)", definition, re.I)
    if not match:
        return definition
    tag = match.group(1)
    start = match.end()
    end = definition.find(tag, start)
    return definition[start:end] if end >= 0 else definition[start:]


def strip_sql_noise(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"--[^\n]*", " ", text)
    return re.sub(r"'(?:''|[^'])*'", "''", text)


def has_relation_reference(text: str, schema: str, name: str) -> bool:
    qualified = rf"(?<![A-Za-z0-9_]){re.escape(schema)}\s*\.\s*{re.escape(name)}(?![A-Za-z0-9_])"
    unqualified = rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])"
    return re.search(qualified, text, re.I) is not None or re.search(unqualified, text, re.I) is not None


def has_function_call(text: str, schema: str, name: str) -> bool:
    qualified = rf"(?<![A-Za-z0-9_]){re.escape(schema)}\s*\.\s*{re.escape(name)}(?![A-Za-z0-9_])\s*\("
    unqualified = rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])\s*\("
    return re.search(qualified, text, re.I) is not None or re.search(unqualified, text, re.I) is not None


def node_key(kind: str, schema: str, name: str) -> str:
    return f"{kind}:{schema}.{name}"


def topological_mixed_order(
    sql_functions: list[dict[str, object]],
    views: list[dict[str, object]],
    view_dependencies: list[dict[str, object]],
) -> list[tuple[str, dict[str, object]]]:
    sql_by_key = {(str(f["schema_name"]), str(f["function_name"])): f for f in sql_functions}
    view_by_key = {(str(v["schema_name"]), str(v["view_name"])): v for v in views}
    if len(sql_by_key) != len(sql_functions):
        raise SystemExit("overloaded SQL functions require signature-aware ordering")

    nodes: dict[str, tuple[str, dict[str, object]]] = {}
    dependencies: dict[str, set[str]] = defaultdict(set)
    for (schema, name), function in sql_by_key.items():
        nodes[node_key("F", schema, name)] = ("function", function)
    for (schema, name), view in view_by_key.items():
        nodes[node_key("V", schema, name)] = ("view", view)

    for dep in view_dependencies:
        child = node_key("V", str(dep["dependent_schema"]), str(dep["dependent_name"]))
        parent = node_key("V", str(dep["referenced_schema"]), str(dep["referenced_name"]))
        if child in nodes and parent in nodes and child != parent:
            dependencies[child].add(parent)

    for (schema, name), function in sql_by_key.items():
        key = node_key("F", schema, name)
        body = strip_sql_noise(extract_body(str(function["definition"])))
        for view_schema, view_name in view_by_key:
            if has_relation_reference(body, view_schema, view_name):
                dependencies[key].add(node_key("V", view_schema, view_name))
        for callee_schema, callee_name in sql_by_key:
            if (callee_schema, callee_name) != (schema, name) and has_function_call(body, callee_schema, callee_name):
                dependencies[key].add(node_key("F", callee_schema, callee_name))

    for (schema, name), view in view_by_key.items():
        key = node_key("V", schema, name)
        definition = strip_sql_noise(str(view["definition"]))
        for callee_schema, callee_name in sql_by_key:
            if has_function_call(definition, callee_schema, callee_name):
                dependencies[key].add(node_key("F", callee_schema, callee_name))

    for key in nodes:
        dependencies[key] &= set(nodes)
        dependencies[key].discard(key)

    pending = set(nodes)
    ordered: list[tuple[str, dict[str, object]]] = []
    while pending:
        ready = sorted(key for key in pending if not (dependencies[key] & pending))
        if not ready:
            cycle = {key: sorted(dependencies[key] & pending) for key in sorted(pending)}
            raise SystemExit("unresolved SQL-function/view dependency cycle:\n" + json.dumps(cycle, indent=2))
        for key in ready:
            ordered.append(nodes[key])
            pending.remove(key)
    return ordered


def read_stream() -> dict[str, list[dict[str, object]]]:
    pending: dict[tuple[str, str], dict[str, object]] = {}
    ended = False
    for line in sys.stdin:
        if not line.strip():
            continue
        part = json.loads(line)
        if part.get("end") is True:
            ended = True
            break
        category = str(part["category"])
        key = str(part["key"])
        entry = pending.setdefault(
            (category, key),
            {"total": int(part["total"]), "chunks": {}},
        )
        if entry["total"] != int(part["total"]):
            raise SystemExit(f"inconsistent chunk count for {category}/{key}")
        entry["chunks"][int(part["index"])] = str(part["data"])
    if not ended:
        raise SystemExit("catalog stream ended without explicit end marker")

    catalog: dict[str, list[dict[str, object]]] = defaultdict(list)
    for (category, key), entry in sorted(pending.items()):
        chunks = entry["chunks"]
        total = int(entry["total"])
        if len(chunks) != total:
            raise SystemExit(f"incomplete chunks for {category}/{key}: {len(chunks)}/{total}")
        encoded = "".join(chunks[index] for index in range(total))
        value = json.loads(base64.b64decode(encoded, validate=True))
        if not isinstance(value, dict):
            raise SystemExit(f"catalog row must be an object: {category}/{key}")
        catalog[category].append(value)
    return dict(catalog)


def append_acl_reset(ddl: list[str], kind: str, identity: str) -> None:
    ddl.append(f"revoke all on {kind} {identity} from public, anon, authenticated, service_role;")


def main() -> None:
    catalog = read_stream()
    meta_rows = catalog.pop("meta", [])
    if len(meta_rows) != 1:
        raise SystemExit("expected exactly one extraction metadata row")
    meta = meta_rows[0]
    if meta.get("source_project_ref") != SOURCE_PROJECT:
        raise SystemExit("catalog source project mismatch")
    if meta.get("auth_users") != 0 or meta.get("app_users") != 0:
        raise SystemExit("snapshot boundary is not synthetic-identity clean")

    # Application-owned triggers are not necessarily attached to an ERP table.
    # Keep the auth.users guard separate so the catalog fixture remains free of
    # Auth rows while the disposable full-schema boundary is still exact.
    external_triggers = catalog.pop("external_triggers", [])
    if external_triggers != [EXPECTED_EXTERNAL_TRIGGER]:
        raise SystemExit("external application trigger boundary mismatch")

    for category, expected in EXPECTED_COUNTS.items():
        actual = len(catalog.get(category, []))
        if actual != expected:
            raise SystemExit(f"expected {expected} {category}, got {actual}")

    safe_rows: dict[str, list[dict[str, object]]] = {}
    for item in catalog.get("safe_data", []):
        table = str(item["table_name"])
        if table in safe_rows or table not in SAFE_DATA_TABLES or table in FORBIDDEN_DATA_TABLES:
            raise SystemExit(f"unsafe or duplicate data table: {table}")
        rows = item["rows"]
        if not isinstance(rows, list):
            raise SystemExit(f"safe data payload is not an array: {table}")
        safe_rows[table] = rows
    if set(safe_rows) != set(SAFE_DATA_TABLES):
        raise SystemExit("safe configuration table set is incomplete")
    for table, expected in EXPECTED_SAFE_ROWS.items():
        if len(safe_rows[table]) != expected:
            raise SystemExit(f"expected {expected} safe rows in {table}, got {len(safe_rows[table])}")

    columns_by_table: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for column in catalog["columns"]:
        columns_by_table[(str(column["schema_name"]), str(column["table_name"]))].append(column)
    for columns in columns_by_table.values():
        columns.sort(key=lambda item: int(item["ordinal_position"]))

    ddl = [
        r"\set ON_ERROR_STOP on",
        "set client_min_messages=warning;",
        "create extension if not exists pgcrypto with schema extensions;",
        'create extension if not exists "uuid-ossp" with schema extensions;',
        "create extension if not exists pg_stat_statements with schema extensions;",
        "create extension if not exists supabase_vault with schema vault;",
        "create extension if not exists pg_cron with schema pg_catalog;",
        "drop schema if exists erp cascade;",
        "create schema erp authorization postgres;",
    ]

    for custom_type in catalog.get("custom_types", []):
        schema = qi(custom_type["schema_name"])
        name = qi(custom_type["type_name"])
        if custom_type["typtype"] == "e":
            labels = ",".join(ql(label) for label in custom_type["enum_labels"])
            ddl.append(f"create type {schema}.{name} as enum ({labels});")
        elif custom_type["typtype"] == "d":
            text = f"create domain {schema}.{name} as {custom_type['domain_base_type']}"
            if custom_type.get("domain_default"):
                text += f" default {custom_type['domain_default']}"
            if custom_type.get("domain_not_null"):
                text += " not null"
            ddl.append(text + ";")

    for sequence in catalog["sequences"]:
        relation = f"{qi(sequence['schema_name'])}.{qi(sequence['sequence_name'])}"
        ddl.append(
            f"create sequence {relation} as {sequence['data_type']} increment by {sequence['seqincrement']} "
            f"minvalue {sequence['seqmin']} maxvalue {sequence['seqmax']} start with {sequence['seqstart']} "
            f"cache {sequence['seqcache']}" + (" cycle;" if sequence["seqcycle"] else " no cycle;")
        )
        ddl.append(f"alter sequence {relation} owner to {qi(sequence['owner_name'])};")

    for table in catalog["tables"]:
        key = (str(table["schema_name"]), str(table["table_name"]))
        definitions = []
        for column in columns_by_table[key]:
            suffix = ""
            if column["attgenerated"] == "s":
                suffix += f" generated always as ({column['default_expression']}) stored"
            elif column["attidentity"] == "a":
                suffix += " generated always as identity"
            elif column["attidentity"] == "d":
                suffix += " generated by default as identity"
            elif column.get("default_expression"):
                suffix += f" default {column['default_expression']}"
            if column["not_null"]:
                suffix += " not null"
            definitions.append(f"{qi(column['column_name'])} {column['data_type']}{suffix}")
        relation = f"{qi(table['schema_name'])}.{qi(table['table_name'])}"
        ddl.append(f"create table {relation} (\n  " + ",\n  ".join(definitions) + "\n);")
        ddl.append(f"alter table {relation} owner to {qi(table['owner_name'])};")

    for constraint in catalog["constraints"]:
        ddl.append(
            f"alter table only {qi(constraint['schema_name'])}.{qi(constraint['table_name'])} "
            f"add constraint {qi(constraint['constraint_name'])} {constraint['definition']};"
        )
    for index in catalog["indexes"]:
        ddl.append(statement(index["definition"]))

    non_sql_functions = []
    sql_functions = []
    for function in catalog["functions"]:
        target = sql_functions if extract_language(str(function["definition"])) == "sql" else non_sql_functions
        target.append(function)

    ddl.append("set check_function_bodies=off;")
    for function in non_sql_functions:
        ddl.append(statement(function["definition"]))
        ddl.append(
            f"alter function {qi(function['schema_name'])}.{qi(function['function_name'])}"
            f"({function['identity_arguments']}) owner to {qi(function['owner_name'])};"
        )
    ddl.append("set check_function_bodies=on;")

    mixed_order = topological_mixed_order(sql_functions, catalog["views"], catalog["view_dependencies"])
    order_evidence = []
    for kind, item in mixed_order:
        if kind == "function":
            ddl.append(statement(item["definition"]))
            ddl.append(
                f"alter function {qi(item['schema_name'])}.{qi(item['function_name'])}"
                f"({item['identity_arguments']}) owner to {qi(item['owner_name'])};"
            )
            order_evidence.append(f"F:{item['schema_name']}.{item['function_name']}")
        else:
            options = ""
            if item.get("reloptions"):
                options = " with (" + ",".join(item["reloptions"]) + ")"
            relation = f"{qi(item['schema_name'])}.{qi(item['view_name'])}"
            ddl.append(f"create or replace view {relation}{options} as\n{item['definition']};")
            ddl.append(f"alter view {relation} owner to {qi(item['owner_name'])};")
            order_evidence.append(f"V:{item['schema_name']}.{item['view_name']}")

    for trigger in catalog["triggers"]:
        ddl.append(statement(trigger["definition"]))
        relation = f"{qi(trigger['schema_name'])}.{qi(trigger['table_name'])}"
        trigger_name = qi(trigger["trigger_name"])
        enabled = str(trigger["enabled"])
        if enabled == "D":
            ddl.append(f"alter table {relation} disable trigger {trigger_name};")
        elif enabled == "A":
            ddl.append(f"alter table {relation} enable always trigger {trigger_name};")
        elif enabled == "R":
            ddl.append(f"alter table {relation} enable replica trigger {trigger_name};")

    for table in catalog["tables"]:
        relation = f"{qi(table['schema_name'])}.{qi(table['table_name'])}"
        if table["rls_enabled"]:
            ddl.append(f"alter table {relation} enable row level security;")
        if table["rls_forced"]:
            ddl.append(f"alter table {relation} force row level security;")

    for policy in catalog["policies"]:
        roles = ", ".join("public" if str(role).lower() == "public" else qi(role) for role in policy["roles"])
        permissive = "permissive" if policy["permissive"] else "restrictive"
        command = str(policy["cmd"]).lower()
        text = (
            f"create policy {qi(policy['policy_name'])} on {qi(policy['schema_name'])}.{qi(policy['table_name'])} "
            f"as {permissive} for {command} to {roles}"
        )
        if policy.get("qual"):
            text += f" using ({policy['qual']})"
        if policy.get("with_check"):
            text += f" with check ({policy['with_check']})"
        ddl.append(text + ";")

    function_identities = {
        (str(item["schema_name"]), str(item["function_name"]), str(item["identity_arguments"]))
        for item in catalog["functions"]
    }
    for schema, name, arguments in sorted(function_identities):
        append_acl_reset(ddl, "function", f"{qi(schema)}.{qi(name)}({arguments})")
    relation_identities = {
        (str(item["schema_name"]), str(item["table_name"])) for item in catalog["tables"]
    } | {(str(item["schema_name"]), str(item["view_name"])) for item in catalog["views"]}
    for schema, name in sorted(relation_identities):
        append_acl_reset(ddl, "table", f"{qi(schema)}.{qi(name)}")
    for sequence in catalog["sequences"]:
        append_acl_reset(ddl, "sequence", f"{qi(sequence['schema_name'])}.{qi(sequence['sequence_name'])}")

    for grant in catalog["table_grants"]:
        grantee = "public" if str(grant["grantee"]).upper() == "PUBLIC" else qi(grant["grantee"])
        suffix = " with grant option" if grant["is_grantable"] else ""
        ddl.append(
            f"grant {grant['privilege_type']} on table {qi(grant['schema_name'])}.{qi(grant['relation_name'])} "
            f"to {grantee}{suffix};"
        )
    for grant in catalog["sequence_grants"]:
        grantee = "public" if str(grant["grantee"]).upper() == "PUBLIC" else qi(grant["grantee"])
        suffix = " with grant option" if grant["is_grantable"] else ""
        ddl.append(
            f"grant {grant['privilege_type']} on sequence {qi(grant['schema_name'])}.{qi(grant['sequence_name'])} "
            f"to {grantee}{suffix};"
        )
    for grant in catalog["routine_grants"]:
        grantee = "public" if str(grant["grantee"]).upper() == "PUBLIC" else qi(grant["grantee"])
        suffix = " with grant option" if grant["is_grantable"] else ""
        ddl.append(
            f"grant {grant['privilege_type']} on function {qi(grant['schema_name'])}.{qi(grant['routine_name'])}"
            f"({grant['identity_arguments']}) to {grantee}{suffix};"
        )

    ddl.append("set session_replication_role=replica;")
    for table in SAFE_DATA_TABLES:
        rows = safe_rows[table]
        if not rows:
            continue
        columns = [
            item for item in columns_by_table[("erp", table)]
            if not item["attgenerated"]
        ]
        column_list = ",".join(qi(item["column_name"]) for item in columns)
        payload = json.dumps(rows, separators=(",", ":"), ensure_ascii=False)
        delimiter = "$cp45a_snapshot_20260903$"
        if delimiter in payload:
            raise SystemExit(f"unsafe dollar delimiter in {table}")
        overriding = " overriding system value" if any(item["attidentity"] == "a" for item in columns) else ""
        relation = f"{qi('erp')}.{qi(table)}"
        ddl.append(
            f"insert into {relation} ({column_list}){overriding} "
            f"select {column_list} from jsonb_populate_recordset(null::{relation},"
            f"{delimiter}{payload}{delimiter}::jsonb);"
        )
    ddl.append("set session_replication_role=origin;")

    ddl.extend([
        "create schema if not exists supabase_migrations;",
        "create table if not exists supabase_migrations.schema_migrations(version text primary key);",
        "alter table supabase_migrations.schema_migrations add column if not exists statements text[];",
        "alter table supabase_migrations.schema_migrations add column if not exists name text;",
        "truncate table supabase_migrations.schema_migrations;",
    ])
    for migration in catalog["platform_migrations"]:
        ddl.append(
            "insert into supabase_migrations.schema_migrations(version,name,statements) "
            f"values({ql(migration['version'])},{ql(migration['name'])},array[]::text[]);"
        )
    ddl.append("notify pgrst,'reload schema';")

    sql = ("\n\n".join(ddl) + "\n").encode()
    lowered = sql.lower()
    forbidden_patterns = (
        b"postgresql://",
        b"service_role_key",
        b"supabase_service_role_key",
        b"bearer eyj",
        b"-----begin private key-----",
    )
    if any(pattern in lowered for pattern in forbidden_patterns):
        raise SystemExit("credential-like material found in generated fixture")
    compressed = gzip.compress(sql, compresslevel=9, mtime=0)
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_bytes(compressed)

    external_trigger_sql = (
        r"\set ON_ERROR_STOP on" + "\n\n"
        + "set client_min_messages=warning;\n\n"
        + statement(EXPECTED_EXTERNAL_TRIGGER["definition"]) + "\n"
    ).encode()
    EXTERNAL_TRIGGER_PATH.write_bytes(external_trigger_sql)

    canonical_source = json.dumps(
        {category: rows for category, rows in sorted(catalog.items())},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    manifest = {
        "format": "ERP_ENTENG_CP45A_CATALOG_CONFIG_BOOTSTRAP_V1",
        "source_project_ref": SOURCE_PROJECT,
        "source_kind": "READ_ONLY_PG_CATALOG_PLUS_ALLOWLISTED_CONFIGURATION",
        "captured_at_utc": meta["captured_at_utc"],
        "postgres_version": meta["postgres_version"],
        "contains_business_rows": False,
        "contains_auth_rows": False,
        "contains_app_users": False,
        "contains_credentials": False,
        "excluded_nonzero_table": {"table": "audit_logs", "rows": meta["audit_log_rows"]},
        "counts": {category: len(catalog.get(category, [])) for category in sorted(EXPECTED_COUNTS)},
        "support_counts": {
            category: len(catalog.get(category, []))
            for category in ("columns", "custom_types", "view_dependencies", "table_grants", "sequence_grants", "routine_grants")
        },
        "safe_configuration_rows": {table: len(safe_rows[table]) for table in SAFE_DATA_TABLES},
        "catalog_payload_sha256": sha256(canonical_source),
        "external_application_triggers": {
            "captured_at_utc": meta["captured_at_utc"],
            "count": len(external_triggers),
            "source_payload_sha256": sha256(json.dumps(
                external_triggers,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()),
            "fixture_path": str(EXTERNAL_TRIGGER_PATH),
            "sql_bytes": len(external_trigger_sql),
            "sql_sha256": sha256(external_trigger_sql),
        },
        "mixed_sql_function_view_order_count": len(order_evidence),
        "sql_bytes": len(sql),
        "sql_sha256": sha256(sql),
        "gzip_bytes": len(compressed),
        "gzip_sha256": sha256(compressed),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
