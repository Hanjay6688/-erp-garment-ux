-- ================================================================ BC policy settings, zones, execution context
-- Owner decision 25 Sep 2026: policy rows ACC-DEC01, ACC-DEC03..07 and ERP-DEC02 are application settings with a fail-closed
-- default; runtime acceptance stays case evidence. Until the owner sets a value every dependent financial step is refused
-- with BC_POLICY_PENDING, while the physical steps that do not depend on it (receipt, inspection, custody) stay possible.

create table erp.bc_policy_settings_v1(
  policy_key text primary key check(policy_key in('ACC_DEC01','ACC_DEC03','ACC_DEC04','ACC_DEC05','ACC_DEC06','ACC_DEC07','ERP_DEC02')),
  status text not null default 'PENDING_POLICY_VALUE' check(status in('PENDING_POLICY_VALUE','SET')),
  value jsonb,
  version bigint not null default 1 check(version>0),
  set_by uuid,
  set_at timestamptz not null default statement_timestamp(),
  reason text not null check(length(btrim(reason))>0),
  check((status='SET')=(value is not null))
);
comment on table erp.bc_policy_settings_v1 is 'BC: owner policy settings of the accessory service/return workflow (ACC-DEC01, ACC-DEC03..07, ERP-DEC02). Default PENDING_POLICY_VALUE refuses every dependent financial step; the owner sets or clears a value with an expected version; every change is kept in bc_policy_setting_events_v1 and every document keeps the versions it used.';
create table erp.bc_policy_setting_events_v1(
  id uuid primary key default gen_random_uuid(),
  policy_key text not null references erp.bc_policy_settings_v1(policy_key),
  version bigint not null,
  status text not null check(status in('PENDING_POLICY_VALUE','SET')),
  value jsonb,
  set_by uuid,
  set_at timestamptz not null default statement_timestamp(),
  reason text not null,
  request_id uuid,
  unique(policy_key,version)
);
insert into erp.bc_policy_settings_v1(policy_key,reason)
select k,'Default fail-closed: belum ditetapkan owner' from unnest(array['ACC_DEC01','ACC_DEC03','ACC_DEC04','ACC_DEC05','ACC_DEC06','ACC_DEC07','ERP_DEC02']) k;
insert into erp.bc_policy_setting_events_v1(policy_key,version,status,value,reason)
select policy_key,version,status,value,reason from erp.bc_policy_settings_v1;

-- Zones: a service post, the inspection area and the damaged area are active raw-material warehouse locations registered
-- here (M:5018 option "reuse lokasi gudang bahan dengan sublokasi/tujuan operasional yang sah"); one ledger, the condition is
-- the location. Stock at a zone moves only through the BC facade (or an opening count at import), never through the note,
-- the generic transfer or adjustment.
create table erp.bc_accessory_zones_v1(
  location_id uuid primary key references erp.locations(id),
  zone_kind text not null check(zone_kind in('SERVICE_POST','INSPECTION','DAMAGED')),
  reason text not null check(length(btrim(reason))>0),
  created_by uuid,
  created_at timestamptz not null default statement_timestamp()
);
comment on table erp.bc_accessory_zones_v1 is 'BC: raw-material warehouse locations that are a service post (company stock ready to use at the post), the inspection area (waiting for inspection) or the damaged area (damaged, waiting for disposition). Stock there is not issueable by the mandor note and moves only through erp.save_accessory_service_action_v1.';

create table erp.bc_execution_context_v1(
  backend_pid integer not null,
  transaction_id bigint not null,
  actor_key text not null,
  primary key(backend_pid,transaction_id)
);
comment on table erp.bc_execution_context_v1 is 'BC: marks the transaction of one BC facade command so its native transfers, adjustments and reversals may touch zone stock; the row is removed at the end of the command (rolled back with it on error).';

do $rls$
declare t text;
begin
  foreach t in array array['bc_policy_settings_v1','bc_policy_setting_events_v1','bc_accessory_zones_v1','bc_execution_context_v1'] loop
    execute format('alter table erp.%I enable row level security',t);
    execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
  end loop;
end $rls$;

CREATE OR REPLACE FUNCTION erp.bc_enter_context_v1()
 RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$
  insert into erp.bc_execution_context_v1(backend_pid,transaction_id,actor_key)
  values(pg_backend_pid(),txid_current(),erp._idempotency_actor_key()) on conflict do nothing
$function$;

CREATE OR REPLACE FUNCTION erp.bc_leave_context_v1()
 RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$
  delete from erp.bc_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current()
$function$;

CREATE OR REPLACE FUNCTION erp.bc_in_context_v1()
 RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select exists(select 1 from erp.bc_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current())
$function$;

CREATE OR REPLACE FUNCTION erp.bc_zone_kind_v1(p_location uuid)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select zone_kind from erp.bc_accessory_zones_v1 where location_id=p_location $function$;

-- ---------------------------------------------------------------- policy values
CREATE OR REPLACE FUNCTION erp.bc_policy_v1(p_key text)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select case when status='SET' then value end from erp.bc_policy_settings_v1 where policy_key=p_key $function$;

CREATE OR REPLACE FUNCTION erp.bc_policy_version_v1(p_key text)
 RETURNS bigint LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select version from erp.bc_policy_settings_v1 where policy_key=p_key $function$;

CREATE OR REPLACE FUNCTION erp.bc_require_policy_v1(p_key text,p_what text)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb;
begin
  v:=erp.bc_policy_v1(p_key);
  if v is null then
    raise exception 'BC_POLICY_PENDING: % menunggu keputusan owner (%); langkah finansial ini belum dapat diposting',p_what,replace(p_key,'_','-');
  end if;
  return v;
end;$function$;

-- An active, postable chart account of the allowed types (a setting names the account itself, not a free mapping).
CREATE OR REPLACE FUNCTION erp.bc_policy_account_v1(p_value jsonb,p_field text,p_types text[])
 RETURNS uuid LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v uuid;
begin
  if jsonb_typeof(p_value->p_field) is distinct from 'string' or (p_value->>p_field)!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    raise exception 'BC_POLICY_VALUE: % wajib id akun',p_field;
  end if;
  select id into v from erp.chart_accounts where id=(p_value->>p_field)::uuid and is_active and is_postable and account_type=any(p_types);
  if v is null then raise exception 'BC_POLICY_VALUE: % harus akun aktif yang dapat diposting berjenis %',p_field,array_to_string(p_types,'/');end if;
  return v;
end;$function$;

-- Normalized value of one setting, or a refusal. Only values the implementation actually supports are accepted.
CREATE OR REPLACE FUNCTION erp.bc_check_policy_value_v1(p_key text,p_value jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb;v_x jsonb;k text;v_ids jsonb:='[]'::jsonb;v_zone jsonb:='{}'::jsonb;v_users jsonb;u text;
begin
  if jsonb_typeof(p_value) is distinct from 'object' then raise exception 'BC_POLICY_VALUE: nilai pengaturan wajib objek';end if;
  if p_key='ACC_DEC01' then
    perform erp._cp3_assert_closed_json_object(p_value,array['mode'],array['mode'],'ACC-DEC01');
    if p_value->>'mode' is distinct from 'BOTH_REAL_TIMELINES' then raise exception 'BC_POLICY_VALUE: ACC-DEC01 hanya BOTH_REAL_TIMELINES';end if;
    return jsonb_build_object('mode','BOTH_REAL_TIMELINES');
  elsif p_key='ACC_DEC03' then
    perform erp._cp3_assert_closed_json_object(p_value,array['credit_account_id','unit_value_cap'],array['credit_account_id','unit_value_cap'],'ACC-DEC03');
    if p_value->>'unit_value_cap' is null or p_value->>'unit_value_cap' not in('MOVING_AVERAGE','NONE') then
      raise exception 'BC_POLICY_VALUE: ACC-DEC03 unit_value_cap MOVING_AVERAGE atau NONE';end if;
    return jsonb_build_object('credit_account_id',erp.bc_policy_account_v1(p_value,'credit_account_id',array['REVENUE','EXPENSE']),
      'unit_value_cap',p_value->>'unit_value_cap');
  elsif p_key='ACC_DEC04' then
    perform erp._cp3_assert_closed_json_object(p_value,array[]::text[],array['CUSTOMER_SERVICE_account_id','OWN_FG_REPAIR_account_id'],'ACC-DEC04');
    v:='{}'::jsonb;
    foreach k in array array['CUSTOMER_SERVICE_account_id','OWN_FG_REPAIR_account_id'] loop
      if p_value ? k and jsonb_typeof(p_value->k)<>'null' then v:=v||jsonb_build_object(k,erp.bc_policy_account_v1(p_value,k,array['EXPENSE']));end if;
    end loop;
    if v='{}'::jsonb then raise exception 'BC_POLICY_VALUE: ACC-DEC04 memerlukan paling sedikit satu akun tujuan';end if;
    return v;
  elsif p_key='ACC_DEC05' then
    perform erp._cp3_assert_closed_json_object(p_value,array['mode','credit_conditions'],array['mode','credit_conditions'],'ACC-DEC05');
    if p_value->>'mode' is null or p_value->>'mode' not in('CREDIT_UNPAID_ONLY','CREDIT_THEN_CARRY','CREDIT_THEN_REFUND') then
      raise exception 'BC_POLICY_VALUE: ACC-DEC05 mode CREDIT_UNPAID_ONLY, CREDIT_THEN_CARRY atau CREDIT_THEN_REFUND';end if;
    if jsonb_typeof(p_value->'credit_conditions') is distinct from 'array' or jsonb_array_length(p_value->'credit_conditions') not between 1 and 2
      or exists(select 1 from jsonb_array_elements(p_value->'credit_conditions') c where c#>>'{}' not in('USABLE','DAMAGED') or jsonb_typeof(c)<>'string')
      or (select count(distinct c#>>'{}') from jsonb_array_elements(p_value->'credit_conditions') c)<>jsonb_array_length(p_value->'credit_conditions') then
      raise exception 'BC_POLICY_VALUE: ACC-DEC05 credit_conditions berisi USABLE dan/atau DAMAGED';end if;
    return jsonb_build_object('mode',p_value->>'mode','credit_conditions',
      (select jsonb_agg(c order by c) from (select distinct y#>>'{}' c from jsonb_array_elements(p_value->'credit_conditions') y) s));
  elsif p_key='ACC_DEC06' then
    perform erp._cp3_assert_closed_json_object(p_value,array['mode','gain_account_id','loss_account_id'],array['mode','gain_account_id','loss_account_id'],'ACC-DEC06');
    if p_value->>'mode' is distinct from 'NOTE_NEAREST_RUPIAH' then raise exception 'BC_POLICY_VALUE: ACC-DEC06 mode NOTE_NEAREST_RUPIAH';end if;
    return jsonb_build_object('mode','NOTE_NEAREST_RUPIAH','gain_account_id',erp.bc_policy_account_v1(p_value,'gain_account_id',array['REVENUE','EXPENSE']),
      'loss_account_id',erp.bc_policy_account_v1(p_value,'loss_account_id',array['EXPENSE']));
  elsif p_key='ACC_DEC07' then
    -- Owner decision no. 6 (26 Sep 2026): "gausah ada approval dulu sementara karena belum relevan" is approval NONE, an explicit
    -- value that can be changed in the app later; a threshold (owner_approval_above) is the other form. Pending stays fail closed.
    perform erp._cp3_assert_closed_json_object(p_value,array[]::text[],array['approval','owner_approval_above','zone_users'],'ACC-DEC07');
    if (p_value ? 'approval')=(p_value ? 'owner_approval_above') then
      raise exception 'BC_POLICY_VALUE: ACC-DEC07 diisi salah satu: approval NONE (tanpa persetujuan) atau owner_approval_above (batas nominal)';end if;
    if p_value ? 'approval' and p_value->'approval' is distinct from '"NONE"'::jsonb then
      raise exception 'BC_POLICY_VALUE: ACC-DEC07 approval hanya NONE';end if;
    if p_value ? 'owner_approval_above' then
      if jsonb_typeof(p_value->'owner_approval_above') is distinct from 'string' then raise exception 'BC_POLICY_VALUE: ACC-DEC07 owner_approval_above wajib nominal teks';end if;
      perform erp.bb_parse_amount_v1(p_value->>'owner_approval_above','owner_approval_above',true);
    end if;
    if p_value ? 'zone_users' then
      if jsonb_typeof(p_value->'zone_users') is distinct from 'object' then raise exception 'BC_POLICY_VALUE: zone_users wajib objek lokasi -> daftar pengguna';end if;
      for k,v_users in select key,value from jsonb_each(p_value->'zone_users') loop
        if k!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' or not exists(select 1 from erp.bc_accessory_zones_v1 where location_id=k::uuid) then
          raise exception 'BC_POLICY_VALUE: % bukan zona aksesori terdaftar',k;end if;
        if jsonb_typeof(v_users) is distinct from 'array' or jsonb_array_length(v_users) not between 1 and 50 then
          raise exception 'BC_POLICY_VALUE: daftar pengguna zona % tidak valid',k;end if;
        for u in select jsonb_array_elements_text(v_users) loop
          if u!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' or not exists(select 1 from erp.app_users where id=u::uuid and is_active) then
            raise exception 'BC_POLICY_VALUE: pengguna % tidak aktif atau tidak dikenal',u;end if;
        end loop;
        v_zone:=v_zone||jsonb_build_object(k,(select jsonb_agg(distinct y order by y) from jsonb_array_elements_text(v_users) y));
      end loop;
    end if;
    if p_value ? 'approval' then return jsonb_build_object('approval','NONE','zone_users',v_zone);end if;
    return jsonb_build_object('owner_approval_above',erp.bb_parse_amount_v1(p_value->>'owner_approval_above','owner_approval_above',true)::numeric(20,2)::text,
      'zone_users',v_zone);
  elsif p_key='ERP_DEC02' then
    perform erp._cp3_assert_closed_json_object(p_value,array['special_free_category_ids'],array['special_free_category_ids'],'ERP-DEC02');
    if jsonb_typeof(p_value->'special_free_category_ids') is distinct from 'array' or jsonb_array_length(p_value->'special_free_category_ids')>50 then
      raise exception 'BC_POLICY_VALUE: ERP-DEC02 special_free_category_ids wajib daftar kategori';end if;
    for v_x in select value from jsonb_array_elements(p_value->'special_free_category_ids') loop
      if jsonb_typeof(v_x) is distinct from 'string' or v_x#>>'{}'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        or not exists(select 1 from erp.accessory_categories where id=(v_x#>>'{}')::uuid and is_active) then
        raise exception 'BC_POLICY_VALUE: kategori gratis % tidak aktif atau tidak dikenal',v_x#>>'{}';end if;
      if not v_ids @> jsonb_build_array(v_x) then v_ids:=v_ids||jsonb_build_array(v_x);end if;
    end loop;
    return jsonb_build_object('special_free_category_ids',(select coalesce(jsonb_agg(y order by y),'[]'::jsonb) from jsonb_array_elements_text(v_ids) y));
  end if;
  raise exception 'BC_POLICY_KEY: pengaturan % tidak dikenal',p_key;
end;$function$;

-- Owner only: set a value or clear it back to pending, against the version the owner saw.
CREATE OR REPLACE FUNCTION erp.bc_set_policy_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare s erp.bc_policy_settings_v1%rowtype;v_key text:=upper(btrim(coalesce(p_payload->>'policy_key','')));v_value jsonb;v_op text;
  v_reason text:=nullif(btrim(p_payload->>'reason'),'');
begin
  if session_user not in('postgres','supabase_admin') and erp.current_app_role() is distinct from 'OWNER' then
    raise exception 'BC_OWNER_ONLY: pengaturan kebijakan hanya dapat diubah owner';
  end if;
  perform erp.require_permission('settings.erp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['policy_key','operation','expected_version','reason'],
    array['policy_key','operation','expected_version','reason','value'],'policy payload');
  v_op:=upper(p_payload->>'operation');
  if v_op not in('SET','CLEAR') then raise exception 'BC_POLICY_OPERATION: SET atau CLEAR';end if;
  if v_reason is null or length(v_reason)>1000 then raise exception 'BC_REASON_REQUIRED: alasan wajib diisi, maksimal 1000 karakter';end if;
  select * into s from erp.bc_policy_settings_v1 where policy_key=replace(v_key,'-','_') for update;
  if s.policy_key is null then raise exception 'BC_POLICY_KEY: pengaturan % tidak dikenal',v_key;end if;
  if jsonb_typeof(p_payload->'expected_version') is distinct from 'string' or p_payload->>'expected_version' is distinct from s.version::text then
    raise exception 'STALE_VERSION: pengaturan % berubah; muat ulang',s.policy_key;end if;
  if v_op='SET' then v_value:=erp.bc_check_policy_value_v1(s.policy_key,p_payload->'value');
  elsif p_payload ? 'value' then raise exception 'BC_POLICY_VALUE: CLEAR tidak membawa nilai';end if;
  update erp.bc_policy_settings_v1 set status=case when v_op='SET' then 'SET' else 'PENDING_POLICY_VALUE' end,value=v_value,version=version+1,
    set_by=erp.current_app_user_id(),set_at=statement_timestamp(),reason=v_reason where policy_key=s.policy_key returning * into s;
  insert into erp.bc_policy_setting_events_v1(policy_key,version,status,value,set_by,reason,request_id)
  values(s.policy_key,s.version,s.status,s.value,s.set_by,v_reason,p_request);
  return jsonb_build_object('policy_key',s.policy_key,'status',s.status,'value',s.value,'version',s.version::text);
end;$function$;

-- ---------------------------------------------------------------- zones
CREATE OR REPLACE FUNCTION erp.bc_register_zone_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_kind text:=upper(coalesce(p_payload->>'zone_kind',''));v_code text:=btrim(coalesce(p_payload->>'location_code',''));
  v_name text:=btrim(coalesce(p_payload->>'location_name',''));v_id uuid;v_reason text:=nullif(btrim(p_payload->>'reason'),'');
begin
  perform erp.require_owner_admin();perform erp.require_permission('master.location.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['zone_kind','location_code','location_name','reason'],
    array['zone_kind','location_code','location_name','reason'],'zone payload');
  if v_kind not in('SERVICE_POST','INSPECTION','DAMAGED') then raise exception 'BC_ZONE_KIND: SERVICE_POST, INSPECTION atau DAMAGED';end if;
  if v_code!~'^[A-Za-z0-9][A-Za-z0-9._-]{1,39}$' or length(v_name) not between 2 and 120 then
    raise exception 'BC_ZONE_IDENTITY: kode lokasi 2-40 huruf/angka dan nama 2-120 karakter';end if;
  if v_reason is null then raise exception 'BC_REASON_REQUIRED: alasan wajib diisi';end if;
  if exists(select 1 from erp.locations where lower(location_code)=lower(v_code)) then raise exception 'BC_ZONE_IDENTITY: kode lokasi sudah dipakai';end if;
  insert into erp.locations(id,location_code,location_name,location_type,is_active)
  values(p_request,v_code,v_name,'RAW_MATERIAL_WAREHOUSE',true) returning id into v_id;
  insert into erp.bc_accessory_zones_v1(location_id,zone_kind,reason,created_by) values(v_id,v_kind,v_reason,erp.current_app_user_id());
  return jsonb_build_object('location_id',v_id,'zone_kind',v_kind,'location_code',v_code);
end;$function$;

-- Zone stock moves only through the BC facade; an opening count may put accessory stock at a zone (ALL-C03).
CREATE OR REPLACE FUNCTION erp.bc_guard_zone_movement_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_kind text;
begin
  select zone_kind into v_kind from erp.bc_accessory_zones_v1 where location_id=new.location_id;
  if v_kind is null then return new;end if;
  if (select material_type from erp.materials where id=new.material_id) is distinct from 'ACCESSORY' then
    raise exception 'BC_ZONE_ACCESSORY_ONLY: zona pos servis/pemeriksaan/rusak hanya untuk aksesori';end if;
  if erp.bc_in_context_v1() then return new;end if;
  if new.movement_type='OPENING' and new.qty_signed>0 then return new;end if;
  if new.movement_type='REVERSAL' and exists(select 1 from erp.material_stock_movements o where o.id=new.reversal_of_id and o.movement_type='OPENING') then
    return new;end if;
  raise exception 'BC_ZONE_NATIVE_REFUSED: stok di % hanya bergerak lewat Pemakaian & Pengembalian Aksesori',
    case v_kind when 'SERVICE_POST' then 'pos servis' when 'INSPECTION' then 'area pemeriksaan' else 'area rusak' end;
end;$function$;
create trigger trg_bc_zone_movement before insert on erp.material_stock_movements
  for each row execute function erp.bc_guard_zone_movement_v1();

-- A registered zone keeps its kind and stays a raw-material warehouse; it cannot be deactivated while it holds stock.
CREATE OR REPLACE FUNCTION erp.bc_guard_zone_location_v1()
 RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
begin
  if tg_table_name='bc_accessory_zones_v1' then
    if tg_op='DELETE' or new.location_id<>old.location_id or new.zone_kind<>old.zone_kind then
      raise exception 'BC_ZONE_IMMUTABLE: jenis zona tetap; buat zona baru bila perlu';end if;
    return new;
  end if;
  if exists(select 1 from erp.bc_accessory_zones_v1 where location_id=old.location_id) and (new.location_type is distinct from old.location_type
     or (old.is_active and not new.is_active and exists(select 1 from erp.material_stock_movements m where m.location_id=old.id
       group by m.material_id having sum(m.qty_signed)<>0))) then
    raise exception 'BC_ZONE_IMMUTABLE: zona tetap gudang bahan dan tidak dinonaktifkan selama masih ada stok';
  end if;
  return new;
end;$function$;
create trigger trg_bc_zone_row before update or delete on erp.bc_accessory_zones_v1
  for each row execute function erp.bc_guard_zone_location_v1();
create trigger trg_bc_zone_location before update on erp.locations
  for each row execute function erp.bc_guard_zone_location_v1();
