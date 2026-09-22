"""Cutover physical positions and consumed receipt provenance; no historic issue/payroll.

The immutable opening item remains the valuation baseline. Receipt origins are
attribution within that baseline, never another stock receipt or opening value.
"""
import json
from pathlib import Path

PREDECESSOR=json.loads(Path('docs/evidence/cp6-initial-import-production-predecessor.json').read_text())['functions']

SCHEMA=r"""
create table erp.initial_import_production_sources(
 opening_item_id uuid primary key references erp.opening_balance_items(id) on delete cascade,
 source_row_id uuid not null unique references erp.migration_staging_rows(id),
 batch_id uuid not null references erp.migration_batches(id),
 po_id uuid not null references erp.production_orders(id),size_id uuid not null references erp.sizes(id),
 stage text not null check(stage in('SEWING','LAUNDRY','QC')),
 qty_pcs integer not null check(qty_pcs>0),original_amount numeric(20,2) not null check(original_amount>=0),
 accessory_cost_included boolean not null,bs_case_id uuid unique references erp.bs_cases(id)
);
create index initial_import_production_po on erp.initial_import_production_sources(po_id);
create table erp.initial_import_cost_origins(
 source_row_id uuid primary key references erp.migration_staging_rows(id),
 purchase_item_id uuid not null references erp.material_purchase_items(id),
 opening_item_id uuid not null references erp.opening_balance_items(id),
 material_qty numeric(18,6) not null check(material_qty>0),unit_cost_snapshot numeric(18,6) not null check(unit_cost_snapshot>=0),
 unique(purchase_item_id,opening_item_id)
);
create index initial_import_cost_origin_target on erp.initial_import_cost_origins(opening_item_id);
create table erp.initial_import_origin_cost_events(
 id uuid primary key default gen_random_uuid(),opening_item_id uuid not null references erp.opening_balance_items(id),
 previous_delta numeric(20,2) not null,new_delta numeric(20,2) not null,economic_date date not null,
 journal_entry_id uuid references erp.journal_entries(id),created_at timestamptz not null default clock_timestamp(),
 created_by uuid not null references erp.app_users(id)
);
create index initial_import_origin_cost_event_target on erp.initial_import_origin_cost_events(opening_item_id,created_at,id);
create table erp.initial_import_wip_outputs(
 id uuid primary key default gen_random_uuid(),opening_item_id uuid not null references erp.initial_import_production_sources(opening_item_id),
 lot_id uuid not null unique references erp.fg_lots(id),qty_pcs integer not null check(qty_pcs>0),
 physical_at timestamptz not null,reason text not null,created_at timestamptz not null default clock_timestamp(),
 created_by uuid not null references erp.app_users(id)
);
create index initial_import_wip_output_source on erp.initial_import_wip_outputs(opening_item_id);
create table erp.initial_import_bs_value_events(
 id uuid primary key default gen_random_uuid(),opening_item_id uuid not null references erp.initial_import_production_sources(opening_item_id),
 disposed_qty integer not null check(disposed_qty>=0),previous_amount numeric(20,2) not null,target_amount numeric(20,2) not null,
 economic_date date not null,journal_entry_id uuid references erp.journal_entries(id),
 created_at timestamptz not null default clock_timestamp(),created_by uuid not null references erp.app_users(id)
);
create index initial_import_bs_value_target on erp.initial_import_bs_value_events(opening_item_id,created_at,id);
alter table erp.initial_import_receipt_lines alter column opening_item_id drop not null;
alter table erp.initial_import_production_sources enable row level security;
alter table erp.initial_import_cost_origins enable row level security;
alter table erp.initial_import_origin_cost_events enable row level security;
alter table erp.initial_import_wip_outputs enable row level security;
alter table erp.initial_import_bs_value_events enable row level security;
revoke all on erp.initial_import_production_sources,erp.initial_import_cost_origins,erp.initial_import_origin_cost_events,
 erp.initial_import_wip_outputs,erp.initial_import_bs_value_events from public,anon,authenticated,service_role;
"""

VALIDATE=r"""create or replace function erp.validate_initial_import_production_v1(p_batch uuid) returns void
language plpgsql security definer set search_path='' as $function$
declare r record;j jsonb;k text;t text;q numeric;v numeric;v_po jsonb;v_model text;v_contractor text;
begin
 perform erp.require_owner_admin();
 for r in select * from erp.migration_staging_rows where batch_id=p_batch and entity_type='OPENING_BALANCE_ITEM'
   and (nullif(normalized_payload->>'po_number','') is not null or
     (upper(normalized_payload->>'balance_type') in('WIP','BS') and nullif(normalized_payload->>'opening_source_key','') is not null)) loop
  begin
   j:=r.normalized_payload;t:=upper(j->>'balance_type');
   if t not in('WIP','BS') then raise exception 'po_number: hanya untuk saldo fisik WIP/BS';end if;
   foreach k in array array['po_number','size_code','stage','qty','opening_source_key','accessory_cost_included'] loop
    if nullif(j->>k,'') is null then raise exception '%: wajib untuk saldo fisik WIP/BS',k;end if;
   end loop;
   if j->>'accessory_cost_included' not in('true','false') then raise exception 'accessory_cost_included: isi true atau false';end if;
   if j->>'stage' not in('SEWING','LAUNDRY','QC') or (t='WIP' and j->>'stage'='QC') then
    raise exception 'stage: WIP memakai SEWING/LAUNDRY; BS boleh QC';end if;
   if j->>'stage'='SEWING' and nullif(j->>'contractor_code','') is null then raise exception 'contractor_code: mandor pemegang wajib diisi';end if;
   if j->>'stage'='LAUNDRY' and nullif(j->>'vendor_code','') is null then raise exception 'vendor_code: laundry pemegang wajib diisi';end if;
   if t='BS' and nullif(j->>'product_sku','') is null then raise exception 'product_sku: BS bernilai memerlukan identitas produk';end if;
   q:=(j->>'qty')::numeric;v:=coalesce(nullif(j->>'amount','')::numeric,q*nullif(j->>'unit_cost','')::numeric);
   if q<=0 or q<>trunc(q) or q>2147483647 or v is null or v<0 or v<>round(v,2) then
    raise exception 'qty: saldo fisik perlu pcs bulat positif dan nilai tepat dua desimal (nol boleh)';end if;
   if nullif(j->>'unit_cost','') is not null and (j->>'unit_cost')::numeric<0 then raise exception 'unit_cost: biaya tidak boleh negatif';end if;
   if nullif(j->>'amount','') is not null and nullif(j->>'unit_cost','') is not null
     and (j->>'amount')::numeric<>round(q*(j->>'unit_cost')::numeric,2) then raise exception 'amount: nilai harus sama dengan jumlah x biaya';end if;
   select s.normalized_payload into v_po from erp.migration_staging_rows s where s.batch_id=p_batch
     and s.entity_type='OPEN_PO' and s.normalized_payload->>'po_number'=j->>'po_number' and s.validation_status='VALID';
   if v_po is null then raise exception 'po_number: saldo fisik wajib menunjuk OPEN_PO valid dalam batch yang sama';end if;
   if v_po->>'status' in('FINISHED','CANCELLED') then raise exception 'po_number: saldo fisik belum selesai tidak boleh masuk PO selesai/batal';end if;
   if nullif(j->>'model_code','') is not null and j->>'model_code'<>v_po->>'model_code' then raise exception 'model_code: model berbeda dengan PO';end if;
   if exists(select 1 from erp.production_orders p where p.po_number=j->>'po_number' and p.migration_batch_id is distinct from p_batch) then
    raise exception 'po_number: PO sudah memiliki riwayat di luar batch ini';end if;
   if not exists(select 1 from erp.sizes where size_code=j->>'size_code' and is_active)
      and not exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='SIZE'
        and s.validation_status='VALID' and s.normalized_payload->>'size_code'=j->>'size_code') then raise exception 'size_code: ukuran aktif tidak ditemukan';end if;
   select m.model_code into v_model from erp.products p join erp.product_models m on m.id=p.model_id where p.sku=j->>'product_sku';
   if v_model is null then select normalized_payload->>'model_code' into v_model from erp.migration_staging_rows where batch_id=p_batch
     and entity_type='PRODUCT' and validation_status='VALID' and normalized_payload->>'sku'=j->>'product_sku';end if;
   if v_model is not null and v_model<>v_po->>'model_code' then raise exception 'product_sku: produk berbeda model dengan PO';end if;
   if exists(select 1 from erp.migration_staging_rows s where s.batch_id=p_batch and s.entity_type='OPENING_BALANCE_ITEM'
     and upper(s.normalized_payload->>'balance_type')='WIP' and nullif(s.normalized_payload->>'po_number','') is null) then
    raise exception 'po_number: jangan campur ringkasan WIP tanpa PO dengan rincian fisik WIP/BS';end if;
  exception when others then update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm) where id=r.id;
  end;
 end loop;
end;$function$;"""

LINK=r"""create or replace function erp.link_initial_import_production_v1(p_batch uuid,p_row uuid,p_item uuid) returns void
language plpgsql security definer set search_path='' as $function$
declare j jsonb;i erp.opening_balance_items%rowtype;v_po uuid;v_size uuid;
begin
 perform erp.require_owner_admin();
 select normalized_payload into strict j from erp.migration_staging_rows where id=p_row and batch_id=p_batch;
 if nullif(j->>'po_number','') is null then return;end if;
 select * into strict i from erp.opening_balance_items where id=p_item;
 select id into strict v_po from erp.production_orders where po_number=j->>'po_number' and is_legacy and migration_batch_id=p_batch;
 select id into strict v_size from erp.sizes where size_code=j->>'size_code' and is_active;
 insert into erp.initial_import_production_sources(opening_item_id,source_row_id,batch_id,po_id,size_id,stage,qty_pcs,original_amount,accessory_cost_included)
 values(p_item,p_row,p_batch,v_po,v_size,j->>'stage',i.qty::integer,round(coalesce(i.amount,i.qty*i.unit_cost_snapshot),2),(j->>'accessory_cost_included')::boolean);
end;$function$;"""

VALUE=r"""create or replace function erp.initial_import_source_value_v1(p_item uuid) returns numeric
language sql stable security definer set search_path='' as $function$
 select round(coalesce(i.amount,i.qty*i.unit_cost_snapshot,0),2)+coalesce((
  select sum(e.new_delta-e.previous_delta) from erp.initial_import_origin_cost_events e where e.opening_item_id=i.id),0)
 from erp.opening_balance_items i where i.id=p_item;
$function$;"""

LOT_COST=r"""create or replace function erp.initial_import_lot_cost_v1(p_lot uuid) returns numeric
language sql stable security definer set search_path='' as $function$
 select coalesce(sum(erp.initial_import_source_value_v1(s.opening_item_id)*l.initial_qty_pcs/s.qty_pcs),0)
 from erp.fg_lots l join erp.initial_import_production_sources s on
   exists(select 1 from erp.initial_import_wip_outputs o where o.lot_id=l.id and o.opening_item_id=s.opening_item_id)
   or exists(select 1 from erp.rework_orders ro where ro.good_fg_lot_id=l.id and ro.bs_case_id=s.bs_case_id and ro.status='COMPLETED')
 where l.id=p_lot and l.lot_origin='PRODUCTION';
$function$;"""

READER=r"""create or replace function erp.initial_import_production_rows_v1(p_batch uuid default null) returns jsonb
language sql stable security definer set search_path='' as $function$
 select coalesce(jsonb_agg(jsonb_build_object('opening_item_id',s.opening_item_id,'source_key',k.source_key,
  'batch_id',s.batch_id,'po_id',s.po_id,'po_number',p.po_number,'balance_type',i.balance_type,'stage',s.stage,
  'size_code',z.size_code,'qty_pcs',s.qty_pcs,'completed_qty_pcs',coalesce(o.qty,0),'remaining_qty_pcs',
    s.qty_pcs-case when s.bs_case_id is null then coalesce(o.qty,0) else coalesce(br.qty,0) end,
  'contractor_name',c.contractor_name,'vendor_name',v.vendor_name,'bs_case_id',s.bs_case_id,
  'original_amount',s.original_amount::text,'current_amount',erp.initial_import_source_value_v1(s.opening_item_id)::text,
  'cutover_date',h.opening_date,'product_id',i.product_id,'accessory_cost_included',s.accessory_cost_included
 ) order by p.po_number,s.stage,z.size_code,k.source_key),'[]'::jsonb)
 from erp.initial_import_production_sources s join erp.opening_balance_items i on i.id=s.opening_item_id
 join erp.initial_import_opening_stock_sources k on k.opening_item_id=i.id
 join erp.opening_balance_headers h on h.id=i.opening_id and h.status='POSTED'
 join erp.production_orders p on p.id=s.po_id join erp.sizes z on z.id=s.size_id
 left join erp.contractors c on c.id=i.contractor_id left join erp.laundry_vendors v on v.id=i.vendor_id
 left join lateral(select sum(qty_pcs) qty from erp.initial_import_wip_outputs where opening_item_id=i.id) o on true
 left join lateral(select sum(qty_pcs) qty from erp.bs_resolutions where bs_case_id=s.bs_case_id) br on true
 where p_batch is null or s.batch_id=p_batch;
$function$;"""

def extend_production_contract(functions):
    def change(identity,old,new,count=1):
        assert functions[identity].count(old)==count,(identity,old)
        functions[identity]=functions[identity].replace(old,new)
    functions.update({r[0]:r[1] for r in PREDECESSOR})
    functions.update({
        'erp.validate_initial_import_production_v1(uuid)':VALIDATE,
        'erp.link_initial_import_production_v1(uuid,uuid,uuid)':LINK,
        'erp.initial_import_source_value_v1(uuid)':VALUE,
        'erp.initial_import_lot_cost_v1(uuid)':LOT_COST,
        'erp.initial_import_production_rows_v1(uuid)':READER,
    })
    i='erp.validate_initial_import_receipts_v1(uuid)'
    change(i,"upper(r.normalized_payload->>'balance_type')<>'MATERIAL'","upper(r.normalized_payload->>'balance_type') not in('MATERIAL','FINISHED_GOODS','WIP','BS')")
    change(i,'kode unik maksimal 120 karakter hanya untuk stok bahan','kode unik maksimal 120 karakter hanya untuk stok/WIP/BS')
    i='erp.link_initial_import_stock_source_v1(uuid,uuid,uuid)'
    change(i,"i.balance_type='MATERIAL'","i.balance_type in('MATERIAL','FINISHED_GOODS','WIP','BS')")
    change(i,'opening_source_key hanya untuk rincian stok bahan','opening_source_key hanya untuk rincian stok/WIP/BS')
    i='erp.prepare_migration_opening_balance(uuid,text)'
    needle='    perform erp.link_initial_import_stock_source_v1(b.id,r.id,v_opening_item);'
    change(i,needle,needle+'\n    perform erp.link_initial_import_production_v1(b.id,r.id,v_opening_item);',2)
    i='erp.save_initial_import_action_v1(text,jsonb,uuid)'
    change(i,'     perform erp.validate_initial_import_receipts_v1(b.id);','     perform erp.validate_initial_import_production_v1(b.id);\n     perform erp.validate_initial_import_receipts_v1(b.id);')
    i='erp.validate_initial_import_totals_v1(uuid)'
    change(i,"when v_type='BS' then 0","when v_type='BS' then case when nullif(j->>'po_number','') is not null then round(coalesce(nullif(j->>'amount','')::numeric,v_qty*v_cost),2) else 0 end")
    needle="   if (v_entry->>'type' in("
    change(i,needle,"""   if v_entry->>'type'='WIP' and nullif(j->>'qty','') is null and exists(
      select 1 from erp.migration_staging_rows x where x.batch_id=p_batch_id and x.entity_type='OPENING_BALANCE_ITEM'
      and x.normalized_payload->>'control_key'=v_key and nullif(x.normalized_payload->>'po_number','') is not null) then
     raise exception 'qty: total pembanding WIP fisik wajib berisi jumlah pcs';end if;
"""+needle)
    i='erp.post_opening_balance(uuid)'
    change(i,'  v_product_at timestamptz;','  v_product_at timestamptz;v_source erp.initial_import_production_sources%rowtype;v_bs uuid;')
    needle='  for r in select * from erp.opening_balance_items where opening_id=h.id order by id loop\n    if r.balance_type='
    change(i,needle,needle.replace("    if r.balance_type=","    select * into v_source from erp.initial_import_production_sources where opening_item_id=r.id;\n    if r.balance_type="))
    change(i,"jsonb_build_object('mapping_key','WIP','debit',round(v_value,2),'credit',0)","jsonb_build_object('mapping_key','WIP','debit',round(v_value,2),'credit',0,'po_id',v_source.po_id)")
    change(i,"responsible_contractor_id,qty_pcs,status,physical_at,notes)","responsible_contractor_id,responsible_vendor_id,qty_pcs,status,physical_at,notes,legacy_reference)")
    change(i,"null,r.product_id,'UNKNOWN','UNKNOWN','LEGACY',r.contractor_id,r.qty::integer,'OPEN',v_product_at,r.notes);", "v_source.po_id,r.product_id,coalesce(v_source.stage,'UNKNOWN'),'UNKNOWN','LEGACY',r.contractor_id,r.vendor_id,r.qty::integer,'OPEN',v_product_at,r.notes,case when v_source.opening_item_id is not null then 'OPENING:'||r.id::text else null end) returning id into v_bs;\n        if v_source.opening_item_id is not null then\n          update erp.initial_import_production_sources set bs_case_id=v_bs where opening_item_id=r.id;\n          v_value:=v_source.original_amount;\n          if v_value>0 then v_lines:=v_lines||jsonb_build_array(jsonb_build_object('mapping_key','WIP','debit',v_value,'credit',0,'po_id',v_source.po_id));v_debits:=v_debits+v_value;end if;\n        end if;")
    i='erp.rebuild_po_hpp(uuid,text)'
    change(i,'  v_material numeric(24,6):=0;','  v_material numeric(24,6):=0;v_opening_cost numeric(24,6):=0;')
    needle='    v_lot_cost:=v_lot_material+'
    change(i,needle,'    v_opening_cost:=erp.initial_import_lot_cost_v1(r.id);\n    v_lot_cost:=v_opening_cost+v_lot_material+')
    needle="      (v_new_id,'OTHER','Other/adjustment allocation',v_lot_other,'PO',p_po_id);"
    change(i,needle,needle[:-1]+",\n      (v_new_id,'OTHER','Saldo fisik sebelum cutover',v_opening_cost,'INITIAL_IMPORT_PRODUCTION',r.id);")
    i='erp.ensure_fg_accessory_cost_snapshot(uuid)'
    needle="  if exists(select 1 from erp.fg_accessory_cost_snapshots where lot_id=l.id) then return; end if;"
    change(i,needle,"  if exists(select 1 from erp.initial_import_wip_outputs o join erp.initial_import_production_sources s on s.opening_item_id=o.opening_item_id where o.lot_id=l.id and s.accessory_cost_included) then return;end if;\n"+needle)
    i='erp.compute_po_hpp_gl_book_v2620e(uuid)'
    change(i,'  where l.po_id=p_po_id','  where l.po_id=p_po_id and e.source_type<>\'INITIAL_IMPORT_BS_VALUE\'')
    i='erp.run_v268_financial_report_checks()'
    change(i,"        when i.balance_type='WIP' then", "        when i.balance_type='BS' and exists(select 1 from erp.initial_import_production_sources ps where ps.opening_item_id=i.id) then coalesce(i.amount,i.qty*i.unit_cost_snapshot)\n        when i.balance_type='WIP' then")
    change(i,'    )::numeric source_cost',r"""      +coalesce((select sum(erp.initial_import_source_value_v1(ps.opening_item_id)) from erp.initial_import_production_sources ps where ps.po_id=s.po_id),0)
      -coalesce((select sum(e.target_amount-e.previous_amount) from erp.initial_import_bs_value_events e join erp.initial_import_production_sources ps on ps.opening_item_id=e.opening_item_id where ps.po_id=s.po_id),0)
      +coalesce((select sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)) from erp.pocket_period_destinations d where d.po_id=s.po_id),0)
    )::numeric source_cost""")
    i='erp.get_initial_import_workspace_v1(uuid)'
    change(i,"     'opening_id',(select h.id","     'production_sources',erp.initial_import_production_rows_v1(b.id),\n     'opening_id',(select h.id")
    i='erp.get_wip_control_v1(text,uuid,text,text)'
    needle="'rows',"
    change(i,needle,"'opening_rows',erp.initial_import_production_rows_v1(null),'rows',")

TRIGGERS=''
