"""BD T1_FAMILY probe: priced laundry deliveries (LAU-05b: package, components with partial coverage, lump sum per batch,
minimum charge, scoped rates), laundry vendor invoices, the laundry policy settings LAU-DEC01..06 and ALL-W05 physical
(laundry claims and uninvoiced returns at cutover), before and after.

Label T1_FAMILY: targeted family evidence on the disposable chain AN -> AU -> AV -> AW..AZ -> BA -> BB -> BC (+ BD in phase
'after'), never release evidence. Oracles come from the contract (M:4339-4374 LAU-T01..T36, LAU-05b, LAU-DEC01..06 M:4472-4477)
and the auditors' pre-code oracles (gpt_lau.md, fable_lau.md; ALL-W05 from the r9 ALL oracle), never from observed behaviour; where two readings differ the
more fail-closed one is used. Amounts are synthetic fixtures (no real tariff is invented). Outcomes:
  NO_ROUTE       phase 'before' only: no BD facade before BD (the public RPC is unknown); nothing changes.
  PASS / FAIL    the oracle holds / does not hold. A refusal with another code, or a wrong NO_ROUTE, is INCOMPLETE.
Each case runs inside the group's rolled-back savepoint; nothing is committed to the clone.
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys,tempfile,traceback,uuid
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


def two_size_fixture(cur,today,label,q1=6,q2=4):
    """The chain's production fixture (cp6_aa partial_production) with two sizes: one roll of 10 cut into q1 of the base size
    and q2 of a fresh RFC size of the same model, one pickup batch, a zero-rate sewing completion of all pieces and its
    terminal. Only masters are seeded (the second size, its model link and product); every movement is an ordinary posting."""
    prod,base=chain.production,chain.base
    f=prod.estimated_receipt(cur,today)
    chain.actors.admin(cur)
    day=f['purchase_day']+timedelta(days=1)
    size2=str(uuid.uuid4())
    cur.execute('insert into erp.sizes(id,size_code,sort_order,is_active) values(%s,%s,99,true)',(size2,'BD2-'+size2[:8]))
    cur.execute('insert into erp.product_model_sizes(model_id,size_id,sort_order) values(%s,%s,99)',(prod.MODEL,size2))
    po=str(uuid.uuid4())
    cur.execute("""insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
      values(%s,%s,%s,%s,'CUTTING','CUTTING',%s,'BD two-size lot')""",(po,'BD2-PO-'+po,prod.MODEL,q1+q2,prod.at(day,7)))
    cut_payload=dict(action='SAVE_DRAFT',po_id=po,pattern_id=prod.PATTERN,source_location_id=f['location'],cut_at=prod.at(day,8),
                     change_reason='BD two-size cutting',
                     size_slots=[dict(slot_no=1,size_id=base.SIZE,drawing_no=1),dict(slot_no=2,size_id=size2,drawing_no=1)],
                     rolls=[dict(roll_id=f['roll'],qty_issued=10,qty_consumed=10,qty_reported_remaining=0,
                                 yields=[dict(slot_no=1,qty_pcs=q1),dict(slot_no=2,qty_pcs=q2)])])
    cut=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',cut_payload)
    group=cut['cutting_group_id']
    cut=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(cut_payload,id=group,action='POST'),expected_version=int(cut['row_version']))
    chain.actors.admin(cur)
    yields=q(cur,"""select y.id::text,s.size_id::text,y.qty_pcs from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
      join erp.cutting_group_size_slots s on s.id=y.size_slot_id where r.cutting_group_id=%s order by s.slot_no""",group)
    assert [(s,n) for _,s,n in yields]==[(base.SIZE,q1),(size2,q2)],('BD_TWO_SIZE_YIELDS',yields)
    pickup_payload=dict(action='SAVE_DRAFT',cutting_group_id=group,contractor_id=prod.CONTRACTOR,picked_up_at=prod.at(day,9),allocation_mode='ROLL',
                        expected_group_version=int(cut['row_version']),change_reason='BD two-size pickup',
                        batches=[dict(batch_no=1,allocations=[dict(cutting_roll_yield_id=y,qty_pcs=n) for y,_,n in yields])])
    pickup=prod.rpc(cur,'public.erp_save_cutting_pickup_v1',pickup_payload)
    pickup=prod.rpc(cur,'public.erp_save_cutting_pickup_v1',dict(pickup_payload,id=pickup['pickup_id'],action='POST'),expected_version=int(pickup['row_version']))
    chain.actors.admin(cur)
    batch=one(cur,'select id::text from erp.cutting_distribution_batches where pickup_id=%s',pickup['pickup_id'])
    snapshot,completion=str(uuid.uuid4()),str(uuid.uuid4())
    cur.execute('insert into erp.po_work_component_snapshots(id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at) values(%s,%s,%s,1,0,%s)',
                (snapshot,po,prod.COMPONENT,prod.at(day,9,30)))
    chain.peer.ordinary(cur)
    cur.execute("""insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)
      values(%s,%s,%s,%s,%s,%s,'DRAFT','BD two-size sewing draft',%s)""",(completion,'BD2-WC-'+completion,po,prod.CONTRACTOR,group,prod.at(day,10),base.OPERATOR_APP))
    cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot) values(%s,%s,%s,%s,%s,0)',
                (completion,snapshot,prod.COMPONENT,q1+q2,q1+q2))
    cur.execute('select erp.post_work_completion(%s)',(completion,))
    prod.owner(cur)
    cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)',
        (json.dumps(dict(work_completion_id=completion,qty_pcs=q1+q2,reason='BD '+label+' two-size terminal')),uuid.uuid4()))
    chain.actors.admin(cur)
    vendor=str(uuid.uuid4());process=str(uuid.uuid4());tag=uuid.uuid4().hex[:12]
    cur.execute("insert into erp.laundry_vendors(id,vendor_code,vendor_name,is_active) values(%s,%s,%s,true)",(vendor,'BD-'+tag,'BD vendor '+label))
    cur.execute("insert into erp.wash_processes(id,process_code,process_name,is_active) values(%s,%s,%s,true)",(process,'BDP-'+tag,'BD wash '+label))
    return dict(day=day,batch=batch,model=prod.MODEL,vendor=vendor,process=process,group=group,po=po,size2=size2,q1=q1,q2=q2,
                start=prod.at(day,0),send=prod.at(day,11))


def sized_product(cur,size,label):
    """A fresh product of the base model in the given size: the chain's create_product with the size chosen at insert (a
    product's size is immutable once the row exists, erp.validate_product_identity_period)."""
    product=str(uuid.uuid4())
    cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,is_active,is_portal_visible)
      select %s,%s,model_id,brand_id,%s,%s,%s,%s,effective_from,true,true from erp.products where id=%s""",
      (product,'CP6-E-'+label,'CP6-E-'+label,size,'CP6 E '+label,product,chain.base.BASE_PRODUCT))
    cur.execute("insert into erp.accessory_bom_versions(product_id,version_label,effective_from,is_active,notes) values(%s,'CP6-E-EMPTY','2026-01-01',true,'Explicit empty BOM')",
                (product,))
    return product


def t24_multi_size_lot_hpp(cur,today):
    """LAU-T24/T26 with two sizes in one BD delivery (the multi-size lot limit of BD): 6 pieces of the base size at a scoped
    8,000 and 4 of a second size at the base rate 5,000 (LAU-DEC05 MODEL_SIZE, fallback BASE_RATE) are sent, returned and
    finished into one FG lot per size. Each lot takes its own size's laundry (8,000 and 5,000 a piece, never the 6,800 mean);
    the other costs per piece are equal. A vendor invoice of 70,000 (PRODUCT_COST) spreads its 2,000 over the receipt line's
    pieces: 1,200 and 800."""
    fx=two_size_fixture(cur,today,'T24M')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    base=chain.base
    process_rate(cur,fx,'5000.00');invoice_policies(cur)
    policy(cur,'LAU_DEC05',dict(scopes=['MODEL_SIZE'],fallback='BASE_RATE'))
    bd(cur,'SAVE_SCOPED_RATE',dict(vendor_id=fx['vendor'],wash_process_id=fx['process'],scope='MODEL_SIZE',model_id=fx['model'],size_id=base.SIZE,
                                   rate_per_pcs='8000.00',effective_from=iso(fx['start']),reason='BD probe synthetic size rate'))
    payload=dict(distribution_batch_id=fx['batch'],vendor_id=fx['vendor'],wash_process_id=fx['process'],target_dyeing_color='BD-COLOR',
                 physical_at=iso(chain.production.at(fx['day'],11)),reason='BD probe two-size delivery',
                 lines=[dict(size_id=base.SIZE,qty_sent_pcs=fx['q1']),dict(size_id=fx['size2'],qty_sent_pcs=fx['q2'])])
    sent=bd(cur,'POST_PRICED_DELIVERY',dict(delivery=payload,expected_version=str(base.group_version(cur,fx['group'])),pricing=dict()))
    delivery=sent['delivery_id']
    sizes=dict(q(cur,"""select x.size_id::text,x.id::text from erp.laundry_delivery_batch_size_lines x join erp.laundry_delivery_lines l on l.id=x.delivery_line_id
      where l.delivery_id=%s""",delivery))
    estimates={s:str(one(cur,'select known_amount from erp.bd_laundry_size_estimates_v1 where delivery_batch_size_line_id=%s',i)) for s,i in sizes.items()}
    rec=chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=delivery,wash_process_id=fx['process'],physical_at=iso(chain.production.at(fx['day'],13)),
        reason='BD probe two-size return',lines=[dict(delivery_batch_size_line_id=sizes[s],qty_good_received=n,qty_bs_laundry=0,bs_product_id=None)
                                                 for s,n in ((base.SIZE,fx['q1']),(fx['size2'],fx['q2']))]),base.delivery_version(cur,delivery))
    line=receipt_line(cur,rec['receipt_id'])
    rsl=dict(q(cur,"""select d.size_id::text,x.id::text from erp.laundry_receipt_batch_size_lines x
      join erp.laundry_delivery_batch_size_lines d on d.id=x.delivery_batch_size_line_id where x.receipt_line_id=%s""",line))
    allocations={s:str(one(cur,'select amount from erp.bd_laundry_receipt_allocations_v1 where receipt_batch_size_line_id=%s',i)) for s,i in rsl.items()}
    p1=sized_product(cur,base.SIZE,'BDM1-'+uuid.uuid4().hex[:8]);p2=sized_product(cur,fx['size2'],'BDM2-'+uuid.uuid4().hex[:8])
    chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=fx['group'],destination_location_id=base.LOCATION,
        physical_at=iso(chain.production.at(fx['day'],14)),reason='BD probe two-size finished goods',good_qty_pcs=fx['q1']+fx['q2'],completion_mode='ALL_READY',
        lines=[dict(final_product_id=p,qty_good_pcs=n,qty_bs_pcs=0,source_laundry_receipt_line_id=line,source_laundry_receipt_batch_size_line_id=rsl[s])
               for p,s,n in ((p1,base.SIZE,fx['q1']),(p2,fx['size2'],fx['q2']))]),base.group_version(cur,fx['group']))
    lots=[one(cur,"select id::text from erp.fg_lots where po_id=%s and product_id=%s and lot_origin='PRODUCTION'",fx['po'],p) for p in (p1,p2)]
    def per_piece(lot):return D(str(one(cur,'select hpp_per_pcs from erp.hpp_versions where lot_id=%s and is_current',lot)))
    v0=[lot_value(cur,l) for l in lots];u0=[per_piece(l) for l in lots]
    other=[(v0[0]-8000*fx['q1'])/fx['q1'],(v0[1]-5000*fx['q2'])/fx['q2']]
    wip0=wip(cur,fx['po'])
    _,posted=invoice(cur,fx,[dict(line=line,qty=fx['q1']+fx['q2'],amount='70000.00')],'70000.00')
    v1=[lot_value(cur,l) for l in lots]
    return verdict(dict(estimates=estimates=={base.SIZE:'48000.00',fx['size2']:'20000.00'},
        allocations=allocations=={base.SIZE:'48000.00',fx['size2']:'20000.00'},
        receipt_line_cost=str(one(cur,'select actual_cost from erp.laundry_receipt_lines where id=%s',line))=='68000.00',
        two_lots=len(set(lots))==2,
        per_size_laundry=u0[0]-u0[1]==3000,
        other_costs_equal_per_piece=other[0]==other[1],
        variance_by_pieces=[v1[0]-v0[0],v1[1]-v0[1]]==[1200,800],
        nothing_left_in_wip=wip(cur,fx['po'])==wip0),
        estimates=estimates,allocations=allocations,lot_values=[str(x) for x in v0],after_invoice=[str(x) for x in v1],
        per_piece=[str(x) for x in u0],other_per_piece=[str(x) for x in other])


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


def finish_goods(cur,fx,receipt,qty,hour):
    """POST_FINAL_SKU of the returned pieces into an FG lot of a fresh product (the chain's own production path)."""
    product=chain.base.create_product(cur,'BD-'+uuid.uuid4().hex[:8])
    size,line=q(cur,'select x.id::text,x.receipt_line_id::text from erp.laundry_receipt_batch_size_lines x join erp.laundry_receipt_lines l on l.id=x.receipt_line_id where l.receipt_id=%s',receipt)[0]
    chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=fx['group'],destination_location_id=chain.base.LOCATION,
        physical_at=iso(chain.production.at(fx['day'],hour)),reason='BD probe finished goods',good_qty_pcs=qty,completion_mode='ALL_READY',
        lines=[dict(final_product_id=product,qty_good_pcs=qty,qty_bs_pcs=0,source_laundry_receipt_line_id=line,source_laundry_receipt_batch_size_line_id=size)]),
        chain.base.group_version(cur,fx['group']))
    lot=one(cur,"select id::text from erp.fg_lots where po_id=%s and product_id=%s and lot_origin='PRODUCTION'",fx['po'],product)
    return product,lot


def sell(cur,fx,product,qty,hour):
    customer=chain.base.create_customer(cur,'BD-'+uuid.uuid4().hex[:8])
    chain.production.owner(cur)
    sale=cur.execute('select erp.save_sale_draft_v2(%s::jsonb,%s::uuid,null)',(json.dumps(dict(sale_number='BD-SALE-'+uuid.uuid4().hex[:10],
        customer_id=customer,source_location_id=chain.base.LOCATION,sale_date=iso(chain.production.at(fx['day'],hour)),reason='BD probe sale',
        items=[dict(product_id=product,qty_pcs=qty,unit_price_snapshot='20000',discount_amount=0)])),str(uuid.uuid4()))).fetchone()[0]
    version=one(cur,'select row_version from erp.sales_headers where id=%s',sale['sale_id'])
    chain.production.owner(cur);cur.execute('select erp.post_sale_v2(%s,%s,%s)',(sale['sale_id'],uuid.uuid4(),version))
    chain.actors.admin(cur);return sale['sale_id']


def lot_value(cur,lot):
    return D(str(one(cur,'select total_cost from erp.hpp_versions where lot_id=%s and is_current',lot)))


def t22_variance_to_fg_and_cogs(cur,today):
    """LAU-T22 (M:4360): 10 PCS at a synthetic 7,000 are finished (one FG lot, laundry 70,000), 4 are sold; an invoice of
    75,000 (PRODUCT_COST) raises the lot's laundry cost to 75,000: unsold FG and the sold quantity's cost of sales take the
    difference, nothing stays in WIP, and the delta adds up to 5,000."""
    fx=fixture(cur,today,'T22')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    process_rate(cur,fx,'7000.00');invoice_policies(cur)
    rec=receive(cur,plain_delivery(cur,fx,10,11),fx,10,13)
    product,lot=finish_goods(cur,fx,rec['receipt_id'],10,14)
    sell(cur,fx,product,4,16)
    keys=('WIP','FG_INVENTORY','COGS')
    before={k:gl(cur,k) for k in keys};lv0=lot_value(cur,lot)
    _,posted=invoice(cur,fx,[dict(line=receipt_line(cur,rec['receipt_id']),qty=10,amount='75000.00')],'75000.00')
    after={k:gl(cur,k) for k in keys};lv1=lot_value(cur,lot)
    delta={k:after[k]-before[k] for k in keys}
    return verdict(dict(lot_up_5000=lv1-lv0==5000,no_wip_left=delta['WIP']==0,fg_and_cogs=delta['FG_INVENTORY']+delta['COGS']==5000,
        cogs_share=delta['COGS']==2000,fg_share=delta['FG_INVENTORY']==3000),lot_values=[str(lv0),str(lv1)],delta={k:str(v) for k,v in delta.items()})


def dec04_sale_unknown_laundry(cur,today):
    """LAU-04/LAU-T34/LAU-DEC04 (M:4475, M:4372): finished goods from a delivery with an UNKNOWN component price cannot be sold
    while LAU-DEC04 is pending or REFUSE (BD_SALE_LAUNDRY_PRICE_UNKNOWN, nothing posted); with ALLOW_PENDING the sale posts
    and close stays blocked; once the price is set the goods sell under a refusing policy too."""
    fx=fixture(cur,today,'DEC04')
    if not bd_installed(cur):return no_route(cur,lambda:route_call(cur))
    g=component(cur,fx,'GARMENT','5000.00');s=component(cur,fx,'SPRAY',None,status='UNKNOWN');terms(cur,fx,'COMPONENTS')
    sent=post_priced(cur,fx,dict(components=[dict(component_id=g,covered_qty=10),dict(component_id=s,covered_qty=10)]))
    rec=receive(cur,sent['delivery_id'],fx,10,13);product,lot=finish_goods(cur,fx,rec['receipt_id'],10,14)
    pending=refused(cur,lambda:sell(cur,fx,product,2,15),'BD_SALE_LAUNDRY_PRICE_UNKNOWN')
    policy(cur,'LAU_DEC04',dict(sale_with_unknown_laundry='REFUSE'))
    refuse=refused(cur,lambda:sell(cur,fx,product,2,15),'BD_SALE_LAUNDRY_PRICE_UNKNOWN')
    posted_none=one(cur,"select count(*) from erp.sales_items i join erp.sales_headers h on h.id=i.sale_id where i.product_id=%s and h.status='POSTED'",product)
    policy(cur,'LAU_DEC04',dict(sale_with_unknown_laundry='ALLOW_PENDING'))
    sell(cur,fx,product,2,15)
    blocked=blockers(cur,fx['day'],sent['delivery_id'])
    policy(cur,'LAU_DEC04',dict(sale_with_unknown_laundry='REFUSE'))
    unknown=one(cur,"select id::text from erp.bd_laundry_charge_lines_v1 where delivery_line_id=(select id from erp.laundry_delivery_lines where delivery_id=%s) and rate_status='UNKNOWN'",sent['delivery_id'])
    bd(cur,'SET_CHARGE_PRICE',dict(charge_line_id=unknown,rate_per_pcs='1000.00',reason='vendor price arrived'))
    sell(cur,fx,product,2,16)
    posted=one(cur,"select count(*) from erp.sales_items i join erp.sales_headers h on h.id=i.sale_id where i.product_id=%s and h.status='POSTED'",product)
    return verdict(dict(pending_refused=pending['ok'],refuse_refused=refuse['ok'],nothing_posted=posted_none==0,
        allowed_but_close_blocked=blocked==['BD_LAUNDRY_COMPONENT_PRICE_UNKNOWN'],known_then_sold=posted==2),blocked=blocked,refusals=[pending,refuse])

# ---------------------------------------------------------------- ALL-W05 physical: laundry away at cutover (import)
W05_KEYS=('WIP','OPENING_EQUITY','AP_VENDOR','OTHER_EXPENSE','ACCRUED_MANUFACTURING','FG_INVENTORY')


def w05_rows(today,claims=((None,'MISSING','1'),),payable=None,stage='LAUNDRY',uninvoiced=()):
    """The auditor's ALL-W05 fixture (r9): laundry {C} held 10 PCS of PO {C}; 2 came back before cutover (not opening WIP); the
    8 still away are the BB opening WIP at stage LAUNDRY held by laundry {C} (40.00, 5.00 a piece); the documented claims
    on them are dated before cutover (number, type, qty). `payable` adds the vendor's opening payable (original, settled)."""
    rows=bbp.production_rows(stage=stage)
    before=str(today-timedelta(days=12))
    for i,(number,kind,qty) in enumerate(claims):
        rows.setdefault('OPENING_LAUNDRY_CLAIM',[]).append(dict(claim_number=number or '{C}-KL%d'%(i+1),source_key='WIP',vendor_code='{C}',
            claim_type=kind,qty=qty,claim_date=before,dispatch_number='KRM-LAMA-7',notes='dikirim 10, kembali 2 sebelum cutover'))
    if payable:
        doc=bbp.document('VENDOR_PAYABLE','vendor_code','INV-LAMA-{C}',*payable);doc.pop('_days');doc['document_date']=str(today-timedelta(days=40))
        rows['OPENING_BALANCE_ITEM'].append(doc)
        rows['OPENING_CONTROL'].append(dict(control_key='VENDOR_PAYABLE',balance_type='VENDOR_PAYABLE',amount=doc['amount']))
    if uninvoiced:rows['OPENING_LAUNDRY_UNINVOICED']=list(uninvoiced)
    return rows


def amount_keys(value,path=''):
    """Every key naming an amount in a JSON value (a production reader's view must carry none)."""
    if isinstance(value,dict):return [p for k,v in value.items() for p in ([path+'.'+k] if 'amount' in k else [])+amount_keys(v,path+'.'+k)]
    if isinstance(value,list):return [p for i,v in enumerate(value) for p in amount_keys(v,'%s[%d]'%(path,i))]
    return []


def claim_of(cur,fx,index=0):
    return bbp.source_of(cur,fx)['bd']['claims'][index]


def claim_op(cur,fx,operation,claim=None,**kw):
    if claim is not None:kw.update(claim_id=claim['claim_id'],expected_version=claim['row_version'])
    return bbp.wip_op(cur,fx,operation,**kw)


def w05_custody_claim(cur,today):
    """ALL-W05 (r9): only the 8 pieces still away are imported; the documented claim holds 1 of them apart (residual custody 7,
    claim 1); import posts no laundry, payment or claim journal (the WIP 40.00 against opening equity only); completing 8 is
    refused (a claimed piece is not ready goods); the PO cannot finish while the claim is open; the 7 come back and are
    completed at 5.00 a piece (the WIP status still lists the row as active: a claim holds 1); the claim is written off (no journal: no vendor charge or expense without a priced source);
    the PO then finishes and the baseline residual close expenses the lost piece's 5.00 once (WIP 0)."""
    rows=w05_rows(today)
    if not bd_installed(cur):return no_route(cur,lambda:bbp.production_post(cur,today,rows))
    b0=bcp.ledger(cur,W05_KEYS);j0=one(cur,'select count(*) from erp.journal_entries')
    fx=bbp.production_post(cur,today,rows)
    imported=bcp.delta(b0,bcp.ledger(cur,W05_KEYS))
    # Journals the import wrote: none of a laundry claim, accrual, settlement or vendor invoice.
    claim_journals=one(cur,"""select count(*) from (select source_type from erp.journal_entries order by created_at desc,id limit %s) j
        where j.source_type in('BD_OPENING_LAUNDRY_CLAIM','LAUNDRY_CLAIM_SETTLEMENT','BD_OPENING_LAUNDRY_ACCRUAL','VENDOR_INVOICE')""",
        one(cur,'select count(*) from erp.journal_entries')-j0)
    s=bbp.source_of(cur,fx);claim=s['bd']['claims'][0]
    listed=[c for c in api.read(cur,fx['batch'])['batch']['laundry_claims'] if c['claim_id']==claim['claim_id']]
    over=bcp.denied(cur,lambda:bbp.complete(cur,fx,today,8),'tidak melebihi sisa WIP')
    bbp.complete(cur,fx,today,7)
    after=bbp.source_of(cur,fx)
    active=lambda:[x['opening_item_id'] for x in one(cur,"select erp.get_wip_control_v1('ACTIVE',null,'PATTERN',%s)",fx['code'])['opening_rows']]
    active_while_claimed=active()==[s['opening_item_id']]
    finish_open=bcp.denied(cur,lambda:internal(cur,'finish_production_order',fx['po']),'WIP/BS saldo awal yang belum selesai')
    b1=bcp.ledger(cur,W05_KEYS)
    claim_op(cur,fx,'RESOLVE_CLAIM',claim_of(cur,fx),resolution='WRITTEN_OFF',date=str(today))
    written=bcp.delta(b1,bcp.ledger(cur,W05_KEYS))
    resolved=claim_of(cur,fx)
    inactive_after=active()==[]
    b2=bcp.ledger(cur,W05_KEYS)
    internal(cur,'finish_production_order',fx['po'])
    closed=bcp.delta(b2,bcp.ledger(cur,W05_KEYS))
    return verdict(dict(import_wip_only=imported.get('WIP')==D('40.00') and set(imported)<={'WIP','OPENING_EQUITY'} and claim_journals==0,
        separate_states=(s['qty_pcs'],s['remaining_qty_pcs'],s['bd']['held_qty_pcs'],claim['state'],claim['qty_claimed'])==(8,7,1,'OPEN',1),
        provenance=bool(listed) and listed[0]['dispatch_number']=='KRM-LAMA-7' and listed[0]['origin']=='IMPORT',
        claimed_not_goods=over['ok'],completed_seven=after['remaining_qty_pcs']==0 and after['completed_qty_pcs']==7,
        wip_status_active_while_claimed=active_while_claimed and inactive_after,
        finish_waits_for_claim=finish_open['ok'],write_off_no_journal=written=={},
        resolved=(resolved['state'],resolved['lost'])==('WRITTEN_OFF',1),
        lost_value_once=closed=={'WIP':D('-5.00'),'OTHER_EXPENSE':D('5.00')}),
        imported={k:str(v) for k,v in imported.items()},closed={k:str(v) for k,v in closed.items()},source=s,refusals=[over,finish_open])


def w05_claim_continuations(cur,today):
    """ALL-W05 continuations on the canonical path (WIP_OUTPUT: same locks and remaining check as a completion). 2 PCS of 8
    claimed MISSING at cutover; 1 comes back (RECOVER_CLAIM, remaining 7). A claim after cutover (OPEN_CLAIM) takes only unheld
    pieces (8 refused while 7 are left), a claim number is used once, an imported claim is not cancelled (it is recovered) and
    a claim opened after cutover is cancelled; it held its piece until the day it was cancelled, so completing 7 dated the day
    before is refused (BA A3 dated remaining). The 7 are completed, so the recovery can no longer be reversed; recovering more
    than the claim still holds is refused. A SETTLED compensation above the vendor's payable (50.00) is refused; 3.00 posts
    once AP_VENDOR 3.00 / OTHER_EXPENSE -3.00, a second resolution is refused, and reversing it reverses its journal. The claim
    part that production readers get (the opening WIP row and the WIP status page) carries quantities and states only: no
    amount, also after a SETTLED compensation (the compensation stays on the owner/admin import workspace)."""
    rows=w05_rows(today,claims=((None,'MISSING','2'),),payable=('50.00','0.00'))
    if not bd_installed(cur):return no_route(cur,lambda:bbp.production_post(cur,today,rows))
    fx=bbp.production_post(cur,today,rows)
    claim_op(cur,fx,'RECOVER_CLAIM',claim_of(cur,fx),qty_pcs='1',date=str(today))
    recovered=bbp.source_of(cur,fx)
    number=claim_of(cur,fx)['claim_number']
    too_many=refused(cur,lambda:claim_op(cur,fx,'OPEN_CLAIM',claim_number=fx['code']+'-K9',claim_type='STUCK',qty_pcs='8',date=str(today)),
                     'BD_W05_CLAIM_EXCEEDS_REMAINING')
    duplicate=refused(cur,lambda:claim_op(cur,fx,'OPEN_CLAIM',claim_number=number,claim_type='STUCK',qty_pcs='1',date=str(today)),'BD_W05_DUPLICATE_CLAIM')
    claim_op(cur,fx,'OPEN_CLAIM',claim_number=fx['code']+'-K9',claim_type='STUCK',qty_pcs='1',date=str(today))
    opened=bbp.source_of(cur,fx)
    later=[c for c in opened['bd']['claims'] if c['origin']=='CONTINUATION'][0]
    imported_cancel=refused(cur,lambda:claim_op(cur,fx,'CANCEL_CLAIM',claim_of(cur,fx)),'BD_W05_IMPORTED_CLAIM')
    claim_op(cur,fx,'CANCEL_CLAIM',later)
    cancelled=bbp.source_of(cur,fx)
    dated=refused(cur,lambda:bbp.complete(cur,fx,today,7),'BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING')
    bbp.complete(cur,fx,bcp.REAL_TODAY,7)
    c=[x for x in bbp.source_of(cur,fx)['bd']['claims'] if x['origin']=='IMPORT'][0]
    event=[e for e in c['events'] if e['kind']=='RECOVER'][0]['event_id']
    in_use=refused(cur,lambda:claim_op(cur,fx,'REVERSE_CLAIM_EVENT',c,event_id=event),'BD_W05_RECOVERED_IN_USE')
    over_recover=refused(cur,lambda:claim_op(cur,fx,'RECOVER_CLAIM',c,qty_pcs='2',date=str(today)),'BD_W05_RECOVER_EXCEEDS_CLAIM')
    above=refused(cur,lambda:claim_op(cur,fx,'RESOLVE_CLAIM',c,resolution='SETTLED',compensation_amount='60.00',date=str(today)),
                  'BD_W05_COMPENSATION_EXCEEDS_PAYABLE')
    b0=bcp.ledger(cur,W05_KEYS)
    claim_op(cur,fx,'RESOLVE_CLAIM',c,resolution='SETTLED',compensation_amount='3.00',date=str(today))
    settled=bcp.delta(b0,bcp.ledger(cur,W05_KEYS))
    status_rows=one(cur,"select erp.get_wip_control_v1('ALL',null,'PATTERN',%s)",fx['code'])['opening_rows']
    production_part=bbp.source_of(cur,fx)['bd']
    leaked=amount_keys(production_part)+amount_keys([x.get('bd') for x in status_rows])
    compensation_listed=[x.get('compensation_amount') for x in api.read(cur,fx['batch'])['batch']['laundry_claims'] if x['origin']=='IMPORT']
    c=claim_of(cur,fx) if claim_of(cur,fx)['origin']=='IMPORT' else claim_of(cur,fx,1)
    twice=refused(cur,lambda:claim_op(cur,fx,'RESOLVE_CLAIM',c,resolution='WRITTEN_OFF',date=str(today)),'BD_W05_CLAIM_RESOLVED')
    resolve_event=[e for e in c['events'] if e['kind']=='RESOLVE' and not e['reversed']][0]['event_id']
    claim_op(cur,fx,'REVERSE_CLAIM_EVENT',c,event_id=resolve_event)
    back=bcp.ledger(cur,W05_KEYS)
    return verdict(dict(recovered_to_wip=(recovered['remaining_qty_pcs'],recovered['bd']['held_qty_pcs'])==(7,1),
        later_claim_unheld_only=too_many['ok'],number_once=duplicate['ok'],later_claim_holds=opened['remaining_qty_pcs']==6,
        imported_not_cancelled=imported_cancel['ok'],later_cancelled=cancelled['remaining_qty_pcs']==7,held_until_cancelled=dated['ok'],
        recovery_in_use=in_use['ok'],
        recover_capacity=over_recover['ok'],compensation_capped=above['ok'],
        compensation_once=settled=={'AP_VENDOR':D('3.00'),'OTHER_EXPENSE':D('-3.00')},resolved_once=twice['ok'],inverse=back==b0,
        production_reads_without_amounts=leaked==[] and bool(status_rows) and all(x.get('bd') is not None for x in status_rows),
        compensation_on_import_workspace=[str(v) for v in compensation_listed]==['3.00']),
        settled={k:str(v) for k,v in settled.items()},leaked=leaked,compensation_listed=[str(v) for v in compensation_listed],refusals=[too_many,duplicate,imported_cancel,dated,in_use,over_recover,above,twice])


def w05_import_refusals(cur,today):
    """ALL-W05 import refusals (r9 negatives): claims above the pieces away (9 of 8), a claim of another vendor, a claim dated
    after cutover (a later claim is a continuation), a claim on a row that is not WIP at a laundry, a claim number used twice;
    an uninvoiced receipt imported twice (same document and category), a zero estimate (unknown stays empty, never a zero
    journal), and a receipt dated after cutover."""
    before=str(today-timedelta(days=12))
    claim=lambda number,qty,**kw:dict(dict(claim_number='{C}-'+number,source_key='WIP',vendor_code='{C}',claim_type='MISSING',qty=qty,claim_date=before),**kw)
    rows=w05_rows(today,claims=())
    rows['OPENING_LAUNDRY_CLAIM']=[claim('A','5'),claim('B','4'),claim('V','1',vendor_code='ZZ'+uuid.uuid4().hex[:6]),
        claim('L','1',claim_date=str(today)),claim('S','1',source_key='TIDAK-ADA'),claim('D','1'),claim('D','1')]
    rec=lambda doc,**kw:dict(dict(document_number=doc,vendor_code='{C}',receipt_date=before,category='GOOD',qty='3'),**kw)
    rows['OPENING_LAUNDRY_UNINVOICED']=[rec('R1'),rec('R1'),rec('R2',estimated_amount='0.00'),rec('R3',receipt_date=str(today))]
    if not bd_installed(cur):return no_route(cur,lambda:bbp.production_post(cur,today,rows,expect=True))
    errs=bbp.production_post(cur,today,rows,expect=True)['errors']
    sewing=w05_rows(today,stage='SEWING')
    errs2=bbp.production_post(cur,today,sewing,expect=True)['errors']
    text=lambda es,entity:' | '.join(e for k,e in es if k==entity)
    c,u,c2=text(errs,'OPENING_LAUNDRY_CLAIM'),text(errs,'OPENING_LAUNDRY_UNINVOICED'),text(errs2,'OPENING_LAUNDRY_CLAIM')
    return verdict(dict(exceeds_source=c.count('BD_W05_CLAIM_EXCEEDS_SOURCE')>=2,vendor=('BD_W05_VENDOR_MISMATCH' in c),
        after_cutover='BD_W05_CLAIM_AFTER_CUTOVER' in c,no_source='BD_W05_SOURCE_REQUIRED' in c,duplicate=c.count('BD_W05_DUPLICATE_CLAIM')==2,
        not_laundry='BD_W05_SOURCE_REQUIRED' in c2,receipt_twice=u.count('BD_W05_DUPLICATE_RECEIPT')==2,zero_estimate='BB_AMOUNT_INVALID' in u,
        receipt_after_cutover='receipt_date:' in u),claims=c,uninvoiced=u,sewing=c2)


def opening_invoice(cur,vendor,day,lines,header,post=True):
    payload=dict(vendor_id=vendor,invoice_number='INV-'+uuid.uuid4().hex[:10],invoice_date=str(day),header_total=header,
                 lines=[dict(line_kind=l.get('kind','BILL'),opening_uninvoiced_id=l['source'],category=l.get('category','GOOD'),qty=l.get('qty',0),
                             amount=l['amount']) for l in lines])
    draft=bd(cur,'SAVE_INVOICE_DRAFT',payload)
    return post_draft(cur,draft) if post else draft


def w05_uninvoiced(cur,today):
    """ALL-W05 old receipt/invoice (r9: no second bill, no vendor charge without an accepted priced source, unknown value stays
    pending and blocks financial finalization, no zero journal). Imported: A = 10 GOOD returned before cutover with an
    evidenced estimate 70,000 (opening accrual ACCRUED_MANUFACTURING -70,000 / OPENING_EQUITY +70,000, as the supplier GRNI
    opening); B = 2 FAILED_ATTEMPT with no estimate (nothing journaled; close blocked BD_OPENING_LAUNDRY_PRICE_UNKNOWN).
    The vendor bills A 6 for 42,000 (releases 42,000), then 5 more is over capacity; 4 for 30,000 leaves a 2,000 difference
    that is no PO's product cost, refused under PRODUCT_COST (BD_OPENING_VARIANCE_NEEDS_ACCOUNT) and posted to the owner's
    variance account under VARIANCE_ACCOUNT (A's accrual back to 0). B cannot be billed as GOOD; GUDANG cannot set its
    estimate; the owner sets 8,000 (accrual, blocker gone); its invoice of 8,000 releases it; reversing that invoice
    restores the accrual and the payable."""
    rows=bbp.masters()
    before=str(today-timedelta(days=12))
    rows['OPENING_LAUNDRY_UNINVOICED']=[dict(document_number='{C}-TRM-1',vendor_code='{C}',receipt_date=before,category='GOOD',qty='10',
                                             estimated_amount='70000.00',dispatch_number='KRM-LAMA-3'),
                                        dict(document_number='{C}-TRM-2',vendor_code='{C}',receipt_date=before,category='FAILED_ATTEMPT',qty='2')]
    if not bd_installed(cur):return no_route(cur,lambda:bbp.post_batch(cur,today,rows))
    b0=bcp.ledger(cur,W05_KEYS)
    batch,code,cutover=bbp.post_batch(cur,today,rows)
    imported=bcp.delta(b0,bcp.ledger(cur,W05_KEYS))
    vendor=one(cur,'select id::text from erp.laundry_vendors where vendor_code=%s',code)
    src={u['category']:u for u in bd_ws(cur,dict(vendor_id=vendor))['opening_uninvoiced']}
    a,b=src['GOOD']['id'],src['FAILED_ATTEMPT']['id']
    blocked=lambda s:sorted(r[0] for r in q(cur,"select code from erp.period_blockers_v1(%s,null) where reference->>'opening_uninvoiced_id'=%s",today,s))
    before_blockers=(blocked(a),blocked(b))
    invoice_policies(cur)
    first=opening_invoice(cur,vendor,today,[dict(source=a,qty=6,amount='42000.00')],'42000.00')
    over=refused(cur,lambda:opening_invoice(cur,vendor,today,[dict(source=a,qty=5,amount='35000.00')],'35000.00'),'BD_INVOICE_CAPACITY')
    no_account=refused(cur,lambda:opening_invoice(cur,vendor,today,[dict(source=a,qty=4,amount='30000.00')],'30000.00'),'BD_OPENING_VARIANCE_NEEDS_ACCOUNT')
    expense=one(cur,"select id::text from erp.chart_accounts where account_type='EXPENSE' and is_postable and is_active and account_code='5100'")
    invoice_policies(cur,mode='VARIANCE_ACCOUNT',account=expense)
    v0=bcp.gl_account(cur,expense)
    second=opening_invoice(cur,vendor,today,[dict(source=a,qty=4,amount='30000.00')],'30000.00')
    variance=bcp.gl_account(cur,expense)-v0
    wrong=refused(cur,lambda:opening_invoice(cur,vendor,today,[dict(source=b,qty=2,amount='8000.00')],'8000.00',post=False),'BD_INVOICE_CATEGORY')
    version=lambda s:[u for u in bd_ws(cur,dict(vendor_id=vendor))['opening_uninvoiced'] if u['id']==s][0]['row_version']
    gudang=user(cur,'GUDANG')
    denied=bcp.denied(cur,lambda:bd(cur,'SET_OPENING_ESTIMATE',dict(opening_uninvoiced_id=b,expected_version=version(b),estimated_amount='8000.00',
        reason='x'),auth=gudang),'')
    b1=bcp.ledger(cur,W05_KEYS)
    bd(cur,'SET_OPENING_ESTIMATE',dict(opening_uninvoiced_id=b,expected_version=version(b),estimated_amount='8000.00',reason='nota vendor lisan'))
    estimated=bcp.delta(b1,bcp.ledger(cur,W05_KEYS))
    after_estimate=blocked(b)
    b2=bcp.ledger(cur,W05_KEYS)
    third=opening_invoice(cur,vendor,today,[dict(source=b,category='FAILED_ATTEMPT',qty=2,amount='8000.00')],'8000.00')
    billed=bcp.delta(b2,bcp.ledger(cur,W05_KEYS))
    bd(cur,'REVERSE_INVOICE',dict(invoice_id=third['invoice_id'],expected_version=third['row_version'],reason='salah vendor'))
    reversed_=bcp.ledger(cur,W05_KEYS)==b2
    end={u['category']:u for u in bd_ws(cur,dict(vendor_id=vendor))['opening_uninvoiced']}
    l1,l2=first['lines'][0],second['lines'][0]
    return verdict(dict(import_accrual_only=imported=={'ACCRUED_MANUFACTURING':D('-70000.00'),'OPENING_EQUITY':D('70000.00')},
        states=(src['GOOD']['estimate_status'],src['FAILED_ATTEMPT']['estimate_status'])==('KNOWN','UNKNOWN'),
        unknown_blocks_close=before_blockers==([],['BD_OPENING_LAUNDRY_PRICE_UNKNOWN']),
        partial_release=(l1['released_estimate'],l1['variance'],l1['completes_source'])==('42000.00','0.00',False),capacity=over['ok'],
        variance_needs_account=no_account['ok'],
        residual_release=(l2['released_estimate'],l2['variance'],l2['product_variance'],l2['completes_source'])==('28000.00','2000.00','0.00',True)
          and variance==2000,
        category=wrong['ok'],estimate_owner_only=denied['ok'],
        estimate_accrual=estimated=={'ACCRUED_MANUFACTURING':D('-8000.00'),'OPENING_EQUITY':D('8000.00')} and after_estimate==[],
        billed_releases=billed=={'ACCRUED_MANUFACTURING':D('8000.00'),'AP_VENDOR':D('-8000.00')},inverse=reversed_,
        end=(end['GOOD']['billed'],end['GOOD']['invoiced'],end['FAILED_ATTEMPT']['billed'],end['FAILED_ATTEMPT']['invoiced'])==(10,True,0,False)),
        lines=[l1,l2],imported={k:str(v) for k,v in imported.items()},billed={k:str(v) for k,v in billed.items()},
        refusals=[over,no_account,wrong,denied])


# ---------------------------------------------------------------- D07: the v2.5.5 recost alarm at document level
D07_ALARM='MATERIAL_RECOST_GL_STATE_DRIFT'


def d07_alarm(cur):
    api.admin(cur)
    return int(one(cur,"select issue_count from erp.run_v255_material_cost_integrity_checks() where check_name=%s",D07_ALARM) or 0)


def d07_books(cur):
    """Material GL, qty x moving average (rounded), WIP GL and the supplier obligation (AP + GRNI)."""
    api.admin(cur)
    gl=lambda key:D(str(one(cur,'select coalesce(sum(debit-credit),0) from erp.journal_lines where account_id=erp.account_id(%s)',key)))
    return dict(material=gl('MATERIAL_INVENTORY'),sub=D(str(one(cur,'select round(coalesce(sum(cached_stock_qty*moving_average_cost),0),2) from erp.materials'))),
                wip=gl('WIP'),obligation=gl('AP_SUPPLIER')+gl('GRNI_MATERIAL'))


def d07_receipt(cur,day,price,qty,first=None):
    """An ordinary estimated purchase receipt (the purchase RPCs) of `qty` units at `price`; `first` reuses its material and
    location (stacked documents of one material)."""
    prod=chain.production;api.admin(cur);prod.zone(cur,'Asia/Jakarta')
    if first:material,location=first['material'],first['location']
    else:
        material=prod.prior.clone_material(cur,'bd-d07');location=uuid.uuid4()
        cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,'BD D07 raw warehouse','RAW_MATERIAL_WAREHOUSE',true)",
                    (location,'BD-D07-'+location.hex[:20]))
    draft=prod.rpc(cur,'erp.save_material_purchase_draft_v2',dict(purchase_number='BD-D07-'+uuid.uuid4().hex,supplier_id=prod.prior.BASE_SUPPLIER,
        location_id=location,physical_at=prod.at(day,10),change_reason='BD D07 estimated receipt',
        lines=[dict(material_id=material,qty=qty,unit_price=price,price_state='ESTIMATED',price_source='MANUAL_ESTIMATE',
                    rolls=[dict(roll_number='BD-D07-'+uuid.uuid4().hex,qty=qty)])]))
    purchase=uuid.UUID(draft['purchase_id'])
    cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',(purchase,uuid.uuid4(),int(draft['row_version']),'BD D07 receipt'));api.admin(cur)
    item,roll=cur.execute('select i.id,r.id from erp.material_purchase_items i join erp.material_rolls r on r.purchase_item_id=i.id where i.purchase_id=%s',(purchase,)).fetchone()
    return dict(material=material,purchase=purchase,item=item,location=location,roll=roll,qty=qty)


def d07_invoice(cur,fx,day,price):
    """The supplier's late invoice for the whole receipt at `price`, then the cost queue."""
    prod=chain.production;api.admin(cur)
    version=int(one(cur,'select row_version from erp.material_purchase_headers where id=%s',fx['purchase']))
    prod.zone(cur,'Asia/Jakarta')
    prod.rpc(cur,'erp.finalize_material_purchase_invoice_v2',dict(purchase_id=fx['purchase'],supplier_invoice_number='BD-D07-INV-'+uuid.uuid4().hex[:10],
        invoice_date=str(day),received_at=prod.at(day,15),reason='BD D07 late invoice at '+price,
        lines=[dict(purchase_item_id=fx['item'],qty_invoiced=fx['qty'],final_unit_price=price)]),uuid.uuid4(),version)
    api.admin(cur);prod.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)


def d07_path(cur,today,kind,n=1,qty=10,adj=3,p0='10.00',p1='10.005'):
    """One native path; returns the alarm delta and the books oracle (exact books: obligation = the documents rounded per
    document, M:835; material GL = qty x average within a cent, M:485; stacked: WIP = the documents' cents, material 0, T3 A)."""
    azp=bbp.azp
    d=today-timedelta(days=5);boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    alarm0=d07_alarm(cur);b0=d07_books(cur)
    if kind=='STACKED':
        fxs=[]
        for _ in range(n):fxs.append(d07_receipt(cur,d,p0,1,fxs[0] if fxs else None))
        for i,fx in enumerate(fxs):azp.cut(cur,fx,d+timedelta(days=1),1,8+i)
        for fx in fxs:d07_invoice(cur,fx,d+timedelta(days=2),p1)
    else:
        fx=d07_receipt(cur,d,p0,qty)
        if kind=='ADJUST':azp.adjust(cur,fx,d+timedelta(days=1),adj)
        d07_invoice(cur,fx,d+timedelta(days=2),p1)
    b1=d07_books(cur)
    cent=lambda v:D(str(v)).quantize(D('0.01'),rounding='ROUND_HALF_UP')
    docs=n if kind=='STACKED' else 1;units=1 if kind=='STACKED' else qty
    books=dict(obligation=b1['obligation']-b0['obligation']==-cent(D(p1)*units)*docs,
               material_within_a_cent=abs((b1['material']-b0['material'])-(b1['sub']-b0['sub']))<=D('0.01'))
    if kind=='STACKED':books.update(wip=b1['wip']-b0['wip']==cent(D(p1))*n,material_used_up=b1['material']-b0['material']==0)
    return dict(alarm=d07_alarm(cur)-alarm0,books=books,books_exact=all(books.values()))


def d07_recost_alarm(cur,today):
    """D07 (R12 handoff task 1; the auditors' technical proposal, the owner's direction recorded open in OWNER_DECISIONS_CP6_DRAFT.md
    §D07): MATERIAL_RECOST_GL_STATE_DRIFT (v2.5.5, ERROR) at document level. Five native paths whose books are exact: a late
    invoice only; a count correction of -3 of 10 then a late invoice at 10.005 and at 2.10 (the adjustment's recost is in the
    v2.6.20t facts, not in the per-movement state); 3 and 10 stacked one-unit receipts cut one by one, then invoiced at 10.005
    (the documents' cents go with one cut, owner T3 option A). With D07 the alarm stays silent on all five; before D07 it rings
    on three with exact books (COUNTEREXAMPLE). Negative controls, each in a savepoint rolled back: a consumption state off by
    1.00, a consumption state removed (target 2.00: a corrected movement with no recost at all), an adjustment fact off by 1.00,
    the adjustment's facts removed (the facts are append-only, so the change is made with session_replication_role=replica
    inside the savepoint): the alarm rings on each."""
    installed='D07' in (one(cur,"select prosrc from pg_proc where oid='erp.run_v255_material_cost_integrity_checks()'::regprocedure") or '')
    paths={}
    for key,kw in (('CONTROL',dict(kind='CONTROL')),('ADJUST_10.005',dict(kind='ADJUST')),('ADJUST_2.10',dict(kind='ADJUST',p1='2.10')),
                   ('STACKED_3',dict(kind='STACKED',n=3)),('STACKED_10',dict(kind='STACKED',n=10))):
        cur.execute('savepoint d07_path')
        try:paths[key]=d07_path(cur,today,**kw)
        finally:cur.execute('rollback to savepoint d07_path');api.admin(cur)
    books_exact=all(p['books_exact'] for p in paths.values())
    rings=sorted(k for k,p in paths.items() if p['alarm'])
    if not installed:
        return dict(status='COUNTEREXAMPLE' if books_exact and rings else 'INCOMPLETE',paths=paths,rings_on_exact_books=rings)
    controls={}
    cur.execute('savepoint d07_neg')
    try:
        d07_path(cur,today,'STACKED',n=3,p1='12.00')
        mat=one(cur,"select m.material_id from erp.material_stock_movements m join erp.material_cost_revaluation_state s on s.movement_id=m.id where m.source_type='CUTTING_GROUP' order by s.updated_at desc limit 1")
        sid=one(cur,"select s.movement_id from erp.material_cost_revaluation_state s join erp.material_stock_movements m on m.id=s.movement_id where m.material_id=%s and m.source_type='CUTTING_GROUP' and abs(s.applied_inventory_delta)>0.01 limit 1",mat)
        base=d07_alarm(cur)
        for name,sql in (('state_off_by_1.00','update erp.material_cost_revaluation_state set applied_inventory_delta=applied_inventory_delta+1 where movement_id=%s'),
                         ('state_removed','delete from erp.material_cost_revaluation_state where movement_id=%s')):
            cur.execute('savepoint d07_c');cur.execute(sql,(sid,));controls[name]=d07_alarm(cur)-base;cur.execute('rollback to savepoint d07_c');api.admin(cur)
        cur.execute('rollback to savepoint d07_neg');cur.execute('savepoint d07_neg')
        d07_path(cur,today,'ADJUST',p1='2.10')
        adj=one(cur,'select adjustment_id from erp.material_adjustment_revaluation_facts order by created_at desc limit 1')
        inv=str(one(cur,"select erp.account_id('MATERIAL_INVENTORY')"))
        base=d07_alarm(cur)
        for name,sql,args in (('fact_off_by_1.00',"update erp.material_adjustment_revaluation_facts set ledger_delta=jsonb_set(ledger_delta,array[%s],to_jsonb((ledger_delta->>%s)::numeric+1)) where adjustment_id=%s",(inv,inv,adj)),
                              ('facts_removed','delete from erp.material_adjustment_revaluation_facts where adjustment_id=%s',(adj,))):
            cur.execute('savepoint d07_c');cur.execute('set local session_replication_role=replica');cur.execute(sql,args)
            controls[name]=d07_alarm(cur)-base;cur.execute('rollback to savepoint d07_c');api.admin(cur)
    finally:cur.execute('rollback to savepoint d07_neg');api.admin(cur)
    return verdict(dict(books_exact_on_all_paths=books_exact,silent_on_exact_books=rings==[],
        negative_controls_ring=len(controls)==4 and all(v>0 for v in controls.values())),paths=paths,controls=controls)


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
      ('T24:MULTI_SIZE_LOT_HPP','NO_ROUTE',t24_multi_size_lot_hpp),
      ('T32:REPLAY_ACCESS_GRANTS','NO_ROUTE',replay_and_access),
      ('T16:INVOICE_ABOVE_ESTIMATE_PRODUCT_COST','NO_ROUTE',t16_invoice_above_estimate),
      ('T17:PARTIAL_NM_CAPACITY','NO_ROUTE',t17_partial_nm_capacity),
      ('T21:DISCOUNT_TAX_ROUNDING','NO_ROUTE',t21_discount_tax_rounding),
      ('DEC06:VARIANCE_ACCOUNT','NO_ROUTE',dec06_variance_account),
      ('T23:REVERSE_PAY_CORRECT','NO_ROUTE',t23_reverse_pay_correct),
      ('DEC02:BILLABLE_CATEGORIES_ACCESS','NO_ROUTE',dec02_categories),
      ('T22:VARIANCE_TO_FG_AND_COGS','NO_ROUTE',t22_variance_to_fg_and_cogs),
      ('DEC04:SALE_UNKNOWN_LAUNDRY_PRICE','NO_ROUTE',dec04_sale_unknown_laundry),
      ('W05:OPENING_CUSTODY_CLAIM_SEPARATE','NO_ROUTE',w05_custody_claim),
      ('W05:CLAIM_CONTINUATIONS','NO_ROUTE',w05_claim_continuations),
      ('W05:IMPORT_REFUSALS','NO_ROUTE',w05_import_refusals),
      ('W05:UNINVOICED_ACCRUAL_INVOICE','NO_ROUTE',w05_uninvoiced),
      ('D07:RECOST_ALARM_DOCUMENT_LEVEL','COUNTEREXAMPLE',d07_recost_alarm)]
assert len({k for k,_,_ in PLAN})==len(PLAN),'BD_DUPLICATE_CASE_ID'


# Every BD workspace and import batch workspace a case reads, and the owner's Laundry/QC workspace read next to each owner BD
# read, is saved and run through the pages' own parsers after the group (scripts/cp6_bd_workspace_parse.mjs): a page hides
# what it cannot parse, so a refusal there is a probe failure. Missing until auditor scenario run 36206435863 found the
# owner's BD workspace refused by its page (released "0" for an unreleased opening record).
WS=dict(dir=None,case=None,n=0)
_READ,_BD_WS=api.read,bd_ws


def _save(kind,result):
    if WS['dir'] is not None and isinstance(result,dict):
        WS['n']+=1
        name='%s_%s_%03d.json'%(kind,re.sub(r'[^A-Za-z0-9]+','_',WS['case'] or 'SETUP'),WS['n'])
        (WS['dir']/name).write_text(json.dumps(result,default=str))
    return result


def recording_read(cur,batch=None):
    result=_READ(cur,batch)
    return _save('import',result) if batch is not None and isinstance(result,dict) and result.get('batch') else result


def recording_bd_ws(cur,filters=None,auth=None):
    result=_save('bd',_BD_WS(cur,filters,auth))
    if auth is None:
        # The Laundry page itself, as the same owner, at the same point of the case (read only, in its own savepoint).
        cur.execute('savepoint bd_ws_laundry')
        try:
            chain.production.owner(cur)
            laundry=cur.execute("select public.erp_get_laundry_qc_workspace_v1('LAUNDRY',null)").fetchone()[0]
            chain.actors.admin(cur);cur.execute('release savepoint bd_ws_laundry');_save('laundry',laundry)
        except psycopg.Error as exc:
            cur.execute('rollback to savepoint bd_ws_laundry');chain.actors.admin(cur);_save('laundryerror',dict(error=str(exc)[:500]))
    return result


def cases(cur,today):
    day=case_day(today)
    def run_one(key,fn):
        WS.update(case=key,n=0);return fn(cur,day)
    return [(key,lambda k=key,f=fn:run_one(k,f)) for key,_,fn in PLAN]


def workspace_parse(phase):
    run=subprocess.run(['node',str(AUDITOR/'scripts/cp6_bd_workspace_parse.mjs'),str(WS['dir']),phase],capture_output=True,text=True,cwd=AUDITOR)
    lines=run.stdout.strip().splitlines()
    try:parsed=json.loads(lines[-1])
    except (IndexError,ValueError):parsed=dict(files=None,refused=None,error=(run.stderr or run.stdout)[-1500:])
    kept=OUT/('WORKSPACE_REFUSED_'+phase.upper());kept.mkdir(parents=True,exist_ok=True)
    for item in parsed.get('refused') or []:(kept/item['file']).write_text((WS['dir']/item['file']).read_text())
    ok=run.returncode==0 and parsed.get('refused')==[] and (phase=='before' or (parsed.get('files') or 0)>0)
    return dict(status='PASS' if ok else 'FAIL',files=parsed.get('files'),kinds=parsed.get('kinds'),f3_seed_ids=parsed.get('f3_seed_ids'),
                refused=parsed.get('refused'),error=parsed.get('error'),exit=run.returncode)


def run(phase):
    global bd_ws
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
        WS['dir']=Path(tempfile.mkdtemp(prefix='cp6-bd-ws-'));api.read=recording_read;bd_ws=recording_bd_ws
        try:group=r1.group('BD_CASES_'+phase.upper(),cases,verify)
        finally:api.read=_READ;bd_ws=_BD_WS
        report['bd_cases']={k:group[k] for k in ('status','counts')}
        report['workspace_parse']=workspace_parse(phase)
        print(json.dumps(dict(bd_workspace_parse=report['workspace_parse']),default=str),flush=True)
        final={k:v['status'] for k,v in group['cases'].items()}
        report['final']=final
        report['expectation_mismatch']={k:dict(planned=list(e),final=final.get(k)) for k,e in planned.items() if final.get(k) not in e}
        report['status']=('REVIEW_COMPLETE' if group['status']!='INCOMPLETE' and not report['expectation_mismatch']
                          and report['workspace_parse']['status']=='PASS' else 'INCOMPLETE')
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
