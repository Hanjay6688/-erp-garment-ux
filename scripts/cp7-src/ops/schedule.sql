-- ------------------------------------------------- CP7C server schedule --
-- Owner decision 9 Oct 2026 WIB: the cleanup of finished analyses and the 7-day
-- purge run on the server's own schedule (pg_cron), and the database is backed
-- up every night (outside the database: scripts/cp7_nightly_backup.py). This
-- file only defines the scheduled entries; registering them with pg_cron on a
-- real database is the installation step (scripts/cp7_schedule.py) and waits
-- for the audit and the owner's installation permission.
--
-- pg_cron runs in UTC. The agreed jobs:
--   cp7-staged-cleanup    every 5 minutes      cleanup_tick: up to 5 DONE runs whose final
--                                             result verifies lose their temporary work
--   cp7-staged-retention  19:30 UTC = 02:30 WIB retention_tick: expired runs (7 days) purged
-- Each entry is SECURITY DEFINER as cp7_capture (the owner of the staged
-- tables) and executable only by the scheduler's role postgres; anon,
-- authenticated and service_role cannot call it. Both are safe to repeat: a
-- run cleaned or purged once is logged and never touched again, a running job
-- is never selected, and a failed cleanup changes nothing and is retried.
create schema cp7_ops authorization cp7_capture;
revoke all on schema cp7_ops from public,anon,authenticated,service_role;
create function cp7_ops.schedules()returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_array(
  jsonb_build_object('name','cp7-staged-cleanup','schedule','*/5 * * * *','command','select cp7_ops.cleanup_tick()',
   'timezone','UTC','meaning','every 5 minutes'),
  jsonb_build_object('name','cp7-staged-retention','schedule','30 19 * * *','command','select cp7_ops.retention_tick()',
   'timezone','UTC','meaning','02:30 WIB daily'))
$$;
create function cp7_ops.cleanup_tick()returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_analysis_stage.clean_pending(5)||jsonb_build_object('tick','cp7-staged-cleanup','at',clock_timestamp())
$$;
create function cp7_ops.retention_tick()returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_analysis_stage.purge_expired(200)||jsonb_build_object('tick','cp7-staged-retention','at',clock_timestamp())
$$;
alter function cp7_ops.schedules()owner to cp7_capture;
alter function cp7_ops.cleanup_tick()owner to cp7_capture;
alter function cp7_ops.retention_tick()owner to cp7_capture;
revoke all on all functions in schema cp7_ops from public,anon,authenticated,service_role;
grant usage on schema cp7_ops to postgres;
grant execute on function cp7_ops.schedules(),cp7_ops.cleanup_tick(),cp7_ops.retention_tick()to postgres;
