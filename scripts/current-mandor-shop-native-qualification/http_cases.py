"""Real Auth/PostgREST Mandor cases on the owning disposable HTTP copy.

Tokens come from the unchanged Auth login helper. SQL connections only inspect
complete state and prepare the one explicitly recorded actor-deactivation
fixture. All reservation/release/read/replay calls use the real HTTP user.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from time import monotonic
import uuid
import access_cases

READ=access_cases.READ
WRITE=access_cases.WRITE
HTTP_IDS=(
 'MANDOR_REAL_AUTH_HTTP_OWNER_RESERVE_REPLAY_RELEASE_AND_CURRENT_ROLE_STALE_REFUSALS',
 'MANDOR_REAL_AUTH_HTTP_CACHED_ALLOCATION_REFUSES_PENDING_AND_COMMITTED_ACCESS_REVOCATION',
)


def require(value,message):
    if not value:raise ValueError(message)


def ok(reply):
    require(reply.get('status')==200 and type(reply.get('body'))is dict,
        'MANDOR_HTTP_EXACT_SUCCESS_REQUIRED:'+str(reply))
    return reply['body']


def denied(reply,message,code):
    require(type(reply.get('status'))is int and reply['status']>=400
        and type(reply.get('body'))is dict and reply['body'].get('message')==message
        and reply['body'].get('code')==code,'MANDOR_HTTP_EXACT_CURRENT_REFUSAL_REQUIRED:'+str(reply))
    return reply


def context(product,state,fixture,user):
    require(user.role=='OWNER'and str(uuid.UUID(user.auth_user_id))==user.auth_user_id,
        'MANDOR_HTTP_REAL_OWNER_ID_REQUIRED')
    return access_cases.Context(product,state,dict(fixture,actor=user.auth_user_id),'HTTP')


def read(user,fixture):
    value=ok(user.rpc(READ,dict(p_payroll=fixture['payroll_id'],p_after=None)))
    require(value['payroll_id']==fixture['payroll_id']and value['can_change']is True,
        'MANDOR_HTTP_REAL_OWNER_SELECTED_PAYROLL_CAPABILITY')
    cards=[r for r in value['cards']if r['sale_id']==fixture['sale_id']]
    require(len(cards)==1,'MANDOR_HTTP_EXACT_CURRENT_INVOICE_CARD')
    return value,cards[0]


def send(user,body,request,action='RESERVE'):
    require(action in('RESERVE','RELEASE'),'MANDOR_HTTP_FIXED_PUBLIC_COMMAND')
    return user.rpc(WRITE,dict(p_action=action,p_payload=body,p_request=str(request)))


def observe(ctx,http):
    with http.connect(connect_timeout=5)as conn,conn.cursor()as cur:
        ctx.verify(cur);value=ctx.snapshot(cur);conn.rollback();return value


def one_reservation(before,after,first,body):
    require(before['invoice']==after['invoice'],'MANDOR_HTTP_RESERVATION_CANNOT_SETTLE_INVOICE')
    require(after['payroll'][0]=='CALCULATED'and Decimal(after['payroll'][1])==Decimal('1900000.00'),
        'MANDOR_HTTP_SINGLE_RESERVATION_EXACT_NET')
    require(first['kind']=='COMMITTED_OUTCOME'and first['invoice_settled_by_this_command']is False,
        'MANDOR_HTTP_UNPAID_RESERVATION_OUTCOME_REQUIRED')
    states=[r for r in after['allocation_states']if r['allocation_id']==first['allocation_id']]
    require(len(states)==1 and states[0]['state']=='RESERVED','MANDOR_HTTP_SINGLE_RESERVED_ALLOCATION')
    require(len(after['deductions'])==len(before['deductions'])+1,'MANDOR_HTTP_ONE_NATIVE_DEDUCTION')
    old={r['request_id']:r for r in before['requests']};new={r['request_id']:r for r in after['requests']}
    require(set(new)==set(old)|{first['request_id']}and all(new[k]==v for k,v in old.items()),
        'MANDOR_HTTP_ONE_IMMUTABLE_REQUEST_APPEND')
    require(new[first['request_id']]['response']==first and new[first['request_id']]['payload']==body,
        'MANDOR_HTTP_EXACT_STORED_PUBLIC_INTENT_AND_REPLY')


def matrix(http,today,product,state,fixture):
    owner=http.login('OWNER','mandor-owner');other=http.login('OWNER','mandor-other-owner')
    warehouse=http.login('GUDANG','mandor-warehouse')
    ctx=context(product,state,fixture,owner);before=observe(ctx,http)
    workspace,card=read(owner,fixture);body=ctx.body(card)
    anonymous=http.anon_rpc(READ,dict(p_payroll=fixture['payroll_id'],p_after=None))
    require(anonymous['status']>=400,'MANDOR_HTTP_ANONYMOUS_PRIVATE_PAYROLL_MUST_REFUSE')
    warehouse_read=denied(warehouse.rpc(READ,dict(p_payroll=fixture['payroll_id'],p_after=None)),
        'CP7_MANDOR_SHOP_ACCESS_DENIED','42501')
    warehouse_write=denied(send(warehouse,body,uuid.uuid4()),'CP7_MANDOR_SHOP_ACCESS_DENIED','42501')
    proofs=[access_cases.retain('HTTP_READ_RIGHTS',before,observe(ctx,http))]
    request=uuid.uuid4();first=ok(send(owner,body,request));held=observe(ctx,http)
    one_reservation(before,held,first,body)
    proofs.append(access_cases.retain('HTTP_RESERVE',before,held,allowed=access_cases.ALLOCATION_TABLES))
    replay=ok(send(owner,body,request));require(replay==first,'MANDOR_HTTP_SAME_UUID_EXACT_REPLAY')
    changed=denied(send(owner,dict(body,amount='100000.01'),request),'CP7_MANDOR_SHOP_REQUEST_CHANGED','P0001')
    stale=denied(send(owner,body,uuid.uuid4()),'CP7_MANDOR_SHOP_REVIEW_CHANGED','P0001')
    other_actor=denied(send(other,body,request),'CP7_MANDOR_SHOP_REVIEW_CHANGED','P0001')
    proofs.append(access_cases.retain('HTTP_REPLAY',held,observe(ctx,http)))
    _,fresh=read(owner,fixture)
    release=dict(contract_version='cp7.mandor-shop-allocation-command.v1',payroll_id=fixture['payroll_id'],
        sale_id=fixture['sale_id'],review_token=fresh['review_token'],allocation_id=first['allocation_id'])
    release_request=uuid.uuid4();released=ok(send(owner,release,release_request,'RELEASE'))
    after=observe(ctx,http)
    require(after['invoice']==before['invoice']and after['deductions']==before['deductions']
        and Decimal(after['payroll'][1])==Decimal('2000000.00'),'MANDOR_HTTP_RELEASE_RESTORES_UNPAID_NET_ONLY')
    row=next(r for r in after['allocation_states']if r['allocation_id']==first['allocation_id'])
    require(row['state']=='RELEASED'and released['allocation_id']==first['allocation_id'],
        'MANDOR_HTTP_EXPLICIT_SAME_ALLOCATION_RELEASE')
    proofs.append(access_cases.retain('HTTP_RELEASE',held,after,allowed=access_cases.ALLOCATION_TABLES))
    require(ok(send(owner,release,release_request,'RELEASE'))==released,'MANDOR_HTTP_EXACT_RELEASE_REPLAY')
    proofs.append(access_cases.retain('HTTP_RELEASE_REPLAY',after,observe(ctx,http)))
    return dict(status='PASS',real_Auth_HTTP=True,owner_auth_user_id=owner.auth_user_id,first=first,
        replay=replay,release=released,warehouse_read_refusal=warehouse_read,warehouse_write_refusal=warehouse_write,
        anonymous_status=anonymous['status'],changed_intent_refusal=changed,stale_refusal=stale,
        other_actor_same_UUID_refusal=other_actor,complete_census_proofs=proofs,
        invoice_settled=False,actual_Native_case_credit=0,actual_two_session_case_credit=0,actual_browser_case_credit=0)


def cached_revocation(http,today,product,state,fixture):
    owner=http.login('OWNER','mandor-revoke-owner');ctx=context(product,state,fixture,owner)
    _,card=read(owner,fixture);body=ctx.body(card);request=uuid.uuid4()
    before=observe(ctx,http);cached=ok(send(owner,body,request));held=observe(ctx,http)
    one_reservation(before,held,cached,body)
    proofs=[access_cases.retain('HTTP_REVOKE_RESERVE',before,held,allowed=access_cases.ALLOCATION_TABLES)]
    with http.connect(connect_timeout=5)as holder,holder.cursor()as cur:
        ctx.admin(cur)
        changed=cur.execute('update erp.app_users set is_active=false where auth_user_id=%s::uuid and is_active returning id::text',
            (owner.auth_user_id,)).fetchall()
        require(len(changed)==1,'MANDOR_HTTP_ONLY_ONE_REAL_AUTH_ACTOR_REVOKED')
        with ThreadPoolExecutor(max_workers=1)as pool:
            start=monotonic();future=pool.submit(send,owner,body,request)
            try:pending=future.result(timeout=12)
            finally:
                if not future.done():holder.rollback()
        elapsed=monotonic()-start
        denied(pending,'could not obtain lock on relation "app_users"','55P03')
        require(elapsed<3,'MANDOR_HTTP_PENDING_REVOCATION_MUST_REFUSE_PROMPTLY')
        holder.commit()
    revoked=observe(ctx,http)
    require(revoked['actor']['id']==held['actor']['id']and held['actor']['is_active']is True
        and revoked['actor']['is_active']is False,'MANDOR_HTTP_EXACT_ORIGINAL_AUTH_ACTOR_DEACTIVATED')
    proofs.append(access_cases.retain('HTTP_ACTOR_REVOKED',held,revoked,
        allowed={'erp.app_users','erp.audit_logs','sequence:erp.audit_logs_id_seq'}))
    committed=denied(send(owner,body,request),'CP7_MANDOR_SHOP_ACCESS_DENIED','42501')
    no_read=denied(owner.rpc(READ,dict(p_payroll=fixture['payroll_id'],p_after=None)),
        'CP7_MANDOR_SHOP_ACCESS_DENIED','42501')
    proofs.append(access_cases.retain('HTTP_CACHED_REVOKED',revoked,observe(ctx,http)))
    return dict(status='PASS',real_Auth_HTTP=True,owner_auth_user_id=owner.auth_user_id,
        original_cached_reply=cached,pending_revocation=pending,pending_elapsed=elapsed,
        committed_revocation=committed,revoked_read_refusal=no_read,complete_census_proofs=proofs,
        original_Auth_token_used_after_app_access_revocation=True,fixture_actor_restored_by_copy_disposal=True,
        invoice_settled=False,actual_Native_case_credit=0,actual_two_session_case_credit=0,actual_browser_case_credit=0)


def http_cases(http,today,*,product,state,fixture):
    require(fixture['physical']['good_day']==str(today),'MANDOR_HTTP_CURRENT_WIB_COMMITTED_GOOD_REQUIRED')
    return[(HTTP_IDS[0],lambda:matrix(http,today,product,state,fixture)),
        (HTTP_IDS[1],lambda:cached_revocation(http,today,product,state,fixture))]
