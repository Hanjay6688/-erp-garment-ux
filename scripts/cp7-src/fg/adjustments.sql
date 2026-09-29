-- Existing FG adjustment writers own quantities, HPP and inverse journals.
-- This bridge admits an exact reviewed signed correction, never a client HPP.
create role cp7_fg_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
grant usage on schema cp7_fg,erp,auth to cp7_fg_write;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text),
 erp.save_fg_adjustment_draft_v2(jsonb,uuid,bigint),erp.post_fg_adjustment_v2(uuid,uuid,bigint,text),erp.reverse_fg_adjustment_v2(uuid,text,uuid,bigint) to cp7_fg_write;
grant select on erp.fg_adjustments,erp.fg_adjustment_items to cp7_fg_read;
create table cp7_fg.requests(actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,expected_version text,response jsonb,primary key(actor,request_id));
alter table cp7_fg.requests owner to cp7_fg_write;
alter table cp7_fg.requests enable row level security;
create table cp7_fg.adjustment_documents(adjustment_id uuid primary key,source_signature jsonb not null);
alter table cp7_fg.adjustment_documents owner to cp7_fg_write;
alter table cp7_fg.adjustment_documents enable row level security;
revoke all on cp7_fg.requests,cp7_fg.adjustment_documents from public,anon,authenticated,service_role,cp7_capture,cp7_fg_read;
grant select on cp7_fg.adjustment_documents to cp7_fg_read;

create function cp7_fg.adjust_access() returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;allowed boolean;
begin
 a:=cp7_fg.access_now('SUMMARY');
 allowed:=erp.has_permission('warehouse.stock.adjust') and a->'profile'->>'role_code' in('OWNER','ADMIN');
 return a||jsonb_build_object('can_adjust',allowed);
end $$;

create function cp7_fg.adjust_signature(p_id uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('number',h.adjustment_number,'location',h.location_id,'at',extract(epoch from h.physical_at),'reason_code',h.reason_code,'reason',h.reason,'notes',h.notes,
  'items',(select jsonb_agg(jsonb_build_array(i.id,i.lot_id,i.product_id,i.quality_grade,i.qty_signed,i.notes) order by i.id) from erp.fg_adjustment_items i where i.adjustment_id=h.id))
 from erp.fg_adjustments h where h.id=p_id
$$;

create function cp7_fg.adjust_validate(p_payload jsonb,p_id uuid default null) returns void
language plpgsql stable security definer set search_path='' as $$
declare h erp.fg_adjustments;loc uuid;at_time timestamptz;items jsonb;line jsonb;seen text[]:='{}';key text;
begin
 perform cp7_fg.adjust_access();
 if p_id is not null then
  select * into h from erp.fg_adjustments where id=p_id;
  if not found then raise exception 'CP7_FG_ADJUST_NOT_FOUND';end if;
  loc:=h.location_id;at_time:=h.physical_at;
  select jsonb_agg(jsonb_build_object('lot_id',lot_id,'product_id',product_id,'quality_grade',quality_grade,'qty_signed',qty_signed::text,'notes',notes) order by id) into items from erp.fg_adjustment_items where adjustment_id=p_id;
 else
  loc:=(p_payload->>'location_id')::uuid;at_time:=(p_payload->>'physical_at')::timestamptz;items:=p_payload->'items';
 end if;
 if at_time is null or at_time>statement_timestamp() or loc is null or not exists(select 1 from erp.locations where id=loc and is_active and location_type='FG_WAREHOUSE') then raise exception 'CP7_FG_ADJUST_TIME_LOCATION';end if;
 if jsonb_typeof(items) is distinct from 'array' or jsonb_array_length(items) not between 1 and 100 then raise exception 'CP7_FG_ADJUST_LINES';end if;
 for line in select value from jsonb_array_elements(items) loop
  if jsonb_typeof(line) is distinct from 'object' or not line ?& array['lot_id','product_id','quality_grade','qty_signed']
   or exists(select 1 from jsonb_each(line) e where e.key not in('lot_id','product_id','quality_grade','qty_signed','notes') or jsonb_typeof(e.value) not in('string','null'))
   or line->>'qty_signed' is null or line->>'qty_signed'!~'^-?[1-9][0-9]{0,8}$'
   or coalesce(line->>'quality_grade','') not in('GRADE_A','GRADE_B') then raise exception 'CP7_FG_ADJUST_EXACT_LINE';end if;
  if not exists(select 1 from erp.fg_lots l join erp.products p on p.id=l.product_id where l.id=(line->>'lot_id')::uuid and l.product_id=(line->>'product_id')::uuid and l.lot_origin<>'VOIDED_PRODUCTION' and p.is_active) then raise exception 'CP7_FG_ADJUST_LINEAGE';end if;
  key:=(line->>'lot_id')||'/'||(line->>'quality_grade');
  if key=any(seen) then raise exception 'CP7_FG_ADJUST_DUPLICATE';end if;seen:=array_append(seen,key);
 end loop;
end $$;

create function cp7_fg.adjust_command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;old cp7_fg.requests;r jsonb;ident uuid;expected bigint;proof jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_fg.adjust_access();
 if a->'can_adjust' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_FG_ADJUST_DENIED';end if;
 if p_action is null or p_action not in('SAVE','DELETE','POST','REVERSE') or p_request is null or jsonb_typeof(p_payload) is distinct from 'object' then raise exception 'CP7_FG_ADJUST_FIELDS';end if;
 if p_expected is not null and p_expected!~'^[1-9][0-9]{0,18}$' then raise exception 'CP7_FG_ADJUST_VERSION';end if;expected:=p_expected::bigint;
 insert into cp7_fg.requests(actor,request_id,action,payload,expected_version) values(auth.uid(),p_request,p_action,p_payload,p_expected) on conflict do nothing;
 select * into old from cp7_fg.requests where actor=auth.uid() and request_id=p_request for update;
 if old.action<>p_action or old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_FG_ADJUST_REQUEST_CHANGED';end if;
 if cp7_fg.adjust_access()<>a then raise exception using errcode='42501',message='CP7_FG_ADJUST_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 if p_action='SAVE' then
  if not p_payload ?& array['adjustment_number','location_id','physical_at','reason_code','reason','change_reason','items']
   or exists(select 1 from jsonb_each(p_payload) e where e.key not in('id','adjustment_number','location_id','physical_at','reason_code','reason','change_reason','items','notes') or (e.key<>'items' and jsonb_typeof(e.value) not in('string','null')))
   or coalesce(p_payload->>'reason_code','') not in('LOSS','DAMAGE','COUNT_CORRECTION') then raise exception 'CP7_FG_ADJUST_FIELDS';end if;
  ident:=(p_payload->>'id')::uuid;
  if ident is not null then
   perform 1 from cp7_fg.adjustment_documents where adjustment_id=ident for update;
   if not found then raise exception 'CP7_FG_ADJUST_SOURCE_WORKFLOW_REQUIRED';end if;
  end if;
  perform cp7_fg.adjust_validate(p_payload);
  r:=erp.save_fg_adjustment_draft_v2(p_payload,p_request,expected);ident:=(r->>'fg_adjustment_id')::uuid;
  perform cp7_fg.adjust_validate(null,ident);
  insert into cp7_fg.adjustment_documents values(ident,cp7_fg.adjust_signature(ident)) on conflict(adjustment_id) do update set source_signature=excluded.source_signature;
 else
  if expected is null or not p_payload ?& array['adjustment_id','change_reason'] or exists(select 1 from jsonb_each(p_payload) e where e.key not in('adjustment_id','change_reason') or jsonb_typeof(e.value)<>'string') then raise exception 'CP7_FG_ADJUST_FIELDS';end if;
  ident:=(p_payload->>'adjustment_id')::uuid;
  select source_signature into proof from cp7_fg.adjustment_documents where adjustment_id=ident for update;
  if not found then raise exception 'CP7_FG_ADJUST_SOURCE_WORKFLOW_REQUIRED';end if;
  if p_action='POST' then
   if cp7_fg.adjust_signature(ident) is distinct from proof then raise exception 'CP7_FG_ADJUST_DRAFT_CHANGED_REVIEW_AGAIN';end if;
   perform cp7_fg.adjust_validate(null,ident);
   r:=erp.post_fg_adjustment_v2(ident,p_request,expected,p_payload->>'change_reason');
   perform cp7_fg.adjust_validate(null,ident);
   if cp7_fg.adjust_signature(ident) is distinct from proof then raise exception 'CP7_FG_ADJUST_DRAFT_CHANGED_REVIEW_AGAIN';end if;
  elsif p_action='DELETE' then
   r:=erp.save_fg_adjustment_draft_v2(jsonb_build_object('id',ident,'action','DELETE','change_reason',p_payload->'change_reason'),p_request,expected);
   delete from cp7_fg.adjustment_documents where adjustment_id=ident;
  else r:=erp.reverse_fg_adjustment_v2(ident,p_payload->>'change_reason',p_request,expected);
  end if;
 end if;
 if cp7_fg.adjust_access()<>a then raise exception using errcode='42501',message='CP7_FG_ADJUST_ACCESS_CHANGED';end if;
 r:=jsonb_build_object('contract_version','cp7.fg-adjustment-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'adjustment_id',ident,'status',r->'status','row_version',r->>'row_version');
 update cp7_fg.requests set response=r where actor=auth.uid() and request_id=p_request;
 return r;
end $$;
create function public.erp_cp7_save_fg_adjustment_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_fg.adjust_command(p_action,p_payload,p_request,p_expected)$$;
