"""Unexecuted real-Auth HTTP and two-session date-setting cases.

The owning qualifier must admit FREE3, install the complete component, restore
each committed race copy and own real Auth cleanup. No connection, ERP import,
fake JWT signing, role promotion or execution occurs on module load.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from threading import Barrier
from time import monotonic,sleep
from types import SimpleNamespace
import gzip,json,subprocess,uuid

READ='erp_cp7_get_good_policy_dates_v1'
WRITE='erp_cp7_save_good_policy_date_v1'
PAGE=dict(before_version=None,before_date=None)
HTTP_IDS=(
    'NONPAYABLE_AUTH_HTTP_OWNER_ADMIN_DENIAL_REPLAY_CANCEL_AND_STALE_TIMELINE',
    'NONPAYABLE_AUTH_HTTP_CACHED_REPLAY_OWNER_DEACTIVATED_DURING_REAL_LOCK_WAIT',
)
RACE_IDS=(
    'NONPAYABLE_TWO_SESSION_SAME_REQUEST_ONE_IMMUTABLE_DATE_AND_REPLY',
    'NONPAYABLE_TWO_SESSION_DIFFERENT_REQUESTS_ONE_DATE_AND_ONE_STALE_TIMELINE',
)
ALLOWED_DATE_TABLES={'cp7_accessory_nonpayable.category_versions_v1','cp7_accessory_nonpayable.date_requests_v1'}
ORIGINAL_BASE='0da4d79a4f7201ef053d6de1eb155d990b4bfa4d'
ORIGINALS={'scripts/cp7_master_cases.py': (45605, 'e8340084c8a302391149a789ceb26126a0dc3ef132d4df3486e0c1b1235d8ef5'), 'scripts/current-s03-sku-s05-composite-qualification/modes.py': (23300, '5f4f45edcc99d24987908369fbec687f8373c6ffb37ce01d5e0fe63d79c6afb4')}


def source_controls():
    from . import native_fixture
    fixture=native_fixture.source_controls();root=Path(__file__).resolve().parents[2]
    for name,pin in ORIGINALS.items():
        raw=(root/name).read_bytes()
        if (len(raw),sha256(raw).hexdigest())!=pin or raw!=subprocess.check_output(
            ['/usr/bin/git','-C',str(root),'show',ORIGINAL_BASE+':'+name]):
            raise ValueError('NONPAYABLE_ACCESS_ORIGINAL_CHANGED:'+name)
    if len(set(HTTP_IDS+RACE_IDS))!=4:raise ValueError('NONPAYABLE_FOUR_UNIQUE_ACCESS_IDS_REQUIRED')
    return dict(status='FOUR_ACCESS_CASES_SOURCE_PREPARED_NOT_EXECUTED',HTTP_case_ids=list(HTTP_IDS),
        two_database_session_case_ids=list(RACE_IDS),additional_original_source_files=len(ORIGINALS),
        Native_fixture_sources=fixture,actual_SQL_executed=0,actual_Auth_HTTP_cases=0,
        actual_two_session_cases=0,production_go=False,independent_acceptance=False)

def context(cur,state,mode):
    from . import admission,native_fixture,settings_stage
    admission.parent_receipt()  # Before domain imports, cursor or tool use.
    source_controls()
    names={'HTTP':'cp6_auditor_http','RACE':'cp6_auditor_race'}
    if mode not in names:raise ValueError('NONPAYABLE_EXPLICIT_ACCESS_COPY_MODE_REQUIRED')
    connection=cur.connection
    if (connection.info.host not in('127.0.0.1','localhost')or connection.info.port!=54322
        or cur.execute('select current_database()').fetchone()!=(names[mode],)):
        raise ValueError('NONPAYABLE_ACCESS_DISPOSABLE_COPY_ONLY')
    from cp7_p21_current_chain_rehearsal_probe import helper
    import cp6_bc_probe as bc
    import cp7_master_cases as master
    bc.api.admin(cur)
    with helper.control.product_catalog(cur):settings_stage.verify(cur,state)
    return SimpleNamespace(bc=bc,master=master,product=settings_stage,control=helper.control)

def payload(workspace,day,reason):
    return dict(contract_version='cp7.good-policy-date-command.v1',actor=workspace['actor'],
        access_epoch=workspace['access_epoch'],effective_from=str(day),
        source_event_id=workspace['current_source']['id'],expected_current_version=workspace['current_source']['version'],
        expected_timeline=workspace['timeline_token'],reason=reason,reviewed=True)

def send(user,body,request,*,cancel=False):
    return user.rpc(WRITE,dict(p_payload=body,p_request=str(request),p_cancel=cancel))

def ok(reply):
    if reply.get('status')!=200 or not isinstance(reply.get('body'),dict):
        raise ValueError('NONPAYABLE_ACTUAL_HTTP_SUCCESS_REQUIRED:'+json.dumps(reply,default=str)[:1500])
    return reply['body']

def denied(reply,code,sqlstate=None):
    body=reply.get('body')
    if (reply.get('status',0)<400 or not isinstance(body,dict)or code not in body.get('message','')
        or(sqlstate is not None and body.get('code')!=sqlstate)):
        raise ValueError('NONPAYABLE_EXACT_HTTP_REFUSAL_REQUIRED:'+json.dumps(reply,default=str)[:1500])
    return reply

def capture(cur,modules,state):
    modules.bc.api.admin(cur)
    with modules.control.product_catalog(cur):
        modules.product.verify(cur,state);catalog=modules.product.runtime()[-1]
        groups=catalog._catalog_rows(cur);data=catalog._data(cur)
    if len(groups)!=22:raise ValueError('NONPAYABLE_ACCESS_FULL_RAW_ALL22_REQUIRED')
    return dict(catalog=groups,data_and_all_sequences=data,
        date_versions=[r[0]for r in cur.execute('select to_jsonb(v)from cp7_accessory_nonpayable.category_versions_v1 v order by id').fetchall()],
        date_requests=[r[0]for r in cur.execute('select to_jsonb(r)from cp7_accessory_nonpayable.date_requests_v1 r order by request_id').fetchall()])

def require_changes(before,after,allowed=()):
    a,b=before['data_and_all_sequences'],after['data_and_all_sequences']
    changed={k for k in a if a[k]!=b.get(k)}
    if before['catalog']!=after['catalog']or set(a)!=set(b)or not changed.issubset(set(allowed)):
        raise ValueError('NONPAYABLE_ACCESS_UNEXPECTED_CATALOG_ROW_OR_SEQUENCE_CHANGE:'+str(sorted(changed)))
    if not allowed and before!=after:
        raise ValueError('NONPAYABLE_ACCESS_NO_EFFECT_REQUIRES_ALL_ROWS_AND_DATE_LEDGERS_EQUAL')
    return sorted(changed)

def require_append(before,after,section,key,added_keys):
    old={r[key]:r for r in before[section]};new={r[key]:r for r in after[section]}
    wanted=set(added_keys)
    if (len(old)!=len(before[section])or len(new)!=len(after[section])or set(old)&wanted
        or set(new)!=set(old)|wanted or any(new.get(k)!=v for k,v in old.items())):
        raise ValueError('NONPAYABLE_ACCESS_EXACT_APPEND_ONLY_HISTORY_REQUIRED:'+section)

def retain(label,before,after,allowed=()):
    changed=require_changes(before,after,allowed)
    # Keep the complete, unprojected census once, rather than repeating it in
    # every log line. The owning canonical archive must include this original.
    root=Path(__file__).resolve().parents[2]/'cp6-proof/t3';root.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(dict(before=before,after=after),sort_keys=True,default=str)+'\n').encode()
    packed=gzip.compress(raw,mtime=0);name='AFUI_ACCESS_'+label+'_'+uuid.uuid4().hex+'_FULL_CENSUS.json.gz'
    target=root/name
    with target.open('xb')as stream:stream.write(packed)
    return dict(status='PASS',actual_all22_groups=22,dropped_catalog_or_data_or_sequence_keys=[],
        actual_changed_tables=changed,allowed_tables=sorted(allowed),
        original=dict(name=name,bytes=len(raw),sha256=sha256(raw).hexdigest(),gzip_bytes=len(packed),gzip_sha256=sha256(packed).hexdigest()))

def http_capture(http,state):
    with http.connect(connect_timeout=5)as conn,conn.cursor()as cur:
        modules=context(cur,state,'HTTP');value=capture(cur,modules,state);conn.rollback();return value

def http_matrix(http,today,state):
    owner=http.login('OWNER','afui-date-owner');admin=http.login('ADMIN','afui-date-admin')
    auditor=http.login('AUDITOR_VIEW_ONLY','afui-date-auditor');warehouse=http.login('GUDANG','afui-date-warehouse')
    before=http_capture(http,state)
    workspace=ok(owner.rpc(READ,dict(p_payload=PAGE)));admin_workspace=ok(admin.rpc(READ,dict(p_payload=PAGE)))
    if workspace['can_write']is not True or admin_workspace['can_write']is not False:
        raise ValueError('NONPAYABLE_REAL_OWNER_WRITE_ADMIN_READ_ONLY_REQUIRED')
    refusals={role:denied(user.rpc(READ,dict(p_payload=PAGE)),'NONPAYABLE_SETTINGS_DENIED','42501')
        for role,user in(('AUDITOR_VIEW_ONLY',auditor),('GUDANG',warehouse))}
    anon=http.anon_rpc(READ,dict(p_payload=PAGE))
    if anon.get('status',0)<400:raise ValueError('NONPAYABLE_ANONYMOUS_DATE_WORKSPACE_MUST_REFUSE')
    admin_denied=denied(send(admin,payload(admin_workspace,today,'Admin cannot confirm GOOD date'),uuid.uuid4()),
        'NONPAYABLE_OWNER_DATE_REQUIRED','42501')
    reads_proof=retain('HTTP_ROLE_MATRIX',before,http_capture(http,state))
    request=uuid.uuid4();body=payload(workspace,today,'Actual Auth owner explicitly confirms GOOD date')
    first=ok(send(owner,body,request))
    if first['status']!='SAVED'or first['request_id']!=str(request):raise ValueError('NONPAYABLE_REAL_HTTP_DATE_SAVE_REQUIRED')
    saved=http_capture(http,state);save_proof=retain('HTTP_OWNER_SAVE',before,saved,ALLOWED_DATE_TABLES)
    versions=[r for r in saved['date_versions']if r['request_id']==str(request)]
    ledger=[r for r in saved['date_requests']if r['request_id']==str(request)]
    if (len(versions)!=1 or len(ledger)!=1 or ledger[0]['response']!=first or ledger[0]['request_body']!=body
        or versions[0]['id']!=first['id']or versions[0]['effective_from']!=str(today)
        or str(versions[0]['source_version'])!=workspace['current_source']['version']):
        raise ValueError('NONPAYABLE_REAL_HTTP_SAVE_MUST_HAVE_ONE_EXACT_DATE_AND_REQUEST')
    require_append(before,saved,'date_versions','id',[first['id']])
    require_append(before,saved,'date_requests','request_id',[str(request)])
    replay=ok(send(owner,body,request));late_cancel=ok(send(owner,body,request,cancel=True))
    changed=denied(send(owner,dict(body,reason='Changed intent on existing request'),request),
        'NONPAYABLE_DATE_REQUEST_INTENT_CHANGED','P0001')
    stale=denied(send(owner,dict(body,effective_from=str(today+timedelta(days=1))),uuid.uuid4()),
        'NONPAYABLE_TIMELINE_STALE','P0001')
    if replay!=first or late_cancel!=first:raise ValueError('NONPAYABLE_REAL_REPLAY_AND_LATE_CANCEL_MUST_RETURN_ORIGINAL_SUCCESS')
    replay_proof=retain('HTTP_REPLAY_STALE_AND_CHANGED_INTENT',saved,http_capture(http,state))
    cancel_request=uuid.uuid4();cancel_body=dict(body,reason='Owner cancels absent uncertain date request')
    cancelled=ok(send(owner,cancel_body,cancel_request,cancel=True))
    after_cancel=http_capture(http,state)
    if cancelled['status']!='CANCELLED'or after_cancel['date_versions']!=saved['date_versions']:
        raise ValueError('NONPAYABLE_REAL_ABSENT_CANCEL_MUST_ONLY_ADD_TOMBSTONE')
    require_append(saved,after_cancel,'date_requests','request_id',[str(cancel_request)])
    cancel_proof=retain('HTTP_ABSENT_CANCEL',saved,after_cancel,{'cp7_accessory_nonpayable.date_requests_v1'})
    if ok(send(owner,cancel_body,cancel_request))!=cancelled:
        raise ValueError('NONPAYABLE_REAL_LATE_REQUEST_MUST_REPLAY_CANCELLED')
    late_proof=retain('HTTP_LATE_CANCELLED_SAVE',after_cancel,http_capture(http,state))
    return dict(status='PASS',real_Auth_HTTP=True,owner_auth_user_id=owner.auth_user_id,
        admin_read_only=True,role_refusals=refusals,admin_write_refusal=admin_denied,anonymous_status=anon['status'],
        original_success=first,actual_replay=replay,late_cancel=late_cancel,changed_intent_refusal=changed,
        stale_timeline_refusal=stale,cancellation=cancelled,
        complete_census_proofs=[reads_proof,save_proof,replay_proof,cancel_proof,late_proof],
        physical_GOOD_stock_HPP_journal_payroll_and_BC_source_unchanged=True,
        actual_Native_case_credit=0,actual_browser_case_credit=0,full_copy_restore_and_real_Auth_cleanup_required=True)

def http_revoke_wait(http,today,state):
    owner=http.login('OWNER','afui-date-wait-owner')
    workspace=ok(owner.rpc(READ,dict(p_payload=PAGE)))
    body=payload(workspace,today+timedelta(days=1),'Actual Auth cached request permission wait')
    request=uuid.uuid4();cached=ok(send(owner,body,request))
    if cached['status']!='SAVED':raise ValueError('NONPAYABLE_REAL_CACHED_DATE_REQUIRED')
    # Only this one HTTP request can wait on this dedicated copy. Its actual
    # PostgREST backend must be observed blocked by our exact holder PID.
    observed=None;answer=None;proof=None;access_fixture=None
    with http.connect(connect_timeout=5)as holder,holder.cursor()as hcur:
        modules=context(hcur,state,'HTTP')
        holder_pid=hcur.execute('select pg_backend_pid()').fetchone()[0]
        hcur.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
        with ThreadPoolExecutor(max_workers=1)as pool:
            future=pool.submit(send,owner,body,request)
            try:
                deadline=monotonic()+8
                while monotonic()<deadline:
                    with http.connect(connect_timeout=5)as conn,conn.cursor()as cur:
                        context(cur,state,'HTTP')
                        rows=cur.execute("select pid,wait_event_type,wait_event,query from pg_stat_activity "
                            "where datname='cp6_auditor_http'and %s=any(pg_blocking_pids(pid)) "
                            "and query ilike '%%erp_cp7_save_good_policy_date_v1%%'",(holder_pid,)).fetchall()
                        conn.rollback()
                    if len(rows)==1:observed=dict(pid=rows[0][0],wait_event_type=rows[0][1],wait_event=rows[0][2],actual_query=rows[0][3]);break
                    if future.done():raise ValueError('NONPAYABLE_CACHED_REPLAY_RETURNED_BEFORE_REAL_WAIT')
                    sleep(.1)
                if observed is None:raise ValueError('NONPAYABLE_ACTUAL_HTTP_BACKEND_LOCK_WAIT_REQUIRED')
                with http.connect(connect_timeout=5)as conn,conn.cursor()as cur:
                    context(cur,state,'HTTP')
                    row=cur.execute("select u.id::text,u.is_active,r.role_code from erp.app_users u "
                        "join erp.app_roles r on r.id=u.role_id where u.auth_user_id=%s for update of u",(owner.auth_user_id,)).fetchone()
                    if row is None or row[1:]!=(True,'OWNER'):raise ValueError('NONPAYABLE_EXACT_REAL_AUTH_OWNER_ACCESS_FIXTURE_REQUIRED')
                    cur.execute('update erp.app_users set is_active=false where id=%s',(row[0],));conn.commit()
                    access_fixture=dict(app_user_id=row[0],auth_user_id=owner.auth_user_id,role='OWNER',before_active=True,after_active=False)
                revoked=http_capture(http,state)
            finally:
                holder.rollback()  # Always release before joining the HTTP worker.
            answer=denied(future.result(timeout=25),'NONPAYABLE_SETTINGS_DENIED','42501')
            proof=retain('HTTP_REVOKED_CACHED_REPLAY',revoked,http_capture(http,state))
    return dict(status='PASS',real_Auth_HTTP=True,cached_original=cached,holder_pid=holder_pid,
        actual_blocked_PostgREST_backend=observed,administrative_access_fixture=access_fixture,
        actual_refusal_after_wait=answer,complete_noeffect_after_access_commit=proof,
        actual_same_request_uuid=str(request),permission_checked_before_cached_reply=True,
        fixture_is_not_role_editor_UI_or_Native_financial_case=True,
        actual_Native_case_credit=0,actual_browser_case_credit=0,full_copy_restore_and_real_Auth_cleanup_required=True)

def sql_read(cur,modules,subject):
    modules.bc.session(cur,subject)
    value=cur.execute('select public.erp_cp7_get_good_policy_dates_v1(%s::jsonb)',(json.dumps(PAGE),)).fetchone()[0]
    modules.bc.api.admin(cur);return value

def race(tools,today,state,*,same_request):
    with tools.connect(connect_timeout=5)as conn,conn.cursor()as cur:
        modules=context(cur,state,'RACE');subject=modules.master.role_actor(cur,'OWNER')
        workspace=sql_read(cur,modules,subject)
        body=payload(workspace,today,'Two real sessions confirm one reviewed GOOD date')
        before=capture(cur,modules,state);conn.commit()
    barrier=Barrier(2);request=str(uuid.uuid4());requests=[request,request if same_request else str(uuid.uuid4())]
    def worker(key):
        from psycopg import Error
        with tools.connect(connect_timeout=5)as conn,conn.cursor()as cur:
            modules=context(cur,state,'RACE')
            cur.execute("set local lock_timeout='8s';set local statement_timeout='15s'")
            backend=cur.execute('select pg_backend_pid()').fetchone()[0]
            barrier.wait(timeout=8)
            try:
                modules.bc.session(cur,subject)
                value=cur.execute('select public.erp_cp7_save_good_policy_date_v1(%s::jsonb,%s,false)',(json.dumps(body),key)).fetchone()[0]
                conn.commit();return dict(ok=True,result=value,backend_pid=backend,request_id=key)
            except Error as error:
                conn.rollback();return dict(ok=False,sqlstate=error.sqlstate,message=error.diag.message_primary,backend_pid=backend,request_id=key)
    with ThreadPoolExecutor(max_workers=2)as pool:
        pending=[pool.submit(worker,key)for key in requests];results=[p.result(timeout=25)for p in pending]
    winners=[r for r in results if r['ok']];losers=[r for r in results if not r['ok']]
    if len({r['backend_pid']for r in results})!=2:raise ValueError('NONPAYABLE_TWO_DISTINCT_ACTUAL_DATABASE_SESSIONS_REQUIRED')
    if same_request:
        if len(winners)!=2 or winners[0]['result']!=winners[1]['result']:
            raise ValueError('NONPAYABLE_SAME_REQUEST_TWO_SESSION_EXACT_REPLAY_REQUIRED:'+str(results))
    elif(len(winners)!=1 or len(losers)!=1 or losers[0]['sqlstate']!='P0001'
         or not losers[0]['message'].startswith('NONPAYABLE_TIMELINE_STALE:')):
        raise ValueError('NONPAYABLE_TWO_REQUESTS_REQUIRE_ONE_WINNER_AND_ONE_EXACT_STALE_REFUSAL:'+str(results))
    with tools.connect(connect_timeout=5)as conn,conn.cursor()as cur:
        modules=context(cur,state,'RACE');after=capture(cur,modules,state);conn.rollback()
    new_versions=[v for v in after['date_versions']if v['request_id']in requests]
    new_requests=[v for v in after['date_requests']if v['request_id']in requests]
    if (len(new_versions)!=1 or len(new_requests)!=1 or new_requests[0]['response']!=winners[0]['result']
        or new_requests[0]['request_body']!=body or new_versions[0]['id']!=winners[0]['result']['id']
        or any(r['result'].get('status')!='SAVED'for r in winners)):
        raise ValueError('NONPAYABLE_TWO_SESSION_MUST_HAVE_ONE_IMMUTABLE_DATE_AND_REQUEST')
    require_append(before,after,'date_versions','id',[new_versions[0]['id']])
    require_append(before,after,'date_requests','request_id',[new_requests[0]['request_id']])
    return dict(status='PASS',actual_two_database_sessions=True,administrative_actor_not_real_Auth=True,
        actor_subject=subject,results=results,actual_versions=new_versions,actual_requests=new_requests,
        complete_census=retain('TWO_SESSION_'+('SAME_REQUEST'if same_request else'STALE_TIMELINE'),before,after,ALLOWED_DATE_TABLES),
        actual_Auth_HTTP_case_credit=0,actual_Native_case_credit=0,actual_browser_case_credit=0,
        full_copy_restore_before_and_after_each_race_required=True)

def http_cases(http,today,*,state):
    from . import admission
    admission.parent_receipt()
    return[(HTTP_IDS[0],lambda:http_matrix(http,today,state)),
           (HTTP_IDS[1],lambda:http_revoke_wait(http,today,state))]

def races(tools,today,*,state):
    from . import admission
    admission.parent_receipt()
    return[(RACE_IDS[0],lambda:race(tools,today,state,same_request=True)),
           (RACE_IDS[1],lambda:race(tools,today,state,same_request=False))]
