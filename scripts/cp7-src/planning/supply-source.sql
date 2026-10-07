-- Authoritative global production source. Batches are source-reading windows,
-- never independent pools or separately normalized balances: a batch's own graph
-- only proves which groups are exhausted (PL-8); every netted balance comes from
-- the one global graph. One stable caller statement supplies every batch the
-- same MVCC snapshot and capture clock.
create schema cp7_supply_native authorization cp7_capture;
revoke all on schema cp7_supply_native from public,anon,authenticated,service_role;

create function cp7_supply_native.merge_facts(a jsonb,b jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare k text;items jsonb;outcome jsonb:='{}';
begin
 if jsonb_typeof(a) is distinct from 'object' or jsonb_typeof(b) is distinct from 'object'
  or (select array_agg(x order by x)from jsonb_object_keys(a)x)
   is distinct from(select array_agg(x order by x)from jsonb_object_keys(b)x)then
  raise exception 'CP7_SUPPLY_FACT_SHAPE';end if;
 for k in select jsonb_object_keys(a)loop
  if jsonb_typeof(a->k)is distinct from 'array'or jsonb_typeof(b->k)is distinct from 'array'then
   raise exception 'CP7_SUPPLY_FACT_SHAPE';end if;
  if exists(select 1 from jsonb_array_elements((a->k)||(b->k))x
   where jsonb_typeof(x->'id')is distinct from 'string'or x->>'id'='')then
   raise exception 'CP7_SUPPLY_FACT_ID';end if;
  if exists(select 1 from jsonb_array_elements((a->k)||(b->k))x
   group by x->>'id'having count(distinct x)>1)then
   raise exception 'CP7_SUPPLY_FACT_CONFLICT';end if;
  select coalesce(jsonb_agg(x order by x->>'id'),'[]'::jsonb)into items
   from(select distinct value x from jsonb_array_elements((a->k)||(b->k)))s;
  if jsonb_array_length(items)>20000 then raise exception 'CP7_SUPPLY_FACT_LIMIT';end if;
  outcome:=outcome||jsonb_build_object(k,items);
 end loop;
 return outcome;
end $$;

create function cp7_supply_native.capture_at(s jsonb,p_at timestamptz)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare cut jsonb;other jsonb;part jsonb;ids uuid[];k text;i integer;n integer;
begin
 perform cp7_wip.fields(s,array['cutting_groups','opening_items','unsourced_bs']);
 foreach k in array array['cutting_groups','opening_items','unsourced_bs']loop
  if jsonb_typeof(s->k)is distinct from 'array'or jsonb_array_length(s->k)>1000 then
   raise exception 'CP7_SUPPLY_GLOBAL_SCOPE_LIMIT';end if;
  if exists(select 1 from jsonb_array_elements(s->k)x where jsonb_typeof(x)<>'string')
   or(select count(distinct value)from jsonb_array_elements(s->k))<>jsonb_array_length(s->k)then
   raise exception 'CP7_SUPPLY_GLOBAL_SCOPE';end if;
 end loop;
 cut:=cp7_wip.capture_cutting_sources(array[]::uuid[],p_at);
 other:=cp7_wip.capture_other_sources(array[]::uuid[],array[]::uuid[],p_at);
 foreach k in array array['cutting_groups','opening_items','unsourced_bs']loop
  select coalesce(array_agg(value::uuid order by value::uuid),array[]::uuid[])into ids
   from jsonb_array_elements_text(s->k);
  n:=cardinality(ids);i:=1;
  while i<=n loop
   if k='cutting_groups'then
    part:=cp7_wip.capture_cutting_sources(ids[i:least(i+49,n)],p_at);
    if part->>'status'is distinct from 'COMPLETE'then
     raise exception 'CP7_SUPPLY_NATIVE_BATCH_INCOMPLETE';end if;
    cut:=jsonb_set(cut,'{facts}',cp7_supply_native.merge_facts(cut->'facts',part->'facts'));
   else
    part:=cp7_wip.capture_other_sources(
     case when k='opening_items'then ids[i:least(i+49,n)]else array[]::uuid[]end,
     case when k='unsourced_bs'then ids[i:least(i+49,n)]else array[]::uuid[]end,p_at);
    if part->>'status'is distinct from 'COMPLETE'then
     raise exception 'CP7_SUPPLY_NATIVE_BATCH_INCOMPLETE';end if;
    other:=jsonb_set(other,'{facts}',cp7_supply_native.merge_facts(other->'facts',part->'facts'));
   end if;
   i:=i+50;
  end loop;
 end loop;
 return jsonb_build_object('contract_version','cp7.production-facts.v1','captured_at',cp7_planning.utc(p_at),
  'status','COMPLETE','scope',s,'facts',jsonb_build_object('cutting',cut->'facts','other',other->'facts'));
end $$;

-- PL-8: a posted group is exhausted when its own batch's conserved graph is
-- COMPLETE and every pool of the group holds no WIP, BS or withheld piece (all
-- of its input reached FG or EXIT), and nothing about it is still open: no
-- unresolved WIP flag, no failed laundry attempt, no rework or laundry claim
-- outside a closed status, no BS case on hold. A batch whose graph is not
-- COMPLETE, or that refuses, proves nothing: every group of it stays in scope.
-- A group's pools, nodes and events never touch another group's pool, and the
-- review signals (open flags, failed attempts) are excluded above, so dropping
-- a proven group leaves every other pool, position and signal as it was.
create function cp7_supply_native.exhausted_groups(capture jsonb)returns uuid[]
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare f jsonb:=capture->'facts';norm jsonb;spent uuid[];
begin
 begin
  norm:=cp7_wip.normalize_cutting(capture);
 exception when others then return '{}'::uuid[];
 end;
 if norm->>'status'is distinct from 'COMPLETE'then return '{}'::uuid[];end if;
 with pools as(
  select split_part(t->>'pool_key',':',2)k,
   bool_and((t->>'wip_pcs')::numeric=0 and(t->>'bs_pcs')::numeric=0 and(t->>'withheld_pcs')::numeric=0)spent
  from jsonb_array_elements(norm->'totals')t where split_part(t->>'pool_key',':',1)='CUT'group by 1
 ),cases as(select x->>'id'id,x->>'group_id'g,x->>'status'status from jsonb_array_elements(f->'bs')x),
 open as(
  select x->>'group_id'g from jsonb_array_elements(f->'flags')x where x->>'status'is distinct from 'RESOLVED'
  union all select r->>'group_id'from jsonb_array_elements(f->'failed')a
   join jsonb_array_elements(f->'receipts')r on r->>'id'=a->>'receipt_line_id'
  union all select g from cases where status='ON_HOLD'
  union all select b.g from jsonb_array_elements(f->'reworks')w join cases b on b.id=w->>'bs_case_id'
   where w->>'status'is null or w->>'status'not in('COMPLETED','CANCELLED')
  union all select d->>'group_id'from jsonb_array_elements(f->'claims')x
   join jsonb_array_elements(f->'deliveries')d on d->>'delivery_id'=x->>'delivery_id'
   where x->>'status'is null or x->>'status'not in('REJECTED','SETTLED','WRITTEN_OFF')
 )
 select coalesce(array_agg(x.id order by x.id),'{}'::uuid[])into spent
 from(select(value->>'id')::uuid id,value->>'id'k from jsonb_array_elements(f->'groups'))x
 join pools p on p.k=x.k and p.spent
 where not exists(select 1 from open o where o.g=x.k);
 return spent;
end $$;

-- Every posted group at this clock is read in batches of the unchanged capture;
-- this STABLE function's statements share the caller's snapshot. A group proven
-- exhausted leaves the production facts and is listed, never dropped, in
-- scope.exhausted_cutting_groups. The 1000-id scope applies to the rest; more
-- than 20000 posted groups is refused before any is classified.
create function cp7_supply_native.wip_source_at(p_at timestamptz)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare ids uuid[];kept uuid[]:='{}';spent uuid[]:='{}';proved uuid[];part jsonb;opening jsonb;nonpo jsonb;n integer;i integer:=1;
begin
 select coalesce(jsonb_agg(x.id order by x.id),'[]'::jsonb)into opening from(
  select s.opening_item_id id from erp.initial_import_production_sources s
  join erp.opening_balance_items i on i.id=s.opening_item_id
  join erp.opening_balance_headers h on h.id=i.opening_id
  join erp.migration_batches m on m.id=s.batch_id
  where h.status='POSTED'and m.status='POSTED'
   and h.opening_date<=(p_at at time zone 'Asia/Jakarta')::date
  order by s.opening_item_id limit 1001)x;
 select coalesce(jsonb_agg(x.id order by x.id),'[]'::jsonb)into nonpo from(
  select b.id from erp.bs_cases b where b.cutting_group_id is null
   and b.qc_item_id is null and b.source_laundry_receipt_line_id is null
   and b.po_id is null and b.untracked_type in('OUT_OF_NOWHERE','LEGACY')and b.physical_at<=p_at
   and not exists(select 1 from erp.initial_import_production_sources s where s.bs_case_id=b.id)
   and not exists(select 1 from erp.bb_wip_bs_splits_v1 s where s.bs_case_id=b.id)
  order by b.id limit 1001)x;
 if jsonb_array_length(opening)>1000 or jsonb_array_length(nonpo)>1000 then raise exception 'CP7_SUPPLY_GLOBAL_SCOPE_LIMIT';end if;
 select coalesce(array_agg(x.id order by x.id),'{}'::uuid[])into ids from(
  select g.id from erp.cutting_groups g
  where g.material_issue_posted and g.cut_at<=p_at order by g.id limit 20001)x;
 n:=cardinality(ids);
 if n>20000 then raise exception 'CP7_SUPPLY_GLOBAL_SCOPE_LIMIT';end if;
 while i<=n loop
  part:=cp7_wip.capture_cutting_sources(ids[i:least(i+49,n)],p_at);
  if part->>'status'is distinct from 'COMPLETE'then raise exception 'CP7_SUPPLY_NATIVE_BATCH_INCOMPLETE';end if;
  proved:=cp7_supply_native.exhausted_groups(part);spent:=spent||proved;
  kept:=kept||array(select x from unnest(ids[i:least(i+49,n)])x where not x=any(proved)order by x);
  i:=i+50;
 end loop;
 if cardinality(kept)>1000 then raise exception 'CP7_SUPPLY_GLOBAL_SCOPE_LIMIT';end if;
 return jsonb_set(cp7_supply_native.capture_at(jsonb_build_object('cutting_groups',to_jsonb(kept),
  'opening_items',opening,'unsourced_bs',nonpo),p_at),'{scope,exhausted_cutting_groups}',to_jsonb(spent));
end $$;

create function cp7_supply_native.source()returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with source as materialized(select cp7_baseline_native.source()c)
 select c||jsonb_build_object('production_sources',
  cp7_supply_native.wip_source_at((c->>'captured_at')::timestamptz))from source
$$;

create function cp7_supply_native.fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('native',c->'facts',
  'profiles',c->'profiles','production_policies',c->'production_policies'->'rows',
  'production_scope',c->'production_sources'->'scope',
  'production',c->'production_sources'->'facts')::text,'UTF8'),'sha256'),'hex')
$$;

create function cp7_supply_native.build(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare baseline jsonb;wip jsonb;hash text;
begin
 baseline:=cp7_baseline_native.build(c,q);wip:=cp7_wip.normalize_production(c->'production_sources');
 hash:=cp7_supply_native.fingerprint(c);
 -- The global label is granted by this server-derived source, after one graph
 -- reconciles all origins. A caller never supplies a completeness flag.
 if wip->>'status'='COMPLETE'then
  wip:=wip||jsonb_build_object('scope','GLOBAL_NATIVE_POSTED_PRODUCTION_ORIGINS',
   'source_basis','ONE_CLOCK_ONE_MVCC_SOURCE_BATCHES_ONE_CONSERVED_GRAPH');
 end if;
 return jsonb_build_object('contract_version','cp7.native-supply.v2',
  'captured_at',c->>'captured_at','source_hash',hash,
  'scope','GLOBAL_CURRENT_PHYSICAL_ROOTS_AND_POSTED_PRODUCTION_ORIGINS',
  'baseline_run_result',baseline,'production_scope',c->'production_sources'->'scope',
  'production_scope_basis','POSTED_CUTTING_GROUPS_NOT_PROVEN_EXHAUSTED_EXHAUSTED_LISTED',
  'wip',wip,'matching_state','UNKNOWN','yield_state','UNKNOWN','calendar_state','UNKNOWN',
  'capacity_state','UNKNOWN','allocation_state','UNKNOWN',
  'reason','NATIVE_PHYSICAL_WIP_KNOWN_ONLY_WHEN_CONSERVED_NOT_FUTURE_SELLABLE_SUPPLY',
  'apply_enabled',false,'production_go',false);
end $$;

create table cp7_supply_native.runs(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,
 query jsonb not null,captured_at timestamptz not null,access_at_capture jsonb not null,
 facts jsonb not null,result jsonb not null,dependency_hash text not null,unique(actor,request_id)
);
alter table cp7_supply_native.runs owner to cp7_capture;
alter table cp7_supply_native.runs enable row level security;
create policy cp7_supply_no_access on cp7_supply_native.runs for all to public using(false)with check(false);
revoke all on cp7_supply_native.runs from public,anon,authenticated,service_role;
create trigger immutable_supply_run before update or delete on cp7_supply_native.runs
 for each row execute function cp7_private.immutable_run();

create function cp7_supply_native.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_supply_native.runs%rowtype;c jsonb;outcome jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();select *into r from cp7_supply_native.runs
  where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_SUPPLY_RUN_UNAVAILABLE';end if;
 c:=cp7_supply_native.source();
 outcome:=r.result||jsonb_build_object('run_id',r.id,'request_id',r.request_id,
  'source_state',case when c->>'status'='COMPLETE'and cp7_supply_native.fingerprint(c)=r.dependency_hash
   then 'UNCHANGED'else 'ARCHIVED_STALE'end);
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLY_ACCESS_CHANGED';end if;
 return outcome;
end $$;

create function cp7_supply_native.capture(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;r cp7_supply_native.runs%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_private.access_now();q:=cp7_planning.history_query(p_query);
 if p_request is null then raise exception 'CP7_SUPPLY_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:SUPPLY:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLY_ACCESS_CHANGED';end if;
 select *into r from cp7_supply_native.runs where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if r.query<>q then raise exception 'CP7_SUPPLY_REQUEST_CHANGED';end if;return cp7_supply_native.serve(r.id);
 end if;
 with source as materialized(select cp7_supply_native.source()c),
 calculated as materialized(select c,cp7_supply_native.build(c,q)result from source)
 insert into cp7_supply_native.runs(actor,request_id,query,captured_at,access_at_capture,facts,result,dependency_hash)
 select(a->>'actor')::uuid,p_request,q,(c->>'captured_at')::timestamptz,a,c,result,result->>'source_hash'
 from calculated returning *into r;
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLY_ACCESS_CHANGED';end if;
 return cp7_supply_native.serve(r.id);
end $$;

alter function cp7_supply_native.merge_facts(jsonb,jsonb)owner to cp7_capture;
alter function cp7_supply_native.capture_at(jsonb,timestamptz)owner to cp7_capture;
alter function cp7_supply_native.exhausted_groups(jsonb)owner to cp7_capture;
alter function cp7_supply_native.wip_source_at(timestamptz)owner to cp7_capture;
alter function cp7_supply_native.source()owner to cp7_capture;
alter function cp7_supply_native.fingerprint(jsonb)owner to cp7_capture;
alter function cp7_supply_native.build(jsonb,jsonb)owner to cp7_capture;
alter function cp7_supply_native.serve(uuid)owner to cp7_capture;
alter function cp7_supply_native.capture(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_supply_native from public,anon,authenticated,service_role;
grant create on schema public to cp7_capture;
create function public.erp_cp7_capture_production_supply_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_supply_native.capture(p_query,p_request)$$;
create function public.erp_cp7_read_production_supply_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_supply_native.serve(p_run)$$;
alter function public.erp_cp7_capture_production_supply_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_read_production_supply_v1(uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_capture_production_supply_v1(jsonb,uuid),public.erp_cp7_read_production_supply_v1(uuid)
 from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_capture_production_supply_v1(jsonb,uuid),public.erp_cp7_read_production_supply_v1(uuid)to authenticated;
