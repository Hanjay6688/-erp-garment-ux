"""Versioned consumer derived from the pinned baseline/model projection path."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def once(source, old, new):
    assert source.count(old) == 1, ('MODEL_CONSUMER_V2_ANCHOR',old[:100])
    return source.replace(old,new)


def render():
    s = (ROOT.parent/'cp7_model_target_consumer/consumer.sql').read_text()
    s = s.replace('cp7_model_target_consumer','cp7_model_target_consumer_v2')
    # The producer supplies complete stock references at the captured clock.
    # This consumer binds those references to captured non-stock facts without
    # rereading tables; both it and forecast arithmetic remain immutable.
    s = once(s,"reason text;at timestamptz;business_day date;key text;",
      "reason text;at timestamptz;business_day date;key text;selection_by_target jsonb;selection_row jsonb;\n scoped_products jsonb;physical_rows jsonb;physical_by_target jsonb;runtime_value text;")
    s = once(s,"'engine_hash','consumer_engine_hash','live_history_source_hash'",
      "'engine_hash','scoped_engine_hash','history_engine_hash','producer_hash','selection','consumer_engine_hash','live_history_source_hash'")
    s = once(s,"'cp7.model-target-source.v1'","'cp7.model-target-source.v2'")
    start = s.index(' -- A model checked against a newer physical source')
    end = s.index(' for row_value in select value from jsonb_array_elements(base_rows)loop',start)
    s = s[:start]+''' -- The source must match the global captured boundary before a model can
 -- consume it. Global and single-root histories retain distinct identities.
 if s->'selection'='null'::jsonb then
  if exists(select 1 from jsonb_each(models)x where x.value->'run_id'is distinct from'null'::jsonb
   or x.value->>'reason'is distinct from'MODEL_CURRENT_ACCESS_REQUIRED')then
   raise exception 'CP7_MODEL_CONSUMER_SELECTION_BINDING';end if;
 else
  perform cp7_demand.items(s->'selection',5000);
  select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into selection_by_target from jsonb_array_elements(s->'selection')x;
  if jsonb_array_length(s->'selection')<>(select count(*)from jsonb_each(models))
   or jsonb_array_length(s->'selection')<>(select count(*)from jsonb_each(selection_by_target))then
   raise exception 'CP7_MODEL_CONSUMER_SELECTION_BINDING';end if;
  for m in select value from jsonb_each(models)loop
   selection_row:=selection_by_target->(m->>'target_key');
   if selection_row is null or selection_row->'run_id'is distinct from m->'run_id'
    or selection_row->'runtime'is distinct from m->'runtime'
    or selection_row->'read_method'is distinct from m->'read_method'
    or selection_row->'captured_at'is distinct from m->'captured_at'then
    raise exception 'CP7_MODEL_CONSUMER_SELECTION_BINDING';end if;
  end loop;
 end if;
 if exists(select 1 from jsonb_each(models)x where x.value->>'state'='ELIGIBLE'and x.value->>'runtime'='GLOBAL_V2')and
  (c->>'status'is distinct from'COMPLETE'or encode(extensions.digest(convert_to((c->'facts')::text,'UTF8'),'sha256'),'hex')is distinct from s->>'live_history_source_hash')then
  raise exception 'CP7_MODEL_CONSUMER_PHYSICAL_SOURCE_MISMATCH';end if;
 select coalesce(jsonb_agg(p order by p->>'id'),'[]')into scoped_products from jsonb_array_elements(c->'facts'->'products')p
  where models->((p->>'root_id')||':'||(p->>'size_id'))->>'runtime'='SCOPED_V3'
   and models->((p->>'root_id')||':'||(p->>'size_id'))->>'state'='ELIGIBLE';
 if jsonb_array_length(scoped_products)>0 then
  perform cp7_demand.items(c->'model_target_stock_references',5000);
  physical_rows:=cp7_model_target_source_v2.physical_rows(c,5000,c->'model_target_stock_references',s->>'producer_hash');
  select coalesce(jsonb_object_agg(x->>'target_key',x->'reference'->'scoped_source_hash'),'{}')into physical_by_target from jsonb_array_elements(physical_rows)x;
  if exists(select 1 from jsonb_each(models)x where x.value->>'state'='ELIGIBLE'and x.value->>'runtime'='SCOPED_V3'
   and(x.value->'history_source_hash'is distinct from x.value->'physical_source_hash'
    or x.value->'physical_source_hash'is distinct from physical_by_target->x.key))then
   raise exception 'CP7_MODEL_CONSUMER_PHYSICAL_SOURCE_MISMATCH';end if;
 end if;
'''+s[end:]
    anchor="  if m is null or m->'target_key'is distinct from row_value->'target_key'then raise exception 'CP7_MODEL_CONSUMER_TARGET_BINDING';end if;"
    s = once(s,anchor,anchor+'''
  perform cp7_wip.fields(m,array['target_key','run_id','runtime','read_method','state','reason','history_run_id','history_scope',
   'history_query','history_source_hash','physical_source_hash','model_source_hash','captured_at','forecast_from_date','selected_model','forecast']);
  runtime_value:=m->>'runtime';
  if m->>'state'is null or m->>'state'not in('BASELINE_REQUIRED','ELIGIBLE')or m->>'reason'is null then
   raise exception 'CP7_MODEL_CONSUMER_RUNTIME_BINDING';end if;
  if m->'run_id'='null'::jsonb then
   if m->>'state'<>'BASELINE_REQUIRED'or exists(select 1 from jsonb_each(m)x
    where x.key not in('target_key','state','reason')and x.value<>'null'::jsonb)then
    raise exception 'CP7_MODEL_CONSUMER_RUNTIME_BINDING';end if;
  else
   perform(m->>'run_id')::uuid;perform(m->>'history_run_id')::uuid;
   if runtime_value is null or runtime_value not in('GLOBAL_V2','SCOPED_V3')
    or m->>'read_method'is distinct from(case runtime_value when'GLOBAL_V2'then'erp_cp7_read_model_evaluation_v2'else'erp_cp7_read_model_evaluation_v3'end)
    or m->>'history_scope'is distinct from(case runtime_value when'GLOBAL_V2'then'GLOBAL_CURRENT_PHYSICAL_ROOTS'else'SINGLE_CURRENT_PHYSICAL_ROOT'end)
    or m->>'model_source_hash'is null or m->>'model_source_hash'!~'^[0-9a-f]{64}$'
    or m->>'history_source_hash'is null or m->>'history_source_hash'!~'^[0-9a-f]{64}$'
    or m->>'physical_source_hash'is null or m->>'physical_source_hash'!~'^[0-9a-f]{64}$'
    or cp7_demand.instant(m->'captured_at')>at then raise exception 'CP7_MODEL_CONSUMER_RUNTIME_BINDING';end if;
  end if;''')
    s = once(s,"'cp7.model-target-resolution.v1'","'cp7.model-target-resolution.v2'")
    s = once(s,"'run_id',m->'run_id','history_run_id',m->'history_run_id'",
      "'run_id',m->'run_id','runtime',m->'runtime','read_method',m->'read_method',\n   'history_scope',m->'history_scope','history_source_hash',m->'history_source_hash','physical_source_hash',m->'physical_source_hash','history_run_id',m->'history_run_id'")
    s = once(s,"'policy_source',s->'policy_source','engine_hash',s->'engine_hash','consumer_engine_hash',s->'consumer_engine_hash'",
      "'policy_source',s->'policy_source','engine_hash',case when runtime_value='SCOPED_V3'then s->'scoped_engine_hash'else s->'engine_hash'end,\n   'global_engine_hash',s->'engine_hash','scoped_engine_hash',s->'scoped_engine_hash','history_engine_hash',s->'history_engine_hash','consumer_engine_hash',s->'consumer_engine_hash'")
    s = once(s,"'cp7.target-demand-provenance.v2'","'cp7.target-demand-provenance.v3'")
    return s
