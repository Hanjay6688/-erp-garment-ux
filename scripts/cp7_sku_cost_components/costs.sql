-- Separate cost units never add physical pieces. All roots exist at conversion
-- posting, including zero-cost roots that may receive a later invoice.
create table cp7_sku_conversion.cost_events_v3(
 id uuid primary key,
 source_type text not null check(source_type in('SKU_CONVERSION','SALE','SALES_RETURN')),
 source_id uuid not null,
 line_no integer not null check(line_no>0),
 phase text not null check(phase in('POST','REVERSE')),
 side text not null check(side in('SOURCE','TARGET','ORIGIN','POOL')),
 product_id uuid not null references erp.products(id),
 location_id uuid not null references erp.locations(id),
 quality_grade text not null check(quality_grade='GRADE_A'),
 root_lot_id uuid not null references erp.fg_lots(id),
 units_delta numeric(30,12) not null check(units_delta<>0),
 physical_at timestamptz not null,
 economic_date date not null,
 recorded_at timestamptz not null default statement_timestamp(),
 supersedes_event_id uuid references cp7_sku_conversion.cost_events_v3(id),
 check((source_type='SKU_CONVERSION'and side in('SOURCE','TARGET','ORIGIN'))
  or(source_type<>'SKU_CONVERSION'and side='POOL')),
 check((phase='POST'and supersedes_event_id is null)or(phase='REVERSE'and supersedes_event_id is not null)),
 unique(source_type,source_id,line_no,phase,side),unique(supersedes_event_id)
);

create table cp7_sku_conversion.cost_contributors_v3(
 group_id uuid not null references cp7_sku_conversion.valuation_quotes_v2(group_id),
 line_no integer not null check(line_no>0),
 root_lot_id uuid not null references erp.fg_lots(id),
 po_id uuid references erp.production_orders(id),
 hpp_version_id uuid not null references erp.hpp_versions(id),
 pool_component_units numeric(30,12) not null check(pool_component_units>0),
 transfer_units numeric(30,12) not null check(transfer_units>0),
 unit_value numeric(24,12) not null,
 contributed_value numeric(24,6) not null,
 transfer_value numeric(24,2) not null,
 primary key(group_id,line_no),unique(group_id,root_lot_id),
 check(contributed_value=round(pool_component_units*unit_value,6))
);

create table cp7_sku_conversion.sale_cost_components_v3(
 sale_stock_allocation_id uuid not null references cp7_sku_conversion.sale_allocation_values_v2(sale_stock_allocation_id),
 line_no integer not null check(line_no>0),
 root_lot_id uuid not null references erp.fg_lots(id),
 po_id uuid references erp.production_orders(id),
 component_units numeric(30,12) not null check(component_units>0),
 booked_value numeric(24,2) not null,
 primary key(sale_stock_allocation_id,line_no),unique(sale_stock_allocation_id,root_lot_id)
);

create table cp7_sku_conversion.return_cost_components_v3(
 sales_return_item_id uuid not null references cp7_sku_conversion.sales_return_values_v2(sales_return_item_id),
 line_no integer not null check(line_no>0),
 root_lot_id uuid not null references erp.fg_lots(id),
 po_id uuid references erp.production_orders(id),
 component_units numeric(30,12) not null check(component_units>0),
 booked_value numeric(24,2) not null,
 primary key(sales_return_item_id,line_no),unique(sales_return_item_id,root_lot_id)
);

create trigger cost_events_immutable_v3 before update or delete on cp7_sku_conversion.cost_events_v3
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger cost_contributors_immutable_v3 before update or delete on cp7_sku_conversion.cost_contributors_v3
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger sale_cost_components_immutable_v3 before update or delete on cp7_sku_conversion.sale_cost_components_v3
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger return_cost_components_immutable_v3 before update or delete on cp7_sku_conversion.return_cost_components_v3
 for each row execute function cp7_sku_conversion.immutable_v1();
alter table cp7_sku_conversion.cost_events_v3 enable row level security;
alter table cp7_sku_conversion.cost_contributors_v3 enable row level security;
alter table cp7_sku_conversion.sale_cost_components_v3 enable row level security;
alter table cp7_sku_conversion.return_cost_components_v3 enable row level security;
revoke all on cp7_sku_conversion.cost_events_v3,cp7_sku_conversion.cost_contributors_v3,
 cp7_sku_conversion.sale_cost_components_v3,cp7_sku_conversion.return_cost_components_v3 from public,anon,authenticated,service_role;

create function cp7_sku_conversion.cost_root_v3(p_lot uuid)
returns table(root_lot_id uuid,po_id uuid,hpp_version_id uuid,unit_value numeric,source_revision jsonb)
language plpgsql stable security definer set search_path=''as $$
declare r record;n integer;
begin
 select count(*)into n from erp.product_conversion_allocations a where a.destination_lot_id=p_lot;
 if n<>1 then raise exception 'CP7_SKU_COST_ROOT_ALLOCATION_NOT_UNIQUE';end if;
 select a.*,c.status conversion_status,l.po_id,h.id version_id,h.cost_state,
  erp.be_allocation_extra_v1(a.id)extra
 into strict r from erp.product_conversion_allocations a
 join erp.product_conversions c on c.id=a.conversion_id
 join erp.fg_lots l on l.id=a.destination_lot_id
 left join erp.hpp_versions h on h.lot_id=l.id and h.is_current where a.destination_lot_id=p_lot;
 if r.qty_pcs<=0 or r.extra is null or r.extra::text in('NaN','Infinity','-Infinity')
  or r.version_id is null or r.cost_state='ESTIMATED' or r.conversion_status not in('POSTED','REVERSED')
  or erp.bd_lot_laundry_unknown_v1(p_lot)
  or(r.po_id is not null and not exists(select 1 from erp.get_hpp_completeness(r.po_id)c where c.pending_reason_count=0))then
  raise exception 'CP7_SKU_POOL_HPP_UNKNOWN: seluruh komponen ekonomi termasuk reservasi harus diketahui';end if;
 return query select p_lot,r.po_id,r.version_id,(r.extra/r.qty_pcs)::numeric,
  jsonb_build_object('allocation',to_jsonb(r),'sources',(select coalesce(jsonb_agg(to_jsonb(s)order by s.document_id),'[]')
   from erp.be_conversion_cost_sources_v1 s where s.conversion_id=r.conversion_id),
   'events',(select coalesce(jsonb_agg(to_jsonb(e)order by e.id),'[]')from erp.be_conversion_cost_events_v1 e
    join erp.be_conversion_cost_sources_v1 s on s.document_id=e.document_id where s.conversion_id=r.conversion_id));
end $$;

create function cp7_sku_conversion.pool_cost_components_v3(p_product uuid,p_location uuid,p_grade text default 'GRADE_A')
returns table(line_no integer,root_lot_id uuid,po_id uuid,hpp_version_id uuid,component_units numeric,unit_value numeric,value numeric,source_revision jsonb)
language plpgsql stable security definer set search_path=''as $$
begin
 if exists(select 1 from cp7_sku_conversion.cost_events_v3 e
  where e.product_id=p_product and e.location_id=p_location and e.quality_grade=p_grade
  and(e.source_type<>'SALE'or exists(select 1 from erp.sales_headers h where h.id=e.source_id and h.status in('POSTED','PARTIAL_PAID','PAID','REVERSED')))
  and(e.source_type<>'SALES_RETURN'or exists(select 1 from erp.sales_returns h where h.id=e.source_id and h.status in('POSTED','REVERSED')))
  group by e.root_lot_id having sum(e.units_delta)< -0.000000000001)then
  raise exception 'CP7_SKU_COST_COMPONENT_CAPACITY';end if;
 return query with amounts as(
  select e.root_lot_id,sum(e.units_delta)::numeric units from cp7_sku_conversion.cost_events_v3 e
  where e.product_id=p_product and e.location_id=p_location and e.quality_grade=p_grade
  and(e.source_type<>'SALE'or exists(select 1 from erp.sales_headers h where h.id=e.source_id and h.status in('POSTED','PARTIAL_PAID','PAID','REVERSED')))
  and(e.source_type<>'SALES_RETURN'or exists(select 1 from erp.sales_returns h where h.id=e.source_id and h.status in('POSTED','REVERSED')))
  group by e.root_lot_id having sum(e.units_delta)>0.000000000001
 )select row_number()over(order by a.root_lot_id)::integer,a.root_lot_id,r.po_id,r.hpp_version_id,a.units,r.unit_value,
  round(a.units*r.unit_value,6)::numeric,r.source_revision
 from amounts a cross join lateral cp7_sku_conversion.cost_root_v3(a.root_lot_id)r order by a.root_lot_id;
end $$;

create function cp7_sku_conversion.cost_scope_value_v3(p_product uuid,p_po uuid,p_kind text)
returns numeric language plpgsql stable security definer set search_path=''as $$
declare v numeric;
begin
 if p_kind not in('OWNED','CONVERSION','SOLD','RETURNED')then raise exception 'CP7_SKU_COST_SCOPE_KIND';end if;
 with entries as(
  select e.product_id,e.root_lot_id,e.units_delta units from cp7_sku_conversion.cost_events_v3 e
  where(p_kind='OWNED'or(p_kind='CONVERSION'and e.source_type='SKU_CONVERSION'))
   and(e.source_type<>'SALE'or exists(select 1 from erp.sales_headers h where h.id=e.source_id and h.status in('POSTED','PARTIAL_PAID','PAID','REVERSED')))
   and(e.source_type<>'SALES_RETURN'or exists(select 1 from erp.sales_returns h where h.id=e.source_id and h.status in('POSTED','REVERSED')))
  union all select v.product_id,c.root_lot_id,c.component_units from cp7_sku_conversion.sale_cost_components_v3 c
   join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)
   join erp.sales_headers h on h.id=v.sale_id and h.status in('POSTED','PARTIAL_PAID','PAID')where p_kind='SOLD'
  union all select v.product_id,c.root_lot_id,c.component_units from cp7_sku_conversion.return_cost_components_v3 c
   join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
   join erp.sales_returns h on h.id=v.return_id and h.status='POSTED'where p_kind='RETURNED'
 ),totals as(
  select e.root_lot_id,sum(e.units)::numeric units from entries e join erp.fg_lots l on l.id=e.root_lot_id
  where(p_po is null and l.po_id is null and e.product_id=p_product)or l.po_id=p_po
  group by e.root_lot_id having abs(sum(e.units))>0.000000000001
 )select coalesce(sum(t.units*r.unit_value),0)into v from totals t
 cross join lateral cp7_sku_conversion.cost_root_v3(t.root_lot_id)r;
 return v;
end $$;

create function cp7_sku_conversion.return_cost_components_v3(p_allocation uuid,p_qty numeric,p_current_return uuid)
returns table(root_lot_id uuid,po_id uuid,component_units numeric,hpp_per_pcs numeric,hpp_version_id uuid)
language plpgsql stable security definer set search_path=''as $$
declare v_sold numeric;v_prior numeric;
begin
 perform erp.require_internal();
 if p_qty is null or p_qty<=0 or p_qty<>trunc(p_qty)or p_qty::text in('NaN','Infinity','-Infinity')then
  raise exception 'CP7_SKU_RETURN_COMPONENT_QTY_INVALID';end if;
 select v.qty_pcs into v_sold from cp7_sku_conversion.sale_allocation_values_v2 v where v.sale_stock_allocation_id=p_allocation;
 if not found then return;end if;
 select coalesce(sum(i.qty_pcs),0)into v_prior from erp.sales_return_items i join erp.sales_returns h on h.id=i.return_id
  where i.sale_stock_allocation_id=p_allocation and h.status='POSTED';
 if p_current_return is not null then v_prior:=v_prior+coalesce((select sum(v.qty_pcs)
  from cp7_sku_conversion.sales_return_values_v2 v where v.sale_stock_allocation_id=p_allocation and v.return_id=p_current_return),0);end if;
 if v_prior+p_qty>v_sold then raise exception 'CP7_SKU_RETURN_VALUE_EXCEEDS_SALE_ALLOCATION';end if;
 return query with prior as(
  select c.root_lot_id,sum(c.component_units)::numeric units from cp7_sku_conversion.return_cost_components_v3 c
  join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)join erp.sales_returns h on h.id=v.return_id
  where v.sale_stock_allocation_id=p_allocation and(h.status='POSTED'or h.id=p_current_return)group by c.root_lot_id
 ),planned as(
  select c.root_lot_id,c.po_id,(round((v_prior+p_qty)*c.component_units/v_sold,12)-coalesce(p.units,0))::numeric units
  from cp7_sku_conversion.sale_cost_components_v3 c left join prior p on p.root_lot_id=c.root_lot_id
  where c.sale_stock_allocation_id=p_allocation
 )select p.root_lot_id,p.po_id,p.units,r.unit_value,r.hpp_version_id from planned p
 cross join lateral cp7_sku_conversion.cost_root_v3(p.root_lot_id)r where p.units<>0 order by p.root_lot_id;
end $$;

create function cp7_sku_conversion.finalize_costs_v3(p_group uuid)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare q cp7_sku_conversion.valuation_quotes_v2%rowtype;
begin
 perform erp.require_internal();select *into strict q from cp7_sku_conversion.valuation_quotes_v2 where group_id=p_group;
 if exists(select 1 from cp7_sku_conversion.cost_events_v3 where source_type='SKU_CONVERSION'and source_id=p_group)then
  raise exception 'CP7_SKU_COST_ALREADY_FINALIZED';end if;
 insert into cp7_sku_conversion.cost_events_v3(id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,root_lot_id,units_delta,physical_at,economic_date)
 select gen_random_uuid(),'SKU_CONVERSION',p_group,c.line_no,'POST',side,
  case when side='SOURCE'then q.source_product_id else q.target_product_id end,q.location_id,q.quality_grade,c.root_lot_id,
  case when side='SOURCE'then-c.transfer_units else c.transfer_units end,q.physical_at,(q.physical_at at time zone 'Asia/Jakarta')::date
 from cp7_sku_conversion.cost_contributors_v3 c cross join(values('SOURCE'),('TARGET'))s(side)where c.group_id=p_group;
 insert into cp7_sku_conversion.cost_events_v3(id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,root_lot_id,units_delta,physical_at,economic_date)
 select gen_random_uuid(),'SKU_CONVERSION',p_group,row_number()over(order by a.id)::integer,'POST','ORIGIN',
  q.target_product_id,q.location_id,q.quality_grade,a.destination_lot_id,a.qty_pcs,q.physical_at,(q.physical_at at time zone 'Asia/Jakarta')::date
 from cp7_sku_conversion.members_v1 m join erp.product_conversion_allocations a on a.conversion_id=m.conversion_id where m.group_id=p_group;
 if q.qty_pcs is distinct from(select sum(units_delta)from cp7_sku_conversion.cost_events_v3
  where source_type='SKU_CONVERSION'and source_id=p_group and phase='POST'and side='ORIGIN')then
  raise exception 'CP7_SKU_ALL_NATIVE_COST_ALLOCATIONS_REQUIRED';end if;
end $$;

create function cp7_sku_conversion.post_sale_costs_v3(p_sale uuid)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
begin
 perform erp.require_internal();
 insert into cp7_sku_conversion.cost_events_v3(id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,root_lot_id,units_delta,physical_at,economic_date)
 select gen_random_uuid(),'SALE',p_sale,row_number()over(order by v.product_id,v.location_id,c.root_lot_id)::integer,'POST','POOL',
 v.product_id,v.location_id,v.quality_grade,c.root_lot_id,-sum(c.component_units),h.sale_date,(h.sale_date at time zone 'Asia/Jakarta')::date
 from cp7_sku_conversion.sale_cost_components_v3 c join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)
 join erp.sales_headers h on h.id=v.sale_id where v.sale_id=p_sale group by v.product_id,v.location_id,v.quality_grade,c.root_lot_id,h.sale_date;
end $$;

create function cp7_sku_conversion.post_return_costs_v3(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
begin
 perform erp.require_internal();
 insert into cp7_sku_conversion.cost_events_v3(id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,root_lot_id,units_delta,physical_at,economic_date)
 select gen_random_uuid(),'SALES_RETURN',p_return,row_number()over(order by v.product_id,v.location_id,c.root_lot_id)::integer,'POST','POOL',
 v.product_id,v.location_id,v.quality_grade,c.root_lot_id,sum(c.component_units),h.physical_at,(h.physical_at at time zone 'Asia/Jakarta')::date
 from cp7_sku_conversion.return_cost_components_v3 c join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
 join erp.sales_returns h on h.id=v.return_id where v.return_id=p_return group by v.product_id,v.location_id,v.quality_grade,c.root_lot_id,h.physical_at;
end $$;

create function cp7_sku_conversion.reverse_costs_v3(p_type text,p_source uuid)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
begin
 perform erp.require_internal();
 if exists(select 1 from cp7_sku_conversion.cost_events_v3 where source_type=p_type and source_id=p_source and phase='REVERSE')then
  raise exception 'CP7_SKU_COST_ALREADY_REVERSED';end if;
 insert into cp7_sku_conversion.cost_events_v3(id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,root_lot_id,units_delta,physical_at,economic_date,supersedes_event_id)
 select gen_random_uuid(),source_type,source_id,line_no,'REVERSE',side,product_id,location_id,quality_grade,root_lot_id,-units_delta,
  statement_timestamp(),(statement_timestamp()at time zone 'Asia/Jakarta')::date,id from cp7_sku_conversion.cost_events_v3
 where source_type=p_type and source_id=p_source and phase='POST'order by side,line_no;
 if exists(select 1 from cp7_sku_conversion.cost_events_v3 where source_type=p_type and source_id=p_source
  group by side,product_id,location_id,quality_grade,root_lot_id having sum(units_delta)<>0)then
  raise exception 'CP7_SKU_COST_REVERSE_NOT_EXACT';end if;
end $$;

revoke all on function cp7_sku_conversion.cost_root_v3(uuid),
 cp7_sku_conversion.pool_cost_components_v3(uuid,uuid,text),cp7_sku_conversion.cost_scope_value_v3(uuid,uuid,text),
 cp7_sku_conversion.return_cost_components_v3(uuid,numeric,uuid),cp7_sku_conversion.finalize_costs_v3(uuid),
 cp7_sku_conversion.post_sale_costs_v3(uuid),cp7_sku_conversion.post_return_costs_v3(uuid),
 cp7_sku_conversion.reverse_costs_v3(text,uuid)from public,anon,authenticated,service_role;
