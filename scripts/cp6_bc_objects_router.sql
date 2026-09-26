-- ================================================================ BC reversal, command router, workspace read, public RPCs

-- The inverse of one BC document, linked, in the reverse order of what depends on it (M:5040, 6.3). A reversal that
-- would take away stock or a quantity that a later document already used is refused by the native guards (negative
-- stock) or by the lot state check at the end; nothing is left half-done.
CREATE OR REPLACE FUNCTION erp.bc_reverse_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare d erp.bc_documents_v1%rowtype;v_reason text;r record;v_lot uuid;v_event erp.bc_lot_events_v1%rowtype;v_item uuid;v_lots uuid[]:='{}';
  s jsonb;v_version bigint;v_payroll uuid;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['document_id','expected_version','reason'],array['document_id','expected_version','reason'],
    'reversal payload');
  v_reason:=erp.bc_text_v1(p_payload,'reason',true,1000);
  select * into d from erp.bc_documents_v1 where id=erp.bc_uuid_v1(p_payload,'document_id',true) for update;
  if d.id is null then raise exception 'BC_DOCUMENT_NOT_FOUND: dokumen tidak ditemukan';end if;
  if jsonb_typeof(p_payload->'expected_version') is distinct from 'string' or p_payload->>'expected_version' is distinct from d.row_version::text then
    raise exception 'STALE_VERSION: dokumen berubah; muat ulang';end if;
  if d.status<>'POSTED' then raise exception 'BC_ALREADY_REVERSED: dokumen sudah dibatalkan';end if;
  if d.action in('VALUE_CUSTODY') then perform erp.require_permission('finance.hpp.manage');end if;
  if d.action in('CREDIT_NOTE_RETURN','ROUND_NOTE') then perform erp.require_permission('finance.contractor_accessory.reverse');end if;
  if d.action='ALLOCATE_CARRY' then perform erp.require_permission('finance.payroll.approve');end if;
  -- Lots this document created or touched, locked in id order.
  for v_lot in select x from (select id x from erp.bc_return_lots_v1 where document_id=d.id union select lot_id from erp.bc_lot_events_v1 where document_id=d.id
      union select parent_lot_id from erp.bc_return_lots_v1 where document_id=d.id and parent_lot_id is not null) z order by x loop
    perform pg_advisory_xact_lock(hashtextextended('BCLOT|'||v_lot::text,0));
    v_lots:=v_lots||v_lot;
  end loop;
  -- Dependants first: a receipt whose lots have live events or credited children, an in-custody garment used by an internal
  -- use, a count whose variance was resolved, a credit whose carry is in a payroll or whose custody child has events.
  if exists(select 1 from erp.bc_return_lots_v1 l join erp.bc_lot_events_v1 e on e.lot_id=l.id join erp.bc_documents_v1 x on x.id=e.document_id
      where l.document_id=d.id and x.status='POSTED' and x.id<>d.id) then
    raise exception 'BC_REVERSE_DEPENDANTS: batalkan dahulu pemeriksaan, kredit atau penilaian atas penerimaan ini';end if;
  if d.action='CUSTOMER_GARMENT_IN' and (exists(select 1 from erp.bc_customer_custody_v1 c join erp.bc_documents_v1 x on x.id=c.out_document_id
        where c.in_document_id=d.id and x.status='POSTED')
      or exists(select 1 from erp.bc_internal_use_lines_v1 u join erp.bc_documents_v1 x on x.id=u.document_id where u.customer_custody_id=d.id and x.status='POSTED')) then
    raise exception 'BC_REVERSE_DEPENDANTS: titipan ini sudah dikembalikan atau dipakai pada pemakaian servis';end if;
  if d.action='COUNT_POST' and exists(select 1 from erp.bc_count_variances_v1 v join erp.bc_documents_v1 x on x.id=v.resolution_document_id
      where v.document_id=d.id and x.status='POSTED') then
    raise exception 'BC_REVERSE_DEPENDANTS: batalkan dahulu penyelesaian selisih hitung';end if;
  if d.action='CREDIT_NOTE_RETURN' then
    select * into v_event from erp.bc_lot_events_v1 where document_id=d.id;
    -- The carry lock of ALLOCATE_CARRY: a reversal and an allocation of the same credit never run at once.
    perform pg_advisory_xact_lock(hashtextextended('BCCARRY|'||v_event.id::text,0));
    if v_event.amount_carry>0 and erp.bc_carry_remaining_v1(v_event.id)<>v_event.amount_carry then
      raise exception 'BC_REVERSE_DEPENDANTS: lepaskan dahulu kredit yang sudah masuk payroll';end if;
  end if;

  update erp.bc_documents_v1 set status='REVERSED',reversed_at=clock_timestamp(),reversed_by=erp.current_app_user_id(),reversal_reason=v_reason,
    row_version=row_version+1 where id=d.id returning row_version into v_version;
  -- Native inverses in reverse creation order.
  for r in select l.link_kind,l.link_id from erp.bc_document_links_v1 l where l.document_id=d.id
      order by case l.link_kind when 'PAYROLL_LINE' then 1 when 'JOURNAL' then 2 when 'SETTLEMENT' then 3 when 'MOVEMENT' then 4 else 5 end,
        l.link_id desc loop
    if r.link_kind='TRANSFER' then
      perform erp.reverse_material_transfer_v2(r.link_id,v_reason,gen_random_uuid(),(select row_version from erp.material_transfers where id=r.link_id));
    elsif r.link_kind='ADJUSTMENT' then
      perform erp.reverse_material_adjustment_v2(r.link_id,v_reason,gen_random_uuid(),(select row_version from erp.material_adjustments where id=r.link_id));
    elsif r.link_kind='MOVEMENT' then
      perform erp.reverse_material_movement(r.link_id,v_reason);
      perform erp.recalculate_material_cost((select material_id from erp.material_stock_movements where id=r.link_id));
    elsif r.link_kind='JOURNAL' then
      perform erp._cp3_r4_reverse_journal_internal(r.link_id,v_reason);
    elsif r.link_kind='SETTLEMENT' then
      perform erp.reverse_opening_subledger_settlement(r.link_id,v_reason);
    elsif r.link_kind='PAYROLL_LINE' then
      select payroll_id into v_payroll from erp.payroll_reimbursements where id=r.link_id;
      delete from erp.payroll_reimbursements where id=r.link_id;
      perform erp.recalculate_payroll(v_payroll);
    end if;
  end loop;
  if d.action='CUSTOMER_GARMENT_OUT' then update erp.bc_customer_custody_v1 set out_document_id=null where out_document_id=d.id;end if;
  if d.action in('CREDIT_NOTE_RETURN','ROUND_NOTE') then
    for v_item in select coalesce(l.note_item_id,null) from erp.bc_lot_events_v1 e join erp.bc_return_lots_v1 l on l.id=e.lot_id where e.document_id=d.id and l.note_item_id is not null
      union select item_id from erp.bc_note_roundings_v1 where id=d.id loop
      if erp.bc_note_item_allocated_v1(v_item)>erp.bc_note_item_collectible_v1(v_item)+0.01 then
        raise exception 'BC_REVERSE_BELOW_PAID: potongan payroll melebihi tagihan sesudah pembatalan';end if;
      perform erp.refresh_contractor_issue_payroll_status(v_item);
    end loop;
  end if;
  -- Every lot keeps non-negative buckets.
  foreach v_lot in array v_lots loop
    s:=erp.bc_lot_state_v1(v_lot);
    if (s->>'waiting')::numeric<0 or (s->>'usable')::numeric<0 or (s->>'damaged')::numeric<0 then
      raise exception 'BC_REVERSE_DEPENDANTS: jumlah ini sudah dipakai dokumen sesudahnya; batalkan dokumen itu dahulu';end if;
  end loop;
  return jsonb_build_object('reversed_document_id',d.id,'row_version',v_version::text);
end;$function$;

-- ---------------------------------------------------------------- the command router (one public RPC)
CREATE OR REPLACE FUNCTION erp.save_accessory_service_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO '' SET "TimeZone" TO 'UTC' SET "DateStyle" TO 'ISO, YMD'
AS $function$
declare v_action text:=upper(btrim(coalesce(p_action,'')));v_cached jsonb;v_result jsonb;v_doc uuid;
begin
  perform erp.require_permission('warehouse.accessory.view');
  if v_action not in('SET_POLICY','REGISTER_ZONE','FILL_POST','RETURN_TO_WAREHOUSE','INTERNAL_USE','RECEIVE_RETURN','INSPECT','VALUE_CUSTODY',
      'CREDIT_NOTE_RETURN','ALLOCATE_CARRY','DISPOSE_STOCK','CLOSE_CUSTODY','CUSTOMER_GARMENT_IN','CUSTOMER_GARMENT_OUT','COUNT_POST',
      'RESOLVE_VARIANCE','ROUND_NOTE','REVERSE') then
    raise exception 'BC_ACTION_UNKNOWN: tindakan aksesori tidak dikenal';end if;
  if v_action in('FILL_POST','RETURN_TO_WAREHOUSE','INTERNAL_USE','RECEIVE_RETURN','INSPECT','CLOSE_CUSTODY','DISPOSE_STOCK','CUSTOMER_GARMENT_IN',
      'CUSTOMER_GARMENT_OUT','COUNT_POST','RESOLVE_VARIANCE','REVERSE') then
    perform erp.require_permission('warehouse.stock.adjust');
  end if;
  if v_action='REVERSE' then
    begin perform erp.require_owner_admin();
    exception when others then raise exception 'BC_APPROVAL_REQUIRED: pembatalan memerlukan owner/admin';end;
  end if;
  perform erp.require_internal();
  if p_client_request_id is null then raise exception 'BC_REQUEST_ID_REQUIRED: request id wajib';end if;
  if jsonb_typeof(p_payload) is distinct from 'object' or octet_length(p_payload::text)>20000 then raise exception 'BC_PAYLOAD_INVALID: data tidak valid';end if;
  v_cached:=erp._idempotency_begin('save_accessory_service_action_v1',p_client_request_id,
    erp._request_hash(jsonb_build_object('action',v_action,'payload',p_payload)));
  if v_cached is not null then return v_cached;end if;
  if exists(select 1 from erp.bc_documents_v1 where id=p_client_request_id) then raise exception 'BC_REQUEST_REUSED: request id sudah dipakai';end if;
  perform set_config('app.change_reason',coalesce(nullif(btrim(p_payload->>'reason'),''),v_action),true);
  perform erp.bc_enter_context_v1();
  v_result:=case v_action
    when 'SET_POLICY' then erp.bc_set_policy_v1(p_payload,p_client_request_id)
    when 'REGISTER_ZONE' then erp.bc_register_zone_v1(p_payload,p_client_request_id)
    when 'FILL_POST' then erp.bc_move_post_v1(v_action,p_payload,p_client_request_id)
    when 'RETURN_TO_WAREHOUSE' then erp.bc_move_post_v1(v_action,p_payload,p_client_request_id)
    when 'INTERNAL_USE' then erp.bc_internal_use_v1(p_payload,p_client_request_id)
    when 'RECEIVE_RETURN' then erp.bc_receive_return_v1(p_payload,p_client_request_id)
    when 'INSPECT' then erp.bc_inspect_v1(p_payload,p_client_request_id)
    when 'VALUE_CUSTODY' then erp.bc_value_custody_v1(p_payload,p_client_request_id)
    when 'CREDIT_NOTE_RETURN' then erp.bc_credit_note_return_v1(p_payload,p_client_request_id)
    when 'ALLOCATE_CARRY' then erp.bc_allocate_carry_v1(p_payload,p_client_request_id)
    when 'DISPOSE_STOCK' then erp.bc_dispose_stock_v1(p_payload,p_client_request_id)
    when 'CLOSE_CUSTODY' then erp.bc_close_custody_v1(p_payload,p_client_request_id)
    when 'CUSTOMER_GARMENT_IN' then erp.bc_customer_garment_v1(v_action,p_payload,p_client_request_id)
    when 'CUSTOMER_GARMENT_OUT' then erp.bc_customer_garment_v1(v_action,p_payload,p_client_request_id)
    when 'COUNT_POST' then erp.bc_count_post_v1(p_payload,p_client_request_id)
    when 'RESOLVE_VARIANCE' then erp.bc_resolve_variance_v1(p_payload,p_client_request_id)
    when 'ROUND_NOTE' then erp.bc_round_note_v1(p_payload,p_client_request_id)
    else erp.bc_reverse_v1(p_payload,p_client_request_id) end;
  perform erp.bc_leave_context_v1();
  v_doc:=case when v_action='REVERSE' then (v_result->>'reversed_document_id')::uuid
    when v_action in('SET_POLICY','REGISTER_ZONE') then null else p_client_request_id end;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values(case when v_action='SET_POLICY' then 'bc_policy_settings_v1' when v_action='REGISTER_ZONE' then 'bc_accessory_zones_v1' else 'bc_documents_v1' end,
    coalesce(v_doc,p_client_request_id),case when v_action='REVERSE' then 'REVERSE' else 'INSERT' end,
    jsonb_build_object('action',v_action,'result',v_result),erp.current_app_user_id(),coalesce(nullif(btrim(p_payload->>'reason'),''),v_action));
  v_result:=v_result||jsonb_build_object('request_id',p_client_request_id,'action',v_action,'document_id',v_doc,
    'status',case when v_action='REVERSE' then 'REVERSED' when v_action in('SET_POLICY','REGISTER_ZONE') then 'SAVED' else 'POSTED' end,
    'row_version',case when v_action='REVERSE' then v_result->>'row_version' when v_doc is not null then
      (select row_version::text from erp.bc_documents_v1 where id=v_doc) end);
  return erp._idempotency_complete('save_accessory_service_action_v1',p_client_request_id,v_result);
end;$function$;

-- ---------------------------------------------------------------- workspace read (server-side search and pagination)
CREATE OR REPLACE FUNCTION erp.bc_bucket_label_v1(p_kind text)
 RETURNS text LANGUAGE sql IMMUTABLE SET search_path TO ''
AS $function$
  select case p_kind when 'MAIN' then 'Di gudang — siap dipakai' when 'SERVICE_POST' then 'Di pos servis — siap dipakai'
    when 'INSPECTION' then 'Menunggu pemeriksaan' when 'DAMAGED' then 'Rusak — menunggu disposisi' end
$function$;

CREATE OR REPLACE FUNCTION erp.get_accessory_service_workspace_v1(p_filters jsonb default '{}'::jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO '' SET "TimeZone" TO 'UTC'
AS $function$
declare v_query text:=lower(btrim(coalesce(p_filters->>'query','')));v_location uuid;v_page integer;v_size integer;v_offset integer;
  v_action text:=upper(nullif(btrim(p_filters->>'action'),''));v_status text:=upper(nullif(btrim(p_filters->>'status'),''));
  v_from date;v_to date;v_value boolean;v_result jsonb;v_doc uuid;v_card jsonb;v_note_query text:=lower(btrim(coalesce(p_filters->>'note_query','')));
  v_customer_query text:=lower(btrim(coalesce(p_filters->>'customer_query','')));v_admin boolean;
begin
  perform erp.require_permission('warehouse.accessory.view');
  perform erp._cp3_assert_closed_json_object(p_filters,array[]::text[],array['query','location_id','action','status','date_from','date_to','page',
    'page_size','document_id','card_material_id','card_location_id','note_query','customer_query'],'accessory service filters');
  if length(v_query)>120 or length(v_note_query)>120 or length(v_customer_query)>120 then raise exception 'BC_FILTER_INVALID: pencarian terlalu panjang';end if;
  if p_filters ? 'page' and (jsonb_typeof(p_filters->'page')<>'number' or (p_filters->>'page')!~'^[1-9][0-9]{0,5}$') then raise exception 'BC_FILTER_INVALID: halaman';end if;
  if p_filters ? 'page_size' and (jsonb_typeof(p_filters->'page_size')<>'number' or (p_filters->>'page_size')!~'^[1-9][0-9]?$' or (p_filters->>'page_size')::int>50) then
    raise exception 'BC_FILTER_INVALID: ukuran halaman 1-50';end if;
  v_page:=coalesce((p_filters->>'page')::int,1);v_size:=coalesce((p_filters->>'page_size')::int,25);v_offset:=(v_page-1)*v_size;
  v_location:=erp.bc_uuid_v1(p_filters,'location_id',false);
  if p_filters ? 'date_from' then v_from:=erp.bb_parse_date_v1(p_filters->>'date_from','date_from');end if;
  if p_filters ? 'date_to' then v_to:=erp.bb_parse_date_v1(p_filters->>'date_to','date_to');end if;
  -- Costs and values only for roles allowed to see them (M:10.2).
  v_value:=erp.has_permission('finance.hpp.view');
  v_admin:=coalesce(erp.current_app_role(),'') in('OWNER','ADMIN') or session_user in('postgres','supabase_admin');
  v_doc:=erp.bc_uuid_v1(p_filters,'document_id',false);
  if p_filters ? 'card_material_id' then
    with m as(select x.*,sum(x.qty_signed) over(order by x.physical_at,x.system_created_at,x.id) running
        from erp.material_stock_movements x where x.material_id=erp.bc_uuid_v1(p_filters,'card_material_id',true)
          and x.location_id=erp.bc_uuid_v1(p_filters,'card_location_id',true)),
      pg as(select * from m order by physical_at desc,system_created_at desc,id desc limit v_size offset v_offset)
    select jsonb_build_object('total',(select count(*) from m),'rows',coalesce(jsonb_agg(jsonb_build_object('movement_id',id,'movement_type',movement_type,
      'source_type',source_type,'physical_local',to_char(physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI'),
      'recorded_local',to_char(system_created_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI'),
      'before',(running-qty_signed)::text,'qty',qty_signed::text,'after',running::text) order by physical_at desc,system_created_at desc,id desc),'[]'::jsonb))
    into v_card from pg;
  end if;
  with loc as(select l.id,l.location_code,l.location_name,coalesce(z.zone_kind,'MAIN') kind from erp.locations l
      left join erp.bc_accessory_zones_v1 z on z.location_id=l.id where l.location_type='RAW_MATERIAL_WAREHOUSE' and l.is_active),
    stock as(select m.id material_id,m.material_sku,m.material_name,m.unit_code,c.category_name,l.id location_id,l.location_name,l.kind,
        sum(s.qty_signed) qty,max(s.system_created_at) last_at,m.moving_average_cost
      from erp.material_stock_movements s join erp.materials m on m.id=s.material_id and m.material_type='ACCESSORY'
      left join erp.accessory_categories c on c.id=m.accessory_category_id join loc l on l.id=s.location_id
      where (v_location is null or l.id=v_location)
        and (v_query='' or strpos(lower(concat_ws(' ',m.material_sku,m.material_name,c.category_name,l.location_name)),v_query)>0)
      group by m.id,m.material_sku,m.material_name,m.unit_code,c.category_name,l.id,l.location_name,l.kind,m.moving_average_cost
      having sum(s.qty_signed)<>0),
    docs as(select d.*,(select count(*) from erp.bc_document_links_v1 k where k.document_id=d.id) links from erp.bc_documents_v1 d
      where (v_action is null or d.action=v_action) and (v_status is null or d.status=v_status)
        and (v_from is null or erp._cp3_business_date(d.physical_at)>=v_from) and (v_to is null or erp._cp3_business_date(d.physical_at)<=v_to)
        and (v_query='' or strpos(lower(concat_ws(' ',d.document_number,d.reference,d.responsible,d.reason)),v_query)>0)
        and (v_location is null or exists(select 1 from erp.bc_document_links_v1 k join erp.material_transfers t on t.id=k.link_id
            where k.document_id=d.id and v_location in(t.from_location_id,t.to_location_id))
          or exists(select 1 from erp.bc_document_links_v1 k join erp.material_adjustments a on a.id=k.link_id where k.document_id=d.id and a.location_id=v_location)
          or exists(select 1 from erp.bc_return_lots_v1 l where l.document_id=d.id and l.location_id=v_location))),
    lots as(select l.*,m.material_sku,m.material_name,erp.bc_lot_state_v1(l.id) st,(select document_number from erp.bc_documents_v1 where id=l.document_id) doc_number
      from erp.bc_return_lots_v1 l join erp.materials m on m.id=l.material_id
      where (l.document_id is null or (select status from erp.bc_documents_v1 where id=l.document_id)='POSTED')
        and (l.parent_event_id is null or (select x.status from erp.bc_lot_events_v1 e join erp.bc_documents_v1 x on x.id=e.document_id where e.id=l.parent_event_id)='POSTED')
        and (v_query='' or strpos(lower(concat_ws(' ',m.material_sku,m.material_name,l.reference)),v_query)>0))
  select jsonb_build_object(
    'can_see_value',v_value,'is_admin',v_admin,'filters',p_filters,'page',v_page,'page_size',v_size,
    'policies',(select jsonb_agg(jsonb_build_object('key',replace(policy_key,'_','-'),'status',status,'version',version::text,
        'value',case when v_admin then value end,'set_at',set_at) order by policy_key) from erp.bc_policy_settings_v1),
    'locations',coalesce((select jsonb_agg(jsonb_build_object('id',id,'code',location_code,'name',location_name,'kind',kind,'label',erp.bc_bucket_label_v1(kind))
      order by kind,location_name,id) from loc),'[]'::jsonb),
    'stock_total',(select count(*) from stock),
    'stock',coalesce((select jsonb_agg(jsonb_build_object('material_id',material_id,'sku',material_sku,'name',material_name,'unit',unit_code,
        'category',category_name,'location_id',location_id,'location',location_name,'bucket',erp.bc_bucket_label_v1(kind),'kind',kind,
        'qty',qty::numeric(24,6)::text,'value',case when v_value then round(qty*moving_average_cost,2)::text end,
        'updated_local',to_char(last_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI')) order by material_name,location_name,material_id,location_id)
      from (select * from stock order by material_name,location_name,material_id,location_id limit v_size offset v_offset) x),'[]'::jsonb),
    'documents_total',(select count(*) from docs),
    'documents',coalesce((select jsonb_agg(jsonb_build_object('id',id,'number',document_number,'action',action,'status',status,
        'physical_local',to_char(physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI'),
        'recorded_local',to_char(created_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI'),'responsible',responsible,'reference',reference,
        'reason',reason,'row_version',row_version::text,'links',links) order by physical_at desc,id)
      from (select * from docs order by physical_at desc,id limit v_size offset v_offset) x),'[]'::jsonb),
    'lots',coalesce((select jsonb_agg(jsonb_build_object('id',id,'document',doc_number,'source_kind',source_kind,'owner_kind',owner_kind,
        'value_status',case value_mode when 'LEDGER' then 'Bernilai di buku' when 'PENDING' then 'Belum dinilai' else 'Milik mandor — menunggu kredit' end,
        'material_id',material_id,'sku',material_sku,'name',material_name,'location_id',location_id,
        'received_local',to_char(received_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI'),'note_item_id',note_item_id,
        'opening_note_line_id',opening_note_line_id,'reference',reference,
        'state',erp.bc_lot_state_text_v1(id)) order by (st->>'open')::numeric=0,received_at desc,id)
      from (select * from lots order by (st->>'open')::numeric=0,received_at desc,id limit 100) x),'[]'::jsonb),
    'outstanding',coalesce((select jsonb_agg(jsonb_build_object('id',o.id,'source_kind',o.source_kind,'owner_kind',o.owner_kind,'material_id',o.material_id,
        'description',o.description,'holder',o.holder,'reference',o.reference,'expected',o.qty_expected::text,
        'received',coalesce((select sum(l.qty_received) from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
          where l.outstanding_id=o.id and d.status='POSTED'),0)::numeric(24,6)::text,'label','Belum kembali') order by o.created_at desc,o.id)
      from erp.bc_outstanding_returns_v1 o where o.status='OPEN'),'[]'::jsonb),
    'customer_custody',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'customer',k.customer_name,'description',c.description,'qty',c.qty::text,
        'received_local',to_char(c.received_at at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI'),'returned',c.out_document_id is not null
          and (select status from erp.bc_documents_v1 where id=c.out_document_id)='POSTED') order by c.received_at desc,c.id)
      from erp.bc_customer_custody_v1 c join erp.customers k on k.id=c.customer_id
      where c.batch_id is not null or (select status from erp.bc_documents_v1 where id=c.in_document_id)='POSTED'),'[]'::jsonb),
    'variances',coalesce((select jsonb_agg(jsonb_build_object('id',v.id,'material_id',v.material_id,'location_id',v.location_id,'book',v.book_qty::text,
        'counted',v.counted_qty::text,'variance',v.variance::text,'label','Selisih belum diketahui — perlu tinjauan',
        'resolved',v.resolution_document_id is not null and (select status from erp.bc_documents_v1 where id=v.resolution_document_id)='POSTED')
        order by v.counted_at desc,v.id)
      from erp.bc_count_variances_v1 v where (select status from erp.bc_documents_v1 where id=v.document_id)='POSTED'),'[]'::jsonb),
    'notes',case when v_note_query<>'' then coalesce((select jsonb_agg(jsonb_build_object('item_id',i.id,'issue_id',h.id,'number',h.issue_number,
        'contractor',c.contractor_name,'material_id',i.material_id,'sku',m.material_sku,'name',m.material_name,'qty',i.qty::text,
        'returned',coalesce((select sum(l.qty_received) from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
          where l.note_item_id=i.id and d.status='POSTED'),0)::numeric(24,6)::text,
        'collectible',round(erp.bc_note_item_collectible_v1(i.id),2)::text,'allocated',erp.bc_note_item_allocated_v1(i.id)::numeric(24,2)::text,
        'payroll_status',i.payroll_status) order by h.issue_number,i.id)
      from erp.contractor_material_issue_items i join erp.contractor_material_issues h on h.id=i.issue_id join erp.contractors c on c.id=h.contractor_id
      join erp.materials m on m.id=i.material_id
      where i.id in(select i2.id from erp.contractor_material_issue_items i2 join erp.contractor_material_issues h2 on h2.id=i2.issue_id
        join erp.contractors c2 on c2.id=h2.contractor_id join erp.materials m2 on m2.id=i2.material_id
        where h2.status='POSTED' and m2.material_type='ACCESSORY' and strpos(lower(concat_ws(' ',h2.issue_number,c2.contractor_name)),v_note_query)>0
        order by h2.issue_number,i2.id limit 50)),'[]'::jsonb) end,
    'opening_notes',case when v_note_query<>'' then coalesce((select jsonb_agg(jsonb_build_object('line_id',n.id,'number',n.document_number,
        'contractor',c.contractor_name,'material_id',n.material_id,'sku',m.material_sku,'name',m.material_name,'qty',n.qty::text,
        'line_amount',n.line_amount::text,'returned',coalesce((select sum(l.qty_received) from erp.bc_return_lots_v1 l join erp.bc_documents_v1 d on d.id=l.document_id
          where l.opening_note_line_id=n.id and d.status='POSTED'),0)::numeric(24,6)::text,'remaining_receivable',(b.original_amount-b.settled_amount)::text) order by n.document_number,n.line_number)
      from erp.bc_opening_note_lines_v1 n join erp.opening_subledger_balances b on b.id=n.balance_id join erp.contractors c on c.id=b.contractor_id
      join erp.materials m on m.id=n.material_id where n.id in(select n2.id from erp.bc_opening_note_lines_v1 n2 join erp.opening_subledger_balances b2 on b2.id=n2.balance_id
        join erp.contractors c2 on c2.id=b2.contractor_id where strpos(lower(concat_ws(' ',n2.document_number,c2.contractor_name)),v_note_query)>0
        order by n2.document_number,n2.line_number limit 50)),'[]'::jsonb) end,
    'customers',case when v_customer_query<>'' then coalesce((select jsonb_agg(jsonb_build_object('id',id,'code',customer_code,'name',customer_name) order by customer_name,id)
      from (select * from erp.customers where is_active and strpos(lower(concat_ws(' ',customer_code,customer_name)),v_customer_query)>0 order by customer_name,id limit 20) x),'[]'::jsonb) end,
    'document',case when v_doc is not null then (select jsonb_build_object('id',d.id,'number',d.document_number,'action',d.action,'status',d.status,
        'row_version',d.row_version::text,'payload',d.payload,'policy_versions',d.policy_versions,'reversal_reason',d.reversal_reason,
        'links',coalesce((select jsonb_agg(jsonb_build_object('kind',k.link_kind,'id',k.link_id) order by k.link_kind,k.link_id) from erp.bc_document_links_v1 k where k.document_id=d.id),'[]'::jsonb),
        'events',coalesce((select jsonb_agg(jsonb_build_object('id',e.id,'lot_id',e.lot_id,'kind',e.event_kind,'condition',e.condition,'qty',e.qty::text,
          'qty_usable',e.qty_usable::text,'qty_damaged',e.qty_damaged::text,'inspector',e.inspector,
          'amount',case when v_value or v_admin then e.amount::text end,'unpaid',case when v_value or v_admin then e.amount_unpaid::text end,
          'carry',case when v_value or v_admin then e.amount_carry::text end,'refund',case when v_value or v_admin then e.amount_refund::text end,
          'carry_remaining',case when (v_value or v_admin) and e.event_kind='CREDIT' and e.amount_carry>0 then erp.bc_carry_remaining_v1(e.id)::text end,
          -- Owner decision no. 4: where the carried due went (payroll, its status, amount), so return -> credit -> payroll -> payment is traceable.
          'carry_payroll_lines',case when (v_value or v_admin) and e.event_kind='CREDIT' and e.amount_carry>0 then coalesce((select jsonb_agg(jsonb_build_object(
              'payroll_id',ps.id,'payroll_number',ps.payroll_number,'status',ps.status,'amount',r.amount::numeric(18,2)::text,'period_end',ps.period_end::text)
              order by ps.period_end,ps.id) from erp.payroll_reimbursements r join erp.payroll_settlements ps on ps.id=r.payroll_id
            where r.bc_credit_event_id=e.id and r.source_type='BC_RETURN_CARRY'),'[]'::jsonb) end)
          order by e.created_at,e.id)
          from erp.bc_lot_events_v1 e where e.document_id=d.id),'[]'::jsonb),
        -- ACC-DEC05 carry: the draft payrolls of the same mandor that a carried credit may enter (owner/admin with payroll view).
        'carry_payrolls',case when v_admin and erp.has_permission('finance.payroll.view') then coalesce((select jsonb_agg(jsonb_build_object('id',p.id,
            'number',p.payroll_number,'status',p.status,'period_end',p.period_end::text,
            'is_next',exists(select 1 from erp.bc_lot_events_v1 e2 where e2.document_id=d.id and e2.event_kind='CREDIT' and erp.bc_carry_next_payroll_v1(e2.id)=p.id))
            order by p.period_end,p.id)
          from erp.payroll_settlements p where p.status in('DRAFT','CALCULATED','REVIEW') and p.contractor_id in(
            select coalesce(l.contractor_id,(select c.contractor_id from erp.contractor_material_issues c join erp.contractor_material_issue_items i on i.issue_id=c.id
              where i.id=l.note_item_id)) from erp.bc_lot_events_v1 e join erp.bc_return_lots_v1 l on l.id=e.lot_id
            where e.document_id=d.id and e.event_kind='CREDIT' and e.amount_carry>0)),'[]'::jsonb) else '[]'::jsonb end)
      from erp.bc_documents_v1 d where d.id=v_doc) end,
    'card',v_card,
    -- Pick lists for the forms: accessories matching the search, cash accounts; for owner/admin the accounts, categories and
    -- users the policy settings name.
    'materials',coalesce((select jsonb_agg(jsonb_build_object('id',id,'sku',material_sku,'name',material_name,'unit',unit_code) order by material_name,id)
      from (select m.* from erp.materials m where m.material_type='ACCESSORY' and m.is_active
        and (v_query='' or strpos(lower(concat_ws(' ',m.material_sku,m.material_name)),v_query)>0) order by m.material_name,m.id limit 50) x),'[]'::jsonb),
    'cash_accounts',case when v_admin then coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',cash_account_name) order by cash_account_name,id)
      from erp.cash_accounts where is_active),'[]'::jsonb) end,
    'accounts',case when v_admin then coalesce((select jsonb_agg(jsonb_build_object('id',id,'code',account_code,'name',account_name,'type',account_type)
      order by account_code,id) from erp.chart_accounts where is_postable and is_active),'[]'::jsonb) end,
    'categories',case when v_admin then coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',category_name) order by category_name,id)
      from erp.accessory_categories where is_active),'[]'::jsonb) end,
    'users',case when v_admin then coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',full_name) order by full_name,id)
      from erp.app_users where is_active),'[]'::jsonb) end
  ) into v_result;
  return v_result;
end;$function$;

CREATE OR REPLACE FUNCTION public.erp_save_accessory_service_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.save_accessory_service_action_v1(p_action,p_payload,p_client_request_id) $function$;
CREATE OR REPLACE FUNCTION public.erp_get_accessory_service_workspace_v1(p_filters jsonb default '{}'::jsonb)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.get_accessory_service_workspace_v1(p_filters) $function$;

do $grants$
declare f text;
begin
  for f in select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='erp' and (p.proname like 'bc\_%' or p.proname in('save_accessory_service_action_v1','get_accessory_service_workspace_v1')) loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
  end loop;
end $grants$;
revoke all on function public.erp_save_accessory_service_action_v1(text,jsonb,uuid) from public,anon;
revoke all on function public.erp_get_accessory_service_workspace_v1(jsonb) from public,anon;
grant execute on function public.erp_save_accessory_service_action_v1(text,jsonb,uuid) to authenticated,service_role;
grant execute on function public.erp_get_accessory_service_workspace_v1(jsonb) to authenticated,service_role;
