"""Explicit continuation for cutover WIP and value ownership for native BS actions."""

SCHEMA=r"""
create table erp.initial_import_wip_output_reversals(
 output_id uuid primary key references erp.initial_import_wip_outputs(id),reason text not null,
 physical_at timestamptz not null,created_at timestamptz not null default clock_timestamp(),
 created_by uuid not null references erp.app_users(id)
);
alter table erp.initial_import_wip_output_reversals enable row level security;
revoke all on erp.initial_import_wip_output_reversals from public,anon,authenticated,service_role;
"""

BS_VALUE=r"""create or replace function erp.sync_initial_import_bs_value_v1(p_item uuid,p_date date) returns void
language plpgsql security definer set search_path='' as $function$
declare s erp.initial_import_production_sources%rowtype;v_qty integer;v_target numeric;v_prior numeric;v_delta numeric;v_event uuid;v_journal uuid;
begin
 perform erp.require_internal();
 if not pg_try_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0)) then raise exception 'WIP_VALUE_BUSY: penilaian stok sedang berubah, coba ulang';end if;
 select * into s from erp.initial_import_production_sources where opening_item_id=p_item for update;
 if s.bs_case_id is null then return;end if;
 select coalesce(sum(qty_pcs),0) into v_qty from erp.bs_resolutions where bs_case_id=s.bs_case_id
  and source_rework_order_id is null and resolution_type not in('REWORK_SEWING','REWORK_LAUNDRY');
 if v_qty>s.qty_pcs then raise exception 'Pengeluaran BS melebihi saldo fisik';end if;
 v_target:=round(erp.initial_import_source_value_v1(p_item)*v_qty/s.qty_pcs,2);
 select coalesce(sum(target_amount-previous_amount),0) into v_prior from erp.initial_import_bs_value_events where opening_item_id=p_item;
 v_delta:=v_target-v_prior;if v_delta=0 then return;end if;
 v_event:=gen_random_uuid();
 v_journal:=erp.post_journal('INITIAL_IMPORT_BS_VALUE',v_event,p_date,'Nilai BS saldo awal yang dikeluarkan atau dikembalikan',jsonb_build_array(
  jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',greatest(v_delta,0),'credit',greatest(-v_delta,0),'po_id',s.po_id),
  jsonb_build_object('mapping_key','WIP','debit',greatest(-v_delta,0),'credit',greatest(v_delta,0),'po_id',s.po_id)));
 insert into erp.initial_import_bs_value_events(id,opening_item_id,disposed_qty,previous_amount,target_amount,economic_date,journal_entry_id,created_by)
 values(v_event,p_item,v_qty,v_prior,v_target,p_date,v_journal,erp.current_app_user_id());
end;$function$;"""

BS_TRIGGER=r"""create or replace function erp.sync_initial_import_bs_disposition_v1() returns trigger
language plpgsql security definer set search_path='' as $function$
declare v_item uuid;v_date date;v_case uuid;v_po_status text;
begin
 if tg_op='DELETE' then v_case:=old.bs_case_id;v_date:=erp._cp3_business_date(statement_timestamp());
 else v_case:=new.bs_case_id;v_date:=erp._cp3_business_date(new.physical_at);end if;
 select opening_item_id into v_item from erp.initial_import_production_sources where bs_case_id=v_case;
 if v_item is not null and tg_op='DELETE' then
  if not pg_try_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0)) then raise exception 'WIP_VALUE_BUSY: penilaian stok sedang berubah, coba ulang';end if;
  select p.status into v_po_status from erp.production_orders p join erp.initial_import_production_sources s on s.po_id=p.id
   where s.opening_item_id=v_item for update of p;
  if v_po_status in('FINISHED','CANCELLED') then raise exception 'Buka kembali PO sebelum mengembalikan saldo BS';end if;
 end if;
 if v_item is not null then perform erp.sync_initial_import_bs_value_v1(v_item,v_date);end if;
 if tg_op='DELETE' then return old;end if;return new;
end;$function$;"""

PO_GUARD=r"""create or replace function erp.guard_initial_import_po_completion_v1() returns trigger
language plpgsql security definer set search_path='' as $function$
begin
 if new.status in('FINISHED','CANCELLED') and old.status is distinct from new.status and exists(
  select 1 from erp.initial_import_production_sources s where s.po_id=new.id and s.qty_pcs>
   case when s.bs_case_id is not null then coalesce((select sum(qty_pcs) from erp.bs_resolutions where bs_case_id=s.bs_case_id),0)
   else coalesce((select sum(o.qty_pcs) from erp.initial_import_wip_outputs o where o.opening_item_id=s.opening_item_id
      and not exists(select 1 from erp.initial_import_wip_output_reversals rv where rv.output_id=o.id)),0) end
 ) then raise exception 'PO masih memiliki WIP/BS saldo awal yang belum selesai';end if;
 return new;
end;$function$;"""

COMPLETE=r"""create or replace function erp.complete_initial_import_wip_v1(p_payload jsonb) returns jsonb
language plpgsql security definer set search_path='' set DateStyle='ISO, YMD' as $function$
declare s erp.initial_import_production_sources%rowtype;i erp.opening_balance_items%rowtype;
 v_batch uuid;v_product uuid;v_location uuid;v_qty integer;v_remaining integer;v_lot uuid;v_output uuid;v_date date;v_at timestamptz;
 v_reason text;v_hpp numeric;v_prior record;v_movement uuid;v_po_status text;v_op text:=coalesce(p_payload->>'operation','COMPLETE');
begin
 perform erp.require_owner_admin();perform erp.require_permission('settings.erp.view');
 perform erp.pocket_period_lock_v1();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 v_batch:=(p_payload->>'batch_id')::uuid;v_reason:=nullif(btrim(p_payload->>'reason'),'');
 if v_reason is null then raise exception 'reason: catatan penyelesaian wajib diisi';end if;
 select * into s from erp.initial_import_production_sources where opening_item_id=(p_payload->>'opening_item_id')::uuid and batch_id=v_batch for update;
 if s.opening_item_id is null or s.bs_case_id is not null then raise exception 'Saldo fisik WIP tidak ditemukan';end if;
 select status into v_po_status from erp.production_orders where id=s.po_id for update;
 if v_po_status in('FINISHED','CANCELLED') then raise exception 'Buka kembali PO sebelum mengubah hasil WIP saldo awal';end if;
 select * into strict i from erp.opening_balance_items where id=s.opening_item_id;
 if i.balance_type<>'WIP' or not exists(select 1 from erp.opening_balance_headers where id=i.opening_id and status='POSTED')
   or not exists(select 1 from erp.migration_batches where id=v_batch and status='POSTED') then raise exception 'Saldo awal harus sudah disahkan';end if;
 select s.qty_pcs-coalesce(sum(o.qty_pcs),0) into v_remaining from erp.initial_import_wip_outputs o where o.opening_item_id=i.id
   and not exists(select 1 from erp.initial_import_wip_output_reversals rv where rv.output_id=o.id);
 if coalesce(p_payload->>'expected_remaining','') !~ '^[0-9]+$' or (p_payload->>'expected_remaining')::numeric<>v_remaining then
  raise exception 'STALE_VERSION: sisa WIP berubah, muat ulang';end if;
 perform set_config('app.change_reason',v_reason,true);
 if v_op='REVERSE' then
  select o.* into v_prior from erp.initial_import_wip_outputs o where o.id=(p_payload->>'output_id')::uuid and o.opening_item_id=i.id
    and not exists(select 1 from erp.initial_import_wip_output_reversals rv where rv.output_id=o.id) for update;
  if v_prior.id is null then raise exception 'Hasil WIP tidak ditemukan atau sudah dibatalkan';end if;
  if erp.fg_lot_has_active_downstream(v_prior.lot_id,'QC_GOOD','INITIAL_IMPORT_WIP',v_prior.id) then raise exception 'Hasil WIP masih dipakai transaksi lanjutan; batalkan transaksi tersebut dahulu';end if;
  if exists(select 1 from erp.contractor_accessory_reimbursement_entitlements where lot_id=v_prior.lot_id and payroll_status<>'UNALLOCATED') then raise exception 'Reimbursement sudah masuk payroll';end if;
  for v_movement in select id from erp.journal_entries where source_type='ACCESSORY_REIMBURSE_ACCRUAL' and source_id=v_prior.lot_id and status='POSTED' loop
   perform erp.reverse_journal(v_movement,v_reason);
  end loop;
  update erp.contractor_accessory_reimbursement_entitlements set payroll_status='CANCELLED' where lot_id=v_prior.lot_id and payroll_status='UNALLOCATED';
  for v_movement in select id from erp.fg_stock_movements where lot_id=v_prior.lot_id and source_type='INITIAL_IMPORT_WIP' and source_id=v_prior.id and movement_type='QC_GOOD'
   and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=erp.fg_stock_movements.id) loop
   perform erp.reverse_fg_movement(v_movement,v_reason);
  end loop;
  v_at:=statement_timestamp();v_date:=erp._cp3_business_date(v_at);
  insert into erp.initial_import_wip_output_reversals(output_id,reason,physical_at,created_by) values(v_prior.id,v_reason,v_at,erp.current_app_user_id());
  update erp.fg_lots set lot_origin='VOIDED_PRODUCTION',is_open=false where id=v_prior.lot_id;
  insert into erp.wip_stage_events(po_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by,notes)
   values(s.po_id,'FINISHED',s.stage,v_prior.qty_pcs,i.contractor_id,'INITIAL_IMPORT_WIP_REVERSE',v_prior.id,v_at,erp.current_app_user_id(),v_reason);
  v_output:=v_prior.id;v_lot:=v_prior.lot_id;
 elsif v_op='COMPLETE' then
  if coalesce(p_payload->>'qty_pcs','') !~ '^[1-9][0-9]{0,9}$' or (p_payload->>'qty_pcs')::numeric>v_remaining then raise exception 'qty_pcs: jumlah harus bulat positif dan tidak melebihi sisa WIP';end if;
  v_qty:=(p_payload->>'qty_pcs')::integer;
  if coalesce(p_payload->>'date','') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'date: gunakan YYYY-MM-DD';end if;
  v_date:=(p_payload->>'date')::date;
  if v_date::text<>p_payload->>'date' or v_date<(select opening_date from erp.opening_balance_headers where id=i.opening_id)
    or v_date>erp._cp3_business_date(statement_timestamp()) then raise exception 'date: tanggal hasil harus sejak cutover dan tidak di masa depan';end if;
  select p.id into v_product from erp.products p join erp.production_orders po on po.id=s.po_id
    where p.sku=p_payload->>'product_sku' and p.is_active and p.model_id=po.model_id and p.size_id=s.size_id;
  if v_product is null then raise exception 'product_sku: pilih produk aktif dengan model PO dan ukuran saldo yang sama';end if;
  select id into v_location from erp.locations where location_code=p_payload->>'location_code' and is_active and location_type='FG_WAREHOUSE';
  if v_location is null then raise exception 'location_code: pilih gudang barang jadi aktif';end if;
  v_at:=erp.product_opening_physical_at(v_product,v_date);v_output:=gen_random_uuid();
  insert into erp.fg_lots(lot_number,po_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,is_open,lot_origin)
   values('OWIP-'||v_output::text,s.po_id,v_product,v_qty,0,v_at,true,'PRODUCTION') returning id into v_lot;
  insert into erp.initial_import_wip_outputs(id,opening_item_id,lot_id,qty_pcs,physical_at,reason,created_by)
   values(v_output,i.id,v_lot,v_qty,v_at,v_reason,erp.current_app_user_id());
  perform erp.post_fg_movement(v_product,v_lot,v_location,'GRADE_A','QC_GOOD',v_qty,0,null,'INITIAL_IMPORT_WIP',v_output,v_at,v_reason,false);
  perform erp.ensure_fg_accessory_cost_snapshot(v_lot);
  perform erp.post_accessory_reimbursement_accrual(v_lot);
  insert into erp.wip_stage_events(po_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by,notes)
   values(s.po_id,s.stage,'FINISHED',v_qty,i.contractor_id,'INITIAL_IMPORT_WIP',v_output,v_at,erp.current_app_user_id(),v_reason);
 else raise exception 'Aksi hasil WIP tidak dikenal';end if;
 perform erp.rebuild_po_hpp(s.po_id,'Penyelesaian atau inverse WIP saldo awal');
 perform erp.propagate_conversion_hpp_for_po(s.po_id);
 perform erp.sync_po_hpp_to_gl(s.po_id,v_date);
 return jsonb_build_object('output_id',v_output,'lot_id',v_lot,'operation',v_op);
end;$function$;"""

def extend_production_lifecycle(functions):
    def change(i,old,new,count=1):
        assert functions[i].count(old)==count,(i,old)
        functions[i]=functions[i].replace(old,new)
    functions.update({
        'erp.sync_initial_import_bs_value_v1(uuid,date)':BS_VALUE,
        'erp.sync_initial_import_bs_disposition_v1()':BS_TRIGGER,
        'erp.guard_initial_import_po_completion_v1()':PO_GUARD,
        'erp.complete_initial_import_wip_v1(jsonb)':COMPLETE,
    })
    i='erp.save_initial_import_action_v1(text,jsonb,uuid)'
    change(i,"'ALLOCATE_CASH_ADVANCE','PREPAYMENT')","'ALLOCATE_CASH_ADVANCE','PREPAYMENT','WIP_OUTPUT')")
    change(i," elsif v_action='PREPAYMENT' then",r""" elsif v_action='WIP_OUTPUT' then
   v_batch:=(p_payload->>'batch_id')::uuid;
   v_result:=erp.complete_initial_import_wip_v1(p_payload);
   v_result:=v_result||jsonb_build_object('request_id',p_client_request_id,'action',v_action,'batch_id',v_batch,'status','POSTED');
   return erp._idempotency_complete('save_initial_import_action_v1',p_client_request_id,v_result);
 elsif v_action='PREPAYMENT' then""")
    i='erp.initial_import_production_rows_v1(uuid)'
    change(i,'where opening_item_id=i.id) o on true','where opening_item_id=i.id and not exists(select 1 from erp.initial_import_wip_output_reversals rv where rv.output_id=erp.initial_import_wip_outputs.id)) o on true')
    change(i,"'cutover_date',h.opening_date",r"""'outputs',coalesce((select jsonb_agg(jsonb_build_object('id',o.id,'qty_pcs',o.qty_pcs,'date',erp._cp3_business_date(o.physical_at),'reversed',exists(select 1 from erp.initial_import_wip_output_reversals rv where rv.output_id=o.id)) order by o.created_at,o.id) from erp.initial_import_wip_outputs o where o.opening_item_id=i.id),'[]'::jsonb),
  'cutover_date',h.opening_date""")
    i='erp.get_wip_control_v1(text,uuid,text,text)'
    change(i,"'opening_rows',erp.initial_import_production_rows_v1(null)",r"""'opening_rows',coalesce((select jsonb_agg(x-'original_amount'-'current_amount'-'accessory_cost_included')
     from jsonb_array_elements(erp.initial_import_production_rows_v1(null)) x
     where p_pattern_id is null and (v_filter='ALL' or ((x->>'remaining_qty_pcs')::integer>0)=(v_filter='ACTIVE'))
       and (v_query is null or lower(concat_ws(' ',x->>'po_number',x->>'source_key',x->>'size_code',x->>'contractor_name',x->>'vendor_name')) like '%'||v_query||'%')),'[]'::jsonb)""")

TRIGGERS=r"""
create trigger initial_import_bs_disposition after insert or delete on erp.bs_resolutions
 for each row execute function erp.sync_initial_import_bs_disposition_v1();
create trigger initial_import_po_completion before update on erp.production_orders
 for each row execute function erp.guard_initial_import_po_completion_v1();
"""
