-- Selected complete source cards compose a Nota. Native payroll allocations are
-- the only payable reservation; composing/posting never creates FG or labor cost.
create role cp7_nota_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create role cp7_payroll_header nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
grant usage on schema cp7_payroll,auth,erp to cp7_nota_write,cp7_payroll_header;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_nota_write,cp7_payroll_header;
grant execute on function erp.merge_eligible_work_into_payroll_v2(uuid,jsonb,uuid,bigint) to cp7_nota_write;
-- No financial/status column mutation, item DML, or general ERP writer grant.
grant select on erp.payroll_settlements to cp7_payroll_header;
grant insert(id,payroll_number,contractor_id,period_start,period_end,notes) on erp.payroll_settlements to cp7_payroll_header;
grant update(id) on erp.payroll_settlements to cp7_payroll_header;

create table cp7_payroll.notes(
 id uuid primary key default gen_random_uuid(),note_number text not null unique,
 contractor_id uuid not null,note_date date not null,period_start date not null,period_end date not null,
 notes text not null default '',target_payroll_id uuid,target_version text,
 cards jsonb not null,status text not null check(status in('DRAFT','POSTED','VOID')),
 row_version bigint not null default 1,created_by uuid not null,updated_by uuid not null,
 created_at timestamptz not null default statement_timestamp(),updated_at timestamptz not null default statement_timestamp(),
 posted_payroll_id uuid,posted_at timestamptz,void_reason text,
 check(period_start<=period_end)
);
create table cp7_payroll.card_claims(card_key text primary key,note_id uuid not null references cp7_payroll.notes(id));
create table cp7_payroll.note_requests(actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,expected_version text,response jsonb,primary key(actor,request_id));
alter table cp7_payroll.notes owner to cp7_nota_write;
alter table cp7_payroll.card_claims owner to cp7_nota_write;
alter table cp7_payroll.note_requests owner to cp7_nota_write;
alter table cp7_payroll.notes enable row level security;
alter table cp7_payroll.card_claims enable row level security;
alter table cp7_payroll.note_requests enable row level security;
revoke all on cp7_payroll.notes,cp7_payroll.card_claims,cp7_payroll.note_requests from public,anon,authenticated,service_role,cp7_capture;
grant select on cp7_payroll.notes,cp7_payroll.card_claims to cp7_payroll_read;

create function cp7_payroll.note_access() returns jsonb
language plpgsql stable security definer set search_path='' as $$
begin return cp7_payroll.access_now('NOTA');end $$;

create function cp7_payroll.note_capture(p_cards jsonb,p_contractor uuid,p_end date) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare v jsonb;c jsonb;result jsonb:='[]';seen text[]:='{}';line_count integer:=0;
begin
 perform cp7_payroll.access_now('NOTA');
 if p_contractor is null or p_end is null or jsonb_typeof(p_cards) is distinct from 'array' or jsonb_array_length(p_cards) not between 1 and 50 then raise exception 'CP7_NOTA_CARDS';end if;
 for v in select value from jsonb_array_elements(p_cards) order by value->>'card_key' loop
  if jsonb_typeof(v) is distinct from 'object' or not v ?& array['card_key','source_token']
   or exists(select 1 from jsonb_each(v) e where e.key not in('card_key','source_token') or jsonb_typeof(e.value)<>'string')
   or coalesce(v->>'source_token','')!~'^[a-f0-9]{32}$' or v->>'card_key'=any(seen) then raise exception 'CP7_NOTA_EXACT_CARD';end if;
  seen:=array_append(seen,v->>'card_key');
  select s.card into c from cp7_payroll.source_cards(true) s where s.card_key=v->>'card_key';
  if c is null or c->>'source_token' is distinct from v->>'source_token' then raise exception 'CP7_NOTA_SOURCE_CHANGED';end if;
  if (c->>'contractor_id')::uuid<>p_contractor then raise exception 'CP7_NOTA_DIFFERENT_CONTRACTOR';end if;
  if exists(select 1 from jsonb_array_elements(c->'lines') l where ((l->>'eligible_at')::timestamptz at time zone 'Asia/Jakarta')::date>p_end) then raise exception 'CP7_NOTA_AFTER_PERIOD';end if;
  line_count:=line_count+jsonb_array_length(c->'lines');if line_count>500 then raise exception 'CP7_NOTA_TOO_MANY_COMPONENTS';end if;
  result:=result||jsonb_build_array(c);
 end loop;
 return result;
end $$;

create function cp7_payroll.note_payroll(p_id uuid,p_contractor uuid,p_start date,p_end date) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare p erp.payroll_settlements;
begin
 perform cp7_payroll.access_now('NOTA');
 select * into p from erp.payroll_settlements where id=p_id;
 if p.id is null or p.contractor_id<>p_contractor or p.period_start<>p_start or p.period_end<>p_end or p.status not in('DRAFT','CALCULATED','REVIEW') then raise exception 'CP7_NOTA_PAYROLL_TARGET_CHANGED';end if;
 return jsonb_build_object('id',p.id,'row_version',p.row_version::text);
end $$;

create function cp7_payroll.note_header(p_id uuid,p_contractor uuid,p_start date,p_end date,p_expected text,p_note uuid) returns jsonb
language plpgsql volatile security definer set search_path='' as $$
declare p erp.payroll_settlements;a jsonb;
begin
 a:=cp7_payroll.note_access();if a->'can_post_nota' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_NOTA_WRITE_DENIED';end if;
 if p_id is null then
  -- Native period-overlap trigger serializes new headers for the contractor.
  insert into erp.payroll_settlements(id,payroll_number,contractor_id,period_start,period_end,notes)
  values(gen_random_uuid(),'PAY-'||p_note::text,p_contractor,p_start,p_end,'Dibuat dari Nota FG '||p_note::text) returning * into p;
 else
  -- Match native lock order: payroll header, then contractor, then work sources.
  select * into p from erp.payroll_settlements where id=p_id for update;
  if p.id is null or p.row_version::text is distinct from p_expected or p.contractor_id<>p_contractor or p.period_start<>p_start or p.period_end<>p_end or p.status not in('DRAFT','CALCULATED','REVIEW') then raise exception 'CP7_NOTA_PAYROLL_TARGET_CHANGED';end if;
 end if;
 if cp7_payroll.note_access() is distinct from a then raise exception using errcode='42501',message='CP7_NOTA_ACCESS_CHANGED';end if;
 return jsonb_build_object('id',p.id,'row_version',p.row_version::text);
end $$;

create function cp7_payroll.note_allocation(p_id uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(jsonb_build_object('source_type',i.source_type,'source_id',i.source_id,'component_id',i.work_component_id,'qty',i.qty_payable::text,'rate',i.rate_snapshot::text) order by i.id),'[]')
 from erp.payroll_work_items i where i.payroll_id=p_id
$$;

create function cp7_payroll.note_verify_allocation(p_id uuid,p_before jsonb,p_cards jsonb) returns void
language plpgsql stable security definer set search_path='' as $$
declare c jsonb;l jsonb;old_qty integer;i erp.payroll_work_items;
begin
 for c in select value from jsonb_array_elements(p_cards) loop
  for l in select value from jsonb_array_elements(c->'lines') loop
   select coalesce(sum((x->>'qty')::integer),0)::integer into old_qty from jsonb_array_elements(p_before) x where x->>'source_type'=l->>'source_type' and x->>'source_id'=l->>'source_id' and x->>'component_id'=l->>'component_id';
   select * into i from erp.payroll_work_items where payroll_id=p_id and source_type=l->>'source_type' and source_id=(l->>'source_id')::uuid and work_component_id=(l->>'component_id')::uuid;
   if i.id is null or i.qty_payable<>old_qty+(l->>'remaining_qty')::integer or i.rate_snapshot<>(l->>'rate')::numeric then raise exception 'CP7_NOTA_NATIVE_ALLOCATION_CHANGED';end if;
  end loop;
 end loop;
end $$;

create function cp7_payroll.note_command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;old cp7_payroll.note_requests;n cp7_payroll.notes;ident uuid;cid uuid;start_at date;end_at date;note_at date;snapshot_cards jsonb;target jsonb;prior jsonb;lines jsonb;r jsonb;refs jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_payroll.note_access();if a->'can_post_nota' is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_NOTA_WRITE_DENIED';end if;
 if p_action is null or p_action not in('SAVE','POST','VOID') or p_request is null or jsonb_typeof(p_payload) is distinct from 'object'
  or p_expected is not null and p_expected!~'^[1-9][0-9]{0,18}$' then raise exception 'CP7_NOTA_FIELDS';end if;
 insert into cp7_payroll.note_requests values(auth.uid(),p_request,p_action,p_payload,p_expected,null) on conflict do nothing;
 select * into old from cp7_payroll.note_requests where actor=auth.uid() and request_id=p_request for update;
 if old.action<>p_action or old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_NOTA_REQUEST_CHANGED';end if;
 if cp7_payroll.note_access() is distinct from a then raise exception using errcode='42501',message='CP7_NOTA_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 ident:=(p_payload->>'id')::uuid;
 if ident is not null then
  select * into n from cp7_payroll.notes where id=ident for update;
  if n.id is null or n.row_version::text is distinct from p_expected then raise exception 'CP7_NOTA_STALE_VERSION';end if;
  if n.status<>'DRAFT' then raise exception 'CP7_NOTA_LOCKED';end if;
 elsif p_action<>'SAVE' or p_expected is not null then raise exception 'CP7_NOTA_FIELDS';end if;
 if p_action='SAVE' then
  if not p_payload ?& array['contractor_id','note_date','period_start','period_end','cards']
   or exists(select 1 from jsonb_each(p_payload) e where e.key not in('id','contractor_id','note_date','period_start','period_end','cards','target_payroll_id','notes') or(e.key<>'cards' and jsonb_typeof(e.value) not in('string','null')))
   or exists(select 1 from unnest(array['note_date','period_start','period_end']) k where coalesce(p_payload->>k,'')!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
   or length(coalesce(p_payload->>'notes',''))>2000 then raise exception 'CP7_NOTA_FIELDS';end if;
  cid:=(p_payload->>'contractor_id')::uuid;start_at:=(p_payload->>'period_start')::date;end_at:=(p_payload->>'period_end')::date;note_at:=(p_payload->>'note_date')::date;
  if start_at>end_at or note_at>(statement_timestamp() at time zone 'Asia/Jakarta')::date then raise exception 'CP7_NOTA_DATES';end if;
  snapshot_cards:=cp7_payroll.note_capture(p_payload->'cards',cid,end_at);
  if p_payload->>'target_payroll_id' is not null then target:=cp7_payroll.note_payroll((p_payload->>'target_payroll_id')::uuid,cid,start_at,end_at);end if;
  if ident is null then
   ident:=gen_random_uuid();
   insert into cp7_payroll.notes(id,note_number,contractor_id,note_date,period_start,period_end,notes,target_payroll_id,target_version,cards,status,created_by,updated_by)
   values(ident,'NFG-'||ident::text,cid,note_at,start_at,end_at,coalesce(p_payload->>'notes',''),(target->>'id')::uuid,target->>'row_version',snapshot_cards,'DRAFT',auth.uid(),auth.uid());
  else
   update cp7_payroll.notes set contractor_id=cid,note_date=note_at,period_start=start_at,period_end=end_at,notes=coalesce(p_payload->>'notes',''),target_payroll_id=(target->>'id')::uuid,target_version=target->>'row_version',cards=snapshot_cards,row_version=row_version+1,updated_by=auth.uid(),updated_at=statement_timestamp() where id=ident;
  end if;
  delete from cp7_payroll.card_claims where note_id=ident;
  if exists(select 1 from cp7_payroll.card_claims q join jsonb_array_elements(snapshot_cards) c on c->>'card_key'=q.card_key) then raise exception 'CP7_NOTA_CARD_IN_OTHER_DRAFT';end if;
  insert into cp7_payroll.card_claims select c->>'card_key',ident from jsonb_array_elements(snapshot_cards) c order by c->>'card_key';
 elsif p_action='VOID' then
  if not p_payload ?& array['id','change_reason'] or exists(select 1 from jsonb_each(p_payload) e where e.key not in('id','change_reason') or jsonb_typeof(e.value)<>'string') or length(btrim(p_payload->>'change_reason')) not between 5 and 1000 then raise exception 'CP7_NOTA_REASON';end if;
  update cp7_payroll.notes set status='VOID',void_reason=btrim(p_payload->>'change_reason'),row_version=row_version+1,updated_by=auth.uid(),updated_at=statement_timestamp() where id=ident;
  delete from cp7_payroll.card_claims where note_id=ident;
 else
  if not p_payload ?& array['id','change_reason'] or exists(select 1 from jsonb_each(p_payload) e where e.key not in('id','change_reason') or jsonb_typeof(e.value)<>'string') or length(btrim(p_payload->>'change_reason')) not between 5 and 1000 then raise exception 'CP7_NOTA_REASON';end if;
  target:=cp7_payroll.note_header(n.target_payroll_id,n.contractor_id,n.period_start,n.period_end,n.target_version,n.id);
  select jsonb_agg(jsonb_build_object('card_key',c->'card_key','source_token',c->'source_token') order by c->>'card_key') into refs from jsonb_array_elements(n.cards) c;
  snapshot_cards:=cp7_payroll.note_capture(refs,n.contractor_id,n.period_end);
  if snapshot_cards is distinct from n.cards then raise exception 'CP7_NOTA_SOURCE_CHANGED';end if;
  prior:=cp7_payroll.note_allocation((target->>'id')::uuid);
  select jsonb_agg(jsonb_build_object('source_type',l->'source_type','source_id',l->'source_id','qty',(l->>'remaining_qty')::integer) order by l->>'source_type',l->>'source_id') into lines from jsonb_array_elements(snapshot_cards) c cross join lateral jsonb_array_elements(c->'lines') l;
  perform set_config('app.change_reason',btrim(p_payload->>'change_reason'),true);
  -- The private envelope owns retry identity. Do not forward an untrusted UUID
  -- into another scope's cache; its native request commits atomically with ours.
  r:=erp.merge_eligible_work_into_payroll_v2((target->>'id')::uuid,lines,gen_random_uuid(),(target->>'row_version')::bigint);
  perform cp7_payroll.note_verify_allocation((target->>'id')::uuid,prior,snapshot_cards);
  update cp7_payroll.notes set status='POSTED',posted_payroll_id=(target->>'id')::uuid,posted_at=statement_timestamp(),row_version=row_version+1,updated_by=auth.uid(),updated_at=statement_timestamp() where id=ident;
  delete from cp7_payroll.card_claims where note_id=ident;
 end if;
 if cp7_payroll.note_access() is distinct from a then raise exception using errcode='42501',message='CP7_NOTA_ACCESS_CHANGED';end if;
 select * into n from cp7_payroll.notes where id=ident;
 r:=jsonb_build_object('contract_version','cp7.nota-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'note_id',n.id,'status',n.status,'row_version',n.row_version::text,'payroll_id',n.posted_payroll_id);
 update cp7_payroll.note_requests set response=r where actor=auth.uid() and request_id=p_request;
 return r;
end $$;

create function public.erp_cp7_save_nota_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_payroll.note_command(p_action,p_payload,p_request,p_expected)$$;
