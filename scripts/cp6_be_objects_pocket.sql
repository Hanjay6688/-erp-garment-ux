-- ALL-C04: evidenced historical expense and sewing output. No synthetic stock/work events.
create table erp.be_pocket_usage_v1(
 id uuid primary key,source_row_id uuid not null unique references erp.migration_staging_rows(id),batch_id uuid not null references erp.migration_batches(id),
 document_number text not null,line_number text not null,physical_date date not null,material_id uuid not null references erp.materials(id),
 material_qty numeric(18,6) not null check(material_qty>0),original_amount numeric(20,2) not null check(original_amount>0),
 allocation_status text not null check(allocation_status in('ALLOCATED','UNALLOCATED')),prior_allocation_reference text,
 journal_id uuid references erp.journal_entries(id),created_at timestamptz not null default statement_timestamp(),
 check((allocation_status='ALLOCATED')=(prior_allocation_reference is not null))
);
create unique index be_pocket_usage_identity on erp.be_pocket_usage_v1(lower(btrim(document_number)),lower(btrim(line_number)));
create table erp.be_pocket_sewing_v1(
 id uuid primary key,source_row_id uuid not null unique references erp.migration_staging_rows(id),batch_id uuid not null references erp.migration_batches(id),
 document_number text not null,line_number text not null,physical_date date not null,contractor_id uuid not null references erp.contractors(id),
 qty bigint not null check(qty>0),target_kind text not null check(target_kind in('WIP','BS','FINISHED_GOODS','COGS')),
 opening_item_id uuid references erp.opening_balance_items(id),po_id uuid references erp.production_orders(id),product_id uuid references erp.products(id),
 sold_reference text,created_at timestamptz not null default statement_timestamp(),
 check((target_kind='COGS' and opening_item_id is null and product_id is not null and sold_reference is not null)
   or (target_kind<>'COGS' and opening_item_id is not null and sold_reference is null))
);
create unique index be_pocket_sewing_identity on erp.be_pocket_sewing_v1(lower(btrim(document_number)),lower(btrim(line_number)));
create table erp.be_pocket_source_events_v1(
 id uuid primary key,usage_id uuid not null references erp.be_pocket_usage_v1(id),previous_amount numeric(20,2) not null,
 new_amount numeric(20,2) not null check(new_amount>=0),economic_date date not null,reason text not null,
 journal_id uuid not null references erp.journal_entries(id),created_by uuid,created_at timestamptz not null default clock_timestamp()
);
create table erp.be_pocket_target_events_v1(
 id uuid primary key default gen_random_uuid(),pool_id uuid not null references erp.pocket_periods(id),
 sewing_id uuid not null references erp.be_pocket_sewing_v1(id),opening_item_id uuid not null references erp.opening_balance_items(id),
 previous_amount numeric(20,2) not null,new_amount numeric(20,2) not null,economic_date date not null,
 created_by uuid,created_at timestamptz not null default clock_timestamp()
);
-- Preserve the old unique native source identity; add an explicit alternative FK for history.
alter table erp.pocket_period_sources drop constraint pocket_period_sources_pkey;
alter table erp.pocket_period_sources alter column adjustment_id drop not null;
alter table erp.pocket_period_sources add column historical_usage_id uuid references erp.be_pocket_usage_v1(id);
alter table erp.pocket_period_sources add column id uuid not null default gen_random_uuid() primary key;
alter table erp.pocket_period_sources add constraint be_pocket_source_exactly_one check(num_nonnulls(adjustment_id,historical_usage_id)=1);
create unique index be_pocket_source_native on erp.pocket_period_sources(pool_id,adjustment_id);
create unique index be_pocket_source_history on erp.pocket_period_sources(pool_id,historical_usage_id);
alter table erp.pocket_period_destinations drop constraint pocket_period_destinations_pkey;
alter table erp.pocket_period_destinations alter column event_id drop not null;
alter table erp.pocket_period_destinations alter column po_id drop not null;
alter table erp.pocket_period_destinations add column historical_sewing_id uuid references erp.be_pocket_sewing_v1(id);
alter table erp.pocket_period_destinations add column id uuid not null default gen_random_uuid() primary key;
alter table erp.pocket_period_destinations add constraint be_pocket_destination_exactly_one check(num_nonnulls(event_id,historical_sewing_id)=1 and (event_id is null or po_id is not null));
create unique index be_pocket_destination_native on erp.pocket_period_destinations(pool_id,event_id);
create unique index be_pocket_destination_history on erp.pocket_period_destinations(pool_id,historical_sewing_id);

CREATE OR REPLACE FUNCTION erp.be_pocket_immutable_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$ begin raise exception 'BE_POCKET_HISTORY_IMMUTABLE: gunakan koreksi atau pembatalan tertaut';end;$function$;
create trigger be_pocket_usage_immutable before update or delete on erp.be_pocket_usage_v1 for each row execute function erp.be_pocket_immutable_v1();
create trigger be_pocket_sewing_immutable before update or delete on erp.be_pocket_sewing_v1 for each row execute function erp.be_pocket_immutable_v1();
create trigger be_pocket_source_event_immutable before update or delete on erp.be_pocket_source_events_v1 for each row execute function erp.be_pocket_immutable_v1();
create trigger be_pocket_target_event_immutable before update or delete on erp.be_pocket_target_events_v1 for each row execute function erp.be_pocket_immutable_v1();

CREATE OR REPLACE FUNCTION erp.be_pocket_usage_amount_v1(p_usage uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select u.original_amount+coalesce((select sum(e.new_amount-e.previous_amount) from erp.be_pocket_source_events_v1 e where e.usage_id=u.id),0)
 from erp.be_pocket_usage_v1 u where u.id=p_usage
$function$;
CREATE OR REPLACE FUNCTION erp.be_pocket_opening_extra_v1(p_item uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select coalesce(sum(new_amount-previous_amount),0) from erp.be_pocket_target_events_v1 where opening_item_id=p_item $function$;

CREATE OR REPLACE FUNCTION erp.be_check_pocket_import_v1(p_batch uuid,p_row uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare r erp.migration_staging_rows%rowtype;j jsonb;k text;c date;d date;t record;v_qty numeric;v_amount numeric;v_kind text;
begin
 perform erp.require_owner_admin();perform erp.pocket_period_lock_v1();
 select * into strict r from erp.migration_staging_rows where id=p_row and batch_id=p_batch;
 j:=r.normalized_payload;select null::uuid id,null::jsonb p into t;
 foreach k in array array['document_number','line_number','physical_date','qty'] loop
  if nullif(btrim(j->>k),'') is null or length(j->>k)>120 then raise exception 'BE_POCKET_PROVENANCE: % wajib dan maksimal 120 karakter',k;end if;
 end loop;
 if j->>'physical_date' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'BE_POCKET_DATE';end if;
 d:=(j->>'physical_date')::date;select erp._cp3_business_date(cutover_at) into c from erp.migration_batches where id=p_batch;
 if d>=c or d::text<>j->>'physical_date' then raise exception 'BE_POCKET_DATE: riwayat harus sebelum tanggal cutover';end if;
 if j->>'qty' !~ '^[0-9]+([.][0-9]{1,6})?$' or (j->>'qty')::numeric<=0 then raise exception 'BE_POCKET_QTY';end if;
 v_qty:=(j->>'qty')::numeric(18,6);
 if exists(select 1 from erp.migration_staging_rows x where x.entity_type=r.entity_type and x.id<>r.id
   and lower(btrim(x.normalized_payload->>'document_number'))=lower(btrim(j->>'document_number'))
   and lower(btrim(x.normalized_payload->>'line_number'))=lower(btrim(j->>'line_number'))
   and (x.batch_id=p_batch or x.posted_entity_id is not null)) then raise exception 'BE_POCKET_DUPLICATE_SOURCE: dokumen dan baris telah dipakai';end if;
 if exists(select 1 from erp.pocket_periods p where erp.pocket_period_active_v1(p.id) and d between p.period_start and p.period_end) then
  raise exception 'BE_POCKET_PERIOD_ACTIVE: batalkan alokasi periode sebelum menambah sumber historis';end if;
 if r.entity_type='OPENING_POCKET_USAGE' then
  v_amount:=erp.bb_parse_amount_v1(j->>'amount','amount',false);v_kind:=upper(j->>'allocation_status');
  if v_kind is null or v_kind not in('ALLOCATED','UNALLOCATED') then raise exception 'BE_POCKET_ALLOCATION_STATUS';end if;
  if (v_kind='ALLOCATED')<>(nullif(btrim(j->>'prior_allocation_reference'),'') is not null) then raise exception 'BE_POCKET_PRIOR_ALLOCATION: referensi wajib hanya untuk nilai yang telah dialokasikan';end if;
  if not exists(select 1 from erp.materials where material_sku=j->>'material_sku' and is_active)
   and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='MATERIAL' and validation_status='VALID' and normalized_payload->>'material_sku'=j->>'material_sku') then raise exception 'BE_POCKET_MATERIAL';end if;
  -- An independent source-sheet total is a control, never a second journal.
  if nullif(btrim(j->>'control_key'),'') is null then raise exception 'BE_POCKET_CONTROL_REQUIRED';end if;
  if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type=r.entity_type and x.normalized_payload->>'control_key'=j->>'control_key'
    and (x.normalized_payload->>'control_amount' is distinct from j->>'control_amount' or x.normalized_payload->>'control_qty' is distinct from j->>'control_qty')) then raise exception 'BE_POCKET_CONTROL_INCONSISTENT';end if;
  if (select sum((normalized_payload->>'amount')::numeric) from erp.migration_staging_rows where batch_id=p_batch and entity_type=r.entity_type and normalized_payload->>'control_key'=j->>'control_key')
      is distinct from erp.bb_parse_amount_v1(j->>'control_amount','control_amount',false)
   or (select sum((normalized_payload->>'qty')::numeric) from erp.migration_staging_rows where batch_id=p_batch and entity_type=r.entity_type and normalized_payload->>'control_key'=j->>'control_key')
      is distinct from (j->>'control_qty')::numeric then raise exception 'BE_POCKET_CONTROL_MISMATCH';end if;
  perform erp.be_pocket_check_receipt_origin_v1(p_batch,j);
  return jsonb_build_object('qty',v_qty,'amount',v_amount,'physical_date',d,'kind',v_kind);
 elsif r.entity_type='OPENING_POCKET_SEWING' then
  if v_qty<>trunc(v_qty) or v_qty>2147483647 then raise exception 'BE_POCKET_SEWING_PCS';end if;
  if nullif(btrim(j->>'control_key'),'') is null or coalesce(j->>'control_qty','') !~ '^[1-9][0-9]*$' then raise exception 'BE_POCKET_DENOMINATOR_CONTROL_REQUIRED';end if;
  if exists(select 1 from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type=r.entity_type and x.normalized_payload->>'control_key'=j->>'control_key'
     and x.normalized_payload->>'control_qty' is distinct from j->>'control_qty')
   or (select sum((x.normalized_payload->>'qty')::numeric) from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type=r.entity_type and x.normalized_payload->>'control_key'=j->>'control_key')
     is distinct from (j->>'control_qty')::numeric then raise exception 'BE_POCKET_DENOMINATOR_INCOMPLETE';end if;
  v_kind:=upper(j->>'target_kind');
  if v_kind is null or v_kind not in('WIP','BS','FINISHED_GOODS','COGS') then raise exception 'BE_POCKET_TARGET';end if;
  if not exists(select 1 from erp.contractors where contractor_code=j->>'contractor_code')
   and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='CONTRACTOR' and validation_status='VALID' and normalized_payload->>'contractor_code'=j->>'contractor_code') then raise exception 'BE_POCKET_CONTRACTOR';end if;
  if v_kind='COGS' then
   if nullif(btrim(j->>'sold_reference'),'') is null or nullif(btrim(j->>'target_source_key'),'') is not null then raise exception 'BE_POCKET_SOLD_PROVENANCE';end if;
   if not exists(select 1 from erp.products where sku=j->>'product_sku')
    and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch and entity_type='PRODUCT' and validation_status='VALID' and normalized_payload->>'sku'=j->>'product_sku') then raise exception 'BE_POCKET_PRODUCT';end if;
  else
   if nullif(btrim(j->>'sold_reference'),'') is not null then raise exception 'BE_POCKET_TARGET_AMBIGUOUS';end if;
   select s.id,s.normalized_payload p into t from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
     and s.validation_status='VALID' and s.normalized_payload->>'opening_source_key'=j->>'target_source_key';
   if t.id is null or upper(t.p->>'balance_type')<>v_kind or (v_kind in('WIP','BS') and nullif(t.p->>'po_number','') is null) then raise exception 'BE_POCKET_TARGET_SOURCE_REQUIRED';end if;
   if (select sum((x.normalized_payload->>'qty')::numeric) from erp.migration_staging_rows x where x.batch_id=p_batch and x.entity_type=r.entity_type and x.normalized_payload->>'target_source_key'=j->>'target_source_key')>(t.p->>'qty')::numeric then raise exception 'BE_POCKET_SEWING_EXCEEDS_OPENING';end if;
  end if;
  return jsonb_build_object('qty',v_qty,'physical_date',d,'kind',v_kind,'target_row',case when v_kind<>'COGS' then t.id end);
 end if;
 raise exception 'BE_POCKET_IMPORT_ENTITY';
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_validate_pocket_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;
begin
 for r in select id from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_POCKET_USAGE','OPENING_POCKET_SEWING') order by entity_type,source_row_no loop
  begin
   perform erp.be_check_pocket_import_v1(p_batch,r.id);
   update erp.migration_staging_rows set validation_status='VALID',validation_errors='[]' where id=r.id;
  exception when others then update erp.migration_staging_rows set validation_status='ERROR',validation_errors=jsonb_build_array(sqlerrm) where id=r.id;end;
 end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_apply_pocket_imports_v1(p_batch uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;j jsonb;c jsonb;v_id uuid;v_date date;v_journal uuid;v_item uuid;v_po uuid;
begin
 perform erp.require_owner_admin();perform erp.pocket_period_lock_v1();
 select erp._cp3_business_date(cutover_at) into strict v_date from erp.migration_batches where id=p_batch;
 for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type in('OPENING_POCKET_USAGE','OPENING_POCKET_SEWING') and posted_entity_id is null order by entity_type,source_row_no loop
  if r.validation_status<>'VALID' then raise exception 'BE_POCKET_IMPORT_NOT_VALID';end if;
  j:=r.normalized_payload;c:=erp.be_check_pocket_import_v1(p_batch,r.id);v_id:=gen_random_uuid();v_journal:=null;
  if r.entity_type='OPENING_POCKET_USAGE' then
   if c->>'kind'='UNALLOCATED' then
    v_journal:=erp.post_journal('BE_OPENING_POCKET_EXPENSE',v_id,v_date,'Pengeluaran kain kantong sebelum cutover '||btrim(j->>'document_number'),jsonb_build_array(
     jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',(c->>'amount')::numeric,'credit',0),
     jsonb_build_object('mapping_key','OPENING_EQUITY','debit',0,'credit',(c->>'amount')::numeric)));
   end if;
   insert into erp.be_pocket_usage_v1(id,source_row_id,batch_id,document_number,line_number,physical_date,material_id,material_qty,original_amount,allocation_status,prior_allocation_reference,journal_id)
   values(v_id,r.id,p_batch,btrim(j->>'document_number'),btrim(j->>'line_number'),(c->>'physical_date')::date,
    (select id from erp.materials where material_sku=j->>'material_sku'),(c->>'qty')::numeric,(c->>'amount')::numeric,c->>'kind',nullif(btrim(j->>'prior_allocation_reference'),''),v_journal);
   perform erp.be_pocket_link_receipt_origin_v1(v_id,p_batch,j);
  else
   v_item:=null;v_po:=null;
   if c->>'target_row' is not null then
    select opening_item_id into strict v_item from erp.initial_import_opening_stock_sources where batch_id=p_batch and source_row_id=(c->>'target_row')::uuid;
    select po_id into v_po from erp.initial_import_production_sources where opening_item_id=v_item;
   end if;
   insert into erp.be_pocket_sewing_v1(id,source_row_id,batch_id,document_number,line_number,physical_date,contractor_id,qty,target_kind,opening_item_id,po_id,product_id,sold_reference)
   values(v_id,r.id,p_batch,btrim(j->>'document_number'),btrim(j->>'line_number'),(c->>'physical_date')::date,
    (select id from erp.contractors where contractor_code=j->>'contractor_code'),(c->>'qty')::numeric::bigint,c->>'kind',v_item,v_po,
    (select id from erp.products where sku=j->>'product_sku'),nullif(btrim(j->>'sold_reference'),''));
  end if;
  update erp.migration_staging_rows set posted_entity_id=v_id,posted_entity_type=r.entity_type,posted_at=statement_timestamp(),updated_at=statement_timestamp() where id=r.id;
 end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_pocket_import_workspace_v1(p_batch uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select jsonb_build_object('pocket_usage',coalesce((select jsonb_agg(jsonb_build_object('id',u.id,'document_number',u.document_number,'line_number',u.line_number,
  'date',u.physical_date,'material_sku',m.material_sku,'qty',u.material_qty::text,'original_amount',u.original_amount::text,'amount',erp.be_pocket_usage_amount_v1(u.id)::numeric(20,2)::text,
  'allocation_status',u.allocation_status,'prior_allocation_reference',u.prior_allocation_reference,
  'active_period',(select s.pool_id from erp.pocket_period_sources s where s.historical_usage_id=u.id and erp.pocket_period_active_v1(s.pool_id))) order by u.physical_date,u.document_number,u.line_number)
  from erp.be_pocket_usage_v1 u join erp.materials m on m.id=u.material_id where u.batch_id=p_batch),'[]'),
 'pocket_sewing',coalesce((select jsonb_agg(jsonb_build_object('id',s.id,'document_number',s.document_number,'line_number',s.line_number,'date',s.physical_date,
  'contractor_name',c.contractor_name,'qty',s.qty,'target_kind',s.target_kind,'opening_item_id',s.opening_item_id,'po_id',s.po_id,'sold_reference',s.sold_reference,
  'allocated_amount',coalesce((select sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)) from erp.pocket_period_destinations d where d.historical_sewing_id=s.id),0)::numeric(20,2)::text) order by s.physical_date,s.document_number,s.line_number)
  from erp.be_pocket_sewing_v1 s join erp.contractors c on c.id=s.contractor_id where s.batch_id=p_batch),'[]'))
$function$;

CREATE OR REPLACE FUNCTION erp.be_pocket_sync_targets_v1(p_pool uuid,p_date date,p_cancel boolean)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;v_before numeric;v_target numeric;v_delta numeric;
begin
 perform erp.require_internal();perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 for r in select d.*,s.opening_item_id,s.target_kind from erp.pocket_period_destinations d join erp.be_pocket_sewing_v1 s on s.id=d.historical_sewing_id
   where d.pool_id=p_pool and s.opening_item_id is not null order by s.opening_item_id,s.id loop
  select coalesce(sum(new_amount-previous_amount),0) into v_before from erp.be_pocket_target_events_v1 where pool_id=p_pool and sewing_id=r.historical_sewing_id;
  v_target:=case when p_cancel then 0 else erp.pocket_period_amount_v1(p_pool,r.preceding_qty,r.sewing_qty) end;v_delta:=v_target-v_before;
  if v_delta=0 then continue;end if;
  insert into erp.be_pocket_target_events_v1(pool_id,sewing_id,opening_item_id,previous_amount,new_amount,economic_date,created_by)
   values(p_pool,r.historical_sewing_id,r.opening_item_id,v_before,v_target,p_date,erp.current_app_user_id());
  if r.target_kind='FINISHED_GOODS' then perform erp.refresh_initial_import_fg_cost_v1(r.opening_item_id,v_delta,p_date);
  else
   perform erp.sync_initial_import_bs_value_v1(r.opening_item_id,p_date);
   perform erp.bb_sync_item_split_values_v1(r.opening_item_id,p_date);
  end if;
 end loop;
end;$function$;

-- Historical documents select a period; their opening value first exists at cutover.
-- This never changes the closed-period lock for a period containing native transactions.
CREATE OR REPLACE FUNCTION erp.be_pocket_period_post_date_v1(p_manifest jsonb,p_end date)
 RETURNS date LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select greatest(p_end,(select max(erp._cp3_business_date(b.cutover_at)) from erp.migration_batches b where b.id in(
  select u.batch_id from erp.be_pocket_usage_v1 u join jsonb_array_elements(p_manifest->'sources') x on u.id=(x->>'historical_usage_id')::uuid
  union select s.batch_id from erp.be_pocket_sewing_v1 s join jsonb_array_elements(p_manifest->'destinations') x on s.id=(x->>'historical_sewing_id')::uuid)))
$function$;

CREATE OR REPLACE FUNCTION erp.be_correct_pocket_usage_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET DateStyle TO 'ISO, YMD'
AS $function$
declare u erp.be_pocket_usage_v1%rowtype;v_amount numeric;v_old numeric;v_date date;v_reason text;v_journal uuid;v_pool uuid;v_cached jsonb;r jsonb;
begin
 perform erp.require_owner_admin();perform erp.require_permission('warehouse.stock.adjust');perform erp.require_permission('finance.hpp.manage');
 perform erp._cp3_assert_closed_json_object(p_payload,array['usage_id','amount','economic_date','expected_amount','reason'],array['usage_id','amount','economic_date','expected_amount','reason'],'koreksi kain kantong');
 v_cached:=erp._idempotency_begin('be_correct_pocket_usage_v1',p_request,erp._request_hash(p_payload));if v_cached is not null then return v_cached;end if;
 perform erp.pocket_period_lock_v1();select * into u from erp.be_pocket_usage_v1 where id=(p_payload->>'usage_id')::uuid for update;
 if u.id is null or u.allocation_status<>'UNALLOCATED' then raise exception 'BE_POCKET_CORRECTION_SOURCE: pilih sumber pool yang belum dialokasikan sebelum cutover';end if;
 if exists(select 1 from erp.be_pocket_receipt_origins_v1 where usage_id=u.id) then raise exception 'BE_POCKET_USE_SUPPLIER_INVOICE: koreksi nilai harus melalui nota supplier sumber';end if;
 v_old:=erp.be_pocket_usage_amount_v1(u.id);v_amount:=erp.bb_parse_amount_v1(p_payload->>'amount','amount',true);
 if v_old is distinct from (p_payload->>'expected_amount')::numeric then raise exception 'STALE_VERSION: nilai sumber kain kantong berubah';end if;
 v_date:=(p_payload->>'economic_date')::date;v_reason:=nullif(btrim(p_payload->>'reason'),'');
 if v_date is null or v_date<(select erp._cp3_business_date(cutover_at) from erp.migration_batches where id=u.batch_id)
  or v_date>erp._cp3_business_date(statement_timestamp()) or v_reason is null then raise exception 'BE_POCKET_CORRECTION_DATE_REASON';end if;
 if v_amount=v_old then raise exception 'BE_POCKET_NO_CHANGE';end if;
 v_journal:=erp.post_journal('BE_POCKET_SOURCE_CORRECTION',p_request,v_date,v_reason,jsonb_build_array(
  jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',greatest(v_amount-v_old,0),'credit',greatest(v_old-v_amount,0)),
  jsonb_build_object('mapping_key','OPENING_EQUITY','debit',greatest(v_old-v_amount,0),'credit',greatest(v_amount-v_old,0))));
 insert into erp.be_pocket_source_events_v1(id,usage_id,previous_amount,new_amount,economic_date,reason,journal_id,created_by)
 values(p_request,u.id,v_old,v_amount,v_date,v_reason,v_journal,erp.current_app_user_id());
 for v_pool in select pool_id from erp.pocket_period_sources where historical_usage_id=u.id and erp.pocket_period_active_v1(pool_id) order by pool_id loop
  perform erp.sync_pocket_period_v1(v_pool,v_date,'RECOST',v_reason);
 end loop;
 r:=jsonb_build_object('action','CORRECT_OPENING_USAGE','request_id',p_request,'id',u.id,'status','CORRECTED','usage_id',u.id,'amount',v_amount::numeric(20,2)::text);
 return erp._idempotency_complete('be_correct_pocket_usage_v1',p_request,r);
end;$function$;

-- Historical consumed receipt quantities are explicit origins, never stock movements.
create table erp.be_pocket_receipt_origins_v1(
 usage_id uuid primary key references erp.be_pocket_usage_v1(id),purchase_item_id uuid not null references erp.material_purchase_items(id),
 material_qty numeric(18,6) not null check(material_qty>0),unit_cost_snapshot numeric(18,6) not null check(unit_cost_snapshot>=0)
);
create trigger be_pocket_receipt_immutable before update or delete on erp.be_pocket_receipt_origins_v1 for each row execute function erp.be_pocket_immutable_v1();
CREATE OR REPLACE FUNCTION erp.be_pocket_receipt_staged_qty_v1(p_batch uuid,p_receipt jsonb)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 select coalesce(sum((x.normalized_payload->>'qty')::numeric),0) from erp.migration_staging_rows x
 where x.batch_id=p_batch and x.entity_type='OPENING_POCKET_USAGE' and x.validation_status='VALID'
  and x.normalized_payload->>'supplier_code'=p_receipt->>'supplier_code'
  and lower(btrim(x.normalized_payload->>'receipt_number'))=lower(btrim(p_receipt->>'receipt_number'))
  and lower(btrim(x.normalized_payload->>'receipt_line_number'))=lower(btrim(p_receipt->>'receipt_line_number'))
$function$;
CREATE OR REPLACE FUNCTION erp.be_pocket_check_receipt_origin_v1(p_batch uuid,p_usage jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare n integer;r erp.migration_staging_rows%rowtype;v_part jsonb;v_cost numeric;
begin
 n:=num_nonnulls(nullif(btrim(p_usage->>'supplier_code'),''),nullif(btrim(p_usage->>'receipt_number'),''),nullif(btrim(p_usage->>'receipt_line_number'),''));
 if n=0 then return;end if;
 if n<>3 or upper(p_usage->>'allocation_status')<>'UNALLOCATED' then raise exception 'BE_POCKET_RECEIPT_IDENTITY: sumber penerimaan wajib lengkap, hanya pool yang belum dialokasikan';end if;
 if (select count(*) from erp.migration_staging_rows where batch_id=p_batch and entity_type='UNINVOICED_RECEIPT'
  and normalized_payload->>'supplier_code'=p_usage->>'supplier_code'
  and lower(btrim(normalized_payload->>'receipt_number'))=lower(btrim(p_usage->>'receipt_number'))
  and lower(btrim(normalized_payload->>'receipt_line_number'))=lower(btrim(p_usage->>'receipt_line_number')))<>1 then raise exception 'BE_POCKET_RECEIPT_REQUIRED';end if;
 select * into r from erp.migration_staging_rows where batch_id=p_batch and entity_type='UNINVOICED_RECEIPT'
  and normalized_payload->>'supplier_code'=p_usage->>'supplier_code'
  and lower(btrim(normalized_payload->>'receipt_number'))=lower(btrim(p_usage->>'receipt_number'))
  and lower(btrim(normalized_payload->>'receipt_line_number'))=lower(btrim(p_usage->>'receipt_line_number'));
 if r.normalized_payload->>'material_sku' is distinct from p_usage->>'material_sku' then raise exception 'BE_POCKET_RECEIPT_MATERIAL';end if;
 v_part:=erp.bb_receipt_row_invoiced_part_v1(p_batch,r.id);v_cost:=(r.normalized_payload->>'unit_cost')::numeric;
 if v_part is not null then v_cost:=round(((r.normalized_payload->>'qty')::numeric*v_cost+(v_part->>'invoiced_amount')::numeric)/((r.normalized_payload->>'qty')::numeric+(v_part->>'invoiced_qty')::numeric),6);end if;
 if round((p_usage->>'qty')::numeric*v_cost,2) is distinct from (p_usage->>'amount')::numeric then raise exception 'BE_POCKET_RECEIPT_VALUE: nilai sumber harus sama dengan qty bahan dikali biaya penerimaan';end if;
end;$function$;
CREATE OR REPLACE FUNCTION erp.be_pocket_link_receipt_origin_v1(p_usage uuid,p_batch uuid,p_payload jsonb)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_item uuid;
begin
 if nullif(btrim(p_payload->>'receipt_number'),'') is null then return;end if;
 select l.purchase_item_id into strict v_item from erp.initial_import_receipt_lines l join erp.initial_import_receipt_headers h on h.purchase_id=l.purchase_id
  join erp.suppliers s on s.id=h.supplier_id where h.batch_id=p_batch and s.supplier_code=p_payload->>'supplier_code'
  and lower(btrim(h.receipt_number))=lower(btrim(p_payload->>'receipt_number')) and lower(btrim(l.receipt_line_number))=lower(btrim(p_payload->>'receipt_line_number'));
 insert into erp.be_pocket_receipt_origins_v1(usage_id,purchase_item_id,material_qty,unit_cost_snapshot)
 values(p_usage,v_item,(p_payload->>'qty')::numeric,erp.bb_receipt_opening_unit_cost_v1(v_item));
end;$function$;
CREATE OR REPLACE FUNCTION erp.be_pocket_recost_receipt_v1(p_item uuid)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare r record;v_old numeric;v_new numeric;v_delta numeric;v_event uuid;v_journal uuid;v_date date;v_pool uuid;
begin
 perform erp.require_internal();perform erp.pocket_period_lock_v1();
 v_date:=coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(statement_timestamp()));
 for r in select * from erp.be_pocket_receipt_origins_v1 where purchase_item_id=p_item order by usage_id loop
  v_old:=erp.be_pocket_usage_amount_v1(r.usage_id);v_new:=round(r.material_qty*erp.material_purchase_current_unit_cost(p_item),2);v_delta:=v_new-v_old;
  if v_delta=0 then continue;end if;v_event:=gen_random_uuid();
  v_journal:=erp.post_journal('BE_POCKET_RECEIPT_RECOST',v_event,v_date,'Koreksi nota sumber kain kantong sebelum cutover',jsonb_build_array(
   jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',greatest(v_delta,0),'credit',greatest(-v_delta,0)),
   jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',greatest(-v_delta,0),'credit',greatest(v_delta,0))));
  insert into erp.be_pocket_source_events_v1(id,usage_id,previous_amount,new_amount,economic_date,reason,journal_id,created_by)
   values(v_event,r.usage_id,v_old,v_new,v_date,'Koreksi nota sumber kain kantong sebelum cutover',v_journal,erp.current_app_user_id());
  for v_pool in select pool_id from erp.pocket_period_sources where historical_usage_id=r.usage_id and erp.pocket_period_active_v1(pool_id) order by pool_id loop
   perform erp.sync_pocket_period_v1(v_pool,v_date,'RECOST','Koreksi nota sumber kain kantong sebelum cutover');
  end loop;
 end loop;
end;$function$;

CREATE OR REPLACE FUNCTION erp.be_pocket_workspace_v1(p_query text)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
 with sources as(select u.id,u.document_number,u.line_number,u.physical_date date,m.material_sku,m.material_name,u.material_qty::text qty,
  u.original_amount::text original_amount,erp.be_pocket_usage_amount_v1(u.id)::numeric(20,2)::text amount,u.allocation_status,u.prior_allocation_reference,
  exists(select 1 from erp.be_pocket_receipt_origins_v1 o where o.usage_id=u.id) receipt_backed,
  (select s.pool_id from erp.pocket_period_sources s where s.historical_usage_id=u.id and erp.pocket_period_active_v1(s.pool_id)) active_period
  from erp.be_pocket_usage_v1 u join erp.materials m on m.id=u.material_id
  where coalesce(btrim(p_query),'')='' or strpos(lower(concat_ws(' ',u.document_number,u.line_number,m.material_sku,m.material_name)),lower(btrim(p_query)))>0),
 targets as(select s.id,s.document_number,s.line_number,s.physical_date date,c.contractor_name,s.qty,s.target_kind,s.sold_reference,
  coalesce(k.source_key,p.sku) target_reference,
  coalesce((select sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)) from erp.pocket_period_destinations d where d.historical_sewing_id=s.id),0)::numeric(20,2)::text allocated_amount
  from erp.be_pocket_sewing_v1 s join erp.contractors c on c.id=s.contractor_id
  left join erp.initial_import_opening_stock_sources k on k.opening_item_id=s.opening_item_id left join erp.products p on p.id=s.product_id
  where coalesce(btrim(p_query),'')='' or strpos(lower(concat_ws(' ',s.document_number,s.line_number,c.contractor_name,k.source_key,p.sku)),lower(btrim(p_query)))>0)
 select jsonb_build_object('opening_usage',coalesce((select jsonb_agg(to_jsonb(x) order by x.date desc,x.id) from(select * from sources order by date desc,id limit 100) x),'[]'),
  'opening_usage_count',(select count(*) from sources),'opening_sewing',coalesce((select jsonb_agg(to_jsonb(x) order by x.date desc,x.id) from(select * from targets order by date desc,id limit 100) x),'[]'),
  'opening_sewing_count',(select count(*) from targets))
$function$;
