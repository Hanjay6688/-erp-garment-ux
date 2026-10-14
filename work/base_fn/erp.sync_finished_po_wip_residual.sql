-- bootstrap lines 24594-24639
CREATE OR REPLACE FUNCTION erp.sync_finished_po_wip_residual(p_po_id uuid, p_effective_date date DEFAULT CURRENT_DATE, p_reason text DEFAULT 'Finished PO residual WIP close'::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  v_status text;
  v_wip_account uuid;
  v_residual numeric(24,6):=0;
  v_event uuid;
  v_journal uuid;
  v_lines jsonb;
begin
  perform erp.require_internal();
  select status into v_status from erp.production_orders where id=p_po_id for update;
  if v_status is null then raise exception 'PO not found'; end if;
  if v_status<>'FINISHED' then return; end if;
  v_wip_account:=erp.account_id('WIP');

  select coalesce(sum(jl.debit-jl.credit),0) into v_residual
  from erp.journal_lines jl
  join erp.journal_entries je on je.id=jl.journal_entry_id
  where je.status in ('POSTED','REVERSED')
    and jl.po_id=p_po_id and jl.account_id=v_wip_account;

  if abs(v_residual)<=0.005 then return; end if;
  insert into erp.po_wip_close_events(po_id,effective_date,residual_amount,reason)
  values (p_po_id,p_effective_date,v_residual,p_reason) returning id into v_event;

  if v_residual>0 then
    v_lines:=jsonb_build_array(
      jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',round(v_residual,2),'credit',0,'po_id',p_po_id),
      jsonb_build_object('mapping_key','WIP','debit',0,'credit',round(v_residual,2),'po_id',p_po_id));
  else
    v_lines:=jsonb_build_array(
      jsonb_build_object('mapping_key','WIP','debit',round(abs(v_residual),2),'credit',0,'po_id',p_po_id),
      jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',0,'credit',round(abs(v_residual),2),'po_id',p_po_id));
  end if;
  v_journal:=erp.post_journal('PO_WIP_RESIDUAL_CLOSE',v_event,p_effective_date,p_reason,v_lines);
  update erp.po_wip_close_events set journal_entry_id=v_journal where id=v_event;
end;
$function$;

alter function "erp"."sync_finished_po_wip_residual"(p_po_id uuid, p_effective_date date, p_reason text) owner to "postgres";
