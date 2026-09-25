"""BD T1_FAMILY probe: priced laundry deliveries (LAU-05b: package, components with partial coverage, lump sum per batch,
minimum charge, scoped rates) and the laundry policy settings LAU-DEC01..06, before and after.

Label T1_FAMILY: targeted family evidence on the disposable chain AN -> AU -> AV -> AW..AZ -> BA -> BB -> BC (+ BD in phase
'after'), never release evidence. Oracles come from the contract (M:4339-4374 LAU-T01..T36, LAU-05b, LAU-DEC01..06 M:4472-4477)
and the auditors' pre-code oracles (gpt_lau.md, fable_lau.md), never from observed behaviour; where two readings differ the
more fail-closed one is used. Amounts are synthetic fixtures (no real tariff is invented). Outcomes:
  NO_ROUTE       phase 'before' only: no BD facade before BD (the public RPC is unknown); nothing changes.
  PASS / FAIL    the oracle holds / does not hold. A refusal with another code, or a wrong NO_ROUTE, is INCOMPLETE.
Each case runs inside the group's rolled-back savepoint; nothing is committed to the clone.
"""
from decimal import Decimal
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys,traceback,uuid
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_bc_probe as bcp
import cp6_bd_build as bd_build
import cp6_run_identity as run_identity
bbp=bcp.bbp
r1,api,boundary,prior,chain=bcp.r1,bcp.api,bcp.boundary,bcp.prior,bcp.chain
code_of,verdict,no_route,refused,q,one,gl,user=bcp.code_of,bcp.verdict,bcp.no_route,bcp.refused,bcp.q,bcp.one,bcp.gl,bcp.user

OUT=AUDITOR/'cp6-proof/bd'
BD_SQL=AUDITOR/'supabase/dev/cp6_bd_t1_family.sql'
LABEL='T1_FAMILY'
D=Decimal
bcp.NO_ROUTE_MESSAGES=bcp.NO_ROUTE_MESSAGES+('erp_save_laundry_bd_action_v1(','erp_get_laundry_bd_workspace_v1(')
case_day=bcp.case_day


def dev_source(signature):
    name=signature.split('(')[0]
    text=BD_SQL.read_text()
    heads=[m.start() for m in re.finditer(r'(?i)create or replace function '+re.escape(name)+r'\(',text)]
    assert heads,('BD_T1_FUNCTION_NOT_IN_DEV_FILE',signature)
    start=re.compile(r'(?i)\bas \$(function\$|\$)').search(text,heads[-1])
    delim='$function$' if start.group(1)=='function$' else '$$'
    return text[start.end():text.index(delim,start.end())]


def bd_installed(cur):
    return cur.execute('select count(*) from erp.schema_migrations where version=%s',(bd_build.VERSION,)).fetchone()[0]==1


def bd_functions():
    return tuple(bd_build.REPLACED)+tuple(dict.fromkeys(bd_build.new_functions()))


def bd_verified(cur):
    base=bcp.bc_verified(cur)
    assert bd_installed(cur),'BD_T1_MARKER'
    for name in bd_functions():
        schema,proname=name.split('(')[0].split('.')
        rows=cur.execute("select p.oid::regprocedure::text,p.prosrc from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and p.proname=%s",
                         (schema,proname)).fetchall()
        assert len(rows)==1,('BD_T1_FUNCTION_NOT_UNIQUE',name,[r[0] for r in rows])
        assert rows[0][1]==dev_source(name),('BD_T1_FUNCTION_NOT_CURRENT',name)
    for table in bd_build.NEW_TABLES:
        assert cur.execute('select to_regclass(%s) is not null',('erp.'+table,)).fetchone()[0],('BD_T1_TABLE_MISSING',table)
    return dict(base,stage='AV_PLUS_AW_AX_AY_AZ_BA_BB_BC_BD_T1',bd_sql_sha256=hashlib.sha256(BD_SQL.read_bytes()).hexdigest(),
                bd_functions=list(bd_functions()))


def install_bd():
    with psycopg.connect(boundary.PG,autocommit=True) as conn,conn.cursor() as cur:cur.execute(BD_SQL.read_text(),prepare=False)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        result=bd_verified(cur);conn.rollback()
    return result


# ---------------------------------------------------------------- calls
def bd(cur,action,payload,key=None,auth=None):
    """The BD facade as the owner (or `auth`), through its public wrapper."""
    if auth:bcp.session(cur,auth)
    else:chain.production.owner(cur)
    result=cur.execute('select public.erp_save_laundry_bd_action_v1(%s,%s::jsonb,%s)',(action,json.dumps(payload,default=str),str(key or uuid.uuid4()))).fetchone()[0]
    chain.actors.admin(cur);return result


def bd_ws(cur,filters=None,auth=None):
    if auth:bcp.session(cur,auth)
    else:chain.production.owner(cur)
    result=cur.execute('select public.erp_get_laundry_bd_workspace_v1(%s::jsonb)',(json.dumps(filters or {},default=str),)).fetchone()[0]
    chain.actors.admin(cur);return result


def compute(cur,delivery,pricing=None):
    """The pricing of a delivery payload without posting it (the facade's own computation, called as the database owner)."""
    api.admin(cur)
    return cur.execute('select erp.bd_compute_pricing_v1(%s::jsonb,%s::jsonb)',(json.dumps(delivery,default=str),json.dumps(pricing or {}))).fetchone()[0]


def route_call(cur):
    """The first BD call of every case, made directly (before BD neither the facade nor its tables exist)."""
    return bd(cur,'SET_POLICY',dict(policy_key='LAU_DEC01',operation='SET',expected_version='1',reason='BD probe route',value=dict(units=['BATCH'])))


def internal(cur,name,*args):
    """A native internal function in the owner's session. Usage on schema erp is granted to authenticated only when it is
    missing and put back as it was (the BC helper revokes it even when it was granted before the call)."""
    api.admin(cur)
    had=cur.execute("select has_schema_privilege('authenticated','erp','usage')").fetchone()[0]
    if not had:cur.execute('grant usage on schema erp to authenticated')
    chain.production.owner(cur)
    value=cur.execute('select erp.'+name+'('+','.join(['%s']*len(args))+')',args).fetchone()[0];api.admin(cur)
    if not had:cur.execute('revoke usage on schema erp from authenticated')
    return value


def iso(value):
    return value.isoformat()


def policy(cur,key,value=None,operation='SET'):
    version=one(cur,'select version from erp.bd_policy_settings_v1 where policy_key=%s',key)
    payload=dict(policy_key=key,operation=operation,expected_version=str(version),reason='BD probe owner setting '+key)
    if value is not None:payload['value']=value
    return bd(cur,'SET_POLICY',payload)


# ---------------------------------------------------------------- fixture
def fixture(cur,today,label):
    """Ten pieces of one size ready to go to laundry (the chain's production fixture), a fresh laundry vendor and wash process."""
    base,production=chain.base,chain.production
    f=chain.work.draft(cur,today,D(0))
    chain.peer.ordinary(cur);cur.execute('select erp.post_work_completion(%s)',(f['completion'],))
    production.owner(cur)
    cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)',
        (json.dumps(dict(work_completion_id=str(f['completion']),qty_pcs=10,reason='BD '+label+' ten pieces')),uuid.uuid4()))
    chain.actors.admin(cur)
    day=cur.execute("select (physical_at at time zone 'Asia/Jakarta')::date from erp.work_completion_events where id=%s",(f['completion'],)).fetchone()[0]
    batch=cur.execute('select b.id from erp.cutting_distribution_batches b join erp.cutting_pickups p on p.id=b.pickup_id where p.cutting_group_id=%s',(f['group'],)).fetchone()[0]
    model=cur.execute('select po.model_id from erp.production_orders po where po.id=%s',(f['po'],)).fetchone()[0]
    vendor=str(uuid.uuid4());process=str(uuid.uuid4());tag=uuid.uuid4().hex[:12]
    cur.execute("insert into erp.laundry_vendors(id,vendor_code,vendor_name,is_active) values(%s,%s,%s,true)",(vendor,'BD-'+tag,'BD vendor '+label))
    cur.execute("insert into erp.wash_processes(id,process_code,process_name,is_active) values(%s,%s,%s,true)",(process,'BDP-'+tag,'BD wash '+label))
    return dict(f=f,day=day,batch=str(batch),model=str(model),vendor=vendor,process=process,group=str(f['group']),po=str(f['po']),
                start=production.at(day,0),send=production.at(day,11))


def delivery_payload(fx,qty=10,hour=11,minute=0,color='BD-COLOR'):
    return dict(distribution_batch_id=fx['batch'],vendor_id=fx['vendor'],wash_process_id=fx['process'],target_dyeing_color=color,
                physical_at=iso(chain.production.at(fx['day'],hour,minute)),reason='BD probe delivery',
                lines=[dict(size_id=chain.base.SIZE,qty_sent_pcs=qty)])


def post_priced(cur,fx,pricing,qty=10,hour=11,minute=0,key=None):
    return bd(cur,'POST_PRICED_DELIVERY',dict(delivery=delivery_payload(fx,qty,hour,minute),
        expected_version=str(chain.base.group_version(cur,fx['group'])),pricing=pricing),key=key)


def component(cur,fx,code,rate,status='KNOWN',vendor=None):
    c=bd(cur,'SAVE_COMPONENT',dict(vendor_id=vendor or fx['vendor'],component_code=code,component_name='BD '+code,is_active=True,reason='BD probe master'))
    payload=dict(component_id=c['component_id'],rate_status=status,effective_from=iso(fx['start']),reason='BD probe synthetic price')
    if status=='KNOWN':payload['rate_per_pcs']=rate
    bd(cur,'SAVE_COMPONENT_RATE',payload)
    return c['component_id']


def terms(cur,fx,mode,unit='PCS',minimum=None):
    version=one(cur,'select coalesce((select row_version from erp.bd_laundry_vendor_terms_v1 where vendor_id=%s),0)',fx['vendor'])
    return bd(cur,'SAVE_VENDOR_TERMS',dict(vendor_id=fx['vendor'],pricing_mode=mode,pricing_unit=unit,minimum_charge=minimum,
                                           expected_version=str(version),reason='BD probe vendor terms'))


def process_rate(cur,fx,rate,start=None):
    return bd(cur,'SAVE_PROCESS_RATE',dict(vendor_id=fx['vendor'],wash_process_id=fx['process'],rate_per_pcs=rate,
                                           effective_from=iso(start or fx['start']),reason='BD probe synthetic process rate'))


def receive(cur,delivery,fx,good,hour,process=None):
    return chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=delivery,wash_process_id=process or fx['process'],
        physical_at=iso(chain.production.at(fx['day'],hour)),reason='BD probe return',
        lines=[dict(delivery_batch_size_line_id=chain.base.delivery_size_line(cur,delivery),qty_good_received=good,qty_bs_laundry=0,bs_product_id=None)]),
        chain.base.delivery_version(cur,delivery))


def line_state(cur,delivery):
    row=q(cur,"""select l.id,l.qty_sent_pcs,l.estimated_rate_snapshot,l.estimated_cost_status,p.total_known,p.total_complete,p.pricing_mode,
        (select count(*) from erp.bd_laundry_charge_lines_v1 c where c.delivery_line_id=l.id),
        (select count(*) from erp.laundry_delivery_lines x where x.delivery_id=l.delivery_id)
      from erp.laundry_delivery_lines l left join erp.bd_laundry_priced_lines_v1 p on p.delivery_line_id=l.id where l.delivery_id=%s""",delivery)[0]
    return dict(line=str(row[0]),qty=row[1],rate=None if row[2] is None else str(row[2]),status=row[3],known=None if row[4] is None else str(row[4]),
                complete=row[5],mode=row[6],charges=row[7],lines=row[8])


def accrual(cur,po):
    return dict(desired=str(one(cur,'select erp.desired_laundry_accrual(%s)',po)),
                booked=str(one(cur,"select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l where l.po_id=%s and l.account_id=erp.account_id('ACCRUED_MANUFACTURING')",po)))


def blockers(cur,through,delivery):
    return sorted(r[0] for r in q(cur,"select code from erp.period_blockers_v1(%s,null) where reference->>'delivery_id'=%s",through,delivery))


# ---------------------------------------------------------------- cases
def policy_settings(cur,today):
    """LAU-DEC01..06 are owner settings, pending until set (owner decision 25 Sep 2026, M:1757): every key starts
    PENDING_POLICY_VALUE; an admin cannot set one; the owner sets and clears with the version seen; a stale version, a value
    outside the allowed shape and an account of the wrong type are refused; each change is an event."""
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    start=q(cur,'select policy_key,status,version from erp.bd_policy_settings_v1 order by 1')
    admin=user(cur,'ADMIN',grants=('settings.erp.manage',))
    v=str(one(cur,"select version from erp.bd_policy_settings_v1 where policy_key='LAU_DEC01'"))
    by_admin=refused(cur,lambda:bd(cur,'SET_POLICY',dict(policy_key='LAU_DEC01',operation='SET',expected_version=v,reason='x',value=dict(units=['BATCH'])),auth=admin),'BD_OWNER_ONLY')
    bad=refused(cur,lambda:policy(cur,'LAU_DEC01',dict(units=['DAILY'])),'BD_POLICY_VALUE')
    bad05=refused(cur,lambda:policy(cur,'LAU_DEC05',dict(scopes=['MODEL'],fallback='GUESS')),'BD_POLICY_VALUE')
    asset=one(cur,"select id::text from erp.chart_accounts where account_type='ASSET' and is_postable and is_active order by account_code limit 1")
    bad06=refused(cur,lambda:policy(cur,'LAU_DEC06',dict(variance_mode='VARIANCE_ACCOUNT',after_payment='REFUSE',variance_account_id=asset)),'BD_POLICY_VALUE')
    s=policy(cur,'LAU_DEC01',dict(units=['MINIMUM','BATCH']))
    stale=refused(cur,lambda:bd(cur,'SET_POLICY',dict(policy_key='LAU_DEC01',operation='CLEAR',expected_version=v,reason='stale')),'STALE_VERSION')
    c=policy(cur,'LAU_DEC01',operation='CLEAR')
    events=q(cur,"select version,status from erp.bd_policy_setting_events_v1 where policy_key='LAU_DEC01' order by version")
    return verdict(dict(all_pending=len(start)==6 and all(r[1]=='PENDING_POLICY_VALUE' for r in start),admin_refused=by_admin['ok'],
        bad_value_refused=bad['ok'] and bad05['ok'] and bad06['ok'],set=s['status']=='SET' and s['value']==dict(units=['BATCH','MINIMUM']),
        stale_refused=stale['ok'],cleared=c['status']=='PENDING_POLICY_VALUE' and c['version']=='3',
        events=[(r[0],r[1]) for r in events]==[(1,'PENDING_POLICY_VALUE'),(2,'SET'),(3,'PENDING_POLICY_VALUE')]),
        refusals=[by_admin,bad,bad05,bad06,stale])


def t02_package(cur,today):
    """LAU-T02 (M:4340): a package at a synthetic 12,000/PCS covering its listed components, 10 PCS -> 120,000; the physical
    quantity stays 10 (not the component count), the package and its components are one charge line; the accrual is the
    estimate; the plain laundry facade cannot post this vendor at a base rate (BD_PRICING_REQUIRED)."""
    fx=fixture(cur,today,'T02')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    g=component(cur,fx,'GARMENT','5000.00');s=component(cur,fx,'SPRAY','1000.00')
    pkg=bd(cur,'SAVE_PACKAGE',dict(vendor_id=fx['vendor'],package_code='PKG',package_name='Paket uji',component_ids=[g,s],is_active=True,reason='BD probe'))['package_id']
    bd(cur,'SAVE_PACKAGE_RATE',dict(package_id=pkg,rate_per_pcs='12000.00',effective_from=iso(fx['start']),reason='BD probe synthetic package price'))
    process_rate(cur,fx,'100.00');terms(cur,fx,'PACKAGE')
    plain=refused(cur,lambda:chain.laundry_action(cur,'POST_DELIVERY',delivery_payload(fx),chain.base.group_version(cur,fx['group'])),'BD_PRICING_REQUIRED')
    sent=post_priced(cur,fx,dict(package_id=pkg))
    st=line_state(cur,sent['delivery_id']);acc=accrual(cur,fx['po'])
    charges=sent['pricing']['charges']
    return verdict(dict(plain_refused=plain['ok'],qty_10=st['qty']==10 and st['lines']==1,total=st['known']=='120000.00' and st['complete'] is True,
        rate=st['rate']=='12000.00' and st['status']=='ESTIMATED',one_charge=len(charges)==1 and charges[0]['kind']=='PACKAGE'
        and sorted(charges[0]['included_components'])==sorted([g,s]),accrual=acc['desired']=='120000.00' and acc['booked']=='120000.00'),
        state=st,accrual=acc,refusal=plain)


def t03_t04_components(cur,today,four):
    """LAU-T03/T04 (M:4341-4342): per-PCS components summed on the same 10 pieces (5,000 + 1,000 + 1,000 [+ 5,000]) ->
    70,000 (120,000); the physical quantity stays 10, never 30/40; the same component twice is refused."""
    fx=fixture(cur,today,'T04' if four else 'T03')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    ids=[component(cur,fx,c,r) for c,r in (('GARMENT','5000.00'),('SPRAY','1000.00'),('WHISKER','1000.00'))+((('WIPPING','5000.00'),) if four else ())]
    terms(cur,fx,'COMPONENTS')
    dup=refused(cur,lambda:post_priced(cur,fx,dict(components=[dict(component_id=ids[0],covered_qty=10),dict(component_id=ids[0],covered_qty=10)])),'BD_COMPONENT_DUPLICATE')
    sent=post_priced(cur,fx,dict(components=[dict(component_id=i,covered_qty=10) for i in ids]))
    st=line_state(cur,sent['delivery_id']);total='120000.00' if four else '70000.00'
    return verdict(dict(duplicate_refused=dup['ok'],qty_10=st['qty']==10,total=st['known']==total,charges=st['charges']==len(ids),
        accrual=accrual(cur,fx['po'])['booked']==total),state=st)


def t05_partial_coverage(cur,today):
    """LAU-T05 (M:4343): Garment on 10 PCS at 5,000 and Spray on 4 PCS at 1,000 -> 54,000; the physical quantity stays 10
    (not 14); coverage above the delivery (11) is refused."""
    fx=fixture(cur,today,'T05')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    g=component(cur,fx,'GARMENT','5000.00');s=component(cur,fx,'SPRAY','1000.00');terms(cur,fx,'COMPONENTS')
    over=refused(cur,lambda:post_priced(cur,fx,dict(components=[dict(component_id=g,covered_qty=10),dict(component_id=s,covered_qty=11)])),'BD_COVERAGE_EXCEEDS_DELIVERY')
    sent=post_priced(cur,fx,dict(components=[dict(component_id=g,covered_qty=10),dict(component_id=s,covered_qty=4)]))
    st=line_state(cur,sent['delivery_id'])
    cov=sorted((c['covered_qty'],c['amount']) for c in sent['pricing']['charges'])
    return verdict(dict(over_refused=over['ok'],qty_10=st['qty']==10,total=st['known']=='54000.00',coverage=cov==[(4,'4000.00'),(10,'50000.00')]),state=st)


def t06_package_extra(cur,today):
    """LAU-T06 (M:4344): an extra that is already in the package is refused (no second charge for the same units); a distinct
    extra waits for LAU-DEC03 (pending -> BD_POLICY_PENDING), and once the owner allows extras it is charged once."""
    fx=fixture(cur,today,'T06')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    g=component(cur,fx,'GARMENT','5000.00');w=component(cur,fx,'WHISKER','1000.00')
    pkg=bd(cur,'SAVE_PACKAGE',dict(vendor_id=fx['vendor'],package_code='PKG',package_name='Paket uji',component_ids=[g],is_active=True,reason='BD probe'))['package_id']
    bd(cur,'SAVE_PACKAGE_RATE',dict(package_id=pkg,rate_per_pcs='6000.00',effective_from=iso(fx['start']),reason='BD probe'));terms(cur,fx,'PACKAGE')
    same=refused(cur,lambda:post_priced(cur,fx,dict(package_id=pkg,extras=[dict(component_id=g,covered_qty=10,reason='x')])),'BD_COMPONENT_ALREADY_INCLUDED')
    pending=refused(cur,lambda:post_priced(cur,fx,dict(package_id=pkg,extras=[dict(component_id=w,covered_qty=10,reason='whisker extra')])),'BD_POLICY_PENDING')
    policy(cur,'LAU_DEC03',dict(discount='REFUSED',extra='ALLOWED',rounding='REFUSED'))
    sent=post_priced(cur,fx,dict(package_id=pkg,extras=[dict(component_id=w,covered_qty=10,reason='whisker extra')]))
    st=line_state(cur,sent['delivery_id'])
    return verdict(dict(same_refused=same['ok'],pending_refused=pending['ok'],total=st['known']=='70000.00',charges=st['charges']==2,
        versions='LAU_DEC03' in (sent['pricing'].get('policy_versions') or {})),state=st)


def t07_versions(cur,today):
    """LAU-T07/T14 (M:4345, M:4352): a posted delivery keeps its price version; a new version cannot start at or before a
    posted delivery (BD_VERSION_BEFORE_POSTED_DELIVERY); a version starting after it prices the next delivery only; the
    receipt of the first delivery keeps the first estimate."""
    fx=fixture(cur,today,'T07')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    g=component(cur,fx,'GARMENT','5000.00');terms(cur,fx,'COMPONENTS')
    first=post_priced(cur,fx,dict(components=[dict(component_id=g,covered_qty=6)]),qty=6,hour=11)
    early=refused(cur,lambda:bd(cur,'SAVE_COMPONENT_RATE',dict(component_id=g,rate_status='KNOWN',rate_per_pcs='6000.00',
        effective_from=iso(chain.production.at(fx['day'],10)),reason='backdated')),'BD_VERSION_BEFORE_POSTED_DELIVERY')
    bd(cur,'SAVE_COMPONENT_RATE',dict(component_id=g,rate_status='KNOWN',rate_per_pcs='6000.00',effective_from=iso(chain.production.at(fx['day'],12)),reason='V2'))
    second=post_priced(cur,fx,dict(components=[dict(component_id=g,covered_qty=4)]),qty=4,hour=13)
    rec=receive(cur,first['delivery_id'],fx,6,14)
    a=line_state(cur,first['delivery_id']);b=line_state(cur,second['delivery_id'])
    cost=one(cur,'select actual_cost from erp.laundry_receipt_lines where receipt_id=%s',rec['receipt_id'])
    return verdict(dict(early_refused=early['ok'],first_kept=a['known']=='30000.00',second_v2=b['known']=='24000.00',receipt_first_estimate=str(cost)=='30000.00'),
        first=a,second=b,receipt_cost=str(cost))


def t08_bad_nominal(cur,today):
    """LAU-T08 (M:4346): negative, one-decimal, float, zero and malformed prices and overlapping versions are refused and write
    nothing (zero needs an explicit free policy, none exists; unknown is UNKNOWN, never 0)."""
    fx=fixture(cur,today,'T08')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    c=bd(cur,'SAVE_COMPONENT',dict(vendor_id=fx['vendor'],component_code='GARMENT',component_name='BD GARMENT',is_active=True,reason='BD probe'))['component_id']
    before=one(cur,'select count(*) from erp.bd_laundry_component_rates_v1 where component_id=%s',c)
    def price(value):
        return lambda:bd(cur,'SAVE_COMPONENT_RATE',dict(component_id=c,rate_status='KNOWN',rate_per_pcs=value,effective_from=iso(fx['start']),reason='bad'))
    bad=[refused(cur,price(v),'BD_AMOUNT_INVALID') for v in ('-1.00','5000.5',5000,'0.00','NaN','1e3','99999999999999999.00')]
    unknown_with_value=refused(cur,lambda:bd(cur,'SAVE_COMPONENT_RATE',dict(component_id=c,rate_status='UNKNOWN',rate_per_pcs='1.00',effective_from=iso(fx['start']),reason='x')),'BD_RATE_STATUS')
    bd(cur,'SAVE_COMPONENT_RATE',dict(component_id=c,rate_status='KNOWN',rate_per_pcs='5000.00',effective_from=iso(fx['start']),
        effective_to=iso(chain.production.at(fx['day'],6)),reason='closed window'))
    overlap=refused(cur,lambda:bd(cur,'SAVE_COMPONENT_RATE',dict(component_id=c,rate_status='KNOWN',rate_per_pcs='5000.00',
        effective_from=iso(chain.production.at(fx['day'],1)),effective_to=iso(chain.production.at(fx['day'],3)),reason='inside')),'BD_VERSION_OVERLAP')
    after=one(cur,'select count(*) from erp.bd_laundry_component_rates_v1 where component_id=%s',c)
    return verdict(dict(bad_refused=all(b['ok'] for b in bad),unknown_with_value=unknown_with_value['ok'],overlap=overlap['ok'],one_row=(before,after)==(0,1)),
        refusals=[b['refusal'] for b in bad if not b['ok']])


def t12_unknown_component(cur,today):
    """LAU-T12/T09/T34 (M:4350, 4347, 4372): one component known (5,000) and one intentionally UNKNOWN: the delivery posts
    physically, the known subtotal 50,000 is accrued, the rate stays NULL (never 0, never the base rate), status PENDING; close
    is blocked (LAU_PRICE_UNKNOWN while pieces are out, BD_LAUNDRY_COMPONENT_PRICE_UNKNOWN once all are back and costed at
    the known part); the old flat owner estimate is refused; only owner/admin with finance.hpp.manage sets the charge price,
    once; then the line is complete (60,000), accrual follows and the blockers clear."""
    fx=fixture(cur,today,'T12')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    g=component(cur,fx,'GARMENT','5000.00');s=component(cur,fx,'SPRAY',None,status='UNKNOWN')
    process_rate(cur,fx,'100.00');terms(cur,fx,'COMPONENTS')
    sent=post_priced(cur,fx,dict(components=[dict(component_id=g,covered_qty=10),dict(component_id=s,covered_qty=10)]))
    st=line_state(cur,sent['delivery_id']);acc1=accrual(cur,fx['po']);b1=blockers(cur,fx['day'],sent['delivery_id'])
    def flat():
        chain.production.owner(cur)
        return cur.execute('select public.erp_set_laundry_rate_owner_estimate_v1(%s,6000,%s)',(st['line'],'BD flat estimate')).fetchone()[0]
    estimate=refused(cur,flat,'BD_USE_CHARGE_PRICE')
    rec=receive(cur,sent['delivery_id'],fx,10,14)
    cost=one(cur,'select actual_cost from erp.laundry_receipt_lines where receipt_id=%s',rec['receipt_id']);acc2=accrual(cur,fx['po'])
    b2=blockers(cur,fx['day'],sent['delivery_id'])
    unknown=one(cur,"select id::text from erp.bd_laundry_charge_lines_v1 where delivery_line_id=%s and rate_status='UNKNOWN'",st['line'])
    gudang=user(cur,'GUDANG')
    denied=bcp.denied(cur,lambda:bd(cur,'SET_CHARGE_PRICE',dict(charge_line_id=unknown,rate_per_pcs='1000.00',reason='x'),auth=gudang),'')
    zero=refused(cur,lambda:bd(cur,'SET_CHARGE_PRICE',dict(charge_line_id=unknown,rate_per_pcs='0.00',reason='x')),'BD_AMOUNT_INVALID')
    set_=bd(cur,'SET_CHARGE_PRICE',dict(charge_line_id=unknown,rate_per_pcs='1000.00',reason='vendor price arrived'))
    again=refused(cur,lambda:bd(cur,'SET_CHARGE_PRICE',dict(charge_line_id=unknown,rate_per_pcs='2000.00',reason='again')),'BD_PRICE_ALREADY_KNOWN')
    st2=line_state(cur,sent['delivery_id']);acc3=accrual(cur,fx['po']);b3=blockers(cur,fx['day'],sent['delivery_id'])
    cost2=one(cur,'select actual_cost from erp.laundry_receipt_lines where receipt_id=%s',rec['receipt_id'])
    return verdict(dict(physical=st['qty']==10,known_part=st['known']=='50000.00' and st['complete'] is False,rate_null=st['rate'] is None and st['status']=='PENDING',
        accrued_known=acc1['booked']=='50000.00',blocked_out='LAUNDRY_PRICE_UNKNOWN' in b1,flat_estimate_refused=estimate['ok'],
        receipt_known_part=str(cost)=='50000.00' and acc2['booked']=='50000.00',blocked_back=b2==['BD_LAUNDRY_COMPONENT_PRICE_UNKNOWN'],
        denied=denied['ok'],zero_refused=zero['ok'],set=set_['complete'] is True,again_refused=again['ok'],
        complete=st2['known']=='60000.00' and st2['rate']=='6000.00' and st2['status']=='ESTIMATED',receipt_full=str(cost2)=='60000.00',
        accrual_full=acc3['booked']=='60000.00' and acc3['desired']=='60000.00',unblocked=b3==[]),
        states=[st,st2],accruals=[acc1,acc2,acc3],blockers=[b1,b2,b3],denied=denied)


def t13_no_version(cur,today):
    """LAU-T13 (M:4351): a component without any price version is an error, not UNKNOWN: the delivery is refused and nothing
    moves."""
    fx=fixture(cur,today,'T13')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    c=bd(cur,'SAVE_COMPONENT',dict(vendor_id=fx['vendor'],component_code='GARMENT',component_name='BD GARMENT',is_active=True,reason='BD probe'))['component_id']
    terms(cur,fx,'COMPONENTS')
    before=one(cur,'select count(*) from erp.laundry_deliveries where vendor_id=%s',fx['vendor'])
    r=refused(cur,lambda:post_priced(cur,fx,dict(components=[dict(component_id=c,covered_qty=10)])),'BD_COMPONENT_RATE_NOT_EXACT')
    after=one(cur,'select count(*) from erp.laundry_deliveries where vendor_id=%s',fx['vendor'])
    return verdict(dict(refused=r['ok'],nothing=(before,after)==(0,0)),refusal=r)


def t20_lump_sum(cur,today):
    """LAU-T20 (M:4358): a lump sum per batch waits for LAU-DEC01 (BD_POLICY_PENDING); once BATCH is allowed, a synthetic
    100.01 for 10 pieces received as 3 + 3 + 4 is 30.00 + 30.00 + 40.01 (last return takes the residual): exactly 100.01,
    charged once; nothing stays uncosted."""
    fx=fixture(cur,today,'T20')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    pending=refused(cur,lambda:terms(cur,fx,'RATE','BATCH'),'BD_POLICY_PENDING')
    policy(cur,'LAU_DEC01',dict(units=['BATCH']));terms(cur,fx,'RATE','BATCH')
    no_lump=bcp.denied(cur,lambda:post_priced(cur,fx,dict()),'requires non-null key lump_sum')
    sent=post_priced(cur,fx,dict(lump_sum='100.01'))
    costs=[]
    for good,hour in ((3,13),(3,14),(4,15)):
        r=receive(cur,sent['delivery_id'],fx,good,hour)
        costs.append(str(one(cur,'select actual_cost from erp.laundry_receipt_lines where receipt_id=%s',r['receipt_id'])))
    st=line_state(cur,sent['delivery_id']);acc=accrual(cur,fx['po'])
    uncosted=one(cur,'select erp.bd_uncosted_estimate_v1(%s,10,10,null)',st['line'])
    return verdict(dict(pending_refused=pending['ok'],no_lump_refused=no_lump['ok'],
        batch=st['mode']=='BATCH' and st['known']=='100.01',split=costs==['30.00','30.00','40.01'],uncosted_zero=D(str(uncosted))==0,
        accrual=acc['booked']=='100.01'),costs=costs,state=st,accrual=acc,refusals=[pending,no_lump])


def minimum_charge(cur,today):
    """LAU-DEC01 MINIMUM (M:4472): a vendor minimum charge needs the owner's MINIMUM unit; 10 PCS at 7,000 = 70,000 is topped
    up to the synthetic minimum 100,000 by one MINIMUM_TOPUP line; with an unknown component the minimum is refused."""
    fx=fixture(cur,today,'MIN')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    pending=refused(cur,lambda:terms(cur,fx,'COMPONENTS',minimum='100000.00'),'BD_POLICY_PENDING')
    policy(cur,'LAU_DEC01',dict(units=['MINIMUM']));terms(cur,fx,'COMPONENTS',minimum='100000.00')
    g=component(cur,fx,'GARMENT','7000.00');u=component(cur,fx,'SPRAY',None,status='UNKNOWN')
    unknown=refused(cur,lambda:post_priced(cur,fx,dict(components=[dict(component_id=g,covered_qty=10),dict(component_id=u,covered_qty=10)])),'BD_MINIMUM_NEEDS_KNOWN_PRICE')
    sent=post_priced(cur,fx,dict(components=[dict(component_id=g,covered_qty=10)]))
    st=line_state(cur,sent['delivery_id'])
    kinds=[(c['kind'],c['amount']) for c in sent['pricing']['charges']]
    return verdict(dict(pending_refused=pending['ok'],unknown_refused=unknown['ok'],total=st['known']=='100000.00',
        topup=kinds==[('COMPONENT','70000.00'),('MINIMUM_TOPUP','30000.00')]),state=st,charges=kinds)


def t24_scoped(cur,today):
    """LAU-T24/T26 (M:4362, 4364; LAU-DEC05): a scoped rate waits for LAU-DEC05; with scopes MODEL_SIZE and fallback REFUSE a
    size rate of 8,000 prices the 10 pieces at 80,000 (one eligible basis, never stacked on the base rate); a size without
    its own rate is refused under REFUSE and takes the base rate under BASE_RATE (pricing preview of a second size)."""
    fx=fixture(cur,today,'T24')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    process_rate(cur,fx,'5000.00')
    scoped=dict(vendor_id=fx['vendor'],wash_process_id=fx['process'],scope='MODEL_SIZE',model_id=fx['model'],size_id=chain.base.SIZE,
                rate_per_pcs='8000.00',effective_from=iso(fx['start']),reason='BD probe synthetic size rate')
    pending=refused(cur,lambda:bd(cur,'SAVE_SCOPED_RATE',scoped),'BD_POLICY_PENDING')
    policy(cur,'LAU_DEC05',dict(scopes=['MODEL_SIZE'],fallback='REFUSE'))
    bd(cur,'SAVE_SCOPED_RATE',scoped)
    plain=refused(cur,lambda:chain.laundry_action(cur,'POST_DELIVERY',delivery_payload(fx),chain.base.group_version(cur,fx['group'])),'BD_PRICING_REQUIRED')
    other=str(uuid.uuid4())
    preview=dict(delivery_payload(fx),lines=[dict(size_id=chain.base.SIZE,qty_sent_pcs=6),dict(size_id=other,qty_sent_pcs=4)])
    refuse=refused(cur,lambda:compute(cur,preview),'BD_SCOPED_RATE_MISSING')
    policy(cur,'LAU_DEC05',dict(scopes=['MODEL_SIZE'],fallback='BASE_RATE'))
    mixed=compute(cur,preview)
    sent=post_priced(cur,fx,dict())
    st=line_state(cur,sent['delivery_id'])
    return verdict(dict(pending_refused=pending['ok'],plain_refused=plain['ok'],refuse_without_rate=refuse['ok'],
        mixed=mixed['total_known']=='68000.00' and sorted(c['kind'] for c in mixed['charges'])==['RATE','SCOPED_RATE'],
        posted=st['known']=='80000.00' and st['mode']=='SCOPED' and st['charges']==1),state=st,mixed=mixed)


def receipt_process_changed(cur,today):
    """LAU-T15 (M:4353) for a BD-priced delivery: its price was agreed for the process it was sent with; a receipt with another
    actual process is refused (BD_PROCESS_CHANGED) and nothing moves (the recorded limit: such a change needs a new priced
    delivery)."""
    fx=fixture(cur,today,'T15')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    g=component(cur,fx,'GARMENT','5000.00');terms(cur,fx,'COMPONENTS')
    sent=post_priced(cur,fx,dict(components=[dict(component_id=g,covered_qty=10)]))
    other=str(uuid.uuid4())
    cur.execute("insert into erp.wash_processes(id,process_code,process_name,is_active) values(%s,%s,'BD other',true)",(other,'BDO-'+uuid.uuid4().hex[:12]))
    r=refused(cur,lambda:receive(cur,sent['delivery_id'],fx,10,14,process=other),'BD_PROCESS_CHANGED')
    n=one(cur,'select count(*) from erp.laundry_receipts where delivery_id=%s',sent['delivery_id'])
    return verdict(dict(refused=r['ok'],nothing=n==0),refusal=r)


def replay_and_access(cur,today):
    """LAU-T32/T33 (M:4370-4371): the same request key and payload returns the first result without a second effect; the same
    key with another payload is refused; master edits need owner/admin with master.partner.manage (GUDANG and a
    laundry-only role refused at the server); anon has no grant."""
    fx=fixture(cur,today,'T32')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    key=uuid.uuid4();payload=dict(vendor_id=fx['vendor'],component_code='GARMENT',component_name='BD GARMENT',is_active=True,reason='BD probe')
    a=bd(cur,'SAVE_COMPONENT',payload,key=key);b=bd(cur,'SAVE_COMPONENT',payload,key=key)
    reused=refused(cur,lambda:bd(cur,'SAVE_COMPONENT',dict(payload,component_name='other'),key=key),'BD_REQUEST_REUSED')
    n=one(cur,'select count(*) from erp.bd_laundry_components_v1 where vendor_id=%s',fx['vendor'])
    gudang=user(cur,'GUDANG')
    denied=bcp.denied(cur,lambda:bd(cur,'SAVE_COMPONENT',dict(payload,component_code='X'),auth=gudang),'')
    api.admin(cur)
    anon=q(cur,"select has_function_privilege('anon','public.erp_save_laundry_bd_action_v1(text,jsonb,uuid)','execute'),"
              "has_function_privilege('authenticated','erp.bd_set_charge_price_v1(jsonb,uuid)','execute'),"
              "has_table_privilege('authenticated','erp.bd_laundry_charge_lines_v1','select')")[0]
    ws=bd_ws(cur,dict(vendor_id=fx['vendor']))
    return verdict(dict(replayed=b.get('replayed') is True and b['component_id']==a['component_id'],reused_refused=reused['ok'],one_row=n==1,
        denied=denied['ok'],grants=anon==(False,False,False),workspace=isinstance(ws,dict)),grants=anon,denied=denied)


# ---------------------------------------------------------------- BD-3 laundry vendor invoices
def plain_delivery(cur,fx,qty,hour):
    """A baseline (per-PCS) delivery through the ordinary laundry facade (the vendor has no BD terms)."""
    return chain.laundry_action(cur,'POST_DELIVERY',delivery_payload(fx,qty,hour),chain.base.group_version(cur,fx['group']))['delivery_id']


def receipt_line(cur,receipt):
    return str(one(cur,'select id from erp.laundry_receipt_lines where receipt_id=%s',receipt))


def invoice(cur,fx,lines,header,number=None,**extra):
    """Save a draft and post it; returns (draft, posted or None when post is skipped with post=False)."""
    post=extra.pop('post',True)
    payload=dict(vendor_id=fx['vendor'],invoice_number=number or 'INV-'+uuid.uuid4().hex[:10],invoice_date=str(fx['day']),header_total=header,
                 lines=[dict(line_kind=l.get('kind','BILL'),receipt_line_id=l['line'],category=l.get('category','GOOD'),qty=l.get('qty',0),amount=l['amount'])
                        for l in lines],**extra)
    draft=bd(cur,'SAVE_INVOICE_DRAFT',payload)
    if not post:return draft,None
    return draft,bd(cur,'POST_INVOICE',dict(invoice_id=draft['invoice_id'],expected_version=draft['row_version']))


def post_draft(cur,draft):
    return bd(cur,'POST_INVOICE',dict(invoice_id=draft['invoice_id'],expected_version=draft['row_version']))


def ap(cur,vendor):
    return str(one(cur,"select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id "
                       "where j.status in('POSTED','REVERSED') and l.account_id=erp.account_id('AP_VENDOR') and l.vendor_id=%s",vendor))


def wip(cur,po):
    return D(str(one(cur,"select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l where l.po_id=%s and l.account_id=erp.account_id('WIP')",po)))


def pay(cur,invoice_id,amount,day):
    cash=one(cur,'select id::text from erp.cash_accounts where is_active order by cash_account_code limit 1')
    pid=one(cur,'insert into erp.vendor_payments(vendor_invoice_id,payment_number,payment_date,amount,cash_account_id) values(%s,%s,%s,%s,%s) returning id::text',
            invoice_id,'BDPAY-'+uuid.uuid4().hex[:10],str(day)+'T15:00:00+07:00',amount,cash)
    internal(cur,'post_vendor_payment',pid);return pid


def invoice_policies(cur,billable=('GOOD','BS','FAILED_ATTEMPT'),mode='PRODUCT_COST',after='REFUSE',account=None):
    policy(cur,'LAU_DEC02',dict(billable=list(billable)))
    value=dict(variance_mode=mode,after_payment=after)
    if account:value['variance_account_id']=account
    policy(cur,'LAU_DEC06',value)


def t16_invoice_above_estimate(cur,today):
    """LAU-T16/T10 (M:4354, M:4348): 10 PCS at a synthetic 7,000 accrue 70,000 until the invoice; a draft may wait but posting
    waits for LAU-DEC02 and LAU-DEC06 (BD_POLICY_PENDING); an invoice of 75,000 replaces the accrual (accrual 0), AP +75,000,
    and the +5,000 difference stays in product cost (WIP) under PRODUCT_COST; the payable is an ordinary vendor invoice."""
    fx=fixture(cur,today,'T16')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    process_rate(cur,fx,'7000.00');d=plain_delivery(cur,fx,10,11);rec=receive(cur,d,fx,10,13);line=receipt_line(cur,rec['receipt_id'])
    before=dict(accrual=accrual(cur,fx['po']),ap=ap(cur,fx['vendor']),wip=wip(cur,fx['po']))
    draft,_=invoice(cur,fx,[dict(line=line,qty=10,amount='75000.00')],'75000.00',post=False)
    pending=refused(cur,lambda:post_draft(cur,draft),'BD_POLICY_PENDING')
    invoice_policies(cur)
    posted=post_draft(cur,draft)
    after=dict(accrual=accrual(cur,fx['po']),ap=ap(cur,fx['vendor']),wip=wip(cur,fx['po']))
    vi=q(cur,'select status,total_amount from erp.vendor_invoices where id=%s',posted['invoice_id'])[0]
    l0=posted['lines'][0]
    return verdict(dict(draft_saved=draft['status']=='DRAFT',pending_refused=pending['ok'],accrued_before=before['accrual']['booked']=='70000.00',
        accrual_replaced=after['accrual']=={'desired':'0.00','booked':'0.00'} or (D(after['accrual']['desired'])==0 and D(after['accrual']['booked'])==0),
        ap=D(after['ap'])-D(before['ap'])==75000,variance_in_wip=after['wip']-before['wip']==5000,
        line=(l0['released_estimate'],l0['variance'],l0['product_variance'],l0['completes_source'])==('70000.00','5000.00','5000.00',True),
        payable=(vi[0],str(vi[1]))==('POSTED','75000.00')),before=before,after=after,line=l0)


def t17_partial_nm_capacity(cur,today):
    """LAU-T17/T18/T19 (M:4355-4357): two deliveries (6 and 4 PCS at 7,000); invoice A bills 3 of the first and all 4 of the
    second (one invoice, two deliveries), invoice B bills the other 3 of the first (one delivery, two invoices); a third invoice
    under a new request key for 1 more piece is refused (capacity is the source's, not the key's); released 21,000 + 28,000
    then the residual 21,000; accrual 0 at the end."""
    fx=fixture(cur,today,'T17')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    process_rate(cur,fx,'7000.00');invoice_policies(cur)
    d1=plain_delivery(cur,fx,6,11);d2=plain_delivery(cur,fx,4,12)
    l1=receipt_line(cur,receive(cur,d1,fx,6,13)['receipt_id']);l2=receipt_line(cur,receive(cur,d2,fx,4,14)['receipt_id'])
    _,a=invoice(cur,fx,[dict(line=l1,qty=3,amount='21000.00'),dict(line=l2,qty=4,amount='28000.00')],'49000.00')
    mid=accrual(cur,fx['po'])
    over=refused(cur,lambda:invoice(cur,fx,[dict(line=l1,qty=4,amount='28000.00')],'28000.00'),'BD_INVOICE_CAPACITY')
    _,b=invoice(cur,fx,[dict(line=l1,qty=3,amount='21000.00')],'21000.00')
    again=refused(cur,lambda:invoice(cur,fx,[dict(line=l1,qty=1,amount='7000.00')],'7000.00'),'BD_INVOICE_CAPACITY')
    end=accrual(cur,fx['po'])
    rel=[(x['qty'],x['released_estimate'],x['completes_source']) for x in a['lines']+b['lines']]
    return verdict(dict(mid_accrual=mid['booked']=='21000.00',over_refused=over['ok'],again_refused=again['ok'],
        released=rel==[(3,'21000.00',False),(4,'28000.00',True),(3,'21000.00',True)],end_accrual=D(end['booked'])==0 and D(end['desired'])==0),
        released=rel,accruals=[mid,end])


def t21_discount_tax_rounding(cur,today):
    """LAU-T21 (M:4359): discount, tax and a rounding line wait for LAU-DEC03 (BD_POLICY_PENDING); refused when the owner
    refuses discount; a header total that is not lines - discount + rounding + tax is refused; with discount ALLOWED,
    rounding LAST_LINE and an input tax account: 70,000 - 1,000 - 0.40 + 6,930 = 75,929.60 payable, tax on its account,
    product cost 68,999.60 (variance -1,000.40)."""
    fx=fixture(cur,today,'T21')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    process_rate(cur,fx,'7000.00');invoice_policies(cur)
    line=receipt_line(cur,receive(cur,plain_delivery(cur,fx,10,11),fx,10,13)['receipt_id'])
    extra=dict(discount_amount='1000.00',tax_amount='6930.00',rounding_amount='-0.40')
    pending=refused(cur,lambda:invoice(cur,fx,[dict(line=line,qty=10,amount='70000.00')],'75929.60',**extra),'BD_POLICY_PENDING')
    tax_account=one(cur,"select id::text from erp.chart_accounts where account_type='ASSET' and is_postable and is_active and account_code='1500'")
    policy(cur,'LAU_DEC03',dict(discount='REFUSED',extra='REFUSED',rounding='LAST_LINE',tax_account_id=tax_account))
    no_discount=refused(cur,lambda:invoice(cur,fx,[dict(line=line,qty=10,amount='70000.00')],'75929.60',**extra),'BD_DISCOUNT_REFUSED')
    policy(cur,'LAU_DEC03',dict(discount='ALLOWED',extra='REFUSED',rounding='LAST_LINE',tax_account_id=tax_account))
    mismatch=refused(cur,lambda:invoice(cur,fx,[dict(line=line,qty=10,amount='70000.00')],'75930.00',**extra),'BD_INVOICE_TOTAL_MISMATCH')
    before=dict(ap=ap(cur,fx['vendor']),tax=bcp.gl_account(cur,tax_account))
    _,posted=invoice(cur,fx,[dict(line=line,qty=10,amount='70000.00')],'75929.60',**extra)
    l0=posted['lines'][0]
    return verdict(dict(pending_refused=pending['ok'],discount_refused=no_discount['ok'],mismatch_refused=mismatch['ok'],
        ap=D(ap(cur,fx['vendor']))-D(before['ap'])==D('75929.60'),tax=bcp.gl_account(cur,tax_account)-before['tax']==D('6930.00'),
        line=(l0['discount_share'],l0['rounding_share'],l0['net_amount'],l0['variance'])==('1000.00','-0.40','68999.60','-1000.40')),line=l0)


def dec06_variance_account(cur,today):
    """LAU-DEC06 VARIANCE_ACCOUNT (M:4477): the owner's expense variance account takes invoice - estimate (+5,000); WIP keeps
    the estimate only (no product variance); an asset account is refused as variance account."""
    fx=fixture(cur,today,'DEC06')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    process_rate(cur,fx,'7000.00')
    expense=one(cur,"select id::text from erp.chart_accounts where account_type='EXPENSE' and is_postable and is_active and account_code='5100'")
    invoice_policies(cur,mode='VARIANCE_ACCOUNT',account=expense)
    line=receipt_line(cur,receive(cur,plain_delivery(cur,fx,10,11),fx,10,13)['receipt_id'])
    before=dict(wip=wip(cur,fx['po']),var=bcp.gl_account(cur,expense))
    _,posted=invoice(cur,fx,[dict(line=line,qty=10,amount='75000.00')],'75000.00')
    l0=posted['lines'][0]
    return verdict(dict(variance_account=bcp.gl_account(cur,expense)-before['var']==5000,wip_unchanged=wip(cur,fx['po'])==before['wip'],
        no_product_variance=l0['product_variance']=='0.00' and l0['variance']=='5000.00',mode=posted['variance_mode']=='VARIANCE_ACCOUNT'),line=l0)


def t23_reverse_pay_correct(cur,today):
    """LAU-T23 (M:4361), LAU-DEC06 after payment: an unpaid invoice is reversed (payable REVERSED, accrual back to 70,000,
    AP back) and replaced; while posted the receipt cannot be reversed; once paid it cannot be reversed (BD_INVOICE_PAID); a
    correction line after payment is refused under REFUSE and posted as a linked correction document under
    CORRECTION_DOCUMENT (+2,000 payable, product cost +2,000)."""
    fx=fixture(cur,today,'T23')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    process_rate(cur,fx,'7000.00');invoice_policies(cur)
    rec=receive(cur,plain_delivery(cur,fx,10,11),fx,10,13);line=receipt_line(cur,rec['receipt_id'])
    ap0=D(ap(cur,fx['vendor']))
    _,first=invoice(cur,fx,[dict(line=line,qty=10,amount='72000.00')],'72000.00')
    rv=one(cur,'select row_version from erp.laundry_receipts where id=%s',rec['receipt_id'])
    receipt_locked=refused(cur,lambda:chain.laundry_action(cur,'REVERSE_RECEIPT',dict(receipt_id=rec['receipt_id'],reason='BD probe reverse invoiced receipt'),rv),
                           'BD_RECEIPT_INVOICED')
    rev=bd(cur,'REVERSE_INVOICE',dict(invoice_id=first['invoice_id'],expected_version=first['row_version'],reason='salah nominal'))
    back=dict(accrual=accrual(cur,fx['po']),ap=D(ap(cur,fx['vendor']))-ap0,vi=one(cur,'select status from erp.vendor_invoices where id=%s',first['invoice_id']))
    _,second=invoice(cur,fx,[dict(line=line,qty=10,amount='71000.00')],'71000.00',number=first['invoice_number'])
    pay(cur,second['invoice_id'],'10000.00',fx['day'])
    s2=q(cur,'select row_version from erp.bd_laundry_invoices_v1 where id=%s',second['invoice_id'])[0][0]
    paid=refused(cur,lambda:bd(cur,'REVERSE_INVOICE',dict(invoice_id=second['invoice_id'],expected_version=str(s2),reason='x')),'BD_INVOICE_PAID')
    refuse=refused(cur,lambda:invoice(cur,fx,[dict(line=line,kind='CORRECTION',amount='2000.00')],'2000.00'),'BD_PAID_CORRECTION_REFUSED')
    invoice_policies(cur,after='CORRECTION_DOCUMENT')
    w=wip(cur,fx['po']);a=D(ap(cur,fx['vendor']))
    _,corr=invoice(cur,fx,[dict(line=line,kind='CORRECTION',amount='2000.00')],'2000.00')
    return verdict(dict(receipt_locked=receipt_locked['ok'],reversed=rev['status']=='REVERSED' and back['vi']=='REVERSED',
        accrual_back=back['accrual']['booked']=='70000.00',ap_back=back['ap']==0,replaced=second['status']=='POSTED',paid_refused=paid['ok'],
        correction_refused=refuse['ok'],correction=corr['status']=='POSTED' and D(ap(cur,fx['vendor']))-a==2000 and wip(cur,fx['po'])-w==2000),
        back={k:str(v) for k,v in back.items()})


def dec02_categories(cur,today):
    """LAU-DEC02 (M:4473): only the categories the owner makes billable can be billed (GOOD when only BS is billable is refused);
    a draft is kept; a line with another vendor's receipt is refused; access: GUDANG cannot draft an invoice."""
    fx=fixture(cur,today,'DEC02')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    process_rate(cur,fx,'7000.00');invoice_policies(cur,billable=('BS',))
    line=receipt_line(cur,receive(cur,plain_delivery(cur,fx,10,11),fx,10,13)['receipt_id'])
    draft,_=invoice(cur,fx,[dict(line=line,qty=10,amount='70000.00')],'70000.00',post=False)
    cat=refused(cur,lambda:post_draft(cur,draft),'BD_CATEGORY_NOT_BILLABLE')
    other=dict(fx,vendor=str(uuid.uuid4()))
    cur.execute("insert into erp.laundry_vendors(id,vendor_code,vendor_name,is_active) values(%s,%s,'BD other vendor',true)",(other['vendor'],'BDV-'+uuid.uuid4().hex[:10]))
    foreign=refused(cur,lambda:invoice(cur,other,[dict(line=line,qty=1,amount='7000.00')],'7000.00',post=False),'BD_INVOICE_VENDOR')
    gudang=user(cur,'GUDANG')
    denied=bcp.denied(cur,lambda:bd(cur,'SAVE_INVOICE_DRAFT',dict(vendor_id=fx['vendor'],invoice_number='X',invoice_date=str(fx['day']),header_total='1.00',
        lines=[dict(line_kind='BILL',receipt_line_id=line,category='GOOD',qty=1,amount='1.00')]),auth=gudang),'')
    return verdict(dict(category_refused=cat['ok'],draft_kept=one(cur,'select status from erp.bd_laundry_invoices_v1 where id=%s',draft['invoice_id'])=='DRAFT',
        foreign_refused=foreign['ok'],denied=denied['ok']),refusals=[cat,foreign,denied])


PLAN=[('POLICY:LAU_DEC_SETTINGS_OWNER_VERSIONED_PENDING','NO_ROUTE',policy_settings),
      ('T02:PACKAGE_ONE_CHARGE_PHYSICAL_QTY','NO_ROUTE',t02_package),
      ('T03:COMPONENT_SUM_SAME_PIECES','NO_ROUTE',lambda c,t:t03_t04_components(c,t,False)),
      ('T04:FOUR_COMPONENTS','NO_ROUTE',lambda c,t:t03_t04_components(c,t,True)),
      ('T05:PARTIAL_COMPONENT_COVERAGE','NO_ROUTE',t05_partial_coverage),
      ('T06:PACKAGE_EXTRA_ONCE','NO_ROUTE',t06_package_extra),
      ('T07:VERSION_AFTER_POSTED_DELIVERY','NO_ROUTE',t07_versions),
      ('T08:BAD_NOMINAL_REFUSED','NO_ROUTE',t08_bad_nominal),
      ('T12:UNKNOWN_COMPONENT_KNOWN_SUBTOTAL','NO_ROUTE',t12_unknown_component),
      ('T13:NO_VERSION_IS_ERROR','NO_ROUTE',t13_no_version),
      ('T15:BD_RECEIPT_PROCESS_CHANGED','NO_ROUTE',receipt_process_changed),
      ('T20:LUMP_SUM_SPLIT_RECEIPTS','NO_ROUTE',t20_lump_sum),
      ('DEC01:MINIMUM_CHARGE_TOPUP','NO_ROUTE',minimum_charge),
      ('T24:SCOPED_SIZE_RATE','NO_ROUTE',t24_scoped),
      ('T32:REPLAY_ACCESS_GRANTS','NO_ROUTE',replay_and_access),
      ('T16:INVOICE_ABOVE_ESTIMATE_PRODUCT_COST','NO_ROUTE',t16_invoice_above_estimate),
      ('T17:PARTIAL_NM_CAPACITY','NO_ROUTE',t17_partial_nm_capacity),
      ('T21:DISCOUNT_TAX_ROUNDING','NO_ROUTE',t21_discount_tax_rounding),
      ('DEC06:VARIANCE_ACCOUNT','NO_ROUTE',dec06_variance_account),
      ('T23:REVERSE_PAY_CORRECT','NO_ROUTE',t23_reverse_pay_correct),
      ('DEC02:BILLABLE_CATEGORIES_ACCESS','NO_ROUTE',dec02_categories)]
assert len({k for k,_,_ in PLAN})==len(PLAN),'BD_DUPLICATE_CASE_ID'


def cases(cur,today):
    day=case_day(today)
    return [(key,lambda f=fn:f(cur,day)) for key,_,fn in PLAN]


def run(phase):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    r1.OUT=OUT
    planned={k:(e if isinstance(e,tuple) else (e,)) if phase=='before' else ('PASS',) for k,e,_ in PLAN}
    report=dict(status='INCOMPLETE',label=LABEL,phase=phase,source=r1.source(),production_go=False,independent_acceptance=False,release_evidence=False,
                planned={k:list(v) for k,v in planned.items()})
    report['run_identity']=run_identity.announce(LABEL,phase=phase)
    r1.save('RESULT_'+phase.upper(),report)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        r1.writer.install_at()
        control_url=os.environ['CP6_ADMISSION_CONTROL_PGURL']
        awp,axp,ayp,azp,bap=bbp.awp,bbp.axp,bbp.ayp,bbp.azp,bbp.bap
        report['au_install']=awp.au_runtime.change('install',boundary.PG,control_url)['status']
        report['av_install']=awp.av_runtime.change('install',boundary.PG,control_url)['status']
        report['aw_install']=awp.install_aw();report['ax_install']=axp.install_ax();report['ay_install']=ayp.install_ay()
        report['az_install']=azp.install_az();report['ba_install']=bap.install_ba();report['bb_install']=bbp.install_bb()
        report['bc_install']=bcp.install_bc();verify=bcp.bc_verified
        if phase=='after':report['bd_install']=install_bd();verify=bd_verified
        r1.save('RESULT_'+phase.upper(),report)
        print(json.dumps(dict(bd_probe_setup={k:report.get(k) for k in ('au_install','av_install','bc_install','bd_install')}),default=str),flush=True)
        group=r1.group('BD_CASES_'+phase.upper(),cases,verify)
        report['bd_cases']={k:group[k] for k in ('status','counts')}
        final={k:v['status'] for k,v in group['cases'].items()}
        report['final']=final
        report['expectation_mismatch']={k:dict(planned=list(e),final=final.get(k)) for k,e in planned.items() if final.get(k) not in e}
        report['status']='REVIEW_COMPLETE' if group['status']!='INCOMPLETE' and not report['expectation_mismatch'] else 'INCOMPLETE'
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        r1.save('RESULT_'+phase.upper(),report)
    print(json.dumps(dict(bd_probe_phase=phase,**{k:v for k,v in report.items() if k!='source'}),default=str),flush=True)
    assert report['status']=='REVIEW_COMPLETE',report.get('error') or ('BD_PROBE_EXPECTATION_MISMATCH',report.get('expectation_mismatch'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('before','after'),required=True)
    run(parser.parse_args().phase)
