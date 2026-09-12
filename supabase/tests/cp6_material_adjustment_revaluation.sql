-- Shared native/PGlite oracle. Requires the isolated CP6 seed and m_*/o_* helpers.
-- All expected money is calculated with PostgreSQL numeric document endpoints.
create function pg_temp.t_ledger() returns jsonb language sql as $$
 select jsonb_object_agg(mapping,balance) from (
  select mapping,coalesce((select sum(l.debit-l.credit) from erp.journal_lines l
   join erp.journal_entries j on j.id=l.journal_entry_id
   where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id(mapping)),0) balance
  from unnest(array['MATERIAL_INVENTORY','OTHER_EXPENSE','OTHER_INCOME','AP_SUPPLIER']) u(mapping)
 ) a
$$;
create function pg_temp.t_delta(p_before jsonb,p_after jsonb) returns jsonb
language sql immutable as $$
 select jsonb_object_agg(key,value::numeric-(p_before->>key)::numeric) from jsonb_each_text(p_after)
$$;
create function pg_temp.t_boundary() returns jsonb language plpgsql as $$
declare v text;v_hash text;r jsonb:=pg_temp.o_boundary();begin
 foreach v in array array['material_adjustments','material_adjustment_items','materials',
  'material_adjustment_revaluation_facts'] loop
  if to_regclass('erp.'||v) is not null then
   execute format('select md5(coalesce(jsonb_agg(to_jsonb(x) order by to_jsonb(x)::text)::text,'''')) from erp.%I x',v) into v_hash;
   r:=r||jsonb_build_object(v,v_hash);
  end if;
 end loop;return r;
end$$;
create function pg_temp.t_clone_material() returns uuid language plpgsql as $$
declare v uuid;begin
 insert into erp.materials
 select (jsonb_populate_record(null::erp.materials,to_jsonb(m)||jsonb_build_object(
  'id',gen_random_uuid(),'material_code','T-MAT-'||gen_random_uuid(),
  'material_sku','T-SKU-'||gen_random_uuid(),'material_name','T isolated adjustment material',
  'cached_stock_qty',0,'moving_average_cost',0))).*
 from erp.materials m where id='c8c30000-0000-4000-8000-000000000002' returning id into v;
 return v;
end$$;
create function pg_temp.t_purchase(
  p_material uuid,p_rolls numeric[], p_price numeric default 10, p_final boolean default false,
  p_location uuid default null
) returns uuid language plpgsql as $$
declare
  v_location uuid:=gen_random_uuid();
  v_draft jsonb;
  v_rolls jsonb;
  v_quantity numeric;
begin
  select sum(qty),jsonb_agg(jsonb_build_object(
    'roll_number','O-ROLL-'||ord||'-'||gen_random_uuid(),'qty',qty
  ) order by ord)
  into v_quantity,v_rolls
  from unnest(p_rolls) with ordinality u(qty,ord);
  if p_location is not null then v_location:=p_location;else
  insert into erp.locations(id,location_code,location_name,location_type,is_active)
  values(v_location,'O-RAW-'||substr(v_location::text,1,16),
    'T multi-material warehouse','RAW_MATERIAL_WAREHOUSE',true);
  end if;
  v_draft:=erp.save_material_purchase_draft_v2(jsonb_build_object(
    'purchase_number','O-PUR-'||gen_random_uuid(),
    'supplier_id','c8c30000-0000-4000-8000-000000000001',
    'location_id',v_location,
    'physical_at','2026-09-01T08:00:00Z',
    'change_reason','O cumulative return allocation oracle',
    'lines',jsonb_build_array(jsonb_build_object(
      'material_id',p_material,
      'qty',v_quantity,'unit_price',p_price,
      'price_state',case when p_final then 'FINAL' else 'ESTIMATED' end,
      'price_source',case when p_final then 'SUPPLIER_INVOICE' else 'MANUAL_ESTIMATE' end,
      'rolls',v_rolls
    ))
  ),gen_random_uuid(),null);
  perform erp.post_material_purchase_v2((v_draft->>'purchase_id')::uuid,
    gen_random_uuid(),(v_draft->>'row_version')::bigint,
    'O cumulative return allocation receipt');
  return (v_draft->>'purchase_id')::uuid;
end
$$;

create function pg_temp.t_adjustment(p_purchase uuid,p_fraction numeric default 1)
returns uuid language plpgsql as $$
declare v uuid;begin
 insert into erp.material_adjustments(adjustment_number,physical_at,location_id,reason_code,notes,status)
 select 'T-ADJ-'||gen_random_uuid(),'2026-09-02T12:00:00Z',location_id,
  'COUNT_CORRECTION','T lawful stock adjustment','DRAFT'
 from erp.material_purchase_headers where id=p_purchase returning id into v;
 insert into erp.material_adjustment_items(adjustment_id,material_id,roll_id,qty_signed)
 select v,i.material_id,r.id,-r.original_qty*p_fraction
 from erp.material_purchase_items i join erp.material_rolls r on r.purchase_item_id=i.id
 where i.purchase_id=p_purchase and p_fraction<>0;
 return v;
end$$;
create function pg_temp.t_multi_fixture() returns jsonb language plpgsql as $$
declare m1 uuid:=pg_temp.t_clone_material();m2 uuid:=pg_temp.t_clone_material();
 p1 uuid;p2 uuid;a uuid;loc uuid;c1 uuid:=gen_random_uuid();c2 uuid:=gen_random_uuid();v_before jsonb;
begin
 v_before:=pg_temp.t_ledger();
 p1:=pg_temp.t_purchase(m1,array[2]::numeric[],.015,true);
 select location_id into loc from erp.material_purchase_headers where id=p1;
 p2:=pg_temp.t_purchase(m2,array[2]::numeric[],.015,true,loc);
 a:=pg_temp.t_adjustment(p1,.5);
 insert into erp.material_adjustment_items(adjustment_id,material_id,roll_id,qty_signed)
 select a,m2,r.id,-1 from erp.material_purchase_items i join erp.material_rolls r on r.purchase_item_id=i.id where i.purchase_id=p2;
 perform erp.post_material_adjustment(a);
 insert into erp.material_purchase_cost_corrections(id,correction_number,purchase_id,invoice_date,reason,status)
 values(c1,'T-C1-'||c1,p1,'2026-09-03','T material A cost correction','DRAFT'),
       (c2,'T-C2-'||c2,p2,'2026-09-04','T material B cost correction','DRAFT');
 insert into erp.material_purchase_cost_correction_items(correction_id,purchase_item_id,new_unit_price)
 select case when purchase_id=p1 then c1 else c2 end,id,.02 from erp.material_purchase_items where purchase_id in(p1,p2);
 return jsonb_build_object('purchase_a',p1,'purchase_b',p2,'material_a',m1,'material_b',m2,
  'correction_a',c1,'correction_b',c2,'adjustment',a,'before',v_before);
end$$;
create function pg_temp.t_day_zone() returns jsonb language plpgsql as $$
declare z text;d date:=erp._cp3_business_date(current_timestamp);begin
 -- These real zones are 26 hours apart. At least one day differs from Jakarta.
 foreach z in array array['Etc/GMT+12','Pacific/Kiritimati'] loop
  perform set_config('TimeZone',z,true);
  if current_date<>d then return jsonb_build_object('zone',z,'canonical_day',d,
   'session_day',current_date,'lagging',current_date<d);end if;
 end loop;raise exception 'T_NO_DISTINCT_REAL_TIMEZONE';
end$$;

create function pg_temp.t_case(p_case text,p_fixed boolean) returns jsonb language plpgsql as $$
declare p uuid;a uuid;c uuid;mat uuid;j uuid;pay uuid;v_qty numeric:=2;v_used numeric;
 v_rolls numeric[]:=array[1,1];v_price numeric:=.015;v_new numeric:=.02;v_fraction numeric:=1;
 v_before jsonb;v_boundary jsonb;v_actual jsonb;v_expected jsonb;v_corrected jsonb;v_result jsonb:='{}';
 v_affected boolean:=false;v_refused boolean:=false;v_unsafe boolean:=false;v_zero boolean:=false;
 v_inverse boolean:=false;v_adjustment_first boolean:=false;v_day jsonb;v_date date;v_resolved date;
 v_old_period date;v_definition text;v_predecessor text;v_count bigint;v_report text;v_id uuid;
begin
 if pg_temp.m_report()<>'READY' then raise exception 'T_BASELINE_NOT_READY';end if;
 if p_case in('MULTI_MATERIAL_A_FIRST','MULTI_MATERIAL_B_FIRST') then
  v_affected:=true;v_result:=pg_temp.t_multi_fixture();
  perform erp.post_material_purchase_cost_correction((v_result->>(case when p_case='MULTI_MATERIAL_A_FIRST' then 'correction_a' else 'correction_b' end))::uuid);
  perform erp.post_material_purchase_cost_correction((v_result->>(case when p_case='MULTI_MATERIAL_A_FIRST' then 'correction_b' else 'correction_a' end))::uuid);
  v_actual:=pg_temp.t_delta(v_result->'before',pg_temp.t_ledger());
  v_expected:=jsonb_build_object('AP_SUPPLIER',-.08,'MATERIAL_INVENTORY',.04,'OTHER_EXPENSE',.04,'OTHER_INCOME',0);
  if (p_fixed and v_actual is distinct from v_expected) or (not p_fixed and v_actual=v_expected)
   or pg_temp.m_report()<>'READY' then raise exception 'T_MULTI_MATERIAL_DOCUMENT_CENTS %',v_actual;end if;
  v_unsafe:=not p_fixed;v_result:=v_result||jsonb_build_object('actual',v_actual,'expected',v_expected);
 elsif p_case='MISSING_NONZERO_JOURNAL' then
  p:=pg_temp.o_purchase(array[2]::numeric[],10,true);a:=pg_temp.t_adjustment(p);
  perform erp.post_material_adjustment(a);
  select id into j from erp.journal_entries where source_type='MATERIAL_ADJUSTMENT' and source_id=a and status='POSTED';
  -- Adversarial source/journal mismatch via the existing generic business inverse.
  perform erp.reverse_journal(j,'T missing-original-journal guard control');v_boundary:=pg_temp.t_boundary();
  begin perform erp.reverse_material_adjustment(a,'T may not erase nonzero original journal');
  exception when raise_exception then
   if sqlerrm<>'Jurnal material adjustment tidak ditemukan; reversal dibatalkan agar stok dan pembukuan tidak berbeda' then raise;end if;v_refused:=true;
  end;
  if not v_refused or v_boundary is distinct from pg_temp.t_boundary() then raise exception 'T_MISSING_JOURNAL_NOT_ATOMIC';end if;
  v_result:=jsonb_build_object('missing_nonzero_original_refused',true,'boundary_unchanged',true);
 elsif p_case like 'COST_%' or p_case in('LINKED_INVERSE','ADJUSTMENT_FIRST_INVERSE','FACT_GUARDS','DETECTOR_COST') then
  v_affected:=true;
  if p_case='COST_SINGLE_ENDPOINT' then v_rolls:=array[1];v_qty:=1;
  elsif p_case='COST_HALF_YARD' then v_rolls:=array[.5,.5];v_qty:=1;v_price:=10000.01;v_new:=10000.02;
  elsif p_case='COST_DECREASE' then v_price:=.02;v_new:=.015;
  elsif p_case='COST_PARTIAL' then v_rolls:=array[2,2];v_qty:=4;v_fraction:=.5;
  elsif p_case='COST_SINGLE_ROLL_CONTROL' then v_rolls:=array[2];v_affected:=false;
  elsif p_case='COST_INTEGER_CONTROL' then v_price:=10;v_new:=12;v_affected:=false;
  elsif p_case not in('COST_SPLIT','LINKED_INVERSE','ADJUSTMENT_FIRST_INVERSE','FACT_GUARDS','DETECTOR_COST') then
   raise exception 'T_UNKNOWN_COST_CASE';
  end if;
  v_inverse:=p_case in('LINKED_INVERSE','ADJUSTMENT_FIRST_INVERSE');
  v_adjustment_first:=p_case='ADJUSTMENT_FIRST_INVERSE';
  v_before:=pg_temp.t_ledger();p:=pg_temp.o_purchase(v_rolls,v_price,true);
  a:=pg_temp.t_adjustment(p,v_fraction);perform erp.post_material_adjustment(a);
  if p_case='DETECTOR_COST' and p_fixed then
   select pg_get_functiondef('erp.sync_material_cost_revaluation(uuid)'::regprocedure) into v_definition;
   select object_definition into v_predecessor from erp.cp6_v2620t_rollback_capsule
    where object_regidentity='erp.sync_material_cost_revaluation(uuid)';
   if v_predecessor is null then raise exception 'T_DETECTOR_PREDECESSOR_MISSING';end if;
   execute v_predecessor;
  end if;
  c:=pg_temp.m_correct(p,v_new);
  if p_case='DETECTOR_COST' and p_fixed then execute v_definition;end if;
  v_used:=v_qty*v_fraction;v_actual:=pg_temp.t_delta(v_before,pg_temp.t_ledger());
  v_expected:=jsonb_build_object('AP_SUPPLIER',-round(v_qty*v_new,2),
   'MATERIAL_INVENTORY',round(v_qty*v_new,2)-round(v_used*v_new,2),
   'OTHER_EXPENSE',round(v_used*v_new,2),'OTHER_INCOME',0);
  v_corrected:=v_actual;v_report:=pg_temp.m_report();
  if p_case='DETECTOR_COST' then
   select coalesce(sum(issue_count),0) into v_count from erp.run_v268_financial_report_checks()
    where check_name='V2620T_MATERIAL_ADJUSTMENT_REVALUATION';
   if v_actual=v_expected or v_count<>(case when p_fixed then 1 else 0 end)
    or v_report<>(case when p_fixed then 'BLOCKED' else 'READY' end) then
    raise exception 'T_REVALUATION_DETECTOR_FAILED';end if;
   v_unsafe:=true;
  else
   if (p_fixed or not v_affected) and v_actual is distinct from v_expected then
    raise exception 'T_DOCUMENT_CENT_CONSERVATION actual=% expected=%',v_actual,v_expected;
   elsif not p_fixed and v_affected and v_actual=v_expected then
    raise exception 'T_S_COUNTEREXAMPLE_NOT_REPRODUCED';
   end if;
   if v_report<>'READY' then raise exception 'T_VALID_REVALUATION_BLOCKED %',pg_temp.m_issues();end if;
   v_unsafe:=not p_fixed and v_affected;
  end if;
  if v_inverse then
   if v_adjustment_first then perform erp.reverse_material_adjustment(a,'T adjustment-first inverse');
   end if;
   perform erp.reverse_material_purchase_cost_correction(c,'T linked cost inverse');
   if not v_adjustment_first then perform erp.reverse_material_adjustment(a,'T correction-first inverse');end if;
   v_actual:=pg_temp.t_delta(v_before,pg_temp.t_ledger());
   if v_actual is distinct from jsonb_build_object('AP_SUPPLIER',-round(v_qty*v_price,2),
    'MATERIAL_INVENTORY',round(v_qty*v_price,2),'OTHER_EXPENSE',0,'OTHER_INCOME',0)
    or pg_temp.m_report()<>'READY' then raise exception 'T_LINKED_INVERSE_RESIDUE %',v_actual;end if;
   v_unsafe:=false;
  end if;
  if p_case='FACT_GUARDS' and p_fixed then
   select journal_entry_id,id into j,v_id from erp.material_adjustment_revaluation_facts where adjustment_id=a order by created_at limit 1;
   if j is null then raise exception 'T_FACT_NOT_CREATED';end if;
   v_boundary:=pg_temp.t_boundary();
   begin perform erp.reverse_journal(j,'T generic revaluation inverse must refuse');
   exception when raise_exception then
    if sqlerrm<>'T_PROTECTED_REVALUATION_JOURNAL_USE_SOURCE_WORKFLOW' then raise;end if;v_refused:=true;
   end;
   if not v_refused then raise exception 'T_GENERIC_REVALUATION_INVERSE_ACCEPTED';end if;
   begin update erp.material_adjustment_revaluation_facts set effective_date=effective_date+1 where id=v_id;
    raise exception 'T_FACT_UPDATE_ACCEPTED';exception when insufficient_privilege then null;end;
   begin delete from erp.material_adjustment_revaluation_facts where id=v_id;
    raise exception 'T_FACT_DELETE_ACCEPTED';exception when insufficient_privilege then null;end;
   begin truncate erp.material_adjustment_revaluation_facts;
    raise exception 'T_FACT_TRUNCATE_ACCEPTED';exception when insufficient_privilege then null;end;
   if exists(select 1 from information_schema.role_table_grants where table_schema='erp'
    and table_name='material_adjustment_revaluation_facts' and grantee in('PUBLIC','anon','authenticated','service_role'))
    then raise exception 'T_FACT_PUBLIC_GRANTS';end if;
   perform erp.sync_material_cost_revaluation('c8c30000-0000-4000-8000-000000000002');
   if pg_temp.t_boundary() is distinct from v_boundary then raise exception 'T_FACT_GUARD_OR_REPLAY_RESIDUE';end if;
  end if;
  v_result:=jsonb_build_object('corrected',v_corrected,'expected_corrected',v_expected,
   'after',v_actual,'report_at_correction',v_report,'detector_count',v_count,
   'inverse_completed',v_inverse,'fact_guards_tested',p_case='FACT_GUARDS' and p_fixed);
 elsif p_case in('ZERO_NET_INVERSE','ZERO_NET_CORRECTED_INVERSE','POSITIVE_CONTROL') then
  v_zero:=p_case<>'POSITIVE_CONTROL';v_affected:=v_zero;
  p:=pg_temp.o_purchase(array[1,1]::numeric[],.015,true);
  mat:=pg_temp.t_clone_material();a:=pg_temp.t_adjustment(p,case when v_zero then 1 else 0 end);
  if not v_zero then delete from erp.material_adjustment_items where adjustment_id=a;end if;
  insert into erp.material_adjustment_items(adjustment_id,material_id,qty_signed,input_unit_cost)
   values(a,mat,1,.03);
  perform erp.post_material_adjustment(a);
  if v_zero and exists(select 1 from erp.journal_entries where source_type='MATERIAL_ADJUSTMENT' and source_id=a)
   then raise exception 'T_ZERO_NET_UNEXPECTED_ORIGINAL_JOURNAL';end if;
  if p_case='ZERO_NET_CORRECTED_INVERSE' then c:=pg_temp.m_correct(p,.02);end if;
  v_boundary:=pg_temp.t_boundary();
  begin perform erp.reverse_material_adjustment(a,'T lawful aggregate-zero inverse');
  exception when raise_exception then
   if sqlerrm<>'Jurnal material adjustment tidak ditemukan; reversal dibatalkan agar stok dan pembukuan tidak berbeda' then raise;end if;
   v_refused:=true;
  end;
  if v_refused is distinct from (v_zero and not p_fixed) then raise exception 'T_ZERO_NET_INVERSE_EXPECTATION';end if;
  if v_refused and v_boundary is distinct from pg_temp.t_boundary() then raise exception 'T_ZERO_REFUSAL_NOT_ATOMIC';end if;
  if not v_refused and ((select status from erp.material_adjustments where id=a)<>'REVERSED'
   or (select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=mat)<>0)
   then raise exception 'T_ZERO_INVERSE_STOCK_RESIDUE';end if;
  v_unsafe:=not p_fixed and p_case='ZERO_NET_CORRECTED_INVERSE';
  if pg_temp.m_report()<>'READY' then raise exception 'T_ZERO_INVERSE_FALSE_BLOCKED %',pg_temp.m_issues();end if;
  v_result:=jsonb_build_object('inverse_refused',v_refused,'atomic_refusal',v_refused,
   'status',(select status from erp.material_adjustments where id=a),'report',pg_temp.m_report());
 elsif p_case in('REAL_DAY_BOUNDARY','CLOSED_PERIOD_DAY','JAKARTA_TODAY_CONTROL','FUTURE_REFUSAL_CONTROL') then
  v_affected:=p_case in('REAL_DAY_BOUNDARY','CLOSED_PERIOD_DAY');
  p:=pg_temp.m_purchase(10,10,true);
  if v_affected then v_day:=pg_temp.t_day_zone();
  else perform set_config('TimeZone','Asia/Jakarta',true);
   v_day:=jsonb_build_object('zone','Asia/Jakarta','canonical_day',erp._cp3_business_date(current_timestamp),
    'session_day',current_date,'lagging',false);end if;
  v_date:=(v_day->>'canonical_day')::date;
  if p_case='CLOSED_PERIOD_DAY' then
   select closed_through into v_old_period from erp.accounting_period_control where singleton_id=1;
   update erp.accounting_period_control set closed_through=v_date-2 where singleton_id=1;
   v_resolved:=erp.resolve_accounting_transaction_date(v_date-3);
   update erp.accounting_period_control set closed_through=v_old_period where singleton_id=1;
   if v_resolved is distinct from (case when p_fixed then v_date else (v_day->>'session_day')::date end)
    then raise exception 'T_CLOSED_PERIOD_DAY_EXPECTATION';end if;
  else
   if p_case='FUTURE_REFUSAL_CONTROL' or (p_case='REAL_DAY_BOUNDARY' and not (v_day->>'lagging')::boolean) then v_date:=v_date+1;end if;
   insert into erp.supplier_payments(purchase_id,payment_number,payment_date,amount,cash_account_id,status)
   select p,'T-DAY-'||gen_random_uuid(),v_date::timestamp at time zone 'Asia/Jakarta',40,id,'DRAFT'
    from erp.cash_accounts where is_active order by cash_account_code limit 1 returning id into pay;
   v_boundary:=pg_temp.t_boundary();
   begin perform erp.post_supplier_payment(pay);exception when raise_exception then
    if sqlerrm not like 'Transaksi/jurnal tidak boleh dipost ke tanggal masa depan:%' then raise;end if;v_refused:=true;
   end;
   if v_refused is distinct from (case when p_case='REAL_DAY_BOUNDARY' then
     case when p_fixed then not (v_day->>'lagging')::boolean else (v_day->>'lagging')::boolean end
    else p_case='FUTURE_REFUSAL_CONTROL' end) then raise exception 'T_REAL_BUSINESS_DAY_EXPECTATION';end if;
   if v_refused and pg_temp.t_boundary() is distinct from v_boundary then raise exception 'T_DAY_REFUSAL_NOT_ATOMIC';end if;
   if not v_refused then
    select economic_date into v_resolved from erp.journal_entries where source_type='SUPPLIER_PAYMENT' and source_id=pay;
    if v_resolved<>v_date then raise exception 'T_JOURNAL_BUSINESS_DAY_DRIFT';end if;
   end if;
   v_unsafe:=not v_refused and v_date>(v_day->>'canonical_day')::date;
  end if;
  v_result:=jsonb_build_object('real_clock',current_timestamp,'days',v_day,'economic_date',v_date,
   'resolved_date',v_resolved,'refused',v_refused,'atomic_refusal',v_refused,'fixture_closed_period',p_case='CLOSED_PERIOD_DAY');
 else raise exception 'T_UNKNOWN_CASE %',p_case;
 end if;
 perform set_config('TimeZone','UTC',true);
 return v_result||jsonb_build_object('case',p_case,'status',case when p_fixed then 'PASS'
  when v_affected then 'KNOWN_S_BUG_REPRODUCED' else 'CONTROL_PASS' end,
  'unsafe_history',v_unsafe,'http_ui_reachability_proven',false);
end$$;
