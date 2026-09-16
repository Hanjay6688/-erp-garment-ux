#!/usr/bin/env python3
"""Build the AF child-history repair from native AE definitions and its capsule.

The admitted AE SQL stays immutable. Native pg_get_functiondef hashes, owners,
ACLs, platform history and complete data boundaries bind this new SQL edge.
"""
from pathlib import Path
import hashlib
import json

import cp6_v2620ae_build_sql as ae

STAMP = "20260916014332"
NAME = "erp_v2_6_20af_cp6_posted_child_integrity"
VERSION = "v2.6.20af"
MIGRATION = Path(f"supabase/migrations/{STAMP}_{NAME}.sql")
ROLLBACK = Path(f"supabase/rollbacks/{STAMP}_{NAME}.rollback.sql")
PINS = Path("docs/evidence/cp6-af-runtime-pins.json")
INPUT = Path("docs/evidence/cp6-af-predecessor-functions.json")
BUILDER = Path(__file__).relative_to(Path.cwd())
PREDECESSOR_HEAD = "ce8e8ea5cdfab4b39ea7095c1b3bd1c8ab1f33d1"
PREDECESSOR_TREE = "738fab9caa9f1d9a66756f169b82f407f929a214"
IDENTITIES = ("erp.guard_child_by_parent_status()", "erp.run_v268_financial_report_checks()")

GUARD_BODY = """
declare
  v_parent_id uuid; v_old_id uuid; v_new_id uuid;
  v_status text; v_allowed text[];
begin
  -- Existing trusted server paths retain their existing authority. Ordinary
  -- callers must protect BOTH parents, even when the foreign key changes.
  if current_user in ('postgres','service_role','supabase_admin') then
    if TG_OP='DELETE' then return OLD; else return NEW; end if;
  end if;
  v_allowed:=string_to_array(TG_ARGV[2],',');
  if TG_OP in ('UPDATE','DELETE') then
    v_old_id:=nullif(to_jsonb(OLD)->>TG_ARGV[1],'')::uuid;
    if v_old_id is null then raise exception 'Missing parent reference for %',TG_TABLE_NAME; end if;
  end if;
  if TG_OP in ('INSERT','UPDATE') then
    v_new_id:=nullif(to_jsonb(NEW)->>TG_ARGV[1],'')::uuid;
    if v_new_id is null then raise exception 'Missing parent reference for %',TG_TABLE_NAME; end if;
  end if;
  -- SHARE also conflicts with a status-only NO KEY UPDATE. KEY SHARE would
  -- leave an insert-versus-post race. Keep both locks to transaction end.
  for v_parent_id in
    select distinct p.id from unnest(array[v_old_id,v_new_id]) p(id)
    where p.id is not null order by p.id
  loop
    v_status:=null;
    execute format('SELECT status::text FROM erp.%I WHERE id=$1 FOR SHARE',TG_ARGV[0])
      into v_status using v_parent_id;
    if v_status is null then raise exception 'Parent document not found for %',TG_TABLE_NAME; end if;
    if (v_status=any(v_allowed)) is not true then
      raise exception '% cannot be changed while parent % status is %',TG_TABLE_NAME,TG_ARGV[0],v_status;
    end if;
  end loop;
  if TG_OP='DELETE' then return OLD; else return NEW; end if;
end;
"""

# Reverse lineage checks start at immutable facts, not only at currently POSTED
# children. That is what the original move-to-draft counterexample escaped.
# Material input cost is immutable; current recosted valuation is NOT compared.
DIRTY_QUERY = """select count(*)::bigint from (
    select m.id
    from erp.material_stock_movements m
    left join erp.opening_balance_items i on i.id=m.source_id
    left join erp.opening_balance_headers h on h.id=i.opening_id
    where m.source_type='OPENING_BALANCE_ITEM' and m.movement_type='OPENING'
      and m.reversal_of_id is null and (
        h.status is distinct from 'POSTED' or i.balance_type is distinct from 'MATERIAL'
        or m.material_id is distinct from i.material_id
        or m.roll_id is distinct from i.roll_id or m.location_id is distinct from i.location_id
        or m.qty_signed is distinct from i.qty
        or m.input_unit_cost is distinct from i.unit_cost_snapshot)
    union all
    select m.id
    from erp.fg_stock_movements m
    left join erp.opening_balance_items i on i.id=m.source_id
    left join erp.opening_balance_headers h on h.id=i.opening_id
    where m.source_type='OPENING_BALANCE_ITEM' and m.movement_type='OPENING'
      and m.reversal_of_id is null and (
        h.status is distinct from 'POSTED' or i.balance_type is distinct from 'FINISHED_GOODS'
        or m.product_id is distinct from i.product_id or m.qty_signed is distinct from i.qty
        or (i.location_id is not null and m.location_id is distinct from i.location_id))
    union all
    select s.id
    from erp.opening_subledger_balances s
    left join erp.opening_balance_items i on i.id=s.opening_item_id
    left join erp.opening_balance_headers h on h.id=i.opening_id
    where h.status is distinct from 'POSTED'
      or i.balance_type is distinct from (s.party_type||'_'||s.direction)
      or s.original_amount is distinct from i.amount
    union all
    select h.id from erp.opening_balance_headers h
    where h.status='POSTED'
      and not exists(select 1 from erp.opening_balance_items i where i.opening_id=h.id)
    union all
    select e.id from erp.journal_entries e
    left join erp.opening_balance_headers h on h.id=e.source_id
    where e.source_type='OPENING_BALANCE' and e.reversal_of_id is null
      and h.status is distinct from 'POSTED'
    union all
    select h.id from erp.opening_balance_headers h
    cross join lateral (
      select coalesce(sum(greatest(coalesce(round(case
        when i.balance_type in('MATERIAL','FINISHED_GOODS') then i.qty*i.unit_cost_snapshot
        when i.balance_type='WIP' then coalesce(i.amount,coalesce(i.qty,0)*coalesce(i.unit_cost_snapshot,0))
        when i.balance_type in('CONTRACTOR_RECEIVABLE','CUSTOMER_RECEIVABLE','CASH_BANK') then i.amount
        else 0 end,2),0),0)),0) debits,
        coalesce(sum(greatest(coalesce(round(case
        when i.balance_type in('CONTRACTOR_PAYABLE','VENDOR_PAYABLE','SUPPLIER_PAYABLE') then i.amount
        else 0 end,2),0),0)),0) credits
      from erp.opening_balance_items i where i.opening_id=h.id
    ) expected
    cross join lateral (
      select coalesce(sum(l.debit),0) debits,coalesce(sum(l.credit),0) credits
      from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id
      where e.source_type='OPENING_BALANCE' and e.source_id=h.id and e.reversal_of_id is null
    ) actual
    where h.status='POSTED' and (
      actual.debits<>greatest(expected.debits,expected.credits)
      or actual.credits<>greatest(expected.debits,expected.credits))
  ) broken_opening_lineage"""

REPORT_SQL = """
  return query
  select 'V2620AF_OPENING_SOURCE_LINEAGE_MISMATCH'::text,'CRITICAL'::text,
    (%s),
    'Opening stock and subledger facts require their original posted source with conserved quantity and input value'::text;
""" % DIRTY_QUERY

sha = ae.sha
replace = ae.exact_replace
block = ae.replace_block


def rows(functions, mode):
    result = []
    for f in functions:
        acl = "array[" + ",".join("'"+a+"'" for a in f["acl"]) + "]::text[]"
        values = ["'"+f["identity"]+"'", "'"+f["predecessor_sha256"]+"'"]
        if mode == "installed":
            values.append("'"+f["installed_sha256"]+"'")
        if mode != "restore":
            values.append(acl)
        result.append("("+",".join(values)+")")
    return ",\n    ".join(result)


def build():
    prior_pins = json.loads(ae.PINS.read_text())
    for path in (ae.MIGRATION, ae.ROLLBACK):
        assert sha(path.read_bytes()) == prior_pins["source_pins"][str(path)]["sha256"]
    source = json.loads(INPUT.read_text())
    assert (source["head"], source["tree"]) == (PREDECESSOR_HEAD, PREDECESSOR_TREE)
    predecessors = {r[0]: r for r in source["functions"]}
    assert set(predecessors) == set(IDENTITIES)
    guard = predecessors[IDENTITIES[0]][1]
    opening_delimiter = "AS $function$"
    installed_guard = guard[:guard.index(opening_delimiter)+len(opening_delimiter)] + GUARD_BODY + "$function$\n"
    installed_report = replace(predecessors[IDENTITIES[1]][1], "\nend\n$function$", REPORT_SQL+"\nend\n$function$")
    definitions = (installed_guard, installed_report)
    functions = []
    for identity, definition in zip(IDENTITIES, definitions, strict=True):
        row = predecessors[identity]
        assert row[3] == "postgres"
        functions.append(dict(identity=identity, predecessor_sha256=sha(row[1]),
                              installed_sha256=sha(definition), owner=row[3],
                              acl=sorted(row[2].strip("{}").split(","))))
    prior_rows = {mode: rows(prior_pins["functions"], mode) for mode in ("predecessor","installed","restore")}
    new_rows = {mode: rows(functions, mode) for mode in prior_rows}

    def advance(sql):
        # Placeholders avoid cascading successor/predecessor renames.
        for old, tag in (("v2620ae","__AF_CAP__"),("v2.6.20ae","__AF_VER__"),("AE_","__AF_ERR__")):
            sql=sql.replace(old,tag)
        sql=sql.replace("v2620ad","v2620ae").replace("v2.6.20ad","v2.6.20ae")
        sql=sql.replace("__AF_CAP__","v2620af").replace("__AF_VER__",VERSION).replace("__AF_ERR__","AF_")
        return sql.replace("<>217","<>218").replace("expected217","expected218")

    migration = advance(ae.MIGRATION.read_text())
    migration = migration[migration.index("begin;\n"):]
    migration = "-- CP6 AF: preserve both ends of posted child lineage and serialize status changes.\n-- Original AE native comparison: run 35044505762. No posted history rewrite.\n"+migration
    migration = replace(migration, "where p.oid in('erp.post_opening_balance(uuid)'::regprocedure,'erp.run_v268_financial_report_checks()'::regprocedure)",
                        "where p.oid in('erp.guard_child_by_parent_status()'::regprocedure,'erp.run_v268_financial_report_checks()'::regprocedure)")
    predecessor_guard = f"""do $predecessor_v2620af$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='{ae.VERSION}')
     or exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or to_regclass('erp.cp6_v2620af_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ae_rollback_capsule') is null then
    raise exception 'AF_REQUIRES_EXACT_AE_WITHOUT_AF_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='{ae.NAME}')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='{ae.STAMP}' and name='{ae.NAME}'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')='{sha(ae.MIGRATION.read_bytes())}')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'{ae.STAMP}')
     or (select count(*) from erp.cp6_v2620ae_rollback_capsule)<>2 then
    raise exception 'AF_REQUIRES_EXACT_AE_PLATFORM_CAPSULE';
  end if;
  for r in select * from(values
    {new_rows['predecessor']}
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex')
    into v_actual from pg_proc p where p.oid=to_regprocedure(r.identity)
      and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then
      raise exception 'AF_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if ({DIRTY_QUERY})<>0 then raise exception 'AF_PREEXISTING_OPENING_LINEAGE_REVIEW_REQUIRED'; end if;
end
$predecessor_v2620af$;"""
    migration=block(migration,"do $predecessor_v2620af$","$predecessor_v2620af$;",predecessor_guard)
    canonical = "do $canonical_opening_v2620af$\nbegin\n" + "\n".join(
        "  execute $definition$"+definition+"$definition$;" for definition in definitions
    ) + "\nend\n$canonical_opening_v2620af$;"
    migration=block(migration,"do $canonical_opening_v2620af$","$canonical_opening_v2620af$;",canonical)
    migration=replace(migration,prior_rows["installed"],new_rows["installed"])
    migration=replace(migration,"One physical fabric roll enters opening stock once, within original quantity; invalid history makes owner reports not ready",
                      "Posted child origin and destination remain immutable; parent status is locked; orphan opening source facts block reports")
    MIGRATION.write_text(migration)

    rollback=advance(ae.ROLLBACK.read_text())
    rollback=rollback.replace("-> exact AD.","-> exact AE.")
    for mode in prior_rows:
        if prior_rows[mode] in rollback:
            rollback=replace(rollback,prior_rows[mode],new_rows[mode])
    rollback=rollback.replace(ae.STAMP, STAMP).replace(ae.NAME,NAME)
    rollback=rollback.replace(sha(ae.MIGRATION.read_bytes()),sha(migration))
    rollback=rollback.replace(sha(ae.MIGRATION.read_text().removesuffix("\n")),sha(migration.removesuffix("\n")))
    ROLLBACK.write_text(rollback)
    pins=dict(format="CP6_AF_RUNTIME_PINS_V1",stamp=STAMP,name=NAME,version=VERSION,
              predecessor_head=PREDECESSOR_HEAD,predecessor_tree=PREDECESSOR_TREE,
              functions=functions,boundary_count=218,predecessor_function_count=533,
              predecessor_table_count=220,comparison_run=35044505762,production_go=False,
              source_pins={str(p):dict(sha256=sha(p.read_bytes()),bytes=p.stat().st_size)
                           for p in (BUILDER,INPUT,ae.MIGRATION,ae.ROLLBACK,MIGRATION,ROLLBACK)})
    PINS.write_text(json.dumps(pins,indent=2)+"\n")
    print(json.dumps({"migration":sha(migration),"rollback":sha(rollback),"pins":sha(PINS.read_bytes())}))
    return pins


if __name__ == "__main__":
    build()
