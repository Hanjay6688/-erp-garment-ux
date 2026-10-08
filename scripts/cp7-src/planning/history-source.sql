-- One statement snapshot, one server clock, and the entire declared ERP scope.
-- Monetary columns never enter these operational source projections.
-- p_products bounds the current products read (one more is read so a larger
-- universe is INCOMPLETE, never cut). The single capture keeps 1000
-- (history_source below); the staged 5,000-target job passes its own bound.
create function cp7_planning.history_source_within(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC' as $$
with clock as materialized(select clock_timestamp()at),
-- K7: each root's first creation in one pass over every product (it was one
-- scan of the whole table per current product); same rows, same value.
established as materialized(
 select coalesce(p0.identity_root_id,p0.id)root_id,min(p0.created_at)established_at from erp.products p0 group by 1
),
products as materialized(
 select p.id,coalesce(p.identity_root_id,p.id)root_id,p.size_id,p.model_id,p.brand_id,
  p.sku,p.product_name,p.is_active,p.effective_from,p.effective_to,p.created_at,
  e.established_at,
  coalesce((select jsonb_agg(jsonb_build_object('sku_id',s.id,'sku',s.sku,'version_id',v.id,'revision',v.revision::text)order by v.id)
   from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
   join erp.bf_skus_v1 s on s.id=v.sku_id
   where m.product_root=coalesce(p.identity_root_id,p.id)and v.effective_from<=c.at
    and(v.effective_to is null or v.effective_to>c.at)),'[]')commercial
 from erp.products p cross join clock c join established e on e.root_id=coalesce(p.identity_root_id,p.id)
 where p.effective_from<=c.at and(p.effective_to is null or p.effective_to>c.at)
 order by coalesce(p.identity_root_id,p.id),p.id limit p_products+1
),
stock as materialized(
 select m.id,coalesce(p.identity_root_id,p.id)root_id,p.size_id,m.product_id,m.lot_id,m.location_id,
  m.quality_grade,m.qty_signed::text qty_signed,m.physical_at,m.system_created_at,
  m.movement_type,m.source_type,m.source_id,m.reversal_of_id,m.book_order
 from erp.fg_stock_movements m join erp.products p on p.id=m.product_id cross join clock c
 where coalesce(p.identity_root_id,p.id)in(select root_id from products)
  and m.physical_at<=c.at and m.system_created_at<=c.at order by m.id limit 50001
),
sales as materialized(
 select i.id,h.id sale_id,coalesce(p.identity_root_id,p.id)root_id,p.size_id,
  i.product_id,i.qty_pcs::text qty_pcs,h.status,h.row_version::text revision,
  h.sale_date,h.created_at,h.updated_at,
  coalesce((select jsonb_agg(jsonb_build_object('sku_id',s.id,'version_id',v.id,'revision',v.revision::text)order by v.id)
   from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
   join erp.bf_skus_v1 s on s.id=v.sku_id
   where m.product_root=coalesce(p.identity_root_id,p.id)and v.effective_from<=h.sale_date
    and(v.effective_to is null or v.effective_to>h.sale_date)),'[]')sold_commercial
 from erp.sales_items i join erp.sales_headers h on h.id=i.sale_id
 join erp.products p on p.id=i.product_id cross join clock c
 where coalesce(p.identity_root_id,p.id)in(select root_id from products)and h.created_at<=c.at
 order by i.id limit 50001
),
sale_journals as materialized(
 select j.id,j.source_id sale_id,j.status,j.posting_at,j.transaction_date,j.economic_date,j.reversal_of_id
 from erp.journal_entries j cross join clock c
 where(j.source_type='SALE'and j.source_id in(select sale_id from sales)
  or j.reversal_of_id in(select x.id from erp.journal_entries x
   where x.source_type='SALE'and x.source_id in(select sale_id from sales)))
  and j.posting_at<=c.at order by j.id limit 50001
),
returns as materialized(
 select ri.id,r.id return_id,r.sale_id,a.sale_item_id,ri.qty_pcs::text qty_pcs,
  r.status,r.physical_at,r.created_at
 from erp.sales_return_items ri join erp.sales_returns r on r.id=ri.return_id
 join erp.sale_stock_allocations a on a.id=ri.sale_stock_allocation_id cross join clock c
 where a.sale_item_id in(select id from sales)and r.created_at<=c.at order by ri.id limit 50001
),
return_journals as materialized(
 select j.id,j.source_id return_id,j.status,j.posting_at,j.transaction_date,j.economic_date,j.reversal_of_id
 from erp.journal_entries j cross join clock c
 where(j.source_type='SALES_RETURN'and j.source_id in(select return_id from returns)
  or j.reversal_of_id in(select x.id from erp.journal_entries x
   where x.source_type='SALES_RETURN'and x.source_id in(select return_id from returns)))
  and j.posting_at<=c.at order by j.id limit 50001
),
-- K7: built once (it was rebuilt for each later use of facts).
source as materialized(select jsonb_build_object(
 'products',coalesce((select jsonb_agg(to_jsonb(p)order by p.id)from products p),'[]'),
 'stock',coalesce((select jsonb_agg(to_jsonb(m)order by m.id)from stock m),'[]'),
 'sales',coalesce((select jsonb_agg(to_jsonb(s)order by s.id)from sales s),'[]'),
 'sale_journals',coalesce((select jsonb_agg(to_jsonb(j)order by j.id)from sale_journals j),'[]'),
 'returns',coalesce((select jsonb_agg(to_jsonb(r)order by r.id)from returns r),'[]'),
 'return_journals',coalesce((select jsonb_agg(to_jsonb(j)order by j.id)from return_journals j),'[]'))facts)
select jsonb_build_object('contract_version','cp7.native-demand-facts.v1',
 'captured_at',cp7_planning.utc(c.at),'scope','GLOBAL_CURRENT_PHYSICAL_ROOTS',
 'status',case when jsonb_array_length(facts->'products')<=p_products
  and not exists(select 1 from jsonb_each(facts)where key<>'products'and jsonb_array_length(value)>50000)
  and(select count(*)from products)=(select count(distinct root_id)from products)
  and not exists(select 1 from products where jsonb_array_length(commercial)>1)
  and not exists(select 1 from sales where jsonb_array_length(sold_commercial)>1)
  and not exists(select 1 from sales s left join(select j.sale_id,count(*)n from sale_journals j where j.reversal_of_id is null group by 1)k
   on k.sale_id=s.sale_id where s.status in('POSTED','PARTIAL_PAID','PAID','REVERSED')and coalesce(k.n,0)<>1)
 then 'COMPLETE'else 'INCOMPLETE'end,'facts',facts)from source cross join clock c
$$;
create function cp7_planning.history_source()returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC' as $$
 select cp7_planning.history_source_within(1000)
$$;

-- Translate immutable native posting/inverse instants, not the mutable current
-- invoice status, into the private lineage protocol. Returns stay separate
-- from gross demand. A later-known backdate cannot enter earlier training.
create function cp7_planning.history_events(c jsonb)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC' as $$
with sales as(select value s from jsonb_array_elements(c->'facts'->'sales')),
sj as(select value j from jsonb_array_elements(c->'facts'->'sale_journals')),
returns as(select value r from jsonb_array_elements(c->'facts'->'returns')),
rj as(select value j from jsonb_array_elements(c->'facts'->'return_journals')),
originals as materialized(
 select s,j from sales join sj on j->>'sale_id'=s->>'sale_id'and j->'reversal_of_id'='null'::jsonb
),
return_changes as(
 select o.s,o.j original_journal,r,rj.j,1 sign from originals o join returns on r->>'sale_item_id'=o.s->>'id'
 join rj on rj.j->>'return_id'=r->>'return_id'and rj.j->'reversal_of_id'='null'::jsonb
 union all
 select o.s,o.j,r,inverse.j,-1 from originals o join returns on r->>'sale_item_id'=o.s->>'id'
 join rj original on original.j->>'return_id'=r->>'return_id'and original.j->'reversal_of_id'='null'::jsonb
 join rj inverse on inverse.j->>'reversal_of_id'=original.j->>'id'
),
returned as(
 select s,original_journal,r,j,
  (1+row_number()over(partition by s->>'id'order by(j->>'posting_at')::timestamptz,j->>'id',r->>'id'))::text revision,
  sum(sign*(r->>'qty_pcs')::numeric)over(partition by s->>'id'order by(j->>'posting_at')::timestamptz,j->>'id',r->>'id'rows unbounded preceding)::text returned_pcs
 from return_changes
),
events as(
 select s,'1'::text revision,cp7_planning.utc((j->>'posting_at')::timestamptz)known_at,
  cp7_planning.utc((s->>'sale_date')::timestamptz)effective_at,'POSTED'::text status,
  cp7_planning.utc((s->>'sale_date')::timestamptz)posted_at,'0'::text returned_pcs,j->>'id'journal_id
 from originals
 union all
 select s,revision,cp7_planning.utc((j->>'posting_at')::timestamptz),
  cp7_planning.utc(greatest((s->>'sale_date')::timestamptz,(r->>'physical_at')::timestamptz)),
  'POSTED',cp7_planning.utc((s->>'sale_date')::timestamptz),returned_pcs,j->>'id'from returned
 union all
 select o.s,((select count(*)from return_changes x where x.s->>'id'=o.s->>'id')+2)::text,
  cp7_planning.utc((inverse.j->>'posting_at')::timestamptz),
  cp7_planning.utc(greatest((o.s->>'sale_date')::timestamptz,
   (inverse.j->>'transaction_date')::date::timestamp at time zone 'Asia/Jakarta')),
  'CANCELLED',null,'0',inverse.j->>'id'
 from originals o join sj inverse on inverse.j->>'reversal_of_id'=o.j->>'id'
 union all
 select s,s->>'revision',cp7_planning.utc((s->>'updated_at')::timestamptz),
  cp7_planning.utc((s->>'sale_date')::timestamptz),s->>'status',null,'0',null
 from sales where s->>'status'in('DRAFT','CANCELLED')and not exists(select 1 from originals o where o.s->>'id'=sales.s->>'id')
)
select coalesce(jsonb_agg(jsonb_build_object('lineage_key',s->>'id','revision',revision,
 'known_at',known_at,'effective_at',effective_at,'posted_at',posted_at,'status',status,
 'target_key',(s->>'root_id')||':'||(s->>'size_id'),'size_id',s->>'size_id',
 'sold_group_key',coalesce(s->'sold_commercial'->0->>'sku_id',s->>'root_id'),
 'qty_pcs',s->>'qty_pcs','returned_pcs',returned_pcs,
 'refs',jsonb_build_array(jsonb_build_object('kind','SALE_ITEM','id',s->>'id','revision',revision))||
  case when journal_id is null then '[]'::jsonb else jsonb_build_array(jsonb_build_object('kind','JOURNAL','id',journal_id,'revision','1'))end)
 order by s->>'id',revision::numeric),'[]')from events
$$;
