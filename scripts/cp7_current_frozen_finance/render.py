"""Explicit A finance-v2 derivation, with the mode bound before the first seal."""
from hashlib import sha256
from pathlib import Path
import re
from cp7_analysis_finance_bridge import patches as finance
from cp7_bounded_analysis_stage import source
from cp7_frozen_analysis_v2 import render as capsule

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT.parent
SCHEMA = 'cp7_current_frozen_finance'
OPERATIONAL = 'cp7_frozen_analysis_units_v2.request(jsonb,uuid)'
PRODUCER = 'cp7_frozen_analysis_units_v2.producer_hash()'
SOURCE = SCHEMA+'.source(jsonb,boolean)'
FINANCE = SCHEMA+'.request_finance(jsonb,uuid)'


def block(text, name):
    found = re.findall(r'create (?:or replace )?function '+re.escape(name)+r'\(.*?\$\$;', text, re.S)
    if len(found) != 1:
        raise ValueError('CURRENT_FROZEN_FINANCE_SINGLE_SOURCE_REQUIRED:'+name)
    return found[0]


def originals():
    return {
        OPERATIONAL: block((SCRIPTS/'cp7_frozen_analysis_units_v2/request.prepared.sql').read_text(), OPERATIONAL.split('(')[0]),
        PRODUCER: block((SCRIPTS/'cp7_frozen_analysis_units_v2/source.prepared.sql').read_text(), PRODUCER.split('(')[0]),
    }


def definitions():
    old = originals()
    # An operational UUID cannot silently replay an explicitly financial job.
    operational = source.once(old[OPERATIONAL],
        "  if jq<>q then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;",
        "  if jq<>q or exists(select 1 from cp7_analysis_stage.jobs x where x.id=jid\n"
        "   and coalesce(x.reference->>'finance_sidecar_mode','DEFERRED')<>'DEFERRED')then\n"
        "   raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;")
    operational = source.once(operational, 'create function ', 'create or replace function ')
    # Both routes share a producer identity that also covers A's new source and
    # request bodies. Existing B unit/freshness dispatch stays unchanged.
    producer = source.once(old[PRODUCER],
        "n.nspname='cp7_frozen_analysis_units_v2'",
        "n.nspname in('cp7_frozen_analysis_units_v2','"+SCHEMA+"')")
    producer = source.once(producer, 'create function ', 'create or replace function ')

    frozen = block((SCRIPTS/'cp7_frozen_analysis_v2/capsule.sql').read_text(), 'cp7_frozen_analysis_v2.source')
    frozen = source.once(frozen, 'cp7_frozen_analysis_v2.source(', SCHEMA+'.source(')
    frozen = source.once(frozen,
        "||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');",
        "||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED','finance_sidecar_mode','STAGED');")
    frozen = source.once(frozen, 'producer:=cp7_frozen_analysis_v2.producer_hash();',
                         'producer:=cp7_frozen_analysis_units_v2.producer_hash();')

    status = source.block('analysis-stages.sql', 'cp7_analysis_stage.status')
    request = finance.patched({finance.REQUEST:old[OPERATIONAL], finance.STATUS:status})[finance.REQUEST]
    request = source.once(request, 'cp7_frozen_analysis_units_v2.request(', SCHEMA+'.request_finance(')
    request = source.once(request, " if p_request is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;",
        " if p_query->'finance_mode'is distinct from'\"STAGED\"'::jsonb then\n"
        "  raise exception 'CP7_BOUNDED_FINANCE_EXPLICIT_STAGED_REQUIRED';end if;\n"
        " if p_request is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;")
    lock = " perform pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS-REQUEST:'||(a->>'actor')||':'||p_request::text,0));"
    request = source.once(request, lock, lock+"\n if cp7_schedule_native.access_now(false)is distinct from a\n"
        "  or not cp7_analysis_stage.report_finance_access(a,false)then\n"
        "  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_CHANGED';end if;")
    request = source.once(request, 'cp7_frozen_analysis_units_v2.source(q,true)', SCHEMA+'.source(q,true)')
    # The source already bound STAGED before seal. Never append a field to an
    # existing capsule: that would invalidate its immutable hash.
    request = source.once(request,
        "if finance_mode='STAGED'then c:=c||jsonb_build_object('finance_sidecar_mode','STAGED');end if;\n ", '')
    for tail in ('  return cp7_analysis_stage.status(jid);',
                 " -- More planned products than the job's declared capacity:"):
        # Admission at replay and after the potentially long source read.
        anchor = "if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;\n"+tail
        replacement = "if cp7_schedule_native.access_now(false)is distinct from a\n"
        replacement += "  or not cp7_analysis_stage.report_finance_access(a,false)then\n"
        replacement += "  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_CHANGED';end if;\n"+tail
        request = source.once(request, anchor, replacement)
    return {OPERATIONAL:operational, PRODUCER:producer, SOURCE:frozen, FINANCE:request}


def render():
    out = ['create schema '+SCHEMA+' authorization cp7_capture;',
           'revoke all on schema '+SCHEMA+' from public,anon,authenticated,service_role;']
    for signature, definition in definitions().items():
        out.append(definition)
        if signature in (SOURCE, FINANCE):
            out.extend(['alter function '+signature+' owner to cp7_capture;',
                        'revoke all on function '+signature+' from public,anon,authenticated,service_role;'])
    return '\n'.join(out)+'\n'


def manifest():
    return dict(contract='cp7.current-frozen-official-finance-private.v1',
        original_sql_sha256={k:sha256(v.encode()).hexdigest() for k,v in originals().items()},
        generated_sql_sha256=sha256(render().encode()).hexdigest(),
        A_finance_patcher_sha256=sha256(Path(finance.__file__).read_bytes()).hexdigest(),
        B_capsule_renderer_sha256=sha256(Path(capsule.__file__).read_bytes()).hexdigest(),
        old_replacements=[OPERATIONAL,PRODUCER], new_private_functions=[SOURCE,FINANCE],
        new_schemas=1, new_tables=0, new_public_rpcs=0, finance_mode='STAGED',
        finance_mode_bound_before_first_seal=True, source_sealed_once=True,
        official_source='cp7_finance_capture', financial_math_added=False,
        Native40_actual_predecessor_required=True, factory_finance_qualified=False,
        default_adopted=False, production_go=False)
