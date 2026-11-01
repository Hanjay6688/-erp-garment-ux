"""Prepared actual-domain fixture; no ERP import, connection or commit on load.

Only the contractor master supplied to the unchanged physical constructor is
bound privately. Every cutting, pickup, work, laundry, receipt, issue and GOOD
fact still comes from the existing Native commands. No product/source graph
is replaced. An actual accepted FREE3 parent and installed settings stage are
mandatory before loading the domain modules.
"""
from datetime import timedelta
from decimal import Decimal,ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from types import FunctionType,SimpleNamespace
import json,subprocess,uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE='0da4d79a4f7201ef053d6de1eb155d990b4bfa4d'
ORIGINALS={
    'scripts/cp6_bc_probe.py':(139394,'147de7092ba2284312ba376f8cae82bf05c0fbb77e28956f45966cdfa6c8adb1'),
    'scripts/cp6_bd_probe.py':(142782,'c3add21e66d4d5544bf4e4d046a9fa8d64dbcb0cb285551a92c2d7405156b31b'),
    'scripts/cp6_aa_invoice_partial_audit.py':(29949,'aac0f1648806a108805591c40cb09ed4a1a78d4c16b5bdb93422d41582724578'),
    'scripts/cp6_auditor_runner.py':(14911,'2c74439f7e919e2adb2484bc774bef4881e71237124f2e6b6dabdab141348ea7'),
    'scripts/cp7_accessory_standard_report/cases.py':(19581,'e025be1280630dfb89f62261163194ce072b6f6ad6d909b56ff6c82f75778e98'),
    'scripts/cp7_invoice_cases.py':(18588,'a6b2e46346b211c0934b8b43f30d9ecfeb161ba37ab4eff5fdf7f183fc810bb1'),
    'scripts/cp7_qc_source_cases.py':(10188,'67fe6812924583a7789377f6a01525614d9d0fb2665a8d59ee113a794d076ed5'),
}

def source_controls():
    for name,pin in ORIGINALS.items():
        raw=(ROOT/name).read_bytes()
        if (len(raw),sha256(raw).hexdigest())!=pin or raw!=subprocess.check_output(
                ['/usr/bin/git','-C',str(ROOT),'show',BASE+':'+name]):
            raise ValueError('NONPAYABLE_NATIVE_FIXTURE_ORIGINAL_CHANGED:'+name)
    return dict(status='EXACT_UNCHANGED_NATIVE_FIXTURE_AND_RUNNER_SOURCES',source_files=len(ORIGINALS),
        original_parent=BASE,Native_body_changes=0,posted_row_injection=False,actual_Native_cases=0)

def admitted_modules(cur,state):
    from . import admission
    admission.parent_receipt()  # Refuse before domain imports or cursor use.
    source_controls()
    from . import settings_stage as product
    from cp7_p21_current_chain_rehearsal_probe import helper
    with helper.control.product_catalog(cur):product.verify(cur,state)
    connection=cur.connection
    if(connection.info.host not in('localhost','127.0.0.1')or connection.info.port!=54322
       or cur.execute('select current_database()').fetchone()!=('cp6_rollback',)):
        raise ValueError('NONPAYABLE_NATIVE_FIXTURE_LOCAL_DISPOSABLE_ONLY')
    import cp6_bc_probe as bc
    import cp6_bd_probe as bd
    import cp7_invoice_cases as invoice
    import cp7_qc_source_cases as qc
    from cp7_accessory_standard_report import cases as bom
    return SimpleNamespace(bc=bc,bd=bd,invoice=invoice,qc=qc,bom=bom,product=product,control=helper.control)

def contractor_constructor(bd,contractor):
    """Keep the original code object; bind one new fixture master explicitly."""
    if str(uuid.UUID(contractor))!=contractor:raise ValueError('NONPAYABLE_CANONICAL_FIXTURE_CONTRACTOR_REQUIRED')
    original=bd.two_size_fixture
    if original.__globals__.get('chain')is not bd.chain:
        raise ValueError('NONPAYABLE_ORIGINAL_PHYSICAL_CONSTRUCTOR_GLOBAL_REQUIRED')
    production=SimpleNamespace(**vars(bd.chain.production));production.CONTRACTOR=contractor
    chain=SimpleNamespace(**vars(bd.chain));chain.production=production
    private=FunctionType(original.__code__,dict(original.__globals__,chain=chain),original.__name__,
        original.__defaults__,original.__closure__)
    private.__kwdefaults__=dict(original.__kwdefaults__ or {})
    if private.__code__ is not original.__code__ or bd.chain.production.CONTRACTOR==contractor:
        raise ValueError('NONPAYABLE_FRESH_PRIVATE_MASTER_BINDING_REQUIRED')
    return private

def policy(cur,modules,contractor,start,special):
    modules.bd.chain.production.owner(cur)
    payload=dict(contractor_id=contractor,effective_from=str(start),is_special=special,
        attendance_required=False,reason='Native GOOD-date fixture: explicit dated Mandor classification')
    result=cur.execute('select public.erp_set_contractor_hpp_policy_v1(%s::jsonb,%s,null)',
        (json.dumps(payload),uuid.uuid4())).fetchone()[0]
    modules.bc.api.admin(cur)
    return result

def confirm_date(cur,modules,day):
    modules.bd.chain.production.owner(cur)
    workspace=cur.execute('select public.erp_cp7_get_good_policy_dates_v1(%s::jsonb)',
        (json.dumps(dict(before_version=None,before_date=None)),)).fetchone()[0]
    if workspace['can_write']is not True:raise ValueError('NONPAYABLE_ACTUAL_OWNER_DATE_CAPABILITY_REQUIRED')
    payload=dict(contract_version='cp7.good-policy-date-command.v1',actor=workspace['actor'],
        access_epoch=workspace['access_epoch'],effective_from=str(day),
        source_event_id=workspace['current_source']['id'],expected_current_version=workspace['current_source']['version'],
        expected_timeline=workspace['timeline_token'],reason='Native fixture owner confirms physical GOOD-date policy',reviewed=True)
    request=uuid.uuid4()
    reply=cur.execute('select public.erp_cp7_save_good_policy_date_v1(%s::jsonb,%s,false)',
        (json.dumps(payload),request)).fetchone()[0]
    if reply['status']!='SAVED'or reply['effective_from']!=str(day):
        raise ValueError('NONPAYABLE_ACTUAL_OWNER_DATE_CONFIRMATION_REQUIRED')
    modules.bc.api.admin(cur)
    return dict(workspace=workspace,payload=payload,request_id=str(request),reply=reply)

def prepare(cur,today,modules,*,special=True,transition=None,unit_cost='2',qty_per_good='1',register_date=True):
    bc,bd=modules.bc,modules.bd
    accessory=bc.fixture(cur,today,stock_qty=1000,cost=unit_cost,zones=False)
    bc.api.admin(cur)
    if cur.execute('select count(*)from erp.contractor_hpp_policy_versions where contractor_id=%s',
            (accessory['mandor'],)).fetchone()[0]!=0:
        raise ValueError('NONPAYABLE_FRESH_MANDOR_POLICY_WITHOUT_PROMOTION_REQUIRED')
    start=today-timedelta(days=7)
    classification=[policy(cur,modules,accessory['mandor'],start,special)]
    bc.policy(cur,'ERP_DEC02',dict(special_free_category_ids=[accessory['category']]))
    confirmation=confirm_date(cur,modules,start)if register_date else None
    constructor=contractor_constructor(bd,accessory['mandor'])
    physical=constructor(cur,today,'NONPAYABLE',size_quantities=[(bd.chain.base.SIZE,10)])
    bc.api.admin(cur)
    if str(cur.execute('select contractor_id from erp.production_orders where id=%s',
            (physical['po'],)).fetchone()[0])!=accessory['mandor']:
        raise ValueError('NONPAYABLE_EXPLICIT_SAME_MANDOR_PHYSICAL_PO_REQUIRED')
    product=bd.sized_product(cur,bd.chain.base.SIZE,'NP-'+uuid.uuid4().hex[:8])
    physical.update(product=product,contractor=accessory['mandor'],accessory=accessory)
    modules.bom.recipe(cur,physical,qty=qty_per_good,rate='2',method='CATEGORY_MOVING_AVG')
    # A known process rate uses the original ordinary delivery path; no fake
    # final amount, posted row, tariff fallback or material stock is supplied.
    bd.process_rate(cur,physical,'1')
    delivery=bd.plain_delivery(cur,physical,10,11)
    received=bd.receive(cur,delivery,physical,10,13)
    bc.api.admin(cur)
    rows=cur.execute('select s.id::text,s.receipt_line_id::text from erp.laundry_receipt_batch_size_lines s '
        'join erp.laundry_receipt_lines l on l.id=s.receipt_line_id where l.receipt_id=%s',
        (received['receipt_id'],)).fetchall()
    if len(rows)!=1:raise ValueError('NONPAYABLE_NATIVE_SINGLE_RECEIPT_LINEAGE_REQUIRED')
    line=dict(material_id=accessory['material'],qty='3',mode='FREE'if special else'MANUAL')
    if special:line['free_policy_version']=str(cur.execute("select erp.bc_policy_version_v1('ERP_DEC02')").fetchone()[0])
    else:line['manual_price']='2'
    note=bc.note_call(cur,'POST',dict(id=None,expected_version=None,number='NP-'+uuid.uuid4().hex,
        contractor_id=accessory['mandor'],location_id=accessory['main'],po_id=physical['po'],
        physical_at=bc.local_at(physical['day'],10),reason='Native counted issue before GOOD',notes='',items=[line]))
    good_day=physical['day']
    if transition is not None:
        good_day+=timedelta(days=1)
        classification.append(policy(cur,modules,accessory['mandor'],good_day,transition))
    physical.update(receipt=received,receipt_size=rows[0][0],receipt_line=rows[0][1],delivery=delivery,
        good_day=good_day,classification=classification,category_date_confirmation=confirmation,note=note,
        qty_per_good=qty_per_good,unit_cost=unit_cost,constructor_binding=dict(
            original_code_object_unchanged=True,only_bound_master='chain.production.CONTRACTOR',
            contractor_id=accessory['mandor'],Native_function_or_product_graph_changes=False))
    return physical

def post_good(cur,modules,f,*,good_qty=10,bs_qty=0):
    bd,bc=modules.bd,modules.bc
    if type(good_qty)is not int or type(bs_qty)is not int or good_qty<=0 or bs_qty<0 or good_qty+bs_qty!=10:
        raise ValueError('NONPAYABLE_NATIVE_EXACT_TEN_RECEIVED_PCS_REQUIRED')
    payload=dict(cutting_group_id=f['group'],destination_location_id=bd.chain.base.LOCATION,
        physical_at=bd.chain.production.at(f['good_day'],14).isoformat(),reason='Native actual company-funded GOOD',
        good_qty_pcs=good_qty,completion_mode='ALL_READY',lines=[dict(final_product_id=f['product'],qty_good_pcs=good_qty,
            qty_bs_pcs=bs_qty,source_laundry_receipt_line_id=f['receipt_line'],source_laundry_receipt_batch_size_line_id=f['receipt_size'])])
    result=bd.chain.laundry_action(cur,'POST_FINAL_SKU',payload,bd.chain.base.group_version(cur,f['group']))
    bc.api.admin(cur)
    lots=cur.execute("select id::text,initial_qty_pcs from erp.fg_lots where po_id=%s and product_id=%s and lot_origin='PRODUCTION'",
        (f['po'],f['product'])).fetchall()
    if len(lots)!=1 or lots[0][1]!=good_qty:raise ValueError('NONPAYABLE_NATIVE_ONE_AUTHORITATIVE_GOOD_LOT_REQUIRED')
    f.update(lot=lots[0][0],good=result,good_payload=payload,good_qty=good_qty)
    return result

def observe(cur,modules,f):
    modules.bc.api.admin(cur)
    cur.execute("set local timezone='UTC'")  # Stable JSON timestamps across committed-copy sessions.
    snapshots=cur.execute('select to_jsonb(s),to_jsonb(b),cp7_accessory_nonpayable.snapshot_identity_v1(s.id) '
        'from erp.fg_accessory_cost_snapshots s left join cp7_accessory_nonpayable.good_bases_v1 b on b.snapshot_id=s.id '
        'where s.lot_id=%s order by s.id',(f['lot'],)).fetchall()
    entitlements=cur.execute('select to_jsonb(e)from erp.contractor_accessory_reimbursement_entitlements e where lot_id=%s order by id',
        (f['lot'],)).fetchall()
    journals=cur.execute("select to_jsonb(j),coalesce((select jsonb_agg(to_jsonb(l)order by l.id)from erp.journal_lines l where l.journal_entry_id=j.id),'[]'::jsonb) "
        "from erp.journal_entries j where j.source_type='ACCESSORY_REIMBURSE_ACCRUAL'and j.source_id=%s order by j.id",(f['lot'],)).fetchall()
    booked={key:cur.execute("select coalesce(sum(l.debit-l.credit),0)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id "
        "where j.status='POSTED'and l.account_id=erp.account_id(%s)and((j.source_type='ACCESSORY_REIMBURSE_ACCRUAL'and j.source_id=%s)or "
        "(j.source_type='ACCESSORY_HPP_RECOST'and exists(select 1 from erp.fg_accessory_cost_revisions r join erp.fg_accessory_cost_snapshots s "
        "on s.id=r.snapshot_id where r.id=j.source_id and s.lot_id=%s)))",(key,f['lot'],f['lot'])).fetchone()[0]
        for key in('WIP','CONTRACTOR_PAYABLE','ACCESSORY_REIMBURSE_VARIANCE')}
    material=f['accessory']
    movements=cur.execute("select to_jsonb(m),jsonb_build_object('id',m.id,'material_id',m.material_id,'location_id',m.location_id,"
        "'source_type',m.source_type,'source_id',m.source_id,'movement_type',m.movement_type,'qty_signed',m.qty_signed,"
        "'physical_at_epoch',extract(epoch from m.physical_at))from erp.material_stock_movements m where material_id=%s order by id",
        (material['material'],)).fetchall()
    return dict(snapshots=[dict(snapshot=s,basis=b,actual_fixed_identity=i)for s,b,i in snapshots],
        entitlements=[v[0]for v in entitlements],original_accrual=[dict(header=j,lines=l)for j,l in journals],
        booked={k:str(v)for k,v in booked.items()},raw_material_movements=[v[0]for v in movements],
        physical_material_movements=[v[1]for v in movements],
        accessory_stock=str(modules.bc.stock(cur,material['material'],material['main'])))

def require_economics(value,f,*,nonpayable,hpp):
    D=Decimal;rows=value['snapshots']
    if len(rows)!=1:raise ValueError('NONPAYABLE_EXACT_SINGLE_BOM_COMPONENT_REQUIRED')
    row=rows[0];s,b=row['snapshot'],row['basis']
    expected_qty=D(f.get('good_qty',10))*D(f['qty_per_good']);reimbursement=D(0)if nonpayable else expected_qty*D(2)
    if (D(str(s['good_qty_pcs']))!=D(f.get('good_qty',10))or D(str(s['qty_per_good_fg_base']))!=D(f['qty_per_good'])
        or D(str(s['total_hpp_cost']))!=D(hpp)or D(str(s['total_reimbursement']))!=reimbursement
        or D(str(s['reimbursement_unit_rate_base_snapshot']))!=(D(0)if nonpayable else D(2))
        or b['nonpayable']is not nonpayable or b['contractor_id']!=f['contractor']
        or b['good_date']!=str(f['good_day'])or D(str(b['original_reimbursement_rate']))!=2
        or b['fixed_snapshot']!=row['actual_fixed_identity']):
        raise ValueError('NONPAYABLE_NATIVE_GOOD_DATE_RATE_AND_POSITIVE_HPP_ORACLE_FAILED')
    if nonpayable and value['entitlements']:raise ValueError('NONPAYABLE_MUST_NOT_CREATE_ENTITLEMENT')
    if not nonpayable and sum(D(str(e['amount']))for e in value['entitlements'])!=reimbursement:
        raise ValueError('NONPAYABLE_NORMAL_REIMBURSEMENT_FLOW_REGRESSION')
    amount=D(hpp).quantize(D('.01'),rounding=ROUND_HALF_UP)
    expected=dict(WIP=amount,CONTRACTOR_PAYABLE=-reimbursement,ACCESSORY_REIMBURSE_VARIANCE=reimbursement-amount)
    if {k:D(v)for k,v in value['booked'].items()}!=expected:
        raise ValueError('NONPAYABLE_NATIVE_EXACT_CUMULATIVE_JOURNAL_ORACLE_FAILED')
    if D(value['accessory_stock'])!=997:raise ValueError('NONPAYABLE_NATIVE_PHYSICAL_ISSUE_MUST_HAPPEN_ONCE')
