-- bootstrap lines 13391-13490
CREATE OR REPLACE FUNCTION erp.post_journal(p_source_type text, p_source_id uuid, p_transaction_date date, p_description text, p_lines jsonb)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_entry_id uuid;
  v_number text;
  v_debit numeric(20,2);
  v_credit numeric(20,2);
  r jsonb;
  v_account_id uuid;
  v_gl_date date;
  v_ap_vendor_account uuid;
  v_vendor_id uuid;
  v_vendor_balance numeric(24,6);
  v_vendor_delta numeric(24,6);
begin
  perform erp.require_internal();
  if jsonb_typeof(p_lines)<>'array' or jsonb_array_length(p_lines)<2 then raise exception 'Journal requires at least two lines'; end if;
  select coalesce(sum(coalesce((x->>'debit')::numeric,0)),0),coalesce(sum(coalesce((x->>'credit')::numeric,0)),0)
  into v_debit,v_credit from jsonb_array_elements(p_lines) x;
  if round(v_debit,2)<>round(v_credit,2) or v_debit<=0 then raise exception 'Journal is not balanced. Debit %, Credit %',v_debit,v_credit; end if;
  if exists(select 1 from erp.journal_entries where source_type=p_source_type and source_id=p_source_id and status='POSTED') then
    raise exception 'A posted journal already exists for this source';
  end if;

  -- Serialize journal posting with accounting close/reopen. A close that starts
  -- first blocks this journal until the new closed-through date is visible; a
  -- journal that starts first keeps the close waiting until this posting commits.
  perform 1 from erp.accounting_period_control where singleton_id=1 for share;

  -- Vendor AP is allowed to reach zero, but not become negative. Negative AP
  -- means the company has a receivable/advance from the vendor and requires a
  -- separate explicit workflow instead of silently crossing the account sign.
  v_ap_vendor_account:=erp.account_id('AP_VENDOR');
  for v_vendor_id in
    select distinct nullif(x->>'vendor_id','')::uuid
    from jsonb_array_elements(p_lines) x
    where nullif(x->>'vendor_id','') is not null
      and coalesce((x->>'debit')::numeric,0)>coalesce((x->>'credit')::numeric,0)
      and (
        (x ? 'mapping_key' and x->>'mapping_key'='AP_VENDOR')
        or (x ? 'account_id' and nullif(x->>'account_id','')::uuid=v_ap_vendor_account)
      )
    order by 1
  loop
    perform pg_advisory_xact_lock(hashtextextended('VENDOR_AP|'||v_vendor_id::text,0));

    select coalesce(sum(jl.credit-jl.debit),0)
      into v_vendor_balance
    from erp.journal_lines jl
    join erp.journal_entries je on je.id=jl.journal_entry_id
    where je.status in ('POSTED','REVERSED')
      and jl.account_id=v_ap_vendor_account
      and jl.vendor_id=v_vendor_id;

    select coalesce(sum(
      coalesce((x->>'credit')::numeric,0)-coalesce((x->>'debit')::numeric,0)
    ),0)
      into v_vendor_delta
    from jsonb_array_elements(p_lines) x
    where nullif(x->>'vendor_id','')::uuid=v_vendor_id
      and (
        (x ? 'mapping_key' and x->>'mapping_key'='AP_VENDOR')
        or (x ? 'account_id' and nullif(x->>'account_id','')::uuid=v_ap_vendor_account)
      );

    if v_vendor_balance+v_vendor_delta < -0.01 then
      raise exception 'Transaksi ini membuat hutang vendor menjadi negatif. Hutang saat ini %, perubahan %, hasil %. Reverse/koreksi pembayaran, claim, atau invoice terkait dulu; kelebihan bayar/claim vendor harus masuk workflow piutang vendor terpisah.',
        round(v_vendor_balance,2),round(v_vendor_delta,2),round(v_vendor_balance+v_vendor_delta,2);
    end if;
  end loop;

  v_gl_date:=erp.resolve_accounting_transaction_date(p_transaction_date);
  v_number:='JRN-'||to_char(clock_timestamp(),'YYYYMMDDHH24MISSMS')||'-'||substr(gen_random_uuid()::text,1,8);
  insert into erp.journal_entries(journal_number,economic_date,transaction_date,posting_at,source_type,source_id,description,status,created_by)
  values(v_number,p_transaction_date,v_gl_date,now(),p_source_type,p_source_id,p_description,'POSTED',erp.current_app_user_id()) returning id into v_entry_id;

  for r in select * from jsonb_array_elements(p_lines) loop
    if r?'account_id' then v_account_id:=(r->>'account_id')::uuid; else v_account_id:=erp.account_id(r->>'mapping_key'); end if;
    insert into erp.journal_lines(journal_entry_id,account_id,description,debit,credit,customer_id,vendor_id,contractor_id,po_id,product_id)
    values(v_entry_id,v_account_id,r->>'description',coalesce((r->>'debit')::numeric,0),coalesce((r->>'credit')::numeric,0),nullif(r->>'customer_id','')::uuid,nullif(r->>'vendor_id','')::uuid,nullif(r->>'contractor_id','')::uuid,nullif(r->>'po_id','')::uuid,nullif(r->>'product_id','')::uuid);
  end loop;

  insert into erp.account_daily_balances(balance_date,account_id,debit_total,credit_total)
  select v_gl_date,jl.account_id,sum(jl.debit),sum(jl.credit) from erp.journal_lines jl where jl.journal_entry_id=v_entry_id group by jl.account_id
  on conflict(balance_date,account_id) do update set debit_total=erp.account_daily_balances.debit_total+excluded.debit_total,credit_total=erp.account_daily_balances.credit_total+excluded.credit_total,updated_at=now();

  if v_gl_date<>p_transaction_date then
    insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
    values('journal_entries',v_entry_id,'POST',jsonb_build_object('economic_date',p_transaction_date,'transaction_date',v_gl_date,'period_shifted',true,'source_type',p_source_type,'source_id',p_source_id),erp.current_app_user_id(),'Late/backdated posting moved to open accounting period');
  end if;
  return v_entry_id;
end;
$function$;

alter function "erp"."post_journal"(p_source_type text, p_source_id uuid, p_transaction_date date, p_description text, p_lines jsonb) owner to "postgres";
