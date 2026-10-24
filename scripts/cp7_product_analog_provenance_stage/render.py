"""Opt-in public explanation overlay, derived from the consumer candidate.

No default install. Existing public facade names/argument contracts stay exact;
reader and projection responses explicitly version their richer bodies.
"""
from pathlib import Path
from hashlib import sha256
import json
import cp7_product_analog_consumer_stage.render as consumer
from cp7_production_stage import _body

ROOT=Path(__file__).resolve().parent
once=consumer.once


def originals():
    return {
      'cp7_product_analog_consumer.baseline_rows(jsonb,jsonb,jsonb,text,jsonb)':consumer.block('cp7_product_analog_consumer/baseline.sql','cp7_product_analog_consumer.baseline_rows'),
      'cp7_reorder_inputs.points(jsonb,jsonb,jsonb,jsonb)':consumer.replacements()['cp7_reorder_inputs.points(jsonb,jsonb,jsonb,jsonb)'],
      'cp7_product_analog_stage.read_candidates(uuid,text,integer,integer,text)':consumer.block('cp7_product_analog_reader_stage/reader.sql','cp7_product_analog_stage.read_candidates'),
      'cp7_reorder_caller.evaluate(jsonb,jsonb)':consumer.block('cp7_reorder_caller_stage/evaluate.sql','cp7_reorder_caller.evaluate'),
    }


def replacements():
    out=originals()
    sig='cp7_product_analog_consumer.baseline_rows(jsonb,jsonb,jsonb,text,jsonb)'
    out[sig]=once(out[sig],"'refs',all_refs)||case when resolution", "'refs',all_refs,'demand_provenance',cp7_product_analog_consumer.provenance(c,context->'query',r,estimate,resolution,target))||case when resolution")
    sig='cp7_reorder_inputs.points(jsonb,jsonb,jsonb,jsonb)'
    out[sig]=once(out[sig],"'analog_resolution',row_value->'analog_resolution','manual_state'", "'analog_resolution',row_value->'analog_resolution',\n   'demand_provenance',(row_value->'demand_provenance')||jsonb_build_object(\n    'basis',case when profile->>'quality'='UNREVIEWED'and counted>=14 then'OWN_AVAILABLE_HISTORY_ASSUMED_REPRESENTATIVE'else coalesce(row_value->'demand_estimate'->>'basis','UNKNOWN')end,\n    'daily_total_pcs',kernel->'inputs'->'daily_total_pcs','counted_days',kernel->'inputs'->'counted_days',\n    'daily_sd',kernel->'inputs'->'daily_sd','target_pcs',kernel->'target_pcs','reorder_point_pcs',kernel->'reorder_point_pcs'),\n   'manual_state'")
    sig='cp7_product_analog_stage.read_candidates(uuid,text,integer,integer,text)'
    out[sig]=once(out[sig],"'contract_version','cp7.product-analog-candidates-read.v1'", "'contract_version','cp7.product-analog-candidates-read.v2'")
    out[sig]=once(out[sig],"'result',candidates,", "'consumer_capability','REVIEWED_ANALOG_FOR_FRESH_CAPTURES',\n  'target_demand',(select x->'demand_provenance'from jsonb_array_elements(j.reference#>'{bounded_history_inputs,inputs,targets}')x where x->>'target_key'=p_target),\n  'result',candidates,")
    sig='cp7_reorder_caller.evaluate(jsonb,jsonb)'
    out[sig]=once(out[sig],"'contract_version','cp7.fg-reorder-projection.v1'", "'contract_version','cp7.fg-reorder-projection.v2','target_demand',p->'demand_provenance'")
    out[sig]=once(out[sig],"'daily_sd',p->'daily_sd'", "'daily_sd',config->'daily_sd'")
    return out


def render():return '\n\n'.join(replacements().values())+'\n'


def manifest():
    return dict(contract='cp7.product-analog-provenance-overlay.prototype.v1',
      predecessor_body_sha256={sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in originals().items()},
      replacement_body_sha256={sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in replacements().items()},
      helper_sql_sha256=sha256((ROOT/'provenance.sql').read_bytes()).hexdigest(),sql_sha256=sha256(render().encode()).hexdigest(),
      new_private_functions=1,existing_replacements=4,new_public_rpcs=0,new_tables=0,
      reader_contract='cp7.product-analog-candidates-read.v2',projection_contract='cp7.fg-reorder-projection.v2',
      Native_qualified=False,Auth_qualified=False,production_go=False)


if __name__=='__main__':
    (ROOT/'hooks.sql').write_text(render())
    (ROOT/'MANIFEST.json').write_text(json.dumps(manifest(),indent=2)+'\n')
