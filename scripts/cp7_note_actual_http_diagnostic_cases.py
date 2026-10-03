"""Actual Auth/PostgREST experiment with forced Native command rollback.

One diagnostic emission, zero Native40/P19 product exit credit. No accepted
definition, role setting, statement timeout or financial guard is changed.
The temporary RPC is installed only on the disposable HTTP database, removed
before return and excluded from every product installation bundle.
"""
from decimal import Decimal
from datetime import timedelta
from time import monotonic, sleep
from urllib.parse import urlparse
import copy
import hashlib
import json
import os
import uuid

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp7_note_correction_cases as cases
import cp7_note_command_diagnostic_cases as private
import cp6_auditor_runner as native
from cp7_catalog_state import canonical_public_state
from cp7_note_http_trace import server_frames
import cp7_note_command_function_profile as function_profile

RPC = 'cp7_note_actual_http_diagnostic'
SIGNATURE = 'public.' + RPC + '(text,jsonb,uuid,text)'
OBSERVER_SIGNATURE = 'public.cp7_note_actual_http_observe(jsonb,jsonb)'
TRACK_SIGNATURE = 'public.cp7_note_actual_http_track(text)'
FUNCTION_COUNTERS_SELECT = r"""
select coalesce(jsonb_agg(to_jsonb(c)order by c.function_oid::oid),'[]'::jsonb)
from (
 select s.funcid::text as function_oid,n.nspname::text as schema_name,
  p.proname::text as function_name,
  pg_catalog.pg_get_function_identity_arguments(p.oid)as identity_arguments,
  s.calls::text as calls,s.total_time::text as total_time_ms,s.self_time::text as self_time_ms
 from pg_catalog.pg_stat_xact_user_functions s
 join pg_catalog.pg_proc p on p.oid=s.funcid
 join pg_catalog.pg_namespace n on n.oid=p.pronamespace
 where n.nspname='erp' or pg_catalog.left(n.nspname,4)='cp7_'
  or p.oid='public.erp_cp7_correct_note_v1(jsonb,uuid,text)'::regprocedure
 order by s.funcid limit 1001
)c
"""
SQL = r"""
-- No function SET frame here: the closed, fully-qualified setter must keep
-- SET LOCAL effective in its caller. It never invokes the owning command.
-- Only this disposable database and a fresh current owner can use it.
create function public.cp7_note_actual_http_track(p_value text)
returns text language plpgsql volatile security definer as $$
begin
 if pg_catalog.current_database()<>'cp6_auditor_http' or session_user<>'authenticator' then
  raise exception 'DIAGNOSTIC_REAL_DISPOSABLE_POSTGREST_ONLY';end if;
 if p_value is null or p_value not in('none','pl','all')then
  raise exception 'DIAGNOSTIC_CLOSED_TRACK_VALUE_REQUIRED';end if;
 perform cp7_note.access_now();
 return pg_catalog.set_config('track_functions',p_value,true);
end $$;
alter function public.cp7_note_actual_http_track(text)owner to postgres;
revoke all on function public.cp7_note_actual_http_track(text)
 from public,anon,authenticated,service_role;
grant execute on function public.cp7_note_actual_http_track(text)to authenticated;

create function public.cp7_note_actual_http_observe(p_payload jsonb,p_outcome jsonb)
returns jsonb language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
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
  'physical_before_forced_rollback',physical,'FG_value_before_forced_rollback',fg_value,
  'immutable_original_facts',jsonb_build_object('header',
   (select to_jsonb(h)-array['status','paid_total','row_version','updated_at']
    from erp.sales_headers h where h.id=(p_outcome->>'previous_sale_id')::uuid),
   'items',(select jsonb_agg(to_jsonb(i)order by id)from erp.sales_items i
    where i.sale_id=(p_outcome->>'previous_sale_id')::uuid)),
  'source_sku',(select sku from erp.products where id=(p_payload->'items'->0->>'product_id')::uuid),
  'source_lot_ids',(select coalesce(jsonb_agg(distinct lot_id),'[]')from erp.fg_stock_movements
   where product_id=(p_payload->'items'->0->>'product_id')::uuid
    and location_id=(p_payload->>'source_location_id')::uuid and quality_grade='GRADE_A'));
end $$;
alter function public.cp7_note_actual_http_observe(jsonb,jsonb)owner to postgres;
revoke all on function public.cp7_note_actual_http_observe(jsonb,jsonb)
 from public,anon,authenticated,service_role;
grant execute on function public.cp7_note_actual_http_observe(jsonb,jsonb)to authenticated;

create function public.cp7_note_actual_http_diagnostic(
 p_mode text,p_payload jsonb,p_request uuid,p_expected text
)returns jsonb language plpgsql volatile security invoker set search_path=''as $$
declare started timestamptz;command_end timestamptz;outcome jsonb;observation jsonb;
 page jsonb;book_rows jsonb:='[]';lot_rows jsonb;cards jsonb:='[]';lot text;off integer;total integer;
 result jsonb;failure_state text;failure_context text;
 stage text:='COMMAND';initial_jit text:=current_setting('jit');actual_jit text;
 initial_timeout text:=current_setting('statement_timeout');
 initial_track text:=current_setting('track_functions');
 counters_before jsonb;counters_after jsonb;profile_setup timestamptz;setup_ms numeric;
 profile_complete boolean:=false;root_oid text;
begin
 if current_database()<>'cp6_auditor_http' or session_user<>'authenticator'
  or current_user<>'authenticated' then
  raise exception 'DIAGNOSTIC_REAL_DISPOSABLE_POSTGREST_ONLY';end if;
 if p_mode='IDENTITY_ONLY' then
  -- Readiness applies the original current owner/fine-right fence. Actual
  -- command modes use only the owning RPC's original admission sequence.
  perform public.cp7_note_actual_http_observe(null,null);
  return jsonb_build_object('diagnostic_only',true,'session_user',session_user,
   'invoker_role',current_user,'statement_timeout',initial_timeout,'jit',initial_jit,
   'track_functions',initial_track);end if;
 if p_mode is null or p_mode not in('DEFAULT','JIT_OFF','YEAR_364_DEFAULT','YEAR_364_FUNCTION_PROFILE')then
  raise exception 'DIAGNOSTIC_CLOSED_EXPERIMENT_REQUIRED';end if;
 if p_mode='YEAR_364_FUNCTION_PROFILE'then
  profile_setup:=clock_timestamp();
  begin
   perform public.cp7_note_actual_http_track('all');
  exception when insufficient_privilege then
   if current_setting('track_functions')<>initial_track then
    raise exception 'DIAGNOSTIC_TRACK_NOT_RESTORED';end if;
   return jsonb_build_object('status','FUNCTION_INSTRUMENT_UNAVAILABLE',
    'reason','EXISTING_DISPOSABLE_TRACKING_PREFLIGHT_DENIED',
    'business_command_called',false,'forced_business_rollback',false,
    'diagnostic_only',true,'product_qualification',false,'Native_exit_case_credit',0,
    'mode',p_mode,'session_user',session_user,'invoker_role',current_user,
    'statement_timeout',initial_timeout,'initial_track_functions',initial_track,
    'track_functions_restored',true);
  end;
  if current_setting('track_functions')<>'all'then
   raise exception 'DIAGNOSTIC_TRACKING_NOT_ACTIVE';end if;
  root_oid:='public.erp_cp7_correct_note_v1(jsonb,uuid,text)'::regprocedure::oid::text;
  select (__FUNCTION_COUNTERS_SELECT__)into counters_before;
  if jsonb_array_length(counters_before)>1000 then raise exception 'DIAGNOSTIC_FUNCTION_CAP';end if;
  setup_ms:=extract(epoch from clock_timestamp()-profile_setup)*1000;
 end if;
 -- This USERSET experiment is request-local, never a product/role setting.
 if p_mode='JIT_OFF'then perform set_config('jit','off',true);end if;
 actual_jit:=current_setting('jit');started:=clock_timestamp();
 begin
  outcome:=public.erp_cp7_correct_note_v1(p_payload,p_request,p_expected);
  command_end:=clock_timestamp();
  if p_mode='YEAR_364_FUNCTION_PROFILE'then
   select (__FUNCTION_COUNTERS_SELECT__)into counters_after;
   if jsonb_array_length(counters_after)>1000 then raise exception 'DIAGNOSTIC_FUNCTION_CAP';end if;
   profile_complete:=true;
  end if;
  stage:='AFTER_COMMAND_OBSERVATION';
  observation:=public.cp7_note_actual_http_observe(p_payload,outcome);
  if p_mode in('YEAR_364_DEFAULT','YEAR_364_FUNCTION_PROFILE')then
   off:=0;
   loop
    page:=public.erp_cp7_get_fg_book_v2(jsonb_build_object(
     'q',observation->>'source_sku','limit',100,'offset',off));
    book_rows:=book_rows||(page->'page'->'rows');total:=(page->'page'->>'total')::integer;
    if jsonb_array_length(book_rows)>2000 then raise exception 'DIAGNOSTIC_HISTORY_CAP';end if;
    exit when page->'page'->>'next_offset'is null;
    if (page->'page'->>'next_offset')::integer<=off or jsonb_array_length(page->'page'->'rows')=0
     then raise exception 'DIAGNOSTIC_HISTORY_NO_PROGRESS';end if;
    off:=(page->'page'->>'next_offset')::integer;
   end loop;
   if jsonb_array_length(book_rows)<>total then raise exception 'DIAGNOSTIC_HISTORY_INCOMPLETE';end if;
   if jsonb_array_length(observation->'source_lot_ids')>20 then raise exception 'DIAGNOSTIC_LOT_CAP';end if;
   for lot in select jsonb_array_elements_text(observation->'source_lot_ids')loop
    off:=0;lot_rows:='[]';
    loop
     page:=public.erp_cp7_get_fg_ledger_v2(jsonb_build_object(
      'product_id',p_payload->'items'->0->>'product_id','lot_id',lot,
      'location_id',p_payload->>'source_location_id','quality_grade','GRADE_A',
      'purpose','CARD','limit',100,'offset',off));
     lot_rows:=lot_rows||(page->'page'->'rows');total:=(page->'page'->>'total')::integer;
     if jsonb_array_length(lot_rows)>2000 then raise exception 'DIAGNOSTIC_HISTORY_CAP';end if;
     exit when page->'page'->>'next_offset'is null;
     if (page->'page'->>'next_offset')::integer<=off or jsonb_array_length(page->'page'->'rows')=0
      then raise exception 'DIAGNOSTIC_HISTORY_NO_PROGRESS';end if;
     off:=(page->'page'->>'next_offset')::integer;
    end loop;
    if jsonb_array_length(lot_rows)<>total then raise exception 'DIAGNOSTIC_HISTORY_INCOMPLETE';end if;
    cards:=cards||jsonb_build_array(jsonb_build_object('lot_id',lot,'rows',lot_rows));
   end loop;
   observation:=observation||jsonb_build_object('actual_Auth_book_before_forced_rollback',book_rows,
    'actual_Auth_lot_cards_before_forced_rollback',cards);
  end if;
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
   -- If the command was interrupted, completed child calls and unwind may
   -- remain visible. These partial counters never claim a full command time.
   if p_mode='YEAR_364_FUNCTION_PROFILE'and counters_after is null then
    select (__FUNCTION_COUNTERS_SELECT__)into counters_after;
   end if;
   result:=jsonb_build_object('status','SQL_ERROR_ROLLED_BACK','failure_stage',stage,
    'sqlstate',failure_state,'elapsed_ms',extract(epoch from clock_timestamp()-started)*1000,
    'command_elapsed_ms',case when command_end is not null then
     extract(epoch from command_end-started)*1000 else null end,
    'static_context_to_filter',failure_context);
 end;
 if current_setting('statement_timeout')<>initial_timeout then
  raise exception 'DIAGNOSTIC_TIMEOUT_CHANGED';end if;
 if p_mode='YEAR_364_FUNCTION_PROFILE'then
  perform public.cp7_note_actual_http_track(initial_track);
  if current_setting('track_functions')<>initial_track then
   raise exception 'DIAGNOSTIC_TRACK_NOT_RESTORED';end if;
  result:=result||jsonb_build_object('function_counters_before',counters_before,
   'function_counters_after',counters_after,'function_command_completed',profile_complete,
   'function_root_oid',root_oid,'initial_track_functions',initial_track,
   'instrument_track_functions','all','track_functions_restored',true,
   'function_counter_collection','CURRENT_TRANSACTION_BEFORE_AFTER_COMMAND_BEFORE_OBSERVATION',
   'function_profile_setup_ms',setup_ms);
 end if;
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
SQL = SQL.replace('__FUNCTION_COUNTERS_SELECT__', FUNCTION_COUNTERS_SELECT)


def instrument_connection(http):
    # This authority is already created by the isolated diagnostic workflow.
    # Only temporary instrumentation is owned/dropped with it. The actual
    # correction continues through the original authenticated PostgREST RPC.
    control = os.environ.get('CP6_ADMISSION_CONTROL_PGURL')
    if not control:
        raise ValueError('PROFILE_INSTALL_EXISTING_CONTROL_REQUIRED')
    admitted = function_profile.instrument_admission(conninfo_to_dict(control),
                                                     conninfo_to_dict(http.url))
    return psycopg.connect(control, dbname=admitted['database'], connect_timeout=5,
                           application_name='cp7_disposable_function_instrument')


def instrument_identity(cur):
    observed = cur.execute("select pg_catalog.current_database(),session_user,current_user,"
                           "(select rolsuper from pg_catalog.pg_roles where rolname=current_user)").fetchone()
    assert observed == ('cp6_auditor_http', 'cp6_maintenance_admission',
                        'cp6_maintenance_admission', True), 'PROFILE_INSTALL_ACTUAL_AUTHORITY_REQUIRED'


def admit_tracker_owner(http):
    with instrument_connection(http) as conn, conn.cursor() as cur:
        instrument_identity(cur)
        before = cur.execute("select pg_catalog.pg_get_userbyid(proowner),prosecdef,proconfig,"
                             "pg_catalog.pg_get_functiondef(oid),"
                             "pg_catalog.has_function_privilege('authenticated',oid,'EXECUTE'),"
                             "pg_catalog.has_function_privilege('anon',oid,'EXECUTE'),"
                             "pg_catalog.has_function_privilege('service_role',oid,'EXECUTE')"
                             "from pg_catalog.pg_proc where oid=%s::regprocedure",
                             (TRACK_SIGNATURE,)).fetchone()
        assert before and before[:3] == ('postgres', True, None) and before[4:] == (True, False, False)
        cur.execute('alter function public.cp7_note_actual_http_track(text)owner to cp6_maintenance_admission')
        after = cur.execute("select pg_catalog.pg_get_userbyid(proowner),prosecdef,proconfig,"
                            "pg_catalog.pg_get_functiondef(oid),"
                            "pg_catalog.has_function_privilege('authenticated',oid,'EXECUTE'),"
                            "pg_catalog.has_function_privilege('anon',oid,'EXECUTE'),"
                            "pg_catalog.has_function_privilege('service_role',oid,'EXECUTE')"
                            "from pg_catalog.pg_proc where oid=%s::regprocedure",
                            (TRACK_SIGNATURE,)).fetchone()
        assert after and after[:3] == ('cp6_maintenance_admission', True, None)
        assert after[3:] == before[3:], 'PROFILE_TRACKER_DEFINITION_OR_EXECUTE_ACL_CHANGED'
        conn.commit()
    return dict(database='cp6_auditor_http', temporary_tracking_owner='cp6_maintenance_admission',
                existing_installer_superuser_checked=True, no_new_role_or_parameter_SET_grant=True,
                tracking_definition_and_existing_execute_scope_unchanged=True,
                connection_strings_or_passwords_emitted=False,
                owning_command_still_original_authenticated_invoker=True)


def http_cases(http, today):
    def emission():
        target = urlparse(http.url)
        assert target.hostname in ('localhost', '127.0.0.1') and target.path == '/cp6_auditor_http'
        user = http.login('OWNER', label='note-actual-http-diagnostic')
        installed = False
        measurements = []
        with open(function_profile.__file__, 'rb') as source:
            profile_parser_sha256 = hashlib.sha256(source.read()).hexdigest()
        with http.connect() as conn, conn.cursor() as cur:
            cases.b.api.admin(cur)
            public_before = canonical_public_state(native.public_state(cur))
            for signature in (SIGNATURE, OBSERVER_SIGNATURE, TRACK_SIGNATURE):
                assert cur.execute('select to_regprocedure(%s)', (signature,)).fetchone()[0] is None
            native_definitions_before = cases.ownership.verify(cur)
            conn.rollback()
        try:
            # Fail before creating any instrumentation if the existing local
            # maintenance identity is unavailable or points elsewhere.
            with instrument_connection(http) as conn, conn.cursor() as cur:
                instrument_identity(cur)
                conn.rollback()
            with http.connect() as conn, conn.cursor() as cur:
                cur.execute(SQL, prepare=False)
                cur.execute("notify pgrst,'reload schema'")
                conn.commit()
                installed = True
            tracker_installation = admit_tracker_owner(http)
            with http.connect() as conn, conn.cursor() as cur:
                cur.execute("notify pgrst,'reload schema'")
                conn.commit()
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
            denied_track = http.anon_rpc('cp7_note_actual_http_track', dict(p_value='all'))
            assert denied_track['status'] in (401, 403)
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
            # Bounded real Auth history exercise: original24 ->12 and364 later
            # Native sales. This remains inside the same zero-credit emission.
            with http.connect() as conn, conn.cursor() as cur:
                first = cases.source.fg.ax.r1.now(cur) - timedelta(days=366, hours=1)
                fixture = cases.stock(cur, today, 24 + 12 * 364 + 100, first - timedelta(days=1))
                fixture['sale_at'] = first.isoformat()
                cases.posted(cur, fixture, '24', '20')
                root_facts = cases.unchanged_facts(cur, fixture['sale'])
                later_ids = []
                for index in range(364):
                    later = dict(fixture, tag=fixture['tag'] + '-H' + str(index + 1),
                                 sale_at=(first + timedelta(days=index + 1)).isoformat())
                    cases.posted(cur, later, '12', '20')
                    later_ids.append(str(cur.execute("select m.id from erp.fg_stock_movements m "
                        "join erp.sales_items i on i.id=m.source_id where i.sale_id=%s "
                        "and m.movement_type='SALE'", (later['sale'],)).fetchone()[0]))
                before = cases.snapshot(cur)
                before_book = cases.complete_book(cur, fixture)
                before_card = cases.complete_lot_card(cur, fixture)
                payload, version = cases.edit(cur, fixture, '12')
                payload['item_lineage'] = [i['id'] for i in cases.source.read(cur, fixture)['detail']['items']]
                key = str(uuid.uuid4())
                conn.commit()
            # A separately declared instrumented comparison follows the original
            # uninstrumented year attempt. Neither attempt earns product credit.
            # Identical inputs may be reused only after complete forced rollback.
            for mode in ('YEAR_364_DEFAULT', 'YEAR_364_FUNCTION_PROFILE'):
                started = monotonic()
                response = user.rpc(RPC, dict(p_mode=mode, p_payload=payload,
                                              p_request=key, p_expected=version))
                row = dict(scenario='ACTUAL_AUTH_YEAR364', mode=mode, exact_request_id=key,
                           exact_payload_and_version_reused_after_full_rollback=True,
                           HTTP_status=response['status'],
                           HTTP_elapsed_ms=round((monotonic()-started)*1000, 3),
                           diagnostic_only=True, product_qualification=False, Native_exit_case_credit=0)
                if response['status'] == 200:
                    observed = copy.deepcopy(response['body'])
                    context = observed.pop('static_context_to_filter', '')
                    row.update(observed, server_function_frames=server_frames(context))
                    assert observed['session_user'] == 'authenticator' and observed['invoker_role'] == 'authenticated'
                    assert observed['statement_timeout'] == '8s'
                    assert observed['diagnostic_only'] and observed['product_qualification'] is False
                    assert observed['Native_exit_case_credit'] == 0
                    if observed['status'] != 'FUNCTION_INSTRUMENT_UNAVAILABLE':
                        assert observed['forced_business_rollback']
                    if observed['status'] == 'MEASURED_BEFORE_FORCED_ROLLBACK':
                        outcome = observed['outcome_before_forced_rollback']
                        assert outcome['kind'] == 'COMMITTED_OUTCOME' and outcome['request_id'] == key
                        assert outcome['previous_sale_id'] == fixture['sale'] and outcome['revision'] == '1'
                        assert observed['immutable_original_facts'] == root_facts
                        assert observed['product_qualification'] is False and observed['Native_exit_case_credit'] == 0
                        after_book = {r['id']: r for r in observed['actual_Auth_book_before_forced_rollback']}
                        cards = observed['actual_Auth_lot_cards_before_forced_rollback']
                        assert len(cards) == 1 and cards[0]['lot_id'] == fixture['lot']
                        after_card = {r['id']: r for r in cards[0]['rows']}
                        assert len(after_book) == len(after_card) == len(before_book) == len(before_card) == 366
                        for ident in later_ids:
                            for field in ('official_physical_after', 'book_physical_after',
                                          'official_available_after', 'book_available_after'):
                                assert Decimal(after_book[ident][field])-Decimal(before_book[ident][field]) == 12
                            for field in ('physical_balance', 'available_balance'):
                                assert Decimal(after_card[ident][field])-Decimal(before_card[ident][field]) == 12
                            assert after_book[ident]['physical_delta'] == '-12' and after_book[ident]['correction_count'] == '0'
                        assert all(after_book[ident]['book_order'] == value['book_order'] for ident, value in before_book.items())
                        assert Decimal(str(observed['physical_before_forced_rollback'])) == 112
                        assert Decimal(str(observed['FG_value_before_forced_rollback'])) == 1120
                        financial = observed['financial_before_forced_rollback']
                        assert [Decimal(financial[k]) for k in ('net_total', 'paid_total', 'open_balance')] == [240, 0, 240]
                        row['all364_actual_Auth_main_and_lot_prefixes_plus12_with_original_order'] = True
                    elif observed['status'] == 'FUNCTION_INSTRUMENT_UNAVAILABLE':
                        assert mode == 'YEAR_364_FUNCTION_PROFILE'
                        assert observed['business_command_called'] is False
                        assert observed['forced_business_rollback'] is False
                        assert observed['track_functions_restored']
                        row['function_profile_available'] = False
                    else:
                        assert observed['status'] == 'SQL_ERROR_ROLLED_BACK'
                else:
                    assert response['status'] == 500 and response['body'].get('code') == '57014', (
                        'DIAGNOSTIC_UNEXPECTED_HTTP_RESPONSE', response['status'], response['body'].get('code'))
                    row.update(status='ACTUAL_HTTP_STATEMENT_TIMEOUT', sqlstate='57014')
                if mode == 'YEAR_364_FUNCTION_PROFILE' and response['status'] == 200 and \
                        row['status'] != 'FUNCTION_INSTRUMENT_UNAVAILABLE':
                    assert row['instrument_track_functions'] == 'all' and row['track_functions_restored']
                    row['function_profile'] = function_profile.summarize(
                        row['function_counters_before'], row['function_counters_after'],
                        row['function_root_oid'], command_completed=row['function_command_completed'])
                    row['function_profile_available'] = True
                with http.connect() as conn, conn.cursor() as cur:
                    assert cases.snapshot(cur) == before, 'ACTUAL_YEAR_HTTP_FULL_ROLLBACK_MISMATCH'
                    assert cases.unchanged_facts(cur, fixture['sale']) == root_facts
                    assert cases.ownership.verify(cur) == native_definitions_before
                    conn.rollback()
                row['exact_full_Native_and_private_rollback'] = True
                measurements.append(row)
                print('CP7_NOTE_ACTUAL_HTTP_DIAGNOSTIC ' + json.dumps(row), flush=True)
            restored_identity = user.rpc(RPC, dict(p_mode='IDENTITY_ONLY', p_payload=None,
                                                  p_request=None, p_expected=None))
            assert restored_identity['status'] == 200
            assert restored_identity['body']['track_functions'] == identity['body']['track_functions']
            assert restored_identity['body']['statement_timeout'] == '8s'
            assert restored_identity['body']['session_user'] == 'authenticator'
            assert restored_identity['body']['invoker_role'] == 'authenticated'
        finally:
            if installed:
                with instrument_connection(http) as conn, conn.cursor() as cur:
                    instrument_identity(cur)
                    cur.execute('drop function ' + SIGNATURE)
                    cur.execute('drop function ' + OBSERVER_SIGNATURE)
                    cur.execute('drop function ' + TRACK_SIGNATURE)
                    cur.execute("notify pgrst,'reload schema'")
                    conn.commit()
                    assert canonical_public_state(native.public_state(cur)) == public_before
                    assert cases.ownership.verify(cur) == native_definitions_before
                    conn.rollback()
        return dict(status='PASS', diagnostic_emission_only=True, product_qualification=False,
                    Native_exit_case_credit=0, measurements=measurements,
                    temporary_RPC_and_public_catalog_restored=True,
                    function_profile_parser_sha256=profile_parser_sha256,
                    request_local_tracking_and_actual_identity_restored=True,
                    anonymous_tracking_helper_denied=True,
                    tracker_installation=tracker_installation,
                    same_UUID_payload_version_and_full_rollback_each_pair=True,
                    default_real_timeout_and_every_Native_guard_unchanged=True)
    return [('NOTE_ACTUAL_AUTH_POSTGREST_DEFAULT_VS_JIT_EMISSION', emission)]
