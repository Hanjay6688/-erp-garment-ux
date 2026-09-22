"""Connected count-accessory workspace over the admitted native issue lifecycle."""

QUOTE = r"""create or replace function erp.accessory_issue_quote_v1(p_material uuid,p_contractor uuid,p_at timestamptz)
returns jsonb language plpgsql stable security definer set search_path='' as $function$
declare m record;p erp.contractor_accessory_price_versions%rowtype;v_factor numeric;
begin
 select x.id,x.material_sku,x.material_name,x.unit_code,c.id category_id,c.category_name
 into m from erp.materials x join erp.accessory_categories c on c.id=x.accessory_category_id
 join erp.uom_definitions u on u.unit_code=x.unit_code
 where x.id=p_material and x.is_active and x.material_type='ACCESSORY' and c.is_active
  and u.is_active and u.dimension='COUNT' and upper(x.unit_code)='PCS' and c.base_uom_code=x.unit_code;
 if m.id is null then return null;end if;
 select * into p from erp.contractor_accessory_price_versions v
 where v.category_id=m.category_id and (v.contractor_id=p_contractor or v.contractor_id is null)
  and v.effective_from<=p_at and (v.effective_to is null or v.effective_to>p_at)
 order by (v.contractor_id is not null) desc,v.effective_from desc,v.id limit 1;
 if p.id is not null then v_factor:=erp.accessory_uom_factor(m.category_id,p.selling_uom_code,p_at);end if;
 return jsonb_build_object('id',m.id,'sku',m.material_sku,'name',m.material_name,'unit',m.unit_code,
  'category',m.category_name,'price_version_id',p.id,'master_price',p.selling_price::numeric(24,6)::text,
  'price_unit',p.selling_uom_code,'factor',v_factor::numeric(24,6)::text);
end;$function$;
"""

READER = r"""create or replace function erp.get_accessory_issue_workspace_v1(p_filters jsonb default '{}'::jsonb)
returns jsonb language plpgsql security definer set search_path='' set TimeZone='UTC' as $function$
declare v_contractor uuid:=nullif(p_filters->>'contractor_id','')::uuid;v_location uuid:=nullif(p_filters->>'location_id','')::uuid;
 v_id uuid:=nullif(p_filters->>'id','')::uuid;v_at timestamptz:=coalesce(nullif(p_filters->>'physical_at','')::timestamptz,statement_timestamp());
 v_query text:=lower(btrim(coalesce(p_filters->>'query','')));v_material_query text:=lower(btrim(coalesce(p_filters->>'material_query','')));
 v_result jsonb;v_document jsonb;v_material_ids jsonb:=coalesce(p_filters->'material_ids','[]'::jsonb);
begin
 perform erp.require_permission('finance.contractor_accessory.view');perform erp.require_internal();
 perform erp._cp3_assert_closed_json_object(p_filters,array[]::text[],array['contractor_id','location_id','physical_at','id','query','material_query','material_ids'],'accessory workspace filters');
 if length(v_query)>120 or length(v_material_query)>120 then raise exception 'Pencarian terlalu panjang';end if;
 if p_filters?'material_ids' and (jsonb_typeof(p_filters->'material_ids')<>'array' or jsonb_array_length(p_filters->'material_ids')>100) then raise exception 'Daftar aksesori tidak valid';end if;
 if v_id is not null then
  if not exists(select 1 from erp.contractor_material_issues where id=v_id) then raise exception 'Nota tidak ditemukan';end if;
  if not(p_filters?'contractor_id') then select contractor_id into v_contractor from erp.contractor_material_issues where id=v_id;end if;
  if not(p_filters?'location_id') then select location_id into v_location from erp.contractor_material_issues where id=v_id;end if;
  if not(p_filters?'physical_at') then select physical_at into v_at from erp.contractor_material_issues where id=v_id;end if;
  select jsonb_build_object('id',h.id,'number',h.issue_number,'contractor_id',h.contractor_id,'location_id',h.location_id,'po_id',h.po_id,
   'physical_local',to_char(h.physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),
   'status',h.status,'row_version',h.row_version::text,'notes',coalesce(h.notes,''),
   'total',coalesce((select sum(i.total_receivable) from erp.contractor_material_issue_items i where i.issue_id=h.id),0)::numeric(24,2)::text,
   'payroll_locked',exists(select 1 from erp.payroll_deductions d join erp.payroll_settlements s on s.id=d.payroll_id
     join erp.contractor_material_issue_items i on i.id=d.contractor_issue_item_id where i.issue_id=h.id and s.status<>'REVERSED'),
   'items',coalesce((select jsonb_agg(jsonb_build_object('id',i.id,'material_id',i.material_id,'sku',m.material_sku,'name',m.material_name,
     'unit',m.unit_code,'qty',i.qty::numeric(24,6)::text,'manual_price',i.manual_retail_unit_price::numeric(24,2)::text,
     'price',i.unit_sale_price_snapshot::numeric(24,6)::text,'factor',i.base_qty_per_transaction_uom::numeric(24,6)::text,
     'price_unit',i.transaction_uom_code,'price_version_id',i.accessory_price_version_id,
     'amount',i.total_receivable::numeric(24,6)::text,'payroll_status',i.payroll_status) order by i.id)
     from erp.contractor_material_issue_items i join erp.materials m on m.id=i.material_id where i.issue_id=h.id),'[]'::jsonb))
  into v_document from erp.contractor_material_issues h where h.id=v_id;
  if not(p_filters?'material_ids') then select coalesce(jsonb_agg(material_id),'[]'::jsonb) into v_material_ids from erp.contractor_material_issue_items where issue_id=v_id;end if;
 end if;
 with history as (
  select h.id,h.issue_number number,c.contractor_name contractor,h.status,h.row_version::text row_version,
   erp._cp3_business_date(h.physical_at) date,
   coalesce((select sum(i.total_receivable) from erp.contractor_material_issue_items i where i.issue_id=h.id),0)::numeric(24,2)::text total
  from erp.contractor_material_issues h join erp.contractors c on c.id=h.contractor_id
  where (v_query='' or strpos(lower(concat_ws(' ',h.issue_number,c.contractor_name)),v_query)>0)
   and not exists(select 1 from erp.contractor_material_issue_items i join erp.materials m on m.id=i.material_id
    join erp.uom_definitions u on u.unit_code=m.unit_code where i.issue_id=h.id and (m.material_type<>'ACCESSORY' or u.dimension<>'COUNT'))
 ), choices as (
  select m.id from erp.materials m join erp.accessory_categories c on c.id=m.accessory_category_id
  join erp.uom_definitions u on u.unit_code=m.unit_code
  where m.material_type='ACCESSORY' and m.is_active and c.is_active and u.is_active and u.dimension='COUNT' and upper(m.unit_code)='PCS' and m.unit_code=c.base_uom_code
   and ((v_material_query='' or strpos(lower(concat_ws(' ',m.material_sku,m.material_name,c.category_name)),v_material_query)>0)
    or m.id::text in(select jsonb_array_elements_text(v_material_ids)))
 ), selected as (
  select x.id,erp.accessory_issue_quote_v1(x.id,v_contractor,v_at) quote,
   coalesce((select sum(s.qty_signed) from erp.material_stock_movements s where s.material_id=x.id and s.location_id=v_location),0)::numeric(24,6)::text stock
  from choices x order by (x.id::text in(select jsonb_array_elements_text(v_material_ids))) desc,x.id limit 100
 ) select jsonb_build_object(
  'contractor_id',v_contractor,'location_id',v_location,
  'physical_local',to_char(v_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),
  'filters',p_filters,'document',v_document,'history_count',(select count(*) from history),'material_count',(select count(*) from choices),
  'history',coalesce((select jsonb_agg(to_jsonb(x) order by x.date desc,x.id) from(select * from history order by date desc,id limit 50)x),'[]'::jsonb),
  'materials',coalesce((select jsonb_agg(quote||jsonb_build_object('stock',stock) order by quote->>'name',id) from selected),'[]'::jsonb),
  'contractors',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',contractor_name) order by contractor_name,id) from erp.contractors where is_active and contractor_type='MANDOR'),'[]'::jsonb),
  'locations',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',location_name) order by location_name,id) from erp.locations where is_active and location_type='RAW_MATERIAL_WAREHOUSE'),'[]'::jsonb),
  'orders',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',po_number) order by po_number,id) from erp.production_orders where contractor_id=v_contractor and status not in('FINISHED','CANCELLED')),'[]'::jsonb)
 ) into v_result;
 return v_result;
end;$function$;
"""

COMMAND = r"""create or replace function erp.save_accessory_issue_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
returns jsonb language plpgsql security definer set search_path='' set TimeZone='UTC' as $function$
declare v_action text:=upper(btrim(p_action));v_cached jsonb;v_result jsonb;v_native jsonb;v_line jsonb;v_quote jsonb;
 v_id uuid;v_version bigint;v_contractor uuid;v_location uuid;v_po uuid;v_at timestamptz;v_reason text;v_items jsonb:='[]'::jsonb;
 h erp.contractor_material_issues%rowtype;
begin
 perform erp.require_permission('finance.contractor_accessory.view');perform erp.require_internal();
 if v_action not in('SAVE_DRAFT','POST','DELETE','REVERSE') or v_action is null then raise exception 'Tindakan nota tidak dikenal';end if;
 if v_action in('SAVE_DRAFT','POST','DELETE') then perform erp.require_permission('finance.contractor_accessory.create');end if;
 if v_action='POST' then perform erp.require_permission('finance.contractor_accessory.post');end if;
 if v_action='REVERSE' then perform erp.require_owner_admin();perform erp.require_permission('finance.contractor_accessory.reverse');end if;
 perform erp._cp3_assert_closed_json_object(p_payload,array['reason'],array['id','expected_version','number','contractor_id','location_id','po_id','physical_at','notes','items','reason'],'accessory issue payload');
 if jsonb_typeof(p_payload->'reason')<>'string' or nullif(btrim(p_payload->>'reason'),'') is null or length(p_payload->>'reason')>1000 then raise exception 'Alasan nota wajib diisi';end if;
 v_reason:=btrim(p_payload->>'reason');v_id:=nullif(p_payload->>'id','')::uuid;
 if p_payload->>'expected_version' is not null and (jsonb_typeof(p_payload->'expected_version')<>'string' or (p_payload->>'expected_version')!~'^[1-9][0-9]{0,18}$') then raise exception 'Versi nota wajib berupa teks bilangan bulat';end if;
 v_version:=(p_payload->>'expected_version')::bigint;
 v_cached:=erp._idempotency_begin('save_accessory_issue_action_v1',p_client_request_id,erp._request_hash(jsonb_build_object('action',v_action,'payload',p_payload)));
 if v_cached is not null then return v_cached;end if;
 if v_id is not null then
  select * into h from erp.contractor_material_issues where id=v_id for update;
  if h.id is null then raise exception 'Nota tidak ditemukan';end if;
  if v_version is null or h.row_version<>v_version then raise exception 'STALE_VERSION: nota berubah, muat ulang';end if;
  if exists(select 1 from erp.contractor_material_issue_items i join erp.materials m on m.id=i.material_id
   join erp.uom_definitions u on u.unit_code=m.unit_code where i.issue_id=v_id and (m.material_type<>'ACCESSORY' or u.dimension<>'COUNT')) then raise exception 'Form ini hanya untuk nota aksesori hitung';end if;
 elsif v_version is not null or v_action in('DELETE','REVERSE') then raise exception 'Identitas dan versi nota tidak cocok';end if;
 if v_action in('SAVE_DRAFT','POST') then
  if v_id is not null and h.status<>'DRAFT' then raise exception 'Nota disahkan tidak dapat diedit';end if;
  if jsonb_typeof(p_payload->'number') is distinct from 'string' or nullif(btrim(p_payload->>'number'),'') is null or length(p_payload->>'number')>60 then raise exception 'Nomor nota wajib diisi';end if;
  if jsonb_typeof(p_payload->'physical_at') is distinct from 'string' or (p_payload->>'physical_at')!~'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+07:00$' then raise exception 'Waktu pengambilan wajib memakai tanggal dan jam WIB';end if;
  v_at:=(p_payload->>'physical_at')::timestamptz;
  if (to_char(v_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')||'+07:00')<>(p_payload->>'physical_at')
   or erp._cp3_business_date(v_at)>erp._cp3_business_date(statement_timestamp()) then raise exception 'Tanggal pengambilan tidak valid atau di masa depan';end if;
  v_contractor:=(p_payload->>'contractor_id')::uuid;v_location:=(p_payload->>'location_id')::uuid;v_po:=nullif(p_payload->>'po_id','')::uuid;
  if not exists(select 1 from erp.contractors where id=v_contractor and is_active and contractor_type='MANDOR') then raise exception 'Pilih mandor aktif';end if;
  if not exists(select 1 from erp.locations where id=v_location and is_active and location_type='RAW_MATERIAL_WAREHOUSE') then raise exception 'Pilih gudang bahan aktif';end if;
  if v_po is not null then
   perform 1 from erp.production_orders where id=v_po and contractor_id=v_contractor and status not in('FINISHED','CANCELLED') for update;
   if not found then raise exception 'PO harus aktif dan milik mandor yang sama';end if;
  end if;
  if jsonb_typeof(p_payload->'items') is distinct from 'array' then raise exception 'Rincian aksesori wajib diisi';end if;
  if jsonb_array_length(p_payload->'items') not between 1 and 100 then raise exception 'Isi 1 sampai 100 aksesori';end if;
  if exists(select 1 from jsonb_array_elements(p_payload->'items') x group by x->>'material_id' having count(*)>1) then raise exception 'Aksesori yang sama tidak boleh dua baris';end if;
  for v_line in select value from jsonb_array_elements(p_payload->'items') loop
   perform erp._cp3_assert_closed_json_object(v_line,array['material_id','qty','mode'],array['material_id','qty','mode','manual_price','price_version_id','factor'],'accessory issue line');
   if jsonb_typeof(v_line->'qty') is distinct from 'string' or (v_line->>'qty')!~'^[1-9][0-9]{0,11}$' then raise exception 'Jumlah aksesori harus PCS utuh positif';end if;
   v_quote:=erp.accessory_issue_quote_v1((v_line->>'material_id')::uuid,v_contractor,v_at);
   if v_quote is null then raise exception 'Aksesori hitung aktif tidak ditemukan';end if;
   if v_line->>'mode'='MANUAL' then
    if jsonb_typeof(v_line->'manual_price') is distinct from 'string' or (v_line->>'manual_price')!~'^[0-9]{1,12}(\.[0-9]{1,2})?$' then raise exception 'Harga eceran wajib nominal nonnegatif, maksimal dua desimal';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty','manual_retail_unit_price',v_line->>'manual_price'));
   elsif v_line->>'mode'='MASTER' then
    if v_line->>'manual_price' is not null then raise exception 'Pilih satu dasar harga';end if;
    if v_quote->>'price_version_id' is null or v_line->>'price_version_id' is distinct from v_quote->>'price_version_id'
     or v_line->>'factor' is distinct from v_quote->>'factor' then raise exception 'STALE_PRICE: harga master berubah atau belum tersedia, muat ulang';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty'));
   else raise exception 'Pilih harga master atau eceran per pcs';end if;
  end loop;
  v_native:=erp.save_contractor_material_issue_draft_v2(jsonb_build_object('id',v_id,'issue_number',btrim(p_payload->>'number'),
   'contractor_id',v_contractor,'location_id',v_location,'po_id',v_po,'physical_at',v_at,'notes',p_payload->>'notes','change_reason',v_reason,'items',v_items),p_client_request_id,v_version);
  v_id:=(v_native->>'contractor_material_issue_id')::uuid;
  -- Native save takes the configured-price locks. Verify the actually selected
  -- versions there, so a concurrent tariff/conversion edit cannot pass preview.
  if exists(select 1 from jsonb_array_elements(p_payload->'items') x
   join erp.contractor_material_issue_items i on i.issue_id=v_id and i.material_id=(x->>'material_id')::uuid
   where x->>'mode'='MASTER' and (i.accessory_price_version_id::text is distinct from x->>'price_version_id'
    or i.base_qty_per_transaction_uom is distinct from (x->>'factor')::numeric)) then
   raise exception 'STALE_PRICE: harga master berubah, muat ulang';end if;
  if v_action='POST' then v_native:=erp.post_contractor_material_issue_v2(v_id,p_client_request_id,(v_native->>'row_version')::bigint,v_reason);end if;
 elsif v_action='DELETE' then
  v_native:=erp.save_contractor_material_issue_draft_v2(jsonb_build_object('id',v_id,'action','DELETE','change_reason',v_reason),p_client_request_id,v_version);
 else v_native:=erp.reverse_contractor_material_issue_v2(v_id,v_reason,p_client_request_id,v_version);
 end if;
 select * into h from erp.contractor_material_issues where id=v_id;
 v_result:=jsonb_build_object('id',v_id,'action',v_action,'request_id',p_client_request_id,'status',case when v_action='DELETE' then 'DELETED' else h.status end,'row_version',h.row_version::text);
 return erp._idempotency_complete('save_accessory_issue_action_v1',p_client_request_id,v_result);
end;$function$;
"""

def extend_accessory_issue_contract(functions):
    added={
        'erp.accessory_issue_quote_v1(uuid,uuid,timestamp with time zone)':QUOTE,
        'erp.get_accessory_issue_workspace_v1(jsonb)':READER,
        'erp.save_accessory_issue_action_v1(text,jsonb,uuid)':COMMAND,
    }
    for name,args,call,types in [
      ('get_accessory_issue_workspace_v1',"p_filters jsonb default '{}'::jsonb",'p_filters','jsonb'),
      ('save_accessory_issue_action_v1','p_action text,p_payload jsonb,p_client_request_id uuid','p_action,p_payload,p_client_request_id','text,jsonb,uuid')]:
        added['public.erp_'+name+'('+types+')']=f"create or replace function public.erp_{name}({args}) returns jsonb language sql security definer set search_path='' as $function$ select erp.{name}({call});$function$;"
    old=dict(functions);functions.clear();functions.update(added);functions.update(old)
