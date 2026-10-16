-- Owner D15-3 (Fable FABLE-017, Astra ASTRA-C17-04, Sol KNOWN-DAILY-MASTER): daily master data is created, changed and
-- deactivated from the app: customers, suppliers and laundry vendors, Mandor (with the attendance HPP policy that marks a
-- Special Mandor), warehouses and locations, fabric (with its benchmark price) and accessories (category with the Mandor
-- accessory price, and variant). Mandor work rates per model x work component live in rates.sql.
-- Nothing is deleted. A record used by a transaction keeps its id and its code (only its name and contact details change,
-- and a material's name and code only through the audited rename of material-name.sql); it is deactivated instead, and
-- deactivation is refused while the record still holds stock or open work (the same predicates as the Native guards).
-- Every command carries the review token of the record it changes, is idempotent per (actor, request), writes through the
-- Native writer where one exists (erp.save_fabric_master_v2, erp.set_fabric_benchmark_price_v2,
-- erp.save_accessory_category_v2, erp.save_accessory_material_v2, erp.set_accessory_selling_price_v2,
-- erp.set_contractor_hpp_policy_v1) and otherwise on the master row itself, and records an immutable history row. The
-- Native audit log (erp.audit_logs, with the change reason) is the history the screen shows.
create role cp7_master_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create role cp7_master_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_master authorization cp7_master_read;
revoke all on schema cp7_master from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_master to postgres,cp7_master_write;
create table cp7_master.requests(
 actor uuid not null,request_id uuid not null,kind text not null,payload jsonb not null,response jsonb,
 primary key(actor,request_id)
);
create table cp7_master.history(
 id bigint generated always as identity primary key,kind text not null,entity_id uuid not null,action text not null,
 before jsonb,after jsonb not null,reason text not null,actor uuid not null,request_id uuid not null,
 recorded_at timestamptz not null default clock_timestamp()
);
create index master_history_entity on cp7_master.history(kind,entity_id,recorded_at);
alter table cp7_master.requests owner to postgres;
alter table cp7_master.history owner to postgres;
alter table cp7_master.requests enable row level security;
alter table cp7_master.history enable row level security;
create policy private_requests on cp7_master.requests for all using(false)with check(false);
create policy private_history on cp7_master.history for all using(false)with check(false);
revoke all on all tables in schema cp7_master from public,anon,authenticated,service_role,cp7_capture,cp7_master_read,cp7_master_write;

create function cp7_master.immutable()returns trigger
language plpgsql security invoker set search_path=''as $$
begin raise exception 'CP7_MASTER_HISTORY_IMMUTABLE';end $$;
create trigger immutable_history before update or delete on cp7_master.history
 for each row execute function cp7_master.immutable();
create trigger immutable_history_truncate before truncate on cp7_master.history
 for each statement execute function cp7_master.immutable();

-- The permission keys already seeded in erp.app_permissions (v2.6.17): view to read, manage to change; a price or a rate
-- also needs master.price.edit_draft (the key the access catalog gives "editMasterPrice").
create function cp7_master.permission(p_kind text,p_level text)returns text
language sql immutable set search_path=''as $$
 select 'master.'||case p_kind when'CUSTOMER'then'customer'when'SUPPLIER'then'partner'when'LAUNDRY_VENDOR'then'partner'
  when'MANDOR'then'workforce'when'WORK_RATE'then'workforce'when'LOCATION'then'location'when'FABRIC'then'fabric'
  when'ACCESSORY_CATEGORY'then'accessory'when'ACCESSORY'then'accessory'end||case when p_level='READ'then'.view'else'.manage'end$$;

create function cp7_master.access_now(p_kind text,p_level text)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;
begin
 if p_kind is null or p_kind not in('CUSTOMER','SUPPLIER','LAUNDRY_VENDOR','MANDOR','LOCATION','FABRIC','ACCESSORY_CATEGORY','ACCESSORY','WORK_RATE')
  or p_level is null or p_level not in('READ','WRITE','PRICE')then raise exception 'CP7_MASTER_KIND';end if;
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_MASTER_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or erp.has_permission(cp7_master.permission(p_kind,'READ'))is distinct from true then
  raise exception using errcode='42501',message='CP7_MASTER_DENIED';end if;
 if p_level<>'READ'and(coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')
   or erp.has_permission(cp7_master.permission(p_kind,'WRITE'))is distinct from true
   or(p_level='PRICE'and erp.has_permission('master.price.edit_draft')is distinct from true))then
  raise exception using errcode='42501',message='CP7_MASTER_DENIED';end if;
 return a;
end $$;

-- The record as the screen reviews it; its md5 is the review token. Timestamps are rendered in UTC so the token does not
-- depend on the session zone.
create function cp7_master.entity(p_kind text,p_id uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select case p_kind
 when'CUSTOMER'then(select jsonb_build_object('id',x.id,'code',x.customer_code,'name',x.customer_name,'active',x.is_active,
   'phone',x.phone,'address',x.address,'created_at',x.created_at,'updated_at',x.updated_at)from erp.customers x where x.id=p_id)
 when'SUPPLIER'then(select jsonb_build_object('id',x.id,'code',x.supplier_code,'name',x.supplier_name,'active',x.is_active,
   'supplier_type',x.supplier_type,'phone',x.phone,'address',x.address,'created_at',x.created_at)from erp.suppliers x where x.id=p_id)
 when'LAUNDRY_VENDOR'then(select jsonb_build_object('id',x.id,'code',x.vendor_code,'name',x.vendor_name,'active',x.is_active,
   'phone',x.phone,'notes',x.notes,'created_at',x.created_at,'updated_at',x.updated_at)from erp.laundry_vendors x where x.id=p_id)
 when'MANDOR'then(select jsonb_build_object('id',x.id,'code',x.contractor_code,'name',x.contractor_name,'active',x.is_active,
   'attendance_required',x.attendance_required,'notes',x.notes,'created_at',x.created_at,'updated_at',x.updated_at,
   'policies',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'effective_from',p.effective_from,'effective_to',p.effective_to,
     'is_special',p.is_special,'attendance_required',p.attendance_required_snapshot,'reason',p.reason,'row_version',p.row_version)
     order by p.effective_from,p.id)from erp.contractor_hpp_policy_versions p where p.contractor_id=x.id),'[]'::jsonb))
   from erp.contractors x where x.id=p_id and x.contractor_type='MANDOR')
 when'LOCATION'then(select jsonb_build_object('id',x.id,'code',x.location_code,'name',x.location_name,'active',x.is_active,
   'location_type',x.location_type,'zone',(select z.zone_kind from erp.bc_accessory_zones_v1 z where z.location_id=x.id),
   'created_at',x.created_at)from erp.locations x where x.id=p_id)
 when'FABRIC'then(select jsonb_build_object('id',x.id,'code',x.material_sku,'name',x.material_name,'active',x.is_active,
   'unit',x.unit_code,'row_version',x.row_version,'stock',x.cached_stock_qty::text,'updated_at',x.updated_at,
   'profile',(select jsonb_build_object('fabric_category',f.fabric_category,'composition',f.composition,'construction',f.construction,
     'color_name',f.color_name,'width_cm',f.width_cm::text,'gsm',f.gsm::text,'minimum_stock_qty',f.minimum_stock_qty::text,
     'preferred_supplier_id',f.preferred_supplier_id,
     'preferred_supplier_name',(select s.supplier_name from erp.suppliers s where s.id=f.preferred_supplier_id),
     'notes',f.notes,'row_version',f.row_version)from erp.fabric_master_profiles f where f.material_id=x.id),
   'benchmarks',coalesce((select jsonb_agg(jsonb_build_object('id',v.id,'price',v.benchmark_price_per_base_uom::text,
     'unit',v.base_uom_code_snapshot,'effective_from',v.effective_from,'effective_to',v.effective_to,'reason',v.change_reason)
     order by v.effective_from,v.id)from erp.fabric_benchmark_price_versions v where v.material_id=x.id),'[]'::jsonb))
   from erp.materials x where x.id=p_id and x.material_type='FABRIC')
 when'ACCESSORY_CATEGORY'then(select jsonb_build_object('id',x.id,'code',x.category_code,'name',x.category_name,'active',x.is_active,
   'base_uom',x.base_uom_code,'notes',x.notes,'row_version',x.row_version,'updated_at',x.updated_at,
   'prices',coalesce((select jsonb_agg(jsonb_build_object('id',v.id,'contractor_id',v.contractor_id,
     'contractor_name',(select c.contractor_name from erp.contractors c where c.id=v.contractor_id),'price',v.selling_price::text,
     'uom',v.selling_uom_code,'effective_from',v.effective_from,'effective_to',v.effective_to,'notes',v.notes)
     order by v.contractor_id nulls first,v.effective_from,v.id)from erp.contractor_accessory_price_versions v where v.category_id=x.id),'[]'::jsonb))
   from erp.accessory_categories x where x.id=p_id)
 when'ACCESSORY'then(select jsonb_build_object('id',x.id,'code',x.material_sku,'name',x.material_name,'active',x.is_active,
   'unit',x.unit_code,'category_id',x.accessory_category_id,
   'category_name',(select c.category_name from erp.accessory_categories c where c.id=x.accessory_category_id),
   'row_version',x.row_version,'stock',x.cached_stock_qty::text,'updated_at',x.updated_at)
   from erp.materials x where x.id=p_id and x.material_type='ACCESSORY')
 end$$;

-- What already points at the record ("Dipakai di"); any document count other than the informational ones makes the
-- record used, so its code (and a location's type, a material's unit, a category's base unit) no longer changes.
create function cp7_master.usage(p_kind text,p_id uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select case p_kind
 when'CUSTOMER'then jsonb_build_object(
  'sales',(select count(*)from erp.sales_headers x where x.customer_id=p_id),
  'sales_draft',(select count(*)from erp.sales_headers x where x.customer_id=p_id and x.status='DRAFT'),
  'returns',(select count(*)from erp.sales_returns x where x.customer_id=p_id),
  'opening',(select count(*)from erp.opening_balance_items x where x.customer_id=p_id)+(select count(*)from erp.opening_subledger_balances x where x.customer_id=p_id))
 when'SUPPLIER'then jsonb_build_object(
  'purchases',(select count(*)from erp.material_purchase_headers x where x.supplier_id=p_id),
  'purchase_draft',(select count(*)from erp.material_purchase_headers x where x.supplier_id=p_id and x.status='DRAFT'),
  'invoices',(select count(*)from erp.material_supplier_invoices x where x.supplier_id=p_id),
  'rolls',(select count(*)from erp.material_rolls x where x.supplier_id=p_id),
  'returns',(select count(*)from erp.material_supplier_returns x where x.supplier_id=p_id),
  'opening',(select count(*)from erp.opening_balance_items x where x.supplier_id=p_id)+(select count(*)from erp.opening_subledger_balances x where x.supplier_id=p_id))
 when'LAUNDRY_VENDOR'then jsonb_build_object(
  'deliveries',(select count(*)from erp.laundry_deliveries x where x.vendor_id=p_id),
  'deliveries_open',(select count(*)from erp.laundry_deliveries x where x.vendor_id=p_id and x.status in('DRAFT','SENT','PARTIAL_RETURN')),
  'invoices',(select count(*)from erp.vendor_invoices x where x.vendor_id=p_id),
  'claims',(select count(*)from erp.laundry_claims x where x.vendor_id=p_id),
  'opening',(select count(*)from erp.opening_balance_items x where x.vendor_id=p_id)+(select count(*)from erp.opening_subledger_balances x where x.vendor_id=p_id))
 when'MANDOR'then jsonb_build_object(
  'production_orders',(select count(*)from erp.production_orders x where x.contractor_id=p_id),
  'production_open',(select count(*)from erp.production_orders x where x.contractor_id=p_id and x.status not in('FINISHED','CANCELLED')),
  'pickups',(select count(*)from erp.cutting_pickups x where x.contractor_id=p_id),
  'work',(select count(*)from erp.work_completion_events x where x.contractor_id=p_id),
  'payrolls',(select count(*)from erp.payroll_settlements x where x.contractor_id=p_id),
  'issues',(select count(*)from erp.contractor_material_issues x where x.contractor_id=p_id),
  'opening',(select count(*)from erp.opening_balance_items x where x.contractor_id=p_id)+(select count(*)from erp.opening_subledger_balances x where x.contractor_id=p_id),
  'work_rates',(select count(*)from erp.contractor_work_rates x where x.contractor_id=p_id))
 when'LOCATION'then jsonb_build_object(
  'material_moves',(select count(*)from erp.material_stock_movements x where x.location_id=p_id),
  'fg_moves',(select count(*)from erp.fg_stock_movements x where x.location_id=p_id),
  'purchases',(select count(*)from erp.material_purchase_headers x where x.location_id=p_id),
  'sales',(select count(*)from erp.sales_headers x where x.source_location_id=p_id),
  'material_qty',(select coalesce(sum(x.qty_signed),0)::text from erp.material_stock_movements x where x.location_id=p_id),
  'fg_qty',(select coalesce(sum(x.qty_signed),0)from erp.fg_stock_movements x where x.location_id=p_id))
 when'FABRIC'then jsonb_build_object(
  'rolls',(select count(*)from erp.material_rolls x where x.material_id=p_id),
  'moves',(select count(*)from erp.material_stock_movements x where x.material_id=p_id),
  'purchase_lines',(select count(*)from erp.material_purchase_items x where x.material_id=p_id))
 when'ACCESSORY'then jsonb_build_object(
  'moves',(select count(*)from erp.material_stock_movements x where x.material_id=p_id),
  'purchase_lines',(select count(*)from erp.material_purchase_items x where x.material_id=p_id),
  'issues',(select count(*)from erp.contractor_material_issue_items x where x.material_id=p_id))
 when'ACCESSORY_CATEGORY'then jsonb_build_object(
  'variants',(select count(*)from erp.materials x where x.accessory_category_id=p_id),
  'variants_active',(select count(*)from erp.materials x where x.accessory_category_id=p_id and x.is_active),
  'prices',(select count(*)from erp.contractor_accessory_price_versions x where x.category_id=p_id),
  'bom_items',(select count(*)from erp.accessory_bom_items x where x.category_id=p_id))
 end$$;

create function cp7_master.used(p_kind text,p_id uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from jsonb_each_text(cp7_master.usage(p_kind,p_id))u
  where u.key not in('sales_draft','purchase_draft','deliveries_open','production_open','work_rates','material_qty','fg_qty','variants_active')
   and u.value::numeric<>0)$$;

-- Deactivation is refused while the record still holds something that needs it; the stock predicates are those of the
-- Native guards (erp.guard_location_identity_and_deactivation, save_fabric_master_v2, save_accessory_material_v2,
-- save_accessory_category_v2), so the screen and the database agree.
create function cp7_master.deactivate_blockers(p_kind text,p_id uuid)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare b jsonb:='[]';n numeric;f bigint;t text;
begin
 case p_kind
 when'CUSTOMER'then
  select count(*)into f from erp.sales_headers where customer_id=p_id and status='DRAFT';
  if f>0 then b:=b||jsonb_build_array(jsonb_build_object('kind','OPEN_SALES_DRAFT','count',f));end if;
 when'SUPPLIER'then
  select count(*)into f from erp.material_purchase_headers where supplier_id=p_id and status='DRAFT';
  if f>0 then b:=b||jsonb_build_array(jsonb_build_object('kind','OPEN_PURCHASE_DRAFT','count',f));end if;
 when'LAUNDRY_VENDOR'then
  select count(*)into f from erp.laundry_deliveries where vendor_id=p_id and status in('DRAFT','SENT','PARTIAL_RETURN');
  if f>0 then b:=b||jsonb_build_array(jsonb_build_object('kind','OPEN_LAUNDRY_DELIVERY','count',f));end if;
 when'MANDOR'then
  select count(*)into f from erp.production_orders where contractor_id=p_id and status not in('FINISHED','CANCELLED');
  if f>0 then b:=b||jsonb_build_array(jsonb_build_object('kind','OPEN_PRODUCTION_ORDER','count',f));end if;
 when'LOCATION'then
  select location_type into t from erp.locations where id=p_id;
  if t not in('RAW_MATERIAL_WAREHOUSE','FG_WAREHOUSE','SCRAP_AREA','OTHER')then
   b:=b||jsonb_build_array(jsonb_build_object('kind','SYSTEM_LOCATION','location_type',t));end if;
  select coalesce(sum(qty_signed),0)into n from erp.material_stock_movements where location_id=p_id;
  select coalesce(sum(qty_signed),0)into f from erp.fg_stock_movements where location_id=p_id;
  if abs(n)>0.000001 or f<>0 then
   b:=b||jsonb_build_array(jsonb_build_object('kind','STOCK_AT_LOCATION','material_qty',n::text,'fg_qty',f));end if;
 when'FABRIC','ACCESSORY'then
  select cached_stock_qty into n from erp.materials where id=p_id;
  if abs(n)>0.000001 then b:=b||jsonb_build_array(jsonb_build_object('kind','STOCK_ON_HAND','qty',n::text));end if;
 when'ACCESSORY_CATEGORY'then
  select count(*)into f from erp.materials where accessory_category_id=p_id and is_active;
  if f>0 then b:=b||jsonb_build_array(jsonb_build_object('kind','ACTIVE_VARIANTS','count',f));end if;
 else null;
 end case;
 return b;
end $$;

-- The Native audit log of the record (with the change reason), newest first. Rows that only move a material's cached
-- stock or average cost are not master changes and are left out.
create function cp7_master.audit(p_kind text,p_id uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce(jsonb_agg(jsonb_build_object('at',z.changed_at,'table',z.entity_type,'action',z.action,
   'actor',(select u.full_name from erp.app_users u where u.id=z.changed_by),'reason',z.change_reason,'fields',z.fields)
   order by z.changed_at desc,z.id desc),'[]'::jsonb)
 from(select l.id,l.changed_at,l.entity_type,l.action,l.changed_by,l.change_reason,
   coalesce((select jsonb_agg(k order by k)from jsonb_object_keys(coalesce(l.new_data,'{}'::jsonb)||coalesce(l.old_data,'{}'::jsonb))k
    where k not in('updated_at','row_version','created_at','updated_by','created_by','cached_stock_qty','moving_average_cost')
     and(l.old_data->k)is distinct from(l.new_data->k)),'[]'::jsonb)fields
  from erp.audit_logs l where l.entity_id=p_id and l.entity_type=any(case p_kind
   when'CUSTOMER'then array['customers']when'SUPPLIER'then array['suppliers']when'LAUNDRY_VENDOR'then array['laundry_vendors']
   when'MANDOR'then array['contractors']when'LOCATION'then array['locations']when'FABRIC'then array['materials','fabric_master_profiles']
   when'ACCESSORY_CATEGORY'then array['accessory_categories']when'ACCESSORY'then array['materials']end)
  order by l.changed_at desc,l.id desc limit 200)z
 where z.action<>'UPDATE'or jsonb_array_length(z.fields)>0$$;

-- One page of the list; the search is a plain substring of code and name (no pattern characters).
create function cp7_master.rows(p_kind text,p_q text,p_status text,p_offset integer,p_limit integer)returns jsonb
language sql stable security definer set search_path=''as $$
 with base as(
  select x.id,x.customer_code::text code,x.customer_name::text name,x.is_active active,jsonb_build_object('phone',x.phone)extra
   from erp.customers x where p_kind='CUSTOMER'
  union all select x.id,x.supplier_code,x.supplier_name,x.is_active,jsonb_build_object('supplier_type',x.supplier_type,'phone',x.phone)
   from erp.suppliers x where p_kind='SUPPLIER'
  union all select x.id,x.vendor_code,x.vendor_name,x.is_active,jsonb_build_object('phone',x.phone)
   from erp.laundry_vendors x where p_kind='LAUNDRY_VENDOR'
  union all select x.id,x.contractor_code,x.contractor_name,x.is_active,jsonb_build_object('attendance_required',x.attendance_required,
    'is_special',coalesce((select p.is_special from erp.contractor_hpp_policy_versions p where p.contractor_id=x.id
     and p.effective_from<=(clock_timestamp()at time zone'Asia/Jakarta')::date
     and(p.effective_to is null or p.effective_to>=(clock_timestamp()at time zone'Asia/Jakarta')::date)
     order by p.effective_from desc,p.id desc limit 1),false))
   from erp.contractors x where p_kind='MANDOR'and x.contractor_type='MANDOR'
  union all select x.id,x.location_code,x.location_name,x.is_active,jsonb_build_object('location_type',x.location_type)
   from erp.locations x where p_kind='LOCATION'
  union all select x.id,x.material_sku,x.material_name,x.is_active,jsonb_build_object('unit',x.unit_code,'stock',x.cached_stock_qty::text)
   from erp.materials x where p_kind='FABRIC'and x.material_type='FABRIC'
  union all select x.id,x.category_code,x.category_name,x.is_active,jsonb_build_object('base_uom',x.base_uom_code)
   from erp.accessory_categories x where p_kind='ACCESSORY_CATEGORY'
  union all select x.id,x.material_sku,x.material_name,x.is_active,jsonb_build_object('unit',x.unit_code,'stock',x.cached_stock_qty::text,
    'category_name',(select c.category_name from erp.accessory_categories c where c.id=x.accessory_category_id))
   from erp.materials x where p_kind='ACCESSORY'and x.material_type='ACCESSORY'
 ),hit as(
  select * from base where(coalesce(p_q,'')=''or position(lower(p_q)in lower(code||' '||name))>0)
   and(p_status='ALL'or active=(p_status='ACTIVE'))
 )
 select jsonb_build_object('total',(select count(*)from hit),
  'rows',coalesce((select jsonb_agg(jsonb_build_object('id',z.id,'code',z.code,'name',z.name,'active',z.active)||z.extra order by z.code,z.id)
   from(select * from hit order by code,id offset p_offset limit p_limit)z),'[]'::jsonb))$$;

create function cp7_master.options(p_kind text)returns jsonb
language sql stable security definer set search_path=''as $$
 select case p_kind
 when'SUPPLIER'then jsonb_build_object('supplier_types',jsonb_build_array('MATERIAL','ACCESSORY','OTHER'))
 when'LOCATION'then jsonb_build_object('location_types',jsonb_build_array('RAW_MATERIAL_WAREHOUSE','FG_WAREHOUSE','SCRAP_AREA','OTHER'))
 when'FABRIC'then jsonb_build_object(
  'units',(select coalesce(jsonb_agg(u order by u),'[]'::jsonb)from(select upper(unit_code)u from erp.materials where material_type='FABRIC'
    union select upper(unit_code)from erp.uom_definitions where is_active and dimension in('LENGTH','WEIGHT'))z),
  'suppliers',(select coalesce(jsonb_agg(jsonb_build_object('id',s.id,'code',s.supplier_code,'name',s.supplier_name)order by s.supplier_code,s.id),'[]'::jsonb)
    from(select * from erp.suppliers where is_active order by supplier_code,id limit 300)s))
 when'ACCESSORY'then jsonb_build_object(
  'categories',(select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'code',c.category_code,'name',c.category_name,'base_uom',c.base_uom_code)
    order by c.category_code,c.id),'[]'::jsonb)from(select * from erp.accessory_categories where is_active order by category_code,id limit 300)c))
 when'ACCESSORY_CATEGORY'then jsonb_build_object(
  'uoms',(select coalesce(jsonb_agg(jsonb_build_object('code',u.unit_code,'name',u.unit_name)order by u.unit_code),'[]'::jsonb)
    from erp.uom_definitions u where u.is_active),
  'mandors',(select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'code',c.contractor_code,'name',c.contractor_name)order by c.contractor_code,c.id),'[]'::jsonb)
    from(select * from erp.contractors where is_active and contractor_type='MANDOR'order by contractor_code,id limit 300)c))
 else'{}'::jsonb end$$;

create function cp7_master.workspace(p_kind text,p_query jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb:=coalesce(p_query,'{}'::jsonb);v_offset integer;v_limit integer;v_status text;v_id uuid;e jsonb;sel jsonb;
 can_write boolean;can_price boolean;
 uuid_re constant text:='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
 a:=cp7_master.access_now(p_kind,'READ');
 if p_kind='WORK_RATE'or jsonb_typeof(q)<>'object'
  or exists(select 1 from jsonb_object_keys(q)k where k not in('q','status','offset','limit','id'))
  or(q?'q'and(jsonb_typeof(q->'q')<>'string'or length(q->>'q')>80))
  or(q?'status'and(jsonb_typeof(q->'status')<>'string'or(q->>'status')not in('ALL','ACTIVE','INACTIVE')))
  or(q?'offset'and(jsonb_typeof(q->'offset')<>'number'or(q->>'offset')!~'^[0-9]{1,6}$'))
  or(q?'limit'and(jsonb_typeof(q->'limit')<>'number'or(q->>'limit')!~'^[0-9]{1,2}$'or(q->>'limit')::integer not between 1 and 50))
  or(q?'id'and q->'id'<>'null'::jsonb and(jsonb_typeof(q->'id')<>'string'or(q->>'id')!~uuid_re))then
  raise exception 'CP7_MASTER_QUERY';end if;
 v_offset:=coalesce((q->>'offset')::integer,0);v_limit:=coalesce((q->>'limit')::integer,20);v_status:=coalesce(q->>'status','ALL');
 v_id:=case when q->'id'is null or q->'id'='null'::jsonb then null else(q->>'id')::uuid end;
 can_write:=coalesce(a->'profile'->>'role_code','')in('OWNER','ADMIN')and erp.has_permission(cp7_master.permission(p_kind,'WRITE'))is true;
 can_price:=can_write and erp.has_permission('master.price.edit_draft')is true;
 if v_id is not null then
  e:=cp7_master.entity(p_kind,v_id);
  if e is not null then
   sel:=jsonb_build_object('entity',e,'review_token',md5(e::text),'usage',cp7_master.usage(p_kind,v_id),'used',cp7_master.used(p_kind,v_id),
    'deactivate_blockers',case when(e->>'active')::boolean then cp7_master.deactivate_blockers(p_kind,v_id)else'[]'::jsonb end,
    'audit',cp7_master.audit(p_kind,v_id),'history',(select count(*)from cp7_master.history h where h.kind=p_kind and h.entity_id=v_id));
  end if;
 end if;
 if cp7_master.access_now(p_kind,'READ')is distinct from a then raise exception using errcode='42501',message='CP7_MASTER_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.master-workspace.v1','kind',p_kind,'can_write',can_write,'can_price',can_price,
  'today',(clock_timestamp()at time zone'Asia/Jakarta')::date,
  'page',cp7_master.rows(p_kind,q->>'q',v_status,v_offset,v_limit)||jsonb_build_object('offset',v_offset,'limit',v_limit,'query',coalesce(q->>'q',''),'status',v_status),
  'selected',sel,'selected_missing',v_id is not null and e is null,'options',cp7_master.options(p_kind));
end $$;

-- Field set per kind (the client sends the whole form). Strings are trimmed; an empty optional field is null.
create function cp7_master.fields(p_kind text,p_action text,f jsonb)returns jsonb
language plpgsql immutable set search_path=''as $$
declare keys text[];k text;v jsonb;o jsonb:='{}'::jsonb;s text;
 opt text[]:=array['phone','address','notes','fabric_category','composition','construction','color_name','width_cm','gsm',
  'preferred_supplier_id','contractor_id','policy_from'];
 uuid_re constant text:='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
 keys:=case when p_action='SET_BENCHMARK'then array['price','effective_date']
  when p_action='SET_MANDOR_PRICE'then array['contractor_id','price','uom','effective_date','notes']
  when p_kind='CUSTOMER'then array['code','name','phone','address']
  when p_kind='SUPPLIER'then array['code','name','supplier_type','phone','address']
  when p_kind='LAUNDRY_VENDOR'then array['code','name','phone','notes']
  when p_kind='MANDOR'then array['code','name','attendance_required','is_special','policy_from','notes']
  when p_kind='LOCATION'then array['code','name','location_type']
  when p_kind='FABRIC'then array['code','name','unit','fabric_category','composition','construction','color_name','width_cm','gsm',
   'minimum_stock_qty','preferred_supplier_id','notes']
  when p_kind='ACCESSORY_CATEGORY'then array['code','name','base_uom','notes']
  when p_kind='ACCESSORY'then array['code','name','category_id']end;
 if keys is null or jsonb_typeof(f)is distinct from'object'or not(f?&keys)or(select count(*)from jsonb_object_keys(f))<>cardinality(keys)then
  raise exception 'CP7_MASTER_FIELDS';end if;
 foreach k in array keys loop
  v:=f->k;
  if k in('attendance_required','is_special')then
   if jsonb_typeof(v)<>'boolean'then raise exception 'CP7_MASTER_FIELDS: %',k;end if;o:=o||jsonb_build_object(k,v);continue;end if;
  if jsonb_typeof(v)='null'and k=any(opt)then o:=o||jsonb_build_object(k,null);continue;end if;
  if jsonb_typeof(v)<>'string'then raise exception 'CP7_MASTER_FIELDS: %',k;end if;
  s:=btrim(v#>>'{}');
  if s=''then
   if k=any(opt)then o:=o||jsonb_build_object(k,null);continue;end if;
   raise exception 'CP7_MASTER_FIELDS: %',k;end if;
  if s~'[[:cntrl:]]'and k not in('address','notes')then raise exception 'CP7_MASTER_FIELDS: %',k;end if;
  if(k='code'and length(s)>case when p_kind in('FABRIC','ACCESSORY')then 60 when p_kind='ACCESSORY_CATEGORY'then 40 else 30 end)
   or(k='name'and length(s)>case when p_kind in('CUSTOMER','SUPPLIER','FABRIC','ACCESSORY')then 150 else 120 end)
   or(k='phone'and length(s)>50)or(k in('address','composition','construction')and length(s)>500)or(k='notes'and length(s)>1000)
   or(k in('fabric_category','color_name')and length(s)>100)
   or(k='supplier_type'and s not in('MATERIAL','ACCESSORY','OTHER'))
   or(k='location_type'and s not in('RAW_MATERIAL_WAREHOUSE','CUTTING_WIP','CONTRACTOR_WIP','LAUNDRY_WIP','QC_WIP','FG_WAREHOUSE','SCRAP_AREA','OTHER'))
   or(k in('unit','base_uom','uom')and s!~'^[A-Za-z][A-Za-z0-9]{0,19}$')
   or(k in('width_cm','gsm')and(s!~'^[0-9]{1,9}([.][0-9]{1,3})?$'or s::numeric<=0))
   or(k='minimum_stock_qty'and s!~'^[0-9]{1,12}([.][0-9]{1,6})?$')
   or(k in('preferred_supplier_id','category_id','contractor_id')and s!~uuid_re)
   or(k in('effective_date','policy_from')and(s!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'or to_char(to_date(s,'YYYY-MM-DD'),'YYYY-MM-DD')<>s))
   or(k='price'and(s!~case p_action when'SET_BENCHMARK'then'^[0-9]{1,12}([.][0-9]{1,6})?$'else'^[0-9]{1,12}([.][0-9]{1,4})?$'end
     or(p_action='SET_BENCHMARK'and s::numeric<=0)))then
   raise exception 'CP7_MASTER_FIELDS: %',k;end if;
  if k in('unit','base_uom','uom')then s:=upper(s);end if;
  if k='code'and p_kind not in('FABRIC')then s:=upper(s);end if;
  o:=o||jsonb_build_object(k,s);
 end loop;
 return o;
end $$;

create function cp7_master.code_taken(p_kind text,p_code text,p_except uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select case p_kind
 when'CUSTOMER'then exists(select 1 from erp.customers x where lower(x.customer_code)=lower(p_code)and x.id is distinct from p_except)
 when'SUPPLIER'then exists(select 1 from erp.suppliers x where lower(x.supplier_code)=lower(p_code)and x.id is distinct from p_except)
 when'LAUNDRY_VENDOR'then exists(select 1 from erp.laundry_vendors x where lower(x.vendor_code)=lower(p_code)and x.id is distinct from p_except)
 when'MANDOR'then exists(select 1 from erp.contractors x where lower(x.contractor_code)=lower(p_code)and x.id is distinct from p_except)
 when'LOCATION'then exists(select 1 from erp.locations x where lower(x.location_code)=lower(p_code)and x.id is distinct from p_except)
 when'ACCESSORY_CATEGORY'then exists(select 1 from erp.accessory_categories x where lower(x.category_code)=lower(p_code)and x.id is distinct from p_except)
 else exists(select 1 from erp.materials x where lower(x.material_sku)=lower(p_code)and x.id is distinct from p_except)end$$;

-- The record without the stamps every write moves (updated_at, row versions), to tell a real change from none.
create function cp7_master.content(e jsonb)returns jsonb
language sql immutable set search_path=''as $$
 select(e-array['updated_at','row_version'])||case when jsonb_typeof(e->'profile')='object'
  then jsonb_build_object('profile',(e->'profile')-'row_version')else'{}'::jsonb end$$;

-- The policy version of a Mandor that covers a WIB date (Native ranges are inclusive dates).
create function cp7_master.policy_at(p_contractor uuid,p_day date)returns erp.contractor_hpp_policy_versions
language sql stable security definer set search_path=''as $$
 select p from erp.contractor_hpp_policy_versions p where p.contractor_id=p_contractor and p.effective_from<=p_day
  and(p.effective_to is null or p.effective_to>=p_day)order by p.effective_from desc,p.id desc limit 1$$;

create function cp7_master.save(p_kind text,p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare
 a jsonb;old cp7_master.requests;v_action text;v_level text;v_reason text;f jsonb;v_id uuid;e0 jsonb;e1 jsonb;b jsonb;answer jsonb;
 v_actor uuid;v_native uuid;v_today date;v_day date;v_at timestamptz;r jsonb;keys text[];v_profile jsonb;v_policy erp.contractor_hpp_policy_versions;
 v_special boolean;v_prev uuid;v_last timestamptz;v_code_changed boolean;
 uuid_re constant text:='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
 code_re constant text:='^[A-Za-z0-9][A-Za-z0-9._/-]*$';
 work_types constant text[]:=array['RAW_MATERIAL_WAREHOUSE','FG_WAREHOUSE','SCRAP_AREA','OTHER'];
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if p_request is null or jsonb_typeof(p)is distinct from'object'or jsonb_typeof(p->'action')is distinct from'string'then
  raise exception 'CP7_MASTER_FIELDS';end if;
 v_action:=p->>'action';
 v_level:=case when v_action in('SET_BENCHMARK','SET_MANDOR_PRICE')then'PRICE'else'WRITE'end;
 a:=cp7_master.access_now(p_kind,v_level);
 keys:=case when v_action='CREATE'then array['action','fields','reason']
  when v_action in('UPDATE','SET_BENCHMARK','SET_MANDOR_PRICE')then array['action','id','review_token','fields','reason']
  when v_action in('DEACTIVATE','REACTIVATE')then array['action','id','review_token','reason']end;
 if p_kind='WORK_RATE'or keys is null or not(p?&keys)or(select count(*)from jsonb_object_keys(p))<>cardinality(keys)
  or(v_action='SET_BENCHMARK'and p_kind<>'FABRIC')or(v_action='SET_MANDOR_PRICE'and p_kind<>'ACCESSORY_CATEGORY')
  or jsonb_typeof(p->'reason')is distinct from'string'or length(btrim(p->>'reason'))not between 5 and 1000
  or(p?'id'and(jsonb_typeof(p->'id')<>'string'or(p->>'id')!~uuid_re))
  or(p?'review_token'and(jsonb_typeof(p->'review_token')<>'string'or(p->>'review_token')!~'^[a-f0-9]{32}$'))then
  raise exception 'CP7_MASTER_FIELDS';end if;
 v_reason:=btrim(p->>'reason');
 if p?'fields'then f:=cp7_master.fields(p_kind,v_action,p->'fields');end if;
 insert into cp7_master.requests values(auth.uid(),p_request,p_kind,p,null)on conflict do nothing;
 select*into strict old from cp7_master.requests where actor=auth.uid()and request_id=p_request for update;
 if old.kind is distinct from p_kind or old.payload is distinct from p then raise exception 'CP7_MASTER_REQUEST_CHANGED';end if;
 if cp7_master.access_now(p_kind,v_level)is distinct from a then raise exception using errcode='42501',message='CP7_MASTER_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 v_actor:=erp.current_app_user_id();
 if v_actor is null then raise exception using errcode='42501',message='CP7_MASTER_DENIED';end if;
 v_today:=(clock_timestamp()at time zone'Asia/Jakarta')::date;
 -- One Native request id per facade request, distinct per actor (the Native idempotency key has no actor).
 v_native:=md5(auth.uid()::text||':'||p_request::text||':cp7-master')::uuid;
 perform set_config('app.change_reason',v_reason,true);

 if v_action='CREATE'then
  if(f->>'code')!~code_re then raise exception 'CP7_MASTER_FIELDS: code';end if;
  perform pg_advisory_xact_lock(hashtextextended('CP7MASTER:'||case when p_kind in('FABRIC','ACCESSORY')then'MATERIAL'else p_kind end||':'||lower(f->>'code'),0));
  if cp7_master.code_taken(p_kind,f->>'code',null)then raise exception 'CP7_MASTER_DUPLICATE_CODE';end if;
  case p_kind
  when'CUSTOMER'then
   insert into erp.customers(customer_code,customer_name,phone,address,is_active)
   values(f->>'code',f->>'name',f->>'phone',f->>'address',true)returning id into v_id;
  when'SUPPLIER'then
   insert into erp.suppliers(supplier_code,supplier_name,supplier_type,phone,address,is_active)
   values(f->>'code',f->>'name',f->>'supplier_type',f->>'phone',f->>'address',true)returning id into v_id;
  when'LAUNDRY_VENDOR'then
   insert into erp.laundry_vendors(vendor_code,vendor_name,phone,notes,is_active)
   values(f->>'code',f->>'name',f->>'phone',f->>'notes',true)returning id into v_id;
  when'MANDOR'then
   -- A new Mandor starts with an attendance HPP policy (regular or Special) from a date the user names.
   if f->>'policy_from'is null then raise exception 'CP7_MASTER_POLICY_DATE';end if;
   insert into erp.contractors(contractor_code,contractor_name,contractor_type,attendance_required,notes,is_active)
   values(f->>'code',f->>'name','MANDOR',(f->>'attendance_required')::boolean,f->>'notes',true)returning id into v_id;
   perform erp.set_contractor_hpp_policy_v1(jsonb_build_object('contractor_id',v_id::text,'effective_from',f->>'policy_from',
    'is_special',(f->>'is_special')::boolean,'attendance_required',(f->>'attendance_required')::boolean,'reason',v_reason),v_native,null);
  when'LOCATION'then
   if not((f->>'location_type')=any(work_types))then raise exception 'CP7_MASTER_LOCATION_TYPE';end if;
   insert into erp.locations(location_code,location_name,location_type,is_active)
   values(f->>'code',f->>'name',f->>'location_type',true)returning id into v_id;
  when'FABRIC'then
   if f->>'preferred_supplier_id'is not null and not exists(select 1 from erp.suppliers where id=(f->>'preferred_supplier_id')::uuid and is_active)then
    raise exception 'CP7_MASTER_SUPPLIER_INACTIVE';end if;
   r:=erp.save_fabric_master_v2(jsonb_build_object('material_sku',f->>'code','material_name',f->>'name','unit_code',f->>'unit','is_active',true,
    'change_reason',v_reason,'profile',f-array['code','name','unit']),v_native,null);
   v_id:=(r->>'material_id')::uuid;
  when'ACCESSORY_CATEGORY'then
   if not exists(select 1 from erp.uom_definitions where upper(unit_code)=f->>'base_uom'and is_active)then raise exception 'CP7_MASTER_UOM';end if;
   r:=erp.save_accessory_category_v2(jsonb_build_object('category_code',f->>'code','category_name',f->>'name','base_uom_code',f->>'base_uom',
    'is_active',true,'notes',f->>'notes','change_reason',v_reason),v_native,null);
   v_id:=(r->>'accessory_category_id')::uuid;
  when'ACCESSORY'then
   if not exists(select 1 from erp.accessory_categories where id=(f->>'category_id')::uuid and is_active)then raise exception 'CP7_MASTER_CATEGORY_INACTIVE';end if;
   r:=erp.save_accessory_material_v2(jsonb_build_object('material_sku',f->>'code','material_name',f->>'name','accessory_category_id',f->>'category_id',
    'is_active',true,'change_reason',v_reason),v_native,null);
   v_id:=(r->>'material_id')::uuid;
  end case;
  e0:=null;
 else
  v_id:=(p->>'id')::uuid;
  -- The record row first, then its review token.
  case p_kind
  when'CUSTOMER'then perform 1 from erp.customers where id=v_id for update;
  when'SUPPLIER'then perform 1 from erp.suppliers where id=v_id for update;
  when'LAUNDRY_VENDOR'then perform 1 from erp.laundry_vendors where id=v_id for update;
  when'MANDOR'then perform 1 from erp.contractors where id=v_id and contractor_type='MANDOR'for update;
  when'LOCATION'then perform 1 from erp.locations where id=v_id for update;
  when'ACCESSORY_CATEGORY'then perform 1 from erp.accessory_categories where id=v_id for update;
  else perform 1 from erp.materials where id=v_id and material_type=p_kind for update;
  end case;
  if not found then raise exception 'CP7_MASTER_NOT_FOUND';end if;
  e0:=cp7_master.entity(p_kind,v_id);
  if md5(e0::text)is distinct from p->>'review_token'then raise exception 'CP7_MASTER_REVIEW_CHANGED';end if;

  if v_action='UPDATE'then
   v_code_changed:=(f->>'code')is distinct from(e0->>'code');
   if p_kind in('FABRIC','ACCESSORY')and(v_code_changed or(f->>'name')is distinct from(e0->>'name'))then
    -- A material's name and code are corrected only through the audited rename (material-name.sql).
    raise exception 'CP7_MASTER_USE_RENAME';end if;
   if v_code_changed then
    if(f->>'code')!~code_re then raise exception 'CP7_MASTER_FIELDS: code';end if;
    if cp7_master.used(p_kind,v_id)then raise exception 'CP7_MASTER_CODE_IN_USE';end if;
    perform pg_advisory_xact_lock(hashtextextended('CP7MASTER:'||p_kind||':'||lower(f->>'code'),0));
    if cp7_master.code_taken(p_kind,f->>'code',v_id)then raise exception 'CP7_MASTER_DUPLICATE_CODE';end if;
   end if;
   case p_kind
   when'CUSTOMER'then
    update erp.customers set customer_code=f->>'code',customer_name=f->>'name',phone=f->>'phone',address=f->>'address'where id=v_id;
   when'SUPPLIER'then
    update erp.suppliers set supplier_code=f->>'code',supplier_name=f->>'name',supplier_type=f->>'supplier_type',phone=f->>'phone',
     address=f->>'address'where id=v_id;
   when'LAUNDRY_VENDOR'then
    update erp.laundry_vendors set vendor_code=f->>'code',vendor_name=f->>'name',phone=f->>'phone',notes=f->>'notes'where id=v_id;
   when'MANDOR'then
    -- The HPP policy is dated: a change of attendance or Special needs the date it applies from; the contractor flag is
    -- written first because the Native policy writer requires it to match.
    v_day:=coalesce((f->>'policy_from')::date,v_today);
    v_policy:=cp7_master.policy_at(v_id,v_day);
    v_special:=coalesce(v_policy.is_special,false);
    if f->>'policy_from'is null and((f->>'attendance_required')::boolean is distinct from(e0->>'attendance_required')::boolean
      or(f->>'is_special')::boolean is distinct from v_special)then raise exception 'CP7_MASTER_POLICY_DATE';end if;
    update erp.contractors set contractor_code=f->>'code',contractor_name=f->>'name',attendance_required=(f->>'attendance_required')::boolean,
     notes=f->>'notes'where id=v_id;
    if f->>'policy_from'is not null then
     if v_policy.id is not null and v_policy.effective_from=v_day then raise exception 'CP7_MASTER_POLICY_SAME_DAY';end if;
     perform erp.set_contractor_hpp_policy_v1(jsonb_build_object('contractor_id',v_id::text,'effective_from',f->>'policy_from',
      'is_special',(f->>'is_special')::boolean,'attendance_required',(f->>'attendance_required')::boolean,'reason',v_reason),v_native,v_policy.id);
    end if;
   when'LOCATION'then
    if(f->>'location_type')is distinct from(e0->>'location_type')then
     if not((f->>'location_type')=any(work_types))or not((e0->>'location_type')=any(work_types))then raise exception 'CP7_MASTER_LOCATION_TYPE';end if;
     if e0->>'zone'is not null then raise exception 'CP7_MASTER_TYPE_IN_USE';end if;
     if exists(select 1 from erp.material_stock_movements where location_id=v_id)or exists(select 1 from erp.fg_stock_movements where location_id=v_id)then
      raise exception 'CP7_MASTER_TYPE_IN_USE';end if;
    end if;
    update erp.locations set location_code=f->>'code',location_name=f->>'name',location_type=f->>'location_type'where id=v_id;
   when'FABRIC'then
    if upper(e0->>'unit')is distinct from f->>'unit'and(exists(select 1 from erp.material_stock_movements where material_id=v_id)
      or exists(select 1 from erp.material_rolls where material_id=v_id)or exists(select 1 from erp.material_purchase_items where material_id=v_id))then
     raise exception 'CP7_MASTER_UNIT_IN_USE';end if;
    if f->>'preferred_supplier_id'is not null and(f->>'preferred_supplier_id')is distinct from(e0->'profile'->>'preferred_supplier_id')
      and not exists(select 1 from erp.suppliers where id=(f->>'preferred_supplier_id')::uuid and is_active)then
     raise exception 'CP7_MASTER_SUPPLIER_INACTIVE';end if;
    perform erp.save_fabric_master_v2(jsonb_build_object('id',v_id,'material_sku',e0->>'code','material_name',e0->>'name','unit_code',f->>'unit',
     'is_active',(e0->>'active')::boolean,'change_reason',v_reason,'profile',f-array['code','name','unit']),v_native,(e0->>'row_version')::bigint);
   when'ACCESSORY_CATEGORY'then
    if upper(e0->>'base_uom')is distinct from f->>'base_uom'and cp7_master.used(p_kind,v_id)then raise exception 'CP7_MASTER_UOM_IN_USE';end if;
    if not exists(select 1 from erp.uom_definitions where upper(unit_code)=f->>'base_uom'and is_active)then raise exception 'CP7_MASTER_UOM';end if;
    perform erp.save_accessory_category_v2(jsonb_build_object('id',v_id,'category_code',f->>'code','category_name',f->>'name',
     'base_uom_code',f->>'base_uom','is_active',(e0->>'active')::boolean,'notes',f->>'notes','change_reason',v_reason),v_native,(e0->>'row_version')::bigint);
   when'ACCESSORY'then
    if(f->>'category_id')is distinct from(e0->>'category_id')then
     if exists(select 1 from erp.material_stock_movements where material_id=v_id)then raise exception 'CP7_MASTER_CATEGORY_IN_USE';end if;
     if not exists(select 1 from erp.accessory_categories where id=(f->>'category_id')::uuid and is_active)then raise exception 'CP7_MASTER_CATEGORY_INACTIVE';end if;
    end if;
    perform erp.save_accessory_material_v2(jsonb_build_object('id',v_id,'material_sku',e0->>'code','material_name',e0->>'name',
     'accessory_category_id',f->>'category_id','is_active',(e0->>'active')::boolean,'change_reason',v_reason),v_native,(e0->>'row_version')::bigint);
   end case;

  elsif v_action in('DEACTIVATE','REACTIVATE')then
   if(e0->>'active')::boolean=(v_action='REACTIVATE')then raise exception 'CP7_MASTER_ALREADY_%',case when v_action='REACTIVATE'then'ACTIVE'else'INACTIVE'end;end if;
   if v_action='DEACTIVATE'then
    b:=cp7_master.deactivate_blockers(p_kind,v_id);
    if jsonb_array_length(b)<>0 then raise exception 'CP7_MASTER_BLOCKED: %',b;end if;
   elsif p_kind='ACCESSORY'and not exists(select 1 from erp.accessory_categories where id=(e0->>'category_id')::uuid and is_active)then
    raise exception 'CP7_MASTER_CATEGORY_INACTIVE';
   end if;
   case p_kind
   when'CUSTOMER'then update erp.customers set is_active=(v_action='REACTIVATE')where id=v_id;
   when'SUPPLIER'then update erp.suppliers set is_active=(v_action='REACTIVATE')where id=v_id;
   when'LAUNDRY_VENDOR'then update erp.laundry_vendors set is_active=(v_action='REACTIVATE')where id=v_id;
   when'MANDOR'then update erp.contractors set is_active=(v_action='REACTIVATE')where id=v_id;
   when'LOCATION'then update erp.locations set is_active=(v_action='REACTIVATE')where id=v_id;
   when'FABRIC'then
    v_profile:=coalesce(e0->'profile','{}'::jsonb)-array['row_version','preferred_supplier_name'];
    perform erp.save_fabric_master_v2(jsonb_build_object('id',v_id,'material_sku',e0->>'code','material_name',e0->>'name','unit_code',e0->>'unit',
     'is_active',v_action='REACTIVATE','change_reason',v_reason,'profile',v_profile),v_native,(e0->>'row_version')::bigint);
   when'ACCESSORY_CATEGORY'then
    perform erp.save_accessory_category_v2(jsonb_build_object('id',v_id,'category_code',e0->>'code','category_name',e0->>'name',
     'base_uom_code',e0->>'base_uom','is_active',v_action='REACTIVATE','notes',e0->>'notes','change_reason',v_reason),v_native,(e0->>'row_version')::bigint);
   when'ACCESSORY'then
    perform erp.save_accessory_material_v2(jsonb_build_object('id',v_id,'material_sku',e0->>'code','material_name',e0->>'name',
     'accessory_category_id',e0->>'category_id','is_active',v_action='REACTIVATE','change_reason',v_reason),v_native,(e0->>'row_version')::bigint);
   end case;

  elsif v_action='SET_BENCHMARK'then
   -- A new benchmark starts at 00:00 WIB of its date, after the current version's start (Native rule).
   v_at:=((f->>'effective_date')::date)::timestamp at time zone'Asia/Jakarta';
   if exists(select 1 from erp.fabric_benchmark_price_versions where material_id=v_id and effective_from>=v_at)then
    raise exception 'CP7_MASTER_BENCHMARK_DATE';end if;
   perform erp.set_fabric_benchmark_price_v2(v_id,(f->>'price')::numeric,v_at,v_reason,v_native,(e0->>'row_version')::bigint);

  elsif v_action='SET_MANDOR_PRICE'then
   -- The Mandor accessory price (contractor null = the price for every Mandor without his own) from 00:00 WIB of its date.
   if(e0->>'active')::boolean is distinct from true then raise exception 'CP7_MASTER_CATEGORY_INACTIVE';end if;
   if f->>'contractor_id'is not null and not exists(select 1 from erp.contractors where id=(f->>'contractor_id')::uuid and is_active and contractor_type='MANDOR')then
    raise exception 'CP7_MASTER_MANDOR_INACTIVE';end if;
   v_at:=((f->>'effective_date')::date)::timestamp at time zone'Asia/Jakarta';
   if exists(select 1 from erp.contractor_accessory_price_versions where category_id=v_id and contractor_id is not distinct from(f->>'contractor_id')::uuid
     and effective_from=v_at)then raise exception 'CP7_MASTER_PRICE_DATE';end if;
   select v.id into v_prev from erp.contractor_accessory_price_versions v where v.category_id=v_id
    and v.contractor_id is not distinct from(f->>'contractor_id')::uuid and v.effective_from<v_at and(v.effective_to is null or v.effective_to>v_at)
    order by v.effective_from desc limit 1;
   if v_prev is not null then
    select max(i.physical_at)into v_last from erp.contractor_material_issue_items ii join erp.contractor_material_issues i on i.id=ii.issue_id
     where ii.accessory_price_version_id=v_prev;
    if v_last is not null and v_at<=v_last then raise exception 'CP7_MASTER_PRICE_USED_UNTIL: %',(v_last at time zone'Asia/Jakarta')::date;end if;
   end if;
   begin
    perform erp.accessory_uom_factor(v_id,f->>'uom',v_at);
   exception when others then raise exception 'CP7_MASTER_UOM_CONVERSION';
   end;
   perform erp.set_accessory_selling_price_v2(v_id,(f->>'contractor_id')::uuid,(f->>'price')::numeric,f->>'uom',v_at,f->>'notes',v_reason,v_native,v_prev);
  end if;
 end if;

 e1:=cp7_master.entity(p_kind,v_id);
 if e1 is null then raise exception 'CP7_MASTER_INCOMPLETE';end if;
 if v_action='UPDATE'and cp7_master.content(e1)=cp7_master.content(e0)then raise exception 'CP7_MASTER_NO_CHANGE';end if;
 if v_action in('CREATE','REACTIVATE')and(e1->>'active')::boolean is distinct from true
  or v_action='DEACTIVATE'and(e1->>'active')::boolean is distinct from false then raise exception 'CP7_MASTER_INCOMPLETE';end if;
 insert into cp7_master.history(kind,entity_id,action,before,after,reason,actor,request_id)
 values(p_kind,v_id,v_action,e0,e1,v_reason,auth.uid(),p_request);
 if cp7_master.access_now(p_kind,v_level)is distinct from a then raise exception using errcode='42501',message='CP7_MASTER_ACCESS_CHANGED';end if;
 answer:=jsonb_build_object('contract_version','cp7.master-outcome.v1','kind','COMMITTED_OUTCOME','master_kind',p_kind,'action',v_action,
  'request_id',p_request,'id',v_id,'entity',e1,'review_token',md5(e1::text));
 update cp7_master.requests set response=answer where actor=auth.uid()and request_id=p_request;
 return answer;
end $$;

create function public.erp_cp7_get_master_v1(p_kind text,p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_master.workspace(p_kind,p_query)$$;
create function public.erp_cp7_save_master_v1(p_kind text,p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_master.save(p_kind,p_payload,p_request)$$;
