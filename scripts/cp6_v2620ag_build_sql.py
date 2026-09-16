#!/usr/bin/env python3
"""AG: bind sale drafts to their reservations; preserve all admitted SQL."""
from pathlib import Path
import json
import cp6_v2620af_build_sql as af

STAMP='20260916050822'
NAME='erp_v2_6_20ag_cp6_sale_reservation_lineage'
VERSION='v2.6.20ag'
PREDECESSOR_HEAD='f46699865501b03f9fba3a8b188f3fd01eedf404'
PREDECESSOR_TREE='f4dad6a6bccfffa1ba01f542cac36ac1d100c63f'
MIGRATION=Path(f'supabase/migrations/{STAMP}_{NAME}.sql')
ROLLBACK=Path(f'supabase/rollbacks/{STAMP}_{NAME}.rollback.sql')
PINS=Path('docs/evidence/cp6-ag-runtime-pins.json')
INPUT=Path('docs/evidence/cp6-ag-predecessor-functions.json')
CATALOG=Path('docs/evidence/cp6-ag-af-catalog-pins.json')
BUILDER=Path(__file__).relative_to(Path.cwd())
IDENTITIES=('erp.guard_child_by_parent_status()','erp.guard_posted_document()',
            'erp.post_sale(uuid)','erp.run_v268_financial_report_checks()')
sha,replace,block,rows=af.sha,af.replace,af.block,af.rows

# Active reservations/sales must match their source, including per-lot quantity.
# Reversed reserves from legal RPC edits retain history but are not active.
# A reversed sale keeps its allocation history; returns keep original sale qty.
DIRTY_QUERY="""with active as (
  select m.* from erp.fg_stock_movements m
  where m.source_type='SALE_ITEM' and m.movement_type in('SALE_RESERVE','SALE')
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)
), allocations as (
  select a.sale_item_id,a.lot_id,a.location_id,sum(a.qty_pcs)::bigint qty
  from erp.sale_stock_allocations a group by a.sale_item_id,a.lot_id,a.location_id
), movements as (
  select m.source_id sale_item_id,m.lot_id,m.location_id,sum(-m.qty_signed)::bigint qty
  from active m group by m.source_id,m.lot_id,m.location_id
)
select count(*)::bigint from (
  select m.id,sh_lineage.id sale_id from active m
  left join erp.sales_items i on i.id=m.source_id
  left join erp.sales_headers sh_lineage on sh_lineage.id=i.sale_id
  left join erp.fg_lots l on l.id=m.lot_id
  where sh_lineage.status is null or sh_lineage.status not in('DRAFT','POSTED','PARTIAL_PAID','PAID')
    or m.movement_type is distinct from case when sh_lineage.status='DRAFT' then 'SALE_RESERVE' else 'SALE' end
    or m.product_id is distinct from i.product_id or l.product_id is distinct from i.product_id
    or m.location_id is distinct from sh_lineage.source_location_id
    or m.customer_id is distinct from sh_lineage.customer_id or m.physical_at is distinct from sh_lineage.sale_date
    or m.quality_grade is distinct from 'GRADE_A' or m.qty_signed>=0
  union all
  select a.id,sh_lineage.id from erp.sale_stock_allocations a
  left join erp.sales_items i on i.id=a.sale_item_id
  left join erp.sales_headers sh_lineage on sh_lineage.id=i.sale_id
  left join erp.fg_lots l on l.id=a.lot_id
  where sh_lineage.status is null or sh_lineage.status not in('DRAFT','POSTED','PARTIAL_PAID','PAID','REVERSED')
    or l.product_id is distinct from i.product_id
    or a.location_id is distinct from sh_lineage.source_location_id or a.qty_pcs<=0
  union all
  select i.id,sh_lineage.id from allocations a full join movements m using(sale_item_id,lot_id,location_id)
  join erp.sales_items i on i.id=coalesce(a.sale_item_id,m.sale_item_id)
  join erp.sales_headers sh_lineage on sh_lineage.id=i.sale_id
  where sh_lineage.status in('DRAFT','POSTED','PARTIAL_PAID','PAID') and a.qty is distinct from m.qty
  union all
  select i.id,sh_lineage.id from erp.sales_items i join erp.sales_headers sh_lineage on sh_lineage.id=i.sale_id
  where (sh_lineage.status in('POSTED','PARTIAL_PAID','PAID') or
    (sh_lineage.status='DRAFT' and (exists(select 1 from erp.sale_stock_allocations a
       join erp.sales_items sibling on sibling.id=a.sale_item_id where sibling.sale_id=sh_lineage.id)
      or exists(select 1 from active m join erp.sales_items sibling on sibling.id=m.source_id where sibling.sale_id=sh_lineage.id))))
    and (i.qty_pcs is distinct from (select coalesce(sum(a.qty_pcs),0) from erp.sale_stock_allocations a where a.sale_item_id=i.id)
      or i.qty_pcs is distinct from (select coalesce(sum(-m.qty_signed),0) from active m where m.source_id=i.id))
  union all
  select sh_lineage.id,sh_lineage.id from erp.sales_headers sh_lineage where sh_lineage.status in('POSTED','PARTIAL_PAID','PAID')
    and not exists(select 1 from erp.sales_items i where i.sale_id=sh_lineage.id)
) broken where /*SCOPE*/true"""

CHILD_GUARD="""
  -- AF already locks both parents through transaction end. Examine dependent
  -- facts only after those locks, so a concurrent official save cannot race.
  if TG_TABLE_NAME='sales_items' then
    if TG_OP<>'UPDATE' or
       (to_jsonb(NEW)->'id',to_jsonb(NEW)->'sale_id',to_jsonb(NEW)->'product_id',to_jsonb(NEW)->'qty_pcs')
       is distinct from
       (to_jsonb(OLD)->'id',to_jsonb(OLD)->'sale_id',to_jsonb(OLD)->'product_id',to_jsonb(OLD)->'qty_pcs') then
      if exists(select 1 from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
           where i.sale_id=any(array[v_old_id,v_new_id]))
         or exists(select 1 from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
           where i.sale_id=any(array[v_old_id,v_new_id]) and m.source_type='SALE_ITEM'
             and m.movement_type in('SALE_RESERVE','SALE')
             and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)) then
        raise exception 'AG_RESERVED_SALE_EDIT_REQUIRES_SAVE_RPC: edit all lines through save_sale_draft_v2';
      end if;
    end if;
  end if;
"""
HEADER_GUARD="""
  -- Ordinary header writes already hold the row lock. Server RPCs above use
  -- release/rebuild or cancellation atomically under that same header lock.
  IF TG_TABLE_NAME='sales_headers' AND TG_OP IN('UPDATE','DELETE') THEN
    IF TG_OP='DELETE' OR
       (to_jsonb(NEW)->'id',to_jsonb(NEW)->'customer_id',to_jsonb(NEW)->'source_location_id',to_jsonb(NEW)->'sale_date')
       IS DISTINCT FROM
       (to_jsonb(OLD)->'id',to_jsonb(OLD)->'customer_id',to_jsonb(OLD)->'source_location_id',to_jsonb(OLD)->'sale_date') THEN
      IF EXISTS(SELECT 1 FROM erp.sale_stock_allocations a JOIN erp.sales_items i ON i.id=a.sale_item_id WHERE i.sale_id=OLD.id)
         OR EXISTS(SELECT 1 FROM erp.fg_stock_movements m JOIN erp.sales_items i ON i.id=m.source_id
           WHERE i.sale_id=OLD.id AND m.source_type='SALE_ITEM' AND m.movement_type IN('SALE_RESERVE','SALE')
             AND NOT EXISTS(SELECT 1 FROM erp.fg_stock_movements rv WHERE rv.reversal_of_id=m.id)) THEN
        RAISE EXCEPTION 'AG_RESERVED_SALE_EDIT_REQUIRES_SAVE_RPC: use save_sale_draft_v2 or cancel_sale_draft_v2';
      END IF;
    END IF;
  END IF;
"""

def build():
    original=json.loads(INPUT.read_text());assert (original['head'],original['tree'])==(PREDECESSOR_HEAD,PREDECESSOR_TREE)
    src={r[0]:r for r in original['functions']};assert set(src)==set(IDENTITIES)
    prior=json.loads(af.PINS.read_text())
    for p in (af.MIGRATION,af.ROLLBACK):assert sha(p.read_bytes())==prior['source_pins'][str(p)]['sha256']
    child=replace(src[IDENTITIES[0]][1],"  if TG_OP='DELETE' then return OLD; else return NEW; end if;\nend;",CHILD_GUARD+"  if TG_OP='DELETE' then return OLD; else return NEW; end if;\nend;")
    header=replace(src[IDENTITIES[1]][1],"\n  IF TG_OP='INSERT' THEN",HEADER_GUARD+"\n  IF TG_OP='INSERT' THEN")
    post_dirty=DIRTY_QUERY.replace('/*SCOPE*/true','broken.sale_id=h.id')
    post_dirty=replace(post_dirty,"where m.source_type='SALE_ITEM'", "where exists(select 1 from erp.sales_items scope_item where scope_item.id=m.source_id and scope_item.sale_id=h.id) and m.source_type='SALE_ITEM'")
    post_dirty=replace(post_dirty,'from erp.sale_stock_allocations a group by','from erp.sale_stock_allocations a where exists(select 1 from erp.sales_items scope_item where scope_item.id=a.sale_item_id and scope_item.sale_id=h.id) group by')
    post=replace(src[IDENTITIES[2]][1],"  ) then raise exception 'Sale allocation does not match Draft line quantity'; end if;",
      "  ) then raise exception 'Sale allocation does not match Draft line quantity'; end if;\n\n  if ("+post_dirty+")<>0 then\n    raise exception 'AG_SALE_RESERVATION_LINEAGE_MISMATCH';\n  end if;")
    report=replace(src[IDENTITIES[3]][1],"\nend\n$function$","\n  return query select 'V2620AG_SALE_RESERVATION_LINEAGE_MISMATCH'::text,'CRITICAL'::text,("+DIRTY_QUERY+"),'Sale source and reserved or posted stock must agree on item, lot, quantity, location, customer and physical time'::text;\nend\n$function$")
    defs=[child,header,post,report]
    functions=[dict(identity=i,predecessor_sha256=sha(src[i][1]),installed_sha256=sha(d),owner=src[i][3],acl=sorted(src[i][2].strip('{}').split(','))) for i,d in zip(IDENTITIES,defs,strict=True)]
    old_rows={m:rows(prior['functions'],m) for m in ('predecessor','installed','restore')};new_rows={m:rows(functions,m) for m in old_rows}
    def advance(sql):
        for old,tag in (('v2620af','__AG_CAP__'),('v2.6.20af','__AG_VER__'),('AF_','__AG_ERR__')):sql=sql.replace(old,tag)
        sql=sql.replace('v2620ae','v2620af').replace('v2.6.20ae','v2.6.20af')
        return sql.replace('__AG_CAP__','v2620ag').replace('__AG_VER__',VERSION).replace('__AG_ERR__','AG_').replace('<>218','<>219').replace('expected218','expected219')
    migration=advance(af.MIGRATION.read_text());migration=migration[migration.index('begin;\n'):]
    migration='-- CP6 AG: preserve sale draft/reservation lineage across every normal entry point.\n-- Original AF counterexample run 35058065869; posted history remains immutable.\n'+migration
    capture="where p.oid in("+','.join("'"+i+"'::regprocedure" for i in IDENTITIES)+");"
    old_capture="where p.oid in('erp.guard_child_by_parent_status()'::regprocedure,'erp.run_v268_financial_report_checks()'::regprocedure);"
    migration=replace(migration,old_capture,capture)
    guard=f"""do $predecessor_v2620ag$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='{af.VERSION}')
     or exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or to_regclass('erp.cp6_v2620ag_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620af_rollback_capsule') is null then raise exception 'AG_REQUIRES_EXACT_AF_WITHOUT_AG_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='{af.NAME}')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='{af.STAMP}' and name='{af.NAME}'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')='{sha(af.MIGRATION.read_bytes())}')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'{af.STAMP}')
     or (select count(*) from erp.cp6_v2620af_rollback_capsule)<>2 then raise exception 'AG_REQUIRES_EXACT_AF_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    {new_rows['predecessor']}
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AG_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
  if ({DIRTY_QUERY})<>0 then raise exception 'AG_PREEXISTING_SALE_LINEAGE_REVIEW_REQUIRED'; end if;
end
$predecessor_v2620ag$;"""
    migration=block(migration,'do $predecessor_v2620ag$','$predecessor_v2620ag$;',guard)
    canonical='do $canonical_opening_v2620ag$\nbegin\n'+'\n'.join('  execute $definition$'+d+'$definition$;' for d in defs)+'\nend\n$canonical_opening_v2620ag$;'
    migration=block(migration,'do $canonical_opening_v2620ag$','$canonical_opening_v2620ag$;',canonical)
    migration=replace(migration,old_rows['installed'],new_rows['installed'])
    migration=migration.replace("(select count(*) from erp.cp6_v2620ag_rollback_capsule)<>2","(select count(*) from erp.cp6_v2620ag_rollback_capsule)<>4")
    migration=migration.replace('Posted child origin and destination remain immutable; parent status is locked; orphan opening source facts block reports','Reserved sale edits use the atomic draft RPC; posting and reports require exact source/stock lineage')
    MIGRATION.write_text(migration)
    rollback=advance(af.ROLLBACK.read_text()).replace('-> exact AE.','-> exact AF.')
    for mode in old_rows:
        if old_rows[mode] in rollback:rollback=replace(rollback,old_rows[mode],new_rows[mode])
    rollback=rollback.replace(af.STAMP,STAMP).replace(af.NAME,NAME)
    rollback=rollback.replace(sha(af.MIGRATION.read_bytes()),sha(migration)).replace(sha(af.MIGRATION.read_text().removesuffix('\n')),sha(migration.removesuffix('\n')))
    rollback=rollback.replace('(select count(*) from erp.cp6_v2620ag_rollback_capsule)<>2','(select count(*) from erp.cp6_v2620ag_rollback_capsule)<>4')
    ROLLBACK.write_text(rollback)
    pins=dict(format='CP6_AG_RUNTIME_PINS_V1',stamp=STAMP,name=NAME,version=VERSION,predecessor_head=PREDECESSOR_HEAD,predecessor_tree=PREDECESSOR_TREE,functions=functions,boundary_count=219,predecessor_function_count=533,predecessor_table_count=221,comparison_run=35058065869,production_go=False,source_pins={str(p):dict(sha256=sha(p.read_bytes()),bytes=p.stat().st_size) for p in (BUILDER,INPUT,CATALOG,af.MIGRATION,af.ROLLBACK,MIGRATION,ROLLBACK)})
    PINS.write_text(json.dumps(pins,indent=2)+'\n');print(json.dumps({'migration':sha(migration),'rollback':sha(rollback),'pins':sha(PINS.read_bytes())}));return pins

if __name__=='__main__':build()
