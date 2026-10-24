"""Derive the private dated-vector timeline from the unchanged backlog kernel."""
from pathlib import Path


def render():
    text=(Path(__file__).resolve().parents[1]/'cp7-src/baseline/timeline.sql').read_text()
    def once(old,new):
        nonlocal text
        if text.count(old)!=1:raise ValueError('MODEL_TIMELINE_PREDECESSOR_CHANGED: '+old)
        text=text.replace(old,new,1)
    once('cp7_baseline.timeline(', 'cp7_model_target_consumer.timeline(')
    once("'cp7.timeline-input.v1'", "'cp7.model-target-timeline-input.v1'")
    once("if e->'qty_pcs'<>'null'::jsonb then perform cp7_demand.decimal(e->'qty_pcs');end if;",
      """if e->'qty_pcs'<>'null'::jsonb then
   -- A 30-place forecast times a 12-place partial day needs 42 places.
   -- Retain the exact product; the original kernel and its bounds are unchanged.
   if jsonb_typeof(e->'qty_pcs')is distinct from'string'or e->>'qty_pcs'!~'^(0|[1-9][0-9]{0,29})(\\.[0-9]{1,42})?$'then
    raise exception 'CP7_MODEL_TIMELINE_DECIMAL';end if;
  end if;""")
    once("qty:=cp7_demand.decimal(e->'qty_pcs');", "qty:=(e->>'qty_pcs')::numeric;")
    once("'kernel_version','timeline-1'", "'kernel_version','timeline-dated-model-1'")
    return ('-- Private exact dated-vector arithmetic; no model admission or public RPC.\n'+text+
      '\nalter function cp7_model_target_consumer.timeline(jsonb)owner to cp7_capture;\n'
      'revoke all on function cp7_model_target_consumer.timeline(jsonb)from public,anon,authenticated,service_role;\n')
