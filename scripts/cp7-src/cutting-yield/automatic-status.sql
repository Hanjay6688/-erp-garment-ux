-- OW16 / D17-15 / D17-16. Descriptive status from current factory facts,
-- independent of the actor-owned prospective learning experiment. Read-only
-- against ERP. The owner supplies coverage/minimum history; no active default.
create schema cp7_cutting_status authorization cp7_capture;
revoke all on schema cp7_cutting_status from public,anon,authenticated,service_role;
grant usage on schema cp7_cutting_status to cp7_policy;

create table cp7_cutting_status.policies(
 id uuid primary key default gen_random_uuid(),revision bigint not null unique check(revision>0),
 state text not null check(state in('ACTIVE','PAUSED')),
 coverage numeric not null check(coverage>0 and coverage<1),
 min_groups integer not null check(min_groups between 1 and 1000000),
 reason text not null check(length(btrim(reason))between 1 and 1000),
 actor uuid not null,request_id uuid not null,recorded_at timestamptz not null,
 unique(actor,request_id)
);
create table cp7_cutting_status.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 recorded_at timestamptz not null,primary key(actor,request_id)
);
alter table cp7_cutting_status.policies owner to cp7_policy;
alter table cp7_cutting_status.requests owner to cp7_policy;
alter table cp7_cutting_status.policies enable row level security;
alter table cp7_cutting_status.requests enable row level security;
create policy cutting_status_policy_private on cp7_cutting_status.policies for all using(false)with check(false);
create policy cutting_status_policy_reader on cp7_cutting_status.policies for select to cp7_capture using(true);
create policy cutting_status_request_private on cp7_cutting_status.requests for all using(false)with check(false);
revoke all on cp7_cutting_status.policies,cp7_cutting_status.requests from public,anon,authenticated,service_role;
grant select on cp7_cutting_status.policies to cp7_capture;

create function cp7_cutting_status.immutable()returns trigger
language plpgsql security invoker set search_path=''as $$
begin raise exception 'CP7_CUTTING_STATUS_HISTORY_IMMUTABLE';end $$;
alter function cp7_cutting_status.immutable()owner to cp7_policy;
create trigger cutting_status_policy_immutable before update or delete on cp7_cutting_status.policies
 for each row execute function cp7_cutting_status.immutable();
create trigger cutting_status_policy_truncate before truncate on cp7_cutting_status.policies
 for each statement execute function cp7_cutting_status.immutable();
create trigger cutting_status_request_immutable before update or delete on cp7_cutting_status.requests
 for each row execute function cp7_cutting_status.immutable();
create trigger cutting_status_request_truncate before truncate on cp7_cutting_status.requests
 for each statement execute function cp7_cutting_status.immutable();

-- This narrow private definer lets the policy principal check the same live
-- identity without granting it ERP reads or access to the planning internals.
create function cp7_cutting_status.access(writing boolean default false)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_cutting_yield.access_now();
 if writing and(coalesce(a->'profile'->>'role_code','')<>'OWNER'
  or erp.has_permission('master.product.manage')is distinct from true)then
  raise exception using errcode='42501',message='CP7_CUTTING_STATUS_OWNER_REQUIRED';end if;
 return a;
end $$;

create function cp7_cutting_status.policy_json(r cp7_cutting_status.policies)returns jsonb
language sql immutable security invoker set search_path=''as $$
 select jsonb_build_object('id',r.id,'revision',r.revision::text,'state',r.state,'coverage',trim_scale(r.coverage)::text,
  'min_groups',r.min_groups::text,'reason',r.reason,'actor',r.actor,'recorded_at',cp7_planning.utc(r.recorded_at))
$$;

-- A single statement supplies group, policy, current output and all prior
-- physical groups. No actor filter, sample truncation, post-cut learning
-- capture or client-provided material/pattern/size identity is involved.
create function cp7_cutting_status.capture(gid uuid,at timestamptz)returns jsonb
language sql stable security invoker set search_path=''as $$
 with current_group as materialized(
  select g.id,g.po_id,g.row_version,g.cut_at,g.created_at,g.material_issue_posted,g.pattern_id,
   g.pattern_revision_snapshot,g.pattern_code_snapshot,g.pattern_name_snapshot,
   po.status::text production_status,po.current_stage::text production_stage,
   (select array_agg(distinct s.size_id order by s.size_id)from erp.cutting_group_size_slots s where s.cutting_group_id=g.id)sizes
  from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id where g.id=gid
 ),policy as materialized(select p from cp7_cutting_status.policies p order by revision desc limit 1),
 current_materials as materialized(
  select roll.material_id,m.material_sku,m.material_name,m.unit_code,sum(r.qty_consumed)consumed,
   sum(y.pcs)pcs,bool_and(coalesce(r.qty_consumed>0 and y.pcs>0,false))complete
  from erp.cutting_group_rolls r join erp.material_rolls roll on roll.id=r.roll_id
   join erp.materials m on m.id=roll.material_id
   left join lateral(select sum(z.qty_pcs)::numeric pcs from erp.cutting_roll_yields z
    join erp.cutting_group_size_slots s on s.id=z.size_slot_id
    where z.cutting_group_roll_id=r.id and s.cutting_group_id=r.cutting_group_id)y on true
  where r.cutting_group_id=gid group by roll.material_id,m.material_sku,m.material_name,m.unit_code
 ),history as materialized(
  select g.id group_id,roll.material_id,sum(y.pcs)/sum(r.qty_consumed)rate
  from current_group c join erp.cutting_groups g on g.id<>c.id and g.material_issue_posted
    and(g.cut_at<c.cut_at or(g.cut_at=c.cut_at and g.created_at<c.created_at))
    and g.cut_at<=at and g.pattern_id=c.pattern_id
    and g.pattern_revision_snapshot=c.pattern_revision_snapshot
   join erp.cutting_group_rolls r on r.cutting_group_id=g.id
   join erp.material_rolls roll on roll.id=r.roll_id
   join current_materials m on m.material_id=roll.material_id
   left join lateral(select sum(z.qty_pcs)::numeric pcs from erp.cutting_roll_yields z
    join erp.cutting_group_size_slots s on s.id=z.size_slot_id
    where z.cutting_group_roll_id=r.id and s.cutting_group_id=g.id)y on true
  where c.sizes is not null and c.sizes=(select array_agg(distinct s.size_id order by s.size_id)
    from erp.cutting_group_size_slots s where s.cutting_group_id=g.id)
  group by g.id,roll.material_id
  having bool_and(coalesce(r.qty_consumed>0 and y.pcs>0,false))and sum(r.qty_consumed)>0
 ),ranked as materialized(
  select h.*,count(*)over(partition by material_id)n,
   row_number()over(partition by material_id order by rate,group_id)rank from history h
 ),bands as(
  select h.material_id,max(h.n)n,
   max(h.rate)filter(where h.rank=greatest(1,ceil((1-(p.p).coverage)/2*h.n)))low,
   max(h.rate)filter(where h.rank=greatest(1,ceil((1+(p.p).coverage)/2*h.n)))high
  from ranked h left join policy p on true group by h.material_id
 ),values_now as(
  select m.*,coalesce(b.n,0)n,ceil(b.low*m.consumed)low,floor(b.high*m.consumed)high,
   case when not c.material_issue_posted then'NOT_FINISHED'
    when not m.complete or c.pattern_id is null or c.pattern_revision_snapshot is null or c.sizes is null then'DATA_INCOMPLETE'
    when(p.p).id is null then'POLICY_REQUIRED'when(p.p).state='PAUSED'then'POLICY_PAUSED'
    when coalesce(b.n,0)<(p.p).min_groups then'INSUFFICIENT_HISTORY'
    when b.low is null or b.high is null or ceil(b.low*m.consumed)>floor(b.high*m.consumed)then'DATA_INCOMPLETE'
    when m.pcs<ceil(b.low*m.consumed)then'LOW'
    when m.pcs>floor(b.high*m.consumed)then'HIGH'else'WITHIN'end status
  from current_materials m cross join current_group c left join bands b on b.material_id=m.material_id
   left join policy p on true
 )select jsonb_build_object('contract_version','cp7.automatic-cutting-status.v1','checked_at',cp7_planning.utc(at),
  'group',(select jsonb_build_object('id',c.id,'version',c.row_version::text,'posted',c.material_issue_posted,
   'physical_at',cp7_planning.utc(c.cut_at),'pattern_id',c.pattern_id,'pattern_revision',c.pattern_revision_snapshot,
   'pattern_label',concat_ws(' · ',c.pattern_code_snapshot,c.pattern_name_snapshot),
   'production_status',c.production_status,'production_stage',c.production_stage)from current_group c),
  'policy',(select cp7_cutting_status.policy_json(p.p)from policy p),
  'materials',coalesce((select jsonb_agg(jsonb_build_object('material_id',v.material_id,'sku',v.material_sku,
   'name',v.material_name,'unit',v.unit_code,'size_ids',coalesce(to_jsonb(c.sizes),'[]'::jsonb),
   'size_labels',(select coalesce(jsonb_agg(s.size_code order by s.sort_order,s.size_code,s.id),'[]')from erp.sizes s where s.id=any(c.sizes)),
   'consumed',trim_scale(v.consumed)::text,'total_pcs',trim_scale(v.pcs)::text,'history_groups',v.n::text,
   'status',v.status,'lower_pcs',case when v.status in('WITHIN','LOW','HIGH')then trim_scale(v.low)::text end,
   'upper_pcs',case when v.status in('WITHIN','LOW','HIGH')then trim_scale(v.high)::text end)
   order by v.material_sku,v.material_id)from values_now v cross join current_group c),'[]'),
  'scope','FACTORY','basis','CURRENT_POSTED_PRIOR_PHYSICAL_GROUPS_MATERIAL_PATTERN_REVISION_EXACT_SIZE_SET',
  'business_write',false)
$$;

create function cp7_cutting_status.workspace(gid uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''as $$
declare a jsonb;outcome jsonb;
begin
 a:=cp7_cutting_status.access();
 if gid is null then raise exception 'CP7_CUTTING_STATUS_GROUP_REQUIRED';end if;
 outcome:=cp7_cutting_status.capture(gid,clock_timestamp());
 if outcome->'group'='null'::jsonb then raise exception 'CP7_CUTTING_STATUS_GROUP_UNAVAILABLE';end if;
 if cp7_cutting_status.access()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_STATUS_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create function cp7_cutting_status.payload(p jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
begin
 perform cp7_wip.fields(p,array['expected_revision','state','coverage','min_groups','reason','explicit_review']);
 if(select count(*)from jsonb_object_keys(p))<>6 or p->'explicit_review'is distinct from'true'::jsonb
  or jsonb_typeof(p->'expected_revision')is distinct from'string'or p->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'
  or(p->>'expected_revision')::numeric>9223372036854775806
  or jsonb_typeof(p->'state')is distinct from'string'or p->>'state'not in('ACTIVE','PAUSED')
  or jsonb_typeof(p->'coverage')is distinct from'string'or p->>'coverage'!~'^0\.[0-9]{1,12}$'
  or(p->>'coverage')::numeric<=0 or(p->>'coverage')::numeric>=1
  or jsonb_typeof(p->'min_groups')is distinct from'string'or p->>'min_groups'!~'^[1-9][0-9]{0,6}$'
  or(p->>'min_groups')::numeric>1000000
  or jsonb_typeof(p->'reason')is distinct from'string'or length(btrim(p->>'reason'))not between 1 and 1000 then
  raise exception 'CP7_CUTTING_STATUS_POLICY_REVIEW';end if;
 return p;
end $$;

create function cp7_cutting_status.command(p_payload jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''as $$
declare a jsonb;p jsonb;r cp7_cutting_status.requests%rowtype;pol cp7_cutting_status.policies%rowtype;
 revision_now bigint;outcome jsonb;
begin
 a:=cp7_cutting_status.access(true);p:=cp7_cutting_status.payload(p_payload);
 if p_request is null or p_lookup is null then raise exception 'CP7_CUTTING_STATUS_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:CUTTING_STATUS_REQUEST:'||auth.uid()::text||':'||p_request::text,0));
 if cp7_cutting_status.access(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_STATUS_ACCESS_CHANGED';end if;
 select *into r from cp7_cutting_status.requests where actor=auth.uid()and request_id=p_request;
 if r.request_id is not null then
  if r.payload<>p then raise exception 'CP7_CUTTING_STATUS_REQUEST_CHANGED';end if;return r.result;
 end if;
 if p_lookup then
  outcome:=jsonb_build_object('contract_version','cp7.automatic-cutting-policy-result.v1',
   'request_id',p_request,'status','NOT_COMMITTED','policy',null);
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:CUTTING_STATUS_FACTORY_POLICY',0));
  if cp7_cutting_status.access(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_STATUS_ACCESS_CHANGED';end if;
  select coalesce(max(revision),0)into revision_now from cp7_cutting_status.policies;
  if revision_now<>(p->>'expected_revision')::bigint then raise exception using errcode='40001',message='CP7_CUTTING_STATUS_POLICY_CHANGED';end if;
  insert into cp7_cutting_status.policies(revision,state,coverage,min_groups,reason,actor,request_id,recorded_at)
   values(revision_now+1,p->>'state',(p->>'coverage')::numeric,(p->>'min_groups')::integer,btrim(p->>'reason'),auth.uid(),p_request,clock_timestamp())returning *into pol;
  outcome:=jsonb_build_object('contract_version','cp7.automatic-cutting-policy-result.v1',
   'request_id',p_request,'status','COMMITTED','policy',cp7_cutting_status.policy_json(pol));
 end if;
 insert into cp7_cutting_status.requests values(auth.uid(),p_request,p,outcome,clock_timestamp());
 return outcome;
end $$;

alter function cp7_cutting_status.access(boolean)owner to cp7_capture;
alter function cp7_cutting_status.policy_json(cp7_cutting_status.policies)owner to cp7_policy;
alter function cp7_cutting_status.capture(uuid,timestamptz)owner to cp7_capture;
alter function cp7_cutting_status.workspace(uuid)owner to cp7_capture;
alter function cp7_cutting_status.payload(jsonb)owner to cp7_policy;
alter function cp7_cutting_status.command(jsonb,uuid,boolean)owner to cp7_policy;
revoke all on all functions in schema cp7_cutting_status from public,anon,authenticated,service_role;
grant execute on function cp7_cutting_status.access(boolean)to cp7_policy;
grant execute on function cp7_cutting_status.policy_json(cp7_cutting_status.policies)to cp7_capture;
-- Pure payload/UTC helpers are delegated only to the existing configuration
-- principal, not to browser roles. No ERP business writer is granted here.
grant usage on schema cp7_wip,cp7_planning to cp7_policy;
grant execute on function cp7_wip.fields(jsonb,text[]),cp7_planning.utc(timestamptz)to cp7_policy;
grant select(id,material_name)on erp.materials to cp7_capture;
grant select(id,sort_order)on erp.sizes to cp7_capture;

create function public.erp_cp7_get_cutting_status_v1(p_group uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_status.workspace(p_group)$$;
create function public.erp_cp7_save_cutting_status_policy_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_status.command(p_payload,p_request,false)$$;
create function public.erp_cp7_get_cutting_status_policy_request_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_status.command(p_payload,p_request,true)$$;
alter function public.erp_cp7_get_cutting_status_v1(uuid)owner to cp7_capture;
alter function public.erp_cp7_save_cutting_status_policy_v1(jsonb,uuid)owner to cp7_policy;
alter function public.erp_cp7_get_cutting_status_policy_request_v1(jsonb,uuid)owner to cp7_policy;
revoke all on function public.erp_cp7_get_cutting_status_v1(uuid),public.erp_cp7_save_cutting_status_policy_v1(jsonb,uuid),
 public.erp_cp7_get_cutting_status_policy_request_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_cutting_status_v1(uuid),public.erp_cp7_save_cutting_status_policy_v1(jsonb,uuid),
 public.erp_cp7_get_cutting_status_policy_request_v1(jsonb,uuid)to authenticated;
