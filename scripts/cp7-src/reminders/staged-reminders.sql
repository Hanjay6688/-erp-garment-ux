-- Reminders v2 from a staged analysis snapshot (owner decision 8 Oct 2026;
-- docs/cp7/p19/P19_STAGED_SNAPSHOT_V2.md §5). The production, fabric and
-- accessory conditions of one staged run are built once, page by page, as
-- they stood at the snapshot ("data analisis per <time>") and never changed.
-- Before a local reminder preview is claimed, and again when it is finished,
-- the condition is checked again against the ERP as it is now, inside the
-- same transaction and after the last lock: a condition that has been
-- resolved since (stock and WIP now cover the need, the receivable has been
-- paid, the payable settled) is recorded as resolved and NOT claimed, so a
-- finished condition is never billed. Receivables and payables are always
-- read live with the v1 readers. Delivery stays the local preview record
-- (LOCAL_TEST_SINK): nothing is sent outside the ERP. Version 1 (one whole
-- Original) is unchanged; both versions share requests, destinations
-- (local_bindings), policies (rule_policies) and every lock key.

-- The intents a staged target's live recheck counts (a plan recorded after
-- the snapshot): their recording time and row transaction only.
grant select(recorded_at,xmin)on cp7_plan_native.intents to cp7_capture;

-- ------------------------------------------------------------------ tables --
create table cp7_reminder_native.staged_condition_sets(
 run_id uuid primary key,job_id uuid not null,actor uuid not null,identity_hash text not null check(identity_hash~'^[0-9a-f]{64}$'),
 data_as_of timestamptz not null,page_count integer not null check(page_count>=0),targets_total integer not null check(targets_total>=0),
 state text not null check(state in('RUNNING','DONE','FAILED')),unit_count integer not null check(unit_count=page_count+1),
 units_done integer not null default 0,unit_attempts integer not null default 0,failure_unit integer,failure_sqlstate text,failure_code text,
 failure_message text,totals jsonb,set_hash text check(set_hash~'^[0-9a-f]{64}$'),created_at timestamptz not null,updated_at timestamptz not null,
 check(units_done between 0 and unit_count),check((state='FAILED')=(failure_code is not null)),
 check((state='DONE')=(units_done=unit_count and set_hash is not null and totals is not null)));
create table cp7_reminder_native.staged_conditions(
 run_id uuid not null references cp7_reminder_native.staged_condition_sets(run_id),key text not null,page_index integer not null check(page_index>=0),
 seq integer not null check(seq>=0),ord integer not null check(ord>=1),rule_id text not null check(rule_id in('PRODUCTION_GAP','ACCESSORY_NEED','FABRIC_NEED')),
 domain text not null check(domain in('PRODUCTION','ACCESSORY','FABRIC')),target_key text not null,material_key text,source_id text,
 snapshot_state text not null check(snapshot_state in('ACTIVE','DATA_REVIEW','NO_CURRENT_GAP','RESOLVED')),reason text not null,
 value jsonb not null,production_state jsonb,label text,condition_hash text not null check(condition_hash~'^[0-9a-f]{64}$'),
 primary key(run_id,key),unique(run_id,page_index,seq));
create index staged_conditions_filter on cp7_reminder_native.staged_conditions(run_id,rule_id,snapshot_state,ord);
-- One episode per condition key at a time, shared by every actor and run,
-- opened by the first claim that finds the condition still open now and
-- resolved by a recheck that finds it resolved now.
create table cp7_reminder_native.staged_episodes(
 id uuid primary key default gen_random_uuid(),condition_key text not null,rule_id text not null,episode_number bigint not null check(episode_number>0),
 previous_id uuid references cp7_reminder_native.staged_episodes(id),state text not null check(state in('ACTIVE','RESOLVED')),
 opened_at timestamptz not null,resolved_at timestamptz,unique(condition_key,episode_number),check((state='RESOLVED')=(resolved_at is not null)));
create unique index staged_episode_one_active on cp7_reminder_native.staged_episodes(condition_key)where state='ACTIVE';
-- Every recorded recheck: its verdict now, the numbers it compared and, for
-- a snapshot condition, the time of the snapshot. Written once.
create table cp7_reminder_native.staged_rechecks(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,run_id uuid not null,
 identity_hash text not null,condition_key text not null,rule_id text not null,kind text not null check(kind in('SNAPSHOT','LIVE')),
 phase text not null check(phase in('CLAIM','FINISH')),data_as_of timestamptz,checked_at timestamptz not null,
 verdict text not null check(verdict in('STILL_OPEN','RESOLVED_NOW','BELOW_THRESHOLD_NOW','UNKNOWN_NOW','CHANGED_REVIEW_REQUIRED','NO_LONGER_DUE','NOT_FOUND_NOW','CONDITION_CHANGED')),
 reason text not null,numbers jsonb not null,policy_id uuid,episode_id uuid references cp7_reminder_native.staged_episodes(id),created_at timestamptz not null,
 check((kind='SNAPSHOT')=(data_as_of is not null)));
create index staged_rechecks_actor_run on cp7_reminder_native.staged_rechecks(actor,run_id,created_at);
create table cp7_reminder_native.staged_claims(
 id uuid primary key default gen_random_uuid(),actor uuid not null,run_id uuid not null,identity_hash text not null,
 binding_id uuid not null references cp7_reminder_native.local_bindings(id),condition_key text not null,rule_id text not null,
 kind text not null check(kind in('SNAPSHOT','LIVE')),condition_hash text not null,
 episode_id uuid not null references cp7_reminder_native.staged_episodes(id),occurrence_key text not null,
 environment text not null check(environment='LOCAL_TEST_SINK'),policy_id uuid not null,
 recheck_id uuid not null references cp7_reminder_native.staged_rechecks(id),finish_recheck_id uuid references cp7_reminder_native.staged_rechecks(id),
 fence uuid not null default gen_random_uuid(),status text not null check(status in('CLAIMED','LOCAL_SINK_CAPTURED','SUPPRESSED','UNKNOWN')),
 body text not null,body_sha256 text not null,reason text,created_at timestamptz not null,finished_at timestamptz,
 unique(actor,binding_id,environment,occurrence_key),check(status<>'LOCAL_SINK_CAPTURED'or finished_at is not null));
create index staged_claims_actor_run on cp7_reminder_native.staged_claims(actor,run_id,created_at);
create index staged_claims_key on cp7_reminder_native.staged_claims(condition_key,episode_id);
create table cp7_reminder_native.staged_claim_resolutions(
 id uuid primary key default gen_random_uuid(),claim_id uuid not null unique references cp7_reminder_native.staged_claims(id),
 actor uuid not null,outcome text not null check(outcome in('CAPTURE_CONFIRMED','NOT_CAPTURED_CONFIRMED')),
 reason text not null,created_at timestamptz not null);
do $$declare t text;begin
 foreach t in array array['staged_condition_sets','staged_conditions','staged_episodes','staged_rechecks','staged_claims','staged_claim_resolutions']loop
  execute format('alter table cp7_reminder_native.%I owner to cp7_reminder',t);
  execute format('alter table cp7_reminder_native.%I enable row level security',t);
  execute format('create policy %I on cp7_reminder_native.%I for all to public using(false)with check(false)',t||'_no_access',t);
  execute format('revoke all on cp7_reminder_native.%I from public,anon,authenticated,service_role',t);
 end loop;
end $$;
create trigger staged_conditions_immutable before update or delete on cp7_reminder_native.staged_conditions for each row execute function cp7_reminder_native.immutable_request();
create trigger staged_rechecks_immutable before update or delete on cp7_reminder_native.staged_rechecks for each row execute function cp7_reminder_native.immutable_request();
create trigger staged_resolutions_immutable before update or delete on cp7_reminder_native.staged_claim_resolutions for each row execute function cp7_reminder_native.immutable_request();

-- A set changes only its progress until it is DONE or FAILED; the totals and
-- the set hash are written once by its last unit.
create function cp7_reminder_native.guard_staged_set()returns trigger
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='DELETE'or old.state<>'RUNNING'or(old.run_id,old.job_id,old.actor,old.identity_hash,old.data_as_of,old.page_count,old.targets_total,old.unit_count,old.created_at)
  is distinct from(new.run_id,new.job_id,new.actor,new.identity_hash,new.data_as_of,new.page_count,new.targets_total,new.unit_count,new.created_at)
  or new.units_done<old.units_done or(old.totals is not null and new.totals is distinct from old.totals)
  or(old.set_hash is not null and new.set_hash is distinct from old.set_hash)then
  raise exception using errcode='55000',message='CP7_REMINDER_V2_SET_IMMUTABLE';end if;
 return new;
end $$;
create trigger staged_set_progress before update or delete on cp7_reminder_native.staged_condition_sets for each row execute function cp7_reminder_native.guard_staged_set();
-- An episode is opened ACTIVE and can only be resolved, once.
create function cp7_reminder_native.guard_staged_episode()returns trigger
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='DELETE'or old.state<>'ACTIVE'or new.state<>'RESOLVED'or(old.id,old.condition_key,old.rule_id,old.episode_number,old.previous_id,old.opened_at)
  is distinct from(new.id,new.condition_key,new.rule_id,new.episode_number,new.previous_id,new.opened_at)then
  raise exception using errcode='55000',message='CP7_REMINDER_V2_EPISODE_IMMUTABLE';end if;
 return new;
end $$;
create trigger staged_episode_history before update or delete on cp7_reminder_native.staged_episodes for each row execute function cp7_reminder_native.guard_staged_episode();
-- A claim is finished once: CLAIMED to its outcome, with its finish recheck.
create function cp7_reminder_native.guard_staged_claim()returns trigger
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='DELETE'or old.status<>'CLAIMED'or new.status='CLAIMED'or(old.id,old.actor,old.run_id,old.identity_hash,old.binding_id,old.condition_key,
  old.rule_id,old.kind,old.condition_hash,old.episode_id,old.occurrence_key,old.environment,old.policy_id,old.recheck_id,old.fence,old.body,old.body_sha256,old.created_at)
  is distinct from(new.id,new.actor,new.run_id,new.identity_hash,new.binding_id,new.condition_key,
  new.rule_id,new.kind,new.condition_hash,new.episode_id,new.occurrence_key,new.environment,new.policy_id,new.recheck_id,new.fence,new.body,new.body_sha256,new.created_at)
  or old.finish_recheck_id is not null then
  raise exception using errcode='55000',message='CP7_LOCAL_CLAIM_IMMUTABLE';end if;
 return new;
end $$;
create trigger staged_claim_history before update or delete on cp7_reminder_native.staged_claims for each row execute function cp7_reminder_native.guard_staged_claim();

-- --------------------------------------------------------- capabilities --
-- Private capabilities into the caller's own finished staged run (owner
-- cp7_capture; EXECUTE only to cp7_reminder; precedent original_authority).
-- They return only what the reminders need; they never decide a verdict.
grant usage,create on schema cp7_reminder_native to cp7_capture;
-- The run (its identity, time, pages, totals) and which of the given target
-- keys it holds. A run of another actor, not finished, or without its
-- retained index is unavailable.
create function cp7_reminder_native.staged_authority(p_run uuid,p_targets text[])returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;j cp7_analysis_stage.jobs%rowtype;s cp7_analysis_stage.page_sets%rowtype;h cp7_analysis_stage.headers%rowtype;present text[];
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if cardinality(coalesce(p_targets,'{}'))>4000 then raise exception 'CP7_REMINDER_V2_PAYLOAD';end if;
 select *into j from cp7_analysis_stage.jobs x where x.run_id=p_run and x.actor=(a->>'actor')::uuid and x.state='DONE';
 select *into s from cp7_analysis_stage.page_sets x where x.run_id=j.run_id;
 select *into h from cp7_analysis_stage.headers x where x.run_id=j.run_id;
 if j.id is null or s.run_id is null or h.run_id is null then raise exception using errcode='42501',message='CP7_REMINDER_V2_SNAPSHOT_UNAVAILABLE';end if;
 if not exists(select 1 from cp7_analysis_stage.plan_scope x where x.job_id=j.id)
  or not exists(select 1 from cp7_analysis_stage.capture_marks x where x.job_id=j.id)then raise exception 'CP7_REMINDER_V2_SNAPSHOT_INDEX_MISSING';end if;
 present:=array(select distinct k from unnest(coalesce(p_targets,'{}'))k
  where exists(select 1 from cp7_analysis_stage.plan_targets t where t.job_id=j.id and t.target_key=k)order by k);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return jsonb_build_object('run_id',j.run_id,'job_id',j.id,'actor',j.actor,'identity_hash',s.identity_hash,'data_as_of',j.captured_at,
  'page_count',h.page_count,'targets_total',h.targets_total,'totals',s.totals,'targets_present',to_jsonb(present));
end $$;
-- One page of the run as the reminders read it: per recommendation its
-- target, product and conditional gap; per material need its target,
-- material and additional external need; the labels of the page's targets
-- (as the report reads them, a target with two labels refused) and the
-- retained index of the page's targets (order, count, conditional gap).
create function cp7_reminder_native.staged_page_inputs(p_run uuid,p_index integer)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;j cp7_analysis_stage.jobs%rowtype;h cp7_analysis_stage.headers%rowtype;pg cp7_analysis_stage.pages%rowtype;
 body jsonb;recs jsonb;mats jsonb;labels jsonb;dup text;targets jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 select *into j from cp7_analysis_stage.jobs x where x.run_id=p_run and x.actor=(a->>'actor')::uuid and x.state='DONE';
 select *into h from cp7_analysis_stage.headers x where x.run_id=j.run_id;
 if j.id is null or h.run_id is null then raise exception using errcode='42501',message='CP7_REMINDER_V2_SNAPSHOT_UNAVAILABLE';end if;
 select *into pg from cp7_analysis_stage.pages x where x.run_id=j.run_id and x.idx=p_index;
 if pg.run_id is null then raise exception 'CP7_REMINDER_V2_SNAPSHOT_INVARIANT';end if;
 body:=pg.body::jsonb;
 if body->>'run_id'is distinct from p_run::text or(body->>'index')::integer is distinct from p_index
  or coalesce(jsonb_array_length(body->'items'->'recommendations'),0)<>coalesce((pg.counts->>'recommendations')::integer,0)
  or coalesce(jsonb_array_length(body->'items'->'material_needs'),0)<>coalesce((pg.counts->>'material_needs')::integer,0)then
  raise exception 'CP7_REMINDER_V2_SNAPSHOT_INVARIANT';end if;
 select coalesce(jsonb_agg(jsonb_build_object('target_key',r.v->'target'->'key','product_id',r.v->'target'->'product_id',
   'q_conditional',r.v->'q_conditional','production_state',r.v->'production_state')order by r.o),'[]'::jsonb)into recs
  from jsonb_array_elements(coalesce(body->'items'->'recommendations','[]'::jsonb))with ordinality r(v,o);
 select coalesce(jsonb_agg(jsonb_build_object('target_key',m.v->'target_key','material_key',m.v->'material_key',
   'additional_external',m.v->'additional_external')order by m.o),'[]'::jsonb)into mats
  from jsonb_array_elements(coalesce(body->'items'->'material_needs','[]'::jsonb))with ordinality m(v,o);
 with keys as materialized(select distinct x->>'target_key'tk from jsonb_array_elements(recs||mats)x),
 lb as materialized(select l.value->>'target_key'tk,count(*)n,min(jsonb_build_object('sku',l.value->'sku','product_name',l.value->'product_name')::text)::jsonb v
  from jsonb_array_elements(coalesce((h.body::jsonb)->'product_labels','[]'::jsonb))l where l.value->>'target_key'in(select tk from keys)group by 1)
 select coalesce(jsonb_object_agg(lb.tk,lb.v),'{}'::jsonb),min(lb.tk)filter(where lb.n>1)into labels,dup from lb;
 if dup is not null then raise exception 'CP7_REMINDER_V2_LABEL_AMBIGUOUS';end if;
 select coalesce(jsonb_object_agg(x.target_key,jsonb_build_object('ord',x.ord,'n',x.n,'conditional_gap_pcs',x.gap)),'{}'::jsonb)into targets
  from(select t.target_key,min(t.ord)ord,count(*)n,min(t.row->>'conditional_gap_pcs')gap from cp7_analysis_stage.plan_targets t
   where t.job_id=j.id and t.ord between pg.target_lo and pg.target_hi group by t.target_key)x;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return jsonb_build_object('index',pg.idx,'target_lo',pg.target_lo,'target_hi',pg.target_hi,'recommendations',recs,'material_needs',mats,
  'labels',labels,'targets',targets);
end $$;
-- One target of the run now: the snapshot values the recheck compares
-- (conditional gap, available finished stock, the WIP of the model and size
-- when the snapshot's WIP was complete, the product), the target read live by
-- the plan v2 reader (current product, production policy, finished stock and
-- WIP, under one clock), the plans of the target recorded after the snapshot
-- and, for a fabric material, its stock movements and purchase commitments
-- recorded after the snapshot (by the snapshot's database snapshot, so a
-- write running at the capture or a backdated entry both count).
create function cp7_reminder_native.staged_target_now(p_run uuid,p_target text,p_material text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;j cp7_analysis_stage.jobs%rowtype;m cp7_analysis_stage.capture_marks%rowtype;n integer;r jsonb;sc jsonb;product jsonb;products jsonb;
 live jsonb;since timestamptz;snap pg_snapshot;ref bigint;low bigint;plans bigint;moves bigint;commitments bigint;material uuid;wip_snap text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if p_target!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or p_material is not null and p_material!~'^FABRIC_[A-Z]+:'and p_material!~'^[A-Za-z0-9_:-]{1,200}$'then raise exception 'CP7_REMINDER_V2_PAYLOAD';end if;
 select *into j from cp7_analysis_stage.jobs x where x.run_id=p_run and x.actor=(a->>'actor')::uuid and x.state='DONE';
 if j.id is null then raise exception using errcode='42501',message='CP7_REMINDER_V2_SNAPSHOT_UNAVAILABLE';end if;
 select *into m from cp7_analysis_stage.capture_marks x where x.job_id=j.id;
 if m.job_id is null then raise exception 'CP7_REMINDER_V2_SNAPSHOT_INDEX_MISSING';end if;
 select count(*)into n from cp7_analysis_stage.plan_targets x where x.job_id=j.id and x.target_key=p_target;
 if n<>1 then raise exception using errcode='42501',message='CP7_REMINDER_V2_CONDITION_UNAVAILABLE';end if;
 select x.row into r from cp7_analysis_stage.plan_targets x where x.job_id=j.id and x.target_key=p_target;
 select x.scope into sc from cp7_analysis_stage.plan_scope x where x.job_id=j.id;
 if sc is null then raise exception 'CP7_REMINDER_V2_SNAPSHOT_INDEX_MISSING';end if;
 select coalesce(jsonb_agg(x),'[]'::jsonb)into products from jsonb_array_elements(r->'products')x where(x->>'root_id')||':'||(x->>'size_id')=p_target;
 product:=case when jsonb_array_length(products)=1 then products->0 end;
 wip_snap:=case when sc->>'wip_status'='COMPLETE'and product is not null then
  coalesce(sc->'wip_by_model_size'->>((product->>'model_id')||':'||(product->>'size_id')),'0')end;
 live:=cp7_plan_native.staged_live(p_run,p_target);
 since:=j.captured_at;snap:=m.source_snapshot;
 -- A row's 32-bit xmin as the full id in the 2^32 window ending at this
 -- statement's snapshot (analysis-stage-snapshot.sql, plan v2 after_snapshot).
 ref:=pg_snapshot_xmax(pg_current_snapshot())::text::bigint;low:=ref%4294967296;
 select count(*)into plans from cp7_plan_native.intents i where i.target_key=p_target and(i.recorded_at>=since or(snap is not null and not pg_visible_in_snapshot(
  ((case when i.xmin::text::bigint<=low then ref-low else greatest(ref-low-4294967296,0)end)+i.xmin::text::bigint)::text::xid8,snap)));
 if p_material~'^FABRIC_MATERIAL:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'then
  material:=split_part(p_material,':',2)::uuid;
  select count(*)into moves from erp.material_stock_movements x where x.material_id=material and(x.system_created_at>=since or(snap is not null and not pg_visible_in_snapshot(
   ((case when x.xmin::text::bigint<=low then ref-low else greatest(ref-low-4294967296,0)end)+x.xmin::text::bigint)::text::xid8,snap)));
  select count(distinct c.id)into commitments from erp.bb_purchase_commitments_v1 c join erp.bb_purchase_commitment_lines_v1 l on l.commitment_id=c.id
   where l.material_id=material and(c.created_at>=since or(snap is not null and not pg_visible_in_snapshot(
    ((case when c.xmin::text::bigint<=low then ref-low else greatest(ref-low-4294967296,0)end)+c.xmin::text::bigint)::text::xid8,snap)));
 end if;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return jsonb_build_object('checked_at',live->'checked_at','data_as_of',since,
  'snapshot',jsonb_build_object('need_pcs',r->'conditional_gap_pcs','available_fg_pcs',r->'available_fg_pcs','wip_status',sc->'wip_status',
   'wip_model_size_pcs',wip_snap,'product',product,'production_state',r->'production_policy'->'policy'->'state'),
  'live',jsonb_build_object('products',live->'products','policy_state',live->'policy'->'policy'->'state','policy_quality',live->'policy'->'policy'->'quality',
   'fg_pcs',live->'fg_pcs','wip',live->'wip'),
  'target_plans_after',plans,'material',case when material is null then null else
   jsonb_build_object('material_id',material,'movements_after',moves,'commitments_after',commitments)end);
end $$;
do $$declare r record;begin
 for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='cp7_reminder_native'and p.proname in('staged_authority','staged_page_inputs','staged_target_now')loop
  execute format('alter function %s owner to cp7_capture',r.sig);
  execute format('revoke all on function %s from public,anon,authenticated,service_role',r.sig);
  execute format('grant execute on function %s to cp7_reminder',r.sig);
 end loop;
end $$;
revoke create on schema cp7_reminder_native from cp7_capture;

-- ---------------------------------------------------------------- access --
create function cp7_reminder_native.staged_wib(t timestamptz)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select to_char(t at time zone 'Asia/Jakarta','YYYY-MM-DD HH24:MI:SS')||' WIB'
$$;
-- The caller's current reminder access (internal role and the four planning
-- permissions, as v1) over its own finished staged run. A staged run holds no
-- finance, so the v1 rechecks see no financial source.
create function cp7_reminder_native.staged_access(p_run uuid,p_targets text[] default null)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;k text;s jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if p_run is null then raise exception 'CP7_REMINDER_V2_PAYLOAD';end if;
 if auth.uid()is null or coalesce(auth.jwt()->>'role','')<>'authenticated'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();if a->'allowed'is distinct from'true'::jsonb then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_DENIED';end if;
 if coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN','STAFF')then raise exception using errcode='42501',message='CP7_REMINDER_INTERNAL_ROLE_REQUIRED';end if;
 foreach k in array array['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']loop
  if not erp.has_permission(k)then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_DENIED';end if;
 end loop;
 s:=cp7_reminder_native.staged_authority(p_run,p_targets);
 if erp.get_my_access_v1()is distinct from a then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return jsonb_build_object('access',a,'analysis',jsonb_build_object('run_id',p_run,'financial_source',null,'staged',s));
end $$;
-- The latest policies visible now (v1's rule): receivable/payable rules only
-- with their finance view, a target policy only for a target of this run.
create function cp7_reminder_native.staged_policy_rows(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare latest jsonb;present jsonb;
begin
 select coalesce(jsonb_agg(to_jsonb(p)order by p.rule_id,p.scope_kind,p.scope_key),'[]'::jsonb)into latest from(
  select distinct on(rule_id,scope_kind,scope_key)*from cp7_reminder_native.rule_policies order by rule_id,scope_kind,scope_key,revision desc)p;
 present:=cp7_reminder_native.staged_authority(p_run,array(select distinct x->>'scope_key'from jsonb_array_elements(latest)x where x->>'scope_kind'='TARGET'))->'targets_present';
 return(select coalesce(jsonb_agg(jsonb_build_object('policy_id',x->'id','rule_id',x->'rule_id','scope_kind',x->'scope_kind','scope_key',x->'scope_key',
   'revision',x->>'revision','previous_id',x->'previous_id','config',x->'config','reason',x->'reason','created_at',x->'created_at','created_by',x->'created_by')
   order by x->>'rule_id',x->>'scope_kind',x->>'scope_key'),'[]'::jsonb)
  from jsonb_array_elements(latest)x
  where(x->>'rule_id'not in('AR_DUE','AP_DUE')or erp.has_permission(case x->>'rule_id'when'AR_DUE'then'finance.ar.view'else'finance.ap.view'end))
   and(x->>'scope_kind'='GLOBAL'or present?(x->>'scope_key')));
end $$;
-- A row as v1's condition_policy reads it, from a stored snapshot condition.
create function cp7_reminder_native.staged_row(c cp7_reminder_native.staged_conditions,p_as_of timestamptz)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('key',c.key,'rule_id',c.rule_id,'target_key',c.target_key,'source_id',c.source_id,'material_key',c.material_key,
  'state',c.snapshot_state,'reason',c.reason,'value',c.value,'production_state',c.production_state,'domain',c.domain,'label',c.label,
  'page_index',c.page_index,'ord',c.ord,'condition_hash',c.condition_hash,'kind','SNAPSHOT','data_as_of',p_as_of,'economic_state','NOT_APPLICABLE',
  'financial_source',null,'business_resolved',c.snapshot_state='RESOLVED')
$$;
-- The hash a live obligation row is presented with: the row without the
-- policy fields computed at the read (a new reading of the same facts and
-- the same document gives the same hash; a payment, a correction or the next
-- day of lateness gives another).
create function cp7_reminder_native.staged_live_hash(r jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(pg_catalog.sha256(convert_to((r-'policy_binding'-'policy_timing'-'eligibility'-'delivery_sent'-'eligibility_meaning'-'condition_hash')::text,'UTF8')),'hex')
$$;

-- ------------------------------------------------------- condition set --
-- The snapshot conditions of one page, with v1's rules (rule-condition-
-- source.sql) as they stood at the snapshot; the SOURCE_CHANGED state of v1
-- does not exist here (the snapshot is labelled with its time instead). The
-- page's gap must equal the retained index's gap of the same target.
create function cp7_reminder_native.staged_page_rows(inp jsonb,p_run uuid,p_identity text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare acc jsonb[]:='{}';r jsonb;t jsonb;tk text;value jsonb;known boolean;state text;reason text;label text;row jsonb;seq integer:=0;
 rule text;domain text;mk text;key text;
begin
 for r in select x.value from jsonb_array_elements(inp->'recommendations')x loop
  tk:=r->>'target_key';t:=inp->'targets'->tk;
  if tk is null or t is null or(t->>'n')::integer<>1 or r->'q_conditional'->>'value'is distinct from t->>'conditional_gap_pcs'then
   raise exception 'CP7_REMINDER_V2_SNAPSHOT_INVARIANT';end if;
  value:=r->'q_conditional';known:=value->>'state'in('KNOWN','ASSUMED');
  if not known then state:='DATA_REVIEW';reason:='GAP_NOT_PROVEN_AT_SNAPSHOT';
  elsif(value->>'value')::numeric>0 then state:='ACTIVE';reason:='EXACT_SIZE_GAP_AT_SNAPSHOT';
  elsif value->>'state'='ASSUMED'then state:='NO_CURRENT_GAP';reason:='SELECTED_SCENARIO_COVERAGE_AT_SNAPSHOT';
  else state:='RESOLVED';reason:='KNOWN_ZERO_GAP_AT_SNAPSHOT';end if;
  label:=(inp->'labels'->tk->>'sku')||' · '||(inp->'labels'->tk->>'product_name');key:='PRODUCTION_GAP:'||tk;
  row:=jsonb_build_object('key',key,'seq',seq,'ord',(t->>'ord')::integer,'rule_id','PRODUCTION_GAP','domain','PRODUCTION','target_key',tk,
   'material_key',null,'source_id',r->>'product_id','snapshot_state',state,'reason',reason,'value',value,'production_state',r->'production_state','label',label);
  acc:=acc||(row||jsonb_build_object('condition_hash',encode(pg_catalog.sha256(convert_to((row-'seq'||jsonb_build_object('run_id',p_run,'identity_hash',p_identity))::text,'UTF8')),'hex')));
  seq:=seq+1;
 end loop;
 for r in select x.value from jsonb_array_elements(inp->'material_needs')x loop
  tk:=r->>'target_key';t:=inp->'targets'->tk;mk:=r->>'material_key';
  if tk is null or t is null or(t->>'n')::integer<>1 then raise exception 'CP7_REMINDER_V2_SNAPSHOT_INVARIANT';end if;
  value:=r->'additional_external';known:=value->>'state'in('KNOWN','ASSUMED');
  if left(coalesce(mk,''),7)='FABRIC_'then
   rule:='FABRIC_NEED';domain:='FABRIC';key:='FABRIC_NEED:'||tk||':'||mk;
   if not known then state:='DATA_REVIEW';
    reason:=case when mk like'FABRIC_UNREVIEWED:%'then'FABRIC_RECIPE_NOT_REVIEWED'else coalesce(value->>'reason','FABRIC_PHYSICAL_NOT_PROVEN')end;
   elsif(value->>'value')::numeric>0 then state:='ACTIVE';reason:='ADDITIONAL_EXTERNAL_FABRIC_NEED_AT_SNAPSHOT';
   elsif value->>'state'='ASSUMED'then state:='NO_CURRENT_GAP';reason:='SELECTED_FABRIC_RECIPE_SCENARIO_AT_SNAPSHOT';
   else state:='RESOLVED';reason:='KNOWN_ZERO_FABRIC_NEED_AT_SNAPSHOT';end if;
  else
   rule:='ACCESSORY_NEED';domain:='ACCESSORY';key:='ACCESSORY_NEED:'||tk||':'||coalesce(mk,'UNKNOWN_BOM');
   if not known then state:='DATA_REVIEW';reason:='INSTALLATION_AND_ELIGIBLE_UNUSED_SUPPLY_NOT_PROVEN';
   elsif(value->>'value')::numeric>0 then state:='ACTIVE';reason:='ADDITIONAL_EXTERNAL_ACCESSORY_NEED_AT_SNAPSHOT';
   elsif value->>'state'='ASSUMED'then state:='NO_CURRENT_GAP';reason:='SELECTED_MATERIAL_SCENARIO_AT_SNAPSHOT';
   else state:='RESOLVED';reason:='KNOWN_ZERO_ACCESSORY_NEED_AT_SNAPSHOT';end if;
  end if;
  label:=(inp->'labels'->tk->>'sku')||' · '||(inp->'labels'->tk->>'product_name');
  row:=jsonb_build_object('key',key,'seq',seq,'ord',(t->>'ord')::integer,'rule_id',rule,'domain',domain,'target_key',tk,
   'material_key',mk,'source_id',split_part(tk,':',1),'snapshot_state',state,'reason',reason,'value',value,'production_state',null,'label',label);
  acc:=acc||(row||jsonb_build_object('condition_hash',encode(pg_catalog.sha256(convert_to((row-'seq'||jsonb_build_object('run_id',p_run,'identity_hash',p_identity))::text,'UTF8')),'hex')));
  seq:=seq+1;
 end loop;
 return to_jsonb(acc);
end $$;
create function cp7_reminder_native.staged_set_status(p_run uuid)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('contract_version','cp7.reminder-condition-set.v2','run_id',s.run_id,'identity_hash',s.identity_hash,'data_as_of',s.data_as_of,
  'state',s.state,'stage',case when s.state='RUNNING'then case when s.units_done<s.page_count then 'PAGE'else 'SEAL'end end,
  'units_done',s.units_done,'unit_count',s.unit_count,'unit_attempts',s.unit_attempts,'pages_done',least(s.units_done,s.page_count),
  'page_count',s.page_count,'targets_total',s.targets_total,'totals',s.totals,'set_hash',s.set_hash,'last_progress_at',s.updated_at,
  'failure',case when s.state='FAILED'then jsonb_build_object('unit',s.failure_unit,'sqlstate',s.failure_sqlstate,'code',s.failure_code)end,
  'worker_active',false,'sent',false)
 from cp7_reminder_native.staged_condition_sets s where s.run_id=p_run
$$;
-- One unit of a set: page k (its conditions), then SEAL: the row counts
-- equal the run's totals (every recommendation and material need of every
-- page), the totals per rule and state, and the set hash over the identity
-- hash and every condition hash in page order.
create function cp7_reminder_native.staged_set_unit(s cp7_reminder_native.staged_condition_sets,a jsonb)returns void
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare inp jsonb;rows jsonb;recs bigint;mats bigint;tot jsonb;h text;items jsonb:=a->'analysis'->'staged'->'totals'->'items';
begin
 if s.units_done<s.page_count then
  inp:=cp7_reminder_native.staged_page_inputs(s.run_id,s.units_done);
  rows:=cp7_reminder_native.staged_page_rows(inp,s.run_id,s.identity_hash);
  begin
   insert into cp7_reminder_native.staged_conditions(run_id,key,page_index,seq,ord,rule_id,domain,target_key,material_key,source_id,
    snapshot_state,reason,value,production_state,label,condition_hash)
   select s.run_id,x->>'key',s.units_done,(x->>'seq')::integer,(x->>'ord')::integer,x->>'rule_id',x->>'domain',x->>'target_key',x->>'material_key',
    x->>'source_id',x->>'snapshot_state',x->>'reason',x->'value',nullif(x->'production_state','null'::jsonb),x->>'label',x->>'condition_hash'
   from jsonb_array_elements(rows)x;
  exception when unique_violation then raise exception 'CP7_REMINDER_V2_SNAPSHOT_INVARIANT';
  end;
  return;
 end if;
 select count(*)filter(where c.rule_id='PRODUCTION_GAP'),count(*)filter(where c.rule_id<>'PRODUCTION_GAP')into recs,mats
  from cp7_reminder_native.staged_conditions c where c.run_id=s.run_id;
 if recs<>coalesce((items->>'recommendations')::bigint,0)or mats<>coalesce((items->>'material_needs')::bigint,0)then
  raise exception 'CP7_REMINDER_V2_SNAPSHOT_INVARIANT';end if;
 select jsonb_build_object('conditions',recs+mats,'by_rule',coalesce(jsonb_object_agg(x.rule_id,x.states),'{}'::jsonb))into tot from(
  select y.rule_id,jsonb_object_agg(y.snapshot_state,y.n)states from(select c.rule_id,c.snapshot_state,count(*)n from cp7_reminder_native.staged_conditions c
   where c.run_id=s.run_id group by 1,2)y group by 1)x;
 select encode(pg_catalog.sha256(convert_to(s.identity_hash||E'\n'||coalesce(string_agg(c.condition_hash,E'\n'order by c.page_index,c.seq),''),'UTF8')),'hex')into h
  from cp7_reminder_native.staged_conditions c where c.run_id=s.run_id;
 update cp7_reminder_native.staged_condition_sets set totals=tot,set_hash=h where run_id=s.run_id;
end $$;
-- One request builds at most one unit (the 8 s statement limit holds per
-- request); a concurrent request skips the locked set and reports it.
create function cp7_reminder_native.staged_set_step(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;st jsonb;s cp7_reminder_native.staged_condition_sets%rowtype;r jsonb;
begin
 a:=cp7_reminder_native.staged_access(p_run);st:=a->'analysis'->'staged';
 select *into s from cp7_reminder_native.staged_condition_sets x where x.run_id=p_run for update skip locked;
 if not found then
  if exists(select 1 from cp7_reminder_native.staged_condition_sets x where x.run_id=p_run)then
   return cp7_reminder_native.staged_set_status(p_run)||jsonb_build_object('worker_active',true);end if;
  insert into cp7_reminder_native.staged_condition_sets(run_id,job_id,actor,identity_hash,data_as_of,page_count,targets_total,state,unit_count,created_at,updated_at)
  values(p_run,(st->>'job_id')::uuid,auth.uid(),st->>'identity_hash',(st->>'data_as_of')::timestamptz,(st->>'page_count')::integer,
   (st->>'targets_total')::integer,'RUNNING',(st->>'page_count')::integer+1,clock_timestamp(),clock_timestamp())on conflict do nothing;
  select *into s from cp7_reminder_native.staged_condition_sets x where x.run_id=p_run for update skip locked;
  if not found then return cp7_reminder_native.staged_set_status(p_run)||jsonb_build_object('worker_active',true);end if;
 end if;
 if s.actor<>auth.uid()or s.identity_hash<>st->>'identity_hash'then raise exception 'CP7_REMINDER_V2_SNAPSHOT_INVARIANT';end if;
 if s.state='RUNNING'then
  begin
   perform cp7_reminder_native.staged_set_unit(s,a);
   update cp7_reminder_native.staged_condition_sets set units_done=units_done+1,unit_attempts=0,updated_at=clock_timestamp(),
    state=case when units_done+1=unit_count then 'DONE'else 'RUNNING'end where run_id=p_run;
  exception
   when query_canceled then
    update cp7_reminder_native.staged_condition_sets set unit_attempts=unit_attempts+1,updated_at=clock_timestamp(),
     state=case when unit_attempts+1>=3 then 'FAILED'else state end,
     failure_unit=case when unit_attempts+1>=3 then units_done end,failure_sqlstate=case when unit_attempts+1>=3 then SQLSTATE end,
     failure_code=case when unit_attempts+1>=3 then 'CP7_REMINDER_V2_STAGE_STOPPED'end,failure_message=case when unit_attempts+1>=3 then SQLERRM end where run_id=p_run;
   when insufficient_privilege then raise;
   when others then
    update cp7_reminder_native.staged_condition_sets set state='FAILED',updated_at=clock_timestamp(),failure_unit=units_done,failure_sqlstate=SQLSTATE,
     failure_code=case when SQLERRM~'^CP7_[A-Z0-9_]+$'then SQLERRM else 'CP7_REMINDER_V2_STAGE_ERROR'end,failure_message=SQLERRM where run_id=p_run;
  end;
 end if;
 r:=cp7_reminder_native.staged_set_status(p_run);
 if erp.get_my_access_v1()is distinct from a->'access'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return r;
end $$;

-- ---------------------------------------------------------------- reads --
-- The snapshot conditions of the run, filtered and paged (at most 50), each
-- with the policy that applies to it now and its eligibility for a local
-- preview judged on the snapshot value (the recheck at claim decides).
create function cp7_reminder_native.staged_conditions_read(p jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;run uuid;s cp7_reminder_native.staged_condition_sets%rowtype;policies jsonb;rows jsonb;total bigint;at timestamptz:=clock_timestamp();
 lim integer;off integer;
begin
 if jsonb_typeof(p)is distinct from'object'or not(p?&array['run_id','rule_id','state','offset','limit'])or(select count(*)from jsonb_object_keys(p))<>5
  or jsonb_typeof(p->'run_id')<>'string'or p->>'run_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'rule_id')not in('string','null')or coalesce(p->>'rule_id','PRODUCTION_GAP')not in('PRODUCTION_GAP','ACCESSORY_NEED','FABRIC_NEED')
  or jsonb_typeof(p->'state')not in('string','null')or coalesce(p->>'state','ACTIVE')not in('ACTIVE','DATA_REVIEW','NO_CURRENT_GAP','RESOLVED')
  or jsonb_typeof(p->'offset')<>'number'or jsonb_typeof(p->'limit')<>'number'or(p->>'offset')!~'^(0|[1-9][0-9]{0,6})$'or(p->>'limit')!~'^([1-9]|[1-4][0-9]|50)$'
  then raise exception 'CP7_REMINDER_V2_PAYLOAD';end if;
 run:=(p->>'run_id')::uuid;lim:=(p->>'limit')::integer;off:=(p->>'offset')::integer;
 a:=cp7_reminder_native.staged_access(run);
 select *into s from cp7_reminder_native.staged_condition_sets x where x.run_id=run;
 if s.run_id is null or s.state<>'DONE'then raise exception using errcode='40001',message='CP7_REMINDER_V2_CONDITIONS_NOT_READY';end if;
 policies:=cp7_reminder_native.staged_policy_rows(run);
 select count(*)into total from cp7_reminder_native.staged_conditions c where c.run_id=run
  and(p->>'rule_id'is null or c.rule_id=p->>'rule_id')and(p->>'state'is null or c.snapshot_state=p->>'state');
 select coalesce(jsonb_agg(cp7_reminder_native.condition_policy(cp7_reminder_native.staged_row(c,s.data_as_of),policies,at)order by c.ord,c.page_index,c.seq),'[]'::jsonb)
  into rows from(select *from cp7_reminder_native.staged_conditions c where c.run_id=run
   and(p->>'rule_id'is null or c.rule_id=p->>'rule_id')and(p->>'state'is null or c.snapshot_state=p->>'state')
   order by c.ord,c.page_index,c.seq offset off limit lim)c;
 if erp.get_my_access_v1()is distinct from a->'access'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.reminder-conditions.v2','actor_scope_id',auth.uid(),'run_id',run,'identity_hash',s.identity_hash,
  'data_as_of',s.data_as_of,'set',cp7_reminder_native.staged_set_status(run),'query',p,'total',total,'rows',rows,'read_at',at,
  'eligibility_basis','SNAPSHOT_VALUE_POLICY_AT_READ','recheck_required_before_preview',true,'external_delivery_enabled',false,'sent',false);
end $$;
-- Receivables and payables of every domain the caller may see, read now with
-- the v1 readers and rules (never from a snapshot), each with its hash.
-- p_domain limits the read to the one reader a single condition needs.
create function cp7_reminder_native.staged_obligation_rows(p_domain text,policies jsonb,p_at timestamptz)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare ar jsonb;ap jsonb;other jsonb;rows jsonb;
begin
 if p_domain is not null and p_domain not in('SALES_AR','MATERIAL_AP','OPENING_AR','OPENING_AP','PAYROLL_AP','ACCESSORY_AP','LAUNDRY_AP','LAUNDRY_RECEIPT','LAUNDRY_OPENING_UNINVOICED')then
  raise exception 'CP7_REMINDER_V2_PAYLOAD';end if;
 select case when(p_domain is null or p_domain='SALES_AR')and erp.has_permission('finance.ar.view')then cp7_reminder_native.receivable_source()end,
  case when(p_domain is null or p_domain='MATERIAL_AP')and erp.has_permission('finance.ap.view')then cp7_reminder_native.payable_source()end,
  case when p_domain is null or p_domain not in('SALES_AR','MATERIAL_AP')then cp7_reminder_native.other_obligation_source()end
 into ar,ap,other;
 rows:=cp7_reminder_native.condition_rows('{}'::jsonb,ar,ap,policies,p_at);
 select rows||coalesce(jsonb_agg(cp7_reminder_native.condition_policy(x.value,policies,p_at)order by x.value->>'key'),'[]'::jsonb)into rows
  from jsonb_array_elements(coalesce(other->'rows','[]'::jsonb))x;
 if jsonb_array_length(rows)>15000 or octet_length(rows::text)>8000000 or(select count(distinct x->>'key')from jsonb_array_elements(rows)x)<>jsonb_array_length(rows)then
  raise exception 'CP7_RULE_CONDITION_SCOPE_INCOMPLETE';end if;
 if exists(select 1 from jsonb_array_elements(rows)x where not cp7_reminder_native.condition_domain_access(x->>'domain'))then
  raise exception using errcode='42501',message='CP7_RULE_CONDITION_DOMAIN_CHANGED';end if;
 select coalesce(jsonb_agg(x||jsonb_build_object('condition_hash',cp7_reminder_native.staged_live_hash(x),'kind','LIVE')order by x->>'key'),'[]'::jsonb)into rows
  from jsonb_array_elements(rows)x;
 return jsonb_build_object('rows',rows,'coverage',jsonb_build_object(
  'sales_ar',case when ar is null then case when p_domain is null or p_domain='SALES_AR'then'EXCLUDED_BY_CURRENT_RIGHTS'else'NOT_READ'end else'COMPLETE_NATIVE_DOCUMENT_SCOPE'end,
  'material_ap',case when ap is null then case when p_domain is null or p_domain='MATERIAL_AP'then'EXCLUDED_BY_CURRENT_RIGHTS'else'NOT_READ'end else'COMPLETE_NATIVE_DOCUMENT_SCOPE'end)
  ||coalesce(other->'coverage','{}'::jsonb));
end $$;
create function cp7_reminder_native.staged_obligations(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb:=cp7_reminder_native.staged_access(p_run);at timestamptz:=clock_timestamp();policies jsonb;o jsonb;
begin
 policies:=cp7_reminder_native.staged_policy_rows(p_run);
 o:=cp7_reminder_native.staged_obligation_rows(null,policies,at);
 if erp.get_my_access_v1()is distinct from a->'access'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.reminder-obligations.v2','actor_scope_id',auth.uid(),'run_id',p_run,
  'rows',o->'rows','coverage',o->'coverage','total',jsonb_array_length(o->'rows'),'read_at',at,'basis','READ_NOW_NOT_FROM_SNAPSHOT',
  'external_delivery_enabled',false,'sent',false);
end $$;

-- -------------------------------------------------------------- recheck --
-- The verdict of one condition now. Snapshot conditions (production, fabric,
-- accessory) compare the snapshot with the target read live:
--   need_now = need at the snapshot minus any increase of (finished stock +
--   WIP of the model and size) since the snapshot (plan v2's rule; a decrease
--   never adds); 0 is RESOLVED_NOW. A product, production policy or plan of
--   the target changed since the snapshot needs a new analysis
--   (CHANGED_REVIEW_REQUIRED); WIP not known is UNKNOWN_NOW. A fabric need is
--   held back when its production need fell or its material moved, was
--   ordered or planned since the snapshot. Receivables and payables are read
--   now: RESOLVED (paid/settled) is RESOLVED_NOW, not due is NO_LONGER_DUE,
--   unknown is UNKNOWN_NOW, a missing row NOT_FOUND_NOW and a still open row
--   whose facts differ from the hash the user saw is CONDITION_CHANGED.
-- STILL_OPEN only when the policy threshold is reached. Nothing is written.
create function cp7_reminder_native.staged_verdict(p_run uuid,p_key text,p_hash text,policies jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare c cp7_reminder_native.staged_conditions%rowtype;s cp7_reminder_native.staged_condition_sets%rowtype;d text;
 now_t jsonb;sn jsonb;lv jsonb;lp jsonb;need_snap numeric;fg_snap numeric;wip_snap numeric;fg_now numeric;wip_now numeric;increase numeric;need_now numeric;
 verdict text;reason text;numbers jsonb;pb jsonb;threshold numeric;unit text;value numeric;r jsonb;o jsonb;at timestamptz;
begin
 d:=cp7_reminder_native.condition_domain(p_key);
 if d in('PRODUCTION','ACCESSORY','FABRIC')then
  select *into s from cp7_reminder_native.staged_condition_sets x where x.run_id=p_run;
  if s.run_id is null or s.state<>'DONE'then raise exception using errcode='40001',message='CP7_REMINDER_V2_CONDITIONS_NOT_READY';end if;
  select *into c from cp7_reminder_native.staged_conditions x where x.run_id=p_run and x.key=p_key;
  if c.run_id is null then raise exception using errcode='42501',message='CP7_REMINDER_V2_CONDITION_UNAVAILABLE';end if;
  if p_hash is not null and p_hash<>c.condition_hash then raise exception using errcode='40001',message='CP7_REMINDER_V2_CONDITION_CHANGED',
   detail=jsonb_build_object('condition_key',p_key,'presented_hash',p_hash,'snapshot_hash',c.condition_hash)::text;end if;
  pb:=cp7_reminder_native.policy_resolve(policies,c.rule_id,c.target_key);
  now_t:=cp7_reminder_native.staged_target_now(p_run,c.target_key,case when c.rule_id='FABRIC_NEED'then c.material_key end);
  sn:=now_t->'snapshot';lv:=now_t->'live';lp:=case when jsonb_array_length(lv->'products')=1 then lv->'products'->0 end;
  need_snap:=(sn->>'need_pcs')::numeric;fg_snap:=(sn->>'available_fg_pcs')::numeric;wip_snap:=(sn->>'wip_model_size_pcs')::numeric;
  fg_now:=(lv->>'fg_pcs')::numeric;wip_now:=case when lv->'wip'->>'status'='COMPLETE'then(lv->'wip'->>'pcs')::numeric end;
  if need_snap is not null and fg_snap is not null and wip_snap is not null and fg_now is not null and wip_now is not null then
   increase:=greatest(0,(fg_now+wip_now)-(fg_snap+wip_snap));need_now:=greatest(0,need_snap-increase);end if;
  if need_now=0 then verdict:='RESOLVED_NOW';reason:='FINISHED_STOCK_AND_WIP_COVER_THE_NEED_NOW';
  elsif lp is null or lp->'is_active'is distinct from'true'::jsonb or sn->'product'is null
   or lp->>'model_id'is distinct from sn->'product'->>'model_id'or lp->>'size_id'is distinct from sn->'product'->>'size_id'then
   verdict:='CHANGED_REVIEW_REQUIRED';reason:='PRODUCT_CHANGED_AFTER_SNAPSHOT';
  elsif lv->>'policy_state'is distinct from'ACTIVE'or lv->>'policy_quality'is distinct from'KNOWN'then
   verdict:='CHANGED_REVIEW_REQUIRED';reason:='PRODUCTION_POLICY_CHANGED_AFTER_SNAPSHOT';
  elsif(now_t->>'target_plans_after')::bigint>0 then verdict:='CHANGED_REVIEW_REQUIRED';reason:='TARGET_PLANNED_AFTER_SNAPSHOT';
  elsif need_snap is null then verdict:='UNKNOWN_NOW';reason:='SNAPSHOT_NEED_UNKNOWN';
  elsif wip_snap is null then verdict:='UNKNOWN_NOW';reason:='SNAPSHOT_WIP_NOT_COMPLETE';
  elsif wip_now is null then verdict:='UNKNOWN_NOW';reason:=coalesce(lv->'wip'->>'reason','WIP_NOW_UNKNOWN');
  elsif c.rule_id='PRODUCTION_GAP'then
   threshold:=(pb->'policy'->'config'->>'threshold_value')::numeric;
   if threshold is not null and need_now<threshold then verdict:='BELOW_THRESHOLD_NOW';reason:='NEED_NOW_BELOW_SELECTED_THRESHOLD';
   else verdict:='STILL_OPEN';reason:='NEED_STILL_OPEN_NOW';end if;
  elsif c.rule_id='FABRIC_NEED'then
   if need_now<need_snap then verdict:='CHANGED_REVIEW_REQUIRED';reason:='PRODUCTION_NEED_FELL_AFTER_SNAPSHOT';
   elsif now_t->'material'is null then verdict:='UNKNOWN_NOW';reason:='FABRIC_MATERIAL_NOT_KNOWN';
   elsif(now_t->'material'->>'movements_after')::bigint>0 or(now_t->'material'->>'commitments_after')::bigint>0 then
    verdict:='CHANGED_REVIEW_REQUIRED';reason:='FABRIC_MATERIAL_CHANGED_AFTER_SNAPSHOT';
   elsif c.snapshot_state<>'ACTIVE'then verdict:='UNKNOWN_NOW';reason:='FABRIC_NEED_NOT_KNOWN_AT_SNAPSHOT';
   else
    value:=(c.value->>'value')::numeric;unit:=c.value->>'unit';threshold:=(pb->'policy'->'config'->>'threshold_value')::numeric;
    if threshold is not null and pb->'policy'->'config'->>'threshold_unit'is distinct from unit then verdict:='UNKNOWN_NOW';reason:='UNIT_REVIEW_REQUIRED';
    elsif threshold is not null and value<threshold then verdict:='BELOW_THRESHOLD_NOW';reason:='NEED_BELOW_SELECTED_THRESHOLD';
    else verdict:='STILL_OPEN';reason:='FABRIC_NEED_UNCHANGED_SINCE_SNAPSHOT';end if;
   end if;
  else verdict:='UNKNOWN_NOW';reason:='ACCESSORY_NEED_NOT_RECHECKED_LIVE';end if;
  numbers:=jsonb_build_object('need_snapshot_pcs',sn->'need_pcs','fg_snapshot_pcs',sn->'available_fg_pcs','wip_snapshot_pcs',sn->'wip_model_size_pcs',
   'fg_now_pcs',lv->'fg_pcs','wip_now_pcs',lv->'wip'->'pcs','wip_status_now',lv->'wip'->'status','increase_pcs',trim_scale(increase)::text,
   'need_now_pcs',trim_scale(need_now)::text,'target_plans_after',now_t->'target_plans_after','material',now_t->'material',
   'snapshot_value',c.value->'value','snapshot_unit',c.value->'unit','threshold',pb->'policy'->'config'->'threshold_value');
  return jsonb_build_object('condition_key',c.key,'rule_id',c.rule_id,'kind','SNAPSHOT','label',c.label,'target_key',c.target_key,
   'snapshot_state',c.snapshot_state,'condition_hash',c.condition_hash,'data_as_of',s.data_as_of,'checked_at',now_t->'checked_at',
   'verdict',verdict,'reason',reason,'numbers',numbers,'policy_binding',pb,'row',cp7_reminder_native.staged_row(c,s.data_as_of));
 end if;
 at:=clock_timestamp();o:=cp7_reminder_native.staged_obligation_rows(d,policies,at);
 select x into r from jsonb_array_elements(o->'rows')x where x->>'key'=p_key;
 if r is null then verdict:='NOT_FOUND_NOW';reason:='CONDITION_NOT_IN_CURRENT_SOURCE';
 elsif r->>'state'='RESOLVED'then verdict:='RESOLVED_NOW';reason:=coalesce(r->>'reason','RESOLVED');
 elsif r->>'state'='NO_CURRENT_GAP'then verdict:='NO_LONGER_DUE';reason:=coalesce(r->>'reason','NO_CURRENT_GAP');
 elsif r->>'state'<>'ACTIVE'then verdict:='UNKNOWN_NOW';reason:=coalesce(r->>'reason','DATA_REVIEW');
 elsif p_hash is not null and r->>'condition_hash'<>p_hash then verdict:='CONDITION_CHANGED';reason:='OPEN_CONDITION_FACTS_CHANGED';
 elsif r->'value'->>'value'is null then verdict:='UNKNOWN_NOW';reason:='DAYS_OVERDUE_UNKNOWN';
 else
  pb:=r->'policy_binding';threshold:=(pb->'policy'->'config'->>'threshold_value')::numeric;value:=(r->'value'->>'value')::numeric;
  if threshold is not null and value<threshold then verdict:='BELOW_THRESHOLD_NOW';reason:='DAYS_OVERDUE_BELOW_SELECTED_THRESHOLD';
  else verdict:='STILL_OPEN';reason:='OBLIGATION_STILL_OPEN_NOW';end if;
 end if;
 numbers:=jsonb_build_object('days_overdue',r->'value'->'value','remaining_idr',r->'financial_source'->'remaining'->'value',
  'recorded_due_date',r->'financial_source'->'recorded_due_date','due_basis',r->'financial_source'->'document'->'due_basis',
  'presented_hash',p_hash,'current_hash',r->'condition_hash','state_now',r->'state');
 return jsonb_build_object('condition_key',p_key,'rule_id',coalesce(r->>'rule_id',case when p_key like'AR_DUE:%'then'AR_DUE'else'AP_DUE'end),'kind','LIVE',
  'label',r->>'label','target_key',null,'snapshot_state',null,'condition_hash',r->'condition_hash','data_as_of',null,'checked_at',at,
  'verdict',verdict,'reason',reason,'numbers',numbers,'policy_binding',coalesce(r->'policy_binding',cp7_reminder_native.policy_resolve(policies,
   case when p_key like'AR_DUE:%'then'AR_DUE'else'AP_DUE'end,null)),'row',r);
end $$;
-- Read-only recheck for the screen: the verdict now, not recorded.
create function cp7_reminder_native.staged_recheck(p_run uuid,p_condition text)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;v jsonb;
begin
 if p_condition is null or length(p_condition)>400 then raise exception 'CP7_REMINDER_V2_PAYLOAD';end if;
 a:=cp7_reminder_native.staged_access(p_run);
 if not cp7_reminder_native.condition_domain_access(cp7_reminder_native.condition_domain(p_condition))then
  raise exception using errcode='42501',message='CP7_LOCAL_CONDITION_DOMAIN_DENIED';end if;
 v:=cp7_reminder_native.staged_verdict(p_run,p_condition,null,cp7_reminder_native.staged_policy_rows(p_run));
 if erp.get_my_access_v1()is distinct from a->'access'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.reminder-recheck.v2','actor_scope_id',auth.uid(),'run_id',p_run)||(v-'row')
  ||jsonb_build_object('recorded',false,'external_delivery_enabled',false,'sent',false);
end $$;

-- ------------------------------------------------------------- commands --
-- The preview text: what the snapshot said and its time, what the recheck
-- found and when. Never called current data; nothing is sent.
create function cp7_reminder_native.staged_body(v jsonb)returns text
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare n jsonb:=v->'numbers';r jsonb:=v->'row';
begin
 return 'PRATINJAU LOKAL — BELUM DIKIRIM'||chr(10)||case v->>'rule_id'
  when'PRODUCTION_GAP'then'Kebutuhan produksi'when'ACCESSORY_NEED'then'Kebutuhan aksesori'when'FABRIC_NEED'then'Kebutuhan kain'
  when'AR_DUE'then'Piutang jatuh tempo'else'Utang jatuh tempo'end||chr(10)||coalesce(v->>'label','(tanpa label)')||chr(10)||
  case v->>'kind'when'SNAPSHOT'then
   'Data analisis per '||cp7_reminder_native.staged_wib((v->>'data_as_of')::timestamptz)||': '||
   case v->>'rule_id'when'PRODUCTION_GAP'then'kurang '||coalesce(n->>'need_snapshot_pcs','?')||' PCS.'
    else'tambahan dari luar '||coalesce(n->>'snapshot_value','?')||' '||coalesce(n->>'snapshot_unit','')||'.'end||chr(10)||
   'Diperiksa ulang '||cp7_reminder_native.staged_wib((v->>'checked_at')::timestamptz)||': '||
   case v->>'rule_id'when'PRODUCTION_GAP'then'masih kurang sedikitnya '||(n->>'need_now_pcs')||' PCS (stok jadi dan barang dalam proses naik '||
     (n->>'increase_pcs')||' PCS sejak analisis).'
    else'kebutuhan produksi belum turun dan tidak ada gerakan stok, PO, atau rencana potong baru untuk bahan ini sejak analisis.'end
  else
   'Dibaca '||cp7_reminder_native.staged_wib((v->>'checked_at')::timestamptz)||': lewat jatuh tempo '||coalesce(n->>'days_overdue','?')||' hari.'||chr(10)||
   'Sisa tagihan: '||coalesce(n->>'remaining_idr','Belum diketahui')||' IDR'||chr(10)||
   case when left(coalesce(n->>'due_basis',''),5)='RULE_'
    then'Jatuh tempo menurut aturan (pembayaran penerimaan ke jatuh tempo tertua dulu; bukan bukti per invoice): 'else'Jatuh tempo tercatat: 'end||
   coalesce(n->>'recorded_due_date','Belum diketahui')end||chr(10)||
  'Ini pratinjau lokal. Masalah tetap diperiksa dari transaksi ERP.';
end $$;
-- The payload of a v2 command (every one carries the identity hash, so its
-- key set never equals a v1 payload's) and the caller's access over its run.
create function cp7_reminder_native.staged_payload(p jsonb,keys text[],p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;
begin
 if p_request is null or p_lookup is null or jsonb_typeof(p)is distinct from'object'or not(p?&keys)or(select count(*)from jsonb_object_keys(p))<>cardinality(keys)
  or jsonb_typeof(p->'run_id')<>'string'or p->>'run_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'identity_hash')<>'string'or p->>'identity_hash'!~'^[0-9a-f]{64}$'then raise exception 'CP7_REMINDER_V2_PAYLOAD';end if;
 a:=cp7_reminder_native.staged_access((p->>'run_id')::uuid);
 if a->'analysis'->'staged'->>'identity_hash'<>p->>'identity_hash'then raise exception 'CP7_REMINDER_V2_IDENTITY_CHANGED';end if;
 return a;
end $$;
-- Whether a target is in the run now (for a target policy).
create function cp7_reminder_native.staged_policy_scope(a jsonb,p jsonb)returns void
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin
 perform cp7_reminder_native.recheck(a,case p->>'rule_id'when'AR_DUE'then'AR'when'AP_DUE'then'MATERIAL_AP'else null end);
 if a->'access'->'profile'->>'role_code'not in('OWNER','ADMIN')or not erp.has_permission('master.product.manage')then
  raise exception using errcode='42501',message='CP7_RULE_POLICY_MANAGE_DENIED';end if;
 if p->>'scope_kind'='GLOBAL'then
  if p->>'scope_key'<>'*'then raise exception 'CP7_RULE_POLICY_SCOPE';end if;
 elsif p->>'scope_kind'='TARGET'and p->>'rule_id'in('PRODUCTION_GAP','ACCESSORY_NEED','FABRIC_NEED')then
  if not(cp7_reminder_native.staged_authority((p->>'run_id')::uuid,array[p->>'scope_key'])->'targets_present')?(p->>'scope_key')then
   raise exception using errcode='42501',message='CP7_RULE_POLICY_TARGET_UNAVAILABLE';end if;
 else raise exception 'CP7_RULE_POLICY_SCOPE';end if;
end $$;
-- Policy (v1's table, revision rule and lock): a target policy for a target of
-- the staged run. The snapshot need not be current (its time is shown).
create function cp7_reminder_native.staged_policy_command(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare a jsonb;actor uuid:=auth.uid();cached cp7_reminder_native.requests%rowtype;old cp7_reminder_native.rule_policies%rowtype;
 inserted cp7_reminder_native.rule_policies%rowtype;result jsonb;expected bigint;
begin
 a:=cp7_reminder_native.staged_payload(p,array['run_id','identity_hash','rule_id','scope_kind','scope_key','expected_revision','config','reason'],p_request,p_lookup);
 if exists(select 1 from jsonb_each(p)e where e.key<>'config'and jsonb_typeof(e.value)<>'string')
  or p->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'or(p->>'expected_revision')::numeric>9223372036854775806
  or btrim(p->>'reason')=''or length(p->>'reason')>1000 then raise exception 'CP7_RULE_POLICY_PAYLOAD';end if;
 perform cp7_reminder_native.policy_validate(p->>'rule_id',p->'config');expected:=(p->>'expected_revision')::bigint;
 perform cp7_reminder_native.staged_policy_scope(a,p);
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));
 perform cp7_reminder_native.staged_policy_scope(a,p);
 select *into cached from cp7_reminder_native.requests r where r.actor=actor and r.request_id=p_request;
 if found then if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then
  result:=jsonb_build_object('request_id',p_request,'status','NOT_COMMITTED','policy_id',null,'revision',null);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:RULE_POLICY:'||(p->>'rule_id')||':'||(p->>'scope_kind')||':'||(p->>'scope_key'),0));
  perform cp7_reminder_native.staged_policy_scope(a,p);
  select *into old from cp7_reminder_native.rule_policies r where r.rule_id=p->>'rule_id'and r.scope_kind=p->>'scope_kind'
   and r.scope_key=p->>'scope_key'order by r.revision desc limit 1;
  if coalesce(old.revision,0)<>expected then raise exception using errcode='40001',message='CP7_RULE_POLICY_STALE_REVISION';end if;
  insert into cp7_reminder_native.rule_policies(rule_id,scope_kind,scope_key,revision,previous_id,config,reason,created_at,created_by)
   values(p->>'rule_id',p->>'scope_kind',p->>'scope_key',expected+1,old.id,p->'config',p->>'reason',clock_timestamp(),actor)returning *into inserted;
  result:=jsonb_build_object('request_id',p_request,'status','COMMITTED','policy_id',inserted.id,'revision',inserted.revision::text);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 perform cp7_reminder_native.staged_policy_scope(a,p);
 return jsonb_build_object('result',result);
end $$;
-- Destination (v1's local_bindings: one per actor, revision rule and lock).
create function cp7_reminder_native.staged_binding_command(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare a jsonb;actor uuid:=auth.uid();old cp7_reminder_native.local_bindings%rowtype;inserted cp7_reminder_native.local_bindings%rowtype;
 cached cp7_reminder_native.requests%rowtype;r text;result jsonb;expected bigint;
begin
 a:=cp7_reminder_native.staged_payload(p,array['run_id','identity_hash','expected_revision','enabled','label','environment','rules','reason'],p_request,p_lookup);
 if jsonb_typeof(p->'enabled')is distinct from'boolean'or p->>'environment'is distinct from'LOCAL_TEST_SINK'
  or jsonb_typeof(p->'rules')is distinct from'array'or jsonb_array_length(p->'rules')not between 1 and 5
  or exists(select 1 from jsonb_array_elements(p->'rules')x where jsonb_typeof(x)<>'string'or x#>>'{}'not in('PRODUCTION_GAP','ACCESSORY_NEED','FABRIC_NEED','AR_DUE','AP_DUE'))
  or(select count(distinct x)from jsonb_array_elements(p->'rules')x)<>jsonb_array_length(p->'rules')
  or exists(select 1 from jsonb_each(p)e where e.key not in('enabled','rules')and jsonb_typeof(e.value)<>'string')
  or btrim(p->>'label')=''or length(p->>'label')>120 or btrim(p->>'reason')=''or length(p->>'reason')>1000
  or p->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'or(p->>'expected_revision')::numeric>9223372036854775806 then raise exception 'CP7_LOCAL_BINDING_PAYLOAD';end if;
 expected:=(p->>'expected_revision')::bigint;
 for r in select jsonb_array_elements_text(p->'rules')loop perform cp7_reminder_native.local_recheck(a,r);end loop;
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));perform cp7_reminder_native.recheck(a);
 select *into cached from cp7_reminder_native.requests q where q.actor=actor and q.request_id=p_request;
 if found then if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then result:=jsonb_build_object('request_id',p_request,'status','NOT_COMMITTED','binding_id',null,'revision',null);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:LOCAL_BINDING:'||actor::text,0));perform cp7_reminder_native.local_recheck(a);
  for r in select jsonb_array_elements_text(p->'rules')loop perform cp7_reminder_native.local_recheck(a,r);end loop;
  select *into old from cp7_reminder_native.local_bindings q where q.actor=actor order by q.revision desc limit 1;
  if coalesce(old.revision,0)<>expected then raise exception using errcode='40001',message='CP7_LOCAL_BINDING_STALE';end if;
  insert into cp7_reminder_native.local_bindings(actor,revision,previous_id,enabled,label,environment,rules,reason,created_at)
   values(actor,expected+1,old.id,(p->>'enabled')::boolean,p->>'label','LOCAL_TEST_SINK',p->'rules',p->>'reason',clock_timestamp())returning *into inserted;
  result:=jsonb_build_object('request_id',p_request,'status','COMMITTED','binding_id',inserted.id,'revision',inserted.revision::text);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 perform cp7_reminder_native.local_recheck(a);
 for r in select jsonb_array_elements_text(p->'rules')loop perform cp7_reminder_native.local_recheck(a,r);end loop;
 return jsonb_build_object('result',result);
end $$;
-- The last local capture of this condition in this episode (v2 claims), and
-- of the same condition in v1's local claims (any episode; v1 cannot see v2).
create function cp7_reminder_native.staged_last_local(p_actor uuid,p_key text,p_episode uuid,p_except uuid)returns timestamptz
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select max(t)from(
  select q.finished_at t from cp7_reminder_native.staged_claims q where q.actor=p_actor and q.condition_key=p_key and q.episode_id=p_episode
   and q.status='LOCAL_SINK_CAPTURED'and q.id is distinct from p_except
  union all select s.created_at from cp7_reminder_native.staged_claim_resolutions s join cp7_reminder_native.staged_claims q on q.id=s.claim_id
   where q.actor=p_actor and q.condition_key=p_key and q.episode_id=p_episode and s.outcome='CAPTURE_CONFIRMED'and q.id is distinct from p_except
  union all select q.finished_at from cp7_reminder_native.local_claims q where q.actor=p_actor and q.condition_key=p_key and q.status='LOCAL_SINK_CAPTURED'
  union all select s.created_at from cp7_reminder_native.local_resolutions s join cp7_reminder_native.local_claims q on q.id=s.claim_id
   where q.actor=p_actor and q.condition_key=p_key and s.outcome='CAPTURE_CONFIRMED')x
$$;
-- Record a recheck, and move the shared episode: still open opens one (when
-- none is active), resolved now resolves the active one.
create function cp7_reminder_native.staged_record(v jsonb,p_run uuid,p_identity text,p_request uuid,p_phase text,p_policy uuid,p_open boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare e cp7_reminder_native.staged_episodes%rowtype;prev cp7_reminder_native.staged_episodes%rowtype;id uuid;
begin
 select *into e from cp7_reminder_native.staged_episodes x where x.condition_key=v->>'condition_key'and x.state='ACTIVE'for update;
 if v->>'verdict'='RESOLVED_NOW'and e.id is not null then
  update cp7_reminder_native.staged_episodes set state='RESOLVED',resolved_at=(v->>'checked_at')::timestamptz where staged_episodes.id=e.id returning *into e;
 elsif v->>'verdict'='STILL_OPEN'and e.id is null and p_open then
  select *into prev from cp7_reminder_native.staged_episodes x where x.condition_key=v->>'condition_key'order by x.episode_number desc limit 1;
  insert into cp7_reminder_native.staged_episodes(condition_key,rule_id,episode_number,previous_id,state,opened_at)
   values(v->>'condition_key',v->>'rule_id',coalesce(prev.episode_number,0)+1,prev.id,'ACTIVE',(v->>'checked_at')::timestamptz)returning *into e;
 end if;
 insert into cp7_reminder_native.staged_rechecks(actor,request_id,run_id,identity_hash,condition_key,rule_id,kind,phase,data_as_of,checked_at,
  verdict,reason,numbers,policy_id,episode_id,created_at)
 values(auth.uid(),p_request,p_run,p_identity,v->>'condition_key',v->>'rule_id',v->>'kind',p_phase,(v->>'data_as_of')::timestamptz,
  (v->>'checked_at')::timestamptz,v->>'verdict',v->>'reason',v->'numbers',p_policy,e.id,clock_timestamp())returning staged_rechecks.id into id;
 return jsonb_build_object('recheck_id',id,'episode_id',e.id,'episode_state',e.state);
end $$;
create function cp7_reminder_native.staged_recheck_json(p_id uuid)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('id',r.id,'request_id',r.request_id,'run_id',r.run_id,'identity_hash',r.identity_hash,'condition_key',r.condition_key,
  'rule_id',r.rule_id,'kind',r.kind,'phase',r.phase,'data_as_of',r.data_as_of,'checked_at',r.checked_at,'verdict',r.verdict,'reason',r.reason,
  'numbers',r.numbers,'policy_id',r.policy_id,'episode_id',r.episode_id,'created_at',r.created_at)
 from cp7_reminder_native.staged_rechecks r where r.id=p_id
$$;
create function cp7_reminder_native.staged_claim_json(p_id uuid)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('id',q.id,'run_id',q.run_id,'identity_hash',q.identity_hash,'status',q.status,'occurrence_key',q.occurrence_key,
  'binding_id',q.binding_id,'environment',q.environment,'condition_key',q.condition_key,'rule_id',q.rule_id,'kind',q.kind,
  'condition_hash',q.condition_hash,'episode_id',q.episode_id,'policy_id',q.policy_id,'recheck_id',q.recheck_id,'finish_recheck_id',q.finish_recheck_id,
  'body_sha256',q.body_sha256,'body',q.body,'fence',q.fence,'created_at',q.created_at,'finished_at',q.finished_at,'reason',q.reason,
  'resolution',(select jsonb_build_object('id',s.id,'outcome',s.outcome,'reason',s.reason,'created_at',s.created_at)
   from cp7_reminder_native.staged_claim_resolutions s where s.claim_id=q.id))
 from cp7_reminder_native.staged_claims q where q.id=p_id
$$;
-- Claim a local preview of one condition. After the request, destination and
-- episode locks (v1's order), the condition as the user saw it must still be
-- the one presented (snapshot: active at the snapshot, same hash), the policy
-- must allow a preview now, and the condition is rechecked now. Any verdict
-- but STILL_OPEN is recorded as the request's result and nothing is claimed
-- (NOT_SENT); STILL_OPEN claims one preview per episode and policy.
create function cp7_reminder_native.staged_claim(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare actor uuid:=auth.uid();a jsonb;cached cp7_reminder_native.requests%rowtype;binding cp7_reminder_native.local_bindings%rowtype;
 claim cp7_reminder_native.staged_claims%rowtype;c cp7_reminder_native.staged_conditions%rowtype;result jsonb;policies jsonb;pb jsonb;
 timing jsonb;v jsonb;rec jsonb;rule text;key text;run uuid;policy_id uuid;occurrence text;attempt bigint;body text;last_local timestamptz;episode uuid;d text;
begin
 a:=cp7_reminder_native.staged_payload(p,array['run_id','identity_hash','condition_key','condition_hash','binding_id'],p_request,p_lookup);
 if exists(select 1 from jsonb_each(p)e where jsonb_typeof(e.value)<>'string')or p->>'condition_hash'!~'^[0-9a-f]{64}$'
  or p->>'binding_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'or length(p->>'condition_key')>400 then raise exception 'CP7_REMINDER_V2_PAYLOAD';end if;
 key:=p->>'condition_key';run:=(p->>'run_id')::uuid;d:=cp7_reminder_native.condition_domain(key);
 rule:=case d when'PRODUCTION'then'PRODUCTION_GAP'when'ACCESSORY'then'ACCESSORY_NEED'when'FABRIC'then'FABRIC_NEED'
  else case when key like'AR_DUE:%'then'AR_DUE'else'AP_DUE'end end;
 perform cp7_reminder_native.local_recheck(a,rule,key);
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));perform cp7_reminder_native.recheck(a);
 select *into cached from cp7_reminder_native.requests q where q.actor=actor and q.request_id=p_request;
 if found then if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then result:=jsonb_build_object('request_id',p_request,'status','NOT_COMMITTED','outcome',null,'verdict',null,'recheck_id',null,'claim_id',null,'fence',null);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:LOCAL_BINDING:'||actor::text,0));perform cp7_reminder_native.recheck(a);
  select *into binding from cp7_reminder_native.local_bindings q where q.actor=actor order by q.revision desc limit 1;
  if binding.id is null or binding.id::text<>p->>'binding_id'or not binding.enabled then raise exception using errcode='40001',message='CP7_LOCAL_BINDING_UNAVAILABLE';end if;
  if not(binding.rules?rule)then raise exception using errcode='42501',message='CP7_LOCAL_CONDITION_UNAVAILABLE';end if;
  if d in('PRODUCTION','ACCESSORY','FABRIC')then
   if not exists(select 1 from cp7_reminder_native.staged_condition_sets x where x.run_id=run and x.state='DONE')then
    raise exception using errcode='40001',message='CP7_REMINDER_V2_CONDITIONS_NOT_READY';end if;
   select *into c from cp7_reminder_native.staged_conditions x where x.run_id=run and x.key=key;
   if c.run_id is null then raise exception using errcode='42501',message='CP7_REMINDER_V2_CONDITION_UNAVAILABLE';end if;
   if c.condition_hash<>p->>'condition_hash'then raise exception using errcode='40001',message='CP7_REMINDER_V2_CONDITION_CHANGED',
    detail=jsonb_build_object('condition_key',key,'presented_hash',p->>'condition_hash','snapshot_hash',c.condition_hash)::text;end if;
   if c.snapshot_state<>'ACTIVE'then raise exception using errcode='40001',message='CP7_REMINDER_V2_NOT_ACTIVE_IN_SNAPSHOT';end if;
  end if;
  perform cp7_reminder_native.local_recheck(a,rule,key);
  perform pg_advisory_xact_lock(hashtextextended('CP7:RULE_EPISODES:CURRENT_SOURCE',0));perform cp7_reminder_native.recheck(a);
  perform cp7_reminder_native.local_recheck(a,rule,key);
  policies:=cp7_reminder_native.staged_policy_rows(run);
  pb:=cp7_reminder_native.policy_resolve(policies,rule,case when d in('PRODUCTION','ACCESSORY','FABRIC')then c.target_key end);
  policy_id:=(pb->'policy'->>'policy_id')::uuid;
  select x.id into episode from cp7_reminder_native.staged_episodes x where x.condition_key=key and x.state='ACTIVE';
  last_local:=cp7_reminder_native.staged_last_local(actor,key,episode,null);
  timing:=cp7_reminder_native.policy_timing(case when pb->'policy'is null or pb->'policy'='null'::jsonb then null else pb->'policy'->'config'end,clock_timestamp(),last_local);
  if timing->>'status'<>'READY'then raise exception using errcode='40001',message='CP7_LOCAL_COOLDOWN_OR_QUIET',detail=timing::text;end if;
  -- v1 local claims of this condition still unresolved (sent or not unknown):
  -- no second copy from v2 either.
  if exists(select 1 from cp7_reminder_native.local_claims q where q.actor=actor and q.condition_key=key and q.status in('CLAIMED','UNKNOWN')
   and not exists(select 1 from cp7_reminder_native.local_resolutions s where s.claim_id=q.id))then
   raise exception using errcode='40001',message='CP7_LOCAL_AMBIGUOUS_EPISODE_NO_NEW_OCCURRENCE';end if;
  -- The recheck now, after the last lock.
  v:=cp7_reminder_native.staged_verdict(run,key,p->>'condition_hash',policies);
  if v->>'verdict'='CONDITION_CHANGED'then raise exception using errcode='40001',message='CP7_REMINDER_V2_CONDITION_CHANGED',detail=(v->'numbers')::text;end if;
  rec:=cp7_reminder_native.staged_record(v,run,p->>'identity_hash',p_request,'CLAIM',policy_id,true);
  if v->>'verdict'<>'STILL_OPEN'then
   result:=jsonb_build_object('request_id',p_request,'status','COMMITTED','outcome','NOT_SENT','verdict',v->>'verdict','recheck_id',rec->>'recheck_id','claim_id',null,'fence',null);
  else
   episode:=(rec->>'episode_id')::uuid;
   -- A preview confirmed not captured, or suppressed by its finish recheck,
   -- was never captured: it does not use up the episode. A new request may
   -- then claim a new preview with the facts as they are now.
   select count(*)into attempt from cp7_reminder_native.staged_claims q where q.actor=actor and q.binding_id=binding.id and q.condition_key=key
    and q.episode_id=episode and q.policy_id=policy_id and(q.status='SUPPRESSED'or exists(select 1 from cp7_reminder_native.staged_claim_resolutions s
     where s.claim_id=q.id and s.outcome='NOT_CAPTURED_CONFIRMED'));
   occurrence:=encode(pg_catalog.sha256(convert_to(jsonb_build_object('binding',binding.id,'environment','LOCAL_TEST_SINK',
    'condition',key,'episode',episode,'policy',policy_id,'reviewed_non_capture_count',attempt::text)::text,'UTF8')),'hex');
   select *into claim from cp7_reminder_native.staged_claims q where q.actor=actor and q.binding_id=binding.id and q.environment='LOCAL_TEST_SINK'and q.occurrence_key=occurrence;
   if claim.id is null then
    if exists(select 1 from cp7_reminder_native.staged_claims q where q.actor=actor and q.condition_key=key and q.episode_id=episode
     and q.status in('CLAIMED','UNKNOWN')and not exists(select 1 from cp7_reminder_native.staged_claim_resolutions s where s.claim_id=q.id))then
     raise exception using errcode='40001',message='CP7_LOCAL_AMBIGUOUS_EPISODE_NO_NEW_OCCURRENCE';end if;
    body:=cp7_reminder_native.staged_body(v);
    insert into cp7_reminder_native.staged_claims(actor,run_id,identity_hash,binding_id,condition_key,rule_id,kind,condition_hash,episode_id,occurrence_key,
     environment,policy_id,recheck_id,status,body,body_sha256,created_at)
    values(actor,run,p->>'identity_hash',binding.id,key,rule,v->>'kind',p->>'condition_hash',episode,occurrence,'LOCAL_TEST_SINK',policy_id,
     (rec->>'recheck_id')::uuid,'CLAIMED',body,encode(pg_catalog.sha256(convert_to(body,'UTF8')),'hex'),clock_timestamp())returning *into claim;
   end if;
   result:=jsonb_build_object('request_id',p_request,'status','COMMITTED','outcome','CLAIMED','verdict','STILL_OPEN','recheck_id',rec->>'recheck_id',
    'claim_id',claim.id,'fence',claim.fence);
  end if;
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 perform cp7_reminder_native.recheck(a);perform cp7_reminder_native.local_recheck(a,rule,key);
 return jsonb_build_object('result',result);
end $$;
-- Finish a claimed preview. After the same locks the condition is rechecked
-- again: a condition no longer open now (or changed, or a destination or
-- policy that no longer allows it) suppresses the preview instead of
-- recording it; the outcome is never retried by a worker.
create function cp7_reminder_native.staged_finish(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare actor uuid:=auth.uid();a jsonb;cached cp7_reminder_native.requests%rowtype;binding cp7_reminder_native.local_bindings%rowtype;
 claim cp7_reminder_native.staged_claims%rowtype;result jsonb;outcome text;reason text;policies jsonb;pb jsonb;timing jsonb;v jsonb;rec jsonb;target text;
begin
 a:=cp7_reminder_native.staged_payload(p,array['run_id','identity_hash','claim_id','fence','outcome'],p_request,p_lookup);
 if exists(select 1 from jsonb_each(p)e where jsonb_typeof(e.value)<>'string')or p->>'outcome'not in('LOCAL_CAPTURE','UNKNOWN')
  or p->>'claim_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'or p->>'fence'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  then raise exception 'CP7_LOCAL_OUTCOME_PAYLOAD';end if;
 perform cp7_reminder_native.local_recheck(a);
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));perform cp7_reminder_native.recheck(a);
 select *into cached from cp7_reminder_native.requests q where q.actor=actor and q.request_id=p_request;
 if found then if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then result:=jsonb_build_object('request_id',p_request,'status','NOT_COMMITTED','claim_id',p->'claim_id','local_status',null,'recheck_id',null);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:LOCAL_BINDING:'||actor::text,0));perform cp7_reminder_native.recheck(a);
  perform pg_advisory_xact_lock(hashtextextended('CP7:RULE_EPISODES:CURRENT_SOURCE',0));perform cp7_reminder_native.recheck(a);
  select *into claim from cp7_reminder_native.staged_claims q where q.id=(p->>'claim_id')::uuid and q.actor=actor for update;
  if claim.id is null or claim.fence::text<>p->>'fence'or claim.run_id::text<>p->>'run_id'or claim.identity_hash<>p->>'identity_hash'then
   raise exception using errcode='42501',message='CP7_LOCAL_FENCE_DENIED';end if;
  perform cp7_reminder_native.local_recheck(a,claim.rule_id,claim.condition_key);
  if claim.status='CLAIMED'then
   select *into binding from cp7_reminder_native.local_bindings q where q.actor=actor order by q.revision desc limit 1;
   policies:=cp7_reminder_native.staged_policy_rows(claim.run_id);
   v:=cp7_reminder_native.staged_verdict(claim.run_id,claim.condition_key,case when claim.kind='LIVE'then claim.condition_hash end,policies);
   target:=v->>'target_key';pb:=cp7_reminder_native.policy_resolve(policies,claim.rule_id,target);
   rec:=cp7_reminder_native.staged_record(v,claim.run_id,claim.identity_hash,p_request,'FINISH',(pb->'policy'->>'policy_id')::uuid,false);
   timing:=cp7_reminder_native.policy_timing(case when pb->'policy'is null or pb->'policy'='null'::jsonb then null else pb->'policy'->'config'end,
    clock_timestamp(),cp7_reminder_native.staged_last_local(actor,claim.condition_key,claim.episode_id,claim.id));
   if binding.id is distinct from claim.binding_id or not coalesce(binding.enabled,false)or not(binding.rules?claim.rule_id)then
    outcome:='SUPPRESSED';reason:='BINDING_CHANGED_OR_DISABLED';
   elsif v->>'verdict'<>'STILL_OPEN'then outcome:='SUPPRESSED';reason:='RECHECK_'||(v->>'verdict');
   elsif(pb->'policy'->>'policy_id')::uuid is distinct from claim.policy_id then outcome:='SUPPRESSED';reason:='POLICY_CHANGED';
   elsif not exists(select 1 from cp7_reminder_native.staged_episodes q where q.id=claim.episode_id and q.state='ACTIVE')then
    outcome:='SUPPRESSED';reason:='EPISODE_NO_LONGER_ACTIVE';
   elsif timing->>'status'<>'READY'then outcome:='SUPPRESSED';reason:='CURRENT_COOLDOWN_OR_QUIET';
   elsif p->>'outcome'='UNKNOWN'then outcome:='UNKNOWN';reason:='LOCAL_OUTCOME_UNCERTAIN_NO_AUTOMATIC_RESEND';
   else outcome:='LOCAL_SINK_CAPTURED';reason:='EXPLICIT_LOCAL_CONTRACT_CAPTURE_NOT_EXTERNAL_DELIVERY';end if;
   update cp7_reminder_native.staged_claims q set status=outcome,reason=reason,finished_at=clock_timestamp(),finish_recheck_id=(rec->>'recheck_id')::uuid
    where q.id=claim.id returning *into claim;
  end if;
  result:=jsonb_build_object('request_id',p_request,'status','COMMITTED','claim_id',claim.id,'local_status',claim.status,'recheck_id',claim.finish_recheck_id);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 select *into claim from cp7_reminder_native.staged_claims q where q.id=(p->>'claim_id')::uuid and q.actor=actor;
 if claim.id is null or claim.fence::text<>p->>'fence'then raise exception using errcode='42501',message='CP7_LOCAL_FENCE_DENIED';end if;
 perform cp7_reminder_native.local_recheck(a,claim.rule_id,claim.condition_key);perform cp7_reminder_native.recheck(a);
 return jsonb_build_object('result',result);
end $$;
-- An UNKNOWN preview resolved by the person who claimed it (v1's rule).
create function cp7_reminder_native.staged_resolution(p jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare actor uuid:=auth.uid();a jsonb;claim cp7_reminder_native.staged_claims%rowtype;saved cp7_reminder_native.staged_claim_resolutions%rowtype;
 cached cp7_reminder_native.requests%rowtype;result jsonb;
begin
 a:=cp7_reminder_native.staged_payload(p,array['run_id','identity_hash','claim_id','fence','outcome','reason'],p_request,p_lookup);
 if exists(select 1 from jsonb_each(p)e where jsonb_typeof(e.value)<>'string')
  or p->>'outcome'not in('CAPTURE_CONFIRMED','NOT_CAPTURED_CONFIRMED')or btrim(p->>'reason')=''or length(p->>'reason')>1000
  or p->>'claim_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'or p->>'fence'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  then raise exception 'CP7_LOCAL_RESOLUTION_PAYLOAD';end if;
 perform cp7_reminder_native.local_recheck(a);
 perform pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||actor::text||':'||p_request::text,0));perform cp7_reminder_native.recheck(a);
 select *into cached from cp7_reminder_native.requests q where q.actor=actor and q.request_id=p_request;
 if found then if cached.payload<>p then raise exception 'CP7_REMINDER_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then result:=jsonb_build_object('request_id',p_request,'status','NOT_COMMITTED','claim_id',p->'claim_id','resolution_id',null);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:LOCAL_BINDING:'||actor::text,0));perform cp7_reminder_native.recheck(a);
  perform pg_advisory_xact_lock(hashtextextended('CP7:RULE_EPISODES:CURRENT_SOURCE',0));perform cp7_reminder_native.recheck(a);
  select *into claim from cp7_reminder_native.staged_claims q where q.id=(p->>'claim_id')::uuid and q.actor=actor for update;
  if claim.id is null or claim.fence::text<>p->>'fence'or claim.run_id::text<>p->>'run_id'or claim.identity_hash<>p->>'identity_hash'then
   raise exception using errcode='42501',message='CP7_LOCAL_FENCE_DENIED';end if;
  perform cp7_reminder_native.local_recheck(a,claim.rule_id,claim.condition_key);
  if claim.status<>'UNKNOWN'then raise exception using errcode='40001',message='CP7_LOCAL_UNKNOWN_REQUIRED';end if;
  if exists(select 1 from cp7_reminder_native.staged_claim_resolutions q where q.claim_id=claim.id)then raise exception using errcode='40001',message='CP7_LOCAL_ALREADY_RESOLVED';end if;
  insert into cp7_reminder_native.staged_claim_resolutions(claim_id,actor,outcome,reason,created_at)
   values(claim.id,actor,p->>'outcome',p->>'reason',clock_timestamp())returning *into saved;
  result:=jsonb_build_object('request_id',p_request,'status','COMMITTED','claim_id',claim.id,'resolution_id',saved.id);
  insert into cp7_reminder_native.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 select *into claim from cp7_reminder_native.staged_claims q where q.id=(p->>'claim_id')::uuid and q.actor=actor;
 if claim.id is null or claim.fence::text<>p->>'fence'then raise exception using errcode='42501',message='CP7_LOCAL_FENCE_DENIED';end if;
 perform cp7_reminder_native.local_recheck(a,claim.rule_id,claim.condition_key);perform cp7_reminder_native.recheck(a);
 return jsonb_build_object('result',result);
end $$;
-- One command or the lookup of a held request; the reply carries the claim
-- and the recheck it names, read again after the command.
create function cp7_reminder_native.staged_command(p jsonb,p_request uuid,operation text,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare out jsonb;res jsonb;claim jsonb;rec jsonb;
begin
 case operation when'BINDING'then out:=cp7_reminder_native.staged_binding_command(p,p_request,p_lookup);
 when'POLICY'then out:=cp7_reminder_native.staged_policy_command(p,p_request,p_lookup);
 when'CLAIM'then out:=cp7_reminder_native.staged_claim(p,p_request,p_lookup);
 when'OUTCOME'then out:=cp7_reminder_native.staged_finish(p,p_request,p_lookup);
 when'RESOLUTION'then out:=cp7_reminder_native.staged_resolution(p,p_request,p_lookup);
 else raise exception 'CP7_REMINDER_V2_OPERATION';end case;
 res:=out->'result';
 if res->>'claim_id'is not null then
  claim:=cp7_reminder_native.staged_claim_json((res->>'claim_id')::uuid);
  if claim is null or claim->>'id'is null then raise exception using errcode='42501',message='CP7_LOCAL_CLAIM_UNAVAILABLE';end if;
 end if;
 if res->>'recheck_id'is not null then rec:=cp7_reminder_native.staged_recheck_json((res->>'recheck_id')::uuid);end if;
 return jsonb_build_object('contract_version','cp7.reminder-command.v2','actor_scope_id',auth.uid(),'operation',operation,'run_id',p->'run_id',
  'identity_hash',p->'identity_hash','result',res,'claim',claim,'recheck',rec,'external_delivery_enabled',false,'scheduler_enabled',false,'sent',false);
end $$;
-- The reminder workspace of one staged run: the condition set, the policies
-- and destination, and (to a manager) the claims and recorded rechecks of this
-- run, newest first (at most 200 each).
create function cp7_reminder_native.staged_workspace(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare a jsonb:=cp7_reminder_native.staged_access(p_run);actor uuid:=auth.uid();manage boolean;binding cp7_reminder_native.local_bindings%rowtype;
 policies jsonb;allowed jsonb;claims jsonb:='[]';rechecks jsonb:='[]';
begin
 manage:=a->'access'->'profile'->>'role_code'in('OWNER','ADMIN')and erp.has_permission('master.product.manage');
 policies:=cp7_reminder_native.staged_policy_rows(p_run);
 select coalesce(jsonb_agg(rule order by rule),'[]'::jsonb)into allowed from unnest(array['PRODUCTION_GAP','ACCESSORY_NEED','FABRIC_NEED','AR_DUE','AP_DUE'])rule
  where rule not in('AR_DUE','AP_DUE')or erp.has_permission(case rule when'AR_DUE'then'finance.ar.view'else'finance.ap.view'end);
 if manage then
  select *into binding from cp7_reminder_native.local_bindings q where q.actor=actor order by q.revision desc limit 1;
  select coalesce(jsonb_agg(cp7_reminder_native.staged_claim_json(x.id)order by x.created_at desc,x.id),'[]'::jsonb)into claims from(
   select q.id,q.created_at from cp7_reminder_native.staged_claims q where q.actor=actor and q.run_id=p_run
    and cp7_reminder_native.condition_domain_access(cp7_reminder_native.condition_domain(q.condition_key))order by q.created_at desc,q.id limit 200)x;
  select coalesce(jsonb_agg(cp7_reminder_native.staged_recheck_json(x.id)order by x.created_at desc,x.id),'[]'::jsonb)into rechecks from(
   select r.id,r.created_at from cp7_reminder_native.staged_rechecks r where r.actor=actor and r.run_id=p_run
    and cp7_reminder_native.condition_domain_access(cp7_reminder_native.condition_domain(r.condition_key))order by r.created_at desc,r.id limit 200)x;
 end if;
 if erp.get_my_access_v1()is distinct from a->'access'then raise exception using errcode='42501',message='CP7_REMINDER_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.reminder-workspace.v2','actor_scope_id',actor,'run_id',p_run,
  'identity_hash',a->'analysis'->'staged'->'identity_hash','data_as_of',a->'analysis'->'staged'->'data_as_of',
  'conditions',cp7_reminder_native.staged_set_status(p_run),'policies',policies,'allowed_rules',allowed,'manage_allowed',manage,
  'missing_policy','UNCONFIGURED_NOT_ZERO_NOT_DISABLED',
  'binding',case when binding.id is null then null else jsonb_build_object('id',binding.id,'revision',binding.revision::text,'previous_id',binding.previous_id,
   'enabled',binding.enabled,'label',binding.label,'environment',binding.environment,'rules',binding.rules,'reason',binding.reason,'created_at',binding.created_at)end,
  'claims',claims,'rechecks',rechecks,'read_at',clock_timestamp(),'external_delivery_enabled',false,'scheduler_enabled',false,'sent',false);
end $$;

do $$declare r record;begin
 for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='cp7_reminder_native'and p.proname in('guard_staged_set','guard_staged_episode','guard_staged_claim','staged_wib','staged_access',
   'staged_policy_rows','staged_row','staged_live_hash','staged_page_rows','staged_set_status','staged_set_unit','staged_set_step','staged_conditions_read',
   'staged_obligation_rows','staged_obligations','staged_verdict','staged_recheck','staged_body','staged_payload','staged_policy_scope',
   'staged_policy_command','staged_binding_command','staged_last_local','staged_record','staged_recheck_json','staged_claim_json','staged_claim',
   'staged_finish','staged_resolution','staged_command','staged_workspace')loop
  execute format('alter function %s owner to cp7_reminder',r.sig);
  execute format('revoke all on function %s from public,anon,authenticated,service_role',r.sig);
 end loop;
end $$;
grant create on schema public to cp7_reminder;
create function public.erp_cp7_step_reminder_conditions_v2(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.staged_set_step(p_run)$$;
create function public.erp_cp7_read_reminder_conditions_v2(p_query jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.staged_conditions_read(p_query)$$;
create function public.erp_cp7_get_reminder_obligations_v2(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.staged_obligations(p_run)$$;
create function public.erp_cp7_recheck_reminder_v2(p_run uuid,p_condition text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.staged_recheck(p_run,p_condition)$$;
create function public.erp_cp7_get_reminder_workspace_v2(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.staged_workspace(p_run)$$;
create function public.erp_cp7_save_reminder_policy_v2(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.staged_command(p_payload,p_request,'POLICY',false)$$;
create function public.erp_cp7_save_reminder_binding_v2(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.staged_command(p_payload,p_request,'BINDING',false)$$;
create function public.erp_cp7_claim_reminder_v2(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.staged_command(p_payload,p_request,'CLAIM',false)$$;
create function public.erp_cp7_finish_reminder_v2(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.staged_command(p_payload,p_request,'OUTCOME',false)$$;
create function public.erp_cp7_resolve_reminder_claim_v2(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.staged_command(p_payload,p_request,'RESOLUTION',false)$$;
create function public.erp_cp7_get_reminder_request_v2(p_payload jsonb,p_request uuid,p_operation text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.staged_command(p_payload,p_request,p_operation,true)$$;
do $$declare s text;begin
 foreach s in array array['public.erp_cp7_step_reminder_conditions_v2(uuid)','public.erp_cp7_read_reminder_conditions_v2(jsonb)',
  'public.erp_cp7_get_reminder_obligations_v2(uuid)','public.erp_cp7_recheck_reminder_v2(uuid,text)','public.erp_cp7_get_reminder_workspace_v2(uuid)',
  'public.erp_cp7_save_reminder_policy_v2(jsonb,uuid)','public.erp_cp7_save_reminder_binding_v2(jsonb,uuid)','public.erp_cp7_claim_reminder_v2(jsonb,uuid)',
  'public.erp_cp7_finish_reminder_v2(jsonb,uuid)','public.erp_cp7_resolve_reminder_claim_v2(jsonb,uuid)','public.erp_cp7_get_reminder_request_v2(jsonb,uuid,text)']loop
  execute format('alter function %s owner to cp7_reminder',s);
  execute format('revoke all on function %s from public,anon,authenticated,service_role',s);
  execute format('grant execute on function %s to authenticated',s);
 end loop;
end $$;
revoke create on schema public from cp7_reminder;
