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
-- classify also returns the graph size (in total and per spent group), which
-- the reconcile limits of a batch are checked against when proofs are reused.
create function cp7_supply_native.classify(capture jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare f jsonb:=capture->'facts';norm jsonb;spent jsonb;graph jsonb;
begin
 begin
  norm:=cp7_wip.normalize_cutting(capture);
 exception when others then return jsonb_build_object('complete',false);
 end;
 if norm->>'status'is distinct from 'COMPLETE'then return jsonb_build_object('complete',false);end if;
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
 select coalesce(jsonb_agg(x.k order by x.id),'[]'::jsonb)into spent
 from(select(value->>'id')::uuid id,value->>'id'k from jsonb_array_elements(f->'groups'))x
 join pools p on p.k=x.k and p.spent
 where not exists(select 1 from open o where o.g=x.k);
 graph:=norm->'graph';
 return jsonb_build_object('complete',true,'spent',spent,'pools',jsonb_array_length(graph->'pools'),
  'nodes',jsonb_array_length(graph->'nodes'),'events',jsonb_array_length(graph->'events'),
  'counts',(select coalesce(jsonb_object_agg(z.g,jsonb_build_array(z.p,z.n,z.e)),'{}'::jsonb)from(
   select y.g,count(*)filter(where y.t='p')p,count(*)filter(where y.t='n')n,count(*)filter(where y.t='e')e from(
    select 'p't,split_part(value->>'key',':',2)g from jsonb_array_elements(graph->'pools')
    union all select 'n',split_part(value->>'pool_key',':',2)from jsonb_array_elements(graph->'nodes')
    union all select 'e',split_part(value->>'pool_key',':',2)from jsonb_array_elements(graph->'events'))y
   where y.g in(select jsonb_array_elements_text(spent))group by y.g)z));
end $$;
create function cp7_supply_native.exhausted_groups(capture jsonb)returns uuid[]
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select array(select x::uuid from jsonb_array_elements_text(cp7_supply_native.classify(capture)->'spent')x)
$$;

-- PL-8 part 3: stored exhaustion proofs. A group is classified alone whenever
-- no fact row of its batch links it to another group of the batch (the
-- reference columns below) and no row but a laundry claim belongs to two
-- groups: its graph then shares no pool, node, event or lookup with another
-- group, so its verdict is a function of its own captured rows. A proof binds
-- that verdict to a sha256 of exactly those rows (every fact array, in capture
-- order, with each rework's completion read against the clock as settle_bs
-- reads it) and to proof_kernel(): the definition of every CP7 function the
-- capture, slicing and classification reach, plus the server version. Any
-- correction, reversal or backdated row that reaches the group's capture at
-- that clock changes the hash, so the proof is not found and the group is
-- classified again. Rows are only added; a superseded proof stays readable.
create table cp7_supply_native.exhaustion_proofs(
 id uuid primary key default gen_random_uuid(),group_id uuid not null,
 facts_hash text not null check(facts_hash~'^[0-9a-f]{64}$'),kernel_version text not null check(kernel_version~'^[0-9a-f]{64}$'),
 captured_at timestamptz not null,verdict text not null check(verdict='EXHAUSTED'),
 graph_pools integer not null check(graph_pools>0),graph_nodes integer not null check(graph_nodes>=0),
 graph_events integer not null check(graph_events>=0),recorded_at timestamptz not null default now()
);
create index exhaustion_proofs_key on cp7_supply_native.exhaustion_proofs(group_id,kernel_version,facts_hash);
alter table cp7_supply_native.exhaustion_proofs owner to cp7_capture;
alter table cp7_supply_native.exhaustion_proofs enable row level security;
create policy cp7_supply_proof_no_access on cp7_supply_native.exhaustion_proofs for all to public using(false)with check(false);
revoke all on cp7_supply_native.exhaustion_proofs from public,anon,authenticated,service_role;
create trigger immutable_exhaustion_proof before update or delete on cp7_supply_native.exhaustion_proofs
 for each row execute function cp7_private.immutable_run();

-- NULL (nothing is reused or proven) unless reconcile still refuses exactly at
-- the graph limits batch_verdict checks a reused batch against.
create function cp7_supply_native.proof_kernel()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with recursive k(oid)as(
  select p.oid from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='cp7_supply_native'and p.proname in('proof_kernel','classify','batch_reuse','batch_verdict')
   or n.nspname='cp7_wip'and p.proname='capture_cutting_sources'
  union
  select p.oid from k join pg_proc q on q.oid=k.oid,regexp_matches(q.prosrc,'(cp7_[a-z0-9_]+)\.([a-z0-9_]+)\s*\(','g')m,
   pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=m[1]and p.proname=m[2]
 )
 select case when position('jsonb_array_length(g->''pools'')>1000 or jsonb_array_length(g->''nodes'')>10000 or jsonb_array_length(g->''events'')>20000'
   in(select prosrc from pg_proc where oid='cp7_wip.reconcile(jsonb)'::regprocedure))>0
  then encode(extensions.digest(convert_to(current_setting('server_version_num')||E'\n'||
   string_agg(pg_get_functiondef(k.oid),E'\n'order by k.oid::regprocedure::text),'UTF8'),'sha256'),'hex')end
 from k
$$;

-- One batch capture: every row with the group(s) it belongs to, the groups a
-- reference column links across (or a row shared by two groups other than a
-- claim), the fact hash of each other group, the stored proofs that match it,
-- and, when some match, the batch without their rows (claims of a delivery
-- shared with an unmatched group stay). A row with no batch group, or an
-- unknown or malformed fact array, disables reuse for the batch.
create function cp7_supply_native.batch_reuse(capture jsonb,kernel text)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare outcome jsonb;contract text:=capture->>'contract_version';mode text:=capture->>'knowledge_mode';
 clock timestamptz:=(capture->>'captured_at')::timestamptz;
begin
 with r as materialized(
  select e.key k,x.o,x.x from jsonb_each(capture->'facts')e,
   jsonb_array_elements(case when jsonb_typeof(e.value)='array'then e.value else '[null]'end)with ordinality x(x,o)
 ),grp as materialized(select x->>'id'g from r where k='groups'),
 bs as materialized(select x->>'id'id,x->>'group_id'g from r where k='bs'),
 rc as materialized(select x->>'id'id,x->>'group_id'g from r where k='receipts'),
 fa as materialized(select a.x->>'id'id,rc.g from r a join rc on rc.id=a.x->>'receipt_line_id'where a.k='failed'),
 ds as materialized(select x->>'id'id,x->>'group_id'g from r where k='delivery_sizes'),
 dl as materialized(select distinct x->>'delivery_id'd,x->>'group_id'g from r where k='deliveries'),
 own as materialized(
  select r.k,r.o,r.x,case when r.k='groups'then r.x->>'id'else r.x->>'group_id'end g from r
   where r.k in('groups','yields','batches','deliveries','delivery_sizes','receipts','receipt_sizes','qc','bs','sewing','flags')
  union all select r.k,r.o,r.x,b.g from r left join bs b on b.id=r.x->>'bs_case_id'where r.k in('reworks','resolutions','holds','bs_fg')
  union all select r.k,r.o,r.x,a.g from r left join rc a on a.id=r.x->>'receipt_line_id'where r.k='failed'
  union all select r.k,r.o,r.x,a.g from r left join fa a on a.id=r.x->>'attempt_id'where r.k='failed_sizes'
  union all select r.k,r.o,r.x,s.g from r left join ds s on s.id=r.x->>'source_id'or s.id=r.x->>'successor_id'where r.k='redispatch'
  union all select r.k,r.o,r.x,d.g from r left join dl d on d.d=r.x->>'delivery_id'where r.k='claims'
  union all select r.k,r.o,r.x,null from r where r.k not in('groups','yields','batches','deliveries','delivery_sizes','receipts',
   'receipt_sizes','qc','bs','sewing','flags','reworks','resolutions','holds','bs_fg','failed','failed_sizes','redispatch','claims')
 ),bad as materialized(select exists(select 1 from own o where o.g is null or o.g not in(select g from grp where g is not null))b),
 link as materialized(
  select s.g a,t.g b from own s join own t on t.k='yields'and t.x->>'id'=s.x->>'yield_id'where s.k='batches'
  union all select s.g,t.g from own s join own t on t.k='batches'and t.x->>'batch_id'=s.x->>'batch_id'where s.k='delivery_sizes'
  union all select s.g,t.g from own s join own t on t.k='deliveries'and t.x->>'id'=s.x->>'delivery_line_id'where s.k in('delivery_sizes','receipts')
  union all select s.g,t.g from own s join own t on t.k='receipts'and t.x->>'id'=s.x->>'receipt_line_id'where s.k in('receipt_sizes','qc','bs')
  union all select s.g,t.g from own s join own t on t.k='delivery_sizes'and t.x->>'id'=s.x->>'delivery_size_id'where s.k in('receipt_sizes','failed_sizes')
  union all select s.g,t.g from own s join own t on t.k='receipt_sizes'and t.x->>'id'=s.x->>'receipt_size_id'where s.k='qc'
  union all select s.g,t.g from own s join own t on t.k='qc'and t.x->>'id'=s.x->>'qc_item_id'where s.k='bs'
  union all select s.g,t.g from own s join own t on t.k='reworks'and t.x->>'id'=s.x->>'source_rework_order_id'where s.k='resolutions'
  union all select s.g,t.g from own s join own t on t.k='resolutions'and t.x->>'id'=s.x->>'bs_resolution_id'where s.k='bs_fg'
  union all select s.g,t.g from own s join own t on t.k='redispatch'and t.x->>'id'=s.x->>'releases_allocation_event_id'where s.k='redispatch'
 ),tangled as materialized(
  select a g from link where a is distinct from b union select b from link where a is distinct from b
  union select o.g from own o join(select k,o from own where k<>'claims'group by k,o having count(distinct g)>1)m on m.k=o.k and m.o=o.o
 ),slice as(
  select o.g,o.k,o.o,case when o.k='reworks'then o.x||jsonb_build_object('completed_by_clock',
   (o.x->>'completed_at')::timestamptz<=clock)else o.x end x
  from own o where not(select b from bad)and not exists(select 1 from tangled t where t.g=o.g)
 ),hashes as materialized(
  select s.g,encode(extensions.digest(convert_to(concat_ws(E'\n',contract,mode,
   string_agg(s.k||E'\t'||s.x::text,E'\n'order by s.k,s.o)),'UTF8'),'sha256'),'hex')h
  from slice s group by s.g
 ),hit as materialized(
  select h.g::uuid group_id,p.np,p.nn,p.ne from hashes h,lateral(select min(x.graph_pools)np,min(x.graph_nodes)nn,min(x.graph_events)ne,
   count(distinct(x.graph_pools,x.graph_nodes,x.graph_events))n from cp7_supply_native.exhaustion_proofs x
   where x.group_id=h.g::uuid and x.kernel_version=kernel and x.facts_hash=h.h)p where p.n=1
 )
 select jsonb_build_object('hashes',(select coalesce(jsonb_object_agg(g,h),'{}'::jsonb)from hashes),
  'hit',(select coalesce(jsonb_agg(group_id order by group_id),'[]'::jsonb)from hit),
  'pools',(select coalesce(sum(np),0)from hit),'nodes',(select coalesce(sum(nn),0)from hit),'events',(select coalesce(sum(ne),0)from hit),
  'residual',case when exists(select 1 from hit)then jsonb_set(capture,'{facts}',(
   select jsonb_object_agg(e.key,coalesce(v.v,'[]'::jsonb))from jsonb_each(capture->'facts')e left join(
    select z.k,jsonb_agg(z.x order by z.o)v from(select distinct on(o.k,o.o)o.k,o.o,o.x from own o
     where not exists(select 1 from hit where hit.group_id=o.g::uuid)order by o.k,o.o)z group by z.k)v on v.k=e.key))end)into outcome;
 return outcome;
end $$;

-- A batch is proven with the stored proofs that match and the unchanged
-- classifier over the rest. It proves what the whole batch would: nothing
-- unless the rest is COMPLETE and the whole graph stays within reconcile's
-- limits, else every reused group and every spent group of the rest. Spent
-- groups classified alone become proofs for a VOLATILE caller to store.
create function cp7_supply_native.batch_verdict(part jsonb,kernel text)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare reuse jsonb;cl jsonb;hit jsonb:='[]';spent jsonb:='[]';
begin
 if kernel is not null and part->>'status'='COMPLETE'then
  begin reuse:=cp7_supply_native.batch_reuse(part,kernel);
  exception when others then reuse:=null;
  end;
  hit:=coalesce(reuse->'hit','[]'::jsonb);
 end if;
 if jsonb_array_length(hit)=0 then cl:=cp7_supply_native.classify(part);
 elsif jsonb_array_length(hit)=jsonb_array_length(part->'facts'->'groups')then
  cl:=jsonb_build_object('complete',true,'spent','[]'::jsonb,'pools',0,'nodes',0,'events',0,'counts','{}'::jsonb);
 else cl:=cp7_supply_native.classify(reuse->'residual');
 end if;
 if(cl->>'complete')::boolean and coalesce((reuse->>'pools')::bigint,0)+(cl->>'pools')::bigint<=1000
  and coalesce((reuse->>'nodes')::bigint,0)+(cl->>'nodes')::bigint<=10000 and coalesce((reuse->>'events')::bigint,0)+(cl->>'events')::bigint<=20000 then
  select coalesce(jsonb_agg(x order by x::uuid),'[]'::jsonb)into spent
  from(select jsonb_array_elements_text(hit)x union all select jsonb_array_elements_text(cl->'spent'))s;
 end if;
 return jsonb_build_object('spent',spent,'proofs',(select coalesce(jsonb_agg(jsonb_build_object('group_id',x,'facts_hash',reuse->'hashes'->>x,
  'kernel_version',kernel,'pools',cl->'counts'->x->0,'nodes',cl->'counts'->x->1,'events',cl->'counts'->x->2)order by x::uuid),'[]'::jsonb)
  from jsonb_array_elements_text(case when(cl->>'complete')::boolean then cl->'spent'end)x where reuse->'hashes'?x));
end $$;

-- Every posted group at this clock is read in batches of the unchanged capture;
-- this STABLE function's statements share the caller's snapshot. A group proven
-- exhausted leaves the production facts and is listed, never dropped, in
-- scope.exhausted_cutting_groups. The 1000-id scope applies to the rest; more
-- than 20000 posted groups is refused before any is classified. New proofs are
-- returned beside the source; only a VOLATILE caller stores them.
create function cp7_supply_native.wip_source_parts(p_at timestamptz)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare ids uuid[];kept uuid[]:='{}';spent uuid[]:='{}';proved uuid[];part jsonb;opening jsonb;nonpo jsonb;n integer;i integer:=1;
 kernel text;v jsonb;proofs jsonb:='[]';
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
 begin kernel:=cp7_supply_native.proof_kernel();
 exception when others then kernel:=null;
 end;
 while i<=n loop
  part:=cp7_wip.capture_cutting_sources(ids[i:least(i+49,n)],p_at);
  if part->>'status'is distinct from 'COMPLETE'then raise exception 'CP7_SUPPLY_NATIVE_BATCH_INCOMPLETE';end if;
  v:=cp7_supply_native.batch_verdict(part,kernel);proofs:=proofs||(v->'proofs');
  proved:=array(select x::uuid from jsonb_array_elements_text(v->'spent')x);spent:=spent||proved;
  kept:=kept||array(select x from unnest(ids[i:least(i+49,n)])x where not x=any(proved)order by x);
  i:=i+50;
 end loop;
 if cardinality(kept)>1000 then raise exception 'CP7_SUPPLY_GLOBAL_SCOPE_LIMIT';end if;
 return jsonb_build_object('source',jsonb_set(cp7_supply_native.capture_at(jsonb_build_object('cutting_groups',to_jsonb(kept),
  'opening_items',opening,'unsourced_bs',nonpo),p_at),'{scope,exhausted_cutting_groups}',to_jsonb(spent)),'proofs',proofs);
end $$;
create function cp7_supply_native.wip_source_at(p_at timestamptz)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select cp7_supply_native.wip_source_parts(p_at)->'source'
$$;

create function cp7_supply_native.source_parts_within(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with source as materialized(select cp7_baseline_native.source_within(p_products)c),
 parts as materialized(select c,cp7_supply_native.wip_source_parts((c->>'captured_at')::timestamptz)p from source)
 select jsonb_build_object('c',c||jsonb_build_object('production_sources',p->'source'),'proofs',p->'proofs')from parts
$$;
create function cp7_supply_native.source_parts()returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select cp7_supply_native.source_parts_within(1000)
$$;
create function cp7_supply_native.source_within(p_products integer)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select cp7_supply_native.source_parts_within(p_products)->'c'
$$;
create function cp7_supply_native.source()returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select cp7_supply_native.source_within(1000)
$$;

-- Appends the proofs not stored yet. No unique key, so concurrent writers never
-- wait on each other; an equal row they may both add is read as one proof.
create function cp7_supply_native.store_proofs(p_proofs jsonb,p_at timestamptz)returns integer
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare k integer;
begin
 insert into cp7_supply_native.exhaustion_proofs(group_id,facts_hash,kernel_version,captured_at,verdict,graph_pools,graph_nodes,graph_events)
 select(x->>'group_id')::uuid,x->>'facts_hash',x->>'kernel_version',p_at,'EXHAUSTED',(x->>'pools')::integer,(x->>'nodes')::integer,(x->>'events')::integer
 from jsonb_array_elements(p_proofs)x where not exists(select 1 from cp7_supply_native.exhaustion_proofs p
  where p.group_id=(x->>'group_id')::uuid and p.kernel_version=x->>'kernel_version'and p.facts_hash=x->>'facts_hash')
 order by(x->>'group_id')::uuid;
 get diagnostics k=row_count;
 return k;
end $$;

-- Stores proofs for up to p_count posted groups after p_after (by id) at this
-- clock: each batch's capture, classification and insert are one statement.
-- Proofs do not depend on how groups are batched, so a history too large for
-- one request is proven in windows; next_after continues it.
create function cp7_supply_native.prove_exhausted(p_at timestamptz,p_after uuid,p_count integer)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare ids uuid[];n integer;i integer:=1;kernel text;made integer:=0;
begin
 if p_at is null or p_count is null or p_count not between 1 and 1000 then raise exception 'CP7_SUPPLY_PROOF_WINDOW';end if;
 kernel:=cp7_supply_native.proof_kernel();
 if kernel is null then raise exception 'CP7_SUPPLY_PROOF_KERNEL';end if;
 select coalesce(array_agg(x.id order by x.id),'{}'::uuid[])into ids from(
  select g.id from erp.cutting_groups g where g.material_issue_posted and g.cut_at<=p_at
   and(p_after is null or g.id>p_after)order by g.id limit p_count)x;
 n:=cardinality(ids);
 while i<=n loop
  made:=made+cp7_supply_native.store_proofs(cp7_supply_native.batch_verdict(
   cp7_wip.capture_cutting_sources(ids[i:least(i+49,n)],p_at),kernel)->'proofs',p_at);
  i:=i+50;
 end loop;
 return jsonb_build_object('scanned',n,'proofs_added',made,'next_after',ids[n],'done',n<p_count);
end $$;

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
 -- The run and the proofs its source found are stored by this one statement.
 with source as materialized(select cp7_supply_native.source_parts()s),
 calculated as materialized(select s->'c'c,cp7_supply_native.build(s->'c',q)result,
  cp7_supply_native.store_proofs(s->'proofs',(s->'c'->>'captured_at')::timestamptz)proofs from source)
 insert into cp7_supply_native.runs(actor,request_id,query,captured_at,access_at_capture,facts,result,dependency_hash)
 select(a->>'actor')::uuid,p_request,q,(c->>'captured_at')::timestamptz,a,c,result,result->>'source_hash'
 from calculated where proofs>=0 returning *into r;
 if cp7_private.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_SUPPLY_ACCESS_CHANGED';end if;
 return cp7_supply_native.serve(r.id);
end $$;

alter function cp7_supply_native.merge_facts(jsonb,jsonb)owner to cp7_capture;
alter function cp7_supply_native.capture_at(jsonb,timestamptz)owner to cp7_capture;
alter function cp7_supply_native.classify(jsonb)owner to cp7_capture;
alter function cp7_supply_native.exhausted_groups(jsonb)owner to cp7_capture;
alter function cp7_supply_native.proof_kernel()owner to cp7_capture;
alter function cp7_supply_native.batch_reuse(jsonb,text)owner to cp7_capture;
alter function cp7_supply_native.batch_verdict(jsonb,text)owner to cp7_capture;
alter function cp7_supply_native.wip_source_parts(timestamptz)owner to cp7_capture;
alter function cp7_supply_native.wip_source_at(timestamptz)owner to cp7_capture;
alter function cp7_supply_native.source_parts_within(integer)owner to cp7_capture;
alter function cp7_supply_native.source_parts()owner to cp7_capture;
alter function cp7_supply_native.source_within(integer)owner to cp7_capture;
alter function cp7_supply_native.source()owner to cp7_capture;
alter function cp7_supply_native.store_proofs(jsonb,timestamptz)owner to cp7_capture;
alter function cp7_supply_native.prove_exhausted(timestamptz,uuid,integer)owner to cp7_capture;
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
