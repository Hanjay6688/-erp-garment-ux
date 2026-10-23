-- Private derived threshold cache. It never stores or substitutes live FG.
create schema cp7_reorder_reader authorization cp7_capture;
revoke all on schema cp7_reorder_reader from public,anon,authenticated,service_role,cp7_alert;
create table cp7_reorder_reader.cache(
 id boolean primary key check(id),threshold_hash text not null check(threshold_hash~'^[0-9a-f]{64}$'),
 threshold_captured_at timestamptz not null,query jsonb not null check(jsonb_typeof(query)='object'),
 body jsonb not null check(jsonb_typeof(body)='object')
);
create table cp7_reorder_reader.use_marks(id boolean primary key check(id),used_at timestamptz not null);
alter table cp7_reorder_reader.cache owner to cp7_capture;
alter table cp7_reorder_reader.use_marks owner to cp7_capture;
alter table cp7_reorder_reader.cache enable row level security;
alter table cp7_reorder_reader.use_marks enable row level security;
create policy reorder_cache_no_access on cp7_reorder_reader.cache for all to public using(false)with check(false);
create policy reorder_use_no_access on cp7_reorder_reader.use_marks for all to public using(false)with check(false);
revoke all on cp7_reorder_reader.cache,cp7_reorder_reader.use_marks from public,anon,authenticated,service_role,cp7_alert;

create function cp7_reorder_reader.immutable_use()returns trigger
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
begin raise exception 'CP7_REORDER_USE_MARK_IMMUTABLE';end $$;
alter function cp7_reorder_reader.immutable_use()owner to cp7_capture;
revoke all on function cp7_reorder_reader.immutable_use()from public,anon,authenticated,service_role,cp7_alert;
create trigger reorder_use_immutable before update or delete on cp7_reorder_reader.use_marks
 for each row execute function cp7_reorder_reader.immutable_use();

-- s must come from the private server source in the caller's statement. No
-- Auth endpoint accepts this DTO. Recheck the current source on EVERY call;
-- only the threshold arithmetic can be reused, never free stock or rights.
create function cp7_reorder_reader.snapshot(s jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare cached cp7_reorder_reader.cache%rowtype;compiled jsonb;body jsonb;stock jsonb;hit boolean;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 if not pg_try_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0))then
  raise exception using errcode='55P03',message='CP7_FORMULA_BUSY';end if;
 perform cp7_wip.fields(s,array['contract_version','status','captured_at','query','native','defaults','product_bound',
  'stock_summary','leads','manuals','engine_hash','context_hash','threshold_hash','apply_enabled','production_go']);
 if s->>'contract_version'is distinct from'cp7.reorder-native-source.v1'
  or jsonb_typeof(s->'threshold_hash')is distinct from'string'or s->>'threshold_hash'!~'^[0-9a-f]{64}$'
  or s->'captured_at'is distinct from s->'native'->'captured_at'or s->'status'is distinct from s->'native'->'status'
  or s->'apply_enabled'is distinct from'false'::jsonb or s->'production_go'is distinct from'false'::jsonb then
  raise exception 'CP7_REORDER_CACHE_SOURCE_BINDING';end if;
 select*into cached from cp7_reorder_reader.cache where id;
 hit:=cached.threshold_hash is not distinct from s->>'threshold_hash'and cached.query=s->'query';
 if hit then body:=cached.body;
 else
  compiled:=cp7_reorder_inputs.compile(s);
  body:=jsonb_build_object('points',compiled->'points','products',compiled->'inputs'->'products',
   'threshold_source_hash',compiled->'inputs'->'source_hash','input_path',compiled->'input_path',
   'history_statistics',(select coalesce(jsonb_object_agg(h->>'target_key',jsonb_build_object(
    'sale_days',(select count(*)from jsonb_array_elements(h->'days')d where d->>'state'='AVAILABLE'and(d->>'gross_observed_pcs')::numeric>0),
    'available_days',h->'available_days','gross_observed_pcs',h->'gross_observed_pcs')),'{}')
    from jsonb_array_elements(compiled->'inputs'->'history')h));
  insert into cp7_reorder_reader.cache(id,threshold_hash,threshold_captured_at,query,body)
   values(true,s->>'threshold_hash',(s->>'captured_at')::timestamptz,s->'query',body)
   on conflict(id)do update set threshold_hash=excluded.threshold_hash,threshold_captured_at=excluded.threshold_captured_at,
    query=excluded.query,body=excluded.body;
  cached.threshold_captured_at:=(s->>'captured_at')::timestamptz;
 end if;
 -- Same source snapshot, actual Native draft/reservation validation. Today-only
 -- movement can change this even when the historical threshold key is equal.
 stock:=cp7_reorder_inputs.current_stock(s->'native',s->'stock_summary',s->>'context_hash');
 insert into cp7_reorder_reader.use_marks(id,used_at)values(true,(s->>'captured_at')::timestamptz)on conflict(id)do nothing;
 return body||jsonb_build_object('contract_version','cp7.reorder-reader-snapshot.v1','captured_at',s->'captured_at',
  'query',s->'query','defaults',s->'defaults','leads',s->'leads','manuals',s->'manuals','current_stock',stock,
  'threshold_hash',s->'threshold_hash','threshold_captured_at',cp7_planning.utc(cached.threshold_captured_at),
  'context_hash',s->'context_hash','engine_hash',s->'engine_hash','native_capture_status',s->'status','cache_hit',hit,
  'live_ROP_caller_changed',false,'apply_enabled',false,'production_go',false);
end $$;
alter function cp7_reorder_reader.snapshot(jsonb)owner to cp7_capture;
revoke all on function cp7_reorder_reader.snapshot(jsonb)from public,anon,authenticated,service_role,cp7_alert;
