"""R3-05 (auditor Fable FABLE-016 remainder, S3): posting QC & Final SKU, and a Nota Ambil Aksesori deducted from the
Mandor's payroll, on the connected screens (browser cases in cp7_r3_qc_note_browser.mjs, spliced into the CP17 harness
through cp7_r3_cases.py BROWSER).

Fixtures use the Native writers the existing SQL cases already qualify:
- QC: the G2 chain (cp7_cp17_fix_cases.finish_fixture) stopped before its Final SKU: ten pieces of one PO sewn, sent to
  laundry and all ten received back GOOD (Native laundry facade), a fresh Final SKU product of the PO's model and size,
  nothing posted to QC yet. The limited role is a seeded active role that may view QC & Final SKU but not post it,
  read from the Native role rows (GUDANG in the seed of 20260902104937, AUDITOR_VIEW_ONLY otherwise).
- Note to payroll: the P12 payroll fixture (cp7_settlement_read_cases.fixture: a fresh Mandor, a work-only payroll draft of
  6000.00 from a posted Native Nota), an accessory counted in PCS with 1000 in a raw warehouse (cp6_bc_probe.fixture, as the
  native P12_SETTLEMENT_KASBON_CARRY case), and a bank holding owner capital of exactly the net the payroll will pay
  (labor - note A; D14-3: the capital is the only money the bank receives).

The state readers are direct SQL on the Native rows the screens change (QC inspections and items, FG lots, FG stock
movements, BS cases, WIP stage events, laundry receipt lines, PO stage, HPP versions, journal lines; accessory issues and
items, material stock, payroll settlements and deductions, journal lines by contractor and by cash account). They never
read a facade's answer. Money is returned as text with two decimals so the browser compares exact strings.
"""
from datetime import timedelta,timezone
from decimal import Decimal as D
import uuid

NATIVE=[]
RACES=[]
HTTP=[]
BROWSER=['CP17_BROWSER_R3_05_QC_FINAL_SKU_DESKTOP','CP17_BROWSER_R3_05_QC_FINAL_SKU_MOBILE','CP17_BROWSER_R3_05_ACCESSORY_NOTE_TO_PAYROLL_DESKTOP']
WIB=timezone(timedelta(hours=7))
KEYS=('WIP','FG_INVENTORY','ACCRUED_MANUFACTURING','COGS','OTHER_EXPENSE','OTHER_INCOME','CONTRACTOR_PAYABLE')

def cases(cur,today):return []
def races(tools,today):return []
def http_cases(http,today):return []

def cp17():
    import cp7_cp17_fix_cases as m
    return m
def row(cur,sql,args=()):return cur.execute(sql,args).fetchone()
def money(value):return str(D(value).quantize(D('0.01')))

# ---------------------------------------------------------------- QC & Final SKU
def limited_role(cur):
    """A seeded active role that may view QC & Final SKU but not post it (Native role rows)."""
    found=row(cur,"""select r.role_code from erp.app_roles r where r.is_active and r.role_code<>'OWNER'
        and exists(select 1 from erp.app_role_permissions p where p.role_id=r.id and p.permission_key='production.final_sku.view')
        and not exists(select 1 from erp.app_role_permissions p where p.role_id=r.id and p.permission_key='production.final_sku.post')
        order by case r.role_code when 'GUDANG' then 0 when 'AUDITOR_VIEW_ONLY' then 1 else 2 end,r.role_code limit 1""")
    assert found,'CP17_R3_05_NO_SEEDED_ROLE_WITH_QC_VIEW_WITHOUT_POST'
    return found[0]

def qc_fixture(cur,today):
    """Ten pieces of one PO back GOOD from laundry and ready for QC (the G2 chain without its Final SKU post)."""
    c=cp17();bd=c.bd;chain=bd.chain;base=chain.base
    f=bd.fixture(cur,today-timedelta(days=3),'R305-QC-'+uuid.uuid4().hex[:8]);bd.process_rate(cur,f,'2.00');c.b.api.admin(cur)
    delivery=bd.plain_delivery(cur,f,10,11);receipt=bd.receive(cur,delivery,f,10,13)['receipt_id'];c.b.api.admin(cur)
    product=str(chain.base.create_product(cur,'R305-'+uuid.uuid4().hex[:10]));c.b.api.admin(cur)
    size_line,receipt_line=row(cur,"""select x.id::text,x.receipt_line_id::text from erp.laundry_receipt_batch_size_lines x
        join erp.laundry_receipt_lines l on l.id=x.receipt_line_id where l.receipt_id=%s""",(receipt,))
    po_number,group_number,version=row(cur,"""select o.po_number,g.group_number,g.row_version from erp.cutting_groups g
        join erp.production_orders o on o.id=g.po_id where g.id=%s""",(f['group'],))
    sku,brand=row(cur,'select p.sku,b.brand_name from erp.products p join erp.brands b on b.id=p.brand_id where p.id=%s',(product,))
    location=str(base.LOCATION);location_code=row(cur,'select location_code from erp.locations where id=%s',(location,))[0]
    at=chain.production.at(f['day'],14).astimezone(WIB)
    # The screen proves that a filtered queue still holds every ready piece of the Potongan only for a plain ASCII query
    # that is part of the PO/Potongan number (ConnectedQcFinalPage qcQueueSourceComplete).
    assert all(32<=ord(ch)<=126 for ch in po_number) and not any(ch in po_number for ch in '%_\\'),po_number
    return dict(group=str(f['group']),po=str(f['po']),po_number=po_number,group_number=group_number,group_version=int(version),query=po_number,
                delivery=str(delivery),receipt=str(receipt),receipt_line=receipt_line,receipt_size=size_line,
                size_code=row(cur,'select size_code from erp.sizes where id=%s',(base.SIZE,))[0],
                product=product,sku=sku,brand=brand,location=location,location_code=location_code,
                qc_local=at.strftime('%Y-%m-%dT%H:%M'),qc_iso=at.isoformat(timespec='seconds'),qc_day=str(f['day']),
                limited_role=limited_role(cur))

def journals(cur,where,args):
    """Journal entries touching the given lines, each with its balance and its non-zero net per account (mapping key, or
    the account code when the account has none of KEYS)."""
    names={str(row(cur,'select erp.account_id(%s)',(k,))[0]):k for k in KEYS}
    out={}
    for jid,kind,status,day,account,code,debit,credit in cur.execute(f"""select j.id::text,j.source_type,j.status,j.economic_date::text,
        l.account_id::text,a.account_code,coalesce(sum(l.debit),0),coalesce(sum(l.credit),0)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id join erp.chart_accounts a on a.id=l.account_id
        where j.id in(select x.journal_entry_id from erp.journal_lines x where {where})
        group by j.id,j.source_type,j.status,j.economic_date,l.account_id,a.account_code order by j.id,l.account_id""",args).fetchall():
        j=out.setdefault(jid,dict(id=jid,source_type=kind,status=status,economic_date=day,debit=D(0),credit=D(0),nets={}))
        j['debit']+=debit;j['credit']+=credit;net=D(debit)-D(credit)
        if net:j['nets'][names.get(account,code)]=money(net)
    return [dict(j,balanced=j['debit']==j['credit'],debit=money(j['debit']),credit=money(j['credit'])) for j in out.values()]

def qc_state(cur,p):
    c=cp17();c.b.api.admin(cur);g,po=p['group'],p['po']
    inspections=[dict(id=i,number=n,status=s,location=loc,physical_local=t,row_version=int(v)) for i,n,s,loc,t,v in cur.execute("""select q.id::text,
        q.inspection_number,q.status,q.destination_location_id::text,to_char(q.physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI'),q.row_version
        from erp.qc_inspections q where exists(select 1 from erp.qc_inspection_items i where i.inspection_id=q.id and i.cutting_group_id=%s)
        order by q.physical_at,q.id""",(g,)).fetchall()]
    items=[dict(id=i,inspection=q,product=pr,good=int(gd),bs=int(b),receipt_line=rl) for i,q,pr,gd,b,rl in cur.execute("""select i.id::text,
        i.inspection_id::text,i.final_product_id::text,i.qty_good_pcs,i.qty_bs_pcs,i.source_laundry_receipt_line_id::text
        from erp.qc_inspection_items i where i.cutting_group_id=%s order by i.id""",(g,)).fetchall()]
    lots=[dict(id=i,product=pr,qc_item=q,origin=o) for i,pr,q,o in cur.execute("""select l.id::text,l.product_id::text,l.qc_item_id::text,l.lot_origin
        from erp.fg_lots l where l.po_id=%s order by l.id""",(po,)).fetchall()]
    movements=[dict(id=i,lot=lt,location=loc,qty=int(q),movement_type=mt,source_type=st,source_id=si,reversal_of=rv) for i,lt,loc,q,mt,st,si,rv in cur.execute("""
        select m.id::text,m.lot_id::text,m.location_id::text,m.qty_signed,m.movement_type,m.source_type,m.source_id::text,m.reversal_of_id::text
        from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s order by m.id""",(po,)).fetchall()]
    stage=[[a,b,int(q),st,si] for a,b,q,st,si in cur.execute("""select stage_from,stage_to,qty_pcs,source_type,source_id::text from erp.wip_stage_events
        where cutting_group_id=%s or(po_id=%s and cutting_group_id is null) order by physical_at,id""",(g,po)).fetchall()]
    received=int(row(cur,"""select coalesce(sum(rl.qty_good_received),0) from erp.laundry_receipt_lines rl join erp.laundry_receipts r on r.id=rl.receipt_id
        join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id join erp.laundry_deliveries d on d.id=dl.delivery_id
        where r.status='POSTED' and d.status<>'REVERSED' and dl.cutting_group_id=%s""",(g,))[0])
    accounted=int(row(cur,"""select coalesce(sum(i.qty_good_pcs+i.qty_bs_pcs),0) from erp.qc_inspection_items i join erp.qc_inspections q on q.id=i.inspection_id
        where q.status='POSTED' and i.cutting_group_id=%s""",(g,))[0])
    def balance(key):
        return money(row(cur,"""select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
            where j.status in('POSTED','REVERSED') and l.po_id=%s and l.account_id=erp.account_id(%s)""",(po,key))[0])
    stock={lt:int(q) for lt,q in cur.execute('select m.lot_id::text,coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s group by m.lot_id',(po,)).fetchall()}
    current=cur.execute("""select h.lot_id::text,h.total_cost,h.qty_basis_pcs from erp.hpp_versions h join erp.fg_lots l on l.id=h.lot_id
        where l.po_id=%s and h.is_current order by h.lot_id""",(po,)).fetchall()
    hpp=[[lt,money(t),int(q)] for lt,t,q in current]
    # The FG value the books must hold for this PO: each lot's current HPP for the pieces of it still in FG.
    fg_value=sum(((D(t)*stock.get(lt,0)/q).quantize(D('0.01')) if q else D(0) for lt,t,q in current),D(0))
    status=row(cur,'select status,current_stage from erp.production_orders where id=%s',(po,))
    return dict(inspections=inspections,items=items,lots=lots,movements=movements,fg_stock=sum(stock.values()),
                bs_cases=int(row(cur,'select count(*) from erp.bs_cases where cutting_group_id=%s',(g,))[0]),
                stage_events=stage,received_good=received,qc_accounted=accounted,ready=received-accounted,po=list(status),
                group_version=int(row(cur,'select row_version from erp.cutting_groups where id=%s',(g,))[0]),
                journals=journals(cur,'x.po_id=%s',(po,)),fg_balance=balance('FG_INVENTORY'),wip_balance=balance('WIP'),hpp=hpp,hpp_fg_value=money(fg_value))

# ---------------------------------------------------------------- Nota Ambil Aksesori -> payroll
NOTE_A=dict(qty=7,price='300')   # kept: deducted from the payroll
NOTE_B=dict(qty=3,price='500')   # reversed on the screen before the payroll is counted: never deducted

def note_fixture(cur,today):
    c=cp17();s,bc=c.s,c.bc
    f=s.review.fixture(cur,today);c.b.api.admin(cur)
    label='Mandor R305 '+uuid.uuid4().hex[:8]
    cur.execute('update erp.contractors set contractor_name=%s where id=%s',(label,f['contractor']))
    # As the native P12_SETTLEMENT_KASBON_CARRY case: the accessory note on a completed day (the BC fixture's 08:00 rule).
    workday=today-timedelta(days=1);fx=bc.fixture(cur,workday,zones=False);c.b.api.admin(cur)
    number,labor,period_end=row(cur,'select payroll_number,labor_total,period_end from erp.payroll_settlements where id=%s',(f['payroll'],))
    assert workday<=period_end,(workday,period_end)
    tag=uuid.uuid4().hex[:8].upper();notes={}
    for key,n in (('a',NOTE_A),('b',NOTE_B)):notes[key]=dict(n,number=f'R305{key.upper()}-{tag}',total=money(D(n['qty'])*D(n['price'])))
    net=D(labor)-D(notes['a']['total']);assert net>0,(labor,notes)
    bank=str(bc.bank_account(cur,'R305N'+tag));c.funding.fund(cur,bank,money(net),today);c.b.api.admin(cur)
    return dict(contractor=str(f['contractor']),label=label,payroll=str(f['payroll']),payroll_number=number,labor=money(labor),net=money(net),
                material=str(fx['material']),material_code=fx['code'],location=str(fx['main']),note_local=f'{workday:%Y-%m-%d}T10:00',
                a=notes['a'],b=notes['b'],bank=bank,bank_code=row(cur,'select cash_account_code from erp.cash_accounts where id=%s',(bank,))[0],
                stock=int(bc.stock(cur,fx['material'],fx['main'])),today=str(today))

def note_state(cur,p):
    c=cp17();bc=c.bc;c.b.api.admin(cur);who=p['contractor']
    status,labor,deducted,net,end,paid_on,paid_from=row(cur,"""select status,labor_total,deduction_total,net_payable,period_end,payment_date,payment_cash_account_id::text
        from erp.payroll_settlements where id=%s""",(p['payroll'],))
    deductions=[[t,i,money(a)] for t,i,a in cur.execute("""select deduction_type,contractor_issue_item_id::text,amount from erp.payroll_deductions
        where payroll_id=%s order by deduction_type,contractor_issue_item_id,amount""",(p['payroll'],)).fetchall()]
    notes={}
    for key in ('a','b'):
        found=row(cur,"""select id::text,status,contractor_id::text,location_id::text,to_char(physical_at at time zone 'Asia/Jakarta','YYYY-MM-DD"T"HH24:MI')
            from erp.contractor_material_issues where issue_number=%s""",(p[key]['number'],))
        if not found:notes[key]=None;continue
        items=[dict(id=i,material=m,qty=int(q),amount=money(t),payroll_status=ps) for i,m,q,t,ps in cur.execute("""select id::text,material_id::text,qty,
            total_receivable,payroll_status from erp.contractor_material_issue_items where issue_id=%s order by id""",(found[0],)).fetchall()]
        notes[key]=dict(id=found[0],status=found[1],contractor=found[2],location=found[3],physical_local=found[4],items=items,
            journals=[[t,s] for t,s in cur.execute('select source_type,status from erp.journal_entries where source_id=%s order by source_type,status,id',(found[0],)).fetchall()])
    # Oracle of what a count of this payroll may deduct (Native rows): every item of this Mandor's POSTED notes dated on or
    # before the period end, less what other active payrolls already took.
    collectible=row(cur,"""select coalesce(sum(i.total_receivable-coalesce((select sum(d.amount) from erp.payroll_deductions d join erp.payroll_settlements s
            on s.id=d.payroll_id where d.contractor_issue_item_id=i.id and s.id<>%s and s.status<>'REVERSED'),0)),0)
        from erp.contractor_material_issue_items i join erp.contractor_material_issues h on h.id=i.issue_id
        where h.contractor_id=%s and h.status='POSTED' and (h.physical_at at time zone 'Asia/Jakarta')::date<=%s""",(p['payroll'],who,end))[0]
    payable=row(cur,"""select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
        where l.contractor_id=%s and l.account_id=erp.account_id('CONTRACTOR_PAYABLE') and j.status in('POSTED','REVERSED')""",(who,))[0]
    def journal(kind):
        n,dr,cr=c.s.journal(cur,p['payroll'],kind);return [int(n),money(dr),money(cr)]
    return dict(payroll=dict(status=status,labor=money(labor),deduction=money(deducted),net=money(net),period_end=str(end),
                             payment_date=None if paid_on is None else str(paid_on),cash_account=paid_from),
                deductions=deductions,collectible=money(collectible),notes=notes,
                receivable=money(c.receivable(cur,who)),payable=money(payable),bank=money(c.balance(cur,p['bank'])),
                stock=int(bc.stock(cur,p['material'],p['location'])),
                payroll_journals=dict(material_deduction=journal('PAYROLL_MATERIAL_DEDUCTION'),payment=journal('PAYROLL_PAYMENT')))
