-- Prepared only. Base-stock monetary custody is separate from added costs.
create table cp7_sku_conversion.base_money_events_v4(
 id uuid primary key,
 kind text not null check(kind in('ORIGIN','TRANSFER','SOURCE_PRICE','INVERSE_TRANSFER')),
 source_id uuid not null,
 root_lot_id uuid not null references erp.fg_lots(id),
 product_id uuid not null references erp.products(id),
 units_delta numeric(30,12) not null check(units_delta::text not in('NaN','Infinity','-Infinity')),
 amount_delta numeric(24,2) not null check(amount_delta::text not in('NaN','Infinity','-Infinity')),
 source_proof jsonb not null,
 economic_date date not null,
 recorded_at timestamptz not null default statement_timestamp(),
 unique(kind,source_id,root_lot_id,product_id),
 check(kind<>'SOURCE_PRICE'or units_delta=0)
);
create index base_money_events_root_product_v4 on cp7_sku_conversion.base_money_events_v4(root_lot_id,product_id);
create trigger base_money_events_immutable_v4 before update or delete on cp7_sku_conversion.base_money_events_v4
 for each row execute function cp7_sku_conversion.immutable_v1();
alter table cp7_sku_conversion.base_money_events_v4 enable row level security;
revoke all on cp7_sku_conversion.base_money_events_v4 from public,anon,authenticated,service_role;

create function cp7_sku_conversion.base_money_cells_v4(p_root uuid)
returns table(product_id uuid,units numeric,amount numeric)
language sql stable security definer set search_path=''as $$
 select e.product_id,sum(e.units_delta)::numeric,sum(e.amount_delta)::numeric
 from cp7_sku_conversion.base_money_events_v4 e where e.root_lot_id=p_root group by e.product_id
$$;

create function cp7_sku_conversion.base_raw_custody_v4(p_root uuid)
returns table(product_id uuid,units numeric)
language sql stable security definer set search_path=''as $$
 with entries as(
  select l.product_id,(case when l.lot_origin='VOIDED_PRODUCTION'or(l.lot_origin='CONVERSION'and not exists(
   select 1 from erp.product_conversion_allocations a join erp.product_conversions c on c.id=a.conversion_id
   where a.destination_lot_id=l.id and c.status='POSTED'))then 0 else l.initial_qty_pcs end
   -coalesce((select sum(a.qty_pcs)from erp.product_conversion_allocations a
    join erp.product_conversions c on c.id=a.conversion_id where a.source_lot_id=l.id and c.status='POSTED'),0))::numeric units
  from erp.fg_lots l where l.id=p_root
  union all select e.product_id,e.units_delta from cp7_sku_conversion.component_events_v2 e
   where e.root_lot_id=p_root and e.source_type='SKU_CONVERSION'
 )select e.product_id,sum(e.units)::numeric from entries e group by e.product_id
$$;

create function cp7_sku_conversion.base_current_unit_v4(p_root uuid,p_product uuid)returns numeric
language plpgsql stable security definer set search_path=''as $$
declare h record;c record;qty numeric;amount numeric;
begin
 select v.*,l.po_id into strict h from erp.fg_lots l join erp.hpp_versions v on v.lot_id=l.id and v.is_current where l.id=p_root;
 if h.po_id is not null and exists(select 1 from cp7_sku_conversion.base_money_events_v4 where root_lot_id=p_root)then
  raise exception 'CP7_SKU_BASE_MONEY_PO_PROVENANCE_CHANGED';end if;
 if h.po_id is not null or not exists(select 1 from cp7_sku_conversion.base_money_events_v4 where root_lot_id=p_root)then
  return h.hpp_per_pcs;end if;
 select sum(x.units),sum(x.amount)into qty,amount from cp7_sku_conversion.base_money_cells_v4(p_root)x;
 if p_product is null or h.qty_basis_pcs<=0 or h.total_cost<0 or h.total_cost::text in('NaN','Infinity','-Infinity')
  or h.cost_state='ESTIMATED'or qty is distinct from h.qty_basis_pcs or amount is distinct from round(h.total_cost,2)
  or(select count(*)from cp7_sku_conversion.base_money_events_v4 where root_lot_id=p_root and kind='ORIGIN')<>1
  or exists(select 1 from cp7_sku_conversion.base_money_cells_v4(p_root)x where x.units<0 or x.amount<0 or(x.units=0 and x.amount<>0))then
  raise exception 'CP7_SKU_BASE_MONEY_SOURCE_NOT_EXACT';end if;
 select *into c from cp7_sku_conversion.base_money_cells_v4(p_root)where product_id=p_product;
 if not found or c.units=0 then return 0;end if;
 return c.amount/c.units;
end $$;

create function cp7_sku_conversion.base_transition_value_v4(p_root uuid,p_product uuid)returns numeric
language plpgsql stable security definer set search_path=''as $$
declare owned numeric;physical numeric;difference numeric;expected numeric;native_unit numeric;unit numeric;
begin
 if not exists(select 1 from cp7_sku_conversion.base_money_events_v4 where root_lot_id=p_root)then return 0;end if;
 unit:=cp7_sku_conversion.base_current_unit_v4(p_root,p_product);
 select coalesce(sum(c.units),0)into owned from cp7_sku_conversion.base_money_cells_v4(p_root)c where c.product_id=p_product;
 select coalesce(sum(c.units),0)into physical from cp7_sku_conversion.base_raw_custody_v4(p_root)c where c.product_id=p_product;
 difference:=physical-owned;
 if difference=0 then return 0;end if;
 -- Only the existing private owning command may observe its intermediate
 -- Native physical transfer before the economic component hook. A GUC, role
 -- name, arbitrary backend or historical group cannot manufacture this lease.
 select coalesce(sum(case when e.mode='POST'and pc.status='POSTED'then -a.qty_pcs
  when e.mode='REVERSE'and pc.status='REVERSED'then a.qty_pcs else 0 end),0)into expected
 from cp7_sku_conversion.execution_v1 e
 join cp7_sku_conversion.valuation_quotes_v2 q on q.group_id=e.group_id
 join erp.product_conversions pc on exists(select 1 from cp7_sku_conversion.members_v1 m
   where m.group_id=e.group_id and m.conversion_id=pc.id)
  or(e.mode='POST'and pc.from_product_id=q.source_product_id and pc.to_product_id=q.target_product_id
   and pc.to_product_id=e.target_id and pc.location_id=q.location_id and pc.location_id=e.location_id
   and pc.qty_pcs=e.qty and pc.physical_at=e.physical_at
   and exists(select 1 from erp.be_execution_context_v1 b where b.backend_pid=e.backend_pid
    and b.transaction_id=e.transaction_id and b.request_id=pc.id))
 join erp.product_conversion_allocations a on a.conversion_id=pc.id
 join erp.fg_lots l on l.id=a.source_lot_id
 where e.backend_pid=pg_backend_pid()and e.transaction_id=txid_current()
  and a.source_lot_id=p_root and l.product_id=p_product
  and(exists(select 1 from cp7_sku_conversion.members_v1 m where m.group_id=e.group_id and m.conversion_id=pc.id)
   or(a.source_lot_id=e.source_lot_id and a.qty_pcs=e.qty));
 if difference is distinct from expected or expected=0 then raise exception 'CP7_SKU_BASE_MONEY_CUSTODY_NOT_EXACT';end if;
 select h.hpp_per_pcs into strict native_unit from erp.hpp_versions h where h.lot_id=p_root and h.is_current;
 return difference*(native_unit-unit);
end $$;

create function cp7_sku_conversion.base_scope_correction_v4(p_product uuid)returns numeric
language plpgsql stable security definer set search_path=''as $$
declare c record;answer numeric:=0;
begin
 for c in select e.root_lot_id,sum(e.units_delta)units,sum(e.amount_delta)amount,h.hpp_per_pcs
  from cp7_sku_conversion.base_money_events_v4 e join erp.hpp_versions h on h.lot_id=e.root_lot_id and h.is_current
  where e.product_id=p_product group by e.root_lot_id,h.hpp_per_pcs loop
  perform cp7_sku_conversion.base_current_unit_v4(c.root_lot_id,p_product);
  perform cp7_sku_conversion.base_transition_value_v4(c.root_lot_id,p_product);
  answer:=answer+c.amount-c.units*c.hpp_per_pcs;
 end loop;
 return answer;
end $$;

create function cp7_sku_conversion.ensure_base_money_v4(p_root uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
declare r record;cell record;
begin
 perform erp.require_internal();perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select l.*,h.id hpp_id,h.qty_basis_pcs,h.total_cost,h.cost_state into strict r
 from erp.fg_lots l join erp.hpp_versions h on h.lot_id=l.id and h.is_current where l.id=p_root;
 if r.po_id is not null then perform cp7_sku_conversion.base_current_unit_v4(p_root,r.product_id);return;end if;
 if exists(select 1 from cp7_sku_conversion.base_money_events_v4 where root_lot_id=p_root)then
  perform cp7_sku_conversion.base_current_unit_v4(p_root,r.product_id);
  for cell in select product_id from cp7_sku_conversion.base_money_cells_v4(p_root)
   union select product_id from cp7_sku_conversion.base_raw_custody_v4(p_root)loop
   perform cp7_sku_conversion.base_transition_value_v4(p_root,cell.product_id);
  end loop;
  return;end if;
 if r.lot_origin in('CONVERSION','VOIDED_PRODUCTION')or r.qty_basis_pcs<=0 or r.qty_basis_pcs<>r.initial_qty_pcs
  or r.total_cost<0 or r.total_cost::text in('NaN','Infinity','-Infinity')or r.cost_state='ESTIMATED'
  or exists(select 1 from cp7_sku_conversion.component_events_v2 where root_lot_id=p_root and source_type='SKU_CONVERSION')
  or exists(select 1 from erp.product_conversion_allocations a join erp.product_conversions c on c.id=a.conversion_id
   where a.source_lot_id=p_root and c.status='POSTED')then
  raise exception 'CP7_SKU_BASE_MONEY_UNADMITTED_PRIOR_CUSTODY';end if;
 insert into cp7_sku_conversion.base_money_events_v4(id,kind,source_id,root_lot_id,product_id,units_delta,amount_delta,source_proof,economic_date)
 values(gen_random_uuid(),'ORIGIN',r.hpp_id,p_root,r.product_id,r.qty_basis_pcs,round(r.total_cost,2),to_jsonb(r),
  (statement_timestamp()at time zone 'Asia/Jakarta')::date);
end $$;

create function cp7_sku_conversion.prepare_base_money_v4(p_preview jsonb)returns void
language plpgsql volatile security definer set search_path=''as $$
declare c record;
begin
 perform erp.require_internal();perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 for c in select *from cp7_sku_conversion.pool_components_v2((p_preview->>'source_product_id')::uuid,
  (p_preview->>'location_id')::uuid,'GRADE_A')where po_id is null and component_units>0 loop
  perform cp7_sku_conversion.ensure_base_money_v4(c.root_lot_id);
 end loop;
end $$;

create function cp7_sku_conversion.transfer_base_money_v4(p_group uuid,p_reverse boolean)returns void
language plpgsql volatile security definer set search_path=''as $$
declare q cp7_sku_conversion.valuation_quotes_v2%rowtype;c record;s record;sender uuid;receiver uuid;amount numeric;kind text;day date;
begin
 perform erp.require_internal();perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 select *into strict q from cp7_sku_conversion.valuation_quotes_v2 where group_id=p_group;
 sender:=case when p_reverse then q.target_product_id else q.source_product_id end;
 receiver:=case when p_reverse then q.source_product_id else q.target_product_id end;
 kind:=case when p_reverse then 'INVERSE_TRANSFER'else 'TRANSFER'end;
 day:=(case when p_reverse then statement_timestamp()else q.physical_at end at time zone 'Asia/Jakarta')::date;
 for c in select *from cp7_sku_conversion.valuation_contributors_v2 where group_id=p_group and po_id is null order by root_lot_id loop
  perform cp7_sku_conversion.base_current_unit_v4(c.root_lot_id,sender);
  select *into strict s from cp7_sku_conversion.base_money_cells_v4(c.root_lot_id)where product_id=sender;
  amount:=case when p_reverse then round(c.transfer_units*s.amount/s.units,2)else c.transfer_value end;
  if c.transfer_units<=0 or c.transfer_units>s.units or amount<0 or amount>s.amount
   or(c.transfer_units=s.units and amount<>s.amount)then raise exception 'CP7_SKU_BASE_MONEY_TRANSFER_CAPACITY';end if;
  insert into cp7_sku_conversion.base_money_events_v4(id,kind,source_id,root_lot_id,product_id,units_delta,amount_delta,source_proof,economic_date)
  values(gen_random_uuid(),kind,p_group,c.root_lot_id,sender,-c.transfer_units,-amount,jsonb_build_object('contributor',to_jsonb(c),'current_transfer',amount),day),
        (gen_random_uuid(),kind,p_group,c.root_lot_id,receiver,c.transfer_units,amount,jsonb_build_object('contributor',to_jsonb(c),'current_transfer',amount),day);
 end loop;
end $$;

create function cp7_sku_conversion.capture_base_price_v4(p_root uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare product uuid;h jsonb;cells jsonb;events jsonb;
begin
 perform cp7_sku_conversion.ensure_base_money_v4(p_root);
 select l.product_id,to_jsonb(v)into strict product,h from erp.fg_lots l join erp.hpp_versions v on v.lot_id=l.id and v.is_current where l.id=p_root;
 perform cp7_sku_conversion.base_current_unit_v4(p_root,product);
 select jsonb_agg(to_jsonb(cell)order by cell.product_id)into cells from cp7_sku_conversion.base_money_cells_v4(p_root)cell;
 select jsonb_agg(to_jsonb(e)order by e.id)into events from cp7_sku_conversion.base_money_events_v4 e where e.root_lot_id=p_root;
 return jsonb_build_object('root',p_root,'hpp',h,'cells',cells,'events',events,'backend_pid',pg_backend_pid(),'transaction_id',txid_current());
end $$;

create function cp7_sku_conversion.reprice_base_money_v4(p_root uuid,p_date date,p_before jsonb)returns void
language plpgsql volatile security definer set search_path=''as $$
declare h record;c record;cells jsonb;events jsonb;new_total numeric;old_total numeric;cumulative numeric:=0;prior numeric:=0;target numeric;delta numeric;
begin
 perform erp.require_internal();perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if p_before->>'root'is distinct from p_root::text or(p_before->>'backend_pid')::integer is distinct from pg_backend_pid()
  or(p_before->>'transaction_id')::bigint is distinct from txid_current()then raise exception 'CP7_SKU_BASE_PRICE_PROOF_REQUIRED';end if;
 select *into strict h from erp.hpp_versions where lot_id=p_root and is_current;
 select jsonb_agg(to_jsonb(cell)order by cell.product_id)into cells from cp7_sku_conversion.base_money_cells_v4(p_root)cell;
 select jsonb_agg(to_jsonb(e)order by e.id)into events from cp7_sku_conversion.base_money_events_v4 e where e.root_lot_id=p_root;
 old_total:=round((p_before->'hpp'->>'total_cost')::numeric,2);new_total:=round(h.total_cost,2);
 if cells is distinct from p_before->'cells'or events is distinct from p_before->'events'
  or h.qty_basis_pcs is distinct from(p_before->'hpp'->>'qty_basis_pcs')::integer
  or h.supersedes_id::text is distinct from p_before->'hpp'->>'id'
  or new_total<0 or new_total::text in('NaN','Infinity','-Infinity')or h.cost_state='ESTIMATED'
  or old_total is distinct from(select sum(x.amount)from cp7_sku_conversion.base_money_cells_v4(p_root)x)then
  raise exception 'CP7_SKU_BASE_PRICE_SOURCE_NOT_EXACT';end if;
 if new_total=old_total then return;end if;
 for c in select *from cp7_sku_conversion.base_money_cells_v4(p_root)order by product_id loop
  cumulative:=cumulative+c.units;target:=round(new_total*cumulative/h.qty_basis_pcs,2);delta:=target-prior-c.amount;prior:=target;
  if delta<>0 then
   insert into cp7_sku_conversion.base_money_events_v4(id,kind,source_id,root_lot_id,product_id,units_delta,amount_delta,source_proof,economic_date)
   values(gen_random_uuid(),'SOURCE_PRICE',h.id,p_root,c.product_id,0,delta,
    jsonb_build_object('old_hpp',p_before->'hpp','new_hpp',to_jsonb(h),'before_cell',to_jsonb(c),
     'prior_event_count',jsonb_array_length(events),'prior_event_digest',md5(events::text),'cumulative_units',cumulative,'cumulative_target',target),p_date);
  end if;
 end loop;
 if cumulative is distinct from h.qty_basis_pcs or prior is distinct from new_total then raise exception 'CP7_SKU_BASE_PRICE_CENTS_NOT_EXACT';end if;
end $$;

revoke all on function cp7_sku_conversion.base_money_cells_v4(uuid),cp7_sku_conversion.base_raw_custody_v4(uuid),
 cp7_sku_conversion.base_current_unit_v4(uuid,uuid),cp7_sku_conversion.base_transition_value_v4(uuid,uuid),
 cp7_sku_conversion.base_scope_correction_v4(uuid),cp7_sku_conversion.ensure_base_money_v4(uuid),
 cp7_sku_conversion.prepare_base_money_v4(jsonb),cp7_sku_conversion.transfer_base_money_v4(uuid,boolean),
 cp7_sku_conversion.capture_base_price_v4(uuid),cp7_sku_conversion.reprice_base_money_v4(uuid,date,jsonb)
 from public,anon,authenticated,service_role;
