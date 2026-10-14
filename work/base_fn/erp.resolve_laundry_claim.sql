-- bootstrap lines 17183-17214
CREATE OR REPLACE FUNCTION erp.resolve_laundry_claim(p_claim_id uuid, p_resolution text, p_reason text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare c erp.laundry_claims%rowtype;v_ap_account uuid;v_ap_balance numeric(24,6):=0;v_effective_date date;
begin
  perform erp.require_owner_admin();
  if p_resolution not in ('SETTLED','WRITTEN_OFF') then raise exception 'Claim resolution must be SETTLED or WRITTEN_OFF'; end if;
  if nullif(trim(p_reason),'') is null then raise exception 'Claim resolution reason is required'; end if;
  select * into c from erp.laundry_claims where id=p_claim_id for update;
  if c.id is null then raise exception 'Laundry claim not found'; end if;
  if c.status in ('SETTLED','WRITTEN_OFF') then return; end if;
  if c.status='REJECTED' then raise exception 'Rejected laundry claim cannot be settled/write-off without reopening'; end if;
  if p_resolution='WRITTEN_OFF' and c.compensation_amount>0 then raise exception 'WRITTEN_OFF claim must have zero compensation; set compensation to zero or use SETTLED'; end if;
  v_effective_date:=coalesce(c.resolution_date,current_date);
  if v_effective_date>current_date then raise exception 'Tanggal penyelesaian claim laundry berada di masa depan'; end if;
  if p_resolution='SETTLED' and c.compensation_amount>0 then
    v_ap_account:=erp.account_id('AP_VENDOR');
    select coalesce(sum(jl.credit-jl.debit),0) into v_ap_balance from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
    where je.status in ('POSTED','REVERSED') and jl.vendor_id=c.vendor_id and jl.account_id=v_ap_account;
    if v_ap_balance+0.01<c.compensation_amount then raise exception 'Claim compensation % exceeds current laundry vendor payable %. Cash/receivable settlement needs a separate receivable workflow',c.compensation_amount,round(v_ap_balance,2); end if;
    perform erp.post_journal('LAUNDRY_CLAIM_SETTLEMENT',c.id,v_effective_date,'Laundry claim compensation offset',jsonb_build_array(
      jsonb_build_object('mapping_key','AP_VENDOR','debit',round(c.compensation_amount,2),'credit',0,'vendor_id',c.vendor_id),
      jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',0,'credit',round(c.compensation_amount,2),'vendor_id',c.vendor_id)));
  end if;
  update erp.laundry_claims set status=p_resolution,resolution_date=v_effective_date,resolved_at=now(),notes=concat_ws(E'\n',notes,'Resolution: '||p_reason) where id=c.id;
end$function$;

alter function "erp"."resolve_laundry_claim"(p_claim_id uuid, p_resolution text, p_reason text) owner to "postgres";
