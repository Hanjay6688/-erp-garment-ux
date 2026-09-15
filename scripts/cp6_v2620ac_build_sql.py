#!/usr/bin/env python3
"""Build the deterministic AC migration and pre-use rollback from its spec."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


STAMP = "20260915031500"
VERSION = "v2.6.20ac"
NAME = "erp_v2_6_20ac_cp6_temporal_surface_closure"
CAPSULE = "erp.cp6_v2620ac_rollback_capsule"
RELATION_CAPSULE = "erp.cp6_v2620ac_relation_rollback_capsule"
AB_NAME = "erp_v2_6_20ab_cp6_operational_business_clock"
AB_STAMP = "20260914190500"
AB_SHA = "7b31f000b3ca89f4bc776d93f3211f39dce5adbc73445291b9c0e0268f2d7fe3"
AB_SHA_NO_NL = "8e12af37b972bea6043f6ea83f06f495c669e11647042918bfa822cfe250b757"

AB_FUNCTIONS = [
    ("erp.sync_material_cost_revaluation(uuid)",
     "af752a5cb068d71af90c646718b55ef2b6eabd9319021202a0d8f92042892f91",
     ["postgres=X/postgres"]),
    ("erp.process_cost_recalc_queue(integer)",
     "7fe85b6739fa5684171cffd26d028eabd35efe3bb2691e2daa9e52cf40892a13",
     ["authenticated=X/postgres", "postgres=X/postgres", "service_role=X/postgres"]),
    ("erp.resolve_accounting_transaction_date(date)",
     "656ac4cd3ae6a2df24bd11f4c1c044c3e9bf423cc6c7343ab863bad16eee6803",
     ["postgres=X/postgres"]),
    ("erp._cp3_r4_reverse_journal_internal(uuid,text)",
     "2996d1c16396768097306556b5916ba93996d2ff451f3c5e7cd35deea7a3ac6f",
     ["postgres=X/postgres"]),
    ("erp.post_journal(text,uuid,date,text,jsonb)",
     "0a84003a5e6a27cc445e835673d4f5030cbc19cb6b130037eaed922340d34d77",
     ["postgres=X/postgres", "service_role=X/postgres"]),
]


def sha(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def q(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def array_sql(values: list[str] | None) -> str:
    if values is None:
        return "null::text[]"
    return "array[" + ",".join(q(value) for value in values) + "]::text[]"


def values_sql(rows: list[str]) -> str:
    return ",\n  ".join(rows)


def parse_view(statement: str, name: str) -> tuple[str, list[str]]:
    match = re.match(
        rf"^CREATE(?: OR REPLACE)? VIEW erp\.{re.escape(name)}"
        r"(?P<options> WITH \([^\n]+\))? AS\n(?P<body>.*);$",
        statement,
        re.S,
    )
    if match is None:
        raise AssertionError(f"cannot parse view statement: {name}")
    options_text = match.group("options")
    options: list[str] = []
    if options_text:
        raw = options_text.removeprefix(" WITH (").removesuffix(")")
        for item in raw.split(","):
            key, value = item.split("=", 1)
            options.append(f"{key.strip()}={value.strip().strip(chr(39))}")
    return match.group("body").strip(), sorted(options)


def relation_acl(dump: str, name: str) -> list[str]:
    pattern = re.compile(
        rf"(?m)^GRANT ([A-Z,]+) ON TABLE erp\.{re.escape(name)} TO ([a-zA-Z_][a-zA-Z0-9_]*);$"
    )
    grants = pattern.findall(dump)
    privilege_code = {
        "INSERT": "a", "SELECT": "r", "UPDATE": "w", "DELETE": "d",
        "TRUNCATE": "D", "REFERENCES": "x", "TRIGGER": "t",
        "MAINTAIN": "m",
    }
    canonical_order = "arwdDxtm"
    # pg_dump omits an owner-only relation ACL because it is semantically the
    # default.  Pin effective privileges so a NULL relacl and its materialized
    # owner-only equivalent are admitted identically across restore paths.
    acl = ["postgres=arwdDxtm/postgres"]
    for privileges, role in grants:
        if privileges == "ALL":
            codes = canonical_order
        else:
            wanted = {privilege_code[item] for item in privileges.split(",")}
            codes = "".join(code for code in canonical_order if code in wanted)
        acl.append(
            f"{role}={codes}/postgres"
        )
    return sorted(acl)


def load_table_boundary(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, dict[str, Any]] = {}
    for schema, name, rls, owner, acl_text, _rows, _digest in payload["tables"]:
        if schema != "erp":
            continue
        if name in result:
            raise AssertionError(f"duplicate boundary table: {name}")
        if acl_text is None:
            acl = None
        else:
            if not (acl_text.startswith("{") and acl_text.endswith("}")):
                raise AssertionError(f"unexpected table ACL form: {name}")
            body = acl_text[1:-1]
            acl = [] if not body else sorted(body.split(","))
        result[name] = {"owner": owner, "acl": acl, "rls": bool(rls)}
    return result


def apply_view_statement(statement: str) -> str:
    return re.sub(
        r"^CREATE(?: OR REPLACE)? VIEW ",
        "CREATE OR REPLACE VIEW ",
        statement,
        count=1,
    )


def expected_rows(
    spec: dict[str, Any], dump: str, table_boundary: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    functions = []
    for identity, before, after, acl, owner in spec["generated_payload"]["functions"]:
        functions.append({
            "identity": identity,
            "before": before,
            "after": after,
            "before_sha": sha(before),
            "after_sha": sha(after),
            "acl": acl,
            "owner": owner,
        })
    views = []
    for name, before, after in spec["generated_payload"]["views"]:
        before_body, before_options = parse_view(before, name)
        after_body, after_options = parse_view(after, name)
        if before_options != after_options:
            raise AssertionError(f"view options changed: {name}")
        views.append({
            "name": name,
            "identity": f"erp.{name}",
            "before": before,
            "after": apply_view_statement(after),
            "before_body": before_body,
            "after_body": after_body,
            "before_body_sha": sha(before_body),
            "after_body_sha": sha(after_body),
            "reloptions": before_options,
            "acl": relation_acl(dump, name),
            "owner": "postgres",
            "rls": False,
        })
        option_sql = (
            " WITH (" + ",".join(before_options) + ")"
            if before_options else ""
        )
        views[-1]["restore_sha"] = sha(
            f"CREATE OR REPLACE VIEW erp.{name}{option_sql} AS\n{before_body};"
        )
    defaults = []
    for item in spec["generated_payload"]["table_defaults"]:
        table_pin = table_boundary.get(item["table"])
        if table_pin is None:
            raise AssertionError(f"default table absent from boundary: {item['table']}")
        defaults.append({
            **item,
            "identity": f"erp.{item['table']}.{item['column']}",
            **table_pin,
        })
        defaults[-1]["restore_sha"] = sha(
            f"ALTER TABLE erp.{item['table']} ALTER COLUMN {item['column']} "
            f"SET DEFAULT {item['before']};"
        )
    if (len(functions), len(views), len(defaults)) != (115, 13, 144):
        raise AssertionError("AC generated target cardinality mismatch")
    return functions, views, defaults


def expected_temp_tables(
    functions: list[dict[str, Any]],
    views: list[dict[str, Any]],
    defaults: list[dict[str, Any]],
) -> str:
    function_rows = values_sql([
        "(" + ",".join((
            q(item["identity"]), q(item["before_sha"]), q(item["after_sha"]),
            q(item["owner"]), array_sql(item["acl"]),
        )) + ")"
        for item in functions
    ])
    view_rows = values_sql([
        "(" + ",".join((
            q(item["identity"]), q(item["before_body"]),
            q(item["before_body_sha"]), q(item["after_body"]),
            q(item["after_body_sha"]), q(item["owner"]),
            array_sql(item["acl"]), array_sql(item["reloptions"]),
            "true" if item["rls"] else "false",
            q(item["restore_sha"]),
        )) + ")"
        for item in views
    ])
    default_rows = values_sql([
        "(" + ",".join((
            q(item["identity"]), q(item["table"]), q(item["column"]),
            q(item["before"]), q(item["after"]), q(item["owner"]),
            array_sql(item["acl"]),
            "true" if item["rls"] else "false",
            q(item["restore_sha"]),
        )) + ")"
        for item in defaults
    ])
    return f"""
create temporary table cp6_ac_expected_functions(
  identity text primary key,before_sha256 text not null,after_sha256 text not null,
  owner_name text not null,acl text[]
) on commit drop;
insert into pg_temp.cp6_ac_expected_functions values
  {function_rows};

create temporary table cp6_ac_expected_views(
  identity text primary key,before_body text not null,before_sha256 text not null,
  after_body text not null,after_sha256 text not null,
  owner_name text not null,acl text[],reloptions text[],rls boolean not null,
  restore_sha256 text not null
) on commit drop;
insert into pg_temp.cp6_ac_expected_views values
  {view_rows};

create temporary table cp6_ac_expected_defaults(
  identity text primary key,table_name text not null,column_name text not null,
  before_expression text not null,after_expression text not null,
  owner_name text not null,acl text[],rls boolean not null,
  restore_sha256 text not null
) on commit drop;
insert into pg_temp.cp6_ac_expected_defaults values
  {default_rows};

create or replace function pg_temp.cp6_ac_normalized_view_sha256(p_body text)
returns text
language plpgsql
set search_path to pg_catalog
as $cp6_ac_view_probe$
declare v_sha256 text;
begin
  execute format('create temporary view cp6_ac_normalization_probe as %s',p_body);
  select encode(extensions.digest(convert_to(btrim(pg_get_viewdef(
    'pg_temp.cp6_ac_normalization_probe'::regclass,false),E' \\n\\t\\r;'),
    'UTF8'),'sha256'),'hex') into v_sha256;
  execute 'drop view pg_temp.cp6_ac_normalization_probe';
  return v_sha256;
exception when others then
  execute 'drop view if exists pg_temp.cp6_ac_normalization_probe';
  raise;
end
$cp6_ac_view_probe$;
"""


def predecessor_guard() -> str:
    ab_rows = values_sql([
        f"({q(identity)},{q(installed)},{array_sql(acl)})"
        for identity, installed, acl in AB_FUNCTIONS
    ])
    return f"""
do $predecessor_v2620ac$
declare r record;c record;v_live_sha text;v_expected_sha text;v_owner text;
  v_acl text[];v_reloptions text[];v_expression text;v_rls boolean;
begin
  if (select count(*) from erp.schema_migrations where version='v2.6.20ab')<>1
     or exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or to_regclass('{CAPSULE}') is not null
     or to_regclass('{RELATION_CAPSULE}') is not null
     or (select count(*) from supabase_migrations.schema_migrations
         where name='{AB_NAME}')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='{AB_STAMP}' and name='{AB_NAME}'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
             in('{AB_SHA}','{AB_SHA_NO_NL}'))
     or exists(select 1 from supabase_migrations.schema_migrations
       where version>'{AB_STAMP}')
     or (select count(*) from erp.cp6_v2620ab_rollback_capsule)<>5 then
    raise exception 'AC_REQUIRES_EXACT_AB_WITHOUT_SUCCESSOR_RESIDUE';
  end if;

  for r in select * from(values
    {ab_rows}
  ) expected(identity,installed_sha256,acl) loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c from erp.cp6_v2620ab_rollback_capsule cap
    left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
    where cap.object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_actual is distinct from c.definition_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.installed_actual is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.installed_owner is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or c.installed_acl is distinct from r.acl then
      raise exception 'AC_TRUSTED_AB_CAPSULE_MISMATCH: %',r.identity;
    end if;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_functions loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') sha256,
      pg_get_userbyid(p.proowner) owner_name,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end acl
    into c from pg_proc p where p.oid=to_regprocedure(r.identity);
    if c.sha256 is distinct from r.before_sha256
       or c.owner_name is distinct from r.owner_name
       or c.acl is distinct from r.acl then
      raise exception 'AC_FUNCTION_PREDECESSOR_MISMATCH: %',r.identity;
    end if;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_views loop
    v_expected_sha:=pg_temp.cp6_ac_normalized_view_sha256(r.before_body);
    select encode(extensions.digest(convert_to(btrim(pg_get_viewdef(catalog_rel.oid,false),E' \\n\\t\\r;'),'UTF8'),'sha256'),'hex'),
      pg_get_userbyid(catalog_rel.relowner),
      array(select a::text from unnest(coalesce(catalog_rel.relacl,
        acldefault('r',catalog_rel.relowner))) a order by a::text),
      case when catalog_rel.reloptions is null then null else
        array(select x from unnest(catalog_rel.reloptions) x order by x) end,
      catalog_rel.relrowsecurity
    into v_live_sha,v_owner,v_acl,v_reloptions,v_rls
    from pg_class catalog_rel
    where catalog_rel.oid=r.identity::regclass and catalog_rel.relkind='v';
    if encode(extensions.digest(convert_to(r.before_body,'UTF8'),'sha256'),'hex')
         is distinct from r.before_sha256
       or v_live_sha is distinct from v_expected_sha
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_reloptions is distinct from r.reloptions
       or v_rls is distinct from r.rls then
      raise exception 'AC_VIEW_PREDECESSOR_MISMATCH: %',r.identity using detail=format(
        'source=%s body=%s owner=%s acl=%s options=%s rls=%s expected_acl=%s live_acl=%s',
        encode(extensions.digest(convert_to(r.before_body,'UTF8'),'sha256'),'hex')
          is not distinct from r.before_sha256,
        v_live_sha is not distinct from v_expected_sha,
        v_owner is not distinct from r.owner_name,
        v_acl is not distinct from r.acl,
        v_reloptions is not distinct from r.reloptions,
        v_rls is not distinct from r.rls,r.acl,v_acl);
    end if;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_defaults loop
    select pg_get_expr(d.adbin,d.adrelid),pg_get_userbyid(catalog_rel.relowner),
      case when catalog_rel.relacl is null then null else
        array(select x::text from unnest(catalog_rel.relacl) x order by x::text) end,
      catalog_rel.relrowsecurity
    into v_expression,v_owner,v_acl,v_rls
    from pg_class catalog_rel
    join pg_namespace n on n.oid=catalog_rel.relnamespace
    join pg_attribute a on a.attrelid=catalog_rel.oid and a.attname=r.column_name
    left join pg_attrdef d on d.adrelid=catalog_rel.oid and d.adnum=a.attnum
    where n.nspname='erp' and catalog_rel.relname=r.table_name
      and catalog_rel.relkind in('r','p');
    if v_expression is distinct from r.before_expression
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_rls is distinct from r.rls then
      raise exception 'AC_DEFAULT_PREDECESSOR_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$predecessor_v2620ac$;
"""


def capsule_sql() -> str:
    return f"""
create table {CAPSULE}(
  like erp.cp6_v2620ab_rollback_capsule including all
);
alter table {CAPSULE} owner to postgres;
alter table {CAPSULE} enable row level security;
revoke all on {CAPSULE} from public,anon,authenticated,service_role;
insert into {CAPSULE}(
  object_identity,object_regidentity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,
    pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else
    array(select a::text from unnest(p.proacl) a order by a::text) end,
  pg_get_userbyid(p.proowner)
from pg_temp.cp6_ac_expected_functions e
join pg_proc p on p.oid=to_regprocedure(e.identity)
join pg_namespace n on n.oid=p.pronamespace;

create table {RELATION_CAPSULE}(
  object_kind text not null check(object_kind in('VIEW','COLUMN_DEFAULT')),
  object_identity text primary key,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  reloptions_snapshot text[],
  rls_snapshot boolean not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table {RELATION_CAPSULE} owner to postgres;
alter table {RELATION_CAPSULE} enable row level security;
revoke all on {RELATION_CAPSULE} from public,anon,authenticated,service_role;

insert into {RELATION_CAPSULE}(
  object_kind,object_identity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot,reloptions_snapshot,rls_snapshot
)
select 'VIEW',e.identity,
  format('CREATE OR REPLACE VIEW %s%s AS%s%s;',e.identity,
    case when e.reloptions is null then '' else
      ' WITH ('||array_to_string(e.reloptions,',')||')' end,E'\\n',e.before_body),
  encode(extensions.digest(convert_to(e.before_body,'UTF8'),'sha256'),'hex'),
  array(select a::text from unnest(coalesce(c.relacl,
    acldefault('r',c.relowner))) a order by a::text),
  pg_get_userbyid(c.relowner),
  case when c.reloptions is null then null else
    array(select x from unnest(c.reloptions) x order by x) end,
  c.relrowsecurity
from pg_temp.cp6_ac_expected_views e
join pg_class c on c.oid=e.identity::regclass and c.relkind='v';

insert into {RELATION_CAPSULE}(
  object_kind,object_identity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot,reloptions_snapshot,rls_snapshot
)
select 'COLUMN_DEFAULT',e.identity,
  format('ALTER TABLE erp.%I ALTER COLUMN %I SET DEFAULT %s;',
    e.table_name,e.column_name,pg_get_expr(d.adbin,d.adrelid)),
  encode(extensions.digest(convert_to(pg_get_expr(d.adbin,d.adrelid),'UTF8'),'sha256'),'hex'),
  case when c.relacl is null then null else
    array(select a::text from unnest(c.relacl) a order by a::text) end,
  pg_get_userbyid(c.relowner),null,c.relrowsecurity
from pg_temp.cp6_ac_expected_defaults e
join pg_class c on c.relname=e.table_name
join pg_namespace n on n.oid=c.relnamespace and n.nspname='erp'
join pg_attribute a on a.attrelid=c.oid and a.attname=e.column_name
join pg_attrdef d on d.adrelid=c.oid and d.adnum=a.attnum;

do $capsule_v2620ac$
begin
  if (select count(*) from {CAPSULE})<>115
     or (select count(*) from {RELATION_CAPSULE} where object_kind='VIEW')<>13
     or (select count(*) from {RELATION_CAPSULE} where object_kind='COLUMN_DEFAULT')<>144
     or exists(
       select 1 from {RELATION_CAPSULE} cap
       join pg_temp.cp6_ac_expected_views e on e.identity=cap.object_identity
       where cap.object_kind='VIEW'
         and (cap.definition_sha256 is distinct from e.before_sha256
           or encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),
             'sha256'),'hex') is distinct from e.restore_sha256
           or cap.owner_snapshot is distinct from e.owner_name
           or cap.acl_snapshot is distinct from e.acl
           or cap.reloptions_snapshot is distinct from e.reloptions
           or cap.rls_snapshot is distinct from e.rls)
     )
     or exists(
       select 1 from {RELATION_CAPSULE} cap
       join pg_temp.cp6_ac_expected_defaults e on e.identity=cap.object_identity
       where cap.object_kind='COLUMN_DEFAULT'
         and (cap.definition_sha256 is distinct from encode(extensions.digest(
             convert_to(e.before_expression,'UTF8'),'sha256'),'hex')
           or encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),
             'sha256'),'hex') is distinct from e.restore_sha256
           or cap.owner_snapshot is distinct from e.owner_name
           or cap.acl_snapshot is distinct from e.acl
           or cap.reloptions_snapshot is not null
           or cap.rls_snapshot is distinct from e.rls)
     ) then
    raise exception 'AC_CAPSULE_CARDINALITY_MISMATCH';
  end if;
end
$capsule_v2620ac$;
"""


def apply_definitions(
    functions: list[dict[str, Any]],
    views: list[dict[str, Any]],
    defaults: list[dict[str, Any]],
) -> str:
    function_sql = "\n\n".join(item["after"].rstrip() + ";" for item in functions)
    view_sql = "\n\n".join(item["after"].rstrip() for item in views)
    default_sql = "\n".join(
        f"alter table erp.{item['table']} alter column {item['column']} "
        f"set default {item['after']};"
        for item in defaults
    )
    return f"""
-- Generated only from the 709/709 reviewed disposition; do not hand-edit.
{function_sql}

{view_sql}

{default_sql}
"""


def installed_guard() -> str:
    return f"""
do $installed_v2620ac$
declare r record;c record;v_live_sha text;v_expected_sha text;v_owner text;
  v_acl text[];v_reloptions text[];v_expression text;v_rls boolean;
begin
  update {CAPSULE} cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from pg_temp.cp6_ac_expected_functions loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c from {CAPSULE} cap
    left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
    where cap.object_regidentity=r.identity;
    if c.definition_sha256 is distinct from r.before_sha256
       or c.definition_actual is distinct from r.before_sha256
       or c.installed_definition_sha256 is distinct from r.after_sha256
       or c.installed_actual is distinct from r.after_sha256
       or c.owner_snapshot is distinct from r.owner_name
       or c.installed_owner is distinct from r.owner_name
       or c.acl_snapshot is distinct from r.acl
       or c.installed_acl is distinct from r.acl then
      raise exception 'AC_INSTALLED_FUNCTION_MISMATCH: %',r.identity;
    end if;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_views loop
    v_expected_sha:=pg_temp.cp6_ac_normalized_view_sha256(r.after_body);
    select encode(extensions.digest(convert_to(btrim(pg_get_viewdef(catalog_rel.oid,false),E' \\n\\t\\r;'),'UTF8'),'sha256'),'hex'),
      pg_get_userbyid(catalog_rel.relowner),
      array(select a::text from unnest(coalesce(catalog_rel.relacl,
        acldefault('r',catalog_rel.relowner))) a order by a::text),
      case when catalog_rel.reloptions is null then null else
        array(select x from unnest(catalog_rel.reloptions) x order by x) end,
      catalog_rel.relrowsecurity
    into v_live_sha,v_owner,v_acl,v_reloptions,v_rls
    from pg_class catalog_rel
    where catalog_rel.oid=r.identity::regclass and catalog_rel.relkind='v';
    if encode(extensions.digest(convert_to(r.after_body,'UTF8'),'sha256'),'hex')
         is distinct from r.after_sha256
       or v_live_sha is distinct from v_expected_sha
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_reloptions is distinct from r.reloptions
       or v_rls is distinct from r.rls then
      raise exception 'AC_INSTALLED_VIEW_MISMATCH: %',r.identity using detail=format(
        'source=%s body=%s owner=%s acl=%s options=%s rls=%s expected_acl=%s live_acl=%s',
        encode(extensions.digest(convert_to(r.after_body,'UTF8'),'sha256'),'hex')
          is not distinct from r.after_sha256,
        v_live_sha is not distinct from v_expected_sha,
        v_owner is not distinct from r.owner_name,
        v_acl is not distinct from r.acl,
        v_reloptions is not distinct from r.reloptions,
        v_rls is not distinct from r.rls,r.acl,v_acl);
    end if;
    update {RELATION_CAPSULE} set installed_definition_sha256=v_live_sha
    where object_kind='VIEW' and object_identity=r.identity;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_defaults loop
    select pg_get_expr(d.adbin,d.adrelid),pg_get_userbyid(catalog_rel.relowner),
      case when catalog_rel.relacl is null then null else
        array(select x::text from unnest(catalog_rel.relacl) x order by x::text) end,
      catalog_rel.relrowsecurity
    into v_expression,v_owner,v_acl,v_rls
    from pg_class catalog_rel
    join pg_namespace n on n.oid=catalog_rel.relnamespace
    join pg_attribute a on a.attrelid=catalog_rel.oid and a.attname=r.column_name
    left join pg_attrdef d on d.adrelid=catalog_rel.oid and d.adnum=a.attnum
    where n.nspname='erp' and catalog_rel.relname=r.table_name
      and catalog_rel.relkind in('r','p');
    if v_expression is distinct from r.after_expression
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_rls is distinct from r.rls then
      raise exception 'AC_INSTALLED_DEFAULT_MISMATCH: %',r.identity;
    end if;
    update {RELATION_CAPSULE} set installed_definition_sha256=
      encode(extensions.digest(convert_to(v_expression,'UTF8'),'sha256'),'hex')
    where object_kind='COLUMN_DEFAULT' and object_identity=r.identity;
  end loop;
end
$installed_v2620ac$;
"""


def boundary_and_marker() -> str:
    return f"""
do $boundary_v2620ac$
declare v_table text;v_hash text;v_snapshot jsonb:='{{}}';
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='erp' and c.relkind in('r','p')
      and c.relname not in('schema_migrations','cp6_v2620ac_rollback_capsule',
        'cp6_v2620ac_relation_rollback_capsule') order by c.relname
  loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  if (select count(*) from jsonb_object_keys(v_snapshot))<>214 then
    raise exception 'AC_FULL_ERP_BOUNDARY_CARDINALITY expected214 actual%',
      (select count(*) from jsonb_object_keys(v_snapshot));
  end if;
  update {CAPSULE} set boundary_snapshot=v_snapshot;
end
$boundary_v2620ac$;

insert into erp.schema_migrations(version,description)
values('{VERSION}','Complete CP6 temporal surface: Jakarta statement-date semantics, explicit instant-to-date conversion, stable current views, and operational statement timestamps');
commit;
"""


def migration_sql(
    spec: dict[str, Any],
    functions: list[dict[str, Any]],
    views: list[dict[str, Any]],
    defaults: list[dict[str, Any]],
) -> str:
    evidence_sha = sha(json.dumps(
        {key: value for key, value in spec.items() if key != "generated_payload"},
        indent=2,
        sort_keys=True,
    ) + "\n")
    return f"""-- CP6 AC: complete classified temporal surface closure.
-- 208/208 open hits resolved plus 216 transaction-clock metadata hardenings.
-- Total reviewed: 709; changes: 422; retained: 285; two date-only exclusions.
-- Evidence SHA-256: {evidence_sha}
-- AB SQL remains immutable. production_go:false.
begin;
set local lock_timeout='10s';
set local statement_timeout='360s';
set local timezone='UTC';
set local search_path='pg_catalog';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

do $lock_all_erp_v2620ac$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='erp' and c.relkind in('r','p') order by c.relname
  loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620ac$;

{expected_temp_tables(functions, views, defaults)}
{predecessor_guard()}
{capsule_sql()}
{apply_definitions(functions, views, defaults)}
{installed_guard()}
{boundary_and_marker()}"""


def rollback_sql(
    migration_sha: str,
    migration_sha_no_nl: str,
    functions: list[dict[str, Any]],
    views: list[dict[str, Any]],
    defaults: list[dict[str, Any]],
) -> str:
    return f"""-- REVIEWED PRE-USE ROLLBACK: CP6 {VERSION} -> exact AB.
-- Execute only through the AC maintenance boundary before production use.
begin;
set local lock_timeout='10s';
set local statement_timeout='360s';
set local timezone='UTC';
set local search_path='pg_catalog';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;

do $platform_guard_v2620ac$
begin
  if (select count(*) from supabase_migrations.schema_migrations where name='{NAME}')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='{STAMP}' and name='{NAME}'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
           in('{migration_sha}','{migration_sha_no_nl}'))
     or exists(select 1 from supabase_migrations.schema_migrations where version>'{STAMP}') then
    raise exception 'AC_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR';
  end if;
end
$platform_guard_v2620ac$;

do $lock_all_erp_v2620ac$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='erp' and c.relkind in('r','p') order by c.relname
  loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620ac$;

{expected_temp_tables(functions, views, defaults)}

do $restore_v2620ac$
declare r record;c record;v_table text;v_hash text;v_expected jsonb;
  v_live_sha text;v_expected_sha text;v_expression text;v_owner text;
  v_acl text[];v_reloptions text[];v_rls boolean;
begin
  if (select count(*) from erp.schema_migrations where version='{VERSION}')<>1
     or (select count(*) from erp.schema_migrations where version='v2.6.20ab')<>1
     or (select count(*) from {CAPSULE})<>115
     or (select count(*) from {RELATION_CAPSULE})<>157 then
    raise exception 'AC_ROLLBACK_MARKER_OR_CAPSULE_MISMATCH';
  end if;

  for r in select * from pg_temp.cp6_ac_expected_functions loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c from {CAPSULE} cap
    left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
    where cap.object_regidentity=r.identity;
    if c.definition_sha256 is distinct from r.before_sha256
       or c.definition_actual is distinct from r.before_sha256
       or c.installed_definition_sha256 is distinct from r.after_sha256
       or c.installed_actual is distinct from r.after_sha256
       or c.owner_snapshot is distinct from r.owner_name
       or c.installed_owner is distinct from r.owner_name
       or c.acl_snapshot is distinct from r.acl
       or c.installed_acl is distinct from r.acl then
      raise exception 'AC_ROLLBACK_FUNCTION_GUARD: %',r.identity;
    end if;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_views loop
    select cap.* into c from {RELATION_CAPSULE} cap
      where cap.object_kind='VIEW' and cap.object_identity=r.identity;
    v_expected_sha:=pg_temp.cp6_ac_normalized_view_sha256(r.after_body);
    select encode(extensions.digest(convert_to(btrim(pg_get_viewdef(v.oid,false),E' \\n\\t\\r;'),'UTF8'),'sha256'),'hex'),
      pg_get_userbyid(v.relowner),
      array(select x::text from unnest(coalesce(v.relacl,
        acldefault('r',v.relowner))) x order by x::text),
      case when v.reloptions is null then null else
        array(select x from unnest(v.reloptions) x order by x) end,
      v.relrowsecurity
    into v_live_sha,v_owner,v_acl,v_reloptions,v_rls
    from pg_class v where v.oid=r.identity::regclass and v.relkind='v';
    if encode(extensions.digest(convert_to(r.before_body,'UTF8'),'sha256'),'hex')
         is distinct from r.before_sha256
       or encode(extensions.digest(convert_to(r.after_body,'UTF8'),'sha256'),'hex')
         is distinct from r.after_sha256
       or c.definition_sha256 is distinct from r.before_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),
         'sha256'),'hex') is distinct from r.restore_sha256
       or c.installed_definition_sha256 is distinct from v_live_sha
       or v_live_sha is distinct from v_expected_sha
       or c.owner_snapshot is distinct from r.owner_name
       or c.acl_snapshot is distinct from r.acl
       or c.reloptions_snapshot is distinct from r.reloptions
       or c.rls_snapshot is distinct from r.rls
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_reloptions is distinct from r.reloptions
       or v_rls is distinct from r.rls then
      raise exception 'AC_ROLLBACK_VIEW_GUARD: %',r.identity;
    end if;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_defaults loop
    select cap.* into c from {RELATION_CAPSULE} cap
      where cap.object_kind='COLUMN_DEFAULT' and cap.object_identity=r.identity;
    select pg_get_expr(d.adbin,d.adrelid),pg_get_userbyid(t.relowner),
      case when t.relacl is null then null else
        array(select x::text from unnest(t.relacl) x order by x::text) end,
      t.relrowsecurity
    into v_expression,v_owner,v_acl,v_rls
    from pg_class t join pg_namespace n on n.oid=t.relnamespace
    join pg_attribute a on a.attrelid=t.oid and a.attname=r.column_name
    left join pg_attrdef d on d.adrelid=t.oid and d.adnum=a.attnum
    where n.nspname='erp' and t.relname=r.table_name and t.relkind in('r','p');
    if c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(r.before_expression,'UTF8'),'sha256'),'hex')
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),
         'sha256'),'hex') is distinct from r.restore_sha256
       or c.installed_definition_sha256 is distinct from encode(extensions.digest(
         convert_to(r.after_expression,'UTF8'),'sha256'),'hex')
       or v_expression is distinct from r.after_expression
       or c.owner_snapshot is distinct from r.owner_name
       or c.acl_snapshot is distinct from r.acl
       or c.rls_snapshot is distinct from r.rls
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_rls is distinct from r.rls then
      raise exception 'AC_ROLLBACK_DEFAULT_GUARD: %',r.identity;
    end if;
  end loop;

  select boundary_snapshot into v_expected from {CAPSULE} limit 1;
  if v_expected is null or (select count(*) from jsonb_object_keys(v_expected))<>214
     or (select count(*) from pg_class rel join pg_namespace n on n.oid=rel.relnamespace
         where n.nspname='erp' and rel.relkind in('r','p')
           and rel.relname not in('schema_migrations','cp6_v2620ac_rollback_capsule',
             'cp6_v2620ac_relation_rollback_capsule'))<>214
     or exists(select 1 from {CAPSULE} where boundary_snapshot is distinct from v_expected) then
    raise exception 'AC_ROLLBACK_BOUNDARY_CAPSULE_MISMATCH';
  end if;
  for v_table in select rel.relname from pg_class rel join pg_namespace n on n.oid=rel.relnamespace
    where n.nspname='erp' and rel.relkind in('r','p')
      and rel.relname not in('schema_migrations','cp6_v2620ac_rollback_capsule',
        'cp6_v2620ac_relation_rollback_capsule') order by rel.relname
  loop
    execute format($q$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$q$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'AC_POST_USE_ROLLBACK_REFUSED: %',v_table;
    end if;
  end loop;

  for c in select * from {CAPSULE} order by object_regidentity loop
    execute c.object_definition;
  end loop;
  for c in select * from {RELATION_CAPSULE} where object_kind='VIEW'
    order by object_identity loop
    execute c.object_definition;
  end loop;
  for c in select * from {RELATION_CAPSULE} where object_kind='COLUMN_DEFAULT'
    order by object_identity loop
    execute c.object_definition;
  end loop;

  for r in select * from pg_temp.cp6_ac_expected_functions loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(
        to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.before_sha256 then
      raise exception 'AC_ROLLBACK_FUNCTION_RESTORE_MISMATCH: %',r.identity;
    end if;
  end loop;
  for r in select * from pg_temp.cp6_ac_expected_views loop
    v_expected_sha:=pg_temp.cp6_ac_normalized_view_sha256(r.before_body);
    select encode(extensions.digest(convert_to(btrim(pg_get_viewdef(v.oid,false),E' \\n\\t\\r;'),'UTF8'),'sha256'),'hex')
    into v_live_sha from pg_class v
      where v.oid=r.identity::regclass and v.relkind='v';
    if v_live_sha is distinct from v_expected_sha then
      raise exception 'AC_ROLLBACK_VIEW_RESTORE_MISMATCH: %',r.identity;
    end if;
  end loop;
  for r in select * from pg_temp.cp6_ac_expected_defaults loop
    select pg_get_expr(d.adbin,d.adrelid),pg_get_userbyid(t.relowner),
      case when t.relacl is null then null else
        array(select x::text from unnest(t.relacl) x order by x::text) end,
      t.relrowsecurity
    into v_expression,v_owner,v_acl,v_rls
    from pg_class t join pg_namespace n on n.oid=t.relnamespace
    join pg_attribute a on a.attrelid=t.oid and a.attname=r.column_name
    left join pg_attrdef d on d.adrelid=t.oid and d.adnum=a.attnum
    where n.nspname='erp' and t.relname=r.table_name;
    if v_expression is distinct from r.before_expression
       or v_owner is distinct from r.owner_name
       or v_acl is distinct from r.acl
       or v_rls is distinct from r.rls then
      raise exception 'AC_ROLLBACK_DEFAULT_RESTORE_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$restore_v2620ac$;

drop table {RELATION_CAPSULE};
drop table {CAPSULE};
delete from erp.schema_migrations where version='{VERSION}';
delete from supabase_migrations.schema_migrations
where version='{STAMP}' and name='{NAME}'
  and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
    in('{migration_sha}','{migration_sha_no_nl}');

do $postcheck_v2620ac$
begin
  if exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or exists(select 1 from supabase_migrations.schema_migrations where name='{NAME}')
     or to_regclass('{CAPSULE}') is not null
     or to_regclass('{RELATION_CAPSULE}') is not null
     or (select count(*) from erp.schema_migrations where version='v2.6.20ab')<>1
     or (select count(*) from erp.cp6_v2620ab_rollback_capsule)<>5 then
    raise exception 'AC_ROLLBACK_POSTCONDITION_FAILED';
  end if;
end
$postcheck_v2620ac$;
commit;
"""


def run(args: argparse.Namespace) -> None:
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if spec["summary"] != {
        "additional_transaction_clock_hardening_occurrences": 216,
        "change_occurrences": 422,
        "completeness_gate": "PASS_SPEC",
        "explicit_exclusions": 2,
        "incoming_open_occurrences": 208,
        "paired_occurrences_covered_by_format_edits": 3,
        "retained_occurrences": 285,
        "reviewed_occurrences": 709,
        "source_inventory_occurrences": 709,
        "source_edits": 419,
        "transformed_functions": 115,
        "transformed_table_defaults": 144,
        "transformed_views": 13,
        "unresolved_occurrences": 0,
    }:
        raise AssertionError("AC spec summary mismatch")
    dump = args.schema_dump.read_text(encoding="utf-8")
    table_boundary = load_table_boundary(args.table_boundary)
    functions, views, defaults = expected_rows(spec, dump, table_boundary)
    pins = {
        "format": "CP6_V2620AC_RUNTIME_PINS_V1",
        "source": {
            **spec["source"],
            "table_boundary_sha256": sha(args.table_boundary.read_bytes()),
        },
        "summary": {
            "functions": len(functions),
            "views": len(views),
            "table_defaults": len(defaults),
            "main_capsule_rows": len(functions),
            "relation_capsule_rows": len(views) + len(defaults),
        },
        "functions": [{
            key: item[key] for key in
            ("identity", "before_sha", "after_sha", "owner", "acl")
        } for item in functions],
        "views": [{
            key: item[key] for key in (
                "identity", "before_body_sha", "after_body_sha", "owner",
                "acl", "reloptions", "rls", "restore_sha",
            )
        } for item in views],
        "table_defaults": [{
            key: item[key] for key in
            ("identity", "table", "column", "before", "after", "owner",
             "acl", "rls", "restore_sha")
        } for item in defaults],
    }
    if args.pins is not None:
        args.pins.parent.mkdir(parents=True, exist_ok=True)
        args.pins.write_text(
            json.dumps(pins, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    migration = migration_sql(spec, functions, views, defaults)
    args.migration.parent.mkdir(parents=True, exist_ok=True)
    args.migration.write_text(migration, encoding="utf-8")
    migration_sha = sha(args.migration.read_bytes())
    without_newline = migration[:-1] if migration.endswith("\n") else migration
    rollback = rollback_sql(
        migration_sha, sha(without_newline), functions, views, defaults
    )
    args.rollback.parent.mkdir(parents=True, exist_ok=True)
    args.rollback.write_text(rollback, encoding="utf-8")
    print(json.dumps({
        "migration": str(args.migration),
        "migration_bytes": args.migration.stat().st_size,
        "migration_sha256": migration_sha,
        "rollback": str(args.rollback),
        "rollback_bytes": args.rollback.stat().st_size,
        "rollback_sha256": sha(args.rollback.read_bytes()),
    }, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--schema-dump", type=Path, required=True)
    parser.add_argument("--table-boundary", type=Path, required=True)
    parser.add_argument("--migration", type=Path, required=True)
    parser.add_argument("--rollback", type=Path, required=True)
    parser.add_argument("--pins", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
