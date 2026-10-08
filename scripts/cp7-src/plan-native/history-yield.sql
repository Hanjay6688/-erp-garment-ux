-- PL-5 B (owner decision 8 Oct 2026, docs/cp7/PL5_YIELD_POLICY_PROPOSAL_20261007.md):
-- the good-piece yield of a new start comes from the factory's own finished
-- production. Only cutting groups with a stored PL-8 exhaustion proof that
-- still matches their current facts count: a correction, reversal or backdated
-- row changes the facts, so the group drops out until it is proven again.
-- Window and minimum sample are a versioned policy that an owner or admin
-- saves with a reason; the one-sided 90% Wilson lower bound, the floor to 0.1%
-- and the levels (product+size, then the same model, never another model) are
-- the decision itself and fixed. Without a saved policy history_yield keeps
-- its earlier pending answer unchanged; a paused policy gives no value. When
-- history has no value the plan uses the reviewed estimate A or stays UNKNOWN.
create schema cp7_yield_policy authorization cp7_policy;
revoke all on schema cp7_yield_policy from public,anon,authenticated,service_role;
grant usage on schema cp7_yield_policy to cp7_capture;
create table cp7_yield_policy.policies(
 id uuid primary key default gen_random_uuid(),revision bigint not null unique check(revision>0),
 state text not null check(state in('ACTIVE','PAUSED')),
 window_days integer not null check(window_days between 1 and 3660),
 min_groups integer not null check(min_groups between 1 and 1000),
 min_cut_pcs integer not null check(min_cut_pcs between 1 and 1000000),
 confidence text not null check(confidence='0.90'),z text not null check(z='1.2815515655446004'),
 method text not null check(method='WILSON_SCORE_ONE_SIDED_LOWER_BOUND'),rounding text not null check(rounding='FLOOR_PERMILLE'),
 levels text[] not null check(levels=array['PRODUCT_SIZE','MODEL']),
 reason text not null check(length(reason)between 1 and 1000),actor uuid not null,
 actor_role text not null check(actor_role in('OWNER','ADMIN')),request_id uuid not null,
 recorded_at timestamptz not null default clock_timestamp(),unique(actor,request_id)
);
create table cp7_yield_policy.commands(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
alter table cp7_yield_policy.policies owner to cp7_policy;
alter table cp7_yield_policy.commands owner to cp7_policy;
alter table cp7_yield_policy.policies enable row level security;
alter table cp7_yield_policy.commands enable row level security;
create policy cp7_yield_policy_no_access on cp7_yield_policy.policies for all to public using(false)with check(false);
create policy cp7_yield_policy_command_no_access on cp7_yield_policy.commands for all to public using(false)with check(false);
revoke all on cp7_yield_policy.policies,cp7_yield_policy.commands from public,anon,authenticated,service_role;
grant select on cp7_yield_policy.policies to cp7_capture;
create trigger immutable_yield_policy before update or delete on cp7_yield_policy.policies
 for each row execute function cp7_identity.immutable_row();
create trigger immutable_yield_policy_command before update or delete on cp7_yield_policy.commands
 for each row execute function cp7_identity.immutable_row();

-- Reading needs the planning view rights; saving also master.product.manage
-- and the OWNER or ADMIN role, recorded on the row as its signature.
create function cp7_yield_policy.access(p_writing boolean)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;
begin
 a:=cp7_identity.access_now(p_writing);
 if p_writing and coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')then
  raise exception using errcode='42501',message='CP7_YIELD_POLICY_OWNER_ADMIN_REQUIRED';end if;
 return a;
end $$;

create function cp7_yield_policy.row_json(r cp7_yield_policy.policies)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('id',r.id,'revision',r.revision::text,'state',r.state,'window_days',r.window_days::text,
  'min_groups',r.min_groups::text,'min_cut_pcs',r.min_cut_pcs::text,'confidence',r.confidence,'method',r.method,
  'rounding',r.rounding,'levels',to_jsonb(r.levels),'reason',r.reason,'actor',r.actor,'actor_role',r.actor_role,'recorded_at',r.recorded_at)
$$;

-- The package the owner approved on 8 Oct 2026, returned for the form to show
-- beside the saved revisions; it is not in force until a revision is saved.
create function cp7_yield_policy.workspace()returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;cur cp7_yield_policy.policies%rowtype;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_yield_policy.access(false);
 select *into cur from cp7_yield_policy.policies order by revision desc limit 1;
 outcome:=jsonb_build_object('contract_version','cp7.history-yield-policy.v1',
  'state',case when cur.id is null then 'PENDING_POLICY_VALUE'else cur.state end,
  'current',case when cur.id is null then null else cp7_yield_policy.row_json(cur)end,
  'revisions',coalesce((select jsonb_agg(cp7_yield_policy.row_json(x)order by x.revision desc)
   from(select *from cp7_yield_policy.policies order by revision desc limit 50)x),'[]'::jsonb),
  'decided_package',jsonb_build_object('decision','OWNER_DECISION_2026_10_08','window_days','180','min_groups','5','min_cut_pcs','200',
   'confidence','0.90','method','WILSON_SCORE_ONE_SIDED_LOWER_BOUND','rounding','FLOOR_PERMILLE','levels',jsonb_build_array('PRODUCT_SIZE','MODEL')),
  'manage_allowed',erp.has_permission('master.product.manage')and coalesce(a->'profile'->>'role_code','')in('OWNER','ADMIN'));
 if cp7_yield_policy.access(false)is distinct from a then raise exception using errcode='42501',message='CP7_YIELD_POLICY_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create function cp7_yield_policy.apply(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_yield_policy.commands%rowtype;r cp7_yield_policy.policies%rowtype;expected bigint;current_revision bigint;
 reason text;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_yield_policy.access(true);
 if p_request is null then raise exception 'CP7_YIELD_POLICY_REQUEST_REQUIRED';end if;
 perform cp7_wip.fields(p,array['expected_revision','state','window_days','min_groups','min_cut_pcs','confidence','reason']);
 perform pg_advisory_xact_lock(hashtextextended('CP7:YIELD_POLICY:REQUEST:'||auth.uid()::text||':'||p_request::text,0));
 if cp7_yield_policy.access(true)is distinct from a then raise exception using errcode='42501',message='CP7_YIELD_POLICY_ACCESS_CHANGED';end if;
 select *into old from cp7_yield_policy.commands where actor=auth.uid()and request_id=p_request;
 if found then
  if old.payload<>p then raise exception 'CP7_YIELD_POLICY_REQUEST_CHANGED';end if;
  return old.result;
 end if;
 reason:=btrim(p->>'reason');
 if jsonb_typeof(p->'expected_revision')is distinct from'string'or p->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'
  or jsonb_typeof(p->'state')is distinct from'string'or p->>'state'not in('ACTIVE','PAUSED')
  or jsonb_typeof(p->'reason')is distinct from'string'or length(reason)not between 1 and 1000 then raise exception 'CP7_YIELD_POLICY_REVIEW';end if;
 if jsonb_typeof(p->'window_days')is distinct from'string'or p->>'window_days'!~'^[1-9][0-9]{0,3}$'or(p->>'window_days')::integer>3660
  or jsonb_typeof(p->'min_groups')is distinct from'string'or p->>'min_groups'!~'^[1-9][0-9]{0,3}$'or(p->>'min_groups')::integer>1000
  or jsonb_typeof(p->'min_cut_pcs')is distinct from'string'or p->>'min_cut_pcs'!~'^[1-9][0-9]{0,6}$'or(p->>'min_cut_pcs')::integer>1000000
  then raise exception 'CP7_YIELD_POLICY_VALUES';end if;
 -- The confidence is the owner's decision, not a setting.
 if p->'confidence'is distinct from'"0.90"'::jsonb then raise exception 'CP7_YIELD_POLICY_CONFIDENCE_FIXED';end if;
 expected:=(p->>'expected_revision')::bigint;
 perform pg_advisory_xact_lock(hashtextextended('CP7:YIELD_POLICY',0));
 select coalesce(max(revision),0)into current_revision from cp7_yield_policy.policies;
 if expected<>current_revision then raise exception using errcode='40001',message='CP7_YIELD_POLICY_REVISION_CHANGED';end if;
 insert into cp7_yield_policy.policies(revision,state,window_days,min_groups,min_cut_pcs,confidence,z,method,rounding,levels,reason,actor,actor_role,request_id)
 values(current_revision+1,p->>'state',(p->>'window_days')::integer,(p->>'min_groups')::integer,(p->>'min_cut_pcs')::integer,'0.90',
  '1.2815515655446004','WILSON_SCORE_ONE_SIDED_LOWER_BOUND','FLOOR_PERMILLE',array['PRODUCT_SIZE','MODEL'],reason,auth.uid(),a->'profile'->>'role_code',p_request)
 returning *into r;
 if cp7_yield_policy.access(true)is distinct from a then raise exception using errcode='42501',message='CP7_YIELD_POLICY_ACCESS_CHANGED';end if;
 outcome:=jsonb_build_object('contract_version','cp7.history-yield-policy-outcome.v1','request_id',p_request,'policy',cp7_yield_policy.row_json(r));
 insert into cp7_yield_policy.commands(actor,request_id,payload,result)values(auth.uid(),p_request,p,outcome);
 return outcome;
end $$;

alter function cp7_yield_policy.access(boolean)owner to cp7_policy;
alter function cp7_yield_policy.row_json(cp7_yield_policy.policies)owner to cp7_policy;
alter function cp7_yield_policy.workspace()owner to cp7_capture;
alter function cp7_yield_policy.apply(jsonb,uuid)owner to cp7_policy;
revoke all on all functions in schema cp7_yield_policy from public,anon,authenticated,service_role;
grant execute on function cp7_yield_policy.access(boolean),cp7_yield_policy.row_json(cp7_yield_policy.policies)to cp7_capture;
grant create on schema public to cp7_capture,cp7_policy;
create function public.erp_cp7_get_history_yield_policy_v1()returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_yield_policy.workspace()$$;
create function public.erp_cp7_save_history_yield_policy_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_yield_policy.apply(p_payload,p_request)$$;
alter function public.erp_cp7_get_history_yield_policy_v1()owner to cp7_capture;
alter function public.erp_cp7_save_history_yield_policy_v1(jsonb,uuid)owner to cp7_policy;
revoke create on schema public from cp7_capture,cp7_policy;
revoke all on function public.erp_cp7_get_history_yield_policy_v1(),public.erp_cp7_save_history_yield_policy_v1(jsonb,uuid)
 from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_history_yield_policy_v1(),public.erp_cp7_save_history_yield_policy_v1(jsonb,uuid)to authenticated;

-- floor(1000·L) for the one-sided 90% Wilson lower bound of x good out of n cut:
-- L=(2x+z²−z·sqrt(z²+4x(n−x)/n))/(2(n+z²)), z=1.2815515655446004. The square
-- root only gives a first guess; k is then fixed by exact numeric arithmetic:
-- 1000L≥k ⇔ A≥0 and A²·n≥10⁶·z²·(z²·n+4x(n−x)), A=1000(2x+z²)−2k(n+z²).
-- The bound is below n/(n+z²)<1, so all good never gives 100%.
create function cp7_plan_native.wilson_permille(p_x bigint,p_n bigint)returns integer
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare z numeric:=1.2815515655446004;zz numeric;rhs numeric;k integer;lhs numeric;
begin
 if p_x is null or p_n is null or p_n<1 or p_x<0 or p_x>p_n then raise exception 'CP7_HISTORY_YIELD_WILSON_INPUT';end if;
 zz:=z*z;rhs:=1000000*zz*(zz*p_n+4*p_x*(p_n-p_x));
 k:=greatest(0,floor(1000*(2*p_x+zz-z*sqrt(zz+4*p_x*(p_n-p_x)/p_n::numeric))/(2*(p_n+zz))))::integer;
 loop
  lhs:=1000*(2*p_x+zz)-2*k*(p_n+zz);
  exit when k=0 or(lhs>=0 and lhs*lhs*p_n>=rhs);
  k:=k-1;
 end loop;
 loop
  lhs:=1000*(2*p_x+zz)-2*(k+1)*(p_n+zz);
  exit when not(lhs>=0 and lhs*lhs*p_n>=rhs);
  k:=k+1;
 end loop;
 return k;
end $$;

-- One batch of candidate groups (≤50, one clock): the groups whose current
-- facts match a stored proof under the current kernel, each with its matched
-- proof, its cut pools and when it finished (its last physical event). The
-- rest are listed as stale or unverifiable. Counting only, nothing is stored.
create function cp7_plan_native.history_groups(p_ids uuid[],p_at timestamptz,p_kernel text)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare part jsonb;reuse jsonb;hits uuid[];sub jsonb;norm jsonb;grp_rows jsonb;
begin
 part:=cp7_wip.capture_cutting_sources(p_ids,p_at);
 if part->>'status'is distinct from 'COMPLETE'then return jsonb_build_object('status','UNKNOWN','reason','HISTORY_SOURCE_INCOMPLETE');end if;
 begin reuse:=cp7_supply_native.batch_reuse(part,p_kernel);
 exception when others then reuse:=null;
 end;
 hits:=array(select x::uuid from jsonb_array_elements_text(coalesce(reuse->'hit','[]'::jsonb))x order by x::uuid);
 if cardinality(hits)>0 then
  sub:=cp7_wip.capture_cutting_sources(hits,p_at);
  if sub->>'status'is distinct from 'COMPLETE'then return jsonb_build_object('status','UNKNOWN','reason','HISTORY_SOURCE_INCOMPLETE');end if;
  begin norm:=cp7_wip.normalize_cutting(sub);
  exception when others then norm:=jsonb_build_object('status','UNKNOWN','reason','HISTORY_NORMALIZATION_REFUSED');
  end;
  if norm->>'status'is distinct from 'COMPLETE'then return jsonb_build_object('status','UNKNOWN','reason',coalesce(norm->>'reason','HISTORY_NORMALIZATION_REFUSED'));end if;
  with f as materialized(select sub->'facts'f),
  bsg as materialized(select x->>'id'id,x->>'group_id'g from f,jsonb_array_elements(f->'bs')x),
  dlg as materialized(select distinct x->>'delivery_id'd,x->>'group_id'g from f,jsonb_array_elements(f->'deliveries')x),
  events as(
   select x->>'id'g,(x->>'cut_at')::timestamptz ts from f,jsonb_array_elements(f->'groups')x
   union all select x->>'group_id',(x->>'physical_at')::timestamptz from f,jsonb_array_elements(f->'qc')x where x->>'status'='POSTED'
   union all select x->>'group_id',(x->>'physical_at')::timestamptz from f,jsonb_array_elements(f->'bs')x
   union all select x->>'group_id',(x->>'physical_at')::timestamptz from f,jsonb_array_elements(f->'receipts')x
   union all select x->>'group_id',(x->>'physical_at')::timestamptz from f,jsonb_array_elements(f->'sewing')x
   union all select b.g,(x->>'completed_at')::timestamptz from f,jsonb_array_elements(f->'reworks')x join bsg b on b.id=x->>'bs_case_id'
   union all select b.g,(x->>'physical_at')::timestamptz from f,jsonb_array_elements(f->'resolutions')x join bsg b on b.id=x->>'bs_case_id'
   union all select b.g,(x->>'physical_at')::timestamptz from f,jsonb_array_elements(f->'holds')x join bsg b on b.id=x->>'bs_case_id'
   union all select b.g,(x->>'physical_at')::timestamptz from f,jsonb_array_elements(f->'bs_fg')x join bsg b on b.id=x->>'bs_case_id'
   union all select d.g,(x->>'resolved_at')::timestamptz from f,jsonb_array_elements(f->'claims')x join dlg d on d.d=x->>'delivery_id'
  ),finished as(select g,max(ts)ts from events where ts is not null and ts<=p_at group by g),
  qc as(select x->>'group_id'g,x->>'size_id'size_id,x->>'product_root'root,p.model_id
   from f,jsonb_array_elements(f->'qc')x join erp.products p on p.id=(x->>'final_product_id')::uuid where x->>'status'='POSTED'),
  pools as(select split_part(t->>'pool_key',':',2)g,t from jsonb_array_elements(norm->'totals')t where t->>'pool_key'like 'CUT:%'),
  grouped as(
   select h.id,
    (select jsonb_build_object('proof_id',x.id,'facts_hash',x.facts_hash,'captured_at',x.captured_at)
     from cp7_supply_native.exhaustion_proofs x where x.group_id=h.id and x.kernel_version=p_kernel and x.facts_hash=reuse->'hashes'->>h.id::text
     order by x.captured_at,x.id limit 1)proof,
    (select ts from finished where g=h.id::text)finished_at,
    (select x->>'model_id'from f,jsonb_array_elements(f->'groups')x where x->>'id'=h.id::text)model_id,
    coalesce((select jsonb_agg(jsonb_build_object('size_id',p.t->'size_id','input_pcs',p.t->'input_pcs','fg_pcs',p.t->'fg_pcs',
      'exited_pcs',p.t->'exited_pcs','spent',(p.t->>'wip_pcs')::numeric=0 and(p.t->>'bs_pcs')::numeric=0 and(p.t->>'withheld_pcs')::numeric=0
       and(p.t->>'input_pcs')::numeric=(p.t->>'fg_pcs')::numeric+(p.t->>'exited_pcs')::numeric,
      'qc_roots',coalesce((select jsonb_agg(distinct q.root)from qc q where q.g=h.id::text and q.size_id=p.t->>'size_id'),'[]'::jsonb))
     order by p.t->>'pool_key')from pools p where p.g=h.id::text),'[]'::jsonb)pools,
    coalesce((select jsonb_agg(distinct q.model_id)from qc q where q.g=h.id::text),'[]'::jsonb)qc_models
   from unnest(hits)h(id)
  )select coalesce(jsonb_agg(jsonb_build_object('group_id',id,'proof',proof,'finished_at',finished_at,'model_id',model_id,
    'pools',pools,'qc_models',qc_models)order by id),'[]'::jsonb)into grp_rows from grouped;
 end if;
 return jsonb_build_object('status','COMPLETE','groups',coalesce(grp_rows,'[]'::jsonb),
  'unverified',(select coalesce(jsonb_agg(x order by x),'[]'::jsonb)from unnest(p_ids)x where not x=any(hits)));
end $$;

-- The history yield of one target (root:size) of model p_model now, under the
-- latest saved policy. Candidates are posted groups of that model only, with
-- a proof under the current kernel captured inside the window (an earlier
-- proof proves an earlier finish). Product+size first: pools of the target's
-- size whose posted QC all went to the target's root; then every pool of the
-- model's groups. More than 200 candidates at a level leaves that level
-- unknown, as the WIP read does. Sufficient means at least min_groups groups
-- and min_cut_pcs cut pieces at the level.
create function cp7_plan_native.history_source(p_target text,p_model uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;pol cp7_yield_policy.policies%rowtype;clk timestamptz:=clock_timestamp();root uuid;size uuid;kernel text;first_day date;
 w_start timestamptz;ps_ids uuid[];ps_n integer;m_ids uuid[];m_n integer;todo uuid[];done uuid[]:='{}';res jsonb:='[]';part jsonb;
 unverified integer:=0;bi integer;lv jsonb:='[]';used jsonb;chosen jsonb;level text;st text;rs text;k integer;ng integer;cut numeric;fg numeric;
 lvl text;stale_or_unverifiable integer;outside integer;unattributed integer;not_spent integer;
begin
 a:=cp7_private.access_now();
 if p_target!~'^[0-9a-f-]{36}:[0-9a-f-]{36}$'then raise exception 'CP7_PLAN_TARGET';end if;
 select *into pol from cp7_yield_policy.policies order by revision desc limit 1;
 if pol.id is null then
  return jsonb_build_object('status','PENDING_POLICY_VALUE','reason','OWNER_HISTORY_YIELD_POLICY_NOT_APPROVED',
   'window_days',null,'minimum_sample',null,'lower_bound',null,'numerator',null,'denominator',null,'target_key',p_target);
 end if;
 root:=split_part(p_target,':',1)::uuid;size:=split_part(p_target,':',2)::uuid;
 first_day:=(clk at time zone 'Asia/Jakarta')::date-pol.window_days+1;w_start:=first_day::timestamp at time zone 'Asia/Jakarta';
 if pol.state='PAUSED'then st:='POLICY_PAUSED';rs:='HISTORY_YIELD_POLICY_PAUSED';
 elsif p_model is null or(select count(*)from erp.products p where coalesce(p.identity_root_id,p.id)=root and p.size_id=size
   and p.effective_from<=clk and(p.effective_to is null or p.effective_to>clk))<>1
  or not exists(select 1 from erp.products p where coalesce(p.identity_root_id,p.id)=root and p.size_id=size and p.model_id=p_model
   and p.effective_from<=clk and(p.effective_to is null or p.effective_to>clk))then st:='UNKNOWN';rs:='TARGET_MODEL_CHANGED';
 else
  begin kernel:=cp7_supply_native.proof_kernel();
  exception when others then kernel:=null;
  end;
  if kernel is null then st:='UNKNOWN';rs:='PROOF_KERNEL_UNAVAILABLE';end if;
 end if;
 if st is null then
  -- Product+size candidates: the model's groups with posted QC of this root and size.
  select coalesce(array_agg(x.id order by x.id),'{}'::uuid[]),count(*)into ps_ids,ps_n from(
   select g.id from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id
   where po.model_id=p_model and g.material_issue_posted and g.cut_at<=clk
    and exists(select 1 from cp7_supply_native.exhaustion_proofs x where x.group_id=g.id and x.kernel_version=kernel and x.captured_at>=w_start)
    and exists(select 1 from erp.qc_inspection_items i join erp.qc_inspections q on q.id=i.inspection_id join erp.products p on p.id=i.final_product_id
     where i.cutting_group_id=g.id and q.status='POSTED'and coalesce(p.identity_root_id,p.id)=root and p.size_id=size)
   order by g.id limit 201)x;
  select coalesce(array_agg(x.id order by x.id),'{}'::uuid[]),count(*)into m_ids,m_n from(
   select g.id from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id
   where po.model_id=p_model and g.material_issue_posted and g.cut_at<=clk
    and exists(select 1 from cp7_supply_native.exhaustion_proofs x where x.group_id=g.id and x.kernel_version=kernel and x.captured_at>=w_start)
   order by g.id limit 201)x;
  foreach lvl in array array['PRODUCT_SIZE','MODEL']loop
   if lvl='PRODUCT_SIZE'and ps_n>200 or lvl='MODEL'and m_n>200 then
    lv:=lv||jsonb_build_array(jsonb_build_object('level',lvl,'status','UNKNOWN','reason','HISTORY_GROUP_LIMIT'));continue;end if;
   if lvl='MODEL'and chosen is not null then
    lv:=lv||jsonb_build_array(jsonb_build_object('level',lvl,'status','NOT_EVALUATED','reason','PRODUCT_SIZE_SUFFICIENT'));continue;end if;
   todo:=array(select x from unnest(case when lvl='PRODUCT_SIZE'then ps_ids else m_ids end)x where not x=any(done)order by x);
   bi:=1;
   while bi<=cardinality(todo)loop
    part:=cp7_plan_native.history_groups(todo[bi:least(bi+49,cardinality(todo))],clk,kernel);
    if part->>'status'<>'COMPLETE'then st:='UNKNOWN';rs:=part->>'reason';exit;end if;
    res:=res||(part->'groups');unverified:=unverified+jsonb_array_length(part->'unverified');
    bi:=bi+50;
   end loop;
   exit when st is not null;
   done:=done||todo;
   -- The groups of this level that count: proven, spent in every pool, of
   -- this model only (cut and QC), finished inside the window.
   with gr as(select x from jsonb_array_elements(res)x where(x->>'group_id')::uuid=any(case when lvl='PRODUCT_SIZE'then ps_ids else m_ids end)),
   ok as(select x from gr where x->>'model_id'=p_model::text and x->'qc_models'<@jsonb_build_array(p_model)
     and not exists(select 1 from jsonb_array_elements(x->'pools')p where p->'spent'<>'true'::jsonb)
     and x->>'finished_at'is not null and((x->>'finished_at')::timestamptz at time zone 'Asia/Jakarta')::date>=first_day),
   pl as(select o.x->>'group_id'g,p from ok o,jsonb_array_elements(o.x->'pools')p
     where lvl='MODEL'or(p->>'size_id'=size::text and jsonb_array_length(p->'qc_roots')>0 and p->'qc_roots'<@jsonb_build_array(root)))
   select count(distinct g),coalesce(sum((p->>'input_pcs')::numeric),0),coalesce(sum((p->>'fg_pcs')::numeric),0),
    coalesce((select jsonb_agg(jsonb_build_object('group_id',o.x->'group_id','proof_id',o.x->'proof'->'proof_id','facts_hash',o.x->'proof'->'facts_hash',
      'captured_at',o.x->'proof'->'captured_at','finished_at',o.x->'finished_at')order by o.x->>'group_id')
     from ok o where o.x->>'group_id'in(select g from pl)),'[]'::jsonb)
   into ng,cut,fg,used from pl;
   if ng>=pol.min_groups and cut>=pol.min_cut_pcs then
    k:=cp7_plan_native.wilson_permille(fg::bigint,cut::bigint);
    lv:=lv||jsonb_build_array(jsonb_build_object('level',lvl,'status',case when k>=1 then'SUFFICIENT'else'UNKNOWN'end,
     'reason',case when k<1 then 'LOWER_BOUND_BELOW_ONE_PERMILLE'end,'groups',ng::text,'cut_pcs',cut::text,'fg_pcs',fg::text,
     'raw_numerator',fg::text,'raw_denominator',cut::text,'lower_bound_permille',k::text));
    chosen:=jsonb_build_object('level',lvl,'groups',ng,'cut',cut,'fg',fg,'k',k,'proofs',used);
   else
    lv:=lv||jsonb_build_array(jsonb_build_object('level',lvl,'status','INSUFFICIENT_SAMPLE','reason','HISTORY_SAMPLE_BELOW_POLICY',
     'groups',ng::text,'cut_pcs',cut::text,'fg_pcs',fg::text,'raw_numerator',fg::text,'raw_denominator',cut::text,'lower_bound_permille',null));
   end if;
  end loop;
  if st is null then
   if chosen is not null and(chosen->>'k')::integer>=1 then st:='AVAILABLE';rs:='HISTORY_LOWER_BOUND_AT_POLICY';level:=chosen->>'level';
   elsif chosen is not null then st:='UNKNOWN';rs:='LOWER_BOUND_BELOW_ONE_PERMILLE';level:=chosen->>'level';
   elsif exists(select 1 from jsonb_array_elements(lv)x where x->>'status'='UNKNOWN')then st:='UNKNOWN';
    rs:=(select x->>'reason'from jsonb_array_elements(lv)x where x->>'status'='UNKNOWN'limit 1);
   else st:='INSUFFICIENT_SAMPLE';rs:='HISTORY_SAMPLE_BELOW_POLICY';end if;
  end if;
  stale_or_unverifiable:=unverified;
  select count(*)filter(where x->>'finished_at'is null or((x->>'finished_at')::timestamptz at time zone 'Asia/Jakarta')::date<first_day),
   count(*)filter(where x->>'model_id'is distinct from p_model::text or not x->'qc_models'<@jsonb_build_array(p_model)),
   count(*)filter(where exists(select 1 from jsonb_array_elements(x->'pools')p where p->'spent'<>'true'::jsonb))
   into outside,unattributed,not_spent from jsonb_array_elements(res)x;
 end if;
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PLAN_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.history-yield.v2','status',st,'reason',rs,'target_key',p_target,
  'root_id',root,'size_id',size,'model_id',p_model,'checked_at',clk,'window_first_day',first_day,'kernel_version',kernel,
  'basis','PL8_STORED_PROOF_MATCHING_CURRENT_FACTS',
  'policy',jsonb_build_object('id',pol.id,'revision',pol.revision::text,'state',pol.state,'window_days',pol.window_days::text,
   'min_groups',pol.min_groups::text,'min_cut_pcs',pol.min_cut_pcs::text,'confidence',pol.confidence,'actor_role',pol.actor_role,'recorded_at',pol.recorded_at),
  'window_days',pol.window_days::text,'minimum_sample',jsonb_build_object('groups',pol.min_groups::text,'cut_pcs',pol.min_cut_pcs::text),
  'level',level,'levels',lv,
  'groups',case when st='AVAILABLE'then chosen->>'groups'end,'cut_pcs',case when st='AVAILABLE'then chosen->>'cut'end,
  'fg_pcs',case when st='AVAILABLE'then chosen->>'fg'end,'lower_bound_permille',case when st='AVAILABLE'then chosen->>'k'end,
  'lower_bound',case when st='AVAILABLE'then trim_scale((chosen->>'k')::numeric/1000)::text end,
  'numerator',case when st='AVAILABLE'then chosen->>'k'end,'denominator',case when st='AVAILABLE'then '1000'end,
  'proofs',case when st='AVAILABLE'then chosen->'proofs'else'[]'::jsonb end,
  'excluded',case when kernel is null then null else jsonb_build_object('stale_or_unverifiable',coalesce(stale_or_unverifiable,0)::text,
   'outside_window',coalesce(outside,0)::text,'unattributed',coalesce(unattributed,0)::text,'not_spent_now',coalesce(not_spent,0)::text)end);
end $$;

-- PL-5: the yield preflight uses. Without a saved policy it is the earlier
-- pending answer, byte for byte.
create function cp7_plan_native.history_yield(p_target text,p_model uuid)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select cp7_plan_native.history_source(p_target,p_model)
$$;

alter function cp7_plan_native.wilson_permille(bigint,bigint)owner to cp7_capture;
alter function cp7_plan_native.history_groups(uuid[],timestamptz,text)owner to cp7_capture;
alter function cp7_plan_native.history_source(text,uuid)owner to cp7_capture;
revoke all on function cp7_plan_native.wilson_permille(bigint,bigint),cp7_plan_native.history_groups(uuid[],timestamptz,text),
 cp7_plan_native.history_source(text,uuid)from public,anon,authenticated,service_role;
grant execute on function cp7_plan_native.history_source(text,uuid)to cp7_plan_writer;
