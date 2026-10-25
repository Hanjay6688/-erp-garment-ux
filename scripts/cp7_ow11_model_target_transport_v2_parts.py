"""Two declared partitions of the unchanged eleven transport controls.

Every operation remains the original function. The catalog anchor repeats in
both parts, for no additional case credit. Complete qualification requires both
Originals at the same source head, including each restoration/advisor gate.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import cp7_ow11_model_target_transport_v2_cases as full

ROOT=Path(__file__).resolve().parent
PARTS={
 'A':dict(native=list(full.IDS['native']),races=list(full.IDS['races'][:4])),
 'B':dict(native=list(full.IDS['native']),races=list(full.IDS['races'][4:]),http=list(full.IDS['http']))}


def verify_coverage():
    assert full.EXPECTED==full.DECLARED==11
    assert full.REQUIRED==dict(native=1,races=7,http=3)
    assert {k:len(v)for k,v in PARTS['A'].items()}==dict(native=1,races=4)
    assert {k:len(v)for k,v in PARTS['B'].items()}==dict(native=1,races=3,http=3)
    assert PARTS['A']['native']==PARTS['B']['native']==full.IDS['native']
    assert PARTS['A']['races']+PARTS['B']['races']==full.IDS['races']
    assert not set(PARTS['A']['races'])&set(PARTS['B']['races'])
    assert PARTS['B']['http']==full.IDS['http']
    assert len(set(n for ids in PARTS.values()for names in ids.values()for n in names))==11
    return dict(unique_required_cases=11,duplicate_catalog_anchor_credit=0,part_case_counts=dict(A=5,B=7))


def sources():
    return {p.name:sha256(p.read_bytes()).hexdigest()for p in (Path(__file__),ROOT/'cp7_ow11_model_target_transport_v2_cases.py')}


def selected(part):
    verify_coverage()
    if part not in PARTS:raise ValueError('MODEL_TARGET_TRANSPORT_PART_UNKNOWN')
    ids=deepcopy(PARTS[part]);required={k:len(v)for k,v in ids.items()}
    provider=SimpleNamespace(CONTRACT='cp7.ow11.model-target-transport-part-'+part.lower()+'.v2',
      IDS=ids,REQUIRED=required,EXPECTED=sum(required.values()),DECLARED=sum(required.values()),
      FUNCTIONS=full.FUNCTIONS,SCHEDULES=full.SCHEDULES,stage=full.stage,sources=full.sources,PARENT_CHECKER=None,
      INSTALL_STATES={},REORDER_STATES={},CHECKED_STATE={},SCHEDULE_STATE={},BOUNDED_STATE={},REFERENCE_STATE={},STAGE_STATE={})

    def group(name,context,today):
        full.PARENT_CHECKER=provider.PARENT_CHECKER
        if name not in ids:return []
        operations=getattr(full,'cases'if name=='native'else'http_cases'if name=='http'else'races')(context,today)
        assert [key for key,_ in operations]==full.IDS[name]
        selected_ops=[(key,operation)for key,operation in operations if key in ids[name]]
        assert [key for key,_ in selected_ops]==ids[name]
        return selected_ops

    provider.cases=lambda cur,today:group('native',cur,today)
    provider.races=lambda tools,today:group('races',tools,today)
    provider.http_cases=lambda http,today:group('http',http,today)
    return provider
