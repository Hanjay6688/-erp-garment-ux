#!/usr/bin/env python3
"""Build AE from the exact AD functions and reviewed AD capsule pattern."""

from pathlib import Path
import hashlib
import json

import cp6_v2620ad_build_sql as ad_build


STAMP = "20260915201500"
NAME = "erp_v2_6_20ae_cp6_opening_roll_integrity"
VERSION = "v2.6.20ae"
MIGRATION = Path(f"supabase/migrations/{STAMP}_{NAME}.sql")
ROLLBACK = Path(f"supabase/rollbacks/{STAMP}_{NAME}.rollback.sql")
PINS = Path("docs/evidence/cp6-ae-runtime-pins.json")
BUILDER = Path("scripts/cp6_v2620ae_build_sql.py")
AD_MIGRATION = ad_build.MIGRATION
AD_ROLLBACK = ad_build.ROLLBACK
AD_MIGRATION_SHA256 = "cd4879eb9b053e3b7a975e1430f481131e377f260ece2f19f07bfb4c98498c1d"
AD_ROLLBACK_SHA256 = "38eb8025f07fa9a49f221fa274e56242c5c525947c3d24dc98a735d02b75512c"
PREDECESSOR_HEAD = "b2663a0cb490432b53ca92670a17f7a268a8e7a3"
PREDECESSOR_TREE = "12cff34f745f19930b50296d003f6e5da3127d3e"
ACL = "array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]"
IDENTITIES = ad_build.IDENTITIES
AD_HASHES = (
    "cc89ac9e978723c70728cc183104490109bf2530ce8dd1a99b314018a5b0f6eb",
    "6a93242cb0325baee511c2753eb65588600fe8b9a7fc62d423b85f14bf9c71d5",
)

POST_ANCHOR = """  if not exists(select 1 from erp.opening_balance_items where opening_id=h.id) then raise exception 'Opening balance has no lines'; end if;
  select count(*),(array_agg(id order by id))[1] into v_fg_count,v_default_fg_location from erp.locations where location_type='FG_WAREHOUSE' and is_active=true;"""

POST_REPLACEMENT = """  if not exists(select 1 from erp.opening_balance_items where opening_id=h.id) then raise exception 'Opening balance has no lines'; end if;

  perform i.id from erp.opening_balance_items i
  where i.opening_id=h.id order by i.id for update;
  if exists(
    select 1 from erp.opening_balance_items i
    where i.opening_id=h.id and i.roll_id is not null
      and i.balance_type<>'MATERIAL'
  ) then
    raise exception 'AE_OPENING_ROLL_ONLY_ALLOWED_FOR_MATERIAL';
  end if;
  if exists(
    select 1 from erp.opening_balance_items i
    where i.opening_id=h.id and i.balance_type='MATERIAL'
      and i.roll_id is not null
    group by i.roll_id having count(*)>1
  ) then
    raise exception 'AE_OPENING_ROLL_DUPLICATE_IN_DOCUMENT';
  end if;
  perform mr.id from erp.material_rolls mr
  where mr.id in(
    select i.roll_id from erp.opening_balance_items i
    where i.opening_id=h.id and i.roll_id is not null
  ) order by mr.id for update;
  for r in
    select i.*,m.material_type,
      mr.material_id as roll_material_id,
      mr.original_qty as roll_original_qty,
      mr.cached_qty as roll_cached_qty,
      mr.purchase_item_id as roll_purchase_item_id,
      mr.status as roll_status
    from erp.opening_balance_items i
    left join erp.materials m on m.id=i.material_id
    left join erp.material_rolls mr on mr.id=i.roll_id
    where i.opening_id=h.id and i.balance_type='MATERIAL'
    order by i.id
  loop
    if r.material_type='FABRIC' and r.roll_id is null then
      raise exception 'AE_FABRIC_OPENING_REQUIRES_ROLL';
    end if;
    if r.roll_id is not null then
      if r.material_type is distinct from 'FABRIC' then
        raise exception 'AE_OPENING_ROLL_REQUIRES_FABRIC';
      end if;
      if r.roll_material_id is distinct from r.material_id then
        raise exception 'AE_OPENING_ROLL_MATERIAL_MISMATCH';
      end if;
      if r.roll_status is distinct from 'AVAILABLE' then
        raise exception 'AE_OPENING_ROLL_NOT_AVAILABLE';
      end if;
      if r.roll_purchase_item_id is not null then
        raise exception 'AE_PURCHASE_ROLL_CANNOT_BE_OPENING_BALANCE';
      end if;
      if coalesce(r.qty,0)>r.roll_original_qty then
        raise exception 'AE_OPENING_QTY_EXCEEDS_ROLL_ORIGINAL';
      end if;
      if exists(
        select 1 from erp.opening_balance_items prior
        join erp.opening_balance_headers prior_h on prior_h.id=prior.opening_id
        where prior.roll_id=r.roll_id and prior_h.status='POSTED'
      ) then
        raise exception 'AE_OPENING_ROLL_ALREADY_POSTED';
      end if;
      if exists(select 1 from erp.material_stock_movements prior_m where prior_m.roll_id=r.roll_id)
         or coalesce(r.roll_cached_qty,0)<>0 then
        raise exception 'AE_OPENING_ROLL_HAS_EXISTING_STOCK_HISTORY';
      end if;
    end if;
  end loop;

  select count(*),(array_agg(id order by id))[1] into v_fg_count,v_default_fg_location from erp.locations where location_type='FG_WAREHOUSE' and is_active=true;"""

DIRTY_QUERY = """select count(*)::bigint
    from erp.opening_balance_items i
    join erp.opening_balance_headers h on h.id=i.opening_id and h.status='POSTED'
    left join erp.materials material on material.id=i.material_id
    left join erp.material_rolls roll on roll.id=i.roll_id
    where (i.roll_id is not null and i.balance_type<>'MATERIAL')
      or (i.balance_type='MATERIAL' and (
      (material.material_type='FABRIC' and i.roll_id is null)
      or (i.roll_id is not null and (
        material.material_type is distinct from 'FABRIC'
        or
        roll.material_id is distinct from i.material_id
        or roll.purchase_item_id is not null
        or i.qty>roll.original_qty
        or (select count(*) from erp.opening_balance_items other_i
            join erp.opening_balance_headers other_h on other_h.id=other_i.opening_id
            where other_h.status='POSTED' and other_i.balance_type='MATERIAL'
              and other_i.roll_id=i.roll_id)<>1
        or (select count(*) from erp.material_stock_movements opening_m
            where opening_m.roll_id=i.roll_id and opening_m.movement_type='OPENING'
              and opening_m.reversal_of_id is null)<>1
        or exists(select 1 from erp.material_stock_movements purchase_m
            where purchase_m.roll_id=i.roll_id and purchase_m.movement_type='PURCHASE'
              and purchase_m.reversal_of_id is null)
      ))
    ))"""

REPORT_SQL = """
  return query
  select 'V2620AE_OPENING_MATERIAL_ROLL_INTEGRITY'::text,'CRITICAL'::text,
    (%s),
    'Each posted opening roll must belong to one fabric line, enter once, and stay within original quantity'::text;
""" % DIRTY_QUERY


def sha(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def exact_replace(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise AssertionError((old[:120], source.count(old)))
    return source.replace(old, new, 1)


def replace_block(source: str, start_token: str, end_token: str, replacement: str) -> str:
    start = source.index(start_token)
    end = source.index(end_token, start) + len(end_token)
    return source[:start] + replacement + source[end:]


def ad_definitions() -> dict[str, str]:
    incoming = json.loads(ad_build.INPUT.read_text())
    rows = {row[0]: row for row in incoming["functions"]}
    definitions: dict[str, str] = {}
    for identity, expected_hash in zip(IDENTITIES, AD_HASHES, strict=True):
        definition = rows[identity][1]
        if identity == IDENTITIES[0]:
            definition = ad_build.exact_replace(
                definition,
                "h.opening_date::timestamptz",
                "(h.opening_date::timestamp at time zone 'Asia/Jakarta')",
            )
        else:
            definition = ad_build.exact_replace(
                definition, "\nend\n$function$", ad_build.CHECK_SQL + "\nend\n$function$"
            )
        if sha(definition) != expected_hash:
            raise AssertionError("AE_AD_FUNCTION_RECONSTRUCTION_MISMATCH:" + identity)
        definitions[identity] = definition
    return definitions


def expected_rows(functions: list[dict[str, object]], mode: str) -> str:
    rows = []
    for function in functions:
        if mode == "predecessor":
            values = (function["identity"], function["predecessor_sha256"], ACL)
            rows.append(f"('{values[0]}','{values[1]}',{values[2]})")
        elif mode == "installed":
            rows.append(
                f"('{function['identity']}','{function['predecessor_sha256']}',"
                f"'{function['installed_sha256']}',{ACL})"
            )
        elif mode == "restore":
            rows.append(f"('{function['identity']}','{function['predecessor_sha256']}')")
        else:
            raise AssertionError(mode)
    return ",\n    ".join(rows)


def build() -> dict[str, object]:
    if sha(AD_MIGRATION.read_bytes()) != AD_MIGRATION_SHA256:
        raise AssertionError("AE_AD_MIGRATION_BYTES_MISMATCH")
    if sha(AD_ROLLBACK.read_bytes()) != AD_ROLLBACK_SHA256:
        raise AssertionError("AE_AD_ROLLBACK_BYTES_MISMATCH")

    predecessor = ad_definitions()
    installed = {
        IDENTITIES[0]: exact_replace(predecessor[IDENTITIES[0]], POST_ANCHOR, POST_REPLACEMENT),
        IDENTITIES[1]: exact_replace(
            predecessor[IDENTITIES[1]], "\nend\n$function$", REPORT_SQL + "\nend\n$function$"
        ),
    }
    functions = [
        {
            "identity": identity,
            "predecessor_sha256": sha(predecessor[identity]),
            "installed_sha256": sha(installed[identity]),
            "owner": "postgres",
            "acl": [
                "authenticated=X/postgres",
                "postgres=X/postgres",
                "service_role=X/postgres",
            ],
        }
        for identity in IDENTITIES
    ]
    predecessor_values = expected_rows(functions, "predecessor")
    installed_values = expected_rows(functions, "installed")
    restore_values = expected_rows(functions, "restore")

    migration = AD_MIGRATION.read_text()
    migration = migration.replace("v2620ad", "v2620ae").replace("v2.6.20ad", VERSION).replace("AD_", "AE_")
    migration = exact_replace(
        migration,
        "-- CP6 AD: one canonical material-opening clock and its owner-report detector.\n"
        "-- Qualified AC native counterexamples: run 34963873816; no posted history rewrite.\n",
        "-- CP6 AE: one physical roll can enter opening stock once and never above its original quantity.\n"
        "-- Qualified AD comparison run 35016787895; no posted history rewrite.\n",
    )
    guard = f"""do $predecessor_v2620ae$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20ad')
     or exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or to_regclass('erp.cp6_v2620ae_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ad_rollback_capsule') is null then
    raise exception 'AE_REQUIRES_EXACT_AD_WITHOUT_AE_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations
        where name='erp_v2_6_20ad_cp6_opening_material_business_day')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260915113627'
         and name='erp_v2_6_20ad_cp6_opening_material_business_day'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
             ='{AD_MIGRATION_SHA256}')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260915113627')
     or (select count(*) from erp.cp6_v2620ad_rollback_capsule)<>2 then
    raise exception 'AE_REQUIRES_EXACT_AD_PLATFORM_CAPSULE';
  end if;
  for r in select * from(values
    {predecessor_values}
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'AE_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if ({DIRTY_QUERY})<>0 then
    raise exception 'AE_PREEXISTING_OPENING_ROLL_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620ae$;"""
    migration = replace_block(
        migration, "do $predecessor_v2620ae$", "$predecessor_v2620ae$;", guard
    )
    migration = exact_replace(
        migration,
        "like erp.cp6_v2620ab_rollback_capsule including all",
        "like erp.cp6_v2620ad_rollback_capsule including all",
    )
    canonical = f"""do $canonical_opening_v2620ae$
declare d text;anchor text;
begin
  select pg_get_functiondef('erp.post_opening_balance(uuid)'::regprocedure) into d;
  anchor:=$anchor${POST_ANCHOR}$anchor$;
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'AE_OPENING_GUARD_ANCHOR';
  end if;
  execute replace(d,anchor,$replacement${POST_REPLACEMENT}$replacement$);
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure) into d;
  anchor:=E'\\nend\\n$function$';
  if (length(d)-length(replace(d,anchor,'')))/length(anchor)<>1 then
    raise exception 'AE_REPORT_ANCHOR';
  end if;
  execute replace(d,anchor,$replacement${REPORT_SQL}
end
$function$$replacement$);
end
$canonical_opening_v2620ae$;"""
    migration = replace_block(
        migration, "do $canonical_opening_v2620ae$", "$canonical_opening_v2620ae$;", canonical
    )
    old_installed = ",\n    ".join(
        f"('{identity}','{old_hash}','{new_hash}',{ACL})"
        for identity, old_hash, new_hash in zip(
            IDENTITIES, ad_build.OLD_HASHES, AD_HASHES, strict=True
        )
    )
    migration = exact_replace(migration, old_installed, installed_values)
    migration = migration.replace("<>216", "<>217").replace("expected216", "expected217")
    migration = exact_replace(
        migration,
        "Canonical Jakarta material opening for direct and imported stock; report detects source timeline drift; posted history remains immutable",
        "One physical fabric roll enters opening stock once, within original quantity; invalid history makes owner reports not ready",
    )
    MIGRATION.write_text(migration)

    migration_hash = sha(migration)
    migration_no_newline_hash = sha(migration.removesuffix("\n"))
    rollback = AD_ROLLBACK.read_text()
    rollback = rollback.replace("v2620ad", "v2620ae").replace("v2.6.20ad", VERSION).replace("AD_", "AE_")
    rollback = exact_replace(
        rollback,
        "-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20ae -> exact AC.",
        "-- REVIEWED PRE-USE ROLLBACK: CP6 v2.6.20ae -> exact AD.",
    )
    platform_guard = f"""do $platform_guard_v2620ae$
begin
  if (select count(*) from supabase_migrations.schema_migrations where name='{NAME}')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='{STAMP}' and name='{NAME}'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
           in('{migration_hash}','{migration_no_newline_hash}'))
     or exists(select 1 from supabase_migrations.schema_migrations where version>'{STAMP}') then
    raise exception 'AE_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR';
  end if;
end
$platform_guard_v2620ae$;"""
    rollback = replace_block(
        rollback, "do $platform_guard_v2620ae$", "$platform_guard_v2620ae$;", platform_guard
    )
    restore_guard = f"""do $restore_guard_v2620ae$
declare r record;c record;v_table text;v_hash text;v_expected jsonb;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20ad')
     or not exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or exists(select 1 from erp.schema_migrations
       where version not in('v2.6.20ad','{VERSION}')
         and installed_at>(select installed_at from erp.schema_migrations where version='{VERSION}'))
     or (select count(*) from erp.cp6_v2620ae_rollback_capsule)<>2 then
    raise exception 'AE_ROLLBACK_MARKER_CAPSULE_OR_SUCCESSOR';
  end if;
  for r in select * from(values
    {installed_values}
  ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c from erp.cp6_v2620ae_rollback_capsule cap
    left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
    where cap.object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or c.definition_actual is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.installed_actual is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or c.installed_owner is distinct from 'postgres'
       or c.installed_acl is distinct from r.acl then
      raise exception 'AE_TRUSTED_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;
  select boundary_snapshot into v_expected from erp.cp6_v2620ae_rollback_capsule limit 1;
  if (select count(*) from (
       select relation.relname from pg_class relation
       join pg_namespace namespace on namespace.oid=relation.relnamespace
       where namespace.nspname='erp' and relation.relkind in('r','p')
         and relation.relname not in('schema_migrations','cp6_v2620ae_rollback_capsule')
     ) all_erp_tables)<>217
     or v_expected is null
     or (select count(*) from jsonb_object_keys(v_expected))<>217
     or exists(select 1 from erp.cp6_v2620ae_rollback_capsule
       where boundary_snapshot is distinct from v_expected) then
    raise exception 'AE_BOUNDARY_SNAPSHOT_MISMATCH';
  end if;
  for v_table in
    select relation.relname from pg_class relation
    join pg_namespace namespace on namespace.oid=relation.relnamespace
    where namespace.nspname='erp' and relation.relkind in('r','p')
      and relation.relname not in('schema_migrations','cp6_v2620ae_rollback_capsule')
    order by relation.relname
  loop
    execute format($q$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$q$,v_table) into v_hash;
    if v_hash is distinct from v_expected->>v_table then
      raise exception 'AE_POST_USE_ROLLBACK_REFUSED: %',v_table;
    end if;
  end loop;
  for c in select * from erp.cp6_v2620ae_rollback_capsule order by object_regidentity loop
    execute c.object_definition;
  end loop;
  for r in select * from(values
    {restore_values}
  ) expected(identity,sha256) loop
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'AE_ROLLBACK_RESTORE_HASH_MISMATCH: %',r.identity;
    end if;
  end loop;
end
$restore_guard_v2620ae$;"""
    rollback = replace_block(
        rollback, "do $restore_guard_v2620ae$", "$restore_guard_v2620ae$;", restore_guard
    )
    rollback = exact_replace(
        rollback,
        "where version='20260915113627'\n  and name='erp_v2_6_20ad_cp6_opening_material_business_day'",
        f"where version='{STAMP}'\n  and name='{NAME}'",
    )
    old_delete_hashes = (
        "in('cd4879eb9b053e3b7a975e1430f481131e377f260ece2f19f07bfb4c98498c1d',\n"
        "       '3fd50d662eff38f5c0c627798216a15eca9bc7cc559529be7d83fa2e9a0a3829')"
    )
    rollback = exact_replace(
        rollback,
        old_delete_hashes,
        f"in('{migration_hash}',\n       '{migration_no_newline_hash}')",
    )
    postcheck = f"""do $postcheck_v2620ae$
declare r record;v_actual text;
begin
  for r in select * from(values
    {predecessor_values}
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'AE_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or exists(select 1 from supabase_migrations.schema_migrations where name='{NAME}')
     or to_regclass('erp.cp6_v2620ae_rollback_capsule') is not null
     or not exists(select 1 from erp.schema_migrations where version='v2.6.20ad')
     or to_regclass('erp.cp6_v2620ad_rollback_capsule') is null then
    raise exception 'AE_ROLLBACK_POSTCONDITION_FAILED';
  end if;
end
$postcheck_v2620ae$;"""
    rollback = replace_block(
        rollback, "do $postcheck_v2620ae$", "$postcheck_v2620ae$;", postcheck
    )
    rollback = rollback.replace("<>216", "<>217").replace("expected216", "expected217")
    ROLLBACK.write_text(rollback)

    pins: dict[str, object] = {
        "format": "CP6_AE_RUNTIME_PINS_V1",
        "stamp": STAMP,
        "name": NAME,
        "version": VERSION,
        "predecessor_head": PREDECESSOR_HEAD,
        "predecessor_tree": PREDECESSOR_TREE,
        "functions": functions,
        "boundary_count": 217,
        "predecessor_function_count": 533,
        "predecessor_table_count": 219,
        "source_pins": {
            str(path): {"sha256": sha(path.read_bytes()), "bytes": path.stat().st_size}
            for path in (BUILDER, AD_MIGRATION, AD_ROLLBACK, MIGRATION, ROLLBACK)
        },
        "comparison_run": 35016787895,
        "production_go": False,
    }
    PINS.write_text(json.dumps(pins, indent=2) + "\n")
    print(json.dumps(pins, indent=2))
    return pins


if __name__ == "__main__":
    build()
