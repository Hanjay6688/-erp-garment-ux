-- ---------------------------------------------------- K6 PL-8 proof runner --
-- Owner decision 8 Oct 2026 (8, PL-8): "arahkan penjalan bukti otomatis di
-- server. Bukti harus diperiksa terhadap versi sumber dan tidak boleh tetap
-- dianggap berlaku setelah koreksi atau pembatalan."
-- The server proves the posted cutting history in windows, so a capture finds
-- its exhausted groups already proven instead of classifying every group again
-- (PL-8 part 3, open question "who runs prove_exhausted"). It calls the
-- unchanged prover cp7_supply_native.prove_exhausted, which binds each proof to
-- the group's own captured fact rows (facts_hash) and to the classifier's
-- definition (kernel_version). A correction, reversal or backdated row changes
-- the hash, so the old proof is never matched again and the group is
-- classified anew, by a capture or by the next pass. The runner only adds
-- proofs through that prover: it never deletes or changes one and never
-- decides a group by itself.
-- cp7_ops.proof_tick (pg_cron, cp7_ops.schedules(): every 10 minutes, up to 20
-- calls, each in its own transaction under the 8 s limit) calls prove_next.
-- A pass walks every posted group by id at one clock (the pass clock) in
-- windows of at most 200 groups; when it ends, the runner rests one hour and
-- then starts the next pass at a new clock, which proves what changed since
-- (new, corrected or newly finished groups; a group found proven costs only
-- its capture and hash).
-- The 8 s limit holds as for K4: the session's statement limit must be set
-- and at most 8 s, otherwise the call is refused before anything is read or
-- written. A window stopped by the limit stores nothing (its statement is
-- undone) and the next call halves the window, down to one capture batch of
-- 50 groups; a window of 50 stopped three times in a row is skipped: its first
-- and last group and the stop are recorded in the pass, the cursor moves past
-- it, and those groups stay unproven (a capture classifies them as before).
-- Another refusal inside a window (a capture batch not COMPLETE) is handled
-- the same way and recorded with its code. Without a proof kernel (reconcile's
-- graph limits changed) nothing can be proven: the refusal is recorded and the
-- runner rests one hour, the cursor unchanged.
-- One call proves at a time: the runner's private lock is taken without
-- waiting, and a call that does not get it returns BUSY having read and
-- written nothing, so no call ever waits on another (cf. SOL-K4-01).
create schema cp7_proof_runner authorization cp7_capture;
revoke all on schema cp7_proof_runner from public,anon,authenticated,service_role;

-- The runner's one row: the current pass, its cursor and window, and the
-- last tick. Updated in place by the lock holder only; never deleted.
create table cp7_proof_runner.state(
 id boolean primary key check(id),
 pass integer not null check(pass>=1),
 pass_clock timestamptz not null,
 pass_started_at timestamptz not null,
 after_id uuid,
 window_size integer not null check(window_size between 50 and 200),
 window_stops integer not null check(window_stops between 0 and 2),
 scanned bigint not null check(scanned>=0),
 proofs_added bigint not null check(proofs_added>=0),
 skipped jsonb not null check(jsonb_typeof(skipped)='array'),
 refusal jsonb check(refusal is null or jsonb_typeof(refusal)='object'),
 rest_until timestamptz,
 last_tick_at timestamptz not null,
 statement_timeout_ms integer not null check(statement_timeout_ms between 1 and 8000)
);
-- Every finished pass, insert-only.
create table cp7_proof_runner.passes(
 pass integer primary key check(pass>=1),
 pass_clock timestamptz not null,
 started_at timestamptz not null,
 finished_at timestamptz not null,
 scanned bigint not null check(scanned>=0),
 proofs_added bigint not null check(proofs_added>=0),
 skipped jsonb not null check(jsonb_typeof(skipped)='array')
);
do $$declare t text;begin
 foreach t in array array['state','passes']loop
  execute format('alter table cp7_proof_runner.%I owner to cp7_capture',t);
  execute format('alter table cp7_proof_runner.%I enable row level security',t);
  execute format('create policy cp7_proof_runner_no_access on cp7_proof_runner.%I for all to public using(false)with check(false)',t);
  execute format('revoke all on cp7_proof_runner.%I from public,anon,authenticated,service_role',t);
 end loop;
end $$;
create trigger immutable_proof_runner_state before delete on cp7_proof_runner.state
 for each row execute function cp7_private.immutable_run();
create trigger immutable_proof_runner_pass before update or delete on cp7_proof_runner.passes
 for each row execute function cp7_private.immutable_run();

create function cp7_proof_runner.prove_next()returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare limit_ms integer;r cp7_proof_runner.state%rowtype;t timestamptz:=clock_timestamp();res jsonb;ids uuid[];
 stop jsonb;outcome text;
begin
 select x.setting::integer into limit_ms from pg_catalog.pg_settings x where x.name='statement_timeout';
 if limit_ms is null or limit_ms not between 1 and 8000 then
  raise exception using errcode='55000',message='CP7_RUNNER_STATEMENT_LIMIT_REQUIRED',
   detail=jsonb_build_object('statement_timeout_ms',limit_ms,'required','statement_timeout 1..8000 ms')::text;
 end if;
 if not pg_catalog.pg_try_advisory_xact_lock(pg_catalog.hashtextextended('CP7:K6_PROOF_RUNNER',0))then
  return jsonb_build_object('ran',false,'outcome','BUSY');
 end if;
 select *into r from cp7_proof_runner.state where id;
 if not found then
  insert into cp7_proof_runner.state values(true,1,t,t,null,200,0,0,0,'[]',null,null,t,limit_ms)returning *into r;
 end if;
 update cp7_proof_runner.state set last_tick_at=t,statement_timeout_ms=limit_ms where id;
 if r.rest_until is not null then
  if t<r.rest_until then
   return jsonb_build_object('ran',false,'outcome','RESTING','pass',r.pass,'rest_until',r.rest_until);
  end if;
  if r.refusal is null or r.refusal->>'code'<>'CP7_SUPPLY_PROOF_KERNEL'then r.pass:=r.pass+1;r.pass_clock:=t;r.pass_started_at:=t;r.after_id:=null;
   r.window_size:=200;r.window_stops:=0;r.scanned:=0;r.proofs_added:=0;r.skipped:='[]';
  end if;
  r.refusal:=null;r.rest_until:=null;
 end if;
 begin
  res:=cp7_supply_native.prove_exhausted(r.pass_clock,r.after_id,r.window_size);
 exception
  when query_canceled then stop:=jsonb_build_object('code','CP7_PROOF_WINDOW_STOPPED','sqlstate',SQLSTATE);
  when others then
   if SQLERRM='CP7_SUPPLY_PROOF_KERNEL'then
    r.refusal:=jsonb_build_object('code',SQLERRM,'sqlstate',SQLSTATE,'at',t);r.rest_until:=t+interval'1 hour';
    update cp7_proof_runner.state set refusal=r.refusal,rest_until=r.rest_until where id;
    return jsonb_build_object('ran',false,'outcome','REFUSED','pass',r.pass,'code',SQLERRM,'rest_until',r.rest_until);
   end if;
   stop:=jsonb_build_object('code',case when SQLERRM~'^CP7_[A-Z0-9_]+$'then SQLERRM else 'CP7_PROOF_RUNNER_ERROR'end,'sqlstate',SQLSTATE);
 end;
 if stop is null then
  r.scanned:=r.scanned+(res->>'scanned')::integer;r.proofs_added:=r.proofs_added+(res->>'proofs_added')::integer;
  r.after_id:=coalesce((res->>'next_after')::uuid,r.after_id);r.window_size:=least(200,r.window_size*2);r.window_stops:=0;
  outcome:='WINDOW_PROVEN';
  if(res->>'done')::boolean then
   insert into cp7_proof_runner.passes values(r.pass,r.pass_clock,r.pass_started_at,t,r.scanned,r.proofs_added,r.skipped);
   r.rest_until:=t+interval'1 hour';outcome:='PASS_DONE';
  end if;
 elsif r.window_size>50 then r.window_size:=greatest(50,r.window_size/2);r.window_stops:=0;outcome:='WINDOW_STOPPED';
 elsif r.window_stops<2 then r.window_stops:=r.window_stops+1;outcome:='WINDOW_STOPPED';
 else
  select array(select g.id from erp.cutting_groups g where g.material_issue_posted and g.cut_at<=r.pass_clock
   and(r.after_id is null or g.id>r.after_id)order by g.id limit 50)into ids;
  r.skipped:=r.skipped||jsonb_build_array(stop||jsonb_build_object('first',ids[1],'last',ids[cardinality(ids)],'groups',cardinality(ids),'at',t));
  r.after_id:=coalesce(ids[cardinality(ids)],r.after_id);r.window_stops:=0;outcome:='WINDOW_SKIPPED';
 end if;
 update cp7_proof_runner.state set pass=r.pass,pass_clock=r.pass_clock,pass_started_at=r.pass_started_at,after_id=r.after_id,
  window_size=r.window_size,window_stops=r.window_stops,scanned=r.scanned,proofs_added=r.proofs_added,skipped=r.skipped,
  refusal=r.refusal,rest_until=r.rest_until where id;
 return jsonb_build_object('ran',true,'outcome',outcome,'pass',r.pass,'pass_clock',r.pass_clock,'after_id',r.after_id,
  'window_size',r.window_size,'scanned',coalesce((res->>'scanned')::integer,0),'proofs_added',coalesce((res->>'proofs_added')::integer,0),
  'stop',stop,'rest_until',r.rest_until);
end $$;

-- What the runner is doing, for the operator and the auditor (not exposed to
-- the app): the current pass, the last tick, and the last finished passes.
create function cp7_proof_runner.status()returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('state',(select to_jsonb(s)-'id'from cp7_proof_runner.state s),
  'passes',(select coalesce(jsonb_agg(to_jsonb(p)order by p.pass desc),'[]'::jsonb)from(select *from cp7_proof_runner.passes order by pass desc limit 10)p),
  'proofs',(select count(*)from cp7_supply_native.exhaustion_proofs))
$$;

do $$declare r record;begin
 for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_proof_runner'loop
  execute format('alter function %s owner to cp7_capture',r.sig);
 end loop;
end $$;
revoke all on all functions in schema cp7_proof_runner from public,anon,authenticated,service_role;
