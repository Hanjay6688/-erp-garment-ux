"""Prepared real two-backend Mandor races; the owning copy runner is required.

Every case operates on a fresh committed local copy of an actually installed
candidate. No connection, fixture, role change or financial case runs on import.
The caller must supply the exact product/state and a separately committed Native
fixture; source preparation alone never opens that caller's admission.
"""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from decimal import Decimal
from pathlib import Path
from time import monotonic
import gzip,json,uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
READ='erp_cp7_get_mandor_shop_payroll_v1'
WRITE='erp_cp7_save_mandor_shop_allocation_v1'
RACE_IDS=(
 'MANDOR_TWO_BACKEND_SAME_UUID_BUSY_THEN_ONE_EXACT_ALLOCATION_REPLAY',
 'MANDOR_TWO_BACKEND_COMPETING_UUID_BUSY_THEN_STALE_WITHOUT_SECOND_DEDUCTION',
 'MANDOR_TWO_BACKEND_CACHED_ALLOCATION_REFUSES_PENDING_AND_COMMITTED_ACCESS_REVOCATION',
 'MANDOR_TWO_BACKEND_CACHED_SALE_REFUSES_PENDING_AND_COMMITTED_ACCESS_REVOCATION',
)
ALLOCATION_TABLES={
 'cp7_mandor_shop.payroll_identities','cp7_mandor_shop.allocations',
 'cp7_mandor_shop.allocation_events','cp7_mandor_shop.allocation_states',
 'cp7_mandor_shop.deduction_links','cp7_mandor_shop.requests',
 'erp.payroll_deductions','erp.payroll_settlements','erp.audit_logs',
 'sequence:erp.audit_logs_id_seq',
}


def require(value,message):
    if not value:raise ValueError(message)


def prepare(native,cur,today):
    """One actual posted invoice and unpaid future payroll, no case credit."""
    native.admin(cur)
    f,physical=native.physical(cur,today)
    sale=native.create_invoice(cur,f)
    payroll=native.payroll(cur,f,today,back=-7)
    native.admin(cur)
    rows=cur.execute("select request_id::text,payload,response,actor::text from cp7_mandor_shop.requests "
        "where actor=%s::uuid and action='SALE_CREATE'and response->>'sale_id'=%s",
        (f['actor'],f['sale'])).fetchall()
    require(len(rows)==1,'MANDOR_ACCESS_ONE_EXACT_ORIGINAL_SALE_REQUEST')
    request,payload,response,actor=rows[0]
    require(payload['action']=='CREATE'and response==sale['created'],'MANDOR_ACCESS_EXACT_NATIVE_SALE_REQUEST_BINDING')
    require(payload['document']==sale['payload'],'MANDOR_ACCESS_ORIGINAL_SALE_PAYLOAD_BINDING')
    current=native.observe(cur,f,payroll)
    require(current['payroll']['status']=='DRAFT'and Decimal(current['invoice']['paid'])==0,
        'MANDOR_ACCESS_UNPAID_DRAFT_FIXTURE_REQUIRED')
    return dict(contract='cp7.mandor-shop-access-fixture.v1',actor=actor,sale_id=f['sale'],payroll_id=payroll,
        contractor_id=f['contractor'],physical=physical,Native_sale=sale,
        original_sale_request=dict(request_id=request,payload=payload,response=response),
        actual_case_credit=0,production_go=False)


class Context:
    def __init__(self,product,state,fixture,mode):
        require(mode=='RACE','MANDOR_ACCESS_PREPARED_RACE_MODE_ONLY')
        require(fixture['contract']=='cp7.mandor-shop-access-fixture.v1','MANDOR_ACCESS_EXACT_COMMITTED_FIXTURE')
        self.product=product;self.state=state;self.fixture=fixture;self.mode=mode
        self.modules=product.domain_modules
        require(self.modules is not None,'MANDOR_ACCESS_ACTUAL_ADMITTED_DOMAIN_REQUIRED')

    def local(self,cur):
        info=cur.connection.info
        require(info.host in('127.0.0.1','localhost')and info.port==54322,'MANDOR_ACCESS_LOOPBACK_COPY_ONLY')
        require(cur.execute('select current_database()').fetchone()==('cp6_auditor_race',),
            'MANDOR_ACCESS_FIXED_FRESH_RACE_COPY_ONLY')
        require(cur.execute("select current_setting('transaction_isolation')").fetchone()==('read committed',),
            'MANDOR_ACCESS_FRESH_CURRENT_READ_COMMITTED')

    def admin(self,cur):
        self.local(cur);self.modules.bc.api.admin(cur)

    def verify(self,cur):
        self.admin(cur)
        with self.modules.control.product_catalog(cur):self.product.verify(cur,self.state)

    def snapshot(self,cur):
        self.admin(cur)
        with self.modules.control.product_catalog(cur):
            catalog=self.product.runtime()[-1]
            actual=catalog._catalog_rows(cur)
            require(actual==self.state['after'],'MANDOR_ACCESS_EXACT_INSTALLED_ALL22')
            data=catalog._data(cur)
        f=self.fixture
        invoice=cur.execute('select erp.sale_net_total(%s::uuid)::text,cp7_credit.current_effective_paid(%s::uuid)::text,'
            'status from erp.sales_headers where id=%s::uuid',(f['sale_id'],f['sale_id'],f['sale_id'])).fetchone()
        states=[r[0]for r in cur.execute('select to_jsonb(s)from cp7_mandor_shop.allocation_states s '
            'where sale_id=%s::uuid order by allocation_id',(f['sale_id'],)).fetchall()]
        requests=[r[0]for r in cur.execute('select to_jsonb(r)from cp7_mandor_shop.requests r '
            'where actor=%s::uuid order by request_id',(f['actor'],)).fetchall()]
        deductions=[r[0]for r in cur.execute('select to_jsonb(d)from erp.payroll_deductions d '
            'where payroll_id=%s::uuid order by id',(f['payroll_id'],)).fetchall()]
        payroll=cur.execute('select status,net_payable::text from erp.payroll_settlements where id=%s::uuid',
            (f['payroll_id'],)).fetchone()
        actor=cur.execute('select to_jsonb(u)from erp.app_users u where auth_user_id=%s::uuid',
            (f['actor'],)).fetchone()[0]
        audits=[r[0]for r in cur.execute("select to_jsonb(a)from erp.audit_logs a where entity_type='app_users'and entity_id=%s::uuid order by id",
            (actor['id'],)).fetchall()]
        return dict(actual_all22=actual,full_data_and_sequences=data,actor=actor,actor_audits=audits,invoice=list(invoice),
            allocation_states=states,requests=requests,deductions=deductions,payroll=list(payroll))

    def read(self,cur):
        self.admin(cur);self.modules.bc.session(cur,self.fixture['actor'])
        value=cur.execute('select public.erp_cp7_get_mandor_shop_payroll_v1(%s::uuid,null)',
            (self.fixture['payroll_id'],)).fetchone()[0]
        self.modules.bc.api.admin(cur)
        require(value['payroll_id']==self.fixture['payroll_id'],'MANDOR_ACCESS_SELECTED_PAYROLL_ONLY')
        rows=[r for r in value['cards']if r['sale_id']==self.fixture['sale_id']]
        require(len(rows)==1,'MANDOR_ACCESS_ONE_EXACT_INVOICE_CARD')
        return rows[0]

    def body(self,card):
        return dict(contract_version='cp7.mandor-shop-allocation-command.v1',payroll_id=self.fixture['payroll_id'],
            sale_id=self.fixture['sale_id'],review_token=card['review_token'],amount='100000.00')

    def allocation(self,cur,body,request):
        self.admin(cur);self.modules.bc.session(cur,self.fixture['actor'])
        value=cur.execute('select public.erp_cp7_save_mandor_shop_allocation_v1(%s,%s::jsonb,%s::uuid)',
            ('RESERVE',json.dumps(body),request)).fetchone()[0]
        self.modules.bc.api.admin(cur);return value

    def sale_replay(self,cur):
        self.admin(cur);saved=self.fixture['original_sale_request'];intent=saved['payload']
        self.modules.bc.session(cur,self.fixture['actor'])
        value=cur.execute('select public.erp_cp7_save_mandor_shop_sale_v1(%s,%s::jsonb,%s::uuid,%s)',
            (intent['action'],json.dumps(intent['document']),saved['request_id'],intent['expected_version'])).fetchone()[0]
        self.modules.bc.api.admin(cur);return value

    def observe(self,tools):
        with tools.connect(connect_timeout=5)as conn,conn.cursor()as cur:
            self.verify(cur);value=self.snapshot(cur);conn.rollback();return value


def retain(label,before,after,*,allowed=()):
    require(before['actual_all22']==after['actual_all22'],'MANDOR_ACCESS_ALL22_CHANGED')
    left,right=before['full_data_and_sequences'],after['full_data_and_sequences']
    require(set(left)==set(right),'MANDOR_ACCESS_DATA_OR_SEQUENCE_SCOPE_CHANGED')
    changed=sorted(k for k in left if left[k]!=right[k])
    require(set(changed)<=set(allowed),'MANDOR_ACCESS_UNEXPECTED_DATA_OR_SEQUENCE_CHANGE:'+str(changed))
    if not allowed:require(before==after,'MANDOR_ACCESS_FULL_NO_EFFECT_REQUIRED')
    raw=(json.dumps(dict(before=before,after=after),sort_keys=True,default=str)+'\n').encode()
    packed=gzip.compress(raw,mtime=0);name='MANDOR_ACCESS_'+label+'_'+uuid.uuid4().hex+'.json.gz'
    directory=ROOT/'cp6-proof/t3';directory.mkdir(parents=True,exist_ok=True)
    with (directory/name).open('xb')as output:output.write(packed)
    return dict(status='PASS',changed_tables=changed,allowed_tables=sorted(allowed),
        original=dict(name=name,raw_bytes=len(raw),raw_sha256=sha256(raw).hexdigest(),
            gzip_bytes=len(packed),gzip_sha256=sha256(packed).hexdigest()),actual_all22_groups=22)


def worker(ctx,tools,operation):
    from psycopg import Error
    with tools.connect(connect_timeout=5)as conn,conn.cursor()as cur:
        ctx.local(cur);pid=cur.execute('select pg_backend_pid()').fetchone()[0]
        cur.execute("set local lock_timeout='3s';set local statement_timeout='8s'")
        start=monotonic()
        try:
            reply=operation(cur);conn.commit()
            return dict(ok=True,reply=reply,backend_pid=pid,elapsed=monotonic()-start)
        except Error as error:
            conn.rollback()
            return dict(ok=False,sqlstate=error.sqlstate,message=error.diag.message_primary,
                backend_pid=pid,elapsed=monotonic()-start)


def refused(result,code,message):
    require(result['ok']is False and result['sqlstate']==code and result['message']==message,
        'MANDOR_ACCESS_EXACT_ACTUAL_REFUSAL_REQUIRED:'+str(result))


def concurrent_reserve(ctx,tools,*,same_request):
    with tools.connect(connect_timeout=5)as conn,conn.cursor()as cur:
        ctx.verify(cur);body=ctx.body(ctx.read(cur));before=ctx.snapshot(cur);conn.commit()
    require(before['allocation_states']==[]and before['deductions']==[],'MANDOR_ACCESS_FRESH_UNALLOCATED_NATIVE_FIXTURE')
    request=str(uuid.uuid4());other=request if same_request else str(uuid.uuid4())
    with tools.connect(connect_timeout=5)as holder,holder.cursor()as cur:
        ctx.local(cur);holder_pid=cur.execute('select pg_backend_pid()').fetchone()[0]
        first=ctx.allocation(cur,body,request)
        # Execute the second backend while the first transaction is still open.
        with ThreadPoolExecutor(max_workers=1)as pool:
            pending=pool.submit(worker,ctx,tools,lambda c:ctx.allocation(c,body,other))
            try:blocked=pending.result(timeout=12)
            finally:
                # On an unexpected blocked worker, release before pool join.
                if not pending.done():holder.rollback()
        require(blocked['backend_pid']!=holder_pid,'MANDOR_ACCESS_TWO_DISTINCT_BACKENDS_REQUIRED')
        expected='CP7_MANDOR_SHOP_REQUEST_BUSY'if same_request else'could not obtain lock on row in relation "payroll_settlements"'
        refused(blocked,'55P03',expected)
        require(blocked['elapsed']<3,'MANDOR_ACCESS_NOWAIT_MUST_NOT_USE_TIMEOUT')
        holder.commit()
    after=ctx.observe(tools)
    require(after['invoice']==before['invoice'],'MANDOR_ACCESS_RESERVATION_MUST_NOT_PAY_INVOICE')
    require(after['payroll'][0]=='CALCULATED'and Decimal(after['payroll'][1])==Decimal('1900000.00'),
        'MANDOR_ACCESS_EXACT_NATIVE_CALCULATED_NET_AFTER_ONE_RESERVATION')
    require(first['kind']=='COMMITTED_OUTCOME'and first['invoice_settled_by_this_command']is False,
        'MANDOR_ACCESS_RESERVATION_OUTCOME_IS_NOT_PAYMENT')
    added=[r for r in after['allocation_states']if r['allocation_id']==first['allocation_id']]
    require(len(added)==1 and added[0]['state']=='RESERVED','MANDOR_ACCESS_ONE_RESERVED_ALLOCATION')
    require(len(after['deductions'])==len(before['deductions'])+1,'MANDOR_ACCESS_ONE_NATIVE_DEDUCTION')
    require(len(after['requests'])==len(before['requests'])+1,'MANDOR_ACCESS_ONE_IMMUTABLE_REQUEST')
    proof=retain('SAME'if same_request else'COMPETING',before,after,allowed=ALLOCATION_TABLES)
    retry=worker(ctx,tools,lambda c:ctx.allocation(c,body,other))
    if same_request:require(retry['ok']is True and retry['reply']==first,'MANDOR_ACCESS_EXACT_REPLAY_AFTER_WINNER_COMMIT')
    else:refused(retry,'P0001','CP7_MANDOR_SHOP_REVIEW_CHANGED')
    changed_intent=worker(ctx,tools,lambda c:ctx.allocation(c,dict(body,amount='100000.01'),request))
    refused(changed_intent,'P0001','CP7_MANDOR_SHOP_REQUEST_CHANGED')
    old={r['request_id']:r for r in before['requests']};new={r['request_id']:r for r in after['requests']}
    require(set(new)==set(old)|{request}and all(new[k]==v for k,v in old.items()),
        'MANDOR_ACCESS_EXACT_IMMUTABLE_REQUEST_APPEND')
    require(new[request]['response']==first and new[request]['payload']==body,'MANDOR_ACCESS_EXACT_STORED_INTENT_AND_OUTCOME')
    unchanged=retain('RETRY',after,ctx.observe(tools))
    return dict(status='PASS',actual_two_database_sessions=True,holder_pid=holder_pid,contender=blocked,
        first=first,retry=retry,changed_intent_refusal=changed_intent,one_allocation_one_deduction=True,proofs=[proof,unchanged],
        administrative_actor_not_real_Auth=True,actual_Native_case_credit=0,actual_Auth_HTTP_case_credit=0,
        actual_browser_case_credit=0,full_copy_restore_required=True)


def cached_access_revocation(ctx,tools,*,sale):
    with tools.connect(connect_timeout=5)as conn,conn.cursor()as cur:
        ctx.verify(cur)
        if sale:
            operation=lambda c:ctx.sale_replay(c)
            cached=operation(cur)
            require(cached==ctx.fixture['original_sale_request']['response'],'MANDOR_ACCESS_EXACT_ORIGINAL_SALE_REPLAY')
        else:
            body=ctx.body(ctx.read(cur));request=str(uuid.uuid4())
            operation=lambda c:ctx.allocation(c,body,request)
            cached=operation(cur)
        conn.commit()
    before=ctx.observe(tools)
    with tools.connect(connect_timeout=5)as holder,holder.cursor()as cur:
        ctx.admin(cur);holder_pid=cur.execute('select pg_backend_pid()').fetchone()[0]
        changed=cur.execute('update erp.app_users set is_active=false where auth_user_id=%s::uuid and is_active returning id::text',
            (ctx.fixture['actor'],)).fetchall()
        require(len(changed)==1,'MANDOR_ACCESS_REVOKE_ONLY_EXACT_ACTIVE_FIXTURE_ACTOR')
        with ThreadPoolExecutor(max_workers=1)as pool:
            pending=pool.submit(worker,ctx,tools,operation)
            try:busy=pending.result(timeout=12)
            finally:
                if not pending.done():holder.rollback()
        require(busy['backend_pid']!=holder_pid,'MANDOR_ACCESS_TWO_DISTINCT_REVOCATION_BACKENDS')
        refused(busy,'55P03','could not obtain lock on relation "app_users"')
        require(busy['elapsed']<3,'MANDOR_ACCESS_PERMISSION_NOWAIT_MUST_NOT_TIMEOUT')
        holder.commit()
    revoked=ctx.observe(tools)
    require(before['actor']['is_active']is True and revoked['actor']['is_active']is False,
        'MANDOR_ACCESS_EXACT_FIXTURE_ACTOR_REVOKED')
    require(revoked['actor']['id']==before['actor']['id'],'MANDOR_ACCESS_SAME_ACTOR_REVOCATION')
    old_audits={r['id']:r for r in before['actor_audits']};new_audits={r['id']:r for r in revoked['actor_audits']}
    require(len(new_audits)==len(old_audits)+1 and all(new_audits[k]==v for k,v in old_audits.items()),
        'MANDOR_ACCESS_ONE_NATIVE_AUDIT_FOR_ACCESS_FIXTURE')
    audit=next(v for k,v in new_audits.items()if k not in old_audits)
    require(audit['action']=='UPDATE'and audit['old_data']==before['actor']and audit['new_data']==revoked['actor'],
        'MANDOR_ACCESS_EXACT_OLD_NEW_AUDIT_CONTENT')
    access_change=retain('ACCESS_FIXTURE',before,revoked,
        allowed={'erp.app_users','erp.audit_logs','sequence:erp.audit_logs_id_seq'})
    denied=worker(ctx,tools,operation)
    message='CP7_SALES_ACCESS_DENIED'if sale else'CP7_MANDOR_SHOP_ACCESS_DENIED'
    refused(denied,'42501',message)
    proof=retain('CACHED_REVOKED',revoked,ctx.observe(tools))
    return dict(status='PASS',actual_two_database_sessions=True,holder_pid=holder_pid,pending_revocation=busy,
        committed_revocation=denied,original_cached_reply=cached,permission_checked_before_cached_reply=True,
        administrative_fixture_actor_deactivated=ctx.fixture['actor'],actor_restored_by_fresh_copy_disposal=True,
        proofs=[access_change,proof],administrative_actor_not_real_Auth=True,actual_Native_case_credit=0,
        actual_Auth_HTTP_case_credit=0,actual_browser_case_credit=0,full_copy_restore_required=True)


def races(tools,today,*,product,state,fixture):
    require(fixture['physical']['good_day']==str(today),'MANDOR_ACCESS_CURRENT_WIB_GOOD_FIXTURE_REQUIRED')
    ctx=Context(product,state,fixture,'RACE')
    return[(RACE_IDS[0],lambda:concurrent_reserve(ctx,tools,same_request=True)),
        (RACE_IDS[1],lambda:concurrent_reserve(ctx,tools,same_request=False)),
        (RACE_IDS[2],lambda:cached_access_revocation(ctx,tools,sale=False)),
        (RACE_IDS[3],lambda:cached_access_revocation(ctx,tools,sale=True))]
