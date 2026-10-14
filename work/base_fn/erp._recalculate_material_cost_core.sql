-- bootstrap lines 5576-5762
CREATE OR REPLACE FUNCTION erp._recalculate_material_cost_core(p_material_id uuid, p_recalc_from timestamp with time zone, p_allow_checkpoint boolean)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  r erp.material_stock_movements%rowtype;
  rr record;
  v_stock numeric(18,6):=0;
  v_avg numeric(18,6):=0;
  v_stock_before numeric(18,6);
  v_avg_before numeric(18,6);
  v_cost numeric(18,6);
  v_new_stock numeric(18,6);
  v_new_avg numeric(18,6);
  v_closed date;
  v_cp erp.material_cost_checkpoints%rowtype;
  v_use_checkpoint boolean:=false;
begin
  perform erp.require_internal();
  select closed_through into v_closed from erp.accounting_period_control where singleton_id=1 for share;
  perform 1 from erp.materials where id=p_material_id for update;
  if not found then raise exception 'Material not found'; end if;

  if p_allow_checkpoint and p_recalc_from is not null and v_closed is not null then
    select * into v_cp from erp.material_cost_checkpoints where material_id=p_material_id;
    if v_cp.material_id is not null
       and v_cp.checkpoint_date<=v_closed
       and p_recalc_from::date>v_cp.checkpoint_date then
      v_use_checkpoint:=true;
      v_stock:=v_cp.stock_qty;
      v_avg:=v_cp.moving_average_cost;
    end if;
  end if;

  if v_use_checkpoint then
    if v_cp.last_movement_id is null then
      delete from erp.material_cost_history where material_id=p_material_id;
    else
      delete from erp.material_cost_history h
      using erp.material_stock_movements msm
      where h.material_id=p_material_id and h.movement_id=msm.id
        and (msm.physical_at,msm.system_created_at,msm.id)>(v_cp.last_physical_at,v_cp.last_system_created_at,v_cp.last_movement_id);
    end if;
  else
    delete from erp.material_cost_history where material_id=p_material_id;
  end if;

  for r in
    select * from erp.material_stock_movements msm
    where msm.material_id=p_material_id
      and msm.reversal_of_id is null
      and not exists(select 1 from erp.material_stock_movements rv where rv.reversal_of_id=msm.id)
      and (
        not v_use_checkpoint
        or v_cp.last_movement_id is null
        or (msm.physical_at,msm.system_created_at,msm.id)>(v_cp.last_physical_at,v_cp.last_system_created_at,v_cp.last_movement_id)
      )
    order by msm.physical_at,msm.system_created_at,msm.id
    for update
  loop
    v_stock_before:=v_stock;
    v_avg_before:=v_avg;
    if r.qty_signed>0 then
      if r.movement_type='REVERSAL' and r.reversal_of_id is not null then
        select x.unit_cost_snapshot into v_cost from erp.material_stock_movements x where x.id=r.reversal_of_id;
        v_cost:=coalesce(v_cost,r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      elsif r.movement_type='CUTTING_RETURN' and r.source_type='CUTTING_GROUP_RETURN' then
        select x.unit_cost_snapshot into v_cost
        from erp.material_stock_movements x
        where x.material_id=r.material_id
          and x.source_type='CUTTING_GROUP' and x.source_id=r.source_id
          and x.movement_type='CUTTING_ISSUE'
          and x.roll_id is not distinct from r.roll_id
        order by x.physical_at desc,x.system_created_at desc,x.id desc limit 1;
        v_cost:=coalesce(v_cost,r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      else
        v_cost:=coalesce(r.input_unit_cost,r.unit_cost_snapshot,v_avg);
      end if;
      v_new_stock:=v_stock+r.qty_signed;
      if v_new_stock>0 then
        v_new_avg:=((v_stock*v_avg)+(r.qty_signed*v_cost))/v_new_stock;
      else
        v_new_avg:=0;
      end if;
    else
      v_new_stock:=v_stock+r.qty_signed;
      if v_new_stock<0 then
        raise exception 'Backdate/correction would create negative material stock for material %, movement %',p_material_id,r.id;
      end if;
      v_cost:=v_avg;
      v_new_avg:=case when v_new_stock=0 then 0 else v_avg end;
    end if;

    update erp.material_stock_movements
    set original_unit_cost_snapshot=coalesce(original_unit_cost_snapshot,v_cost),
        unit_cost_snapshot=v_cost,
        is_cost_recalculated=true
    where id=r.id;

    insert into erp.material_cost_history(material_id,movement_id,physical_at,stock_before,average_before,movement_qty,movement_unit_cost,stock_after,average_after)
    values(p_material_id,r.id,r.physical_at,v_stock_before,v_avg_before,r.qty_signed,v_cost,v_new_stock,v_new_avg);
    v_stock:=v_new_stock;
    v_avg:=v_new_avg;
  end loop;

  for rr in
    select mr.id as roll_id,coalesce(sum(msm.qty_signed),0)::numeric as roll_qty
    from erp.material_rolls mr
    left join erp.material_stock_movements msm on msm.roll_id=mr.id
    where mr.material_id=p_material_id
    group by mr.id
  loop
    if rr.roll_qty<0 then raise exception 'Correction would create negative roll stock for roll %',rr.roll_id; end if;
    update erp.material_rolls
    set cached_qty=rr.roll_qty,
        status=case when rr.roll_qty=0 then 'EXHAUSTED' when rr.roll_qty<original_qty then 'HALF_USED' else 'AVAILABLE' end,
        updated_at=now()
    where id=rr.roll_id and status<>'RETURNED_SUPPLIER';
  end loop;

  update erp.cutting_group_rolls cgr
  set unit_cost_snapshot=(
    select msm.unit_cost_snapshot
    from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CUTTING_GROUP'
      and msm.source_id=cgr.cutting_group_id and msm.movement_type='CUTTING_ISSUE'
      and msm.roll_id is not distinct from cgr.roll_id
    order by msm.physical_at desc,msm.system_created_at desc,msm.id desc limit 1
  )
  where exists(
    select 1 from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CUTTING_GROUP'
      and msm.source_id=cgr.cutting_group_id and msm.movement_type='CUTTING_ISSUE'
      and msm.roll_id is not distinct from cgr.roll_id
  );

  update erp.contractor_material_issue_items ii
  set unit_cost_snapshot=(
    select msm.unit_cost_snapshot from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'
      and msm.source_id=ii.id and msm.movement_type='CONTRACTOR_ISSUE'
    order by msm.physical_at desc,msm.system_created_at desc,msm.id desc limit 1
  )
  where ii.material_id=p_material_id and exists(
    select 1 from erp.material_stock_movements msm
    where msm.material_id=p_material_id and msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'
      and msm.source_id=ii.id and msm.movement_type='CONTRACTOR_ISSUE'
  );

  update erp.materials set cached_stock_qty=v_stock,moving_average_cost=v_avg,updated_at=now() where id=p_material_id;

  perform erp.sync_material_cost_revaluation(p_material_id);

  insert into erp.cost_recalc_queue(entity_type,entity_id,recalc_from,reason)
  select distinct 'PO',cg.po_id,min(msm.physical_at),'Material moving-average/backdate recalculation'
  from erp.material_stock_movements msm
  join erp.cutting_groups cg on msm.source_type in('CUTTING_GROUP','CUTTING_GROUP_RETURN') and msm.source_id=cg.id
  where msm.material_id=p_material_id
    and exists(select 1 from erp.fg_lots fl where fl.po_id=cg.po_id)
    and not exists(select 1 from erp.cost_recalc_queue q where q.entity_type='PO' and q.entity_id=cg.po_id and (q.status in('PENDING','RUNNING') or (q.status='FAILED' and q.attempt_count<3)))
  group by cg.po_id;

  insert into erp.cost_recalc_queue(entity_type,entity_id,recalc_from,reason)
  select distinct 'PO',cmi.po_id,min(msm.physical_at),'Contractor material moving-average/backdate recalculation'
  from erp.material_stock_movements msm
  join erp.contractor_material_issue_items ii on msm.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM' and msm.source_id=ii.id
  join erp.contractor_material_issues cmi on cmi.id=ii.issue_id
  where msm.material_id=p_material_id and cmi.po_id is not null
    and exists(select 1 from erp.fg_lots fl where fl.po_id=cmi.po_id)
    and not exists(select 1 from erp.cost_recalc_queue q where q.entity_type='PO' and q.entity_id=cmi.po_id and (q.status in('PENDING','RUNNING') or (q.status='FAILED' and q.attempt_count<3)))
  group by cmi.po_id;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('materials',p_material_id,'RECALCULATE',jsonb_build_object('cached_stock_qty',v_stock,'moving_average_cost',v_avg,'original_movement_snapshots_preserved',true,'gl_revaluation_synced',true,'checkpoint_used',v_use_checkpoint,'recalc_from',p_recalc_from),erp.current_app_user_id(),'Material chronological moving-average recalculation');

  perform erp.refresh_accessory_hpp_after_material_recost(p_material_id,'Material chronological moving-average recalculation');

  if not v_use_checkpoint and v_closed is not null then
    perform erp.refresh_material_cost_checkpoint(p_material_id,v_closed);
  end if;
end;
$function$;

alter function "erp"."_recalculate_material_cost_core"(p_material_id uuid, p_recalc_from timestamp with time zone, p_allow_checkpoint boolean) owner to "postgres";
