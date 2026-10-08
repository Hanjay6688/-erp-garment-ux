-- Staged snapshot contract v2 (owner decision 8 Oct 2026; docs/cp7/p19/P19_STAGED_SNAPSHOT_V2.md).
-- A staged run stays an immutable snapshot and may be used, with its time
-- label, after the ERP has changed. Freshness is reported, never forced: the
-- changes recorded since the snapshot per category (by the database snapshot
-- the reference was read in, so a write still running at the capture and a
-- backdated entry both count; deletions from the audit trail) and the last
-- full source check, which says only how the snapshot compared with the data
-- at the check's time. Nothing here changes a job, its reference, header or pages.

-- What the counts read and the capture role could not yet: recording times
-- and row transactions of three tables, and of the audit trail only the table,
-- action, time and transaction of each entry (deletions; never its data).
grant select(system_created_at,xmin)on erp.material_stock_movements to cp7_capture;
grant select(created_at,xmin)on erp.bb_purchase_commitments_v1 to cp7_capture;
grant select(created_at,xmin)on erp.locations to cp7_capture;
grant select(entity_type,action,changed_at,xmin)on erp.audit_logs to cp7_capture;

-- Every full source check of a staged run, once, as it was answered, with the
-- database snapshot the check read in (null when the checking transaction had
-- already written; changes after the check are then judged by recording time).
create table cp7_analysis_stage.source_checks(id bigint generated always as identity primary key,
 run_id uuid not null references cp7_analysis_stage.page_sets(run_id),actor uuid not null,
 checked_at timestamptz not null,source_state text not null check(source_state in('UNCHANGED','ARCHIVED_STALE')),
 source_snapshot pg_snapshot,recorded_at timestamptz not null);
create index cp7_analysis_stage_source_checks_run on cp7_analysis_stage.source_checks(run_id,id);
alter table cp7_analysis_stage.source_checks owner to cp7_capture;
alter table cp7_analysis_stage.source_checks enable row level security;
create policy cp7_analysis_stage_no_access on cp7_analysis_stage.source_checks for all to public using(false)with check(false);
revoke all on cp7_analysis_stage.source_checks from public,anon,authenticated,service_role;
create trigger immutable_stage_source_checks before update or delete on cp7_analysis_stage.source_checks
 for each row execute function cp7_private.immutable_run();

-- The tracked change sources, in display order: category, relation and the
-- recording-time columns. A fixed list; no caller input reaches the dynamic
-- statements below.
create function cp7_analysis_stage.change_sources()returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select '[
  {"category":"SALES","schema":"erp","table":"sales_headers","columns":["created_at","updated_at"]},
  {"category":"SALES","schema":"erp","table":"sales_returns","columns":["created_at"]},
  {"category":"FG_STOCK","schema":"erp","table":"fg_stock_movements","columns":["system_created_at"]},
  {"category":"MATERIAL_STOCK","schema":"erp","table":"material_stock_movements","columns":["system_created_at"]},
  {"category":"PRODUCTION","schema":"erp","table":"cutting_groups","columns":["created_at","updated_at"]},
  {"category":"PRODUCTION","schema":"erp","table":"cutting_pickups","columns":["created_at","updated_at"]},
  {"category":"PRODUCTION","schema":"erp","table":"cutting_distribution_batches","columns":["created_at"]},
  {"category":"PRODUCTION","schema":"erp","table":"bb_wip_pickups_v1","columns":["created_at"]},
  {"category":"PRODUCTION","schema":"erp","table":"sewing_terminal_events","columns":["created_at"]},
  {"category":"PRODUCTION","schema":"erp","table":"qc_inspections","columns":["created_at","updated_at"]},
  {"category":"PRODUCTION","schema":"erp","table":"laundry_deliveries","columns":["created_at","updated_at"]},
  {"category":"PRODUCTION","schema":"erp","table":"laundry_receipts","columns":["created_at","updated_at"]},
  {"category":"PRODUCTION","schema":"erp","table":"bs_cases","columns":["created_at","updated_at"]},
  {"category":"PRODUCTION","schema":"erp","table":"bs_resolutions","columns":["created_at"]},
  {"category":"PRODUCTION","schema":"erp","table":"rework_orders","columns":["created_at","updated_at"]},
  {"category":"PRODUCTION","schema":"erp","table":"wip_control_flags","columns":["created_at","updated_at"]},
  {"category":"PRODUCTION_ORDERS","schema":"erp","table":"production_orders","columns":["created_at","updated_at"]},
  {"category":"MASTER_DATA","schema":"erp","table":"products","columns":["created_at","updated_at"]},
  {"category":"MASTER_DATA","schema":"erp","table":"bf_sku_versions_v1","columns":["created_at"]},
  {"category":"MASTER_DATA","schema":"erp","table":"production_patterns","columns":["created_at","updated_at"]},
  {"category":"MASTER_DATA","schema":"erp","table":"materials","columns":["created_at","updated_at"]},
  {"category":"MASTER_DATA","schema":"erp","table":"accessory_bom_versions","columns":["created_at"]},
  {"category":"MASTER_DATA","schema":"erp","table":"locations","columns":["created_at"]},
  {"category":"MATERIAL_PURCHASES","schema":"erp","table":"bb_purchase_commitments_v1","columns":["created_at"]},
  {"category":"PLANNING_POLICIES","schema":"cp7_identity","table":"production_policy","columns":["recorded_at"]},
  {"category":"PLANNING_POLICIES","schema":"cp7_profile","table":"profiles","columns":["recorded_at"]},
  {"category":"PLANNING_POLICIES","schema":"cp7_schedule_native","table":"plans","columns":["recorded_at"]},
  {"category":"PLANNING_POLICIES","schema":"cp7_fabric_native","table":"recipes","columns":["recorded_at"]},
  {"category":"PLANNING_POLICIES","schema":"cp7_supply_native","table":"exhaustion_proofs","columns":["recorded_at"]}
 ]'::jsonb
$$;

-- Rows recorded after a boundary, per category: a row counts when it was
-- inserted or last changed by a transaction the boundary's database snapshot
-- did not see (so one still running at the boundary and committed after it
-- counts, whatever its recording time), or when its recording time is after
-- the boundary time (the only test when the boundary has no snapshot). Rows
-- deleted after the boundary count from the audit trail's DELETE entries.
-- p_check is the last full check (null: none); one scan per relation.
create function cp7_analysis_stage.changes_since(p_since timestamptz,p_since_snap pg_snapshot,p_check timestamptz,p_check_snap pg_snapshot)
returns jsonb language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare s jsonb;r record;rec text;fx text;after1 text;after2 text;n bigint;m bigint;last timestamptz;cat text;
 ref bigint:=pg_snapshot_xmax(pg_current_snapshot())::text::bigint;low bigint;tables text[]:='{}';
 rows_by jsonb:='{}';del_by jsonb:='{}';after_by jsonb:='{}';last_by jsonb:='{}';order_by text[]:='{}';cat_of jsonb:='{}';out jsonb:='[]';
begin
 -- A row's 32-bit xmin as the full transaction id: the one in the 2^32 window
 -- ending at this statement's snapshot (every row a recent snapshot may miss
 -- lies there; an older row mapped wrongly can only count as a change).
 low:=ref%4294967296;
 fx:=format('(case when xmin::text::bigint<=%s then %s else greatest(%s,0)end+xmin::text::bigint)::text::xid8',low,ref-low,ref-low-4294967296);
 for s in select value from jsonb_array_elements(cp7_analysis_stage.change_sources())loop
  cat:=s->>'category';if not cat=any(order_by)then order_by:=order_by||cat;end if;
  if s->>'schema'='erp'then tables:=tables||(s->>'table');cat_of:=cat_of||jsonb_build_object(s->>'table',cat);end if;
  select 'greatest('||string_agg(format('%I',c),',')||')'into rec from jsonb_array_elements_text(s->'columns')c;
  after1:=format('(%s>$1 or($2 is not null and not pg_visible_in_snapshot(%s,$2)))',rec,fx);
  after2:=format('(%s>$3 or($4 is not null and not pg_visible_in_snapshot(%s,$4)))',rec,fx);
  execute format('select count(*)filter(where %1$s),count(*)filter(where $3 is not null and %2$s),max(%3$s)filter(where %1$s)from %4$I.%5$I',
   after1,after2,rec,s->>'schema',s->>'table')into n,m,last using p_since,p_since_snap,p_check,p_check_snap;
  rows_by:=rows_by||jsonb_build_object(cat,coalesce((rows_by->>cat)::bigint,0)+n);
  after_by:=after_by||jsonb_build_object(cat,coalesce((after_by->>cat)::bigint,0)+m);
  last_by:=last_by||jsonb_build_object(cat,greatest((last_by->>cat)::timestamptz,last));
 end loop;
 after1:=format('(changed_at>$1 or($2 is not null and not pg_visible_in_snapshot(%s,$2)))',fx);
 after2:=format('(changed_at>$3 or($4 is not null and not pg_visible_in_snapshot(%s,$4)))',fx);
 for r in execute format('select entity_type::text t,count(*)filter(where %1$s)n,count(*)filter(where $3 is not null and %2$s)m,
   max(changed_at)filter(where %1$s)last from erp.audit_logs where action=''DELETE''and entity_type=any($5)group by 1',after1,after2)
   using p_since,p_since_snap,p_check,p_check_snap,tables loop
  cat:=cat_of->>r.t;
  rows_by:=rows_by||jsonb_build_object(cat,(rows_by->>cat)::bigint+r.n);
  del_by:=del_by||jsonb_build_object(cat,coalesce((del_by->>cat)::bigint,0)+r.n);
  after_by:=after_by||jsonb_build_object(cat,(after_by->>cat)::bigint+r.m);
  if r.n>0 then last_by:=last_by||jsonb_build_object(cat,greatest((last_by->>cat)::timestamptz,r.last));end if;
 end loop;
 foreach cat in array order_by loop
  out:=out||jsonb_build_array(jsonb_build_object('category',cat,'rows',(rows_by->>cat)::bigint,'deleted',coalesce((del_by->>cat)::bigint,0),
   'rows_after_check',case when p_check is null then null else(after_by->>cat)::bigint end,'last_recorded_at',last_by->cat));
 end loop;
 return out;
end $$;

-- Freshness of the actor's own DONE run (cp7.native-analysis-snapshot-freshness.v1).
-- The snapshot is never called current; a full check only ever says how it
-- compared with the data at the check's time:
-- STALE_VERIFIED: the last full check found the source changed;
-- VERIFIED_SAME: the last full check found it the same and nothing was
--   recorded after that check ("same as the data at <check time>");
-- CHANGES_RECORDED: rows were recorded after the snapshot (or after the last same check);
-- NO_RECORDED_CHANGE: nothing recorded in the tracked sources and no full check yet.
create function cp7_analysis_stage.freshness(p_run uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;j cp7_analysis_stage.jobs%rowtype;s cp7_analysis_stage.page_sets%rowtype;m cp7_analysis_stage.capture_marks%rowtype;
 c cp7_analysis_stage.source_checks%rowtype;changes jsonb;total bigint;after bigint;state text;evaluated timestamptz:=clock_timestamp();
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 select *into j from cp7_analysis_stage.jobs x where x.run_id=p_run and x.actor=(a->>'actor')::uuid and x.state='DONE';
 if j.id is null then raise exception using errcode='42501',message='CP7_ANALYSIS_RUN_UNAVAILABLE';end if;
 select *into s from cp7_analysis_stage.page_sets where run_id=p_run;
 select *into m from cp7_analysis_stage.capture_marks where job_id=j.id;
 if s.run_id is null or m.job_id is null then raise exception 'CP7_ANALYSIS_STAGE_INVARIANT';end if;
 select *into c from cp7_analysis_stage.source_checks x where x.run_id=p_run order by x.id desc limit 1;
 changes:=cp7_analysis_stage.changes_since(j.captured_at,m.source_snapshot,c.checked_at,c.source_snapshot);
 select sum((x->>'rows')::bigint),sum((x->>'rows_after_check')::bigint)into total,after from jsonb_array_elements(changes)x;
 -- Rows after the check are rows after the snapshot too (a later boundary).
 state:=case when c.source_state='ARCHIVED_STALE'then 'STALE_VERIFIED'when c.source_state='UNCHANGED'and after=0 then 'VERIFIED_SAME'
  when total>0 then 'CHANGES_RECORDED'else 'NO_RECORDED_CHANGE'end;
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-analysis-snapshot-freshness.v1','run_id',p_run,'identity_hash',s.identity_hash,
  'data_as_of',j.captured_at,'evaluated_at',evaluated,'freshness_state',state,
  'capture_boundary',case when m.source_snapshot is null then 'RECORDING_TIME'else 'SNAPSHOT'end,
  'changes_since',changes,'changes_total',total,
  'last_full_check',case when c.id is null then null else jsonb_build_object('source_state',c.source_state,'checked_at',c.checked_at,
   'boundary',case when c.source_snapshot is null then 'RECORDING_TIME'else 'SNAPSHOT'end,'changes_after_check',after)end,
  'same_as_of',case when state='VERIFIED_SAME'then c.checked_at end,'apply_enabled',false,'production_go',false);
end $$;

-- The full source check, recorded once as answered with the snapshot it read
-- in (one statement; check_source is stable). It answers only the check: the
-- check alone is close to the 8 s limit at 5,000 targets, so the change counts
-- are read by the caller afterwards (freshness), each under its own limit.
create function cp7_analysis_stage.check_and_record(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r jsonb;snap pg_snapshot;
begin
 a:=cp7_schedule_native.access_now(false);
 select cp7_analysis_stage.check_source(p_run),case when pg_current_xact_id_if_assigned()is null then pg_current_snapshot()end into r,snap;
 insert into cp7_analysis_stage.source_checks(run_id,actor,checked_at,source_state,source_snapshot,recorded_at)
 values(p_run,(a->>'actor')::uuid,(r->>'checked_at')::timestamptz,r->>'source_state',snap,clock_timestamp());
 return jsonb_build_object('contract_version','cp7.native-analysis-snapshot-check.v1','run_id',p_run,'source_state',r->>'source_state',
  'checked_at',r->'checked_at','boundary',case when snap is null then 'RECORDING_TIME'else 'SNAPSHOT'end);
end $$;

-- One target of a staged run as planning reads it (contract v2 §2): its row,
-- the run's planning scope and the page holding it, from the retained index
-- (never the whole reference or the pages). The caller checks actor and state.
create function cp7_analysis_stage.plan_target(p_job uuid,p_target text)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare n integer;r cp7_analysis_stage.plan_targets%rowtype;s jsonb;page integer;
begin
 select x.scope into s from cp7_analysis_stage.plan_scope x where x.job_id=p_job;
 if s is null then raise exception 'CP7_PLAN_V2_SNAPSHOT_INDEX_MISSING';end if;
 select count(*)into n from cp7_analysis_stage.plan_targets x where x.job_id=p_job and x.target_key=p_target;
 if n=0 then raise exception 'CP7_PLAN_TARGET';end if;
 if n>1 then raise exception 'CP7_PLAN_V2_TARGET_AMBIGUOUS';end if;
 select *into r from cp7_analysis_stage.plan_targets x where x.job_id=p_job and x.target_key=p_target;
 select min(c.o-1)into page from cp7_analysis_stage.headers h cross join lateral jsonb_array_elements(h.cuts)with ordinality c(v,o)
  where h.job_id=p_job and r.ord between(c.v->>0)::integer and(c.v->>1)::integer;
 return jsonb_build_object('ord',r.ord,'page_index',page,'row',r.row,'scope',s);
end $$;

do $$declare r record;begin
 for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='cp7_analysis_stage'and p.proname in('change_sources','changes_since','freshness','check_and_record','plan_target')loop
  execute format('alter function %s owner to cp7_capture',r.sig);
  execute format('revoke all on function %s from public,anon,authenticated,service_role',r.sig);
 end loop;
end $$;
grant create on schema public to cp7_capture;
create function public.erp_cp7_staged_snapshot_freshness_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.freshness(p_run)$$;
create function public.erp_cp7_check_staged_snapshot_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_analysis_stage.check_and_record(p_run)$$;
alter function public.erp_cp7_staged_snapshot_freshness_v1(uuid)owner to cp7_capture;
alter function public.erp_cp7_check_staged_snapshot_v1(uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_staged_snapshot_freshness_v1(uuid),public.erp_cp7_check_staged_snapshot_v1(uuid)
 from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_staged_snapshot_freshness_v1(uuid),public.erp_cp7_check_staged_snapshot_v1(uuid)to authenticated;
