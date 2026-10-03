"""Actual Auth/PostgREST experiment with forced Native command rollback.

One diagnostic emission, zero Native40/P19 product exit credit. No accepted
definition, role setting, statement timeout or financial guard is changed.
The temporary RPC is installed only on the disposable HTTP database, removed
before return and excluded from every product installation bundle.
"""
from decimal import Decimal
from time import monotonic, sleep
from urllib.parse import urlparse
import copy
import json
import uuid

import cp7_note_correction_cases as cases
import cp7_note_command_diagnostic_cases as private
import cp6_auditor_runner as native
from cp7_catalog_state import canonical_public_state
from cp7_note_http_trace import server_frames

RPC = 'cp7_note_actual_http_diagnostic'
SIGNATURE = 'public.' + RPC + '(text,jsonb,uuid,text)'
OBSERVER_SIGNATURE = 'public.cp7_note_actual_http_observe(jsonb,jsonb)'
SQL = r"""
create function public.cp7_note_actual_http_observe(p_payload jsonb,p_outcome jsonb)
returns jsonb language plpgsql volatile security definer set search_path=''as $$
declare detail jsonb;physical numeric;fg_value numeric;
begin
 if current_database()<>'cp6_auditor_http' or session_user<>'authenticator' then
  raise exception 'DIAGNOSTIC_REAL_DISPOSABLE_POSTGREST_ONLY';end if;
 perform cp7_note.access_now();
 if p_outcome is null then return '{}'::jsonb;end if;
 detail:=public.erp_cp7_get_sales_v1(jsonb_build_object(
  'sale_id',p_outcome->>'sale_id','limit',1,'offset',0));
 select coalesce(sum(m.qty_signed),0)into physical from erp.fg_stock_movements m
  where m.product_id=(p_payload->'items'->0->>'product_id')::uuid
   and m.location_id=(p_payload->>'source_location_id')::uuid
   and m.quality_grade='GRADE_A';
 select coalesce(sum(m.qty_signed*h.hpp_per_pcs),0)into fg_value
  from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id
   join erp.v_current_hpp h on h.lot_id=l.id
  where m.product_id=(p_payload->'items'->0->>'product_id')::uuid
   and m.location_id=(p_payload->>'source_location_id')::uuid
   and m.quality_grade='GRADE_A';
 return jsonb_build_object('financial_before_forced_rollback',detail->'detail'->'financial',
  'physical_before_forced_rollback',physical,'FG_value_before_forced_rollback',fg_value);
end $$;
alter function public.cp7_note_actual_http_observe(jsonb,jsonb)owner to postgres;
revoke all on function public.cp7_note_actual_http_observe(jsonb,jsonb)
 from public,anon,authenticated,service_role;
grant execute on function public.cp7_note_actual_http_observe(jsonb,jsonb)to authenticated;

create function public.cp7_note_actual_http_diagnostic(
 p_mode text,p_payload jsonb,p_request uuid,p_expected text
)returns jsonb language plpgsql volatile security invoker set search_path=''as $$
declare started timestamptz;command_end timestamptz;outcome jsonb;observation jsonb;
 result jsonb;failure_state text;failure_context text;
 stage text:='COMMAND';initial_jit text:=current_setting('jit');actual_jit text;
 initial_timeout text:=current_setting('statement_timeout');
begin
 if current_database()<>'cp6_auditor_http' or session_user<>'authenticator'
  or current_user<>'authenticated' then
  raise exception 'DIAGNOSTIC_REAL_DISPOSABLE_POSTGREST_ONLY';end if;
 if p_mode='IDENTITY_ONLY' then
  -- Readiness applies the original current owner/fine-right fence. Actual
  -- command modes use only the owning RPC's original admission sequence.
  perform public.cp7_note_actual_http_observe(null,null);
  return jsonb_build_object('diagnostic_only',true,'session_user',session_user,
   'invoker_role',current_user,'statement_timeout',initial_timeout,'jit',initial_jit);end if;
 if p_mode is null or p_mode not in('DEFAULT','JIT_OFF')then
  raise exception 'DIAGNOSTIC_CLOSED_EXPERIMENT_REQUIRED';end if;
 -- This USERSET experiment is request-local, never a product/role setting.
 if p_mode='JIT_OFF'then perform set_config('jit','off',true);end if;
 actual_jit:=current_setting('jit');started:=clock_timestamp();
 begin
  outcome:=public.erp_cp7_correct_note_v1(p_payload,p_request,p_expected);
  command_end:=clock_timestamp();stage:='AFTER_COMMAND_OBSERVATION';
  observation:=public.cp7_note_actual_http_observe(p_payload,outcome);
  result:=jsonb_build_object('status','MEASURED_BEFORE_FORCED_ROLLBACK',
   'command_elapsed_ms',extract(epoch from command_end-started)*1000,
   'observation_elapsed_ms',extract(epoch from clock_timestamp()-command_end)*1000,
   'outcome_before_forced_rollback',outcome)||observation;
  raise exception using errcode='PZ001',message='DIAGNOSTIC_FORCED_ROLLBACK';
 exception
  when sqlstate 'PZ001' then
   if result is null then raise;end if;
  when query_canceled or others then
   get stacked diagnostics failure_state=returned_sqlstate,
    failure_context=pg_exception_context;
   result:=jsonb_build_object('status','SQL_ERROR_ROLLED_BACK','failure_stage',stage,
    'sqlstate',failure_state,'elapsed_ms',extract(epoch from clock_timestamp()-started)*1000,
    'command_elapsed_ms',case when command_end is not null then
     extract(epoch from command_end-started)*1000 else null end,
    'static_context_to_filter',failure_context);
 end;
 if current_setting('statement_timeout')<>initial_timeout then
  raise exception 'DIAGNOSTIC_TIMEOUT_CHANGED';end if;
 return result||jsonb_build_object('diagnostic_only',true,'product_qualification',false,
  'Native_exit_case_credit',0,'mode',p_mode,'session_user',session_user,
  'invoker_role',current_user,
  'initial_jit',initial_jit,'experiment_jit',actual_jit,
  'statement_timeout',initial_timeout,'forced_business_rollback',true);
end $$;
alter function public.cp7_note_actual_http_diagnostic(text,jsonb,uuid,text)owner to postgres;
revoke all on function public.cp7_note_actual_http_diagnostic(text,jsonb,uuid,text)
 from public,anon,authenticated,service_role;
grant execute on function public.cp7_note_actual_http_diagnostic(text,jsonb,uuid,text)
 to authenticated;
"""


def http_cases(http, today):
    def emission():
        target = urlparse(http.url)
        assert target.hostname in ('localhost', '127.0.0.1') and target.path == '/cp6_auditor_http'
        user = http.login('OWNER', label='note-actual-http-diagnostic')
        installed = False
        measurements = []
        with http.connect() as conn, conn.cursor() as cur:
            cases.b.api.admin(cur)
            public_before = canonical_public_state(native.public_state(cur))
            for signature in (SIGNATURE, OBSERVER_SIGNATURE):
                assert cur.execute('select to_regprocedure(%s)', (signature,)).fetchone()[0] is None
            native_definitions_before = cases.ownership.verify(cur)
            conn.rollback()
        try:
            with http.connect() as conn, conn.cursor() as cur:
                cur.execute(SQL, prepare=False)
                cur.execute("notify pgrst,'reload schema'")
                conn.commit()
                installed = True
            # Only a read-only identity operation polls schema registration.
            # No failed Native command is retried or converted into a PASS.
            deadline = monotonic() + 10
            while True:
                identity = user.rpc(RPC, dict(p_mode='IDENTITY_ONLY', p_payload=None,
                                              p_request=None, p_expected=None))
                if identity['status'] == 200:
                    break
                assert identity['status'] == 404 and monotonic() < deadline, (
                    'DIAGNOSTIC_SCHEMA_READINESS_FAILED', identity['status'], identity['body'].get('code'))
                sleep(.1)
            assert identity['body']['session_user'] == 'authenticator'
            assert identity['body']['invoker_role'] == 'authenticated'
            assert identity['body']['statement_timeout'] == '8s', identity
            denied = http.anon_rpc(RPC, dict(p_mode='IDENTITY_ONLY', p_payload=None,
                                            p_request=None, p_expected=None))
            assert denied['status'] in (401, 403)
            count = 0
            for checkpoint in (1, 4):
                with http.connect() as conn, conn.cursor() as cur:
                    for _ in range(checkpoint - count):
                        fixture = private.prepare(cur, today)
                        count += 1
                    # Snapshot establishes UTC before creating the review token.
                    before = cases.snapshot(cur)
                    payload, version = cases.edit(cur, fixture, '16')
                    payload['item_lineage'] = [i['id'] for i in cases.source.read(cur, fixture)['detail']['items']]
                    key = str(uuid.uuid4())
                    conn.commit()
                args = dict(p_payload=payload, p_request=key, p_expected=version)
                for mode in ('DEFAULT', 'JIT_OFF'):
                    started = monotonic()
                    response = user.rpc(RPC, dict(p_mode=mode, **args))
                    duration = round((monotonic() - started) * 1000, 3)
                    row = dict(actual_E01_fixtures=checkpoint, mode=mode,
                               exact_request_id=key, exact_payload_and_version_reused=True,
                               HTTP_status=response['status'], HTTP_elapsed_ms=duration,
                               diagnostic_only=True, product_qualification=False, Native_exit_case_credit=0)
                    if response['status'] == 200:
                        observed = copy.deepcopy(response['body'])
                        context = observed.pop('static_context_to_filter', '')
                        row.update(observed, server_function_frames=server_frames(context))
                        assert observed['session_user'] == 'authenticator' and observed['statement_timeout'] == '8s'
                        assert observed['invoker_role'] == 'authenticated'
                        assert observed['forced_business_rollback'] and observed['diagnostic_only']
                        assert observed['product_qualification'] is False and observed['Native_exit_case_credit'] == 0
                        if observed['status'] == 'MEASURED_BEFORE_FORCED_ROLLBACK':
                            outcome = observed['outcome_before_forced_rollback']
                            financial = observed['financial_before_forced_rollback']
                            assert outcome['kind'] == 'COMMITTED_OUTCOME' and outcome['request_id'] == key
                            assert outcome['previous_sale_id'] == fixture['sale'] and outcome['revision'] == '1'
                            assert Decimal(str(observed['physical_before_forced_rollback'])) == 49
                            assert Decimal(str(observed['FG_value_before_forced_rollback'])) == 735
                            assert [Decimal(financial[k]) for k in ('net_total', 'paid_total', 'open_balance')] == [275, 200, 75]
                            row['actual_Native_stock49_value735_net275_paid200_AR75_before_rollback'] = True
                        else:
                            assert observed['status'] == 'SQL_ERROR_ROLLED_BACK'
                    else:
                        # Preserve an actual statement error, never retry it.
                        assert response['status'] == 500 and response['body'].get('code') == '57014', (
                            'DIAGNOSTIC_UNEXPECTED_HTTP_RESPONSE', response['status'], response['body'].get('code'))
                        row.update(status='ACTUAL_HTTP_STATEMENT_TIMEOUT', sqlstate='57014')
                    with http.connect() as conn, conn.cursor() as cur:
                        after = cases.snapshot(cur)
                        assert after == before, 'ACTUAL_HTTP_NATIVE_OR_PRIVATE_ROLLBACK_MISMATCH'
                        assert cases.ownership.verify(cur) == native_definitions_before
                        conn.rollback()
                    row['exact_full_Native_and_private_rollback'] = True
                    measurements.append(row)
                    print('CP7_NOTE_ACTUAL_HTTP_DIAGNOSTIC ' + json.dumps(row), flush=True)
        finally:
            if installed:
                with http.connect() as conn, conn.cursor() as cur:
                    cur.execute('drop function ' + SIGNATURE)
                    cur.execute('drop function ' + OBSERVER_SIGNATURE)
                    cur.execute("notify pgrst,'reload schema'")
                    conn.commit()
                    assert canonical_public_state(native.public_state(cur)) == public_before
                    assert cases.ownership.verify(cur) == native_definitions_before
                    conn.rollback()
        return dict(status='PASS', diagnostic_emission_only=True, product_qualification=False,
                    Native_exit_case_credit=0, measurements=measurements,
                    temporary_RPC_and_public_catalog_restored=True,
                    same_UUID_payload_version_and_full_rollback_each_pair=True,
                    default_real_timeout_and_every_Native_guard_unchanged=True)
    return [('NOTE_ACTUAL_AUTH_POSTGREST_DEFAULT_VS_JIT_EMISSION', emission)]
