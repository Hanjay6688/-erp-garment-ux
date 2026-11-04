-- Private, transaction-owned admission for Native automatic rework/redye.
-- No public payload switch or session-setting flag can create this lease.
create table cp7_sku_conversion.automatic_context_v5(
 backend_pid integer not null,transaction_id bigint not null,
 native_request_id uuid not null,rework_id uuid not null references erp.rework_orders(id),
 conversion_id uuid not null,phase text not null check(phase in('POST','REVERSE')),
 source_lot_id uuid not null references erp.fg_lots(id),
 source_po_id uuid not null references erp.production_orders(id),
 source_product_id uuid not null references erp.products(id),
 target_product_id uuid not null references erp.products(id),
 location_id uuid not null references erp.locations(id),
 qty integer not null check(qty>0),physical_at timestamptz not null,
 origin_kind text not null check(origin_kind in('REWORK','REDYE')),
 rework_proof jsonb not null,target_proof jsonb not null,
 primary key(backend_pid,transaction_id)
);
create table cp7_sku_conversion.automatic_admissions_v5(
 conversion_id uuid not null references erp.product_conversions(id),
 phase text not null check(phase in('POST','REVERSE')),
 rework_id uuid not null references erp.rework_orders(id),
 context_proof jsonb not null,conversion_proof jsonb not null,
 recorded_at timestamptz not null default statement_timestamp(),
 primary key(conversion_id,phase)
);
create trigger automatic_admissions_immutable_v5 before update or delete
 on cp7_sku_conversion.automatic_admissions_v5
 for each row execute function cp7_sku_conversion.immutable_v1();
alter table cp7_sku_conversion.automatic_context_v5 enable row level security;
alter table cp7_sku_conversion.automatic_admissions_v5 enable row level security;
revoke all on cp7_sku_conversion.automatic_context_v5,cp7_sku_conversion.automatic_admissions_v5
 from public,anon,authenticated,service_role;

create function cp7_sku_conversion.automatic_valid_v5()returns boolean
language sql stable security definer set search_path=''as $$
 select exists(
  select 1 from cp7_sku_conversion.automatic_context_v5 f
  join erp.be_execution_context_v1 e on e.backend_pid=f.backend_pid and e.transaction_id=f.transaction_id
   and e.request_id=f.native_request_id
  join erp.rework_orders r on r.id=f.rework_id
  join erp.be_rework_targets_v1 t on t.rework_id=r.id
  join erp.bs_cases bs on bs.id=r.bs_case_id
  join erp.fg_lots l on l.id=r.good_fg_lot_id
  join erp.production_orders po on po.id=l.po_id
  left join erp.product_conversions c on c.id=f.conversion_id
  left join erp.be_conversion_sources_v1 s on s.conversion_id=c.id
  where f.backend_pid=pg_backend_pid()and f.transaction_id=txid_current()
   and r.cost_posted is true and r.status='COMPLETED'
   and to_jsonb(r)=f.rework_proof and to_jsonb(t)=f.target_proof
   and r.good_fg_lot_id=f.source_lot_id and r.qty_good_returned=f.qty
   and r.return_fg_location_id=f.location_id and r.completed_at=f.physical_at
   and l.po_id=f.source_po_id and l.po_id=bs.po_id and l.product_id=bs.product_id
   and l.product_id=f.source_product_id and l.lot_origin='PRODUCTION'
   and l.initial_qty_pcs=f.qty
   and(f.phase='REVERSE'or(t.target_product_id=f.target_product_id
    and f.origin_kind=case when t.mode='REDYE_SKU'then'REDYE'else'REWORK'end))
   and exists(select 1 from erp.fg_stock_movements m where m.lot_id=l.id
    and m.source_type='REWORK_ORDER'and m.source_id=r.id and m.movement_type='REWORK_IN'
    and m.product_id=l.product_id and m.location_id=f.location_id and m.quality_grade='GRADE_A'
    and m.qty_signed=f.qty and m.physical_at=f.physical_at
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id))
   and((f.phase='POST'and(c.id is null or c.status in('DRAFT','POSTED')))
    or(f.phase='REVERSE'and c.status in('POSTED','REVERSED')))
   and(c.id is null or(c.from_product_id=f.source_product_id and c.to_product_id=f.target_product_id
    and c.location_id=f.location_id and c.qty_pcs=f.qty and c.physical_at=f.physical_at
    and((s.conversion_id is null and f.phase='POST'and c.status='DRAFT')
     or(s.source_lot_id=f.source_lot_id and s.rework_id=f.rework_id and s.origin_kind=f.origin_kind))))
 )
$$;

create function cp7_sku_conversion.automatic_enter_v5(p_rework uuid,p_phase text,p_conversion uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
declare r erp.rework_orders%rowtype;t erp.be_rework_targets_v1%rowtype;
 l erp.fg_lots%rowtype;c erp.product_conversions%rowtype;s erp.be_conversion_sources_v1%rowtype;
 request uuid;target uuid;origin text;
begin
 perform erp.require_internal();
 if p_phase is null or p_phase not in('POST','REVERSE')or p_conversion is null then
  raise exception 'CP7_SKU_AUTOMATIC_PHASE_AND_CHILD_REQUIRED';end if;
 if exists(select 1 from cp7_sku_conversion.automatic_context_v5
  where backend_pid=pg_backend_pid()and transaction_id=txid_current())
  or exists(select 1 from cp7_sku_conversion.execution_v1
   where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
  raise exception 'CP7_SKU_AUTOMATIC_NESTING_REFUSED';end if;
 select request_id into strict request from erp.be_execution_context_v1
  where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 select *into strict r from erp.rework_orders where id=p_rework for update;
 select *into strict t from erp.be_rework_targets_v1 where rework_id=r.id;
 select *into strict l from erp.fg_lots where id=r.good_fg_lot_id;
 if p_phase='POST'then
  if exists(select 1 from erp.product_conversions where id=p_conversion)
   or exists(select 1 from cp7_sku_conversion.groups_v1 where request_id=p_conversion)then
   raise exception 'CP7_SKU_AUTOMATIC_NEW_CHILD_REQUIRED';end if;
  target:=t.target_product_id;origin:=case when t.mode='REDYE_SKU'then'REDYE'else'REWORK'end;
 else
  select *into strict c from erp.product_conversions where id=p_conversion for update;
  select *into strict s from erp.be_conversion_sources_v1 where conversion_id=c.id;
  if c.status<>'POSTED'or s.rework_id is distinct from r.id
   or s.source_lot_id is distinct from l.id or s.origin_kind not in('REWORK','REDYE')then
   raise exception 'CP7_SKU_AUTOMATIC_EXACT_POSTED_CHILD_REQUIRED';end if;
  target:=c.to_product_id;origin:=s.origin_kind;
 end if;
 insert into cp7_sku_conversion.automatic_context_v5(backend_pid,transaction_id,native_request_id,
  rework_id,conversion_id,phase,source_lot_id,source_po_id,source_product_id,target_product_id,
  location_id,qty,physical_at,origin_kind,rework_proof,target_proof)
 values(pg_backend_pid(),txid_current(),request,r.id,p_conversion,p_phase,l.id,l.po_id,l.product_id,target,
  r.return_fg_location_id,r.qty_good_returned,r.completed_at,origin,to_jsonb(r),to_jsonb(t));
 if not cp7_sku_conversion.automatic_valid_v5()then
  raise exception 'CP7_SKU_AUTOMATIC_GENUINE_COMPLETED_PO_GOOD_REQUIRED';end if;
end $$;

create function cp7_sku_conversion.automatic_scope_v5(p_product uuid,p_location uuid,p_grade text)returns boolean
language sql stable security definer set search_path=''as $$
 select p_grade='GRADE_A'and cp7_sku_conversion.automatic_valid_v5()and exists(
  select 1 from cp7_sku_conversion.automatic_context_v5 f
  where f.backend_pid=pg_backend_pid()and f.transaction_id=txid_current()
   and p_location=f.location_id and p_product in(f.source_product_id,f.target_product_id))
$$;

create function cp7_sku_conversion.automatic_root_v5(p_lot uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select cp7_sku_conversion.automatic_valid_v5()and exists(
  select 1 from cp7_sku_conversion.automatic_context_v5 f join erp.fg_lots l on l.id=p_lot
  where f.backend_pid=pg_backend_pid()and f.transaction_id=txid_current()and l.po_id is not null
   and(exists(select 1 from cp7_sku_conversion.pool_components_v2(f.source_product_id,f.location_id,'GRADE_A')b
        where b.root_lot_id=p_lot and b.component_units>0.000000000001)
    or exists(select 1 from cp7_sku_conversion.pool_components_v2(f.target_product_id,f.location_id,'GRADE_A')b
        where b.root_lot_id=p_lot and b.component_units>0.000000000001)
    or exists(select 1 from cp7_sku_conversion.cost_events_v3 e
     where e.root_lot_id=p_lot and e.product_id in(f.source_product_id,f.target_product_id)
      and e.location_id=f.location_id and e.quality_grade='GRADE_A'
      and(e.source_type<>'SALE'or exists(select 1 from erp.sales_headers h
       where h.id=e.source_id and h.status in('POSTED','PARTIAL_PAID','PAID','REVERSED')))
      and(e.source_type<>'SALES_RETURN'or exists(select 1 from erp.sales_returns h
       where h.id=e.source_id and h.status in('POSTED','REVERSED')))
     group by e.product_id having sum(e.units_delta)>0.000000000001)))
$$;

create function cp7_sku_conversion.automatic_cost_root_v5(p_lot uuid,p_product uuid,p_location uuid,p_grade text)
returns table(root_lot_id uuid,po_id uuid,hpp_version_id uuid,unit_value numeric,source_revision jsonb)
language plpgsql stable security definer set search_path=''as $$
begin
 if cp7_sku_conversion.automatic_scope_v5(p_product,p_location,p_grade)
  and cp7_sku_conversion.automatic_root_v5(p_lot)then
  return query select *from cp7_sku_conversion.cost_accounting_root_v5(p_lot);
 else return query select *from cp7_sku_conversion.cost_root_v3(p_lot);end if;
end $$;

create function cp7_sku_conversion.automatic_cost_unit_v5(p_lot uuid,p_product uuid,p_location uuid,p_grade text)returns numeric
language plpgsql stable security definer set search_path=''as $$
begin
 if cp7_sku_conversion.automatic_scope_v5(p_product,p_location,p_grade)
  and cp7_sku_conversion.automatic_root_v5(p_lot)then
  return cp7_sku_conversion.cost_accounting_unit_v5(p_lot,p_product);
 end if;
 return cp7_sku_conversion.cost_current_unit_v3(p_lot,p_product);
end $$;

create function cp7_sku_conversion.automatic_assert_native_v5(
 p_conversion uuid,p_origin text,p_rework uuid,p_payload jsonb
)returns void language plpgsql stable security definer set search_path=''as $$
declare f cp7_sku_conversion.automatic_context_v5%rowtype;
begin
 select *into f from cp7_sku_conversion.automatic_context_v5
  where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if not found then return;end if;
 if not cp7_sku_conversion.automatic_valid_v5()or p_conversion is distinct from f.conversion_id then
  raise exception 'CP7_SKU_AUTOMATIC_NATIVE_CHILD_NOT_EXACT';end if;
 if p_payload is null then
  if f.phase<>'REVERSE'then raise exception 'CP7_SKU_AUTOMATIC_PHASE_MISMATCH';end if;
 elsif f.phase<>'POST'or p_origin is distinct from f.origin_kind or p_rework is distinct from f.rework_id
  or(p_payload->>'source_lot_id')::uuid is distinct from f.source_lot_id
  or(p_payload->>'target_product_id')::uuid is distinct from f.target_product_id
  or(p_payload->>'location_id')::uuid is distinct from f.location_id
  or(p_payload->>'qty_pcs')::integer is distinct from f.qty
  or(p_payload->>'physical_at')::timestamptz is distinct from f.physical_at
  or p_payload->'reason' is distinct from f.target_proof->'reason'
  or p_payload-array['source_lot_id','target_product_id','location_id','qty_pcs','physical_at','reason','expected_version']<>'{}'::jsonb then
  raise exception 'CP7_SKU_AUTOMATIC_NATIVE_PAYLOAD_NOT_EXACT';
 end if;
end $$;

create function cp7_sku_conversion.automatic_leave_v5(p_rework uuid,p_phase text,p_conversion uuid)returns void
language plpgsql volatile security definer set search_path=''as $$
declare f cp7_sku_conversion.automatic_context_v5%rowtype;c erp.product_conversions%rowtype;
 s erp.be_conversion_sources_v1%rowtype;g cp7_sku_conversion.legacy_groups_v4%rowtype;
begin
 perform erp.require_internal();
 select *into strict f from cp7_sku_conversion.automatic_context_v5
  where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if not cp7_sku_conversion.automatic_valid_v5()or f.rework_id is distinct from p_rework
  or f.phase is distinct from p_phase or f.conversion_id is distinct from p_conversion then
  raise exception 'CP7_SKU_AUTOMATIC_OWNING_RESULT_NOT_EXACT';end if;
 select *into strict c from erp.product_conversions where id=f.conversion_id;
 select *into strict s from erp.be_conversion_sources_v1 where conversion_id=c.id;
 select *into g from cp7_sku_conversion.legacy_groups_v4 where group_id=c.id;
 if (f.phase='POST'and c.status is distinct from 'POSTED')
  or(f.phase='REVERSE'and c.status is distinct from 'REVERSED')
  or(f.phase='POST'and(g.group_id is null or not exists(
    select 1 from cp7_sku_conversion.valuation_postings_v2 v where v.group_id=c.id and v.phase='POST')))
  or(g.group_id is not null and not exists(select 1 from cp7_sku_conversion.valuation_postings_v2 v
    where v.group_id=c.id and v.phase=f.phase))then
  raise exception 'CP7_SKU_AUTOMATIC_NATIVE_AND_ECONOMIC_RESULT_REQUIRED';end if;
 insert into cp7_sku_conversion.automatic_admissions_v5(conversion_id,phase,rework_id,context_proof,conversion_proof)
 values(c.id,f.phase,f.rework_id,to_jsonb(f),jsonb_build_object(
  'native',to_jsonb(c),'source',to_jsonb(s),'legacy',to_jsonb(g),
  'valuation',(select to_jsonb(q)from cp7_sku_conversion.valuation_quotes_v2 q where q.group_id=c.id)));
 delete from cp7_sku_conversion.automatic_context_v5
  where backend_pid=f.backend_pid and transaction_id=f.transaction_id and conversion_id=f.conversion_id;
end $$;

revoke all on function cp7_sku_conversion.automatic_valid_v5(),
 cp7_sku_conversion.automatic_enter_v5(uuid,text,uuid),cp7_sku_conversion.automatic_scope_v5(uuid,uuid,text),
 cp7_sku_conversion.automatic_root_v5(uuid),cp7_sku_conversion.automatic_cost_root_v5(uuid,uuid,uuid,text),
 cp7_sku_conversion.automatic_cost_unit_v5(uuid,uuid,uuid,text),
 cp7_sku_conversion.automatic_assert_native_v5(uuid,text,uuid,jsonb),
 cp7_sku_conversion.automatic_leave_v5(uuid,text,uuid)from public,anon,authenticated,service_role;
