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
  -- Documentary identity is independent of nullable journal dimensions/status.
  union select 'CONVERSION',s.conversion_id,'BC_DOCUMENT',s.document_id from erp.be_conversion_cost_sources_v1 s
  union select 'COST_EVENT',e.id,'BC_DOCUMENT',e.document_id from erp.be_conversion_cost_events_v1 e
  union select 'COST_EVENT',e.id,'ADJUSTMENT',e.adjustment_id from erp.be_conversion_cost_events_v1 e
  union select 'COST_EVENT',e.id,'JOURNAL',e.journal_id from erp.be_conversion_cost_events_v1 e
  union select 'TRANSFER_EVENT',e.id,'CONVERSION',e.conversion_id from erp.be_nonpo_transfer_events_v1 e
  union select 'TRANSFER_EVENT',e.id,'JOURNAL',e.journal_id from erp.be_nonpo_transfer_events_v1 e
  union select 'CONVERSION',r.conversion_id,'RETURN_OUTSTANDING',r.outstanding_id from erp.be_conversion_returns_v1 r
  union select 'RETURN_OUTSTANDING',r.id,'BC_DOCUMENT',r.document_id from erp.bc_outstanding_returns_v1 r where r.document_id is not null
  union select 'RETURN_LOT',l.id,'RETURN_OUTSTANDING',l.outstanding_id from erp.bc_return_lots_v1 l where l.outstanding_id is not null
  union select 'RETURN_LOT',l.id,'BC_DOCUMENT',l.document_id from erp.bc_return_lots_v1 l where l.document_id is not null
  union select 'RETURN_LOT',l.id,'RETURN_LOT',l.parent_lot_id from erp.bc_return_lots_v1 l where l.parent_lot_id is not null
  union select 'RETURN_LOT',l.id,'RETURN_EVENT',l.parent_event_id from erp.bc_return_lots_v1 l where l.parent_event_id is not null
  union select 'RETURN_EVENT',e.id,'RETURN_LOT',e.lot_id from erp.bc_lot_events_v1 e
  union select 'RETURN_EVENT',e.id,'BC_DOCUMENT',e.document_id from erp.bc_lot_events_v1 e
  union select 'ADJUSTMENT',p.adjustment_id,'BC_DOCUMENT',p.document_id from erp.bc_adjustment_purposes_v1 p
  -- Kind-qualified fact IDs connect shared documents without an account/category hub.
  union select 'BC_DOCUMENT',l.document_id,case l.link_kind when 'JOURNAL'then'JOURNAL'when'ADJUSTMENT'then'ADJUSTMENT'
    else'BC_LINK_'||l.link_kind end,l.link_id from erp.bc_document_links_v1 l
  union select 'JOURNAL',l.journal_entry_id,'PRODUCT',l.product_id from erp.journal_lines l where l.product_id is not null
  union select 'JOURNAL',l.journal_entry_id,'PO',l.po_id from erp.journal_lines l where l.po_id is not null
  union select 'JOURNAL',j.id,'JOURNAL',j.reversal_of_id from erp.journal_entries j where j.reversal_of_id is not null
  union select 'JOURNAL',j.id,'CONVERSION',j.source_id from erp.journal_entries j where j.source_type='PRODUCT_CONVERSION'and j.source_id is not null
  union select 'JOURNAL',j.id,'COST_EVENT',j.source_id from erp.journal_entries j where j.source_type='BE_CONVERSION_SOURCED_COST'and j.source_id is not null
  union select 'JOURNAL',j.id,'TRANSFER_EVENT',j.source_id from erp.journal_entries j where j.source_type='BE_NONPO_CONVERSION_RECOST'and j.source_id is not null
  union select 'HPP_SYNC_EVENT',e.id,'PRODUCT',e.product_id from erp.non_po_hpp_gl_sync_events_v2620f e
  union select 'HPP_SYNC_EVENT',e.id,'JOURNAL',e.journal_entry_id from erp.non_po_hpp_gl_sync_events_v2620f e
 ),edges(ak,a,bk,b)as(select *from forward_edges where a is not null and b is not null
   union select bk,b,ak,a from forward_edges where a is not null and b is not null),
 relevant(kind,id)as(select *from seed union select e.bk,e.b from relevant r join edges e on(e.ak,e.a)=(r.kind,r.id)),
 global_lots as(select *from erp.fg_lots where po_id is null),
 global_products as(select distinct product_id id from global_lots),
 global_conversions as(
  select c.id from erp.product_conversions c where c.from_product_id in(select id from global_products)or c.to_product_id in(select id from global_products)
  union select a.conversion_id from erp.product_conversion_allocations a where a.source_lot_id in(select id from global_lots)or a.destination_lot_id in(select id from global_lots)
  union select s.conversion_id from erp.be_conversion_sources_v1 s where s.source_lot_id in(select id from global_lots)
 ),support(kind,id)as(
  (select *from relevant union select 'PRODUCT',id from global_products)
  union select e.bk,e.b from support s join edges e on(e.ak,e.a)=(s.kind,s.id)
 ),outside_members as(select *from support except select *from relevant),
 members(domain,kind,id)as(select 'relevant'::text,*from relevant union select 'support',*from support union select 'outside',*from outside_members),
 domains as(select domain,jsonb_build_object(
  'identity_keys',jsonb_agg(jsonb_build_object('kind',kind,'id',id)order by kind,id),
  'lot_ids',coalesce(jsonb_agg(id order by id)filter(where kind='LOT'),'[]'),
  'product_ids',coalesce(jsonb_agg(id order by id)filter(where kind='PRODUCT'),'[]'),
  'po_ids',coalesce(jsonb_agg(id order by id)filter(where kind='PO'),'[]'),
  'conversion_ids',coalesce(jsonb_agg(id order by id)filter(where kind='CONVERSION'),'[]'),
  'journal_ids',coalesce(jsonb_agg(id order by id)filter(where kind='JOURNAL'),'[]'),
  'document_ids',coalesce(jsonb_agg(id order by id)filter(where kind='BC_DOCUMENT'),'[]'),
  'adjustment_ids',coalesce(jsonb_agg(id order by id)filter(where kind='ADJUSTMENT'),'[]'),
  'return_outstanding_ids',coalesce(jsonb_agg(id order by id)filter(where kind='RETURN_OUTSTANDING'),'[]'),
  'return_lot_ids',coalesce(jsonb_agg(id order by id)filter(where kind='RETURN_LOT'),'[]'),
  'return_event_ids',coalesce(jsonb_agg(id order by id)filter(where kind='RETURN_EVENT'),'[]'),
  'cost_event_ids',coalesce(jsonb_agg(id order by id)filter(where kind='COST_EVENT'),'[]'),
  'transfer_event_ids',coalesce(jsonb_agg(id order by id)filter(where kind='TRANSFER_EVENT'),'[]'),
  'hpp_sync_event_ids',coalesce(jsonb_agg(id order by id)filter(where kind='HPP_SYNC_EVENT'),'[]'))value
  from members group by domain),empty_domain as(select jsonb_build_object('identity_keys','[]'::jsonb,'lot_ids','[]'::jsonb,'product_ids','[]'::jsonb,
   'po_ids','[]'::jsonb,'conversion_ids','[]'::jsonb,'journal_ids','[]'::jsonb,'document_ids','[]'::jsonb,'adjustment_ids','[]'::jsonb,
   'return_outstanding_ids','[]'::jsonb,'return_lot_ids','[]'::jsonb,'return_event_ids','[]'::jsonb,
   'cost_event_ids','[]'::jsonb,'transfer_event_ids','[]'::jsonb,'hpp_sync_event_ids','[]'::jsonb)value)
 select jsonb_build_object('financial_sale_ids',to_jsonb(sales),'financial_graphs',graphs,
  'relevant',coalesce((select value from domains where domain='relevant'),(select value from empty_domain)),
  'support',coalesce((select value from domains where domain='support'),(select value from empty_domain)),
  'outside',coalesce((select value from domains where domain='outside'),(select value from empty_domain)),
  -- Native G domains intentionally retain their original predicates exactly.
  'global',jsonb_build_object('all_nonpo_lot_ids',coalesce((select jsonb_agg(id order by id)from global_lots),'[]'),
   'propagation_lock_lot_ids',coalesce((select jsonb_agg(id order by id)from global_lots where lot_origin<>'VOIDED_PRODUCTION'),'[]'),
   'sync_product_ids',coalesce((select jsonb_agg(id order by id)from global_products),'[]'),
   'support_conversion_ids',coalesce((select jsonb_agg(id order by id)from global_conversions),'[]'),
   'transfer_allocation_ids',coalesce((select jsonb_agg(a.id order by a.id)from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'join global_lots l on l.id=a.source_lot_id),'[]'),
   'guard_be_source_ids',coalesce((select jsonb_agg(s.conversion_id order by s.conversion_id)from erp.be_conversion_sources_v1 s
    where s.source_lot_id in(select id from global_lots)),'[]')),
  'history_status_filters_used_for_identity_closure',false,'Native_visit_domains_are_separate_from_support_domain',true,
  'identity_partition','FINITE_UNDIRECTED_SUPPORT_CLOSURE_MINUS_COMPLETE_RELEVANT_CLOSURE',
  'account_or_category_identity_hubs_used',false)into answer;
 return answer;
end $$;
alter function cp7_global_nonpo_native_graph.scope_v1(uuid[]) owner to postgres;
revoke all on function cp7_global_nonpo_native_graph.scope_v1(uuid[]) from public,anon,authenticated,service_role;
