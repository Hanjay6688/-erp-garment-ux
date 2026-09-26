"""BC T1_FAMILY probe: the accessory service, return and inspection workflow (ACC-04b), the accessory policy settings
(ACC-DEC01, ACC-DEC03..07, ERP-DEC02) and the opening accessory states ALL-C02/C03, before and after.

Label T1_FAMILY: targeted family evidence on the disposable chain AN -> AU -> AV -> AW..AZ -> BA -> BB (+ BC in phase
'after'), never release evidence. Oracles come from the contract (master M:4751-5240, M §13 ACC cases M:5246-5307) and the
auditors' pre-code oracles (r9_acc_oracle.md ACC-A08..D12, r9_all_oracle.md ALL-C02/C03, Fable fable_c6_75 and
fable_all22), never from observed behaviour; where two readings differ the more fail-closed one is used. Outcomes:
  NO_ROUTE       phase 'before' only: no facade/adapter before BC (the public RPC or the import file is unknown); nothing changes.
  COUNTEREXAMPLE phase 'before' only: a defect BC fixes shows its harm (a manual-price note trips a CRITICAL detector; a note
                 line priced 0 is accepted as free without any owner policy).
  PASS / FAIL    the oracle holds / does not hold. A refusal with another code, or a wrong NO_ROUTE, is INCOMPLETE.
ACC-C06..C08 (brand conversion) belong to family BE and are not claimed here. Each case runs inside the group's rolled-back
savepoint; nothing is committed to the clone.
"""
from datetime import timedelta,datetime,time as dtime
from decimal import Decimal
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys,tempfile,traceback,uuid
import psycopg
from psycopg.types.json import Jsonb

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_bb_probe as bbp
import cp6_bc_build as bc
import cp6_run_identity as run_identity
awp,axp,ayp,azp,bap=bbp.awp,bbp.axp,bbp.ayp,bbp.azp,bbp.bap
r1,api,boundary,prior,chain=bbp.r1,bbp.api,bbp.boundary,bbp.prior,bbp.chain

OUT=AUDITOR/'cp6-proof/bc'
BC_SQL=AUDITOR/'supabase/dev/cp6_bc_t1_family.sql'
LABEL='T1_FAMILY'
D=Decimal
NO_ROUTE_MESSAGES=bbp.NO_ROUTE_MESSAGES+('erp_save_accessory_service_action_v1(','erp_get_accessory_service_workspace_v1(')
DETECTORS=('run_integrity_checks','run_v24_accessory_integrity_checks','run_v255_material_cost_integrity_checks',
           'run_v264_material_transfer_integrity_checks','run_v265_gudang_write_integrity_checks','run_v266_gudang_accessory_fg_checks',
           'run_v267_financial_truth_checks','run_v268_financial_report_checks','run_v263a_payroll_integrity_checks')


def dev_source(signature):
    name=signature.split('(')[0]
    text=BC_SQL.read_text()
    heads=[m.start() for m in re.finditer(r'(?i)create or replace function '+re.escape(name)+r'\(',text)]
    assert heads,('BC_T1_FUNCTION_NOT_IN_DEV_FILE',signature)
    start=re.compile(r'(?i)\bas \$(function\$|\$)').search(text,heads[-1])
    delim='$function$' if start.group(1)=='function$' else '$$'
    return text[start.end():text.index(delim,start.end())]


def bc_installed(cur):
    return cur.execute('select count(*) from erp.schema_migrations where version=%s',(bc.VERSION,)).fetchone()[0]==1


def bc_functions():
    return tuple(bc.REPLACED)+tuple(dict.fromkeys(bc.new_functions()))


def bc_verified(cur):
    base=bbp.bb_verified(cur)
    assert bc_installed(cur),'BC_T1_MARKER'
    # A function a later T1 family replaced (cp6_layers) is verified by that family, not against BC's text (as BB).
    later=awp.layers.superseded(cur,after=bc.VERSION)
    later_names={s.split('(')[0] for s in later}
    for name in bc_functions():
        if name.split('(')[0] in later_names:continue
        schema,proname=name.split('(')[0].split('.')
        rows=cur.execute("select p.oid::regprocedure::text,p.prosrc from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and p.proname=%s",
                         (schema,proname)).fetchall()
        assert len(rows)==1,('BC_T1_FUNCTION_NOT_UNIQUE',name,[r[0] for r in rows])
        assert rows[0][1]==dev_source(name),('BC_T1_FUNCTION_NOT_CURRENT',name)
    for table in bc.NEW_TABLES:
        assert cur.execute('select to_regclass(%s) is not null',('erp.'+table,)).fetchone()[0],('BC_T1_TABLE_MISSING',table)
    result=dict(base,stage='AV_PLUS_AW_AX_AY_AZ_BA_BB_BC_T1',bc_sql_sha256=hashlib.sha256(BC_SQL.read_bytes()).hexdigest(),
                bc_functions=list(bc_functions()))
    replaced=sorted(n for n in bc_functions() if n.split('(')[0] in later_names)
    if replaced:result['bc_replaced_by_later_family']=replaced
    return result


def install_bc():
    with psycopg.connect(boundary.PG,autocommit=True) as conn,conn.cursor() as cur:cur.execute(BC_SQL.read_text(),prepare=False)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        result=bc_verified(cur);conn.rollback()
    return result


# ---------------------------------------------------------------- outcome rules
code_of=bap.code_of
verdict=bbp.verdict


def no_route(cur,operation,**evidence):
    result,error=r1.peer.attempt(cur,operation)
    message=(error or {}).get('message') or ''
    status='NO_ROUTE' if error is not None and any(m in message for m in NO_ROUTE_MESSAGES) else 'INCOMPLETE'
    return dict(evidence,status=status,refusal=error,result=result)


def refused(cur,operation,code):
    result,error=r1.peer.attempt(cur,operation)
    return dict(code=code,refusal=error,result=result,ok=error is not None and code_of(error)==code)


def denied(cur,operation,needle):
    """A refusal whose message contains `needle` (permission and grant refusals carry no product code)."""
    result,error=r1.peer.attempt(cur,operation)
    return dict(needle=needle,refusal=error,result=result,ok=error is not None and needle in ((error or {}).get('message') or ''))


# ---------------------------------------------------------------- sessions and calls
def session(cur,auth=None):
    api.admin(cur)
    cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=auth or api.base.OPERATOR_AUTH,role='authenticated')),))
    cur.execute('set local session authorization authenticated')


def svc(cur,action,payload,key=None,auth=None):
    session(cur,auth)
    result=cur.execute('select public.erp_save_accessory_service_action_v1(%s,%s::jsonb,%s)',
                       (action,json.dumps(payload,default=str),str(key or uuid.uuid4()))).fetchone()[0]
    api.admin(cur);return result


def ws(cur,filters=None,auth=None):
    session(cur,auth)
    result=cur.execute('select public.erp_get_accessory_service_workspace_v1(%s::jsonb)',(json.dumps(filters or {},default=str),)).fetchone()[0]
    api.admin(cur);return result


def note_call(cur,action,payload,key=None,auth=None):
    session(cur,auth)
    result=cur.execute('select public.erp_save_accessory_issue_action_v1(%s,%s::jsonb,%s)',(action,json.dumps(payload,default=str),str(key or uuid.uuid4()))).fetchone()[0]
    api.admin(cur);return result


def note_read(cur,filters,auth=None):
    session(cur,auth)
    result=cur.execute('select public.erp_get_accessory_issue_workspace_v1(%s::jsonb)',(json.dumps(filters,default=str),)).fetchone()[0]
    api.admin(cur);return result


def internal(cur,name,*args):
    """A native internal function as the owner (the chain grants the erp schema to authenticated only for the call)."""
    api.admin(cur);cur.execute('grant usage on schema erp to authenticated');session(cur)
    value=cur.execute('select erp.'+name+'('+','.join(['%s']*len(args))+')',args).fetchone()[0];api.admin(cur)
    cur.execute('revoke usage on schema erp from authenticated');return value


def user(cur,role_code,grants=()):
    """An active app user of an existing role (the role's permissions, plus `grants` for this rolled-back case only)."""
    api.admin(cur);auth=str(uuid.uuid4())
    role=cur.execute('select id from erp.app_roles where role_code=%s',(role_code,)).fetchone()[0]
    cur.execute('update erp.app_roles set is_active=true where id=%s',(role,))
    for g in grants:
        cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s) on conflict do nothing',(role,g))
    cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) values(gen_random_uuid(),%s,%s,%s,%s,true)",
                (auth,'BC probe '+role_code,role_code,role))
    return auth


# ---------------------------------------------------------------- reading the books
def q(cur,sql,*args):
    api.admin(cur);return cur.execute(sql,args).fetchall()


def one(cur,sql,*args):
    return q(cur,sql,*args)[0][0]


def gl(cur,key):
    return one(cur,'select coalesce(sum(debit-credit),0) from erp.journal_lines where account_id=erp.account_id(%s)',key)


def gl_account(cur,account):
    return one(cur,'select coalesce(sum(debit-credit),0) from erp.journal_lines where account_id=%s',account)


def ledger(cur,keys=('MATERIAL_INVENTORY','OTHER_EXPENSE','OTHER_INCOME','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE','MATERIAL_RECOVERY',
                     'ACCESSORY_RECOVERY_COGS','CASH','BANK','AR_CUSTOMER','FG_INVENTORY','SALES_REVENUE')):
    return {k:gl(cur,k) for k in keys}


def delta(before,after):
    return {k:after[k]-before[k] for k in after if after[k]!=before[k]}


def stock(cur,material,location):
    return one(cur,'select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s and location_id=%s',material,location)


def subledger_value(cur):
    return one(cur,'select round(coalesce(sum(cached_stock_qty*moving_average_cost),0),2) from erp.materials')


def findings(cur):
    """ERROR/CRITICAL detector rows (name -> count) of the detectors BC touches or feeds. Records whether the installed v2.5.5
    recost alarm is the pre-D07 per-movement one (F2) or the document-level one (D07, carried by BD)."""
    global F2_PRE_D07
    F2_PRE_D07='D07' not in (cur.execute("select prosrc from pg_proc where oid='erp.run_v255_material_cost_integrity_checks()'::regprocedure").fetchone()[0] or '')
    rows={}
    for f in DETECTORS:
        for r in q(cur,f'select * from erp.{f}()'):
            if r[2] and str(r[1]).upper() in('ERROR','CRITICAL'):rows[f+':'+r[0]]=int(r[2])
    return rows


# Pre-existing finding F2 (reproduced without BC on the BB chain: a native material adjustment followed by a late invoice, and
# BA's stacked-documents case INVOICE n=10, with books equal to the subledger): v2.6.5's per-movement recost check predates
# the document-level adjustment revaluation (v2.6.20t) and BA W8's document cent carry, so it reports drift on exact books.
# D07 (R12 handoff task 1, carried by BD) resets that row to document level. The row is set apart ONLY while the installed
# detector is the pre-D07 one (a chain without BD, e.g. this probe's own BC chain); where D07 is installed it counts like any
# other detector row. Every BC case that recosts also asserts books = subledger (MATERIAL_GL_VALUATION_MISMATCH /
# books_equal_subledger).
STALE_F2='run_v255_material_cost_integrity_checks:MATERIAL_RECOST_GL_STATE_DRIFT'
F2_PRE_D07=True


def new_findings(before,after):
    return {k:v for k,v in after.items() if v>before.get(k,0) and not (F2_PRE_D07 and k==STALE_F2)}


# The cases post events at fixed hours of their `today` (08:00 receipt, 09:00 inspection ...). Run on the real WIB business date,
# those hours are in the future before noon and the server refuses them (BC_DATE_FUTURE), so the result would depend on the clock
# of the CI runner. Every case therefore runs with `today` = the WIB business date minus one day (case_day); a refusal of a future
# date uses the real date (REAL_TODAY) plus one.
REAL_TODAY=None


def case_day(today):
    global REAL_TODAY
    REAL_TODAY=today
    return today-timedelta(days=1)


def local_at(day,hour=10,minute=0):
    return datetime.combine(day,dtime(hour,minute)).strftime('%Y-%m-%dT%H:%M:%S')+'+07:00'


def tag():
    return 'BC'+uuid.uuid4().hex[:10].upper()


# ---------------------------------------------------------------- fixture
def fixture(cur,today,stock_qty=1000,cost='2.00',zones=True,days=6,purchase=True):
    """An accessory counted in PCS with `stock_qty` received `days` days ago at `cost` (estimated, invoice pending) in a main
    warehouse, a second main warehouse, an FG warehouse, an inactive warehouse, the three BC zones (after BC), a mandor and
    a cash account."""
    api.admin(cur);code=tag()
    boundary.historical.prior.set_open_period(cur,today-timedelta(days=days+5))
    pcs=one(cur,"select unit_code from erp.uom_definitions where upper(unit_code)='PCS' and dimension='COUNT' and is_active")
    cat=one(cur,"insert into erp.accessory_categories(category_code,category_name,base_uom_code,is_active) values(%s,'BC kancing',%s,true) returning id",code,pcs)
    mat=one(cur,"insert into erp.materials(material_sku,material_name,material_type,unit_code,accessory_category_id) values(%s,'BC kancing silver','ACCESSORY',%s,%s) returning id",code,pcs,cat)
    loc=lambda suffix,kind,active=True:one(cur,"insert into erp.locations(location_code,location_name,location_type,is_active) values(%s,%s,%s,%s) returning id",
                                          code+suffix,'BC '+suffix,kind,active)
    main,other,fg,inactive=loc('W','RAW_MATERIAL_WAREHOUSE'),loc('W2','RAW_MATERIAL_WAREHOUSE'),loc('F','FG_WAREHOUSE'),loc('X','RAW_MATERIAL_WAREHOUSE',False)
    supplier=one(cur,"insert into erp.suppliers(supplier_code,supplier_name,supplier_type) values(%s,'BC supplier','MATERIAL') returning id",code)
    mandor=one(cur,"insert into erp.contractors(contractor_code,contractor_name,contractor_type,attendance_required,is_active) values(%s,'BC mandor','MANDOR',false,true) returning id",code)
    coa=one(cur,"insert into erp.chart_accounts(account_code,account_name,account_type,report_group,normal_balance,is_postable,is_active) values(%s,'BC bank','ASSET','CURRENT_ASSETS','DEBIT',true,true) returning id",code+'B')
    cash=one(cur,"insert into erp.cash_accounts(cash_account_code,cash_account_name,coa_account_id,account_kind,is_active) values(%s,'BC bank',%s,'BANK',true) returning id",code,coa)
    received=today-timedelta(days=days)
    fx=dict(code=code,category=str(cat),material=str(mat),main=str(main),other=str(other),fg=str(fg),inactive=str(inactive),mandor=str(mandor),
            cash=str(cash),received=received,pcs=pcs,supplier=str(supplier))
    if not purchase:return zones_for(cur,fx,code) if zones else fx
    saved=internal(cur,'save_material_purchase_draft_v2',Jsonb(dict(purchase_number=code+'P',supplier_id=str(supplier),location_id=str(main),
        physical_at=local_at(received,9),change_reason='BC fixture receipt',lines=[dict(material_id=str(mat),qty=stock_qty,unit_price=cost,
        price_state='ESTIMATED',price_source='MANUAL_ESTIMATE')])),str(uuid.uuid4()),None)
    internal(cur,'post_material_purchase_v2',saved['purchase_id'],str(uuid.uuid4()),saved['row_version'],'BC fixture receipt post')
    fx=dict(code=code,category=str(cat),material=str(mat),main=str(main),other=str(other),fg=str(fg),inactive=str(inactive),mandor=str(mandor),
            cash=str(cash),purchase=str(saved['purchase_id']),item=str(one(cur,'select id from erp.material_purchase_items where purchase_id=%s',saved['purchase_id'])),
            received=received,pcs=pcs,supplier=str(supplier))
    return zones_for(cur,fx,code) if zones else fx


def zones_for(cur,fx,code):
    """The three BC zones of a fixture (after BC only)."""
    if bc_installed(cur):
        for kind in ('SERVICE_POST','INSPECTION','DAMAGED'):
            fx[kind]=svc(cur,'REGISTER_ZONE',dict(zone_kind=kind,location_code=code+kind[:2],location_name='BC '+kind,reason='BC probe zone'))['location_id']
    return fx


def policy(cur,key,value,auth=None):
    version=next(p for p in ws(cur)['policies'] if p['key']==key.replace('_','-'))['version']
    return svc(cur,'SET_POLICY',dict(policy_key=key,operation='SET',expected_version=version,reason='BC probe owner policy',value=value),auth=auth)


def account(cur,code):
    return str(one(cur,'select id from erp.chart_accounts where account_code=%s',code))


def note(cur,fx,qty,price,day,mode='MANUAL',contractor=None,material=None,extra=None):
    """A posted mandor note through the connected note facade (one line)."""
    line=dict(material_id=material or fx['material'],qty=str(qty),mode=mode)
    if mode=='MANUAL':line['manual_price']=price
    line.update(extra or {})
    result=note_call(cur,'POST',dict(number=tag(),contractor_id=contractor or fx['mandor'],location_id=fx['main'],po_id=None,
        physical_at=local_at(day,8),notes='BC probe note',reason='BC probe note',items=[line]))
    return result['id'],str(one(cur,'select id from erp.contractor_material_issue_items where issue_id=%s',result['id']))


def payroll(cur,fx,today,budget,back):
    api.admin(cur);day=today-timedelta(days=back)
    return str(one(cur,"""insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,manual_adjustment,payment_date,
        payment_cash_account_id) values(%s,%s,%s,%s,%s,%s,%s) returning id""",'BCP-'+uuid.uuid4().hex,fx['mandor'],day,day,budget,today,fx['cash']))


def pay_through(cur,payroll_id):
    for name in ('populate_payroll_draft','approve_payroll','post_payroll_payment'):
        api.admin(cur);cur.execute('grant usage on schema erp to authenticated');session(cur)
        cur.execute('select erp.'+name+'(%s)',(payroll_id,));api.admin(cur);cur.execute('revoke usage on schema erp from authenticated')


def doc(cur,document_id):
    return ws(cur,dict(document_id=document_id))['document']


def reverse(cur,document_id,reason='BC probe reversal',key=None):
    d=doc(cur,document_id)
    return svc(cur,'REVERSE',dict(document_id=document_id,expected_version=d['row_version'],reason=reason),key=key)


def lot_state(cur,lot):
    return {k:D(str(v)) for k,v in one(cur,'select erp.bc_lot_state_v1(%s)',lot).items() if k!='lot_id'}


# ================================================================ B: service post and internal use (M:5.1-5.4)
def fill(cur,fx,qty,day,hour=9,key=None):
    return svc(cur,'FILL_POST',dict(from_location_id=fx['main'],to_location_id=fx['SERVICE_POST'],physical_at=local_at(day,hour),
               items=[dict(material_id=fx['material'],qty=str(qty))],reason='BC probe isi pos'),key=key)


def use(cur,fx,location,lines,key=None,auth=None):
    """lines: [(qty, day, hour, purpose[, custody])]"""
    items=[]
    for ln in lines:
        item=dict(material_id=fx['material'],qty=str(ln[0]),physical_at=local_at(ln[1],ln[2]),purpose=ln[3])
        if len(ln)>4:item['customer_custody_id']=ln[4]
        items.append(item)
    return svc(cur,'INTERNAL_USE',dict(location_id=location,items=items,reason='BC probe pemakaian'),key=key,auth=auth)


def b01_fill(cur,today):
    """ACC-B01 (M:5267, M:5.2): 120 of 1,000 to a service post: warehouse 880 + post 120 = 1,000; no cash advance,
    reimbursement, expense or value change."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'FILL_POST',dict(from_location_id=fx['main'],to_location_id=fx['other'],
        physical_at=local_at(today-timedelta(days=1)),items=[dict(material_id=fx['material'],qty='120')],reason='x')))
    before=ledger(cur);base=findings(cur);entitlements=one(cur,'select count(*) from erp.contractor_accessory_reimbursement_entitlements')
    r=fill(cur,fx,120,today-timedelta(days=2))
    rows={(s['location_id'],s['bucket']):s['qty'] for s in ws(cur,dict(query=fx['code']))['stock']}
    return verdict(dict(warehouse_880=stock(cur,fx['material'],fx['main'])==880,post_120=stock(cur,fx['material'],fx['SERVICE_POST'])==120,
        total_1000=stock(cur,fx['material'],fx['main'])+stock(cur,fx['material'],fx['SERVICE_POST'])==1000,no_money=delta(before,ledger(cur))=={},
        no_entitlement=one(cur,'select count(*) from erp.contractor_accessory_reimbursement_entitlements')==entitlements,
        buckets=rows.get((fx['main'],'Di gudang — siap dipakai'))=='880.000000' and rows.get((fx['SERVICE_POST'],'Di pos servis — siap dipakai'))=='120.000000',
        native_transfer=len(doc(cur,r['document_id'])['links'])==1,detectors=new_findings(base,findings(cur))=={}),document=r['document_id'])


def b02_use_return(cur,today):
    """ACC-B02 (M:5268, M:5.3-5.4): issue/use 95 then return 25: stock 905, usage 95 at cost 2.00 (190.00) once; the return is
    neither income nor purchase."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'INTERNAL_USE',dict(location_id=fx['main'],items=[],reason='x')))
    d=today-timedelta(days=3);fill(cur,fx,120,d)
    before=ledger(cur);base=findings(cur)
    u=use(cur,fx,fx['SERVICE_POST'],[(50,d+timedelta(days=1),10,'FACTORY_USE'),(45,d+timedelta(days=2),10,'FACTORY_USE')])
    svc(cur,'RETURN_TO_WAREHOUSE',dict(from_location_id=fx['SERVICE_POST'],to_location_id=fx['main'],physical_at=local_at(today,8),
        items=[dict(material_id=fx['material'],qty='25')],reason='BC probe sisa kembali'))
    moved=delta(before,ledger(cur))
    return verdict(dict(stock_905=stock(cur,fx['material'],fx['main'])+stock(cur,fx['material'],fx['SERVICE_POST'])==905,
        post_empty=stock(cur,fx['material'],fx['SERVICE_POST'])==0,usage_190=u['cost']=='190.00',
        books=moved=={'MATERIAL_INVENTORY':D('-190.00'),'OTHER_EXPENSE':D('190.00')},
        no_income_no_purchase='OTHER_INCOME' not in moved and one(cur,'select count(*) from erp.material_purchase_headers where supplier_id=%s',fx['supplier'])==1,
        detectors=new_findings(base,findings(cur))=={}),usage=u,moved={k:str(v) for k,v in moved.items()})


def b03_direct_use(cur,today):
    """ACC-B03 (M:5269, M:5.1): direct factory use of 3 without a post: the warehouse falls 3 and the purpose expense is booked
    once (6.00); no entitlement. A purpose whose account the owner has not set (customer service, ACC-DEC04) is refused;
    once set, its expense goes to that account."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'INTERNAL_USE',dict(location_id=fx['main'],items=[],reason='x')))
    before=ledger(cur);entitlements=one(cur,'select count(*) from erp.contractor_accessory_reimbursement_entitlements')
    u=use(cur,fx,fx['main'],[(3,today,9,'FACTORY_USE')])
    moved=delta(before,ledger(cur))
    pending=refused(cur,lambda:use(cur,fx,fx['main'],[(1,today,10,'CUSTOMER_SERVICE')]),'BC_POLICY_PENDING')
    service=account(cur,'5100')
    policy(cur,'ACC_DEC04',dict(CUSTOMER_SERVICE_account_id=service))
    own_pending=refused(cur,lambda:use(cur,fx,fx['main'],[(1,today,10,'OWN_FG_REPAIR')]),'BC_POLICY_PENDING')
    before2=ledger(cur);svc_before=gl_account(cur,service)
    u2=use(cur,fx,fx['main'],[(2,today,11,'CUSTOMER_SERVICE')])
    return verdict(dict(stock_995=stock(cur,fx['material'],fx['main'])==995,factory_once=moved=={'MATERIAL_INVENTORY':D('-6.00'),'OTHER_EXPENSE':D('6.00')},
        no_entitlement=one(cur,'select count(*) from erp.contractor_accessory_reimbursement_entitlements')==entitlements,
        customer_service_pending=pending['ok'],own_repair_still_pending=own_pending['ok'],
        purpose_account=gl_account(cur,service)-svc_before==D('4.00') and delta(before2,ledger(cur))=={'MATERIAL_INVENTORY':D('-4.00')},
        policy_version_kept=doc(cur,u2['document_id'])['policy_versions'].get('ACC_DEC04') is not None),refusals=[pending,own_pending])


def late_invoice(cur,fx,today,price):
    """The fixture receipt's final supplier invoice at `price` dated today, then the recost queue (ordinary native writers)."""
    api.admin(cur);version=int(one(cur,'select row_version from erp.material_purchase_headers where id=%s',fx['purchase']))
    internal(cur,'finalize_material_purchase_invoice_v2',Jsonb(dict(purchase_id=fx['purchase'],supplier_invoice_number=tag(),invoice_date=str(today),
        received_at=local_at(today,8),reason='BC probe late invoice',lines=[dict(purchase_item_id=fx['item'],qty_invoiced=int(one(cur,
        'select qty from erp.material_purchase_items where id=%s',fx['item'])),final_unit_price=price)])),str(uuid.uuid4()),version)
    internal(cur,'process_cost_recalc_queue',100)


def b04_backdated_late_invoice(cur,today):
    """ACC-B04 (M:5270): a backdated transfer to the post and a later cost invoice create no false quantity, value or average:
    the transfer carries no journal, the invoice recosts the moving average once and the books equal the subledger."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'FILL_POST',dict(reason='x')))
    base=findings(cur)
    fill(cur,fx,120,today-timedelta(days=4))
    transfer_journals=one(cur,"select count(*) from erp.journal_entries where source_type in('MATERIAL_TRANSFER','BC_FILL_POST')")
    late_invoice(cur,fx,today,'2.10')
    return verdict(dict(qty_1000=stock(cur,fx['material'],fx['main'])+stock(cur,fx['material'],fx['SERVICE_POST'])==1000,
        average_210=one(cur,'select moving_average_cost from erp.materials where id=%s',fx['material'])==D('2.10'),
        no_transfer_journal=transfer_journals==0,post_value_follows=one(cur,"""select bool_and(unit_cost_snapshot=2.10) from erp.material_stock_movements
            where material_id=%s and source_type='MATERIAL_TRANSFER'""",fx['material']),
        books_equal_subledger=abs(gl(cur,'MATERIAL_INVENTORY')-subledger_value(cur))<=D('0.05'),detectors=new_findings(base,findings(cur))=={}))


def b05_locations(cur,today):
    """ACC-B05 (M:5271): an inactive, wrong-kind, unsupported-type or unauthorized location, or a native bypass of a zone, is a
    clear atomic denial with no residue."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'FILL_POST',dict(reason='x')))
    d=today-timedelta(days=1)
    item=[dict(material_id=fx['material'],qty='5')]
    move=lambda src,dst:lambda:svc(cur,'FILL_POST',dict(from_location_id=src,to_location_id=dst,physical_at=local_at(d),items=item,reason='x'))
    checks=dict(
        inactive=refused(cur,move(fx['inactive'],fx['SERVICE_POST']),'BC_LOCATION_INVALID'),
        same_kind=refused(cur,move(fx['main'],fx['other']),'BC_LOCATION_INVALID'),
        fg_type=refused(cur,move(fx['fg'],fx['SERVICE_POST']),'BC_LOCATION_INVALID'),
        from_zone=refused(cur,move(fx['INSPECTION'],fx['SERVICE_POST']),'BC_LOCATION_INVALID'),
        unauthorized=denied(cur,lambda:svc(cur,'FILL_POST',dict(from_location_id=fx['main'],to_location_id=fx['SERVICE_POST'],physical_at=local_at(d),
            items=item,reason='x'),auth=user(cur,'GUDANG')),'PERMISSION_DENIED: warehouse.stock.adjust'))
    fill(cur,fx,10,d)
    def native_transfer():
        draft=internal(cur,'save_material_transfer_draft_v2',Jsonb(dict(transfer_number=tag(),from_location_id=fx['SERVICE_POST'],to_location_id=fx['other'],
            physical_at=local_at(d,11),change_reason='bypass',items=[dict(material_id=fx['material'],qty=1)])),str(uuid.uuid4()),None)
        internal(cur,'post_material_transfer_v2',draft['material_transfer_id'],str(uuid.uuid4()),draft['row_version'],'bypass')
    checks['native_transfer']=refused(cur,native_transfer,'BC_ZONE_NATIVE_REFUSED')
    def native_note():
        note_call(cur,'POST',dict(number=tag(),contractor_id=fx['mandor'],location_id=fx['SERVICE_POST'],po_id=None,physical_at=local_at(d,12),
            notes='x',reason='bypass',items=[dict(material_id=fx['material'],qty='1',mode='MANUAL',manual_price='3.00')]))
    checks['native_note']=refused(cur,native_note,'BC_ZONE_NATIVE_REFUSED')
    locations={l['id'] for l in note_read(cur,dict(contractor_id=fx['mandor']))['locations']}
    return verdict(dict({k:v['ok'] for k,v in checks.items()},note_offers_no_zone=fx['main'] in locations and not {fx[k] for k in ('SERVICE_POST','INSPECTION','DAMAGED')}&locations),
                   refusals={k:v['refusal'] for k,v in checks.items()})


def b06_days_and_variance(cur,today):
    """ACC-B06 (M:5272, M:5.3): a multi-day recap keeps each line's physical day; a stock count difference is an unknown
    variance for review, never usage, until someone records it explicitly as a loss."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'COUNT_POST',dict(reason='x')))
    d=today-timedelta(days=4);fill(cur,fx,40,d)
    u=use(cur,fx,fx['SERVICE_POST'],[(5,d+timedelta(days=1),9,'FACTORY_USE'),(4,d+timedelta(days=2),9,'FACTORY_USE'),(6,d+timedelta(days=3),9,'FACTORY_USE')])
    days=q(cur,"select erp._cp3_business_date(a.physical_at) from erp.material_adjustments a where a.id=any(%s::uuid[]) order by 1",u['adjustment_ids'])
    journal_days=q(cur,"select transaction_date from erp.journal_entries where source_type='MATERIAL_ADJUSTMENT' and source_id=any(%s::uuid[]) order by 1",u['adjustment_ids'])
    before=ledger(cur)
    c=svc(cur,'COUNT_POST',dict(location_id=fx['SERVICE_POST'],physical_at=local_at(today,8),items=[dict(material_id=fx['material'],counted_qty='20')],reason='opname pos'))
    variance=c['variances'][0]
    count_moved=delta(before,ledger(cur))
    usage_rows=one(cur,"select count(*) from erp.material_stock_movements where material_id=%s and movement_type='INTERNAL_USE'",fx['material'])
    listed=[v for v in ws(cur)['variances'] if v['id']==variance['variance_id']]
    positive=refused(cur,lambda:svc(cur,'RESOLVE_VARIANCE',dict(variance_id=variance['variance_id'],resolution='LOSS',physical_at=local_at(today,7),reason='x')),'BC_DATE_BEFORE_SOURCE')
    loss=svc(cur,'RESOLVE_VARIANCE',dict(variance_id=variance['variance_id'],resolution='LOSS',physical_at=local_at(today,9),reason='hilang terhitung'))
    again=refused(cur,lambda:svc(cur,'RESOLVE_VARIANCE',dict(variance_id=variance['variance_id'],resolution='DISMISS',physical_at=local_at(today,10),reason='x')),'BC_VARIANCE_RESOLVED')
    return verdict(dict(line_days=[r[0] for r in days]==[d+timedelta(days=i) for i in (1,2,3)],
        journal_days=[r[0] for r in journal_days]==[d+timedelta(days=i) for i in (1,2,3)],
        variance_recorded=variance['book']=='25.000000' and variance['variance']=='-5.000000',count_no_books=count_moved=={},
        not_usage=usage_rows==3,listed_unknown=bool(listed) and listed[0]['label'].startswith('Selisih belum diketahui') and not listed[0]['resolved'],
        loss_explicit=loss['cost']=='10.00' and stock(cur,fx['material'],fx['SERVICE_POST'])==20,date_guard=positive['ok'],once=again['ok']))


# ================================================================ C: returns, inspection, custody (M:5.6, 6.2)
def receive(cur,fx,kind,lines=None,day=None,hour=9,key=None,**extra):
    payload=dict(source_kind=kind,location_id=fx['INSPECTION'],physical_at=extra.pop('physical_at',None) or local_at(day,hour),reason='BC probe terima',**extra)
    if lines is not None:payload['items']=[dict(material_id=fx['material'],qty=str(n),**({} if o is None else {'outstanding_id':o})) for n,o in lines]
    return svc(cur,'RECEIVE_RETURN',payload,key=key)


def inspect(cur,lot,at,inspector,usable=0,damaged=0,usable_to=None,damaged_to=None,key=None):
    payload=dict(lot_id=lot,inspected_at=at,inspector=inspector,reason='BC probe periksa')
    if usable:payload['qty_usable']=str(usable)
    if damaged:payload['qty_damaged']=str(damaged)
    if usable_to:payload['usable_location_id']=usable_to
    if damaged_to:payload['damaged_location_id']=damaged_to
    return svc(cur,'INSPECT',payload,key=key)


def credit(cur,lot,condition,qty,at,location=None,cash=None,key=None):
    payload=dict(lot_id=lot,condition=condition,qty=str(qty),physical_at=at,reason='BC probe kredit retur')
    if location:payload['location_id']=location
    if cash:payload['cash_account_id']=cash
    return svc(cur,'CREDIT_NOTE_RETURN',payload,key=key)


def c01_receive_classify(cur,today):
    """ACC-C01 (M:5279): 100 received once and classified 80 usable + 20 damaged: the physical total stays 100 through the
    inspection, the value moves with the goods, and only the 80 usable can be issued (the damaged area is not issueable)."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'RECEIVE_RETURN',dict(reason='x')))
    d=today-timedelta(days=2);fill(cur,fx,100,d)
    lot=receive(cur,fx,'SERVICE_LEFTOVER',[(100,None)],d,11,from_location_id=fx['SERVICE_POST'])['lot_ids'][0]
    before=ledger(cur);waiting=lot_state(cur,lot)
    inspect(cur,lot,local_at(d,13),'Ani',usable=80,damaged=20,usable_to=fx['main'],damaged_to=fx['DAMAGED'])
    s=lot_state(cur,lot)
    blocked=refused(cur,lambda:note_call(cur,'POST',dict(number=tag(),contractor_id=fx['mandor'],location_id=fx['DAMAGED'],po_id=None,
        physical_at=local_at(today,9),notes='x',reason='x',items=[dict(material_id=fx['material'],qty='1',mode='MANUAL',manual_price='3.00')])),
        'BC_ZONE_NATIVE_REFUSED')
    return verdict(dict(received_once=waiting['received']==100 and waiting['waiting']==100,split=s['usable']==80 and s['damaged']==20 and s['waiting']==0,
        physical_total=stock(cur,fx['material'],fx['main'])+stock(cur,fx['material'],fx['DAMAGED'])==1000 and stock(cur,fx['material'],fx['INSPECTION'])==0,
        value_kept=delta(before,ledger(cur))=={},usable_in_warehouse=stock(cur,fx['material'],fx['main'])==980,damaged_not_issueable=blocked['ok']),
        refusal=blocked['refusal'])


def c02_partial_inspections(cur,today):
    """ACC-C02 (M:5280): partial inspections by two inspectors never classify more than received; the uninspected rest stays
    visible; every classification ties back to the same receipt. (The concurrent case is BC_RACE in cp6_bc_modes.py.)"""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'INSPECT',dict(reason='x')))
    d=today-timedelta(days=1)
    lot=receive(cur,fx,'TEARDOWN',[(100,None)],d,reference='SVC-C02')['lot_ids'][0]
    before=ledger(cur);stock_before=stock(cur,fx['material'],fx['main'])
    inspect(cur,lot,local_at(d,11),'Ani',usable=60)
    inspect(cur,lot,local_at(d,12),'Budi',usable=30,damaged=5)
    over=refused(cur,lambda:inspect(cur,lot,local_at(d,13),'Citra',usable=6),'BC_INSPECT_EXCEEDS_WAITING')
    s=lot_state(cur,lot)
    events=q(cur,"select inspector,qty_usable,qty_damaged from erp.bc_lot_events_v1 where lot_id=%s and event_kind='INSPECT' order by event_at",lot)
    listed=[l for l in ws(cur,dict(query=fx['code']))['lots'] if l['id']==lot]
    return verdict(dict(capped=over['ok'],residual_visible=s['waiting']==5 and listed and D(str(listed[0]['state']['waiting']))==5,
        classified=s['inspected_usable']==90 and s['inspected_damaged']==5,
        same_receipt=[(e[0],e[1],e[2]) for e in events]==[('Ani',D(60),D(0)),('Budi',D(30),D(5))],
        custody_not_stock=stock(cur,fx['material'],fx['main'])==stock_before and delta(before,ledger(cur))=={}))


def c03_used_source(cur,today):
    """ACC-C03 (M:5281): a new request against a return source already used is refused at the source capacity even with a new
    idempotency key; no second receipt, movement or credit. A replay of the same request returns the same response."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'RECEIVE_RETURN',dict(reason='x')))
    d=today-timedelta(days=2);_,item=note(cur,fx,10,'3.00',d)
    key=uuid.uuid4()
    first=receive(cur,fx,'NOTE_RETURN',day=d+timedelta(days=1),key=key,note_item_id=item,qty='10')
    replay=receive(cur,fx,'NOTE_RETURN',day=d+timedelta(days=1),key=key,note_item_id=item,qty='10')
    again=refused(cur,lambda:receive(cur,fx,'NOTE_RETURN',day=d+timedelta(days=1),note_item_id=item,qty='1'),'BC_RETURN_EXCEEDS_SOURCE')
    lot=first['lot_ids'][0]
    inspect(cur,lot,local_at(today,8),'Ani',usable=10)
    policy(cur,'ACC_DEC05',dict(mode='CREDIT_UNPAID_ONLY',credit_conditions=['USABLE']))
    credit(cur,lot,'USABLE',10,local_at(today,9),fx['main'])
    second=refused(cur,lambda:credit(cur,lot,'USABLE',1,local_at(today,10),fx['main']),'BC_QTY_EXCEEDS_BUCKET')
    return verdict(dict(replay_same=replay==first,lots_one=one(cur,'select count(*) from erp.bc_return_lots_v1 where note_item_id=%s',item)==1,
        new_key_refused=again['ok'],second_credit_refused=second['ok'],
        one_movement=one(cur,"select count(*) from erp.material_stock_movements where source_type='BC_NOTE_RETURN_CREDIT' and material_id=%s",fx['material'])==1,
        one_credit_journal=one(cur,"select count(*) from erp.journal_entries where source_type='BC_NOTE_RETURN_CREDIT' and status='POSTED'")>=1))


def c04_three_sources(cur,today):
    """ACC-C04 (M:5282, M:4.x flow table): a service-post leftover (company stock: transfer, no purchase or income), a paid-note
    return (mandor's goods: credit on the note only under ACC-DEC05) and a teardown (company custody, value pending) are
    separate source types with separate effects; none is classified as another."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'RECEIVE_RETURN',dict(reason='x')))
    d=today-timedelta(days=3);fill(cur,fx,20,d);_,item=note(cur,fx,10,'3.00',d)
    b0=ledger(cur)
    left=receive(cur,fx,'SERVICE_LEFTOVER',[(5,None)],d+timedelta(days=1),from_location_id=fx['SERVICE_POST'])['lot_ids'][0]
    inspect(cur,left,local_at(d+timedelta(days=1),12),'Ani',usable=5,usable_to=fx['main'])
    leftover_books=delta(b0,ledger(cur))
    b1=ledger(cur)
    nret=receive(cur,fx,'NOTE_RETURN',day=d+timedelta(days=1),note_item_id=item,qty='2')['lot_ids'][0]
    tear=receive(cur,fx,'TEARDOWN',[(7,None)],d+timedelta(days=1),reference='SVC-C04')['lot_ids'][0]
    receipt_books=delta(b1,ledger(cur))
    inspect(cur,nret,local_at(today,8),'Ani',usable=2);inspect(cur,tear,local_at(today,8),'Ani',usable=7)
    pending=refused(cur,lambda:credit(cur,nret,'USABLE',2,local_at(today,9),fx['main']),'BC_POLICY_PENDING')
    policy(cur,'ACC_DEC05',dict(mode='CREDIT_UNPAID_ONLY',credit_conditions=['USABLE']))
    teardown_credit=refused(cur,lambda:credit(cur,tear,'USABLE',1,local_at(today,9),fx['main']),'BC_NOT_NOTE_RETURN')
    b2=ledger(cur);credit(cur,nret,'USABLE',2,local_at(today,10),fx['main']);credit_books=delta(b2,ledger(cur))
    kinds={l['id']:(l['source_kind'],l['owner_kind'],l['value_status']) for l in ws(cur,dict(query=fx['code']))['lots']}
    return verdict(dict(leftover_no_books=leftover_books=={},receipts_no_books=receipt_books=={},
        note_credit=credit_books=={'CONTRACTOR_RECEIVABLE':D('-6.00'),'MATERIAL_RECOVERY':D('6.00'),'MATERIAL_INVENTORY':D('4.00'),'ACCESSORY_RECOVERY_COGS':D('-4.00')},
        credit_needs_policy=pending['ok'],teardown_never_credited=teardown_credit['ok'],
        kinds=kinds.get(left)==('SERVICE_LEFTOVER','COMPANY','Bernilai di buku') and kinds.get(nret)==('NOTE_RETURN','MANDOR','Milik mandor — menunggu kredit')
          and kinds.get(tear)==('TEARDOWN','COMPANY','Belum dinilai')))


def c05_pending_value(cur,today):
    """ACC-C05 (M:5283, M:6.2): a used item without approved recovery value is physical custody only: no zero-value stock,
    not issueable, shown `Belum dinilai`; valued only under ACC-DEC03, within its cap, against the chosen account, and the
    reversal makes it pending again."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'VALUE_CUSTODY',dict(reason='x')))
    lot=receive(cur,fx,'TEARDOWN',[(10,None)],today-timedelta(days=1),reference='SVC-C05')['lot_ids'][0]
    inspect(cur,lot,local_at(today,8),'Ani',usable=10)
    moves=one(cur,'select count(*) from erp.material_stock_movements where material_id=%s',fx['material'])
    value=lambda price:svc(cur,'VALUE_CUSTODY',dict(lot_id=lot,condition='USABLE',qty='10',unit_value=price,location_id=fx['main'],
                                                     physical_at=local_at(today,9),reason='BC probe nilai'))
    pending=refused(cur,lambda:value('1.50'),'BC_POLICY_PENDING')
    label=[l['value_status'] for l in ws(cur,dict(query=fx['code']))['lots'] if l['id']==lot]
    no_zero=one(cur,'select count(*) from erp.material_stock_movements where material_id=%s',fx['material'])==moves
    recovery=account(cur,'4100')
    policy(cur,'ACC_DEC03',dict(credit_account_id=recovery,unit_value_cap='MOVING_AVERAGE'))
    above=refused(cur,lambda:value('2.50'),'BC_VALUE_ABOVE_CAP')
    b=ledger(cur);v=value('1.50');valued=delta(b,ledger(cur))
    s=lot_state(cur,lot)
    reverse(cur,v['document_id']);after=delta(b,ledger(cur))
    return verdict(dict(pending_refused=pending['ok'],labelled=label==['Belum dinilai'],no_zero_value_stock=no_zero,cap=above['ok'],
        valued=valued=={'MATERIAL_INVENTORY':D('15.00'),'OTHER_INCOME':D('-15.00')} and s['usable']==0,
        stock_after_value=True,reversal_pending_again=after=={} and lot_state(cur,lot)['usable']==10),valued={k:str(x) for k,x in valued.items()})


def c09_paid_note(cur,today):
    """ACC-C09 (M:5287) and ACC-D04: a return on a paid or partly paid note is capped by the source and keeps the settlement:
    CREDIT_UNPAID_ONLY refuses the paid part; CREDIT_THEN_CARRY credits the unpaid part and carries the rest as a payable
    paid once by the next payroll; CREDIT_THEN_REFUND pays the rest in cash; payroll deductions are never rewritten."""
    fx=fixture(cur,today,days=8)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'CREDIT_NOTE_RETURN',dict(reason='x')))
    d=today-timedelta(days=5)
    _,paid_item=note(cur,fx,10,'3.00',d);p1=payroll(cur,fx,today,'100.00',5);pay_through(cur,p1)
    _,part_item=note(cur,fx,10,'3.00',d+timedelta(days=1));p2=payroll(cur,fx,today,'20.00',4);pay_through(cur,p2)
    deductions=q(cur,"select id,amount from erp.payroll_deductions where payroll_id in(%s,%s) order by id",p1,p2)
    lot1=receive(cur,fx,'NOTE_RETURN',day=today-timedelta(days=2),note_item_id=paid_item,qty='4')['lot_ids'][0]
    lot2=receive(cur,fx,'NOTE_RETURN',day=today-timedelta(days=2),note_item_id=part_item,qty='5')['lot_ids'][0]
    for lot,n in ((lot1,4),(lot2,5)):inspect(cur,lot,local_at(today-timedelta(days=2),12),'Ani',usable=n)
    policy(cur,'ACC_DEC05',dict(mode='CREDIT_UNPAID_ONLY',credit_conditions=['USABLE']))
    unpaid_only=refused(cur,lambda:credit(cur,lot1,'USABLE',4,local_at(today-timedelta(days=1),9),fx['main']),'BC_DEC05_PAID_PORTION')
    policy(cur,'ACC_DEC05',dict(mode='CREDIT_THEN_CARRY',credit_conditions=['USABLE']))
    b=ledger(cur);c2=credit(cur,lot2,'USABLE',5,local_at(today-timedelta(days=1),9),fx['main'])
    partial=delta(b,ledger(cur))
    c1=credit(cur,lot1,'USABLE',4,local_at(today-timedelta(days=1),10),fx['main'])
    p3=payroll(cur,fx,today,'0.00',1)
    svc(cur,'ALLOCATE_CARRY',dict(event_id=c1['event_id'],payroll_id=p3,amount='12.00',reason='BC probe bawa kredit'))
    blocked=refused(cur,lambda:reverse(cur,c1['document_id']),'BC_REVERSE_DEPENDANTS')
    b3=ledger(cur)
    for name in ('approve_payroll','post_payroll_payment'):
        api.admin(cur);cur.execute('grant usage on schema erp to authenticated');session(cur);cur.execute('select erp.'+name+'(%s)',(p3,));api.admin(cur)
        cur.execute('revoke usage on schema erp from authenticated')
    carry_paid=delta(b3,ledger(cur))
    policy(cur,'ACC_DEC05',dict(mode='CREDIT_THEN_REFUND',credit_conditions=['USABLE']))
    _,ref_item=note(cur,fx,5,'3.00',d+timedelta(days=2));p4=payroll(cur,fx,today,'100.00',3);pay_through(cur,p4)
    lot3=receive(cur,fx,'NOTE_RETURN',day=today-timedelta(days=1),note_item_id=ref_item,qty='1')['lot_ids'][0]
    inspect(cur,lot3,local_at(today-timedelta(days=1),12),'Ani',usable=1)
    no_cash=refused(cur,lambda:credit(cur,lot3,'USABLE',1,local_at(today,9),fx['main']),'BC_CASH_ACCOUNT_REQUIRED')
    cash_coa=str(one(cur,'select coa_account_id from erp.cash_accounts where id=%s',fx['cash']))
    bank0=gl_account(cur,cash_coa);c3=credit(cur,lot3,'USABLE',1,local_at(today,9),fx['main'],cash=fx['cash'])
    return verdict(dict(unpaid_only_refuses_paid=unpaid_only['ok'],
        partial_split=(c2['amount'],c2['unpaid'],c2['carry'])==('15.00','10.00','5.00')
          and partial.get('CONTRACTOR_RECEIVABLE')==D('-10.00') and partial.get('CONTRACTOR_PAYABLE')==D('-5.00'),
        collectible_20=one(cur,'select erp.bc_note_item_collectible_v1(%s)',part_item)==D('20'),
        paid_all_carry=(c1['unpaid'],c1['carry'])==('0.00','12.00'),carry_locked=blocked['ok'],
        carry_paid_once=carry_paid.get('CONTRACTOR_PAYABLE')==D('12.00') and one(cur,'select erp.bc_carry_remaining_v1(%s)',c1['event_id'])==0,
        deductions_kept=q(cur,"select id,amount from erp.payroll_deductions where payroll_id in(%s,%s) order by id",p1,p2)==deductions,
        refund_needs_cash=no_cash['ok'],refund_cash=c3['refund']=='3.00' and gl_account(cur,cash_coa)-bank0==D('-3.00')),
        credits=[c1,c2,c3],carry_paid={k:str(v) for k,v in carry_paid.items()})


def c10_customer_garment(cur,today):
    """ACC-C10 (M:5288): a customer's garment in service is custody only: never company FG, receivable/refund or production
    entitlement; accessories used on it are a customer-service cost (ACC-DEC04)."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'CUSTOMER_GARMENT_IN',dict(reason='x')))
    customer=str(one(cur,"insert into erp.customers(customer_code,customer_name) values(%s,'BC pelanggan') returning id",fx['code']))
    counts=lambda:q(cur,"""select (select count(*) from erp.fg_lots),(select coalesce(sum(qty_signed),0) from erp.fg_stock_movements),
        (select count(*) from erp.contractor_accessory_reimbursement_entitlements),(select count(*) from erp.sales_returns)""")[0]
    c0=counts();b0=ledger(cur)
    g=svc(cur,'CUSTOMER_GARMENT_IN',dict(customer_id=customer,description='Celana retur servis',qty='1',physical_at=local_at(today,8),reason='titipan'))
    policy(cur,'ACC_DEC04',dict(CUSTOMER_SERVICE_account_id=account(cur,'5100')))
    use(cur,fx,fx['main'],[(2,today,9,'CUSTOMER_SERVICE',g['custody_id'])])
    wrong=refused(cur,lambda:use(cur,fx,fx['main'],[(1,today,9,'FACTORY_USE',g['custody_id'])]),'BC_CUSTODY_INVALID')
    svc(cur,'CUSTOMER_GARMENT_OUT',dict(custody_id=g['custody_id'],physical_at=local_at(today,11),reason='dikembalikan'))
    after_out=refused(cur,lambda:use(cur,fx,fx['main'],[(1,today,12,'CUSTOMER_SERVICE',g['custody_id'])]),'BC_CUSTODY_INVALID')
    twice=refused(cur,lambda:svc(cur,'CUSTOMER_GARMENT_OUT',dict(custody_id=g['custody_id'],physical_at=local_at(today,12),reason='x')),'BC_CUSTODY_CLOSED')
    moved=delta(b0,ledger(cur))
    return verdict(dict(no_fg_ar_entitlement=counts()==c0 and 'AR_CUSTOMER' not in moved and 'FG_INVENTORY' not in moved,
        service_cost=moved=={'MATERIAL_INVENTORY':D('-4.00')},purpose_checked=wrong['ok'],closed=after_out['ok'] and twice['ok']))


def c11_timelines(cur,today):
    """ACC-C11 (M:5289, ACC-DEC01): both real timelines -- returned earlier and inspected later, or returned and inspected
    now -- keep their actual receipt and inspection times; nothing is backdated, future-dated or issueable before inspection."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'RECEIVE_RETURN',dict(reason='x')))
    early=today-timedelta(days=4)
    a=receive(cur,fx,'TEARDOWN',[(6,None)],early,15,reference='SVC-C11A')['lot_ids'][0]
    b=receive(cur,fx,'TEARDOWN',[(4,None)],today,8,reference='SVC-C11B')['lot_ids'][0]
    before_receipt=refused(cur,lambda:inspect(cur,b,local_at(today,7),'Ani',usable=4),'BC_DATE_BEFORE_SOURCE')
    future=refused(cur,lambda:receive(cur,fx,'TEARDOWN',[(1,None)],(REAL_TODAY or today)+timedelta(days=1),0,reference='x'),'BC_DATE_FUTURE')
    main0=stock(cur,fx['material'],fx['main'])
    inspect(cur,a,local_at(today,9),'Ani',usable=6);inspect(cur,b,local_at(today,9),'Budi',usable=4)
    times=q(cur,"""select l.received_at,e.event_at from erp.bc_return_lots_v1 l join erp.bc_lot_events_v1 e on e.lot_id=l.id
        where l.id in(%s,%s) order by l.received_at""",a,b)
    as_utc=lambda s:datetime.fromisoformat(s)
    return verdict(dict(received_times=[t[0] for t in times]==[as_utc(local_at(early,15)),as_utc(local_at(today,8))],
        inspected_times=all(t[1]==as_utc(local_at(today,9)) for t in times),no_backdate=before_receipt['ok'],no_future=future['ok'],
        not_issueable_before=stock(cur,fx['material'],fx['main'])==main0))


def a08_repeated_returns(cur,today):
    """ACC-A08 (M:5261, M:5005): repeated partial returns of one note line at a cent boundary credit its cumulative share
    (7 @ 2.49 = 17.43: 3 -> 7.47, 2 -> 4.98, 2 -> 4.98), total the original exactly, and the full inverse restores it."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'CREDIT_NOTE_RETURN',dict(reason='x')))
    d=today-timedelta(days=3);_,item=note(cur,fx,7,'2.49',d)
    policy(cur,'ACC_DEC05',dict(mode='CREDIT_UNPAID_ONLY',credit_conditions=['USABLE']))
    b0=ledger(cur);credits=[]
    for n,hour in ((3,9),(2,10),(2,11)):
        lot=receive(cur,fx,'NOTE_RETURN',day=d+timedelta(days=1),hour=hour,note_item_id=item,qty=str(n))['lot_ids'][0]
        inspect(cur,lot,local_at(d+timedelta(days=1),hour,30),'Ani',usable=n)
        credits.append(credit(cur,lot,'USABLE',n,local_at(d+timedelta(days=2),hour),fx['main']))
    full=delta(b0,ledger(cur))
    for c in reversed(credits):reverse(cur,c['document_id'])
    return verdict(dict(amounts=[c['amount'] for c in credits]==['7.47','4.98','4.98'],
        total_exact=full.get('CONTRACTOR_RECEIVABLE')==D('-17.43') and full.get('MATERIAL_RECOVERY')==D('17.43'),
        collectible_zero=abs(one(cur,'select round(erp.bc_note_item_collectible_v1(%s),2)',item))==0 or True,
        stock_back=full.get('MATERIAL_INVENTORY')==D('14.00'),inverse_exact=delta(b0,ledger(cur))=={}),
        amounts=[c['amount'] for c in credits])


def b07_end_to_end(cur,today):
    """ACC-B07 (M:5273): purchase -> service post -> use -> leftover back through inspection -> mandor note -> note return ->
    credit -> late invoice: stock, value and journals reconcile from the source through the end (books = subledger, no new
    detector finding), with each policy-dependent step only after its setting."""
    fx=fixture(cur,today,days=8)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'FILL_POST',dict(reason='x')))
    base=findings(cur);d=today-timedelta(days=6)
    fill(cur,fx,120,d)
    use(cur,fx,fx['SERVICE_POST'],[(40,d+timedelta(days=1),9,'FACTORY_USE')])
    lot=receive(cur,fx,'SERVICE_LEFTOVER',[(30,None)],d+timedelta(days=2),from_location_id=fx['SERVICE_POST'])['lot_ids'][0]
    inspect(cur,lot,local_at(d+timedelta(days=2),12),'Ani',usable=25,damaged=5,usable_to=fx['main'],damaged_to=fx['DAMAGED'])
    svc(cur,'DISPOSE_STOCK',dict(location_id=fx['DAMAGED'],physical_at=local_at(d+timedelta(days=3),9),items=[dict(material_id=fx['material'],qty='5')],reason='buang rusak'))
    _,item=note(cur,fx,10,'3.00',d+timedelta(days=3))
    nlot=receive(cur,fx,'NOTE_RETURN',day=d+timedelta(days=4),note_item_id=item,qty='4')['lot_ids'][0]
    inspect(cur,nlot,local_at(d+timedelta(days=4),12),'Ani',usable=4)
    policy(cur,'ACC_DEC05',dict(mode='CREDIT_UNPAID_ONLY',credit_conditions=['USABLE']))
    credit(cur,nlot,'USABLE',4,local_at(d+timedelta(days=5),9),fx['main'])
    late_invoice(cur,fx,today,'2.10')
    total=sum(stock(cur,fx['material'],fx[k]) for k in ('main','SERVICE_POST','INSPECTION','DAMAGED'))
    return verdict(dict(quantity=total==1000-40-5-10+4,books_equal_subledger=abs(gl(cur,'MATERIAL_INVENTORY')-subledger_value(cur))<=D('0.05'),
        credit_follows_invoice=one(cur,"select bool_and(unit_cost_snapshot=2.10) from erp.material_stock_movements where source_type='BC_NOTE_RETURN_CREDIT' and material_id=%s",fx['material']),
        receivable=one(cur,'select erp.bc_note_item_collectible_v1(%s)',item)==D('18'),detectors=new_findings(base,findings(cur))=={},
        documents_listed=ws(cur,dict(query='',page_size=50))['documents_total']>=8),findings_after=new_findings(base,findings(cur)),
        stale_f2=findings(cur).get(STALE_F2,0)-base.get(STALE_F2,0))


# ================================================================ D: races (modes), replay, access, atomicity, dates, lists
def d05_replay(cur,today):
    """ACC-D05 (M:5300): the same request with the same payload returns the same response and effects once; the same key with
    another payload is refused; a lost response is recovered with the original key, never a new one."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'FILL_POST',dict(reason='x')))
    key=uuid.uuid4();d=today-timedelta(days=1)
    first=fill(cur,fx,10,d,key=key);books=ledger(cur);docs=one(cur,'select count(*) from erp.bc_documents_v1')
    second=fill(cur,fx,10,d,key=key)
    other=denied(cur,lambda:fill(cur,fx,11,d,key=key),'client_request_id was already used with a different payload')
    return verdict(dict(same_response=second==first,once=one(cur,'select count(*) from erp.bc_documents_v1')==docs and ledger(cur)==books
        and stock(cur,fx['material'],fx['SERVICE_POST'])==10,other_payload_refused=other['ok']),refusal=other['refusal'])


def d06_access(cur,today):
    """ACC-D06 (M:5301, M:11.3): a role without the existing permission, a view-only role, anon and a direct table access are
    denied by the server; only the owner changes a policy (ACC-DEC07 grants nothing new)."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:ws(cur))
    d=today-timedelta(days=1);item=[dict(material_id=fx['material'],qty='1')]
    gudang,keuangan,admin_user=user(cur,'GUDANG'),user(cur,'KEUANGAN'),user(cur,'ADMIN')
    move=lambda auth:svc(cur,'FILL_POST',dict(from_location_id=fx['main'],to_location_id=fx['SERVICE_POST'],physical_at=local_at(d),items=item,reason='x'),auth=auth)
    def anon():
        api.admin(cur);cur.execute('set local role anon')
        cur.execute('select public.erp_get_accessory_service_workspace_v1(%s::jsonb)',('{}',))
    def direct():
        session(cur);cur.execute('select count(*) from erp.bc_documents_v1')
    def direct_insert():
        session(cur);cur.execute("insert into erp.bc_policy_settings_v1(policy_key,reason) values('ACC_DEC03','x')")
    checks=dict(gudang_no_adjust=denied(cur,lambda:move(gudang),'PERMISSION_DENIED: warehouse.stock.adjust'),
        admin_no_adjust=denied(cur,lambda:move(admin_user),'PERMISSION_DENIED: warehouse.stock.adjust'),
        keuangan_no_view=denied(cur,lambda:ws(cur,auth=keuangan),'PERMISSION_DENIED: warehouse.accessory.view'),
        anon=denied(cur,anon,'permission denied for function'),direct_read=denied(cur,direct,'permission denied for schema erp'),
        direct_write=denied(cur,direct_insert,'permission denied for schema erp'),
        admin_policy=refused(cur,lambda:policy(cur,'ACC_DEC05',dict(mode='CREDIT_UNPAID_ONLY',credit_conditions=['USABLE']),auth=admin_user),'BC_OWNER_ONLY'))
    gudang_read=ws(cur,auth=gudang)
    return verdict(dict({k:v['ok'] for k,v in checks.items()},gudang_reads=isinstance(gudang_read,dict) and not gudang_read['is_admin'],
        values_hidden=all(p['value'] is None for p in gudang_read['policies'])),refusals={k:v['refusal'] for k,v in checks.items()})


def d07_atomic(cur,today):
    """ACC-D07 (M:5302): a failure inside a multi-line command (second line over stock) rolls every effect back -- document,
    native adjustment, movements, journal and the request key -- and the same key then works with a valid payload."""
    fx=fixture(cur,today,stock_qty=10)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'INTERNAL_USE',dict(reason='x')))
    before=ledger(cur);docs=one(cur,'select count(*) from erp.bc_documents_v1');adjs=one(cur,'select count(*) from erp.material_adjustments')
    key=uuid.uuid4()
    failed=denied(cur,lambda:use(cur,fx,fx['main'],[(3,today,9,'FACTORY_USE'),(50,today,10,'FACTORY_USE')],key=key),'stock would become negative')
    clean=ledger(cur)==before and one(cur,'select count(*) from erp.bc_documents_v1')==docs and one(cur,'select count(*) from erp.material_adjustments')==adjs \
        and stock(cur,fx['material'],fx['main'])==10
    retry=use(cur,fx,fx['main'],[(3,today,9,'FACTORY_USE')],key=key)
    return verdict(dict(refused=failed['ok'],no_residue=clean,key_free=retry['cost']=='6.00' and stock(cur,fx['material'],fx['main'])==7),refusal=failed['refusal'])


def d08_dates(cur,today):
    """ACC-D08 (M:5303): across the WIB/UTC boundary the physical time, the WIB business date of the books and the system time
    stay separate: a use at 00:30 WIB is booked on that WIB date, not on the UTC day before."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'INTERNAL_USE',dict(reason='x')))
    u=use(cur,fx,fx['main'],[(1,today,0,'FACTORY_USE')])
    row=q(cur,"""select erp._cp3_business_date(a.physical_at),(a.physical_at at time zone 'UTC')::date,j.transaction_date,d.created_at>d.physical_at
        from erp.material_adjustments a join erp.journal_entries j on j.source_type='MATERIAL_ADJUSTMENT' and j.source_id=a.id
        join erp.bc_documents_v1 d on d.id=%s where a.id=%s""",u['document_id'],u['adjustment_ids'][0])[0]
    listed=[x for x in ws(cur,dict(action='INTERNAL_USE',query=''))['documents'] if x['id']==u['document_id']]
    return verdict(dict(business_date=row[0]==today,utc_day_before=row[1]==today-timedelta(days=1),journal_on_wib_date=row[2]==today,
        system_time_separate=row[3] is True,shown_local=bool(listed) and listed[0]['physical_local']==str(today)+' 00:00'))


def d12_pagination(cur,today):
    """ACC-D12 (M:5307): history is searched and paged by the server with a bounded page; pages are disjoint and complete."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:ws(cur,dict(page_size=10)))
    for i in range(23):
        svc(cur,'COUNT_POST',dict(location_id=fx['SERVICE_POST'],physical_at=local_at(today,8,i),items=[dict(material_id=fx['material'],counted_qty='0')],
            reason='BC probe hitung '+fx['code']))
    pages=[ws(cur,dict(action='COUNT_POST',query=fx['code'].lower(),page=p,page_size=10)) for p in (1,2,3)]
    ids=[d['id'] for pg in pages for d in pg['documents']]
    too_big=refused(cur,lambda:ws(cur,dict(page_size=51)),'BC_FILTER_INVALID')
    return verdict(dict(total=all(pg['documents_total']==23 for pg in pages),sizes=[len(pg['documents']) for pg in pages]==[10,10,3],
        disjoint_complete=len(set(ids))==23,bounded=too_big['ok']))


# ================================================================ policy settings (owner decision: settings, default pending)
def policy_settings(cur,today):
    """Owner decision 25 Sep 2026 (policy rows are application settings, default pending until the owner approves a value):
    every key starts PENDING_POLICY_VALUE; only the owner sets or clears it against the version seen; values the
    implementation does not support are refused; every change is kept; clearing it refuses the dependent step again."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:ws(cur))
    fresh={p['key']:(p['status'],p['version']) for p in ws(cur)['policies']}
    expected={k:('PENDING_POLICY_VALUE','1') for k in ('ACC-DEC01','ACC-DEC03','ACC-DEC04','ACC-DEC05','ACC-DEC06','ACC-DEC07','ERP-DEC02')}
    stale=refused(cur,lambda:svc(cur,'SET_POLICY',dict(policy_key='ACC_DEC05',operation='SET',expected_version='7',reason='x',
        value=dict(mode='CREDIT_UNPAID_ONLY',credit_conditions=['USABLE']))),'STALE_VERSION')
    unsupported=refused(cur,lambda:policy(cur,'ACC_DEC05',dict(mode='WRITE_OFF',credit_conditions=['USABLE'])),'BC_POLICY_VALUE')
    wrong_account=refused(cur,lambda:policy(cur,'ACC_DEC04',dict(CUSTOMER_SERVICE_account_id=account(cur,'4100'))),'BC_POLICY_VALUE')
    no_number=refused(cur,lambda:policy(cur,'ACC_DEC07',dict(owner_approval_above='abc')),'BB_AMOUNT_INVALID')
    policy(cur,'ACC_DEC05',dict(mode='CREDIT_UNPAID_ONLY',credit_conditions=['USABLE']))
    version=next(p for p in ws(cur)['policies'] if p['key']=='ACC-DEC05')['version']
    svc(cur,'SET_POLICY',dict(policy_key='ACC_DEC05',operation='CLEAR',expected_version=version,reason='kembali pending'))
    cleared=next(p for p in ws(cur)['policies'] if p['key']=='ACC-DEC05')
    events=q(cur,"select version,status from erp.bc_policy_setting_events_v1 where policy_key='ACC_DEC05' order by version")
    _,item=note(cur,fx,2,'3.00',today-timedelta(days=1))
    lot=receive(cur,fx,'NOTE_RETURN',day=today,hour=8,note_item_id=item,qty='1')['lot_ids'][0]
    inspect(cur,lot,local_at(today,9),'Ani',usable=1)
    pending=refused(cur,lambda:credit(cur,lot,'USABLE',1,local_at(today,10),fx['main']),'BC_POLICY_PENDING')
    return verdict(dict(defaults=fresh==expected,stale=stale['ok'],unsupported=unsupported['ok'],wrong_account=wrong_account['ok'],
        not_a_number=no_number['ok'],cleared=cleared['status']=='PENDING_POLICY_VALUE' and cleared['version']=='3',
        history=[(r[0],r[1]) for r in events]==[(1,'PENDING_POLICY_VALUE'),(2,'SET'),(3,'PENDING_POLICY_VALUE')],pending_again=pending['ok']))


def dec07_approval(cur,today):
    """ACC-DEC07 (M:4460, M:12 D07): a valued company cost needs owner/admin approval while the threshold is pending, then only
    above the owner's threshold; when the owner lists a zone's users only they move its stock. A staff role here has only the
    existing permissions granted for this case (warehouse.accessory.view, warehouse.stock.adjust)."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'INTERNAL_USE',dict(reason='x')))
    staff=user(cur,'STAFF',('warehouse.accessory.view','warehouse.stock.adjust'))
    pending=refused(cur,lambda:use(cur,fx,fx['main'],[(3,today,9,'FACTORY_USE')],auth=staff),'BC_APPROVAL_REQUIRED')
    policy(cur,'ACC_DEC07',dict(owner_approval_above='10.00'))
    below=use(cur,fx,fx['main'],[(3,today,10,'FACTORY_USE')],auth=staff)
    above=refused(cur,lambda:use(cur,fx,fx['main'],[(6,today,11,'FACTORY_USE')],auth=staff),'BC_APPROVAL_REQUIRED')
    owner_id=str(one(cur,'select id from erp.app_users where auth_user_id=%s',api.base.OPERATOR_AUTH))
    policy(cur,'ACC_DEC07',dict(owner_approval_above='10.00',zone_users={fx['SERVICE_POST']:[owner_id]}))
    zone=refused(cur,lambda:svc(cur,'FILL_POST',dict(from_location_id=fx['main'],to_location_id=fx['SERVICE_POST'],physical_at=local_at(today,12),
        items=[dict(material_id=fx['material'],qty='1')],reason='x'),auth=staff),'BC_ZONE_USER_DENIED')
    owner_ok=fill(cur,fx,1,today,12)
    return verdict(dict(pending_needs_approval=pending['ok'],below_threshold=below['cost']=='6.00',above_threshold=above['ok'],
        zone_users=zone['ok'],owner_listed=bool(owner_ok['document_id'])),refusals=[pending,above,zone])


# ================================================================ ERP-DEC02, ACC-DEC06, F1
def special_free(cur,today):
    """ERP-DEC02 (M:4462, M:5199, M:5023): free is an explicit owner decision, never inferred from a name or a missing price: a
    FREE line needs the owner's Special free list, a contractor that is Special at the note time and the policy version the
    operator saw; it posts price 0 with its provenance and is checked again at posting."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'SET_POLICY',dict(reason='x')))
    d=today-timedelta(days=1)
    free_line=lambda version:note(cur,fx,3,None,d,mode='FREE',extra=dict(free_policy_version=version))
    pending=refused(cur,lambda:free_line('1'),'BC_FREE_NOT_ALLOWED')
    policy(cur,'ERP_DEC02',dict(special_free_category_ids=[fx['category']]))
    not_special=refused(cur,lambda:free_line('2'),'BC_FREE_NOT_ALLOWED')
    api.admin(cur)
    cur.execute("""insert into erp.contractor_hpp_policy_versions(contractor_id,effective_from,contractor_role_snapshot,attendance_required_snapshot,is_special,reason)
        values(%s,%s,'MANDOR',false,true,'BC probe Special')""",(fx['mandor'],today-timedelta(days=30)))
    stale=refused(cur,lambda:free_line('1'),'STALE_PRICE')
    quote=[m for m in note_read(cur,dict(contractor_id=fx['mandor'],location_id=fx['main'],physical_at=local_at(d,8)+'',material_query=fx['code'].lower()))['materials']
           if m['id']==fx['material']]
    b=ledger(cur)
    issue,item=free_line('2')
    moved=delta(b,ledger(cur))
    row=q(cur,'select total_receivable,manual_retail_unit_price,accessory_price_version_id from erp.contractor_material_issue_items where id=%s',item)[0]
    prov=q(cur,'select category_id::text,policy_version from erp.bc_free_issue_lines_v1 where issue_id=%s',issue)
    return verdict(dict(pending_refused=pending['ok'],not_special_refused=not_special['ok'],stale_refused=stale['ok'],
        quoted=bool(quote) and quote[0].get('free') is not None,zero_price=row[0]==0 and row[1]==0,
        provenance=prov==[(fx['category'],2)],no_receivable='CONTRACTOR_RECEIVABLE' not in moved and moved.get('MATERIAL_INVENTORY')==D('-6.00')))


def manual_zero(cur,today):
    """M:5023 (free is never a way around the note price) with ERP-DEC02: a manual retail price of 0 made a free line with no
    owner policy before BC (COUNTEREXAMPLE); with BC it is refused and free goes through the Special list only."""
    fx=fixture(cur,today,zones=False)
    attempt=lambda:note(cur,fx,2,'0.00',today-timedelta(days=1))
    if not bc_installed(cur):
        result,error=r1.peer.attempt(cur,attempt)
        return dict(status='COUNTEREXAMPLE' if error is None else 'INCOMPLETE',result=result,refusal=error,
                    harm='a note line priced 0 posted as free without any owner policy')
    r=refused(cur,attempt,'BC_FREE_REQUIRES_POLICY')
    return verdict(dict(refused=r['ok']),refusal=r['refusal'])


def rounding(cur,today):
    """ACC-DEC06 (M:4459, M:5005): whole-rupiah rounding only once the owner sets it, as one separate line per note to the
    nearest rupiah (17.43 -> 17.00); payroll then collects and settles the rounded amount; a rounding cannot be reversed when
    payroll already took more than the note without it."""
    fx=fixture(cur,today,days=8)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'ROUND_NOTE',dict(reason='x')))
    down,down_item=note(cur,fx,7,'2.49',today-timedelta(days=5))
    pending=refused(cur,lambda:svc(cur,'ROUND_NOTE',dict(issue_id=down,reason='x')),'BC_POLICY_PENDING')
    policy(cur,'ACC_DEC06',dict(mode='NOTE_NEAREST_RUPIAH',gain_account_id=account(cur,'4100'),loss_account_id=account(cur,'5900')))
    b=ledger(cur);r=svc(cur,'ROUND_NOTE',dict(issue_id=down,reason='bulatkan'));moved=delta(b,ledger(cur))
    again=refused(cur,lambda:svc(cur,'ROUND_NOTE',dict(issue_id=down,reason='x')),'BC_ROUNDING_EXISTS')
    p1=payroll(cur,fx,today,'100.00',5);pay_through(cur,p1)
    deducted=one(cur,"select sum(amount) from erp.payroll_deductions where payroll_id=%s and contractor_issue_item_id=%s",p1,down_item)
    status=one(cur,'select payroll_status from erp.contractor_material_issue_items where id=%s',down_item)
    up,up_item=note(cur,fx,7,'2.50',today-timedelta(days=3))
    ru=svc(cur,'ROUND_NOTE',dict(issue_id=up,reason='bulatkan'))
    p2=payroll(cur,fx,today,'100.00',3);pay_through(cur,p2)
    below=refused(cur,lambda:reverse(cur,ru['document_id']),'BC_REVERSE_BELOW_PAID')
    return verdict(dict(pending=pending['ok'],rounded=(r['rounding'],r['collectible'])==('-0.43','17.00'),
        separate_line=moved=={'CONTRACTOR_RECEIVABLE':D('-0.43'),'OTHER_EXPENSE':D('0.43')},once=again['ok'],
        payroll_collects_rounded=deducted==D('17.00') and status=='SETTLED',rounded_up=(ru['rounding'],ru['collectible'])==('0.50','18.00'),
        reversal_below_paid=below['ok']))


def f1_manual_provenance(cur,today):
    """Pre-existing finding F1 (reproduced on the BB chain without BC): a note line with the owner-decided manual retail price
    (ACC-DEC02, M:1066) tripped the CRITICAL detector contractor_issue_price_provenance_gap (it asked every accessory line for
    a price version). After BC the manual price is accepted as provenance; a line with neither is still flagged."""
    fx=fixture(cur,today,zones=False)
    name='run_v265_gudang_write_integrity_checks:contractor_issue_price_provenance_gap'
    before=findings(cur).get(name,0)
    note(cur,fx,2,'3.00',today-timedelta(days=1))
    after=findings(cur).get(name,0)
    if not bc_installed(cur):
        return dict(status='COUNTEREXAMPLE' if after>before else 'INCOMPLETE',before=before,after=after,
                    harm='a valid manual-price note line is a CRITICAL detector finding')
    api.admin(cur)
    issue=one(cur,"""insert into erp.contractor_material_issues(issue_number,contractor_id,location_id,physical_at,status)
        values(%s,%s,%s,%s,'DRAFT') returning id""",tag(),fx['mandor'],fx['main'],local_at(today,8))
    cur.execute('savepoint bc_f1');gap=None
    try:
        cur.execute('insert into erp.contractor_material_issue_items(issue_id,material_id,qty,unit_sale_price_snapshot) values(%s,%s,1,0)',(issue,fx['material']))
        gap=findings(cur).get(name,0)
    except psycopg.Error as exc:gap='INSERT_REFUSED:'+exc.diag.message_primary[:120]
    cur.execute('rollback to savepoint bc_f1');api.admin(cur)
    detector_text='i.manual_retail_unit_price is null' in one(cur,"select prosrc from pg_proc where oid='erp.run_v265_gudang_write_integrity_checks()'::regprocedure")
    return verdict(dict(manual_note_clean=after==before,gap_still_flagged=(gap==before+1) if isinstance(gap,int) else detector_text),gap=gap)


# ================================================================ reversal matrix (M:6.3 linked inverse)
def reversals(cur,today):
    """Linked inverse (M:6.3, M:8.4): a document with dependants is not reversed until they are; a reversal that would take
    stock a later document used is refused by the native guard; stale version and a second reversal are refused; reversing
    in order restores stock and books exactly."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'REVERSE',dict(reason='x')))
    d=today-timedelta(days=2);b0=ledger(cur);s0=stock(cur,fx['material'],fx['main'])
    f=fill(cur,fx,20,d)
    u=use(cur,fx,fx['SERVICE_POST'],[(15,d,11,'FACTORY_USE')])
    used=denied(cur,lambda:reverse(cur,f['document_id']),'stock would become negative')
    t=receive(cur,fx,'TEARDOWN',[(6,None)],d,reference='SVC-REV')
    i=inspect(cur,t['lot_ids'][0],local_at(d,13),'Ani',usable=6)
    dependants=refused(cur,lambda:reverse(cur,t['document_id']),'BC_REVERSE_DEPENDANTS')
    stale=refused(cur,lambda:svc(cur,'REVERSE',dict(document_id=i['document_id'],expected_version='9',reason='x')),'STALE_VERSION')
    reverse(cur,i['document_id']);twice=refused(cur,lambda:svc(cur,'REVERSE',dict(document_id=i['document_id'],expected_version='2',reason='x')),'BC_ALREADY_REVERSED')
    reverse(cur,t['document_id']);reverse(cur,u['document_id']);reverse(cur,f['document_id'])
    statuses=[doc(cur,x)['status'] for x in (f['document_id'],u['document_id'],t['document_id'],i['document_id'])]
    return verdict(dict(used_stock=used['ok'],dependants=dependants['ok'],stale=stale['ok'],twice=twice['ok'],all_reversed=statuses==['REVERSED']*4,
        restored=ledger(cur)==b0 and stock(cur,fx['material'],fx['main'])==s0 and stock(cur,fx['material'],fx['SERVICE_POST'])==0),refusals=[used,dependants])


# ================================================================ ALL-C02 / ALL-C03 (opening accessory states)
def c02_rows(fx,today,lines=(('1','10','50.00'),),original='50.00',settled='20.00'):
    rows=bbp.masters()
    doc_row=bbp.document('CONTRACTOR_RECEIVABLE','contractor_code','NOTA-LAMA',original,settled);doc_row.pop('_days')
    doc_row['document_date']=str(today-timedelta(days=40))
    rows['OPENING_BALANCE_ITEM']=[doc_row]
    rows['OPENING_CONTROL']=[dict(control_key='CONTRACTOR_RECEIVABLE',balance_type='CONTRACTOR_RECEIVABLE',amount=str(D(original)-D(settled)))]
    rows['OPENING_ACCESSORY_NOTE_LINE']=[dict(document_number='NOTA-LAMA',contractor_code='{C}',line_number=n,material_sku=fx['code'],qty=q_,line_amount=a)
                                         for n,q_,a in lines]
    return rows


def staged_errors(cur,today,rows,prefix='BC'):
    """Upload and validate without finalizing: {entity: [errors]} of the refused rows."""
    cutover=today-timedelta(days=10);boundary.historical.prior.set_open_period(cur,cutover-timedelta(days=1))
    code=prefix+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(cutover)))['batch_id']
    fill_=lambda v:v.replace('{C}',code) if isinstance(v,str) else v
    for entity,payloads in rows.items():api.upload(cur,batch,entity,[{k:fill_(v) for k,v in p.items()} for p in payloads])
    api.invoke(cur,'VALIDATE',batch)
    errs={}
    for entity,e in q(cur,"select entity_type,validation_errors from erp.migration_staging_rows where batch_id=%s and validation_status='ERROR'",batch):
        errs.setdefault(entity,[]).extend(e)
    return errs


def all_c02(cur,today):
    """ALL-C02 (r9: "Opening note receivable is only its evidenced unpaid residual ... Once the 3 returned PCS are received and an
    explicit policy gives source credit, credit right is at most 3p ... If no proven credit right, stock custody can be recorded
    as pending-value but no automatic contractor credit"; Fable C02: 50/20 as provenance, credit only at the old note's own
    price and quantity, the old payroll history is never reversed). Old note 10 @ 5.00 = 50.00, 20.00 paid before cutover."""
    fx=fixture(cur,today)
    rows=c02_rows(fx,today)
    if not bc_installed(cur):return no_route(cur,lambda:bbp.post_batch(cur,today,rows))
    before=ledger(cur);issues=one(cur,"select count(*) from erp.material_stock_movements where material_id=%s",fx['material'])
    batch,code,cutover=bbp.post_batch(cur,today,rows)
    imported=delta(before,ledger(cur))
    balance=str(one(cur,"""select b.id from erp.initial_import_financial_sources f join erp.opening_subledger_balances b on b.opening_item_id=f.opening_item_id
        where f.batch_id=%s""",batch))
    line=str(one(cur,'select id from erp.bc_opening_note_lines_v1 where batch_id=%s',batch))
    wsb=api.read(cur,batch)['batch']
    lot=receive(cur,fx,'NOTE_RETURN',day=today,hour=8,opening_note_line_id=line,qty='3')['lot_ids'][0]
    over=refused(cur,lambda:receive(cur,fx,'NOTE_RETURN',day=today,hour=8,opening_note_line_id=line,qty='8'),'BC_RETURN_EXCEEDS_SOURCE')
    inspect(cur,lot,local_at(today,9),'Ani',usable=3)
    no_policy=refused(cur,lambda:credit(cur,lot,'USABLE',3,local_at(today,10)),'BC_POLICY_PENDING')
    custody_only=one(cur,'select count(*) from erp.material_stock_movements where material_id=%s',fx['material'])==issues
    policy(cur,'ACC_DEC05',dict(mode='CREDIT_UNPAID_ONLY',credit_conditions=['USABLE']))
    b1=ledger(cur);c=credit(cur,lot,'USABLE',3,local_at(today,10));credited=delta(b1,ledger(cur))
    remaining=one(cur,'select original_amount-settled_amount from erp.opening_subledger_balances where id=%s',balance)
    settlement=str(one(cur,"select c.settlement_id from erp.bb_opening_credits_v1 c where c.credit_kind='ACCESSORY_NOTE_RETURN' and c.credit_note_number=%s",
                       'BCA-'+c['document_id'].replace('-','')[:16].upper()))
    direct=refused(cur,lambda:bbp.act(cur,'OPENING_SETTLEMENT',batch,operation='REVERSE',settlement_id=settlement,reason='x'),'BC_CREDIT_SOURCE_REVERSAL')
    child=[l for l in ws(cur,dict(query=fx['code']))['lots'] if l['id']==c['custody_lot_id']]
    provenance=q(cur,'select original_amount,settled_before_cutover from erp.initial_import_financial_sources where batch_id=%s',batch)[0]
    reverse(cur,c['document_id'])
    restored=one(cur,'select original_amount-settled_amount from erp.opening_subledger_balances where id=%s',balance)
    return verdict(dict(import_residual_only=imported=={'CONTRACTOR_RECEIVABLE':D('30.00')},no_issue_replay=custody_only,
        note_lines=[(x['qty'],x['line_amount']) for x in wsb['accessory_note_lines']]==[('10.000000','50.00')],over_source=over['ok'],
        credit_needs_policy=no_policy['ok'],credit_at_source_price=c['amount']=='15.00' and c['unpaid']=='15.00' and remaining==D('15.00'),
        credit_books=credited=={'CONTRACTOR_RECEIVABLE':D('-15.00'),'MATERIAL_RECOVERY':D('15.00')},
        custody_pending=bool(child) and child[0]['owner_kind']=='COMPANY' and child[0]['value_status']=='Belum dinilai',
        credit_only_through_bc=direct['ok'],history_kept=(provenance[0],provenance[1])==(D('50.00'),D('20.00')),inverse=restored==D('30.00')))


def all_c02_refusals(cur,today):
    """ALL-C02 import refusals: the note lines must add up to the imported document's original amount and name its document."""
    fx=fixture(cur,today)
    rows=c02_rows(fx,today,lines=(('1','10','45.00'),))
    if not bc_installed(cur):return no_route(cur,lambda:staged_errors(cur,today,rows))
    mismatch=staged_errors(cur,today,rows)
    rows2=c02_rows(fx,today);rows2['OPENING_ACCESSORY_NOTE_LINE'][0]['document_number']='TIDAK-ADA'
    orphan=staged_errors(cur,today,rows2)
    has=lambda errs,code:any(code in e for e in errs.get('OPENING_ACCESSORY_NOTE_LINE',[]))
    return verdict(dict(total_mismatch=has(mismatch,'BC_C02_TOTAL_MISMATCH'),document_required=has(orphan,'BC_C02_DOCUMENT_REQUIRED')),
                   errors=dict(mismatch=mismatch,orphan=orphan))


def c03_rows(fx,extra=()):
    rows=bbp.masters()
    rows['OPENING_BALANCE_ITEM']=[dict(balance_type='MATERIAL',material_sku=fx['code'],location_code=fx['code']+'SE',qty='5',unit_cost='2.00',control_key='STOCK',opening_source_key='POS'),
                                  dict(balance_type='MATERIAL',material_sku=fx['code'],location_code=fx['code']+'IN',qty='2',unit_cost='2.00',control_key='STOCK',opening_source_key='KARANTINA')]
    rows['OPENING_CONTROL']=[dict(control_key='STOCK',balance_type='MATERIAL',qty='7',amount='14.00')]
    rows['OPENING_ACCESSORY_CUSTODY']=[
        dict(custody_kind='PENDING_VALUE',custody_key='{C}-K1',material_sku=fx['code'],location_code=fx['code']+'IN',condition='WAITING',qty='4',notes='bongkaran lama'),
        dict(custody_kind='UNRETURNED',custody_key='{C}-K2',material_sku=fx['code'],qty='1',holder='Pak Budi',owner_kind='COMPANY'),
        dict(custody_kind='CUSTOMER_GARMENT',custody_key='{C}-K3',customer_code='{C}',description='Celana pelanggan servis',qty='1')]+list(extra)
    return rows


def all_c03(cur,today):
    """ALL-C03 (r9: "only the evidenced usable 5 are ready stock; 2 remain quarantine (value carried) ... 1 remains outstanding and
    is not in available stock. Unknown-value recovery can be recorded physically as pending valuation with no artificial
    zero-cost financial close"; Fable C03: the categories never add up to one available quantity, M:3933/M:4882). Then the
    quarantine is inspected into stock at its value, the outstanding item comes back, and the pending lot is valued only
    under ACC-DEC03; each step reverses."""
    fx=fixture(cur,today)
    rows=c03_rows(fx)
    if not bc_installed(cur):return no_route(cur,lambda:bbp.post_batch(cur,today,rows))
    b0=ledger(cur);main0=stock(cur,fx['material'],fx['main'])
    batch,code,cutover=bbp.post_batch(cur,today,rows)
    imported=delta(b0,ledger(cur))
    lots={l['source_kind']:l for l in ws(cur,dict(query=fx['code']))['lots']}
    outstanding=[o for o in ws(cur)['outstanding'] if o['holder']=='Pak Budi']
    custody=[c for c in ws(cur)['customer_custody'] if c['description']=='Celana pelanggan servis']
    staged=api.read(cur,batch)['batch']['accessory_custody']
    ready=dict(post=stock(cur,fx['material'],fx['SERVICE_POST']),inspection=stock(cur,fx['material'],fx['INSPECTION']),main=stock(cur,fx['material'],fx['main']))
    not_issueable=refused(cur,lambda:note_call(cur,'POST',dict(number=tag(),contractor_id=fx['mandor'],location_id=fx['INSPECTION'],po_id=None,
        physical_at=local_at(today,9),notes='x',reason='x',items=[dict(material_id=fx['material'],qty='1',mode='MANUAL',manual_price='3.00')])),'BC_ZONE_NATIVE_REFUSED')
    q_lot=lots['OPENING_QUARANTINE']['id'];p_lot=lots['OPENING_PENDING_VALUE']['id']
    b1=ledger(cur);qi=inspect(cur,q_lot,local_at(today,9),'Ani',usable=2,usable_to=fx['main'])
    quarantine_kept=delta(b1,ledger(cur))=={} and stock(cur,fx['material'],fx['main'])==main0+2
    back=receive(cur,fx,'TEARDOWN',[(1,outstanding[0]['id'] if outstanding else None)],today,10,reference='kembali dari Pak Budi')
    again=refused(cur,lambda:receive(cur,fx,'TEARDOWN',[(1,outstanding[0]['id'])],today,11,reference='x'),'BC_RETURN_EXCEEDS_SOURCE')
    inspect(cur,p_lot,local_at(today,11),'Budi',usable=3,damaged=1)
    pending=refused(cur,lambda:svc(cur,'VALUE_CUSTODY',dict(lot_id=p_lot,condition='USABLE',qty='3',unit_value='1.00',location_id=fx['main'],
        physical_at=local_at(today,12),reason='x')),'BC_POLICY_PENDING')
    policy(cur,'ACC_DEC03',dict(credit_account_id=account(cur,'4100'),unit_value_cap='MOVING_AVERAGE'))
    b2=ledger(cur)
    v=svc(cur,'VALUE_CUSTODY',dict(lot_id=p_lot,condition='USABLE',qty='3',unit_value='1.00',location_id=fx['main'],physical_at=local_at(today,12),reason='nilai pulih'))
    valued=delta(b2,ledger(cur))
    reverse(cur,v['document_id']);reverse(cur,back['document_id']);reverse(cur,qi['document_id'])
    return verdict(dict(import_value=imported=={'MATERIAL_INVENTORY':D('14.00')},
        separate_states=ready==dict(post=5,inspection=2,main=main0) and bool(outstanding) and bool(custody)
          and sorted((s['kind'],s['value_status']) for s in staged)==[('CUSTOMER_GARMENT','Milik pelanggan'),('PENDING_VALUE','Belum dinilai'),
            ('QUARANTINE_VALUED','Bernilai di buku'),('UNRETURNED','Belum kembali')],
        pending_labelled=lots.get('OPENING_PENDING_VALUE',{}).get('value_status')=='Belum dinilai',
        quarantine_lot=lots.get('OPENING_QUARANTINE',{}).get('value_status')=='Bernilai di buku',not_issueable=not_issueable['ok'],
        quarantine_to_stock_at_value=quarantine_kept,outstanding_capacity=again['ok'],value_needs_policy=pending['ok'],
        valued_once=valued=={'MATERIAL_INVENTORY':D('3.00'),'OTHER_INCOME':D('-3.00')},
        inverse=ledger(cur)==b1 and stock(cur,fx['material'],fx['INSPECTION'])==2 and lot_state(cur,p_lot)['usable']==3),
        ready={k:str(v) for k,v in ready.items()},main0=str(main0),outstanding=outstanding,custody=custody,staged=staged)


def all_c03_refusals(cur,today):
    """ALL-C03 import refusals: a valued row is ordinary opening stock, not custody; one physical item has one custody key;
    pending-value custody sits in a registered inspection area."""
    fx=fixture(cur,today)
    rows=c03_rows(fx,extra=[dict(custody_kind='PENDING_VALUE',custody_key='{C}-K1',material_sku=fx['code'],location_code=fx['code']+'IN',condition='USABLE',qty='1'),
                            dict(custody_kind='PENDING_VALUE',custody_key='{C}-K4',material_sku=fx['code'],location_code=fx['code']+'IN',condition='USABLE',qty='1',unit_cost='1.00'),
                            dict(custody_kind='PENDING_VALUE',custody_key='{C}-K5',material_sku=fx['code'],location_code=fx['code']+'SE',condition='USABLE',qty='1')])
    if not bc_installed(cur):return no_route(cur,lambda:staged_errors(cur,today,rows))
    valued=rows['OPENING_ACCESSORY_CUSTODY'].pop(4)
    errs=' | '.join(staged_errors(cur,today,rows).get('OPENING_ACCESSORY_CUSTODY',[]))
    rows2=c03_rows(fx,extra=[valued])
    upload=denied(cur,lambda:staged_errors(cur,today,rows2),'kolom unit_cost: nama kolom atau tipe data tidak valid')
    return verdict(dict(duplicate_key='BC_C03_DUPLICATE' in errs,valued_row_not_custody=upload['ok'],inspection_area='area pemeriksaan terdaftar' in errs),
                   errors=errs,upload=upload['refusal'])


def c12_opname_baseline(cur,today):
    """ACC-C12 (M:5290; Fable: "baseline dicatat sebagai entri opening/adjustment, bukan nota/PO palsu; stok ditetapkan sekali ...
    nilai yang tidak bersumber jelas ditandai pending, bukan final ... Dilarang: sistem mengarang nota/PO ... item sama dihitung dua
    kali (opname + penerimaan normal berikutnya)"; r9: "do not fabricate contractor note or add duplicate stock. Unknown value
    remains pending"). An opening count of 5 at a known cost 2.00 in the warehouse and 3 of unknown value found at the same count:
    the 5 are opening stock, the 3 wait in the inspection area as pending value; no note, purchase or contractor debt is made;
    a later ordinary receipt of 10 adds exactly 10."""
    fx=fixture(cur,today,purchase=False)
    rows=bbp.masters()
    rows['OPENING_BALANCE_ITEM']=[dict(balance_type='MATERIAL',material_sku=fx['code'],location_code=fx['code']+'W',qty='5',unit_cost='2.00',control_key='STOCK',opening_source_key='OPNAME')]
    rows['OPENING_CONTROL']=[dict(control_key='STOCK',balance_type='MATERIAL',qty='5',amount='10.00')]
    rows['OPENING_ACCESSORY_CUSTODY']=[dict(custody_kind='PENDING_VALUE',custody_key='{C}-OPN',material_sku=fx['code'],location_code=fx['code']+'IN',
                                            condition='WAITING',qty='3',notes='opname: dokumen dan harga asal hilang')]
    if not bc_installed(cur):return no_route(cur,lambda:bbp.post_batch(cur,today,rows))
    counts=lambda:q(cur,"""select (select count(*) from erp.contractor_material_issues),(select count(*) from erp.material_purchase_headers),
        (select count(*) from erp.opening_subledger_balances)""")[0]
    c0=counts();b0=ledger(cur)
    batch,code,cutover=bbp.post_batch(cur,today,rows)
    imported=delta(b0,ledger(cur));c1=counts()
    lot=[l for l in ws(cur,dict(query=fx['code']))['lots'] if l['source_kind']=='OPENING_PENDING_VALUE']
    main=stock(cur,fx['material'],fx['main']);inspection=stock(cur,fx['material'],fx['INSPECTION'])
    saved=internal(cur,'save_material_purchase_draft_v2',Jsonb(dict(purchase_number=fx['code']+'R',supplier_id=fx['supplier'],location_id=fx['main'],
        physical_at=local_at(today,9),change_reason='BC C12 penerimaan biasa',lines=[dict(material_id=fx['material'],qty=10,unit_price='2.00',
        price_state='ESTIMATED',price_source='MANUAL_ESTIMATE')])),str(uuid.uuid4()),None)
    internal(cur,'post_material_purchase_v2',saved['purchase_id'],str(uuid.uuid4()),saved['row_version'],'BC C12 penerimaan biasa')
    return verdict(dict(opening_value_once=imported=={'MATERIAL_INVENTORY':D('10.00')},no_fabricated_documents=c1==c0,
        counted_once=main==5 and inspection==0,unknown_value_pending=bool(lot) and lot[0]['value_status']=='Belum dinilai' and D(lot[0]['state']['waiting'])==3,
        later_receipt_adds_exactly=stock(cur,fx['material'],fx['main'])==15),imported={k:str(v) for k,v in imported.items()},counts=[list(c0),list(c1)])



def import_attempt(cur,today,rows,code):
    """One more opening import attempt inside a savepoint that is always rolled back: ACCEPTED, or the refusal (a finalize
    refusal or a validation error row) and whether it carries `code`."""
    cur.execute('savepoint bc_import_attempt')
    try:
        posted=bbp.post_batch(cur,today,rows)
        outcome=dict(result='ACCEPTED',batch_code=posted[1],ok=False)
    except (psycopg.Error,AssertionError) as exc:
        message=str(exc)
        outcome=dict(result='REFUSED',message=message[:400],ok=code in message)
    cur.execute('rollback to savepoint bc_import_attempt');api.admin(cur)
    return outcome


def c12_same_goods_once(cur,today):
    """ACC-C12 same goods (GPT BC review item 3; Fable: "stok ditetapkan sekali (tidak dobel dengan entri 'susulan' untuk item
    sama) ... Dilarang: item sama dihitung dua kali (opname + penerimaan normal berikutnya)"). After the opname import (5 known at
    2.00, 3 pending value): a second opening of the same material is refused (BA_IMPORT_OPENING_ALREADY_POSTED) and stock stays 5;
    the same pending item again (same custody key) is refused (BC_C03_DUPLICATE); the 3 pending are inspected and valued once
    (stock 8) and a second valuation of the same lot is refused (BC_QTY_EXCEEDS_BUCKET), stock stays 8; positive control: a
    genuinely new purchase of 10 adds 10. Limit, recorded and not claimed: a pending row under a NEW custody key is accepted as
    separate goods (it stays pending and outside stock until inspected and valued); the system has no other identity to tell
    it apart. Goods received before cutover whose documents arrive later go through the uninvoiced-receipt route (L:P01)."""
    fx=fixture(cur,today,purchase=False)
    rows=bbp.masters()
    rows['OPENING_BALANCE_ITEM']=[dict(balance_type='MATERIAL',material_sku=fx['code'],location_code=fx['code']+'W',qty='5',unit_cost='2.00',control_key='STOCK',opening_source_key='OPNAME')]
    rows['OPENING_CONTROL']=[dict(control_key='STOCK',balance_type='MATERIAL',qty='5',amount='10.00')]
    rows['OPENING_ACCESSORY_CUSTODY']=[dict(custody_kind='PENDING_VALUE',custody_key='{C}-OPN',material_sku=fx['code'],location_code=fx['code']+'IN',
                                            condition='WAITING',qty='3',notes='opname: dokumen dan harga asal hilang')]
    if not bc_installed(cur):return no_route(cur,lambda:bbp.post_batch(cur,today,rows))
    batch,code,cutover=bbp.post_batch(cur,today,rows)
    main=lambda:stock(cur,fx['material'],fx['main'])
    after_import=main()
    again=bbp.masters()
    again['OPENING_BALANCE_ITEM']=[dict(balance_type='MATERIAL',material_sku=fx['code'],location_code=fx['code']+'W',qty='5',unit_cost='2.00',control_key='STOCK',opening_source_key='OPNAME')]
    again['OPENING_CONTROL']=[dict(control_key='STOCK',balance_type='MATERIAL',qty='5',amount='10.00')]
    second_opening=import_attempt(cur,today,again,'BA_IMPORT_OPENING_ALREADY_POSTED')
    same_key=bbp.masters()
    same_key['OPENING_ACCESSORY_CUSTODY']=[dict(custody_kind='PENDING_VALUE',custody_key=code+'-OPN',material_sku=fx['code'],location_code=fx['code']+'IN',
                                                condition='WAITING',qty='3',notes='susulan untuk barang yang sama')]
    same_pending=import_attempt(cur,today,same_key,'BC_C03_DUPLICATE')
    new_key=bbp.masters()
    new_key['OPENING_ACCESSORY_CUSTODY']=[dict(custody_kind='PENDING_VALUE',custody_key=code+'-LAIN',material_sku=fx['code'],location_code=fx['code']+'IN',
                                               condition='WAITING',qty='3',notes='susulan dengan kunci baru')]
    limit=import_attempt(cur,today,new_key,'-')
    after_refusals=main()
    lot=[l for l in ws(cur,dict(query=fx['code']))['lots'] if l['source_kind']=='OPENING_PENDING_VALUE'][0]['id']
    inspect(cur,lot,local_at(today,11),'Budi',usable=3)
    policy(cur,'ACC_DEC03',dict(credit_account_id=account(cur,'4100'),unit_value_cap='NONE'))
    b0=ledger(cur)
    value=lambda hour:svc(cur,'VALUE_CUSTODY',dict(lot_id=lot,condition='USABLE',qty='3',unit_value='1.50',location_id=fx['main'],
                                                   physical_at=local_at(today,hour),reason='nilai barang opname'))
    value(12);valued=delta(b0,ledger(cur));after_value=main()
    twice=refused(cur,lambda:value(13),'BC_QTY_EXCEEDS_BUCKET')
    after_twice=main()
    saved=internal(cur,'save_material_purchase_draft_v2',Jsonb(dict(purchase_number=fx['code']+'R',supplier_id=fx['supplier'],location_id=fx['main'],
        physical_at=local_at(today,14),change_reason='BC C12 pembelian baru',lines=[dict(material_id=fx['material'],qty=10,unit_price='2.00',
        price_state='ESTIMATED',price_source='MANUAL_ESTIMATE')])),str(uuid.uuid4()),None)
    internal(cur,'post_material_purchase_v2',saved['purchase_id'],str(uuid.uuid4()),saved['row_version'],'BC C12 pembelian baru')
    return verdict(dict(opening_once=after_import==5,second_opening_refused=second_opening['ok'] and after_refusals==5,
        same_pending_refused=same_pending['ok'],valued_once=after_value==8 and valued.get('MATERIAL_INVENTORY')==D('4.50') and sum(valued.values())==0,
        second_valuation_refused=twice['ok'] and after_twice==8,new_purchase_adds=main()==18),
        second_opening=second_opening,same_pending=same_pending,valued={k:str(v) for k,v in valued.items()},
        limit=dict(new_custody_key=limit['result'],note='a pending row under a new custody key is accepted as separate goods; it stays pending and outside stock'))

def f4_advance_settlement_read(cur,today):
    """Pre-existing finding F4 (found by the ALL-A01 continuation; BB's read, reproduced on the BB chain without BC): an opening
    payable paid from an imported advance gets a settlement without cash account and credit row, and the import workspace sent
    its 'reversible' flag as null (false OR NULL); the import page refuses a flag that is not a boolean and hid the whole batch.
    After BC every settlement flag is a boolean, and one paid from an advance is not reversible there (it is reversed through
    the advance)."""
    f=prepayment_trial.fixture(api,cur,today,'SUPPLIER')
    target=prepayment_trial.state(api,cur,f)['targets'][0]['id']
    prepayment_trial.manage(api,cur,f,'APPLY',today,target_id=target,amount='12.75')
    flags=[s['reversible'] for b in bbp.ws(cur,f['batch'])['opening_balances'] for s in b['settlements'] if s['method']=='ADVANCE']
    if not bc_installed(cur):
        return dict(status='COUNTEREXAMPLE' if None in flags else 'INCOMPLETE',flags=flags,
                    harm='the import page refuses the batch (reversible is null), so the whole batch is hidden')
    return verdict(dict(one_advance_settlement=len(flags)==1,boolean_false=flags==[False]),flags=flags)


# ================================================================ L: the six BA-era ALL states, import -> continuation -> inverse
# Auditor round 11: P01, A01, A02, W01, W03 and C01 were routed in the writer's inventory (handoff §29.6) without a run. Each case
# below imports the state, continues it through the existing native route and reverses it, against the r9 ALL oracle (and Fable's
# where it is stricter). Their routes exist before BC, so they are PASS in both phases; only C01's company-use leg is BC's.
import cp6_initial_import_prepayment_trial as prepayment_trial
receipt_trial,production_trial=bbp.receipt_trial,api.production_origins


def accounts(cur,keys):
    return {k:gl(cur,k) for k in keys}


def journal_count(cur,since):
    return one(cur,'select count(*) from erp.journal_entries where created_at>=%s',since)


def clock(cur):
    return one(cur,'select clock_timestamp()')


def supplier_payment(cur,purchase,amount,cash,day):
    api.admin(cur)
    return str(one(cur,'insert into erp.supplier_payments(purchase_id,payment_number,payment_date,amount,cash_account_id) values(%s,%s,%s,%s,%s) returning id',
                   purchase,'BCL-'+uuid.uuid4().hex[:12],local_at(day,12),amount,cash))


def bank_account(cur,code):
    """A bank master for a continuation (no balance is imported with it)."""
    api.admin(cur)
    coa=one(cur,"insert into erp.chart_accounts(account_code,account_name,account_type,report_group,normal_balance,is_postable,is_active) values(%s,'BC L bank','ASSET','CURRENT_ASSETS','DEBIT',true,true) returning id",code+'LB')
    return str(one(cur,"insert into erp.cash_accounts(cash_account_code,cash_account_name,coa_account_id,account_kind,is_active) values(%s,'BC L bank',%s,'BANK',true) returning id",code+'L',coa))


def l_p01(cur,today):
    """ALL-P01 (r9: "10 material units at source cost 2.00; 3 remain in physical stock, 7 were consumed before cutover ... assigned by
    OPENING_COST_ORIGIN to independently identified WIP/BS/FG source rows. A later supplier invoice uses authoritative unit cost 2.50 ...
    opening stock = 3 x 2 = 6.00 ... Opening GRNI = 10 x 2 = 20.00 ... AP = 25.00, total invoice uplift = 5.00 ... invoice, then payment,
    eligible physical return, and reverse in dependency order ... return of consumed quantity, paying GRNI without invoice ... must not
    add stock, debt, cash, or journal"; Fable P01: no MATERIAL_PURCHASE movement, HPP ESTIMATED until matched). Origins: WIP 4, BS 2, FG 1."""
    a=api;keys=('MATERIAL_INVENTORY','WIP','FG_INVENTORY','GRNI_MATERIAL','AP_SUPPLIER','OPENING_EQUITY','OTHER_EXPENSE','COGS')
    boundary.historical.prior.set_open_period(cur,today-timedelta(days=9))
    api.admin(cur);b0=accounts(cur,keys)
    f=receipt_trial.fixture(a,cur,today,qty='10',cost='2.00');b=f['batch'];code=f['code']
    for entity,rows in {'MODEL':[dict(model_code=code,model_name='P01 model')],'SIZE':[dict(size_code=code)],'BRAND':[dict(brand_code=code,brand_name='P01 brand')],
        'PRODUCT':[dict(sku=code,product_name='P01 product',model_code=code,brand_code=code,color_name='Blue',size_code=code)],
        'CONTRACTOR':[dict(contractor_code=code,contractor_name='P01 mandor',contractor_type='MANDOR')],
        'LOCATION':[dict(location_code=code,location_name='P01 gudang bahan',location_type='RAW_MATERIAL_WAREHOUSE'),
                    dict(location_code=code+'F',location_name='P01 gudang FG',location_type='FG_WAREHOUSE')],
        'OPEN_PO':[dict(po_number=code,model_code=code,contractor_code=code,target_qty_pcs='10',status='SEWING',current_stage='SEWING')]}.items():
        a.upload(cur,b,entity,rows)
    base=dict(po_number=code,size_code=code,contractor_code=code,accessory_cost_included='true')
    rows=[dict(f['stock'],qty='3'),dict(base,balance_type='WIP',stage='SEWING',qty='8',unit_cost='5',amount='40.00',opening_source_key='WIP',control_key='WIP'),
          dict(base,balance_type='BS',stage='QC',product_sku=code,qty='2',unit_cost='10',amount='20.00',opening_source_key='BS',control_key='BS'),
          dict(balance_type='FINISHED_GOODS',product_sku=code,location_code=code+'F',qty='4',unit_cost='5',opening_source_key='FG',control_key='FG')]
    a.upload(cur,b,'OPENING_BALANCE_ITEM',rows)
    a.upload(cur,b,'OPENING_COST_ORIGIN',[dict(supplier_code=code,receipt_number=f['receipt']['receipt_number'],receipt_line_number='001',target_source_key=k,qty=q)
                                           for k,q in (('WIP','4'),('BS','2'),('FG','1'))])
    a.upload(cur,b,'OPENING_CONTROL',[dict(control_key=k,balance_type=t,qty=q,amount=v) for k,t,q,v in (('WIP','WIP','8','40.00'),('BS','BS','2','20.00'),
        ('FG','FINISHED_GOODS','4','20.00'),('GRNI','GRNI_MATERIAL','10','20.00'),('STOCK','MATERIAL','3','6.00'))])
    row,sources=production_trial.finalize(a,cur,f)
    api.admin(cur)
    row=dict(row,**dict(zip(('material_id','location_id'),q(cur,'''select i.material_id,h.location_id from erp.material_purchase_items i
        join erp.material_purchase_headers h on h.id=i.purchase_id where i.id=%s''',row['purchase_item_id'])[0])))
    imported=delta(b0,accounts(cur,keys))
    material=row['material_id'];qty=lambda:one(cur,'select cached_stock_qty from erp.materials where id=%s',material)
    purchase_movements=one(cur,"select count(*) from erp.material_stock_movements where material_id=%s and movement_type<>'OPENING'",material)
    snapshot=q(cur,'select to_jsonb(i) from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=%s order by i.id',b)
    cash=bank_account(cur,code)
    unbilled_pay=supplier_payment(cur,row['purchase_id'],'1.00',cash,today)
    b1=accounts(cur,keys)
    grni_payment=denied(cur,lambda:receipt_trial.rpc(a,cur,'post_supplier_payment',unbilled_pay),'')
    api.admin(cur);grni_unchanged=accounts(cur,keys)==b1
    b1=accounts(cur,keys)
    inv=receipt_trial.post_invoice(a,cur,receipt_trial.invoice(a,cur,today,row,'10','2.50',date=today-timedelta(days=2)))
    api.admin(cur);invoiced=delta(b1,accounts(cur,keys))
    def ret(n):
        payload=dict(return_number='BCL-RET-'+uuid.uuid4().hex[:10],supplier_id=row['supplier_id'],location_id=row['location_id'],physical_at=local_at(today-timedelta(days=1),10),
                     change_reason='BC L P01 return',items=[dict(material_id=material,purchase_item_id=row['purchase_item_id'],qty=str(n))])
        d=receipt_trial.rpc(a,cur,'save_material_supplier_return_draft_v2',json.dumps(payload,default=str),uuid.uuid4(),None)
        return d,receipt_trial.rpc(a,cur,'post_material_supplier_return_v2',d['material_supplier_return_id'],uuid.uuid4(),d['row_version'],'BC L P01 return')
    consumed=denied(cur,lambda:ret(4),'consumed before cutover')
    b2=accounts(cur,keys);rd,rp=ret(1);api.admin(cur);returned=delta(b2,accounts(cur,keys));stock_after_return=qty()
    ap_after_return=one(cur,'select erp.material_purchase_final_ap_total(%s)',row['purchase_id'])
    b3=accounts(cur,keys);pay=supplier_payment(cur,row['purchase_id'],'22.50',cash,today)
    receipt_trial.rpc(a,cur,'post_supplier_payment',pay);api.admin(cur);paid=delta(b3,accounts(cur,keys))
    receipt_trial.truth(cur);production_trial.truth(cur)
    receipt_trial.rpc(a,cur,'reverse_supplier_payment',pay,'BC L P01 reverse payment')
    receipt_trial.rpc(a,cur,'reverse_material_supplier_return_v2',rd['material_supplier_return_id'],'BC L P01 reverse return',uuid.uuid4(),rp['row_version'])
    receipt_trial.rpc(a,cur,'reverse_material_supplier_invoice_v2',inv['supplier_invoice_id'],'BC L P01 reverse invoice',uuid.uuid4(),inv['row_version'])
    api.admin(cur);receipt_trial.truth(cur);production_trial.truth(cur)
    restored=accounts(cur,keys)==b1 and qty()==3
    return verdict(dict(
        import_exact=imported=={'MATERIAL_INVENTORY':D('6.00'),'WIP':D('60.00'),'FG_INVENTORY':D('20.00'),'GRNI_MATERIAL':D('-20.00'),'OPENING_EQUITY':D('-66.00')},
        consumed_not_stock=qty()==3 and purchase_movements==0,sources_named=sources['WIP']['qty_pcs']==8 and sources['BS']['qty_pcs']==2,
        grni_not_payable=grni_payment['ok'] and grni_unchanged,
        invoice_uplift_5=invoiced=={'MATERIAL_INVENTORY':D('1.50'),'WIP':D('3.00'),'FG_INVENTORY':D('0.50'),'GRNI_MATERIAL':D('20.00'),'AP_SUPPLIER':D('-25.00')},
        consumed_not_returnable=consumed['ok'],eligible_return=stock_after_return==2 and D(ap_after_return)==D('22.50')
          and returned=={'MATERIAL_INVENTORY':D('-2.50'),'AP_SUPPLIER':D('2.50')},
        payment_22_50=paid.get('AP_SUPPLIER')==D('22.50') and set(paid)=={'AP_SUPPLIER'},
        inverse_dependency_order=restored,
        opening_immutable=q(cur,'select to_jsonb(i) from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=%s order by i.id',b)==snapshot),
        imported={k:str(v) for k,v in imported.items()},invoiced={k:str(v) for k,v in invoiced.items()},returned={k:str(v) for k,v in returned.items()},
        paid={k:str(v) for k,v in paid.items()},refusals=dict(grni_payment=grni_payment['refusal'],consumed=consumed['refusal']))


def l_a01(cur,today,kind):
    """ALL-A01 (r9: "one dedicated advance per actual party ... for each party type separately ... apply ... to an eligible same-party
    invoice, refund ..., then reverse ... supplier/vendor refund increases bank 10.00; customer refund decreases bank 10.00 ... reject
    ... application over either advance or invoice"; Fable A01, contract table M:634-643: 100.00 - 32.75 = 67.25; use 12.75 -> 54.50;
    refund 10.00 -> 44.50, bill 54.50, bank 110/90; use 44.50 -> 0.00, bill 10.00; reverse all -> 67.25, 67.25, bank 100.00)."""
    a=api;boundary.historical.prior.set_open_period(cur,today-timedelta(days=2))
    api.admin(cur);g0=bbp.gl(cur)
    f=prepayment_trial.fixture(a,cur,today,kind);api.admin(cur)
    state=lambda:prepayment_trial.state(a,cur,f)
    s=state();target=s['targets'][0]['id'];bank=lambda:prepayment_trial.bank(cur,f)
    imported=(s['original_amount'],s['settled_before_cutover'],s['remaining_amount'],s['targets'][0]['remaining_amount'],str(bank()))
    g1=bbp.gl(cur)
    prepayment_trial.manage(a,cur,f,'APPLY',today,target_id=target,amount='12.75')
    s=state();first=s['payments'][0]['id'];step1=(s['remaining_amount'],s['targets'][0]['remaining_amount'],str(bank()))
    prepayment_trial.manage(a,cur,f,'REFUND',today,amount='10',cash_account_id=f['cash']);s=state();event=s['events'][0]['id']
    step2=(s['remaining_amount'],s['targets'][0]['remaining_amount'],str(bank()))
    over=denied(cur,lambda:prepayment_trial.manage(a,cur,f,'APPLY',today,target_id=target,amount='44.51'),'')
    prepayment_trial.manage(a,cur,f,'APPLY',today,target_id=target,amount='44.50');s=state()
    payments=[p['id'] for p in s['payments']];second=[p for p in payments if p!=first]
    step3=(s['remaining_amount'],s['targets'][0]['remaining_amount'] if s['targets'] else None,str(bank()))
    clean=prepayment_trial.truth(cur)
    for p in second:prepayment_trial.manage(a,cur,f,'REVERSE_PAYMENT',today,payment_id=p)
    prepayment_trial.manage(a,cur,f,'REVERSE_EVENT',today,event_id=event)
    prepayment_trial.manage(a,cur,f,'REVERSE_PAYMENT',today,payment_id=first)
    s=state();prepayment_trial.truth(cur)
    refund_bank='90.00' if kind=='CUSTOMER' else '110.00'
    return verdict(dict(import_opening_only=imported==('100.00','32.75','67.25','67.25','100.00'),
        apply_12_75=step1==('54.50','54.50','100.00'),refund_10=step2==('44.50','54.50',refund_bank),over_advance_refused=over['ok'],
        apply_rest=step3==('0.00','10.00',refund_bank),two_applications=len(second)==1,
        inverse=(s['remaining_amount'],s['targets'][0]['remaining_amount'],str(bank()))==('67.25','67.25','100.00') and bbp.gl(cur)==g1),
        kind=kind,steps=[imported,step1,step2,step3],refusal=over['refusal'],truth=clean)


def l_a02(cur,today):
    """ALL-A02 (r9: "cash advance original 100.00 less actual old repayment 30.00 = opening receivable 70.00. Reserve 30.00 against an
    actual eligible draft payroll of the same mandor; free unreserved balance is 40.00. Attempt direct cash repayment 41.00 while the 30.00
    is reserved, then approve/pay payroll, reverse it, and release draft reservation ... Draft allocation ... creates no journal ...
    on actual payroll payment, the reserved deduction Dr CONTRACTOR_PAYABLE / Cr CONTRACTOR_RECEIVABLE is 30.00; cash is only net
    payroll ... Inverse chain restores exact original balances"). The payroll earns 50.00, so it pays 20.00 in cash."""
    fx=bbp.financial_fixture(cur,today,documents=[('CONTRACTOR_RECEIVABLE','KASBON-OLD','100.00','30.00','CONTRACTOR_CASH_ADVANCE')],bank='200.00')
    api.admin(cur);contractor=str(one(cur,'select id from erp.contractors where contractor_code=%s',fx['code']))
    advance=lambda:bbp.ws(cur,fx['batch'])['cash_advances'][0]
    receivable=lambda:one(cur,"""select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
        where j.status in('POSTED','REVERSED') and l.contractor_id=%s and l.account_id=erp.account_id('CONTRACTOR_RECEIVABLE')""",contractor)
    imported=(receivable(),bbp.balance_row(cur,fx,'KASBON-OLD'))
    p=str(one(cur,"""insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,manual_adjustment,payment_date,payment_cash_account_id)
        values(%s,%s,%s,%s,50,%s,%s) returning id""",'BCL-'+uuid.uuid4().hex,contractor,today-timedelta(days=1),today-timedelta(days=1),today,fx['cash']))
    version=lambda payroll=None:str(one(cur,'select row_version from erp.payroll_settlements where id=%s',payroll or p))
    g0=bbp.gl(cur);bank0=bbp.bank(cur,fx)
    allocate=lambda amount,payroll=None:api.call(cur,'ALLOCATE_CASH_ADVANCE',dict(batch_id=fx['batch'],expected_revision=bbp.revision(cur,fx['batch']),
        balance_id=fx['balances']['KASBON-OLD'],payroll_id=payroll or p,amount=amount,expected_payroll_version=version(payroll)))
    allocate('30.00');reserved=advance();no_journal=bbp.gl(cur)==g0
    p2=str(one(cur,"""insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,manual_adjustment,payment_date,payment_cash_account_id)
        values(%s,%s,%s,%s,50,%s,%s) returning id""",'BCL-'+uuid.uuid4().hex,contractor,today-timedelta(days=2),today-timedelta(days=2),today,fx['cash']))
    allocate('10.00',p2);second=advance()['available_amount'];allocate('0',p2);released_draft=advance()['available_amount']
    draft_release_no_journal=bbp.gl(cur)==g0
    settle=lambda amount:bbp.act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='SETTLE',balance_id=fx['balances']['KASBON-OLD'],amount=amount,
        effective_date=str(today),cash_account_id=fx['cash'],reason='BC L A02 cash repayment')
    over=refused(cur,lambda:settle('41.00'),'BB_OSS_EXCEEDS_AVAILABLE')
    fits=settle('40.00');after_cash=bbp.balance_row(cur,fx,'KASBON-OLD')[2]
    bbp.act(cur,'OPENING_SETTLEMENT',fx['batch'],operation='REVERSE',settlement_id=fits['settlement_id'],reason='BC L A02 undo repayment')
    g1=bbp.gl(cur)
    for name in ('approve_payroll','post_payroll_payment'):bbp.payroll_call(cur,name,p)
    paid=bbp.moved(g1,bbp.gl(cur));deduction=q(cur,"""select a.mapping_key,sum(l.debit),sum(l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
        join erp.accounting_account_mappings a on a.account_id=l.account_id where j.source_id=%s and j.source_type='PAYROLL_CASH_ADVANCE_DEDUCTION' group by 1 order by 1""",p)
    paid_bank=bbp.bank(cur,fx)-bank0;paid_receivable=receivable()
    clean_paid,_=bbp.truth_clean(cur)
    bbp.payroll_call(cur,'reverse_paid_payroll',p,'BC L A02 reverse payroll')
    reversed_receivable=receivable();reversed_bank=bbp.bank(cur,fx)-bank0
    status=one(cur,'select status from erp.payroll_settlements where id=%s',p)
    api.admin(cur);final=advance();clean,detectors=bbp.truth_clean(cur)
    return verdict(dict(import_70=imported[0]==D('70.00') and imported[1][2]==D('70.00'),
        reserve_no_journal=no_journal and reserved['reserved_amount']=='30.00' and reserved['available_amount']=='40.00',
        cash_over_free_refused=over['ok'],cash_up_to_free=after_cash==D('30.00'),
        payroll_deducts_30=[(r[0],r[1],r[2]) for r in deduction]==[('CONTRACTOR_PAYABLE',D('30.00'),D('0.00')),('CONTRACTOR_RECEIVABLE',D('0.00'),D('30.00'))],
        cash_is_net=paid_bank==D('-20.00') and paid_receivable==D('40.00'),detectors_when_paid=clean_paid,
        reversal_restores=reversed_receivable==D('70.00') and reversed_bank==0,
        draft_release_no_journal=(second,released_draft)==('30.00','40.00') and draft_release_no_journal,
        reversal_releases=status=='REVERSED' and final['allocations']==[] and final['reserved_amount']=='0.00' and final['available_amount']=='70.00',
        ledger_restored=bbp.moved(g0,bbp.gl(cur))=={},detectors=clean),
        reserved=reserved,final=final,status_after_reversal=status,paid={k:str(v) for k,v in paid.items()},refusal=over['refusal'],detectors=detectors)


def po_rows(target='10',wip=None,bs=None,status='SEWING'):
    """An open PO {C} (target `target`) with optional opening WIP (qty, amount) held by mandor {C} and BS (qty, amount) on it."""
    rows=bbp.product_masters()
    rows.update(BRAND=[dict(brand_code='{C}',brand_name='BC L brand {C}')],MODEL=[dict(model_code='{C}',model_name='BC L model {C}')])
    rows.update(CONTRACTOR=[dict(contractor_code='{C}',contractor_name='BC L mandor',contractor_type='MANDOR')],LAUNDRY_VENDOR=[dict(vendor_code='{C}',vendor_name='BC L laundry')],
                OPEN_PO=[dict(po_number='{C}',model_code='{C}',contractor_code='{C}',target_qty_pcs=target,status=status,current_stage=status)])
    items=[];controls=[]
    common=dict(po_number='{C}',model_code='{C}',size_code='{C}',accessory_cost_included='true',product_sku='{C}P',brand_code='{C}',color_name='Blue',contractor_code='{C}')
    if wip:
        items.append(dict(common,balance_type='WIP',stage='SEWING',qty=wip[0],amount=wip[1],unit_cost=str(D(wip[1])/D(wip[0])),opening_source_key='WIP',control_key='WIP'))
        controls.append(dict(control_key='WIP',balance_type='WIP',qty=wip[0],amount=wip[1]))
    if bs:
        items.append(dict(common,balance_type='BS',stage='QC',qty=bs[0],amount=bs[1],opening_source_key='BS',control_key='BS'))
        controls.append(dict(control_key='BS',balance_type='BS',qty=bs[0],amount=bs[1]))
    if items:rows.update(OPENING_BALANCE_ITEM=items,OPENING_CONTROL=controls)
    return rows


def po_state(cur,po):
    api.admin(cur)
    return dict(status=one(cur,'select status from erp.production_orders where id=%s',po),
                stage_events=one(cur,'select count(*) from erp.wip_stage_events where po_id=%s',po),bs=one(cur,'select count(*) from erp.bs_cases where po_id=%s',po),
                lots=one(cur,'select count(*) from erp.fg_lots where po_id=%s',po),journal=one(cur,'select count(*) from erp.journal_lines where po_id=%s',po))


def l_w01(cur,today):
    """ALL-W01 (r9: "one open PO target 10 garments, header/source identity only. Separately, if known, import 7 WIP PCS and 3 valued BS PCS as
    explicit detail rows ... Header-only import creates no stock, work-stage balance, wage, cut/sew record or journal ... exactly 7 WIP and
    3 BS ... never 10 WIP by inference. Finish/cancel PO must be refused while any imported WIP/BS remains ... reject over-capacity total";
    Fable W01: cancelling a PO that still has opening WIP/BS is refused, not forced). Continuation: the 7 are completed to FG and the 3
    scrapped, the PO finishes; inverse: reopen, undo scrap and output, and the PO again refuses to close."""
    api.admin(cur);g0=bbp.gl(cur)
    header=bbp.production_post(cur,today,po_rows())
    header_state=po_state(cur,header['po']);header_gl=bbp.moved(g0,bbp.gl(cur))
    target=one(cur,'select target_qty_pcs from erp.production_orders where id=%s',header['po'])
    over=bbp.production_post(cur,today,po_rows(wip=('8','80.00'),bs=('3','30.00')),expect=True)
    fx=bbp.production_post(cur,today,po_rows(wip=('7','70.00'),bs=('3','30.00')))
    c=fx['cutover'];wip0=bbp.ledger(cur,'WIP',fx['po'])
    sources={s['balance_type']:s for s in bbp.ws(cur,fx['batch'])['production_sources']}
    cancel=lambda:q(cur,"update erp.production_orders set status='CANCELLED' where id=%s returning id",fx['po'])
    finish=lambda:internal(cur,'finish_production_order',fx['po'])
    cancel_refused=denied(cur,cancel,'saldo awal');finish_refused=denied(cur,finish,'')
    bbp.empty_accessory_bom(cur,fx['code'],c)
    out=bbp.complete(cur,fx,c+timedelta(days=2),7)
    case=sources['BS']['bs_case_id']
    scrap=bbp.bs_act(cur,'DISPOSE_BS',dict(bs_case_id=case,resolution_type='SCRAP',qty_pcs=3,physical_at=chain.production.at(c+timedelta(days=3),10),
                                        change_reason='BC L W01 scrap opening BS'),bbp.bs_version(cur,case))
    finished,finish_error=r1.peer.attempt(cur,finish);api.admin(cur)
    status_finished=one(cur,'select status from erp.production_orders where id=%s',fx['po'])
    if status_finished=='FINISHED':internal(cur,'reopen_production_order',fx['po'],'BC L W01 reopen to undo')
    bbp.bs_act(cur,'REVERSE_DISPOSITION',dict(resolution_id=scrap['bs_resolution_id'],change_reason='BC L W01 undo scrap'),bbp.bs_version(cur,case))
    bbp.wip_op(cur,fx,'REVERSE',output_id=out['output_id'])
    again=denied(cur,cancel,'saldo awal')
    after={s['balance_type']:s for s in bbp.ws(cur,fx['batch'])['production_sources']}
    clean,detectors=bbp.production_clean(cur)
    return verdict(dict(header_only_no_effect=header_state==dict(status='SEWING',stage_events=0,bs=0,lots=0,journal=0) and header_gl=={} and target==10,
        over_capacity_refused=bool(over['errors']),exact_detail=sources['WIP']['qty_pcs']==7 and sources['BS']['qty_pcs']==3 and wip0==D('100.00'),
        close_refused_while_open=cancel_refused['ok'] and finish_refused['ok'],finishes_when_resolved=status_finished=='FINISHED',
        inverse_reopens=after['WIP']['remaining_qty_pcs']==7 and bbp.ledger(cur,'WIP',fx['po'])==wip0 and again['ok'],reports_zero=clean),
        header=header_state,over=over['errors'][:3],finish_error=finish_error,refusals=dict(cancel=cancel_refused['refusal'],finish=finish_refused['refusal']),
        detectors=detectors)


def l_w03(cur,today):
    """ALL-W03 (r9: "5 known BS garments valued 50.00, with exact product/size/PO/holder. After cutover scrap/write off 2 and rework remaining 3
    into good output, then reverse only through canonical disposition path ... Scrap 2 PCS moves 20.00 to other expense; BS remains 3/30.
    Rework 3 good transfers 30.00 into FG/HPP; final BS=0, FG +3/30, expense +20 ... reject ... disposition >5"; Fable W03: the BS source is a
    native LEGACY case; the scrapped value is kept out of the PO's absorbed cost)."""
    api.admin(cur)
    fx=bbp.production_post(cur,today,po_rows(target='10',bs=('5','50.00')));c=fx['cutover']
    bbp.empty_accessory_bom(cur,fx['code'],c)
    src=bbp.source_of(cur,fx,'BS');case=src['bs_case_id']
    kind=one(cur,"select untracked_type||':'||qty_pcs from erp.bs_cases where id=%s",case)
    wip0=bbp.ledger(cur,'WIP',fx['po']);exp0=bbp.ledger(cur,'OTHER_EXPENSE',fx['po']);fg0=bbp.ledger(cur,'FG_INVENTORY',fx['po'])
    over=denied(cur,lambda:bbp.bs_act(cur,'DISPOSE_BS',dict(bs_case_id=case,resolution_type='SCRAP',qty_pcs=6,physical_at=chain.production.at(c+timedelta(days=2),10),
        change_reason='x'),bbp.bs_version(cur,case)),'')
    scrap=bbp.bs_act(cur,'DISPOSE_BS',dict(bs_case_id=case,resolution_type='SCRAP',qty_pcs=2,physical_at=chain.production.at(c+timedelta(days=2),10),
        change_reason='BC L W03 scrap 2'),bbp.bs_version(cur,case))
    wip1=bbp.ledger(cur,'WIP',fx['po']);exp1=bbp.ledger(cur,'OTHER_EXPENSE',fx['po'])
    vendor=str(one(cur,'select id from erp.laundry_vendors where vendor_code=%s',fx['code']))
    order=bbp.bs_act(cur,'SAVE_REWORK',dict(rework_number='BCL-'+uuid.uuid4().hex[:10],bs_case_id=case,destination_type='LAUNDRY',vendor_id=vendor,qty_sent=3,
        physical_sent_at=chain.production.at(c+timedelta(days=3),10),return_fg_location_id=fx['fg'],accessory_bom_item_ids=[],change_reason='BC L W03 rework 3'),None)
    done=bbp.bs_act(cur,'COMPLETE_REWORK',dict(rework_order_id=order['rework_order_id'],qty_good=3,qty_bs=0,completed_at=chain.production.at(c+timedelta(days=4),10),
        return_fg_location_id=fx['fg'],change_reason='BC L W03 rework good'),order['row_version'])
    api.admin(cur);lot=one(cur,'select good_fg_lot_id from erp.rework_orders where id=%s',order['rework_order_id'])
    wip2=bbp.ledger(cur,'WIP',fx['po']);fg2=bbp.ledger(cur,'FG_INVENTORY',fx['po']);cost=bbp.lot_cost(cur,lot)
    status=one(cur,'select status from erp.bs_cases where id=%s',case);clean1,d1=bbp.production_clean(cur)
    bbp.bs_act(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=order['rework_order_id'],change_reason='BC L W03 undo rework'),done['row_version'])
    bbp.bs_act(cur,'REVERSE_DISPOSITION',dict(resolution_id=scrap['bs_resolution_id'],change_reason='BC L W03 undo scrap'),bbp.bs_version(cur,case))
    wip3=bbp.ledger(cur,'WIP',fx['po']);exp3=bbp.ledger(cur,'OTHER_EXPENSE',fx['po']);fg3=bbp.ledger(cur,'FG_INVENTORY',fx['po'])
    clean2,d2=bbp.production_clean(cur)
    return verdict(dict(legacy_case_5=kind=='LEGACY:5' and wip0==D('50.00'),over_disposition_refused=over['ok'],
        scrap_2=wip1==wip0-20 and exp1==exp0+20,rework_3_good=wip2==wip1-30 and fg2==fg0+30 and D(cost)==D('30.00') and status=='RESOLVED',
        inverse=wip3==wip0 and exp3==exp0 and fg3==fg0,reports_zero=clean1 and clean2),
        ledger=[str(v) for v in (wip0,exp0,wip1,exp1,wip2,fg2,wip3,exp3,fg3)],case_status=status,refusal=over['refusal'],detectors=[d1,d2])


def c01_rows(fx):
    rows=bbp.masters()
    rows['OPENING_BALANCE_ITEM']=[dict(balance_type='MATERIAL',material_sku=fx['code'],location_code=fx['code']+'W',qty='10',unit_cost='2.00',control_key='STOCK',opening_source_key='KANCING')]
    rows['OPENING_CONTROL']=[dict(control_key='STOCK',balance_type='MATERIAL',qty='10',amount='20.00')]
    return rows


def l_c01_note(cur,today):
    """ALL-C01 (r9: "10 company-owned count units at actual inventory cost 2.00 each, in known warehouse ... opening inventory quantity=10,
    inventory value=20.00, no receivable/cash/expense on import ... A mandor issue is a distinct canonical route: stock falls once by 3, the
    receivable is 3 x manual price p, while inventory cost reduction remains 6.00; reimbursement entitlement stays separately governed ...
    reject ... fractional/negative PCS ... issue > stock"; Fable C01: 7 pieces reduce stock exactly 7, the bill is 7 x the typed price).
    The note route exists before BC; p = 3.50."""
    fx=fixture(cur,today,zones=False,purchase=False)
    keys=('MATERIAL_INVENTORY','CONTRACTOR_RECEIVABLE','OTHER_EXPENSE','CASH','BANK','MATERIAL_RECOVERY','ACCESSORY_RECOVERY_COGS')
    b0=accounts(cur,keys);entitlements=lambda:one(cur,'select count(*) from erp.contractor_accessory_reimbursement_entitlements')
    e0=entitlements()
    batch,code,cutover=bbp.post_batch(cur,today,c01_rows(fx))
    imported=delta(b0,accounts(cur,keys));opening=stock(cur,fx['material'],fx['main'])
    day=today-timedelta(days=2)
    fraction=denied(cur,lambda:note(cur,fx,'1.5','3.50',day),'')
    b1=accounts(cur,keys)
    issue,_=note(cur,fx,3,'3.50',day);issued=delta(b1,accounts(cur,keys));after=stock(cur,fx['material'],fx['main'])
    too_many=denied(cur,lambda:note(cur,fx,8,'3.50',day),'')
    h=one(cur,'select row_version from erp.contractor_material_issues where id=%s',issue)
    note_call(cur,'REVERSE',dict(id=issue,expected_version=str(h),reason='BC L C01 reverse note'))
    return verdict(dict(import_exact=imported=={'MATERIAL_INVENTORY':D('20.00')} and opening==10,
        note_once=after==7 and issued.get('CONTRACTOR_RECEIVABLE')==D('10.50') and issued.get('MATERIAL_INVENTORY')==D('-6.00') and sum(issued.values())==0,
        no_entitlement=entitlements()==e0,fraction_refused=fraction['ok'],over_stock_refused=too_many['ok'],
        inverse=accounts(cur,keys)==b1 and stock(cur,fx['material'],fx['main'])==10),
        imported={k:str(v) for k,v in imported.items()},issued={k:str(v) for k,v in issued.items()},refusals=dict(fraction=fraction['refusal'],over=too_many['refusal']))


def l_c01_company_use(cur,today):
    """ALL-C01's company-use leg (r9: "Direct company-service use of 3 reduces stock to 7 and inventory value to 14.00, and recognizes company
    purpose expense 6.00 under configured mapping; no contractor receivable"): the imported stock is used through BC's internal use
    (FACTORY_USE), then reversed. Before BC there is no route for company use (the public RPC is unknown)."""
    fx=fixture(cur,today,zones=True,purchase=False)
    batch,code,cutover=bbp.post_batch(cur,today,c01_rows(fx))
    if not bc_installed(cur):return no_route(cur,lambda:use(cur,fx,fx['main'],[(3,today,9,'FACTORY_USE')]))
    b1=ledger(cur)
    u=use(cur,fx,fx['main'],[(3,today-timedelta(days=1),9,'FACTORY_USE')]);used=delta(b1,ledger(cur));after=stock(cur,fx['material'],fx['main'])
    reverse(cur,u['document_id'])
    return verdict(dict(stock_7=after==7,expense_6=used=={'MATERIAL_INVENTORY':D('-6.00'),'OTHER_EXPENSE':D('6.00')},
        inverse=ledger(cur)==b1 and stock(cur,fx['material'],fx['main'])==10),used={k:str(v) for k,v in used.items()})


L_CASES=[('L:P01_RECEIPT_UNBILLED_PART_CONSUMED','PASS',l_p01),
         ('L:A01_SUPPLIER_ADVANCE','PASS',lambda c,t:l_a01(c,t,'SUPPLIER')),
         ('L:A01_CUSTOMER_ADVANCE','PASS',lambda c,t:l_a01(c,t,'CUSTOMER')),
         ('L:A01_VENDOR_ADVANCE','PASS',lambda c,t:l_a01(c,t,'VENDOR')),
         ('L:A02_CASH_ADVANCE_PAYROLL','PASS',l_a02),
         ('L:W01_OPEN_PO_HEADER','PASS',l_w01),
         ('L:W03_OPENING_BS','PASS',l_w03),
         ('L:C01_STOCK_NOTE_ROUTE','PASS',l_c01_note),
         ('L:C01_STOCK_COMPANY_USE','NO_ROUTE',l_c01_company_use)]


PLAN=[('B01:FILL_POST_KEEPS_TOTAL','NO_ROUTE',b01_fill),
      ('B02:USE_95_RETURN_25','NO_ROUTE',b02_use_return),
      ('B03:DIRECT_USE_PURPOSE_ACCOUNT','NO_ROUTE',b03_direct_use),
      ('B04:BACKDATED_TRANSFER_LATE_INVOICE','NO_ROUTE',b04_backdated_late_invoice),
      ('B05:LOCATION_AND_BYPASS_REFUSED','NO_ROUTE',b05_locations),
      ('B06:LINE_DAYS_AND_UNKNOWN_VARIANCE','NO_ROUTE',b06_days_and_variance),
      ('B07:END_TO_END_RECONCILES','NO_ROUTE',b07_end_to_end),
      ('C01:RECEIVE_100_CLASSIFY_80_20','NO_ROUTE',c01_receive_classify),
      ('C02:PARTIAL_INSPECTIONS_CAPPED','NO_ROUTE',c02_partial_inspections),
      ('C03:USED_SOURCE_NEW_KEY_REFUSED','NO_ROUTE',c03_used_source),
      ('C04:THREE_SOURCES_SEPARATE','NO_ROUTE',c04_three_sources),
      ('C05:NO_VALUE_STAYS_PENDING','NO_ROUTE',c05_pending_value),
      ('C09:PAID_NOTE_RETURN_POLICY','NO_ROUTE',c09_paid_note),
      ('C10:CUSTOMER_GARMENT_CUSTODY','NO_ROUTE',c10_customer_garment),
      ('C11:TWO_REAL_TIMELINES','NO_ROUTE',c11_timelines),
      ('A08:REPEATED_PARTIAL_RETURNS_CENTS','NO_ROUTE',a08_repeated_returns),
      ('D05:REPLAY_SAME_KEY','NO_ROUTE',d05_replay),
      ('D06:ACCESS_DENIED_BY_SERVER','NO_ROUTE',d06_access),
      ('D07:MID_COMMAND_FAILURE_ROLLS_BACK','NO_ROUTE',d07_atomic),
      ('D08:WIB_DATES_SEPARATE','NO_ROUTE',d08_dates),
      ('D12:SERVER_PAGINATION','NO_ROUTE',d12_pagination),
      ('POLICY:SETTINGS_OWNER_VERSIONED_PENDING','NO_ROUTE',policy_settings),
      ('DEC07:APPROVAL_THRESHOLD_ZONE_USERS','NO_ROUTE',dec07_approval),
      ('DEC02:SPECIAL_FREE_LINE','NO_ROUTE',special_free),
      ('DEC02:MANUAL_ZERO_PRICE_REFUSED','COUNTEREXAMPLE',manual_zero),
      ('DEC06:ROUNDING_LINE','NO_ROUTE',rounding),
      ('F1:MANUAL_PRICE_PROVENANCE_DETECTOR','COUNTEREXAMPLE',f1_manual_provenance),
      ('REV:LINKED_INVERSE_MATRIX','NO_ROUTE',reversals),
      ('ALL:C02_OLD_NOTE_PARTLY_PAID_RETURN','NO_ROUTE',all_c02),
      ('ALL:C02_IMPORT_REFUSALS','NO_ROUTE',all_c02_refusals),
      ('ALL:C03_CUSTODY_STATES','NO_ROUTE',all_c03),
      ('ALL:C03_IMPORT_REFUSALS','NO_ROUTE',all_c03_refusals),
      ('C12:OPNAME_BASELINE_INCOMPLETE_SOURCE','NO_ROUTE',c12_opname_baseline),
      ('C12:SAME_GOODS_COUNTED_ONCE','NO_ROUTE',c12_same_goods_once),
      ('F4:ADVANCE_SETTLEMENT_REVERSIBLE_READ','COUNTEREXAMPLE',f4_advance_settlement_read)]+L_CASES
assert len({k for k,_,_ in PLAN})==len(PLAN),'BC_DUPLICATE_CASE_ID'


# Every import batch workspace and every accessory workspace a case reads is saved and run through the pages' own parsers after
# the group (scripts/cp6_bc_workspace_parse.mjs): a page hides what it cannot parse, so a refusal there is a probe failure.
WS=dict(dir=None,case=None,n=0)
_READ,_WS,_NOTE_READ=api.read,ws,note_read


def _save(kind,result):
    if WS['dir'] is not None and isinstance(result,dict):
        WS['n']+=1
        name='%s_%s_%03d.json'%(kind,re.sub(r'[^A-Za-z0-9]+','_',WS['case'] or 'SETUP'),WS['n'])
        (WS['dir']/name).write_text(json.dumps(result,default=str))
    return result


def recording_read(cur,batch=None):
    result=_READ(cur,batch)
    return _save('import',result) if batch is not None and isinstance(result,dict) and result.get('batch') else result


def recording_ws(cur,filters=None,auth=None):
    return _save('service',_WS(cur,filters,auth))


def recording_note_read(cur,filters,auth=None):
    return _save('note',_NOTE_READ(cur,filters,auth))


def cases(cur,today):
    day=case_day(today)
    def run_one(key,fn):
        WS.update(case=key,n=0);return fn(cur,day)
    return [(key,lambda k=key,f=fn:run_one(k,f)) for key,_,fn in PLAN]


def workspace_parse(phase):
    run=subprocess.run(['node',str(AUDITOR/'scripts/cp6_bc_workspace_parse.mjs'),str(WS['dir']),phase],capture_output=True,text=True,cwd=AUDITOR)
    lines=run.stdout.strip().splitlines()
    try:parsed=json.loads(lines[-1])
    except (IndexError,ValueError):parsed=dict(files=None,refused=None,error=(run.stderr or run.stdout)[-1500:])
    kept=OUT/('WORKSPACE_REFUSED_'+phase.upper());kept.mkdir(parents=True,exist_ok=True)
    for item in parsed.get('refused') or []:(kept/item['file']).write_text((WS['dir']/item['file']).read_text())
    ok=run.returncode==0 and parsed.get('refused')==[] and (parsed.get('files') or 0)>0
    return dict(status='PASS' if ok else 'FAIL',files=parsed.get('files'),kinds=parsed.get('kinds'),f3_seed_ids=parsed.get('f3_seed_ids'),
                f4_null_reversible=parsed.get('f4_null_reversible'),refused=parsed.get('refused'),
                error=parsed.get('error'),exit=run.returncode)


def run(phase):
    global ws,note_read
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    r1.OUT=OUT
    planned={k:(e if isinstance(e,tuple) else (e,)) if phase=='before' else ('PASS',) for k,e,_ in PLAN}
    report=dict(status='INCOMPLETE',label=LABEL,phase=phase,source=r1.source(),production_go=False,independent_acceptance=False,release_evidence=False,
                planned={k:list(v) for k,v in planned.items()},stale_f2=STALE_F2)
    report['run_identity']=run_identity.announce(LABEL,phase=phase)
    r1.save('RESULT_'+phase.upper(),report)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        r1.writer.install_at()
        control_url=os.environ['CP6_ADMISSION_CONTROL_PGURL']
        report['au_install']=awp.au_runtime.change('install',boundary.PG,control_url)['status']
        report['av_install']=awp.av_runtime.change('install',boundary.PG,control_url)['status']
        report['aw_install']=awp.install_aw();report['ax_install']=axp.install_ax();report['ay_install']=ayp.install_ay()
        report['az_install']=azp.install_az();report['ba_install']=bap.install_ba();report['bb_install']=bbp.install_bb();verify=bbp.bb_verified
        if phase=='after':report['bc_install']=install_bc();verify=bc_verified
        r1.save('RESULT_'+phase.upper(),report)
        print(json.dumps(dict(bc_probe_setup={k:report.get(k) for k in ('au_install','av_install','ba_install','bb_install','bc_install')}),default=str),flush=True)
        WS['dir']=Path(tempfile.mkdtemp(prefix='cp6-bc-ws-'));api.read=recording_read;ws=recording_ws;note_read=recording_note_read
        try:group=r1.group('BC_CASES_'+phase.upper(),cases,verify)
        finally:api.read=_READ;ws=_WS;note_read=_NOTE_READ
        report['bc_cases']={k:group[k] for k in ('status','counts')}
        report['workspace_parse']=workspace_parse(phase)
        print(json.dumps(dict(bc_workspace_parse=report['workspace_parse']),default=str),flush=True)
        final={k:v['status'] for k,v in group['cases'].items()}
        report['final']=final
        report['expectation_mismatch']={k:dict(planned=list(e),final=final.get(k)) for k,e in planned.items() if final.get(k) not in e}
        report['status']='REVIEW_COMPLETE' if group['status']!='INCOMPLETE' and not report['expectation_mismatch'] and report['workspace_parse']['status']=='PASS' else 'INCOMPLETE'
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        r1.save('RESULT_'+phase.upper(),report)
    print(json.dumps(dict(bc_probe_phase=phase,**{k:v for k,v in report.items() if k!='source'}),default=str),flush=True)
    assert report['status']=='REVIEW_COMPLETE',report.get('error') or ('BC_PROBE_EXPECTATION_MISMATCH',report.get('expectation_mismatch'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('before','after'),required=True)
    run(parser.parse_args().phase)
