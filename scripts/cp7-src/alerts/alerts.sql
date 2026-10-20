-- WA-2a (owner D17-3..D17-6, 19 Oct 2026): "Pengingat sistem" and their forwarding to the owner's WhatsApp through
-- CallMeBot. Design: docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md (v2, separate module). Nothing here changes the reminder
-- module (cp7_reminder_native) or any Native table; it only reads.
--
-- * alerts: one row per system reminder episode (kind + subject). Opened when its source shows it, refreshed while the
--   source's numbers change, resolved when the source no longer shows it; reopened later as a new episode. The sources
--   are read as the owner who saved the WhatsApp settings (K4 pattern: request.jwt.claims for the unit, access read
--   again, claims put back): fabric below the minimum of Kain & Benchmark (the Ringkasan Gudang rule, same tables and
--   filters; the CI compares both answers), receivables and payables due today or overdue (the accepted reminder
--   sources receivable_source()/payable_source(), states DUE_TODAY and OVERDUE), and (SS-1, D17-8/D17-9) finished goods
--   at or under their reorder point (cp7_stock_formula.fg_source(), stock-formula/formula.sql), and (SS-2, SS-3) fabrics on
--   the formula and accessories at or under their manual minimum (cp7_stock_formula.material_source(),
--   stock-formula/materials.sql). Owner D17-10: one fabric reminder, FABRIC_BELOW_MINIMUM "Stok kain di bawah minimum":
--   the minimum of Kain & Benchmark, or the formula's number when that minimum is empty (fabric_kind_source()).
-- * outbox: what must reach WhatsApp: every new alert (AFTER INSERT trigger on alerts, so a rolled-back transaction
--   queues nothing), every manual reminder of the owner whose time has come, and repeats of what is still open.
--   Staff reminders are never read.
-- * dispatches: one row per message (INSTANT, DIGEST, TEST) with its body and the provider's answer.
-- * The CallMeBot key lives only in Supabase Vault (secret cp7_callmebot_apikey). It is written by the owner's RPC and
--   read only inside wa_post(), which hands it to pg_net; no RPC, table or answer returns it.
--
-- Three ticks run every minute from pg_cron (cp7_alert_native.schedules(), jobs erp-wa-*), each under the 8 s statement
-- limit: collect_tick(), send_tick() and (WA-2b) analysis_tick(), which works through the owner's own staged analysis
-- and asks for an automatic one when due (section "analysis" below). send_tick() reads the provider's answers, checks every waiting item against
-- its source again (an item resolved since is RESOLVED_BEFORE_SEND, never sent), holds during quiet hours, sends the
-- digest at its time, and otherwise merges everything waiting into at most one message per minute (after
-- burst_after_per_day messages in a WIB day, one per burst_merge_minutes). Nothing is dropped: lines over max_items
-- become "dan N lainnya", and every open item is in each digest. pg_net sends after commit only.
create role cp7_alert nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
-- The installing role (postgres on the hosted project, not a superuser) may hand objects to cp7_alert only when it can
-- SET ROLE to it (PostgreSQL 16+; WA-3a run 39271239383: "must be able to SET ROLE"). Dropped with the role.
grant cp7_alert to current_user;
create schema cp7_alert_native authorization cp7_alert;
revoke all on schema cp7_alert_native from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_alert_native to postgres;
-- No grant on schema auth: the hosted postgres role cannot pass it on (WA-3a run 39271994388, "permission denied for
-- schema auth"). The request identity is read by cp7_alert_native.uid()/jwt() below, the same settings auth.uid() reads.
grant usage on schema erp to cp7_alert;
grant execute on function erp.get_my_access_v1(),erp.has_permission(text)to cp7_alert;
grant select on erp.manual_reminders,erp.materials,erp.fabric_master_profiles,erp.material_stock_movements,erp.locations to cp7_alert;
grant usage on schema cp7_reminder_native to cp7_alert;
grant execute on function cp7_reminder_native.receivable_source(),cp7_reminder_native.payable_source(),public.erp_cp7_get_sales_v1(jsonb)to cp7_alert;
-- SS-1..SS-3: finished goods, fabrics and accessories at or under their reorder point, from the stock formula module
-- (stock-formula/formula.sql, materials.sql), which checks the caller's screen permissions itself.
grant usage on schema cp7_stock_formula to cp7_alert;
grant execute on function cp7_stock_formula.fg_source(),cp7_stock_formula.material_source(text)to cp7_alert;
-- WA-2b: the owner's own staged analyses, only through the public functions the Analysis and Reminder screens call (each
-- checks the caller's access itself; cp7_alert calls them with the owner's identity), and which jobs the owner has.
grant usage on schema cp7_analysis_stage to cp7_alert;
grant select(actor,run_id,state,query,captured_at,created_at)on cp7_analysis_stage.jobs to cp7_alert;
grant execute on function public.erp_cp7_request_staged_analysis_v1(jsonb,uuid),public.erp_cp7_staged_snapshot_freshness_v1(uuid),
 public.erp_cp7_step_reminder_conditions_v2(uuid),public.erp_cp7_read_reminder_conditions_v2(jsonb),public.erp_cp7_recheck_reminder_v2(uuid,text)
 to cp7_alert;

-- ------------------------------------------------------------------ tables --
-- Settings are append-only revisions; the latest one is in force. actor/actor_user_id: the owner who saved it, whose
-- identity reads the sources. analysis_*: the owner's scheduled analysis (WA-2b).
create table cp7_alert_native.settings(
 revision bigint primary key check(revision>0),enabled boolean not null,phone_e164 text check(phone_e164~'^\+[1-9][0-9]{7,14}$'),
 detail text not null check(detail in('SUMMARY','DETAILED')),digest_times text[] not null,kinds text[] not null,
 repeat_minutes integer not null check(repeat_minutes=0 or repeat_minutes between 60 and 10080),
 burst_after_per_day integer not null check(burst_after_per_day between 1 and 200),
 burst_merge_minutes integer not null check(burst_merge_minutes between 5 and 240),max_items integer not null check(max_items between 1 and 20),
 quiet_enabled boolean not null,quiet_start time not null,quiet_end time not null,
 analysis_every_minutes integer not null check(analysis_every_minutes=0 or analysis_every_minutes between 15 and 1440),
 analysis_start time not null,analysis_end time not null,actor uuid not null,actor_user_id uuid not null,request_id uuid not null unique,
 request_hash text not null check(request_hash~'^[0-9a-f]{64}$'),saved_at timestamptz not null default clock_timestamp(),check(not enabled or phone_e164 is not null),check(quiet_start<>quiet_end),
 check(analysis_start<analysis_end));
-- When the key was set and by whom; never the key.
create table cp7_alert_native.key_events(
 id bigint generated always as identity primary key,actor uuid not null,request_id uuid not null unique,action text not null check(action='SET'),
 at timestamptz not null default clock_timestamp());
-- Where wa_post sends. Only these two addresses can ever receive the key: CallMeBot, and the fake CallMeBot of the CI
-- stack (a docker name that does not resolve anywhere else). Owned by postgres, the only role that may change it (tests);
-- cp7_alert reads it.
create table cp7_alert_native.transport(
 id boolean primary key default true check(id),
 base_url text not null check(base_url in('https://api.callmebot.com/whatsapp.php','http://fake-callmebot:8080/whatsapp.php')),
 timeout_ms integer not null check(timeout_ms between 1000 and 15000));
insert into cp7_alert_native.transport values(true,'https://api.callmebot.com/whatsapp.php',5000);
create table cp7_alert_native.alerts(
 id uuid primary key default gen_random_uuid(),kind text not null check(kind in('FABRIC_BELOW_MINIMUM','ACCESSORY_AT_REORDER_POINT','FG_AT_REORDER_POINT','AR_DUE','AP_DUE','PRODUCTION_GAP','FABRIC_NEED')),
 subject_key text not null check(length(subject_key)between 1 and 200),episode integer not null check(episode>0),
 title text not null check(length(title)between 1 and 300),detail jsonb not null check(jsonb_typeof(detail)='object'),
 party_names jsonb not null check(jsonb_typeof(party_names)='array'),source_hash text not null check(source_hash~'^[0-9a-f]{64}$'),
 opened_at timestamptz not null default clock_timestamp(),refreshed_at timestamptz not null default clock_timestamp(),
 state text not null default'OPEN'check(state in('OPEN','RESOLVED')),resolved_at timestamptz,resolution text,
 unique(kind,subject_key,episode),check((state='OPEN')=(resolved_at is null)and(state='OPEN')=(resolution is null)));
create unique index alerts_one_open on cp7_alert_native.alerts(kind,subject_key)where state='OPEN';
create table cp7_alert_native.dispatches(
 id bigint generated always as identity primary key,kind text not null check(kind in('INSTANT','DIGEST','TEST')),digest_slot timestamptz,
 settings_revision bigint not null references cp7_alert_native.settings(revision),body text check(length(body)between 1 and 1000),
 body_sha256 text check(body_sha256~'^[0-9a-f]{64}$'),request_id uuid unique,net_request_id bigint unique,
 status text not null check(status in('QUEUED','PROVIDER_ACCEPTED','PROVIDER_REFUSED','TRANSPORT_FAILED','UNKNOWN','NOTHING_DUE')),
 queued_at timestamptz not null default clock_timestamp(),answered_at timestamptz,http_status integer,provider_text text check(length(provider_text)<=200),
 resolved_outcome text check(resolved_outcome in('DELIVERED','NOT_DELIVERED')),resolved_by uuid,resolved_at timestamptz,resolve_request uuid unique,
 check((kind='DIGEST')=(digest_slot is not null)),check((kind='TEST')=(request_id is not null)),
 check((status='NOTHING_DUE')=(body is null)),check((body is null)=(body_sha256 is null)),check(status<>'NOTHING_DUE'or kind='DIGEST'),
 check((resolved_outcome is null)=(resolved_at is null)and(resolved_at is null)=(resolved_by is null)),check(resolved_outcome is null or status='UNKNOWN'));
create unique index dispatches_one_digest on cp7_alert_native.dispatches(digest_slot)where kind='DIGEST';
create table cp7_alert_native.outbox(
 id bigint generated always as identity primary key,item_kind text not null check(item_kind in('ALERT','MANUAL_REMINDER')),item_id uuid not null,
 item_episode text not null,round integer not null check(round>=0),
 alert_kind text not null check(alert_kind in('MANUAL_REMINDER','FABRIC_BELOW_MINIMUM','ACCESSORY_AT_REORDER_POINT','FG_AT_REORDER_POINT','AR_DUE','AP_DUE',
  'PRODUCTION_GAP','FABRIC_NEED')),
 queued_at timestamptz not null default clock_timestamp(),
 state text not null default'PENDING'check(state in('PENDING','HELD_QUIET','DISPATCHED','ACCEPTED','UNKNOWN','RESOLVED_BEFORE_SEND','DISABLED','KIND_OFF')),
 dispatch_id bigint references cp7_alert_native.dispatches(id),attempts integer not null default 0 check(attempts>=0),reason text,settled_at timestamptz,
 unique(item_kind,item_id,item_episode,round),check((item_kind='MANUAL_REMINDER')=(alert_kind='MANUAL_REMINDER')),
 check((state in('DISPATCHED','UNKNOWN'))<=(dispatch_id is not null)));
create index outbox_waiting on cp7_alert_native.outbox(state)where state in('PENDING','HELD_QUIET','DISPATCHED','UNKNOWN');
create index outbox_dispatch on cp7_alert_native.outbox(dispatch_id);
-- Which items each message carried (listed as a line or counted in "dan N lainnya"). Written once.
create table cp7_alert_native.dispatch_items(
 dispatch_id bigint not null references cp7_alert_native.dispatches(id),outbox_id bigint not null references cp7_alert_native.outbox(id),
 primary key(dispatch_id,outbox_id));
-- Last read of each source and last run of each tick, for the screen ("diperbarui jam ...").
create table cp7_alert_native.source_state(
 kind text primary key check(kind in('FABRIC_BELOW_MINIMUM','ACCESSORY_AT_REORDER_POINT','FG_AT_REORDER_POINT','AR_DUE','AP_DUE','PRODUCTION_GAP','FABRIC_NEED')),last_try_at timestamptz not null,last_ok_at timestamptz,
 last_error text check(length(last_error)<=200),open_count integer);
create table cp7_alert_native.ticks(job text primary key check(job in('COLLECT','SEND','ANALYSIS')),at timestamptz not null,outcome jsonb not null);
-- The owner's finished staged analyses as the analysis tick works through them (WA-2b): the reminders v2 condition set
-- built, then every condition active at the snapshot checked again, rule by rule, page by page.
create table cp7_alert_native.analysis_runs(
 run_id uuid primary key,data_as_of timestamptz not null,phase text not null check(phase in('SET','CHECK','DONE','FAILED')),
 rule text not null check(rule in('PRODUCTION_GAP','FABRIC_NEED')),next_offset integer not null check(next_offset>=0),
 checked integer not null default 0 check(checked>=0),still_open integer not null default 0 check(still_open>=0),
 closed integer not null default 0 check(closed>=0),rule_off integer not null default 0 check(rule_off>=0),error text check(length(error)<=200),
 started_at timestamptz not null,updated_at timestamptz not null,finished_at timestamptz,
 check((phase in('DONE','FAILED'))=(finished_at is not null)),check((phase='FAILED')=(error is not null)));
-- Automatic analyses the tick asked for in the owner's name (or decided not to: nothing changed since the last one).
create table cp7_alert_native.analysis_requests(
 request_id uuid primary key,query jsonb,based_on_run uuid not null,freshness text not null check(length(freshness)<=60),
 state text not null check(state in('PENDING','REQUESTED','FAILED','SKIPPED_NO_CHANGE')),created_at timestamptz not null,
 requested_at timestamptz,error text check(length(error)<=200),check((state='SKIPPED_NO_CHANGE')=(query is null)),
 check((state in('REQUESTED','FAILED'))=(requested_at is not null)),check((state='FAILED')=(error is not null)));
do $$declare t text;begin
 foreach t in array array['settings','key_events','transport','alerts','dispatches','outbox','dispatch_items','source_state','ticks','analysis_runs',
  'analysis_requests']loop
  execute format('alter table cp7_alert_native.%I enable row level security',t);
  execute format('create policy alert_no_access on cp7_alert_native.%I for all to public using(false)with check(false)',t);
  execute format('revoke all on cp7_alert_native.%I from public,anon,authenticated,service_role',t);
 end loop;end $$;
-- Owned by postgres whoever installs (the CI harness installs as supabase_admin: WA-3b run 39275715784 found the table
-- left with the installer); dropped with the schema on uninstall.
alter table cp7_alert_native.transport owner to postgres;
grant select on cp7_alert_native.transport to cp7_alert;

-- ------------------------------------------------------------------ guards --
create function cp7_alert_native.guard_append_only()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
begin raise exception 'CP7_ALERT_APPEND_ONLY' using detail=tg_table_name;end $$;
create trigger settings_append_only before update or delete on cp7_alert_native.settings for each row execute function cp7_alert_native.guard_append_only();
create trigger key_events_append_only before update or delete on cp7_alert_native.key_events for each row execute function cp7_alert_native.guard_append_only();
create trigger dispatch_items_append_only before update or delete on cp7_alert_native.dispatch_items for each row execute function cp7_alert_native.guard_append_only();
create trigger transport_no_delete before delete on cp7_alert_native.transport for each row execute function cp7_alert_native.guard_append_only();
-- An alert keeps its identity; only an OPEN one changes: refreshed while open, or resolved once.
create function cp7_alert_native.guard_alert()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='DELETE'or old.state<>'OPEN'or(new.id,new.kind,new.subject_key,new.episode,new.opened_at)is distinct from(old.id,old.kind,old.subject_key,old.episode,old.opened_at)
  or(new.state='OPEN'and(new.resolved_at,new.resolution)is distinct from(null::timestamptz,null::text))
  or(new.state='RESOLVED'and(new.title,new.detail,new.party_names,new.source_hash,new.refreshed_at)is distinct from(old.title,old.detail,old.party_names,old.source_hash,old.refreshed_at))
 then raise exception 'CP7_ALERT_IMMUTABLE';end if;
 return new;
end $$;
create trigger alerts_guard before update or delete on cp7_alert_native.alerts for each row execute function cp7_alert_native.guard_alert();
-- A new episode is queued for WhatsApp in the same transaction that opens it.
create function cp7_alert_native.queue_alert()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
begin
 insert into cp7_alert_native.outbox(item_kind,item_id,item_episode,round,alert_kind)values('ALERT',new.id,new.episode::text,0,new.kind);
 return null;
end $$;
create trigger alerts_queue after insert on cp7_alert_native.alerts for each row execute function cp7_alert_native.queue_alert();
create function cp7_alert_native.guard_outbox()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='DELETE'or(new.id,new.item_kind,new.item_id,new.item_episode,new.round,new.alert_kind,new.queued_at)
   is distinct from(old.id,old.item_kind,old.item_id,old.item_episode,old.round,old.alert_kind,old.queued_at)
  or new.attempts<old.attempts or new.attempts>old.attempts+1 or(new.attempts=old.attempts+1)<>(new.state='DISPATCHED'and old.state<>'DISPATCHED')
  or(old.state,new.state)not in(('PENDING','PENDING'),('PENDING','HELD_QUIET'),('HELD_QUIET','PENDING'),('HELD_QUIET','HELD_QUIET'),
   ('PENDING','DISPATCHED'),('HELD_QUIET','DISPATCHED'),('PENDING','RESOLVED_BEFORE_SEND'),('HELD_QUIET','RESOLVED_BEFORE_SEND'),
   ('PENDING','DISABLED'),('HELD_QUIET','DISABLED'),('PENDING','KIND_OFF'),('HELD_QUIET','KIND_OFF'),
   ('DISPATCHED','ACCEPTED'),('DISPATCHED','PENDING'),('DISPATCHED','UNKNOWN'),('UNKNOWN','ACCEPTED'),('UNKNOWN','PENDING'))
 then raise exception 'CP7_ALERT_OUTBOX_TRANSITION' using detail=old.state||'->'||new.state;end if;
 return new;
end $$;
create trigger outbox_guard before update or delete on cp7_alert_native.outbox for each row execute function cp7_alert_native.guard_outbox();
create function cp7_alert_native.guard_dispatch()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='DELETE'or(new.id,new.kind,new.digest_slot,new.settings_revision,new.body,new.body_sha256,new.request_id,new.queued_at)
   is distinct from(old.id,old.kind,old.digest_slot,old.settings_revision,old.body,old.body_sha256,old.request_id,old.queued_at)
  or(old.net_request_id is not null and new.net_request_id is distinct from old.net_request_id)
  or(old.status<>new.status and(old.status,new.status)not in(('QUEUED','PROVIDER_ACCEPTED'),('QUEUED','PROVIDER_REFUSED'),('QUEUED','TRANSPORT_FAILED'),('QUEUED','UNKNOWN')))
  or(old.status<>'QUEUED'and(new.answered_at,new.http_status,new.provider_text)is distinct from(old.answered_at,old.http_status,old.provider_text))
  or(old.resolved_outcome is not null and(new.resolved_outcome,new.resolved_by,new.resolved_at,new.resolve_request)
   is distinct from(old.resolved_outcome,old.resolved_by,old.resolved_at,old.resolve_request))
 then raise exception 'CP7_ALERT_DISPATCH_IMMUTABLE';end if;
 return new;
end $$;
create trigger dispatches_guard before update or delete on cp7_alert_native.dispatches for each row execute function cp7_alert_native.guard_dispatch();
-- A run's identity is fixed and its progress only moves forward; a finished run (DONE or FAILED) is never changed again.
create function cp7_alert_native.guard_analysis_run()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='DELETE'or old.phase in('DONE','FAILED')or(new.run_id,new.data_as_of,new.started_at)is distinct from(old.run_id,old.data_as_of,old.started_at)
  or(old.phase,new.phase)not in(('SET','SET'),('SET','CHECK'),('SET','FAILED'),('CHECK','CHECK'),('CHECK','DONE'),('CHECK','FAILED'))
  or(old.rule='FABRIC_NEED'and new.rule='PRODUCTION_GAP')or(old.rule=new.rule and new.next_offset<old.next_offset)
  or new.checked<old.checked or new.still_open<old.still_open or new.closed<old.closed or new.rule_off<old.rule_off
 then raise exception 'CP7_ALERT_ANALYSIS_RUN_TRANSITION' using detail=old.phase||'->'||new.phase;end if;
 return new;
end $$;
create trigger analysis_runs_guard before update or delete on cp7_alert_native.analysis_runs for each row execute function cp7_alert_native.guard_analysis_run();
-- A request is written once; a PENDING one is answered once (REQUESTED or FAILED).
create function cp7_alert_native.guard_analysis_request()returns trigger
language plpgsql security definer set search_path=''set TimeZone='UTC'as $$
begin
 if tg_op='DELETE'or old.state<>'PENDING'or new.state not in('REQUESTED','FAILED')
  or(new.request_id,new.query,new.based_on_run,new.freshness,new.created_at)is distinct from(old.request_id,old.query,old.based_on_run,old.freshness,old.created_at)
 then raise exception 'CP7_ALERT_ANALYSIS_REQUEST_TRANSITION' using detail=old.state||'->'||new.state;end if;
 return new;
end $$;
create trigger analysis_requests_guard before update or delete on cp7_alert_native.analysis_requests for each row execute function cp7_alert_native.guard_analysis_request();

-- ----------------------------------------------------------------- helpers --
create function cp7_alert_native.ts_key(p timestamptz)returns text
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select to_char(p at time zone'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')$$;
create function cp7_alert_native.label(p timestamptz)returns text
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select extract(day from w)::integer||' '||(array['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'])[extract(month from w)::integer]
  ||' '||to_char(w,'HH24.MI')from(select p at time zone'Asia/Jakarta' w)x$$;
create function cp7_alert_native.tgl(p text)returns text
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select case when p is null then'-'else extract(day from p::date)::integer||' '
  ||(array['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'])[extract(month from p::date)::integer]end$$;
create function cp7_alert_native.rp(p text)returns text
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select case when p is null then'Rp?'else'Rp'||replace(to_char(round(p::numeric),'FM999,999,999,999,990'),',','.')end$$;
create function cp7_alert_native.num(p text)returns text
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select case when p is null then'?'else replace(trim_scale(round(p::numeric,2))::text,'.',',')end$$;
create function cp7_alert_native.in_quiet(p_on boolean,p_start time,p_end time,p_at timestamptz)returns boolean
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select p_on and case when p_start<p_end then t>=p_start and t<p_end else t>=p_start or t<p_end end
 from(select(p_at at time zone'Asia/Jakarta')::time t)x$$;
create function cp7_alert_native.current_settings()returns cp7_alert_native.settings
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select s from cp7_alert_native.settings s order by s.revision desc limit 1$$;
-- The ticks run with the 8 s limit a page request has, like the K4 runner.
create function cp7_alert_native.require_tick_limit()returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare limit_ms integer;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_ALERT_READ_COMMITTED_REQUIRED';end if;
 select x.setting::integer into limit_ms from pg_catalog.pg_settings x where x.name='statement_timeout';
 if limit_ms is null or limit_ms not between 1 and 8000 then
  raise exception using errcode='55000',message='CP7_ALERT_STATEMENT_LIMIT_REQUIRED',detail=jsonb_build_object('statement_timeout_ms',limit_ms)::text;end if;
end $$;
create function cp7_alert_native.record_tick(p_job text,p_outcome jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
begin
 insert into cp7_alert_native.ticks as t(job,at,outcome)values(p_job,clock_timestamp(),p_outcome)
  on conflict(job)do update set at=excluded.at,outcome=excluded.outcome;
 return p_outcome||jsonb_build_object('job',p_job);
end $$;

-- ------------------------------------------------- owner identity (K4) --
-- The request identity exactly as Supabase's auth.jwt()/auth.uid() read it (request.jwt.claims, and the older
-- request.jwt.claim.sub first), without needing a privilege on schema auth.
create function cp7_alert_native.jwt()returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce(nullif(current_setting('request.jwt.claim',true),''),nullif(current_setting('request.jwt.claims',true),''))::jsonb$$;
create function cp7_alert_native.uid()returns uuid
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce(nullif(current_setting('request.jwt.claim.sub',true),''),cp7_alert_native.jwt()->>'sub')::uuid$$;
create function cp7_alert_native.claims_enter(p_actor uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare prior jsonb:=jsonb_build_object('claims',current_setting('request.jwt.claims',true),'sub',current_setting('request.jwt.claim.sub',true),
 'claim',current_setting('request.jwt.claim',true));
begin
 perform set_config('request.jwt.claims',jsonb_build_object('sub',p_actor,'role','authenticated')::text,true),
  set_config('request.jwt.claim.sub','',true),set_config('request.jwt.claim','',true);
 return prior;
end $$;
create function cp7_alert_native.claims_leave(p_prior jsonb)returns void
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
begin
 perform set_config('request.jwt.claims',coalesce(p_prior->>'claims',''),true),set_config('request.jwt.claim.sub',coalesce(p_prior->>'sub',''),true),
  set_config('request.jwt.claim',coalesce(p_prior->>'claim',''),true);
end $$;
-- The request's identity is an active OWNER (and, for a tick, the owner who saved the settings); null otherwise.
create function cp7_alert_native.owner_access(p_actor_user uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;
begin
 if cp7_alert_native.uid()is null or coalesce(cp7_alert_native.jwt()->>'role','')<>'authenticated'then return null;end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or a->'profile'->>'role_code'is distinct from'OWNER'
  or(p_actor_user is not null and a->'profile'->>'id'is distinct from p_actor_user::text)then return null;end if;
 return a;
end $$;

-- ---------------------------------------------------------------- sources --
-- Each source answers {rows:[{subject_key,title,detail,party_names}], states:{subject_key: state}} for the reminders
-- open now; states name why a known subject is not open (the resolution of its alert).
-- Ringkasan Gudang (warehouse-summary/summary.sql, low/low_hit): balances of Bahan & Roll per material x roll x
-- location with physical_at <= statement_timestamp(), nonzero, every location, summed per material; active FABRIC with
-- minimum_stock_qty > 0 in Kain & Benchmark; below when the sum is under the minimum. Same keys as that screen.
create function cp7_alert_native.fabric_source()returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare r jsonb;
begin
 if erp.has_permission('warehouse.dashboard.view')is not true or erp.has_permission('warehouse.material.view')is not true
  or erp.has_permission('master.fabric.view')is not true then raise exception using errcode='42501',message='CP7_ALERT_FABRIC_SOURCE_DENIED';end if;
 with mat_sum as materialized(
  select sm.material_id,sm.roll_id,sm.location_id,sum(sm.qty_signed)qty
  from erp.material_stock_movements sm join erp.materials m on m.id=sm.material_id
  where sm.physical_at<=statement_timestamp()group by sm.material_id,sm.roll_id,sm.location_id),
 mat as materialized(select x.material_id,x.qty from mat_sum x join erp.materials m on m.id=x.material_id join erp.locations l on l.id=x.location_id where x.qty<>0),
 low as materialized(
  select m.id material_id,m.material_sku::text material_sku,m.material_name::text material_name,m.unit_code::text unit_code,
   coalesce((select sum(x.qty)from mat x where x.material_id=m.id),0)qty,fp.minimum_stock_qty minimum_qty
  from erp.materials m join erp.fabric_master_profiles fp on fp.material_id=m.id
  where m.material_type='FABRIC'and m.is_active and fp.minimum_stock_qty>0)
 select jsonb_build_object(
  'rows',coalesce(jsonb_agg(jsonb_build_object('subject_key',y.material_id::text,'title','Stok kain di bawah minimum: '||y.material_name,
   'detail',jsonb_build_object('material_id',y.material_id,'material_sku',y.material_sku,'material_name',y.material_name,'unit_code',y.unit_code,
    'qty',y.qty::text,'minimum_qty',y.minimum_qty::text),'party_names','[]'::jsonb)order by y.material_sku,y.material_id)filter(where y.qty<y.minimum_qty),'[]'),
  'states',coalesce(jsonb_object_agg(y.material_id::text,'AT_OR_ABOVE_MINIMUM')filter(where y.qty>=y.minimum_qty),'{}'))
 into r from low y;
 return r;
end $$;
-- Owner D17-10: the fabric reminder is one kind. Fabrics with a minimum in Kain & Benchmark come from fabric_source()
-- (the Ringkasan Gudang rule, unchanged); fabrics without one come from the formula (cp7_stock_formula.material_source,
-- stock + on order <= the formula's number), whose state for a fabric with a minimum (MANUAL_MINIMUM_IN_FORCE) is left to
-- fabric_source(). The two sets never share a fabric.
create function cp7_alert_native.fabric_kind_source()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare m jsonb:=cp7_alert_native.fabric_source();f jsonb:=cp7_stock_formula.material_source('FABRIC');
begin
 return jsonb_build_object('rows',(m->'rows')||(f->'rows'),
  'states',coalesce((select jsonb_object_agg(e.key,e.value)from jsonb_each(f->'states')e where e.value<>'"MANUAL_MINIMUM_IN_FORCE"'::jsonb),'{}')||(m->'states'));
end $$;
-- Receivables: cp7_reminder_native.receivable_source() (finance.ar.view), open while DUE_TODAY or OVERDUE.
create function cp7_alert_native.ar_source()returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare src jsonb:=cp7_reminder_native.receivable_source();r jsonb;
begin
 with doc as(select x from jsonb_array_elements(src->'pages')pg,jsonb_array_elements(pg->'page'->'rows')x),
 j as(select cd c,d.x from jsonb_array_elements(src->'conditions')cd join doc d on d.x->>'id'=cd->>'source_id')
 select jsonb_build_object(
  'rows',coalesce(jsonb_agg(jsonb_build_object('subject_key',c->>'key','title','Piutang jatuh tempo: '||coalesce(x->>'number','?'),
   'detail',jsonb_build_object('sale_id',x->>'id','number',x->>'number','open_balance',x->'financial'->>'open_balance','due_date',x->>'due_date',
    'state',c->>'state','as_of',src->>'as_of'),
   'party_names',case when x->>'customer_name'is null then'[]'::jsonb else jsonb_build_array(x->>'customer_name')end)order by c->>'key')
   filter(where c->>'state'in('OVERDUE','DUE_TODAY')),'[]'),
  'states',coalesce(jsonb_object_agg(c->>'key',c->>'state')filter(where c->>'state'not in('OVERDUE','DUE_TODAY')),'{}'))
 into r from j;
 return r;
end $$;
-- Supplier material payables: cp7_reminder_native.payable_source() (finance.ap.view), open while DUE_TODAY or OVERDUE.
create function cp7_alert_native.ap_source()returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare src jsonb:=cp7_reminder_native.payable_source();r jsonb;
begin
 select jsonb_build_object(
  'rows',coalesce(jsonb_agg(jsonb_build_object('subject_key',x->'condition'->>'key',
   'title','Tagihan supplier jatuh tempo: '||coalesce(x->'liability'->>'purchase_number','?'),
   'detail',jsonb_build_object('purchase_id',x->'liability'->>'purchase_id','purchase_number',x->'liability'->>'purchase_number',
    'invoice_numbers',x->'liability'->>'active_invoice_numbers','remaining',x->'balance'->>'remaining','due_date',x->>'due_date',
    'state',x->'condition'->>'state','as_of',src->>'as_of'),
   'party_names',case when x->'liability'->>'supplier_name'is null then'[]'::jsonb else jsonb_build_array(x->'liability'->>'supplier_name')end)
   order by x->'condition'->>'key')filter(where x->'condition'->>'state'in('OVERDUE','DUE_TODAY')),'[]'),
  'states',coalesce(jsonb_object_agg(x->'condition'->>'key',x->'condition'->>'state')filter(where x->'condition'->>'state'not in('OVERDUE','DUE_TODAY')),'{}'))
 into r from jsonb_array_elements(src->'rows')x;
 return r;
end $$;

-- ------------------------------------------------------------- collector --
-- One subject of a kind open now: a new episode when none is open (queued by the trigger), else its numbers refreshed.
create function cp7_alert_native.apply_one(p_kind text,x jsonb)returns text
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare h text:=encode(sha256(convert_to(jsonb_build_object('title',x->'title','detail',x->'detail','party_names',x->'party_names')::text,'UTF8')),'hex');
 cur cp7_alert_native.alerts%rowtype;
begin
 select*into cur from cp7_alert_native.alerts a where a.kind=p_kind and a.subject_key=x->>'subject_key'and a.state='OPEN'for update;
 if not found then
  insert into cp7_alert_native.alerts(kind,subject_key,episode,title,detail,party_names,source_hash)
  values(p_kind,x->>'subject_key',coalesce((select max(a.episode)from cp7_alert_native.alerts a where a.kind=p_kind and a.subject_key=x->>'subject_key'),0)+1,
   left(x->>'title',300),x->'detail',x->'party_names',h);
  return'OPENED';
 elsif cur.source_hash<>h then
  update cp7_alert_native.alerts set title=left(x->>'title',300),detail=x->'detail',party_names=x->'party_names',source_hash=h,refreshed_at=clock_timestamp()
  where id=cur.id;
  return'REFRESHED';
 end if;
 return'SAME';
end $$;
-- One subject of a kind no longer open: its open episode (if any) resolved with the reason.
create function cp7_alert_native.resolve_one(p_kind text,p_subject text,p_resolution text)returns integer
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare n integer;
begin
 update cp7_alert_native.alerts set state='RESOLVED',resolved_at=clock_timestamp(),resolution=left(p_resolution,80)
 where kind=p_kind and subject_key=p_subject and state='OPEN';
 get diagnostics n=row_count;
 return n;
end $$;
-- Opens, refreshes and resolves the alerts of one kind from one answer of its source.
create function cp7_alert_native.apply_kind(p_kind text,p_src jsonb)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare x jsonb;did text;opened integer:=0;refreshed integer:=0;resolved integer:=0;
begin
 if jsonb_typeof(p_src->'rows')is distinct from'array'or jsonb_typeof(p_src->'states')is distinct from'object'
  or(select count(distinct e->>'subject_key')from jsonb_array_elements(p_src->'rows')e)<>jsonb_array_length(p_src->'rows')
  or exists(select 1 from jsonb_array_elements(p_src->'rows')e where p_src->'states'?(e->>'subject_key'))
 then raise exception 'CP7_ALERT_SOURCE_SHAPE' using detail=p_kind;end if;
 for x in select value from jsonb_array_elements(p_src->'rows')loop
  did:=cp7_alert_native.apply_one(p_kind,x);
  opened:=opened+(did='OPENED')::integer;refreshed:=refreshed+(did='REFRESHED')::integer;
 end loop;
 update cp7_alert_native.alerts a set state='RESOLVED',resolved_at=clock_timestamp(),resolution=coalesce(p_src->'states'->>a.subject_key,'NOT_IN_SOURCE')
 where a.kind=p_kind and a.state='OPEN'and not exists(select 1 from jsonb_array_elements(p_src->'rows')e where e->>'subject_key'=a.subject_key);
 get diagnostics resolved=row_count;
 return jsonb_build_object('opened',opened,'refreshed',refreshed,'resolved',resolved,'open',jsonb_array_length(p_src->'rows'));
end $$;
-- Reads the given kinds (sorted, one lock per kind, so two ticks never write one kind at once). A source that fails is
-- recorded and leaves its alerts as they are; the others go on. Timeouts are not caught: the tick fails as a whole.
-- The analysis kinds are read by the analysis tick and checked one condition at a time (analysis_recheck), not here.
create function cp7_alert_native.collect_kinds(p_kinds text[])returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare k text;src jsonb;res jsonb;answer jsonb:='{}';
begin
 for k in select distinct u from unnest(p_kinds)u where u not in('MANUAL_REMINDER','PRODUCTION_GAP','FABRIC_NEED')order by 1 loop
  perform pg_advisory_xact_lock(hashtextextended('CP7:ALERT:KIND:'||k,0));
  begin
   src:=case k when'FABRIC_BELOW_MINIMUM'then cp7_alert_native.fabric_kind_source()when'FG_AT_REORDER_POINT'then cp7_stock_formula.fg_source()
    when'ACCESSORY_AT_REORDER_POINT'then cp7_stock_formula.material_source('ACCESSORY')
    when'AR_DUE'then cp7_alert_native.ar_source()
    when'AP_DUE'then cp7_alert_native.ap_source()end;
   if src is null then raise exception 'CP7_ALERT_KIND_UNKNOWN' using detail=k;end if;
   res:=cp7_alert_native.apply_kind(k,src);
   insert into cp7_alert_native.source_state as s(kind,last_try_at,last_ok_at,last_error,open_count)
   values(k,clock_timestamp(),clock_timestamp(),null,(res->>'open')::integer)
   on conflict(kind)do update set last_try_at=excluded.last_try_at,last_ok_at=excluded.last_ok_at,last_error=null,open_count=excluded.open_count;
   answer:=answer||jsonb_build_object(k,res);
  exception when others then
   insert into cp7_alert_native.source_state as s(kind,last_try_at,last_error)values(k,clock_timestamp(),left(SQLSTATE||' '||SQLERRM,200))
   on conflict(kind)do update set last_try_at=excluded.last_try_at,last_error=excluded.last_error;
   answer:=answer||jsonb_build_object(k,jsonb_build_object('error',SQLSTATE,'message',left(SQLERRM,120)));
  end;
 end loop;
 return answer;
end $$;
-- The owner's own manual reminders whose time has come; never anyone else's.
create function cp7_alert_native.queue_manual(p_owner uuid)returns integer
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare n integer;
begin
 insert into cp7_alert_native.outbox(item_kind,item_id,item_episode,round,alert_kind)
 select'MANUAL_REMINDER',r.id,cp7_alert_native.ts_key(r.due_at),0,'MANUAL_REMINDER'from erp.manual_reminders r
 where r.owner_user_id=p_owner and r.status='OPEN'and r.due_at<=clock_timestamp()
 on conflict(item_kind,item_id,item_episode,round)do nothing;
 get diagnostics n=row_count;
 return n;
end $$;
create function cp7_alert_native.collect_tick()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_alert_native.settings;prior jsonb;a jsonb;res jsonb;manual integer;
begin
 perform cp7_alert_native.require_tick_limit();
 if not pg_try_advisory_xact_lock(hashtextextended('CP7:ALERT:COLLECT',0))then return jsonb_build_object('ran',false,'outcome','BUSY');end if;
 s:=cp7_alert_native.current_settings();
 if s.revision is null then return cp7_alert_native.record_tick('COLLECT',jsonb_build_object('ran',false,'outcome','NOT_CONFIGURED'));end if;
 prior:=cp7_alert_native.claims_enter(s.actor);
 a:=cp7_alert_native.owner_access(s.actor_user_id);
 if a is null then
  perform cp7_alert_native.claims_leave(prior);
  return cp7_alert_native.record_tick('COLLECT',jsonb_build_object('ran',false,'outcome','OWNER_ACCESS_DENIED'));
 end if;
 res:=cp7_alert_native.collect_kinds(array['FABRIC_BELOW_MINIMUM','ACCESSORY_AT_REORDER_POINT','FG_AT_REORDER_POINT',
  'AR_DUE','AP_DUE']);
 manual:=cp7_alert_native.queue_manual(s.actor_user_id);
 if erp.get_my_access_v1()is distinct from a then raise exception using errcode='42501',message='CP7_ALERT_ACCESS_CHANGED_DURING_TICK';end if;
 perform cp7_alert_native.claims_leave(prior);
 return cp7_alert_native.record_tick('COLLECT',jsonb_build_object('ran',true,'outcome','COLLECTED','kinds',res,'manual_queued',manual));
end $$;

-- ---------------------------------------------------------------- analysis --
-- WA-2b. PRODUCTION_GAP and FABRIC_NEED come from the owner's own staged analysis: the reminders v2 condition set of the
-- owner's latest finished run, read through the public functions the Reminder screen calls, with the owner's identity
-- (erp_cp7_step_reminder_conditions_v2 builds the set, erp_cp7_read_reminder_conditions_v2 lists the conditions active at
-- the snapshot with the owner's reminder rule, erp_cp7_recheck_reminder_v2 checks one against the ERP now). A condition
-- is an alert only while its reminder rule is on and reached and the recheck says STILL_OPEN, the reminders' own rule
-- for a reminder; ACCESSORY_NEED is never STILL_OPEN there (no live recheck exists), so it is not forwarded.
create function cp7_alert_native.analysis_open(v jsonb)returns boolean
language sql immutable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce(v->>'verdict'='STILL_OPEN'and v->'policy_binding'->'policy'->'config'->>'enabled'='true',false)$$;
-- One rechecked condition as an alert row (no party names: these conditions name products and fabrics only).
create function cp7_alert_native.analysis_row(p_kind text,v jsonb,p_run uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('subject_key',v->>'condition_key',
  'title',case p_kind when'PRODUCTION_GAP'then'Kekurangan produksi: '||coalesce(v->>'label','(tanpa label)')
   else'Kain perlu dibeli: '||coalesce(m.material_name::text,'?')||' untuk '||coalesce(v->>'label','(tanpa label)')end,
  'detail',jsonb_build_object('run_id',p_run,'data_as_of',v->'data_as_of','checked_at',v->'checked_at','label',v->'label','target_key',v->'target_key',
   'need_snapshot_pcs',v->'numbers'->'need_snapshot_pcs','need_now_pcs',v->'numbers'->'need_now_pcs','increase_pcs',v->'numbers'->'increase_pcs',
   'material_id',m.id,'material_name',m.material_name::text,'value',v->'numbers'->'snapshot_value','unit',v->'numbers'->'snapshot_unit',
   'threshold',v->'numbers'->'threshold','reason',v->'reason'),
  'party_names','[]'::jsonb)
 from(select 1)one left join erp.materials m on p_kind='FABRIC_NEED'and m.id::text=v->'numbers'->'material'->>'material_id'$$;
-- One unit of the analysis tick, with the owner's identity already in place: (1) the owner's latest finished run is
-- worked through (its condition set built one step a unit, then the conditions active at the snapshot checked again,
-- ten a page, until the unit's 3 s budget is spent; at the end every analysis alert the run no longer shows is resolved);
-- else (2) a pending automatic request is sent, alone in its unit (the capture is the analysis's heaviest statement);
-- else (3) whether a new automatic analysis is due: none of the owner's running, one finished before (until then the
-- tick says so at any hour), switched on, inside the analysis hours, the last one at least analysis_every_minutes old,
-- and the ERP changed since it (or a new day began). Steps (1) and (2) run at any hour. The automatic
-- analysis repeats the owner's last period length, ending yesterday, with the same grouping; the K4 runner computes it.
create function cp7_alert_native.analysis_unit(s cp7_alert_native.settings,t0 timestamptz)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare d record;r cp7_alert_native.analysis_runs;st jsonb;page jsonb;x jsonb;v jsonb;q jsonb;f jsonb;req cp7_alert_native.analysis_requests;
 deadline timestamptz:=t0+interval'3 seconds';yday date;span integer;total integer;finished boolean:=false;err text;
 n_checked integer:=0;n_open integer:=0;n_closed integer:=0;n_off integer:=0;
begin
 select j.run_id,j.captured_at,j.query into d from cp7_analysis_stage.jobs j where j.actor=s.actor and j.state='DONE'
 order by j.captured_at desc,j.run_id desc limit 1;
 if d.run_id is not null then
  select*into r from cp7_alert_native.analysis_runs x where x.run_id=d.run_id for update;
  if not found then
   insert into cp7_alert_native.analysis_runs(run_id,data_as_of,phase,rule,next_offset,started_at,updated_at)
   values(d.run_id,d.captured_at,'SET','PRODUCTION_GAP',0,t0,t0)returning*into r;
  end if;
 end if;
 if r.phase in('SET','CHECK')then
  begin
   if r.phase='SET'then
    st:=public.erp_cp7_step_reminder_conditions_v2(r.run_id);
    if st->>'state'='FAILED'then raise exception 'CP7_WA_CONDITION_SET_FAILED' using detail=coalesce(st->'failure'->>'code','');end if;
    if st->>'state'<>'DONE'then
     update cp7_alert_native.analysis_runs set updated_at=clock_timestamp()where run_id=r.run_id;
     return jsonb_build_object('ran',true,'outcome','CONDITION_SET_STEP','run_id',r.run_id,'units_done',st->'units_done','unit_count',st->'unit_count',
      'worker_active',st->'worker_active');
    end if;
    update cp7_alert_native.analysis_runs set phase='CHECK',updated_at=clock_timestamp()where run_id=r.run_id returning*into r;
   end if;
   if not pg_try_advisory_xact_lock(hashtextextended('CP7:ALERT:KIND:FABRIC_NEED',0))
    or not pg_try_advisory_xact_lock(hashtextextended('CP7:ALERT:KIND:PRODUCTION_GAP',0))then
    return jsonb_build_object('ran',false,'outcome','KIND_BUSY','run_id',r.run_id);
   end if;
   <<pages>>loop
    page:=public.erp_cp7_read_reminder_conditions_v2(jsonb_build_object('run_id',r.run_id,'rule_id',r.rule,'state','ACTIVE','offset',r.next_offset,'limit',10));
    total:=(page->>'total')::integer;
    if r.next_offset<total and jsonb_array_length(page->'rows')=0 then raise exception 'CP7_WA_CONDITION_PAGE_EMPTY';end if;
    for x in select e from jsonb_array_elements(page->'rows')e loop
     if x->>'eligibility'in('LOCAL_PREVIEW_ELIGIBLE','QUIET','COOLDOWN')then
      v:=public.erp_cp7_recheck_reminder_v2(r.run_id,x->>'key');
      if cp7_alert_native.analysis_open(v)then
       perform cp7_alert_native.apply_one(r.rule,cp7_alert_native.analysis_row(r.rule,v,r.run_id));n_open:=n_open+1;
      else n_closed:=n_closed+cp7_alert_native.resolve_one(r.rule,x->>'key','RECHECK_'||coalesce(v->>'verdict','UNKNOWN'));end if;
     else
      n_off:=n_off+1;n_closed:=n_closed+cp7_alert_native.resolve_one(r.rule,x->>'key','RULE_'||coalesce(x->>'eligibility','UNKNOWN'));
     end if;
     n_checked:=n_checked+1;r.next_offset:=r.next_offset+1;
     exit pages when clock_timestamp()>deadline;
    end loop;
    if r.next_offset>=total then
     if r.rule='PRODUCTION_GAP'then r.rule:='FABRIC_NEED';r.next_offset:=0;else finished:=true;exit pages;end if;
    end if;
    exit pages when clock_timestamp()>deadline;
   end loop;
   if finished then
    update cp7_alert_native.alerts a set state='RESOLVED',resolved_at=clock_timestamp(),resolution='NOT_OPEN_IN_LATEST_ANALYSIS'
    where a.kind in('PRODUCTION_GAP','FABRIC_NEED')and a.state='OPEN'and a.detail->>'run_id'is distinct from r.run_id::text;
    get diagnostics total=row_count;n_closed:=n_closed+total;
   end if;
   update cp7_alert_native.analysis_runs set phase=case when finished then'DONE'else'CHECK'end,rule=r.rule,next_offset=r.next_offset,
    checked=checked+n_checked,still_open=still_open+n_open,closed=closed+n_closed,rule_off=rule_off+n_off,updated_at=clock_timestamp(),
    finished_at=case when finished then clock_timestamp()end
   where run_id=r.run_id;
   return jsonb_build_object('ran',true,'outcome',case when finished then'ANALYSIS_CHECKED'else'ANALYSIS_CHECKING'end,'run_id',r.run_id,
    'rule',r.rule,'next_offset',r.next_offset,'checked',n_checked,'still_open',n_open,'closed',n_closed,'rule_off',n_off);
  exception when query_canceled then raise;
   when others then err:=left(SQLSTATE||' '||SQLERRM,200);
  end;
  -- A run that cannot be used (expired, access, a failed condition set) leaves nothing open from it.
  update cp7_alert_native.alerts a set state='RESOLVED',resolved_at=clock_timestamp(),resolution='ANALYSIS_UNAVAILABLE'
  where a.kind in('PRODUCTION_GAP','FABRIC_NEED')and a.state='OPEN'and a.detail->>'run_id'=r.run_id::text;
  update cp7_alert_native.analysis_runs set phase='FAILED',error=err,updated_at=clock_timestamp(),finished_at=clock_timestamp()where run_id=r.run_id;
  return jsonb_build_object('ran',true,'outcome','ANALYSIS_RUN_FAILED','run_id',r.run_id,'error',err);
 end if;
 select*into req from cp7_alert_native.analysis_requests x where x.state='PENDING'order by x.created_at limit 1 for update;
 if found then
  begin
   st:=public.erp_cp7_request_staged_analysis_v1(req.query,req.request_id);
   update cp7_alert_native.analysis_requests set state='REQUESTED',requested_at=clock_timestamp()where request_id=req.request_id;
   return jsonb_build_object('ran',true,'outcome','ANALYSIS_REQUESTED','request_id',req.request_id,'query',req.query,'job_state',st->'state');
  exception when query_canceled then raise;
   when others then err:=left(SQLSTATE||' '||SQLERRM,200);
  end;
  update cp7_alert_native.analysis_requests set state='FAILED',requested_at=clock_timestamp(),error=err where request_id=req.request_id;
  return jsonb_build_object('ran',true,'outcome','ANALYSIS_REQUEST_FAILED','request_id',req.request_id,'error',err);
 end if;
 -- What the owner's own analysis is doing is reported first, at any hour; the switch and the hours only gate a new
 -- automatic request.
 if exists(select 1 from cp7_analysis_stage.jobs j where j.actor=s.actor and j.state='RUNNING')then
  return jsonb_build_object('ran',false,'outcome','ANALYSIS_RUNNING','run_id',d.run_id);end if;
 if d.run_id is null then return jsonb_build_object('ran',false,'outcome','NO_OWNER_ANALYSIS_YET');end if;
 if s.analysis_every_minutes=0 then return jsonb_build_object('ran',false,'outcome','AUTO_ANALYSIS_OFF','run_id',d.run_id);end if;
 if not((t0 at time zone'Asia/Jakarta')::time>=s.analysis_start and(t0 at time zone'Asia/Jakarta')::time<s.analysis_end)then
  return jsonb_build_object('ran',false,'outcome','OUTSIDE_ANALYSIS_HOURS','run_id',d.run_id);end if;
 if d.captured_at>t0-make_interval(mins=>s.analysis_every_minutes)
  or exists(select 1 from cp7_alert_native.analysis_requests x where x.created_at>t0-make_interval(mins=>s.analysis_every_minutes))then
  return jsonb_build_object('ran',false,'outcome','NOT_DUE','run_id',d.run_id);end if;
 yday:=(t0 at time zone'Asia/Jakarta')::date-1;
 begin f:=public.erp_cp7_staged_snapshot_freshness_v1(d.run_id);
 exception when query_canceled then raise;when others then f:=jsonb_build_object('freshness_state','UNAVAILABLE');
 end;
 if f->>'freshness_state'in('NO_RECORDED_CHANGE','VERIFIED_SAME')and(d.query->>'through_date')::date>=yday then
  insert into cp7_alert_native.analysis_requests(request_id,query,based_on_run,freshness,state,created_at)
  values(gen_random_uuid(),null,d.run_id,f->>'freshness_state','SKIPPED_NO_CHANGE',t0);
  return jsonb_build_object('ran',true,'outcome','NO_CHANGE_SINCE_ANALYSIS','run_id',d.run_id,'freshness',f->>'freshness_state');
 end if;
 span:=(d.query->>'through_date')::date-(d.query->>'from_date')::date;
 q:=jsonb_build_object('from_date',(yday-span)::text,'through_date',yday::text,'group_mode',d.query->>'group_mode');
 insert into cp7_alert_native.analysis_requests(request_id,query,based_on_run,freshness,state,created_at)
 values(gen_random_uuid(),q,d.run_id,coalesce(f->>'freshness_state','UNKNOWN'),'PENDING',t0)returning*into req;
 return jsonb_build_object('ran',true,'outcome','ANALYSIS_DUE','request_id',req.request_id,'query',q,'freshness',req.freshness);
end $$;
create function cp7_alert_native.analysis_tick()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_alert_native.settings;t0 timestamptz:=clock_timestamp();prior jsonb;a jsonb;res jsonb;
begin
 perform cp7_alert_native.require_tick_limit();
 if not pg_try_advisory_xact_lock(hashtextextended('CP7:WA:ANALYSIS',0))then return jsonb_build_object('ran',false,'outcome','BUSY');end if;
 s:=cp7_alert_native.current_settings();
 if s.revision is null then return cp7_alert_native.record_tick('ANALYSIS',jsonb_build_object('ran',false,'outcome','NOT_CONFIGURED'));end if;
 prior:=cp7_alert_native.claims_enter(s.actor);
 a:=cp7_alert_native.owner_access(s.actor_user_id);
 if a is null then
  perform cp7_alert_native.claims_leave(prior);
  return cp7_alert_native.record_tick('ANALYSIS',jsonb_build_object('ran',false,'outcome','OWNER_ACCESS_DENIED'));
 end if;
 res:=cp7_alert_native.analysis_unit(s,t0);
 if erp.get_my_access_v1()is distinct from a then raise exception using errcode='42501',message='CP7_ALERT_ACCESS_CHANGED_DURING_TICK';end if;
 perform cp7_alert_native.claims_leave(prior);
 return cp7_alert_native.record_tick('ANALYSIS',res);
end $$;
-- Before a message, the analysis alerts it would carry (all open ones for a digest) are checked again one condition at
-- a time, in the given order, until p_deadline or p_cap per kind: still open -> numbers refreshed, may be sent; anything
-- else -> resolved (its waiting item becomes RESOLVED_BEFORE_SEND); an expired run -> resolved ANALYSIS_EXPIRED. What is
-- not reached is counted as unchecked and waits; a kind whose lock is held or whose check fails is reported failed.
create function cp7_alert_native.analysis_recheck(p_alerts uuid[],p_deadline timestamptz,p_cap integer)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare x cp7_alert_native.alerts;v jsonb;ok uuid[]:='{}';failed text[]:='{}';unchecked jsonb:='{}';done jsonb:='{}';resolved integer:=0;
begin
 for x in select a.*from unnest(coalesce(p_alerts,'{}'))with ordinality u(id,o)join cp7_alert_native.alerts a on a.id=u.id
  where a.state='OPEN'and a.kind in('PRODUCTION_GAP','FABRIC_NEED')order by u.o loop
  continue when x.kind=any(failed);
  if clock_timestamp()>p_deadline or coalesce((done->>x.kind)::integer,0)>=p_cap then
   unchecked:=jsonb_set(unchecked,array[x.kind],to_jsonb(coalesce((unchecked->>x.kind)::integer,0)+1));continue;
  end if;
  if not pg_try_advisory_xact_lock(hashtextextended('CP7:ALERT:KIND:'||x.kind,0))then failed:=failed||x.kind;continue;end if;
  begin
   v:=public.erp_cp7_recheck_reminder_v2((x.detail->>'run_id')::uuid,x.subject_key);
  exception when query_canceled then raise;
   when others then
    if SQLERRM='CP7_ANALYSIS_RESULT_EXPIRED'then resolved:=resolved+cp7_alert_native.resolve_one(x.kind,x.subject_key,'ANALYSIS_EXPIRED');
    else failed:=failed||x.kind;end if;
    continue;
  end;
  if cp7_alert_native.analysis_open(v)then
   perform cp7_alert_native.apply_one(x.kind,cp7_alert_native.analysis_row(x.kind,v,(x.detail->>'run_id')::uuid));ok:=ok||x.id;
  else resolved:=resolved+cp7_alert_native.resolve_one(x.kind,x.subject_key,'RECHECK_'||coalesce(v->>'verdict','UNKNOWN'));end if;
  done:=jsonb_set(done,array[x.kind],to_jsonb(coalesce((done->>x.kind)::integer,0)+1));
 end loop;
 return jsonb_build_object('ok',to_jsonb(ok),'unchecked',unchecked,'failed',to_jsonb(failed),'resolved',resolved,'checked',done);
end $$;

-- ---------------------------------------------------------------- message --
-- One item as the message shows it: {kind,title,detail,party_names,repeat}.
create function cp7_alert_native.item_line(p jsonb,p_detail text)returns text
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select left(case p->>'kind'
  when'FABRIC_BELOW_MINIMUM'then case when p->'detail'?'reorder_point_qty'then(p->'detail'->>'name')||': sisa '
    ||cp7_alert_native.num(p->'detail'->>'free_qty')||' '||coalesce(p->'detail'->>'unit_code','')
    ||', dipesan '||cp7_alert_native.num(p->'detail'->>'on_order_qty')||' '||coalesce(p->'detail'->>'unit_code','')
    ||', minimum rumus '||cp7_alert_native.num(p->'detail'->>'reorder_point_qty')||' '||coalesce(p->'detail'->>'unit_code','')
   else(p->'detail'->>'material_name')||': sisa '||cp7_alert_native.num(p->'detail'->>'qty')||' '||(p->'detail'->>'unit_code')
   ||', minimum '||cp7_alert_native.num(p->'detail'->>'minimum_qty')||' '||(p->'detail'->>'unit_code')end
  when'FG_AT_REORDER_POINT'then coalesce(p->'detail'->>'product_name','?')||coalesce(' '||(p->'detail'->>'size_code'),'')
   ||': sisa '||cp7_alert_native.num(p->'detail'->>'free_pcs')||' pcs, sedang diproduksi '
   ||case when p->'detail'->>'wip_status'='COMPLETE'then cp7_alert_native.num(p->'detail'->>'wip_pcs')||' pcs'else'belum diketahui'end
   ||', titik pesan ulang '||cp7_alert_native.num(p->'detail'->>'reorder_point_pcs')||' pcs'
  when'ACCESSORY_AT_REORDER_POINT'then(p->'detail'->>'name')||': sisa '||cp7_alert_native.num(p->'detail'->>'free_qty')||' '||coalesce(p->'detail'->>'unit_code','')
   ||', minimum '||cp7_alert_native.num(p->'detail'->>'reorder_point_qty')||' '||coalesce(p->'detail'->>'unit_code','')
  when'MANUAL_REMINDER'then(p->>'title')||case when p_detail='DETAILED'and coalesce(p->'detail'->>'note','')<>''then' ('||left(p->'detail'->>'note',60)||')'else''end
  when'AR_DUE'then coalesce((p->'party_names'->>0)||' ','')||coalesce(p->'detail'->>'number','?')||': '||cp7_alert_native.rp(p->'detail'->>'open_balance')
   ||', jatuh tempo '||cp7_alert_native.tgl(p->'detail'->>'due_date')
  when'AP_DUE'then coalesce((p->'party_names'->>0)||' ','')||coalesce(p->'detail'->>'purchase_number','?')||': '||cp7_alert_native.rp(p->'detail'->>'remaining')
   ||', jatuh tempo '||cp7_alert_native.tgl(p->'detail'->>'due_date')
  when'PRODUCTION_GAP'then coalesce(p->'detail'->>'label','?')||': kurang '||cp7_alert_native.num(p->'detail'->>'need_now_pcs')||' pcs'
  when'FABRIC_NEED'then coalesce(p->'detail'->>'material_name','?')||' untuk '||coalesce(p->'detail'->>'label','?')||': '
   ||cp7_alert_native.num(p->'detail'->>'value')||' '||coalesce(p->'detail'->>'unit','')
  else p->>'title'end,120)$$;
-- SUMMARY (default) never shows supplier or customer names: payables and receivables become one line, count and total.
-- Lines per kind are cut to fit 1000 characters; what is cut is counted in "dan N lainnya", never dropped silently.
-- Analysis kinds carry the time of their analysis data; analysis alerts a digest could not check again in time are
-- only counted (p_unchecked), never listed.
create function cp7_alert_native.render(p_mode text,p_items jsonb,p_failed text[],p_detail text,p_max integer,p_at timestamptz,p_unchecked jsonb)returns text
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare cap integer;body text;k text;n integer;u integer;head text;x jsonb;
 kinds text[]:=array['MANUAL_REMINDER','FABRIC_BELOW_MINIMUM','ACCESSORY_AT_REORDER_POINT','FG_AT_REORDER_POINT','FABRIC_NEED',
  'PRODUCTION_GAP','AP_DUE','AR_DUE'];
 heads jsonb:='{"MANUAL_REMINDER":"Pengingat","FABRIC_BELOW_MINIMUM":"Stok kain di bawah minimum",'
  '"ACCESSORY_AT_REORDER_POINT":"Stok aksesori menipis","FG_AT_REORDER_POINT":"Stok barang jadi menipis",'
  '"FABRIC_NEED":"Kain perlu dibeli",'
  '"PRODUCTION_GAP":"Kekurangan produksi","AP_DUE":"Tagihan supplier jatuh tempo","AR_DUE":"Piutang pelanggan jatuh tempo"}';
begin
 for cap in reverse p_max..0 loop
  body:=case p_mode when'DIGEST'then'📋 Ringkasan ERP Enteng · '
   else case when not exists(select 1 from jsonb_array_elements(p_items)e where e->>'repeat'<>'true')then'🔁 Masih terbuka · ERP Enteng · 'else'⚠ ERP Enteng · 'end end
   ||cp7_alert_native.label(p_at);
  foreach k in array kinds loop
   n:=(select count(*)from jsonb_array_elements(p_items)e where e->>'kind'=k);
   u:=coalesce((coalesce(p_unchecked,'{}')->>k)::integer,0);
   head:=(heads->>k)||coalesce(' · analisis '||cp7_alert_native.label((select max((e->'detail'->>'data_as_of')::timestamptz)from jsonb_array_elements(p_items)e
    where e->>'kind'=k)),'');
   if k=any(coalesce(p_failed,'{}'))then body:=body||E'\n'||(heads->>k)||': belum bisa dicek ulang, lihat ERP';end if;
   if n=0 and u>0 then body:=body||E'\n'||(heads->>k)||': '||u||' belum dicek ulang, lihat ERP';end if;
   continue when n=0;
   if p_detail='SUMMARY'and k in('AR_DUE','AP_DUE')then
    body:=body||E'\n'||head||': '||n||case k when'AR_DUE'then' nota'else' penerimaan'end||', total '
     ||cp7_alert_native.rp((select sum((e->'detail'->>case k when'AR_DUE'then'open_balance'else'remaining'end)::numeric)::text
      from jsonb_array_elements(p_items)e where e->>'kind'=k));
   elsif cap=0 then body:=body||E'\n'||head||': '||n||case when u>0 then' (+'||u||' belum dicek ulang)'else''end;
   else
    body:=body||E'\n'||head||' ('||n||'):';
    for x in select e from jsonb_array_elements(p_items)e where e->>'kind'=k order by e->>'title',e->>'subject_key'limit cap loop
     body:=body||E'\n- '||cp7_alert_native.item_line(x,p_detail);
    end loop;
    if n>cap or u>0 then body:=body||E'\n- dan '||(greatest(n-cap,0)+u)||' lainnya'||case when u>0 then' (belum dicek ulang)'else''end;end if;
   end if;
  end loop;
  body:=body||E'\nBuka ERP > Reminder';
  if length(body)<=1000 then return body;end if;
 end loop;
 return left(body,1000);
end $$;
create function cp7_alert_native.outbox_items(p_ids bigint[])returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select coalesce(jsonb_agg(case o.item_kind when'ALERT'then
   (select jsonb_build_object('kind',a.kind,'subject_key',a.subject_key,'title',a.title,'detail',a.detail,'party_names',a.party_names,'repeat',o.round>0)
    from cp7_alert_native.alerts a where a.id=o.item_id)
  else(select jsonb_build_object('kind','MANUAL_REMINDER','subject_key',r.id::text,'title',r.title,
    'detail',jsonb_build_object('note',r.note,'due_at',r.due_at,'priority',r.priority),'party_names','[]'::jsonb,'repeat',o.round>0)
   from erp.manual_reminders r where r.id=o.item_id)end order by o.id),'[]')
 from cp7_alert_native.outbox o where o.id=any(p_ids)$$;

-- ----------------------------------------------------- Vault and pg_net --
-- Owned by postgres (the hosted stack's Vault and pg_net user) and executable only by cp7_alert. The key never leaves
-- these functions except as the apikey parameter pg_net sends to the transport address.
create function cp7_alert_native.vault_key_present()returns boolean
language sql stable security definer set search_path=''as $$select exists(select 1 from vault.secrets where name='cp7_callmebot_apikey')$$;
create function cp7_alert_native.vault_key_write(p_key text)returns void
language plpgsql volatile security definer set search_path=''as $$
declare sid uuid;
begin
 if p_key is null or p_key!~'^[A-Za-z0-9_-]{4,64}$'then raise exception using errcode='22023',message='CP7_WA_KEY_FORMAT';end if;
 select id into sid from vault.secrets where name='cp7_callmebot_apikey';
 if sid is null then perform vault.create_secret(p_key,'cp7_callmebot_apikey','CallMeBot key for ERP WhatsApp forwarding; written by the owner, read only by cp7_alert_native.wa_post');
 else perform vault.update_secret(sid,p_key);end if;
end $$;
create function cp7_alert_native.wa_post(p_phone text,p_text text)returns bigint
language plpgsql volatile security definer set search_path=''as $$
declare k text;t record;req bigint;
begin
 if p_phone is null or p_phone!~'^\+[1-9][0-9]{7,14}$'or p_text is null or length(p_text)not between 1 and 1000 then raise exception 'CP7_WA_POST_INPUT';end if;
 select x.base_url,x.timeout_ms into t from cp7_alert_native.transport x where x.id;
 select decrypted_secret into k from vault.decrypted_secrets where name='cp7_callmebot_apikey';
 if k is null then raise exception 'CP7_WA_KEY_MISSING';end if;
 select net.http_get(url:=t.base_url,params:=jsonb_build_object('phone',p_phone,'text',p_text,'apikey',k),timeout_milliseconds:=t.timeout_ms)into req;
 return req;
end $$;
-- The provider's answer to one request, with the key masked out of the text.
create function cp7_alert_native.wa_response(p_id bigint)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare r record;k text;
begin
 select status_code,timed_out,error_msg,left(content,400)content into r from net._http_response where id=p_id;
 if not found then return jsonb_build_object('found',false);end if;
 select decrypted_secret into k from vault.decrypted_secrets where name='cp7_callmebot_apikey';
 return jsonb_build_object('found',true,'status_code',r.status_code,'timed_out',coalesce(r.timed_out,false),
  'error_msg',left(case when k is null then r.error_msg else replace(r.error_msg,k,'***')end,200),
  'content',left(case when k is null then r.content else replace(r.content,k,'***')end,200));
end $$;
alter function cp7_alert_native.vault_key_present()owner to postgres;
alter function cp7_alert_native.vault_key_write(text)owner to postgres;
alter function cp7_alert_native.wa_post(text,text)owner to postgres;
alter function cp7_alert_native.wa_response(bigint)owner to postgres;

-- ----------------------------------------------------------------- sender --
-- A message queued now through pg_net; sent after this transaction commits, never if it rolls back.
create function cp7_alert_native.dispatch(p_kind text,p_slot timestamptz,p_revision bigint,p_phone text,p_body text,p_request uuid)returns bigint
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare d bigint;
begin
 insert into cp7_alert_native.dispatches(kind,digest_slot,settings_revision,body,body_sha256,request_id,status)
 values(p_kind,p_slot,p_revision,p_body,case when p_body is not null then encode(sha256(convert_to(p_body,'UTF8')),'hex')end,p_request,
  case when p_body is null then'NOTHING_DUE'else'QUEUED'end)returning id into d;
 if p_body is not null then update cp7_alert_native.dispatches set net_request_id=cp7_alert_native.wa_post(p_phone,p_body)where id=d;end if;
 return d;
end $$;
-- 200: accepted. Other HTTP status, or a connection that never reached the provider: refused, the items wait again.
-- Timeout, any other transport error, or no answer within 10 minutes: UNKNOWN, never sent again automatically; the owner
-- marks it delivered or not on the screen.
create function cp7_alert_native.reconcile()returns integer
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare d record;r jsonb;st text;n integer:=0;
begin
 for d in select x.id,x.net_request_id,x.queued_at from cp7_alert_native.dispatches x where x.status='QUEUED'order by x.id for update loop
  r:=cp7_alert_native.wa_response(d.net_request_id);
  st:=case when r->>'found'='true'then
    case when(r->>'status_code')::integer=200 then'PROVIDER_ACCEPTED'when r->>'status_code'is not null then'PROVIDER_REFUSED'
     when(r->>'timed_out')::boolean then'UNKNOWN'
     when coalesce(r->>'error_msg','')~*'(resolve host|could not resolve|connect to server|connection refused)'then'TRANSPORT_FAILED'else'UNKNOWN'end
   when d.queued_at<=clock_timestamp()-interval'10 minutes'then'UNKNOWN'end;
  continue when st is null;
  update cp7_alert_native.dispatches set status=st,answered_at=clock_timestamp(),http_status=(r->>'status_code')::integer,
   provider_text=left(coalesce(r->>'content',r->>'error_msg'),200)where id=d.id;
  update cp7_alert_native.outbox set state=case st when'PROVIDER_ACCEPTED'then'ACCEPTED'when'UNKNOWN'then'UNKNOWN'else'PENDING'end,
   dispatch_id=case when st in('PROVIDER_REFUSED','TRANSPORT_FAILED')then null else dispatch_id end,
   settled_at=case when st in('PROVIDER_ACCEPTED','UNKNOWN')then clock_timestamp()end,reason=case when st in('PROVIDER_REFUSED','TRANSPORT_FAILED')then st end
  where dispatch_id=d.id and state='DISPATCHED';
  n:=n+1;
 end loop;
 return n;
end $$;
-- An item delivered (accepted) at least repeat_minutes ago and still open is queued again as the next round.
create function cp7_alert_native.queue_repeats(p_repeat integer)returns integer
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare n integer;
begin
 if p_repeat=0 then return 0;end if;
 insert into cp7_alert_native.outbox(item_kind,item_id,item_episode,round,alert_kind)
 select o.item_kind,o.item_id,o.item_episode,o.round+1,o.alert_kind from cp7_alert_native.outbox o
 where o.state='ACCEPTED'and o.settled_at<=clock_timestamp()-make_interval(mins=>p_repeat)
  and not exists(select 1 from cp7_alert_native.outbox x where x.item_kind=o.item_kind and x.item_id=o.item_id and x.item_episode=o.item_episode and x.round>o.round)
  and((o.item_kind='ALERT'and exists(select 1 from cp7_alert_native.alerts a where a.id=o.item_id and a.state='OPEN'))
   or(o.item_kind='MANUAL_REMINDER'and exists(select 1 from erp.manual_reminders r where r.id=o.item_id and r.status='OPEN'
    and cp7_alert_native.ts_key(r.due_at)=o.item_episode)))
 on conflict(item_kind,item_id,item_episode,round)do nothing;
 get diagnostics n=row_count;
 return n;
end $$;
create function cp7_alert_native.send_tick()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_alert_native.settings;t0 timestamptz:=clock_timestamp();prior jsonb;a jsonb;answered integer;repeats integer;
 slot timestamptz;since timestamptz;check_kinds text[];res jsonb;failed text[];pend bigint[];items jsonb;d bigint;last_at timestamptz;sent_today integer;
 refused_at timestamptz;off text;an jsonb;ok uuid[];
begin
 perform cp7_alert_native.require_tick_limit();
 if not pg_try_advisory_xact_lock(hashtextextended('CP7:WA:SEND',0))then return jsonb_build_object('ran',false,'outcome','BUSY');end if;
 answered:=cp7_alert_native.reconcile();
 s:=cp7_alert_native.current_settings();
 off:=case when s.revision is null then'NOT_CONFIGURED'when not s.enabled then'WA_OFF'when s.phone_e164 is null then'PHONE_MISSING'
  when not cp7_alert_native.vault_key_present()then'KEY_MISSING'end;
 if off is not null then
  update cp7_alert_native.outbox set state='DISABLED',reason=off,settled_at=t0 where state in('PENDING','HELD_QUIET');
  return cp7_alert_native.record_tick('SEND',jsonb_build_object('ran',false,'outcome',off,'answered',answered));
 end if;
 prior:=cp7_alert_native.claims_enter(s.actor);
 a:=cp7_alert_native.owner_access(s.actor_user_id);
 if a is null then
  perform cp7_alert_native.claims_leave(prior);
  return cp7_alert_native.record_tick('SEND',jsonb_build_object('ran',false,'outcome','OWNER_ACCESS_DENIED','answered',answered));
 end if;
 repeats:=cp7_alert_native.queue_repeats(s.repeat_minutes);
 update cp7_alert_native.outbox set state='KIND_OFF',reason='KIND_OFF',settled_at=t0 where state in('PENDING','HELD_QUIET')and not(alert_kind=any(s.kinds));
 if cp7_alert_native.in_quiet(s.quiet_enabled,s.quiet_start,s.quiet_end,t0)then
  update cp7_alert_native.outbox set state='HELD_QUIET'where state='PENDING';
  perform cp7_alert_native.claims_leave(prior);
  return cp7_alert_native.record_tick('SEND',jsonb_build_object('ran',true,'outcome','HELD_QUIET','answered',answered,'repeats',repeats));
 end if;
 -- The latest digest time of today (WIB) not yet handled, within the last hour and since WhatsApp was switched on.
 select min(x.saved_at)into since from cp7_alert_native.settings x
 where x.revision>coalesce((select max(y.revision)from cp7_alert_native.settings y where not y.enabled),0);
 select max(z.slot)into slot from(select((t0 at time zone'Asia/Jakarta')::date+t::time)at time zone'Asia/Jakarta'slot from unnest(s.digest_times)t)z
 where z.slot<=t0 and z.slot>t0-interval'60 minutes'and z.slot>=since;
 if slot is not null and exists(select 1 from cp7_alert_native.dispatches x where x.kind='DIGEST'and x.digest_slot=slot)then slot:=null;end if;
 -- Every waiting item is checked against its source now; the digest checks every kind it lists.
 check_kinds:=case when slot is not null then s.kinds else
  (select array_agg(distinct o.alert_kind)from cp7_alert_native.outbox o where o.state in('PENDING','HELD_QUIET')and o.item_kind='ALERT')end;
 res:=cp7_alert_native.collect_kinds(coalesce(check_kinds,'{}'));
 select array_agg(k)into failed from jsonb_each(res)e(k,v)where v?'error';
 -- Analysis items are checked one condition at a time within the tick's budget (all open ones for a digest, in order of
 -- opening); what is not reached waits for the next tick and is never sent unchecked.
 an:=cp7_alert_native.analysis_recheck(case when slot is not null then
   array(select a2.id from cp7_alert_native.alerts a2 where a2.state='OPEN'and a2.kind in('PRODUCTION_GAP','FABRIC_NEED')and a2.kind=any(s.kinds)
    order by a2.kind,a2.opened_at,a2.id)
  else array(select o.item_id from cp7_alert_native.outbox o where o.state in('PENDING','HELD_QUIET')and o.alert_kind in('PRODUCTION_GAP','FABRIC_NEED')
   group by o.item_id order by min(o.id))end,
  t0+interval'5 seconds',case when slot is not null then s.max_items else 20 end);
 ok:=array(select jsonb_array_elements_text(an->'ok')::uuid);
 failed:=nullif(array(select distinct f from unnest(coalesce(failed,'{}')||array(select jsonb_array_elements_text(an->'failed')))f order by 1),'{}');
 update cp7_alert_native.outbox o set state='RESOLVED_BEFORE_SEND',reason=a2.resolution,settled_at=t0 from cp7_alert_native.alerts a2
 where o.item_kind='ALERT'and a2.id=o.item_id and a2.state<>'OPEN'and o.state in('PENDING','HELD_QUIET');
 update cp7_alert_native.outbox o set state='RESOLVED_BEFORE_SEND',settled_at=t0,
  reason=case when r.id is null then'REMINDER_MISSING'when r.owner_user_id<>s.actor_user_id then'REMINDER_NOT_OWNER'
   when r.status='DONE'then'REMINDER_DONE'when r.status='CANCELLED'then'REMINDER_CANCELLED'else'REMINDER_RESCHEDULED'end
 from cp7_alert_native.outbox o2 left join erp.manual_reminders r on r.id=o2.item_id
 where o.id=o2.id and o.item_kind='MANUAL_REMINDER'and o.state in('PENDING','HELD_QUIET')
  and(r.id is null or r.owner_user_id<>s.actor_user_id or r.status<>'OPEN'or cp7_alert_native.ts_key(r.due_at)<>o.item_episode);
 if erp.get_my_access_v1()is distinct from a then raise exception using errcode='42501',message='CP7_ALERT_ACCESS_CHANGED_DURING_TICK';end if;
 perform cp7_alert_native.claims_leave(prior);
 select array_agg(o.id order by o.id)into pend from cp7_alert_native.outbox o
 where o.state in('PENDING','HELD_QUIET')and(o.item_kind='MANUAL_REMINDER'or not(o.alert_kind=any(coalesce(failed,'{}'))))
  and(o.alert_kind not in('PRODUCTION_GAP','FABRIC_NEED')or o.item_id=any(ok));
 if slot is not null then
  select coalesce(jsonb_agg(i order by i->>'kind',i->>'title'),'[]')into items from(
   select jsonb_build_object('kind',x.kind,'subject_key',x.subject_key,'title',x.title,'detail',x.detail,'party_names',x.party_names,'repeat',false)i
   from cp7_alert_native.alerts x where x.state='OPEN'and x.kind=any(s.kinds)and not(x.kind=any(coalesce(failed,'{}')))
    and(x.kind not in('PRODUCTION_GAP','FABRIC_NEED')or x.id=any(ok))
   union all
   select jsonb_build_object('kind','MANUAL_REMINDER','subject_key',r.id::text,'title',r.title,'detail',jsonb_build_object('note',r.note,'due_at',r.due_at),
    'party_names','[]'::jsonb,'repeat',false)
   from erp.manual_reminders r where'MANUAL_REMINDER'=any(s.kinds)and r.owner_user_id=s.actor_user_id and r.status='OPEN'and r.due_at<=t0)q;
  d:=cp7_alert_native.dispatch('DIGEST',slot,s.revision,s.phone_e164,
   case when jsonb_array_length(items)>0 or failed is not null or an->'unchecked'<>'{}'::jsonb
    then cp7_alert_native.render('DIGEST',items,failed,s.detail,s.max_items,t0,an->'unchecked')end,null);
  if pend is not null and exists(select 1 from cp7_alert_native.dispatches x where x.id=d and x.status='QUEUED')then
   update cp7_alert_native.outbox set state='DISPATCHED',dispatch_id=d,attempts=attempts+1 where id=any(pend);
   insert into cp7_alert_native.dispatch_items select d,unnest(pend);
  end if;
  return cp7_alert_native.record_tick('SEND',jsonb_build_object('ran',true,'outcome','DIGEST','dispatch_id',d,'slot',slot,'items',jsonb_array_length(items),
   'covered',coalesce(cardinality(pend),0),'failed',failed,'answered',answered,'repeats',repeats,'analysis',an-'ok'));
 end if;
 if pend is null then return cp7_alert_native.record_tick('SEND',jsonb_build_object('ran',true,'outcome','IDLE','failed',failed,'answered',answered,'repeats',repeats,
  'analysis',an-'ok'));end if;
 -- At most one message a minute; after burst_after_per_day messages in a WIB day, one per burst_merge_minutes; after a
 -- refusal, five minutes' rest.
 select max(x.queued_at),count(*)filter(where x.kind='INSTANT'and(x.queued_at at time zone'Asia/Jakarta')::date=(t0 at time zone'Asia/Jakarta')::date
  and x.status not in('PROVIDER_REFUSED','TRANSPORT_FAILED')),max(x.answered_at)filter(where x.status in('PROVIDER_REFUSED','TRANSPORT_FAILED'))
 into last_at,sent_today,refused_at from cp7_alert_native.dispatches x where x.kind in('INSTANT','DIGEST')and x.status<>'NOTHING_DUE';
 if last_at>t0-interval'55 seconds'or refused_at>t0-interval'5 minutes'
  or(sent_today>=s.burst_after_per_day and last_at>t0-make_interval(mins=>s.burst_merge_minutes))then
  return cp7_alert_native.record_tick('SEND',jsonb_build_object('ran',true,'outcome','WAITING','waiting',cardinality(pend),'sent_today',sent_today,
   'failed',failed,'answered',answered,'repeats',repeats,'analysis',an-'ok'));
 end if;
 items:=cp7_alert_native.outbox_items(pend);
 d:=cp7_alert_native.dispatch('INSTANT',null,s.revision,s.phone_e164,cp7_alert_native.render('INSTANT',items,null,s.detail,s.max_items,t0,'{}'),null);
 update cp7_alert_native.outbox set state='DISPATCHED',dispatch_id=d,attempts=attempts+1 where id=any(pend);
 insert into cp7_alert_native.dispatch_items select d,unnest(pend);
 return cp7_alert_native.record_tick('SEND',jsonb_build_object('ran',true,'outcome','SENT','dispatch_id',d,'items',cardinality(pend),'failed',failed,
  'answered',answered,'repeats',repeats,'analysis',an-'ok'));
end $$;
create function cp7_alert_native.schedules()returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_array(
  jsonb_build_object('name','erp-wa-collect','schedule','* * * * *','command','set statement_timeout to ''8s''; select cp7_alert_native.collect_tick()',
   'timezone','UTC','meaning','every minute: system reminders opened and closed from their sources, owner reminders whose time has come queued'),
  jsonb_build_object('name','erp-wa-send','schedule','* * * * *','command','set statement_timeout to ''8s''; select cp7_alert_native.send_tick()',
   'timezone','UTC','meaning','every minute: answers read, waiting items checked again, at most one WhatsApp message'),
  jsonb_build_object('name','erp-wa-analysis','schedule','* * * * *',
   'command','set statement_timeout to ''8s''; '||rtrim(repeat('begin; select cp7_alert_native.analysis_tick(); commit; ',6)),
   'timezone','UTC','meaning','every minute: up to 6 units, each in its own transaction under the 8 s limit: the owner''s latest analysis '
    ||'checked condition by condition, and the automatic analysis asked for when due'))
$$;

-- --------------------------------------------------------------- the RPCs --
create function cp7_alert_native.require_owner()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb:=cp7_alert_native.owner_access(null);
begin
 if a is null then raise exception using errcode='42501',message='CP7_WA_OWNER_ONLY';end if;
 return a;
end $$;
create function cp7_alert_native.defaults()returns jsonb
language sql immutable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('revision',0,'enabled',false,'phone_e164',null,'detail','SUMMARY','digest_times',jsonb_build_array('08:00','15:00'),
  'kinds',jsonb_build_array('MANUAL_REMINDER','FABRIC_BELOW_MINIMUM','ACCESSORY_AT_REORDER_POINT','FG_AT_REORDER_POINT','AR_DUE',
   'AP_DUE','PRODUCTION_GAP','FABRIC_NEED'),'repeat_minutes',1440,'burst_after_per_day',30,
  'burst_merge_minutes',30,'max_items',10,'quiet_enabled',true,'quiet_start','21:00','quiet_end','06:00','analysis_every_minutes',240,
  'analysis_start','07:00','analysis_end','20:00')$$;
create function cp7_alert_native.settings_json(s cp7_alert_native.settings)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select case when s.revision is null then cp7_alert_native.defaults()else jsonb_build_object('revision',s.revision,'enabled',s.enabled,
  'phone_e164',s.phone_e164,'detail',s.detail,'digest_times',to_jsonb(s.digest_times),'kinds',to_jsonb(s.kinds),'repeat_minutes',s.repeat_minutes,
  'burst_after_per_day',s.burst_after_per_day,'burst_merge_minutes',s.burst_merge_minutes,'max_items',s.max_items,'quiet_enabled',s.quiet_enabled,
  'quiet_start',to_char(s.quiet_start,'HH24:MI'),'quiet_end',to_char(s.quiet_end,'HH24:MI'),'analysis_every_minutes',s.analysis_every_minutes,
  'analysis_start',to_char(s.analysis_start,'HH24:MI'),'analysis_end',to_char(s.analysis_end,'HH24:MI'),'saved_at',s.saved_at)end$$;
-- Where the analysis kinds stand: the latest run worked through, the latest automatic request, the last analysis tick.
create function cp7_alert_native.analysis_status()returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object(
  'run',(select jsonb_build_object('run_id',r.run_id,'data_as_of',r.data_as_of,'phase',r.phase,'rule',r.rule,'next_offset',r.next_offset,'checked',r.checked,
    'still_open',r.still_open,'closed',r.closed,'rule_off',r.rule_off,'error',r.error,'started_at',r.started_at,'updated_at',r.updated_at,'finished_at',r.finished_at)
   from cp7_alert_native.analysis_runs r order by r.started_at desc,r.run_id desc limit 1),
  'request',(select jsonb_build_object('request_id',q.request_id,'state',q.state,'query',q.query,'freshness',q.freshness,'created_at',q.created_at,
    'requested_at',q.requested_at,'error',q.error)from cp7_alert_native.analysis_requests q order by q.created_at desc,q.request_id desc limit 1),
  'tick',(select jsonb_build_object('at',t.at,'outcome',t.outcome->>'outcome')from cp7_alert_native.ticks t where t.job='ANALYSIS'))$$;
-- Pengingat sistem for the Reminder menu: each kind only for a user who may read its source screen.
create function cp7_alert_native.alerts_read(p jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;keep_days integer;vis text[];is_owner boolean;s cp7_alert_native.settings:=cp7_alert_native.current_settings();
begin
 if cp7_alert_native.uid()is null or coalesce(cp7_alert_native.jwt()->>'role','')<>'authenticated'then raise exception using errcode='42501',message='CP7_ALERTS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb then raise exception using errcode='42501',message='CP7_ALERTS_DENIED';end if;
 if jsonb_typeof(p)is distinct from'object'or exists(select 1 from jsonb_object_keys(p)k where k<>'resolved_days')
  or(p?'resolved_days'and(jsonb_typeof(p->'resolved_days')<>'number'or(p->>'resolved_days')!~'^([0-9]|[12][0-9]|30)$'))then
  raise exception 'CP7_ALERTS_QUERY';end if;
 keep_days:=coalesce((p->>'resolved_days')::integer,7);
 is_owner:=a->'profile'->>'role_code'='OWNER';
 vis:=array_remove(array[case when erp.has_permission('warehouse.material.view')and erp.has_permission('master.fabric.view')then'FABRIC_BELOW_MINIMUM'end,
  case when erp.has_permission('warehouse.accessory.view')then'ACCESSORY_AT_REORDER_POINT'end,
  case when erp.has_permission('warehouse.fg.view')then'FG_AT_REORDER_POINT'end,
  case when erp.has_permission('finance.ar.view')then'AR_DUE'end,case when erp.has_permission('finance.ap.view')then'AP_DUE'end]
  ||case when erp.has_permission('master.product.view')and erp.has_permission('production.wip.view')and erp.has_permission('warehouse.stock.view')
   and erp.has_permission('sales.invoice.view')then array['PRODUCTION_GAP','FABRIC_NEED']else'{}'::text[]end,null);
 return jsonb_build_object('contract_version','cp7.system-alerts.v1','read_at',statement_timestamp(),'configured',s.revision is not null,
  'collector',(select jsonb_build_object('at',t.at,'outcome',t.outcome->>'outcome')from cp7_alert_native.ticks t where t.job='COLLECT'),
  'analysis',case when'PRODUCTION_GAP'=any(vis)then cp7_alert_native.analysis_status()end,
  'kinds',coalesce((select jsonb_agg(jsonb_build_object('kind',k,'last_try_at',st.last_try_at,'last_ok_at',st.last_ok_at,'last_error',st.last_error,
    'open_count',st.open_count)order by k)from unnest(vis)k left join cp7_alert_native.source_state st on st.kind=k),'[]'),
  'rows',coalesce((select jsonb_agg(jsonb_build_object('id',x.id,'kind',x.kind,'subject_key',x.subject_key,'episode',x.episode,'title',x.title,
    'detail',x.detail,'party_names',x.party_names,'state',x.state,'opened_at',x.opened_at,'refreshed_at',x.refreshed_at,'resolved_at',x.resolved_at,
    'resolution',x.resolution,'wa',case when is_owner then(select jsonb_build_object('state',o.state,'round',o.round,'reason',o.reason,'dispatch_id',o.dispatch_id,
      'dispatch_status',(select d.status from cp7_alert_native.dispatches d where d.id=o.dispatch_id),'settled_at',o.settled_at)
     from cp7_alert_native.outbox o where o.item_kind='ALERT'and o.item_id=x.id order by o.round desc limit 1)end)
    order by x.state desc,x.opened_at desc,x.id)
   from(select*from cp7_alert_native.alerts y where y.kind=any(vis)and(y.state='OPEN'or y.resolved_at>=statement_timestamp()-make_interval(days=>keep_days))
    order by y.state desc,y.opened_at desc,y.id limit 500)x),'[]'));
end $$;
create function cp7_alert_native.wa_settings_read()returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_alert_native.settings;t0 timestamptz:=clock_timestamp();
begin
 perform cp7_alert_native.require_owner();
 perform cp7_alert_native.reconcile();
 s:=cp7_alert_native.current_settings();
 return jsonb_build_object('contract_version','cp7.wa-settings.v1','read_at',t0,'settings',cp7_alert_native.settings_json(s),
  'defaults',cp7_alert_native.defaults(),'key_present',cp7_alert_native.vault_key_present(),
  'key_set_at',(select max(e.at)from cp7_alert_native.key_events e),
  'transport_is_callmebot',(select t.base_url='https://api.callmebot.com/whatsapp.php'from cp7_alert_native.transport t),
  'quiet_now',coalesce(cp7_alert_native.in_quiet(s.quiet_enabled,s.quiet_start,s.quiet_end,t0),false),'analysis',cp7_alert_native.analysis_status(),
  'ticks',coalesce((select jsonb_object_agg(t.job,jsonb_build_object('at',t.at,'outcome',t.outcome->>'outcome'))from cp7_alert_native.ticks t),'{}'),
  'outbox',coalesce((select jsonb_object_agg(q.state,q.n)from(select o.state,count(*)n from cp7_alert_native.outbox o group by o.state)q),'{}'),
  'dispatches',coalesce((select jsonb_agg(jsonb_build_object('id',d.id,'kind',d.kind,'status',d.status,'queued_at',d.queued_at,'answered_at',d.answered_at,
    'http_status',d.http_status,'provider_text',d.provider_text,'body',d.body,'digest_slot',d.digest_slot,'resolved_outcome',d.resolved_outcome,
    'resolved_at',d.resolved_at,'items',(select count(*)from cp7_alert_native.dispatch_items i where i.dispatch_id=d.id))order by d.id desc)
   from(select*from cp7_alert_native.dispatches x order by x.id desc limit 30)d),'[]'));
end $$;
create function cp7_alert_native.wa_settings_save(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;cur cp7_alert_native.settings;prev cp7_alert_native.settings;fields text[]:=array['expected_revision','enabled','phone_e164','detail','digest_times','kinds',
 'repeat_minutes','burst_after_per_day','burst_merge_minutes','max_items','quiet_enabled','quiet_start','quiet_end','analysis_every_minutes',
 'analysis_start','analysis_end'];times text[];kinds text[];qs time;qe time;
begin
 a:=cp7_alert_native.require_owner();
 if p_request is null then raise exception 'CP7_WA_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:WA:SETTINGS',0));
 select*into prev from cp7_alert_native.settings x where x.request_id=p_request;
 if found then
  if prev.actor<>cp7_alert_native.uid()or prev.request_hash<>encode(sha256(convert_to(coalesce(p::text,''),'UTF8')),'hex')then
   raise exception using errcode='22023',message='CP7_WA_REQUEST_REUSED';end if;
  return jsonb_build_object('replay',true,'settings',cp7_alert_native.settings_json(prev));
 end if;
 if jsonb_typeof(p)is distinct from'object'or not p?&fields or exists(select 1 from jsonb_object_keys(p)k where not k=any(fields))
  or jsonb_typeof(p->'expected_revision')<>'number'or(p->>'expected_revision')!~'^[0-9]{1,18}$'
  or jsonb_typeof(p->'enabled')<>'boolean'or jsonb_typeof(p->'quiet_enabled')<>'boolean'
  or jsonb_typeof(p->'phone_e164')not in('string','null')or coalesce(p->>'phone_e164','+10000000')!~'^\+[1-9][0-9]{7,14}$'
  or p->>'detail'is null or p->>'detail'not in('SUMMARY','DETAILED')
  or jsonb_typeof(p->'digest_times')<>'array'or jsonb_array_length(p->'digest_times')>4
  or exists(select 1 from jsonb_array_elements(p->'digest_times')e where jsonb_typeof(e)<>'string'or e#>>'{}'!~'^([01][0-9]|2[0-3]):[0-5][0-9]$')
  or jsonb_typeof(p->'kinds')<>'array'
  or exists(select 1 from jsonb_array_elements(p->'kinds')e where jsonb_typeof(e)<>'string'
   or e#>>'{}'not in('MANUAL_REMINDER','FABRIC_BELOW_MINIMUM','ACCESSORY_AT_REORDER_POINT','FG_AT_REORDER_POINT','AR_DUE','AP_DUE',
    'PRODUCTION_GAP','FABRIC_NEED'))
  or exists(select 1 from(values('repeat_minutes'),('burst_after_per_day'),('burst_merge_minutes'),('max_items'),('analysis_every_minutes'))v(k)
   where jsonb_typeof(p->v.k)<>'number'or(p->>v.k)!~'^[0-9]{1,5}$')
  or exists(select 1 from(values('quiet_start'),('quiet_end'),('analysis_start'),('analysis_end'))v(k)
   where jsonb_typeof(p->v.k)<>'string'or(p->>v.k)!~'^([01][0-9]|2[0-3]):[0-5][0-9]$')
 then raise exception using errcode='22023',message='CP7_WA_SETTINGS_INVALID';end if;
 if((p->>'repeat_minutes')::integer<>0 and(p->>'repeat_minutes')::integer not between 60 and 10080)
  or(p->>'burst_after_per_day')::integer not between 1 and 200 or(p->>'burst_merge_minutes')::integer not between 5 and 240
  or(p->>'max_items')::integer not between 1 and 20
  or((p->>'analysis_every_minutes')::integer<>0 and(p->>'analysis_every_minutes')::integer not between 15 and 1440)
  or p->>'quiet_start'=p->>'quiet_end'or(p->>'analysis_start')::time>=(p->>'analysis_end')::time
 then raise exception using errcode='22023',message='CP7_WA_SETTINGS_INVALID';end if;
 select array_agg(distinct e#>>'{}'order by e#>>'{}')into times from jsonb_array_elements(p->'digest_times')e;
 select array_agg(distinct e#>>'{}'order by e#>>'{}')into kinds from jsonb_array_elements(p->'kinds')e;
 if coalesce(cardinality(times),0)<>jsonb_array_length(p->'digest_times')or coalesce(cardinality(kinds),0)<>jsonb_array_length(p->'kinds')then
  raise exception using errcode='22023',message='CP7_WA_SETTINGS_DUPLICATE';end if;
 qs:=(p->>'quiet_start')::time;qe:=(p->>'quiet_end')::time;
 if(p->>'quiet_enabled')::boolean and exists(select 1 from unnest(coalesce(times,'{}'))t
  where case when qs<qe then t::time>=qs and t::time<qe else t::time>=qs or t::time<qe end)then
  raise exception using errcode='22023',message='CP7_WA_DIGEST_IN_QUIET_HOURS';end if;
 cur:=cp7_alert_native.current_settings();
 if coalesce(cur.revision,0)<>(p->>'expected_revision')::bigint then raise exception using errcode='40001',message='CP7_WA_SETTINGS_STALE';end if;
 if(p->>'enabled')::boolean and(p->>'phone_e164'is null or not cp7_alert_native.vault_key_present())then
  raise exception using errcode='22023',message='CP7_WA_ENABLE_NEEDS_PHONE_AND_KEY';end if;
 insert into cp7_alert_native.settings(revision,enabled,phone_e164,detail,digest_times,kinds,repeat_minutes,burst_after_per_day,burst_merge_minutes,
  max_items,quiet_enabled,quiet_start,quiet_end,analysis_every_minutes,analysis_start,analysis_end,actor,actor_user_id,request_id,request_hash)
 values(coalesce(cur.revision,0)+1,(p->>'enabled')::boolean,p->>'phone_e164',p->>'detail',coalesce(times,'{}'),coalesce(kinds,'{}'),
  (p->>'repeat_minutes')::integer,(p->>'burst_after_per_day')::integer,(p->>'burst_merge_minutes')::integer,(p->>'max_items')::integer,
  (p->>'quiet_enabled')::boolean,qs,qe,(p->>'analysis_every_minutes')::integer,(p->>'analysis_start')::time,(p->>'analysis_end')::time,
  cp7_alert_native.uid(),(a->'profile'->>'id')::uuid,p_request,encode(sha256(convert_to(p::text,'UTF8')),'hex'))returning*into cur;
 return jsonb_build_object('replay',false,'settings',cp7_alert_native.settings_json(cur));
end $$;
create function cp7_alert_native.wa_key_set(p_key text,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare e cp7_alert_native.key_events;
begin
 perform cp7_alert_native.require_owner();
 if p_request is null then raise exception 'CP7_WA_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:WA:SETTINGS',0));
 select*into e from cp7_alert_native.key_events x where x.request_id=p_request;
 if found then
  if e.actor<>cp7_alert_native.uid()then raise exception using errcode='22023',message='CP7_WA_REQUEST_REUSED';end if;
  return jsonb_build_object('replay',true,'key_present',cp7_alert_native.vault_key_present(),'key_set_at',e.at);
 end if;
 perform cp7_alert_native.vault_key_write(p_key);
 insert into cp7_alert_native.key_events(actor,request_id,action)values(cp7_alert_native.uid(),p_request,'SET')returning*into e;
 return jsonb_build_object('replay',false,'key_present',true,'key_set_at',e.at);
end $$;
create function cp7_alert_native.wa_test(p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare s cp7_alert_native.settings;d cp7_alert_native.dispatches;new_id bigint;
begin
 perform cp7_alert_native.require_owner();
 if p_request is null then raise exception 'CP7_WA_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:WA:TEST',0));
 select*into d from cp7_alert_native.dispatches x where x.request_id=p_request;
 if found then return jsonb_build_object('replay',true,'dispatch_id',d.id,'status',d.status);end if;
 s:=cp7_alert_native.current_settings();
 if s.phone_e164 is null then raise exception using errcode='22023',message='CP7_WA_PHONE_MISSING';end if;
 if not cp7_alert_native.vault_key_present()then raise exception using errcode='22023',message='CP7_WA_KEY_MISSING';end if;
 if(select count(*)from cp7_alert_native.dispatches x where x.kind='TEST'and x.queued_at>clock_timestamp()-interval'1 hour')>=3 then
  raise exception using errcode='22023',message='CP7_WA_TEST_LIMIT';end if;
 new_id:=cp7_alert_native.dispatch('TEST',null,s.revision,s.phone_e164,
  '✅ Pesan uji ERP Enteng · '||cp7_alert_native.label(clock_timestamp())||'. Kalau pesan ini masuk, sambungan WhatsApp sudah benar.',p_request);
 return jsonb_build_object('replay',false,'dispatch_id',new_id,'status','QUEUED');
end $$;
-- The owner says whether a message whose fate is UNKNOWN reached the phone: delivered (its items count as sent) or not
-- (its items wait again).
create function cp7_alert_native.wa_resolve(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare d cp7_alert_native.dispatches;outcome text;
begin
 perform cp7_alert_native.require_owner();
 if p_request is null then raise exception 'CP7_WA_REQUEST_REQUIRED';end if;
 select*into d from cp7_alert_native.dispatches x where x.resolve_request=p_request;
 if found then
  if d.resolved_by<>cp7_alert_native.uid()or d.id::text is distinct from p->>'dispatch_id'or d.resolved_outcome is distinct from p->>'outcome'then
   raise exception using errcode='22023',message='CP7_WA_REQUEST_REUSED';end if;
  return jsonb_build_object('replay',true,'dispatch_id',d.id,'resolved_outcome',d.resolved_outcome);
 end if;
 if jsonb_typeof(p)is distinct from'object'or not p?&array['dispatch_id','outcome']or exists(select 1 from jsonb_object_keys(p)k where k not in('dispatch_id','outcome'))
  or jsonb_typeof(p->'dispatch_id')<>'number'or(p->>'dispatch_id')!~'^[1-9][0-9]{0,18}$'or p->>'outcome'is null or p->>'outcome'not in('DELIVERED','NOT_DELIVERED')
 then raise exception using errcode='22023',message='CP7_WA_RESOLVE_INVALID';end if;
 outcome:=p->>'outcome';
 select*into d from cp7_alert_native.dispatches x where x.id=(p->>'dispatch_id')::bigint for update;
 if not found or d.status<>'UNKNOWN'or d.resolved_outcome is not null then raise exception using errcode='22023',message='CP7_WA_RESOLVE_NOT_UNKNOWN';end if;
 update cp7_alert_native.dispatches set resolved_outcome=outcome,resolved_by=cp7_alert_native.uid(),resolved_at=clock_timestamp(),resolve_request=p_request where id=d.id;
 update cp7_alert_native.outbox set state=case when outcome='DELIVERED'then'ACCEPTED'else'PENDING'end,
  dispatch_id=case when outcome='DELIVERED'then dispatch_id end,settled_at=case when outcome='DELIVERED'then settled_at end,
  reason=case when outcome='NOT_DELIVERED'then'OWNER_NOT_DELIVERED'end
 where dispatch_id=d.id and state='UNKNOWN';
 return jsonb_build_object('replay',false,'dispatch_id',d.id,'resolved_outcome',outcome);
end $$;

-- -------------------------------------------------------------- ownership --
revoke all on all functions in schema cp7_alert_native from public,anon,authenticated,service_role;
do $$declare r record;begin
 for r in select p.oid::regprocedure sig from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='cp7_alert_native'and p.proname not in('vault_key_present','vault_key_write','wa_post','wa_response')loop
  execute format('alter function %s owner to cp7_alert',r.sig);
 end loop;
 for r in select c.oid::regclass t from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='cp7_alert_native'and c.relkind='r'and c.relname<>'transport'loop
  execute format('alter table %s owner to cp7_alert',r.t);
 end loop;
end $$;
revoke all on all functions in schema cp7_alert_native from public,anon,authenticated,service_role;
grant execute on function cp7_alert_native.vault_key_present(),cp7_alert_native.vault_key_write(text),cp7_alert_native.wa_post(text,text),
 cp7_alert_native.wa_response(bigint)to cp7_alert;
grant execute on function cp7_alert_native.collect_tick(),cp7_alert_native.send_tick(),cp7_alert_native.analysis_tick(),cp7_alert_native.schedules()to postgres;
grant create on schema public to cp7_alert;
create function public.erp_cp7_get_alerts_v1(p jsonb)returns jsonb
language sql stable security definer set search_path=''as $$select cp7_alert_native.alerts_read(p)$$;
create function public.erp_cp7_get_wa_settings_v1()returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_alert_native.wa_settings_read()$$;
create function public.erp_cp7_save_wa_settings_v1(p jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_alert_native.wa_settings_save(p,p_request)$$;
create function public.erp_cp7_set_wa_key_v1(p_key text,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_alert_native.wa_key_set(p_key,p_request)$$;
create function public.erp_cp7_send_wa_test_v1(p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_alert_native.wa_test(p_request)$$;
create function public.erp_cp7_resolve_wa_dispatch_v1(p jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_alert_native.wa_resolve(p,p_request)$$;
do $$declare sig text;begin
 foreach sig in array array['public.erp_cp7_get_alerts_v1(jsonb)','public.erp_cp7_get_wa_settings_v1()','public.erp_cp7_save_wa_settings_v1(jsonb,uuid)',
  'public.erp_cp7_set_wa_key_v1(text,uuid)','public.erp_cp7_send_wa_test_v1(uuid)','public.erp_cp7_resolve_wa_dispatch_v1(jsonb,uuid)']loop
  execute format('alter function %s owner to cp7_alert',sig);
  execute format('revoke all on function %s from public,anon,authenticated,service_role,cp7_capture',sig);
  execute format('grant execute on function %s to authenticated',sig);
 end loop;end $$;
revoke create on schema public from cp7_alert;
