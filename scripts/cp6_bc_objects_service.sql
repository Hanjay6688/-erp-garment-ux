-- ================================================================ BC documents, service post, internal use, returns, inspection
-- M:4751-4908 (flows by ownership and purpose, operator flows, buckets), M:5018-5060 (reuse native transfer/adjustment,
-- command contract), M:5066-5095 (cost treatment, recovery value pending). Every command is one BC document that links the
-- native documents it posted; nothing is written to the ledger except through the native writers.

create table erp.bc_documents_v1(
  id uuid primary key,
  document_number text not null unique,
  action text not null check(action in('FILL_POST','RETURN_TO_WAREHOUSE','INTERNAL_USE','RECEIVE_RETURN','INSPECT','VALUE_CUSTODY',
    'CREDIT_NOTE_RETURN','ALLOCATE_CARRY','DISPOSE_STOCK','CLOSE_CUSTODY','CUSTOMER_GARMENT_IN','CUSTOMER_GARMENT_OUT','COUNT_POST',
    'RESOLVE_VARIANCE','ROUND_NOTE')),
  status text not null default 'POSTED' check(status in('POSTED','REVERSED')),
  physical_at timestamptz not null,
  responsible text check(responsible is null or length(responsible) between 1 and 120),
  reference text check(reference is null or length(reference) between 1 and 200),
  reason text not null check(length(btrim(reason)) between 1 and 1000),
  payload jsonb not null,
  policy_versions jsonb not null default '{}'::jsonb,
  row_version bigint not null default 1 check(row_version>0),
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  reversed_by uuid,
  reversed_at timestamptz,
  reversal_reason text,
  check((status='REVERSED')=(reversed_at is not null and reversal_reason is not null))
);
comment on table erp.bc_documents_v1 is 'BC: one command of the Pemakaian & Pengembalian Aksesori workspace (id = its client request id). The native transfers, adjustments, movements, journals and settlements it posted are in bc_document_links_v1; the reversal is linked, never an edit.';
create table erp.bc_document_links_v1(
  document_id uuid not null references erp.bc_documents_v1(id),
  link_kind text not null check(link_kind in('TRANSFER','ADJUSTMENT','MOVEMENT','JOURNAL','SETTLEMENT','PAYROLL_LINE')),
  link_id uuid not null,
  primary key(document_id,link_kind,link_id)
);
create index bc_document_links_v1_link on erp.bc_document_links_v1(link_kind,link_id);

-- Purpose of a native adjustment posted by BC: its expense (outbound) or income (inbound valuation) account.
create table erp.bc_adjustment_purposes_v1(
  adjustment_id uuid primary key references erp.material_adjustments(id),
  document_id uuid not null references erp.bc_documents_v1(id),
  purpose text not null check(purpose in('FACTORY_USE','CUSTOMER_SERVICE','OWN_FG_REPAIR','RECOVERY_VALUATION','DAMAGE_DISPOSAL','COUNT_LOSS')),
  account_id uuid not null references erp.chart_accounts(id),
  policy_key text,
  policy_version bigint
);
comment on table erp.bc_adjustment_purposes_v1 is 'BC: purpose and account of a native material adjustment posted by the BC facade (internal use by purpose, recovery valuation, disposal). erp.post_material_adjustment and the adjustment revaluation read the account here instead of the fixed OTHER_EXPENSE/OTHER_INCOME; every other adjustment is unchanged.';

create table erp.bc_internal_use_lines_v1(
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references erp.bc_documents_v1(id),
  line_number integer not null check(line_number between 1 and 100),
  material_id uuid not null references erp.materials(id),
  location_id uuid not null references erp.locations(id),
  qty numeric(18,6) not null check(qty>0),
  physical_at timestamptz not null,
  purpose text not null check(purpose in('FACTORY_USE','CUSTOMER_SERVICE','OWN_FG_REPAIR')),
  customer_custody_id uuid,
  adjustment_id uuid not null references erp.material_adjustments(id),
  unique(document_id,line_number)
);

-- Expected returns that are not stock: an item still with a holder, the old accessory of a conversion (BE), an opening
-- UNRETURNED count (ALL-C03). A receipt may name one; received quantity never exceeds the expected quantity.
create table erp.bc_outstanding_returns_v1(
  id uuid primary key default gen_random_uuid(),
  source_kind text not null check(source_kind in('OPENING_UNRETURNED','HOLDER','CONVERSION')),
  owner_kind text not null check(owner_kind in('COMPANY','CUSTOMER')),
  material_id uuid references erp.materials(id),
  description text,
  qty_expected numeric(18,6) not null check(qty_expected>0),
  holder text not null check(length(btrim(holder)) between 1 and 120),
  reference text,
  batch_id uuid references erp.migration_batches(id),
  source_row_id uuid,
  document_id uuid references erp.bc_documents_v1(id),
  status text not null default 'OPEN' check(status in('OPEN','CANCELLED')),
  created_at timestamptz not null default statement_timestamp(),
  check(material_id is not null or description is not null)
);

-- Customer-owned garments in service (ACC-C10): custody only, never company FG, AR, refund or entitlement.
create table erp.bc_customer_custody_v1(
  id uuid primary key,
  in_document_id uuid unique references erp.bc_documents_v1(id),
  customer_id uuid not null references erp.customers(id),
  product_id uuid references erp.products(id),
  description text not null check(length(btrim(description)) between 1 and 200),
  qty numeric(18,6) not null check(qty>0 and qty=trunc(qty)),
  received_at timestamptz not null,
  batch_id uuid references erp.migration_batches(id),
  out_document_id uuid unique references erp.bc_documents_v1(id),
  check((in_document_id is null)=(batch_id is not null))
);

-- One physical return lot (one material of one receipt). Ledger lots are company stock already valued in the ledger
-- (service-post leftover at the inspection area); custody lots are not in the ledger: owned by the mandor until a credit
-- (note return), by the company with value pending (teardown, legacy, opening count), or by a customer.
create table erp.bc_return_lots_v1(
  id uuid primary key default gen_random_uuid(),
  document_id uuid references erp.bc_documents_v1(id),
  line_number integer not null default 1,
  source_kind text not null check(source_kind in('SERVICE_LEFTOVER','NOTE_RETURN','OPENING_NOTE_RETURN','TEARDOWN','LEGACY',
    'OPENING_PENDING_VALUE','OPENING_QUARANTINE','NOTE_RETURN_CREDITED')),
  owner_kind text not null check(owner_kind in('COMPANY','MANDOR')),
  value_mode text not null check(value_mode in('LEDGER','PENDING','MANDOR_OWNED')),
  material_id uuid not null references erp.materials(id),
  location_id uuid not null references erp.locations(id),
  qty_received numeric(18,6) not null check(qty_received>0),
  init_usable numeric(18,6) not null default 0 check(init_usable>=0),
  init_damaged numeric(18,6) not null default 0 check(init_damaged>=0),
  received_at timestamptz not null,
  contractor_id uuid references erp.contractors(id),
  note_item_id uuid references erp.contractor_material_issue_items(id),
  opening_note_line_id uuid,
  outstanding_id uuid references erp.bc_outstanding_returns_v1(id),
  parent_lot_id uuid references erp.bc_return_lots_v1(id),
  parent_event_id uuid,
  batch_id uuid references erp.migration_batches(id),
  source_row_id uuid,
  reference text,
  created_at timestamptz not null default statement_timestamp(),
  check(init_usable+init_damaged<=qty_received),
  check((source_kind='NOTE_RETURN')=(note_item_id is not null)),
  check((source_kind='OPENING_NOTE_RETURN')=(opening_note_line_id is not null)),
  check((owner_kind='MANDOR')=(value_mode='MANDOR_OWNED')),
  check((value_mode='LEDGER')=(source_kind in('SERVICE_LEFTOVER','OPENING_QUARANTINE'))),
  check((source_kind='NOTE_RETURN_CREDITED')=(parent_lot_id is not null and parent_event_id is not null)),
  check((document_id is null)=(batch_id is not null)),
  check((source_kind in('OPENING_PENDING_VALUE','OPENING_QUARANTINE'))=(batch_id is not null))
);
create index bc_return_lots_v1_note on erp.bc_return_lots_v1(note_item_id) where note_item_id is not null;
create index bc_return_lots_v1_opening_note on erp.bc_return_lots_v1(opening_note_line_id) where opening_note_line_id is not null;
create index bc_return_lots_v1_outstanding on erp.bc_return_lots_v1(outstanding_id) where outstanding_id is not null;

-- Events on a lot: inspection split, credit of a note return, valuation, disposition, closing. Each belongs to one BC
-- document; a reversed document's events no longer count.
create table erp.bc_lot_events_v1(
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references erp.bc_documents_v1(id),
  lot_id uuid not null references erp.bc_return_lots_v1(id),
  event_kind text not null check(event_kind in('INSPECT','CREDIT','VALUE','RETURN_TO_OWNER','DISCARD')),
  condition text check(condition in('WAITING','USABLE','DAMAGED')),
  qty_usable numeric(18,6) not null default 0 check(qty_usable>=0),
  qty_damaged numeric(18,6) not null default 0 check(qty_damaged>=0),
  qty numeric(18,6) not null default 0 check(qty>=0),
  inspector text,
  event_at timestamptz not null,
  target_location_id uuid references erp.locations(id),
  unit_value numeric(18,2),
  amount numeric(18,2),
  amount_unpaid numeric(18,2),
  amount_carry numeric(18,2),
  amount_refund numeric(18,2),
  cash_account_id uuid references erp.cash_accounts(id),
  created_at timestamptz not null default statement_timestamp(),
  check((event_kind='INSPECT')=(condition is null)),
  check(event_kind<>'INSPECT' or (qty=0 and qty_usable+qty_damaged>0 and inspector is not null)),
  check(event_kind='INSPECT' or (qty>0 and qty_usable=0 and qty_damaged=0)),
  check(event_kind in('INSPECT','RETURN_TO_OWNER') or condition<>'WAITING'),
  check((event_kind='CREDIT')=(amount is not null and amount_unpaid is not null and amount_carry is not null and amount_refund is not null)),
  check(event_kind<>'CREDIT' or amount=amount_unpaid+amount_carry+amount_refund),
  check((amount_refund>0)=(cash_account_id is not null) or event_kind<>'CREDIT')
);
create index bc_lot_events_v1_lot on erp.bc_lot_events_v1(lot_id);

-- A stock count of a service post: a difference is an unknown variance for review, never asserted as usage (ACC-B06).
create table erp.bc_count_variances_v1(
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references erp.bc_documents_v1(id),
  material_id uuid not null references erp.materials(id),
  location_id uuid not null references erp.locations(id),
  book_qty numeric(18,6) not null,
  counted_qty numeric(18,6) not null check(counted_qty>=0),
  variance numeric(18,6) not null,
  counted_at timestamptz not null,
  resolution_document_id uuid references erp.bc_documents_v1(id),
  check(variance=counted_qty-book_qty)
);

do $rls$
declare t text;
begin
  foreach t in array array['bc_documents_v1','bc_document_links_v1','bc_adjustment_purposes_v1','bc_internal_use_lines_v1',
    'bc_outstanding_returns_v1','bc_customer_custody_v1','bc_return_lots_v1','bc_lot_events_v1','bc_count_variances_v1'] loop
    execute format('alter table erp.%I enable row level security',t);
    execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
  end loop;
end $rls$;

-- ---------------------------------------------------------------- parsing and checks
CREATE OR REPLACE FUNCTION erp.bc_parse_at_v1(p_value text,p_field text)
 RETURNS timestamptz LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO '' SET "TimeZone" TO 'UTC'
AS $function$
declare v timestamptz;
begin
  if p_value is null or p_value!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+07:00$' then
    raise exception 'BC_DATE_INVALID: % memakai tanggal dan jam WIB (YYYY-MM-DDTHH:MM:SS+07:00)',p_field;end if;
  begin v:=p_value::timestamptz; exception when others then raise exception 'BC_DATE_INVALID: % bukan tanggal yang ada',p_field; end;
  if to_char(v at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')||'+07:00'<>p_value then
    raise exception 'BC_DATE_INVALID: % bukan tanggal yang ada',p_field;end if;
  if v>clock_timestamp()+interval '5 minutes' then raise exception 'BC_DATE_FUTURE: % tidak boleh di masa depan',p_field;end if;
  return v;
end;$function$;

-- Whole PCS for a COUNT unit, up to six decimals otherwise (ACC-A01/A04/A05); never coerced.
CREATE OR REPLACE FUNCTION erp.bc_parse_qty_v1(p_material uuid,p_value jsonb,p_field text)
 RETURNS numeric LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_count boolean;v numeric;
begin
  select u.dimension='COUNT' into v_count from erp.materials m join erp.uom_definitions u on u.unit_code=m.unit_code where m.id=p_material;
  if jsonb_typeof(p_value) is distinct from 'string' then raise exception 'BC_QTY_INVALID: % wajib angka teks',p_field;end if;
  if v_count then
    if p_value#>>'{}'!~'^[1-9][0-9]{0,11}$' then raise exception 'BC_QTY_INVALID: % harus PCS utuh positif',p_field;end if;
  elsif p_value#>>'{}'!~'^[0-9]{1,12}(\.[0-9]{1,6})?$' then raise exception 'BC_QTY_INVALID: % harus angka positif, maksimal enam desimal',p_field;
  end if;
  v:=(p_value#>>'{}')::numeric;
  if v<=0 then raise exception 'BC_QTY_INVALID: % harus lebih dari nol',p_field;end if;
  return v;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_accessory_v1(p_material uuid)
 RETURNS uuid LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if p_material is null or not exists(select 1 from erp.materials where id=p_material and is_active and material_type='ACCESSORY') then
    raise exception 'BC_MATERIAL_INVALID: pilih aksesori yang aktif';end if;
  return p_material;
end;$function$;

-- An active raw-material warehouse of the wanted kind: MAIN (not a zone) or one of the zone kinds (ACC-B05).
CREATE OR REPLACE FUNCTION erp.bc_location_v1(p_location uuid,p_kinds text[],p_field text)
 RETURNS uuid LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_kind text;
begin
  if p_location is null or not exists(select 1 from erp.locations where id=p_location and is_active and location_type='RAW_MATERIAL_WAREHOUSE') then
    raise exception 'BC_LOCATION_INVALID: % harus gudang bahan aktif',p_field;end if;
  v_kind:=coalesce(erp.bc_zone_kind_v1(p_location),'MAIN');
  if not v_kind=any(p_kinds) then
    raise exception 'BC_LOCATION_INVALID: % harus %',p_field,array_to_string(array(select case k when 'MAIN' then 'gudang utama' when 'SERVICE_POST' then 'pos servis'
      when 'INSPECTION' then 'area pemeriksaan' else 'area rusak' end from unnest(p_kinds) k),' atau ');end if;
  -- ACC-DEC07: when the owner lists the users of a zone, only they may move its stock.
  if v_kind<>'MAIN' and erp.bc_policy_v1('ACC_DEC07')->'zone_users' ? p_location::text
     and session_user not in('postgres','supabase_admin')
     and not (erp.bc_policy_v1('ACC_DEC07')->'zone_users'->p_location::text) ? coalesce(erp.current_app_user_id()::text,'') then
    raise exception 'BC_ZONE_USER_DENIED: pengguna ini tidak terdaftar untuk zona tersebut (ACC-DEC07)';end if;
  return p_location;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_stock_at_v1(p_material uuid,p_location uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=p_material and location_id=p_location and roll_id is null
$function$;

-- ACC-DEC07: a valued company cost (internal use, disposal, count loss) needs owner/admin approval until the owner sets a
-- threshold, then only above it.
CREATE OR REPLACE FUNCTION erp.bc_require_value_approval_v1(p_amount numeric)
 RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb:=erp.bc_policy_v1('ACC_DEC07');
begin
  if v is null or p_amount>(v->>'owner_approval_above')::numeric then
    begin
      perform erp.require_owner_admin();
    exception when others then
      raise exception 'BC_APPROVAL_REQUIRED: biaya % memerlukan persetujuan owner/admin (ACC-DEC07 %)',p_amount::numeric(20,2),
        case when v is null then 'belum ditetapkan' else 'di atas '||(v->>'owner_approval_above') end;
    end;
  end if;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_text_v1(p_payload jsonb,p_field text,p_required boolean,p_max integer)
 RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v text;
begin
  if p_payload ? p_field and jsonb_typeof(p_payload->p_field) not in('string','null') then raise exception 'BC_TEXT_INVALID: % wajib teks',p_field;end if;
  v:=nullif(btrim(p_payload->>p_field),'');
  if v is null and p_required then raise exception 'BC_TEXT_REQUIRED: % wajib diisi',p_field;end if;
  if length(v)>p_max then raise exception 'BC_TEXT_INVALID: % maksimal % karakter',p_field,p_max;end if;
  return v;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_uuid_v1(p_payload jsonb,p_field text,p_required boolean)
 RETURNS uuid LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if not (p_payload ? p_field) or jsonb_typeof(p_payload->p_field)='null' then
    if p_required then raise exception 'BC_ID_REQUIRED: % wajib diisi',p_field;end if;
    return null;
  end if;
  if jsonb_typeof(p_payload->p_field)<>'string' or (p_payload->>p_field)!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    raise exception 'BC_ID_INVALID: % bukan id yang sah',p_field;end if;
  return (p_payload->>p_field)::uuid;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_new_document_v1(p_request uuid,p_action text,p_at timestamptz,p_payload jsonb,p_policies jsonb default '{}'::jsonb)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  insert into erp.bc_documents_v1(id,document_number,action,physical_at,responsible,reference,reason,payload,policy_versions,created_by)
  values(p_request,'BCA-'||upper(substr(replace(p_request::text,'-',''),1,16)),p_action,p_at,erp.bc_text_v1(p_payload,'responsible',false,120),
    erp.bc_text_v1(p_payload,'reference',false,200),erp.bc_text_v1(p_payload,'reason',true,1000),p_payload,p_policies,erp.current_app_user_id());
  return p_request;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bc_link_v1(p_document uuid,p_kind text,p_id uuid)
 RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$ insert into erp.bc_document_links_v1(document_id,link_kind,link_id) values(p_document,p_kind,p_id) on conflict do nothing $function$;

-- Native transfer (value-preserving, M:5018 A) from one location to another for a set of accessory lines.
CREATE OR REPLACE FUNCTION erp.bc_post_transfer_v1(p_document uuid,p_from uuid,p_to uuid,p_at timestamptz,p_items jsonb,p_reason text)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb;v_id uuid;
begin
  v:=erp.save_material_transfer_draft_v2(jsonb_build_object('transfer_number','BCT-'||upper(substr(replace(gen_random_uuid()::text,'-',''),1,16)),
    'from_location_id',p_from,'to_location_id',p_to,'physical_at',p_at,'notes',p_reason,'change_reason',p_reason,'items',p_items),gen_random_uuid(),null);
  v_id:=(v->>'material_transfer_id')::uuid;
  perform erp.post_material_transfer_v2(v_id,gen_random_uuid(),(v->>'row_version')::bigint,p_reason);
  perform erp.bc_link_v1(p_document,'TRANSFER',v_id);
  return v_id;
end;$function$;

-- Native adjustment with the BC purpose account (read by erp.post_material_adjustment through bc_adjustment_account_v1).
CREATE OR REPLACE FUNCTION erp.bc_post_adjustment_v1(p_document uuid,p_location uuid,p_at timestamptz,p_reason_code text,p_items jsonb,
  p_reason text,p_purpose text,p_account uuid,p_policy_key text default null)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb;v_id uuid;
begin
  v:=erp.save_material_adjustment_draft_v2(jsonb_build_object('adjustment_number','BCJ-'||upper(substr(replace(gen_random_uuid()::text,'-',''),1,16)),
    'reason_code',p_reason_code,'physical_at',p_at,'location_id',p_location,'notes',p_reason,'change_reason',p_reason,'items',p_items),gen_random_uuid(),null);
  v_id:=(v->>'material_adjustment_id')::uuid;
  insert into erp.bc_adjustment_purposes_v1(adjustment_id,document_id,purpose,account_id,policy_key,policy_version)
  values(v_id,p_document,p_purpose,p_account,p_policy_key,case when p_policy_key is not null then erp.bc_policy_version_v1(p_policy_key) end);
  perform erp.post_material_adjustment_v2(v_id,gen_random_uuid(),(v->>'row_version')::bigint,p_reason);
  perform erp.bc_link_v1(p_document,'ADJUSTMENT',v_id);
  return v_id;
end;$function$;

-- The account erp.post_material_adjustment and the adjustment revaluation use for an adjustment (BC purpose, else the
-- unchanged OTHER_EXPENSE for an outbound and OTHER_INCOME for an inbound adjustment).
CREATE OR REPLACE FUNCTION erp.bc_adjustment_account_v1(p_adjustment uuid,p_mapping text)
 RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select coalesce((select account_id from erp.bc_adjustment_purposes_v1 where adjustment_id=p_adjustment
    and ((p_mapping='OTHER_EXPENSE' and purpose not in('RECOVERY_VALUATION')) or (p_mapping='OTHER_INCOME' and purpose='RECOVERY_VALUATION'))),
    (select account_id from erp.accounting_account_mappings where mapping_key=p_mapping))
$function$;

CREATE OR REPLACE FUNCTION erp.bc_adjustment_value_v1(p_adjustment uuid)
 RETURNS numeric LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select round(coalesce(sum(m.qty_signed*m.unit_cost_snapshot),0),2) from erp.material_stock_movements m join erp.material_adjustment_items i on i.id=m.source_id
  where m.source_type='MATERIAL_ADJUSTMENT_ITEM' and i.adjustment_id=p_adjustment and m.reversal_of_id is null
$function$;

-- Lines [{material_id, qty}] of distinct active accessories, 1..100.
CREATE OR REPLACE FUNCTION erp.bc_lines_v1(p_payload jsonb,p_extra text[] default array[]::text[])
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb:='[]'::jsonb;v_x jsonb;n integer:=0;v_material uuid;
begin
  if jsonb_typeof(p_payload->'items') is distinct from 'array' or jsonb_array_length(p_payload->'items') not between 1 and 100 then
    raise exception 'BC_LINES_INVALID: isi 1 sampai 100 baris aksesori';end if;
  for v_x in select value from jsonb_array_elements(p_payload->'items') loop
    n:=n+1;
    perform erp._cp3_assert_closed_json_object(v_x,array['material_id','qty'],array['material_id','qty']||p_extra,'accessory line');
    v_material:=erp.bc_accessory_v1(erp.bc_uuid_v1(v_x,'material_id',true));
    v:=v||jsonb_build_array(v_x||jsonb_build_object('line_number',n,'material_id',v_material,'qty',erp.bc_parse_qty_v1(v_material,v_x->'qty','qty baris '||n)::text));
  end loop;
  return v;
end;$function$;

-- ---------------------------------------------------------------- lot state
CREATE OR REPLACE FUNCTION erp.bc_lot_state_v1(p_lot uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  with l as(select * from erp.bc_return_lots_v1 where id=p_lot),
  e as(select e.* from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id where e.lot_id=p_lot and d.status='POSTED'),
  s as(select l.*,
    l.init_usable+coalesce((select sum(qty_usable) from e where event_kind='INSPECT'),0) inspected_usable,
    l.init_damaged+coalesce((select sum(qty_damaged) from e where event_kind='INSPECT'),0) inspected_damaged,
    coalesce((select sum(qty) from e where event_kind<>'INSPECT' and condition='USABLE'),0) out_usable,
    coalesce((select sum(qty) from e where event_kind<>'INSPECT' and condition='DAMAGED'),0) out_damaged,
    coalesce((select sum(qty) from e where event_kind<>'INSPECT' and condition='WAITING'),0) out_waiting,
    coalesce((select sum(qty) from e where event_kind='CREDIT'),0) credited
   from l)
  select jsonb_build_object('lot_id',id,'received',qty_received,
    'waiting',qty_received-inspected_usable-inspected_damaged-out_waiting,
    'usable',inspected_usable-out_usable,'damaged',inspected_damaged-out_damaged,
    'inspected_usable',inspected_usable,'inspected_damaged',inspected_damaged,'credited',credited,
    'open',qty_received-out_usable-out_damaged-out_waiting)
  from s
$function$;

-- Lock a lot (and its source) for a command; the state is read after the lock.
CREATE OR REPLACE FUNCTION erp.bc_lock_lot_v1(p_lot uuid)
 RETURNS erp.bc_return_lots_v1 LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.bc_return_lots_v1%rowtype;
begin
  select * into l from erp.bc_return_lots_v1 where id=p_lot;
  if l.id is null then raise exception 'BC_LOT_NOT_FOUND: penerimaan tidak ditemukan';end if;
  perform pg_advisory_xact_lock(hashtextextended('BCLOT|'||l.id::text,0));
  if l.document_id is not null and (select status from erp.bc_documents_v1 where id=l.document_id)<>'POSTED' then
    raise exception 'BC_LOT_REVERSED: penerimaan ini sudah dibatalkan';end if;
  if l.parent_event_id is not null and (select d.status from erp.bc_lot_events_v1 e join erp.bc_documents_v1 d on d.id=e.document_id where e.id=l.parent_event_id)<>'POSTED' then
    raise exception 'BC_LOT_REVERSED: kredit asal lot ini sudah dibatalkan';end if;
  select * into l from erp.bc_return_lots_v1 where id=p_lot for update;
  return l;
end;$function$;

-- ---------------------------------------------------------------- FILL_POST / RETURN_TO_WAREHOUSE (M:5.2, 5.4; ACC-B01/B02)
CREATE OR REPLACE FUNCTION erp.bc_move_post_v1(p_action text,p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_from uuid;v_to uuid;v_at timestamptz;v_lines jsonb;v_transfer uuid;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['from_location_id','to_location_id','physical_at','items','reason'],
    array['from_location_id','to_location_id','physical_at','items','reason','responsible','reference'],'service post payload');
  if p_action='FILL_POST' then
    v_from:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'from_location_id',true),array['MAIN'],'gudang asal');
    v_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'to_location_id',true),array['SERVICE_POST'],'pos tujuan');
  else
    v_from:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'from_location_id',true),array['SERVICE_POST'],'pos asal');
    v_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'to_location_id',true),array['MAIN'],'gudang tujuan');
  end if;
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  v_lines:=erp.bc_lines_v1(p_payload);
  if (select count(distinct x->>'material_id') from jsonb_array_elements(v_lines) x)<>jsonb_array_length(v_lines) then
    raise exception 'BC_LINES_INVALID: aksesori yang sama tidak boleh dua baris';end if;
  perform erp.bc_new_document_v1(p_request,p_action,v_at,p_payload);
  v_transfer:=erp.bc_post_transfer_v1(p_request,v_from,v_to,v_at,
    (select jsonb_agg(jsonb_build_object('material_id',x->>'material_id','qty',x->>'qty') order by (x->>'line_number')::int) from jsonb_array_elements(v_lines) x),
    btrim(p_payload->>'reason'));
  return jsonb_build_object('transfer_id',v_transfer);
end;$function$;

-- ---------------------------------------------------------------- INTERNAL_USE (M:5.1, 5.3; ACC-B03/B06)
-- Lines with their own physical time and purpose; one native adjustment per (time, purpose, location, custody). Purpose
-- FACTORY_USE keeps the existing INTERNAL_FACTORY_USE account (OTHER_EXPENSE); CUSTOMER_SERVICE and OWN_FG_REPAIR need the
-- ACC-DEC04 account. No note, receivable or reimbursement entitlement is made.
CREATE OR REPLACE FUNCTION erp.bc_internal_use_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_location uuid;v_lines jsonb;v_x jsonb;g record;v_adj uuid;v_account uuid;v_policy text;v_total numeric:=0;v_at timestamptz;
  v_dec04 jsonb;v_custody uuid;v_ids jsonb:='[]'::jsonb;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['location_id','items','reason'],
    array['location_id','items','reason','responsible','reference'],'internal use payload');
  v_location:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),array['MAIN','SERVICE_POST'],'lokasi sumber');
  v_lines:=erp.bc_lines_v1(p_payload,array['physical_at','purpose','customer_custody_id']);
  v_dec04:=erp.bc_policy_v1('ACC_DEC04');
  for v_x in select value from jsonb_array_elements(v_lines) loop
    if v_x->>'purpose' is null or v_x->>'purpose' not in('FACTORY_USE','CUSTOMER_SERVICE','OWN_FG_REPAIR') then
      raise exception 'BC_PURPOSE_INVALID: tujuan baris % FACTORY_USE, CUSTOMER_SERVICE atau OWN_FG_REPAIR',v_x->>'line_number';end if;
    perform erp.bc_parse_at_v1(v_x->>'physical_at','waktu baris '||(v_x->>'line_number'));
    if v_x->>'purpose'<>'FACTORY_USE' then
      perform erp.bc_require_policy_v1('ACC_DEC04','akun biaya '||case v_x->>'purpose' when 'CUSTOMER_SERVICE' then 'servis pelanggan' else 'perbaikan FG sendiri' end);
      if v_dec04->>((v_x->>'purpose')||'_account_id') is null then
        raise exception 'BC_POLICY_PENDING: akun tujuan % belum ditetapkan owner (ACC-DEC04)',v_x->>'purpose';end if;
    end if;
    v_custody:=erp.bc_uuid_v1(v_x,'customer_custody_id',false);
    if v_custody is not null and (v_x->>'purpose'<>'CUSTOMER_SERVICE' or not exists(select 1 from erp.bc_customer_custody_v1 c
        where c.id=v_custody and (c.out_document_id is null or (select status from erp.bc_documents_v1 where id=c.out_document_id)<>'POSTED')
          and (c.batch_id is not null or (select status from erp.bc_documents_v1 where id=c.in_document_id)='POSTED'))) then
      raise exception 'BC_CUSTODY_INVALID: titipan pelanggan hanya untuk servis pelanggan yang masih dititipkan';end if;
  end loop;
  select min(erp.bc_parse_at_v1(x->>'physical_at','physical_at')) into v_at from jsonb_array_elements(v_lines) x;
  perform erp.bc_new_document_v1(p_request,'INTERNAL_USE',v_at,p_payload,
    case when exists(select 1 from jsonb_array_elements(v_lines) x where x->>'purpose'<>'FACTORY_USE')
      then jsonb_build_object('ACC_DEC04',erp.bc_policy_version_v1('ACC_DEC04')) else '{}'::jsonb end
    ||jsonb_build_object('ACC_DEC07',erp.bc_policy_version_v1('ACC_DEC07')));
  for g in select erp.bc_parse_at_v1(x->>'physical_at','physical_at') at_,x->>'purpose' purpose,nullif(x->>'customer_custody_id','') custody,
      jsonb_agg(jsonb_build_object('material_id',x->>'material_id','qty_signed',(-(x->>'qty')::numeric)::text) order by (x->>'line_number')::int) items,
      jsonb_agg(x order by (x->>'line_number')::int) lines
    from jsonb_array_elements(v_lines) x group by 1,2,3 order by 1,2,3 loop
    v_account:=case g.purpose when 'FACTORY_USE' then erp.bc_adjustment_account_v1(null,'OTHER_EXPENSE')
      else (v_dec04->>(g.purpose||'_account_id'))::uuid end;
    v_policy:=case when g.purpose='FACTORY_USE' then null else 'ACC_DEC04' end;
    v_adj:=erp.bc_post_adjustment_v1(p_request,v_location,g.at_,'INTERNAL_FACTORY_USE',g.items,btrim(p_payload->>'reason'),g.purpose,v_account,v_policy);
    insert into erp.bc_internal_use_lines_v1(document_id,line_number,material_id,location_id,qty,physical_at,purpose,customer_custody_id,adjustment_id)
    select p_request,(x->>'line_number')::int,(x->>'material_id')::uuid,v_location,(x->>'qty')::numeric,g.at_,g.purpose,g.custody::uuid,v_adj
    from jsonb_array_elements(g.lines) x;
    v_total:=v_total-erp.bc_adjustment_value_v1(v_adj);
    v_ids:=v_ids||jsonb_build_array(v_adj);
  end loop;
  perform erp.bc_require_value_approval_v1(v_total);
  return jsonb_build_object('adjustment_ids',v_ids,'cost',v_total::numeric(20,2)::text);
end;$function$;

-- ---------------------------------------------------------------- RECEIVE_RETURN (M:5.6; ACC-C01..C05, C09, C11)
-- Asks the origin first. SERVICE_LEFTOVER: company stock moves from the post to the inspection area (value kept). NOTE_RETURN
-- (a posted mandor note line, native or opening): mandor-owned custody until an ACC-DEC05 credit, capped by the note line's
-- quantity less its other returns. TEARDOWN and LEGACY: company custody with value pending (ACC-DEC03), LEGACY only for
-- owner/admin (special review). The physical time is the real return time (ACC-DEC01: both real timelines).
CREATE OR REPLACE FUNCTION erp.bc_receive_return_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_kind text:=upper(coalesce(p_payload->>'source_kind',''));v_at timestamptz;v_zone uuid;v_from uuid;v_lines jsonb;v_x jsonb;
  v_lot uuid;v_lots jsonb:='[]'::jsonb;v_item erp.contractor_material_issue_items%rowtype;v_issue erp.contractor_material_issues%rowtype;
  v_used numeric;v_note record;v_out erp.bc_outstanding_returns_v1%rowtype;v_transfer uuid;v_ref text;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['source_kind','location_id','physical_at','reason'],
    array['source_kind','location_id','from_location_id','physical_at','items','note_item_id','opening_note_line_id','qty','reason',
      'responsible','reference'],'return receipt payload');
  if v_kind not in('SERVICE_LEFTOVER','NOTE_RETURN','TEARDOWN','LEGACY') then
    raise exception 'BC_SOURCE_KIND: asal pengembalian SERVICE_LEFTOVER, NOTE_RETURN, TEARDOWN atau LEGACY';end if;
  v_zone:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),array['INSPECTION'],'area pemeriksaan');
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  v_ref:=erp.bc_text_v1(p_payload,'reference',v_kind in('TEARDOWN','LEGACY'),200);
  if v_kind='LEGACY' then
    begin perform erp.require_owner_admin();
    exception when others then raise exception 'BC_LEGACY_REVIEW: histori lama tanpa sumber hanya dicatat owner/admin (review khusus)';end;
  end if;
  if v_kind='NOTE_RETURN' then
    if (p_payload ? 'items') or (p_payload ? 'from_location_id') then raise exception 'BC_SOURCE_KIND: retur nota memakai baris nota dan qty';end if;
    if (p_payload ? 'note_item_id')=(p_payload ? 'opening_note_line_id') then
      raise exception 'BC_NOTE_SOURCE_REQUIRED: pilih satu baris nota mandor (nota sistem atau nota saldo awal)';end if;
    perform erp.bc_new_document_v1(p_request,'RECEIVE_RETURN',v_at,p_payload);
    if p_payload ? 'note_item_id' then
      select * into v_item from erp.contractor_material_issue_items where id=erp.bc_uuid_v1(p_payload,'note_item_id',true);
      if v_item.id is null then raise exception 'BC_NOTE_SOURCE_REQUIRED: baris nota tidak ditemukan';end if;
      perform pg_advisory_xact_lock(hashtextextended('BCNOTE|'||v_item.id::text,0));
      select * into v_issue from erp.contractor_material_issues where id=v_item.issue_id for update;
      if v_issue.status<>'POSTED' then raise exception 'BC_NOTE_NOT_POSTED: retur hanya untuk nota mandor yang disahkan dan tidak dibatalkan';end if;
      if (select material_type from erp.materials where id=v_item.material_id)<>'ACCESSORY' then raise exception 'BC_NOTE_NOT_ACCESSORY: retur nota hanya untuk aksesori';end if;
      if v_at<v_issue.physical_at then raise exception 'BC_DATE_BEFORE_SOURCE: retur tidak boleh sebelum waktu nota';end if;
      select coalesce(sum(l.qty_received),0) into v_used from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
        where l.note_item_id=v_item.id and d.status='POSTED';
      if erp.bc_parse_qty_v1(v_item.material_id,p_payload->'qty','qty')>v_item.qty-v_used then
        raise exception 'BC_RETURN_EXCEEDS_SOURCE: sisa yang dapat dikembalikan dari baris nota ini % , diminta %',(v_item.qty-v_used)::numeric(18,6),p_payload->>'qty';end if;
      insert into erp.bc_return_lots_v1(document_id,source_kind,owner_kind,value_mode,material_id,location_id,qty_received,received_at,contractor_id,note_item_id)
      values(p_request,'NOTE_RETURN','MANDOR','MANDOR_OWNED',v_item.material_id,v_zone,(p_payload->>'qty')::numeric,v_at,v_issue.contractor_id,v_item.id)
      returning id into v_lot;
    else
      select n.*,b.contractor_id,b.status balance_status into v_note from erp.bc_opening_note_lines_v1 n
        join erp.opening_subledger_balances b on b.id=n.balance_id where n.id=erp.bc_uuid_v1(p_payload,'opening_note_line_id',true);
      if v_note.id is null then raise exception 'BC_NOTE_SOURCE_REQUIRED: baris nota saldo awal tidak ditemukan';end if;
      perform pg_advisory_xact_lock(hashtextextended('BCNOTE|'||v_note.id::text,0));
      if v_at<(select cutover_at from erp.migration_batches where id=v_note.batch_id) then
        raise exception 'BC_DATE_BEFORE_SOURCE: retur nota saldo awal dicatat pada atau sesudah cutover';end if;
      select coalesce(sum(l.qty_received),0) into v_used from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
        where l.opening_note_line_id=v_note.id and d.status='POSTED';
      if erp.bc_parse_qty_v1(v_note.material_id,p_payload->'qty','qty')>v_note.qty-v_used then
        raise exception 'BC_RETURN_EXCEEDS_SOURCE: sisa yang dapat dikembalikan dari baris nota ini % , diminta %',(v_note.qty-v_used)::numeric(18,6),p_payload->>'qty';end if;
      insert into erp.bc_return_lots_v1(document_id,source_kind,owner_kind,value_mode,material_id,location_id,qty_received,received_at,contractor_id,opening_note_line_id)
      values(p_request,'OPENING_NOTE_RETURN','MANDOR','MANDOR_OWNED',v_note.material_id,v_zone,(p_payload->>'qty')::numeric,v_at,v_note.contractor_id,v_note.id)
      returning id into v_lot;
    end if;
    return jsonb_build_object('lot_ids',jsonb_build_array(v_lot));
  end if;
  if (p_payload ? 'note_item_id') or (p_payload ? 'opening_note_line_id') or (p_payload ? 'qty') then
    raise exception 'BC_SOURCE_KIND: baris nota hanya untuk retur nota';end if;
  v_lines:=erp.bc_lines_v1(p_payload,array['outstanding_id']);
  perform erp.bc_new_document_v1(p_request,'RECEIVE_RETURN',v_at,p_payload);
  if v_kind='SERVICE_LEFTOVER' then
    v_from:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'from_location_id',true),array['SERVICE_POST'],'pos asal');
    if exists(select 1 from jsonb_array_elements(v_lines) x where x ? 'outstanding_id') then
      raise exception 'BC_SOURCE_KIND: sisa pos adalah stok perusahaan, bukan barang yang ditunggu';end if;
    if (select count(distinct x->>'material_id') from jsonb_array_elements(v_lines) x)<>jsonb_array_length(v_lines) then
      raise exception 'BC_LINES_INVALID: aksesori yang sama tidak boleh dua baris';end if;
    v_transfer:=erp.bc_post_transfer_v1(p_request,v_from,v_zone,v_at,
      (select jsonb_agg(jsonb_build_object('material_id',x->>'material_id','qty',x->>'qty') order by (x->>'line_number')::int) from jsonb_array_elements(v_lines) x),
      btrim(p_payload->>'reason'));
  elsif p_payload ? 'from_location_id' then raise exception 'BC_SOURCE_KIND: lokasi asal hanya untuk sisa pos';
  end if;
  for v_x in select value from jsonb_array_elements(v_lines) order by (value->>'line_number')::int loop
    if v_x ? 'outstanding_id' then
      select * into v_out from erp.bc_outstanding_returns_v1 where id=erp.bc_uuid_v1(v_x,'outstanding_id',true) for update;
      if v_out.id is null or v_out.status<>'OPEN' or v_out.owner_kind<>'COMPANY' then
        raise exception 'BC_OUTSTANDING_INVALID: barang yang ditunggu tidak ditemukan atau bukan milik perusahaan';end if;
      if v_out.material_id is distinct from (v_x->>'material_id')::uuid then raise exception 'BC_OUTSTANDING_INVALID: aksesori berbeda dari yang ditunggu';end if;
      select coalesce(sum(l.qty_received),0) into v_used from erp.bc_return_lots_v1 l left join erp.bc_documents_v1 d on d.id=l.document_id
        where l.outstanding_id=v_out.id and d.status='POSTED';
      if (v_x->>'qty')::numeric>v_out.qty_expected-v_used then
        raise exception 'BC_RETURN_EXCEEDS_SOURCE: sisa yang ditunggu % , diterima %',(v_out.qty_expected-v_used)::numeric(18,6),v_x->>'qty';end if;
    end if;
    insert into erp.bc_return_lots_v1(document_id,line_number,source_kind,owner_kind,value_mode,material_id,location_id,qty_received,received_at,
      outstanding_id,reference)
    values(p_request,(v_x->>'line_number')::int,v_kind,'COMPANY',case when v_kind='SERVICE_LEFTOVER' then 'LEDGER' else 'PENDING' end,
      (v_x->>'material_id')::uuid,v_zone,(v_x->>'qty')::numeric,v_at,nullif(v_x->>'outstanding_id','')::uuid,v_ref)
    returning id into v_lot;
    v_lots:=v_lots||jsonb_build_array(v_lot);
  end loop;
  return jsonb_build_object('lot_ids',v_lots,'transfer_id',v_transfer);
end;$function$;

-- ---------------------------------------------------------------- INSPECT (M:5.6, 6.2; ACC-C01/C02/C11)
-- Partial, by several inspectors, never above what is still waiting. A ledger lot moves the inspected quantity from the
-- inspection area to the chosen warehouse (usable) and damaged area (damaged); a custody lot only changes its condition.
CREATE OR REPLACE FUNCTION erp.bc_inspect_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.bc_return_lots_v1%rowtype;s jsonb;v_u numeric:=0;v_d numeric:=0;v_at timestamptz;v_inspector text;v_usable_to uuid;v_damaged_to uuid;
  v_event uuid;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['lot_id','inspected_at','inspector','reason'],
    array['lot_id','inspected_at','inspector','qty_usable','qty_damaged','usable_location_id','damaged_location_id','reason','responsible','reference'],
    'inspection payload');
  l:=erp.bc_lock_lot_v1(erp.bc_uuid_v1(p_payload,'lot_id',true));
  v_at:=erp.bc_parse_at_v1(p_payload->>'inspected_at','inspected_at');
  if v_at<l.received_at then raise exception 'BC_DATE_BEFORE_SOURCE: pemeriksaan tidak boleh sebelum barang diterima';end if;
  v_inspector:=erp.bc_text_v1(p_payload,'inspector',true,120);
  if p_payload ? 'qty_usable' then v_u:=erp.bc_parse_qty_v1(l.material_id,p_payload->'qty_usable','qty_usable');end if;
  if p_payload ? 'qty_damaged' then v_d:=erp.bc_parse_qty_v1(l.material_id,p_payload->'qty_damaged','qty_damaged');end if;
  if v_u+v_d<=0 then raise exception 'BC_QTY_INVALID: isi jumlah layak dan/atau rusak';end if;
  s:=erp.bc_lot_state_v1(l.id);
  if v_u+v_d>(s->>'waiting')::numeric then
    raise exception 'BC_INSPECT_EXCEEDS_WAITING: yang belum diperiksa % , diperiksa %',((s->>'waiting')::numeric)::numeric(18,6),v_u+v_d;end if;
  if l.value_mode='LEDGER' then
    if v_u>0 then v_usable_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'usable_location_id',true),array['MAIN'],'gudang untuk barang layak');
    elsif p_payload ? 'usable_location_id' then raise exception 'BC_LOCATION_INVALID: tidak ada barang layak';end if;
    if v_d>0 then v_damaged_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'damaged_location_id',true),array['DAMAGED'],'area rusak');
    elsif p_payload ? 'damaged_location_id' then raise exception 'BC_LOCATION_INVALID: tidak ada barang rusak';end if;
  elsif (p_payload ? 'usable_location_id') or (p_payload ? 'damaged_location_id') then
    raise exception 'BC_LOCATION_INVALID: barang titipan/nilai pending tidak masuk stok saat diperiksa';
  end if;
  perform erp.bc_new_document_v1(p_request,'INSPECT',v_at,p_payload);
  insert into erp.bc_lot_events_v1(document_id,lot_id,event_kind,qty_usable,qty_damaged,inspector,event_at)
  values(p_request,l.id,'INSPECT',v_u,v_d,v_inspector,v_at) returning id into v_event;
  if v_u>0 and l.value_mode='LEDGER' then
    perform erp.bc_post_transfer_v1(p_request,l.location_id,v_usable_to,v_at,jsonb_build_array(jsonb_build_object('material_id',l.material_id,'qty',v_u::text)),btrim(p_payload->>'reason'));
  end if;
  if v_d>0 and l.value_mode='LEDGER' then
    perform erp.bc_post_transfer_v1(p_request,l.location_id,v_damaged_to,v_at,jsonb_build_array(jsonb_build_object('material_id',l.material_id,'qty',v_d::text)),btrim(p_payload->>'reason'));
  end if;
  return jsonb_build_object('event_id',v_event,'lot',erp.bc_lot_state_v1(l.id));
end;$function$;

-- ---------------------------------------------------------------- VALUE_CUSTODY (ACC-DEC03; ACC-C05, C12, ALL-C03)
-- Company custody with value pending enters the ledger only with the owner's recovery-value policy: a native inbound
-- adjustment at the approved unit value (capped by the moving average when the policy says so) against the policy
-- account, into the warehouse (usable) or the damaged area (damaged). Never a zero-value stock-in.
CREATE OR REPLACE FUNCTION erp.bc_value_custody_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.bc_return_lots_v1%rowtype;s jsonb;v_policy jsonb;v_cond text:=upper(coalesce(p_payload->>'condition',''));v_qty numeric;v_unit numeric;
  v_to uuid;v_at timestamptz;v_adj uuid;v_event uuid;v_avg numeric;
begin
  perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['lot_id','condition','qty','unit_value','location_id','physical_at','reason'],
    array['lot_id','condition','qty','unit_value','location_id','physical_at','reason','responsible','reference'],'valuation payload');
  v_policy:=erp.bc_require_policy_v1('ACC_DEC03','nilai pemulihan barang bekas');
  l:=erp.bc_lock_lot_v1(erp.bc_uuid_v1(p_payload,'lot_id',true));
  if l.value_mode<>'PENDING' then raise exception 'BC_NOT_PENDING_VALUE: hanya barang perusahaan bernilai pending yang dapat dinilai';end if;
  if v_cond not in('USABLE','DAMAGED') then raise exception 'BC_CONDITION_INVALID: nilai hanya untuk barang yang sudah diperiksa (USABLE atau DAMAGED)';end if;
  v_qty:=erp.bc_parse_qty_v1(l.material_id,p_payload->'qty','qty');
  s:=erp.bc_lot_state_v1(l.id);
  if v_qty>(s->>lower(v_cond))::numeric then
    raise exception 'BC_QTY_EXCEEDS_BUCKET: % yang tersedia % , diminta %',v_cond,((s->>lower(v_cond))::numeric)::numeric(18,6),v_qty;end if;
  if jsonb_typeof(p_payload->'unit_value') is distinct from 'string' then raise exception 'BB_AMOUNT_INVALID: unit_value harus nominal tepat dua desimal';end if;
  v_unit:=erp.bb_parse_amount_v1(p_payload->>'unit_value','unit_value');
  if v_policy->>'unit_value_cap'='MOVING_AVERAGE' then
    select moving_average_cost into v_avg from erp.materials where id=l.material_id for update;
    if v_avg is null or v_avg<=0 or v_unit>v_avg then
      raise exception 'BC_VALUE_ABOVE_CAP: nilai pemulihan % melebihi rata-rata biaya barang baru %',v_unit,coalesce(v_avg,0)::numeric(18,6);end if;
  end if;
  v_to:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),case when v_cond='USABLE' then array['MAIN'] else array['DAMAGED'] end,
    case when v_cond='USABLE' then 'gudang untuk barang layak' else 'area rusak' end);
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if v_at<l.received_at then raise exception 'BC_DATE_BEFORE_SOURCE: penilaian tidak boleh sebelum barang diterima';end if;
  perform erp.bc_new_document_v1(p_request,'VALUE_CUSTODY',v_at,p_payload,jsonb_build_object('ACC_DEC03',erp.bc_policy_version_v1('ACC_DEC03')));
  insert into erp.bc_lot_events_v1(document_id,lot_id,event_kind,condition,qty,event_at,target_location_id,unit_value,amount)
  values(p_request,l.id,'VALUE',v_cond,v_qty,v_at,v_to,v_unit,round(v_qty*v_unit,2)) returning id into v_event;
  v_adj:=erp.bc_post_adjustment_v1(p_request,v_to,v_at,'OTHER',jsonb_build_array(jsonb_build_object('material_id',l.material_id,
    'qty_signed',v_qty::text,'input_unit_cost',v_unit::text)),btrim(p_payload->>'reason'),'RECOVERY_VALUATION',(v_policy->>'credit_account_id')::uuid,'ACC_DEC03');
  return jsonb_build_object('event_id',v_event,'adjustment_id',v_adj,'value',round(v_qty*v_unit,2)::text,'lot',erp.bc_lot_state_v1(l.id));
end;$function$;

-- ---------------------------------------------------------------- CLOSE_CUSTODY: back to its owner, or discarded
-- A mandor-owned return goes back to the mandor (any condition); company custody without value may be discarded by
-- owner/admin (no ledger effect: it never had value there). A ledger lot is closed by inspection, never here.
CREATE OR REPLACE FUNCTION erp.bc_close_custody_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare l erp.bc_return_lots_v1%rowtype;s jsonb;v_kind text:=upper(coalesce(p_payload->>'disposition',''));v_cond text:=upper(coalesce(p_payload->>'condition',''));
  v_qty numeric;v_at timestamptz;v_event uuid;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['lot_id','disposition','condition','qty','physical_at','reason'],
    array['lot_id','disposition','condition','qty','physical_at','reason','responsible','reference'],'custody close payload');
  l:=erp.bc_lock_lot_v1(erp.bc_uuid_v1(p_payload,'lot_id',true));
  if l.value_mode='LEDGER' then raise exception 'BC_LEDGER_LOT: stok perusahaan diselesaikan lewat pemeriksaan';end if;
  if v_kind='RETURN_TO_OWNER' then
    if l.owner_kind<>'MANDOR' then raise exception 'BC_DISPOSITION_INVALID: hanya barang milik mandor yang dikembalikan ke pemiliknya';end if;
  elsif v_kind='DISCARD' then
    if l.owner_kind<>'COMPANY' then raise exception 'BC_DISPOSITION_INVALID: barang milik mandor tidak dapat dibuang perusahaan';end if;
    begin perform erp.require_owner_admin();
    exception when others then raise exception 'BC_APPROVAL_REQUIRED: pembuangan barang titipan memerlukan owner/admin';end;
  else raise exception 'BC_DISPOSITION_INVALID: RETURN_TO_OWNER atau DISCARD';end if;
  if v_cond not in('WAITING','USABLE','DAMAGED') then raise exception 'BC_CONDITION_INVALID: WAITING, USABLE atau DAMAGED';end if;
  if v_kind='DISCARD' and v_cond='WAITING' then raise exception 'BC_CONDITION_INVALID: periksa dahulu sebelum dibuang';end if;
  v_qty:=erp.bc_parse_qty_v1(l.material_id,p_payload->'qty','qty');
  s:=erp.bc_lot_state_v1(l.id);
  if v_qty>(s->>lower(v_cond))::numeric then
    raise exception 'BC_QTY_EXCEEDS_BUCKET: % yang tersedia % , diminta %',v_cond,((s->>lower(v_cond))::numeric)::numeric(18,6),v_qty;end if;
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if v_at<l.received_at then raise exception 'BC_DATE_BEFORE_SOURCE: tidak boleh sebelum barang diterima';end if;
  perform erp.bc_new_document_v1(p_request,'CLOSE_CUSTODY',v_at,p_payload);
  insert into erp.bc_lot_events_v1(document_id,lot_id,event_kind,condition,qty,event_at)
  values(p_request,l.id,v_kind,v_cond,v_qty,v_at) returning id into v_event;
  return jsonb_build_object('event_id',v_event,'lot',erp.bc_lot_state_v1(l.id));
end;$function$;

-- ---------------------------------------------------------------- DISPOSE_STOCK: valued damaged stock written off
CREATE OR REPLACE FUNCTION erp.bc_dispose_stock_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_location uuid;v_at timestamptz;v_lines jsonb;v_adj uuid;v_value numeric;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['location_id','physical_at','items','reason'],
    array['location_id','physical_at','items','reason','responsible','reference'],'disposal payload');
  v_location:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),array['DAMAGED'],'area rusak');
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  v_lines:=erp.bc_lines_v1(p_payload);
  perform erp.bc_new_document_v1(p_request,'DISPOSE_STOCK',v_at,p_payload,jsonb_build_object('ACC_DEC07',erp.bc_policy_version_v1('ACC_DEC07')));
  v_adj:=erp.bc_post_adjustment_v1(p_request,v_location,v_at,'DAMAGE',
    (select jsonb_agg(jsonb_build_object('material_id',x->>'material_id','qty_signed',(-(x->>'qty')::numeric)::text) order by (x->>'line_number')::int) from jsonb_array_elements(v_lines) x),
    btrim(p_payload->>'reason'),'DAMAGE_DISPOSAL',erp.bc_adjustment_account_v1(null,'OTHER_EXPENSE'));
  v_value:=-erp.bc_adjustment_value_v1(v_adj);
  perform erp.bc_require_value_approval_v1(v_value);
  return jsonb_build_object('adjustment_id',v_adj,'cost',v_value::numeric(20,2)::text);
end;$function$;

-- ---------------------------------------------------------------- customer garment custody (ACC-C10)
CREATE OR REPLACE FUNCTION erp.bc_customer_garment_v1(p_action text,p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare c erp.bc_customer_custody_v1%rowtype;v_at timestamptz;v_customer uuid;v_product uuid;v_qty numeric;
begin
  if p_action='CUSTOMER_GARMENT_IN' then
    perform erp._cp3_assert_closed_json_object(p_payload,array['customer_id','description','qty','physical_at','reason'],
      array['customer_id','product_id','description','qty','physical_at','reason','responsible','reference'],'customer garment payload');
    v_customer:=erp.bc_uuid_v1(p_payload,'customer_id',true);
    if not exists(select 1 from erp.customers where id=v_customer and is_active) then raise exception 'BC_CUSTOMER_INVALID: pilih pelanggan aktif';end if;
    v_product:=erp.bc_uuid_v1(p_payload,'product_id',false);
    if v_product is not null and not exists(select 1 from erp.products where id=v_product) then raise exception 'BC_PRODUCT_INVALID: produk tidak ditemukan';end if;
    if jsonb_typeof(p_payload->'qty') is distinct from 'string' or p_payload->>'qty'!~'^[1-9][0-9]{0,8}$' then
      raise exception 'BC_QTY_INVALID: jumlah titipan harus PCS utuh positif';end if;
    v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
    perform erp.bc_new_document_v1(p_request,p_action,v_at,p_payload);
    insert into erp.bc_customer_custody_v1(id,in_document_id,customer_id,product_id,description,qty,received_at)
    values(p_request,p_request,v_customer,v_product,erp.bc_text_v1(p_payload,'description',true,200),(p_payload->>'qty')::numeric,v_at);
    return jsonb_build_object('custody_id',p_request);
  end if;
  perform erp._cp3_assert_closed_json_object(p_payload,array['custody_id','physical_at','reason'],
    array['custody_id','physical_at','reason','responsible','reference'],'customer garment payload');
  select * into c from erp.bc_customer_custody_v1 where id=erp.bc_uuid_v1(p_payload,'custody_id',true) for update;
  if c.id is null or (c.batch_id is null and (select status from erp.bc_documents_v1 where id=c.in_document_id)<>'POSTED') then
    raise exception 'BC_CUSTODY_INVALID: titipan pelanggan tidak ditemukan';end if;
  if c.out_document_id is not null and (select status from erp.bc_documents_v1 where id=c.out_document_id)='POSTED' then
    raise exception 'BC_CUSTODY_CLOSED: titipan sudah dikembalikan ke pelanggan';end if;
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if v_at<c.received_at then raise exception 'BC_DATE_BEFORE_SOURCE: pengembalian tidak boleh sebelum titipan diterima';end if;
  perform erp.bc_new_document_v1(p_request,p_action,v_at,p_payload);
  update erp.bc_customer_custody_v1 set out_document_id=p_request where id=c.id;
  return jsonb_build_object('custody_id',c.id);
end;$function$;

-- ---------------------------------------------------------------- COUNT_POST / RESOLVE_VARIANCE (ACC-B06)
CREATE OR REPLACE FUNCTION erp.bc_count_post_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_location uuid;v_at timestamptz;v_x jsonb;v_book numeric;v_counted numeric;v_ids jsonb:='[]'::jsonb;v_id uuid;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['location_id','physical_at','items','reason'],
    array['location_id','physical_at','items','reason','responsible','reference'],'count payload');
  v_location:=erp.bc_location_v1(erp.bc_uuid_v1(p_payload,'location_id',true),array['SERVICE_POST'],'pos servis');
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if jsonb_typeof(p_payload->'items') is distinct from 'array' or jsonb_array_length(p_payload->'items') not between 1 and 100 then
    raise exception 'BC_LINES_INVALID: isi 1 sampai 100 baris hitung';end if;
  perform erp.bc_new_document_v1(p_request,'COUNT_POST',v_at,p_payload);
  for v_x in select value from jsonb_array_elements(p_payload->'items') loop
    perform erp._cp3_assert_closed_json_object(v_x,array['material_id','counted_qty'],array['material_id','counted_qty'],'count line');
    perform erp.bc_accessory_v1(erp.bc_uuid_v1(v_x,'material_id',true));
    if jsonb_typeof(v_x->'counted_qty') is distinct from 'string' or v_x->>'counted_qty'!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$' then
      raise exception 'BC_QTY_INVALID: hasil hitung wajib angka teks nol atau lebih';end if;
    v_counted:=(v_x->>'counted_qty')::numeric;
    if exists(select 1 from erp.materials m join erp.uom_definitions u on u.unit_code=m.unit_code where m.id=(v_x->>'material_id')::uuid
        and u.dimension='COUNT') and v_counted<>trunc(v_counted) then raise exception 'BC_QTY_INVALID: hasil hitung harus PCS utuh';end if;
    select coalesce(sum(qty_signed),0) into v_book from erp.material_stock_movements
      where material_id=(v_x->>'material_id')::uuid and location_id=v_location and physical_at<=v_at;
    insert into erp.bc_count_variances_v1(document_id,material_id,location_id,book_qty,counted_qty,variance,counted_at)
    values(p_request,(v_x->>'material_id')::uuid,v_location,v_book,v_counted,v_counted-v_book,v_at) returning id into v_id;
    v_ids:=v_ids||jsonb_build_array(jsonb_build_object('variance_id',v_id,'book',v_book::text,'counted',v_counted::text,'variance',(v_counted-v_book)::text));
  end loop;
  return jsonb_build_object('variances',v_ids);
end;$function$;

-- A negative variance becomes a counted LOSS only by an explicit decision (native LOSS adjustment, valued, ACC-DEC07);
-- DISMISS keeps the book (a recount). A variance is never turned into service usage.
CREATE OR REPLACE FUNCTION erp.bc_resolve_variance_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v erp.bc_count_variances_v1%rowtype;v_kind text:=upper(coalesce(p_payload->>'resolution',''));v_at timestamptz;v_adj uuid;v_value numeric;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['variance_id','resolution','physical_at','reason'],
    array['variance_id','resolution','physical_at','reason','responsible','reference'],'variance payload');
  select * into v from erp.bc_count_variances_v1 where id=erp.bc_uuid_v1(p_payload,'variance_id',true) for update;
  if v.id is null or (select status from erp.bc_documents_v1 where id=v.document_id)<>'POSTED' then raise exception 'BC_VARIANCE_INVALID: selisih tidak ditemukan';end if;
  if v.resolution_document_id is not null and (select status from erp.bc_documents_v1 where id=v.resolution_document_id)='POSTED' then
    raise exception 'BC_VARIANCE_RESOLVED: selisih ini sudah diselesaikan';end if;
  if v_kind not in('LOSS','DISMISS') then raise exception 'BC_VARIANCE_INVALID: LOSS atau DISMISS';end if;
  if v_kind='LOSS' and v.variance>=0 then raise exception 'BC_VARIANCE_INVALID: hanya selisih kurang yang dapat dicatat hilang';end if;
  v_at:=erp.bc_parse_at_v1(p_payload->>'physical_at','physical_at');
  if v_at<v.counted_at then raise exception 'BC_DATE_BEFORE_SOURCE: penyelesaian tidak boleh sebelum hitung';end if;
  perform erp.bc_location_v1(v.location_id,array['SERVICE_POST'],'pos servis');
  perform erp.bc_new_document_v1(p_request,'RESOLVE_VARIANCE',v_at,p_payload,jsonb_build_object('ACC_DEC07',erp.bc_policy_version_v1('ACC_DEC07')));
  update erp.bc_count_variances_v1 set resolution_document_id=p_request where id=v.id;
  if v_kind='LOSS' then
    v_adj:=erp.bc_post_adjustment_v1(p_request,v.location_id,v_at,'LOSS',jsonb_build_array(jsonb_build_object('material_id',v.material_id,
      'qty_signed',v.variance::text)),btrim(p_payload->>'reason'),'COUNT_LOSS',erp.bc_adjustment_account_v1(null,'OTHER_EXPENSE'));
    v_value:=-erp.bc_adjustment_value_v1(v_adj);
    perform erp.bc_require_value_approval_v1(v_value);
  end if;
  return jsonb_build_object('variance_id',v.id,'resolution',v_kind,'adjustment_id',v_adj,'cost',coalesce(v_value,0)::numeric(20,2)::text);
end;$function$;
