-- Prepared monetary custody. These cents follow current economic ownership;
-- they do not add stock pieces or replace any Native cost/dependency guard.
create table cp7_sku_conversion.cost_money_events_v3(
 id uuid primary key,
 kind text not null check(kind in('ORIGIN','TRANSFER','SOURCE_PRICE','INVERSE_TRANSFER','INVERSE_ORIGIN')),
 source_id uuid not null,
 root_lot_id uuid not null references erp.fg_lots(id),
 product_id uuid not null references erp.products(id),
 amount_delta numeric(24,2) not null check(amount_delta::text not in('NaN','Infinity','-Infinity')),
 revision text not null,
 source_proof jsonb not null,
 economic_date date not null,
 recorded_at timestamptz not null default statement_timestamp(),
 unique(kind,source_id,root_lot_id,product_id,revision)
);
create index cost_money_events_root_product_v3 on cp7_sku_conversion.cost_money_events_v3(root_lot_id,product_id);
create trigger cost_money_events_immutable_v3 before update or delete on cp7_sku_conversion.cost_money_events_v3
 for each row execute function cp7_sku_conversion.immutable_v1();
alter table cp7_sku_conversion.cost_money_events_v3 enable row level security;
revoke all on cp7_sku_conversion.cost_money_events_v3 from public,anon,authenticated,service_role;

create function cp7_sku_conversion.cost_money_cells_v3(p_root uuid)
returns table(product_id uuid,units numeric,amount numeric)
language sql stable security definer set search_path=''as $$
 with custody as(
  select e.product_id,sum(e.units_delta)::numeric units from cp7_sku_conversion.cost_events_v3 e
  where e.root_lot_id=p_root and e.source_type='SKU_CONVERSION'group by e.product_id
 ),money as(
  select e.product_id,sum(e.amount_delta)::numeric amount from cp7_sku_conversion.cost_money_events_v3 e
  where e.root_lot_id=p_root group by e.product_id
 )select coalesce(c.product_id,m.product_id),coalesce(c.units,0)::numeric,coalesce(m.amount,0)::numeric
 from custody c full join money m using(product_id)
$$;

create function cp7_sku_conversion.cost_current_unit_v3(p_root uuid,p_product uuid)returns numeric
language plpgsql stable security definer set search_path=''as $$
declare r record;total_units numeric;total_money numeric;owned record;
begin
 -- Keep current HPP completeness and real PO attribution from the Native root.
 select *into strict r from cp7_sku_conversion.cost_root_v3(p_root);
 if r.po_id is not null then return r.unit_value;end if;
 if p_product is null then raise exception 'CP7_SKU_COST_MONEY_PRODUCT_REQUIRED';end if;
 select a.qty_pcs,erp.be_allocation_extra_v1(a.id)extra into strict r
 from erp.product_conversion_allocations a where a.destination_lot_id=p_root;
 select sum(c.units),sum(c.amount)into total_units,total_money from cp7_sku_conversion.cost_money_cells_v3(p_root)c;
 if not exists(select 1 from cp7_sku_conversion.cost_money_events_v3 where root_lot_id=p_root and kind='ORIGIN')
  or total_units is null or total_money is null
  or exists(select 1 from cp7_sku_conversion.cost_money_cells_v3(p_root)c where c.units<0 or(c.units=0 and c.amount<>0))
  or exists(select 1 from cp7_sku_conversion.cost_events_v3 e where e.root_lot_id=p_root
   and(e.source_type<>'SALE'or exists(select 1 from erp.sales_headers h where h.id=e.source_id and h.status in('POSTED','PARTIAL_PAID','PAID','REVERSED')))
   and(e.source_type<>'SALES_RETURN'or exists(select 1 from erp.sales_returns h where h.id=e.source_id and h.status in('POSTED','REVERSED')))
   group by e.product_id having sum(e.units_delta)<0)
  or(total_units<>r.qty_pcs and total_units<>0)
  or(total_units=0 and(total_money<>0 or r.extra<>0))
  or(total_units>0 and total_money is distinct from r.extra)then
  raise exception 'CP7_SKU_COST_MONEY_SOURCE_NOT_EXACT';end if;
 select c.units,c.amount into owned from cp7_sku_conversion.cost_money_cells_v3(p_root)c where c.product_id=p_product;
 if not found or owned.units=0 then return 0;end if;
 return owned.amount/owned.units;
end $$;

create function cp7_sku_conversion.post_conversion_money_v3(p_group uuid)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare q cp7_sku_conversion.valuation_quotes_v2%rowtype;c record;cell record;old_units numeric;
 economic_date date;product uuid;
begin
 perform erp.require_internal();perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select *into strict q from cp7_sku_conversion.valuation_quotes_v2 where group_id=p_group;
 economic_date:=(q.physical_at at time zone 'Asia/Jakarta')::date;
 for c in select *from cp7_sku_conversion.cost_contributors_v3 where group_id=p_group and po_id is null order by root_lot_id loop
  select *into strict cell from cp7_sku_conversion.cost_money_cells_v3(c.root_lot_id)where product_id=q.source_product_id;
  -- Cost units have just moved; the money still belongs to the old source.
  old_units:=cell.units+c.transfer_units;
  if old_units<=0 or c.transfer_units>old_units
   or(c.transfer_units=old_units and c.transfer_value is distinct from cell.amount)
   or(cell.amount>=0 and(c.transfer_value<0 or c.transfer_value>cell.amount))
   or(cell.amount<0 and(c.transfer_value>0 or c.transfer_value<cell.amount))then
   raise exception 'CP7_SKU_COST_MONEY_TRANSFER_CAPACITY';end if;
  insert into cp7_sku_conversion.cost_money_events_v3(id,kind,source_id,root_lot_id,product_id,amount_delta,revision,source_proof,economic_date)
  values(gen_random_uuid(),'TRANSFER',p_group,c.root_lot_id,q.source_product_id,-c.transfer_value,p_group::text,to_jsonb(c),economic_date),
        (gen_random_uuid(),'TRANSFER',p_group,c.root_lot_id,q.target_product_id,c.transfer_value,p_group::text,to_jsonb(c),economic_date);
 end loop;
 for c in select a.*,l.po_id from cp7_sku_conversion.members_v1 m
  join erp.product_conversion_allocations a on a.conversion_id=m.conversion_id join erp.fg_lots l on l.id=a.destination_lot_id
  where m.group_id=p_group and l.po_id is null order by a.id loop
  insert into cp7_sku_conversion.cost_money_events_v3(id,kind,source_id,root_lot_id,product_id,amount_delta,revision,source_proof,economic_date)
  values(gen_random_uuid(),'ORIGIN',p_group,c.destination_lot_id,q.target_product_id,erp.be_allocation_extra_v1(c.id),
   p_group::text,jsonb_build_object('allocation',to_jsonb(c),'initial_extra',erp.be_allocation_extra_v1(c.id)),economic_date);
 end loop;
 for c in select distinct e.root_lot_id from cp7_sku_conversion.cost_events_v3 e where e.source_type='SKU_CONVERSION'and e.source_id=p_group loop
  perform cp7_sku_conversion.cost_current_unit_v3(c.root_lot_id,q.source_product_id);
  perform cp7_sku_conversion.cost_current_unit_v3(c.root_lot_id,q.target_product_id);
 end loop;
end $$;

create function cp7_sku_conversion.reverse_conversion_money_v3(p_group uuid)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare q cp7_sku_conversion.valuation_quotes_v2%rowtype;c record;amount numeric;
 economic_date date:=(statement_timestamp()at time zone 'Asia/Jakarta')::date;
begin
 perform erp.require_internal();perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select *into strict q from cp7_sku_conversion.valuation_quotes_v2 where group_id=p_group;
 for c in select *from cp7_sku_conversion.cost_contributors_v3 where group_id=p_group and po_id is null order by root_lot_id loop
  amount:=round(c.transfer_units*cp7_sku_conversion.cost_current_unit_v3(c.root_lot_id,q.target_product_id),2);
  insert into cp7_sku_conversion.cost_money_events_v3(id,kind,source_id,root_lot_id,product_id,amount_delta,revision,source_proof,economic_date)
  values(gen_random_uuid(),'INVERSE_TRANSFER',p_group,c.root_lot_id,q.target_product_id,-amount,p_group::text,
         jsonb_build_object('original_contributor',to_jsonb(c),'current_amount',amount),economic_date),
        (gen_random_uuid(),'INVERSE_TRANSFER',p_group,c.root_lot_id,q.source_product_id,amount,p_group::text,
         jsonb_build_object('original_contributor',to_jsonb(c),'current_amount',amount),economic_date);
 end loop;
 for c in select a.*,l.po_id from cp7_sku_conversion.members_v1 m
  join erp.product_conversion_allocations a on a.conversion_id=m.conversion_id join erp.fg_lots l on l.id=a.destination_lot_id
  where m.group_id=p_group and l.po_id is null order by a.id loop
  if erp.be_allocation_extra_v1(c.id)<>0
   or exists(select 1 from cp7_sku_conversion.cost_money_cells_v3(c.destination_lot_id)x where x.amount<>0)then
   raise exception 'CP7_SKU_INVERSE_OWN_COST_STILL_ACTIVE';end if;
  insert into cp7_sku_conversion.cost_money_events_v3(id,kind,source_id,root_lot_id,product_id,amount_delta,revision,source_proof,economic_date)
  values(gen_random_uuid(),'INVERSE_ORIGIN',p_group,c.destination_lot_id,q.target_product_id,0,p_group::text,to_jsonb(c),economic_date);
 end loop;
end $$;

create function cp7_sku_conversion.cost_document_money_state_v3(p_document uuid)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare a record;state jsonb:='[]';cells jsonb;
begin
 for a in select allocation.*,l.po_id from erp.be_conversion_cost_sources_v1 s
  join erp.product_conversion_allocations allocation on allocation.conversion_id=s.conversion_id join erp.fg_lots l on l.id=allocation.destination_lot_id
  where s.document_id=p_document and l.po_id is null order by allocation.destination_lot_id loop
  perform cp7_sku_conversion.cost_current_unit_v3(a.destination_lot_id,(select e.product_id from cp7_sku_conversion.cost_events_v3 e
   where e.root_lot_id=a.destination_lot_id and e.side='ORIGIN'and e.phase='POST'));
  select coalesce(jsonb_agg(to_jsonb(c)order by c.product_id),'[]')into cells from cp7_sku_conversion.cost_money_cells_v3(a.destination_lot_id)c;
  state:=state||jsonb_build_array(jsonb_build_object('root_lot_id',a.destination_lot_id,'allocation_id',a.id,'qty',a.qty_pcs,
   'extra',erp.be_allocation_extra_v1(a.id),'cells',cells,
   'money_events',(select coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')from cp7_sku_conversion.cost_money_events_v3 e where e.root_lot_id=a.destination_lot_id)));
 end loop;
 return state;
end $$;

create function cp7_sku_conversion.reprice_document_money_v3(p_document uuid,p_date date,p_before jsonb,p_events jsonb,p_delta numeric)returns void
language plpgsql volatile security definer set search_path=''as $$
declare old_root jsonb;current_cells jsonb;old_events jsonb;a record;c record;new_total numeric;old_total numeric;
 cumulative_units numeric;previous_target numeric;target numeric;amount numeric;total_change numeric:=0;revision text;count_roots integer:=0;
begin
 perform erp.require_internal();perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if jsonb_typeof(p_before)is distinct from 'array'or jsonb_typeof(p_events)is distinct from 'array'then
  raise exception 'CP7_SKU_COST_MONEY_SOURCE_PROOF_REQUIRED';end if;
 for a in select allocation.*,l.po_id from erp.be_conversion_cost_sources_v1 s
  join erp.product_conversion_allocations allocation on allocation.conversion_id=s.conversion_id join erp.fg_lots l on l.id=allocation.destination_lot_id
  where s.document_id=p_document and l.po_id is null order by allocation.destination_lot_id loop
  count_roots:=count_roots+1;
  select value into strict old_root from jsonb_array_elements(p_before)where(value->>'root_lot_id')::uuid=a.destination_lot_id;
  select coalesce(jsonb_agg(to_jsonb(x)order by x.product_id),'[]')into current_cells from cp7_sku_conversion.cost_money_cells_v3(a.destination_lot_id)x;
  select coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')into old_events from cp7_sku_conversion.cost_money_events_v3 e where e.root_lot_id=a.destination_lot_id;
  if old_root->>'allocation_id'is distinct from a.id::text or(old_root->>'qty')::numeric is distinct from a.qty_pcs
   or current_cells is distinct from old_root->'cells'or old_events is distinct from old_root->'money_events'then
   raise exception 'CP7_SKU_COST_MONEY_CUSTODY_CHANGED';end if;
  old_total:=(old_root->>'extra')::numeric;new_total:=erp.be_allocation_extra_v1(a.id);
  if old_total is distinct from(select sum(x.amount)from cp7_sku_conversion.cost_money_cells_v3(a.destination_lot_id)x)
   or new_total is null or new_total<>round(new_total,2)or new_total::text in('NaN','Infinity','-Infinity')then
   raise exception 'CP7_SKU_COST_MONEY_SOURCE_NOT_EXACT';end if;
  total_change:=total_change+new_total-old_total;
  if new_total=old_total then continue;end if;
  if jsonb_array_length(p_events)=0 then raise exception 'CP7_SKU_COST_MONEY_NATIVE_EVENTS_REQUIRED';end if;
  cumulative_units:=0;previous_target:=0;
  revision:=md5(jsonb_build_object('before',old_root,'new_total',new_total,'events',p_events)::text);
  for c in select *from cp7_sku_conversion.cost_money_cells_v3(a.destination_lot_id)order by product_id loop
   if c.units<0 or(c.units=0 and c.amount<>0)then raise exception 'CP7_SKU_COST_MONEY_CAPACITY';end if;
   cumulative_units:=cumulative_units+c.units;
   target:=round(new_total*cumulative_units/a.qty_pcs,2);amount:=target-previous_target-c.amount;previous_target:=target;
   if amount<>0 then
    insert into cp7_sku_conversion.cost_money_events_v3(id,kind,source_id,root_lot_id,product_id,amount_delta,revision,source_proof,economic_date)
    values(gen_random_uuid(),'SOURCE_PRICE',p_document,a.destination_lot_id,c.product_id,amount,revision,
     jsonb_build_object('allocation_id',a.id,'qty_basis_pcs',a.qty_pcs,'old_total',old_total,'new_total',new_total,
      'before_cell',to_jsonb(c),'before_money_event_count',jsonb_array_length(old_root->'money_events'),
      'before_money_revision',md5((old_root->'money_events')::text),'native_events',p_events,
      'cumulative_units',cumulative_units,'cumulative_target',target),p_date);
   end if;
  end loop;
  if cumulative_units is distinct from a.qty_pcs or previous_target is distinct from new_total then
   raise exception 'CP7_SKU_COST_MONEY_ALLOCATION_NOT_EXACT';end if;
 end loop;
 if count_roots<>jsonb_array_length(p_before)or total_change is distinct from p_delta then
  raise exception 'CP7_SKU_COST_MONEY_DOCUMENT_DELTA_NOT_EXACT';end if;
end $$;

revoke all on function cp7_sku_conversion.cost_money_cells_v3(uuid),cp7_sku_conversion.cost_current_unit_v3(uuid,uuid),
 cp7_sku_conversion.post_conversion_money_v3(uuid),cp7_sku_conversion.reverse_conversion_money_v3(uuid),
 cp7_sku_conversion.cost_document_money_state_v3(uuid),cp7_sku_conversion.reprice_document_money_v3(uuid,date,jsonb,jsonb,numeric)
 from public,anon,authenticated,service_role;
