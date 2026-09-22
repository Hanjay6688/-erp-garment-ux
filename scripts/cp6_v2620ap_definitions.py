"""Connected initial-data transport. The admitted domain writers retain ownership."""
import json
from pathlib import Path

CATALOG = json.loads(Path('src/initialImportCatalog.json').read_text())

REVISION = r"""CREATE OR REPLACE FUNCTION erp.initial_import_revision_v1(p_batch_id uuid)
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO '' SET TimeZone TO 'UTC' AS $function$
 select encode(extensions.digest(convert_to(jsonb_build_object(
   'batch',(select to_jsonb(b) from erp.migration_batches b where id=p_batch_id),
   'rows',coalesce((select jsonb_agg(to_jsonb(s) order by s.entity_type,s.source_row_no)
     from erp.migration_staging_rows s where s.batch_id=p_batch_id),'[]'::jsonb),
   'opening',coalesce((select jsonb_agg(to_jsonb(h) order by h.id)
     from erp.opening_balance_headers h where h.migration_batch_id=p_batch_id),'[]'::jsonb),
   'items',coalesce((select jsonb_agg(to_jsonb(i) order by i.id)
     from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
     where h.migration_batch_id=p_batch_id),'[]'::jsonb)
 )::text,'UTF8'),'sha256'),'hex');
$function$;
"""

READER = r"""CREATE OR REPLACE FUNCTION erp.get_initial_import_workspace_v1(p_batch_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare b erp.migration_batches%rowtype; v_batch jsonb;
begin
 perform erp.require_owner_admin();
 perform erp.require_permission('settings.erp.view');
 if p_batch_id is not null then
   select * into b from erp.migration_batches where id=p_batch_id for share;
   if b.id is null then raise exception 'Batch impor tidak ditemukan'; end if;
   select jsonb_build_object('id',b.id,'code',b.batch_code,'status',b.status,
     'cutover_at',b.cutover_at,'notes',b.notes,'revision',erp.initial_import_revision_v1(b.id),
     'rows',coalesce((select jsonb_agg(jsonb_build_object(
       'id',s.id,'entity',s.entity_type,'source_row_no',s.source_row_no,
       'payload',s.normalized_payload,'validation_status',s.validation_status,
       'errors',s.validation_errors,'applied',s.posted_entity_id is not null
     ) order by s.entity_type,s.source_row_no) from erp.migration_staging_rows s where s.batch_id=b.id),'[]'::jsonb),
     'opening_id',(select h.id from erp.opening_balance_headers h where h.migration_batch_id=b.id order by h.created_at limit 1)
   ) into v_batch;
 end if;
 return jsonb_build_object('batch',v_batch,'recent',coalesce((select jsonb_agg(x order by x.created_at desc,x.id)
   from (select id,batch_code,status,cutover_at,created_at from erp.migration_batches
     order by created_at desc,id limit 50) x),'[]'::jsonb));
end;$function$;
"""

COMMAND = r"""CREATE OR REPLACE FUNCTION erp.save_initial_import_action_v1(
 p_action text,p_payload jsonb,p_client_request_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare
 v_action text:=upper(btrim(p_action)); v_batch uuid; v_type text;
 b erp.migration_batches%rowtype; v_cached jsonb; v_result jsonb; v_row jsonb; v_normal jsonb;
 v_field text; v_text text; v_number numeric; v_line integer; v_seen integer[]:='{}';
 v_total bigint; v_valid bigint; v_errors bigint; v_opening uuid; v_date date;
 v_catalog constant jsonb:=__CATALOG__::jsonb;
begin
 perform erp.require_owner_admin();
 perform erp.require_permission('settings.erp.view');
 if v_action is null or v_action not in('CREATE','SAVE_FILE','VALIDATE','FINALIZE') then raise exception 'Aksi impor tidak dikenal'; end if;
 if p_payload is null or jsonb_typeof(p_payload)<>'object' or octet_length(p_payload::text)>5242880 then
   raise exception 'Isi impor harus berupa objek dan maksimal 5 MB'; end if;
 v_cached:=erp._idempotency_begin('save_initial_import_action_v1',p_client_request_id,
   erp._request_hash(jsonb_build_object('action',v_action,'payload',p_payload)));
 if v_cached is not null then return v_cached; end if;
 perform set_config('app.change_reason','Impor awal: '||v_action,true);
 if v_action='CREATE' then
   if p_payload->>'cutover_date' is null or p_payload->>'cutover_date' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then
     raise exception 'Tanggal saldo awal wajib memakai YYYY-MM-DD'; end if;
   v_date:=(p_payload->>'cutover_date')::date;
   if v_date::text<>p_payload->>'cutover_date' or v_date>(statement_timestamp() at time zone 'Asia/Jakarta')::date then
     raise exception 'Tanggal saldo awal tidak valid atau berada di masa depan'; end if;
   v_batch:=erp.create_migration_batch(p_payload->>'batch_code',v_date::timestamp at time zone 'Asia/Jakarta',
     'CSV UTF-8',p_payload->>'notes');
 else
   v_batch:=nullif(p_payload->>'batch_id','')::uuid;
   select * into b from erp.migration_batches where id=v_batch for update;
   if b.id is null then raise exception 'Batch impor tidak ditemukan'; end if;
   if b.status not in('DRAFT','READY','VALIDATING','POSTING') or exists(
     select 1 from erp.opening_balance_headers where migration_batch_id=b.id and status<>'DRAFT') then
     raise exception 'Impor yang sudah disahkan tidak dapat diedit atau disahkan ulang dengan permintaan baru'; end if;
   if nullif(p_payload->>'expected_revision','') is null
     or p_payload->>'expected_revision'<>erp.initial_import_revision_v1(b.id) then
     raise exception 'STALE_VERSION: isi impor berubah. Muat ulang sebelum melanjutkan'; end if;
   if v_action='SAVE_FILE' then
     v_type:=p_payload->>'entity';
     if v_type is null or not v_catalog ? v_type then raise exception 'Jenis file impor tidak didukung'; end if;
     if jsonb_typeof(p_payload->'rows') is distinct from 'array'
       or jsonb_array_length(p_payload->'rows')>5000 then raise exception 'Maksimal 5000 baris per file'; end if;
     if (select count(*) from erp.migration_staging_rows where batch_id=b.id and entity_type<>v_type)
       +jsonb_array_length(p_payload->'rows')>5000 then raise exception 'Maksimal 5000 baris per batch; pecah menjadi batch terpisah'; end if;
     if exists(select 1 from erp.migration_staging_rows where batch_id=b.id
       and posted_entity_id is not null and entity_type<>'OPENING_BALANCE_ITEM') then
       raise exception 'Batch ini sudah menerapkan master melalui jalur lama; selesaikan di jalur asal'; end if;
     perform 1 from erp.opening_balance_headers where migration_batch_id=b.id order by id for update;
     delete from erp.opening_balance_items i using erp.opening_balance_headers h
       where i.opening_id=h.id and h.migration_batch_id=b.id and h.status='DRAFT';
     update erp.migration_staging_rows set posted_entity_type=null,posted_entity_id=null,posted_at=null
       where batch_id=b.id and entity_type='OPENING_BALANCE_ITEM';
     delete from erp.migration_staging_rows where batch_id=b.id and entity_type=v_type;
     for v_row in select value from jsonb_array_elements(p_payload->'rows') loop
       if jsonb_typeof(v_row)<>'object' or jsonb_typeof(v_row->'payload') is distinct from 'object'
         or coalesce(v_row->>'source_row_no','') !~ '^[1-9][0-9]{0,6}$' then raise exception 'Identitas baris impor tidak valid'; end if;
       v_line:=(v_row->>'source_row_no')::integer;
       if v_line=any(v_seen) then raise exception 'Baris sumber % ditulis dua kali',v_line; end if;
       v_seen:=array_append(v_seen,v_line);v_normal:='{}'::jsonb;
       for v_field,v_text in select key,value #>> '{}' from jsonb_each(v_row->'payload') loop
         if not (v_catalog->v_type->'fields') ? v_field or jsonb_typeof(v_row->'payload'->v_field)<>'string' then
           raise exception 'Baris %, kolom %: nama kolom atau tipe data tidak valid',v_line,v_field; end if;
         v_text:=btrim(v_text);
         if length(v_text)>20000 then raise exception 'Baris %, kolom % terlalu panjang',v_line,v_field; end if;
         if v_field in('qty','opening_qty','unit_cost','amount','original_amount','settled_before_cutover','hpp_percent_of_price','target_dozens','target_qty_pcs','sort_order') and v_text<>'' then
           if v_text !~ '^-?[0-9]+([.,][0-9]+)?$' then
             raise exception 'Baris %, kolom %: isi angka tanpa pemisah ribuan',v_line,v_field; end if;
           v_text:=replace(v_text,',','.');v_number:=v_text::numeric;
           if (v_field in('amount','original_amount','settled_before_cutover') and v_number<>round(v_number,2))
             or (v_field in('qty','opening_qty','unit_cost','target_dozens') and v_number<>round(v_number,6))
             or (v_field='hpp_percent_of_price' and v_number<>round(v_number,4))
             or (v_field in('target_qty_pcs','sort_order') and v_number<>trunc(v_number)) then
             raise exception 'Baris %, kolom %: ketelitian angka melebihi kolom tujuan; angka tidak dibulatkan otomatis',v_line,v_field; end if;
         end if;
         v_normal:=v_normal||jsonb_build_object(v_field,v_text);
       end loop;
       perform erp.stage_migration_row(b.id,v_type,v_line,null,
         (v_row->'payload')||jsonb_build_object('_filename',left(coalesce(p_payload->>'filename',''),255)),v_normal);
     end loop;
     update erp.migration_batches set status='DRAFT',validated_at=null,error_message=null where id=b.id;
   else
     if not exists(select 1 from erp.migration_staging_rows where batch_id=b.id) then raise exception 'Unggah data sebelum memeriksa atau mengesahkan'; end if;
     select * into v_total,v_valid,v_errors from erp.validate_migration_batch(b.id);
     if v_action='FINALIZE' and v_errors=0 then
       -- Domain writers execute inside this same transaction. A refusal in any
       -- consumer rolls back masters, opening stock, journals, and application.
       perform erp.apply_migration_master_rows(b.id);
       perform erp.apply_migration_open_pos(b.id);
       if exists(select 1 from erp.migration_staging_rows where batch_id=b.id
         and entity_type in('OPENING_BALANCE_ITEM','MATERIAL_ROLL')) then
         v_opening:=erp.prepare_migration_opening_balance(b.id,null);
         perform erp.post_opening_balance(v_opening);
       end if;
       perform erp.finalize_migration_batch(b.id);
     end if;
   end if;
 end if;
 v_result:=jsonb_build_object('request_id',p_client_request_id,'action',v_action,'batch_id',v_batch,
   'status',(select status from erp.migration_batches where id=v_batch),'total_rows',v_total,
   'valid_rows',v_valid,'error_rows',v_errors,'revision',erp.initial_import_revision_v1(v_batch));
 return erp._idempotency_complete('save_initial_import_action_v1',p_client_request_id,v_result);
end;$function$;
""".replace('__CATALOG__', "'"+json.dumps(CATALOG, ensure_ascii=False).replace("'", "''")+"'")

PUBLIC_READER = r"""CREATE OR REPLACE FUNCTION public.erp_get_initial_import_workspace_v1(p_batch_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO '' AS $function$
 select erp.get_initial_import_workspace_v1(p_batch_id);
$function$;
"""
PUBLIC_COMMAND = r"""CREATE OR REPLACE FUNCTION public.erp_save_initial_import_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO '' AS $function$
 select erp.save_initial_import_action_v1(p_action,p_payload,p_client_request_id);
$function$;
"""
FUNCTIONS = {
 'erp.initial_import_revision_v1(uuid)':REVISION,
 'erp.get_initial_import_workspace_v1(uuid)':READER,
 'erp.save_initial_import_action_v1(text,jsonb,uuid)':COMMAND,
 'public.erp_get_initial_import_workspace_v1(uuid)':PUBLIC_READER,
 'public.erp_save_initial_import_action_v1(text,jsonb,uuid)':PUBLIC_COMMAND,
}

# Preserve the admitted native validators and extend only their entity catalog.
PREDECESSOR = json.loads(Path('docs/evidence/cp6-initial-import-predecessor.json').read_text())['functions']
for identity, definition, *_ in PREDECESSOR:
    if identity.startswith('erp.stage_migration_row('):
        old="'MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPEN_PO')"
        assert definition.count(old)==1
        FUNCTIONS[identity]=definition.replace(old,"'MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPEN_PO','OPENING_CONTROL','LAUNDRY_VENDOR','LOCATION','CHART_ACCOUNT','CASH_ACCOUNT')")
    elif identity.startswith('erp._validate_migration_batch_base('):
        old="entity_type not in('MATERIAL_ROLL','OPENING_BALANCE_ITEM')"
        assert definition.count(old)==1
        FUNCTIONS[identity]=definition.replace(old,"entity_type not in('MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPENING_CONTROL')")
    else:
        FUNCTIONS[identity]=definition

RECONCILE = r"""CREATE OR REPLACE FUNCTION erp.validate_initial_import_totals_v1(p_batch_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' AS $function$
declare r record; c record; j jsonb; v_key text; v_type text; v_qty numeric; v_amount numeric;
 v_totals jsonb:='{}'; v_entry jsonb; v_product uuid; v_cutover timestamptz; v_cost numeric;
begin
 perform erp.require_owner_admin();
 select cutover_at into v_cutover from erp.migration_batches where id=p_batch_id for update;
 if v_cutover is null then raise exception 'Batch tidak ditemukan'; end if;
 for r in select * from erp.migration_staging_rows where batch_id=p_batch_id
   and entity_type in('MATERIAL_ROLL','OPENING_BALANCE_ITEM') order by entity_type,source_row_no loop
  begin
   j:=r.normalized_payload;v_key:=nullif(btrim(j->>'control_key'),'');
   if v_key is null then raise exception 'control_key: rincian wajib terhubung ke total pembanding'; end if;
   if (select count(*) from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_CONTROL'
      and normalized_payload->>'control_key'=v_key)<>1 then
     raise exception 'control_key %: harus punya tepat satu total pembanding',v_key; end if;
   if r.validation_status<>'VALID' then continue; end if;
   v_type:=case when r.entity_type='MATERIAL_ROLL' then 'MATERIAL' else upper(j->>'balance_type') end;
   v_qty:=coalesce(nullif(j->>case when r.entity_type='MATERIAL_ROLL' then 'opening_qty' else 'qty' end,'')::numeric,0);
   v_cost:=nullif(j->>'unit_cost','')::numeric;
   if v_type='FINISHED_GOODS' and upper(j->>'hpp_input_method')='PRICE_PERCENT' then
     v_product:=erp.resolve_opening_product_identity(j->>'product_sku',v_cutover,j->>'color_name',j->>'size_code',j->>'model_code',j->>'brand_code');
     v_cost:=round(erp.resolve_product_price_at(v_product,erp.product_opening_physical_at(v_product,(v_cutover at time zone 'Asia/Jakarta')::date))*(j->>'hpp_percent_of_price')::numeric/100,6);
   end if;
   v_amount:=case when v_type in('MATERIAL','FINISHED_GOODS') then round(v_qty*v_cost,2)
     when v_type='BS' then 0 else round(coalesce(nullif(j->>'amount','')::numeric,v_qty*v_cost),2) end;
   if v_amount is null then raise exception 'amount: nilai rincian belum lengkap'; end if;
   if v_type='WIP' and nullif(j->>'amount','') is not null and v_cost is not null and nullif(j->>'qty','') is not null
     and round((j->>'amount')::numeric,2)<>round(v_qty*v_cost,2) then raise exception 'amount: nilai WIP tidak sama dengan jumlah x biaya'; end if;
   if v_type in('MATERIAL','FINISHED_GOODS','BS') and nullif(j->>'amount','') is not null and (j->>'amount')::numeric<>v_amount then
     raise exception 'amount: nominal rincian tidak sama dengan nilai yang akan dibukukan'; end if;
   v_entry:=v_totals->v_key;
   if v_entry is not null and v_entry->>'type'<>v_type then raise exception 'control_key: satu total tidak boleh mencampur jenis saldo'; end if;
   v_totals:=v_totals||jsonb_build_object(v_key,jsonb_build_object('type',v_type,
     'qty',coalesce((v_entry->>'qty')::numeric,0)+v_qty,'amount',coalesce((v_entry->>'amount')::numeric,0)+v_amount));
  exception when others then
   update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm) where id=r.id;
  end;
 end loop;
 for c in select * from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_CONTROL' order by source_row_no loop
  begin
   j:=c.normalized_payload;v_key:=nullif(btrim(j->>'control_key'),'');v_entry:=v_totals->v_key;
   if v_key is null then raise exception 'control_key: kode total wajib diisi'; end if;
   if (select count(*) from erp.migration_staging_rows where batch_id=p_batch_id and entity_type='OPENING_CONTROL'
     and normalized_payload->>'control_key'=v_key)<>1 then raise exception 'control_key: total ditulis lebih dari sekali'; end if;
   if v_entry is null then raise exception 'control_key: total tidak memiliki rincian yang valid'; end if;
   if upper(j->>'balance_type') is distinct from v_entry->>'type' then raise exception 'balance_type: total dan rincian berbeda'; end if;
   if nullif(j->>'amount','') is null or (j->>'amount')::numeric is distinct from (v_entry->>'amount')::numeric then
     raise exception 'amount: total pembanding %, jumlah rincian %',j->>'amount',v_entry->>'amount'; end if;
   if (v_entry->>'type' in('MATERIAL','FINISHED_GOODS','BS') or nullif(j->>'qty','') is not null)
      and (nullif(j->>'qty','')::numeric is distinct from (v_entry->>'qty')::numeric) then
     raise exception 'qty: total pembanding %, jumlah rincian %',j->>'qty',v_entry->>'qty'; end if;
  exception when others then
   update erp.migration_staging_rows set validation_status='ERROR',validation_errors=validation_errors||jsonb_build_array(sqlerrm) where id=c.id;
  end;
 end loop;
 update erp.migration_batches set status=case when exists(select 1 from erp.migration_staging_rows where batch_id=p_batch_id
   and validation_status<>'VALID') then 'DRAFT' else 'READY' end where id=p_batch_id;
end;$function$;
"""
FUNCTIONS['erp.validate_initial_import_totals_v1(uuid)']=RECONCILE
needle='select * into v_total,v_valid,v_errors from erp.validate_migration_batch(b.id);'
assert COMMAND.count(needle)==1
COMMAND=COMMAND.replace(needle,needle+'''
     perform erp.validate_initial_import_totals_v1(b.id);
     select count(*),count(*) filter(where validation_status='VALID'),count(*) filter(where validation_status='ERROR')
       into v_total,v_valid,v_errors from erp.migration_staging_rows where batch_id=b.id;''')
FUNCTIONS['erp.save_initial_import_action_v1(text,jsonb,uuid)']=COMMAND

from cp6_initial_import_masters import extend_master_contract
extend_master_contract(FUNCTIONS)

from cp6_initial_import_financial_sources import SCHEMA, extend_financial_contract
extend_financial_contract(FUNCTIONS)

from cp6_initial_import_receipts import SCHEMA as RECEIPT_SCHEMA, TRIGGERS, PREDECESSOR as RECEIPT_PREDECESSOR, extend_receipt_contract
SCHEMA += RECEIPT_SCHEMA
PREDECESSOR += RECEIPT_PREDECESSOR
extend_receipt_contract(FUNCTIONS)

from cp6_initial_import_advances import SCHEMA as ADVANCE_SCHEMA, TRIGGERS as ADVANCE_TRIGGERS, PREDECESSOR as ADVANCE_PREDECESSOR, extend_advance_contract
SCHEMA += ADVANCE_SCHEMA
TRIGGERS += ADVANCE_TRIGGERS
PREDECESSOR += ADVANCE_PREDECESSOR
extend_advance_contract(FUNCTIONS)

from cp6_initial_import_prepayments import SCHEMA as PREPAYMENT_SCHEMA, TRIGGERS as PREPAYMENT_TRIGGERS, PREDECESSOR as PREPAYMENT_PREDECESSOR, extend_prepayment_contract
SCHEMA += PREPAYMENT_SCHEMA
TRIGGERS += '\n'+PREPAYMENT_TRIGGERS
PREDECESSOR += PREPAYMENT_PREDECESSOR
extend_prepayment_contract(FUNCTIONS)

from cp6_pocket_fabric import SCHEMA as POCKET_SCHEMA, TRIGGERS as POCKET_TRIGGERS, extend_pocket_contract
SCHEMA += POCKET_SCHEMA
TRIGGERS += '\n'+POCKET_TRIGGERS
extend_pocket_contract(FUNCTIONS)

from cp6_pocket_periods import SCHEMA as PERIOD_SCHEMA, TRIGGERS as PERIOD_TRIGGERS, PREDECESSOR as PERIOD_PREDECESSOR, extend_period_contract
SCHEMA += PERIOD_SCHEMA
TRIGGERS += '\n'+PERIOD_TRIGGERS
PREDECESSOR += PERIOD_PREDECESSOR
extend_period_contract(FUNCTIONS)
