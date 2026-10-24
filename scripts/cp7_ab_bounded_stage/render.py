"""Explicit A finance + B initial/bounded request composition.

All B SQL except the legacy request body remains byte-identical. The bounded
facade remains a strict three-field, DEFERRED method. No global overrides.
"""
from hashlib import sha256
from pathlib import Path
from cp7_production_stage import _body
from cp7_bounded_analysis_stage import render as bounded, source
from cp7_analysis_finance_bridge import patches as finance

ROOT=Path(__file__).resolve().parent
SCHEMA,PRIVATE,PUBLIC=bounded.SCHEMA,bounded.PRIVATE,bounded.PUBLIC
OLD_REQUEST=bounded.OLD_REQUEST


def with_finance(request):
    status=source.block('analysis-stages.sql','cp7_analysis_stage.status')
    return finance.patched({finance.REQUEST:request,finance.STATUS:status})[finance.REQUEST]


def originals():
    result=bounded.originals()
    result[OLD_REQUEST]=with_finance(result[OLD_REQUEST])
    return result


def render():
    sql,replacements=bounded.render()
    original=replacements[OLD_REQUEST]
    replacement=with_finance(original)
    sql=source.once(sql,original,replacement)
    return sql,dict(replacements,**{OLD_REQUEST:replacement})


def manifest():
    sql,new=render();old=originals()
    return dict(contract='cp7.ab-bounded-finance-composition.v1',
        sql_sha256=sha256(sql.encode()).hexdigest(),
        replacements={sig:dict(before_sha256=sha256(_body(text).encode()).hexdigest(),
            after_sha256=sha256(_body(new[sig]).encode()).hexdigest())for sig,text in old.items()},
        B_original_manifest=bounded.manifest(),
        finance_patcher_sha256=sha256(Path(finance.__file__).read_bytes()).hexdigest(),
        bounded_route_finance='DEFERRED_ONLY',bounded_query_fields=['from_date','group_mode','through_date'],
        shared_request_preserves=['initial_auto','finance_mode','same_UUID_recovery','cross_method_UUID_refusal'])
