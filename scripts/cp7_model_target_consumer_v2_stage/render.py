"""Exact target hooks for the explicit global/scoped model namespaces."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_production_stage import _body
import cp7_model_target_consumer_stage.render as previous
import cp7_model_target_consumer_v2 as consumer

ROOT = Path(__file__).resolve().parent
once = previous.once
originals = previous.originals


def replacements():
    consumer.verify_sources()
    out = previous.replacements()
    for signature in ('cp7_baseline_native.source_within(integer)','cp7_reorder_inputs.capture_baseline(integer)'):
        method = 'capture_for_reorder' if signature.startswith('cp7_reorder_inputs.') else 'capture'
        old = "cp7_model_target_source."+method+"(\n   coalesce((select array_agg((p->>'root_id')||':'||(p->>'size_id')order by p->>'root_id')\n    from jsonb_array_elements(value->'facts'->'products')p),array[]::text[]),\n   (value->>'captured_at')::timestamptz)"
        out[signature] = once(out[signature],old,'ms')
        out[signature] = once(out[signature]," roots as(select array_agg((p->>'root_id')::uuid order by p->>'root_id')ids from c,jsonb_array_elements(value->'facts'->'products')p)",
          """ model as materialized(select value,cp7_model_target_source_v2."""+method+"""(value,p_products)ms from c),
 roots as(select array_agg((p->>'root_id')::uuid order by p->>'root_id')ids from model,jsonb_array_elements(value->'facts'->'products')p)""")
        out[signature] = once(out[signature],"'model_target_source',ms,'product_analog_choices',",
          """'model_target_source',ms,'model_target_stock_references',cp7_model_target_source_v2.stock_digests(
   coalesce((select jsonb_agg(p order by p->>'id')from jsonb_array_elements(value->'facts'->'products')p
    where exists(select 1 from jsonb_array_elements(ms->'rows')r where r->>'runtime'='SCOPED_V3'
     and r->>'target_key'=(p->>'root_id')||':'||(p->>'size_id'))),'[]'),(value->>'captured_at')::timestamptz),'product_analog_choices',""")
        out[signature] = once(out[signature],'from c cross join roots','from model cross join roots')
    signature = 'cp7_stock_formula.workspace(jsonb)'
    out[signature] = once(out[signature]," select array_agg(e.target_key order by e.target_key)into model_targets", """ if exists(select 1 from cp7_reorder_caller.evaluations e
  where e.row#>>'{projection,contract_version}'is distinct from'cp7.fg-reorder-projection.v4')then
  raise exception using errcode='40001',message='CP7_MODEL_TARGET_REORDER_REFRESH_REQUIRED';end if;
 select array_agg(e.target_key order by e.target_key)into model_targets""")
    # Model authority is global, independent of the visible page/filter. The
    # current whole boundary is checked before returning even a single page.
    out[signature] = out[signature].replace('cp7_model_target_source.capture_for_reorder(model_targets,clock_timestamp())',
      'cp7_model_target_source_v2.capture_for_reorder(cp7_reorder_inputs.capture_history(5000),5000)')
    assert 'cp7_model_target_source.capture_for_reorder(' not in out[signature]
    for signature,sql in out.items():
        sql = sql.replace('cp7_model_target_consumer.','cp7_model_target_consumer_v2.')
        sql = sql.replace('cp7.native-baseline.v3','cp7.native-baseline.v4')
        sql = sql.replace('cp7.fg-reorder-projection.v3','cp7.fg-reorder-projection.v4')
        sql = sql.replace('policy-gated-dated-model-target-1','policy-gated-dated-model-target-2')
        # Legacy source remains a dependency for actual immutable v2 runs.
        sql = sql.replace("where n.nspname in('cp7_model_target_source',",
          "where n.nspname in('cp7_model_target_source_v2','cp7_model_evaluation_selection','cp7_model_target_binding','cp7_model_scoped_evaluation','cp7_model_scoped_dataset','cp7_model_history_runtime','cp7_model_history_scope','cp7_model_target_source',")
        out[signature] = sql
    assert len(out)==21
    return out


def render():
    return '\n\n'.join(replacements().values())+'\n'


def manifest():
    return dict(contract='cp7.model-target-consumer-hooks.candidate.v2',
      predecessor_body_sha256={sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in originals().items()},
      replacement_body_sha256={sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in replacements().items()},
      hooks_sql_sha256=sha256(render().encode()).hexdigest(),existing_replacements=21,
      new_private_functions=4,new_schemas=2,new_public_rpcs=0,new_tables=0,
      source_stage_required='cp7.model-target-source-stage.v2',source_namespace_preserved=True,
      exact_installer_catalog_qualified=False,public_client_qualified=False,actual_Native=False,
      actual_Auth_HTTP_credit=False,production_go=False)


if __name__=='__main__':
    (ROOT/'hooks.sql').write_text(render())
    (ROOT/'MANIFEST.json').write_text(json.dumps(manifest(),indent=2)+'\n')
