-- Append-only economic valuation for SKU conversion. Physical lot selection
-- remains in the qualified Native conversion engine.

create table cp7_sku_conversion.valuation_quotes_v2(
 group_id uuid primary key references cp7_sku_conversion.groups_v1(request_id),
 source_product_id uuid not null references erp.products(id),
 target_product_id uuid not null references erp.products(id),
 location_id uuid not null references erp.locations(id),
 quality_grade text not null check(quality_grade='GRADE_A'),
 qty_pcs integer not null check(qty_pcs>0),
 physical_at timestamptz not null,
 source_before_qty numeric(20,6) not null check(source_before_qty>=qty_pcs),
 source_before_value numeric(24,6) not null check(source_before_value>=0),
 source_before_average numeric(24,12) not null check(source_before_average>=0),
 target_before_qty numeric(20,6) not null check(target_before_qty>=0),
 target_before_value numeric(24,6) not null check(target_before_value>=0),
 target_before_average numeric(24,12),
 transfer_value numeric(24,2) not null check(transfer_value>=0),
 valuation_revision text not null,
 recorded_at timestamptz not null default statement_timestamp(),
 check(target_before_qty>0 or target_before_average is null),
 check(target_before_qty=0 or target_before_average is not null),
 check(transfer_value=round(qty_pcs*source_before_average,2))
);

create table cp7_sku_conversion.valuation_contributors_v2(
 group_id uuid not null references cp7_sku_conversion.valuation_quotes_v2(group_id),
 line_no integer not null check(line_no>0),
 root_lot_id uuid not null references erp.fg_lots(id),
 po_id uuid references erp.production_orders(id),
 hpp_version_id uuid not null references erp.hpp_versions(id),
 pool_component_units numeric(30,12) not null check(pool_component_units>0),
 transfer_units numeric(30,12) not null check(transfer_units>0),
 unit_value numeric(24,12) not null check(unit_value>=0),
 contributed_value numeric(24,6) not null check(contributed_value>=0),
 transfer_value numeric(24,2) not null check(transfer_value>=0),
 primary key(group_id,line_no),
 unique(group_id,root_lot_id),
 check(contributed_value=round(pool_component_units*unit_value,6))
);

create table cp7_sku_conversion.valuation_postings_v2(
 group_id uuid not null references cp7_sku_conversion.valuation_quotes_v2(group_id),
 phase text not null check(phase in('POST','REVERSE')),
 native_value numeric(24,2) not null,
 transfer_value numeric(24,2) not null,
 correction_value numeric(24,2) not null,
 correction_journal_id uuid references erp.journal_entries(id),
 recorded_at timestamptz not null default statement_timestamp(),
 primary key(group_id,phase),
 check(correction_value=transfer_value-native_value),
 check((phase='POST' and native_value>=0 and transfer_value>=0)
    or(phase='REVERSE' and native_value<=0 and transfer_value<=0)),
 check(abs(correction_value)<=0.005 or correction_journal_id is not null)
);

create table cp7_sku_conversion.valuation_attributions_v2(
 group_id uuid not null references cp7_sku_conversion.valuation_quotes_v2(group_id),
 phase text not null check(phase in('POST','REVERSE','RECOST')),
 side text not null check(side in('SOURCE','TARGET')),
 line_no integer not null check(line_no>0),
 po_id uuid references erp.production_orders(id),
 product_id uuid not null references erp.products(id),
 effective_value_delta numeric(24,2) not null,
 legacy_value_delta numeric(24,2) not null,
 adjustment_delta numeric(24,2) not null,
 supersedes_phase text,
 recorded_at timestamptz not null default statement_timestamp(),
 primary key(group_id,phase,side,line_no),
 check(adjustment_delta=effective_value_delta-legacy_value_delta),
 check((phase='POST'and side='SOURCE'and effective_value_delta<=0)
    or(phase='POST'and side='TARGET'and effective_value_delta>=0)
    or phase in('REVERSE','RECOST'))
);

create table cp7_sku_conversion.sale_allocation_values_v2(
 sale_stock_allocation_id uuid primary key references erp.sale_stock_allocations(id),
 sale_id uuid not null references erp.sales_headers(id),
 product_id uuid not null references erp.products(id),
 lot_id uuid not null references erp.fg_lots(id),
 location_id uuid not null references erp.locations(id),
 quality_grade text not null check(quality_grade='GRADE_A'),
 qty_pcs integer not null check(qty_pcs>0),
 effective_value numeric(24,2) not null check(effective_value>=0),
 legacy_value numeric(24,2) not null check(legacy_value>=0),
 effective_unit_value numeric(24,12) not null check(effective_unit_value>=0),
 pool_revision text not null,
 recorded_at timestamptz not null default statement_timestamp(),
 check(effective_value=round(qty_pcs*effective_unit_value,2))
);

create table cp7_sku_conversion.sale_allocation_attributions_v2(
 sale_stock_allocation_id uuid not null references cp7_sku_conversion.sale_allocation_values_v2(sale_stock_allocation_id),
 line_no integer not null check(line_no>0),
 po_id uuid references erp.production_orders(id),
 product_id uuid not null references erp.products(id),
 location_id uuid not null references erp.locations(id),
 quality_grade text not null check(quality_grade='GRADE_A'),
 effective_value numeric(24,2) not null check(effective_value>=0),
 legacy_value numeric(24,2) not null check(legacy_value>=0),
 adjustment_delta numeric(24,2) not null,
 recorded_at timestamptz not null default statement_timestamp(),
 primary key(sale_stock_allocation_id,line_no),
 check(adjustment_delta=legacy_value-effective_value)
);

create table cp7_sku_conversion.sale_allocation_components_v2(
 sale_stock_allocation_id uuid not null references cp7_sku_conversion.sale_allocation_values_v2(sale_stock_allocation_id),
 line_no integer not null check(line_no>0),
 root_lot_id uuid not null references erp.fg_lots(id),
 po_id uuid references erp.production_orders(id),
 component_units numeric(30,12) not null check(component_units>0),
 booked_value numeric(24,2) not null check(booked_value>=0),
 primary key(sale_stock_allocation_id,line_no),
 unique(sale_stock_allocation_id,root_lot_id)
);

create table cp7_sku_conversion.sales_return_values_v2(
 sales_return_item_id uuid primary key references erp.sales_return_items(id),
 return_id uuid not null references erp.sales_returns(id),
 sale_stock_allocation_id uuid not null references cp7_sku_conversion.sale_allocation_values_v2(sale_stock_allocation_id),
 product_id uuid not null references erp.products(id),
 lot_id uuid not null references erp.fg_lots(id),
 location_id uuid not null references erp.locations(id),
 quality_grade text not null check(quality_grade='GRADE_A'),
 qty_pcs integer not null check(qty_pcs>0),
 effective_value numeric(24,2) not null check(effective_value>=0),
 legacy_value numeric(24,2) not null check(legacy_value>=0),
 effective_unit_value numeric(24,12) not null check(effective_unit_value>=0),
 recorded_at timestamptz not null default statement_timestamp(),
 check(effective_value=round(qty_pcs*effective_unit_value,2))
);

create table cp7_sku_conversion.sales_return_attributions_v2(
 sales_return_item_id uuid not null references cp7_sku_conversion.sales_return_values_v2(sales_return_item_id),
 line_no integer not null check(line_no>0),
 po_id uuid references erp.production_orders(id),
 product_id uuid not null references erp.products(id),
 location_id uuid not null references erp.locations(id),
 quality_grade text not null check(quality_grade='GRADE_A'),
 effective_value numeric(24,2) not null check(effective_value>=0),
 legacy_value numeric(24,2) not null check(legacy_value>=0),
 adjustment_delta numeric(24,2) not null,
 recorded_at timestamptz not null default statement_timestamp(),
 primary key(sales_return_item_id,line_no),
 check(adjustment_delta=effective_value-legacy_value)
);

create table cp7_sku_conversion.sales_return_components_v2(
 sales_return_item_id uuid not null references cp7_sku_conversion.sales_return_values_v2(sales_return_item_id),
 line_no integer not null check(line_no>0),
 root_lot_id uuid not null references erp.fg_lots(id),
 po_id uuid references erp.production_orders(id),
 component_units numeric(30,12) not null check(component_units>0),
 booked_value numeric(24,2) not null check(booked_value>=0),
 primary key(sales_return_item_id,line_no),
 unique(sales_return_item_id,root_lot_id)
);

create table cp7_sku_conversion.valuation_events_v2(
 id uuid primary key,
 group_id uuid references cp7_sku_conversion.valuation_quotes_v2(group_id),
 source_type text not null check(source_type in('SKU_CONVERSION','SALE','SALES_RETURN','RECOST')),
 source_id uuid not null,
 line_no integer not null check(line_no>0),
 phase text not null check(phase in('POST','REVERSE','RECOST')),
 side text not null check(side in('SOURCE','TARGET','POOL')),
 product_id uuid not null references erp.products(id),
 location_id uuid not null references erp.locations(id),
 quality_grade text not null check(quality_grade='GRADE_A'),
 qty_delta numeric(20,6) not null,
 effective_value_delta numeric(24,6) not null,
 legacy_value_delta numeric(24,6) not null,
 adjustment_delta numeric(24,6) not null,
 physical_at timestamptz not null,
 economic_date date not null,
 recorded_at timestamptz not null default statement_timestamp(),
 supersedes_event_id uuid references cp7_sku_conversion.valuation_events_v2(id),
 check(adjustment_delta=effective_value_delta-legacy_value_delta),
 check((source_type='SKU_CONVERSION'and group_id=source_id and side in('SOURCE','TARGET'))
    or(source_type<>'SKU_CONVERSION'and group_id is null and side='POOL')),
 check((source_type='SKU_CONVERSION'and phase='POST' and side='SOURCE' and qty_delta<0 and effective_value_delta<=0)
    or(source_type='SKU_CONVERSION'and phase='POST' and side='TARGET' and qty_delta>0 and effective_value_delta>=0)
    or(source_type<>'SKU_CONVERSION'and phase='POST'and side='POOL')
    or phase in('REVERSE','RECOST'))
);
create unique index valuation_events_original_v2 on cp7_sku_conversion.valuation_events_v2(source_type,source_id,line_no,phase,side)
 where supersedes_event_id is null;
create unique index valuation_events_recost_v2 on cp7_sku_conversion.valuation_events_v2(source_type,source_id,line_no,phase,side,supersedes_event_id)
 where supersedes_event_id is not null;

-- Physical movements remain Native/FIFO. These immutable rows are only the
-- economic-component correction needed to make each pool proportional.
create table cp7_sku_conversion.component_events_v2(
 id uuid primary key,
 group_id uuid references cp7_sku_conversion.valuation_quotes_v2(group_id),
 source_type text not null check(source_type in('SKU_CONVERSION','SALE','SALES_RETURN')),
 source_id uuid not null,
 line_no integer not null check(line_no>0),
 phase text not null check(phase in('POST','REVERSE')),
 side text not null check(side in('SOURCE','TARGET','POOL')),
 product_id uuid not null references erp.products(id),
 location_id uuid not null references erp.locations(id),
 quality_grade text not null check(quality_grade='GRADE_A'),
 root_lot_id uuid not null references erp.fg_lots(id),
 units_delta numeric(30,12) not null check(units_delta<>0),
 physical_at timestamptz not null,
 economic_date date not null,
 recorded_at timestamptz not null default statement_timestamp(),
 supersedes_event_id uuid references cp7_sku_conversion.component_events_v2(id),
 check((source_type='SKU_CONVERSION'and group_id=source_id and side in('SOURCE','TARGET'))
    or(source_type<>'SKU_CONVERSION'and group_id is null and side='POOL'))
);
create unique index component_events_original_v2 on cp7_sku_conversion.component_events_v2(source_type,source_id,line_no,phase,side)
 where supersedes_event_id is null;
create unique index component_events_reverse_v2 on cp7_sku_conversion.component_events_v2(source_type,source_id,line_no,phase,side,supersedes_event_id)
 where supersedes_event_id is not null;

create trigger valuation_quotes_immutable_v2 before update or delete on cp7_sku_conversion.valuation_quotes_v2
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger valuation_contributors_immutable_v2 before update or delete on cp7_sku_conversion.valuation_contributors_v2
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger valuation_postings_immutable_v2 before update or delete on cp7_sku_conversion.valuation_postings_v2
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger valuation_attributions_immutable_v2 before update or delete on cp7_sku_conversion.valuation_attributions_v2
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger sale_allocation_values_immutable_v2 before update or delete on cp7_sku_conversion.sale_allocation_values_v2
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger sale_allocation_attributions_immutable_v2 before update or delete on cp7_sku_conversion.sale_allocation_attributions_v2
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger sale_allocation_components_immutable_v2 before update or delete on cp7_sku_conversion.sale_allocation_components_v2
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger sales_return_values_immutable_v2 before update or delete on cp7_sku_conversion.sales_return_values_v2
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger sales_return_attributions_immutable_v2 before update or delete on cp7_sku_conversion.sales_return_attributions_v2
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger sales_return_components_immutable_v2 before update or delete on cp7_sku_conversion.sales_return_components_v2
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger valuation_events_immutable_v2 before update or delete on cp7_sku_conversion.valuation_events_v2
 for each row execute function cp7_sku_conversion.immutable_v1();
create trigger component_events_immutable_v2 before update or delete on cp7_sku_conversion.component_events_v2
 for each row execute function cp7_sku_conversion.immutable_v1();

alter table cp7_sku_conversion.valuation_quotes_v2 enable row level security;
alter table cp7_sku_conversion.valuation_contributors_v2 enable row level security;
alter table cp7_sku_conversion.valuation_postings_v2 enable row level security;
alter table cp7_sku_conversion.valuation_attributions_v2 enable row level security;
alter table cp7_sku_conversion.sale_allocation_values_v2 enable row level security;
alter table cp7_sku_conversion.sale_allocation_attributions_v2 enable row level security;
alter table cp7_sku_conversion.sale_allocation_components_v2 enable row level security;
alter table cp7_sku_conversion.sales_return_values_v2 enable row level security;
alter table cp7_sku_conversion.sales_return_attributions_v2 enable row level security;
alter table cp7_sku_conversion.sales_return_components_v2 enable row level security;
alter table cp7_sku_conversion.valuation_events_v2 enable row level security;
alter table cp7_sku_conversion.component_events_v2 enable row level security;
create policy valuation_quotes_deny_v2 on cp7_sku_conversion.valuation_quotes_v2 for all using(false) with check(false);
create policy valuation_contributors_deny_v2 on cp7_sku_conversion.valuation_contributors_v2 for all using(false) with check(false);
create policy valuation_postings_deny_v2 on cp7_sku_conversion.valuation_postings_v2 for all using(false) with check(false);
create policy valuation_attributions_deny_v2 on cp7_sku_conversion.valuation_attributions_v2 for all using(false) with check(false);
create policy sale_allocation_values_deny_v2 on cp7_sku_conversion.sale_allocation_values_v2 for all using(false) with check(false);
create policy sale_allocation_attributions_deny_v2 on cp7_sku_conversion.sale_allocation_attributions_v2 for all using(false) with check(false);
create policy sale_allocation_components_deny_v2 on cp7_sku_conversion.sale_allocation_components_v2 for all using(false) with check(false);
create policy sales_return_values_deny_v2 on cp7_sku_conversion.sales_return_values_v2 for all using(false) with check(false);
create policy sales_return_attributions_deny_v2 on cp7_sku_conversion.sales_return_attributions_v2 for all using(false) with check(false);
create policy sales_return_components_deny_v2 on cp7_sku_conversion.sales_return_components_v2 for all using(false) with check(false);
create policy valuation_events_deny_v2 on cp7_sku_conversion.valuation_events_v2 for all using(false) with check(false);
create policy component_events_deny_v2 on cp7_sku_conversion.component_events_v2 for all using(false) with check(false);

create function cp7_sku_conversion.status_component_reverse_v2()returns trigger
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare v_type text;v_id uuid;v_components boolean;v_values boolean;
begin
 if old.status is not distinct from new.status or new.status is distinct from 'REVERSED'then return new;end if;
 if tg_table_schema<>'erp'or tg_table_name not in('sales_headers','sales_returns')then raise exception 'CP7_SKU_COMPONENT_TRIGGER_SCOPE';end if;
 v_type:=case when tg_table_name='sales_headers'then'SALE'else'SALES_RETURN'end;v_id:=new.id;
 select exists(select 1 from cp7_sku_conversion.component_events_v2 where source_type=v_type and source_id=v_id and phase='POST')into v_components;
 select exists(select 1 from cp7_sku_conversion.valuation_events_v2 where source_type=v_type and source_id=v_id and phase='POST')into v_values;
 if not v_components and not v_values then return new;end if;
 if exists(select 1 from cp7_sku_conversion.component_events_v2 where source_type=v_type and source_id=v_id and phase='REVERSE')
 or exists(select 1 from cp7_sku_conversion.valuation_events_v2 where source_type=v_type and source_id=v_id and phase='REVERSE')then
  raise exception 'CP7_SKU_COMPONENT_ALREADY_REVERSED';end if;
 if v_components then
  insert into cp7_sku_conversion.component_events_v2(id,group_id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,root_lot_id,units_delta,physical_at,economic_date,supersedes_event_id)
  select gen_random_uuid(),null,source_type,source_id,line_no,'REVERSE',side,product_id,location_id,quality_grade,root_lot_id,-units_delta,
   statement_timestamp(),(statement_timestamp()at time zone 'Asia/Jakarta')::date,id
  from cp7_sku_conversion.component_events_v2 where source_type=v_type and source_id=v_id and phase='POST'order by line_no;
 end if;
 if v_values then
  insert into cp7_sku_conversion.valuation_events_v2(id,group_id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,qty_delta,effective_value_delta,legacy_value_delta,adjustment_delta,physical_at,economic_date,supersedes_event_id)
  select gen_random_uuid(),null,source_type,source_id,line_no,'REVERSE',side,product_id,location_id,quality_grade,-qty_delta,-effective_value_delta,-legacy_value_delta,-adjustment_delta,
   statement_timestamp(),(statement_timestamp()at time zone 'Asia/Jakarta')::date,id
  from cp7_sku_conversion.valuation_events_v2 where source_type=v_type and source_id=v_id and phase='POST'order by line_no;
 end if;
 if exists(select 1 from cp7_sku_conversion.component_events_v2 where source_type=v_type and source_id=v_id
  group by product_id,location_id,quality_grade,root_lot_id having abs(sum(units_delta))>0.000000000001)then
  raise exception 'CP7_SKU_COMPONENT_STATUS_REVERSE_NOT_EXACT';end if;
 if exists(select 1 from cp7_sku_conversion.valuation_events_v2 where source_type=v_type and source_id=v_id
  group by product_id,location_id,quality_grade having abs(sum(qty_delta))>0.000000000001 or abs(sum(effective_value_delta))>0.001
   or abs(sum(legacy_value_delta))>0.001 or abs(sum(adjustment_delta))>0.001)then
  raise exception 'CP7_SKU_VALUE_STATUS_REVERSE_NOT_EXACT';end if;
 return new;
end $$;
create trigger sku_component_sale_reverse_v2 after update of status on erp.sales_headers
 for each row execute function cp7_sku_conversion.status_component_reverse_v2();
create trigger sku_component_return_reverse_v2 after update of status on erp.sales_returns
 for each row execute function cp7_sku_conversion.status_component_reverse_v2();

create function cp7_sku_conversion.pool_components_v2(p_product uuid,p_location uuid,p_grade text default 'GRADE_A')
returns table(line_no integer,root_lot_id uuid,po_id uuid,hpp_version_id uuid,component_units numeric,unit_value numeric,value numeric)
language sql stable security definer set search_path=''as $$
 with physical as materialized(
  select l.id root_lot_id,
   (coalesce(sum(m.qty_signed),0)+coalesce(sum(abs(m.qty_signed))filter(where m.movement_type='SALE_RESERVE'and not exists(
    select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id and rv.physical_at<=statement_timestamp())),0))::numeric units
  from erp.fg_lots l join erp.fg_stock_movements m on m.lot_id=l.id and m.product_id=p_product
   and m.location_id=p_location and m.quality_grade=p_grade and m.physical_at<=statement_timestamp()
  where l.product_id=p_product and l.lot_origin<>'VOIDED_PRODUCTION'
  group by l.id
 ), entries as(
  select root_lot_id,units from physical
  union all
  select e.root_lot_id,e.units_delta from cp7_sku_conversion.component_events_v2 e
  where e.product_id=p_product and e.location_id=p_location and e.quality_grade=p_grade
 ), totals as(
  select root_lot_id,sum(units)::numeric units from entries group by root_lot_id
  having abs(sum(units))>0.000000000001
 ), valued as(
  select t.root_lot_id,l.po_id,h.id hpp_version_id,t.units component_units,h.hpp_per_pcs unit_value,
   round(t.units*h.hpp_per_pcs,6)::numeric value
  from totals t join erp.fg_lots l on l.id=t.root_lot_id
  left join erp.hpp_versions h on h.lot_id=t.root_lot_id and h.is_current
 )
 select row_number()over(order by root_lot_id)::integer,root_lot_id,po_id,hpp_version_id,component_units,unit_value,value
 from valued order by root_lot_id
$$;

create function cp7_sku_conversion.pool_attribution_v2(p_product uuid,p_location uuid,p_grade text default 'GRADE_A')
returns table(line_no integer,po_id uuid,value numeric,base_value numeric,adjustment numeric)
language sql stable security definer set search_path=''as $$
 with components as(
  select po_id,sum(value)::numeric value from cp7_sku_conversion.pool_components_v2(p_product,p_location,p_grade)
  group by po_id
 ), numbered as(
  select row_number()over(order by po_id nulls last)::integer line_no,po_id,round(value,6)::numeric value
  from components
 )
 select line_no,po_id,value,value base_value,0::numeric adjustment from numbered where abs(value)>0.000001
$$;

create function cp7_sku_conversion.pool_quote_v2(
 p_product uuid,p_location uuid,p_grade text default 'GRADE_A'
) returns jsonb
language plpgsql stable security definer set search_path='' set timezone='UTC' as $$
declare v_qty numeric(20,6);v_base numeric(24,6);v_adjust numeric(24,6);v_value numeric(24,6);v_attr numeric(24,6);v_unknown boolean;v_revision text;
begin
 if p_product is null or p_location is null or p_grade is distinct from 'GRADE_A' then raise exception 'CP7_SKU_VALUE_SCOPE_REQUIRED';end if;
 with components as materialized(
  select c.*,h.cost_state,l.po_id root_po_id
  from cp7_sku_conversion.pool_components_v2(p_product,p_location,p_grade)c
  join erp.fg_lots l on l.id=c.root_lot_id
  left join erp.hpp_versions h on h.id=c.hpp_version_id
 ), totals as(
  select coalesce(sum(component_units),0)::numeric qty,coalesce(sum(value),0)::numeric value,
   coalesce(bool_or(component_units< -0.000000000001 or hpp_version_id is null or unit_value is null or cost_state='ESTIMATED'
    or erp.bd_lot_laundry_unknown_v1(root_lot_id)
    or(root_po_id is not null and not exists(select 1 from erp.get_hpp_completeness(root_po_id)z where z.pending_reason_count=0))),false) unknown
  from components
 )select qty,round(value,6),unknown into v_qty,v_value,v_unknown from totals;
 if v_unknown then raise exception 'CP7_SKU_POOL_HPP_UNKNOWN: seluruh komponen ekonomi termasuk reservasi harus diketahui';end if;
 v_base:=v_value;v_adjust:=0;
 if v_value<0 then raise exception 'CP7_SKU_POOL_VALUE_NEGATIVE: nilai efektif persediaan tidak boleh negatif';end if;
 select coalesce(sum(a.value),0)into v_attr from cp7_sku_conversion.pool_attribution_v2(p_product,p_location,p_grade)a;
 if round(v_attr,6)is distinct from v_value then raise exception 'CP7_SKU_POOL_ATTRIBUTION_MISMATCH';end if;
 select md5(jsonb_build_object('product',p_product,'location',p_location,'grade',p_grade,'qty',v_qty,'base',v_base,'adjust',v_adjust,
  'components',(select coalesce(jsonb_agg(to_jsonb(c)order by c.root_lot_id),'[]'::jsonb)
   from cp7_sku_conversion.pool_components_v2(p_product,p_location,p_grade)c),
  'events',(select coalesce(jsonb_agg(to_jsonb(e)order by e.recorded_at,e.id),'[]'::jsonb)from cp7_sku_conversion.valuation_events_v2 e
   where e.product_id=p_product and e.location_id=p_location and e.quality_grade=p_grade))::text) into v_revision;
 return jsonb_build_object('state',case when v_qty=0 then 'EMPTY' else 'KNOWN'end,'qty',v_qty::text,'value',v_value::text,
  'average',case when v_qty>0 then (v_value/v_qty)::text end,'base_value',v_base::text,'adjustment',v_adjust::text,
  'reserved_included',true,'basis','SKU_LOCATION_GRADE_MOVING_AVERAGE_V2','revision',v_revision);
end $$;

create function cp7_sku_conversion.position_value_v2(p_product uuid,p_location uuid,p_grade text,p_qty numeric)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare q jsonb;v numeric;
begin
 perform erp.require_permission('finance.hpp.view');
 if p_qty is null or p_qty<0 or p_qty::text in('NaN','Infinity','-Infinity')then raise exception 'CP7_SKU_POSITION_QTY_INVALID';end if;
 begin
  q:=cp7_sku_conversion.pool_quote_v2(p_product,p_location,p_grade);
 exception when sqlstate 'P0001'then
  if sqlerrm<>'CP7_SKU_POOL_HPP_UNKNOWN: seluruh komponen ekonomi termasuk reservasi harus diketahui'then raise;end if;
  q:=jsonb_build_object('state','UNKNOWN');
 end;
 -- A depleted or incomplete pool has no current unit cost. Do not invent
 -- zero, hide unrelated failures, or prevent the physical card from opening.
 v:=case when q->>'state'='KNOWN'then(q->>'average')::numeric end;
 return jsonb_build_object('state',case when v is null then'UNKNOWN'else'KNOWN'end,
  'hpp_version_id',null,'hpp_version',null,'cost_state',null,'calculated_at',null,
  'unit_cost',case when v is not null then round(v,6)::text end,
  'value',case when v is not null then round(p_qty*v,6)::text end,
  'basis','SKU_LOCATION_GRADE_MOVING_AVERAGE_V2','pool_revision',q->>'revision','reserved_included',true);
end $$;

create function cp7_sku_conversion.prepare_sale_values_v2(p_sale uuid) returns void
language plpgsql volatile security definer set search_path='' set timezone='UTC' as $$
declare pool record;a record;q jsonb;v_average numeric;v_effective numeric(24,2);v_prior numeric(24,2);v_total_effective numeric(24,2);v_total_legacy numeric(24,2);v_qty integer;v_line integer:=0;
begin
 perform erp.require_internal();
 if exists(select 1 from cp7_sku_conversion.sale_allocation_values_v2 where sale_id=p_sale)then raise exception 'CP7_SKU_SALE_VALUE_ALREADY_PREPARED';end if;
 for pool in select i.product_id,a.location_id,sum(a.qty_pcs)::integer qty
  from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
  where i.sale_id=p_sale group by i.product_id,a.location_id order by i.product_id,a.location_id loop
  q:=cp7_sku_conversion.pool_quote_v2(pool.product_id,pool.location_id,'GRADE_A');
  if(q->>'qty')::numeric<pool.qty then raise exception 'CP7_SKU_SALE_VALUE_POOL_SHORT';end if;
  v_average:=(q->>'average')::numeric;v_prior:=0;v_total_legacy:=0;v_line:=v_line+1;
  for a in select a.id,i.product_id,a.lot_id,a.location_id,a.qty_pcs,h.hpp_per_pcs,
      sum(a.qty_pcs)over(order by a.id rows unbounded preceding)::numeric cumulative_qty
    from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
    join erp.hpp_versions h on h.lot_id=a.lot_id and h.is_current
    where i.sale_id=p_sale and i.product_id=pool.product_id and a.location_id=pool.location_id order by a.id loop
   v_effective:=round(a.cumulative_qty*v_average,2)-v_prior;v_prior:=v_prior+v_effective;
   insert into cp7_sku_conversion.sale_allocation_values_v2(sale_stock_allocation_id,sale_id,product_id,lot_id,location_id,quality_grade,qty_pcs,effective_value,legacy_value,effective_unit_value,pool_revision)
   values(a.id,p_sale,a.product_id,a.lot_id,a.location_id,'GRADE_A',a.qty_pcs,v_effective,round(a.qty_pcs*a.hpp_per_pcs,2),v_effective/a.qty_pcs,q->>'revision');
   v_total_legacy:=v_total_legacy+round(a.qty_pcs*a.hpp_per_pcs,2);
  end loop;
  v_qty:=pool.qty;v_total_effective:=round(v_qty*v_average,2);
  if v_prior is distinct from v_total_effective then raise exception 'CP7_SKU_SALE_CENT_APPORTIONMENT';end if;
  with component_intervals as(
   select c.root_lot_id,c.po_id,c.unit_value,c.component_units*pool.qty/(q->>'qty')::numeric desired_units,
    sum(c.component_units*pool.qty/(q->>'qty')::numeric)over(order by c.root_lot_id rows unbounded preceding)component_end,
    coalesce(sum(c.component_units*pool.qty/(q->>'qty')::numeric)over(order by c.root_lot_id rows between unbounded preceding and 1 preceding),0)component_start
   from cp7_sku_conversion.pool_components_v2(pool.product_id,pool.location_id,'GRADE_A')c
  ), allocation_intervals as(
   select v.sale_stock_allocation_id,v.qty_pcs,v.effective_value,
    sum(v.qty_pcs)over(order by v.sale_stock_allocation_id rows unbounded preceding)::numeric allocation_end,
    coalesce(sum(v.qty_pcs)over(order by v.sale_stock_allocation_id rows between unbounded preceding and 1 preceding),0)::numeric allocation_start
   from cp7_sku_conversion.sale_allocation_values_v2 v
   where v.sale_id=p_sale and v.product_id=pool.product_id and v.location_id=pool.location_id
  ), matrix as(
   select a.sale_stock_allocation_id,c.root_lot_id,c.po_id,c.unit_value,
    greatest(least(a.allocation_end,c.component_end)-greatest(a.allocation_start,c.component_start),0)::numeric component_units,
    a.effective_value
   from allocation_intervals a cross join component_intervals c
  ), raw as(
   select *,component_units*unit_value raw_value,
    sum(component_units*unit_value)over(partition by sale_stock_allocation_id order by root_lot_id rows unbounded preceding)cumulative_raw,
    sum(component_units*unit_value)over(partition by sale_stock_allocation_id)total_raw
   from matrix where component_units>0
  ), targets as(
   select *,case when effective_value=0 then 0 else round(cumulative_raw*effective_value/nullif(total_raw,0),2)end cumulative_target
   from raw
  ), shares as(
   select row_number()over(partition by sale_stock_allocation_id order by root_lot_id)::integer line_no,*,
    cumulative_target-coalesce(lag(cumulative_target)over(partition by sale_stock_allocation_id order by root_lot_id),0)booked_value
   from targets
  )
  insert into cp7_sku_conversion.sale_allocation_components_v2(sale_stock_allocation_id,line_no,root_lot_id,po_id,component_units,booked_value)
  select sale_stock_allocation_id,line_no,root_lot_id,po_id,component_units,booked_value from shares order by sale_stock_allocation_id,line_no;
  if exists(select 1 from cp7_sku_conversion.sale_allocation_values_v2 v where v.sale_id=p_sale and v.product_id=pool.product_id and v.location_id=pool.location_id
   and(abs(v.qty_pcs-coalesce((select sum(c.component_units)from cp7_sku_conversion.sale_allocation_components_v2 c where c.sale_stock_allocation_id=v.sale_stock_allocation_id),0))>0.000000000001
    or v.effective_value is distinct from(select sum(c.booked_value)from cp7_sku_conversion.sale_allocation_components_v2 c where c.sale_stock_allocation_id=v.sale_stock_allocation_id)))then
   raise exception 'CP7_SKU_SALE_COMPONENT_MISMATCH';end if;
  with allocation_ranked as(
   select v.sale_stock_allocation_id,v.product_id,v.location_id,v.effective_value,v.legacy_value,l.po_id physical_po
   from cp7_sku_conversion.sale_allocation_values_v2 v join erp.fg_lots l on l.id=v.lot_id
   where v.sale_id=p_sale and v.product_id=pool.product_id and v.location_id=pool.location_id
  ), economic as(
   select c.sale_stock_allocation_id,c.po_id,sum(c.booked_value)::numeric effective
   from cp7_sku_conversion.sale_allocation_components_v2 c join allocation_ranked a using(sale_stock_allocation_id)
   group by c.sale_stock_allocation_id,c.po_id
  ), keys as(
   select sale_stock_allocation_id,po_id from economic
   union select sale_stock_allocation_id,physical_po from allocation_ranked
  ), numbered as(
   select row_number()over(partition by k.sale_stock_allocation_id order by k.po_id nulls last)::integer line_no,k.sale_stock_allocation_id,k.po_id,
    a.product_id,a.location_id,coalesce(e.effective,0)::numeric effective,
    case when k.po_id is not distinct from a.physical_po then a.legacy_value else 0 end::numeric legacy
   from keys k join allocation_ranked a using(sale_stock_allocation_id)
   left join economic e on e.sale_stock_allocation_id=k.sale_stock_allocation_id and e.po_id is not distinct from k.po_id
  )
  insert into cp7_sku_conversion.sale_allocation_attributions_v2(sale_stock_allocation_id,line_no,po_id,product_id,location_id,quality_grade,effective_value,legacy_value,adjustment_delta)
  select sale_stock_allocation_id,line_no,po_id,product_id,location_id,'GRADE_A',effective,legacy,legacy-effective from numbered order by sale_stock_allocation_id,line_no;
  if exists(select 1 from cp7_sku_conversion.sale_allocation_values_v2 v where v.sale_id=p_sale and v.product_id=pool.product_id and v.location_id=pool.location_id
   and(v.effective_value is distinct from(select sum(a.effective_value)from cp7_sku_conversion.sale_allocation_attributions_v2 a where a.sale_stock_allocation_id=v.sale_stock_allocation_id)
    or v.legacy_value is distinct from(select sum(a.legacy_value)from cp7_sku_conversion.sale_allocation_attributions_v2 a where a.sale_stock_allocation_id=v.sale_stock_allocation_id)))then
   raise exception 'CP7_SKU_SALE_ATTRIBUTION_MISMATCH';end if;
  insert into cp7_sku_conversion.valuation_events_v2(id,group_id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,qty_delta,effective_value_delta,legacy_value_delta,adjustment_delta,physical_at,economic_date)
  select gen_random_uuid(),null,'SALE',p_sale,v_line,'POST','POOL',pool.product_id,pool.location_id,'GRADE_A',-v_qty,-v_total_effective,-v_total_legacy,
   v_total_legacy-v_total_effective,h.sale_date,(h.sale_date at time zone 'Asia/Jakarta')::date from erp.sales_headers h where h.id=p_sale;
 end loop;
 with entries as(
  select v.product_id,v.location_id,v.quality_grade,c.root_lot_id,-c.component_units::numeric units
  from cp7_sku_conversion.sale_allocation_components_v2 c
  join cp7_sku_conversion.sale_allocation_values_v2 v using(sale_stock_allocation_id)where v.sale_id=p_sale
  union all
  select v.product_id,v.location_id,v.quality_grade,v.lot_id,v.qty_pcs::numeric
  from cp7_sku_conversion.sale_allocation_values_v2 v where v.sale_id=p_sale
 ), compact as(
  select product_id,location_id,quality_grade,root_lot_id,sum(units)::numeric units from entries
  group by product_id,location_id,quality_grade,root_lot_id having abs(sum(units))>0.000000000001
 ), numbered as(
  select row_number()over(order by product_id,location_id,quality_grade,root_lot_id)::integer line_no,*from compact
 )
 insert into cp7_sku_conversion.component_events_v2(id,group_id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,root_lot_id,units_delta,physical_at,economic_date)
 select gen_random_uuid(),null,'SALE',p_sale,line_no,'POST','POOL',product_id,location_id,quality_grade,root_lot_id,units,h.sale_date,
  (h.sale_date at time zone 'Asia/Jakarta')::date from numbered cross join erp.sales_headers h where h.id=p_sale order by line_no;
 if exists(select 1 from cp7_sku_conversion.component_events_v2 where source_type='SALE'and source_id=p_sale and phase='POST'
  group by product_id,location_id,quality_grade having abs(sum(units_delta))>0.000000000001)then
  raise exception 'CP7_SKU_SALE_COMPONENT_QTY_NOT_CONSERVED';end if;
end $$;

create function cp7_sku_conversion.sale_allocation_unit_v2(p_allocation uuid,p_lot uuid)returns numeric
language plpgsql stable security definer set search_path=''as $$
declare v numeric;
begin
 perform erp.require_internal();
 select effective_unit_value into v from cp7_sku_conversion.sale_allocation_values_v2 where sale_stock_allocation_id=p_allocation;
 return coalesce(v,erp.lock_current_hpp_per_pcs(p_lot),0);
end $$;

create function cp7_sku_conversion.prepare_return_values_v2(p_return uuid)returns void
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare r record;v_prior_qty integer;v_prior_value numeric(24,2);v_value numeric(24,2);v_legacy numeric(24,2);v_line integer:=0;pool record;
begin
 perform erp.require_internal();
 if exists(select 1 from cp7_sku_conversion.sales_return_values_v2 where return_id=p_return)then raise exception 'CP7_SKU_RETURN_VALUE_ALREADY_PREPARED';end if;
 for r in select i.id,i.return_id,i.sale_stock_allocation_id,i.product_id,i.lot_id,i.location_id,i.quality_grade,i.qty_pcs,
   a.qty_pcs sold_qty,a.effective_value sold_value,h.hpp_per_pcs
  from erp.sales_return_items i join cp7_sku_conversion.sale_allocation_values_v2 a on a.sale_stock_allocation_id=i.sale_stock_allocation_id
  join erp.hpp_versions h on h.lot_id=i.lot_id and h.is_current
  where i.return_id=p_return order by i.sale_stock_allocation_id,i.id loop
  select coalesce(sum(v.qty_pcs),0),coalesce(sum(v.effective_value),0)into v_prior_qty,v_prior_value
   from cp7_sku_conversion.sales_return_values_v2 v join erp.sales_returns h on h.id=v.return_id
   where v.sale_stock_allocation_id=r.sale_stock_allocation_id and(h.status='POSTED'or h.id=p_return);
  if v_prior_qty+r.qty_pcs>r.sold_qty then raise exception 'CP7_SKU_RETURN_VALUE_EXCEEDS_SALE_ALLOCATION';end if;
  if exists(select 1 from cp7_sku_conversion.sale_allocation_components_v2 c
   left join erp.hpp_versions h on h.lot_id=c.root_lot_id and h.is_current
   where c.sale_stock_allocation_id=r.sale_stock_allocation_id and(h.id is null or h.hpp_per_pcs is null or h.cost_state='ESTIMATED'
    or erp.bd_lot_laundry_unknown_v1(c.root_lot_id)))then raise exception 'CP7_SKU_RETURN_COMPONENT_HPP_UNKNOWN';end if;
  with prior as(
   select c.root_lot_id,sum(c.component_units)::numeric units
   from cp7_sku_conversion.sales_return_components_v2 c join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
   join erp.sales_returns h on h.id=v.return_id
   where v.sale_stock_allocation_id=r.sale_stock_allocation_id and(h.status='POSTED'or h.id=p_return)group by c.root_lot_id
  )select round(coalesce(sum(((v_prior_qty+r.qty_pcs)*c.component_units/r.sold_qty-coalesce(p.units,0))*h.hpp_per_pcs),0),2)
   into v_value from cp7_sku_conversion.sale_allocation_components_v2 c
   join erp.hpp_versions h on h.lot_id=c.root_lot_id and h.is_current
   left join prior p on p.root_lot_id=c.root_lot_id where c.sale_stock_allocation_id=r.sale_stock_allocation_id;
  v_legacy:=round(r.qty_pcs*r.hpp_per_pcs,2);
  insert into cp7_sku_conversion.sales_return_values_v2(sales_return_item_id,return_id,sale_stock_allocation_id,product_id,lot_id,location_id,quality_grade,qty_pcs,effective_value,legacy_value,effective_unit_value)
  values(r.id,p_return,r.sale_stock_allocation_id,r.product_id,r.lot_id,r.location_id,r.quality_grade,r.qty_pcs,v_value,v_legacy,v_value/r.qty_pcs);
  with prior as(
   select c.root_lot_id,sum(c.component_units)::numeric units
   from cp7_sku_conversion.sales_return_components_v2 c join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
   join erp.sales_returns h on h.id=v.return_id
   where v.sale_stock_allocation_id=r.sale_stock_allocation_id and(h.status='POSTED'or h.id=p_return)group by c.root_lot_id
  ), raw as(
   select c.root_lot_id,c.po_id,(v_prior_qty+r.qty_pcs)*c.component_units/r.sold_qty-coalesce(p.units,0)component_units,h.hpp_per_pcs
   from cp7_sku_conversion.sale_allocation_components_v2 c join erp.hpp_versions h on h.lot_id=c.root_lot_id and h.is_current
   left join prior p on p.root_lot_id=c.root_lot_id where c.sale_stock_allocation_id=r.sale_stock_allocation_id
  ), ranked as(
   select *,sum(component_units*hpp_per_pcs)over(order by root_lot_id rows unbounded preceding)cumulative_raw,
    sum(component_units*hpp_per_pcs)over()total_raw from raw where component_units>0
  ), targets as(
   select *,case when v_value=0 then 0 else round(cumulative_raw*v_value/nullif(total_raw,0),2)end cumulative_target from ranked
  ), shares as(
   select row_number()over(order by root_lot_id)::integer line_no,*,
    cumulative_target-coalesce(lag(cumulative_target)over(order by root_lot_id),0)booked_value from targets
  )
  insert into cp7_sku_conversion.sales_return_components_v2(sales_return_item_id,line_no,root_lot_id,po_id,component_units,booked_value)
  select r.id,line_no,root_lot_id,po_id,component_units,booked_value from shares order by line_no;
  if abs(r.qty_pcs-coalesce((select sum(c.component_units)from cp7_sku_conversion.sales_return_components_v2 c where c.sales_return_item_id=r.id),0))>0.000000000001
   or v_value is distinct from(select sum(c.booked_value)from cp7_sku_conversion.sales_return_components_v2 c where c.sales_return_item_id=r.id)then
   raise exception 'CP7_SKU_RETURN_COMPONENT_MISMATCH';end if;
  with economic as(
   select po_id,sum(booked_value)::numeric effective from cp7_sku_conversion.sales_return_components_v2 where sales_return_item_id=r.id group by po_id
  ), keys as(
   select po_id from economic union select l.po_id from erp.fg_lots l where l.id=r.lot_id
  ), numbered as(
   select row_number()over(order by k.po_id nulls last)::integer line_no,k.po_id,coalesce(e.effective,0)::numeric effective,
    case when k.po_id is not distinct from l.po_id then v_legacy else 0 end::numeric legacy
   from keys k left join economic e on e.po_id is not distinct from k.po_id cross join erp.fg_lots l where l.id=r.lot_id
  )
  insert into cp7_sku_conversion.sales_return_attributions_v2(sales_return_item_id,line_no,po_id,product_id,location_id,quality_grade,effective_value,legacy_value,adjustment_delta)
  select r.id,line_no,po_id,r.product_id,r.location_id,r.quality_grade,effective,legacy,effective-legacy from numbered order by line_no;
  if v_value is distinct from(select sum(a.effective_value)from cp7_sku_conversion.sales_return_attributions_v2 a where a.sales_return_item_id=r.id)
   or v_legacy is distinct from(select sum(a.legacy_value)from cp7_sku_conversion.sales_return_attributions_v2 a where a.sales_return_item_id=r.id)then
   raise exception 'CP7_SKU_RETURN_ATTRIBUTION_MISMATCH';end if;
 end loop;
 for pool in select product_id,location_id,quality_grade,sum(qty_pcs)::numeric qty,sum(effective_value)::numeric effective,sum(legacy_value)::numeric legacy
  from cp7_sku_conversion.sales_return_values_v2 where return_id=p_return group by product_id,location_id,quality_grade order by product_id,location_id,quality_grade loop
  v_line:=v_line+1;
  insert into cp7_sku_conversion.valuation_events_v2(id,group_id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,qty_delta,effective_value_delta,legacy_value_delta,adjustment_delta,physical_at,economic_date)
  select gen_random_uuid(),null,'SALES_RETURN',p_return,v_line,'POST','POOL',pool.product_id,pool.location_id,pool.quality_grade,pool.qty,pool.effective,pool.legacy,
   pool.effective-pool.legacy,h.physical_at,(h.physical_at at time zone 'Asia/Jakarta')::date from erp.sales_returns h where h.id=p_return;
 end loop;
 with entries as(
  select v.product_id,v.location_id,v.quality_grade,c.root_lot_id,c.component_units::numeric units
  from cp7_sku_conversion.sales_return_components_v2 c join cp7_sku_conversion.sales_return_values_v2 v using(sales_return_item_id)
  where v.return_id=p_return
  union all
  select v.product_id,v.location_id,v.quality_grade,v.lot_id,-v.qty_pcs::numeric
  from cp7_sku_conversion.sales_return_values_v2 v where v.return_id=p_return
 ), compact as(
  select product_id,location_id,quality_grade,root_lot_id,sum(units)::numeric units from entries
  group by product_id,location_id,quality_grade,root_lot_id having abs(sum(units))>0.000000000001
 ), numbered as(
  select row_number()over(order by product_id,location_id,quality_grade,root_lot_id)::integer line_no,*from compact
 )
 insert into cp7_sku_conversion.component_events_v2(id,group_id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,root_lot_id,units_delta,physical_at,economic_date)
 select gen_random_uuid(),null,'SALES_RETURN',p_return,line_no,'POST','POOL',product_id,location_id,quality_grade,root_lot_id,units,h.physical_at,
  (h.physical_at at time zone 'Asia/Jakarta')::date from numbered cross join erp.sales_returns h where h.id=p_return order by line_no;
 if exists(select 1 from cp7_sku_conversion.component_events_v2 where source_type='SALES_RETURN'and source_id=p_return and phase='POST'
  group by product_id,location_id,quality_grade having abs(sum(units_delta))>0.000000000001)then
  raise exception 'CP7_SKU_RETURN_COMPONENT_QTY_NOT_CONSERVED';end if;
end $$;

create function cp7_sku_conversion.return_item_unit_v2(p_item uuid,p_lot uuid,p_fallback numeric)returns numeric
language plpgsql stable security definer set search_path=''as $$
declare v numeric;
begin
 perform erp.require_internal();
 select effective_unit_value into v from cp7_sku_conversion.sales_return_values_v2 where sales_return_item_id=p_item;
 return coalesce(v,erp.lock_current_hpp_per_pcs(p_lot),p_fallback);
end $$;

create function cp7_sku_conversion.prepare_valuation_v2(p_group uuid,p_preview jsonb) returns void
language plpgsql volatile security definer set search_path='' set timezone='UTC' as $$
declare s jsonb;t jsonb;v_qty integer:=(p_preview->>'qty_pcs')::integer;v_transfer numeric(24,2);v_revision text;
begin
 perform erp.require_internal();perform erp.require_permission('warehouse.brand_conversion.post');
 if p_group is null then raise exception 'CP7_SKU_MOVAVG_PREVIEW_REQUIRED';end if;
 s:=cp7_sku_conversion.pool_quote_v2((p_preview->>'source_product_id')::uuid,(p_preview->>'location_id')::uuid,'GRADE_A');
 t:=cp7_sku_conversion.pool_quote_v2((p_preview->>'target_product_id')::uuid,(p_preview->>'location_id')::uuid,'GRADE_A');
 if (s->>'revision')is distinct from(p_preview->>'source_value_revision')or(t->>'revision')is distinct from(p_preview->>'target_value_revision')then
  raise exception 'STALE_VERSION: nilai rata-rata sumber atau tujuan berubah; periksa pratinjau terbaru';end if;
 v_transfer:=round(v_qty*(s->>'average')::numeric,2);
 v_revision:=md5(jsonb_build_object('source',s->>'revision','target',t->>'revision','qty',v_qty,'transfer',v_transfer)::text);
 insert into cp7_sku_conversion.valuation_quotes_v2(group_id,source_product_id,target_product_id,location_id,quality_grade,qty_pcs,physical_at,
  source_before_qty,source_before_value,source_before_average,target_before_qty,target_before_value,target_before_average,transfer_value,valuation_revision)
 values(p_group,(p_preview->>'source_product_id')::uuid,(p_preview->>'target_product_id')::uuid,(p_preview->>'location_id')::uuid,'GRADE_A',v_qty,
  (p_preview->>'physical_at')::timestamptz,(s->>'qty')::numeric,(s->>'value')::numeric,(s->>'average')::numeric,
  (t->>'qty')::numeric,(t->>'value')::numeric,case when t->>'average' is null then null else(t->>'average')::numeric end,v_transfer,v_revision);
 with components as materialized(
  select c.line_no,c.root_lot_id,c.po_id,c.hpp_version_id,c.component_units pool_component_units,c.unit_value,c.value contributed_value,
   c.component_units*v_qty/(s->>'qty')::numeric transfer_units,
   c.component_units*v_qty/(s->>'qty')::numeric*c.unit_value transfer_raw_value
  from cp7_sku_conversion.pool_components_v2((p_preview->>'source_product_id')::uuid,(p_preview->>'location_id')::uuid,'GRADE_A')c
 ), ranked as(
  select c.*,sum(transfer_raw_value)over(order by line_no rows unbounded preceding)cumulative_value,
   sum(transfer_raw_value)over() total_raw_value
  from components c
 ), targets as(
  select r.*,case when v_transfer=0 then 0 else round(cumulative_value*v_transfer/nullif(total_raw_value,0),2)end cumulative_target
  from ranked r
 ), shares as(
  select t.*,cumulative_target-coalesce(lag(cumulative_target)over(order by line_no),0)transfer_share from targets t
 )
 insert into cp7_sku_conversion.valuation_contributors_v2(group_id,line_no,root_lot_id,po_id,hpp_version_id,pool_component_units,transfer_units,unit_value,contributed_value,transfer_value)
 select p_group,line_no,root_lot_id,po_id,hpp_version_id,pool_component_units,transfer_units,unit_value,contributed_value,transfer_share from shares order by line_no;
 if (select round(sum(contributed_value),6)from cp7_sku_conversion.valuation_contributors_v2 where group_id=p_group)
    is distinct from round((s->>'base_value')::numeric,6) then raise exception 'CP7_SKU_MOVAVG_CONTRIBUTOR_MISMATCH';end if;
 if (select coalesce(sum(transfer_value),0)from cp7_sku_conversion.valuation_contributors_v2 where group_id=p_group)
    is distinct from v_transfer then raise exception 'CP7_SKU_MOVAVG_CONTRIBUTOR_CENT_MISMATCH';end if;
 if abs((select coalesce(sum(transfer_units),0)from cp7_sku_conversion.valuation_contributors_v2 where group_id=p_group)-v_qty)>0.000000000001
    then raise exception 'CP7_SKU_MOVAVG_COMPONENT_QTY_MISMATCH';end if;
end $$;

create function cp7_sku_conversion.reverse_valuation_v2(p_group uuid) returns void
language plpgsql volatile security definer set search_path='' set timezone='UTC' as $$
declare q cp7_sku_conversion.valuation_quotes_v2%rowtype;p cp7_sku_conversion.valuation_postings_v2%rowtype;v_journal uuid;v_delta numeric(24,2);v_lines jsonb:='[]'::jsonb;r record;
begin
 perform erp.require_internal();perform erp.require_permission('warehouse.brand_conversion.reverse');perform erp.require_owner_admin();
 select *into strict q from cp7_sku_conversion.valuation_quotes_v2 where group_id=p_group;
 select *into strict p from cp7_sku_conversion.valuation_postings_v2 where group_id=p_group and phase='POST';
 if exists(select 1 from cp7_sku_conversion.valuation_postings_v2 where group_id=p_group and phase='REVERSE')then raise exception 'CP7_SKU_MOVAVG_ALREADY_REVERSED';end if;
 v_delta:=-p.correction_value;
 insert into cp7_sku_conversion.valuation_attributions_v2(group_id,phase,side,line_no,po_id,product_id,effective_value_delta,legacy_value_delta,adjustment_delta,supersedes_phase)
 select group_id,'REVERSE',side,line_no,po_id,product_id,-effective_value_delta,-legacy_value_delta,-adjustment_delta,'POST'
 from cp7_sku_conversion.valuation_attributions_v2 where group_id=p_group and phase='POST';
 for r in select *from cp7_sku_conversion.valuation_attributions_v2 where group_id=p_group and phase='REVERSE'and side='TARGET'and abs(adjustment_delta)>0.005 order by line_no loop
  v_lines:=v_lines||jsonb_build_array(
   (case when r.adjustment_delta>0 then jsonb_build_object('mapping_key','FG_INVENTORY','debit',r.adjustment_delta,'credit',0)
    else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(r.adjustment_delta))end)
    ||case when r.po_id is null then jsonb_build_object('product_id',q.target_product_id)else jsonb_build_object('po_id',r.po_id)end,
   (case when r.adjustment_delta>0 then jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',r.adjustment_delta)
    else jsonb_build_object('mapping_key','FG_INVENTORY','debit',abs(r.adjustment_delta),'credit',0)end)
    ||case when r.po_id is null then jsonb_build_object('product_id',q.source_product_id)else jsonb_build_object('po_id',r.po_id)end);
 end loop;
 if jsonb_array_length(v_lines)>0 then v_journal:=erp.post_journal('SKU_MOVING_AVERAGE_REVERSAL',p_group,(statement_timestamp()at time zone 'Asia/Jakarta')::date,
  'Pembalikan koreksi nilai Ganti Merek rata-rata SKU/gudang',v_lines);end if;
 insert into cp7_sku_conversion.valuation_postings_v2 values(p_group,'REVERSE',-p.native_value,-p.transfer_value,v_delta,v_journal,statement_timestamp());
 insert into cp7_sku_conversion.component_events_v2(id,group_id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,root_lot_id,units_delta,physical_at,economic_date,supersedes_event_id)
 select gen_random_uuid(),group_id,source_type,source_id,line_no,'REVERSE',side,product_id,location_id,quality_grade,root_lot_id,-units_delta,
  statement_timestamp(),(statement_timestamp()at time zone 'Asia/Jakarta')::date,id
 from cp7_sku_conversion.component_events_v2 where group_id=p_group and phase='POST'order by side,line_no;
 if exists(select 1 from cp7_sku_conversion.component_events_v2 where group_id=p_group
  group by side,root_lot_id having abs(sum(units_delta))>0.000000000001)then
  raise exception 'CP7_SKU_MOVAVG_COMPONENT_REVERSE_NOT_EXACT';end if;
 insert into cp7_sku_conversion.valuation_events_v2(id,group_id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,qty_delta,effective_value_delta,legacy_value_delta,adjustment_delta,physical_at,economic_date)
 values(gen_random_uuid(),p_group,'SKU_CONVERSION',p_group,1,'REVERSE','SOURCE',q.source_product_id,q.location_id,q.quality_grade,q.qty_pcs,q.transfer_value,p.native_value,q.transfer_value-p.native_value,statement_timestamp(),(statement_timestamp()at time zone 'Asia/Jakarta')::date),
       (gen_random_uuid(),p_group,'SKU_CONVERSION',p_group,1,'REVERSE','TARGET',q.target_product_id,q.location_id,q.quality_grade,-q.qty_pcs,-q.transfer_value,-p.native_value,p.native_value-q.transfer_value,statement_timestamp(),(statement_timestamp()at time zone 'Asia/Jakarta')::date);
 if abs((select coalesce(sum(effective_value_delta),0)from cp7_sku_conversion.valuation_events_v2 where group_id=p_group))>0.000001
 or abs((select coalesce(sum(adjustment_delta),0)from cp7_sku_conversion.valuation_events_v2 where group_id=p_group))>0.000001 then
  raise exception 'CP7_SKU_MOVAVG_REVERSE_NOT_CONSERVED';end if;
end $$;

create function cp7_sku_conversion.finalize_valuation_v2(p_group uuid) returns void
language plpgsql volatile security definer set search_path='' set timezone='UTC' as $$
declare q cp7_sku_conversion.valuation_quotes_v2%rowtype;v_native numeric(24,2);v_delta numeric(24,2);v_journal uuid;v_lines jsonb:='[]'::jsonb;r record;
begin
 perform erp.require_internal();perform erp.require_permission('warehouse.brand_conversion.post');
 select *into strict q from cp7_sku_conversion.valuation_quotes_v2 where group_id=p_group;
 if exists(select 1 from cp7_sku_conversion.valuation_postings_v2 where group_id=p_group and phase='POST')then raise exception 'CP7_SKU_MOVAVG_ALREADY_FINALIZED';end if;
 select round(coalesce(sum(a.qty_pcs*a.original_hpp_per_pcs),0),2)into v_native from cp7_sku_conversion.members_v1 m
 join erp.product_conversion_allocations a on a.conversion_id=m.conversion_id where m.group_id=p_group;
 v_delta:=q.transfer_value-v_native;
 with effective as(select po_id,sum(transfer_value)::numeric effective from cp7_sku_conversion.valuation_contributors_v2 where group_id=p_group group by po_id),
 legacy as(select l.po_id,round(sum(a.qty_pcs*a.original_hpp_per_pcs),2)::numeric legacy from cp7_sku_conversion.members_v1 m
  join erp.product_conversion_allocations a on a.conversion_id=m.conversion_id join erp.fg_lots l on l.id=a.source_lot_id where m.group_id=p_group group by l.po_id),
 keys as(select po_id from effective union select po_id from legacy),
 joined as(select k.po_id,coalesce(e.effective,0)effective,coalesce(l.legacy,0)legacy from keys k
  left join effective e on e.po_id is not distinct from k.po_id
  left join legacy l on l.po_id is not distinct from k.po_id),
 numbered as(select row_number()over(order by po_id nulls last)::integer line_no,*from joined)
 insert into cp7_sku_conversion.valuation_attributions_v2(group_id,phase,side,line_no,po_id,product_id,effective_value_delta,legacy_value_delta,adjustment_delta)
 select p_group,'POST','SOURCE',line_no,po_id,q.source_product_id,-effective,-legacy,legacy-effective from numbered
 union all select p_group,'POST','TARGET',line_no,po_id,q.target_product_id,effective,legacy,effective-legacy from numbered;
 for r in select *from cp7_sku_conversion.valuation_attributions_v2 where group_id=p_group and phase='POST'and side='TARGET'and abs(adjustment_delta)>0.005 order by line_no loop
  v_lines:=v_lines||jsonb_build_array(
   (case when r.adjustment_delta>0 then jsonb_build_object('mapping_key','FG_INVENTORY','debit',r.adjustment_delta,'credit',0)
    else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(r.adjustment_delta))end)
    ||case when r.po_id is null then jsonb_build_object('product_id',q.target_product_id)else jsonb_build_object('po_id',r.po_id)end,
   (case when r.adjustment_delta>0 then jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',r.adjustment_delta)
    else jsonb_build_object('mapping_key','FG_INVENTORY','debit',abs(r.adjustment_delta),'credit',0)end)
    ||case when r.po_id is null then jsonb_build_object('product_id',q.source_product_id)else jsonb_build_object('po_id',r.po_id)end);
 end loop;
 if jsonb_array_length(v_lines)>0 then v_journal:=erp.post_journal('SKU_MOVING_AVERAGE',p_group,(q.physical_at at time zone 'Asia/Jakarta')::date,
  'Koreksi nilai Ganti Merek ke rata-rata SKU/gudang',v_lines);end if;
 insert into cp7_sku_conversion.valuation_postings_v2 values(p_group,'POST',v_native,q.transfer_value,v_delta,v_journal,statement_timestamp());
 with entries as(
  select 'SOURCE'::text side,q.source_product_id product_id,c.root_lot_id,-c.transfer_units::numeric units
  from cp7_sku_conversion.valuation_contributors_v2 c where c.group_id=p_group
  union all
  select 'SOURCE',q.source_product_id,a.source_lot_id,sum(a.qty_pcs)::numeric
  from cp7_sku_conversion.members_v1 m join erp.product_conversion_allocations a on a.conversion_id=m.conversion_id
  where m.group_id=p_group group by a.source_lot_id
  union all
  select 'TARGET',q.target_product_id,a.destination_lot_id,-sum(a.qty_pcs)::numeric
  from cp7_sku_conversion.members_v1 m join erp.product_conversion_allocations a on a.conversion_id=m.conversion_id
  where m.group_id=p_group group by a.destination_lot_id
  union all
  select 'TARGET',q.target_product_id,c.root_lot_id,c.transfer_units::numeric
  from cp7_sku_conversion.valuation_contributors_v2 c where c.group_id=p_group
 ), compact as(
  select side,product_id,root_lot_id,sum(units)::numeric units from entries group by side,product_id,root_lot_id
  having abs(sum(units))>0.000000000001
 ), numbered as(
  select row_number()over(partition by side order by root_lot_id)::integer line_no,*from compact
 )
 insert into cp7_sku_conversion.component_events_v2(id,group_id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,root_lot_id,units_delta,physical_at,economic_date)
 select gen_random_uuid(),p_group,'SKU_CONVERSION',p_group,line_no,'POST',side,product_id,q.location_id,q.quality_grade,root_lot_id,units,q.physical_at,
  (q.physical_at at time zone 'Asia/Jakarta')::date from numbered order by side,line_no;
 if exists(select 1 from cp7_sku_conversion.component_events_v2 where group_id=p_group and phase='POST'
  group by side having abs(sum(units_delta))>0.000000000001)then
  raise exception 'CP7_SKU_MOVAVG_COMPONENT_POOL_QTY_NOT_CONSERVED';end if;
 insert into cp7_sku_conversion.valuation_events_v2(id,group_id,source_type,source_id,line_no,phase,side,product_id,location_id,quality_grade,qty_delta,effective_value_delta,legacy_value_delta,adjustment_delta,physical_at,economic_date)
 values(gen_random_uuid(),p_group,'SKU_CONVERSION',p_group,1,'POST','SOURCE',q.source_product_id,q.location_id,q.quality_grade,-q.qty_pcs,-q.transfer_value,-v_native,v_native-q.transfer_value,q.physical_at,(q.physical_at at time zone 'Asia/Jakarta')::date),
       (gen_random_uuid(),p_group,'SKU_CONVERSION',p_group,1,'POST','TARGET',q.target_product_id,q.location_id,q.quality_grade,q.qty_pcs,q.transfer_value,v_native,q.transfer_value-v_native,q.physical_at,(q.physical_at at time zone 'Asia/Jakarta')::date);
 if abs((select coalesce(sum(effective_value_delta),0)from cp7_sku_conversion.valuation_events_v2 where group_id=p_group and phase='POST'))>0.000001
 or abs((select coalesce(sum(adjustment_delta),0)from cp7_sku_conversion.valuation_events_v2 where group_id=p_group and phase='POST'))>0.000001 then
  raise exception 'CP7_SKU_MOVAVG_VALUE_NOT_CONSERVED';end if;
 if exists(select 1 from(select po_id,sum(effective_value_delta)effective,sum(legacy_value_delta)legacy,sum(adjustment_delta)adjustment
  from cp7_sku_conversion.valuation_attributions_v2 where group_id=p_group and phase='POST'group by po_id)x
  where abs(effective)>0.005 or abs(legacy)>0.005 or abs(adjustment)>0.005)then raise exception 'CP7_SKU_MOVAVG_ATTRIBUTION_NOT_CONSERVED';end if;
end $$;
