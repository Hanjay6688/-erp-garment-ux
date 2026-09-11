-- Exact N counterexamples and O controls for cumulative AP/GRNI allocation.
-- Requires the disposable CP6 fixture plus m_* and n_* temporary helpers.
create function pg_temp.o_purchase(
  p_rolls numeric[], p_price numeric default 10, p_final boolean default false
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
  insert into erp.locations(id,location_code,location_name,location_type,is_active)
  values(v_location,'O-RAW-'||substr(v_location::text,1,16),
    'O return allocation warehouse','RAW_MATERIAL_WAREHOUSE',true);
  v_draft:=erp.save_material_purchase_draft_v2(jsonb_build_object(
    'purchase_number','O-PUR-'||gen_random_uuid(),
    'supplier_id','c8c30000-0000-4000-8000-000000000001',
    'location_id',v_location,
    'physical_at','2026-09-01T08:00:00Z',
    'change_reason','O cumulative return allocation oracle',
    'lines',jsonb_build_array(jsonb_build_object(
      'material_id','c8c30000-0000-4000-8000-000000000002',
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

create function pg_temp.o_invoice(p_purchase uuid,p_qty numeric,p_price numeric default 10)
returns uuid language plpgsql as $$
declare v_id uuid:=gen_random_uuid();
begin
  insert into erp.material_supplier_invoices(
    id,invoice_number,supplier_id,invoice_date,status,posting_reason
  )
  select v_id,'O-INV-'||v_id,h.supplier_id,'2026-09-02','DRAFT',
    'O partial invoice allocation oracle'
  from erp.material_purchase_headers h where h.id=p_purchase;
  insert into erp.material_supplier_invoice_lines(
    invoice_id,purchase_item_id,qty_invoiced,unit_price
  )
  select v_id,i.id,p_qty,p_price
  from erp.material_purchase_items i where i.purchase_id=p_purchase;
  perform erp.post_material_supplier_invoice(v_id);
  return v_id;
end
$$;

create function pg_temp.o_return_draft(
  p_purchase uuid,p_qtys numeric[],p_credit numeric default null
) returns uuid language plpgsql as $$
declare v_id uuid:=gen_random_uuid();
begin
  insert into erp.material_supplier_returns(
    id,return_number,supplier_id,location_id,physical_at,status,reason
  )
  select v_id,'O-RET-'||v_id,h.supplier_id,h.location_id,
    '2026-09-03T12:00:00Z','DRAFT','O lawful multi-line supplier return'
  from erp.material_purchase_headers h where h.id=p_purchase;
  with numbered_rolls as(
    select r.*,row_number() over(order by r.roll_number,r.id) ord
    from erp.material_rolls r
    join erp.material_purchase_items i on i.id=r.purchase_item_id
    where i.purchase_id=p_purchase
  ), requested as(
    select qty,ord from unnest(p_qtys) with ordinality u(qty,ord) where qty>0
  )
  insert into erp.material_supplier_return_items(
    return_id,material_id,roll_id,qty,purchase_item_id,supplier_credit_unit_price
  )
  select v_id,i.material_id,r.id,q.qty,i.id,
    coalesce(p_credit,erp.material_purchase_current_unit_cost(i.id))
  from requested q join numbered_rolls r using(ord)
  join erp.material_purchase_items i on i.id=r.purchase_item_id;
  return v_id;
end
$$;

create function pg_temp.o_delta(p_before jsonb,p_after jsonb) returns jsonb
language sql immutable as $$
  select jsonb_build_object(
    'ap',(p_after->>'ap')::numeric-(p_before->>'ap')::numeric,
    'grni',(p_after->>'grni')::numeric-(p_before->>'grni')::numeric,
    'inventory',(p_after->>'inventory')::numeric-(p_before->>'inventory')::numeric,
    'variance',(p_after->>'variance')::numeric-(p_before->>'variance')::numeric
  )
$$;

create function pg_temp.o_boundary() returns jsonb language plpgsql as $$
declare v_table text;v_digest text;v_result jsonb:=pg_temp.m_boundary();
begin
  foreach v_table in array array[
    'supplier_cent_posting_facts','material_cost_history',
    'material_cost_revaluation_state','material_cost_revaluation_events',
    'material_cost_checkpoints'
  ]::text[] loop
    execute format('select md5(coalesce(jsonb_agg(to_jsonb(x) order by to_jsonb(x)::text)::text,'''')) from erp.%I x',v_table)
      into v_digest;
    v_result:=v_result||jsonb_build_object(v_table,v_digest);
  end loop;
  return v_result;
end
$$;

create function pg_temp.o_snapshot(p_returns uuid[]) returns jsonb language sql as $$
  select jsonb_build_object(
    'ap_qty',coalesce(sum(i.ap_relief_qty_snapshot),0),
    'grni_qty',coalesce(sum(i.grni_relief_qty_snapshot),0),
    'ap_amount',coalesce(sum(i.ap_relief_amount_snapshot),0),
    'grni_amount',coalesce(sum(i.grni_relief_amount_snapshot),0),
    'movement_count',count(m.id),
    'fact_count',(select count(*) from erp.supplier_cent_posting_facts f
      where f.source_type='MATERIAL_SUPPLIER_RETURN'
        and f.source_id=any(p_returns) and f.phase='POST')
  )
  from erp.material_supplier_return_items i
  left join erp.material_stock_movements m
    on m.source_type='MATERIAL_SUPPLIER_RETURN_ITEM' and m.source_id=i.id
  where i.return_id=any(p_returns)
$$;

create function pg_temp.o_case(p_case text,p_fixed boolean) returns jsonb
language plpgsql as $$
declare
  v_purchase uuid;
  v_invoice uuid;
  v_first_return uuid;
  v_return uuid;
  v_payment uuid;
  v_rolls numeric[]:=array[5,5]::numeric[];
  v_return_qtys numeric[]:=array[5,5]::numeric[];
  v_first_return_qtys numeric[];
  v_invoice_qty numeric:=5;
  v_second_invoice_qty numeric;
  v_invoice_price numeric:=10;
  v_credit numeric;
  v_final boolean:=false;
  v_control boolean:=false;
  v_reverse boolean:=false;
  v_pay numeric;
  v_before jsonb;
  v_after jsonb;
  v_delta jsonb;
  v_snapshot jsonb;
  v_boundary jsonb;
  v_expected_delta jsonb;
  v_expected_ap_qty numeric;
  v_expected_grni_qty numeric;
  v_accepted boolean:=false;
  v_late_invoice_accepted boolean;
  v_late_atomic boolean;
  v_atomic boolean;
  v_code text;
  v_late_code text;
  v_returns uuid[]:='{}';
begin
  if pg_temp.m_report()<>'READY' then
    raise exception 'O_CLEAN_BASELINE_REQUIRED: %',pg_temp.m_issues();
  end if;
  if p_case='NO_INVOICE_TWO_ROLL_FULL' then
    v_invoice_qty:=null;v_control:=true;
    v_expected_delta:=jsonb_build_object('ap',0,'grni',0,'inventory',0,'variance',0);
    v_expected_ap_qty:=0;v_expected_grni_qty:=10;
  elsif p_case='DIRECT_FINAL_TWO_ROLL_FULL' then
    v_invoice_qty:=null;v_final:=true;v_control:=true;
    v_expected_delta:=jsonb_build_object('ap',0,'grni',0,'inventory',0,'variance',0);
    v_expected_ap_qty:=10;v_expected_grni_qty:=0;
  elsif p_case='FULL_INVOICE_TWO_ROLL_FULL' then
    v_invoice_qty:=10;v_control:=true;
    v_expected_delta:=jsonb_build_object('ap',0,'grni',0,'inventory',0,'variance',0);
    v_expected_ap_qty:=10;v_expected_grni_qty:=0;
  elsif p_case='PARTIAL_ONE_ROLL_FULL' then
    v_rolls:=array[10]::numeric[];v_return_qtys:=array[10]::numeric[];v_control:=true;
    v_expected_delta:=jsonb_build_object('ap',0,'grni',0,'inventory',0,'variance',0);
    v_expected_ap_qty:=5;v_expected_grni_qty:=5;
  elsif p_case='PARTIAL_TWO_RETURN_DOCUMENTS' then
    v_first_return_qtys:=array[5,0]::numeric[];
    v_return_qtys:=array[0,5]::numeric[];v_control:=true;
    v_expected_delta:=jsonb_build_object('ap',0,'grni',0,'inventory',0,'variance',0);
    v_expected_ap_qty:=5;v_expected_grni_qty:=5;
  elsif p_case='PARTIAL_TWO_LINES_BELOW_CAP' then
    v_return_qtys:=array[2,2]::numeric[];v_control:=true;
    v_expected_delta:=jsonb_build_object('ap',10,'grni',50,'inventory',60,'variance',0);
    v_expected_ap_qty:=4;v_expected_grni_qty:=0;
  elsif p_case='HIGH_CREDIT_ATOMIC_REFUSAL' then
    v_credit:=12;v_control:=true;
    v_expected_delta:=jsonb_build_object('ap',50,'grni',50,'inventory',100,'variance',0);
    v_expected_ap_qty:=0;v_expected_grni_qty:=0;
  elsif p_case='PARTIAL_TWO_ROLL_FULL' then
    v_expected_delta:=jsonb_build_object('ap',0,'grni',0,'inventory',0,'variance',0);
    v_expected_ap_qty:=5;v_expected_grni_qty:=5;
  elsif p_case='PARTIAL_TWO_LINES_CROSS_CAP' then
    v_return_qtys:=array[3,3]::numeric[];
    v_expected_delta:=jsonb_build_object('ap',0,'grni',40,'inventory',40,'variance',0);
    v_expected_ap_qty:=5;v_expected_grni_qty:=1;
  elsif p_case='PARTIAL_THREE_ROLL_FULL' then
    v_rolls:=array[2,3,5]::numeric[];v_return_qtys:=array[2,3,5]::numeric[];
    v_expected_delta:=jsonb_build_object('ap',0,'grni',0,'inventory',0,'variance',0);
    v_expected_ap_qty:=5;v_expected_grni_qty:=5;
  elsif p_case='SPLIT_INVOICES_TWO_ROLL_FULL' then
    v_invoice_qty:=2;v_second_invoice_qty:=3;
    v_expected_delta:=jsonb_build_object('ap',0,'grni',0,'inventory',0,'variance',0);
    v_expected_ap_qty:=5;v_expected_grni_qty:=5;
  elsif p_case='REPRICED_PARTIAL_TWO_ROLL_FULL' then
    v_invoice_price:=12;
    v_expected_delta:=jsonb_build_object('ap',5,'grni',0,'inventory',0,'variance',5);
    v_expected_ap_qty:=5;v_expected_grni_qty:=5;
  elsif p_case='PRIOR_RELIEF_CROSS_REMAINING_CAP' then
    v_first_return_qtys:=array[2,0]::numeric[];
    v_return_qtys:=array[2,2]::numeric[];
    v_expected_delta:=jsonb_build_object('ap',0,'grni',40,'inventory',40,'variance',0);
    v_expected_ap_qty:=5;v_expected_grni_qty:=1;
  elsif p_case='LOW_CREDIT_SILENT_MISPOST' then
    v_credit:=4;
    v_expected_delta:=jsonb_build_object('ap',30,'grni',0,'inventory',0,'variance',30);
    v_expected_ap_qty:=5;v_expected_grni_qty:=5;
  elsif p_case='LOW_CREDIT_PAYMENT_CAPACITY' then
    v_credit:=2;v_pay:=40;
    v_expected_delta:=jsonb_build_object('ap',0,'grni',0,'inventory',0,'variance',40);
    v_expected_ap_qty:=5;v_expected_grni_qty:=5;
  elsif p_case='LATE_INVOICE_LAUNDER' then
    v_credit:=4;v_second_invoice_qty:=5;
    v_expected_delta:=jsonb_build_object('ap',30,'grni',0,'inventory',0,'variance',30);
    v_expected_ap_qty:=5;v_expected_grni_qty:=5;
  elsif p_case='RETURN_REVERSE_RESTORE' then
    v_reverse:=true;
    v_expected_delta:=jsonb_build_object('ap',50,'grni',50,'inventory',100,'variance',0);
    v_expected_ap_qty:=5;v_expected_grni_qty:=5;
  elsif p_case='FRACTIONAL_QUANTITY' then
    v_rolls:=array[.1,.2]::numeric[];v_return_qtys:=array[.1,.2]::numeric[];
    v_invoice_qty:=.15;
    v_expected_delta:=jsonb_build_object('ap',0,'grni',0,'inventory',0,'variance',0);
    v_expected_ap_qty:=.15;v_expected_grni_qty:=.15;
  else
    raise exception 'O_UNKNOWN_ORACLE_CASE: %',p_case;
  end if;

  v_before:=pg_temp.n_ledger();
  v_purchase:=pg_temp.o_purchase(v_rolls,10,v_final);
  if v_invoice_qty is not null then
    v_invoice:=pg_temp.o_invoice(v_purchase,v_invoice_qty,v_invoice_price);
  end if;
  if p_case='SPLIT_INVOICES_TWO_ROLL_FULL' then
    perform pg_temp.o_invoice(v_purchase,v_second_invoice_qty,v_invoice_price);
  end if;
  if v_pay is not null then
    v_payment:=pg_temp.m_pay(v_purchase,v_pay);
  end if;
  if v_first_return_qtys is not null then
    v_first_return:=pg_temp.o_return_draft(v_purchase,v_first_return_qtys,v_credit);
    perform erp.post_material_supplier_return(v_first_return);
    v_returns:=array_append(v_returns,v_first_return);
  end if;
  v_return:=pg_temp.o_return_draft(v_purchase,v_return_qtys,v_credit);
  v_returns:=array_append(v_returns,v_return);
  v_boundary:=pg_temp.o_boundary();
  begin
    perform erp.post_material_supplier_return(v_return);
    v_accepted:=true;
  exception when raise_exception then
    v_code:=sqlstate;
  end;
  v_atomic:=case when v_accepted then null else v_boundary=pg_temp.o_boundary() end;

  if p_case='LATE_INVOICE_LAUNDER' and v_accepted then
    v_boundary:=pg_temp.o_boundary();
    begin
      perform pg_temp.o_invoice(v_purchase,v_second_invoice_qty,10);
      v_late_invoice_accepted:=true;
    exception when raise_exception then
      v_late_invoice_accepted:=false;v_late_code:=sqlstate;
    end;
    v_late_atomic:=case when v_late_invoice_accepted then null
      else v_boundary=pg_temp.o_boundary() end;
  end if;
  if v_reverse and v_accepted then
    perform erp.reverse_material_supplier_return(
      v_return,'O exact supplier return inverse restore');
  end if;

  v_after:=pg_temp.n_ledger();
  v_delta:=pg_temp.o_delta(v_before,v_after);
  v_snapshot:=pg_temp.o_snapshot(v_returns);

  if p_fixed then
    if p_case='HIGH_CREDIT_ATOMIC_REFUSAL' then
      if v_accepted or v_code is distinct from 'P0001' or not v_atomic then
        raise exception 'O_HIGH_CREDIT_REFUSAL_NOT_ATOMIC';
      end if;
    elsif not v_accepted then
      raise exception 'O_VALID_RETURN_REFUSED: % %',p_case,v_code;
    end if;
    if p_case='LATE_INVOICE_LAUNDER' and
       (v_late_invoice_accepted is distinct from false
        or v_late_code is distinct from 'P0001' or not v_late_atomic) then
      raise exception 'O_LATE_INVOICE_CAPACITY_NOT_ATOMIC';
    end if;
    if v_delta is distinct from v_expected_delta
       or (v_snapshot->>'ap_qty')::numeric<>v_expected_ap_qty
       or (v_snapshot->>'grni_qty')::numeric<>v_expected_grni_qty then
      raise exception 'O_EXACT_ALLOCATION_MISMATCH case=% delta=% snapshot=%',
        p_case,v_delta,v_snapshot;
    end if;
    if p_case='RETURN_REVERSE_RESTORE' and
       (select status from erp.material_supplier_returns where id=v_return)<>'REVERSED' then
      raise exception 'O_RETURN_INVERSE_STATUS_MISMATCH';
    end if;
  elsif v_control then
    if p_case='HIGH_CREDIT_ATOMIC_REFUSAL' then
      if v_accepted or v_code is distinct from 'P0001' or not v_atomic then
        raise exception 'N_HIGH_CREDIT_CONTROL_NOT_ATOMIC';
      end if;
    elsif not v_accepted then
      raise exception 'N_CONTROL_FALSE_REFUSAL: % %',p_case,v_code;
    end if;
    if v_delta is distinct from v_expected_delta
       or (v_snapshot->>'ap_qty')::numeric<>v_expected_ap_qty
       or (v_snapshot->>'grni_qty')::numeric<>v_expected_grni_qty then
      raise exception 'N_CONTROL_EXACT_MISMATCH case=% delta=% snapshot=%',
        p_case,v_delta,v_snapshot;
    end if;
  elsif p_case='LOW_CREDIT_SILENT_MISPOST' then
    if not v_accepted
       or v_delta is distinct from jsonb_build_object(
         'ap',10,'grni',50,'inventory',0,'variance',60)
       or (v_snapshot->>'ap_qty')::numeric<>10
       or (v_snapshot->>'grni_qty')::numeric<>0 then
      raise exception 'N_LOW_CREDIT_SILENT_MISPOST_NOT_REPRODUCED delta=% snapshot=%',
        v_delta,v_snapshot;
    end if;
  elsif p_case='LATE_INVOICE_LAUNDER' then
    if not v_accepted or v_late_invoice_accepted is distinct from true
       or v_delta is distinct from jsonb_build_object(
         'ap',60,'grni',0,'inventory',0,'variance',60)
       or (v_snapshot->>'ap_qty')::numeric<>10
       or (v_snapshot->>'grni_qty')::numeric<>0 then
      raise exception 'N_LATE_INVOICE_LAUNDER_NOT_REPRODUCED delta=% snapshot=%',
        v_delta,v_snapshot;
    end if;
  else
    if v_accepted or v_code is distinct from 'P0001' or not v_atomic
       or (v_snapshot->>'ap_qty')::numeric<>
         (case when p_case='PRIOR_RELIEF_CROSS_REMAINING_CAP' then 2 else 0 end)
       or (v_snapshot->>'grni_qty')::numeric<>0 then
      raise exception 'N_ATOMIC_FALSE_REFUSAL_NOT_REPRODUCED case=% accepted=% code=% atomic=% snapshot=%',
        p_case,v_accepted,v_code,v_atomic,v_snapshot;
    end if;
  end if;
  if pg_temp.m_report()<>'READY' then
    raise exception 'O_CASE_REPORT_NOT_READY case=% issues=%',p_case,pg_temp.m_issues();
  end if;
  return jsonb_build_object(
    'status',case when p_fixed then 'PASS' when v_control then 'CONTROL_PASS'
      else 'KNOWN_N_BUG_REPRODUCED' end,
    'case',p_case,'accepted',v_accepted,'sqlstate',v_code,
    'atomic_refusal',v_atomic,'late_invoice_accepted',v_late_invoice_accepted,
    'late_invoice_sqlstate',v_late_code,'late_invoice_atomic_refusal',v_late_atomic,
    'delta',v_delta,'snapshots',v_snapshot,'report',pg_temp.m_report()
  );
end
$$;
