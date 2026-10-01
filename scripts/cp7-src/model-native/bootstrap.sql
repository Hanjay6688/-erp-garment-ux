-- Prospective model registry and immutable evaluations. No business DML.
create schema cp7_model_native authorization cp7_capture;
revoke all on schema cp7_model_native from public,anon,authenticated,service_role;
create table cp7_model_native.registry(
 id text primary key,registered_at timestamptz not null,configuration jsonb not null);
create table cp7_model_native.runs(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,
 query jsonb not null,history_run_id uuid not null references cp7_planning.history_runs(id),
 captured_at timestamptz not null,registry_id text not null references cp7_model_native.registry(id),
 input jsonb not null,result jsonb not null,dependency_hash text not null,
 unique(actor,request_id));
alter table cp7_model_native.registry owner to cp7_capture;
alter table cp7_model_native.runs owner to cp7_capture;
alter table cp7_model_native.registry enable row level security;
alter table cp7_model_native.runs enable row level security;
create policy model_registry_private on cp7_model_native.registry for all to public using(false)with check(false);
create policy model_run_private on cp7_model_native.runs for all to public using(false)with check(false);
revoke all on all tables in schema cp7_model_native from public,anon,authenticated,service_role;
create trigger model_registry_immutable before update or delete on cp7_model_native.registry for each row execute function cp7_private.immutable_run();
create trigger model_run_immutable before update or delete on cp7_model_native.runs for each row execute function cp7_private.immutable_run();
create index model_history_actor_capture on cp7_planning.history_runs(actor,captured_at,id);
insert into cp7_model_native.registry values('cp7.native-model-policy.v1',clock_timestamp(),
 '{"baseline":{"id":"mean-1","method":"MEAN","params":{}},"challengers":[{"id":"naive-1","method":"NAIVE","params":{}},{"id":"moving-mean-7-1","method":"MOVING_MEAN","params":{"window":"7"}},{"id":"ses-half-1","method":"SES","params":{"alpha":"0.5","initial_level":null}},{"id":"holt-damped-1","method":"DAMPED_HOLT","params":{"alpha":"0.5","beta":"0.5","phi":"0.9","initial_level":null,"initial_trend":"0"}},{"id":"seasonal-7-1","method":"SEASONAL_NAIVE","params":{"season":"7"}},{"id":"sba-half-1","method":"SBA","params":{"alpha":"0.5","beta":"0.5"}},{"id":"tsb-half-1","method":"TSB","params":{"alpha":"0.5","beta":"0.5"}}],"policy":{"minimum_complete_folds":"3","minimum_mae_improvement":"0","maximum_bias_worsening":"0","maximum_tail_worsening":"0","season_lag":"7"},"meaning":"TECHNICAL_PROPOSAL_NOT_OWNER_SERVICE_TARGET"}'::jsonb);
