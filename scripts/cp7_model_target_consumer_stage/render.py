"""Derive model-target hooks from exact predecessors for the opt-in installer.

The actual parent must include analog provenance, the direct-reader correction,
and immutable model-v2. Native catalog and runtime qualification stay explicit.
"""
from pathlib import Path
from hashlib import sha256
import json
from cp7_production_stage import _body
import cp7_product_analog_consumer_stage.render as analog
import cp7_product_analog_provenance_stage.render as provenance
import cp7_baseline_freshness_stage.render as freshness
import cp7_model_target_consumer as consumer

ROOT=Path(__file__).resolve().parent
once=analog.once


def originals():
    all_functions={**analog.replacements(),**provenance.replacements(),freshness.SIGNATURE:freshness.replacement().strip()}
    all_functions['cp7_analysis_stage.analysis_skeleton(jsonb,jsonb,uuid,jsonb,jsonb,jsonb,jsonb,jsonb,boolean,text)']=analog.block('cp7_bounded_analysis_stage/stage.sql','cp7_analysis_stage.analysis_skeleton')
    all_functions['cp7_netting_native.timeline(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)']=analog.block('cp7-src/planning/netting.sql','cp7_netting_native.timeline')
    all_functions['cp7_analysis_stage.analysis_targets(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)']=analog.block('cp7-src/planning/analysis-stages.sql','cp7_analysis_stage.analysis_targets')
    all_functions['cp7_analysis_native.build_operational(jsonb,jsonb,uuid,jsonb)']=analog.block('cp7-src/planning/analysis.sql','cp7_analysis_native.build').replace('cp7_analysis_native.build(', 'cp7_analysis_native.build_operational(',1)
    signatures=[
      'cp7_baseline_native.source_within(integer)','cp7_reorder_inputs.capture_baseline(integer)',
      'cp7_baseline_native.build(jsonb,jsonb)','cp7_baseline_native.serve(uuid)',
      'cp7_analysis_stage.baseline_rows(jsonb,jsonb,jsonb,text)',
      'cp7_analysis_stage.history_prep(jsonb,jsonb,integer,bigint,integer)',
      'cp7_reorder_inputs.compile(jsonb)','cp7_history_bounded.compile(jsonb,jsonb,jsonb,integer)',
      'cp7_bounded_analysis_stage.native_work_fingerprint(jsonb)','cp7_supply_native.fingerprint(jsonb)',
      'cp7_reorder_inputs.source_within(integer)','cp7_bounded_analysis_stage.analysis_source(integer,integer)',
      'cp7_analysis_native.source_within(integer,integer)','cp7_bounded_analysis_stage.producer_hash()',
      'cp7_reorder_caller.evaluate(jsonb,jsonb)',
      'cp7_reorder_inputs.points(jsonb,jsonb,jsonb,jsonb)',
      'cp7_analysis_stage.analysis_skeleton(jsonb,jsonb,uuid,jsonb,jsonb,jsonb,jsonb,jsonb,boolean,text)',
      'cp7_netting_native.timeline(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)',
      'cp7_analysis_stage.analysis_targets(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)',
      'cp7_analysis_native.build_operational(jsonb,jsonb,uuid,jsonb)',
    ]
    return {sig:all_functions[sig]for sig in signatures}


def replacements():
    consumer.verify_sources();out=originals()
    for sig in ['cp7_baseline_native.source_within(integer)','cp7_reorder_inputs.capture_baseline(integer)']:
        out[sig]=once(out[sig],"select value||jsonb_build_object('product_analog_choices',",
         "select value||jsonb_build_object('model_target_source',cp7_model_target_source.capture(\n   coalesce((select array_agg((p->>'root_id')||':'||(p->>'size_id')order by p->>'root_id')\n    from jsonb_array_elements(value->'facts'->'products')p),array[]::text[]),\n   (value->>'captured_at')::timestamptz),'product_analog_choices',")
    out['cp7_reorder_inputs.capture_baseline(integer)']=once(out['cp7_reorder_inputs.capture_baseline(integer)'],'cp7_model_target_source.capture(','cp7_model_target_source.capture_for_reorder(')
    for sig in ['cp7_baseline_native.build(jsonb,jsonb)','cp7_analysis_stage.baseline_rows(jsonb,jsonb,jsonb,text)']:
        out[sig]=once(out[sig],'cp7_product_analog_consumer.baseline_rows(','cp7_model_target_consumer.rows(')
    # Every existing producer/reader/cache uses the exact same extra identity.
    # Timestamps remain outside this stable source hash.
    for sig,text in out.items():
        for variable in ('c','boundary.c'):
            anchor="'analog_consumer_engine',"+variable+"->'analog_consumer_engine'"
            if anchor in text:
                text=text.replace(anchor,anchor+",'model_target_source_hash',"+variable+"->'model_target_source'->'source_hash'")
        out[sig]=text
    sig='cp7_baseline_native.build(jsonb,jsonb)'
    out[sig]=once(out[sig],"case when exists(select 1 from jsonb_array_elements(c->'profiles')x where x#>>'{config,buffer_mode}'='STATISTICAL')then'cp7.native-baseline.v2'else'cp7.native-baseline.v1'end","'cp7.native-baseline.v3'")
    out[sig]=once(out[sig],"case when exists(select 1 from jsonb_array_elements(c->'profiles')x where x#>>'{config,buffer_mode}'='STATISTICAL')then'UNIFIED_TARGET_WITH_SELECTED_PROFILE_ASSUMPTIONS'else'DAYS_WITH_SELECTED_PROFILE_ASSUMPTIONS'end","'UNIFIED_TARGET_WITH_SELECTED_PROFILE_ASSUMPTIONS'")
    out[sig]=once(out[sig],"'model_basis','BASELINE_ADAPTIVE_PROMOTION_NOT_PROVEN'","'model_basis','CURRENT_POLICY_GATED_DATED_NATIVE_MODELS'")
    producer=out[sig].split(' hash:=',1)[1].split(';',1)[0]
    assert out['cp7_baseline_native.serve(uuid)'].split('hash:=',1)[1].split(';',1)[0]==producer
    for sig in ['cp7_reorder_inputs.source_within(integer)','cp7_bounded_analysis_stage.analysis_source(integer,integer)',
                'cp7_analysis_native.source_within(integer,integer)','cp7_bounded_analysis_stage.producer_hash()']:
        out[sig]=once(out[sig],'where n.nspname in(',"where n.nspname in('cp7_model_target_source','cp7_model_target_projection','cp7_model_target_consumer','cp7_model_registry_adapter','cp7_model_policy','cp7_model_activation_gate',")
    sig='cp7_reorder_caller.evaluate(jsonb,jsonb)'
    out[sig]=once(out[sig],"'contract_version','cp7.fg-reorder-projection.v2'","'contract_version','cp7.fg-reorder-projection.v3'")
    sig='cp7_reorder_inputs.points(jsonb,jsonb,jsonb,jsonb)'
    # An unreviewed profile retains the predecessor's measured-lead/statistical
    # default kernel. Its explanation must name that kernel, not the UNKNOWN
    # profile target that preceded it. No model is admitted by this fallback.
    out[sig]=once(out[sig],"'demand_provenance',(row_value->'demand_provenance')||jsonb_build_object(",
      "'demand_provenance',(row_value->'demand_provenance')||jsonb_build_object(\n    'model',case when profile->>'quality'='UNREVIEWED'then(row_value->'model_resolution')||jsonb_build_object(\n     'state','BASELINE_RETAINED','reason','EXISTING_REORDER_DEFAULTS_RETAINED_UNREVIEWED_PROFILE',\n     'baseline_target',kernel,'forecast',null,'forecast_applied',false)else row_value->'model_resolution'end,")
    sig='cp7_analysis_stage.analysis_skeleton(jsonb,jsonb,uuid,jsonb,jsonb,jsonb,jsonb,jsonb,boolean,text)'
    out[sig]=once(out[sig],"'models','native-available-history-fallback-1'","'models','policy-gated-dated-model-target-1'")
    sig='cp7_netting_native.timeline(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)'
    out[sig]=once(out[sig],"events jsonb[]:='{}';", "model_input jsonb:=r->'model_resolution';model_applied boolean:=coalesce(r->'model_resolution'->>'state'='MODEL_PROJECTED',false);\n projection jsonb;timeline_input jsonb;timeline_result jsonb;events jsonb[]:='{}';")
    out[sig]=once(out[sig]," rate:=cp7_demand.decimal(r->'demand_estimate'->'daily_pcs');", """ if model_applied then
  if r->'target'->'model_input'is distinct from model_input
   or model_input->>'source_hash'is distinct from c->'model_target_source'->>'source_hash'
   or model_input->'forecast_applied'is distinct from'true'::jsonb then raise exception 'CP7_MODEL_TIMELINE_BINDING';end if;
  if cfg->'lead_days'is distinct from r->'target'->'inputs'->'lead_days'
   or cfg->'review_days'is distinct from r->'target'->'inputs'->'review_days'then raise exception 'CP7_MODEL_TIMELINE_PROFILE';end if;
  projection:=cp7_model_target_projection.project(model_input->'baseline_target'->'inputs',
   jsonb_build_object('contract_version','cp7.model-target-vector.v1','forecast_from_date',model_input->'forecast_from_date',
    'forecasts',model_input->'forecast'->'forecasts'),(ready at time zone'Asia/Jakarta')::date);
  if projection->>'state'is distinct from'ARITHMETIC_CANDIDATE'or r->'target'is distinct from
   ((projection->'baseline')||(projection->'projected')||jsonb_build_object('reason',projection->'reason',
    'model_input',model_input,'forecast_applied',true))then raise exception 'CP7_MODEL_TIMELINE_TARGET_MISMATCH';end if;
 else rate:=cp7_demand.decimal(r->'demand_estimate'->'daily_pcs');end if;""")
    out[sig]=once(out[sig],"qty:=ceil(rate*duration*1000000000000)/1000000000000;",
      "qty:=case when model_applied then cp7_model_target_projection.sum_window(model_input->'forecast'->'forecasts',i-1,i-1+duration)else ceil(rate*duration*1000000000000)/1000000000000 end;")
    out[sig]=once(out[sig],"'qty_pcs',qty::numeric(42,12)::text", "'qty_pcs',case when model_applied then qty::text else qty::numeric(42,12)::text end")
    out[sig]=once(out[sig]," return cp7_baseline.timeline(jsonb_build_object('contract_version','cp7.timeline-input.v1',",
      " timeline_input:=jsonb_build_object('contract_version',case when model_applied then'cp7.model-target-timeline-input.v1'else'cp7.timeline-input.v1'end,")
    out[sig]=once(out[sig],"'events',to_jsonb(events),'refs',r->'refs'))\n  ||jsonb_build_object('timing_basis','SELECTED_DAILY_RESIDUAL_AT_EACH_24H_END_FROM_CAPTURE',",
      """'events',to_jsonb(events),'refs',r->'refs');
 timeline_result:=case when model_applied then cp7_model_target_consumer.timeline(timeline_input)else cp7_baseline.timeline(timeline_input)end;
 return timeline_result||jsonb_build_object('timing_basis',case when model_applied then'DATED_MODEL_VECTOR_AT_EACH_24H_END_FROM_CAPTURE'else'SELECTED_DAILY_RESIDUAL_AT_EACH_24H_END_FROM_CAPTURE'end,""")
    for sig in ['cp7_analysis_stage.analysis_targets(jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb,jsonb)',
                'cp7_analysis_native.build_operational(jsonb,jsonb,uuid,jsonb)']:
        # A dated vector is not a single daily rate. Keep the existing closed
        # analysis wire; expose its evaluated method and an explicit N/A rate.
        out[sig]=once(out[sig],"'method_id',coalesce(r->'demand_estimate'->>'basis','NATIVE_AVAILABLE_HISTORY')",
          "'method_id',case when r->'model_resolution'->>'state'='MODEL_PROJECTED'then r->'model_resolution'->'selected_model'->>'method'else coalesce(r->'demand_estimate'->>'basis','NATIVE_AVAILABLE_HISTORY')end")
        out[sig]=once(out[sig],"'version','native-available-history-fallback-1','mode','FALLBACK',",
          "'version',case when r->'model_resolution'->>'state'='MODEL_PROJECTED'then'policy-gated-dated-model-target-1'else'native-available-history-fallback-1'end,'mode',case when r->'model_resolution'->>'state'='MODEL_PROJECTED'then'EVALUATED'else'FALLBACK'end,")
        out[sig]=once(out[sig],"'demand_rate',cp7_analysis_native.fact(r->'demand_estimate'->>'daily_pcs','PCS/DAY',refs,row_aids)",
          "'demand_rate',case when r->'model_resolution'->>'state'='MODEL_PROJECTED'then jsonb_build_object('state','NOT_APPLICABLE','unit','PCS/DAY','reason','DATED_VECTOR_HAS_NO_SINGLE_DAILY_RATE','refs',refs)else cp7_analysis_native.fact(r->'demand_estimate'->>'daily_pcs','PCS/DAY',refs,row_aids)end")
        out[sig]=once(out[sig],"'selection_reason','Native available-history/manual fallback; no backtest promotion without earlier-known training evidence'",
          "'selection_reason',case when r->'model_resolution'->>'state'='MODEL_PROJECTED'then 'Current policy-gated dated vector; immutable model run '||(r->'model_resolution'->>'run_id')||'; historical variation remains a selected assumption'else'Native available-history/manual fallback; no backtest promotion without earlier-known training evidence'end")
        out[sig]=once(out[sig],"'timing_policy_id','selected-native-each24h-from-capture-1'",
          "'timing_policy_id',case when r->'model_resolution'->>'state'='MODEL_PROJECTED'then'dated-model-each24h-from-capture-1'else'selected-native-each24h-from-capture-1'end")
    sig='cp7_analysis_native.build_operational(jsonb,jsonb,uuid,jsonb)'
    out[sig]=once(out[sig],"'models','native-available-history-fallback-1'","'models','policy-gated-dated-model-target-1'")
    return out


def render():return '\n\n'.join(replacements().values())+'\n'


def manifest():
    return dict(contract='cp7.model-target-consumer-hooks.candidate.v1',
      predecessor_body_sha256={sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in originals().items()},
      replacement_body_sha256={sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in replacements().items()},
      hooks_sql_sha256=sha256(render().encode()).hexdigest(),existing_replacements=20,
      new_private_functions=8,new_schemas=3,new_public_rpcs=0,new_tables=0,
      exact_installer_catalog_qualified=False,public_client_qualified=False,
      actual_Native_capture=False,actual_Auth_HTTP_credit=False,production_go=False)


if __name__=='__main__':
    (ROOT/'hooks.sql').write_text(render())
    (ROOT/'MANIFEST.json').write_text(json.dumps(manifest(),indent=2)+'\n')
