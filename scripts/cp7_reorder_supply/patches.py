"""Two counted B hooks for the supply-cache producer, not installed by default.

Reader/ROP integration and the complete reversible stage are still open. Never
apply a partial hook to hosted or treat this helper as an A installer release.
"""
from hashlib import sha256
from pathlib import Path
import json
from cp7_production_stage import _body

ROOT=Path(__file__).resolve().parent
RUN='cp7_analysis_stage.run_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units)'
SOURCE='cp7_analysis_native.source_within(integer,integer)'
SIGNATURES=(RUN,SOURCE)


def once(text,old,new,signature):
    if text.count(old)!=1:
        raise ValueError('OW10_SUPPLY_HOOK_ANCHOR_CHANGED: '+signature)
    return text.replace(old,new,1)


def patched(originals):
    pins=json.loads((ROOT/'MANIFEST.json').read_text())['before_bodies']
    if set(originals)!=set(SIGNATURES)or set(pins)!=set(SIGNATURES):
        raise ValueError('OW10_SUPPLY_HOOK_SET_CHANGED')
    for sig,definition in originals.items():
        if sha256(_body(definition).encode()).hexdigest()!=pins[sig]:
            raise ValueError('OW10_SUPPLY_PREDECESSOR_CHANGED: '+sig)
    run=once(originals[RUN],"   'wip_status',wip->'status','schedule_state',scenario->'schedule_state',",
        "   'reorder_supply_budget',cp7_reorder_supply.budgets(wip,scenario->'etas'),\n"
        "   'wip_status',wip->'status','schedule_state',scenario->'schedule_state',",RUN)
    source=once(originals[SOURCE],"'cp7_models','cp7_finance')",
        "'cp7_models','cp7_finance','cp7_reorder_supply')",SOURCE)
    source=once(source,"select c||jsonb_build_object('analysis_engine_signature',signature,",
        "select c||jsonb_build_object('reorder_supply_engine','cp7.reorder-supply.v1','analysis_engine_signature',signature,",SOURCE)
    return {RUN:run,SOURCE:source}
