-- Standalone preparation only. No installer, public RPC or command admission.
create function cp7_global_nonpo_native_graph.scope_v1(p_root_sales uuid[]) returns jsonb
language plpgsql stable security definer set search_path='' set timezone='UTC' as $$
declare root_id uuid; graphs jsonb:='[]'; graph jsonb; sales uuid[]; answer jsonb;
begin
 if p_root_sales is null or cardinality(p_root_sales)=0 or array_position(p_root_sales,null) is not null
  or cardinality(p_root_sales)<>(select count(distinct x)from unnest(p_root_sales)x)then
  raise exception 'CP7_GLOBAL_NONPO_EXACT_NONEMPTY_ROOT_SET_REQUIRED';end if;
 for root_id in select x from unnest(p_root_sales)x order by x loop
  graph:=cp7_credit.consumer_dependency_graph_v1(root_id);
  graphs:=graphs||jsonb_build_array(graph);
 end loop;
 select array_agg(distinct x::uuid order by x::uuid)into sales
 from jsonb_array_elements(graphs)g cross join lateral jsonb_array_elements_text(g->'sale_ids')x;
 with recursive
 seed(kind,id)as(
  select 'LOT'::text,lot from unnest(sales)s cross join lateral unnest(cp7_credit.source_hpp_lot_ids_v1(s))lot
  union select 'PRODUCT',i.product_id from erp.sales_items i where i.sale_id=any(sales)
 ),
 forward_edges(ak,a,bk,b)as(
  select 'LOT'::text,l.id,'PRODUCT'::text,l.product_id from erp.fg_lots l
  union select 'LOT',l.id,'PO',l.po_id from erp.fg_lots l where l.po_id is not null
  union select 'LOT',l.id,'LOT',l.source_lot_id from erp.fg_lots l where l.source_lot_id is not null
  union select 'CONVERSION',c.id,'PRODUCT',c.from_product_id from erp.product_conversions c
  union select 'CONVERSION',c.id,'PRODUCT',c.to_product_id from erp.product_conversions c
  union select 'CONVERSION',a.conversion_id,'LOT',a.source_lot_id from erp.product_conversion_allocations a
  union select 'CONVERSION',a.conversion_id,'LOT',a.destination_lot_id from erp.product_conversion_allocations a where a.destination_lot_id is not null
  union select 'CONVERSION',s.conversion_id,'LOT',s.source_lot_id from erp.be_conversion_sources_v1 s
  union select 'JOURNAL',l.journal_entry_id,'PRODUCT',l.product_id from erp.journal_lines l where l.product_id is not null
  union select 'JOURNAL',l.journal_entry_id,'PO',l.po_id from erp.journal_lines l where l.po_id is not null
 ),edges(ak,a,bk,b)as(select *from forward_edges union select bk,b,ak,a from forward_edges),
 reachable(kind,id)as(select *from seed union select e.bk,e.b from reachable r join edges e on(e.ak,e.a)=(r.kind,r.id)),
 global_lots as(select *from erp.fg_lots where po_id is null),
 global_products as(select distinct product_id id from global_lots),
 global_conversions as(
  select c.id from erp.product_conversions c where c.from_product_id in(select id from global_products)or c.to_product_id in(select id from global_products)
  union select a.conversion_id from erp.product_conversion_allocations a where a.source_lot_id in(select id from global_lots)or a.destination_lot_id in(select id from global_lots)
  union select s.conversion_id from erp.be_conversion_sources_v1 s where s.source_lot_id in(select id from global_lots)
 ),outside_products as(select id from global_products except select id from reachable where kind='PRODUCT')
 select jsonb_build_object(
  'financial_sale_ids',to_jsonb(sales),'financial_graphs',graphs,
  'relevant',jsonb_build_object('lot_ids',coalesce((select jsonb_agg(id order by id)from reachable where kind='LOT'),'[]'),
   'product_ids',coalesce((select jsonb_agg(id order by id)from reachable where kind='PRODUCT'),'[]'),
   'po_ids',coalesce((select jsonb_agg(id order by id)from reachable where kind='PO'),'[]'),
   'conversion_ids',coalesce((select jsonb_agg(id order by id)from reachable where kind='CONVERSION'),'[]'),
   'journal_ids',coalesce((select jsonb_agg(id order by id)from reachable where kind='JOURNAL'),'[]')),
  'global',jsonb_build_object('all_nonpo_lot_ids',coalesce((select jsonb_agg(id order by id)from global_lots),'[]'),
   'propagation_lock_lot_ids',coalesce((select jsonb_agg(id order by id)from global_lots where lot_origin<>'VOIDED_PRODUCTION'),'[]'),
   'sync_product_ids',coalesce((select jsonb_agg(id order by id)from global_products),'[]'),
   'support_conversion_ids',coalesce((select jsonb_agg(id order by id)from global_conversions),'[]'),
   'transfer_allocation_ids',coalesce((select jsonb_agg(a.id order by a.id)from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'join global_lots l on l.id=a.source_lot_id),'[]'),
   'guard_be_source_ids',coalesce((select jsonb_agg(s.conversion_id order by s.conversion_id)from erp.be_conversion_sources_v1 s
    where s.source_lot_id in(select id from global_lots)),'[]')),
  'outside',jsonb_build_object('product_ids',coalesce((select jsonb_agg(id order by id)from outside_products),'[]'),
   'lot_ids',coalesce((select jsonb_agg(l.id order by l.id)from erp.fg_lots l where l.product_id in(select id from outside_products)),'[]')),
  'history_status_filters_used_for_identity_closure',false,'Native_visit_domains_are_separate_from_support_domain',true)into answer;
 return answer;
end $$;
alter function cp7_global_nonpo_native_graph.scope_v1(uuid[]) owner to postgres;
revoke all on function cp7_global_nonpo_native_graph.scope_v1(uuid[]) from public,anon,authenticated,service_role;
