-- U adversarial oracle: canonical Jakarta dates for material accounting and
-- owner reporting. Requires the isolated CP6 seed plus g_* and t_* helpers.
create function pg_temp.u_adjustment(p_purchase uuid,p_physical_at timestamptz)
returns uuid language plpgsql as $$
declare v uuid;begin
 insert into erp.material_adjustments(
  adjustment_number,physical_at,location_id,reason_code,notes,status
 )
 select 'U-ADJ-'||gen_random_uuid(),p_physical_at,location_id,
  'COUNT_CORRECTION','U canonical business-date probe','DRAFT'
 from erp.material_purchase_headers where id=p_purchase returning id into v;
 insert into erp.material_adjustment_items(
  adjustment_id,material_id,roll_id,qty_signed
 )
 select v,i.material_id,r.id,-1
 from erp.material_purchase_items i
 join erp.material_rolls r on r.purchase_item_id=i.id
 where i.purchase_id=p_purchase order by r.id limit 1;
 return v;
end$$;

create function pg_temp.u_post(p_adjustment uuid) returns jsonb
language plpgsql as $$
declare r jsonb;v bigint;begin
 select row_version into v from erp.material_adjustments where id=p_adjustment;
 begin
  execute 'set local role authenticated';
  r:=erp.post_material_adjustment_v2(
    p_adjustment,gen_random_uuid(),v,'U authenticated material posting probe'
  );
  execute 'reset role';
 exception when others then
  execute 'reset role';raise;
 end;
 return r;
end$$;

create function pg_temp.u_reverse(p_adjustment uuid) returns jsonb
language plpgsql as $$
declare r jsonb;v bigint;begin
 select row_version into v from erp.material_adjustments where id=p_adjustment;
 begin
  execute 'set local role authenticated';
  r:=erp.reverse_material_adjustment_v2(
    p_adjustment,'U authenticated material reversal probe',gen_random_uuid(),v
  );
  execute 'reset role';
 exception when others then
  execute 'reset role';raise;
 end;
 return r;
end$$;

create function pg_temp.u_report(p_from date,p_to date,p_as_of date)
returns jsonb language plpgsql as $$
declare r jsonb;begin
 begin
  execute 'set local role authenticated';
  r:=erp.get_owner_financial_snapshot_v2(p_from,p_to,p_as_of);
  execute 'reset role';
 exception when others then
  execute 'reset role';raise;
 end;
 return r;
end$$;

create function pg_temp.u_report_default(p_from date,p_to date)
returns jsonb language plpgsql as $$
declare r jsonb;begin
 begin
  execute 'set local role authenticated';
  r:=erp.get_owner_financial_snapshot_v2(p_from,p_to);
  execute 'reset role';
 exception when others then
  execute 'reset role';raise;
 end;
 return r;
end$$;

create function pg_temp.u_day_zone() returns jsonb language plpgsql as $$
declare z text;d date:=erp._cp3_business_date(current_timestamp);begin
 foreach z in array array['Etc/GMT+12','Pacific/Kiritimati'] loop
  perform set_config('TimeZone',z,true);
  if current_date<>d then
   return jsonb_build_object(
    'zone',z,'canonical_day',d,'session_day',current_date,
    'lagging',current_date<d
   );
  end if;
 end loop;
 raise exception 'U_NO_DISTINCT_REAL_TIMEZONE';
end$$;

create function pg_temp.u_case(p_case text,p_fixed boolean) returns jsonb
language plpgsql as $$
declare
 p uuid;a uuid;j uuid;v_response jsonb;v_day jsonb;v_boundary jsonb;
 v_at timestamptz:='2026-09-13 00:30:00+07';v_canonical date;
 v_actual date;v_session date;v_refused boolean:=false;v_message text;v_state text;
 v_before_utc numeric;v_before_jakarta numeric;v_after_utc numeric;v_after_jakarta numeric;
 v_before_utc_next numeric;v_before_jakarta_next numeric;
 v_after_utc_next numeric;v_after_jakarta_next numeric;
 v_delta_utc numeric;v_delta_jakarta numeric;v_delta_utc_next numeric;v_delta_jakarta_next numeric;
 v_period date;v_result jsonb:='{}';v_unsafe boolean:=false;
begin
 v_canonical:=erp._cp3_business_date(v_at);
 if p_case in('MATERIAL_ORIGINAL_UTC','MATERIAL_ORIGINAL_JAKARTA') then
  p:=pg_temp.t_purchase(pg_temp.t_clone_material(),array[2]::numeric[],10,true);
  a:=pg_temp.u_adjustment(p,v_at);
  perform set_config('TimeZone',case when p_case='MATERIAL_ORIGINAL_UTC'
    then 'UTC' else 'Asia/Jakarta' end,true);
  v_session:=v_at::date;
  v_response:=pg_temp.u_post(a);
  select economic_date into v_actual from erp.journal_entries
   where source_type='MATERIAL_ADJUSTMENT' and source_id=a and status='POSTED';
  if p_fixed and v_actual is distinct from v_canonical then
   raise exception 'U_MATERIAL_ORIGINAL_DATE_NOT_CANONICAL: %/%',v_actual,v_canonical;
  elsif not p_fixed and p_case='MATERIAL_ORIGINAL_UTC'
      and (v_actual is distinct from v_session or v_actual=v_canonical) then
   raise exception 'U_T_ORIGINAL_DATE_COUNTEREXAMPLE_MISSING: %/%/%',
    v_actual,v_session,v_canonical;
  elsif not p_fixed and p_case='MATERIAL_ORIGINAL_JAKARTA'
      and v_actual is distinct from v_canonical then
   raise exception 'U_JAKARTA_ORIGINAL_CONTROL_FAILED: %/%',v_actual,v_canonical;
  end if;
  v_unsafe:=v_actual is distinct from v_canonical;
  v_result:=jsonb_build_object(
   'adjustment_id',a,'rpc_response',v_response,'zone',current_setting('TimeZone'),
   'physical_at',v_at,'session_cast_date',v_session,
   'canonical_date',v_canonical,'journal_date',v_actual
  );
 elsif p_case='MATERIAL_REVERSAL_REAL_ZONE' then
  p:=pg_temp.t_purchase(pg_temp.t_clone_material(),array[2]::numeric[],10,true);
  a:=pg_temp.u_adjustment(p,'2026-09-02 12:00:00+07');
  perform set_config('TimeZone','Asia/Jakarta',true);
  perform pg_temp.u_post(a);
  select id into j from erp.journal_entries
   where source_type='MATERIAL_ADJUSTMENT' and source_id=a and status='POSTED';
  v_day:=pg_temp.u_day_zone();v_boundary:=pg_temp.t_boundary();
  begin
   v_response:=pg_temp.u_reverse(a);
  exception when others then
   get stacked diagnostics v_message=message_text,v_state=returned_sqlstate;
   v_refused:=true;
  end;
  select economic_date into v_actual from erp.journal_entries
   where source_type='JOURNAL_REVERSAL' and reversal_of_id=j and status='POSTED';
  if p_fixed and (v_refused or v_actual is distinct from
      (v_day->>'canonical_day')::date) then
   raise exception 'U_MATERIAL_REVERSAL_NOT_CANONICAL: refused %, date %, day %',
    v_refused,v_actual,v_day;
  elsif not p_fixed and (v_day->>'lagging')::boolean and
      (v_refused or v_actual is distinct from (v_day->>'session_day')::date
       or v_actual=(v_day->>'canonical_day')::date) then
   raise exception 'U_T_LAGGING_REVERSAL_COUNTEREXAMPLE_MISSING: %/%',v_actual,v_day;
  elsif not p_fixed and not (v_day->>'lagging')::boolean and not v_refused then
   raise exception 'U_T_LEADING_REVERSAL_REFUSAL_MISSING: %/%',v_actual,v_day;
  end if;
  if v_refused and pg_temp.t_boundary() is distinct from v_boundary then
   raise exception 'U_T_REVERSAL_REFUSAL_NOT_ATOMIC';
  end if;
  v_unsafe:=not v_refused and v_actual is distinct from
    (v_day->>'canonical_day')::date;
  v_result:=jsonb_build_object(
   'adjustment_id',a,'original_journal_id',j,'days',v_day,
   'refused',v_refused,'sqlstate',v_state,'message',v_message,
   'reversal_journal_date',v_actual,'rpc_response',v_response,
   'atomic_refusal',v_refused
  );
 elsif p_case='OWNER_WIP_CUTOFF' then
  perform set_config('TimeZone','UTC',true);
  v_before_utc:=(pg_temp.u_report('2026-09-12','2026-09-12','2026-09-12')
    #>>'{quality,laundry_outstanding_pcs}')::numeric;
  v_before_utc_next:=(pg_temp.u_report('2026-09-13','2026-09-13','2026-09-13')
    #>>'{quality,laundry_outstanding_pcs}')::numeric;
  perform set_config('TimeZone','Asia/Jakarta',true);
  v_before_jakarta:=(pg_temp.u_report('2026-09-12','2026-09-12','2026-09-12')
    #>>'{quality,laundry_outstanding_pcs}')::numeric;
  v_before_jakarta_next:=(pg_temp.u_report('2026-09-13','2026-09-13','2026-09-13')
    #>>'{quality,laundry_outstanding_pcs}')::numeric;
  perform pg_temp.g_dispatch(1,v_at);
  perform set_config('TimeZone','UTC',true);
  v_after_utc:=(pg_temp.u_report('2026-09-12','2026-09-12','2026-09-12')
    #>>'{quality,laundry_outstanding_pcs}')::numeric;
  v_after_utc_next:=(pg_temp.u_report('2026-09-13','2026-09-13','2026-09-13')
    #>>'{quality,laundry_outstanding_pcs}')::numeric;
  perform set_config('TimeZone','Asia/Jakarta',true);
  v_after_jakarta:=(pg_temp.u_report('2026-09-12','2026-09-12','2026-09-12')
    #>>'{quality,laundry_outstanding_pcs}')::numeric;
  v_after_jakarta_next:=(pg_temp.u_report('2026-09-13','2026-09-13','2026-09-13')
    #>>'{quality,laundry_outstanding_pcs}')::numeric;
  v_delta_utc:=v_after_utc-v_before_utc;
  v_delta_jakarta:=v_after_jakarta-v_before_jakarta;
  v_delta_utc_next:=v_after_utc_next-v_before_utc_next;
  v_delta_jakarta_next:=v_after_jakarta_next-v_before_jakarta_next;
  if p_fixed and row(v_delta_utc,v_delta_jakarta,v_delta_utc_next,v_delta_jakarta_next)
       is distinct from row(0::numeric,0::numeric,1::numeric,1::numeric) then
   raise exception 'U_OWNER_WIP_CUTOFF_NOT_CANONICAL: %/%/%/%',
    v_delta_utc,v_delta_jakarta,v_delta_utc_next,v_delta_jakarta_next;
  elsif not p_fixed and row(v_delta_utc,v_delta_jakarta,v_delta_utc_next,v_delta_jakarta_next)
       is distinct from row(1::numeric,0::numeric,1::numeric,1::numeric) then
   raise exception 'U_T_OWNER_WIP_COUNTEREXAMPLE_MISSING: %/%/%/%',
    v_delta_utc,v_delta_jakarta,v_delta_utc_next,v_delta_jakarta_next;
  end if;
  v_result:=jsonb_build_object(
   'physical_at',v_at,'canonical_date',v_canonical,
   'cutoff_2026_09_12',jsonb_build_object('utc_delta',v_delta_utc,
    'jakarta_delta',v_delta_jakarta),
   'cutoff_2026_09_13',jsonb_build_object('utc_delta',v_delta_utc_next,
    'jakarta_delta',v_delta_jakarta_next)
  );
 elsif p_case='OWNER_DEFAULT_AS_OF' then
  v_day:=pg_temp.u_day_zone();
  v_period:=least((v_day->>'canonical_day')::date,(v_day->>'session_day')::date);
  v_actual:=(pg_temp.u_report_default(v_period,v_period)
    #>>'{basis,balance_sheet_as_of}')::date;
  if p_fixed and v_actual is distinct from (v_day->>'canonical_day')::date then
   raise exception 'U_OWNER_DEFAULT_AS_OF_NOT_CANONICAL: %/%',v_actual,v_day;
  elsif not p_fixed and (v_actual is distinct from (v_day->>'session_day')::date
      or v_actual=(v_day->>'canonical_day')::date) then
   raise exception 'U_T_OWNER_DEFAULT_COUNTEREXAMPLE_MISSING: %/%',v_actual,v_day;
  end if;
  v_result:=jsonb_build_object('days',v_day,'period',v_period,'default_as_of',v_actual);
 else
  raise exception 'U_UNKNOWN_CASE %',p_case;
 end if;
 perform set_config('TimeZone','UTC',true);
 return v_result||jsonb_build_object(
  'case',p_case,'status',case when p_fixed then 'PASS'
    when p_case='MATERIAL_ORIGINAL_JAKARTA' then 'CONTROL_PASS'
    else 'KNOWN_T_BUG_REPRODUCED' end,
  'unsafe_history',v_unsafe,'authenticated_sql_reachability_proven',true,
  'http_ui_reachability_proven',false
 );
end$$;
