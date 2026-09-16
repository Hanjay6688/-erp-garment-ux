#!/usr/bin/env python3
"""AH: return eligibility follows its original allocation, receipt follows destination."""
from pathlib import Path
import json
import cp6_v2620ag_build_sql as ag

STAMP='20260916070451'
NAME='erp_v2_6_20ah_cp6_return_allocation_eligibility'
VERSION='v2.6.20ah'
PREDECESSOR_HEAD='119f8f133131eaf373f08cc45b7b3d6fc27a3d3e'
PREDECESSOR_TREE='bd7dd026d40e64f08f03e122338d8a82ebfd292c'
MIGRATION=Path(f'supabase/migrations/{STAMP}_{NAME}.sql')
ROLLBACK=Path(f'supabase/rollbacks/{STAMP}_{NAME}.rollback.sql')
PINS=Path('docs/evidence/cp6-ah-runtime-pins.json')
INPUT=Path('docs/evidence/cp6-ah-predecessor-functions.json')
CATALOG=Path('docs/evidence/cp6-ah-ag-catalog-pins.json')
BUILDER=Path(__file__).relative_to(Path.cwd())
IDENTITIES=('erp.normalize_sales_return_item_from_allocation()',
            'erp.post_sales_return(uuid)','erp.run_v268_financial_report_checks()')
sha,replace,block,rows=ag.sha,ag.replace,ag.block,ag.rows

# Posted return facts must bind the selected source allocation. A destination
# may differ from the original sale warehouse. Current HPP may change through
# linked recosting; this does not compare immutable snapshots to current cost.
DIRTY_QUERY="""with active_return as (
  select i.*,r.sale_id,r.customer_id,r.physical_at
  from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id
  where r.status='POSTED'
), live_movement as (
  select m.* from erp.fg_stock_movements m
  where m.source_type='SALES_RETURN_ITEM' and m.movement_type='SALE_RETURN'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)
)
select count(*)::bigint from (
  select i.id from active_return i
  left join erp.sale_stock_allocations a on a.id=i.sale_stock_allocation_id
  left join erp.sales_items si on si.id=a.sale_item_id
  left join erp.sales_headers s on s.id=si.sale_id
  where a.id is null or s.status is null or s.status not in('POSTED','PARTIAL_PAID','PAID')
    or i.sale_id is distinct from s.id or i.customer_id is distinct from s.customer_id
    or i.product_id is distinct from si.product_id or i.lot_id is distinct from a.lot_id
    or i.physical_at<s.sale_date
  union all
  select a.id from erp.sale_stock_allocations a join active_return i on i.sale_stock_allocation_id=a.id
  group by a.id,a.qty_pcs having sum(i.qty_pcs)>a.qty_pcs
  union all
  select m.id from live_movement m left join active_return i on i.id=m.source_id
  where i.id is null or m.product_id is distinct from i.product_id or m.lot_id is distinct from i.lot_id
    or m.location_id is distinct from i.location_id or m.quality_grade is distinct from i.quality_grade
    or m.customer_id is distinct from i.customer_id or m.physical_at is distinct from i.physical_at
    or m.qty_signed is distinct from i.qty_pcs
  union all
  select i.id from active_return i left join live_movement m on m.source_id=i.id
  group by i.id,i.qty_pcs having count(m.id)<>1 or sum(m.qty_signed) is distinct from i.qty_pcs::bigint
  union all
  select r.id from erp.sales_returns r where r.status='POSTED'
    and not exists(select 1 from erp.sales_return_items i where i.return_id=r.id)
) broken"""

DRAFT_SOURCE_QUERY="""select exists(
  select 1 from erp.sales_return_items ri
  join erp.sales_returns r on r.id=ri.return_id and r.status='DRAFT'
  join erp.sale_stock_allocations a on a.id=ri.sale_stock_allocation_id
  join erp.sales_items si on si.id=a.sale_item_id
  join erp.sales_headers s on s.id=si.sale_id
  where s.status='DRAFT'
)"""

def build():
    original=json.loads(INPUT.read_text())
    assert (original['head'],original['tree'])==(PREDECESSOR_HEAD,PREDECESSOR_TREE)
    src={r[0]:r for r in original['functions']};assert set(src)==set(IDENTITIES)
    prior=json.loads(ag.PINS.read_text())
    for p in (ag.MIGRATION,ag.ROLLBACK):assert sha(p.read_bytes())==prior['source_pins'][str(p)]['sha256']

    normal=src[IDENTITIES[0]][1]
    normal=replace(normal," LANGUAGE plpgsql\n SET search_path TO 'erp', 'public', 'pg_temp'", " LANGUAGE plpgsql\n SECURITY DEFINER\n SET search_path TO ''")
    normal=replace(normal,'  v_alloc_customer uuid;','  v_alloc_customer uuid;\n  v_alloc_status text;')
    normal=replace(normal,'begin\n  select sr.sale_id','begin\n  perform erp.require_internal();\n  select sr.sale_id')
    normal=replace(normal,'select si.sale_id,sh.customer_id,si.product_id,','select si.sale_id,sh.customer_id,sh.status,si.product_id,')
    normal=replace(normal,'into v_alloc_sale,v_alloc_customer,v_product,','into v_alloc_sale,v_alloc_customer,v_alloc_status,v_product,')
    normal=replace(normal,"  if v_alloc_sale is null then raise exception 'Original sale stock allocation not found'; end if;", "  if v_alloc_sale is null then raise exception 'Original sale stock allocation not found'; end if;\n  if v_alloc_status not in('POSTED','PARTIAL_PAID','PAID') then\n    raise exception 'AH_RETURN_SOURCE_MUST_BE_ACTIVE_POSTED_SALE';\n  end if;")

    post=src[IDENTITIES[1]][1]
    old="""    select coalesce(sum(a.qty_pcs),0)::integer,
           case when coalesce(sum(a.qty_pcs),0)>0 then sum(a.qty_pcs*a.unit_hpp_snapshot)/sum(a.qty_pcs) else null end
    into v_sold_qty,v_original_hpp
    from erp.sale_stock_allocations a
    join erp.sales_items si on si.id=a.sale_item_id
    where si.sale_id=h.sale_id and si.product_id=r.product_id and a.lot_id=r.lot_id and a.location_id=r.location_id;
    if v_sold_qty<=0 or v_original_hpp is null then raise exception 'Returned product/lot/location was not allocated on the original sale'; end if;"""
    new="""    -- Eligibility belongs to the selected allocation. Receipt destination is
    -- independently validated and may be another active FG warehouse.
    select a.qty_pcs,a.unit_hpp_snapshot into v_sold_qty,v_original_hpp
    from erp.sale_stock_allocations a join erp.sales_items si on si.id=a.sale_item_id
    where a.id=r.sale_stock_allocation_id and si.sale_id=h.sale_id
      and si.product_id=r.product_id and a.lot_id=r.lot_id;
    if v_sold_qty is null or v_sold_qty<=0 or v_original_hpp is null then
      raise exception 'AH_RETURN_ALLOCATION_SOURCE_MISMATCH';
    end if;"""
    post=replace(post,old,new)
    post=replace(post,"      and sri.product_id=r.product_id and sri.lot_id=r.lot_id and sri.location_id=r.location_id;", "      and sri.sale_stock_allocation_id=r.sale_stock_allocation_id;")
    post=replace(post,"    where sri.return_id=h.id and sri.product_id=r.product_id and sri.lot_id=r.lot_id and sri.location_id=r.location_id;", "    where sri.return_id=h.id and sri.sale_stock_allocation_id=r.sale_stock_allocation_id;")
    post=replace(post,"      raise exception 'Sales return exceeds quantity originally sold for this lot/location. Sold %, prior returned %, current return %'", "      raise exception 'AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION: Sales return exceeds quantity originally sold for this allocation. Sold %, prior returned %, current return %'")
    report=replace(src[IDENTITIES[2]][1],"\nend\n$function$", "\n  return query select 'V2620AH_RETURN_ALLOCATION_LINEAGE_MISMATCH'::text,'CRITICAL'::text,("+DIRTY_QUERY+"),'Active return quantities and receipt facts must match their selected original sale allocation and chosen destination'::text;\nend\n$function$")
    defs=[normal,post,report]
    functions=[dict(identity=i,predecessor_sha256=sha(src[i][1]),installed_sha256=sha(d),owner=src[i][3],acl=sorted(src[i][2].strip('{}').split(','))) for i,d in zip(IDENTITIES,defs,strict=True)]
    old_rows={m:rows(prior['functions'],m) for m in ('predecessor','installed','restore')}
    new_rows={m:rows(functions,m) for m in old_rows}

    def advance(sql):
        for old,tag in (('v2620ag','__AH_CAP__'),('v2.6.20ag','__AH_VER__'),('AG_','__AH_ERR__')):sql=sql.replace(old,tag)
        sql=sql.replace('v2620af','v2620ag').replace('v2.6.20af','v2.6.20ag')
        return sql.replace('__AH_CAP__','v2620ah').replace('__AH_VER__',VERSION).replace('__AH_ERR__','AH_').replace('<>219','<>220').replace('expected219','expected220')
    migration=advance(ag.MIGRATION.read_text());migration=migration[migration.index('begin;\n'):]
    migration='-- CP6 AH: original allocation eligibility and independent return destination.\n-- Posted history is unchanged; ordinary draft validation uses a confined private trigger.\n'+migration
    migration=replace(migration,"where p.oid in("+','.join("'"+i+"'::regprocedure" for i in ag.IDENTITIES)+");", "where p.oid in("+','.join("'"+i+"'::regprocedure" for i in IDENTITIES)+");")
    guard=f"""do $predecessor_v2620ah$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='{ag.VERSION}')
     or exists(select 1 from erp.schema_migrations where version='{VERSION}')
     or to_regclass('erp.cp6_v2620ah_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620ag_rollback_capsule') is null then raise exception 'AH_REQUIRES_EXACT_AG_WITHOUT_AH_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='{ag.NAME}')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='{ag.STAMP}' and name='{ag.NAME}'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')='{sha(ag.MIGRATION.read_bytes())}')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'{ag.STAMP}')
     or (select count(*) from erp.cp6_v2620ag_rollback_capsule)<>4 then raise exception 'AH_REQUIRES_EXACT_AG_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    {new_rows['predecessor']}
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AH_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
  if ({DIRTY_QUERY})<>0 then raise exception 'AH_PREEXISTING_RETURN_ALLOCATION_REVIEW_REQUIRED'; end if;
  if ({DRAFT_SOURCE_QUERY}) then raise exception 'AH_PREEXISTING_DRAFT_RETURN_SOURCE_REVIEW_REQUIRED'; end if;
end
$predecessor_v2620ah$;"""
    migration=block(migration,'do $predecessor_v2620ah$','$predecessor_v2620ah$;',guard)
    canonical='do $canonical_opening_v2620ah$\nbegin\n'+'\n'.join('  execute $definition$'+d+'$definition$;' for d in defs)+'\nend\n$canonical_opening_v2620ah$;'
    migration=block(migration,'do $canonical_opening_v2620ah$','$canonical_opening_v2620ah$;',canonical)
    migration=replace(migration,old_rows['installed'],new_rows['installed'])
    migration=migration.replace('(select count(*) from erp.cp6_v2620ah_rollback_capsule)<>4','(select count(*) from erp.cp6_v2620ah_rollback_capsule)<>3')
    migration=migration.replace('Reserved sale edits use the atomic draft RPC; posting and reports require exact source/stock lineage','Return allocation eligibility, destination and ordinary draft validation remain coherent')
    MIGRATION.write_text(migration)
    rollback=advance(ag.ROLLBACK.read_text()).replace('-> exact AF.','-> exact AG.')
    for mode in old_rows:
        if old_rows[mode] in rollback:rollback=replace(rollback,old_rows[mode],new_rows[mode])
    rollback=rollback.replace(ag.STAMP,STAMP).replace(ag.NAME,NAME)
    rollback=rollback.replace(sha(ag.MIGRATION.read_bytes()),sha(migration)).replace(sha(ag.MIGRATION.read_text().removesuffix('\n')),sha(migration.removesuffix('\n')))
    rollback=rollback.replace('(select count(*) from erp.cp6_v2620ah_rollback_capsule)<>4','(select count(*) from erp.cp6_v2620ah_rollback_capsule)<>3')
    ROLLBACK.write_text(rollback)
    pins=dict(format='CP6_AH_RUNTIME_PINS_V1',stamp=STAMP,name=NAME,version=VERSION,predecessor_head=PREDECESSOR_HEAD,predecessor_tree=PREDECESSOR_TREE,functions=functions,boundary_count=220,predecessor_function_count=533,predecessor_table_count=222,comparison_run=35066611261,production_go=False,source_pins={str(p):dict(sha256=sha(p.read_bytes()),bytes=p.stat().st_size) for p in (BUILDER,INPUT,CATALOG,ag.MIGRATION,ag.ROLLBACK,MIGRATION,ROLLBACK)})
    PINS.write_text(json.dumps(pins,indent=2)+'\n')
    print(json.dumps({'migration':sha(migration),'rollback':sha(rollback),'pins':sha(PINS.read_bytes())}));return pins

if __name__=='__main__':build()
