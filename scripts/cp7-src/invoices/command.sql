create function cp7_invoice.command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;z jsonb;r jsonb;l jsonb;expected bigint;pid uuid;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_invoice.access_now();
 if p_action is null or p_action not in('FINALIZE','REVERSE') or p_request is null then raise exception 'CP7_INVOICE_ACTION';end if;
 if p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$' then raise exception 'CP7_INVOICE_VERSION';end if;
 expected:=p_expected::bigint;
 if jsonb_typeof(p_payload) is distinct from 'object' then raise exception 'CP7_INVOICE_FIELDS';end if;
 if p_action='FINALIZE' then
  if a->'finalize' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_INVOICE_FINALIZE_DENIED';end if;
  if not p_payload ?& array['purchase_id','supplier_invoice_number','invoice_date','received_at','reason','lines'] or exists(select 1 from jsonb_each(p_payload) e
   where e.key not in('purchase_id','supplier_invoice_number','invoice_date','received_at','reason','lines','due_date','notes') or(e.key<>'lines' and jsonb_typeof(e.value) not in('string','null'))) then raise exception 'CP7_INVOICE_FIELDS';end if;
  if exists(select 1 from unnest(array['purchase_id','supplier_invoice_number','invoice_date','received_at','reason']) k
   where jsonb_typeof(p_payload->k) is distinct from 'string' or nullif(btrim(p_payload->>k),'') is null) then raise exception 'CP7_INVOICE_FIELDS';end if;
  if jsonb_typeof(p_payload->'lines') is distinct from 'array' or jsonb_array_length(p_payload->'lines') not between 1 and 100 then raise exception 'CP7_INVOICE_LINES';end if;
  for l in select value from jsonb_array_elements(p_payload->'lines') loop
   if jsonb_typeof(l) is distinct from 'object' or not l ?& array['purchase_item_id','qty_invoiced','final_unit_price']
    or exists(select 1 from jsonb_each(l) e where e.key not in('purchase_item_id','qty_invoiced','final_unit_price','discount_amount','notes') or jsonb_typeof(e.value) not in('string','null')) then raise exception 'CP7_INVOICE_LINE';end if;
   if l->>'qty_invoiced' is null or l->>'qty_invoiced'!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$' or (l->>'qty_invoiced')::numeric<=0
    or l->>'final_unit_price' is null or l->>'final_unit_price'!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$'
    or(l ? 'discount_amount' and (l->>'discount_amount' is null or l->>'discount_amount'!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$')) then raise exception 'CP7_INVOICE_EXACT_DECIMAL';end if;
  end loop;
  pid:=(p_payload->>'purchase_id')::uuid;
  r:=erp.finalize_material_purchase_invoice_v2(p_payload,p_request,expected);
 else
  if a->'reverse' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_INVOICE_REVERSE_DENIED';end if;
  if not p_payload ?& array['purchase_id','invoice_id','reason'] or exists(select 1 from jsonb_each(p_payload) e where e.key not in('purchase_id','invoice_id','reason') or jsonb_typeof(e.value)<>'string') then raise exception 'CP7_INVOICE_FIELDS';end if;
  pid:=(p_payload->>'purchase_id')::uuid;
  perform cp7_invoice.assert_single_receipt((p_payload->>'invoice_id')::uuid,pid);
  r:=erp.reverse_material_supplier_invoice_v2((p_payload->>'invoice_id')::uuid,p_payload->>'reason',p_request,expected);
 end if;
 z:=cp7_invoice.access_now();if z<>a then raise exception using errcode='42501',message='CP7_INVOICE_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.purchase-invoice-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,
  'purchase_id',pid,'invoice_id',r->'supplier_invoice_id','version_subject',case when p_action='FINALIZE' then 'RECEIPT' else 'INVOICE' end,
  'row_version',r->>'row_version','status',case when p_action='FINALIZE' then 'POSTED' else r->>'status' end);
end $$;
create function public.erp_cp7_save_purchase_invoice_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_invoice.command(p_action,p_payload,p_request,p_expected)$$;
