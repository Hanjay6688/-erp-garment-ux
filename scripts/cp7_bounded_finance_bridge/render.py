"""A-owned explicit bounded finance route, derived from both admitted sources."""
from pathlib import Path
from hashlib import sha256
import re
from cp7_analysis_finance_bridge import patches as finance
from cp7_bounded_analysis_stage import render as bounded
from cp7_bounded_analysis_stage import source

ROOT=Path(__file__).resolve().parent
REQUEST='cp7_bounded_analysis_stage.request(jsonb,uuid)'
FINANCE='cp7_bounded_analysis_stage.request_finance(jsonb,uuid)'
PUBLIC='public.erp_cp7_request_bounded_finance_analysis_v1(jsonb,uuid)'


def original():
    text,_=bounded.render()
    matches=re.findall(r'create function cp7_bounded_analysis_stage\.request\(.*?\$\$;',text,re.S)
    if len(matches)!=1:raise ValueError('BOUNDED_FINANCE_EXACT_REQUEST_REQUIRED')
    return matches[0]


def definitions():
    old=original()
    # Preserve the operational route's closed three-field query. Its only new
    # behavior is refusing a request UUID already bound to a finance job.
    operational=source.once(old,"  if jq<>q then raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;",
        "  if jq<>q or exists(select 1 from cp7_analysis_stage.jobs x where x.id=jid\n"
        "   and coalesce(x.reference->>'finance_sidecar_mode','DEFERRED')<>'DEFERRED')then\n"
        "   raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;")
    operational=source.once(operational,'create function ','create or replace function ')
    status=source.block('analysis-stages.sql','cp7_analysis_stage.status')
    new=finance.patched({finance.REQUEST:old,finance.STATUS:status})[finance.REQUEST]
    new=source.once(new,'create function cp7_bounded_analysis_stage.request(',
        'create function cp7_bounded_analysis_stage.request_finance(')
    new=source.once(new," if p_request is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;",
        " if p_query->'finance_mode'is distinct from'\"STAGED\"'::jsonb then\n"
        "  raise exception 'CP7_BOUNDED_FINANCE_EXPLICIT_STAGED_REQUIRED';end if;\n"
        " if p_request is null then raise exception 'CP7_ANALYSIS_REQUEST_REQUIRED';end if;")
    lock=" perform pg_advisory_xact_lock(hashtextextended('CP7:ANALYSIS-REQUEST:'||(a->>'actor')||':'||p_request::text,0));"
    new=source.once(new,lock,lock+"\n if cp7_schedule_native.access_now(false)is distinct from a\n"
        "  or not cp7_analysis_stage.report_finance_access(a,false)then\n"
        "  raise exception using errcode='42501',message='CP7_ANALYSIS_FINANCE_ACCESS_CHANGED';end if;")
    facade="""create function public.erp_cp7_request_bounded_finance_analysis_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$select cp7_bounded_analysis_stage.request_finance(p_query,p_request)$$;"""
    return {REQUEST:operational,FINANCE:new,PUBLIC:facade}


def render():
    bodies=definitions();out=[]
    for sig,body in bodies.items():
        out.append(body)
        if sig!=REQUEST:
            out.append('alter function '+sig+' owner to cp7_capture;')
            out.append('revoke all on function '+sig+' from public,anon,authenticated,service_role;')
    out.append('grant execute on function '+PUBLIC+' to authenticated;')
    return '\n'.join(out)+'\n'


def manifest():
    return dict(contract='cp7.bounded-official-finance-route.v1',
        generated_sql_sha256=sha256(render().encode()).hexdigest(),
        predecessor_request_sha256=sha256(original().encode()).hexdigest(),
        admitted_A_patcher_sha256=sha256(Path(finance.__file__).read_bytes()).hexdigest(),
        admitted_B_renderer_sha256=sha256(Path(bounded.__file__).read_bytes()).hexdigest(),
        existing_replacements=[REQUEST],new_private_functions=[FINANCE],new_public_rpcs=[PUBLIC],
        new_tables=0,financial_math_added=False,official_source='cp7_finance_capture',
        explicit_mode='STAGED',operational_route_query_fields=['from_date','through_date','group_mode'],
        full_A_chain_qualified=False,factory3600_financial_parity=False,production_go=False)
