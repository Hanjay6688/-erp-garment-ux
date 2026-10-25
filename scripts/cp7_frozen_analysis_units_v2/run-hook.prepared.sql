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
