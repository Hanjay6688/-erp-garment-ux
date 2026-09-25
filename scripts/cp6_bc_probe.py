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
    start=re.compile(r'(?i)\bas \$(function|\$)').search(text,heads[-1])
    delim='$function$' if start.group(1)=='function' else '$$'
    return text[start.end():text.index(delim,start.end())]


def bc_installed(cur):
    return cur.execute('select count(*) from erp.schema_migrations where version=%s',(bc.VERSION,)).fetchone()[0]==1


def bc_functions():
    return tuple(bc.REPLACED)+tuple(dict.fromkeys(bc.new_functions()))


def bc_verified(cur):
    base=bbp.bb_verified(cur)
    assert bc_installed(cur),'BC_T1_MARKER'
    for name in bc_functions():
        schema,proname=name.split('(')[0].split('.')
        rows=cur.execute("select p.oid::regprocedure::text,p.prosrc from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and p.proname=%s",
                         (schema,proname)).fetchall()
        assert len(rows)==1,('BC_T1_FUNCTION_NOT_UNIQUE',name,[r[0] for r in rows])
        assert rows[0][1]==dev_source(name),('BC_T1_FUNCTION_NOT_CURRENT',name)
    for table in bc.NEW_TABLES:
        assert cur.execute('select to_regclass(%s) is not null',('erp.'+table,)).fetchone()[0],('BC_T1_TABLE_MISSING',table)
    return dict(base,stage='AV_PLUS_AW_AX_AY_AZ_BA_BB_BC_T1',bc_sql_sha256=hashlib.sha256(BC_SQL.read_bytes()).hexdigest(),
                bc_functions=list(bc_functions()))


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
    """ERROR/CRITICAL detector rows (name -> count) of the detectors BC touches or feeds."""
    rows={}
    for f in DETECTORS:
        for r in q(cur,f'select * from erp.{f}()'):
            if r[2] and str(r[1]).upper() in('ERROR','CRITICAL'):rows[f+':'+r[0]]=int(r[2])
    return rows


def new_findings(before,after):
    return {k:v for k,v in after.items() if v>before.get(k,0)}


def local_at(day,hour=10,minute=0):
    return datetime.combine(day,dtime(hour,minute)).strftime('%Y-%m-%dT%H:%M:%S')+'+07:00'


def tag():
    return 'BC'+uuid.uuid4().hex[:10].upper()


# ---------------------------------------------------------------- fixture
def fixture(cur,today,stock_qty=1000,cost='2.00',zones=True,days=6):
    """An accessory counted in PCS with `stock_qty` received `days` days ago at `cost` (estimated, invoice pending) in a main
    warehouse, a second main warehouse, an FG warehouse, an inactive warehouse, the three BC zones (after BC), a mandor and
    a cash account."""
    api.admin(cur);code=tag()
    prior.set_open_period(cur,today-timedelta(days=days+5))
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
    saved=internal(cur,'save_material_purchase_draft_v2',Jsonb(dict(purchase_number=code+'P',supplier_id=str(supplier),location_id=str(main),
        physical_at=local_at(received,9),change_reason='BC fixture receipt',lines=[dict(material_id=str(mat),qty=stock_qty,unit_price=cost,
        price_state='ESTIMATED',price_source='MANUAL_ESTIMATE')])),str(uuid.uuid4()),None)
    internal(cur,'post_material_purchase_v2',saved['purchase_id'],str(uuid.uuid4()),saved['row_version'],'BC fixture receipt post')
    fx=dict(code=code,category=str(cat),material=str(mat),main=str(main),other=str(other),fg=str(fg),inactive=str(inactive),mandor=str(mandor),
            cash=str(cash),purchase=str(saved['purchase_id']),item=str(one(cur,'select id from erp.material_purchase_items where purchase_id=%s',saved['purchase_id'])),
            received=received,pcs=pcs,supplier=str(supplier))
    if zones and bc_installed(cur):
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


def b04_backdated_late_invoice(cur,today):
    """ACC-B04 (M:5270): a backdated transfer to the post and a later cost invoice create no false quantity, value or average:
    the transfer carries no journal, the invoice recosts the moving average once and the books equal the subledger."""
    fx=fixture(cur,today)
    if not bc_installed(cur):return no_route(cur,lambda:svc(cur,'FILL_POST',dict(reason='x')))
    base=findings(cur)
    fill(cur,fx,120,today-timedelta(days=4))
    transfer_journals=one(cur,"select count(*) from erp.journal_entries where source_type in('MATERIAL_TRANSFER','BC_FILL_POST')")
    api.admin(cur);version=int(one(cur,'select row_version from erp.material_purchase_headers where id=%s',fx['purchase']))
    session(cur)
    cur.execute('select erp.finalize_material_purchase_invoice_v2(%s::jsonb,%s,%s)',(json.dumps(dict(purchase_id=fx['purchase'],
        supplier_invoice_number=tag(),invoice_date=str(today),received_at=local_at(today,8),reason='BC probe late invoice',
        lines=[dict(purchase_item_id=fx['item'],qty_invoiced=1000,final_unit_price='2.10')])),str(uuid.uuid4()),version))
    cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)
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
