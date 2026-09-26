-- ================================================================ BD facade: one writer and one reader for the laundry BD flows
CREATE OR REPLACE FUNCTION erp.bd_post_priced_delivery_v1(p_payload jsonb,p_request uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_delivery jsonb;v_pricing jsonb;v_computed jsonb;v_response jsonb;v_version bigint;v_line uuid;
begin
  perform erp._cp3_assert_closed_json_object(p_payload,array['delivery','expected_version','pricing'],array['delivery','expected_version','pricing'],
    'priced delivery payload');
  v_delivery:=p_payload->'delivery';v_pricing:=p_payload->'pricing';
  if jsonb_typeof(v_delivery) is distinct from 'object' then raise exception 'BD_PRICING_INVALID: delivery wajib objek POST_DELIVERY';end if;
  if jsonb_typeof(p_payload->'expected_version') is distinct from 'string' or p_payload->>'expected_version'!~'^[1-9][0-9]{0,18}$' then
    raise exception 'BD_FIELD_INVALID: expected_version wajib versi Potongan';end if;
  v_version:=(p_payload->>'expected_version')::bigint;
  -- The prices read below stay as read until the delivery is posted: the version writers take the same locks (process and
  -- scoped rates per vendor/process, component and package prices per vendor) and the terms writer locks the vendor row.
  perform pg_advisory_xact_lock(hashtextextended('LRATE:'||erp.bd_uuid_v1(v_delivery,'vendor_id',true)::text||':'
    ||erp.bd_uuid_v1(v_delivery,'wash_process_id',true)::text,0));
  perform pg_advisory_xact_lock(hashtextextended('LRATE:'||erp.bd_uuid_v1(v_delivery,'vendor_id',true)::text||':*',0));
  perform 1 from erp.laundry_vendors where id=erp.bd_uuid_v1(v_delivery,'vendor_id',true) for share;
  v_computed:=erp.bd_compute_pricing_v1(v_delivery,v_pricing);
  insert into erp.bd_execution_context_v1(backend_pid,transaction_id,action,request_id,pricing)
  values(pg_backend_pid(),txid_current(),'POST_PRICED_DELIVERY',p_request,v_computed);
  v_response:=erp.save_laundry_qc_action_v1('POST_DELIVERY',v_delivery,p_request,v_version);
  delete from erp.bd_execution_context_v1 where backend_pid=pg_backend_pid() and transaction_id=txid_current();
  select l.id into v_line from erp.laundry_delivery_lines l where l.delivery_id=(v_response->>'delivery_id')::uuid;
  if not exists(select 1 from erp.bd_laundry_priced_lines_v1 where delivery_line_id=v_line) then
    raise exception 'BD_INTERNAL: harga kiriman tidak tercatat';end if;
  return v_response||jsonb_build_object('pricing',erp.bd_priced_line_json_v1(v_line));
end;$function$;

CREATE OR REPLACE FUNCTION erp.bd_priced_line_json_v1(p_line uuid)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
  select jsonb_build_object('delivery_line_id',p.delivery_line_id,'delivery_id',p.delivery_id,'mode',p.pricing_mode,'unit',p.pricing_unit,
    'qty_sent',p.qty_sent,'total_known',p.total_known::numeric(18,2)::text,'total_complete',p.total_complete,'policy_versions',p.policy_versions,
    'charges',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'line_no',c.line_no,'kind',c.kind,'ref_id',c.ref_id,'label',c.label,
        'covered_qty',c.covered_qty,'rate_status',c.rate_status,'unit_rate',c.unit_rate::numeric(18,2)::text,'amount',c.amount::numeric(18,2)::text,
        'included_components',c.included_components) order by c.line_no) from erp.bd_laundry_charge_lines_v1 c where c.delivery_line_id=p.delivery_line_id),'[]'::jsonb),
    'sizes',coalesce((select jsonb_agg(jsonb_build_object('delivery_batch_size_line_id',e.delivery_batch_size_line_id,'size_id',s.size_id,
        'qty_sent',e.qty_sent,'known_amount',e.known_amount::numeric(18,2)::text,'complete',e.complete) order by s.size_id)
      from erp.bd_laundry_size_estimates_v1 e join erp.laundry_delivery_batch_size_lines s on s.id=e.delivery_batch_size_line_id
      where e.delivery_line_id=p.delivery_line_id),'[]'::jsonb))
  from erp.bd_laundry_priced_lines_v1 p where p.delivery_line_id=p_line
$function$;

CREATE OR REPLACE FUNCTION erp.save_laundry_bd_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_action text:=upper(btrim(coalesce(p_action,'')));v_prior erp.bd_requests_v1%rowtype;v_result jsonb;
begin
  if erp.current_app_user_id() is null and session_user not in('postgres','supabase_admin') then raise exception 'BD_AUTH_REQUIRED: login ERP diperlukan';end if;
  if p_client_request_id is null then raise exception 'BD_REQUEST_REQUIRED: id permintaan wajib';end if;
  if jsonb_typeof(p_payload) is distinct from 'object' then raise exception 'BD_PAYLOAD_INVALID: payload wajib objek';end if;
  if v_action not in('SET_POLICY','SAVE_VENDOR_TERMS','SAVE_COMPONENT','SAVE_COMPONENT_RATE','SAVE_PACKAGE','SAVE_PACKAGE_RATE','SAVE_PROCESS_RATE',
    'SAVE_SCOPED_RATE','POST_PRICED_DELIVERY','SET_CHARGE_PRICE','SAVE_INVOICE_DRAFT','CANCEL_INVOICE_DRAFT','POST_INVOICE','REVERSE_INVOICE','SET_OPENING_ESTIMATE') then
    raise exception 'BD_ACTION_UNKNOWN: aksi laundry % tidak dikenal',v_action;end if;
  perform pg_advisory_xact_lock(hashtextextended('BDREQ:'||p_client_request_id::text,0));
  select * into v_prior from erp.bd_requests_v1 where request_id=p_client_request_id;
  if v_prior.request_id is not null then
    if v_prior.action<>v_action or v_prior.payload<>p_payload or v_prior.actor is distinct from erp.current_app_user_id() then
      raise exception 'BD_REQUEST_REUSED: id permintaan sudah dipakai untuk isi lain';end if;
    return v_prior.response||jsonb_build_object('replayed',true);
  end if;
  v_result:=case v_action
    when 'SET_POLICY' then erp.bd_set_policy_v1(p_payload,p_client_request_id)
    when 'POST_PRICED_DELIVERY' then erp.bd_post_priced_delivery_v1(p_payload,p_client_request_id)
    when 'SET_CHARGE_PRICE' then erp.bd_set_charge_price_v1(p_payload,p_client_request_id)
    when 'SAVE_INVOICE_DRAFT' then erp.bd_save_invoice_draft_v1(p_payload,p_client_request_id)
    when 'CANCEL_INVOICE_DRAFT' then erp.bd_cancel_invoice_draft_v1(p_payload,p_client_request_id)
    when 'POST_INVOICE' then erp.bd_post_invoice_v1(p_payload,p_client_request_id)
    when 'REVERSE_INVOICE' then erp.bd_reverse_invoice_v1(p_payload,p_client_request_id)
    when 'SET_OPENING_ESTIMATE' then erp.bd_set_opening_estimate_v1(p_payload,p_client_request_id)
    else erp.bd_save_master_v1(v_action,p_payload,p_client_request_id) end;
  v_result:=jsonb_build_object('action',v_action,'request_id',p_client_request_id,'status','SAVED')||v_result;
  insert into erp.bd_requests_v1(request_id,action,actor,payload,response) values(p_client_request_id,v_action,erp.current_app_user_id(),p_payload,v_result);
  return v_result;
end;$function$;

-- Reader: policies, master (terms, components with the current price, packages, process and scoped rates) and priced deliveries.
CREATE OR REPLACE FUNCTION erp.get_laundry_bd_workspace_v1(p_filters jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare v_vendor uuid;v_now timestamptz:=statement_timestamp();v_money boolean;
begin
  perform erp.require_permission('production.laundry.view');
  if jsonb_typeof(coalesce(p_filters,'{}'::jsonb)) is distinct from 'object' then raise exception 'BD_FILTER_INVALID: filter wajib objek';end if;
  v_vendor:=erp.bd_uuid_v1(coalesce(p_filters,'{}'::jsonb),'vendor_id',false);
  v_money:=erp.has_permission('finance.hpp.view') or erp.has_permission('finance.hpp.manage');
  return jsonb_build_object(
    'filters',coalesce(p_filters,'{}'::jsonb),'money_visible',v_money,
    'can_manage_master',erp.current_app_role() in('OWNER','ADMIN') and erp.has_permission('master.partner.manage'),
    'can_set_price',erp.current_app_role() in('OWNER','ADMIN') and erp.has_permission('finance.hpp.manage'),
    'is_owner',erp.current_app_role()='OWNER',
    'policies',(select jsonb_agg(jsonb_build_object('key',replace(policy_key,'_','-'),'status',status,'value',value,'version',version::text,
        'set_at',to_char(set_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),'reason',reason) order by policy_key) from erp.bd_policy_settings_v1),
    'vendors',coalesce((select jsonb_agg(jsonb_build_object('id',v.id,'code',v.vendor_code,'name',v.vendor_name,
        'pricing_mode',coalesce(t.pricing_mode,'RATE'),'pricing_unit',coalesce(t.pricing_unit,'PCS'),
        'bd_priced',t.pricing_mode is distinct from null and (t.pricing_mode<>'RATE' or t.pricing_unit<>'PCS' or t.minimum_charge is not null)
          or exists(select 1 from erp.bd_laundry_scoped_rates_v1 r where r.vendor_id=v.id),
        'minimum_charge',case when v_money then t.minimum_charge::numeric(18,2)::text end,'terms_version',coalesce(t.row_version,0)::text) order by v.vendor_name,v.id)
      from erp.laundry_vendors v left join erp.bd_laundry_vendor_terms_v1 t on t.vendor_id=v.id where v.is_active),'[]'::jsonb),
    'processes',coalesce((select jsonb_agg(jsonb_build_object('id',w.id,'code',w.process_code,'name',w.process_name) order by w.process_name,w.id)
      from erp.wash_processes w where w.is_active),'[]'::jsonb),
    'components',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'vendor_id',c.vendor_id,'code',c.component_code,'name',c.component_name,
        'is_active',c.is_active,'current',(select jsonb_build_object('status',r.rate_status,'rate',case when v_money then r.rate_per_pcs::numeric(18,2)::text end,
          'from',to_char(r.effective_from at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'))
          from erp.bd_laundry_component_rates_v1 r where r.component_id=c.id and r.effective_from<=v_now and (r.effective_to is null or r.effective_to>v_now)))
        order by c.component_name,c.id)
      from erp.bd_laundry_components_v1 c where v_vendor is null or c.vendor_id=v_vendor),'[]'::jsonb),
    'packages',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'vendor_id',p.vendor_id,'code',p.package_code,'name',p.package_name,'is_active',p.is_active,
        'component_ids',(select coalesce(jsonb_agg(pc.component_id order by pc.component_id),'[]'::jsonb) from erp.bd_laundry_package_components_v1 pc where pc.package_id=p.id),
        'current_rate',(select case when v_money then r.rate_per_pcs::numeric(18,2)::text end from erp.bd_laundry_package_rates_v1 r
          where r.package_id=p.id and r.effective_from<=v_now and (r.effective_to is null or r.effective_to>v_now))) order by p.package_name,p.id)
      from erp.bd_laundry_packages_v1 p where v_vendor is null or p.vendor_id=v_vendor),'[]'::jsonb),
    'process_rates',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'vendor_id',r.vendor_id,'wash_process_id',r.wash_process_id,
        'rate',case when v_money then r.rate_per_pcs::numeric(18,2)::text end,'from',to_char(r.effective_from at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),
        'to',to_char(r.effective_to at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) order by r.vendor_id,r.wash_process_id,r.effective_from)
      from erp.laundry_vendor_rate_versions r where (v_vendor is null or r.vendor_id=v_vendor) and (r.effective_to is null or r.effective_to>v_now - interval '120 days')),'[]'::jsonb),
    'scoped_rates',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'vendor_id',r.vendor_id,'wash_process_id',r.wash_process_id,'scope',r.scope,
        'model_id',r.model_id,'size_id',r.size_id,'color_name',r.color_name,'rate',case when v_money then r.rate_per_pcs::numeric(18,2)::text end,
        'from',to_char(r.effective_from at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) order by r.created_at)
      from erp.bd_laundry_scoped_rates_v1 r where v_vendor is null or r.vendor_id=v_vendor),'[]'::jsonb),
    -- Amounts of a priced delivery only for money readers (quantities, labels and price status for everyone).
    'priced_deliveries',coalesce((select jsonb_agg(case when v_money then x.j else (x.j-'total_known')||jsonb_build_object(
        'charges',(select coalesce(jsonb_agg(c-'unit_rate'-'amount' order by (c->>'line_no')::integer),'[]'::jsonb) from jsonb_array_elements(x.j->'charges') c),
        'sizes',(select coalesce(jsonb_agg(s-'known_amount' order by s->>'size_id'),'[]'::jsonb) from jsonb_array_elements(x.j->'sizes') s)) end
      order by x.at desc) from (
        select erp.bd_priced_line_json_v1(p.delivery_line_id)||jsonb_build_object('delivery_number',d.delivery_number,'status',d.status,
          'physical_local',to_char(d.physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS')) j,d.physical_at at
        from erp.bd_laundry_priced_lines_v1 p join erp.laundry_deliveries d on d.id=p.delivery_id
        where v_vendor is null or p.vendor_id=v_vendor order by d.physical_at desc limit 50) x),'[]'::jsonb),
    -- ALL-W05: laundry work returned before cutover and not yet billed (billed later by an invoice line with opening_uninvoiced_id).
    'opening_uninvoiced',coalesce((select jsonb_agg(jsonb_build_object('id',u.id,'vendor_id',u.vendor_id,'vendor_code',v.vendor_code,
        'document_number',u.document_number,'receipt_date',u.receipt_date,'category',u.category,'qty',u.qty,'billed',erp.bd_opening_billed_v1(u.id),
        'estimate_status',case when u.estimated_amount is null then 'UNKNOWN' else 'KNOWN' end,
        'estimated_amount',case when v_money then u.estimated_amount::text end,'released',case when v_money then erp.bd_opening_released_v1(u.id)::numeric(18,2)::text end,
        'invoiced',erp.bd_opening_invoiced_v1(u.id),'po_number',(select po_number from erp.production_orders where id=u.po_id),
        'dispatch_number',u.dispatch_number,'row_version',u.row_version::text) order by u.receipt_date,u.document_number,u.category)
      from erp.bd_opening_laundry_uninvoiced_v1 u join erp.laundry_vendors v on v.id=u.vendor_id where v_vendor is null or u.vendor_id=v_vendor),'[]'::jsonb),
    -- Money readers only (null otherwise: hidden, never empty): the latest invoices and, for one vendor, the receipt lines it
    -- can still bill (capacity and billed quantity per category), and the accounts the owner may pick in LAU-DEC03/06.
    'invoices',case when v_money then coalesce((select jsonb_agg(erp.bd_invoice_json_v1(i.id)||jsonb_build_object('vendor_code',v.vendor_code) order by i.created_at desc,i.id)
        from (select * from erp.bd_laundry_invoices_v1 x where v_vendor is null or x.vendor_id=v_vendor order by x.created_at desc,x.id limit 50) i
        join erp.laundry_vendors v on v.id=i.vendor_id),'[]'::jsonb) end,
    'billable_receipts',case when v_money and v_vendor is not null then coalesce((select jsonb_agg(x.j order by x.at desc,x.id) from (
        select rl.id,r.physical_at at,jsonb_build_object('receipt_line_id',rl.id,'receipt_number',r.receipt_number,'delivery_number',d.delivery_number,
          'po_number',po.po_number,'received_local',to_char(r.physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI:SS'),
          'failed_attempt',a.id is not null,'estimate',rl.actual_cost::numeric(18,2)::text,'released',erp.bd_released_estimate_v1(rl.id)::numeric(18,2)::text,
          'price_known',erp.bd_line_complete_v1(rl.delivery_line_id),
          'capacity',jsonb_build_object('GOOD',erp.bd_invoice_capacity_v1(rl.id,'GOOD'),'BS',erp.bd_invoice_capacity_v1(rl.id,'BS'),
            'FAILED_ATTEMPT',erp.bd_invoice_capacity_v1(rl.id,'FAILED_ATTEMPT')),
          'billed',jsonb_build_object('GOOD',erp.bd_invoice_billed_v1(rl.id,'GOOD'),'BS',erp.bd_invoice_billed_v1(rl.id,'BS'),
            'FAILED_ATTEMPT',erp.bd_invoice_billed_v1(rl.id,'FAILED_ATTEMPT'))) j
        from erp.laundry_receipt_lines rl join erp.laundry_receipts r on r.id=rl.receipt_id and r.status='POSTED'
        join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id join erp.laundry_deliveries d on d.id=dl.delivery_id
        join erp.production_orders po on po.id=d.po_id left join erp.laundry_failed_wash_attempts a on a.receipt_line_id=rl.id
        where d.vendor_id=v_vendor and rl.actual_cost_status='ESTIMATED' and rl.actual_cost is not null and not erp.bd_receipt_invoiced_v1(rl.id)
        order by r.physical_at desc,rl.id limit 200) x),'[]'::jsonb) end,
    'accounts',case when v_money then coalesce((select jsonb_agg(jsonb_build_object('id',a.id,'code',a.account_code,'name',a.account_name,'type',a.account_type)
        order by a.account_code) from erp.chart_accounts a where a.is_active and a.is_postable and a.account_type in('ASSET','EXPENSE')),'[]'::jsonb) end);
end;$function$;

CREATE OR REPLACE FUNCTION public.erp_save_laundry_bd_action_v1(p_action text,p_payload jsonb,p_client_request_id uuid)
 RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.save_laundry_bd_action_v1(p_action,p_payload,p_client_request_id) $function$;
CREATE OR REPLACE FUNCTION public.erp_get_laundry_bd_workspace_v1(p_filters jsonb default '{}'::jsonb)
 RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$ select erp.get_laundry_bd_workspace_v1(p_filters) $function$;

-- Grants (as BC): the tables are private (RLS on, nothing granted), every erp.bd_* function and the two erp facades are revoked
-- from every API role; only the two public wrappers are callable, by an ERP user (the facades check login and permissions).
do $grants$
declare t text;f text;
begin
  foreach t in array array['bd_policy_settings_v1','bd_policy_setting_events_v1','bd_execution_context_v1','bd_laundry_vendor_terms_v1',
    'bd_laundry_components_v1','bd_laundry_component_rates_v1','bd_laundry_packages_v1','bd_laundry_package_components_v1','bd_laundry_package_rates_v1',
    'bd_laundry_scoped_rates_v1','bd_requests_v1','bd_laundry_priced_lines_v1','bd_laundry_charge_lines_v1','bd_laundry_charge_shares_v1',
    'bd_laundry_size_estimates_v1','bd_laundry_receipt_allocations_v1','bd_laundry_invoices_v1','bd_laundry_invoice_lines_v1',
    'bd_opening_laundry_claims_v1','bd_opening_laundry_claim_events_v1','bd_opening_laundry_uninvoiced_v1','bd_custody_sources_v1'] loop
    execute format('alter table erp.%I enable row level security',t);
    execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
  end loop;
  for f in select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='erp' and (p.proname like 'bd\_%' or p.proname in('save_laundry_bd_action_v1','get_laundry_bd_workspace_v1')) loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
  end loop;
end $grants$;
revoke all on function public.erp_save_laundry_bd_action_v1(text,jsonb,uuid) from public,anon;
revoke all on function public.erp_get_laundry_bd_workspace_v1(jsonb) from public,anon;
grant execute on function public.erp_save_laundry_bd_action_v1(text,jsonb,uuid) to authenticated,service_role;
grant execute on function public.erp_get_laundry_bd_workspace_v1(jsonb) to authenticated,service_role;
