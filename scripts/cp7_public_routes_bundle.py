"""R4-01 (Astra ASTRA-R3-01, S1): the older public routes that write or read beside the CP7 facades are closed to the Data API.

Astra proved that the CP4 wrappers public.erp_create/activate_attendance_hpp_pool_v1, still EXECUTE-able by the browser
role, created and activated a pool in a closed period and after the manage right was revoked, while the CP7 facade
refused both. The family (scripts/r4 inventory of the installed stack, 69 public non-CP7 functions EXECUTE-able by
`authenticated`): 40 are what the CP7 app calls (KEEP), 4 are the personal reminder routes that two CP7 layers call from
inside (REMINDER, kept: own-user rows, the Native writer checks the actor), and these 25 are not called by the app and
either have a stricter CP7 facade over the same Native writer or no screen at all (CLOSED).

Owner D14-9 lets the revoke of direct `erp` EXECUTE wait for CP7C only while those paths are not reachable from the
internet; a public route is reachable through the Data API (PostgREST), whose connections log in as `authenticator`. So
each CLOSED function keeps its definition, grants and Native call, and gets one first statement: refuse when the session
is a Data API session (session_user = 'authenticator', every browser and API-key request). A database session opened
with database credentials (operator, migration, test fixture) is unchanged; the direct-SQL boundary stays the CP7C
revoke batch (FABLE-012, D14-9). Install patches the captured definitions (anchor checked, like HPP01); uninstall restores
them through the same `originals` every F03 installer already replays, so no grant is touched.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = ('cp7_public_routes',)
SCHEMA = 'cp7_public_routes'
HELPER = 'cp7_public_routes.refuse_data_api(text)'
REFUSAL = 'CP7_PUBLIC_ROUTE_CLOSED'
# name -> why it is closed (the CP7 route the app uses instead, or none).
CLOSED = {
    'public.erp_create_attendance_hpp_pool_v1(jsonb,uuid)': 'erp_cp7_save_hpp_pool_v1',
    'public.erp_activate_attendance_hpp_pool_v1(uuid,text,uuid,bigint)': 'erp_cp7_save_hpp_pool_v1',
    'public.erp_cancel_attendance_hpp_pool_v1(uuid,text,uuid,bigint)': 'erp_cp7_save_hpp_pool_v1',
    'public.erp_preview_attendance_hpp_pool_v1(date,date)': 'erp_cp7_get_hpp_pools_v1',
    'public.erp_close_accounting_through_v1(date,text)': 'erp_cp7_save_period_control_v1',
    'public.erp_accounting_close_preflight_v1(date)': 'erp_cp7_get_period_control_v1',
    'public.erp_save_attendance_period_v1(jsonb,uuid,bigint,boolean)': 'erp_cp7_save_attendance_v1',
    'public.erp_post_attendance_period_v1(uuid,text,uuid,bigint)': 'erp_cp7_save_attendance_v1',
    'public.erp_reverse_attendance_period_v1(uuid,text,uuid,bigint)': 'erp_cp7_save_attendance_v1',
    'public.erp_get_attendance_workspace_v1(uuid,date,date,boolean)': 'erp_cp7_get_attendance_v1',
    'public.erp_save_worker_roster_v1(jsonb,uuid,bigint)': 'erp_cp7_save_roster_v1',
    'public.erp_set_worker_daily_rate_v1(uuid,numeric,date,text,uuid,bigint)': 'erp_cp7_save_roster_v1',
    'public.erp_record_sewing_terminal_v1(jsonb,uuid)': 'erp_cp7_save_sewing_completion_v1',
    'public.erp_reverse_sewing_terminal_v1(uuid,text,uuid)': 'erp_cp7_save_sewing_completion_v1',
    'public.erp_reverse_sewing_terminal_v1(uuid,text,uuid,bigint)': 'erp_cp7_save_sewing_completion_v1',
    'public.erp_set_contractor_hpp_policy_v1(jsonb,uuid,uuid)': 'erp_cp7_save_master_v1 (MANDOR)',
    'public.erp_post_final_sku_allocation_v1(jsonb,uuid,bigint)': 'erp_save_laundry_qc_action_v1 (POST_FINAL_SKU, same Native writer)',
    'public.erp_assign_pattern_v1(uuid,uuid,text,uuid,bigint)': 'none (no screen)',
    'public.erp_post_fg_unsourced_receipt_v1(jsonb,uuid)': 'none (no screen)',
    'public.erp_reverse_fg_unsourced_receipt_v1(uuid,text,uuid)': 'none (no screen)',
    'public.erp_preview_fg_unsourced_value_v1(uuid,timestamp with time zone)': 'none (no screen)',
    'public.erp_set_fg_stock_policy_v1(uuid,uuid,text,numeric,numeric,integer,date,text,uuid,uuid)': 'none (no screen)',
    'public.erp_set_laundry_rate_owner_estimate_v1(uuid,numeric,text)': 'none (no screen)',
    'public.erp_get_fg_stock_explainability_v1(uuid,uuid)': 'none (no screen)',
    'public.erp_get_cutting_workspace_v1(text,uuid,integer,integer)': 'erp_get_cutting_workspace_v2',
}
# Called by CP7 layers from inside (scripts/cp7-src/manual-reminders/facade.sql, reminders/attention.sql) and kept open.
REMINDER = ('public.erp_save_my_reminder_v1(jsonb,uuid,bigint)', 'public.erp_set_my_reminder_done_v1(uuid,boolean,uuid,bigint)',
            'public.erp_cancel_my_reminder_v1(uuid,text,uuid,bigint)', 'public.erp_list_my_reminders_v1(text,integer)')
# The public non-CP7 routes the CP7 app calls (src/ .rpc names); every other public function a browser role may execute
# must be CLOSED, a REMINDER, or erp_cp7_*. A new one fails verify() until it is reviewed here.
KEEP = (
    'public.erp_deactivate_pattern_v1(uuid,text,uuid,bigint)', 'public.erp_deactivate_role_v1(uuid,text,uuid,bigint)',
    'public.erp_get_access_admin_v1()', 'public.erp_get_accessory_issue_workspace_v1(jsonb)',
    'public.erp_get_accessory_service_workspace_v1(jsonb)', 'public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)',
    'public.erp_get_cutting_pickup_queue_v1(text,uuid,text,integer,integer)',
    'public.erp_get_cutting_workspace_v2(text,uuid,integer,integer,text,integer,integer,text,integer,integer,uuid,uuid)',
    'public.erp_get_initial_import_workspace_v1(uuid)', 'public.erp_get_laundry_bd_workspace_v1(jsonb)',
    'public.erp_get_laundry_history_v1(jsonb)', 'public.erp_get_laundry_qc_workspace_v1(text,text)', 'public.erp_get_my_access_v1()',
    'public.erp_get_pocket_fabric_workspace_v1(text)', 'public.erp_get_pocket_periods_v1(text,integer)',
    'public.erp_get_product_conversion_workspace_v1(jsonb)', 'public.erp_get_sku_hpp_v1(jsonb)', 'public.erp_get_sku_workspace_v1(jsonb)',
    'public.erp_get_supplier_credit_v1(jsonb)', 'public.erp_get_wip_control_v1(text,uuid,text,text)',
    'public.erp_list_patterns_v1(text,text,integer,integer)', 'public.erp_preview_pocket_fabric_period_v1(date,date)',
    'public.erp_save_accessory_issue_action_v1(text,jsonb,uuid)', 'public.erp_save_accessory_service_action_v1(text,jsonb,uuid)',
    'public.erp_save_app_user_v3(jsonb,uuid,bigint)', 'public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)',
    'public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)', 'public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint)',
    'public.erp_save_initial_import_action_v1(text,jsonb,uuid)', 'public.erp_save_laundry_bd_action_v1(text,jsonb,uuid)',
    'public.erp_save_laundry_qc_action_v1(text,jsonb,uuid,bigint)', 'public.erp_save_pattern_v1(jsonb,uuid,bigint)',
    'public.erp_save_pocket_fabric_action_v1(text,jsonb,uuid)', 'public.erp_save_product_conversion_action_v1(text,jsonb,uuid)',
    'public.erp_save_role_v1(jsonb,uuid,bigint)', 'public.erp_save_sku_action_v1(text,jsonb,uuid)', 'public.erp_save_supplier_credit_v1(jsonb,uuid)',
    'public.erp_search_final_sku_products_v1(uuid,timestamptz,text,text,integer)',
    'public.erp_search_laundry_bs_products_v1(uuid,timestamptz,text,text,integer)', 'public.erp_set_wip_control_flag_v1(jsonb,uuid,bigint)',
)
MARK = '-- R4-01 (cp7_public_routes_bundle.py): closed to the Data API.'


def app_routes():
    """The non-CP7 public routes the app names (string literals in src/, tests and generated types left out)."""
    names = set()
    for path in sorted((ROOT / 'src').rglob('*.ts*')):
        if '.test.' not in path.name and 'types' not in path.relative_to(ROOT / 'src').parts:
            names |= set(re.findall(r"""['"`](erp_[a-z0-9_]+_v[0-9]+)['"`]""", path.read_text()))
    return sorted(n for n in names if not n.startswith('erp_cp7_'))


def route(signature):
    return signature.split('.', 1)[1].split('(', 1)[0]


def patched(signature, definition):
    """The captured definition with the refusal as its first statement (the same edit the install's DO block makes)."""
    head, sep, body = definition.partition('AS $function$')
    assert sep and definition.count('AS $function$') == 1 and body.count('$function$') == 1, ('R4_01_ROUTE_SOURCE_CHANGED', signature)
    language = re.search(r'\n LANGUAGE (\w+)', head)
    assert language and language.group(1) in ('sql', 'plpgsql'), ('R4_01_ROUTE_LANGUAGE', signature)
    if language.group(1) == 'sql':
        return head + sep + "\n select cp7_public_routes.refuse_data_api('" + route(signature) + "'); " + MARK + "\n" + body
    begin = re.search(r'\bbegin\b', body, re.I)
    assert begin, ('R4_01_ROUTE_NO_BEGIN', signature)
    return head + sep + body[:begin.end()] + "\n perform cp7_public_routes.refuse_data_api('" + route(signature) + "'); " + MARK + "\n" + body[begin.end():]


CANONICAL = ("select n.nspname||'.'||p.proname||'('||array_to_string(array(select format_type(t,null) from unnest(p.proargtypes::oid[]) t),',')||')' "
             "from pg_proc p join pg_namespace n on n.oid=p.pronamespace where p.oid=%s::regprocedure")


def capture(cur, originals):
    for signature in CLOSED:
        assert signature not in originals, ('R4_01_ROUTE_ALREADY_CAPTURED', signature)
        # The F03 probes compare definitions keyed by the search_path-free regprocedure text; the key must be that text.
        assert cur.execute(CANONICAL, (signature,)).fetchone()[0] == signature, ('R4_01_ROUTE_KEY_NOT_CANONICAL', signature)
        originals[signature] = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
        patched(signature, originals[signature])


def expected_definitions(originals):
    return {signature: patched(signature, originals[signature]) for signature in CLOSED}


def extension():
    signatures = ',\n  '.join("'" + s + "'" for s in CLOSED)
    return """-- R4-01 (Astra ASTRA-R3-01): the older public routes beside the CP7 facades are closed to the Data API
-- (cp7_public_routes_bundle.py). The refusal is the first statement of each; definitions, grants and Native calls stay.
create role cp7_public_routes nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_public_routes authorization cp7_public_routes;
revoke all on schema cp7_public_routes from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_public_routes to postgres;
-- A Data API session logs in as `authenticator` (PostgREST, every browser or API-key request); it is refused here.
create function cp7_public_routes.refuse_data_api(p_route text)returns void
language plpgsql stable set search_path=''as $$
begin
 if session_user='authenticator'then
  raise exception using errcode='42501',message='""" + REFUSAL + """',detail=p_route,
   hint='Jalur lama ini ditutup untuk aplikasi. Pakai layar ERP yang menulis lewat fasad CP7 (dengan pengaman periode dan hak akses).';
 end if;
end $$;
alter function cp7_public_routes.refuse_data_api(text)owner to postgres;
revoke all on function cp7_public_routes.refuse_data_api(text)from public,anon,authenticated,service_role,cp7_capture,cp7_public_routes;
do $r4routes$
declare signature text;definition text;head text;body text;pos integer;language text;stop integer;
begin
 foreach signature in array array[
  """ + signatures + """]::text[] loop
  definition:=pg_get_functiondef(signature::regprocedure);
  pos:=position('AS $function$' in definition);
  if pos=0 or length(definition)-length(replace(definition,'AS $function$',''))<>length('AS $function$') then
   raise exception 'CP7_R4_01_ROUTE_SOURCE_CHANGED %',signature;end if;
  head:=left(definition,pos-1+length('AS $function$'));body:=substr(definition,pos+length('AS $function$'));
  if length(body)-length(replace(body,'$function$',''))<>length('$function$')then raise exception 'CP7_R4_01_ROUTE_SOURCE_CHANGED %',signature;end if;
  select l.lanname into language from pg_proc p join pg_language l on l.oid=p.prolang where p.oid=signature::regprocedure;
  if language='sql'then
   definition:=head||E'\\n select cp7_public_routes.refuse_data_api('''||split_part(split_part(signature,'.',2),'(',1)||'''); """ + MARK + """'||E'\\n'||body;
  elsif language='plpgsql'then
   stop:=regexp_instr(body,'\\mbegin\\M',1,1,1,'i');
   if stop=0 then raise exception 'CP7_R4_01_ROUTE_NO_BEGIN %',signature;end if;
   definition:=head||left(body,stop-1)||E'\\n perform cp7_public_routes.refuse_data_api('''||split_part(split_part(signature,'.',2),'(',1)||'''); """ + MARK + """'||E'\\n'||substr(body,stop);
  else raise exception 'CP7_R4_01_ROUTE_LANGUAGE %',signature;end if;
  execute definition;
 end loop;
end $r4routes$;
"""


EXECUTABLE = r"""
select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where n.nspname='public' and p.proname like 'erp\_%' and p.proname not like 'erp\_cp7\_%'
  and (has_function_privilege('authenticated',p.oid,'EXECUTE') or has_function_privilege('anon',p.oid,'EXECUTE')) order by 1
"""


def verify(cur):
    for signature in CLOSED:
        definition = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
        assert definition.count(MARK) == 1 and "refuse_data_api('" + route(signature) + "')" in definition, ('R4_01_ROUTE_NOT_CLOSED', signature)
        # The refusal runs with the function owner's rights (the helper has no grant), so the route must stay SECURITY DEFINER.
        assert cur.execute('select p.prosecdef and has_function_privilege(p.proowner,%s::regprocedure,%s) from pg_proc p where p.oid=%s::regprocedure',
                           (HELPER, 'EXECUTE', signature)).fetchone()[0], ('R4_01_ROUTE_OWNER_CANNOT_REFUSE', signature)
    row = cur.execute("select pg_get_userbyid(p.proowner),p.prosecdef,p.proconfig,has_function_privilege('authenticated',p.oid,'EXECUTE') "
                      "from pg_proc p where p.oid=%s::regprocedure", (HELPER,)).fetchone()
    assert row == ('postgres', False, ['search_path=""'], False), ('R4_01_HELPER', row)
    assert cur.execute('select rolcanlogin,rolinherit,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls from pg_roles where rolname=%s',
                       (ROLES[0],)).fetchone() == (False, False, False, False, False, False, False)
    # Every public non-CP7 route the browser roles (authenticated, anon) may execute is reviewed: the app's, the reminder
    # routes, or closed.
    executable = {r[0] for r in cur.execute(EXECUTABLE).fetchall()}
    canonical = lambda names: {r[0] for r in cur.execute('select x::regprocedure::text from unnest(%s::text[]) x', (list(names),)).fetchall()}
    unreviewed = sorted(executable - canonical(KEEP) - canonical(REMINDER) - canonical(CLOSED))
    assert not unreviewed, ('R4_01_UNREVIEWED_PUBLIC_ROUTE', unreviewed)
    return dict(closed_to_data_api=len(CLOSED), kept_app_routes=len(KEEP), kept_reminder_routes=len(REMINDER),
                executable_by_browser_roles=len(executable))
