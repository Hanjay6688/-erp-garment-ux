CREATE OR REPLACE FUNCTION erp.refresh_accessory_hpp_after_material_recost(p_material_id uuid, p_reason text DEFAULT 'Accessory historical moving-average recost'::text)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public', 'pg_temp'
AS $function$
declare
  v_category uuid;
  r record;
  v_new numeric(18,6);
  v_changed integer:=0;
  v_po uuid;
  v_rev uuid;v_old numeric;v_newtot numeric;v_d numeric;v_lot uuid;v_lot_po uuid;v_prod uuid;v_lotday date;v_e date;v_date date;
begin
  perform erp.require_internal();
  select accessory_category_id into v_category from erp.materials where id=p_material_id and material_type='ACCESSORY';
  if v_category is null then return 0; end if;
  perform pg_advisory_xact_lock(hashtextextended('ACCESSORY_HPP_CATEGORY|'||v_category::text,0));

  create temporary table if not exists pg_temp.erp_accessory_hpp_changed_pos(po_id uuid primary key) on commit drop;
  truncate pg_temp.erp_accessory_hpp_changed_pos;

  for r in
    select s.id,s.po_id,s.costing_basis_at,s.category_avg_cost_base_snapshot,s.hpp_unit_cost_base_snapshot
    from erp.fg_accessory_cost_snapshots s
    where s.category_id=v_category and s.hpp_method='CATEGORY_MOVING_AVG'
    order by s.costing_basis_at,s.id
    for update
  loop
    v_new:=erp.accessory_category_weighted_avg_cost_at(v_category,r.costing_basis_at);
    if v_new is null then
      raise exception 'Historical accessory recost would remove the valuation basis for FG accessory snapshot %. Correct/reverse the upstream inventory event first.',r.id;
    end if;
    if abs(v_new-r.hpp_unit_cost_base_snapshot)>0.000001 then
      insert into erp.fg_accessory_cost_revisions(snapshot_id,material_id,old_category_avg_cost,new_category_avg_cost,old_hpp_unit_cost,new_hpp_unit_cost,reason,changed_by)
      values(r.id,p_material_id,r.category_avg_cost_base_snapshot,v_new,r.hpp_unit_cost_base_snapshot,v_new,coalesce(nullif(trim(p_reason),''),'Accessory historical moving-average recost'),erp.current_app_user_id())
      returning id into v_rev;
      select total_hpp_cost,lot_id into v_old,v_lot from erp.fg_accessory_cost_snapshots where id=r.id;
      update erp.fg_accessory_cost_snapshots
      set category_avg_cost_base_snapshot=v_new,hpp_unit_cost_base_snapshot=v_new
      where id=r.id;
      -- AZ (independent review of AY rev7): the lot's accessory HPP entered WIP once, with the accrual
      -- (ACCESSORY_REIMBURSE_ACCRUAL: WIP against the Mandor reimbursement and its variance); the PO HPP sync below moves the
      -- change of that HPP out of WIP, so an accrued lot's change enters WIP against the reimbursement variance (the
      -- reimbursement itself is fixed), dated as the sync dates it: the lot day (never before the invoice date, never after
      -- today) on a late invoice with an open date, the invoice date when closed, today otherwise.
      select total_hpp_cost into v_newtot from erp.fg_accessory_cost_snapshots where id=r.id;
      v_d:=round(coalesce(v_newtot,0)-coalesce(v_old,0),2);
      if abs(v_d)>0.005 and exists(select 1 from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL'
                                     and source_id=v_lot and status='POSTED') then
        select fl.po_id,fl.product_id,erp._cp3_business_date(fl.produced_at) into v_lot_po,v_prod,v_lotday from erp.fg_lots fl where fl.id=v_lot;
        v_e:=erp.invoice_recost_economic_date_v1();
        v_date:=case when v_e is null then erp._cp3_business_date(statement_timestamp())
                     when exists(select 1 from erp.accounting_period_control c where c.singleton_id=1 and c.closed_through is not null and v_e<=c.closed_through) then v_e
                     else least(greatest(v_e,v_lotday),erp._cp3_business_date(statement_timestamp())) end;
        perform erp.post_journal('ACCESSORY_HPP_RECOST',v_rev,v_date,'Accessory HPP recost of an accrued lot: WIP against the reimbursement variance',
          jsonb_build_array(
            jsonb_build_object('mapping_key','WIP','debit',greatest(v_d,0),'credit',greatest(-v_d,0),'po_id',v_lot_po,'product_id',v_prod),
            jsonb_build_object('mapping_key','ACCESSORY_REIMBURSE_VARIANCE','debit',greatest(-v_d,0),'credit',greatest(v_d,0),'po_id',v_lot_po,'product_id',v_prod)));
      end if;
      insert into pg_temp.erp_accessory_hpp_changed_pos(po_id) values(r.po_id) on conflict do nothing;
      v_changed:=v_changed+1;
    end if;
  end loop;

  for v_po in select po_id from pg_temp.erp_accessory_hpp_changed_pos order by po_id loop
    perform erp.rebuild_po_hpp(v_po,'Accessory moving-average recost: '||coalesce(nullif(trim(p_reason),''),'historical material recost'));
    perform erp.propagate_conversion_hpp_for_po(v_po);
    perform erp.sync_po_hpp_to_gl(v_po,((statement_timestamp() AT TIME ZONE 'Asia/Jakarta'::text))::date);
  end loop;
  return v_changed;
end;
$function$
