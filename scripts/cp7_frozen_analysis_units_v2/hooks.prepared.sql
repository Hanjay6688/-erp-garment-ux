create or replace function cp7_analysis_stage.run_unit(j cp7_analysis_stage.jobs,u cp7_analysis_stage.units)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare c jsonb;scenario jsonb;g jsonb;out jsonb;rows jsonb;b jsonb:=cp7_analysis_stage.bounds();idx integer;n integer;e integer;
 m integer;t integer:=(b->>'targets_per_chunk')::integer;k integer;p integer;s0 jsonb;carry jsonb;plan jsonb;alloc jsonb;v jsonb;
 alloc_runs boolean;keys text[];small jsonb;wip jsonb;ek jsonb;rk jsonb;rtk jsonb;
begin
 -- Final pages read only the stored header and fragments. Skip detoasting
 -- the full source and loading scenario/netting/allocation for every page.
 if u.kind='PAGES'then
  -- Page u.chunk: the stored items of targets lo..hi, per paged array, with
  -- counts, offsets (items before this page), whole-run totals and summary.
  declare h cp7_analysis_stage.headers%rowtype;items jsonb:='{}';counts jsonb:='{}';offsets jsonb:='{}';totals jsonb:='{}';
   kk text;vv jsonb;f text;frag text;n bigint;off bigint;page jsonb;body text;
  begin
   select *into h from cp7_analysis_stage.headers where run_id=j.run_id;
   if h.run_id is null then raise exception 'CP7_ANALYSIS_PAGE_HEADER_MISSING';end if;
   if h.cuts->u.chunk is distinct from jsonb_build_array(u.lo,u.hi)then raise exception 'CP7_ANALYSIS_PAGE_LAYOUT';end if;
   for kk,vv in select key,value from jsonb_each(h.paged)loop
    f:=cp7_analysis_stage.fragment_field(kk);
    select string_agg(x.body,', 'order by x.ord),coalesce(sum(x.items),0)into frag,n from cp7_analysis_stage.fragments x
     where x.job_id=j.id and x.field=f and x.ord between u.lo and u.hi;
    select coalesce(sum(x.items),0)into off from cp7_analysis_stage.fragments x where x.job_id=j.id and x.field=f and x.ord<u.lo;
    items:=items||jsonb_build_object(kk,('['||coalesce(frag,'')||']')::jsonb);
    if jsonb_array_length(items->kk)<>n then raise exception 'CP7_ANALYSIS_PAGE_LAYOUT';end if;
    counts:=counts||jsonb_build_object(kk,n);offsets:=offsets||jsonb_build_object(kk,off);totals:=totals||jsonb_build_object(kk,vv->'items');
   end loop;
   page:=jsonb_build_object('contract_version','cp7.native-analysis-page.v1','run_id',j.run_id,'request_id',j.request_id,
    'index',u.chunk,'page_count',h.page_count,'target_lo',u.lo,'target_hi',u.hi,'targets_total',h.targets_total,'header_sha256',h.sha256,
    'counts',counts,'offsets',offsets,'totals',totals,'summary',cp7_analysis_stage.page_summary(items),'items',items,'apply_enabled',false,'production_go',false);
   body:=page::text;
   if octet_length(body)>(b->>'page_utf8_bytes')::integer then raise exception 'CP7_ANALYSIS_PAGE_BODY_LIMIT';end if;
   insert into cp7_analysis_stage.pages(run_id,idx,target_lo,target_hi,counts,offsets,summary,body,utf8_bytes,sha256)
   values(j.run_id,u.chunk,u.lo,u.hi,counts,offsets,page->'summary',body,octet_length(body),encode(pg_catalog.sha256(convert_to(body,'UTF8')),'hex'));
   return jsonb_build_object('index',u.chunk,'utf8_bytes',octet_length(body));
  end;
 end if;
 if u.kind='PAGE_INDEX'then
  -- Written last: every page present, contiguous over 1..total, counts
  -- summing to the layout; the identity hash binds the header and every page.
  declare h cp7_analysis_stage.headers%rowtype;p record;expect integer:=1;i integer:=0;sums jsonb:='{}';kk text;vv jsonb;identity text;
   rec jsonb:=jsonb_build_object('ACTIVE',0,'PAUSED',0,'STOPPED',0,'OTHER',0);unreviewed bigint:=0;
  begin
   select *into h from cp7_analysis_stage.headers where run_id=j.run_id;
   if h.run_id is null then raise exception 'CP7_ANALYSIS_PAGE_HEADER_MISSING';end if;
   for p in select *from cp7_analysis_stage.pages x where x.run_id=j.run_id order by x.idx loop
    if p.idx<>i or p.target_lo<>expect then raise exception 'CP7_ANALYSIS_PAGE_LAYOUT';end if;
    expect:=p.target_hi+1;i:=i+1;
    for kk in select key from jsonb_each(h.paged)loop
     sums:=sums||jsonb_build_object(kk,coalesce((sums->>kk)::bigint,0)+(p.counts->>kk)::bigint);
    end loop;
    for kk in select key from jsonb_each(rec)loop
     rec:=rec||jsonb_build_object(kk,(rec->>kk)::bigint+(p.summary->'recommendations'->>kk)::bigint);
    end loop;
    unreviewed:=unreviewed+(p.summary->>'policy_unreviewed')::bigint;
   end loop;
   if i<>h.page_count or expect<>h.targets_total+1 then raise exception 'CP7_ANALYSIS_PAGE_LAYOUT';end if;
   for kk,vv in select key,value from jsonb_each(h.paged)loop
    if (sums->>kk)::bigint is distinct from(vv->>'items')::bigint then raise exception 'CP7_ANALYSIS_PAGE_LAYOUT';end if;
   end loop;
   -- identity_hash = sha256(header_sha256 || '\n' || page sha256s joined by '\n' in index order).
   select encode(pg_catalog.sha256(convert_to(h.sha256||E'\n'||coalesce(string_agg(x.sha256,E'\n'order by x.idx),''),'UTF8')),'hex')into identity
    from cp7_analysis_stage.pages x where x.run_id=j.run_id;
   insert into cp7_analysis_stage.page_sets(run_id,identity_hash,totals,created_at)
   values(j.run_id,identity,jsonb_build_object('targets',h.targets_total,'items',(select coalesce(jsonb_object_agg(x.key,x.value->'items'),'{}'::jsonb)from jsonb_each(h.paged)x),
    'recommendations',rec,'policy_unreviewed',unreviewed),clock_timestamp());
   return jsonb_build_object('pages',h.page_count,'targets',h.targets_total,'identity_hash',identity);
  end;
 end if;
 -- The reference, detoasted once (a per-row query over a toasted value
 -- copies it again and again).
 c:=cp7_frozen_analysis_units_v2.unit_reference(j,u);
 if u.kind in('HIST_PREP','HIST_EVENTS','HIST_VALIDATE','HIST_ROWS','HIST_STOCK','BASE_ROWS','SUPPLY','SCENARIO')then
  return cp7_analysis_stage.run_scenario_unit(j,u,c);
 end if;
 scenario:=cp7_analysis_stage.output(j.id,'SCENARIO')->'scenario';wip:=scenario->'wip';
 small:=jsonb_build_object('captured_at',c->'captured_at','schedule',c->'schedule');
 if u.kind='NET_PREP'then
  select case when cp7_analysis_stage.output(j.id,'SCENARIO')->'rows_null'='true'::jsonb then null else coalesce(jsonb_agg(x.payload order by x.ord),'[]')end
   into rows from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='BASE';
  -- An absent rows array stays absent (SQL NULL), as build reads it.
  g:=cp7_analysis_stage.netting_prep(c,jsonb_build_object('wip',wip,'etas',scenario->'etas','supply_run_result',
   jsonb_build_object('baseline_run_result',case when rows is null then '{}'::jsonb else jsonb_build_object('rows',rows)end)),
   (b->>'job_targets')::integer,(b->>'job_pairs')::bigint,(b->>'job_matching_products')::integer);
  -- The plan after the scenario units, up to ANA_META (which plans the pages).
  idx:=u.idx+1;n:=coalesce(jsonb_array_length(rows),0);
  if g->'wip_complete'='true'::jsonb then
   e:=jsonb_array_length(g->'eligible');
   for k in 0..(n-1)/t loop exit when n=0;
    insert into cp7_analysis_stage.units values(j.id,idx,'NET_TARGETS',k,k*t+1,least(n,(k+1)*t));idx:=idx+1;end loop;
   if n>0 and e>0 then
    p:=greatest(1,(b->>'pairs_per_chunk')::integer/n);
    for k in 0..(e-1)/p loop
     insert into cp7_analysis_stage.units values(j.id,idx,'NET_PAIRS',k,k*p+1,least(e,(k+1)*p));idx:=idx+1;end loop;
   end if;
   insert into cp7_analysis_stage.units values(j.id,idx,'NET_PLAN',0,null,null);idx:=idx+1;
   -- Allocation runs iff build() would call allocate (its three tests in its
   -- order; a NULL schedule state is not "unreviewed" there either). NET_PLAN
   -- checks its own decision against this plan.
   alloc_runs:=not exists(select 1 from jsonb_array_elements(coalesce(rows,'[]'))x where x->'target'->>'status'is distinct from 'SCENARIO'
     or x->>'available_fg_pcs'is null or x->'production_policy'->'policy'->>'state'is null)
    and not coalesce(scenario->>'schedule_state'<>'SELECTED_ASSUMPTIONS',false)and(g->>'supplies_complete')::boolean;
   if alloc_runs then
    insert into cp7_analysis_stage.units values(j.id,idx,'ALLOC_PREP',0,null,null);idx:=idx+1;
    m:=greatest(1,least((b->>'allocation_targets_per_step')::integer,
     (b->>'visits_per_allocation_step')::integer/greatest(1,jsonb_array_length(wip->'positions'))));
    for k in 0..greatest(0,(n-1)/m) loop
     insert into cp7_analysis_stage.units values(j.id,idx,'ALLOC_STEP',k,k*m+1,least(n,(k+1)*m));idx:=idx+1;end loop;
    insert into cp7_analysis_stage.units values(j.id,idx,'ALLOC_FINAL',0,null,null);idx:=idx+1;
   end if;
   for k in 0..(n-1)/t loop exit when n=0;
    insert into cp7_analysis_stage.units values(j.id,idx,'NET_ROWS',k,k*t+1,least(n,(k+1)*t));idx:=idx+1;end loop;
  end if;
  insert into cp7_analysis_stage.units values(j.id,idx,'FABRIC_PLAN',0,null,null);idx:=idx+1;
  if g->'wip_complete'='true'::jsonb then
   for k in 0..(n-1)/t loop exit when n=0;
    insert into cp7_analysis_stage.units values(j.id,idx,'ANA_TARGETS',k,k*t+1,least(n,(k+1)*t));idx:=idx+1;end loop;
  end if;
  insert into cp7_analysis_stage.units values(j.id,idx,'ANA_META',0,null,null);idx:=idx+1;
  update cp7_analysis_stage.jobs set unit_count=idx,targets_total=n,positions_total=coalesce(jsonb_array_length(g->'eligible'),0)where id=j.id;
  return g;
 end if;
 g:=cp7_analysis_stage.output(j.id,'NET_PREP');
 if u.kind='NET_TARGETS'then
  select coalesce(jsonb_agg(x.payload order by s.o),'[]')into rows
   from jsonb_array_elements_text(g->'sorted')with ordinality s(i,o)
   join cp7_analysis_stage.target_rows x on x.job_id=j.id and x.kind='BASE'and x.ord=s.i::integer where s.o between u.lo and u.hi;
  out:=cp7_analysis_stage.netting_targets(g,small,jsonb_build_object('snapshot_id',wip->'snapshot_id'),rows);
  insert into cp7_analysis_stage.target_rows select j.id,'NET1',u.lo+x.o-1,y.v->>'target_key',x.v
   from jsonb_array_elements(out->'rows')with ordinality x(v,o) cross join lateral(select rows->(x.o::integer-1) v)y;
  return jsonb_build_object('all_known',out->'all_known');
 end if;
 if u.kind='NET_PAIRS'then
  select coalesce(jsonb_object_agg(x.i::text,x.pair_row),'{}')into v from cp7_analysis_stage.pair_rows x
   where x.job_id=j.id and x.i<u.lo and x.i in(select l::integer from jsonb_array_elements_text(g->'leaders')l);
  out:=cp7_analysis_stage.netting_pairs(g,u.lo,u.hi,v);
  insert into cp7_analysis_stage.pair_rows select j.id,u.lo+x.o-1,x.v from jsonb_array_elements(out)with ordinality x(v,o);
  -- Per target key, its results in match_results order (position, then row).
  select jsonb_agg(x->'key'order by o)into ek from jsonb_array_elements(g->'eligible')with ordinality e(x,o);
  rk:=g->'row_keys';rtk:=g->'row_target_keys';
  insert into cp7_analysis_stage.pair_lists select j.id,u.chunk,f.k,f.results from(
   select rk->>(r.j::integer-1) k,jsonb_agg(jsonb_build_object('i',u.lo+x.o::integer-1,
     'e',jsonb_build_object('position_key',ek->(u.lo+x.o::integer-2),'target_key',rtk->(r.j::integer-1),'result',r.v))order by x.o,r.j)results
   from jsonb_array_elements(out)with ordinality x(v,o)cross join lateral jsonb_array_elements(x.v)with ordinality r(v,j)
   where rk->>(r.j::integer-1)is not null group by 1)f(k,results);
  return jsonb_build_object('identity_unknown',exists(select 1 from jsonb_array_elements(out)x cross join lateral jsonb_array_elements(x)r
   where r->>'match'in('UNKNOWN','NEEDS_CHECK')),
   -- The target keys (as stored, null included) the fabric plan reads as unresolved.
   'unresolved',(select coalesce(jsonb_agg(distinct rtk->(r.j::integer-1)),'[]')from jsonb_array_elements(out)x
    cross join lateral jsonb_array_elements(x)with ordinality r(v,j)where r.v->>'match'in('UNKNOWN','NEEDS_CHECK')));
 end if;
 if u.kind='NET_PLAN'then
  plan:=cp7_analysis_stage.netting_plan(g,small,wip,scenario->>'schedule_state',
   (select coalesce(jsonb_agg(x.payload->'target' order by x.ord),'[]')from cp7_analysis_stage.target_rows x
     where x.job_id=j.id and x.kind='NET1'and x.payload->'planned'='true'::jsonb),
   not exists(select 1 from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
     where o.job_id=j.id and y.kind='NET_TARGETS'and o.output->'all_known'='false'::jsonb));
  if(jsonb_typeof(plan->'allocation_input')='object')is distinct from exists(select 1 from cp7_analysis_stage.units y where y.job_id=j.id and y.kind='ALLOC_PREP')then
   raise exception 'CP7_ANALYSIS_STAGE_PLAN_MISMATCH';end if;
  return plan||jsonb_build_object('planned_ord',(select coalesce(jsonb_object_agg(f.k,f.o),'{}')from(select x.key k,min(x.ord)o
   from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='NET1'and x.payload->'planned'='true'::jsonb and x.key is not null group by 1)f));
 end if;
 plan:=coalesce(cp7_analysis_stage.output(j.id,'NET_PLAN'),jsonb_build_object('alloc',g->'alloc'));
 if u.kind='ALLOC_PREP'then return cp7_analysis_stage.alloc_prep(plan->'allocation_input',(b->>'job_targets')::integer,(b->>'job_pairs')::bigint);end if;
 if u.kind='ALLOC_STEP'then
  s0:=cp7_analysis_stage.output(j.id,'ALLOC_PREP');
  if s0?'result'or u.lo>jsonb_array_length(s0->'ordered')then return jsonb_build_object('carry',coalesce(cp7_analysis_stage.output(j.id,'ALLOC_STEP')->'carry',s0->'carry'),
   'edges','[]'::jsonb,'rows','[]'::jsonb,'reviews','[]'::jsonb);end if;
  carry:=coalesce((select o.output->'carry'from cp7_analysis_stage.outputs o where o.job_id=j.id and o.idx=u.idx-1 and u.chunk>0),s0->'carry');
  return cp7_analysis_stage.alloc_step(s0,carry,u.lo,least(u.hi,jsonb_array_length(s0->'ordered')),(b->>'visits_per_allocation_step')::integer);
 end if;
 if u.kind='ALLOC_FINAL'then
  s0:=cp7_analysis_stage.output(j.id,'ALLOC_PREP');
  if s0?'result'then return s0->'result';end if;
  select jsonb_agg(o.output order by y.idx)into v from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
   where o.job_id=j.id and y.kind='ALLOC_STEP';
  alloc:=cp7_analysis_stage.alloc_final(plan->'allocation_input',v->-1->'carry',
   (select coalesce(jsonb_agg(x.value order by s.o,x.o),'[]')from jsonb_array_elements(v)with ordinality s(value,o)cross join lateral jsonb_array_elements(s.value->'edges')with ordinality x(value,o)),
   (select coalesce(jsonb_agg(x.value order by s.o,x.o),'[]')from jsonb_array_elements(v)with ordinality s(value,o)cross join lateral jsonb_array_elements(s.value->'rows')with ordinality x(value,o)),
   (select coalesce(jsonb_agg(x.value order by s.o,x.o),'[]')from jsonb_array_elements(v)with ordinality s(value,o)cross join lateral jsonb_array_elements(s.value->'reviews')with ordinality x(value,o)));
  return alloc-'inputs';
 end if;
 alloc:=coalesce(cp7_analysis_stage.output(j.id,'ALLOC_FINAL'),plan->'alloc');
 if u.kind='NET_ROWS'then
  select coalesce(jsonb_agg(jsonb_build_object('ord',s.o,'row',x.payload)order by s.o),'[]'),coalesce(array_agg(x.key),'{}')into rows,keys
   from jsonb_array_elements_text(g->'sorted')with ordinality s(i,o)
   join cp7_analysis_stage.target_rows x on x.job_id=j.id and x.kind='BASE'and x.ord=s.i::integer where s.o between u.lo and u.hi;
  out:=cp7_analysis_stage.netting_rows(g,small,jsonb_build_object('snapshot_id',wip->'snapshot_id'),scenario->'capacity',alloc->>'status',plan,
   plan->'planned_ord',rows,
   (select coalesce(jsonb_object_agg(x.ord::text,x.payload),'{}')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='NET1'and x.ord between u.lo and u.hi),
   (select coalesce(jsonb_object_agg(f.key,f.results),'{}')from(select x.key,jsonb_agg(r.value order by x.chunk,r.o)results
     from cp7_analysis_stage.pair_lists x cross join lateral jsonb_array_elements(x.results)with ordinality r(value,o)
     where x.job_id=j.id and x.key=any(keys)group by x.key)f),
   (select coalesce(jsonb_object_agg(f.k,f.v),'{}')from(select value->>'target_key' k,jsonb_agg(value order by o)v
     from jsonb_array_elements(coalesce(alloc->'allocation'->'edges','[]'))with ordinality a(value,o)
     where value->>'target_key'=any(keys)and value->>'match'='CANDIDATE_MATCH'group by 1)f));
  insert into cp7_analysis_stage.target_rows select j.id,'NETROW',u.lo+x.o-1,x.v->>'target_key',x.v from jsonb_array_elements(out)with ordinality x(v,o);
  -- The only row fields the fabric plan reads (proven on the real plan: f05-staged-scenario).
  insert into cp7_analysis_stage.target_rows select j.id,'FAB',u.lo+x.o-1,x.v->>'target_key',jsonb_build_object('target_key',x.v->'target_key',
   'production_policy',jsonb_build_object('policy',jsonb_build_object('state',x.v->'production_policy'->'policy'->'state')),
   'conditional_gap_pcs',x.v->'conditional_gap_pcs','net',jsonb_build_object('inputs',jsonb_build_object('deadline',x.v->'net'->'inputs'->'deadline')))
   from jsonb_array_elements(out)with ordinality x(v,o);
  return jsonb_build_object('rows',jsonb_array_length(out));
 end if;
 if u.kind='FABRIC_PLAN'then
  -- Global: the fabric plan reads every netting row and match result.
  return jsonb_build_object('plan',cp7_fabric_native.plan(c,jsonb_build_object(
   'rows',(select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='FAB'),
   'match_results',(select coalesce(jsonb_agg(jsonb_build_object('target_key',k.value,'result',jsonb_build_object('match','UNKNOWN'))),'[]')
     from(select distinct k.value from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
      cross join lateral jsonb_array_elements(o.output->'unresolved')k where o.job_id=j.id and y.kind='NET_PAIRS')k))));
 end if;
 if u.kind='ANA_TARGETS'then
  declare by_root jsonb;by_stock jsonb;by_fabric jsonb;
  begin
  select coalesce(jsonb_agg(x.payload order by x.ord),'[]'),coalesce(array_agg(x.key),'{}')into rows,keys
   from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='NETROW'and x.ord between u.lo and u.hi;
  by_root:=(select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)from(select x->>'root_id'k,jsonb_agg(x)items from jsonb_array_elements(c->'facts'->'products')x
     where x->>'root_id'=any(select split_part(y,':',1)from unnest(keys)y)group by x->>'root_id')i);
  by_stock:=(select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)from(select x.key k,jsonb_agg(x.payload order by x.ord)items from cp7_analysis_stage.target_rows x
     where x.job_id=j.id and x.kind='STOCK'and x.key=any(keys)group by x.key)i);
  out:=cp7_analysis_stage.analysis_targets(cp7_analysis_stage.material_scope(c,keys),rows,by_root,by_stock,
   (select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)from(select x.key k,jsonb_agg(x.payload order by x.ord)items from cp7_analysis_stage.target_rows x
     where x.job_id=j.id and x.kind='HIST'and x.key=any(keys)group by x.key)i),
   (select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)from(select x->>'target_key'k,jsonb_agg(x order by o)items
     from jsonb_array_elements(coalesce(alloc->'allocation'->'edges','[]'))with ordinality e(x,o)where x->>'target_key'=any(keys)group by x->>'target_key')i),
   (select coalesce(jsonb_object_agg(f.key,f.results),'{}')from(select x.key,jsonb_agg(r.value->'e' order by x.chunk,r.o)results
     from cp7_analysis_stage.pair_lists x cross join lateral jsonb_array_elements(x.results)with ordinality r(value,o)
     where x.job_id=j.id and x.key=any(keys)group by x.key)f),
   case when c->'schedule'<>'null'::jsonb then jsonb_build_array(c->'schedule'->>'plan_id')else '[]'::jsonb end,
   cp7_analysis_stage.output(j.id,'FABRIC_PLAN')->'plan');
  -- Every target's items per array (canonical text, its UTF8 size): the
  -- pages are cut from these at any target boundary.
  insert into cp7_analysis_stage.fragments(job_id,ord,field,body,items,utf8_bytes)
  select j.id,u.lo+x.o::integer-1,f.field,s.body,jsonb_array_length(x.v->f.field),octet_length(s.body)
  from jsonb_array_elements(out->'targets')with ordinality x(v,o)cross join unnest(cp7_analysis_stage.fragment_fields())f(field)
  cross join lateral(select substr(a.t,2,length(a.t)-2)body from(select(x.v->f.field)::text t)a)s
  where jsonb_array_length(x.v->f.field)>0;
  -- Contract v2 §2: one target's plan inputs, in the same loop order (ord),
  -- with its own fabric assumptions exactly as the header lists them (only
  -- for a known target, as the header does).
  by_fabric:=(select coalesce(jsonb_object_agg(fq.k,fq.items),'{}'::jsonb)from(
    select fa.v->>'target_key'k,jsonb_agg(cp7_analysis_stage.fabric_assumption(fa.v)order by fa.o)items
    from jsonb_array_elements(case when jsonb_typeof(c#>'{fabric_source,selected}')='array'then c#>'{fabric_source,selected}'else'[]'::jsonb end)
     with ordinality fa(v,o)where fa.v->>'target_key'=any(keys)group by 1)fq);
  insert into cp7_analysis_stage.plan_targets(job_id,ord,target_key,row)
  select j.id,u.lo+x.o::integer-1,x.r->>'target_key',jsonb_build_object('target_key',x.r->'target_key','size_id',x.r->'size_id',
   'products',coalesce(by_root->split_part(x.r->>'target_key',':',1),'[]'::jsonb),'stock',coalesce(by_stock->(x.r->>'target_key'),'[]'::jsonb),
   'available_fg_pcs',x.r->'available_fg_pcs','target',x.r->'target','production_policy',x.r->'production_policy',
   'raw_gap_pcs',x.r->'raw_gap_pcs','base_gap_pcs',x.r->'base_gap_pcs','conditional_gap_pcs',x.r->'conditional_gap_pcs',
   'directed_on_time_good_pcs',x.r->'directed_on_time_good_pcs','candidate_allocated_good_pcs',x.r->'candidate_allocated_good_pcs',
   'supplies',x.r->'net'->'inputs'->'supplies','assumptions',out->'targets'->(x.o::integer-1)->'assumptions',
   'fabric_assumptions',case when coalesce((out->'known_keys')?(x.r->>'target_key'),false)then coalesce(by_fabric->(x.r->>'target_key'),'[]'::jsonb)
    else'[]'::jsonb end)
  from jsonb_array_elements(rows)with ordinality x(r,o)where x.r->>'target_key'is not null;
  return jsonb_build_object('known_keys',out->'known_keys','demand_unknown',out->'demand_unknown','materials_null',out->'materials_null',
   'counts',(select coalesce(jsonb_object_agg(i.field,i.n),'{}'::jsonb)from(select f.field,sum(jsonb_array_length(x.v->f.field))n
     from jsonb_array_elements(out->'targets')x(v)cross join unnest(cp7_analysis_stage.fragment_fields())f(field)group by 1)i));
  end;
 end if;
 if u.kind='ANA_META'then
  -- The header skeleton (build_operational after its target loop, the finance
  -- overlay) with each per-target array as one sentinel; the paged arrays;
  -- the page cut from the stored item sizes; the header row; then the last
  -- plan growth: one PAGES unit per cut and PAGE_INDEX.
  declare tag text:=cp7_analysis_stage.tag(j.id);skel jsonb;layout jsonb;cuts jsonb;ntargets integer;npages integer;header jsonb;body text;kk text;vv jsonb;
  begin
   skel:=cp7_analysis_stage.analysis_skeleton(c,j.query,j.run_id,j.access_at_capture,scenario,alloc,g->'matching',
    jsonb_build_object(
     'known_keys',(select coalesce(jsonb_agg(k.value order by y.idx,k.o),'[]')from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
       cross join lateral jsonb_array_elements(o.output->'known_keys')with ordinality k(value,o)where o.job_id=j.id and y.kind='ANA_TARGETS'),
     'demand_unknown',exists(select 1 from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
       where o.job_id=j.id and y.kind='ANA_TARGETS'and o.output->'demand_unknown'='true'::jsonb),
     'materials_null',exists(select 1 from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
       where o.job_id=j.id and y.kind='ANA_TARGETS'and o.output->'materials_null'='true'::jsonb),
     'counts',(select coalesce(jsonb_object_agg(f.field,f.n),'{}')from(select x.field,sum(x.items)n from cp7_analysis_stage.fragments x where x.job_id=j.id group by 1)f)),
    exists(select 1 from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
      where o.job_id=j.id and y.kind='NET_PAIRS'and o.output->'identity_unknown'='true'::jsonb),tag);
   layout:=cp7_analysis_stage.page_layout(j.id,skel,tag);
   select coalesce(sum(y.hi-y.lo+1),0)into ntargets from cp7_analysis_stage.units y where y.job_id=j.id and y.kind='ANA_TARGETS';
   cuts:=cp7_analysis_stage.page_cuts(j.id,layout,ntargets,(b->>'page_utf8_bytes')::integer);
   npages:=jsonb_array_length(cuts);
   -- The analysis without the per-target items: each sentinel removed.
   for kk,vv in select key,value from jsonb_each(layout)loop
    skel:=jsonb_set(skel,array[kk],(select coalesce(jsonb_agg(x.e order by x.o),'[]'::jsonb)
     from jsonb_array_elements(skel->kk)with ordinality x(e,o)where x.e<>to_jsonb(tag||(vv->>'field'))));
   end loop;
   -- The Original's other fields exactly as original() renders them.
   header:=(cp7_analysis_jobs.original(row(j.run_id,j.actor,j.request_id,j.query,j.captured_at,j.access_at_capture,c,
     to_jsonb(tag||'analysis'),j.source_hash)::cp7_analysis_native.runs)-'analysis'-'contract_version')
    ||jsonb_build_object('contract_version','cp7.native-analysis-header.v1','analysis_header',skel,
     'paged',(select coalesce(jsonb_object_agg(x.key,x.value-'field'),'{}'::jsonb)from jsonb_each(layout)x),'targets_total',ntargets,'page_count',npages);
   body:=header::text;
   if octet_length(body)>(b->>'header_utf8_bytes')::integer then raise exception 'CP7_ANALYSIS_PAGE_HEADER_LIMIT';end if;
   insert into cp7_analysis_stage.headers(run_id,job_id,body,utf8_bytes,sha256,paged,targets_total,page_count,cuts)
   values(j.run_id,j.id,body,octet_length(body),encode(pg_catalog.sha256(convert_to(body,'UTF8')),'hex'),header->'paged',ntargets,npages,cuts);
   -- Contract v2 §2: the run's planning scope (allocation, capacity, WIP state,
   -- schedule and its global assumptions (the fabric ones stay with their
   -- target), company cut WIP per model:size) and
   -- every cutting group of the production scope with its open/exhausted
   -- state and whether its pieces were proven to have left WIP.
   insert into cp7_analysis_stage.plan_scope(job_id,scope)
   with totals as materialized(select pt.val from jsonb_array_elements(case when jsonb_typeof(wip->'totals')='array'then wip->'totals'else'[]'::jsonb end)pt(val)
     where pt.val->>'pool_key'like 'CUT:%'and pt.val->>'ownership'='COMPANY'),
    fabric as materialized(select distinct fa.v->>'id' id
     from jsonb_array_elements(case when jsonb_typeof(c#>'{fabric_source,selected}')='array'then c#>'{fabric_source,selected}'else'[]'::jsonb end)fa(v)),
    models as materialized(select pg.val->>'id' id,min(pg.val->>'model_id')model_id
     from jsonb_array_elements(case when jsonb_typeof(c#>'{production_sources,facts,cutting,groups}')='array'
       then c#>'{production_sources,facts,cutting,groups}'else'[]'::jsonb end)pg(val)group by 1)
   select j.id,jsonb_build_object('alloc_status',alloc->'status','capacity',scenario->'capacity','scenario_status',scenario->'status',
    'reorder_supply_budget',cp7_reorder_supply.budgets(wip,scenario->'etas'),
   'wip_status',wip->'status','schedule_state',scenario->'schedule_state',
    'schedule',case when jsonb_typeof(c->'schedule')='object'then jsonb_build_object('plan_id',c->'schedule'->'plan_id','revision',c->'schedule'->'revision')end,
    'assumptions',(select coalesce(jsonb_agg(x.e order by x.o),'[]'::jsonb)from jsonb_array_elements(coalesce(skel->'assumptions','[]'::jsonb))with ordinality x(e,o)
      where jsonb_typeof(x.e)='object'and not exists(select 1 from fabric fi where fi.id=x.e->>'id')),
    'wip_by_model_size',(select coalesce(jsonb_object_agg(pw.k,pw.pcs),'{}'::jsonb)from(
      select pm.model_id||':'||(pt.val->>'size_id')k,sum((pt.val->>'wip_pcs')::numeric)::text pcs
      from totals pt join models pm on pm.id=split_part(pt.val->>'pool_key',':',2)
      where pm.model_id is not null and pt.val->>'size_id'is not null group by 1)pw));
   insert into cp7_analysis_stage.plan_groups(job_id,group_id,scope,unproven)
   with unproven as materialized(select split_part(pt.val->>'pool_key',':',2)gid
     from jsonb_array_elements(case when jsonb_typeof(wip->'totals')='array'then wip->'totals'else'[]'::jsonb end)pt(val)
     where pt.val->>'pool_key'like 'CUT:%'and(pt.val->>'input_pcs')::numeric>(pt.val->>'fg_pcs')::numeric+(pt.val->>'exited_pcs')::numeric group by 1),
    scoped as materialized(select x.value#>>'{}' gid,'OPEN'scope
      from jsonb_array_elements(case when jsonb_typeof(scenario#>'{supply_run_result,production_scope,cutting_groups}')='array'
       then scenario#>'{supply_run_result,production_scope,cutting_groups}'else'[]'::jsonb end)x
     union all select x.value#>>'{}','EXHAUSTED'
      from jsonb_array_elements(case when jsonb_typeof(scenario#>'{supply_run_result,production_scope,exhausted_cutting_groups}')='array'
       then scenario#>'{supply_run_result,production_scope,exhausted_cutting_groups}'else'[]'::jsonb end)x)
   select j.id,ps.gid,min(ps.scope),bool_or(pu.gid is not null)from scoped ps left join unproven pu on pu.gid=ps.gid where ps.gid is not null group by ps.gid;
   idx:=u.idx+1;
   insert into cp7_analysis_stage.units select j.id,idx+x.o::integer-1,'PAGES',x.o::integer-1,(x.v->>0)::integer,(x.v->>1)::integer
    from jsonb_array_elements(cuts)with ordinality x(v,o);
   idx:=idx+npages;
   insert into cp7_analysis_stage.units values(j.id,idx,'PAGE_INDEX',0,null,null);
   update cp7_analysis_stage.jobs set unit_count=idx+1,plan_final=true where id=j.id;
   return jsonb_build_object('paged',layout,'targets',ntargets,'pages',npages,'header_utf8_bytes',octet_length(body));
  end;
 end if;
 raise exception 'CP7_ANALYSIS_STAGE_UNKNOWN_UNIT';
end $$;

create or replace function cp7_supply_native.fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case when c->>'bounded_request_contract'='cp7.bounded-analysis-request.v2'
 then cp7_frozen_analysis_v2.work_fingerprint(c)
 when c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'
 then cp7_bounded_analysis_stage.work_fingerprint(c) else encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts',
  'profiles',c->'profiles','production_policies',c->'production_policies'->'rows','product_analog_choices',c->'product_analog_choices','analog_consumer_engine',c->'analog_consumer_engine','model_target_source_hash',c->'model_target_source'->'source_hash',
  'production_scope',c->'production_sources'->'scope',
  'production',c->'production_sources'->'facts')::text,'UTF8'),'sha256'),'hex') end
$$;

create or replace function cp7_bounded_analysis_stage.require_inputs(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare b jsonb:=c->'bounded_history_inputs';i jsonb:=b->'inputs';n integer:=jsonb_array_length(c->'facts'->'products');keys jsonb;
begin
 if c->>'bounded_request_contract'='cp7.bounded-analysis-request.v2'then
  perform cp7_frozen_analysis_v2.work_fingerprint(c);
 else perform cp7_bounded_analysis_stage.work_fingerprint(c);end if;
 if c->'bounded_query'is distinct from q or b->>'contract_version'is distinct from'cp7.bounded-history-inputs.v1'
  or b->>'coverage'is distinct from'COMPLETE' or b->'captured_at'is distinct from c->'captured_at'
  or b->'query'is distinct from q or b->'raw_native_capture_status'is distinct from c->'status'
  or b->'raw_native_status_overridden'is distinct from'false'::jsonb
  or i->>'contract_version'is distinct from'cp7.reorder-native-inputs.v1'
  or i->'captured_at'is distinct from c->'captured_at' or i->'query'is distinct from q
  or i->'products'is distinct from c->'facts'->'products'
  or i->>'source_hash'is null or i->>'source_hash'!~'^[0-9a-f]{64}$'
  or i->>'history_hash'is null or i->>'history_hash'!~'^[0-9a-f]{64}$'
  or jsonb_typeof(i->'history')is distinct from'array' or jsonb_typeof(i->'current_stock')is distinct from'array'
  or jsonb_typeof(i->'targets')is distinct from'array' then
  raise exception 'CP7_BOUNDED_ANALYSIS_INPUT_BINDING';end if;
 -- One actual Native result per product. Never accept missing or duplicate
 -- rows as zero, or a result for a different target/root/size.
 select coalesce(jsonb_object_agg((p->>'root_id')||':'||(p->>'size_id'),true),'{}')into keys
  from jsonb_array_elements(c->'facts'->'products')p;
 if exists(select 1 from jsonb_each(jsonb_build_object('history',i->'history','stock',i->'current_stock','targets',i->'targets'))a
  where jsonb_array_length(a.value)<>n or n<>(select count(distinct x->>'target_key')from jsonb_array_elements(a.value)x)
   or exists(select 1 from jsonb_array_elements(a.value)x where not(keys?(x->>'target_key'))))then
  raise exception 'CP7_BOUNDED_ANALYSIS_INPUT_TARGETS';end if;
 return i;
end $$;

create or replace function cp7_bounded_analysis_stage.source_for(p_reference jsonb,p_query jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if p_reference->>'bounded_request_contract'='cp7.bounded-analysis-request.v2'then
  if p_reference->'bounded_query'is distinct from p_query then raise exception 'CP7_FROZEN_V2_REFERENCE_SHAPE';end if;
  begin
   return cp7_frozen_analysis_units_v2.source(p_query,false);
  exception when raise_exception then
   if sqlerrm in('CP7_ANALYSIS_STAGED_TARGET_LIMIT','CP7_BOUNDED_ANALYSIS_HISTORY_SCOPE','CP7_REORDER_NON_STOCK_SOURCE_INCOMPLETE')then
    raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';end if;
   raise;
  end;
 end if;
 if p_reference?'bounded_request_contract'then
  if p_reference->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v1'
   or p_reference->'bounded_query'is distinct from p_query then raise exception 'CP7_BOUNDED_ANALYSIS_REFERENCE_SHAPE';end if;
  begin
   return cp7_bounded_analysis_stage.source(p_query,false);
  exception when raise_exception then
   if sqlerrm in('CP7_ANALYSIS_STAGED_TARGET_LIMIT','CP7_BOUNDED_ANALYSIS_HISTORY_SCOPE')then
    raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';end if;
   raise;
  end;
 end if;
 return cp7_schedule_staged_review.current_source();
end $$;

create or replace function cp7_analysis_stage.run_scenario_unit(j cp7_analysis_stage.jobs,u cp7_analysis_stage.units,c jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare b jsonb:=cp7_analysis_stage.bounds();g jsonb;val jsonb;out jsonb;v jsonb;idx integer;n integer;k integer;per integer;days integer;
 keys jsonb;roots jsonb;sub jsonb;avail jsonb;latest jsonb;rows jsonb;offs integer;cut jsonb;
begin
 if c->>'bounded_request_contract'in('cp7.bounded-analysis-request.v1','cp7.bounded-analysis-request.v2')then
  return cp7_bounded_analysis_stage.run_scenario_unit(j,u,c);end if;
 if u.kind='HIST_PREP'then
  g:=cp7_analysis_stage.history_prep(c,j.query,(b->>'job_targets')::integer,(b->>'job_history_cells')::bigint,(b->>'sales_per_events_unit')::integer);
  -- A source that is not clean: the single path's whole events/availability.
  if not(g->>'events_clean')::boolean then
   insert into cp7_analysis_stage.target_rows select j.id,'HEV',x.o,null,x.v from jsonb_array_elements(g->'events')with ordinality x(v,o);
  end if;
  if not(g->>'availability_clean')::boolean then
   insert into cp7_analysis_stage.target_rows select j.id,'HAV',f.k,f.key,f.rows from(
    select row_number()over(order by min(x.o))::integer k,x.v->>'target_key' key,jsonb_agg(x.v order by x.o)rows
    from jsonb_array_elements(g->'availability')with ordinality x(v,o)group by x.v->>'target_key')f;
  end if;
  n:=jsonb_array_length(g->'targets');days:=(g->>'through')::date-(g->>'from')::date+1;idx:=1;
  -- One events unit per sale id range; a source that is not clean: one unit
  -- over the whole events array.
  for k in 0..greatest(jsonb_array_length(g->'cuts'),case when(g->>'events_clean')::boolean then 0 else 1 end)-1 loop
   insert into cp7_analysis_stage.units values(j.id,idx,'HIST_EVENTS',k,null,null);idx:=idx+1;end loop;
  insert into cp7_analysis_stage.units values(j.id,idx,'HIST_VALIDATE',0,null,null);idx:=idx+1;
  per:=greatest(1,(b->>'history_cells_per_unit')::integer/greatest(days,1));
  for k in 0..(n-1)/per loop exit when n=0;
   insert into cp7_analysis_stage.units values(j.id,idx,'HIST_ROWS',k,k*per+1,least(n,(k+1)*per));idx:=idx+1;end loop;
  -- At least one stock unit: its per-root sums read every stock row even
  -- without products, as history_build's do.
  per:=(b->>'targets_per_stock_unit')::integer;
  for k in 0..greatest(0,(n-1)/per)loop
   insert into cp7_analysis_stage.units values(j.id,idx,'HIST_STOCK',k,k*per+1,least(n,(k+1)*per));idx:=idx+1;end loop;
  per:=(b->>'targets_per_chunk')::integer;
  for k in 0..(n-1)/per loop exit when n=0;
   insert into cp7_analysis_stage.units values(j.id,idx,'BASE_ROWS',k,k*per+1,least(n,(k+1)*per));idx:=idx+1;end loop;
  insert into cp7_analysis_stage.units values(j.id,idx,'SUPPLY',0,null,null),(j.id,idx+1,'SCENARIO',0,null,null),(j.id,idx+2,'NET_PREP',0,null,null);
  update cp7_analysis_stage.jobs set unit_count=idx+3,targets_total=n where id=j.id;
  return g-'events'-'availability';
 end if;
 g:=cp7_analysis_stage.output(j.id,'HIST_PREP');
 if u.kind='HIST_EVENTS'then
  if(g->>'events_clean')::boolean then
   cut:=g->'cuts'->u.chunk;
   rows:=cp7_planning.history_events(cp7_analysis_stage.event_facts(c,cut->>0,cut->>1));
  else
   select coalesce(jsonb_agg(x.payload order by x.ord),'[]')into rows from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='HEV';
  end if;
  out:=cp7_analysis_stage.events_validate(jsonb_build_object('known_as_of',c->>'captured_at','effective_as_of',c->>'captured_at',
   'from_date',j.query->'from_date','through_date',j.query->'through_date','group_mode',j.query->'group_mode','targets',g->'targets','events',rows));
  -- The selected events of this chunk's lineages, per target (a target's
  -- lineages may lie in several chunks).
  insert into cp7_analysis_stage.target_rows select j.id,'HSEL',u.idx*100000+(row_number()over(order by e.key))::integer,e.key,e.value from jsonb_each(out->'by_target')e;
  return out-'by_target';
 end if;
 if u.kind='HIST_VALIDATE'then
  return cp7_analysis_stage.history_validate(jsonb_build_object('targets',g->'targets',
   'events',(select coalesce(sum((o.output->>'events')::bigint),0)from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
     where o.job_id=j.id and y.kind='HIST_EVENTS'),
   'errors',(select coalesce(jsonb_agg(o.output->'error'order by o.idx),'[]')from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
     where o.job_id=j.id and y.kind='HIST_EVENTS'and o.output?'error')));
 end if;
 val:=cp7_analysis_stage.output(j.id,'HIST_VALIDATE');
 if u.kind='HIST_ROWS'then
  select coalesce(jsonb_agg(g->'targets'->(k.i::integer-1)order by k.pos),'[]')into v
   from jsonb_array_elements_text(val->'key_order')with ordinality k(i,pos)where k.pos between u.lo and u.hi;
  select coalesce(jsonb_object_agg(t->>'key',true),'{}')into keys from jsonb_array_elements(v)t;
  if(g->>'availability_clean')::boolean then
   -- The chunk's products and their roots' stock rows (array order kept).
   select coalesce(jsonb_agg(p order by o),'[]'),coalesce(jsonb_object_agg(p->>'root_id',true),'{}')into sub,roots
    from jsonb_array_elements(c->'facts'->'products')with ordinality x(p,o)where keys?((p->>'root_id')||':'||(p->>'size_id'));
   avail:=cp7_planning.history_availability(jsonb_build_object('captured_at',c->'captured_at','facts',jsonb_build_object('products',sub,
    'stock',(select coalesce(jsonb_agg(m order by o),'[]')from jsonb_array_elements(c->'facts'->'stock')with ordinality x(m,o)where roots?(m->>'root_id')))),j.query);
  else
   select coalesce(jsonb_agg(e order by x.ord,e.o),'[]')into avail from cp7_analysis_stage.target_rows x cross join lateral jsonb_array_elements(x.payload)with ordinality e(e,o)
    where x.job_id=j.id and x.kind='HAV'and keys?x.key;
  end if;
  select coalesce(jsonb_object_agg(e->>'lineage_key',e),'{}')into latest from cp7_analysis_stage.target_rows x cross join lateral jsonb_array_elements(x.payload)e
   where x.job_id=j.id and x.kind='HSEL'and keys?x.key;
  rows:=cp7_analysis_stage.history_rows(jsonb_build_object('known_as_of',c->>'captured_at','from_date',j.query->'from_date','through_date',j.query->'through_date',
   'history_complete',true,'targets',v,'keys',keys,'latest',latest,'availability',avail));
  insert into cp7_analysis_stage.target_rows select j.id,'HIST',u.lo+x.o-1,x.v->>'target_key',x.v from jsonb_array_elements(rows)with ordinality x(v,o);
  return jsonb_build_object('rows',jsonb_array_length(rows),'availability_rows',jsonb_array_length(avail));
 end if;
 if u.kind='HIST_STOCK'then
  rows:=cp7_analysis_stage.history_stock(c,(select coalesce(jsonb_agg(x.p order by x.o),'[]')from jsonb_array_elements(g->'stock_order')with ordinality x(p,o)
   where x.o between u.lo and u.hi),g->>'hash');
  insert into cp7_analysis_stage.target_rows select j.id,'STOCK',u.lo+x.o-1,x.v->>'target_key',x.v from jsonb_array_elements(rows)with ordinality x(v,o);
  return jsonb_build_object('rows',jsonb_array_length(rows));
 end if;
 if u.kind='BASE_ROWS'then
  rows:=cp7_analysis_stage.baseline_rows(c,
   (select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='HIST'and x.ord between u.lo and u.hi),
   (select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='STOCK'),g->>'baseline_hash');
  insert into cp7_analysis_stage.target_rows select j.id,'BASE',u.lo+x.o-1,x.v->>'target_key',x.v from jsonb_array_elements(rows)with ordinality x(v,o);
  return jsonb_build_object('rows',jsonb_array_length(rows));
 end if;
 if u.kind='SUPPLY'then return cp7_analysis_stage.supply(c);end if;
 if u.kind='SCENARIO'then
  -- The skeleton the later units read (the prototype's SCENARIO output shape).
  return jsonb_build_object('scenario',cp7_analysis_stage.schedule(c,cp7_analysis_stage.output(j.id,'SUPPLY')),'rows_null',false);
 end if;
 raise exception 'CP7_ANALYSIS_STAGE_UNKNOWN_UNIT';
end $$;

create or replace function cp7_analysis_stage.analysis_skeleton(c jsonb,q jsonb,p_run uuid,a jsonb,scenario jsonb,alloc jsonb,matching jsonb,
 meta jsonb,identity_unknown boolean,tag text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare wip jsonb:=scenario->'wip';p jsonb;e jsonb;eta jsonb;part jsonb;k text;part_hash text;count_facts integer:=0;part_count integer;
 plan_refs jsonb:='[]';plan_aids jsonb:='[]';assumptions jsonb;sources jsonb;recommendations jsonb;edges jsonb;actions jsonb;timeline jsonb;
 models jsonb;materials jsonb;metrics jsonb;warnings jsonb;dependencies jsonb:='[]';known_targets jsonb;v jsonb;
 complete boolean:=(c->>'status'='COMPLETE'or(case when c->>'bounded_request_contract'in('cp7.bounded-analysis-request.v1','cp7.bounded-analysis-request.v2')
 then cp7_bounded_analysis_stage.require_inputs(c,q)is not null else false end))and wip->>'status'='COMPLETE';hash text:=cp7_analysis_native.fingerprint(c);
 allocation_known boolean:=alloc->>'status'='SCENARIO';allocated numeric;load numeric;
 scenario_revision bigint:=coalesce((c->'schedule'->>'revision')::bigint,0);
 schedule_assumption jsonb:='[]';fabric_assumptions jsonb[]:='{}';edges_acc jsonb[]:='{}';sources_acc jsonb[]:='{}';
 etas_by_position jsonb;inputs_by_source jsonb;directed_source_keys jsonb;source_inputs jsonb;
 warnings0 jsonb:='["MATERIAL_FEASIBILITY_NOT_PROVEN","ADAPTIVE_MODEL_PROMOTION_NOT_PROVEN","FINANCIAL_DOMAIN_NOT_CAPTURED"]';
begin
 if c->>'bounded_request_contract'in('cp7.bounded-analysis-request.v1','cp7.bounded-analysis-request.v2')and c->>'status'='INCOMPLETE'then
  warnings0:=warnings0||'"RAW_NATIVE_CAPTURE_INCOMPLETE_COMPLETE_SQL_HISTORY_INPUTS"'::jsonb;end if;
 if scenario_revision>9007199254740991 then raise exception 'CP7_ANALYSIS_REVISION_RANGE';end if;
 select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)into etas_by_position from(
  select x->>'position_key'k,jsonb_agg(x->'result'order by o)items from jsonb_array_elements(coalesce(scenario->'etas','[]'))with ordinality e(x,o)
  where x->>'position_key'is not null group by x->>'position_key')i;
 select coalesce(jsonb_object_agg(i.k,true),'{}'::jsonb)into directed_source_keys from(
  select distinct x->>'key'k from jsonb_array_elements(coalesce(matching->'sources','[]'))x
  where x->>'key'is not null and x->>'confirmed_target'is not null)i;
 if c->'schedule'<>'null'::jsonb then
  plan_aids:=jsonb_build_array(c->'schedule'->>'plan_id');
  plan_refs:=jsonb_build_array(cp7_wip.ref('PLANNING_SCHEDULE',c->'schedule'->>'plan_id',c->'schedule'->>'revision'));
  schedule_assumption:=jsonb_build_array(jsonb_build_object('id',c->'schedule'->>'plan_id',
   'label','Jadwal, waktu sisa dan perkiraan hasil bagus yang dipilih; bukan hasil produksi aktual',
   'origin','OWNER_INPUT','confirmed_for_operation',false));
 end if;
 select coalesce(jsonb_object_agg(t.key,true),'{}'::jsonb)into known_targets from jsonb_array_elements_text(meta->'known_keys')t(key);
 for e in select value from jsonb_array_elements(coalesce(alloc->'allocation'->'edges','[]'))loop
  if not(known_targets? (e->>'target_key'))then raise exception 'CP7_ANALYSIS_EDGE_TARGET_UNPROVEN';end if;
  eta:=etas_by_position->(e->>'position_key');
  if jsonb_array_length(eta)>1 then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  eta:=eta->0;
  edges_acc:=array_append(edges_acc,jsonb_build_array(jsonb_build_object('source_key',e->'position_key','target_key',e->'target_key','size_id',e->'size_id',
   'input_qty',cp7_analysis_native.fact(e->>'input_pcs','PCS',e->'refs'),
   'projected_output_qty',cp7_analysis_native.fact(e->>'projected_good_pcs','PCS',e->'refs',plan_aids),
   'match',e->'match','eligible_at',eta->'eta','assumption_ids',plan_aids,'refs',e->'refs')));
 end loop;
 select coalesce(jsonb_agg(x.value order by p.ordinality,x.ordinality),'[]'::jsonb)into edges
  from unnest(edges_acc)with ordinality p(items,ordinality)cross join lateral jsonb_array_elements(p.items)with ordinality x;
 select coalesce(jsonb_object_agg(i.k,i.v),'{}'::jsonb)into inputs_by_source from(
  select x->>'source_key'k,jsonb_agg(x->'input_qty'->'value')v from jsonb_array_elements(edges)x where x->>'source_key'is not null group by x->>'source_key')i;
 for p in select value from jsonb_array_elements(coalesce(wip->'positions','[]'))
  where value->'eligible_company_wip'='true'::jsonb and cp7_wip.pcs(value->'remaining_pcs')>0 loop
  eta:=etas_by_position->(p->>'key');
  if jsonb_array_length(eta)>1 then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  eta:=eta->0;source_inputs:=inputs_by_source->(p->>'key');
  select sum(i.qty::numeric)into allocated from jsonb_array_elements_text(coalesce(source_inputs,'[]'))i(qty);
  sources_acc:=array_append(sources_acc,jsonb_build_array(jsonb_build_object('source_key',p->'key','size_id',p->'size_id','stage',p->'stage',
   'supply_kind',case when directed_source_keys?(p->>'key')then 'DIRECTED'else 'CANDIDATE'end,
   'physical_remaining',cp7_analysis_native.fact(p->>'remaining_pcs','PCS',p->'refs'),
   'eligible_input',cp7_analysis_native.fact(p->'projection'->>'eligible_input_pcs','PCS',p->'refs',plan_aids),
   'eligible_projected',cp7_analysis_native.fact(p->'projection'->>'projected_good_pcs','PCS',p->'refs',plan_aids),
   'allocated',cp7_analysis_native.fact(case when allocation_known then coalesce(allocated,0)::text else null end,'PCS',p->'refs'),
   'eta',eta->'eta','eta_basis',case when eta->>'status'='CONDITIONAL'then 'ASSUMED'when eta->>'status'='KNOWN'then 'CONFIRMED_PLAN'else 'UNKNOWN'end,'refs',p->'refs')));
 end loop;
 for part in select value from jsonb_array_elements(c->'fabric_source'->'selected')loop
  if known_targets?(part->>'target_key')then
   fabric_assumptions:=array_append(fabric_assumptions,cp7_analysis_stage.fabric_assumption(part));
  end if;
 end loop;
 for k,part in select key,value from jsonb_each(jsonb_build_object('native_operational',c->'facts','native_production',c->'production_sources'->'facts',
  'native_matching',c->'matching_products','planning_profiles',c->'profiles','production_policy',c->'production_policies'->'rows',
  'selected_schedule',c->'schedule','dated_capacity_clock',c->'planning_time_bucket','analysis_engine',c->'analysis_engine_signature',
  'native_material_requirements',(c->'material_source')-'captured_at',
  'selected_fabric_requirements',(c->'fabric_source')-'captured_at'))loop
  part_hash:=encode(extensions.digest(convert_to(part::text,'UTF8'),'sha256'),'hex');
  if k in('native_operational','native_production')then
   with recursive objects(value)as(select part union all
    select x.value from objects o cross join lateral jsonb_each(case when jsonb_typeof(o.value)='object'then o.value else '{}'end)x
    where jsonb_typeof(x.value)='object')
   select coalesce(sum(jsonb_array_length(x.value)),0)::integer into part_count
    from objects o cross join lateral jsonb_each(case when jsonb_typeof(o.value)='object'then o.value else '{}'end)x
    where jsonb_typeof(x.value)='array';
  else part_count:=case jsonb_typeof(part)when 'array'then jsonb_array_length(part)when 'object'then 1 else 0 end;end if;
  count_facts:=count_facts+part_count;
  dependencies:=dependencies||jsonb_build_array(jsonb_build_object('domain',k,'revision',part_hash,
   'completeness',case when complete then 'COMPLETE'else 'PARTIAL'end,'fact_count',part_count,'source_hash',part_hash));
 end loop;
 select sum((x->>'existing_load_minutes')::numeric)into load from jsonb_array_elements(coalesce(scenario->'capacity'->'inputs'->'windows','[]'))x;
 -- Per-target arrays: their sentinel (or nothing), in build's order.
 assumptions:=schedule_assumption||cp7_analysis_stage.sentinel(meta,tag,'assumptions')||to_jsonb(fabric_assumptions);
 select coalesce(jsonb_agg(x.value order by p.ordinality,x.ordinality),'[]'::jsonb)into sources
  from unnest(sources_acc)with ordinality p(items,ordinality)cross join lateral jsonb_array_elements(p.items)with ordinality x;
 recommendations:=cp7_analysis_stage.sentinel(meta,tag,'recommendations');actions:=cp7_analysis_stage.sentinel(meta,tag,'actions');
 timeline:=cp7_analysis_stage.sentinel(meta,tag,'timeline');models:=cp7_analysis_stage.sentinel(meta,tag,'models');
 materials:=case when meta->'materials_null'='true'::jsonb then null else cp7_analysis_stage.sentinel(meta,tag,'materials')end;
 metrics:=cp7_analysis_stage.sentinel(meta,tag,'metrics');warnings:=warnings0||cp7_analysis_stage.sentinel(meta,tag,'warnings');
 v:=jsonb_build_object('contract_version','cp7.analysis.v2','run_id',p_run,'status',case when complete then 'PARTIAL'else 'BLOCKED'end,
  'snapshot',jsonb_build_object('snapshot_id',c->>'captured_at','effective_as_of',c->>'captured_at','known_as_of',c->>'captured_at','generated_at',c->>'captured_at','timezone','Asia/Jakarta',
   'knowledge_mode','CURRENT','capture_complete',complete,'fact_count',count_facts,'source_hash',hash),
  'versions',jsonb_build_object('engine',c->'analysis_engine_signature','policy',cp7_supply_native.fingerprint(c),'models','policy-gated-dated-model-target-2',
   'template','native-report-1','access_epoch',encode(extensions.digest(convert_to(a::text,'UTF8'),'sha256'),'hex')),
  'scope',jsonb_build_object('actor_scope_id',a->>'actor','allocation_scope_id','GLOBAL_NATIVE_PLANNING','display_filter','ALL'),
  'quality',jsonb_build_object('quantity',case when complete then 'COMPLETE'else 'UNKNOWN'end,
   'demand',case when jsonb_array_length(recommendations)=0 or meta->'demand_unknown'='true'::jsonb then 'UNKNOWN'else 'ASSUMED'end,
   'identity',case when identity_unknown then 'UNKNOWN'when complete then 'COMPLETE'else 'UNKNOWN'end,
   'timing',case when scenario->'capacity'->>'status'='SCENARIO'then 'ASSUMED'else 'UNKNOWN'end,'materials','UNKNOWN',
   'capacity',case when scenario->'capacity'->>'status'='SCENARIO'then 'ASSUMED'else 'UNKNOWN'end,'financial','UNKNOWN'),
  'scenario',jsonb_build_object('id',coalesce(c->'schedule'->>'plan_id','unreviewed-'||hash),'version',scenario_revision,'kind','CONDITIONAL','assumption_ids',plan_aids),
  'sources',sources,'recommendations',recommendations,'timeline',timeline,'actions',actions,'financial_readiness','BLOCKED',
  'stale',jsonb_build_object('is_stale',false,'reasons','[]'::jsonb),'assumptions',assumptions,'dependencies',dependencies,
  'policy_basis',jsonb_build_object('lead_time_new_days',cp7_analysis_native.fact(null,'DAY','[]'),'review_days',cp7_analysis_native.fact(null,'DAY','[]'),
   'buffer_mode','DAYS','buffer_days',cp7_analysis_native.fact(null,'DAY','[]'),'service_target',cp7_analysis_native.fact(null,'PROBABILITY','[]'),
   'rounding_multiple',cp7_analysis_native.fact(null,'PCS','[]')),
  'demand_models',models,'material_needs',materials,
  'capacity_checks',jsonb_build_array(jsonb_build_object('stage','SELECTED_HOMOGENEOUS_CENTRE','calendar_version',coalesce(c->'schedule'->>'plan_id','UNREVIEWED'),
   'available',cp7_analysis_native.fact(scenario->'capacity'->>'capacity_pcs','PCS',plan_refs,plan_aids),
   'existing_load',cp7_analysis_native.fact(load::text,'MINUTE',plan_refs,plan_aids),'feasible_new',cp7_analysis_native.fact(null,'PCS',plan_refs),
   'status',case when scenario->'capacity'->>'status'='SCENARIO'then 'ASSUMED'else 'UNKNOWN'end)),
  'metrics',metrics,'plan_comparisons','[]'::jsonb,'generation_warnings',warnings,'allocation_edges',edges);
 return cp7_analysis_native.finance_apply(v,c);
end $$;

create or replace function cp7_schedule_staged_review.workspace(p_source_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r record;c jsonb;hash text;plan jsonb;outcome jsonb;
 p jsonb;bound_id text;bound_root text;model text;choices jsonb;requirements jsonb:='[]';
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 select j.run_id id,j.id job_id,j.state job_state,j.query,j.reference facts,j.captured_at,j.source_hash analysis_source_hash,
  cp7_supply_native.fingerprint(j.reference)dependency_hash,
  jsonb_build_object('wip',cp7_wip.normalize_production(j.reference->'production_sources'))result
 into r from cp7_analysis_stage.jobs j where j.request_id=p_source_request and j.actor=(a->>'actor')::uuid and j.state in('RUNNING','DONE','FAILED');
 if r.id is null then raise exception using errcode='42501',message='CP7_SCHEDULE_STAGED_RUN_UNAVAILABLE';end if;
 perform cp7_analysis_stage.require_kept(r.job_id);
 c:=cp7_bounded_analysis_stage.source_for(r.facts,r.query);hash:=cp7_supply_native.fingerprint(c);plan:=cp7_schedule_native.source_at((c->>'captured_at')::timestamptz);
 -- Form guidance belongs to the immutable source being reviewed. A fresh
 -- source check must not silently rebind quantities or an unfinished form.
 for p in select value from jsonb_array_elements(r.result->'wip'->'positions')
  where cp7_schedule_native.route(value->>'stage')is not null and cp7_wip.pcs(value->'remaining_pcs')>0
  order by value->>'key'loop
  bound_id:=case split_part(p->>'pool_key',':',1)
   when 'OPEN'then(select x->>'product_id'from jsonb_array_elements(r.facts->'production_sources'->'facts'->'other'->'origins')x
    where x->>'id'=split_part(p->>'pool_key',':',2))
   when 'NONPO'then(select x->>'product_id'from jsonb_array_elements(r.facts->'production_sources'->'facts'->'other'->'bs')x
    where x->>'id'=split_part(p->>'pool_key',':',2))else null end;
  select coalesce(x.identity_root_id,x.id)::text into bound_root from erp.products x
   where x.id::text=bound_id and x.created_at<=(r.facts->>'captured_at')::timestamptz;
  model:=cp7_schedule_native.position_model(r.facts,p);
  select coalesce(jsonb_agg(jsonb_build_object('target_key',(x->>'root_id')||':'||(x->>'size_id'),
   'product_version_id',x->'id','sku',x->'sku','product_name',x->'product_name')order by x->>'root_id'),'[]')into choices
   from jsonb_array_elements(r.facts->'facts'->'products')x
   where p->'eligible_company_wip'='true'::jsonb and x->>'size_id'=p->>'size_id'and x->>'model_id'=model
    and(bound_root is null or x->>'root_id'=bound_root);
  requirements:=requirements||jsonb_build_array(jsonb_build_object('position_key',p->'key','pool_key',p->'pool_key',
   'stage',p->'stage','size_id',p->'size_id','ownership',p->'ownership','eligible_company_wip',p->'eligible_company_wip',
   'remaining_pcs',p->'remaining_pcs','remaining_route',cp7_schedule_native.route(p->>'stage'),'target_candidates',choices));
 end loop;
 outcome:=jsonb_build_object('contract_version','cp7.planning-schedule-staged.v1','source_run',r.id,'source_request_id',p_source_request,'analysis_state',r.job_state,'current_source_hash',hash,
  'source_hash',r.dependency_hash,'captured_at',cp7_planning.utc(r.captured_at),'staged_review_contract','cp7.schedule-staged-review.v1','analysis_source_hash',r.analysis_source_hash,'history_capture_state',r.facts->'status','production_capture_state',r.result#>'{wip,status}','position_requirements',requirements,
  'source_state',case when hash=r.dependency_hash and cp7_analysis_native.fingerprint(c)=r.analysis_source_hash then 'UNCHANGED'else 'ARCHIVED_STALE'end,
  'plan',plan,'revision',coalesce(plan->>'revision','0'),
  'plan_state',case when plan='null'::jsonb then 'UNREVIEWED'when plan->>'source_hash'=hash then 'SELECTED_ASSUMPTIONS'else 'SOURCE_CHANGED'end,
  'production_go',false);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 if r.facts->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'then
  outcome:=outcome||jsonb_build_object('contract_version','cp7.planning-schedule-staged-bounded.v1',
   'bounded_request_contract',r.facts->'bounded_request_contract','bounded_reference_contract',r.facts->'bounded_reference_contract',
   'history_input_coverage',r.facts#>'{bounded_history_inputs,coverage}');end if;
 if r.facts->>'bounded_request_contract'='cp7.bounded-analysis-request.v2'then
  outcome:=outcome||jsonb_build_object('contract_version','cp7.planning-schedule-staged-bounded.v2',
   'bounded_request_contract',r.facts->'bounded_request_contract','bounded_reference_contract',r.facts->'bounded_reference_contract',
   'history_input_coverage',cp7_frozen_analysis_units_v2.coverage(r.job_id));end if;
 return outcome;
end $$;

create or replace function cp7_schedule_staged_review.save(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_schedule_native.commands%rowtype;run record;
 p cp7_schedule_native.plans%rowtype;c jsonb;wip jsonb;hash text;revision bigint;expected bigint;reason text;config jsonb;outcome jsonb;
 selected jsonb;position jsonb;bound_id text;bound_root text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(true);if p_request is null then raise exception 'CP7_SCHEDULE_REQUEST_REQUIRED';end if;
 perform cp7_wip.fields(p_payload,array['source_run','source_hash','expected_revision','config','reason','staged_review_contract']);
 if p_payload->>'staged_review_contract'is distinct from'cp7.schedule-staged-review.v1'then raise exception 'CP7_SCHEDULE_STAGED_CONTRACT';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:SCHEDULE:REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 select *into old from cp7_schedule_native.commands where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if old.payload<>p_payload then raise exception 'CP7_SCHEDULE_REQUEST_CHANGED';end if;return old.result;
 end if;
 if jsonb_typeof(p_payload->'expected_revision')is distinct from 'string'
  or p_payload->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'
  or jsonb_typeof(p_payload->'source_hash')is distinct from 'string'or p_payload->>'source_hash'!~'^[0-9a-f]{64}$'then
  raise exception 'CP7_SCHEDULE_REVIEW';end if;
 expected:=(p_payload->>'expected_revision')::bigint;
 perform pg_advisory_xact_lock(hashtextextended('CP7:SCHEDULE:GLOBAL',0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 select coalesce(max(x.revision),0)into revision from cp7_schedule_native.plans x;
 if expected<>revision then raise exception 'CP7_SCHEDULE_REVISION_CHANGED';end if;
 select j.run_id id,j.id job_id,j.state job_state,j.reference facts,j.query,j.source_hash analysis_source_hash,
  cp7_supply_native.fingerprint(j.reference)dependency_hash
 into run from cp7_analysis_stage.jobs j where j.run_id=(p_payload->>'source_run')::uuid
  and j.actor=(a->>'actor')::uuid and j.state in('RUNNING','DONE','FAILED');
 if run.id is null then raise exception using errcode='42501',message='CP7_SCHEDULE_STAGED_RUN_UNAVAILABLE';end if;
 perform cp7_analysis_stage.require_kept(run.job_id);
 c:=cp7_bounded_analysis_stage.source_for(run.facts,run.query);hash:=cp7_supply_native.fingerprint(c);
 if hash<>run.dependency_hash or hash<>p_payload->>'source_hash'
  or cp7_analysis_native.fingerprint(c)<>run.analysis_source_hash then raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';end if;
 wip:=cp7_wip.normalize_production(c->'production_sources');config:=cp7_schedule_native.validate(p_payload->'config',c,wip);
 -- A selected destination is metadata, never authority to move a physically
 -- bound opening/non-PO source to a different product root with the same model.
 for selected in select value from jsonb_array_elements(config->'positions')where value->'target_key'<>'null'::jsonb loop
  position:=(select value from jsonb_array_elements(wip->'positions')where value->>'key'=selected->>'position_key');
  bound_id:=case split_part(position->>'pool_key',':',1)
   when 'OPEN'then(select x->>'product_id'from jsonb_array_elements(c->'production_sources'->'facts'->'other'->'origins')x
    where x->>'id'=split_part(position->>'pool_key',':',2))
   when 'NONPO'then(select x->>'product_id'from jsonb_array_elements(c->'production_sources'->'facts'->'other'->'bs')x
    where x->>'id'=split_part(position->>'pool_key',':',2))else null end;
  select coalesce(x.identity_root_id,x.id)::text into bound_root from erp.products x
   where x.id::text=bound_id and x.created_at<=(c->>'captured_at')::timestamptz;
  if bound_root is not null and selected->>'target_key'<>bound_root||':'||(position->>'size_id')then
   raise exception 'CP7_SCHEDULE_NATIVE_TARGET_BOUND';end if;
 end loop;
 reason:=btrim(p_payload->>'reason');if jsonb_typeof(p_payload->'reason')is distinct from 'string'or reason is null or length(reason)not between 1 and 1000 then
  raise exception 'CP7_SCHEDULE_REASON';end if;
 insert into cp7_schedule_native.plans(revision,source_run,source_hash,config,reason,actor,request_id)
 values(revision+1,run.id,hash,config,reason,(a->>'actor')::uuid,p_request)returning *into p;
 outcome:=jsonb_build_object('contract_version','cp7.planning-schedule-staged-outcome.v1','plan_id',p.id,'revision',p.revision::text,
  'source_hash',hash,'request_id',p_request,'quality','SELECTED_ASSUMPTIONS','staged_review_contract','cp7.schedule-staged-review.v1','source_run',run.id,'production_go',false);
 if run.facts->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'then
  outcome:=outcome||jsonb_build_object('contract_version','cp7.planning-schedule-staged-bounded-outcome.v1',
   'bounded_request_contract',run.facts->'bounded_request_contract','bounded_reference_contract',run.facts->'bounded_reference_contract');end if;
 if run.facts->>'bounded_request_contract'='cp7.bounded-analysis-request.v2'then
  outcome:=outcome||jsonb_build_object('contract_version','cp7.planning-schedule-staged-bounded-outcome.v2',
   'bounded_request_contract',run.facts->'bounded_request_contract','bounded_reference_contract',run.facts->'bounded_reference_contract');end if;
 insert into cp7_schedule_native.commands(actor,request_id,payload,result)values((a->>'actor')::uuid,p_request,p_payload,outcome);
 if cp7_supply_native.fingerprint(cp7_bounded_analysis_stage.source_for(run.facts,run.query))<>hash then
  raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';
 end if;
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_SCHEDULE_ACCESS_CHANGED';end if;
 return outcome;
end $$;
