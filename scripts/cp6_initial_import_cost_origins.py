"""Split imported receipts between remaining raw stock and consumed cost origins."""

VALIDATE=r"""create or replace function erp.validate_initial_import_cost_origins_v1(p_batch uuid) returns void
language plpgsql security definer set search_path='' as $function$
declare r record;j jsonb;k text;t jsonb;v_receipt jsonb;v_qty numeric;v_amount numeric;v_basis numeric;
begin
 perform erp.require_owner_admin();
 for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPENING_COST_ORIGIN' loop
  begin
   j:=r.normalized_payload;
   foreach k in array array['supplier_code','receipt_number','receipt_line_number','target_source_key','qty'] loop
    if nullif(j->>k,'') is null then raise exception '%: asal biaya wajib lengkap',k;end if;
   end loop;
   v_qty:=(j->>'qty')::numeric;
   if v_qty<=0 or v_qty<>round(v_qty,6) or v_qty::text in('NaN','Infinity','-Infinity') then raise exception 'qty: asal biaya harus positif maksimal enam desimal';end if;
   perform v_qty::numeric(18,6);
   if (select count(*) from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='UNINVOICED_RECEIPT'
     and s.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and lower(btrim(s.normalized_payload->>'receipt_number'))=lower(btrim(j->>'receipt_number'))
     and lower(btrim(s.normalized_payload->>'receipt_line_number'))=lower(btrim(j->>'receipt_line_number')))<>1 then
    raise exception 'receipt_number: asal biaya harus menunjuk tepat satu baris penerimaan';end if;
   select s.normalized_payload into v_receipt from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='UNINVOICED_RECEIPT'
     and s.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and lower(btrim(s.normalized_payload->>'receipt_number'))=lower(btrim(j->>'receipt_number'))
     and lower(btrim(s.normalized_payload->>'receipt_line_number'))=lower(btrim(j->>'receipt_line_number'));
   if (select count(*) from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
      and s.normalized_payload->>'opening_source_key'=j->>'target_source_key')<>1 then raise exception 'target_source_key: tujuan harus tepat satu rincian WIP/BS/FG';end if;
   select s.normalized_payload into t from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
     and s.normalized_payload->>'opening_source_key'=j->>'target_source_key' and s.validation_status='VALID';
   if t is null or upper(t->>'balance_type') not in('WIP','BS','FINISHED_GOODS')
     or (upper(t->>'balance_type') in('WIP','BS') and nullif(t->>'po_number','') is null)
     or upper(t->>'hpp_input_method')='PRICE_PERCENT' then raise exception 'target_source_key: perlu saldo fisik valid dengan nilai manual yang terurai';end if;
   if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_COST_ORIGIN' and s.id<>r.id
     and s.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and lower(btrim(s.normalized_payload->>'receipt_number'))=lower(btrim(j->>'receipt_number'))
     and lower(btrim(s.normalized_payload->>'receipt_line_number'))=lower(btrim(j->>'receipt_line_number'))
     and s.normalized_payload->>'target_source_key'=j->>'target_source_key') then raise exception 'target_source_key: asal dan tujuan biaya ditulis dua kali';end if;
   select sum(round((s.normalized_payload->>'qty')::numeric*(p.normalized_payload->>'unit_cost')::numeric,2)) into v_amount
   from erp.migration_staging_rows s join erp.migration_staging_rows p on p.batch_id=s.batch_id and p.entity_type='UNINVOICED_RECEIPT'
     and p.normalized_payload->>'supplier_code'=s.normalized_payload->>'supplier_code'
     and lower(btrim(p.normalized_payload->>'receipt_number'))=lower(btrim(s.normalized_payload->>'receipt_number'))
     and lower(btrim(p.normalized_payload->>'receipt_line_number'))=lower(btrim(s.normalized_payload->>'receipt_line_number'))
   where s.batch_id=p_batch and s.entity_type='OPENING_COST_ORIGIN' and s.normalized_payload->>'target_source_key'=j->>'target_source_key';
   v_basis:=round(coalesce(nullif(t->>'amount','')::numeric,(t->>'qty')::numeric*(t->>'unit_cost')::numeric),2);
   if v_basis is null or v_amount is null or v_amount>v_basis then raise exception 'target_source_key: biaya bahan terurai melebihi seluruh nilai saldo tujuan';end if;
  exception when others then update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm) where id=r.id;
  end;
 end loop;
end;$function$;"""

RECOST=r"""create or replace function erp.recost_initial_import_origins_v1(p_purchase_item uuid) returns void
language plpgsql security definer set search_path='' as $function$
declare r record;v_target numeric;v_previous numeric;v_delta numeric;v_date date;v_event uuid;v_journal uuid;
 v_lot uuid;v_hpp erp.hpp_versions%rowtype;v_new uuid;v_po uuid;v_qty integer;
begin
 perform erp.require_internal();
 perform erp.pocket_period_lock_v1();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 v_date:=coalesce(erp.invoice_recost_economic_date_v1(),erp._cp3_business_date(statement_timestamp()));
 for r in select i.* from erp.opening_balance_items i where i.id in(
   select opening_item_id from erp.initial_import_cost_origins where purchase_item_id=p_purchase_item) order by i.id for update loop
  select coalesce(sum(round(o.material_qty*erp.material_purchase_current_unit_cost(o.purchase_item_id),2)
    -round(o.material_qty*o.unit_cost_snapshot,2)),0) into v_target from erp.initial_import_cost_origins o where o.opening_item_id=r.id;
  select coalesce(sum(new_delta-previous_delta),0) into v_previous from erp.initial_import_origin_cost_events where opening_item_id=r.id;
  v_delta:=v_target-v_previous;if v_delta=0 then continue;end if;
  if round(coalesce(r.amount,r.qty*r.unit_cost_snapshot),2)+v_target<0 then raise exception 'Nilai sumber setelah koreksi tidak boleh negatif';end if;
  v_event:=gen_random_uuid();v_po:=null;
  select po_id into v_po from erp.initial_import_production_sources where opening_item_id=r.id;
  insert into erp.initial_import_origin_cost_events(id,opening_item_id,previous_delta,new_delta,economic_date,created_by)
   values(v_event,r.id,v_previous,v_target,v_date,erp.current_app_user_id());
  if r.balance_type='FINISHED_GOODS' then
   select lot_id into strict v_lot from erp.fg_stock_movements where source_type='OPENING_BALANCE_ITEM' and source_id=r.id and movement_type='OPENING';
   select * into strict v_hpp from erp.hpp_versions where lot_id=v_lot and is_current for update;
   update erp.hpp_versions set is_current=false where id=v_hpp.id;
   insert into erp.hpp_versions(lot_id,version_no,cost_state,qty_basis_pcs,total_cost,is_current,supersedes_id,calculation_reason,created_by)
    values(v_lot,v_hpp.version_no+1,'ADJUSTED',v_hpp.qty_basis_pcs,v_hpp.total_cost+v_delta,true,v_hpp.id,'Koreksi asal bahan sebelum cutover',erp.current_app_user_id()) returning id into v_new;
   perform erp.sync_opening_lot_hpp_to_gl(v_lot,v_date);
   -- The native opening-lot synchronizer owns FG/COGS and offsets opening equity.
   -- Replace only that source offset with the invoice's material-inventory leg.
   v_journal:=erp.post_journal('INITIAL_IMPORT_ORIGIN_RECOST',v_event,v_date,'Asal biaya bahan pada FG awal',jsonb_build_array(
    jsonb_build_object('mapping_key','OPENING_EQUITY','debit',greatest(v_delta,0),'credit',greatest(-v_delta,0)),
    jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',greatest(-v_delta,0),'credit',greatest(v_delta,0))));
  else
   if v_po is null then raise exception 'Asal WIP/BS harus terhubung ke PO';end if;
   v_journal:=erp.post_journal('INITIAL_IMPORT_ORIGIN_RECOST',v_event,v_date,'Asal biaya bahan pada WIP/BS awal',jsonb_build_array(
    jsonb_build_object('mapping_key','WIP','debit',greatest(v_delta,0),'credit',greatest(-v_delta,0),'po_id',v_po),
    jsonb_build_object('mapping_key','MATERIAL_INVENTORY','debit',greatest(-v_delta,0),'credit',greatest(v_delta,0))));
   perform erp.sync_initial_import_bs_value_v1(r.id,v_date);
   perform erp.rebuild_po_hpp(v_po,'Koreksi asal bahan sebelum cutover');
   perform erp.propagate_conversion_hpp_for_po(v_po);
   perform erp.sync_po_hpp_to_gl(v_po,v_date);
  end if;
  update erp.initial_import_origin_cost_events set journal_entry_id=v_journal where id=v_event;
 end loop;
end;$function$;"""

def extend_cost_origin_contract(functions):
    def change(identity,old,new,count=1):
        assert functions[identity].count(old)==count,(identity,old)
        functions[identity]=functions[identity].replace(old,new)
    functions.update({'erp.validate_initial_import_cost_origins_v1(uuid)':VALIDATE,'erp.recost_initial_import_origins_v1(uuid)':RECOST})
    i=next(k for k in functions if k.startswith('erp.stage_migration_row('))
    change(i,"'UNINVOICED_RECEIPT'","'OPENING_COST_ORIGIN','UNINVOICED_RECEIPT'")
    i='erp._validate_migration_batch_base(uuid)'
    change(i,"'UNINVOICED_RECEIPT'","'OPENING_COST_ORIGIN','UNINVOICED_RECEIPT'")
    i='erp.finalize_migration_batch(uuid)'
    change(i,"'CASH_ACCOUNT','UNINVOICED_RECEIPT'","'CASH_ACCOUNT','OPENING_COST_ORIGIN','UNINVOICED_RECEIPT'")
    i='erp.save_initial_import_action_v1(text,jsonb,uuid)'
    change(i,'     perform erp.validate_initial_import_receipts_v1(b.id);','     perform erp.validate_initial_import_cost_origins_v1(b.id);\n     perform erp.validate_initial_import_receipts_v1(b.id);')
    i='erp.check_initial_import_receipt_v1(uuid,uuid)'
    change(i,"'qty','unit_cost','opening_source_key','control_key'","'qty','unit_cost','control_key'")
    change(i,"v_key:=btrim(j->>'opening_source_key');","v_key:=nullif(btrim(j->>'opening_source_key'),'');")
    start=" if (select count(*) from erp.migration_staging_rows where batch_id=p_batch_id\n   and entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM')"
    begin=functions[i].index(start);end=functions[i].index(' select id into v_party',begin)
    functions[i]=functions[i][:begin]+r"""
 if v_key is not null then
  if (select count(*) from erp.migration_staging_rows where batch_id=p_batch_id
   and entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM') and normalized_payload->>'opening_source_key'=v_key)<>1 then
   raise exception 'opening_source_key: harus menunjuk tepat satu rincian stok dalam batch ini';end if;
  select * into s from erp.migration_staging_rows where batch_id=p_batch_id
   and entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM') and normalized_payload->>'opening_source_key'=v_key;
  if s.validation_status<>'VALID' or (s.entity_type='OPENING_BALANCE_ITEM' and upper(s.normalized_payload->>'balance_type')<>'MATERIAL') then
   raise exception 'opening_source_key: sumber harus rincian stok bahan yang valid';end if;
  if s.normalized_payload->>'material_sku' is distinct from j->>'material_sku'
   or s.normalized_payload->>'location_code' is distinct from j->>'location_code'
   or (s.normalized_payload->>'unit_cost')::numeric is distinct from v_cost then
   raise exception 'opening_source_key: bahan, gudang, dan biaya harus sama dengan stok awal';end if;
  if nullif(s.normalized_payload->>'supplier_code','') is not null and s.normalized_payload->>'supplier_code'<>j->>'supplier_code' then
   raise exception 'supplier_code: supplier berbeda dengan stok asal';end if;
 end if;
 if v_qty is distinct from coalesce((s.normalized_payload->>case when s.entity_type='MATERIAL_ROLL' then 'opening_qty' else 'qty' end)::numeric,0)
   +coalesce((select sum((x.normalized_payload->>'qty')::numeric) from erp.migration_staging_rows x where x.batch_id=p_batch_id
     and x.entity_type='OPENING_COST_ORIGIN' and x.validation_status='VALID'
     and x.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and lower(btrim(x.normalized_payload->>'receipt_number'))=lower(v_number)
     and lower(btrim(x.normalized_payload->>'receipt_line_number'))=lower(v_line)),0) then
  raise exception 'opening_source_key: jumlah belum ditagih harus tepat sama dengan sisa bahan + seluruh asal biaya yang sudah terpakai';end if;
 if not exists(select 1 from erp.materials where material_sku=j->>'material_sku' and is_active)
   and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='MATERIAL' and validation_status='VALID' and normalized_payload->>'material_sku'=j->>'material_sku') then
  raise exception 'material_sku: bahan aktif tidak ditemukan';end if;
 if not exists(select 1 from erp.locations where location_code=j->>'location_code' and is_active and location_type='RAW_MATERIAL_WAREHOUSE')
   and not exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='LOCATION' and validation_status='VALID' and normalized_payload->>'location_code'=j->>'location_code' and normalized_payload->>'location_type'='RAW_MATERIAL_WAREHOUSE') then
  raise exception 'location_code: gudang bahan aktif tidak ditemukan';end if;
"""+functions[i][end:]
    i='erp.apply_initial_import_receipts_v1(uuid)'
    change(i,' v_opening erp.opening_balance_items%rowtype;v_cutover date;',' v_opening erp.opening_balance_items%rowtype;v_cutover date;v_material uuid;v_location uuid;v_origin record;v_target uuid;')
    change(i,'   select i.* into strict v_opening','   select i.* into v_opening')
    change(i,"   if v_opening.qty<>(j->>'qty')::numeric or v_opening.unit_cost_snapshot<>(j->>'unit_cost')::numeric","   if v_opening.id is not null and (v_opening.unit_cost_snapshot<>(j->>'unit_cost')::numeric")
    change(i,'and m.roll_id is not distinct from v_opening.roll_id) then','and m.roll_id is not distinct from v_opening.roll_id)) then')
    needle='   select purchase_id into v_purchase from erp.initial_import_receipt_headers'
    change(i,needle,"   select id into strict v_material from erp.materials where material_sku=j->>'material_sku' and is_active;\n   select id into strict v_location from erp.locations where location_code=j->>'location_code' and is_active and location_type='RAW_MATERIAL_WAREHOUSE';\n"+needle)
    change(i,'v_supplier,b.cutover_at,v_opening.location_id,','v_supplier,b.cutover_at,v_location,')
    change(i,"values(v_purchase,v_opening.material_id,v_opening.qty,v_opening.unit_cost_snapshot,'ESTIMATED'","values(v_purchase,v_material,(j->>'qty')::numeric,(j->>'unit_cost')::numeric,'ESTIMATED'")
    needle="   update erp.migration_staging_rows set posted_entity_type='OPENING_UNINVOICED_RECEIPT_ITEM'"
    change(i,needle,r"""
   for v_origin in select * from erp.migration_staging_rows x where x.batch_id=b.id and x.entity_type='OPENING_COST_ORIGIN'
     and x.normalized_payload->>'supplier_code'=j->>'supplier_code'
     and lower(btrim(x.normalized_payload->>'receipt_number'))=lower(btrim(j->>'receipt_number'))
     and lower(btrim(x.normalized_payload->>'receipt_line_number'))=lower(btrim(j->>'receipt_line_number')) loop
    select opening_item_id into strict v_target from erp.initial_import_opening_stock_sources where batch_id=b.id and source_key=v_origin.normalized_payload->>'target_source_key';
    insert into erp.initial_import_cost_origins(source_row_id,purchase_item_id,opening_item_id,material_qty,unit_cost_snapshot)
     values(v_origin.id,v_item,v_target,(v_origin.normalized_payload->>'qty')::numeric,(j->>'unit_cost')::numeric);
    update erp.migration_staging_rows set posted_entity_type='OPENING_COST_ORIGIN',posted_entity_id=v_origin.id,posted_at=statement_timestamp(),updated_at=statement_timestamp() where id=v_origin.id;
   end loop;
"""+needle)
    i='erp.refresh_material_purchase_item_cost(uuid)'
    change(i,'and m.movement_type=\'OPENING\' and m.qty_signed=i.qty;',"and m.movement_type='OPENING' and m.qty_signed=(select oi.qty from erp.opening_balance_items oi where oi.id=l.opening_item_id);")
    change(i,"    if not found then raise exception 'Opening source movement missing for imported receipt %',i.id;end if;\n    perform erp.recalculate_material_cost(i.material_id,h.physical_at);", "    if not found and exists(select 1 from erp.initial_import_receipt_lines where purchase_item_id=i.id and opening_item_id is not null) then raise exception 'Opening source movement missing for imported receipt %',i.id;end if;\n    if exists(select 1 from erp.initial_import_receipt_lines where purchase_item_id=i.id and opening_item_id is not null) then perform erp.recalculate_material_cost(i.material_id,h.physical_at);end if;\n    perform erp.recost_initial_import_origins_v1(i.id);")
    i='erp._cp6_supplier_cent_state(uuid[])'
    change(i,'then round(i.qty*erp.material_purchase_current_unit_cost(i.id),2)',r"""then coalesce((select round(oi.qty*erp.material_purchase_current_unit_cost(i.id),2) from erp.initial_import_receipt_lines l join erp.opening_balance_items oi on oi.id=l.opening_item_id where l.purchase_item_id=i.id),0)
       +coalesce((select sum(round(o.material_qty*erp.material_purchase_current_unit_cost(i.id),2)) from erp.initial_import_cost_origins o where o.purchase_item_id=i.id),0)""")
    i='erp.run_v267_financial_truth_checks()'
    change(i,"or oh.status is distinct from 'POSTED'","or (l.opening_item_id is not null and oh.status is distinct from 'POSTED')")
    change(i,"or oi.balance_type is distinct from 'MATERIAL' or pi.qty is distinct from oi.qty", "or (l.opening_item_id is not null and oi.balance_type is distinct from 'MATERIAL')\n        or pi.qty is distinct from coalesce(oi.qty,0)+coalesce((select sum(material_qty) from erp.initial_import_cost_origins where purchase_item_id=pi.id),0)")
    change(i,"or pi.material_id is distinct from oi.material_id or pi.unit_price is distinct from oi.unit_cost_snapshot\n        or oi.location_id is distinct from h.location_id", "or (l.opening_item_id is not null and (pi.material_id is distinct from oi.material_id or pi.unit_price is distinct from oi.unit_cost_snapshot\n        or oi.location_id is distinct from h.location_id))")
    change(i,"or (select count(*) from erp.material_stock_movements m where m.source_type='OPENING_BALANCE_ITEM'\n          and m.source_id=oi.id and m.movement_type='OPENING' and m.qty_signed=oi.qty)<>1", "or (l.opening_item_id is not null and (select count(*) from erp.material_stock_movements m where m.source_type='OPENING_BALANCE_ITEM'\n          and m.source_id=oi.id and m.movement_type='OPENING' and m.qty_signed=oi.qty)<>1)")
    i='erp.get_initial_import_workspace_v1(uuid)'
    change(i,"       'qty',pi.qty,'unmatched_qty'", "       'qty',pi.qty,'on_hand_at_cutover',coalesce((select qty from erp.opening_balance_items where id=rl.opening_item_id),0),\n       'consumed_before_cutover',coalesce((select sum(material_qty) from erp.initial_import_cost_origins where purchase_item_id=pi.id),0),'unmatched_qty'")
