create or replace function erp.save_accessory_issue_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
returns jsonb language plpgsql security definer set search_path='' set TimeZone='UTC' as $function$
declare v_action text:=upper(btrim(p_action));v_cached jsonb;v_result jsonb;v_native jsonb;v_line jsonb;v_quote jsonb;v_free jsonb;
 v_id uuid;v_version bigint;v_contractor uuid;v_location uuid;v_po uuid;v_at timestamptz;v_reason text;v_items jsonb:='[]'::jsonb;
 h erp.contractor_material_issues%rowtype;
begin
 perform erp.require_permission('finance.contractor_accessory.view');
 if v_action not in('SAVE_DRAFT','POST','DELETE','REVERSE') or v_action is null then raise exception 'Tindakan nota tidak dikenal';end if;
 if v_action in('SAVE_DRAFT','POST','DELETE') then perform erp.require_permission('finance.contractor_accessory.create');end if;
 if v_action='POST' then perform erp.require_permission('finance.contractor_accessory.post');end if;
 if v_action='REVERSE' then perform erp.require_owner_admin();perform erp.require_permission('finance.contractor_accessory.reverse');end if;
 perform erp.require_internal();
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
   perform erp._cp3_assert_closed_json_object(v_line,array['material_id','qty','mode'],array['material_id','qty','mode','manual_price','price_version_id','factor','free_policy_version'],'accessory issue line');
   if jsonb_typeof(v_line->'qty') is distinct from 'string' or (v_line->>'qty')!~'^[1-9][0-9]{0,11}$' then raise exception 'Jumlah aksesori harus PCS utuh positif';end if;
   v_quote:=erp.accessory_issue_quote_v1((v_line->>'material_id')::uuid,v_contractor,v_at);
   if v_quote is null then raise exception 'Aksesori hitung aktif tidak ditemukan';end if;
   if v_line->>'mode'='MANUAL' then
    if jsonb_typeof(v_line->'manual_price') is distinct from 'string' or (v_line->>'manual_price')!~'^[0-9]{1,12}(\.[0-9]{1,2})?$' then raise exception 'Harga eceran wajib nominal nonnegatif, maksimal dua desimal';end if;
    -- BC (M:5023, ERP-DEC02): a price of 0 is free; free is never a way around the note price, only an owner-listed Special category.
    if (v_line->>'manual_price')::numeric=0 then raise exception 'BC_FREE_REQUIRES_POLICY: harga eceran 0 hanya lewat gratis Special yang ditetapkan owner (ERP-DEC02)';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty','manual_retail_unit_price',v_line->>'manual_price'));
   elsif v_line->>'mode'='MASTER' then
    if v_line->>'manual_price' is not null then raise exception 'Pilih satu dasar harga';end if;
    if v_quote->>'price_version_id' is null or v_line->>'price_version_id' is distinct from v_quote->>'price_version_id'
     or v_line->>'factor' is distinct from v_quote->>'factor' then raise exception 'STALE_PRICE: harga master berubah atau belum tersedia, muat ulang';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty'));
   elsif v_line->>'mode'='FREE' then
    -- BC (ERP-DEC02): only a category on the owner's Special free list, for a Special contractor at the physical time.
    if v_line ? 'manual_price' or v_line ? 'price_version_id' or v_line ? 'factor' then raise exception 'Pilih satu dasar harga';end if;
    perform 1 from erp.bc_policy_settings_v1 where policy_key='ERP_DEC02' for share;
    v_free:=erp.bc_free_basis_v1((v_line->>'material_id')::uuid,v_contractor,v_at);
    if v_free is null then raise exception 'BC_FREE_NOT_ALLOWED: aksesori ini tidak gratis untuk mandor pada tanggal nota (ERP-DEC02 belum ditetapkan atau kategori/mandor tidak termasuk)';end if;
    if v_line->>'free_policy_version' is distinct from v_free->>'policy_version' then raise exception 'STALE_PRICE: daftar kategori gratis berubah, muat ulang';end if;
    v_items:=v_items||jsonb_build_array(jsonb_build_object('material_id',v_line->>'material_id','qty',v_line->>'qty','manual_retail_unit_price','0'));
   else raise exception 'Pilih harga master, eceran per pcs, atau gratis Special';end if;
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
  -- BC (ERP-DEC02): the free lines of this note with the policy version they used.
  delete from erp.bc_free_issue_lines_v1 where issue_id=v_id;
  insert into erp.bc_free_issue_lines_v1(issue_id,material_id,category_id,policy_version)
  select v_id,m.id,m.accessory_category_id,(x->>'free_policy_version')::bigint from jsonb_array_elements(p_payload->'items') x
   join erp.materials m on m.id=(x->>'material_id')::uuid where x->>'mode'='FREE';
  if v_action='POST' then v_native:=erp.post_contractor_material_issue_v2(v_id,p_client_request_id,(v_native->>'row_version')::bigint,v_reason);end if;
 elsif v_action='DELETE' then
  v_native:=erp.save_contractor_material_issue_draft_v2(jsonb_build_object('id',v_id,'action','DELETE','change_reason',v_reason),p_client_request_id,v_version);
 else v_native:=erp.reverse_contractor_material_issue_v2(v_id,v_reason,p_client_request_id,v_version);
 end if;
 select * into h from erp.contractor_material_issues where id=v_id;
 v_result:=jsonb_build_object('id',v_id,'action',v_action,'request_id',p_client_request_id,'status',case when v_action='DELETE' then 'DELETED' else h.status end,'row_version',h.row_version::text);
 return erp._idempotency_complete('save_accessory_issue_action_v1',p_client_request_id,v_result);
end;$function$;