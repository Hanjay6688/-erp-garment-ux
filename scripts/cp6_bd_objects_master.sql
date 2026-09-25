-- ================================================================ BD laundry master (LAU-05b, M:3729-3737, M:4479)
-- Per vendor: pricing mode (base rate per process, fixed package, or priced components picked per delivery), pricing unit
-- (per PCS, or a lump sum per batch when LAU-DEC01 allows BATCH) and an optional minimum charge (LAU-DEC01 MINIMUM).
-- Components are data, not a fixed list of names (LAU-T04). Every price is a version with an effective window; a version
-- never starts at or before a posted delivery it could reprice (posted snapshots are never rewritten, LAU-T07/T14).

create table erp.bd_laundry_vendor_terms_v1(
  vendor_id uuid primary key references erp.laundry_vendors(id),
  pricing_mode text not null check(pricing_mode in('RATE','PACKAGE','COMPONENTS')),
  pricing_unit text not null check(pricing_unit in('PCS','BATCH')),
  minimum_charge numeric(18,2) check(minimum_charge>0),
  row_version bigint not null default 1 check(row_version>0),
  updated_by uuid,
  updated_at timestamptz not null default statement_timestamp(),
  reason text not null check(length(btrim(reason))>0)
);
comment on table erp.bd_laundry_vendor_terms_v1 is 'BD: laundry vendor pricing terms (LAU-05b). No row = baseline RATE per PCS from laundry_vendor_rate_versions.';

create table erp.bd_laundry_components_v1(
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references erp.laundry_vendors(id),
  component_code text not null check(component_code~'^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$'),
  component_name text not null check(length(btrim(component_name)) between 2 and 120),
  is_active boolean not null default true,
  created_by uuid,
  created_at timestamptz not null default statement_timestamp()
);
create unique index bd_laundry_components_v1_code on erp.bd_laundry_components_v1(vendor_id,lower(component_code));

create table erp.bd_laundry_component_rates_v1(
  id uuid primary key default gen_random_uuid(),
  component_id uuid not null references erp.bd_laundry_components_v1(id),
  rate_status text not null check(rate_status in('KNOWN','UNKNOWN')),
  rate_per_pcs numeric(18,2) check(rate_per_pcs>=0),
  effective_from timestamptz not null,
  effective_to timestamptz,
  reason text not null check(length(btrim(reason))>0),
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  check((rate_status='KNOWN')=(rate_per_pcs is not null)),
  check(effective_to is null or effective_to>effective_from)
);
comment on table erp.bd_laundry_component_rates_v1 is 'BD: component price versions. UNKNOWN is an explicit, attributed unknown price (LAU-T12), never zero; a missing version is an error, not unknown (LAU-T13).';

create table erp.bd_laundry_packages_v1(
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references erp.laundry_vendors(id),
  package_code text not null check(package_code~'^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$'),
  package_name text not null check(length(btrim(package_name)) between 2 and 120),
  is_active boolean not null default true,
  created_by uuid,
  created_at timestamptz not null default statement_timestamp()
);
create unique index bd_laundry_packages_v1_code on erp.bd_laundry_packages_v1(vendor_id,lower(package_code));
create table erp.bd_laundry_package_components_v1(
  package_id uuid not null references erp.bd_laundry_packages_v1(id),
  component_id uuid not null references erp.bd_laundry_components_v1(id),
  primary key(package_id,component_id)
);
create table erp.bd_laundry_package_rates_v1(
  id uuid primary key default gen_random_uuid(),
  package_id uuid not null references erp.bd_laundry_packages_v1(id),
  rate_per_pcs numeric(18,2) not null check(rate_per_pcs>=0),
  effective_from timestamptz not null,
  effective_to timestamptz,
  reason text not null check(length(btrim(reason))>0),
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  check(effective_to is null or effective_to>effective_from)
);

-- LAU-DEC05: a rate scoped to a model (template), a model size, or a model size colour; exactly one basis per unit.
create table erp.bd_laundry_scoped_rates_v1(
  id uuid primary key default gen_random_uuid(),
  vendor_id uuid not null references erp.laundry_vendors(id),
  wash_process_id uuid not null references erp.wash_processes(id),
  scope text not null check(scope in('MODEL','MODEL_SIZE','MODEL_SIZE_COLOR')),
  model_id uuid not null,
  size_id uuid,
  color_name text,
  rate_per_pcs numeric(18,2) not null check(rate_per_pcs>=0),
  effective_from timestamptz not null,
  effective_to timestamptz,
  policy_version bigint not null,
  reason text not null check(length(btrim(reason))>0),
  created_by uuid,
  created_at timestamptz not null default statement_timestamp(),
  check(effective_to is null or effective_to>effective_from),
  check((scope='MODEL' and size_id is null and color_name is null) or (scope='MODEL_SIZE' and size_id is not null and color_name is null)
        or (scope='MODEL_SIZE_COLOR' and size_id is not null and color_name is not null and length(btrim(color_name))>0))
);

-- Request log: idempotency and audit of every BD action (the response is replayed for the same request id).
create table erp.bd_requests_v1(
  request_id uuid primary key,
  action text not null,
  actor uuid,
  payload jsonb not null,
  response jsonb not null,
  created_at timestamptz not null default statement_timestamp()
);

-- ---------------------------------------------------------------- version windows
-- A new version may not start at or before a posted (not reversed) delivery of the same vendor (and process when given):
-- such a delivery would be priced again at receipt (receipts price at the send time).
CREATE OR REPLACE FUNCTION erp.bd_assert_version_start_v1(p_vendor uuid,p_process uuid,p_from timestamptz)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_last timestamptz;
begin
  perform pg_advisory_xact_lock(hashtextextended('LRATE:'||p_vendor::text||':'||coalesce(p_process::text,'*'),0));
  select max(d.physical_at) into v_last from erp.laundry_deliveries d
  where d.vendor_id=p_vendor and d.status not in('DRAFT','REVERSED') and (p_process is null or d.target_wash_process_id=p_process);
  if v_last is not null and p_from<=v_last then
    raise exception 'BD_VERSION_BEFORE_POSTED_DELIVERY: versi harga mulai % tidak boleh pada/ sebelum kiriman terakhir yang sudah diposting (%); snapshot kiriman lama tidak ditimpa',
      p_from,v_last;
  end if;
end;$function$;

-- Close the open version (if any) at the new start; refuse any other overlap.
CREATE OR REPLACE FUNCTION erp.bd_close_open_version_v1(p_table text,p_key_column text,p_key uuid,p_from timestamptz,p_to timestamptz)
 RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_overlap integer;
begin
  if p_table not in('bd_laundry_component_rates_v1','bd_laundry_package_rates_v1') then raise exception 'BD_INTERNAL: tabel versi tidak dikenal';end if;
  execute format('update erp.%I set effective_to=$2 where %I=$1 and effective_to is null and effective_from<$2',p_table,p_key_column) using p_key,p_from;
  execute format('select count(*) from erp.%I where %I=$1 and effective_from<coalesce($3,''infinity''::timestamptz) and coalesce(effective_to,''infinity''::timestamptz)>$2',
    p_table,p_key_column) into v_overlap using p_key,p_from,p_to;
  if v_overlap>0 then raise exception 'BD_VERSION_OVERLAP: versi harga bertumpuk dengan versi yang sudah ada';end if;
end;$function$;

-- ---------------------------------------------------------------- lookups (exactly one version, or an error)
CREATE OR REPLACE FUNCTION erp.bd_process_rate_at_v1(p_vendor uuid,p_process uuid,p_at timestamptz)
 RETURNS numeric LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_n integer;v_rate numeric;
begin
  select count(*)::integer,min(rate_per_pcs) into v_n,v_rate from erp.laundry_vendor_rate_versions
  where vendor_id=p_vendor and wash_process_id=p_process and effective_from<=p_at and (effective_to is null or effective_to>p_at);
  if v_n<>1 then raise exception 'BD_RATE_NOT_EXACT: tepat satu tarif dasar vendor/proses harus berlaku pada waktu kirim; ditemukan %',v_n;end if;
  return v_rate;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bd_component_rate_at_v1(p_component uuid,p_at timestamptz,out rate_status text,out rate_per_pcs numeric,out version_id uuid)
 LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_n integer;
begin
  select count(*)::integer into v_n from erp.bd_laundry_component_rates_v1 r
  where r.component_id=p_component and r.effective_from<=p_at and (r.effective_to is null or r.effective_to>p_at);
  if v_n<>1 then raise exception 'BD_COMPONENT_RATE_NOT_EXACT: tepat satu versi harga komponen harus berlaku pada waktu kirim; ditemukan % (tidak ada versi = galat, bukan harga belum diketahui)',v_n;end if;
  select r.rate_status,r.rate_per_pcs,r.id into rate_status,rate_per_pcs,version_id from erp.bd_laundry_component_rates_v1 r
  where r.component_id=p_component and r.effective_from<=p_at and (r.effective_to is null or r.effective_to>p_at);
end;$function$;

CREATE OR REPLACE FUNCTION erp.bd_package_rate_at_v1(p_package uuid,p_at timestamptz,out rate_per_pcs numeric,out version_id uuid)
 LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_n integer;
begin
  select count(*)::integer into v_n from erp.bd_laundry_package_rates_v1 r
  where r.package_id=p_package and r.effective_from<=p_at and (r.effective_to is null or r.effective_to>p_at);
  if v_n<>1 then raise exception 'BD_PACKAGE_RATE_NOT_EXACT: tepat satu versi harga paket harus berlaku pada waktu kirim; ditemukan %',v_n;end if;
  select r.rate_per_pcs,r.id into rate_per_pcs,version_id from erp.bd_laundry_package_rates_v1 r
  where r.package_id=p_package and r.effective_from<=p_at and (r.effective_to is null or r.effective_to>p_at);
end;$function$;

-- The most specific scoped rate the owner's scopes allow; null when none applies.
CREATE OR REPLACE FUNCTION erp.bd_scoped_rate_at_v1(p_vendor uuid,p_process uuid,p_model uuid,p_size uuid,p_color text,p_at timestamptz,
  out rate_per_pcs numeric,out rate_id uuid,out scope text)
 LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_policy jsonb:=erp.bd_policy_v1('LAU_DEC05');s text;v_n integer;
begin
  if v_policy is null then return;end if;
  foreach s in array array['MODEL_SIZE_COLOR','MODEL_SIZE','MODEL'] loop
    continue when not (v_policy->'scopes') @> to_jsonb(s);
    select count(*)::integer into v_n from erp.bd_laundry_scoped_rates_v1 r
    where r.vendor_id=p_vendor and r.wash_process_id=p_process and r.scope=s and r.model_id=p_model
      and (s='MODEL' or r.size_id=p_size) and (s<>'MODEL_SIZE_COLOR' or lower(btrim(r.color_name))=lower(btrim(coalesce(p_color,''))))
      and r.effective_from<=p_at and (r.effective_to is null or r.effective_to>p_at);
    if v_n>1 then raise exception 'BD_SCOPED_RATE_NOT_EXACT: lebih dari satu tarif % berlaku',s;end if;
    if v_n=1 then
      select r.rate_per_pcs,r.id,r.scope into rate_per_pcs,rate_id,scope from erp.bd_laundry_scoped_rates_v1 r
      where r.vendor_id=p_vendor and r.wash_process_id=p_process and r.scope=s and r.model_id=p_model
        and (s='MODEL' or r.size_id=p_size) and (s<>'MODEL_SIZE_COLOR' or lower(btrim(r.color_name))=lower(btrim(coalesce(p_color,''))))
        and r.effective_from<=p_at and (r.effective_to is null or r.effective_to>p_at);
      return;
    end if;
  end loop;
end;$function$;

-- ---------------------------------------------------------------- master writer (owner/admin, master.partner.manage)
CREATE OR REPLACE FUNCTION erp.bd_save_master_v1(p_action text,p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_vendor uuid;v_id uuid;v_from timestamptz;v_to timestamptz;v_reason text:=nullif(btrim(p_payload->>'reason'),'');v_rate numeric;
  v_policy jsonb;v_terms erp.bd_laundry_vendor_terms_v1%rowtype;v_units jsonb;v_x jsonb;v_status text;v_process uuid;v_model uuid;v_size uuid;
  v_color text;v_scope text;v_min numeric;
begin
  perform erp.require_owner_admin();perform erp.require_permission('master.partner.manage');
  if v_reason is null or length(v_reason)>1000 then raise exception 'BD_REASON_REQUIRED: alasan wajib diisi, maksimal 1000 karakter';end if;
  if p_action='SAVE_VENDOR_TERMS' then
    perform erp._cp3_assert_closed_json_object(p_payload,array['vendor_id','pricing_mode','pricing_unit','expected_version','reason'],
      array['vendor_id','pricing_mode','pricing_unit','minimum_charge','expected_version','reason'],'vendor terms');
    v_vendor:=erp.bd_uuid_v1(p_payload,'vendor_id',true);
    perform 1 from erp.laundry_vendors where id=v_vendor and is_active for update;
    if not found then raise exception 'BD_VENDOR_INACTIVE: vendor laundry aktif wajib dipilih';end if;
    if p_payload->>'pricing_mode' not in('RATE','PACKAGE','COMPONENTS') or p_payload->>'pricing_unit' not in('PCS','BATCH') then
      raise exception 'BD_TERMS_INVALID: pricing_mode RATE/PACKAGE/COMPONENTS dan pricing_unit PCS/BATCH';end if;
    v_units:=coalesce(erp.bd_policy_v1('LAU_DEC01')->'units','[]'::jsonb);
    if p_payload->>'pricing_unit'='BATCH' and not v_units @> '["BATCH"]' then
      perform erp.bd_require_policy_v1('LAU_DEC01','satuan borongan per batch');
      raise exception 'BD_UNIT_NOT_ALLOWED: LAU-DEC01 belum mengizinkan satuan BATCH';end if;
    if jsonb_typeof(p_payload->'minimum_charge')<>'null' then
      if not v_units @> '["MINIMUM"]' then
        perform erp.bd_require_policy_v1('LAU_DEC01','minimum charge');
        raise exception 'BD_UNIT_NOT_ALLOWED: LAU-DEC01 belum mengizinkan minimum charge';end if;
      v_min:=erp.bd_amount_v1(p_payload->'minimum_charge','minimum_charge',true);
    end if;
    select * into v_terms from erp.bd_laundry_vendor_terms_v1 where vendor_id=v_vendor for update;
    if jsonb_typeof(p_payload->'expected_version') is distinct from 'string'
      or p_payload->>'expected_version' is distinct from coalesce(v_terms.row_version::text,'0') then
      raise exception 'STALE_VERSION: ketentuan harga vendor berubah; muat ulang';end if;
    insert into erp.bd_laundry_vendor_terms_v1(vendor_id,pricing_mode,pricing_unit,minimum_charge,updated_by,reason)
    values(v_vendor,p_payload->>'pricing_mode',p_payload->>'pricing_unit',v_min,erp.current_app_user_id(),v_reason)
    on conflict(vendor_id) do update set pricing_mode=excluded.pricing_mode,pricing_unit=excluded.pricing_unit,minimum_charge=excluded.minimum_charge,
      row_version=erp.bd_laundry_vendor_terms_v1.row_version+1,updated_by=excluded.updated_by,updated_at=statement_timestamp(),reason=excluded.reason
    returning * into v_terms;
    return jsonb_build_object('vendor_id',v_vendor,'row_version',v_terms.row_version::text);
  elsif p_action='SAVE_COMPONENT' then
    perform erp._cp3_assert_closed_json_object(p_payload,array['vendor_id','component_code','component_name','is_active','reason'],
      array['id','vendor_id','component_code','component_name','is_active','reason'],'component');
    v_vendor:=erp.bd_uuid_v1(p_payload,'vendor_id',true);v_id:=erp.bd_uuid_v1(p_payload,'id',false);
    if not exists(select 1 from erp.laundry_vendors where id=v_vendor and is_active) then raise exception 'BD_VENDOR_INACTIVE: vendor laundry aktif wajib dipilih';end if;
    if jsonb_typeof(p_payload->'is_active')<>'boolean' then raise exception 'BD_FIELD_INVALID: is_active wajib boolean';end if;
    if v_id is null then
      insert into erp.bd_laundry_components_v1(vendor_id,component_code,component_name,is_active,created_by)
      values(v_vendor,btrim(p_payload->>'component_code'),btrim(p_payload->>'component_name'),(p_payload->>'is_active')::boolean,erp.current_app_user_id())
      returning id into v_id;
    else
      update erp.bd_laundry_components_v1 set component_name=btrim(p_payload->>'component_name'),is_active=(p_payload->>'is_active')::boolean
      where id=v_id and vendor_id=v_vendor and lower(component_code)=lower(btrim(p_payload->>'component_code'));
      if not found then raise exception 'BD_COMPONENT_UNKNOWN: komponen tidak dikenal untuk vendor ini (kode tidak dapat diubah)';end if;
    end if;
    return jsonb_build_object('component_id',v_id);
  elsif p_action='SAVE_COMPONENT_RATE' then
    perform erp._cp3_assert_closed_json_object(p_payload,array['component_id','rate_status','effective_from','reason'],
      array['component_id','rate_status','rate_per_pcs','effective_from','effective_to','reason'],'component rate');
    v_id:=erp.bd_uuid_v1(p_payload,'component_id',true);
    select vendor_id into v_vendor from erp.bd_laundry_components_v1 where id=v_id and is_active for update;
    if v_vendor is null then raise exception 'BD_COMPONENT_UNKNOWN: komponen aktif wajib dipilih';end if;
    v_status:=p_payload->>'rate_status';
    if v_status not in('KNOWN','UNKNOWN') then raise exception 'BD_RATE_STATUS: KNOWN atau UNKNOWN';end if;
    if v_status='KNOWN' then v_rate:=erp.bd_amount_v1(p_payload->'rate_per_pcs','rate_per_pcs',true);
    elsif p_payload ? 'rate_per_pcs' and jsonb_typeof(p_payload->'rate_per_pcs')<>'null' then
      raise exception 'BD_RATE_STATUS: harga UNKNOWN tidak membawa nominal (bukan nol)';end if;
    v_from:=erp.bd_at_v1(p_payload->>'effective_from','effective_from');
    if p_payload ? 'effective_to' and jsonb_typeof(p_payload->'effective_to')<>'null' then v_to:=erp.bd_at_v1(p_payload->>'effective_to','effective_to');end if;
    perform erp.bd_assert_version_start_v1(v_vendor,null,v_from);
    perform erp.bd_close_open_version_v1('bd_laundry_component_rates_v1','component_id',v_id,v_from,v_to);
    insert into erp.bd_laundry_component_rates_v1(component_id,rate_status,rate_per_pcs,effective_from,effective_to,reason,created_by)
    values(v_id,v_status,v_rate,v_from,v_to,v_reason,erp.current_app_user_id()) returning id into v_id;
    return jsonb_build_object('rate_id',v_id);
  elsif p_action='SAVE_PACKAGE' then
    perform erp._cp3_assert_closed_json_object(p_payload,array['vendor_id','package_code','package_name','component_ids','is_active','reason'],
      array['id','vendor_id','package_code','package_name','component_ids','is_active','reason'],'package');
    v_vendor:=erp.bd_uuid_v1(p_payload,'vendor_id',true);v_id:=erp.bd_uuid_v1(p_payload,'id',false);
    if not exists(select 1 from erp.laundry_vendors where id=v_vendor and is_active) then raise exception 'BD_VENDOR_INACTIVE: vendor laundry aktif wajib dipilih';end if;
    if jsonb_typeof(p_payload->'component_ids') is distinct from 'array' or jsonb_array_length(p_payload->'component_ids') not between 1 and 30 then
      raise exception 'BD_PACKAGE_COMPONENTS: paket memuat 1-30 komponen';end if;
    for v_x in select value from jsonb_array_elements(p_payload->'component_ids') loop
      if jsonb_typeof(v_x)<>'string' or v_x#>>'{}'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        or not exists(select 1 from erp.bd_laundry_components_v1 c where c.id=(v_x#>>'{}')::uuid and c.vendor_id=v_vendor and c.is_active) then
        raise exception 'BD_PACKAGE_COMPONENTS: komponen % bukan komponen aktif vendor ini',v_x#>>'{}';end if;
    end loop;
    if (select count(distinct value) from jsonb_array_elements(p_payload->'component_ids'))<>jsonb_array_length(p_payload->'component_ids') then
      raise exception 'BD_PACKAGE_COMPONENTS: komponen ganda dalam paket';end if;
    if jsonb_typeof(p_payload->'is_active')<>'boolean' then raise exception 'BD_FIELD_INVALID: is_active wajib boolean';end if;
    if v_id is null then
      insert into erp.bd_laundry_packages_v1(vendor_id,package_code,package_name,is_active,created_by)
      values(v_vendor,btrim(p_payload->>'package_code'),btrim(p_payload->>'package_name'),(p_payload->>'is_active')::boolean,erp.current_app_user_id())
      returning id into v_id;
    else
      -- The included components of a package that priced a delivery are that delivery's snapshot (kept on its charge lines).
      update erp.bd_laundry_packages_v1 set package_name=btrim(p_payload->>'package_name'),is_active=(p_payload->>'is_active')::boolean
      where id=v_id and vendor_id=v_vendor and lower(package_code)=lower(btrim(p_payload->>'package_code'));
      if not found then raise exception 'BD_PACKAGE_UNKNOWN: paket tidak dikenal untuk vendor ini (kode tidak dapat diubah)';end if;
      delete from erp.bd_laundry_package_components_v1 where package_id=v_id;
    end if;
    insert into erp.bd_laundry_package_components_v1(package_id,component_id)
    select v_id,(value#>>'{}')::uuid from jsonb_array_elements(p_payload->'component_ids');
    return jsonb_build_object('package_id',v_id);
  elsif p_action='SAVE_PACKAGE_RATE' then
    perform erp._cp3_assert_closed_json_object(p_payload,array['package_id','rate_per_pcs','effective_from','reason'],
      array['package_id','rate_per_pcs','effective_from','effective_to','reason'],'package rate');
    v_id:=erp.bd_uuid_v1(p_payload,'package_id',true);
    select vendor_id into v_vendor from erp.bd_laundry_packages_v1 where id=v_id and is_active for update;
    if v_vendor is null then raise exception 'BD_PACKAGE_UNKNOWN: paket aktif wajib dipilih';end if;
    v_rate:=erp.bd_amount_v1(p_payload->'rate_per_pcs','rate_per_pcs',true);
    v_from:=erp.bd_at_v1(p_payload->>'effective_from','effective_from');
    if p_payload ? 'effective_to' and jsonb_typeof(p_payload->'effective_to')<>'null' then v_to:=erp.bd_at_v1(p_payload->>'effective_to','effective_to');end if;
    perform erp.bd_assert_version_start_v1(v_vendor,null,v_from);
    perform erp.bd_close_open_version_v1('bd_laundry_package_rates_v1','package_id',v_id,v_from,v_to);
    insert into erp.bd_laundry_package_rates_v1(package_id,rate_per_pcs,effective_from,effective_to,reason,created_by)
    values(v_id,v_rate,v_from,v_to,v_reason,erp.current_app_user_id()) returning id into v_id;
    return jsonb_build_object('rate_id',v_id);
  elsif p_action='SAVE_PROCESS_RATE' then
    -- The baseline vendor x process rate (laundry_vendor_rate_versions, overlap guard FX:9681); the open version is closed at
    -- the new start, and a version never starts at or before a posted delivery of that vendor/process.
    perform erp._cp3_assert_closed_json_object(p_payload,array['vendor_id','wash_process_id','rate_per_pcs','effective_from','reason'],
      array['vendor_id','wash_process_id','rate_per_pcs','effective_from','effective_to','reason'],'process rate');
    v_vendor:=erp.bd_uuid_v1(p_payload,'vendor_id',true);v_process:=erp.bd_uuid_v1(p_payload,'wash_process_id',true);
    if not exists(select 1 from erp.laundry_vendors where id=v_vendor and is_active) or not exists(select 1 from erp.wash_processes where id=v_process and is_active) then
      raise exception 'BD_VENDOR_INACTIVE: vendor dan proses cuci aktif wajib dipilih';end if;
    v_rate:=erp.bd_amount_v1(p_payload->'rate_per_pcs','rate_per_pcs',true);
    v_from:=erp.bd_at_v1(p_payload->>'effective_from','effective_from');
    if p_payload ? 'effective_to' and jsonb_typeof(p_payload->'effective_to')<>'null' then v_to:=erp.bd_at_v1(p_payload->>'effective_to','effective_to');end if;
    perform erp.bd_assert_version_start_v1(v_vendor,v_process,v_from);
    update erp.laundry_vendor_rate_versions set effective_to=v_from
    where vendor_id=v_vendor and wash_process_id=v_process and effective_to is null and effective_from<v_from;
    insert into erp.laundry_vendor_rate_versions(vendor_id,wash_process_id,rate_per_pcs,effective_from,effective_to,notes)
    values(v_vendor,v_process,v_rate,v_from,v_to,'BD master: '||v_reason) returning id into v_id;
    return jsonb_build_object('rate_id',v_id);
  elsif p_action='SAVE_SCOPED_RATE' then
    v_policy:=erp.bd_require_policy_v1('LAU_DEC05','tarif khusus SKU/model/ukuran');
    perform erp._cp3_assert_closed_json_object(p_payload,array['vendor_id','wash_process_id','scope','model_id','rate_per_pcs','effective_from','reason'],
      array['vendor_id','wash_process_id','scope','model_id','size_id','color_name','rate_per_pcs','effective_from','effective_to','reason'],'scoped rate');
    v_vendor:=erp.bd_uuid_v1(p_payload,'vendor_id',true);v_process:=erp.bd_uuid_v1(p_payload,'wash_process_id',true);
    v_model:=erp.bd_uuid_v1(p_payload,'model_id',true);v_size:=erp.bd_uuid_v1(p_payload,'size_id',false);
    v_scope:=p_payload->>'scope';v_color:=nullif(btrim(coalesce(p_payload->>'color_name','')),'');
    if not (v_policy->'scopes') @> to_jsonb(v_scope) then raise exception 'BD_SCOPE_NOT_ALLOWED: LAU-DEC05 tidak mengizinkan cakupan %',v_scope;end if;
    if not exists(select 1 from erp.laundry_vendors where id=v_vendor and is_active) or not exists(select 1 from erp.wash_processes where id=v_process and is_active) then
      raise exception 'BD_VENDOR_INACTIVE: vendor dan proses cuci aktif wajib dipilih';end if;
    v_rate:=erp.bd_amount_v1(p_payload->'rate_per_pcs','rate_per_pcs',true);
    v_from:=erp.bd_at_v1(p_payload->>'effective_from','effective_from');
    if p_payload ? 'effective_to' and jsonb_typeof(p_payload->'effective_to')<>'null' then v_to:=erp.bd_at_v1(p_payload->>'effective_to','effective_to');end if;
    perform erp.bd_assert_version_start_v1(v_vendor,v_process,v_from);
    update erp.bd_laundry_scoped_rates_v1 set effective_to=v_from
    where vendor_id=v_vendor and wash_process_id=v_process and scope=v_scope and model_id=v_model and size_id is not distinct from v_size
      and lower(coalesce(color_name,'')) = lower(coalesce(v_color,'')) and effective_to is null and effective_from<v_from;
    if exists(select 1 from erp.bd_laundry_scoped_rates_v1 where vendor_id=v_vendor and wash_process_id=v_process and scope=v_scope and model_id=v_model
      and size_id is not distinct from v_size and lower(coalesce(color_name,''))=lower(coalesce(v_color,''))
      and effective_from<coalesce(v_to,'infinity'::timestamptz) and coalesce(effective_to,'infinity'::timestamptz)>v_from) then
      raise exception 'BD_VERSION_OVERLAP: versi tarif khusus bertumpuk';end if;
    insert into erp.bd_laundry_scoped_rates_v1(vendor_id,wash_process_id,scope,model_id,size_id,color_name,rate_per_pcs,effective_from,effective_to,
      policy_version,reason,created_by)
    values(v_vendor,v_process,v_scope,v_model,v_size,v_color,v_rate,v_from,v_to,erp.bd_policy_version_v1('LAU_DEC05'),v_reason,erp.current_app_user_id())
    returning id into v_id;
    return jsonb_build_object('rate_id',v_id);
  end if;
  raise exception 'BD_ACTION_UNKNOWN: aksi master % tidak dikenal',p_action;
end;$function$;
