"""Two explicit authenticated facades; all work remains in the bound private owners."""
from hashlib import sha256
from pathlib import Path
import json
from cp7_current_frozen_finance.render import block

ROOT=Path(__file__).resolve().parent
B_HEAD='c1dd6b5cd231701be3be35bb7dd45c3856ace8fa'
B_PATH='scripts/cp7_frozen_analysis_facade_v2/facade.sql'
B_SHA256='cbfb6ee4cbe165221c3bcab18750547f0b4952224e5ed7e5e0f2cbcd42ebd7c4'
OPERATIONAL='public.erp_cp7_request_bounded_staged_analysis_v2(jsonb,uuid)'
FINANCE='public.erp_cp7_request_bounded_frozen_finance_analysis_v2(jsonb,uuid)'


def upstream():
    raw=(ROOT/'B_facade.sql').read_bytes()
    pins=json.loads((ROOT/'UPSTREAM.json').read_bytes())
    if (sha256(raw).hexdigest()!=B_SHA256 or pins!=dict(head=B_HEAD,path=B_PATH,sha256=B_SHA256)):
        raise ValueError('CURRENT_FROZEN_PUBLIC_UPSTREAM_CHANGED')
    return raw.decode()


def finance_sql():
    return '''create function public.erp_cp7_request_bounded_frozen_finance_analysis_v2(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_current_frozen_finance.request_finance(p_query,p_request)
$$;
alter function public.erp_cp7_request_bounded_frozen_finance_analysis_v2(jsonb,uuid)owner to cp7_capture;
revoke all on function public.erp_cp7_request_bounded_frozen_finance_analysis_v2(jsonb,uuid)from public,anon,authenticated,service_role,postgres;
grant execute on function public.erp_cp7_request_bounded_frozen_finance_analysis_v2(jsonb,uuid)to authenticated;
'''


def definitions():
    return {OPERATIONAL:block(upstream(),OPERATIONAL.split('(')[0]),
            FINANCE:block(finance_sql(),FINANCE.split('(')[0])}


def render():
    return upstream()+'\n'+finance_sql()


def manifest():
    return dict(contract='cp7.current-frozen-public-official-finance.v1',
        qualified_B_candidate=dict(head=B_HEAD,path=B_PATH,sha256=B_SHA256),
        new_public_rpcs=2,new_tables=0,new_schemas=0,existing_replacements=0,
        signatures=sorted(definitions()),owner='cp7_capture',security_definer=True,
        authenticated_execute_only=True,official_finance_owner='cp7_current_frozen_finance.request_finance',
        operational_owner='cp7_frozen_analysis_units_v2.request',financial_math_added=False,
        private_Native45_PASS_required_before_qualification=True,
        B_facade_actual_PASS_required_before_qualification=True,
        default_adopted=False,production_go=False,independent_acceptance=False)
