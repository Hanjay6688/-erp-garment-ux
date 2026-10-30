-- Every array is an actual row set with its identities, including status/history.
-- Outside is a separately named actual capture; it is never a Native sale snapshot.
create function cp7_global_nonpo_native_graph.capture_v1(p_scope jsonb,p_outside boolean) returns jsonb
language sql stable security definer set search_path='' set timezone='UTC' as $$
 with recursive products(id)as(
  select value::uuid from jsonb_array_elements_text(case when p_outside then p_scope#>'{outside,product_ids}'else p_scope#>'{global,sync_product_ids}'end)
  union select value::uuid from jsonb_array_elements_text(case when p_outside then'[]'::jsonb else p_scope#>'{relevant,product_ids}'end)
 ),lots as(select l.*from erp.fg_lots l where l.product_id in(select id from products)),
 conversions as(select c.*from erp.product_conversions c where c.from_product_id in(select id from products)or c.to_product_id in(select id from products)
  or exists(select 1 from erp.product_conversion_allocations a where a.conversion_id=c.id and(a.source_lot_id in(select id from lots)or a.destination_lot_id in(select id from lots)))
  or exists(select 1 from erp.be_conversion_sources_v1 s where s.conversion_id=c.id and s.source_lot_id in(select id from lots))),
 cost_sources as(select s.*from erp.be_conversion_cost_sources_v1 s where s.conversion_id in(select id from conversions)),
 cost_events as(select e.*from erp.be_conversion_cost_events_v1 e where e.document_id in(select document_id from cost_sources)),
 transfers as(select e.*from erp.be_nonpo_transfer_events_v1 e where e.conversion_id in(select id from conversions)),
 return_sources as(select r.*from erp.be_conversion_returns_v1 r where r.conversion_id in(select id from conversions)),
 returned_lots as(select l.*from erp.bc_return_lots_v1 l where l.outstanding_id in(select outstanding_id from return_sources)),
 journals(id)as(
  select l.journal_entry_id from erp.journal_lines l where l.product_id in(select id from products)
   or l.po_id in(select po_id from lots where po_id is not null)
  union select journal_id from cost_events union select journal_id from transfers
  union select e.journal_entry_id from erp.non_po_hpp_gl_sync_events_v2620f e where e.product_id in(select id from products)
  union select j.reversal_of_id from journals x join erp.journal_entries j on j.id=x.id where j.reversal_of_id is not null
 ),allocations as(select a.*from erp.sale_stock_allocations a where a.lot_id in(select id from lots)),
 return_items as(select i.*from erp.sales_return_items i where i.lot_id in(select id from lots)),
 facts as(select jsonb_build_object(
  'fg_lots',coalesce((select jsonb_agg(to_jsonb(l)order by l.id)from lots l),'[]'),
  'hpp_versions',coalesce((select jsonb_agg(to_jsonb(h)order by h.id)from erp.hpp_versions h where h.lot_id in(select id from lots)),'[]'),
  'hpp_components',coalesce((select jsonb_agg(to_jsonb(c)order by c.id)from erp.hpp_version_components c join erp.hpp_versions h on h.id=c.hpp_version_id where h.lot_id in(select id from lots)),'[]'),
  'conversions',coalesce((select jsonb_agg(to_jsonb(c)order by c.id)from conversions c),'[]'),
  'conversion_allocations',coalesce((select jsonb_agg(to_jsonb(a)order by a.id)from erp.product_conversion_allocations a where a.conversion_id in(select id from conversions)),'[]'),
  'BE_sources',coalesce((select jsonb_agg(to_jsonb(s)order by s.conversion_id)from erp.be_conversion_sources_v1 s where s.conversion_id in(select id from conversions)),'[]'),
  'cost_sources',coalesce((select jsonb_agg(to_jsonb(s)order by s.document_id)from cost_sources s),'[]'),
  'cost_events',coalesce((select jsonb_agg(to_jsonb(e)order by e.id)from cost_events e),'[]'),
  'cost_and_return_documents',coalesce((select jsonb_agg(to_jsonb(d)order by d.id)from erp.bc_documents_v1 d where d.id in(select document_id from cost_sources union select document_id from returned_lots)),'[]'),
  'BE_return_sources',coalesce((select jsonb_agg(to_jsonb(r)order by r.outstanding_id)from return_sources r),'[]'),
  'outstanding_returns',coalesce((select jsonb_agg(to_jsonb(r)order by r.id)from erp.bc_outstanding_returns_v1 r where r.id in(select outstanding_id from return_sources)),'[]'),
  'returned_lots',coalesce((select jsonb_agg(to_jsonb(l)order by l.id)from returned_lots l),'[]'),
  'BE_context_rows',coalesce((select jsonb_agg(to_jsonb(c)order by c.backend_pid,c.transaction_id)from erp.be_execution_context_v1 c),'[]'),
  'material_adjustments',coalesce((select jsonb_agg(to_jsonb(a)order by a.id)from erp.material_adjustments a where a.id in(select adjustment_id from cost_events)),'[]'),
  'nonpo_transfers',coalesce((select jsonb_agg(to_jsonb(e)order by e.id)from transfers e),'[]'),
  'stock_movements',coalesce((select jsonb_agg(to_jsonb(m)order by m.id)from erp.fg_stock_movements m where m.lot_id in(select id from lots)),'[]'),
  'inventory_balances',coalesce((select jsonb_agg(to_jsonb(b)order by b.product_id,b.location_id,b.quality_grade)from erp.fg_inventory_balances b where b.product_id in(select id from products)),'[]'),
  'sale_allocations',coalesce((select jsonb_agg(to_jsonb(a)order by a.id)from allocations a),'[]'),
  'sale_items',coalesce((select jsonb_agg(to_jsonb(i)order by i.id)from erp.sales_items i where i.id in(select sale_item_id from allocations)),'[]'),
  'sales_headers',coalesce((select jsonb_agg(to_jsonb(h)order by h.id)from erp.sales_headers h where h.id in(select i.sale_id from erp.sales_items i where i.id in(select sale_item_id from allocations))),'[]'),
  'return_items',coalesce((select jsonb_agg(to_jsonb(i)order by i.id)from return_items i),'[]'),
  'sales_returns',coalesce((select jsonb_agg(to_jsonb(h)order by h.id)from erp.sales_returns h where h.id in(select return_id from return_items)),'[]'),
  'journals',coalesce((select jsonb_agg(to_jsonb(j)order by j.id)from erp.journal_entries j where j.id in(select id from journals)),'[]'),
  'journal_lines',coalesce((select jsonb_agg(to_jsonb(l)order by l.id)from erp.journal_lines l where l.journal_entry_id in(select id from journals)),'[]'),
  'nonpo_hpp_events',coalesce((select jsonb_agg(to_jsonb(e)order by e.id)from erp.non_po_hpp_gl_sync_events_v2620f e where e.product_id in(select id from products)),'[]'),
  'opening_states',coalesce((select jsonb_agg(to_jsonb(s)order by s.lot_id)from erp.opening_lot_hpp_gl_state s where s.lot_id in(select id from lots)),'[]'),
  'opening_corrections',coalesce((select jsonb_agg(to_jsonb(c)order by c.id)from erp.opening_hpp_corrections c where c.lot_id in(select id from lots)),'[]'),
  'po_states',coalesce((select jsonb_agg(to_jsonb(s)order by s.po_id)from erp.po_hpp_gl_state s where s.po_id in(select po_id from lots)),'[]'),
  'hpp_accounts',cp7_credit.initial_hpp_account_facts_v1(),
  'period',(select to_jsonb(c)from erp.accounting_period_control c where singleton_id=1)) value)
 select jsonb_build_object('classification',case when p_outside then'NEW_ACTUAL_OUTSIDE_GLOBAL_FACTS_NOT_NATIVE_SALE_SNAPSHOT'else'ACTUAL_GLOBAL_AND_RELEVANT_SUPPORT'end,
  'facts',value,'sha256',cp7_credit.pg_jsonb_sha256(value),
  'keyset',(select jsonb_object_agg(key,case when jsonb_typeof(v)='array'then jsonb_array_length(v)else null end)from jsonb_each(value)as t(key,v)))from facts
$$;
alter function cp7_global_nonpo_native_graph.capture_v1(jsonb,boolean) owner to postgres;
revoke all on function cp7_global_nonpo_native_graph.capture_v1(jsonb,boolean) from public,anon,authenticated,service_role;
