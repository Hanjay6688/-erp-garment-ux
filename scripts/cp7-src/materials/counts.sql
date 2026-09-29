-- Physical-count intent is a private companion to the accepted adjustment.
-- Only native SAVE/POST/REVERSE writers change ERP stock or accounting.
create table cp7_material.count_documents(
 adjustment_id uuid primary key,input jsonb not null,source_signature jsonb not null,captured_at timestamptz not null default statement_timestamp()
);
alter table cp7_material.count_documents owner to cp7_material_write;
alter table cp7_material.count_documents enable row level security;
revoke all on cp7_material.count_documents from public,anon,authenticated,service_role,cp7_capture;
grant select on cp7_material.count_documents to cp7_material_read;
grant select on erp.material_adjustments,erp.material_adjustment_items to cp7_material_read;
grant execute on function erp.save_material_adjustment_draft_v2(jsonb,uuid,bigint),
 erp.post_material_adjustment_v2(uuid,uuid,bigint,text),erp.reverse_material_adjustment_v2(uuid,text,uuid,bigint) to cp7_material_write;

create function cp7_material.count_lines(p_location uuid,p_at timestamptz,p_lines jsonb,p_check boolean,p_exclude uuid default null) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare a jsonb;line jsonb;m erp.materials;roll uuid;quantity numeric;counted numeric;delta numeric;basis text;rows jsonb:='[]';seen text[]:='{}';key text;
begin
 a:=cp7_material.access_now();
 if p_location is null or p_at is null or p_at>statement_timestamp() then raise exception 'CP7_COUNT_TIME_LOCATION';end if;
 if not exists(select 1 from erp.locations where id=p_location and is_active and location_type='RAW_MATERIAL_WAREHOUSE')
  or exists(select 1 from erp.bc_accessory_zones_v1 where location_id=p_location) then raise exception 'CP7_COUNT_ORDINARY_WAREHOUSE_REQUIRED';end if;
 if jsonb_typeof(p_lines) is distinct from 'array' or jsonb_array_length(p_lines) not between 1 and 100 then raise exception 'CP7_COUNT_LINES';end if;
 for line in select value from jsonb_array_elements(p_lines) loop
  if jsonb_typeof(line) is distinct from 'object' or not line ?& array['material_id','roll_id','physical_qty']
   or exists(select 1 from jsonb_each(line) e where e.key not in('material_id','roll_id','physical_qty','basis_token','input_unit_cost','notes') or jsonb_typeof(e.value) not in('string','null'))
   or line->>'physical_qty' is null or line->>'physical_qty'!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$' then raise exception 'CP7_COUNT_EXACT_PHYSICAL_QTY';end if;
  select * into m from erp.materials where id=(line->>'material_id')::uuid and is_active;
  roll:=(line->>'roll_id')::uuid;
  if not found or (m.material_type='FABRIC' and (roll is null or not exists(select 1 from erp.material_rolls where id=roll and material_id=m.id)))
   or (m.material_type<>'FABRIC' and roll is not null) then raise exception 'CP7_COUNT_MATERIAL_LINEAGE';end if;
  key:=m.id::text||'/'||coalesce(roll::text,'NO_ROLL');
  if key=any(seen) then raise exception 'CP7_COUNT_DUPLICATE_LINE';end if;seen:=array_append(seen,key);
  select coalesce(sum(s.qty_signed),0),md5(coalesce(string_agg(jsonb_build_array(s.id,extract(epoch from s.physical_at),s.qty_signed)::text,',' order by s.id),''))
   into quantity,basis from erp.material_stock_movements s
   where s.material_id=m.id and s.roll_id is not distinct from roll and s.location_id=p_location and s.physical_at<=p_at
    and not(p_exclude is not null and s.source_type='MATERIAL_ADJUSTMENT_ITEM' and exists(select 1 from erp.material_adjustment_items i where i.adjustment_id=p_exclude and i.id=s.source_id));
  if quantity<0 then raise exception 'CP7_COUNT_SOURCE_CONFLICT';end if;
  if p_check and line->>'basis_token' is distinct from basis then raise exception 'CP7_COUNT_STOCK_CHANGED_REVIEW_AGAIN';end if;
  counted:=(line->>'physical_qty')::numeric;delta:=counted-quantity;
  if line->>'input_unit_cost' is not null then
   if a->'can_value' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_COUNT_COST_DENIED';end if;
   if line->>'input_unit_cost'!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$' or delta<=0 then raise exception 'CP7_COUNT_POSITIVE_COST_ONLY';end if;
  end if;
  if p_check and delta>0 and line->>'input_unit_cost' is null then raise exception 'CP7_COUNT_POSITIVE_COST_REQUIRED';end if;
  rows:=rows||jsonb_build_array(jsonb_build_object('material_id',m.id,'material_sku',m.material_sku,'material_name',m.material_name,'unit_code',m.unit_code,
   'roll_id',roll,'roll_number',(select roll_number from erp.material_rolls where id=roll),'system_qty',quantity::text,'physical_qty',counted::text,'qty_signed',delta::text,'basis_token',basis));
 end loop;
 return rows;
end $$;

create function cp7_material.count_preview(p_scope jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare rows jsonb;a jsonb;
begin
 a:=cp7_material.access_now();
 if jsonb_typeof(p_scope) is distinct from 'object' or not p_scope ?& array['location_id','physical_at','items']
  or exists(select 1 from jsonb_object_keys(p_scope) k where k not in('location_id','physical_at','items')) then raise exception 'CP7_COUNT_SCOPE';end if;
 rows:=cp7_material.count_lines((p_scope->>'location_id')::uuid,(p_scope->>'physical_at')::timestamptz,p_scope->'items',false);
 return jsonb_build_object('contract_version','cp7.material-count-preview.v1','read_at',statement_timestamp(),
  'location_id',p_scope->'location_id','physical_at',(p_scope->>'physical_at')::timestamptz,'basis','POSTED_PHYSICAL_AT_COUNT_CURRENT_KNOWLEDGE','items',rows);
end $$;
create function public.erp_cp7_preview_material_count_v1(p_scope jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_material.count_preview(p_scope)$$;

create function cp7_material.count_signature(p_id uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('number',h.adjustment_number,'location',h.location_id,'at',h.physical_at,'reason',h.reason_code,'notes',h.notes,
  'items',(select jsonb_agg(jsonb_build_array(i.material_id,i.roll_id,i.qty_signed,i.input_unit_cost,i.notes) order by i.material_id,i.roll_id nulls first,i.id)
   from erp.material_adjustment_items i where i.adjustment_id=h.id)) from erp.material_adjustments h where h.id=p_id
$$;

create function cp7_material.count_command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;r jsonb;old cp7_material.requests;proof cp7_material.count_documents;rows jsonb;items jsonb;line jsonb;x jsonb;payload jsonb;ident uuid;expected bigint;signature jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_material.access_now();
 if a->'can_adjust' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_MATERIAL_ADJUST_DENIED';end if;
 if p_action is null or p_action not in('SAVE','POST','DELETE','REVERSE') or p_request is null then raise exception 'CP7_COUNT_ACTION';end if;
 if p_action='REVERSE' and a->'can_reverse' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_MATERIAL_REVERSE_DENIED';end if;
 if p_expected is not null and p_expected!~'^[1-9][0-9]{0,18}$' then raise exception 'CP7_MATERIAL_VERSION';end if;expected:=p_expected::bigint;
 if jsonb_typeof(p_payload) is distinct from 'object' then raise exception 'CP7_COUNT_FIELDS';end if;
 insert into cp7_material.requests(actor,request_id,action,payload,expected_version) values(auth.uid(),p_request,p_action||'_COUNT',p_payload,p_expected) on conflict do nothing;
 select * into old from cp7_material.requests where actor=auth.uid() and request_id=p_request for update;
 if old.action<>(p_action||'_COUNT') or old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_COUNT_REQUEST_CHANGED';end if;
 if cp7_material.access_now()<>a then raise exception using errcode='42501',message='CP7_MATERIAL_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 if p_action='SAVE' then
  if not p_payload ?& array['adjustment_number','location_id','physical_at','reason_code','change_reason','items']
   or exists(select 1 from jsonb_each(p_payload) e where e.key not in('id','adjustment_number','location_id','physical_at','reason_code','change_reason','items','notes') or (e.key<>'items' and jsonb_typeof(e.value) not in('string','null')))
   or p_payload->>'reason_code' not in('LOSS','DAMAGE','FOUND','COUNT_CORRECTION') then raise exception 'CP7_COUNT_FIELDS';end if;
  ident:=(p_payload->>'id')::uuid;
  if ident is not null then
   perform 1 from cp7_material.count_documents where adjustment_id=ident for update;
   if not found then raise exception 'CP7_COUNT_SOURCE_WORKFLOW_REQUIRED';end if;
  end if;
  rows:=cp7_material.count_lines((p_payload->>'location_id')::uuid,(p_payload->>'physical_at')::timestamptz,p_payload->'items',true);
  items:='[]';
  for x in select value from jsonb_array_elements(rows) loop
   if (x->>'qty_signed')::numeric=0 then continue;end if;
   select value into line from jsonb_array_elements(p_payload->'items') where (value->>'material_id')::uuid=(x->>'material_id')::uuid and (value->>'roll_id')::uuid is not distinct from (x->>'roll_id')::uuid;
   items:=items||jsonb_build_array(jsonb_build_object('material_id',x->'material_id','roll_id',x->'roll_id','qty_signed',x->'qty_signed','input_unit_cost',line->'input_unit_cost','notes',line->'notes'));
  end loop;
  if jsonb_array_length(items)=0 then raise exception 'CP7_COUNT_NO_DIFFERENCE';end if;
  payload:=p_payload||jsonb_build_object('items',items);
  insert into cp7_material.execution_context values(pg_backend_pid(),txid_current(),auth.uid(),'SAVE_COUNT','warehouse.stock.adjust');
  r:=erp.save_material_adjustment_draft_v2(payload,p_request,expected);ident:=(r->>'material_adjustment_id')::uuid;
  signature:=cp7_material.count_signature(ident);
  insert into cp7_material.count_documents(adjustment_id,input,source_signature) values(ident,p_payload,signature)
   on conflict(adjustment_id) do update set input=excluded.input,source_signature=excluded.source_signature,captured_at=statement_timestamp();
 else
  if expected is null or not p_payload ?& array['adjustment_id','change_reason'] or exists(select 1 from jsonb_each(p_payload) e where e.key not in('adjustment_id','change_reason') or jsonb_typeof(e.value)<>'string') then raise exception 'CP7_COUNT_FIELDS';end if;
  ident:=(p_payload->>'adjustment_id')::uuid;
  select * into proof from cp7_material.count_documents where adjustment_id=ident for update;
  if not found then raise exception 'CP7_COUNT_SOURCE_WORKFLOW_REQUIRED';end if;
  insert into cp7_material.execution_context values(pg_backend_pid(),txid_current(),auth.uid(),p_action||'_COUNT','warehouse.stock.adjust');
  if p_action='POST' then
   if cp7_material.count_signature(ident) is distinct from proof.source_signature then raise exception 'CP7_COUNT_DRAFT_CHANGED_REVIEW_AGAIN';end if;
   perform cp7_material.count_lines((proof.input->>'location_id')::uuid,(proof.input->>'physical_at')::timestamptz,proof.input->'items',true);
   r:=erp.post_material_adjustment_v2(ident,p_request,expected,p_payload->>'change_reason');
   -- Native movement triggers hold each material row through commit. This new
   -- statement rechecks the latest committed prefix after all real row waits.
   perform cp7_material.count_lines((proof.input->>'location_id')::uuid,(proof.input->>'physical_at')::timestamptz,proof.input->'items',true,ident);
   if cp7_material.count_signature(ident) is distinct from proof.source_signature then raise exception 'CP7_COUNT_DRAFT_CHANGED_REVIEW_AGAIN';end if;
  elsif p_action='DELETE' then
   r:=erp.save_material_adjustment_draft_v2(jsonb_build_object('id',ident,'action','DELETE','change_reason',p_payload->'change_reason'),p_request,expected);
   delete from cp7_material.count_documents where adjustment_id=ident;
  else r:=erp.reverse_material_adjustment_v2(ident,p_payload->>'change_reason',p_request,expected);
  end if;
 end if;
 if cp7_material.access_now()<>a then raise exception using errcode='42501',message='CP7_MATERIAL_ACCESS_CHANGED';end if;
 delete from cp7_material.execution_context where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 r:=jsonb_build_object('contract_version','cp7.material-count-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'adjustment_id',ident,'status',r->'status','row_version',r->>'row_version');
 update cp7_material.requests set response=r where actor=auth.uid() and request_id=p_request;
 return r;
end $$;
create function public.erp_cp7_save_material_count_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_material.count_command(p_action,p_payload,p_request,p_expected)$$;
