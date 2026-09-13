-- Shared rollback-only U corrective oracle. Requires pg_temp.u_* and t_*.
-- Fixture rows are privileged setup; public operations below use authenticated.
create function pg_temp.u_extra_purchase(p_at timestamptz,p_final boolean)
returns jsonb language plpgsql as $$
declare m uuid:=pg_temp.t_clone_material();loc uuid:=gen_random_uuid();d jsonb;r jsonb;
 k uuid:=gen_random_uuid();b jsonb;r2 jsonb;
begin
 insert into erp.locations(id,location_code,location_name,location_type,is_active)
 values(loc,'U-X-'||substr(loc::text,1,24),'U isolated boundary warehouse','RAW_MATERIAL_WAREHOUSE',true);
 begin
  execute 'set local role authenticated';
  d:=erp.save_material_purchase_draft_v2(jsonb_build_object(
   'purchase_number','U-X-'||gen_random_uuid(),
   'supplier_id','c8c30000-0000-4000-8000-000000000001','location_id',loc,
   'physical_at',p_at,'change_reason','U receipt date counterexample',
   'lines',jsonb_build_array(jsonb_build_object('material_id',m,'qty',2,'unit_price',.015,
    'price_state',case when p_final then 'FINAL' else 'ESTIMATED' end,
    'price_source',case when p_final then 'SUPPLIER_INVOICE' else 'MANUAL_ESTIMATE' end,
    'rolls',jsonb_build_array(jsonb_build_object('roll_number','U-X-R-'||gen_random_uuid(),'qty',2))
   ))),gen_random_uuid(),null);
  r:=erp.post_material_purchase_v2((d->>'purchase_id')::uuid,k,
    (d->>'row_version')::bigint,'U receipt date counterexample');
  execute 'reset role';
  b:=pg_temp.t_boundary();
  execute 'set local role authenticated';
  r2:=erp.post_material_purchase_v2((d->>'purchase_id')::uuid,k,
    (d->>'row_version')::bigint,'U receipt date counterexample');
  execute 'reset role';
 exception when others then execute 'reset role';raise;end;
 if r2 is distinct from r or pg_temp.t_boundary() is distinct from b then
  raise exception 'U_RECEIPT_REPLAY_NOT_IDEMPOTENT';
 end if;
 return jsonb_build_object('purchase_id',d->>'purchase_id','material_id',m,
  'response',r,'exact_request_replay_inert',true);
end$$;

create function pg_temp.u_extra_case(p_case text,p_fixed boolean)
returns jsonb language plpgsql as $$
declare
 z text;v_at timestamptz:='2026-09-03T00:30:00+07';day date:='2026-09-03';
 final boolean:=p_case like 'RECEIPT_FINAL_%';expected_day date;p uuid;a uuid;j uuid;
 fixture jsonb;before_old jsonb;before_new jsonb;after_old jsonb;after_new jsonb;
 dates jsonb;amount numeric;qty numeric;r jsonb;r2 jsonb;b jsonb;k uuid:=gen_random_uuid();v bigint;
 d text;d2 text;old_d text;header text;err text;state text;issue bigint;expected_issues bigint;
 count_after bigint;before_gl jsonb;after_gl jsonb;checks jsonb;source_before text;
 affected boolean:=false;result jsonb:='{}';rejected boolean:=false;
begin
 if pg_temp.m_report()<>'READY' then raise exception 'U_EXTRA_BASELINE_NOT_READY';end if;
 if p_case like 'RECEIPT_%' then
  z:=case when p_case like '%_UTC' then 'UTC' when p_case like '%_NEW_YORK' then 'America/New_York'
   when p_case like '%_TOKYO' then 'Asia/Tokyo' else 'Asia/Jakarta' end;
  if p_case='RECEIPT_EDGE_BEFORE' then v_at:='2026-09-02T16:59:59Z';day:='2026-09-02';z:='UTC';
  elsif p_case='RECEIPT_EDGE_AT' then v_at:='2026-09-02T17:00:00Z';z:='UTC';end if;
  perform set_config('TimeZone',z,true);
  expected_day:=case when p_fixed then day else v_at::date end;
  affected:=expected_day<>day;
  before_old:=pg_temp.u_report('2026-09-01','2026-09-02','2026-09-02')->'financial_position';
  before_new:=pg_temp.u_report('2026-09-01','2026-09-03','2026-09-03')->'financial_position';
  fixture:=pg_temp.u_extra_purchase(v_at,final);p:=(fixture->>'purchase_id')::uuid;
  select jsonb_agg(jsonb_build_object('source_type',source_type,'economic_date',economic_date,
   'transaction_date',transaction_date) order by source_type) into dates
  from erp.journal_entries where source_id=p and status='POSTED';
  if (select count(*) from erp.journal_entries where source_id=p and status='POSTED')
    <>(case when final then 1 else 2 end)
   or exists(select 1 from erp.journal_entries where source_id=p and status='POSTED'
    and (economic_date<>expected_day or transaction_date<>expected_day)) then
   raise exception 'U_EXTRA_RECEIPT_WRONG_DATES: %/%',dates,expected_day;
  end if;
  select sum(qty_signed) into qty from erp.material_stock_movements
   where material_id=(fixture->>'material_id')::uuid;
  if qty<>2 then raise exception 'U_EXTRA_RECEIPT_STOCK_MISMATCH';end if;
  after_old:=pg_temp.u_report('2026-09-01','2026-09-02','2026-09-02')->'financial_position';
  after_new:=pg_temp.u_report('2026-09-01','2026-09-03','2026-09-03')->'financial_position';
  foreach z in array array['material_inventory','supplier_final_ap','grni_estimated_liability',
    'cash','customer_ar','wip_inventory','fg_inventory'] loop
   amount:=case when z='material_inventory' or(z='supplier_final_ap' and final)
     or(z='grni_estimated_liability' and not final) then .03 else 0 end;
   if (after_new->>z)::numeric-(before_new->>z)::numeric<>amount
    or (after_old->>z)::numeric-(before_old->>z)::numeric<>
      (case when expected_day<='2026-09-02' then amount else 0 end) then
    raise exception 'U_EXTRA_REPORT_CUTOFF_MONEY_MISMATCH: %',z;
   end if;
  end loop;
  result:=jsonb_build_object('physical_at',v_at,'canonical_day',day,'observed_day',expected_day,
    'final_invoice',final,'journals',dates,'qty',qty,'document_value',.03,
    'prior_day_delta',pg_temp.t_delta(before_old,after_old),
    'business_day_delta',pg_temp.t_delta(before_new,after_new),'replay',fixture->'exact_request_replay_inert');
 elsif p_case='FROZEN_DEFAULT_PRIVILEGE' then
  -- Preserve the rejected U design as a negative control after correcting it.
  -- This temporary DDL is tester authority, not an operator capability.
  select pg_get_functiondef('erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure) into d;
  header:=split_part(d,E'\n',1);
  d2:=replace(d,header,'CREATE OR REPLACE FUNCTION erp.get_owner_financial_snapshot_v2(p_from date, p_to date, p_as_of date DEFAULT erp._cp3_business_date(CURRENT_TIMESTAMP))');
  execute d2;
  r:=pg_temp.u_report('2026-09-01','2026-09-02','2026-09-02');
  begin r2:=pg_temp.u_report_default('2026-09-01','2026-09-02');
  exception when others then get stacked diagnostics err=message_text,state=returned_sqlstate;rejected:=true;end;
  execute d;
  if not rejected or state<>'42501' or position('_cp3_business_date' in err)=0
   or r#>>'{data_confidence,status}'<>'READY'
   or has_function_privilege('authenticated','erp._cp3_business_date(timestamptz)','EXECUTE') then
   raise exception 'U_FROZEN_DEFAULT_PRIVILEGE_COUNTEREXAMPLE_MISSING';
  end if;
  result:=jsonb_build_object('frozen_u_default_refused',true,'sqlstate',state,'message',err,
    'explicit_as_of_control','READY','private_helper_still_private',true,'definition_restored',true);
 elsif p_case in('REPORT_EXPLICIT_NULL','REPORT_INVALID_RANGE') then
  b:=pg_temp.t_boundary();
  begin
   if p_case='REPORT_EXPLICIT_NULL' then r:=pg_temp.u_report('2026-09-01','2026-09-02',null);
   else r:=pg_temp.u_report('2026-09-03','2026-09-02','2026-09-03');end if;
  exception when others then get stacked diagnostics err=message_text;rejected:=true;end;
  if not rejected or b is distinct from pg_temp.t_boundary() then raise exception 'U_REPORT_INVALID_INPUT_NOT_ATOMIC';end if;
  result:=jsonb_build_object('atomic_refusal',true,'message',err);
 elsif p_case='DEFAULT_ZONE_ROUNDTRIP' then
  r:='[]';
  foreach z in array array['UTC','Asia/Jakarta','America/New_York','Pacific/Kiritimati','Etc/GMT+12'] loop
   perform set_config('TimeZone',z,true);
   expected_day:=case when p_fixed then erp._cp3_business_date(current_timestamp) else current_date end;
   day:=least(current_date,erp._cp3_business_date(current_timestamp));
   r2:=pg_temp.u_report_default(day,day);
   if (r2#>>'{basis,balance_sheet_as_of}')::date<>expected_day or current_setting('TimeZone')<>z then
    raise exception 'U_DEFAULT_DAY_OR_SESSION_ZONE_LEAK';
   end if;
   r:=r||jsonb_build_array(jsonb_build_object('zone',z,'as_of',expected_day));
  end loop;
  result:=jsonb_build_object('zones',r,'session_configuration_preserved',true);
 elsif p_case in('ADJUSTMENT_IDEMPOTENCY','ADJUSTMENT_FUTURE_ATOMIC','ADJUSTMENT_LINKED_REVERSE') then
  p:=pg_temp.t_purchase(pg_temp.t_clone_material(),array[2]::numeric[],10,true);
  v_at:=case when p_case='ADJUSTMENT_FUTURE_ATOMIC'
   then ((erp._cp3_business_date(current_timestamp)+2)::timestamp at time zone 'Asia/Jakarta')
   else '2026-09-02T12:00:00+07'::timestamptz end;
  a:=pg_temp.u_adjustment(p,v_at);select row_version into v from erp.material_adjustments where id=a;
  b:=pg_temp.t_boundary();before_gl:=pg_temp.t_ledger();
  begin
   execute 'set local role authenticated';
   r:=erp.post_material_adjustment_v2(a,k,v,'U replay or refusal');execute 'reset role';
  exception when others then execute 'reset role';get stacked diagnostics err=message_text;rejected:=true;end;
  if p_case='ADJUSTMENT_FUTURE_ATOMIC' then
   if not rejected or b is distinct from pg_temp.t_boundary() then raise exception 'U_FUTURE_ADJUSTMENT_NOT_ATOMIC';end if;
   result:=jsonb_build_object('atomic_refusal',true,'message',err);
  else
   if rejected then raise exception 'U_LAWFUL_ADJUSTMENT_REFUSED: %',err;end if;
   b:=pg_temp.t_boundary();
   execute 'set local role authenticated';
   r2:=erp.post_material_adjustment_v2(a,k,v,'U replay or refusal');execute 'reset role';
   if r2 is distinct from r or b is distinct from pg_temp.t_boundary() then raise exception 'U_ADJUSTMENT_REPLAY_MUTATED_FACTS';end if;
   if p_case='ADJUSTMENT_LINKED_REVERSE' then
    perform pg_temp.u_reverse(a);after_gl:=pg_temp.t_ledger();
    if after_gl is distinct from before_gl then raise exception 'U_ADJUSTMENT_INVERSE_MONEY_NOT_CONSERVED';end if;
    select id into j from erp.journal_entries where source_type='MATERIAL_ADJUSTMENT' and source_id=a;
    if (select count(*) from erp.journal_entries where reversal_of_id=j and status='POSTED')<>1
      or exists(select 1 from erp.journal_entries rv join erp.journal_entries orig on orig.id=rv.reversal_of_id
       where rv.reversal_of_id=j and rv.economic_date<orig.economic_date) then
     raise exception 'U_INVERSE_LINK_OR_CHRONOLOGY_INVALID';
    end if;
   end if;
   result:=jsonb_build_object('same_request_replay_inert',true,'linked_inverse',p_case='ADJUSTMENT_LINKED_REVERSE');
  end if;
 elsif p_case='DETECTOR_REVERSAL_DATE' then
  p:=pg_temp.t_purchase(pg_temp.t_clone_material(),array[2]::numeric[],10,true);
  a:=pg_temp.u_adjustment(p,'2026-09-02T12:00:00+07');perform pg_temp.u_post(a);
  select pg_get_functiondef('erp._cp3_r4_reverse_journal_internal(uuid,text)'::regprocedure) into d;
  if p_fixed then
   select object_definition into old_d from erp.cp6_v2620u_rollback_capsule
    where object_regidentity='erp._cp3_r4_reverse_journal_internal(uuid,text)';
  else old_d:=d;end if;
  if (length(old_d)-length(replace(old_d,'CURRENT_DATE','')))/length('CURRENT_DATE')<>1 then
   raise exception 'U_REVERSAL_DETECTOR_FAULT_ANCHOR';end if;
  -- Controlled tester fault, not a claimed operator ability or extra business bug.
  execute replace(old_d,'CURRENT_DATE','(erp._cp3_business_date(current_timestamp)-1)');
  perform pg_temp.u_reverse(a);execute d;
  select coalesce(sum(issue_count),0) into issue from erp.run_v268_financial_report_checks()
   where check_name='V2620U_JOURNAL_REVERSAL_BUSINESS_DATE';
  if issue<>(case when p_fixed then 1 else 0 end)
   or pg_temp.m_report()<>(case when p_fixed then 'BLOCKED' else 'READY' end) then
   raise exception 'U_REVERSAL_DETECTOR_SCOPE_MISSING';end if;
  result:=jsonb_build_object('detector','V2620U_JOURNAL_REVERSAL_BUSINESS_DATE',
   'issue_count',issue,'report',pg_temp.m_report(),'controlled_tester_fault',true,
   'runtime_definition_restored',true);
 elsif p_case in('DETECTOR_RECEIPT_DATE','DETECTOR_ADJUSTMENT_DATE') then
  perform set_config('TimeZone','UTC',true);
  if p_case='DETECTOR_RECEIPT_DATE' then
   select pg_get_functiondef('erp.post_material_purchase(uuid)'::regprocedure) into d;
   select pg_get_functiondef('erp.sync_material_purchase_grni_on_status()'::regprocedure) into d2;
   if p_fixed then
    for old_d in select object_definition from erp.cp6_v2620u_rollback_capsule
     where object_regidentity in('erp.post_material_purchase(uuid)','erp.sync_material_purchase_grni_on_status()') loop execute old_d;end loop;
   end if;
   fixture:=pg_temp.u_extra_purchase('2026-09-03T00:30:00+07',false);
   execute d;execute d2;expected_issues:=2;source_before:='V2620U_MATERIAL_RECEIPT_BUSINESS_DATE';
  else
   p:=pg_temp.t_purchase(pg_temp.t_clone_material(),array[2]::numeric[],10,true);
   a:=pg_temp.u_adjustment(p,'2026-09-03T00:30:00+07');
   select pg_get_functiondef('erp.post_material_adjustment(uuid)'::regprocedure) into d;
   if p_fixed then
    select object_definition into old_d from erp.cp6_v2620u_rollback_capsule where object_regidentity='erp.post_material_adjustment(uuid)';execute old_d;
   end if;
   perform pg_temp.u_post(a);execute d;expected_issues:=1;source_before:='V2620U_MATERIAL_ADJUSTMENT_BUSINESS_DATE';
  end if;
  select coalesce(sum(issue_count),0) into issue from erp.run_v268_financial_report_checks() where check_name=source_before;
  if issue<>(case when p_fixed then expected_issues else 0 end)
   or pg_temp.m_report()<>(case when p_fixed then 'BLOCKED' else 'READY' end) then
   raise exception 'U_EXTRA_DETECTOR_OR_REPORT_SCOPE_MISSING';
  end if;
  result:=jsonb_build_object('detector',source_before,'issue_count',issue,'report',pg_temp.m_report(),
    'tester_predecessor_replay',p_fixed,'runtime_definition_restored',true);
 else raise exception 'U_UNKNOWN_EXTRA_CASE: %',p_case;
 end if;
 if p_case not like 'DETECTOR_%' and pg_temp.m_report()<>'READY' then raise exception 'U_EXTRA_FALSE_BLOCKED';end if;
 return result||jsonb_build_object('case',p_case,'status','PASS','predecessor_wrong_day_observed',affected,
  'authenticated_sql_business_operations',true,'http_ui_reachability_proven',false);
end$$;
