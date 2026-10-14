-- bootstrap lines 24935-25015
CREATE OR REPLACE FUNCTION erp.sync_po_hpp_to_gl(p_po_id uuid, p_effective_date date DEFAULT CURRENT_DATE)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  t record;
  s erp.po_hpp_gl_state%rowtype;
  v_target_qty integer:=0;
  v_target_hpp numeric(24,6):=0;
  v_target_fg numeric(24,6):=0;
  v_target_cogs numeric(24,6):=0;
  v_target_other numeric(24,6):=0;
  v_df numeric(24,6);v_dc numeric(24,6);v_do numeric(24,6);v_sum numeric(24,6);
  v_lines jsonb:='[]'::jsonb;v_event uuid;v_journal uuid;v_documented_gain numeric(24,6):=0;
begin
  perform erp.require_internal();
  select * into t from erp.compute_po_hpp_gl_targets(p_po_id);
  select * into s from erp.po_hpp_gl_state where po_id=p_po_id for update;

  if coalesce(t.base_output_qty,0)>0 then
    v_target_qty:=t.base_output_qty;
    v_target_hpp:=coalesce(t.hpp_total_cost,0);
    v_target_fg:=coalesce(t.fg_value,0);
    v_target_cogs:=coalesce(t.cogs_value,0);
    v_target_other:=coalesce(t.other_out_value,0);

    with lot_hpp as (
      select fl.id lot_id,case when coalesce(hv.qty_basis_pcs,0)>0 then hv.total_cost/hv.qty_basis_pcs else 0 end::numeric hpp_per_pcs
      from erp.fg_lots fl left join erp.hpp_versions hv on hv.lot_id=fl.id and hv.is_current=true
      where fl.po_id=p_po_id and fl.lot_origin<>'VOIDED_PRODUCTION'
    ), adj_net as (
      select fm.lot_id,sum(fm.qty_signed)::numeric qty
      from erp.fg_stock_movements fm join erp.fg_lots fl on fl.id=fm.lot_id
      where fl.po_id=p_po_id and fl.lot_origin<>'VOIDED_PRODUCTION'
        and ((fm.movement_type='ADJUSTMENT' and fm.source_type='FG_ADJUSTMENT_ITEM')
          or (fm.movement_type='REVERSAL' and exists(select 1 from erp.fg_stock_movements orig where orig.id=fm.reversal_of_id and orig.movement_type='ADJUSTMENT' and orig.source_type='FG_ADJUSTMENT_ITEM')))
      group by fm.lot_id
    )
    select coalesce(sum(greatest(a.qty,0)*lh.hpp_per_pcs),0) into v_documented_gain
    from adj_net a join lot_hpp lh on lh.lot_id=a.lot_id;

    if v_target_other < -v_documented_gain-0.01 then
      raise exception 'PO HPP allocation inconsistent: current FG + net sold exceeds production output without a matching documented positive FG adjustment';
    end if;
  else
    -- Important reversal boundary: when the last active production output is voided,
    -- unwind any prior HPP allocation instead of returning early and leaving FG/COGS stranded.
    v_target_qty:=0;v_target_hpp:=0;v_target_fg:=0;v_target_cogs:=0;v_target_other:=0;
    if s.po_id is null then return; end if;
  end if;

  v_df:=v_target_fg-coalesce(s.fg_value,0);
  v_dc:=v_target_cogs-coalesce(s.cogs_value,0);
  v_do:=v_target_other-coalesce(s.other_out_value,0);
  v_sum:=v_df+v_dc+v_do;

  if abs(v_df)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_df>0 then jsonb_build_object('mapping_key','FG_INVENTORY','debit',round(v_df,2),'credit',0,'po_id',p_po_id) else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',round(abs(v_df),2),'po_id',p_po_id) end); end if;
  if abs(v_dc)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_dc>0 then jsonb_build_object('mapping_key','COGS','debit',round(v_dc,2),'credit',0,'po_id',p_po_id) else jsonb_build_object('mapping_key','COGS','debit',0,'credit',round(abs(v_dc),2),'po_id',p_po_id) end); end if;
  if abs(v_do)>0.005 then
    if v_do>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',round(v_do,2),'credit',0,'po_id',p_po_id));
    else v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',round(abs(v_do),2),'po_id',p_po_id)); end if;
  end if;
  if abs(v_sum)>0.005 then v_lines:=v_lines||jsonb_build_array(case when v_sum>0 then jsonb_build_object('mapping_key','WIP','debit',0,'credit',round(v_sum,2),'po_id',p_po_id) else jsonb_build_object('mapping_key','WIP','debit',round(abs(v_sum),2),'credit',0,'po_id',p_po_id) end); end if;

  if jsonb_array_length(v_lines)>=2 then
    insert into erp.po_hpp_gl_events(po_id,effective_date,old_hpp_total,new_hpp_total,fg_delta,cogs_delta,other_delta)
    values(p_po_id,p_effective_date,coalesce(s.hpp_total_cost,0),v_target_hpp,v_df,v_dc,v_do) returning id into v_event;
    v_journal:=erp.post_journal('PO_HPP_GL_SYNC',v_event,p_effective_date,'Latest corrected HPP allocation',v_lines);
    update erp.po_hpp_gl_events set journal_entry_id=v_journal where id=v_event;
  end if;

  insert into erp.po_hpp_gl_state(po_id,base_output_qty,hpp_total_cost,fg_value,cogs_value,other_out_value,updated_at)
  values(p_po_id,v_target_qty,v_target_hpp,v_target_fg,v_target_cogs,v_target_other,now())
  on conflict(po_id) do update set base_output_qty=excluded.base_output_qty,hpp_total_cost=excluded.hpp_total_cost,fg_value=excluded.fg_value,cogs_value=excluded.cogs_value,other_out_value=excluded.other_out_value,updated_at=now();
end;
$function$;

alter function "erp"."sync_po_hpp_to_gl"(p_po_id uuid, p_effective_date date) owner to "postgres";
