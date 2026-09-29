-- Narrow initial writer: draft and post route through accepted CP6 functions.
-- Reverse/invoice/transfer are separate P09/P13 increments, not fake actions.
create function cp7_procurement.command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;z jsonb;r jsonb;line jsonb;roll jsonb;expected bigint;price boolean:=false;roll_count integer:=0;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_procurement.access_now();
 if p_request is null or p_action not in ('SAVE_DRAFT','POST') or p_action is null then raise exception 'CP7_PROCUREMENT_ACTION';end if;
 if p_expected is not null and p_expected!~'^[1-9][0-9]{0,18}$' then raise exception 'CP7_PROCUREMENT_VERSION';end if;
 expected:=p_expected::bigint;
 if p_action='SAVE_DRAFT' then
  if a->'can_create'<>'true'::jsonb then raise exception using errcode='42501',message='CP7_PROCUREMENT_CREATE_DENIED';end if;
  perform cp7_procurement.fields(p_payload,array['id','purchase_number','supplier_id','location_id','physical_at','change_reason','notes','supplier_invoice_number','due_date','lines'],
   array['purchase_number','supplier_id','location_id','physical_at','change_reason','lines']);
  if exists(select 1 from jsonb_each(p_payload) e where e.key<>'lines' and jsonb_typeof(e.value) not in ('string','null')) then raise exception 'CP7_PROCUREMENT_FIELDS';end if;
  if (p_payload ? 'supplier_invoice_number' or p_payload ? 'due_date') and a->'can_value'<>'true'::jsonb then raise exception using errcode='42501',message='CP7_PROCUREMENT_VALUE_DENIED';end if;
  if nullif(p_payload->>'id','') is not null and a->'can_value'<>'true'::jsonb then raise exception using errcode='42501',message='CP7_PROCUREMENT_VALUE_REQUIRED_FOR_EDIT';end if;
  if jsonb_typeof(p_payload->'lines') is distinct from 'array' or jsonb_array_length(p_payload->'lines') not between 1 and 100 then raise exception 'CP7_PROCUREMENT_LINES';end if;
  for line in select value from jsonb_array_elements(p_payload->'lines') loop
   perform cp7_procurement.fields(line,array['material_id','qty','unit_price','price_state','price_source','rolls','lot_number','notes'],array['material_id','qty','price_state','price_source','rolls']);
   if exists(select 1 from jsonb_each(line) e where e.key<>'rolls' and jsonb_typeof(e.value) not in ('string','null')) then raise exception 'CP7_PROCUREMENT_FIELDS';end if;
   perform cp7_procurement.decimal(line->'qty',true);
   if line ? 'unit_price' and line->'unit_price'<>'null'::jsonb then
    perform cp7_procurement.decimal(line->'unit_price',false);price:=true;
   elsif line->>'price_source' is distinct from 'BENCHMARK' or line->>'price_state' is distinct from 'ESTIMATED' then
    raise exception 'CP7_PROCUREMENT_PRICE_REQUIRED_OR_BENCHMARK';end if;
   if line->>'price_source'='MIGRATION' then raise exception 'CP7_PROCUREMENT_USE_IMPORT_WORKFLOW';end if;
   if jsonb_typeof(line->'rolls') is distinct from 'array' or jsonb_array_length(line->'rolls')>500 then raise exception 'CP7_PROCUREMENT_ROLLS';end if;
   roll_count:=roll_count+jsonb_array_length(line->'rolls');
   if roll_count>2000 then raise exception 'CP7_PROCUREMENT_DOCUMENT_TOO_LARGE';end if;
   for roll in select value from jsonb_array_elements(line->'rolls') loop
    perform cp7_procurement.fields(roll,array['roll_number','qty','notes'],array['roll_number','qty']);
    if exists(select 1 from jsonb_each(roll) e where jsonb_typeof(e.value) not in ('string','null')) then raise exception 'CP7_PROCUREMENT_FIELDS';end if;
    perform cp7_procurement.decimal(roll->'qty',true);
   end loop;
  end loop;
  if price and a->'can_value'<>'true'::jsonb then raise exception using errcode='42501',message='CP7_PROCUREMENT_VALUE_DENIED';end if;
  r:=erp.save_material_purchase_draft_v2(p_payload,p_request,expected);
 else
  if a->'can_post'<>'true'::jsonb then raise exception using errcode='42501',message='CP7_PROCUREMENT_POST_DENIED';end if;
  perform cp7_procurement.fields(p_payload,array['purchase_id','change_reason'],array['purchase_id','change_reason']);
  if exists(select 1 from jsonb_each(p_payload) e where jsonb_typeof(e.value)<>'string') then raise exception 'CP7_PROCUREMENT_FIELDS';end if;
  if expected is null then raise exception 'CP7_PROCUREMENT_VERSION';end if;
  r:=erp.post_material_purchase_v2((p_payload->>'purchase_id')::uuid,p_request,expected,p_payload->>'change_reason');
 end if;
 -- A revocation while an existing business writer waited rolls back the entire
 -- call. A cached outcome is checked against current access as well.
 z:=cp7_procurement.access_now();
 if z<>a then raise exception using errcode='42501',message='CP7_PROCUREMENT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.procurement-outcome.v1','kind','COMMITTED_OUTCOME',
  'action',p_action,'request_id',p_request,'purchase_id',r->'purchase_id','status',r->'status','row_version',r->>'row_version');
end $$;
