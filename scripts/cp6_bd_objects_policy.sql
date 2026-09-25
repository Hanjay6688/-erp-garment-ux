-- ================================================================ BD laundry policy settings (LAU-DEC01..06)
-- Owner decision 25 Sep 2026 (annex C6 rev4 §3.1): LAU-DEC01..06 are application settings with a fail-closed default. Until
-- the owner sets a value:
--   LAU-DEC01 only the per-PCS unit (baseline) is used; batch/lump-sum and minimum charge are refused;
--   LAU-DEC02 the invoiceable quantity stays the baseline GOOD+BS returned (documented as baseline, not a final policy);
--   LAU-DEC03 invoice discount, extra, tax and rounding lines are refused;
--   LAU-DEC04 a final sale whose goods carry an unknown laundry price is refused (close stays blocked in every case);
--   LAU-DEC05 SKU/model/size scoped rates are refused;
--   LAU-DEC06 no laundry invoice is posted (service/accrual/variance mapping undecided).

create table erp.bd_policy_settings_v1(
  policy_key text primary key check(policy_key in('LAU_DEC01','LAU_DEC02','LAU_DEC03','LAU_DEC04','LAU_DEC05','LAU_DEC06')),
  status text not null default 'PENDING_POLICY_VALUE' check(status in('PENDING_POLICY_VALUE','SET')),
  value jsonb,
  version bigint not null default 1 check(version>0),
  set_by uuid,
  set_at timestamptz not null default statement_timestamp(),
  reason text not null check(length(btrim(reason))>0),
  check((status='SET')=(value is not null))
);
comment on table erp.bd_policy_settings_v1 is 'BD: owner policy settings of the laundry workflow (LAU-DEC01..06). Default PENDING_POLICY_VALUE keeps the baseline or refuses the dependent step; the owner sets or clears a value with an expected version; every change is kept in bd_policy_setting_events_v1 and every priced delivery or invoice keeps the versions it used.';
create table erp.bd_policy_setting_events_v1(
  id uuid primary key default gen_random_uuid(),
  policy_key text not null references erp.bd_policy_settings_v1(policy_key),
  version bigint not null,
  status text not null check(status in('PENDING_POLICY_VALUE','SET')),
  value jsonb,
  set_by uuid,
  set_at timestamptz not null default statement_timestamp(),
  reason text not null,
  request_id uuid,
  unique(policy_key,version)
);
insert into erp.bd_policy_settings_v1(policy_key,reason)
select k,'Default fail-closed: belum ditetapkan owner' from unnest(array['LAU_DEC01','LAU_DEC02','LAU_DEC03','LAU_DEC04','LAU_DEC05','LAU_DEC06']) k;
insert into erp.bd_policy_setting_events_v1(policy_key,version,status,value,reason)
select policy_key,version,status,value,reason from erp.bd_policy_settings_v1;

-- Execution context: the laundry BD facade marks its own transaction so the replaced laundry functions can tell a BD-priced
-- action from a direct call, like BC's context.
create table erp.bd_execution_context_v1(
  backend_pid integer not null,
  transaction_id bigint not null,
  action text not null,
  request_id uuid not null,
  pricing jsonb,
  primary key(backend_pid,transaction_id)
);

CREATE OR REPLACE FUNCTION erp.bd_context_v1()
 RETURNS erp.bd_execution_context_v1 LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select * from erp.bd_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current()
$function$;

CREATE OR REPLACE FUNCTION erp.bd_policy_v1(p_key text)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select case when status='SET' then value end from erp.bd_policy_settings_v1 where policy_key=p_key $function$;

CREATE OR REPLACE FUNCTION erp.bd_policy_version_v1(p_key text)
 RETURNS bigint LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select version from erp.bd_policy_settings_v1 where policy_key=p_key $function$;

CREATE OR REPLACE FUNCTION erp.bd_require_policy_v1(p_key text,p_what text)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v jsonb;
begin
  v:=erp.bd_policy_v1(p_key);
  if v is null then
    raise exception 'BD_POLICY_PENDING: % menunggu keputusan owner (%); langkah ini belum dapat dijalankan',p_what,replace(p_key,'_','-');
  end if;
  return v;
end;$function$;

-- An active, postable chart account of the allowed types (the setting names the account itself).
CREATE OR REPLACE FUNCTION erp.bd_policy_account_v1(p_value jsonb,p_field text,p_types text[])
 RETURNS uuid LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v uuid;
begin
  if jsonb_typeof(p_value->p_field) is distinct from 'string' or (p_value->>p_field)!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    raise exception 'BD_POLICY_VALUE: % wajib id akun',p_field;
  end if;
  select id into v from erp.chart_accounts where id=(p_value->>p_field)::uuid and is_active and is_postable and account_type=any(p_types);
  if v is null then raise exception 'BD_POLICY_VALUE: % harus akun aktif yang dapat diposting berjenis %',p_field,array_to_string(p_types,'/');end if;
  return v;
end;$function$;

-- Normalized value of one setting, or a refusal. Only values the implementation supports are accepted.
CREATE OR REPLACE FUNCTION erp.bd_check_policy_value_v1(p_key text,p_value jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_units jsonb;v_scopes jsonb;v jsonb;
begin
  if jsonb_typeof(p_value) is distinct from 'object' then raise exception 'BD_POLICY_VALUE: nilai pengaturan wajib objek';end if;
  if p_key='LAU_DEC01' then
    perform erp._cp3_assert_closed_json_object(p_value,array['units'],array['units'],'LAU-DEC01');
    if jsonb_typeof(p_value->'units') is distinct from 'array' or jsonb_array_length(p_value->'units') not between 1 and 2
      or exists(select 1 from jsonb_array_elements(p_value->'units') u where jsonb_typeof(u)<>'string' or u#>>'{}' not in('BATCH','MINIMUM'))
      or (select count(distinct u#>>'{}') from jsonb_array_elements(p_value->'units') u)<>jsonb_array_length(p_value->'units') then
      raise exception 'BD_POLICY_VALUE: LAU-DEC01 units berisi BATCH dan/atau MINIMUM (per PCS selalu berlaku)';end if;
    select jsonb_agg(x order by x) into v_units from (select distinct u#>>'{}' x from jsonb_array_elements(p_value->'units') u) s;
    return jsonb_build_object('units',v_units);
  elsif p_key='LAU_DEC02' then
    perform erp._cp3_assert_closed_json_object(p_value,array['invoice_basis'],array['invoice_basis'],'LAU-DEC02');
    if p_value->>'invoice_basis' is null or p_value->>'invoice_basis' not in('RETURNED_GOOD_BS','SENT') then
      raise exception 'BD_POLICY_VALUE: LAU-DEC02 invoice_basis RETURNED_GOOD_BS atau SENT';end if;
    return jsonb_build_object('invoice_basis',p_value->>'invoice_basis');
  elsif p_key='LAU_DEC03' then
    perform erp._cp3_assert_closed_json_object(p_value,array['discount','extra','rounding'],array['discount','extra','rounding','tax_account_id'],'LAU-DEC03');
    if p_value->>'discount' is null or p_value->>'discount' not in('ALLOWED','REFUSED')
      or p_value->>'extra' is null or p_value->>'extra' not in('ALLOWED','REFUSED')
      or p_value->>'rounding' is null or p_value->>'rounding' not in('LAST_LINE','REFUSED') then
      raise exception 'BD_POLICY_VALUE: LAU-DEC03 discount/extra ALLOWED atau REFUSED, rounding LAST_LINE atau REFUSED';end if;
    v:=jsonb_build_object('discount',p_value->>'discount','extra',p_value->>'extra','rounding',p_value->>'rounding','tax_account_id',null);
    if p_value ? 'tax_account_id' and jsonb_typeof(p_value->'tax_account_id')<>'null' then
      v:=v||jsonb_build_object('tax_account_id',erp.bd_policy_account_v1(p_value,'tax_account_id',array['ASSET']));
    end if;
    return v;
  elsif p_key='LAU_DEC04' then
    perform erp._cp3_assert_closed_json_object(p_value,array['sale_with_unknown_laundry'],array['sale_with_unknown_laundry'],'LAU-DEC04');
    if p_value->>'sale_with_unknown_laundry' is null or p_value->>'sale_with_unknown_laundry' not in('REFUSE','ALLOW_PENDING') then
      raise exception 'BD_POLICY_VALUE: LAU-DEC04 sale_with_unknown_laundry REFUSE atau ALLOW_PENDING';end if;
    return jsonb_build_object('sale_with_unknown_laundry',p_value->>'sale_with_unknown_laundry');
  elsif p_key='LAU_DEC05' then
    perform erp._cp3_assert_closed_json_object(p_value,array['scopes','fallback'],array['scopes','fallback'],'LAU-DEC05');
    if jsonb_typeof(p_value->'scopes') is distinct from 'array' or jsonb_array_length(p_value->'scopes') not between 1 and 3
      or exists(select 1 from jsonb_array_elements(p_value->'scopes') u where jsonb_typeof(u)<>'string' or u#>>'{}' not in('MODEL','MODEL_SIZE','MODEL_SIZE_COLOR'))
      or (select count(distinct u#>>'{}') from jsonb_array_elements(p_value->'scopes') u)<>jsonb_array_length(p_value->'scopes') then
      raise exception 'BD_POLICY_VALUE: LAU-DEC05 scopes berisi MODEL, MODEL_SIZE dan/atau MODEL_SIZE_COLOR';end if;
    if p_value->>'fallback' is null or p_value->>'fallback' not in('BASE_RATE','REFUSE') then
      raise exception 'BD_POLICY_VALUE: LAU-DEC05 fallback BASE_RATE atau REFUSE';end if;
    select jsonb_agg(x order by x) into v_scopes from (select distinct u#>>'{}' x from jsonb_array_elements(p_value->'scopes') u) s;
    return jsonb_build_object('scopes',v_scopes,'fallback',p_value->>'fallback');
  elsif p_key='LAU_DEC06' then
    perform erp._cp3_assert_closed_json_object(p_value,array['variance_mode','after_payment'],array['variance_mode','after_payment','variance_account_id'],'LAU-DEC06');
    if p_value->>'variance_mode' is null or p_value->>'variance_mode' not in('PRODUCT_COST','VARIANCE_ACCOUNT') then
      raise exception 'BD_POLICY_VALUE: LAU-DEC06 variance_mode PRODUCT_COST atau VARIANCE_ACCOUNT';end if;
    if p_value->>'after_payment' is null or p_value->>'after_payment' not in('REFUSE','CORRECTION_DOCUMENT') then
      raise exception 'BD_POLICY_VALUE: LAU-DEC06 after_payment REFUSE atau CORRECTION_DOCUMENT';end if;
    v:=jsonb_build_object('variance_mode',p_value->>'variance_mode','after_payment',p_value->>'after_payment','variance_account_id',null);
    if p_value->>'variance_mode'='VARIANCE_ACCOUNT' then
      v:=v||jsonb_build_object('variance_account_id',erp.bd_policy_account_v1(p_value,'variance_account_id',array['EXPENSE']));
    elsif p_value ? 'variance_account_id' and jsonb_typeof(p_value->'variance_account_id')<>'null' then
      raise exception 'BD_POLICY_VALUE: variance_account_id hanya untuk VARIANCE_ACCOUNT';
    end if;
    return v;
  end if;
  raise exception 'BD_POLICY_KEY: pengaturan % tidak dikenal',p_key;
end;$function$;

-- Owner only: set a value or clear it back to pending, against the version the owner saw.
CREATE OR REPLACE FUNCTION erp.bd_set_policy_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare s erp.bd_policy_settings_v1%rowtype;v_key text:=upper(btrim(coalesce(p_payload->>'policy_key','')));v_value jsonb;v_op text;
  v_reason text:=nullif(btrim(p_payload->>'reason'),'');
begin
  if session_user not in('postgres','supabase_admin') and erp.current_app_role() is distinct from 'OWNER' then
    raise exception 'BD_OWNER_ONLY: pengaturan kebijakan laundry hanya dapat diubah owner';
  end if;
  perform erp.require_permission('settings.erp.manage');
  perform erp._cp3_assert_closed_json_object(p_payload,array['policy_key','operation','expected_version','reason'],
    array['policy_key','operation','expected_version','reason','value'],'policy payload');
  v_op:=upper(p_payload->>'operation');
  if v_op not in('SET','CLEAR') then raise exception 'BD_POLICY_OPERATION: SET atau CLEAR';end if;
  if v_reason is null or length(v_reason)>1000 then raise exception 'BD_REASON_REQUIRED: alasan wajib diisi, maksimal 1000 karakter';end if;
  select * into s from erp.bd_policy_settings_v1 where policy_key=replace(v_key,'-','_') for update;
  if s.policy_key is null then raise exception 'BD_POLICY_KEY: pengaturan % tidak dikenal',v_key;end if;
  if jsonb_typeof(p_payload->'expected_version') is distinct from 'string' or p_payload->>'expected_version' is distinct from s.version::text then
    raise exception 'STALE_VERSION: pengaturan % berubah; muat ulang',s.policy_key;end if;
  if v_op='SET' then v_value:=erp.bd_check_policy_value_v1(s.policy_key,p_payload->'value');
  elsif p_payload ? 'value' then raise exception 'BD_POLICY_VALUE: CLEAR tidak membawa nilai';end if;
  update erp.bd_policy_settings_v1 set status=case when v_op='SET' then 'SET' else 'PENDING_POLICY_VALUE' end,value=v_value,version=version+1,
    set_by=erp.current_app_user_id(),set_at=statement_timestamp(),reason=v_reason where policy_key=s.policy_key returning * into s;
  insert into erp.bd_policy_setting_events_v1(policy_key,version,status,value,set_by,reason,request_id)
  values(s.policy_key,s.version,s.status,s.value,s.set_by,v_reason,p_request);
  return jsonb_build_object('policy_key',s.policy_key,'status',s.status,'value',s.value,'version',s.version::text);
end;$function$;

-- Small shared parsers.
CREATE OR REPLACE FUNCTION erp.bd_uuid_v1(p_payload jsonb,p_field text,p_required boolean)
 RETURNS uuid LANGUAGE plpgsql IMMUTABLE SET search_path TO ''
AS $function$
begin
  if p_payload->p_field is null or jsonb_typeof(p_payload->p_field)='null' then
    if p_required then raise exception 'BD_FIELD_REQUIRED: % wajib diisi',p_field;end if;
    return null;
  end if;
  if jsonb_typeof(p_payload->p_field)<>'string' or (p_payload->>p_field)!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    raise exception 'BD_FIELD_INVALID: % wajib UUID',p_field;
  end if;
  return (p_payload->>p_field)::uuid;
end;$function$;

-- A money text with exactly two decimals, >= 0 (or > 0), never a float. Every BD price is > 0: a zero price would need an explicit
-- free policy (LAU-T08), and none exists; a genuinely unknown price is UNKNOWN, never 0.
CREATE OR REPLACE FUNCTION erp.bd_amount_v1(p_value jsonb,p_field text,p_positive boolean)
 RETURNS numeric LANGUAGE plpgsql IMMUTABLE SET search_path TO ''
AS $function$
declare v numeric;
begin
  if jsonb_typeof(p_value) is distinct from 'string' or p_value#>>'{}'!~'^(0|[1-9][0-9]{0,15})\.[0-9]{2}$' then
    raise exception 'BD_AMOUNT_INVALID: % wajib nominal teks dengan tepat dua desimal',p_field;
  end if;
  v:=(p_value#>>'{}')::numeric;
  if p_positive and v<=0 then raise exception 'BD_AMOUNT_INVALID: % harus lebih dari 0',p_field;end if;
  return v;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bd_qty_v1(p_value jsonb,p_field text)
 RETURNS integer LANGUAGE plpgsql IMMUTABLE SET search_path TO ''
AS $function$
begin
  if jsonb_typeof(p_value) is distinct from 'number' or p_value#>>'{}'!~'^[1-9][0-9]{0,8}$' then
    raise exception 'BD_QTY_INVALID: % wajib bilangan bulat PCS > 0',p_field;
  end if;
  return (p_value#>>'{}')::integer;
end;$function$;

CREATE OR REPLACE FUNCTION erp.bd_at_v1(p_value text,p_field text)
 RETURNS timestamptz LANGUAGE plpgsql STABLE SET search_path TO ''
AS $function$
begin
  if p_value is null or p_value!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}(:\d{2})?)$' then
    raise exception 'BD_TIME_INVALID: % wajib waktu bertimezone',p_field;
  end if;
  return p_value::timestamptz;
exception when data_exception then raise exception 'BD_TIME_INVALID: % wajib waktu bertimezone',p_field;
end;$function$;
