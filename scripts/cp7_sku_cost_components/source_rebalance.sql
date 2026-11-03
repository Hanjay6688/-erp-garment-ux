-- A sourced cost may have moved economically to another SKU while Native
-- physical lots stayed elsewhere. Verify all affected books before the source
-- changes; retain Native source/transfer journals; redistribute only the
-- independently bounded source delta before Native FG/COGS reconciliation.
create table cp7_sku_conversion.cost_source_rebalances_v3(
 id uuid primary key,
 document_id uuid not null references erp.bc_documents_v1(id),
 source_delta numeric(24,2) not null,
 before_proof jsonb not null,
 after_proof jsonb not null,
 journal_id uuid not null references erp.journal_entries(id),
 economic_date date not null,
 recorded_at timestamptz not null default statement_timestamp()
);
create trigger cost_source_rebalances_immutable_v3 before update or delete on cp7_sku_conversion.cost_source_rebalances_v3
 for each row execute function cp7_sku_conversion.immutable_v1();
alter table cp7_sku_conversion.cost_source_rebalances_v3 enable row level security;
revoke all on cp7_sku_conversion.cost_source_rebalances_v3 from public,anon,authenticated,service_role;

create function cp7_sku_conversion.cost_source_products_v3(p_document uuid)returns uuid[]
language sql stable security definer set search_path=''as $$
 with recursive affected(lot_id,path,depth)as(
  select a.destination_lot_id,array[a.destination_lot_id],0
  from erp.be_conversion_cost_sources_v1 s join erp.product_conversion_allocations a on a.conversion_id=s.conversion_id
  join erp.fg_lots l on l.id=a.destination_lot_id and l.po_id is null where s.document_id=p_document
  union all
  select a.destination_lot_id,r.path||a.destination_lot_id,r.depth+1 from affected r
  join erp.product_conversion_allocations a on a.source_lot_id=r.lot_id
  join erp.product_conversions c on c.id=a.conversion_id and c.status='POSTED'
  where a.destination_lot_id is not null and not a.destination_lot_id=any(r.path)and r.depth<128
 ),products as(
  select l.product_id from erp.fg_lots l where l.id in(select lot_id from affected)
  union select e.product_id from cp7_sku_conversion.component_events_v2 e where e.root_lot_id in(select lot_id from affected)
  union select e.product_id from cp7_sku_conversion.cost_events_v3 e where e.root_lot_id in(select lot_id from affected)
  union select v.product_id from cp7_sku_conversion.sale_allocation_components_v2 c
   join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)where c.root_lot_id in(select lot_id from affected)
  union select v.product_id from cp7_sku_conversion.sales_return_components_v2 c
   join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)where c.root_lot_id in(select lot_id from affected)
  union select v.product_id from cp7_sku_conversion.sale_cost_components_v3 c
   join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)where c.root_lot_id in(select lot_id from affected)
  union select v.product_id from cp7_sku_conversion.return_cost_components_v3 c
   join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)where c.root_lot_id in(select lot_id from affected)
 )select coalesce(array_agg(product_id order by product_id),'{}'::uuid[])from products
$$;

create function cp7_sku_conversion.capture_cost_source_v3(p_document uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare products uuid[];product uuid;proof jsonb:='[]';target jsonb;book jsonb;events jsonb;
begin
 perform erp.require_internal();perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 products:=cp7_sku_conversion.cost_source_products_v3(p_document);
 if cardinality(products)=0 then raise exception 'CP7_SKU_COST_SOURCE_SCOPE_EMPTY';end if;
 foreach product in array products loop
  -- Opposite unexplained discrepancies cannot cancel in a global sum.
  perform erp.assert_non_po_product_hpp_target_book_v2620f(product);
  select to_jsonb(t)into strict target from erp.compute_non_po_product_hpp_targets_v2620f(product)t;
  select to_jsonb(b)into strict book from erp.compute_non_po_product_hpp_book_v2620f(product)b;
  if target is distinct from book then raise exception 'CP7_SKU_COST_SOURCE_PRESTATE_NOT_EXACT';end if;
  proof:=proof||jsonb_build_array(jsonb_build_object('product_id',product,'target',target,'book',book));
 end loop;
 select coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')into events from erp.be_conversion_cost_events_v1 e where e.document_id=p_document;
 return jsonb_build_object('document_id',p_document,'products',to_jsonb(products),'before',proof,'cost_events',events,
  'backend_pid',pg_backend_pid(),'transaction_id',txid_current());
end $$;

create function cp7_sku_conversion.rebalance_cost_source_v3(p_document uuid,p_date date,p_before jsonb,p_source_delta numeric)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare products uuid[];product uuid;row jsonb;target jsonb;book jsonb;proof jsonb:='[]';lines jsonb:='[]';
 old_events jsonb;delta numeric;target_change numeric:=0;book_change numeric:=0;redistribution numeric:=0;event_change numeric;
 event_id uuid;journal uuid;new_events jsonb;
begin
 perform erp.require_internal();perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if p_before->>'document_id'is distinct from p_document::text
  or(p_before->>'backend_pid')::integer is distinct from pg_backend_pid()
  or(p_before->>'transaction_id')::bigint is distinct from txid_current()
  or p_source_delta is null or p_source_delta<>round(p_source_delta,2)
  or p_source_delta::text in('NaN','Infinity','-Infinity')then raise exception 'CP7_SKU_COST_SOURCE_PROOF_REQUIRED';end if;
 products:=cp7_sku_conversion.cost_source_products_v3(p_document);
 if to_jsonb(products)is distinct from p_before->'products'then raise exception 'CP7_SKU_COST_SOURCE_SCOPE_CHANGED';end if;
 select coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')into old_events from erp.be_conversion_cost_events_v1 e
 where e.document_id=p_document and e.id in(select(value->>'id')::uuid from jsonb_array_elements(p_before->'cost_events'));
 if old_events is distinct from p_before->'cost_events'then raise exception 'CP7_SKU_COST_SOURCE_HISTORY_CHANGED';end if;
 select coalesce(sum(e.target_amount-e.previous_amount),0),coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')into event_change,new_events
 from erp.be_conversion_cost_events_v1 e where e.document_id=p_document
  and e.id not in(select(value->>'id')::uuid from jsonb_array_elements(p_before->'cost_events'));
 if event_change is distinct from p_source_delta then raise exception 'CP7_SKU_COST_SOURCE_EVENT_DELTA_NOT_EXACT';end if;
 -- Retain physical recost and its own immutable source entries. The later
 -- original sync call sees no further physical change and distributes FG/COGS.
 perform erp.be_nonpo_prepare_transfers_v1(p_date);
 foreach product in array products loop
  select value into strict row from jsonb_array_elements(p_before->'before')where(value->>'product_id')::uuid=product;
  select to_jsonb(t)into strict target from erp.compute_non_po_product_hpp_targets_v2620f(product)t;
  select to_jsonb(b)into strict book from erp.compute_non_po_product_hpp_book_v2620f(product)b;
  target_change:=target_change+(target->>'hpp_total_cost')::numeric-(row->'target'->>'hpp_total_cost')::numeric;
  book_change:=book_change+(book->>'hpp_total_cost')::numeric-(row->'book'->>'hpp_total_cost')::numeric;
  delta:=(target->>'hpp_total_cost')::numeric-(book->>'hpp_total_cost')::numeric;
  redistribution:=redistribution+delta;
  proof:=proof||jsonb_build_array(jsonb_build_object('product_id',product,'target',target,'book',book,'source_reallocation',delta));
  if delta<>0 then lines:=lines||jsonb_build_array(jsonb_build_object('mapping_key','FG_INVENTORY','product_id',product,
   'debit',greatest(delta,0),'credit',greatest(-delta,0)));end if;
 end loop;
 if target_change is distinct from p_source_delta or book_change is distinct from p_source_delta or redistribution<>0 then
  raise exception 'CP7_SKU_COST_SOURCE_TOTAL_NOT_EXACT: source %, target change %, book change %, redistribution %',p_source_delta,target_change,book_change,redistribution;end if;
 if jsonb_array_length(lines)>0 then
  event_id:=gen_random_uuid();
  journal:=erp.post_journal('SKU_SOURCED_COST_REALLOCATION',event_id,p_date,'Pembagian biaya sumber mengikuti nilai SKU yang memiliki',lines);
  insert into cp7_sku_conversion.cost_source_rebalances_v3(id,document_id,source_delta,before_proof,after_proof,journal_id,economic_date)
  values(event_id,p_document,p_source_delta,p_before,jsonb_build_object('after_native_physical',proof,'new_source_events',new_events),journal,p_date);
 end if;
end $$;

revoke all on function cp7_sku_conversion.cost_source_products_v3(uuid),
 cp7_sku_conversion.capture_cost_source_v3(uuid),cp7_sku_conversion.rebalance_cost_source_v3(uuid,date,jsonb,numeric)
 from public,anon,authenticated,service_role;
