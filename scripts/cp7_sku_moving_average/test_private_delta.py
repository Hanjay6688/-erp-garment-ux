from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('moving_average_private_delta',HERE/'private_delta.py')
delta=importlib.util.module_from_spec(spec);spec.loader.exec_module(delta)
PARENT=HERE.parent/'cp7_sku_pair_conversion'/'conversion.sql'

def function(text,name,next_name=None):
    start=text.index('create function '+name)
    if next_name is None:return text[start:]
    return text[start:text.index('create function '+next_name,start+1)]

source=PARENT.read_text()
originals={
 delta.SIGNATURES[0]:function(source,'cp7_sku_conversion.preview_v1','cp7_sku_conversion.action_v1'),
 delta.SIGNATURES[1]:function(source,'cp7_sku_conversion.action_v1','cp7_sku_conversion.workspace_v1'),
}
patched=delta.patched(originals)
assert set(patched)==set(delta.SIGNATURES)
assert "order by l.produced_at,l.id loop" in patched[delta.SIGNATURES[0]]
assert "source_value_pool" in patched[delta.SIGNATURES[0]]
assert "native_physical_value" in patched[delta.SIGNATURES[0]]
assert "prepare_valuation_v2(p_request,v)" in patched[delta.SIGNATURES[1]]
assert "finalize_valuation_v2(p_request)" in patched[delta.SIGNATURES[1]]
assert "reverse_valuation_v2(v_group_id)" in patched[delta.SIGNATURES[1]]
assert originals[delta.SIGNATURES[0]].count('pool_quote_v2')==0
assert originals[delta.SIGNATURES[1]].count('valuation_v2')==0

for sig,body in originals.items():
    bad=dict(originals);bad[sig]=body+'\n-- predecessor drift'
    # An unrelated suffix is intentionally harmless. The exact anchors, not a
    # whole-body hash, define the bounded derivation; catalog binding supplies
    # the full predecessor digest at installation.
    assert delta.patched(bad)[sig].endswith('-- predecessor drift')

print({'status':'SKU_MOVAVG_PRIVATE_TWO_EXACT_SUBSTITUTIONS',
       'physical_fifo_preserved':True,'actual_sql':0,'production_go':False})
