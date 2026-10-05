-- Reopen an unpicked posted cutting group through its unchanged Native inverse.
-- No business table DML or new internal/Native guard admission is introduced.
create role cp7_cutting_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create role cp7_cutting_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_cutting_correction authorization cp7_cutting_read;
revoke all on schema cp7_cutting_correction from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_cutting_correction to postgres,cp7_cutting_write;
create table cp7_cutting_correction.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,expected_version text not null,
 response jsonb,primary key(actor,request_id)
);
create table cp7_cutting_correction.history(
 actor uuid not null,request_id uuid not null,group_id uuid not null references erp.cutting_groups,
 original_source jsonb not null,Native_response jsonb not null,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
alter table cp7_cutting_correction.requests owner to postgres;
alter table cp7_cutting_correction.history owner to postgres;
alter table cp7_cutting_correction.requests enable row level security;
alter table cp7_cutting_correction.history enable row level security;
create policy private_requests on cp7_cutting_correction.requests for all using(false)with check(false);
create policy private_history on cp7_cutting_correction.history for all using(false)with check(false);
revoke all on all tables in schema cp7_cutting_correction from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;

create function cp7_cutting_correction.access_now()returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;permission text;
begin
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')then
  raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_DENIED';end if;
 foreach permission in array array['production.distribution.view','production.cutting.view','production.cutting.edit_draft','production.cutting.post']loop
  if erp.has_permission(permission)is distinct from true then
   raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_DENIED';end if;
 end loop;
 return a;
end $$;

create function cp7_cutting_correction.immutable()returns trigger
language plpgsql security invoker set search_path=''as $$
begin raise exception 'CP7_CUTTING_CORRECTION_HISTORY_IMMUTABLE';end $$;
create trigger immutable_history before update or delete on cp7_cutting_correction.history
 for each row execute function cp7_cutting_correction.immutable();
create trigger immutable_history_truncate before truncate on cp7_cutting_correction.history
 for each statement execute function cp7_cutting_correction.immutable();

create function cp7_cutting_correction.snapshot(p_group uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('group',to_jsonb(g),'po',to_jsonb(po),
  'rolls',(select jsonb_agg(to_jsonb(r)order by r.id)from erp.cutting_group_rolls r where r.cutting_group_id=g.id),
  'slots',(select jsonb_agg(to_jsonb(s)order by s.id)from erp.cutting_group_size_slots s where s.cutting_group_id=g.id),
  'yields',(select jsonb_agg(to_jsonb(y)order by y.id)from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id where r.cutting_group_id=g.id),
  'pickups',(select coalesce(jsonb_agg(to_jsonb(p)order by p.id),'[]'::jsonb)from erp.cutting_pickups p where p.cutting_group_id=g.id),
  'materials',(select jsonb_agg(to_jsonb(m)order by m.id)from erp.material_rolls m where exists(select 1 from erp.cutting_group_rolls r where r.cutting_group_id=g.id and r.roll_id=m.id)),
  'movements',(select jsonb_agg(to_jsonb(m)order by m.id)from erp.material_stock_movements m where exists(select 1 from erp.cutting_group_rolls r where r.cutting_group_id=g.id and r.roll_id=m.roll_id)),
  'journals',(select jsonb_agg(to_jsonb(j)order by j.id)from erp.journal_entries j where j.source_id=g.id or exists(select 1 from erp.cutting_group_rolls r where r.cutting_group_id=g.id and r.id=j.source_id)),
  'period',(select jsonb_agg(to_jsonb(p))from erp.accounting_period_control p),
  'downstream',erp.cutting_group_has_downstream_after_pickup(g.id))
 from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id where g.id=p_group
$$;

create function cp7_cutting_correction.workspace(p_group uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;s jsonb;g jsonb;blockers jsonb:='[]';
begin
 a:=cp7_cutting_correction.access_now();s:=cp7_cutting_correction.snapshot(p_group);g:=s->'group';
 if s is null then raise exception 'CP7_CUTTING_CORRECTION_NOT_FOUND';end if;
 if g->>'status'is distinct from'CUT'or g->'picked_up_at'is distinct from'null'::jsonb then
  blockers:=blockers||jsonb_build_array(jsonb_build_object('kind','PICKUP_OR_LIFECYCLE','id',p_group,'label',g->>'group_number'));end if;
 if s->'downstream'is distinct from'false'::jsonb then
  blockers:=blockers||jsonb_build_array(jsonb_build_object('kind','DOWNSTREAM','id',p_group,'label',g->>'group_number'));end if;
 if exists(select 1 from jsonb_array_elements(coalesce(s->'pickups','[]'))p where p->>'status'in('DRAFT','POSTED'))then
  blockers:=blockers||(select jsonb_agg(jsonb_build_object('kind','PICKUP','id',p->>'id','label',g->>'group_number','status',p->>'status')order by p->>'id')
   from jsonb_array_elements(s->'pickups')p where p->>'status'in('DRAFT','POSTED'));end if;
 if g->'material_issue_posted'is distinct from'true'::jsonb or g->'material_return_posted'is distinct from'false'::jsonb then
  blockers:=blockers||jsonb_build_array(jsonb_build_object('kind','MATERIAL_FLOW','id',p_group,'label',g->>'group_number'));end if;
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.cutting-reopen-workspace.v1','group_id',p_group,'po_id',g->>'po_id',
  'number',g->>'group_number','row_version',g->>'row_version','review_token',md5(s::text),
  'eligible',jsonb_array_length(blockers)=0,'blockers',blockers,'business_DML',false);
end $$;

create function cp7_cutting_correction.command(p jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;old cp7_cutting_correction.requests;g erp.cutting_groups;s jsonb;w jsonb;r jsonb;answer jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_cutting_correction.access_now();
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'
  or jsonb_typeof(p)is distinct from'object'or not(p?&array['group_id','po_id','review_token','change_reason'])
  or(select count(*)from jsonb_object_keys(p))<>4
  or jsonb_typeof(p->'group_id')is distinct from'string'or coalesce(p->>'group_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'po_id')is distinct from'string'or coalesce(p->>'po_id','')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'review_token')is distinct from'string'or coalesce(p->>'review_token','')!~'^[a-f0-9]{32}$'
  or jsonb_typeof(p->'change_reason')is distinct from'string'or length(btrim(p->>'change_reason'))not between 5 and 1000 then
  raise exception 'CP7_CUTTING_CORRECTION_FIELDS';end if;
 insert into cp7_cutting_correction.requests values(auth.uid(),p_request,p,p_expected,null)on conflict do nothing;
 select *into strict old from cp7_cutting_correction.requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p or old.expected_version is distinct from p_expected then raise exception 'CP7_CUTTING_CORRECTION_REQUEST_CHANGED';end if;
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||(p->>'group_id'),0));
 select *into g from erp.cutting_groups where id=(p->>'group_id')::uuid for update;
 if g.id is null then raise exception 'CP7_CUTTING_CORRECTION_NOT_FOUND';end if;
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 s:=cp7_cutting_correction.snapshot(g.id);w:=cp7_cutting_correction.workspace(g.id);
 if g.row_version::text is distinct from p_expected or g.po_id::text is distinct from p->>'po_id'
  or md5(s::text)is distinct from p->>'review_token'then raise exception 'CP7_CUTTING_CORRECTION_STALE_REVIEW';end if;
 if w->'eligible'is distinct from'true'::jsonb then raise exception 'CP7_CUTTING_CORRECTION_DEPENDENCIES';end if;
 -- This is the accepted Native transaction. Its stock, GL, period, downstream,
 -- negative-stock, actor and immutable reversal-link guards execute unchanged.
 r:=erp.reverse_cutting_material_flow_before_sewing_v2(g.id,btrim(p->>'change_reason'),p_request,g.row_version);
 -- A revocation during any Native stock/journal lock wait rolls every effect
 -- and both request receipts back, including the immutable Native inverses.
 if cp7_cutting_correction.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_CORRECTION_ACCESS_CHANGED';end if;
 if r->>'cutting_group_id'is distinct from g.id::text or r->>'status'is distinct from'CUT'
  or r->'presewing_reversible'is distinct from'true'::jsonb or exists(
   select 1 from erp.cutting_groups x where x.id=g.id and(x.material_issue_posted or x.material_return_posted or x.picked_up_at is not null))then
  raise exception 'CP7_CUTTING_CORRECTION_INCOMPLETE';end if;
 insert into cp7_cutting_correction.history values(auth.uid(),p_request,g.id,s,r,btrim(p->>'change_reason'),clock_timestamp());
 answer:=jsonb_build_object('contract_version','cp7.cutting-reopen-outcome.v1','kind','COMMITTED_OUTCOME','action','REOPEN_POSTED',
  'request_id',p_request,'group_id',g.id,'po_id',g.po_id,'number',g.group_number,'row_version',r->>'row_version',
  'status','DRAFT_FOR_CORRECTION','Native_response',r);
 update cp7_cutting_correction.requests set response=answer where actor=auth.uid()and request_id=p_request;
 return answer;
end $$;

create function public.erp_cp7_get_cutting_correction_v1(p_group uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.workspace(p_group)$$;
create function public.erp_cp7_reopen_cutting_v1(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.command(p_payload,p_request,p_expected)$$;
alter function cp7_cutting_correction.access_now()owner to postgres;
alter function cp7_cutting_correction.immutable()owner to postgres;
alter function cp7_cutting_correction.snapshot(uuid)owner to postgres;
alter function cp7_cutting_correction.workspace(uuid)owner to postgres;
alter function cp7_cutting_correction.command(jsonb,uuid,text)owner to postgres;
grant create on schema public to cp7_cutting_read,cp7_cutting_write;
alter function public.erp_cp7_get_cutting_correction_v1(uuid)owner to cp7_cutting_read;
alter function public.erp_cp7_reopen_cutting_v1(jsonb,uuid,text)owner to cp7_cutting_write;
revoke create on schema public from cp7_cutting_read,cp7_cutting_write;
revoke all on all functions in schema cp7_cutting_correction from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
grant execute on function cp7_cutting_correction.workspace(uuid)to cp7_cutting_read;
grant execute on function cp7_cutting_correction.command(jsonb,uuid,text)to cp7_cutting_write;
revoke all on function public.erp_cp7_get_cutting_correction_v1(uuid),public.erp_cp7_reopen_cutting_v1(jsonb,uuid,text)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_cutting_correction_v1(uuid),public.erp_cp7_reopen_cutting_v1(jsonb,uuid,text)to authenticated;
