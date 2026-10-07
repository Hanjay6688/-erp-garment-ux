-- P19: staged background analysis for up to 5,000 Native planning targets
-- (docs/cp7/p19/P19_STAGED_5000_20261007.md §10). The single capture path
-- (cp7_analysis_native.capture/serve, the analysis jobs, manifest and
-- segments) and every cap of it are unchanged. A staged run is NEVER inserted
-- into cp7_analysis_native.runs: every existing whole reader finds no such run
-- and refuses it as an unknown run (fail closed by construction).
-- A job captures ONE reference (the operational source at the job's bounds,
-- finance DEFERRED) and computes the same compiler in units, each an ordinary
-- authenticated request under the unchanged 8 s statement limit:
--   HIST_PREP -> HIST_EVENTS*k -> HIST_VALIDATE -> HIST_ROWS*k -> HIST_STOCK*k
--   -> BASE_ROWS*k -> SUPPLY -> SCENARIO -> NET_PREP -> NET_TARGETS*k
--   -> NET_PAIRS*k -> NET_PLAN -> [ALLOC_PREP -> ALLOC_STEP*k -> ALLOC_FINAL]
--   -> NET_ROWS*k -> FABRIC_PLAN -> ANA_TARGETS*k -> ANA_META -> PAGES*k
--   -> PAGE_INDEX
-- Every unit reads only the stored reference and earlier units' immutable
-- rows, so no unit can mix source versions. No unit builds the whole analysis
-- text or the whole Original: ANA_TARGETS stores every target's items of each
-- per-target array as canonical jsonb text with its UTF8 size; ANA_META stores
-- the header (the Original without the per-target items, with the page cut);
-- PAGES stores byte-adaptive pages (contiguous targets in the job's loop
-- order, each page body within the existing 8,000,000-byte body bound, a
-- single oversize target refuses); PAGE_INDEX, written last, binds the header
-- and every page into the run's identity hash. The parity tests
-- (f05-staged-scenario, f05-staged-analysis, f05-staged-pages) prove that
-- header + pages reassemble, byte for byte, the analysis text and the Original
-- of the single build on the same reference, and that every refusal is the
-- single path's first refusal (SQLSTATE and message).
-- Loop bodies below are copies of history_build, the demand kernel's events
-- and rows statements, the baseline loop, the supply and schedule tails,
-- netting.build, allocate and build_operational, each over a part of the
-- input in the single path's order (the parity tests guard them). Caps that
-- bounded one call are bounds per unit here; the whole job keeps declared
-- caps (bounds()) and refuses loudly above them.
create schema cp7_analysis_stage authorization cp7_capture;
revoke all on schema cp7_analysis_stage from public,anon,authenticated,service_role;

-- --------------------------------------------------------------- scenario --
-- cp7_schedule_native.build(c,q) as units (it is the SCENARIO the netting
-- build reads, and its history/baseline/supply chain):
--   HIST_PREP -> HIST_EVENTS*k -> HIST_VALIDATE -> HIST_ROWS*k -> HIST_STOCK*k
--   -> BASE_ROWS*k -> SUPPLY -> SCENARIO
-- HIST_PREP: history_build's checks, targets, the clean-source checks and the
-- plan; HIST_EVENTS: one sale-id range's events (history_events), their
-- checks and selected/group events; HIST_VALIDATE: the events count and the
-- targets checks, then the first events refusal; HIST_ROWS: one key range's
-- availability grid and history rows; HIST_STOCK: one root-order range of
-- history_build's current stock; BASE_ROWS: one key range of the baseline
-- rows; SUPPLY: WIP normalization; SCENARIO: capacity windows and ETAs.
-- Each unit is a copy of the single path's statements over a part of the
-- input, in the single path's order, so the first refusal is the single
-- path's first refusal. A part is cut only where the result provably depends
-- on the part alone: a sale's events on that sale and its journals/returns, a
-- product's availability grid on its own root's stock rows, a history or
-- baseline row on its own target. Where that needs the source to be clean
-- (castable values, unique ids, no revision ties), HIST_PREP checks it; a
-- source that is not clean runs the single path's own function over the whole
-- input instead (exact, including its refusal; bounded by the statement limit).

-- True when v is SQL NULL or casts to t (the cast's own input function).
create function cp7_analysis_stage.castable(v text,t text)returns boolean
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$select v is null or pg_input_is_valid(v,t)$$;
-- history_events reads a sale's own rows only, and orders the result by
-- (lineage, revision). It can be cut by lineage (sale id ranges) when no cast
-- it makes can fail, sale/journal/return ids are unique strings, and no
-- (lineage, revision) can repeat: at most one original journal per sale
-- header and at most one inverse per journal (DESIGN in NOTES).
create function cp7_analysis_stage.events_clean(c jsonb)returns boolean
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare f jsonb:=c->'facts';k text;ok boolean;
begin
 foreach k in array array['sales','sale_journals','returns','return_journals']loop
  if f->k is not null and jsonb_typeof(f->k)<>'array'then return false;end if;
  select coalesce(bool_and(jsonb_typeof(x)='object'and jsonb_typeof(x->'id')='string'),true)and count(distinct x->>'id')=count(*)
   into ok from jsonb_array_elements(f->k)x;
  if not ok then return false;end if;
 end loop;
 select coalesce(bool_and(cp7_analysis_stage.castable(x->>'sale_date','timestamptz')and cp7_analysis_stage.castable(x->>'updated_at','timestamptz')
   and(x->>'status'is null or x->>'status'not in('DRAFT','CANCELLED')or cp7_analysis_stage.castable(x->>'revision','numeric'))),true)
  into ok from jsonb_array_elements(f->'sales')x;
 if not ok then return false;end if;
 select coalesce(bool_and(cp7_analysis_stage.castable(x->>'posting_at','timestamptz')and cp7_analysis_stage.castable(x->>'transaction_date','date')),true)
  into ok from jsonb_array_elements(f->'sale_journals')x;
 if not ok then return false;end if;
 select coalesce(bool_and(cp7_analysis_stage.castable(x->>'physical_at','timestamptz')and cp7_analysis_stage.castable(x->>'qty_pcs','numeric')),true)
  into ok from jsonb_array_elements(f->'returns')x;
 if not ok then return false;end if;
 select coalesce(bool_and(cp7_analysis_stage.castable(x->>'posting_at','timestamptz')),true)into ok from jsonb_array_elements(f->'return_journals')x;
 if not ok then return false;end if;
 -- No repeated (lineage, revision): one original journal per sale header,
 -- one inverse per journal.
 if exists(select 1 from jsonb_array_elements(f->'sale_journals')x where x->'reversal_of_id'='null'::jsonb group by x->>'sale_id'having count(*)>1)
  or exists(select 1 from jsonb_array_elements(f->'sale_journals')x where x->>'reversal_of_id'is not null group by x->>'reversal_of_id'having count(*)>1)
  then return false;end if;
 return true;
end $$;
-- history_availability computes each root's grid from that root's stock rows
-- and products only. Cut by root when no cast it makes can fail and no two
-- sellable movements share an id (the intraday order ties on it otherwise).
create function cp7_analysis_stage.availability_clean(c jsonb,q jsonb)returns boolean
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare ok boolean;
begin
 if c->'facts'->'stock'is not null and jsonb_typeof(c->'facts'->'stock')<>'array'then return false;end if;
 if not(cp7_analysis_stage.castable(q->>'from_date','date')and cp7_analysis_stage.castable(q->>'through_date','date'))then return false;end if;
 select coalesce(bool_and(cp7_analysis_stage.castable(m->>'physical_at','timestamptz')and cp7_analysis_stage.castable(m->>'book_order','numeric')
   and cp7_analysis_stage.castable(m->>'qty_signed','numeric')and m->>'id'is not null),true)and count(distinct m->>'id')=count(*)
  into ok from jsonb_array_elements(c->'facts'->'stock')m where m->>'quality_grade'in('GRADE_A','GRADE_B');
 if not ok then return false;end if;
 select coalesce(bool_and(cp7_analysis_stage.castable(p->>'established_at','timestamptz')),true)into ok
  from jsonb_array_elements(c->'facts'->'products')p;
 return ok;
end $$;
-- history_build up to its demand kernel call and the demand kernel up to its
-- events check, in their order. The single call's caps (products x days
-- 100000, targets 1000, availability 100000, grid 100000) are job bounds
-- here (job targets, job history cells); the kernel's own 3660-day rule and
-- its 50000-event cap are kept. Returns the targets exactly as history_build
-- builds them (same statement, same order), the products in the order of
-- history_build's stock loop (same statement), the cut of the sale ids and,
-- for a source that is not clean, the whole events/availability.
create function cp7_analysis_stage.history_prep(c jsonb,q jsonb,p_targets integer,p_cells bigint,p_sales integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare cells bigint;hash text;targets jsonb;events jsonb;avail jsonb;v jsonb;known timestamptz;effective timestamptz;lo date;hi date;
 p jsonb;stock_order jsonb[]:='{}';events_clean boolean;avail_clean boolean;cuts jsonb;
begin
 if c->>'status'is distinct from 'COMPLETE'then raise exception 'CP7_PLANNING_CAPTURE_INCOMPLETE';end if;
 -- The single call's grid expression (same casts, same errors), its bound per job.
 cells:=jsonb_array_length(c->'facts'->'products')*((q->>'through_date')::date-(q->>'from_date')::date+1);
 if jsonb_array_length(c->'facts'->'products')>p_targets then raise exception 'CP7_ANALYSIS_STAGED_TARGET_LIMIT';end if;
 if cells>p_cells then raise exception 'CP7_PLANNING_HISTORY_GRID_LIMIT';end if;
 hash:=encode(extensions.digest(convert_to((c->'facts')::text,'UTF8'),'sha256'),'hex');
 targets:=(select coalesce(jsonb_agg(jsonb_build_object('key',(value->>'root_id')||':'||(value->>'size_id'),
   'size_id',value->>'size_id','current_group_key',coalesce(value->'commercial'->0->>'sku_id',value->>'root_id'),
   'refs',jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',value->>'id','revision','1')))order by value->>'root_id'),'[]')from jsonb_array_elements(c->'facts'->'products'));
 events_clean:=cp7_analysis_stage.events_clean(c);
 if not events_clean then events:=cp7_planning.history_events(c);end if;
 avail_clean:=cp7_analysis_stage.availability_clean(c,q);
 if not avail_clean then avail:=cp7_planning.history_availability(c,q);end if;
 v:=jsonb_build_object('contract_version','cp7.demand-input.v1','snapshot_id',hash,
  'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','known_as_of',c->>'captured_at','effective_as_of',c->>'captured_at',
  'from_date',q->'from_date','through_date',q->'through_date','history_complete',true,'group_mode',q->'group_mode',
  'targets',targets,'events','[]'::jsonb,'availability','[]'::jsonb);
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','known_as_of','effective_as_of','from_date','through_date','history_complete','group_mode','targets','events','availability']);
 perform cp7_demand.context(v,'cp7.demand-input.v1');
 known:=cp7_demand.instant(v->'known_as_of');effective:=cp7_demand.instant(v->'effective_as_of');
 lo:=cp7_demand.day(v->'from_date');hi:=cp7_demand.day(v->'through_date');
 if hi<lo or hi-lo>3660 or hi>=(effective at time zone 'Asia/Jakarta')::date then raise exception 'CP7_DEMAND_COMPLETE_DAYS_REQUIRED';end if;
 if jsonb_typeof(v->'history_complete') is distinct from 'boolean' or v->>'group_mode' not in ('AS_SOLD','RESTATED') or v->>'group_mode' is null then raise exception 'CP7_DEMAND_POLICY';end if;
 perform cp7_demand.items(v->'targets',p_targets);
 -- history_build's stock loop order (same statement).
 for p in select value from jsonb_array_elements(c->'facts'->'products')order by value->>'root_id'loop
  stock_order:=array_append(stock_order,p);
 end loop;
 -- Sale id ranges of at most p_sales sales each (ids are unique strings when clean).
 if events_clean then
  select coalesce(jsonb_agg(jsonb_build_array(f.lo,f.hi)order by f.k),'[]')into cuts from(
   select(s.i-1)/p_sales k,min(s.id)lo,max(s.id)hi from(select x->>'id' id,row_number()over(order by x->>'id')i
    from jsonb_array_elements(c->'facts'->'sales')x)s group by 1)f;
 end if;
 return jsonb_build_object('hash',hash,'targets',targets,'stock_order',to_jsonb(stock_order),'events_clean',events_clean,'events',events,
  'availability_clean',avail_clean,'availability',avail,'cuts',coalesce(cuts,'[]'::jsonb),'from',lo,'through',hi,
  'baseline_hash',encode(extensions.digest(convert_to(jsonb_build_object('native',c->'facts','profiles',c->'profiles','production_policies',c->'production_policies'->'rows')::text,'UTF8'),'sha256'),'hex'));
end $$;
-- The facts of the sales with ids lo..hi and only the rows history_events
-- joins to them: their headers' journals and the inverses of those, their
-- returns and those returns' journals and inverses (array order kept).
create function cp7_analysis_stage.event_facts(c jsonb,lo text,hi text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare f jsonb:=c->'facts';sales jsonb;headers jsonb;items jsonb;sj jsonb;sj_ids jsonb;r jsonb;returns_ids jsonb;rj jsonb;rj_ids jsonb;
begin
 select coalesce(jsonb_agg(x order by o),'[]'),coalesce(jsonb_object_agg(x->>'id',true),'{}'),
   coalesce(jsonb_object_agg(x->>'sale_id',true)filter(where x->>'sale_id'is not null),'{}')
  into sales,items,headers from jsonb_array_elements(f->'sales')with ordinality a(x,o)where x->>'id'between lo and hi;
 select coalesce(jsonb_object_agg(x->>'id',true),'{}')into sj_ids from jsonb_array_elements(f->'sale_journals')x where headers?(x->>'sale_id');
 select coalesce(jsonb_agg(x order by o),'[]')into sj from jsonb_array_elements(f->'sale_journals')with ordinality a(x,o)
  where headers?(x->>'sale_id')or sj_ids?(x->>'reversal_of_id');
 select coalesce(jsonb_agg(x order by o),'[]'),coalesce(jsonb_object_agg(x->>'return_id',true)filter(where x->>'return_id'is not null),'{}')
  into r,returns_ids from jsonb_array_elements(f->'returns')with ordinality a(x,o)where items?(x->>'sale_item_id');
 select coalesce(jsonb_object_agg(x->>'id',true),'{}')into rj_ids from jsonb_array_elements(f->'return_journals')x where returns_ids?(x->>'return_id');
 select coalesce(jsonb_agg(x order by o),'[]')into rj from jsonb_array_elements(f->'return_journals')with ordinality a(x,o)
  where returns_ids?(x->>'return_id')or rj_ids?(x->>'reversal_of_id');
 return jsonb_build_object('facts',jsonb_build_object('sales',sales,'sale_journals',sj,'returns',r,'return_journals',rj));
end $$;
-- cp7_demand.history's events check (verbatim) for one lineage chunk of the
-- events, then its selected events and group events for those lineages.
-- Every check of an event reads that event, its lineage's flags (a lineage is
-- never cut), the clock and the targets, so the first refusal of the first
-- chunk that has one is the kernel's first events refusal. The kernel checks
-- the events count and the targets BEFORE the events, so a chunk does not
-- raise: it returns its first refusal (SQLSTATE, message) and HIST_VALIDATE
-- raises it after those checks. targets: the target array (the map below is
-- the kernel's map whenever its targets check passes; keys it would refuse
-- are left out here because then the targets check refuses first).
create function cp7_analysis_stage.events_validate(v jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare k text; r jsonb; t jsonb; targets jsonb; i bigint; known timestamptz; effective timestamptz; lo date; hi date;
 qty numeric; returns_qty numeric; event_conflict boolean[]; event_identity boolean[];
 clean boolean; latest jsonb; groups_out jsonb; selected_events jsonb; by_target jsonb;
begin
 known:=cp7_demand.instant(v->'known_as_of');effective:=cp7_demand.instant(v->'effective_as_of');
 lo:=cp7_demand.day(v->'from_date');hi:=cp7_demand.day(v->'through_date');
 select coalesce(jsonb_object_agg(x.value->>'key',x.value),'{}') into targets from jsonb_array_elements(v->'targets')x where x.value->>'key'is not null;
 begin
 select coalesce(array_agg(z.conflict order by z.n),'{}'),coalesce(array_agg(coalesce(z.identity,false) order by z.n),'{}')
 into event_conflict,event_identity from(
  select y.n,y.r<>first_value(y.r)over(partition by jsonb_build_array(y.r->>'lineage_key',y.r->>'revision')::text order by y.n) conflict,
   y.incut and(y.fl->>'target_key'<>y.r->>'target_key' or y.fl->>'size_id'<>y.r->>'size_id') identity
  from(select w.n,w.r,w.incut,first_value(w.r)over(partition by w.r->>'lineage_key',w.incut order by w.n) fl from(
    select x.n,x.r,case when pg_input_is_valid(x.r->>'known_at','timestamptz') and pg_input_is_valid(x.r->>'effective_at','timestamptz')
     then not((x.r->>'known_at')::timestamptz>known or(x.r->>'effective_at')::timestamptz>effective) else false end incut
    from jsonb_array_elements(v->'events')with ordinality x(r,n))w)y)z;
 -- The demand kernel's fast path (verbatim), then its row loop when needed.
 select coalesce(bool_and(coalesce(case when (case when jsonb_typeof(x.r)='object' then x.r-array['lineage_key','revision','known_at','effective_at','posted_at','status','target_key','size_id','sold_group_key','qty_pcs','returned_pcs','refs']='{}'::jsonb and x.r?&array['lineage_key','revision','known_at','effective_at','posted_at','status','target_key','size_id','sold_group_key','qty_pcs','returned_pcs','refs'] else false end) and (jsonb_typeof(x.r->'lineage_key')='string' and length(x.r->'lineage_key'#>>'{}') between 1 and 200 and btrim(x.r->'lineage_key'#>>'{}')=(x.r->'lineage_key'#>>'{}')) and (jsonb_typeof(x.r->'revision')='string' and (x.r->'revision'#>>'{}')~'^(0|[1-9][0-9]{0,29})$') and (case when jsonb_typeof(x.r->'refs')='array' and jsonb_array_length(x.r->'refs')=1 then coalesce((case when jsonb_typeof((x.r->'refs'->0))='object' then (x.r->'refs'->0)-array['kind','id','revision']='{}'::jsonb and (x.r->'refs'->0)?&array['kind','id','revision'] else false end) and (jsonb_typeof((x.r->'refs'->0)->'kind')='string' and length((x.r->'refs'->0)->'kind'#>>'{}') between 1 and 200 and btrim((x.r->'refs'->0)->'kind'#>>'{}')=((x.r->'refs'->0)->'kind'#>>'{}')) and (jsonb_typeof((x.r->'refs'->0)->'id')='string' and length((x.r->'refs'->0)->'id'#>>'{}') between 1 and 200 and btrim((x.r->'refs'->0)->'id'#>>'{}')=((x.r->'refs'->0)->'id'#>>'{}')) and (jsonb_typeof((x.r->'refs'->0)->'revision')='string' and length((x.r->'refs'->0)->'revision'#>>'{}') between 1 and 200 and btrim((x.r->'refs'->0)->'revision'#>>'{}')=((x.r->'refs'->0)->'revision'#>>'{}')),false) when jsonb_typeof(x.r->'refs')='array' and jsonb_array_length(x.r->'refs') between 2 and 1000 then (select coalesce(bool_and(coalesce((case when jsonb_typeof(f.e)='object' then f.e-array['kind','id','revision']='{}'::jsonb and f.e?&array['kind','id','revision'] else false end) and (jsonb_typeof(f.e->'kind')='string' and length(f.e->'kind'#>>'{}') between 1 and 200 and btrim(f.e->'kind'#>>'{}')=(f.e->'kind'#>>'{}')) and (jsonb_typeof(f.e->'id')='string' and length(f.e->'id'#>>'{}') between 1 and 200 and btrim(f.e->'id'#>>'{}')=(f.e->'id'#>>'{}')) and (jsonb_typeof(f.e->'revision')='string' and length(f.e->'revision'#>>'{}') between 1 and 200 and btrim(f.e->'revision'#>>'{}')=(f.e->'revision'#>>'{}')),false)),false) and count(*)=count(distinct f.e) from jsonb_array_elements(x.r->'refs')f(e)) else false end) and (case when jsonb_typeof(x.r->'known_at')='string' and (x.r->'known_at'#>>'{}')~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$' then (case when left((x.r->'known_at'#>>'{}'),10)~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$' and pg_input_is_valid(left((x.r->'known_at'#>>'{}'),10),'date') then to_char(left((x.r->'known_at'#>>'{}'),10)::date,'YYYY-MM-DD')=left((x.r->'known_at'#>>'{}'),10) else false end) and substring((x.r->'known_at'#>>'{}'),12,2)::int<=23 and substring((x.r->'known_at'#>>'{}'),15,2)::int<=59 and substring((x.r->'known_at'#>>'{}'),18,2)::int<=59 and pg_input_is_valid((x.r->'known_at'#>>'{}'),'timestamptz') else false end) and (case when jsonb_typeof(x.r->'effective_at')='string' and (x.r->'effective_at'#>>'{}')~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$' then (case when left((x.r->'effective_at'#>>'{}'),10)~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$' and pg_input_is_valid(left((x.r->'effective_at'#>>'{}'),10),'date') then to_char(left((x.r->'effective_at'#>>'{}'),10)::date,'YYYY-MM-DD')=left((x.r->'effective_at'#>>'{}'),10) else false end) and substring((x.r->'effective_at'#>>'{}'),12,2)::int<=23 and substring((x.r->'effective_at'#>>'{}'),15,2)::int<=59 and substring((x.r->'effective_at'#>>'{}'),18,2)::int<=59 and pg_input_is_valid((x.r->'effective_at'#>>'{}'),'timestamptz') else false end) and (jsonb_typeof(x.r->'target_key')='string' and length(x.r->'target_key'#>>'{}') between 1 and 200 and btrim(x.r->'target_key'#>>'{}')=(x.r->'target_key'#>>'{}')) and (jsonb_typeof(x.r->'sold_group_key')='string' and length(x.r->'sold_group_key'#>>'{}') between 1 and 200 and btrim(x.r->'sold_group_key'#>>'{}')=(x.r->'sold_group_key'#>>'{}')) and (jsonb_typeof(x.r->'size_id')='string' and length(x.r->'size_id'#>>'{}') between 1 and 200 and btrim(x.r->'size_id'#>>'{}')=(x.r->'size_id'#>>'{}')) and (jsonb_typeof(x.r->'qty_pcs')='string' and (x.r->'qty_pcs'#>>'{}')~'^(0|[1-9][0-9]{0,29})$') and (jsonb_typeof(x.r->'returned_pcs')='string' and (x.r->'returned_pcs'#>>'{}')~'^(0|[1-9][0-9]{0,29})$') and x.r->>'status' in ('DRAFT','POSTED','CANCELLED') then (x.r->>'returned_pcs')::numeric<=(x.r->>'qty_pcs')::numeric and case when x.r->>'status'='POSTED' then case when (case when jsonb_typeof(x.r->'posted_at')='string' and (x.r->'posted_at'#>>'{}')~'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$' then (case when left((x.r->'posted_at'#>>'{}'),10)~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$' and pg_input_is_valid(left((x.r->'posted_at'#>>'{}'),10),'date') then to_char(left((x.r->'posted_at'#>>'{}'),10)::date,'YYYY-MM-DD')=left((x.r->'posted_at'#>>'{}'),10) else false end) and substring((x.r->'posted_at'#>>'{}'),12,2)::int<=23 and substring((x.r->'posted_at'#>>'{}'),15,2)::int<=59 and substring((x.r->'posted_at'#>>'{}'),18,2)::int<=59 and pg_input_is_valid((x.r->'posted_at'#>>'{}'),'timestamptz') else false end) then (x.r->>'posted_at')::timestamptz<=(x.r->>'effective_at')::timestamptz else false end else x.r->'posted_at'='null'::jsonb and (x.r->>'returned_pcs')::numeric=0 end and not event_conflict[x.n::int] and((x.r->>'known_at')::timestamptz>known or(x.r->>'effective_at')::timestamptz>effective or(targets->(x.r->>'target_key') is not null and targets->(x.r->>'target_key')->>'size_id'=(x.r->>'size_id') and not event_identity[x.n::int])) else false end,false)),true) into clean
  from jsonb_array_elements(v->'events')with ordinality x(r,n);
 if not clean then
 for r,i in select x.value,x.n from jsonb_array_elements(v->'events')with ordinality x(value,n) order by x.n loop
  perform cp7_wip.fields(r,array['lineage_key','revision','known_at','effective_at','posted_at','status','target_key','size_id','sold_group_key','qty_pcs','returned_pcs','refs']);
  k:=cp7_wip.key(r->'lineage_key');perform cp7_wip.pcs(r->'revision');perform cp7_wip.refs(r->'refs');
  perform cp7_demand.instant(r->'known_at');perform cp7_demand.instant(r->'effective_at');
  perform cp7_wip.key(r->'target_key');perform cp7_wip.key(r->'sold_group_key');perform cp7_wip.key(r->'size_id');
  qty:=cp7_wip.pcs(r->'qty_pcs');returns_qty:=cp7_wip.pcs(r->'returned_pcs');
  if r->>'status' is null or r->>'status' not in ('DRAFT','POSTED','CANCELLED') or returns_qty>qty then raise exception 'CP7_DEMAND_LIFECYCLE';end if;
  if r->>'status'='POSTED' then
   if cp7_demand.instant(r->'posted_at')>cp7_demand.instant(r->'effective_at') then raise exception 'CP7_DEMAND_POSTED_AT';end if;
  elsif r->'posted_at'<>'null'::jsonb or returns_qty<>0 then raise exception 'CP7_DEMAND_UNPOSTED_RETURN';end if;
  if event_conflict[i] then raise exception 'CP7_DEMAND_REVISION_CONFLICT';end if;
  if cp7_demand.instant(r->'known_at')>known or cp7_demand.instant(r->'effective_at')>effective then continue;end if;
  t:=targets->(r->>'target_key');
  if t is null or t->>'size_id'<>r->>'size_id' then raise exception 'CP7_DEMAND_TARGET_SIZE';end if;
  if event_identity[i] then raise exception 'CP7_DEMAND_LINEAGE_IDENTITY';end if;
 end loop;
 end if;
 exception when others then
  return jsonb_build_object('events',jsonb_array_length(v->'events'),'error',jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm));
 end;
 select coalesce(jsonb_object_agg(z.k,z.r),'{}') into latest from(
  select distinct on(x.r->>'lineage_key') x.r->>'lineage_key' k,x.r from jsonb_array_elements(v->'events')with ordinality x(r,n)
  where not((x.r->>'known_at')::timestamptz>known or (x.r->>'effective_at')::timestamptz>effective)
  order by x.r->>'lineage_key',(x.r->>'revision')::numeric desc,x.n)z;
 select coalesce(jsonb_agg(e.value order by e.key),'[]') into selected_events from jsonb_each(latest)e;
 select coalesce(jsonb_agg(jsonb_build_object('group_key',case when v->>'group_mode'='AS_SOLD' then e.value->>'sold_group_key' else targets->(e.value->>'target_key')->>'current_group_key' end,
   'size_id',e.value->'size_id','qty_pcs',e.value->'qty_pcs','lineage_key',e.value->'lineage_key','refs',e.value->'refs') order by e.key),'[]') into groups_out
 from jsonb_each(latest)e where e.value->>'status'='POSTED'
  and ((e.value->>'posted_at')::timestamptz at time zone 'Asia/Jakarta')::date between lo and hi;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}')into by_target from(
  select e.value->>'target_key' k,jsonb_agg(e.value order by e.key)v from jsonb_each(latest)e group by 1)f;
 return jsonb_build_object('events',jsonb_array_length(v->'events'),'selected_events',selected_events,'group_events',groups_out,'by_target',by_target);
end $$;
-- cp7_demand.history's events count check and targets check (verbatim), then
-- the first events refusal any chunk returned, in chunk order.
create function cp7_analysis_stage.history_validate(v jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare k text; t jsonb; i bigint; target_duplicate boolean[]; e jsonb;
begin
 -- cp7_demand.items(v->'events',50000) on the whole events array.
 if (v->>'events')::bigint>50000 then raise exception 'CP7_F04_ARRAY_LIMIT';end if;
 -- (availability 100000 and grid 100000: job bounds, checked in HIST_PREP)
 select coalesce(array_agg(z.dup order by z.n),'{}') into target_duplicate from(
  select x.n,count(*)over(partition by x.value->>'key' order by x.n rows unbounded preceding)>1 dup
  from jsonb_array_elements(v->'targets')with ordinality x(value,n))z;
 for t,i in select x.value,x.n from jsonb_array_elements(v->'targets')with ordinality x(value,n) order by x.n loop
  perform cp7_wip.fields(t,array['key','size_id','current_group_key','refs']);k:=cp7_wip.key(t->'key');
  perform cp7_wip.key(t->'size_id');perform cp7_wip.key(t->'current_group_key');perform cp7_wip.refs(t->'refs');
  if target_duplicate[i] then raise exception 'CP7_DEMAND_DUPLICATE_TARGET';end if;
 end loop;
 for e in select x.value from jsonb_array_elements(v->'errors')with ordinality x(value,o)order by x.o loop
  raise exception using errcode=e->>'sqlstate',message=e->>'message';
 end loop;
 return jsonb_build_object('key_order',(select coalesce(jsonb_agg(x.n order by x.t->>'key'),'[]')
   from jsonb_array_elements(v->'targets')with ordinality x(t,n)));
end $$;
-- The demand kernel's history rows (verbatim statement) for one chunk of
-- targets (in key order): their selected events and their availability rows.
-- Each row aggregates its own target's days only.
create function cp7_analysis_stage.history_rows(v jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare known timestamptz;lo date;hi date;rows_out jsonb;latest jsonb;
begin
 known:=cp7_demand.instant(v->'known_as_of');lo:=cp7_demand.day(v->'from_date');hi:=cp7_demand.day(v->'through_date');
 -- Every availability row history_build makes for a valid, unique target is
 -- valid (NOTES); a row that is not would be a broken invariant, never data.
 if exists(select 1 from jsonb_array_elements(v->'availability')x where not coalesce(jsonb_typeof(x)='object'and x?&array['target_key','date','revision','known_at','state','refs']
   and(x-array['target_key','date','revision','known_at','state','refs'])='{}'::jsonb and x->>'revision'='1'and x->>'known_at'=v->>'known_as_of'
   and x->>'state'in('AVAILABLE','STOCKOUT','UNKNOWN')and v->'keys'?(x->>'target_key'),false))
  then raise exception 'CP7_ANALYSIS_STAGE_INVARIANT';end if;
 latest:=v->'latest';
 with ev as materialized(select e.value ev_row from jsonb_each(latest)e),
 avs as materialized(select distinct on(jsonb_build_array(x.r->>'target_key',x.r->>'date')::text) jsonb_build_array(x.r->>'target_key',x.r->>'date')::text key,x.r value
  from jsonb_array_elements(v->'availability')with ordinality x(r,n) where not (x.r->>'known_at')::timestamptz>known
  order by jsonb_build_array(x.r->>'target_key',x.r->>'date')::text,(x.r->>'revision')::numeric desc,x.n),
 posted as(select ev.ev_row->>'target_key' tk,((ev.ev_row->>'posted_at')::timestamptz at time zone 'Asia/Jakarta')::date d,
   sum((ev.ev_row->>'qty_pcs')::numeric) q,sum((ev.ev_row->>'returned_pcs')::numeric) rq from ev where ev.ev_row->>'status'='POSTED' group by 1,2),
 drafts as(select ev.ev_row->>'target_key' tk,sum((ev.ev_row->>'qty_pcs')::numeric) q from ev where ev.ev_row->>'status'='DRAFT' group by 1),
 days as materialized(select x.n,x.target,g.d,a.value old,
   case when v->'history_complete'='true'::jsonb then coalesce(a.value->>'state','UNKNOWN') else 'UNKNOWN' end day_state,
   coalesce(p.q,0) day_qty,coalesce(p.rq,0) day_returns
  from jsonb_array_elements(v->'targets')with ordinality x(target,n)
  cross join lateral(select lo+s d from generate_series(0,hi-lo)s)g
  left join avs a on a.key=jsonb_build_array(x.target->>'key',g.d::text)::text
  left join posted p on p.tk=x.target->>'key' and p.d=g.d),
 per_target as(select days.n,days.target,sum(days.day_qty) total,coalesce(sum(days.day_qty)filter(where days.day_state='AVAILABLE'),0) observed_total,
   count(*)filter(where days.day_state='AVAILABLE') available_count,count(*)filter(where days.day_state='STOCKOUT') stockout_count,
   count(*)filter(where days.day_state not in('AVAILABLE','STOCKOUT')) unknown_count,
   jsonb_agg(jsonb_build_object('date',days.d::text,'state',days.day_state,'gross_observed_pcs',days.day_qty::text,'returned_pcs',days.day_returns::text,
    'training_pcs',case when days.day_state='AVAILABLE' then days.day_qty::text else null end,'availability_refs',days.old->'refs') order by days.d) day_rows
  from days group by days.n,days.target)
 select coalesce(jsonb_agg(jsonb_build_object('target_key',p.target->'key','size_id',p.target->'size_id','gross_observed_pcs',p.total::text,
   'draft_reserved_pcs',coalesce(dr.q,0)::text,'available_days',p.available_count,'stockout_days',p.stockout_count,'unknown_days',p.unknown_count,
   'calendar_sales_mean',case when v->'history_complete'='true'::jsonb then (p.total/(hi-lo+1))::text else null end,
   'available_sales_mean',case when p.available_count>0 then (p.observed_total/p.available_count)::text else null end,
   'demand_estimate_basis',case when p.available_count>0 then 'ASSUMED_AVAILABLE_DAYS_REPRESENTATIVE' else 'UNKNOWN' end,
   'lost_sales_pcs',null,'days',p.day_rows,'refs',p.target->'refs') order by p.target->>'key'),'[]') into rows_out
 from per_target p left join drafts dr on dr.tk=p.target->>'key';
 return rows_out;
end $$;
-- history_build after the demand kernel: its per-root stock sums and draft
-- lists over the whole capture, then its stock loop (verbatim) for the
-- products at loop positions lo..hi (products: that slice, in loop order).
-- The sums are the same rows summed exactly (numeric); only the reserve
-- anti-join is a set lookup (in PL/pgSQL the verbatim statement took 6.7 s
-- over 36000 stock rows, LOCAL). The first statement is history_build's own
-- first sum, so a value that cannot be cast fails as it does there; the second
-- sum casts a subset of those rows.
create function cp7_analysis_stage.history_stock(c jsonb,products jsonb,hash text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC' as $$
declare p jsonb;target text;refs jsonb;drafts jsonb;current_physical numeric;native_available numeric;availability jsonb;current_rows jsonb[]:='{}';
 available_by_root jsonb;physical_by_root jsonb;drafts_by_root jsonb;reserves jsonb;
begin
 with stock as materialized(select value m from jsonb_array_elements(c->'facts'->'stock'))
 select coalesce((select jsonb_object_agg(x.root_id,x.total)from(select m->>'root_id' root_id,sum((m->>'qty_signed')::numeric)total
   from stock where m->>'quality_grade'in('GRADE_A','GRADE_B')and m->>'root_id' is not null group by 1)x),'{}')
 into available_by_root;
 select coalesce(jsonb_object_agg(m->>'id',true),'{}')into reserves from jsonb_array_elements(c->'facts'->'stock')m
  where m->>'movement_type'='SALE_RESERVE'and m->>'id'is not null;
 select coalesce((select jsonb_object_agg(x.root_id,x.total)from(select s.m->>'root_id' root_id,sum((s.m->>'qty_signed')::numeric)total
   from jsonb_array_elements(c->'facts'->'stock')s(m) where s.m->>'quality_grade'in('GRADE_A','GRADE_B')and s.m->>'movement_type'<>'SALE_RESERVE'and s.m->>'root_id' is not null
    and not coalesce(reserves?(s.m->>'reversal_of_id'),false)group by 1)x),'{}')
 into physical_by_root;
 select coalesce(jsonb_object_agg(x.root_id,x.drafts),'{}')into drafts_by_root from(
  select value->>'root_id' root_id,jsonb_agg(jsonb_build_object('lineage_key',value->>'id','qty_pcs',value->>'qty_pcs',
   'refs',jsonb_build_array(jsonb_build_object('kind','SALE_ITEM','id',value->>'id','revision',value->>'revision')))order by value->>'id')drafts
  from jsonb_array_elements(c->'facts'->'sales')where value->>'status'='DRAFT'and value->>'root_id' is not null group by 1)x;
 for p in select x.value from jsonb_array_elements(products)with ordinality x(value,o)order by x.o loop
  target:=(p->>'root_id')||':'||(p->>'size_id');
  refs:=jsonb_build_array(jsonb_build_object('kind','PRODUCT','id',p->>'id','revision','1'));
  native_available:=coalesce((available_by_root->>(p->>'root_id'))::numeric,0);
  current_physical:=coalesce((physical_by_root->>(p->>'root_id'))::numeric,0);
  drafts:=coalesce(drafts_by_root->(p->>'root_id'),'[]');
  availability:=cp7_demand.availability(jsonb_build_object('contract_version','cp7.available-input.v1',
   'snapshot_id',hash,'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','target_key',target,'size_id',p->>'size_id',
   'fg_basis','ON_HAND_AFTER_POSTED','fg_pcs',current_physical::text,'open_drafts',drafts,
   'residual_future_pcs','0','refs',refs));
  if(availability->>'available_fg_pcs')::numeric<>native_available or native_available<0 then raise exception 'CP7_PLANNING_NATIVE_RESERVATION_MISMATCH';end if;
  current_rows:=array_append(current_rows,jsonb_build_object('target_key',target,'root_id',p->>'root_id',
   'size_id',p->>'size_id','sku',p->>'sku','product_name',p->>'product_name',
   'is_active',(p->>'is_active')::boolean,'grade_basis','NATIVE_SELLABLE_GRADE_A_AND_B','availability',availability,
   'projection_basis','CURRENT_STOCK_ONLY_NO_FORECAST','native_available_pcs',native_available::text,'refs',refs));
 end loop;
 return to_jsonb(current_rows);
end $$;
-- cp7_baseline_native.build's row loop (verbatim) for one chunk of history
-- rows (key order). current_stock: every current stock row, in order (the
-- loop's stock lookup reads the whole array). The maps are built at the
-- chunk's first row exactly as the single loop builds them at its first row.
create function cp7_analysis_stage.baseline_rows(c jsonb,history_rows jsonb,current_stock jsonb,hash text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare h jsonb:=jsonb_build_object('current_stock',current_stock);r jsonb;cfg jsonb;p jsonb;stock jsonb;estimate jsonb;target jsonb;manual jsonb;own jsonb;
 refs jsonb;profile_refs jsonb;total numeric;policy jsonb;state text;rows jsonb[]:='{}';root text;
 profiles jsonb;profiles_repeated jsonb;stocks jsonb;stocks_repeated jsonb;policies jsonb;
begin
 for r in select x.value from jsonb_array_elements(history_rows)with ordinality x(value,o)order by x.o loop
  root:=split_part(r->>'target_key',':',1);
  if profiles is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into profiles,profiles_repeated
    from(select x->>'root_id' k,count(*)n,(array_agg(x order by o))[1] v from jsonb_array_elements(c->'profiles')with ordinality a(x,o)
     where x->>'root_id'is not null group by 1)f;
  end if;
  if profiles_repeated?root then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  p:=profiles->root;
  if stocks is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into stocks,stocks_repeated
    from(select x->>'target_key' k,count(*)n,(array_agg(x order by o))[1] v from jsonb_array_elements(h->'current_stock')with ordinality a(x,o)
     where x->>'target_key'is not null group by 1)f;
  end if;
  if stocks_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  stock:=stocks->(r->>'target_key');
  refs:=r->'refs';cfg:=case when p->>'quality'='SELECTED_ASSUMPTION'then p->'config'else null end;
  profile_refs:=case when cfg is null then '[]'::jsonb else jsonb_build_array(jsonb_build_object('kind','PLANNING_PROFILE','id',p->>'profile_id','revision',p->>'revision'))end;
  select coalesce(sum((value->>'gross_observed_pcs')::numeric),0)into total from jsonb_array_elements(r->'days')where value->>'state'='AVAILABLE';
  own:=jsonb_build_object('available_total_pcs',total::text,'available_days',(r->>'available_days')::text,'capture_complete',true,'refs',refs);
  manual:=case when cfg->>'mean_mode'='SELECTED_MANUAL'then jsonb_build_object('daily_pcs',cfg->'daily_pcs',
   'assumption_id',p->>'profile_id','selected',true,'refs',profile_refs)else null end;
  estimate:=cp7_demand.estimate(jsonb_build_object('contract_version','cp7.demand-estimate-input.v1','snapshot_id',hash,
   'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','target_key',r->>'target_key','size_id',r->>'size_id',
   'minimum_own_available_days',coalesce(cfg->'minimum_available_days','"1"'::jsonb),
   'own',case when cfg is null then null else own end,'analog',null,'manual',manual,'refs',refs||profile_refs));
  target:=cp7_baseline.target(jsonb_build_object('contract_version','cp7.target-input.v1','snapshot_id',hash,
   'scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS','mode','DAYS','daily_mean',estimate->'daily_pcs',
   'lead_days',cfg->'lead_days','review_days',cfg->'review_days','buffer_days',cfg->'buffer_days',
   'quantile',null,'horizon_samples','[]'::jsonb,'refs',refs||profile_refs));
  if policies is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}')into policies
    from(select m.k,(array_agg(x order by o))[1] v from jsonb_array_elements(c->'production_policies'->'rows')with ordinality a(x,o)
     cross join lateral(select e#>>'{}' k from jsonb_array_elements(case when jsonb_typeof(x->'members')='array'then x->'members'end)e
       where jsonb_typeof(e)='string'
      union select jsonb_object_keys(case when jsonb_typeof(x->'members')='object'then x->'members'end)
      union select x->'members'#>>'{}' where jsonb_typeof(x->'members')='string')m group by 1)f;
  end if;
  policy:=policies->root;
  state:=case when policy->'policy'->>'quality'='KNOWN'then policy->'policy'->>'state'else null end;
  rows:=array_append(rows,jsonb_build_object('target_key',r->>'target_key','size_id',r->>'size_id',
   'sku',stock->>'sku','product_name',stock->>'product_name','available_fg_pcs',stock->>'native_available_pcs',
   'profile',p,'demand_estimate',estimate,'target',target,'production_policy',policy,
   'start_new_pcs',case when state in('PAUSED','STOPPED')then '0'else null end,
   'final_gap_pcs',null,'supply_state','UNKNOWN','capacity_state','UNKNOWN','timeline_state','UNKNOWN',
   'reason',case when state in('PAUSED','STOPPED')then 'PRODUCTION_DISABLED_EXISTING_STOCK_STILL_SELLABLE'
    when state is null then 'PRODUCTION_POLICY_UNREVIEWED_OR_IDENTITY_UNAVAILABLE'
    else 'AUTHORITATIVE_WIP_MATCHING_CALENDAR_CAPACITY_NOT_CAPTURED'end,
   'refs',refs||profile_refs));
 end loop;
 return to_jsonb(rows);
end $$;
-- cp7_supply_native.build after its baseline (verbatim): the global WIP
-- normalization over every position (independent of the target count).
create function cp7_analysis_stage.supply(c jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare wip jsonb;hash text;
begin
 wip:=cp7_wip.normalize_production(c->'production_sources');
 hash:=cp7_supply_native.fingerprint(c);
 if wip->>'status'='COMPLETE'then
  wip:=wip||jsonb_build_object('scope','GLOBAL_NATIVE_POSTED_PRODUCTION_ORIGINS',
   'source_basis','ONE_CLOCK_ONE_MVCC_SOURCE_BATCHES_ONE_CONSERVED_GRAPH');
 end if;
 -- The supply result without its baseline (stored by the baseline units).
 return jsonb_build_object('contract_version','cp7.native-supply.v2',
  'captured_at',c->>'captured_at','source_hash',hash,
  'scope','GLOBAL_CURRENT_PHYSICAL_ROOTS_AND_POSTED_PRODUCTION_ORIGINS',
  'production_scope',c->'production_sources'->'scope',
  'production_scope_basis','POSTED_CUTTING_GROUPS_NOT_PROVEN_EXHAUSTED_EXHAUSTED_LISTED',
  'wip',wip,'matching_state','UNKNOWN','yield_state','UNKNOWN','calendar_state','UNKNOWN',
  'capacity_state','UNKNOWN','allocation_state','UNKNOWN',
  'reason','NATIVE_PHYSICAL_WIP_KNOWN_ONLY_WHEN_CONSERVED_NOT_FUTURE_SELLABLE_SUPPLY',
  'apply_enabled',false,'production_go',false);
end $$;
-- cp7_schedule_native.build after its supply call (verbatim), on the stored
-- supply result (without its baseline): capacity windows and the shared ETA
-- queue over every position, independent of the target count.
create function cp7_analysis_stage.schedule(c jsonb,supply jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare plan jsonb:=c->'schedule';cfg jsonb;wip jsonb;p jsonb;selected jsonb;step jsonb;win jsonb;
 refs jsonb;plans_refs jsonb;yield_inputs jsonb[]:='{}';work jsonb;windows jsonb;window_acc jsonb[]:='{}';capacity_windows jsonb[]:='{}';
 etas jsonb[]:='{}';rows jsonb:='[]';by_position jsonb;repeated jsonb;capacity jsonb;eta jsonb;source_state text;hash text;ready timestamptz;cursor_at timestamptz;
 through_at timestamptz;starts timestamptz;ends timestamptz;load numeric:=0;remaining_load numeric;
 minutes numeric;external_load numeric;used numeric;queue_known boolean:=true;other_load_placed boolean:=true;
 window_start timestamptz[]:='{}';window_end timestamptz[]:='{}';wi integer:=1;wj integer;need numeric;covered numeric;usable jsonb;
begin
 wip:=supply->'wip';hash:=cp7_schedule_native.fingerprint(c);
 source_state:=case when plan='null'::jsonb then 'UNREVIEWED'
  when plan->>'source_hash'=cp7_supply_native.fingerprint(c)then 'SELECTED_ASSUMPTIONS'else 'SOURCE_CHANGED'end;
 if wip->>'status'is distinct from 'COMPLETE'or source_state<>'SELECTED_ASSUMPTIONS'then
  return jsonb_build_object('contract_version','cp7.native-planning-scenario.v1','captured_at',c->>'captured_at',
   'source_hash',hash,'planning_time_bucket',c->'planning_time_bucket','supply_run_result',supply,
   'schedule',plan,'schedule_state',source_state,'status','UNKNOWN','wip',wip,'etas','[]'::jsonb,
   'capacity',jsonb_build_object('status','UNKNOWN','capacity_pcs',null),
   'allocation',jsonb_build_object('status','UNKNOWN','reason','AUTHORITATIVE_REVIEWED_GLOBAL_MATCHING_NOT_COMPOSED'),
   'final_gap_pcs',null,'apply_enabled',false,'production_go',false);
 end if;
 cfg:=plan->'config';ready:=(c->>'captured_at')::timestamptz;cursor_at:=ready;
 through_at:=cp7_demand.instant(cfg->'through_at');
 plans_refs:=jsonb_build_array(jsonb_build_object('kind','PLANNING_SCHEDULE','id',plan->>'plan_id','revision',plan->>'revision'));
 for p in select value from jsonb_array_elements(wip->'positions')
  where cp7_schedule_native.route(value->>'stage')is not null and cp7_wip.pcs(value->'remaining_pcs')>0 loop
  if by_position is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into by_position,repeated
    from(select value->>'position_key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(cfg->'positions')
     where value->>'position_key'is not null group by 1)f;
  end if;
  if repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  selected:=by_position->(p->>'key');
  if selected is null or cp7_wip.pcs(selected->'eligible_input_pcs')<>cp7_wip.pcs(p->'remaining_pcs')then
   queue_known:=false;
  elsif exists(select 1 from jsonb_array_elements(selected->'remaining_steps')where value->'remaining_minutes'='null'::jsonb)then
   queue_known:=false;
  else
   select load+coalesce(sum(cp7_wip.pcs(value->'remaining_minutes')),0)into load
    from jsonb_array_elements(selected->'remaining_steps');
  end if;
  if p->'eligible_company_wip'='true'::jsonb and selected is not null and selected->'yield_numerator'<>'null'::jsonb then
   yield_inputs:=array_append(yield_inputs,jsonb_build_object('position_key',p->>'key',
    'eligible_input_pcs',selected->'eligible_input_pcs','numerator',selected->'yield_numerator',
    'denominator',selected->'yield_denominator','basis','ASSUMED','assumption_id',plan->>'plan_id',
    'refs',(p->'refs')||plans_refs));
  end if;
 end loop;
 wip:=cp7_wip.project_yield(wip,to_jsonb(yield_inputs));remaining_load:=load;
 for win in select value from jsonb_array_elements(cfg->'windows')order by cp7_demand.instant(value->'starts_at'),value->>'key'loop
  starts:=greatest(ready,cp7_demand.instant(win->'starts_at'));ends:=cp7_demand.instant(win->'ends_at');
  if ends<=starts then continue;end if;
  window_acc:=array_append(window_acc,jsonb_build_object('start',cp7_planning.utc(starts),'end',cp7_planning.utc(ends)));
  window_start:=array_append(window_start,starts);window_end:=array_append(window_end,ends);
  minutes:=extract(epoch from ends-starts)/60;
  if win->'other_load_minutes'='null'::jsonb then
   external_load:=null;other_load_placed:=false;
  else external_load:=cp7_demand.decimal(win->'other_load_minutes');
   if external_load>0 then other_load_placed:=false;end if;
  end if;
  used:=least(remaining_load,greatest(0,minutes-coalesce(external_load,minutes)));
  remaining_load:=remaining_load-used;
  capacity_windows:=array_append(capacity_windows,jsonb_build_object('key',win->'key',
   'starts_at',cp7_planning.utc(starts),'ends_at',cp7_planning.utc(ends),
   'existing_load_minutes',case when queue_known and external_load is not null
    then(ceil((external_load+used)*1000000000000)/1000000000000)::numeric(42,12)::text else null end,
   'refs',plans_refs));
 end loop;
 windows:=to_jsonb(window_acc);
 if through_at<=ready then
  capacity:=jsonb_build_object('status','UNKNOWN','capacity_pcs',null,'reason','SELECTED_CALENDAR_EXPIRED');
 else
  capacity:=cp7_baseline.capacity(jsonb_build_object('contract_version','cp7.capacity-input.v1',
   'snapshot_id',wip->>'snapshot_id','scope_id','GLOBAL_NATIVE_POSTED_PRODUCTION_ORIGINS',
   'work_centre_id',cfg->>'work_centre_key','from_at',cp7_planning.utc(ready),'through_at',cfg->'through_at',
   'unit_minutes',cfg->'unit_minutes','unit_time_basis',case when cfg->'unit_minutes'='null'::jsonb then 'UNKNOWN'else 'SELECTED_ASSUMPTION'end,
   'windows',to_jsonb(capacity_windows),'refs',plans_refs));
  if remaining_load>0 then capacity:=capacity||jsonb_build_object('status','UNKNOWN','capacity_pcs',null,
   'reason','CAPTURED_REMAINING_WORK_EXCEEDS_SELECTED_CALENDAR');end if;
 end if;
 for p in select value from jsonb_array_elements(wip->'positions')
  where cp7_schedule_native.route(value->>'stage')is not null and cp7_wip.pcs(value->'remaining_pcs')>0 order by value->>'key'loop
  if by_position is null then
   select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into by_position,repeated
    from(select value->>'position_key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(cfg->'positions')
     where value->>'position_key'is not null group by 1)f;
  end if;
  if repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  selected:=by_position->(p->>'key');
  refs:=(p->'refs')||plans_refs;
  if not queue_known or not other_load_placed or through_at<=ready then
   eta:=jsonb_build_object('status','UNKNOWN','eta',null,'on_time',null,'reason',
    case when not queue_known then 'SHARED_NATIVE_REMAINING_QUEUE_NOT_FULLY_REVIEWED'
     when not other_load_placed then 'OTHER_LOAD_DATED_PLACEMENT_NOT_SELECTED'else 'SELECTED_CALENDAR_EXPIRED'end);
  else
   if cardinality(window_acc)>1000 then usable:=windows;
   else
    while wi<=cardinality(window_end)and window_end[wi]<=cursor_at loop wi:=wi+1;end loop;
    select coalesce(sum(cp7_wip.pcs(value->'remaining_minutes')),0)into need from jsonb_array_elements(selected->'remaining_steps');
    wj:=wi;covered:=0;
    while wj<=cardinality(window_end)and covered<=need+1 loop
     covered:=covered+extract(epoch from window_end[wj]-greatest(window_start[wj],cursor_at))/60;wj:=wj+1;
    end loop;
    usable:=to_jsonb(window_acc[wi:wj]);
   end if;
   work:='[]';
   for step in select value from jsonb_array_elements(selected->'remaining_steps')with ordinality order by ordinality loop
    work:=work||jsonb_build_array(jsonb_build_object('stage',step->'stage','remaining_minutes',step->'remaining_minutes',
     'basis','ASSUMED','assumption_id',plan->>'plan_id','calendar_version',(plan->>'plan_id')||':'||(plan->>'revision'),
     'windows',usable,'refs',refs));
   end loop;
   eta:=cp7_wip.remaining_eta(cursor_at,through_at,work);
   if eta->>'status'in('KNOWN','CONDITIONAL')then cursor_at:=(eta->>'eta')::timestamptz;
   else queue_known:=false;end if;
  end if;
  etas:=array_append(etas,jsonb_build_object('position_key',p->'key','target_key',selected->'target_key',
   'result',eta,'refs',refs));
 end loop;
 return jsonb_build_object('contract_version','cp7.native-planning-scenario.v1','captured_at',c->>'captured_at',
  'source_hash',hash,'planning_time_bucket',c->'planning_time_bucket','supply_run_result',supply,
  'schedule',plan,'schedule_state',source_state,'status','SCENARIO','wip',wip,'etas',to_jsonb(etas),'capacity',capacity,
  'resource_basis','SINGLE_HOMOGENEOUS_SELECTED_CENTRE_ALL_CAPTURED_REMAINING_WORK_BEFORE_NEW_STARTS',
  'queue_order','STABLE_NATIVE_POSITION_KEY_SELECTED_SCENARIO_NOT_FACTORY_OPTIMIZER',
  'allocation',jsonb_build_object('status','UNKNOWN','reason','AUTHORITATIVE_REVIEWED_GLOBAL_MATCHING_NOT_COMPOSED'),
  'final_gap_pcs',null,'apply_enabled',false,'production_go',false);
end $$;

-- ---------------------------------------------------------------- netting --
-- ---------------------------------------------------------------- netting --
-- Everything netting.build computes before its first target loop, plus the
-- pair-matrix maps it computes after it (they read only arrays the earlier
-- steps already read, so computing them first raises nothing new).
create function cp7_analysis_stage.netting_prep(c jsonb,scenario jsonb,p_targets integer,p_pairs bigint,p_match integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare wip jsonb:=scenario->'wip';hash text;m jsonb;matching jsonb;models jsonb;p jsonb;eta jsonb;etas jsonb;
 eta_list jsonb[]:='{}';eligible jsonb[]:='{}';budget numeric:=0;supplies_complete boolean:=true;
 eta_at jsonb;eta_repeated jsonb;target_at jsonb;target_repeated jsonb;source_at jsonb;source_repeated jsonb;
 row_keys text[];row_target_keys jsonb[];n integer;first_repeated integer;model_targets jsonb;leaders integer[];row_at jsonb;
 rows jsonb:=scenario->'supply_run_result'->'baseline_run_result'->'rows';sorted integer[]:='{}';ord_i bigint;
begin
 hash:=cp7_netting_native.fingerprint(c);
 if wip->>'status'is distinct from 'COMPLETE'then return jsonb_build_object('wip_complete',false,'hash',hash,
  'alloc',jsonb_build_object('status','UNKNOWN','reason','NATIVE_QUANTITY_CAPTURE_INCOMPLETE'));end if;
 -- Single call: positions x rows above 100000 refuse here. Staged: pairs are
 -- computed in chunks of at most 100000 (netting_pairs); p_pairs bounds the job.
 if jsonb_array_length(wip->'positions')*jsonb_array_length(rows)>p_pairs
  or jsonb_array_length(wip->'positions')>1000 then raise exception 'CP7_NETTING_WORK_LIMIT';end if;
 if jsonb_array_length(rows)>p_targets then raise exception 'CP7_ANALYSIS_STAGED_TARGET_LIMIT';end if;
 m:=cp7_netting_native.matching_models_within(c,wip,p_match);matching:=m->'matching';models:=m->'models';
 for eta in select value from jsonb_array_elements(scenario->'etas')loop
  eta_list:=array_append(eta_list,jsonb_build_object('position_key',eta->'position_key',
   'at',case when eta->'result'->>'status'in('KNOWN','CONDITIONAL')then cp7_planning.utc((eta->'result'->>'eta')::timestamptz)else null end,
   'refs',eta->'refs'));
 end loop;
 etas:=to_jsonb(eta_list);
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into eta_at,eta_repeated
  from(select value->>'position_key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(etas)
   where value->>'position_key'is not null group by 1)f;
 for p in select value from jsonb_array_elements(wip->'positions')where value->'eligible_company_wip'='true'::jsonb loop
  if eta_repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  eta:=eta_at->(p->>'key');eligible:=array_append(eligible,p);
  if p->'projection'->>'quality'='SCENARIO'and eta->>'at'is not null then
   budget:=budget+cp7_wip.pcs(p->'projection'->'projected_good_pcs');
  elsif cp7_wip.pcs(p->'remaining_pcs')>0 then supplies_complete:=false;end if;
 end loop;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into target_at,target_repeated
  from(select value->>'key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(matching->'targets')
   where value->>'key'is not null group by 1)f;
 -- The rows in the build's loop order (same sort, same input order).
 for ord_i in select x.o from jsonb_array_elements(rows)with ordinality x(value,o)order by x.value->>'target_key'loop
  sorted:=array_append(sorted,ord_i::integer);
 end loop;
 select coalesce(array_agg(value->>'target_key' order by o),'{}'),coalesce(array_agg(value->'target_key' order by o),'{}')into row_keys,row_target_keys
  from jsonb_array_elements(rows)with ordinality a(value,o);
 n:=cardinality(row_keys);
 select coalesce(min(u.j),n+1)into first_repeated from unnest(row_keys)with ordinality u(k,j)where target_repeated?u.k;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into source_at,source_repeated
  from(select value->>'key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(matching->'sources')
   where value->>'key'is not null group by 1)f;
 select coalesce(jsonb_object_agg(f.m,f.ks),'{}')into model_targets
  from(select x->>'model_id' m,jsonb_object_agg((x->>'root_id')||':'||(x->>'size_id'),true)ks from jsonb_array_elements(c->'facts'->'products')x
   where x->>'model_id'is not null and(x->>'root_id')||':'||(x->>'size_id')is not null group by 1)f;
 select coalesce(array_agg(f.leader order by f.i),'{}')into leaders
  from(select g.i,case when g.facts is null then g.i else min(g.i)over(partition by g.facts)end leader
   from(select e.i,case when e.s is not null and e.model is not null then
      jsonb_build_array(e.s->'quality',e.s->'size_id',e.s->'confirmed_target',e.s->'constraints',e.model)::text end facts
     from(select x.i,source_at->(x.p->>'key') s,models->>(x.p::text) model from unnest(eligible)with ordinality x(p,i))e)g)f;
 select coalesce(jsonb_object_agg(f.k,f.j),'{}')into row_at
  from(select u.k,min(u.j)j from unnest(row_keys)with ordinality u(k,j)where u.k is not null group by 1)f;
 return jsonb_build_object('wip_complete',true,'hash',hash,'ready',c->>'captured_at','snapshot_id',wip->'snapshot_id',
  'matching',matching,'models',models,'etas',etas,'eta_at',eta_at,'eta_repeated',eta_repeated,'eligible',to_jsonb(eligible),
  'budget',budget::text,'supplies_complete',supplies_complete,'target_at',target_at,'target_repeated',target_repeated,
  'row_keys',to_jsonb(row_keys),'row_target_keys',to_jsonb(row_target_keys),'n',n,'first_repeated',first_repeated,
  'source_at',source_at,'source_repeated',source_repeated,'model_targets',model_targets,'leaders',to_jsonb(leaders),
  'row_at',row_at,'sorted',to_jsonb(sorted));
end $$;
-- netting.build's first target loop for one chunk of rows (loop order).
-- c needs captured_at and schedule; wip needs snapshot_id (timeline and net
-- read nothing else of them).
create function cp7_analysis_stage.netting_targets(g jsonb,c jsonb,wip jsonb,rows jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare r jsonb;cfg jsonb;policy text;production_status text;raw_net jsonb;raw_need numeric;deadline timestamptz;helps timestamptz;
 line jsonb;tf jsonb;refs jsonb;out jsonb[]:='{}';reviews jsonb[];all_known boolean:=true;ready timestamptz:=(g->>'ready')::timestamptz;
 target_repeated jsonb:=g->'target_repeated';target_at jsonb:=g->'target_at';etas jsonb:=g->'etas';matching jsonb:=g->'matching';hash text:=g->>'hash';
begin
 for r in select x.value from jsonb_array_elements(rows)with ordinality x(value,o)order by x.o loop
  cfg:=r->'profile'->'config';policy:=r->'production_policy'->'policy'->>'state';reviews:='{}';
  if r->'target'->>'status'is distinct from 'SCENARIO'or r->>'available_fg_pcs'is null then
   all_known:=false;out:=array_append(out,jsonb_build_object('planned',false,'reviews',jsonb_build_array(
    jsonb_build_object('target_key',r->'target_key','reason','DEMAND_TARGET_STOCK_OR_PRODUCTION_POLICY_UNREVIEWED'))));continue;end if;
  if policy is null then all_known:=false;reviews:=array_append(reviews,jsonb_build_object('target_key',r->'target_key','reason','PRODUCTION_POLICY_UNREVIEWED'));end if;
  production_status:=case when policy='ACTIVE'then 'ACTIVE'when policy in('PAUSED','STOPPED')then 'STOP'else 'UNKNOWN'end;
  raw_net:=cp7_baseline.net(jsonb_build_object('contract_version','cp7.net-input.v1','snapshot_id',wip->'snapshot_id',
   'scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',coalesce(c->'schedule'->'plan_id',to_jsonb('unreviewed-'||hash)),
   'target_key',r->'target_key','size_id',r->'size_id','deadline',cp7_planning.utc(ready),
   'target_pcs',r->'target'->'target_pcs','available_fg_pcs',r->'available_fg_pcs','supplies','[]'::jsonb,'refs',r->'refs'));
  raw_need:=cp7_wip.pcs(raw_net->'q_base_pcs');
  deadline:=ready+((cp7_demand.decimal(cfg->'lead_days')+cp7_demand.decimal(cfg->'review_days'))::text||' days')::interval;
  helps:=ready+(cp7_demand.decimal(cfg->'lead_days')::text||' days')::interval;
  line:=cp7_netting_native.timeline(c,r,etas,'[]'::jsonb,matching,wip);
  if target_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  tf:=target_at->(r->>'target_key');
  select jsonb_agg(x order by x::text)into refs from(select distinct value x from jsonb_array_elements((r->'refs')||(tf->'refs')))u;
  out:=array_append(out,jsonb_build_object('planned',true,'reviews',to_jsonb(reviews),'line',line,
   'target',jsonb_build_object('key',r->'target_key','size_id',r->'size_id',
   'need_pcs',raw_need::text,'deadline',cp7_planning.utc(deadline),
   'risk_at',coalesce(line->'first_known_gap'->'at',to_jsonb(cp7_planning.utc(deadline))),
   'helps_at',cp7_planning.utc(helps),'production_status',production_status,'refs',refs)));
 end loop;
 return jsonb_build_object('rows',to_jsonb(out),'all_known',all_known);
end $$;
-- netting.build's pair loop for eligible positions lo..hi (1-based, eligible
-- order) against every row. leader_rows holds the pair row of each leader
-- before lo (a later position with a leader's facts reuses its verdicts).
create function cp7_analysis_stage.netting_pairs(g jsonb,lo integer,hi integer,leader_rows jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare p jsonb;s jsonb;model text;compatible jsonb;m jsonb;j integer;i integer;n integer:=(g->>'n')::integer;
 first_repeated integer:=(g->>'first_repeated')::integer;row_keys text[];leaders integer[];out jsonb[]:='{}';
 source_at jsonb:=g->'source_at';source_repeated jsonb:=g->'source_repeated';models jsonb:=g->'models';
 model_targets jsonb:=g->'model_targets';target_at jsonb:=g->'target_at';eligible jsonb:=g->'eligible';
 unknown_model jsonb:=jsonb_build_object('match','UNKNOWN','reasons',jsonb_build_array('NATIVE_SOURCE_MODEL_UNPROVEN'));
 model_mismatch jsonb:=jsonb_build_object('match','INCOMPATIBLE','reasons',jsonb_build_array('NATIVE_MODEL_MISMATCH'));
begin
 if n=0 then return '[]'::jsonb;end if;
 select coalesce(array_agg(x.k order by x.o),'{}')into row_keys from jsonb_array_elements_text(g->'row_keys')with ordinality x(k,o);
 select coalesce(array_agg(x.k::integer order by x.o),'{}')into leaders from jsonb_array_elements_text(g->'leaders')with ordinality x(k,o);
 for i in lo..hi loop
  p:=eligible->(i-1);
  if source_repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  s:=source_at->(p->>'key');model:=models->>(p::text);compatible:=model_targets->model;
  if leaders[i]<i then
   select min(u.j)into j from unnest(row_keys)with ordinality u(k,j)where coalesce(compatible?u.k,false);
   if j is not null then m:=cp7_wip.match_target(s,target_at->row_keys[j]);end if;
   out:=array_append(out,case when leaders[i]>=lo then out[leaders[i]-lo+1] else leader_rows->(leaders[i]::text)end);
  else
   select coalesce(jsonb_agg(case when model is null then unknown_model when not coalesce(compatible?u.k,false)then model_mismatch
     else cp7_wip.match_target(s,target_at->u.k)end order by u.j),'[]')into m
    from unnest(row_keys)with ordinality u(k,j)where u.j<first_repeated;
   out:=array_append(out,m);
   if first_repeated<=n then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  end if;
 end loop;
 return to_jsonb(out);
end $$;
-- What netting.build decides between its pair loop and the allocation: the
-- planned targets, whether allocation runs, and the allocation input.
-- targets: every planned target entry in loop order; all_known: the first
-- loop's flag over all chunks.
create function cp7_analysis_stage.netting_plan(g jsonb,c jsonb,wip jsonb,schedule_state text,targets jsonb,all_known boolean)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare alloc jsonb;v jsonb;planned_at jsonb;planned_repeated jsonb;
begin
 if not all_known then alloc:=jsonb_build_object('status','UNKNOWN','reason','GLOBAL_TARGET_NEEDS_OR_POLICY_NOT_FULLY_REVIEWED');
 elsif schedule_state<>'SELECTED_ASSUMPTIONS'then alloc:=jsonb_build_object('status','UNKNOWN','reason','SOURCE_BOUND_WORK_YIELD_NOT_REVIEWED');
 elsif not(g->>'supplies_complete')::boolean then alloc:=jsonb_build_object('status','UNKNOWN','reason','EXISTING_SUPPLY_YIELD_OR_SHARED_ETA_UNKNOWN');
 else
  v:=jsonb_build_object('contract_version','cp7.allocation-input.v1',
   'snapshot_id',wip->'snapshot_id','scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',c->'schedule'->'plan_id',
   'complete_scope',true,'positions',wip,'matching',g->'matching','etas',g->'etas','targets',targets,
   'capacity_pcs',g->>'budget','refs',jsonb_build_array(cp7_wip.ref('PLANNING_SCHEDULE',c->'schedule'->>'plan_id',c->'schedule'->>'revision')));
 end if;
 select coalesce(jsonb_object_agg(f.k,f.v),'{}'),coalesce(jsonb_object_agg(f.k,true)filter(where f.n>1),'{}')into planned_at,planned_repeated
  from(select value->>'key' k,count(*)n,(array_agg(value))[1] v from jsonb_array_elements(targets)
   where value->>'key'is not null group by 1)f;
 return jsonb_build_object('alloc',alloc,'allocation_input',v,'planned_at',planned_at,'planned_repeated',planned_repeated);
end $$;
-- netting.build's second target loop for one chunk. rows: this chunk's rows
-- (loop order) each as {ord,row}; first: the first loop's output per ord;
-- planned_ord: target key -> ord of its planned row; pairs: target key -> its
-- match results in match_results order, each {i: eligible index, e: entry}
-- (a position key may be null; the index is not); candidates: target key ->
-- its allocated CANDIDATE_MATCH edges in allocation edge order.
create function cp7_analysis_stage.netting_rows(g jsonb,c jsonb,wip jsonb,capacity jsonb,alloc_status text,plan jsonb,
 planned_ord jsonb,rows jsonb,first jsonb,pairs jsonb,candidates jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare x jsonb;r jsonb;t jsonb;p jsonb;m jsonb;eta jsonb;line jsonb;net jsonb;supplies jsonb;directed_edges jsonb;line_edges jsonb;
 raw_need numeric;gap numeric;directed numeric;candidate numeric;open_work jsonb[];open_index integer[];i integer;w integer;supply_list jsonb[];edge_list jsonb[];
 row_list jsonb[]:='{}';by_position jsonb;hash text:=g->>'hash';eta_at jsonb:=g->'eta_at';eta_repeated jsonb:=g->'eta_repeated';
 planned_at jsonb:=plan->'planned_at';planned_repeated jsonb:=plan->'planned_repeated';etas jsonb:=g->'etas';matching jsonb:=g->'matching';
begin
 for x in select y.value from jsonb_array_elements(rows)with ordinality y(value,o)order by y.o loop
  r:=x->'row';directed:=0;candidate:=0;raw_need:=null;gap:=null;supplies:='[]';directed_edges:='[]';net:=null;
  if planned_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
  t:=planned_at->(r->>'target_key');
  if t is not null then
   raw_need:=cp7_wip.pcs(t->'need_pcs');
   if open_work is null then
    open_work:='{}';open_index:='{}';i:=0;
    for p in select value from jsonb_array_elements(g->'eligible')loop
     i:=i+1;
     if cp7_wip.pcs(p->'remaining_pcs')>0 then open_work:=array_append(open_work,p);open_index:=array_append(open_index,i);end if;
    end loop;
   end if;
   -- The pair result of each open position for this key's first row: the
   -- first result of that position in the key's match results.
   select coalesce(jsonb_object_agg(f.k,f.v),'{}')into by_position from(
    select y.value->>'i' k,(array_agg(y.value->'e'->'result' order by y.o))[1] v
    from jsonb_array_elements(coalesce(pairs->(r->>'target_key'),'[]'))with ordinality y(value,o)group by 1)f;
   supply_list:='{}';edge_list:='{}';
   for w in 1..coalesce(cardinality(open_work),0) loop
    p:=open_work[w];m:=by_position->(open_index[w]::text);
    if eta_repeated?(p->>'key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
    eta:=eta_at->(p->>'key');
    if m->>'match'='CONFIRMED_TARGET'then
     supply_list:=array_append(supply_list,jsonb_build_object('physical_key',p->'key','snapshot_id',wip->'snapshot_id',
      'target_key',r->'target_key','size_id',r->'size_id','kind','DIRECTED',
      'qty_pcs',case when p->'projection'->>'quality'='SCENARIO'then p->'projection'->'projected_good_pcs'else null end,
      'eta',coalesce(eta->'at','null'::jsonb),'eligible',true,'refs',p->'refs'));
     if p->'projection'->>'quality'='SCENARIO'and eta->>'at'is not null then
      edge_list:=array_append(edge_list,jsonb_build_object('key',p->'key','position_key',p->'key',
       'target_key',r->'target_key','projected_good_pcs',p->'projection'->'projected_good_pcs','refs',p->'refs'));
     end if;
    end if;
   end loop;
   for p in select value from jsonb_array_elements(candidates->(r->>'target_key'))loop
    if eta_repeated?(p->>'position_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;
    eta:=eta_at->(p->>'position_key');
    supply_list:=array_append(supply_list,jsonb_build_object('physical_key',p->'position_key','snapshot_id',wip->'snapshot_id',
     'target_key',r->'target_key','size_id',r->'size_id','kind','ALLOCATED_CANDIDATE','qty_pcs',p->'projected_good_pcs',
     'eta',eta->'at','eligible',true,'refs',p->'refs'));
   end loop;
   supplies:=to_jsonb(supply_list);directed_edges:=to_jsonb(edge_list);
   net:=cp7_baseline.net(jsonb_build_object('contract_version','cp7.net-input.v1','snapshot_id',wip->'snapshot_id',
    'scope_id','GLOBAL_NATIVE_PLANNING','scenario_id',coalesce(c->'schedule'->'plan_id',to_jsonb('unreviewed-'||hash)),
    'target_key',r->'target_key','size_id',r->'size_id','deadline',t->'deadline',
    'target_pcs',r->'target'->'target_pcs','available_fg_pcs',r->'available_fg_pcs','supplies',supplies,'refs',r->'refs'));
   gap:=(net->>'q_base_pcs')::numeric;directed:=coalesce((net->>'directed_on_time_pcs')::numeric,0);
   candidate:=coalesce((net->>'candidate_on_time_pcs')::numeric,0);
  end if;
  if t is null then line:=jsonb_build_object('status','UNKNOWN','reason','TARGET_NEEDS_OR_POLICY_UNREVIEWED');
  else
   line_edges:=directed_edges||coalesce(candidates->(r->>'target_key'),'[]'::jsonb);
   -- build() reuses the first loop's timeline only for the very row that
   -- loop planned: a planned key is unique here (planned_repeated refused
   -- above), so that row is the one with this key's planned ord.
   if line_edges='[]'::jsonb and(planned_ord->>(r->>'target_key'))::integer=(x->>'ord')::integer then
    line:=first->(x->>'ord')->'line';
   else line:=cp7_netting_native.timeline(c,r,etas,line_edges,matching,wip);end if;
  end if;
  row_list:=array_append(row_list,r||jsonb_build_object('raw_gap_pcs',raw_need::text,'directed_on_time_good_pcs',net->'directed_on_time_pcs',
   'base_gap_pcs',net->'q_base_pcs','conditional_gap_pcs',case when alloc_status='SCENARIO'then net->'q_conditional_pcs'else null end,
   'net',net,
   'candidate_allocated_good_pcs',case when alloc_status='SCENARIO'then candidate::text else null end,
   'timeline',line,'start_new_pcs',case when t->>'production_status'='STOP'then '0'else null end,
   'material_state','UNKNOWN','new_start_capacity',capacity,'apply_enabled',false,
   'netting_basis','NATIVE_AVAILABLE_FG_ONCE_SOURCE_BOUND_YIELD_AND_ONE_SHARED_REMAINING_CALENDAR',
   'reason','SCENARIO_EXISTING_SUPPLY_DISTINCT_FROM_NEW_START_MATERIAL_FEASIBILITY'));
 end loop;
 return to_jsonb(row_list);
end $$;

-- ------------------------------------------------------------- allocation --
-- ------------------------------------------------------------- allocation --
-- cp7_baseline.allocate as prep (all validation, the priority order and the
-- per-position arrays), steps over the priority order with carried state
-- (capacity, used, good used, pool used, edge count) and a final validation.
-- The verdict memo is per step: a dropped memo only repeats match_target
-- calls the memo had proven, with the same results.
create function cp7_analysis_stage.alloc_prep(v jsonb,p_targets integer,p_visits bigint)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare t jsonb;p jsonb;tf jsonb;eta jsonb;pool jsonb;e jsonb;proj jsonb;k text;pk text;validation jsonb;capacity numeric;
 num numeric;den numeric;room numeric;good numeric;i integer;repeated integer;sources_n integer;targets_n integer;
 pool_at jsonb;position_at jsonb;eta_at jsonb;source_at jsonb;target_at jsonb;target_ids jsonb;size_lists jsonb;ordered jsonb[]:='{}';
 pool_wip numeric[]:='{}';position_keys text[]:='{}';position_pools integer[]:='{}';remaining numeric[]:='{}';
 eligible_input numeric[]:='{}';projected_good numeric[]:='{}';numerators numeric[]:='{}';denominators numeric[]:='{}';
 eta_times timestamptz[];reviewed boolean[];source_ids integer[];source_confirmed text[];
begin
 perform cp7_wip.fields(v,array['contract_version','snapshot_id','scope_id','scenario_id','complete_scope','positions','matching','etas','targets','capacity_pcs','refs']);
 perform cp7_demand.context(v,'cp7.allocation-input.v1');perform cp7_wip.key(v->'scenario_id');perform cp7_wip.refs(v->'refs');
 if jsonb_typeof(v->'complete_scope') is distinct from 'boolean' then raise exception 'CP7_BASELINE_SCOPE';end if;
 if v->'complete_scope'='false'::jsonb then return jsonb_build_object('result',jsonb_build_object('status','UNKNOWN','reason','COMPLETE_ALLOCATION_SCOPE_REQUIRED'));end if;
 if v->'capacity_pcs'='null'::jsonb then return jsonb_build_object('result',jsonb_build_object('status','UNKNOWN','reason','SHARED_CAPACITY_UNKNOWN'));end if;
 capacity:=cp7_wip.pcs(v->'capacity_pcs');
 if v->'positions'->>'snapshot_id' is distinct from v->>'snapshot_id' or v->'matching'->>'snapshot_id' is distinct from v->>'snapshot_id' then raise exception 'CP7_BASELINE_MATCH_SNAPSHOT';end if;
 validation:=cp7_wip.check_allocations(v->'positions',jsonb_build_object('scenario_id',v->'scenario_id','scope_id',v->'scope_id','complete_scope',true,'matching',v->'matching','edges','[]'::jsonb));
 if validation->>'status'<>'FEASIBLE' then return jsonb_build_object('result',validation);end if;
 perform cp7_demand.items(v->'positions'->'positions',1000);perform cp7_demand.items(v->'positions'->'totals',1000);
 perform cp7_demand.items(v->'targets',p_targets);perform cp7_demand.items(v->'etas',1000);
 -- Single call: positions x targets above 100000 refuse here. Staged: the
 -- job bound (p_visits) refuses here; each alloc_step is bounded on its own.
 if jsonb_array_length(v->'positions'->'positions')*jsonb_array_length(v->'targets')>p_visits then raise exception 'CP7_BASELINE_ALLOCATION_LIMIT';end if;
 select min(f.o) into repeated from(select a.o,row_number()over(partition by a.value->>'pool_key' order by a.o)n
  from jsonb_array_elements(v->'positions'->'totals')with ordinality a(value,o)where a.value->>'pool_key' is not null)f where f.n>1;
 i:=0;
 for pool in select value from jsonb_array_elements(v->'positions'->'totals') loop
  i:=i+1;k:=cp7_wip.key(pool->'pool_key');pool_wip:=array_append(pool_wip,cp7_wip.pcs(pool->'wip_pcs'));
  if i=repeated then raise exception 'CP7_BASELINE_DUPLICATE_POOL';end if;
 end loop;
 select coalesce(jsonb_object_agg(a.value->>'pool_key',a.o),'{}') into pool_at from jsonb_array_elements(v->'positions'->'totals')with ordinality a(value,o);
 select min(f.o) into repeated from(select a.o,row_number()over(partition by a.value->>'key' order by a.o)n
  from jsonb_array_elements(v->'positions'->'positions')with ordinality a(value,o)where a.value->>'key' is not null)f where f.n>1;
 i:=0;
 for p in select value from jsonb_array_elements(v->'positions'->'positions') loop
  i:=i+1;
  k:=cp7_wip.key(p->'key');pk:=cp7_wip.key(p->'pool_key');perform cp7_wip.key(p->'size_id');remaining:=array_append(remaining,cp7_wip.pcs(p->'remaining_pcs'));perform cp7_wip.refs(p->'refs');
  if i=repeated or not pool_at ? pk or jsonb_typeof(p->'eligible_company_wip') is distinct from 'boolean' then raise exception 'CP7_BASELINE_POSITION';end if;
  position_keys:=array_append(position_keys,k);position_pools:=array_append(position_pools,(pool_at->>pk)::integer);
  num:=null;den:=null;room:=null;good:=null;
  if p->'projection'->>'quality'='SCENARIO' then
   proj:=p->'projection';num:=cp7_wip.pcs(proj->'numerator');den:=cp7_wip.pcs(proj->'denominator');
   room:=cp7_wip.pcs(proj->'eligible_input_pcs');good:=cp7_wip.pcs(proj->'projected_good_pcs');
   if den=0 or num>den then raise exception 'CP7_BASELINE_YIELD';end if;
  end if;
  numerators:=array_append(numerators,num);denominators:=array_append(denominators,den);
  eligible_input:=array_append(eligible_input,room);projected_good:=array_append(projected_good,good);
 end loop;
 select coalesce(jsonb_object_agg(a.value->>'key',a.o),'{}') into position_at from jsonb_array_elements(v->'positions'->'positions')with ordinality a(value,o);
 select min(f.o) into repeated from(select a.o,row_number()over(partition by a.value->>'position_key' order by a.o)n
  from jsonb_array_elements(v->'etas')with ordinality a(value,o)where a.value->>'position_key' is not null)f where f.n>1;
 i:=0;
 for eta in select value from jsonb_array_elements(v->'etas') loop
  i:=i+1;
  perform cp7_wip.fields(eta,array['position_key','at','refs']);k:=cp7_wip.key(eta->'position_key');perform cp7_wip.refs(eta->'refs');
  if i=repeated or not position_at ? k then raise exception 'CP7_BASELINE_ETA_BINDING';end if;
  if eta->'at'<>'null'::jsonb then perform cp7_demand.instant(eta->'at');end if;
 end loop;
 select coalesce(jsonb_object_agg(a.value->>'position_key',a.value),'{}') into eta_at from jsonb_array_elements(v->'etas')a;
 select min(f.o) into repeated from(select a.o,row_number()over(partition by a.value->>'key' order by a.o)n
  from jsonb_array_elements(v->'targets')with ordinality a(value,o)where a.value->>'key' is not null)f where f.n>1;
 i:=0;
 for t in select value from jsonb_array_elements(v->'targets') loop
  i:=i+1;
  perform cp7_wip.fields(t,array['key','size_id','need_pcs','deadline','risk_at','helps_at','production_status','refs']);k:=cp7_wip.key(t->'key');perform cp7_wip.key(t->'size_id');perform cp7_wip.refs(t->'refs');
  perform cp7_wip.pcs(t->'need_pcs');
  if i=repeated or t->>'production_status' is null or t->>'production_status' not in ('ACTIVE','STOP') then raise exception 'CP7_BASELINE_TARGET';end if;
  foreach e in array array[t->'deadline',t->'risk_at',t->'helps_at'] loop if e<>'null'::jsonb then perform cp7_demand.instant(e);end if;end loop;
  if target_at is null then
   select coalesce(jsonb_object_agg(a.value->>'key',a.value),'{}') into target_at from jsonb_array_elements(v->'matching'->'targets')a;
  end if;
  tf:=target_at->k;
  if tf is null or tf->>'size_id'<>t->>'size_id' or not ((t->'refs') @> (tf->'refs')) then raise exception 'CP7_BASELINE_TARGET_MATCH_BINDING';end if;
 end loop;
 -- The main loop's priority order (same ORDER BY, same input order).
 for t in select value from jsonb_array_elements(v->'targets') order by
  case when value->'risk_at'<>'null'::jsonb then cp7_demand.instant(value->'risk_at') end nulls last,
  case when value->'deadline'<>'null'::jsonb then cp7_demand.instant(value->'deadline') end nulls last,
  case when value->'helps_at'<>'null'::jsonb then cp7_demand.instant(value->'helps_at') end nulls last,
  cp7_wip.pcs(value->'need_pcs') desc,value->>'key' loop
  ordered:=array_append(ordered,t);
 end loop;
 -- The size lists and fact classes allocate builds at its first timed
 -- ACTIVE target. Every operand was validated above, so building them here
 -- raises nothing; they are unused when no such target exists.
 with x as(select a.o::integer o,a.value p,case when eta_at->(a.value->>'key')->'at'<>'null'::jsonb then cp7_demand.instant(eta_at->(a.value->>'key')->'at') end at
   from jsonb_array_elements(v->'positions'->'positions')with ordinality a(value,o)),
  r as(select x.o,x.p,x.at,row_number()over(order by x.at nulls last,x.p->>'key')rk from x)
 select(select coalesce(jsonb_object_agg(g.sz,g.os),'{}')from(select r.p->>'size_id' sz,jsonb_agg(r.o order by r.rk)os from r
    where r.p->'eligible_company_wip'<>'false'::jsonb group by 1)g),
  coalesce(array_agg(r.at order by r.o),'{}'),
  coalesce(array_agg(eta_at->(r.p->>'key') is null or eta_at->(r.p->>'key')->'at'='null'::jsonb or r.p->'projection'->>'quality' is distinct from 'SCENARIO' order by r.o),'{}')
  into size_lists,eta_times,reviewed from r;
 select coalesce(jsonb_object_agg(a.value->>'key',a.value),'{}') into source_at from jsonb_array_elements(v->'matching'->'sources')a;
 select coalesce(array_agg(f.id order by f.o),'{}'),coalesce(array_agg(f.s->>'confirmed_target' order by f.o),'{}'),coalesce(max(f.id),0) into source_ids,source_confirmed,sources_n
  from(select x.o,x.s,dense_rank()over(order by jsonb_build_array(x.s->'quality',x.s->'size_id',x.s->'confirmed_target'='null'::jsonb,x.s->'constraints')::text collate "C")::integer id
   from(select a.o,source_at->(a.value->>'key') s from jsonb_array_elements(v->'positions'->'positions')with ordinality a(value,o))x)f;
 select coalesce(jsonb_object_agg(f.k,f.id),'{}'),coalesce(max(f.id),0) into target_ids,targets_n
  from(select x.k,dense_rank()over(order by jsonb_build_array(x.tf->'size_id',x.tf->'constraints')::text collate "C")::integer id
   from(select a.value->>'key' k,target_at->(a.value->>'key') tf from jsonb_array_elements(v->'targets')a)x)f;
 return jsonb_build_object('ordered',to_jsonb(ordered),'target_at',target_at,'source_at',source_at,'size_lists',size_lists,
  'eta_times',to_jsonb(eta_times),'reviewed',to_jsonb(reviewed),'source_ids',to_jsonb(source_ids),'source_confirmed',to_jsonb(source_confirmed),
  'sources_n',sources_n,'target_ids',target_ids,'targets_n',targets_n,'position_keys',to_jsonb(position_keys),
  'position_pools',to_jsonb(position_pools),'remaining',to_jsonb(remaining),'eligible_input',to_jsonb(eligible_input),
  'projected_good',to_jsonb(projected_good),'numerators',to_jsonb(numerators),'denominators',to_jsonb(denominators),
  'carry',jsonb_build_object('capacity',capacity::text,'edges',0,
   'used',to_jsonb(array_fill(0::numeric,array[cardinality(position_keys)])),'good_used',to_jsonb(array_fill(0::numeric,array[cardinality(position_keys)])),
   'pool_used',to_jsonb(array_fill(0::numeric,array[cardinality(pool_wip)]))),'pool_wip',to_jsonb(pool_wip));
end $$;
create function cp7_analysis_stage.numerics(a jsonb)returns numeric[]
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select coalesce(array_agg(x.v::numeric order by x.o),'{}')from jsonb_array_elements_text(a)with ordinality x(v,o)
$$;
-- allocate's main loop for priority positions lo..hi of the ordered targets.
create function cp7_analysis_stage.alloc_step(s0 jsonb,carry jsonb,lo integer,hi integer,p_visits integer)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare t jsonb;s jsonb;tf jsonb;m jsonb;refs jsonb;k text;need numeric;left_need numeric;room numeric;good numeric;input_qty numeric;num numeric;den numeric;
 o integer;w integer;slot integer;target_id integer;target_proven boolean;deadline timestamptz;capacity numeric:=(carry->>'capacity')::numeric;edges_before integer:=(carry->>'edges')::integer;
 position_keys text[];position_pools integer[];remaining numeric[];eligible_input numeric[];projected_good numeric[];numerators numeric[];denominators numeric[];
 pool_wip numeric[];used numeric[];good_used numeric[];pool_used numeric[];eta_times timestamptz[];reviewed boolean[];source_ids integer[];source_confirmed text[];
 proven boolean[];verdicts jsonb[];sources_n integer:=(s0->>'sources_n')::integer;targets_n integer:=(s0->>'targets_n')::integer;
 target_at jsonb:=s0->'target_at';source_at jsonb:=s0->'source_at';size_lists jsonb:=s0->'size_lists';target_ids jsonb:=s0->'target_ids';
 edge_list jsonb[]:='{}';row_list jsonb[]:='{}';review_list jsonb[]:='{}';
begin
 select coalesce(array_agg(x.v order by x.o),'{}')into position_keys from jsonb_array_elements_text(s0->'position_keys')with ordinality x(v,o);
 if(hi-lo+1)::bigint*cardinality(position_keys)>p_visits then raise exception 'CP7_BASELINE_ALLOCATION_LIMIT';end if;
 select coalesce(array_agg(x.v::integer order by x.o),'{}')into position_pools from jsonb_array_elements_text(s0->'position_pools')with ordinality x(v,o);
 remaining:=cp7_analysis_stage.numerics(s0->'remaining');eligible_input:=cp7_analysis_stage.numerics(s0->'eligible_input');
 projected_good:=cp7_analysis_stage.numerics(s0->'projected_good');numerators:=cp7_analysis_stage.numerics(s0->'numerators');
 denominators:=cp7_analysis_stage.numerics(s0->'denominators');pool_wip:=cp7_analysis_stage.numerics(s0->'pool_wip');
 used:=cp7_analysis_stage.numerics(carry->'used');good_used:=cp7_analysis_stage.numerics(carry->'good_used');pool_used:=cp7_analysis_stage.numerics(carry->'pool_used');
 select coalesce(array_agg(x.v::timestamptz order by x.o),'{}')into eta_times from jsonb_array_elements_text(s0->'eta_times')with ordinality x(v,o);
 select coalesce(array_agg(x.v::boolean order by x.o),'{}')into reviewed from jsonb_array_elements_text(s0->'reviewed')with ordinality x(v,o);
 select coalesce(array_agg(x.v::integer order by x.o),'{}')into source_ids from jsonb_array_elements_text(s0->'source_ids')with ordinality x(v,o);
 select coalesce(array_agg(x.v order by x.o),'{}')into source_confirmed from jsonb_array_elements_text(s0->'source_confirmed')with ordinality x(v,o);
 proven:=array_fill(false,array[cardinality(position_keys)]);verdicts:=array_fill(null::jsonb,array[2*sources_n*targets_n]);
 for t in select x.value from jsonb_array_elements(s0->'ordered')with ordinality x(value,o)where x.o between lo and hi order by x.o loop
  need:=cp7_wip.pcs(t->'need_pcs');left_need:=need;
  if t->'deadline'='null'::jsonb or t->'risk_at'='null'::jsonb or t->'helps_at'='null'::jsonb then
   review_list:=array_append(review_list,jsonb_build_object('target_key',t->'key','reason','TIME_UNKNOWN','need_pcs',need::text));continue;end if;
  if t->>'production_status'='ACTIVE' then
   tf:=target_at->(t->>'key');
   deadline:=cp7_demand.instant(t->'deadline');target_id:=(target_ids->>(t->>'key'))::integer;target_proven:=false;
   for o in select value::integer from jsonb_array_elements_text(size_lists->(t->>'size_id')) loop
    exit when left_need=0 or capacity=0;
    k:=position_keys[o];w:=position_pools[o];
    if reviewed[o] then
     review_list:=array_append(review_list,jsonb_build_object('position_key',k,'target_key',t->'key','reason','ETA_OR_YIELD_UNKNOWN'));continue;end if;
    if eta_times[o]>deadline then continue;end if;
    s:=source_at->k;
    if s is null then raise exception 'CP7_BASELINE_SOURCE_MATCH_BINDING';end if;
    slot:=((target_id-1)*sources_n+source_ids[o]-1)*2+case when source_confirmed[o]=tf->>'key' then 2 else 1 end;
    m:=case when target_proven and proven[o] then verdicts[slot] end;
    if m is null then m:=cp7_wip.match_target(s,tf);verdicts[slot]:=m;proven[o]:=true;target_proven:=true;end if;
    if m->>'match' not in ('CANDIDATE_MATCH','CONFIRMED_TARGET') then
     review_list:=array_append(review_list,jsonb_build_object('position_key',k,'target_key',t->'key','reason',m));continue;end if;
    num:=numerators[o];den:=denominators[o];if num=0 then continue;end if;
    room:=least(remaining[o],eligible_input[o])-used[o];
    room:=least(room,pool_wip[w]-pool_used[w]);
    good:=greatest(0,least(left_need,capacity,floor(room*num/den),projected_good[o]-good_used[o]));
    if good=0 then continue;end if;input_qty:=ceil(good*den/num);
    select jsonb_agg(value order by value::text) into refs from (select distinct value from jsonb_array_elements((s->'refs')||(tf->'refs'))) q;
    edge_list:=array_append(edge_list,jsonb_build_object('key','edge-'||(edges_before+cardinality(edge_list)+1),'position_key',k,'target_key',t->'key','size_id',t->'size_id',
     'input_pcs',input_qty::text,'projected_good_pcs',good::text,'match',m->'match','refs',refs));
    used[o]:=used[o]+input_qty;good_used[o]:=good_used[o]+good;
    pool_used[w]:=pool_used[w]+input_qty;capacity:=capacity-good;left_need:=left_need-good;
   end loop;
  end if;
  row_list:=array_append(row_list,jsonb_build_object('target_key',t->'key','size_id',t->'size_id','need_pcs',need::text,'allocated_good_pcs',(need-left_need)::text,
   'unresolved_pcs',left_need::text,'production_status',t->'production_status','priority_basis',jsonb_build_object('risk_at',t->'risk_at','deadline',t->'deadline','helps_at',t->'helps_at','size_gap',t->'need_pcs','stable_key',t->'key')));
 end loop;
 return jsonb_build_object('carry',jsonb_build_object('capacity',capacity::text,'edges',edges_before+cardinality(edge_list),
  'used',to_jsonb(used),'good_used',to_jsonb(good_used),'pool_used',to_jsonb(pool_used)),
  'edges',to_jsonb(edge_list),'rows',to_jsonb(row_list),'reviews',to_jsonb(review_list));
end $$;
create function cp7_analysis_stage.alloc_final(v jsonb,carry jsonb,edges jsonb,rows jsonb,reviews jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare validation jsonb;
begin
 validation:=cp7_wip.check_allocations(v->'positions',jsonb_build_object('scenario_id',v->'scenario_id','scope_id',v->'scope_id','complete_scope',true,'matching',v->'matching','edges',edges));
 if validation->>'status'<>'FEASIBLE' then raise exception 'CP7_BASELINE_GENERATED_ALLOCATION_INVALID';end if;
 return jsonb_build_object('status','SCENARIO','kernel_version','greedy-allocation-1','scenario_id',v->'scenario_id','snapshot_id',v->'snapshot_id','scope_id',v->'scope_id',
  'rows',rows,'review_queue',reviews,'remaining_capacity_pcs',carry->>'capacity','allocation',validation,'inputs',v,
  'reason','GLOBAL_SCOPE_RECOMPUTED_MATCH_YIELD_POOL_CAPACITY_PRIORITY_SIMULATION_ONLY');
end $$;

-- --------------------------------------------------------------- analysis --
-- build_operational's per-target loop for one chunk of netting rows (loop
-- order). The maps hold only this chunk's keys, built as build builds them.
-- Returns every target's items per per-target array, in loop order: the
-- single build's arrays are these items concatenated.
create function cp7_analysis_stage.analysis_targets(c jsonb,rows jsonb,products_by_root jsonb,stock_by_target jsonb,history_by_target jsonb,
 edges_by_target jsonb,match_results_by_target jsonb,plan_aids jsonb,fabric_plan jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare r jsonb;refs jsonb;policy text;product jsonb;stock jsonb;hist jsonb;commercial jsonb;row_aids jsonb;v jsonb;target_timeline jsonb;
 t_assumptions jsonb;t_warnings jsonb;t_actions jsonb;t_recommendations jsonb;t_models jsonb;t_materials jsonb;t_metrics jsonb;t_timeline jsonb;
 targets_acc jsonb[]:='{}';known_keys text[]:='{}';materials_null boolean:=false;
 demand_unknown boolean:=false;captured text:=c->>'captured_at';
begin
 for r in select x.value from jsonb_array_elements(rows)with ordinality x(value,o)order by x.o loop
  t_assumptions:='[]';t_warnings:='[]';t_actions:='[]';t_recommendations:='[]';t_models:='[]';t_materials:='[]';t_metrics:='[]';t_timeline:='[]';
  if r->'demand_estimate'->>'daily_pcs'is null then demand_unknown:=true;end if;
  refs:=r->'refs';policy:=r->'production_policy'->'policy'->>'state';
  if policy is null then
   t_warnings:=jsonb_build_array('PRODUCTION_POLICY_UNREVIEWED:'||(r->>'target_key'));
   t_actions:=jsonb_build_array(jsonb_build_object('key','review-policy-'||(r->>'target_key'),
    'intent','REVIEW_SOURCE','source_keys','[]'::jsonb,'target_keys','[]'::jsonb,'primary_reason','PRODUCTION_POLICY_UNREVIEWED',
    'conditional',false,'source_links',refs,'display_priority',jsonb_build_object('rank',null,'lane','REVIEW_DATA',
     'basis',jsonb_build_array('Status produksi produk perlu diperiksa'),'rule_version','native-review-1')));
   targets_acc:=array_append(targets_acc,jsonb_build_object('assumptions',t_assumptions,'warnings',t_warnings,'actions',t_actions,
    'recommendations',t_recommendations,'models',t_models,'materials',t_materials,'metrics',t_metrics,'timeline',t_timeline));continue;
  end if;
  product:=products_by_root->split_part(r->>'target_key',':',1);
  stock:=stock_by_target->(r->>'target_key');hist:=history_by_target->(r->>'target_key');
  if jsonb_array_length(product)>1 or jsonb_array_length(stock)>1 or jsonb_array_length(hist)>1 then
   raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';
  end if;
  product:=product->0;stock:=stock->0;hist:=hist->0;
  row_aids:=plan_aids;
  if r->'profile'->>'quality'='SELECTED_ASSUMPTION'then
   row_aids:=row_aids||jsonb_build_array(r->'profile'->>'profile_id');
   t_assumptions:=jsonb_build_array(jsonb_build_object('id',r->'profile'->>'profile_id',
    'label','Aturan permintaan dan target yang dipilih untuk '||(r->>'sku'),
    'origin','OWNER_INPUT','confirmed_for_operation',false));
  end if;
  commercial:=product->'commercial'->0;known_keys:=array_append(known_keys,r->>'target_key');
  t_recommendations:=jsonb_build_array(jsonb_build_object(
   'target',jsonb_build_object('kind','PRODUCT','key',r->'target_key','brand_id',product->'brand_id',
    'product_id',product->'root_id','product_version_id',product->'id','size_id',r->'size_id',
    'commercial_identity',jsonb_build_object('state',case when commercial is null then 'LEGACY_UNMAPPED'else 'RESOLVED'end,
     'sku_id',commercial->'sku_id','sku_version_id',commercial->'version_id',
     'membership_version_id',case when commercial is null then null else(commercial->>'version_id')||':'||(product->>'root_id')end,
     'grouping_basis','CURRENT_RESTATED')),
   'production_state',policy,'actual_fg',cp7_analysis_native.fact(stock->'availability'->>'physical_fg_pcs','PCS',stock->'refs'),
   'target_qty',cp7_analysis_native.fact(r->'target'->>'target_pcs','PCS',refs,row_aids),
   'q_base',cp7_analysis_native.fact(r->>'base_gap_pcs','PCS',refs,row_aids),
   'q_conditional',cp7_analysis_native.fact(r->>'conditional_gap_pcs','PCS',refs,row_aids),
   'suggested_new',cp7_analysis_native.fact(case when policy in('PAUSED','STOPPED')then '0'else null end,'PCS',refs),
   'rounding_extra',cp7_analysis_native.fact(null,'PCS',refs),
   'feasible_new',cp7_analysis_native.fact(case when policy in('PAUSED','STOPPED')then '0'else null end,'PCS',refs),
   'unresolved_qty',cp7_analysis_native.fact(case when policy in('PAUSED','STOPPED')then r->>'base_gap_pcs'else null end,'PCS',refs,row_aids),
   'reason_codes',jsonb_build_array('MATERIAL_FEASIBILITY_NOT_PROVEN'),'assumption_ids',row_aids));
  if r->'demand_estimate'->>'daily_pcs'is not null and r->'target'->>'horizon_days'is not null then
  t_models:=jsonb_build_array(jsonb_build_object('target_key',r->'target_key','method_id',coalesce(r->'demand_estimate'->>'basis','NATIVE_AVAILABLE_HISTORY'),
   'version','native-available-history-fallback-1','mode','FALLBACK',
   'demand_rate',cp7_analysis_native.fact(r->'demand_estimate'->>'daily_pcs','PCS/DAY',refs,row_aids),
   'observed_days',hist->'available_days','stockout_days',hist->'stockout_days','unknown_days',hist->'unknown_days',
   'horizon_days',ceil((r->'target'->>'horizon_days')::numeric),
   'selection_reason','Native available-history/manual fallback; no backtest promotion without earlier-known training evidence',
   'validation_fold_ids','[]'::jsonb,'scores','[]'::jsonb));
  end if;
  v:=cp7_analysis_native.material_needs(c,r,row_aids);
  if v is null then materials_null:=true;else t_materials:=t_materials||('[]'::jsonb||v);end if;
  v:=cp7_fabric_native.needs(c,r,row_aids,fabric_plan);
  if v is null then materials_null:=true;else t_materials:=t_materials||('[]'::jsonb||v);end if;
  t_metrics:=jsonb_build_array(jsonb_build_object('metric_id','AVAILABLE_FG_PCS:'||(r->>'target_key'),'version','native-availability-1',
   'value',cp7_analysis_native.fact(r->>'available_fg_pcs','PCS',refs),'formula_ref','NATIVE_PHYSICAL_MINUS_ACTIVE_DRAFT_RESERVATIONS_ONCE',
   'operands',jsonb_build_array(cp7_analysis_native.fact(stock->'availability'->>'physical_fg_pcs','PCS',stock->'refs'),
    cp7_analysis_native.fact(stock->'availability'->>'reserved_pcs','PCS',stock->'refs')),
   'readiness','READY','scope_kind','TARGET','scope_key',r->'target_key',
   'period_start',((captured::timestamptz)at time zone 'Asia/Jakarta')::date::text,
   'period_end',((captured::timestamptz)at time zone 'Asia/Jakarta')::date::text,'knowledge_mode','CURRENT'));
  t_actions:=jsonb_build_array(jsonb_build_object('key','review-material-'||(r->>'target_key'),'intent','REVIEW_SOURCE',
   'source_keys','[]'::jsonb,'target_keys',jsonb_build_array(r->'target_key'),'primary_reason','MATERIAL_FEASIBILITY_NOT_PROVEN',
   'conditional',true,'source_links',refs,'display_priority',jsonb_build_object('rank',null,'lane','REVIEW_DATA',
    'basis',jsonb_build_array('Periksa bahan dan batas produksi baru'),'rule_version','native-review-1')));
  declare n jsonb:=jsonb_build_object('allocation',jsonb_build_object('allocation',jsonb_build_object('edges',
   coalesce(edges_by_target->(r->>'target_key'),'[]'::jsonb))),'match_results',coalesce(match_results_by_target->(r->>'target_key'),'[]'::jsonb));
  begin
  with events as materialized(
   select x.value event,x.value->'event' e,x.ordinality ordinal
    from jsonb_array_elements(coalesce(r->'timeline'->'events','[]'))with ordinality x),
  classified as materialized(
   select events.*,case when events.e->>'kind'='SUPPLY'then coalesce(
    (select x->>'match'from jsonb_array_elements(coalesce(n->'allocation'->'allocation'->'edges','[]'))x
     where 'supply-'||(x->>'key')=events.e->>'key'and x->>'target_key'=r->>'target_key'limit 1),
    case when exists(select 1 from jsonb_array_elements(n->'match_results')x
     where 'supply-'||(x->>'position_key')=events.e->>'key'and x->>'target_key'=r->>'target_key'and x->'result'->>'match'='CONFIRMED_TARGET')then'CONFIRMED_TARGET'end)
    else null end supply_match from events)
  select coalesce(jsonb_agg(jsonb_build_object('date',((t.e->>'at')::timestamptz at time zone 'Asia/Jakarta')::date::text,
    'target_key',r->'target_key','demand',cp7_analysis_native.fact(case when t.e->>'kind'='DEMAND'then t.e->>'qty_pcs'else '0'end,'PCS',t.e->'refs',row_aids),
    'directed_supply',cp7_analysis_native.fact(case when t.e->>'kind'='DEMAND'or t.supply_match='CANDIDATE_MATCH'then '0'
     when t.supply_match='CONFIRMED_TARGET'then t.e->>'qty_pcs'else null end,'PCS',t.e->'refs',row_aids),
    'candidate_supply',cp7_analysis_native.fact(case when t.e->>'kind'='DEMAND'or t.supply_match='CONFIRMED_TARGET'then '0'
     when t.supply_match='CANDIDATE_MATCH'then t.e->>'qty_pcs'else null end,'PCS',t.e->'refs',row_aids),
    'proposed_new_supply',cp7_analysis_native.fact(null,'PCS',t.e->'refs'),'balance_end',cp7_analysis_native.fact(t.event->>'balance_pcs','PCS',t.e->'refs',row_aids),
    'mode','BACKLOG','assumed',true,'unmet_demand',cp7_analysis_native.fact(t.event->>'new_unmet_pcs','PCS',t.e->'refs',row_aids),
    'backlog_qty',cp7_analysis_native.fact(case when t.event->>'balance_pcs'is not null then greatest(0,-(t.event->>'balance_pcs')::numeric)::text else null end,'PCS',t.e->'refs',row_aids),
    'min_intraday_balance',cp7_analysis_native.fact(r->'timeline'->>'minimum_balance_pcs','PCS',t.e->'refs',row_aids),
    'first_gap_at',r->'timeline'->'first_known_gap'->'at','timing_basis','DATE_POLICY',
    'timing_policy_id','selected-native-each24h-from-capture-1','event_refs',t.e->'refs')order by t.ordinal),'[]'::jsonb)into target_timeline from classified t;
  t_timeline:=t_timeline||target_timeline;
  end;
  targets_acc:=array_append(targets_acc,jsonb_build_object('assumptions',t_assumptions,'warnings',t_warnings,'actions',t_actions,
   'recommendations',t_recommendations,'models',t_models,'materials',t_materials,'metrics',t_metrics,'timeline',t_timeline));
 end loop;
 return jsonb_build_object('targets',to_jsonb(targets_acc),'known_keys',to_jsonb(known_keys),'demand_unknown',demand_unknown,'materials_null',materials_null);
end $$;
-- What analysis_targets reads of the capture for one chunk of target keys:
-- the capture clock and the accessory source rows material_needs can reach
-- for those roots (array order kept). material_needs takes the first
-- selected row of a root, the first version of its id, that version's items
-- (in id order) and the first category of each item's id: the same rows are
-- first here. A source whose parts are not all arrays is passed whole, so it
-- fails as it does in build. (Whole, each call copied the whole source: at
-- 5000 targets 4.8 s per 250-target chunk, LOCAL.) fabric needs reads only
-- the row and the plan.
create function cp7_analysis_stage.material_scope(c jsonb,keys text[])returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare ms jsonb:=c->'material_source';roots jsonb;sel jsonb;vids jsonb;items jsonb;cids jsonb;
begin
 if jsonb_typeof(ms)is distinct from 'object'or jsonb_typeof(ms->'selected')is distinct from 'array'or jsonb_typeof(ms->'versions')is distinct from 'array'
  or jsonb_typeof(ms->'items')is distinct from 'array'or jsonb_typeof(ms->'categories')is distinct from 'array'then return c;end if;
 select coalesce(jsonb_object_agg(r,true),'{}')into roots from(select distinct split_part(k,':',1)r from unnest(keys)k where k is not null)x where r is not null;
 select coalesce(jsonb_agg(x order by o),'[]'),coalesce(jsonb_object_agg(x->>'version_id',true)filter(where x->>'version_id'is not null),'{}')into sel,vids
  from jsonb_array_elements(ms->'selected')with ordinality a(x,o)where roots?(x->>'root_id');
 select coalesce(jsonb_agg(x order by o),'[]'),coalesce(jsonb_object_agg(x->>'category_id',true)filter(where x->>'category_id'is not null),'{}')into items,cids
  from jsonb_array_elements(ms->'items')with ordinality a(x,o)where vids?(x->>'bom_version_id');
 return jsonb_build_object('captured_at',c->'captured_at','material_source',ms||jsonb_build_object('selected',sel,
  'versions',(select coalesce(jsonb_agg(x order by o),'[]')from jsonb_array_elements(ms->'versions')with ordinality a(x,o)where vids?(x->>'id')),
  'items',items,
  'categories',(select coalesce(jsonb_agg(x order by o),'[]')from jsonb_array_elements(ms->'categories')with ordinality a(x,o)where cids?(x->>'id'))));
end $$;
-- build_operational after its target loop, plus build's finance overlay
-- (without the semantic hash). The per-target arrays are not materialized:
-- each is one sentinel string (tag||field) when it has items, where the
-- stored per-target items go (header: removed; pages: the items). meta: known_keys, demand_unknown,
-- materials_null and the item count per field over all chunks.
create function cp7_analysis_stage.analysis_skeleton(c jsonb,q jsonb,p_run uuid,a jsonb,scenario jsonb,alloc jsonb,matching jsonb,
 meta jsonb,identity_unknown boolean,tag text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare wip jsonb:=scenario->'wip';p jsonb;e jsonb;eta jsonb;part jsonb;k text;part_hash text;count_facts integer:=0;part_count integer;
 plan_refs jsonb:='[]';plan_aids jsonb:='[]';assumptions jsonb;sources jsonb;recommendations jsonb;edges jsonb;actions jsonb;timeline jsonb;
 models jsonb;materials jsonb;metrics jsonb;warnings jsonb;dependencies jsonb:='[]';known_targets jsonb;v jsonb;
 complete boolean:=c->>'status'='COMPLETE'and wip->>'status'='COMPLETE';hash text:=cp7_analysis_native.fingerprint(c);
 allocation_known boolean:=alloc->>'status'='SCENARIO';allocated numeric;load numeric;
 scenario_revision bigint:=coalesce((c->'schedule'->>'revision')::bigint,0);
 schedule_assumption jsonb:='[]';fabric_assumptions jsonb[]:='{}';edges_acc jsonb[]:='{}';sources_acc jsonb[]:='{}';
 etas_by_position jsonb;inputs_by_source jsonb;directed_source_keys jsonb;source_inputs jsonb;
 warnings0 jsonb:='["MATERIAL_FEASIBILITY_NOT_PROVEN","ADAPTIVE_MODEL_PROMOTION_NOT_PROVEN","FINANCIAL_DOMAIN_NOT_CAPTURED"]';
begin
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
   fabric_assumptions:=array_append(fabric_assumptions,jsonb_build_object('id',part->>'id',
    'label','Pemakaian kain per PCS untuk '||(part->>'target_key')||' yang dipilih; bukan konsumsi, pemasangan atau alokasi aktual',
    'origin','OWNER_INPUT','confirmed_for_operation',false));
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
  'versions',jsonb_build_object('engine',c->'analysis_engine_signature','policy',cp7_supply_native.fingerprint(c),'models','native-available-history-fallback-1',
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
create function cp7_analysis_stage.sentinel(meta jsonb,tag text,field text)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case when coalesce((meta->'counts'->>field)::integer,0)>0 then jsonb_build_array(tag||field)else '[]'::jsonb end
$$;
-- The per-target arrays whose items are stored per target (fragments) and paged.
create function cp7_analysis_stage.fragment_fields()returns text[]
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select array['assumptions','warnings','actions','recommendations','models','materials','metrics','timeline']
$$;

-- ------------------------------------------------------------------- jobs --
-- A job is one actor's request over ONE stored reference (jobs.reference).
-- units is the plan, grown three times: HIST_PREP fixes the scenario units
-- and NET_PREP; NET_PREP the netting, allocation and analysis units up to
-- ANA_META; ANA_META the pages (their number is byte-adaptive, known only
-- once every target's item sizes are stored) and PAGE_INDEX, then plan_final.
-- outputs and every intermediate row are written once per unit, never
-- changed; progress is read from these rows, so a reload shows the true state.
create table cp7_analysis_stage.jobs(id uuid primary key,actor uuid not null,request_id uuid not null,query jsonb not null,
 reference jsonb not null,run_id uuid not null unique,access_at_capture jsonb not null,captured_at timestamptz not null,source_hash text not null,
 state text not null check(state in('RUNNING','DONE','FAILED')),unit_count integer not null check(unit_count>0),
 units_done integer not null default 0,plan_final boolean not null default false,targets_total integer,positions_total integer,
 unit_attempts integer not null default 0,failure_unit integer,failure_sqlstate text,failure_code text,failure_message text,
 created_at timestamptz not null,updated_at timestamptz not null,unique(actor,request_id),
 check(units_done between 0 and unit_count),check((state='FAILED')=(failure_code is not null)),
 check((state='DONE')=(plan_final and units_done=unit_count)));
create table cp7_analysis_stage.units(job_id uuid not null references cp7_analysis_stage.jobs(id),idx integer not null check(idx>=0),
 kind text not null,chunk integer not null,lo integer,hi integer,primary key(job_id,idx));
create table cp7_analysis_stage.outputs(job_id uuid not null,idx integer not null,output jsonb not null,server_ms numeric not null,
 finished_at timestamptz not null,primary key(job_id,idx),foreign key(job_id,idx)references cp7_analysis_stage.units(job_id,idx));
create table cp7_analysis_stage.target_rows(job_id uuid not null references cp7_analysis_stage.jobs(id),kind text not null,ord integer not null,
 key text,payload jsonb not null,primary key(job_id,kind,ord));
create index cp7_analysis_stage_target_key on cp7_analysis_stage.target_rows(job_id,kind,key);
create table cp7_analysis_stage.pair_rows(job_id uuid not null references cp7_analysis_stage.jobs(id),i integer not null,pair_row jsonb not null,primary key(job_id,i));
create table cp7_analysis_stage.pair_lists(job_id uuid not null references cp7_analysis_stage.jobs(id),chunk integer not null,key text not null,
 results jsonb not null,primary key(job_id,key,chunk));
-- One target's items of one per-target array (ord: the target's position in
-- the job's loop order) as canonical jsonb text (the items joined by ', ', no
-- brackets) with its UTF8 size; only targets with items. PAGES cuts pages at
-- any target boundary from these rows, by bytes.
create table cp7_analysis_stage.fragments(job_id uuid not null references cp7_analysis_stage.jobs(id),ord integer not null check(ord>=1),field text not null,
 body text not null,items integer not null check(items>0),utf8_bytes integer not null check(utf8_bytes>=0),primary key(job_id,field,ord));
-- The header (cp7.native-analysis-header.v1): the Original without the
-- per-target items, with the paged arrays and the page cut; written by ANA_META.
create table cp7_analysis_stage.headers(run_id uuid primary key references cp7_analysis_stage.jobs(run_id),job_id uuid not null references cp7_analysis_stage.jobs(id),
 body text not null,utf8_bytes integer not null check(utf8_bytes between 1 and 8000000),sha256 text not null,paged jsonb not null,
 targets_total integer not null check(targets_total>=0),page_count integer not null check(page_count>=0),cuts jsonb not null,
 check((page_count=0)=(targets_total=0)));
-- One page (cp7.native-analysis-page.v1): the items of targets lo..hi.
create table cp7_analysis_stage.pages(run_id uuid not null references cp7_analysis_stage.headers(run_id),idx integer not null check(idx>=0),
 target_lo integer not null,target_hi integer not null,counts jsonb not null,offsets jsonb not null,summary jsonb not null,
 body text not null,utf8_bytes integer not null check(utf8_bytes between 1 and 8000000),sha256 text not null,
 primary key(run_id,idx),check(target_lo between 1 and target_hi));
-- The page index, written LAST by PAGE_INDEX: the identity hash over the
-- header and every page, the whole-run totals. A run without it exposes no page.
create table cp7_analysis_stage.page_sets(run_id uuid primary key references cp7_analysis_stage.headers(run_id),identity_hash text not null,
 totals jsonb not null,created_at timestamptz not null);
do $$declare t text;begin
 foreach t in array array['jobs','units','outputs','target_rows','pair_rows','pair_lists','fragments','headers','pages','page_sets']loop
  execute format('alter table cp7_analysis_stage.%I owner to cp7_capture',t);
  execute format('alter table cp7_analysis_stage.%I enable row level security',t);
  execute format('create policy cp7_analysis_stage_no_access on cp7_analysis_stage.%I for all to public using(false)with check(false)',t);
  execute format('revoke all on cp7_analysis_stage.%I from public,anon,authenticated,service_role',t);
 end loop;
 foreach t in array array['units','outputs','target_rows','pair_rows','pair_lists','fragments','headers','pages','page_sets']loop
  execute format('create trigger immutable_stage_%s before update or delete on cp7_analysis_stage.%I for each row execute function cp7_private.immutable_run()',t,t);
 end loop;
end $$;
-- The job row: only its progress columns ever change. Its identity, query,
-- reference, access at capture and run id are immutable (an UPDATE naming
-- one of them is refused), and a job row is never deleted.
create trigger immutable_stage_jobs before update of id,actor,request_id,query,reference,access_at_capture,captured_at,source_hash,run_id,created_at or delete
 on cp7_analysis_stage.jobs for each row execute function cp7_private.immutable_run();

-- Declared bounds, once. Per unit: targets per chunk, pairs per chunk,
-- position-target visits and targets per allocation step, history cells,
-- sales and stock products per unit, UTF8 bytes per page and per header (the
-- existing segment body bound). Per job: targets (the declared capacity),
-- history cells, pairs, matching products; positions <= 1000 and demand
-- events <= 50000 are the kernels' own caps, kept. Chunk sizes are
-- LOCAL_PG16_DEV-derived (phase B: real timelines make ~60 KB of analysis
-- per target; 500 targets / 100000 pairs per unit took 4.6 / 6.5 s).
create function cp7_analysis_stage.bounds()returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('targets_per_chunk',250,'pairs_per_chunk',25000,'visits_per_allocation_step',100000,'allocation_targets_per_step',1000,
  'history_cells_per_unit',12500,'sales_per_events_unit',2500,'targets_per_stock_unit',1000,
  'job_targets',5000,'job_history_cells',500000,'job_pairs',1000000,'job_matching_products',10000,
  'page_utf8_bytes',8000000,'header_utf8_bytes',8000000)
$$;

-- The job status (cp7.native-analysis-staged-job.v1), read from the rows:
-- the next unit's stage, stage k of n, units done, targets done in the
-- current per-target stage, the reference, the last progress time, the
-- statement-limit stops of the current unit, run_id only when DONE, the
-- failure only when FAILED. A partial job never exposes a result.
create function cp7_analysis_stage.status(p_job uuid)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('contract_version','cp7.native-analysis-staged-job.v1','request_id',j.request_id,'state',j.state,
  'stage',u.kind,'stage_index',(select count(distinct x.kind)from cp7_analysis_stage.units x where x.job_id=j.id and x.idx<=coalesce(u.idx,j.units_done-1)),
  'stage_count',(select count(distinct x.kind)from cp7_analysis_stage.units x where x.job_id=j.id),
  'units_done',j.units_done,'unit_count',j.unit_count,'plan_final',j.plan_final,'targets_total',j.targets_total,
  'targets_done_in_stage',(select coalesce(sum(x.hi-x.lo+1),0)from cp7_analysis_stage.units x where x.job_id=j.id and x.kind=u.kind and x.idx<j.units_done and x.lo is not null
   and x.kind in('HIST_ROWS','HIST_STOCK','BASE_ROWS','NET_TARGETS','ALLOC_STEP','NET_ROWS','ANA_TARGETS','PAGES')),
  'reference',jsonb_build_object('captured_at',j.captured_at,'source_hash',j.source_hash),
  'last_progress_at',j.updated_at,'unit_attempts',j.unit_attempts,
  'run_id',case when j.state='DONE'then j.run_id end,
  'failure',case when j.state='FAILED'then jsonb_build_object('unit',j.failure_unit,'sqlstate',j.failure_sqlstate,'code',j.failure_code)end,
  'apply_enabled',false,'production_go',false)
 from cp7_analysis_stage.jobs j left join cp7_analysis_stage.units u on u.job_id=j.id and u.idx=j.units_done where j.id=p_job
$$;

-- The job over one reference, fingerprinted once (= the run's source hash).
-- The run id is fixed here; HIST_PREP is the first unit and plans the next.
create function cp7_analysis_stage.create_job(p_actor uuid,p_request uuid,p_query jsonb,p_access jsonb,p_facts jsonb)returns uuid
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare j uuid:=gen_random_uuid();now_at timestamptz:=clock_timestamp();hash text:=cp7_analysis_native.fingerprint(p_facts);
begin
 insert into cp7_analysis_stage.jobs(id,actor,request_id,query,reference,run_id,access_at_capture,captured_at,source_hash,state,unit_count,targets_total,created_at,updated_at)
 values(j,p_actor,p_request,p_query,p_facts,gen_random_uuid(),p_access,(p_facts->>'captured_at')::timestamptz,hash,'RUNNING',1,
  case when jsonb_typeof(p_facts->'facts'->'products')='array'
   and jsonb_array_length(p_facts->'facts'->'products')<=(cp7_analysis_stage.bounds()->>'job_targets')::integer
   then jsonb_array_length(p_facts->'facts'->'products')end,now_at,now_at);
 insert into cp7_analysis_stage.units values(j,0,'HIST_PREP',0,null,null);
 return j;
end $$;

create function cp7_analysis_stage.output(p_job uuid,p_kind text)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select o.output||'{}'::jsonb from cp7_analysis_stage.outputs o join cp7_analysis_stage.units u using(job_id,idx)
 where o.job_id=p_job and u.kind=p_kind order by u.idx desc limit 1
$$;

-- The sentinel prefix of a job: a per-target array of the header skeleton is
-- one string tag||field where the items go (unique per job).
create function cp7_analysis_stage.tag(p_job uuid)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$select 'P19-STAGED-'||p_job::text||'-'$$;
-- Fragment field -> analysis array key, and back.
create function cp7_analysis_stage.page_field(f text)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case f when 'warnings'then 'generation_warnings'when 'models'then 'demand_models'when 'materials'then 'material_needs'else f end
$$;
create function cp7_analysis_stage.fragment_field(k text)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select case k when 'generation_warnings'then 'warnings'when 'demand_models'then 'models'when 'material_needs'then 'materials'else k end
$$;
-- The paged arrays of a finished analysis: an array is paged iff its sentinel
-- survived ANA_META (it has per-target items and, for material_needs, is not
-- null); prefix = the sentinel's index (global items before the per-target
-- items), items = the per-target item count over all targets.
create function cp7_analysis_stage.page_layout(p_job uuid,skel jsonb,tag text)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare f text;k text;pos bigint;hits bigint;n bigint;paged jsonb:='{}';
begin
 foreach f in array cp7_analysis_stage.fragment_fields()loop
  k:=cp7_analysis_stage.page_field(f);
  if jsonb_typeof(skel->k)='array'then
   select min(x.o)-1,count(*)into pos,hits from jsonb_array_elements(skel->k)with ordinality x(v,o)where x.v=to_jsonb(tag||f);
   if hits>1 then raise exception 'CP7_ANALYSIS_PAGE_LAYOUT';end if;
   if hits=1 then
    select coalesce(sum(x.items),0)into n from cp7_analysis_stage.fragments x where x.job_id=p_job and x.field=f;
    if n<1 then raise exception 'CP7_ANALYSIS_PAGE_LAYOUT';end if;
    paged:=paged||jsonb_build_object(k,jsonb_build_object('field',f,'prefix',pos,'items',n));
   end if;
  end if;
 end loop;
 return paged;
end $$;
-- The page cut: contiguous targets in loop order, each page's items (over
-- the paged arrays, ', ' per item list) within the page bound less a fixed
-- reserve for the page envelope (ids, counts, offsets, totals, summary).
-- A single target above that budget refuses: a target is never cut.
create function cp7_analysis_stage.page_cuts(p_job uuid,layout jsonb,ntargets integer,page_bytes integer)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare budget integer:=page_bytes-4096;sizes integer[];i integer;bytes integer;acc integer:=0;lo integer:=1;cuts jsonb:='[]';
begin
 if ntargets=0 then return cuts;end if;
 if budget<1 then raise exception 'CP7_ANALYSIS_PAGE_BODY_LIMIT';end if;
 select coalesce(array_agg(coalesce(s.bytes,0)order by o.ord),'{}')into sizes from generate_series(1,ntargets)o(ord)
  left join(select x.ord,sum(x.utf8_bytes+2)::integer bytes from cp7_analysis_stage.fragments x
   where x.job_id=p_job and x.field in(select value->>'field'from jsonb_each(layout))group by x.ord)s on s.ord=o.ord;
 for i in 1..ntargets loop
  bytes:=sizes[i];
  if bytes>budget then raise exception 'CP7_ANALYSIS_PAGE_BODY_LIMIT';end if;
  if acc+bytes>budget then cuts:=cuts||jsonb_build_array(jsonb_build_array(lo,i-1));lo:=i;acc:=0;end if;
  acc:=acc+bytes;
 end loop;
 return cuts||jsonb_build_array(jsonb_build_array(lo,ntargets));
end $$;
-- Per page: recommendations by production state and targets whose production
-- policy is unreviewed (their only item is the review-policy action).
create function cp7_analysis_stage.page_summary(items jsonb)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('recommendations',jsonb_build_object(
   'ACTIVE',count(*)filter(where r->>'production_state'='ACTIVE'),'PAUSED',count(*)filter(where r->>'production_state'='PAUSED'),
   'STOPPED',count(*)filter(where r->>'production_state'='STOPPED'),
   'OTHER',count(*)filter(where r->>'production_state'is null or r->>'production_state'not in('ACTIVE','PAUSED','STOPPED'))),
  'policy_unreviewed',(select count(*)from jsonb_array_elements(coalesce(items->'actions','[]'))x where x->>'primary_reason'='PRODUCTION_POLICY_UNREVIEWED'))
 from jsonb_array_elements(coalesce(items->'recommendations','[]'))r
$$;

-- The scenario units (PHASE B). HIST_PREP fixes the plan up to NET_PREP; each
-- later unit reads the stored reference and earlier units' rows only.
create function cp7_analysis_stage.run_scenario_unit(j cp7_analysis_stage.jobs,u cp7_analysis_stage.units,c jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare b jsonb:=cp7_analysis_stage.bounds();g jsonb;val jsonb;out jsonb;v jsonb;idx integer;n integer;k integer;per integer;days integer;
 keys jsonb;roots jsonb;sub jsonb;avail jsonb;latest jsonb;rows jsonb;offs integer;cut jsonb;
begin
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

-- One unit. Reads the stored reference and earlier units' rows only.
create function cp7_analysis_stage.run_unit(j cp7_analysis_stage.jobs,u cp7_analysis_stage.units)returns jsonb
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
 c:=j.reference||'{}'::jsonb;
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
  select coalesce(jsonb_agg(x.payload order by x.ord),'[]'),coalesce(array_agg(x.key),'{}')into rows,keys
   from cp7_analysis_stage.target_rows x where x.job_id=j.id and x.kind='NETROW'and x.ord between u.lo and u.hi;
  out:=cp7_analysis_stage.analysis_targets(cp7_analysis_stage.material_scope(c,keys),rows,
   (select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)from(select x->>'root_id'k,jsonb_agg(x)items from jsonb_array_elements(c->'facts'->'products')x
     where x->>'root_id'=any(select split_part(y,':',1)from unnest(keys)y)group by x->>'root_id')i),
   (select coalesce(jsonb_object_agg(i.k,i.items),'{}'::jsonb)from(select x.key k,jsonb_agg(x.payload order by x.ord)items from cp7_analysis_stage.target_rows x
     where x.job_id=j.id and x.kind='STOCK'and x.key=any(keys)group by x.key)i),
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
  return jsonb_build_object('known_keys',out->'known_keys','demand_unknown',out->'demand_unknown','materials_null',out->'materials_null',
   'counts',(select coalesce(jsonb_object_agg(i.field,i.n),'{}'::jsonb)from(select f.field,sum(jsonb_array_length(x.v->f.field))n
     from jsonb_array_elements(out->'targets')x(v)cross join unnest(cp7_analysis_stage.fragment_fields())f(field)group by 1)i));
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

-- One ordinary request: run the job's next unit, persist it, report progress.
-- A concurrent caller does not wait (skip locked), runs nothing and only
-- reads the status (worker_active). p_access, when given, is the actor's
-- current access: a job whose access at capture differs is FAILED
-- (CP7_ANALYSIS_ACCESS_CHANGED) instead of mixing two access states. The
-- statement limit stopping a unit is retried by the next call (inputs are
-- immutable, so a retry computes the same unit); three stops fail the job.
-- Any other refusal fails the job with its code: the reference is fixed, so
-- a retry would refuse the same way. A step after DONE or FAILED returns the
-- same status and changes nothing.
create function cp7_analysis_stage.step(p_job uuid,p_access jsonb default null)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare j cp7_analysis_stage.jobs%rowtype;u cp7_analysis_stage.units%rowtype;out jsonb;t0 timestamptz;
begin
 select *into j from cp7_analysis_stage.jobs where id=p_job for update skip locked;
 if not found then
  if not exists(select 1 from cp7_analysis_stage.jobs where id=p_job)then raise exception 'CP7_ANALYSIS_JOB_UNAVAILABLE';end if;
  return cp7_analysis_stage.status(p_job)||jsonb_build_object('worker_active',true);
 end if;
 if j.state<>'RUNNING'then return cp7_analysis_stage.status(p_job);end if;
 if p_access is not null and p_access is distinct from j.access_at_capture then
  update cp7_analysis_stage.jobs set state='FAILED',updated_at=clock_timestamp(),failure_unit=units_done,failure_sqlstate='42501',
   failure_code='CP7_ANALYSIS_ACCESS_CHANGED',failure_message='CP7_ANALYSIS_ACCESS_CHANGED'where id=j.id;
  return cp7_analysis_stage.status(p_job);
 end if;
 select *into u from cp7_analysis_stage.units where job_id=j.id and idx=j.units_done;
 begin
  t0:=clock_timestamp();
  out:=cp7_analysis_stage.run_unit(j,u);
  insert into cp7_analysis_stage.outputs values(j.id,u.idx,out,round(extract(epoch from clock_timestamp()-t0)*1000,1),clock_timestamp());
  update cp7_analysis_stage.jobs set units_done=units_done+1,unit_attempts=0,updated_at=clock_timestamp(),
   state=case when plan_final and units_done+1=unit_count then 'DONE'else 'RUNNING'end where id=j.id;
 exception
  when query_canceled then
   update cp7_analysis_stage.jobs set unit_attempts=unit_attempts+1,updated_at=clock_timestamp(),
    state=case when unit_attempts+1>=3 then 'FAILED'else state end,
    failure_unit=case when unit_attempts+1>=3 then u.idx end,failure_sqlstate=case when unit_attempts+1>=3 then SQLSTATE end,
    failure_code=case when unit_attempts+1>=3 then 'CP7_ANALYSIS_STAGE_STOPPED'end,failure_message=case when unit_attempts+1>=3 then SQLERRM end where id=j.id;
  when others then
   update cp7_analysis_stage.jobs set state='FAILED',updated_at=clock_timestamp(),failure_unit=u.idx,failure_sqlstate=SQLSTATE,
    failure_code=case when SQLERRM~'^CP7_[A-Z0-9_]+$'then SQLERRM else 'CP7_ANALYSIS_STAGE_ERROR'end,failure_message=SQLERRM where id=j.id;
 end;
 return cp7_analysis_stage.status(p_job);
end $$;

-- ---------------------------------------------------------------- requests --
-- The staged job's request, step and status as ordinary requests of the
-- measured actor (the actor and its access as cp7_schedule_native.access_now
-- reads them, like the single capture and the analysis jobs).
create function cp7_analysis_stage.job_of(p_actor uuid,p_request uuid)returns uuid
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select j.id from cp7_analysis_stage.jobs j where j.actor=p_actor and j.request_id=p_request
$$;
-- request: the same request UUID with the same query is the same job. A UUID
-- an ordinary capture or analysis job of the actor already owns is refused
-- (one UUID is one request). Otherwise ONE statement captures the reference
-- through the bounded sources at the job's declared bounds (job_targets
-- planned products, one product per size being one target, and
-- job_matching_products matching products; the single capture keeps
-- 1000 / 5000) on the operational path (finance DEFERRED: the protected owner
-- report and the books are never read), and stores it as the job's only
-- reference. A source above the bounds is not cut: it is INCOMPLETE and the
-- job fails at its first unit with the single path's own refusal. The
-- access is re-read after the capture.
create function cp7_analysis_stage.request(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;jid uuid;jq jsonb;c jsonb;b jsonb:=cp7_analysis_stage.bounds();
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);q:=cp7_planning.history_query(p_query);
 if p_request is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS-REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 jid:=cp7_analysis_stage.job_of((a->>'actor')::uuid,p_request);
 if jid is not null then
  select x.query into jq from cp7_analysis_stage.jobs x where x.id=jid;
  if jq<>q then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;
  if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
  return cp7_analysis_stage.status(jid);
 end if;
 if exists(select 1 from cp7_analysis_native.runs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request)
  or exists(select 1 from cp7_analysis_jobs.jobs x where x.actor=(a->>'actor')::uuid and x.request_id=p_request)then
  raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';
 end if;
 c:=cp7_analysis_native.source_within((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)
  ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 jid:=cp7_analysis_stage.create_job((a->>'actor')::uuid,p_request,q,a,c);
 return cp7_analysis_stage.status(jid);
end $$;
-- step: the actor's current access is re-read and handed to step(), which
-- fails the job when it differs from the access at capture; an access that
-- changes during the unit refuses the call (nothing of the unit is kept).
create function cp7_analysis_stage.step_request(p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;jid uuid;s jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 jid:=cp7_analysis_stage.job_of((a->>'actor')::uuid,p_request);
 if jid is null then raise exception 'CP7_ANALYSIS_JOB_UNAVAILABLE';end if;
 s:=cp7_analysis_stage.step(jid,a);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return s;
end $$;
-- get: the job's status from its rows; never runs a unit.
create function cp7_analysis_stage.get(p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;jid uuid;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 jid:=cp7_analysis_stage.job_of((a->>'actor')::uuid,p_request);
 if jid is null then raise exception 'CP7_ANALYSIS_JOB_UNAVAILABLE';end if;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return cp7_analysis_stage.status(jid);
end $$;

-- ----------------------------------------------------------------- readers --
-- Same refusals as the segment reader: fresh access, the actor's own DONE
-- run (any other run, a running or failed job: RUN_UNAVAILABLE), access
-- unchanged at the end. The page set (cp7.native-analysis-pages.v1) returns
-- the access epoch every page read must present, the identity hash, the
-- whole-run totals, the header body and the page index in one response; it
-- reads no source (the source check is its own call).
create function cp7_analysis_stage.page_set(p_run uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;jid uuid;req uuid;captured timestamptz;hash text;h cp7_analysis_stage.headers%rowtype;s cp7_analysis_stage.page_sets%rowtype;pages jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 select j.id,j.request_id,j.captured_at,j.source_hash into jid,req,captured,hash from cp7_analysis_stage.jobs j
  where j.run_id=p_run and j.actor=(a->>'actor')::uuid and j.state='DONE';
 if jid is null then raise exception using errcode='42501',message='CP7_ANALYSIS_RUN_UNAVAILABLE';end if;
 select *into h from cp7_analysis_stage.headers where run_id=p_run;select *into s from cp7_analysis_stage.page_sets where run_id=p_run;
 if h.run_id is null or s.run_id is null then raise exception 'CP7_ANALYSIS_STAGE_INVARIANT';end if;
 select coalesce(jsonb_agg(jsonb_build_object('index',x.idx,'target_lo',x.target_lo,'target_hi',x.target_hi,'utf8_bytes',x.utf8_bytes,
   'sha256',x.sha256,'counts',x.counts)order by x.idx),'[]'::jsonb)into pages from cp7_analysis_stage.pages x where x.run_id=p_run;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-analysis-pages.v1','run_id',p_run,'request_id',req,
  'reference',jsonb_build_object('captured_at',captured,'source_hash',hash),
  'access_epoch',encode(pg_catalog.sha256(convert_to(a::text,'UTF8')),'hex'),'identity_hash',s.identity_hash,
  'targets_total',h.targets_total,'page_count',h.page_count,'paged',h.paged,'totals',s.totals,
  'header',jsonb_build_object('utf8_bytes',h.utf8_bytes,'sha256',h.sha256,'body',h.body),
  'pages',pages,'apply_enabled',false,'production_go',false);
end $$;
-- One page (cp7.native-analysis-page-read.v1): the unchanged access epoch,
-- the actor's own DONE run, the page index within 0..page_count-1.
create function cp7_analysis_stage.page(p_run uuid,p_index integer,p_access text)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;h cp7_analysis_stage.headers%rowtype;s cp7_analysis_stage.page_sets%rowtype;p cp7_analysis_stage.pages%rowtype;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if p_access is distinct from encode(pg_catalog.sha256(convert_to(a::text,'UTF8')),'hex')then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';
 end if;
 if not exists(select 1 from cp7_analysis_stage.jobs j where j.run_id=p_run and j.actor=(a->>'actor')::uuid and j.state='DONE')then
  raise exception using errcode='42501',message='CP7_ANALYSIS_RUN_UNAVAILABLE';
 end if;
 select *into h from cp7_analysis_stage.headers where run_id=p_run;select *into s from cp7_analysis_stage.page_sets where run_id=p_run;
 if h.run_id is null or s.run_id is null then raise exception 'CP7_ANALYSIS_STAGE_INVARIANT';end if;
 select *into p from cp7_analysis_stage.pages where run_id=p_run and idx=p_index;
 if p.run_id is null then raise exception 'CP7_ANALYSIS_PAGE_UNAVAILABLE';end if;
 return jsonb_build_object('contract_version','cp7.native-analysis-page-read.v1','run_id',p_run,'index',p.idx,'page_count',h.page_count,
  'target_lo',p.target_lo,'target_hi',p.target_hi,'header_sha256',h.sha256,'identity_hash',s.identity_hash,
  'utf8_bytes',p.utf8_bytes,'sha256',p.sha256,'body',p.body);
end $$;
-- Freshness, reported, never forced: ONE statement compares the fingerprint
-- of the current source (the same bounded operational source the job
-- captured) with the run's reference.
create function cp7_analysis_stage.check_source(p_run uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;hash text;c jsonb;b jsonb:=cp7_analysis_stage.bounds();
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 select j.source_hash into hash from cp7_analysis_stage.jobs j where j.run_id=p_run and j.actor=(a->>'actor')::uuid and j.state='DONE';
 if hash is null then raise exception using errcode='42501',message='CP7_ANALYSIS_RUN_UNAVAILABLE';end if;
 c:=cp7_analysis_native.source_within((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)
  ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return jsonb_build_object('source_state',case when cp7_analysis_native.fingerprint(c)=hash then 'UNCHANGED'else 'ARCHIVED_STALE'end,
  'checked_at',c->'captured_at');
end $$;

-- --------------------------------------------------------------- retention --
-- Intermediate rows (outputs, target/pair rows, fragments) are needed only
-- until PAGE_INDEX. This private admin function (no grants, no automatic
-- schedule: the retention value is an owner decision, PENDING_POLICY_VALUE)
-- removes them for ONE finished job; the reference, header, pages, page
-- index, plan and job row stay. The immutable triggers are suspended for
-- these deletes only, inside this transaction (ALTER TABLE takes a SHARE ROW
-- EXCLUSIVE lock: a concurrent unit's insert waits for the purge).
create function cp7_analysis_stage.purge_intermediates(p_job uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare st text;t text;n bigint;removed jsonb:='{}';
begin
 select j.state into st from cp7_analysis_stage.jobs j where j.id=p_job for update;
 if st is null then raise exception 'CP7_ANALYSIS_JOB_UNAVAILABLE';end if;
 if st not in('DONE','FAILED')then raise exception 'CP7_ANALYSIS_STAGE_RUNNING';end if;
 foreach t in array array['outputs','target_rows','pair_rows','pair_lists','fragments']loop
  execute format('alter table cp7_analysis_stage.%I disable trigger immutable_stage_%s',t,t);
  execute format('delete from cp7_analysis_stage.%I where job_id=$1',t)using p_job;
  get diagnostics n=row_count;
  execute format('alter table cp7_analysis_stage.%I enable trigger immutable_stage_%s',t,t);
  removed:=removed||jsonb_build_object(t,n);
 end loop;
 return jsonb_build_object('job_id',p_job,'state',st,'removed',removed);
end $$;

-- ------------------------------------------------------------ ownership --
-- Everything here is owned by cp7_capture (dropped by `drop owned by` in a
-- rollback); nothing is executable by anon/authenticated/service_role except
-- the six public RPC wrappers (authenticated only, SECURITY DEFINER).
do $$declare r record;begin
 for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_analysis_stage'loop
  execute format('alter function %s owner to cp7_capture',r.sig);
 end loop;
end $$;
revoke all on all functions in schema cp7_analysis_stage from public,anon,authenticated,service_role;
grant create on schema public to cp7_capture;
create function public.erp_cp7_request_staged_analysis_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.request(p_query,p_request)$$;
create function public.erp_cp7_step_staged_analysis_v1(p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.step_request(p_request)$$;
create function public.erp_cp7_get_staged_analysis_v1(p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.get(p_request)$$;
create function public.erp_cp7_read_staged_analysis_pages_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.page_set(p_run)$$;
create function public.erp_cp7_read_staged_analysis_page_v1(p_run uuid,p_index integer,p_access text)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.page(p_run,p_index,p_access)$$;
create function public.erp_cp7_check_staged_analysis_source_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.check_source(p_run)$$;
alter function public.erp_cp7_request_staged_analysis_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_step_staged_analysis_v1(uuid)owner to cp7_capture;
alter function public.erp_cp7_get_staged_analysis_v1(uuid)owner to cp7_capture;
alter function public.erp_cp7_read_staged_analysis_pages_v1(uuid)owner to cp7_capture;
alter function public.erp_cp7_read_staged_analysis_page_v1(uuid,integer,text)owner to cp7_capture;
alter function public.erp_cp7_check_staged_analysis_source_v1(uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_request_staged_analysis_v1(jsonb,uuid),public.erp_cp7_step_staged_analysis_v1(uuid),public.erp_cp7_get_staged_analysis_v1(uuid),
 public.erp_cp7_read_staged_analysis_pages_v1(uuid),public.erp_cp7_read_staged_analysis_page_v1(uuid,integer,text),
 public.erp_cp7_check_staged_analysis_source_v1(uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_request_staged_analysis_v1(jsonb,uuid),public.erp_cp7_step_staged_analysis_v1(uuid),public.erp_cp7_get_staged_analysis_v1(uuid),
 public.erp_cp7_read_staged_analysis_pages_v1(uuid),public.erp_cp7_read_staged_analysis_page_v1(uuid,integer,text),
 public.erp_cp7_check_staged_analysis_source_v1(uuid)to authenticated;
