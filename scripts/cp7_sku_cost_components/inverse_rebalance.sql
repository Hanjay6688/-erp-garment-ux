-- Called only after the retained Native inverse has reversed every member.
-- Its old value correction stays immutable. A separately proved zero-sum
-- journal reconciles that historical reversal to current source ownership.
create table cp7_sku_conversion.group_inverse_rebalances_v3(
 group_id uuid primary key references cp7_sku_conversion.valuation_quotes_v2(group_id),
 before_proof jsonb not null,
 after_proof jsonb not null,
 journal_id uuid references erp.journal_entries(id),
 economic_date date not null,
 recorded_at timestamptz not null default statement_timestamp()
);
create trigger group_inverse_rebalances_immutable_v3 before update or delete on cp7_sku_conversion.group_inverse_rebalances_v3
 for each row execute function cp7_sku_conversion.immutable_v1();
alter table cp7_sku_conversion.group_inverse_rebalances_v3 enable row level security;
revoke all on cp7_sku_conversion.group_inverse_rebalances_v3 from public,anon,authenticated,service_role;

create function cp7_sku_conversion.assert_group_inverse_capacity_v3(p_group uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
declare q cp7_sku_conversion.valuation_quotes_v2%rowtype;
begin
 perform erp.require_internal();perform erp.require_permission('warehouse.brand_conversion.reverse');perform erp.require_owner_admin();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select *into strict q from cp7_sku_conversion.valuation_quotes_v2 where group_id=p_group;
 if exists(select 1 from cp7_sku_conversion.valuation_postings_v2 where group_id=p_group and phase='REVERSE')then
  raise exception 'CP7_SKU_MOVAVG_ALREADY_REVERSED';end if;
 if not exists(select 1 from cp7_sku_conversion.members_v1 where group_id=p_group)
  or exists(select 1 from cp7_sku_conversion.members_v1 m left join erp.product_conversions c on c.id=m.conversion_id
   where m.group_id=p_group and c.status is distinct from 'POSTED')then
  raise exception 'CP7_SKU_INVERSE_ALL_MEMBERS_POSTED_REQUIRED';end if;
 if exists(
  select 1 from cp7_sku_conversion.valuation_contributors_v2 c
  left join cp7_sku_conversion.pool_components_v2(q.target_product_id,q.location_id,q.quality_grade)p using(root_lot_id)
  where c.group_id=p_group and coalesce(p.component_units,0)<c.transfer_units
 )then raise exception 'CP7_SKU_INVERSE_ECONOMIC_COMPONENT_USED';end if;
 if exists(
  with required as(
   select c.root_lot_id,c.transfer_units units from cp7_sku_conversion.cost_contributors_v3 c where c.group_id=p_group
   union all select e.root_lot_id,e.units_delta from cp7_sku_conversion.cost_events_v3 e
    where e.source_type='SKU_CONVERSION'and e.source_id=p_group and e.side='ORIGIN'and e.phase='POST'
  ),needed as(select root_lot_id,sum(units)units from required group by root_lot_id)
  select 1 from needed n left join cp7_sku_conversion.pool_cost_components_v3(q.target_product_id,q.location_id,q.quality_grade)p using(root_lot_id)
  where coalesce(p.component_units,0)<n.units
 )then raise exception 'CP7_SKU_INVERSE_ECONOMIC_COST_USED';end if;
end $$;

create function cp7_sku_conversion.inverse_source_facts_v3(p_roots uuid[])returns jsonb
language sql stable security definer set search_path=''as $$
 select jsonb_build_object(
  'hpp',(select coalesce(jsonb_agg(to_jsonb(h)order by h.id),'[]')from erp.hpp_versions h where h.lot_id=any(p_roots)and h.is_current),
  'allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')from erp.product_conversion_allocations a where a.destination_lot_id=any(p_roots)),
  'cost_sources',(select coalesce(jsonb_agg(to_jsonb(s)order by s.document_id),'[]')from erp.be_conversion_cost_sources_v1 s
   where s.conversion_id in(select a.conversion_id from erp.product_conversion_allocations a where a.destination_lot_id=any(p_roots))),
  'cost_events',(select coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')from erp.be_conversion_cost_events_v1 e
   join erp.be_conversion_cost_sources_v1 s on s.document_id=e.document_id
   where s.conversion_id in(select a.conversion_id from erp.product_conversion_allocations a where a.destination_lot_id=any(p_roots))))
$$;

create function cp7_sku_conversion.capture_group_inverse_v3(p_group uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare q cp7_sku_conversion.valuation_quotes_v2%rowtype;products uuid[];roots uuid[];product uuid;
 target jsonb;book jsonb;proof jsonb:='[]';
begin
 perform erp.require_internal();perform erp.require_permission('warehouse.brand_conversion.reverse');perform erp.require_owner_admin();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select *into strict q from cp7_sku_conversion.valuation_quotes_v2 where group_id=p_group;
 if not exists(select 1 from cp7_sku_conversion.members_v1 where group_id=p_group)
  or exists(select 1 from cp7_sku_conversion.members_v1 m left join erp.product_conversions c on c.id=m.conversion_id
   where m.group_id=p_group and c.status is distinct from 'REVERSED')then
  raise exception 'CP7_SKU_NATIVE_INVERSE_REQUIRED';end if;
 select array_agg(id order by id)into products from(select distinct unnest(array[q.source_product_id,q.target_product_id])id)p;
 select coalesce(array_agg(distinct id order by id),'{}'::uuid[])into roots from(
  select unnest(cp7_sku_conversion.hpp_scope_lot_ids_v2(p.product_id,null))id from unnest(products)p(product_id)
  union select root_lot_id from cp7_sku_conversion.valuation_contributors_v2 where group_id=p_group
  union select root_lot_id from cp7_sku_conversion.cost_contributors_v3 where group_id=p_group
  union select a.destination_lot_id from cp7_sku_conversion.members_v1 m
   join erp.product_conversion_allocations a on a.conversion_id=m.conversion_id where m.group_id=p_group
 )r;
 foreach product in array products loop
  perform erp.assert_non_po_product_hpp_target_book_v2620f(product);
  select to_jsonb(t)into strict target from erp.compute_non_po_product_hpp_targets_v2620f(product)t;
  select to_jsonb(b)into strict book from erp.compute_non_po_product_hpp_book_v2620f(product)b;
  if target is distinct from book then raise exception 'CP7_SKU_INVERSE_PRESTATE_NOT_EXACT';end if;
  proof:=proof||jsonb_build_array(jsonb_build_object('product_id',product,'target',target,'book',book));
 end loop;
 return jsonb_build_object('group_id',p_group,'products',to_jsonb(products),'roots',to_jsonb(roots),'before',proof,
  'sources',cp7_sku_conversion.inverse_source_facts_v3(roots),'backend_pid',pg_backend_pid(),'transaction_id',txid_current());
end $$;

create function cp7_sku_conversion.rebalance_group_inverse_v3(p_group uuid,p_before jsonb)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare q cp7_sku_conversion.valuation_quotes_v2%rowtype;products uuid[];roots uuid[];product uuid;row jsonb;
 target jsonb;book jsonb;proof jsonb:='[]';lines jsonb:='[]';target_change numeric:=0;book_change numeric:=0;
 redistribution numeric:=0;delta numeric;journal uuid;economic_date date:=(statement_timestamp()at time zone 'Asia/Jakarta')::date;
begin
 perform erp.require_internal();perform erp.require_permission('warehouse.brand_conversion.reverse');perform erp.require_owner_admin();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select *into strict q from cp7_sku_conversion.valuation_quotes_v2 where group_id=p_group;
 if p_before->>'group_id'is distinct from p_group::text
  or(p_before->>'backend_pid')::integer is distinct from pg_backend_pid()
  or(p_before->>'transaction_id')::bigint is distinct from txid_current()then
  raise exception 'CP7_SKU_INVERSE_PROOF_REQUIRED';end if;
 select array_agg(id order by id)into products from(select distinct unnest(array[q.source_product_id,q.target_product_id])id)p;
 if to_jsonb(products)is distinct from p_before->'products'then raise exception 'CP7_SKU_INVERSE_SCOPE_CHANGED';end if;
 select array_agg(value::uuid order by value::uuid)into roots from jsonb_array_elements_text(p_before->'roots');
 if cp7_sku_conversion.inverse_source_facts_v3(roots)is distinct from p_before->'sources'then
  raise exception 'CP7_SKU_INVERSE_SOURCE_CHANGED';end if;
 foreach product in array products loop
  select value into strict row from jsonb_array_elements(p_before->'before')where(value->>'product_id')::uuid=product;
  select to_jsonb(t)into strict target from erp.compute_non_po_product_hpp_targets_v2620f(product)t;
  select to_jsonb(b)into strict book from erp.compute_non_po_product_hpp_book_v2620f(product)b;
  target_change:=target_change+(target->>'hpp_total_cost')::numeric-(row->'target'->>'hpp_total_cost')::numeric;
  book_change:=book_change+(book->>'hpp_total_cost')::numeric-(row->'book'->>'hpp_total_cost')::numeric;
  delta:=(target->>'hpp_total_cost')::numeric-(book->>'hpp_total_cost')::numeric;
  redistribution:=redistribution+delta;
  proof:=proof||jsonb_build_array(jsonb_build_object('product_id',product,'target',target,'book',book,'current_value_reallocation',delta));
  if delta<>0 then lines:=lines||jsonb_build_array(jsonb_build_object('mapping_key','FG_INVENTORY','product_id',product,
   'debit',greatest(delta,0),'credit',greatest(-delta,0)));end if;
 end loop;
 if target_change<>0 or book_change<>0 or redistribution<>0 then
  raise exception 'CP7_SKU_INVERSE_TOTAL_NOT_EXACT: target %, book %, redistribution %',target_change,book_change,redistribution;end if;
 if jsonb_array_length(lines)>0 then
  journal:=erp.post_journal('SKU_CURRENT_VALUE_INVERSE',p_group,economic_date,'Pembalikan mengikuti nilai sumber terkini',lines);
 end if;
 foreach product in array products loop
  perform erp.sync_non_po_product_hpp_to_gl_v2620f(product,economic_date,'SKU_CURRENT_VALUE_INVERSE',p_group,'Nilai terkini sesudah pembalikan Ganti Merek');
  perform erp.assert_non_po_product_hpp_target_book_v2620f(product);
 end loop;
 insert into cp7_sku_conversion.group_inverse_rebalances_v3(group_id,before_proof,after_proof,journal_id,economic_date)
 values(p_group,p_before,jsonb_build_object('after_historical_inverse',proof,'target_change',target_change,'book_change',book_change),journal,economic_date);
end $$;

revoke all on function cp7_sku_conversion.inverse_source_facts_v3(uuid[]),
 cp7_sku_conversion.assert_group_inverse_capacity_v3(uuid),
 cp7_sku_conversion.capture_group_inverse_v3(uuid),cp7_sku_conversion.rebalance_group_inverse_v3(uuid,jsonb)
 from public,anon,authenticated,service_role;
