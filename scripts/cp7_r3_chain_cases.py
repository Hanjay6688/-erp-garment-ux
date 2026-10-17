"""R3-03 / auditor Fable's oracle 3 (owner D16-1): screen-only chains, browser fixtures and Native readbacks.

Fable (verbatim): "Screen chains in the Enteng build: (a) sewing -> Nota -> payroll -> pay -> Kas & Bank -> report -> close;
(b) FG -> invoice -> customer payment -> cash -> AR zero; (c) the D14-2, D14-3/D15-1 and D15-5 guards still refuse."
The browser module is scripts/cp7_r3_chain_browser.mjs; the harness re-runs every CP17 browser case on the Enteng build
(AUDITOR_UI_MODE=ENTENG, ids suffixed _ENTENG), so these cases need nothing of their own for that.

Fixtures give only what no screen of the chain creates, through the same Native writers as the other CP17 fixtures:
- chain (a): a posted cutting of 10 picked up by a fresh Mandor (cp7_cp17_fix_cases.pickup_fixture, dated 14 days back), the
  model's Work BOM valid on that day and the Mandor's rate 3 for its first component, a bank holding owner capital for
  exactly the wage on that day (cp7_cash_funding, D14-3), and the harness state r207 uses: the books opened from two days
  before the chain day and the seed's open items for those days cleared (cp6_aw_probe.quiet_seed); restored at the end.
- chain (b): finished goods found at opname (cp7_fg_cases.fixture), a customer and an empty bank.
- guards (c): an approved work-only payroll (cp7_cp17_fix_cases.approved_payroll), a bank funded before its accrual, an
  empty bank, a bank whose capital is dated inside a closed period (so it is booked on the first open day) with the
  period reopened before that date, an income category; and, only for the D15-5 step, the official cutover date set to
  the latest allowed day through the cutover command (moved back to 2000-01-03 by the existing cutover_reset operation).
Every readback is direct SQL on the Native rows (journal lines, payroll, work completion lines, sales, payments, kasbon,
misc transactions, period control), never a CP7 facade answer. Expected amounts come from Native master rows (Work BOM,
Mandor rates) and from these readbacks.
"""
from datetime import timedelta
from decimal import Decimal as D
import uuid

NATIVE=[]
RACES=[]
HTTP=[]
BROWSER=['CP17_BROWSER_R3_03_CHAIN_SEWING_TO_CLOSE','CP17_BROWSER_R3_03_CHAIN_FG_TO_AR_ZERO','CP17_BROWSER_R3_03_GUARDS_REFUSE']
def cases(cur,today):return []
def races(tools,today):return []
def http_cases(http,today):return []

# Every configured cash/bank book account, as the cash reader and the owner report count them.
CASH="(select c.coa_account_id from erp.cash_accounts c union select erp.account_id('CASH'))"


def cp17():
    import cp7_cp17_fix_cases as c
    return c
def row(cur,sql,args=()):return cur.execute(sql,args).fetchone()
def text(v):return None if v is None else str(v)
def closed(cur):return row(cur,'select closed_through from erp.accounting_period_control where singleton_id=1')[0]
def set_closed(cur,day,why):
    cur.execute("""update erp.accounting_period_control set closed_through=%s,updated_at=clock_timestamp(),updated_by=null,
        change_reason=%s where singleton_id=1""",(day,why))
def bank_code(cur,bank):return row(cur,'select cash_account_code from erp.cash_accounts where id=%s',(bank,))[0]
def bank_name(cur,bank):return row(cur,'select cash_account_name from erp.cash_accounts where id=%s',(bank,))[0]
def bank_balance(cur,bank):
    """Economic balance of one bank from its journal lines (debit minus credit, posted and reversed journals both stay)."""
    return str(row(cur,"""select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
        where j.status in('POSTED','REVERSED') and l.account_id=(select coa_account_id from erp.cash_accounts where id=%s)""",(bank,))[0])
def bank_book(cur,bank):
    """Per journal touching the bank: book date, economic date and the bank's own movement."""
    return [[str(t),str(e),str(v)] for t,e,v in cur.execute("""select j.transaction_date,j.economic_date,sum(l.debit-l.credit) from erp.journal_lines l
        join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED')
        and l.account_id=(select coa_account_id from erp.cash_accounts where id=%s) group by j.id order by j.transaction_date,j.posting_at,j.id""",(bank,)).fetchall()]
def cash_journal(cur,where,args):
    """One journal as the Kas & Bank page lists it: its cash lines summed over every cash/bank book account."""
    r=row(cur,f"""select j.id::text,j.journal_number,j.source_type,j.economic_date::text,j.transaction_date::text,
        coalesce(sum(l.debit) filter(where l.account_id in {CASH}),0)::text,coalesce(sum(l.credit) filter(where l.account_id in {CASH}),0)::text,
        coalesce(sum(l.debit-l.credit) filter(where l.account_id in {CASH}),0)::text
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where {where} group by j.id order by j.posting_at,j.id limit 1""",args)
    return None if r is None else dict(id=r[0],number=r[1],source_type=r[2],economic_date=r[3],transaction_date=r[4],cash_debit=r[5],cash_credit=r[6],cash_net=r[7])


# ---------------------------------------------------------------- chain (a): sewing -> Nota -> payroll -> pay -> cash -> report -> close
def chain_rates(cur,g,at):
    """The PO model's Work BOM valid at the sewing time and the Mandor's rate 3 for its first component (Native master rows).
    A BOM already valid on the chain day is reused as it is; otherwise one is added from the chain day with the G1 shape
    (default rates 2 and 1), ending where a later version of the model begins, so no two active versions overlap
    (integrity check WORK_BOM_OVERLAP) and the later G1/wave/R3-09 fixtures still find their own or reuse this one."""
    c=cp17();prod=c.cut.cutting.qc.physical.b.chain.production;c.b.api.admin(cur)
    model=row(cur,'select model_id from erp.production_orders where id=%s',(g['po'],))[0];since=g['at'](0)
    def valid(t):
        r=row(cur,"""select v.id from erp.work_bom_versions v where v.model_id=%s and v.is_active and v.effective_from<=%s
            and(v.effective_to is null or v.effective_to>%s)and exists(select 1 from erp.work_bom_items x where x.bom_version_id=v.id)
            order by v.effective_from desc,v.version_no desc,v.id desc limit 1""",(model,t,t))
        return None if r is None else r[0]
    created=valid(since) is None
    if created:
        later=row(cur,'select min(v.effective_from) from erp.work_bom_versions v where v.model_id=%s and v.is_active and v.effective_from>%s',(model,since))[0]
        bom=row(cur,"""insert into erp.work_bom_versions(model_id,version_no,effective_from,effective_to,notes)
            values(%s,(select coalesce(max(version_no),0)+1 from erp.work_bom_versions where model_id=%s),%s,%s,'CP17 G1 BOM kerja')returning id""",(model,model,since,later))[0]
        obras=row(cur,'insert into erp.work_components(component_code,component_name)values(%s,%s)returning id',('CP17-OBRAS-'+uuid.uuid4().hex[:8],'CP17 Obras'))[0]
        cur.execute('insert into erp.work_bom_items(bom_version_id,work_component_id,sequence_no,default_rate)values(%s,%s,1,2),(%s,%s,2,1)',(bom,prod.COMPONENT,bom,obras))
    bom=valid(at);assert bom is not None,'CP17_R3_03_CHAIN_NO_WORK_BOM'
    items=cur.execute('select work_component_id,default_rate from erp.work_bom_items where bom_version_id=%s order by sequence_no,id',(bom,)).fetchall()
    cur.execute('insert into erp.contractor_work_rates(contractor_id,model_id,work_component_id,rate_per_pcs,effective_from)values(%s,%s,%s,3,%s)',(g['mandor'],model,items[0][0],since))
    rates=[]
    for comp,default in items:
        r=row(cur,"""select w.rate_per_pcs from erp.contractor_work_rates w where w.contractor_id=%s and w.model_id=%s and w.work_component_id=%s
            and w.effective_from<=%s and(w.effective_to is null or w.effective_to>%s) order by w.effective_from desc,w.id desc limit 1""",(g['mandor'],model,comp,at,at))
        rates.append(D(r[0] if r else default).quantize(D('0.01')))
    return dict(bom=str(bom),bom_created=created,rates=rates)

def browser_sewing_prepare(cur,today):
    import cp7_period_cases as period,cp7_cash_funding as funding
    c=cp17();c.b.api.admin(cur);prev=closed(cur)
    # The cutting is posted and picked up 14 days back (pickup_fixture takes its receipt three days before the day it is
    # given and cuts the day after); its receipt fixture opens the books from the day before that receipt.
    g=c.pickup_fixture(cur,today-timedelta(days=12));c.b.api.admin(cur);day=g['day'];opened=closed(cur)
    label='Mandor R3-03 '+uuid.uuid4().hex[:8].upper()
    cur.execute('update erp.contractors set contractor_name=%s where id=%s',(label,g['mandor']))
    sewn_at=g['at'](14);rates=chain_rates(cur,g,sewn_at);c.b.api.admin(cur)
    quiet=period.aw.quiet_seed(cur,opened,day+timedelta(days=1));c.b.api.admin(cur)
    # The close checks attendance from erp.period_completeness_from_v1(), not from the closed date (P-01), so seed workers'
    # days left empty before `opened` by earlier fixtures also block it (CI 39020856920: 4 workers, 2026-09-19..30). They
    # are filled the same owner way (OFF through quiet_seed) with the books opened from the first such day, then the
    # closed date goes back to `opened`; nothing else is written there.
    gap=row(cur,"""select min(impact_date) from erp.period_blockers_v1(%s,erp.period_completeness_from_v1())
        where code='ATTENDANCE_CELL_MISSING'""",(day,))[0]
    backfill=None
    if gap is not None and gap<=opened:
        cur.execute("""update erp.accounting_period_control set closed_through=%s,updated_at=clock_timestamp(),updated_by=null,
            change_reason='CP17 R3-03 chain: seed attendance gap filled' where singleton_id=1""",(gap-timedelta(days=1),))
        back=period.aw.quiet_seed(cur,gap,opened);c.b.api.admin(cur)
        cur.execute("""update erp.accounting_period_control set closed_through=%s,updated_at=clock_timestamp(),updated_by=null,
            change_reason='CP17 R3-03 chain: closed date back after the gap' where singleton_id=1""",(opened,))
        backfill=dict(from_day=str(gap),to_day=str(opened),attendance=len(back['attendance']),refused=back['refused'])
    left=row(cur,"""select count(*) from erp.period_blockers_v1(%s,erp.period_completeness_from_v1()) where code='ATTENDANCE_CELL_MISSING'""",(day,))[0]
    assert left==0,('CP17_R3_03_CHAIN_SEED_ATTENDANCE_GAP_LEFT',left,backfill)
    qty=10;per=sum(rates['rates'],D('0.00'));wage=(per*qty).quantize(D('0.01'))
    code='R3C'+uuid.uuid4().hex[:8].upper();bank=str(c.bc.bank_account(cur,code));c.b.api.admin(cur)
    capital=funding.fund(cur,bank,str(wage),day);c.b.api.admin(cur)
    return dict(group=str(g['group']),po=str(g['po']),mandor=str(g['mandor']),mandor_label=label,
        number=row(cur,'select group_number from erp.cutting_groups where id=%s',(g['group'],))[0],day=str(day),sewn_local=f'{day:%Y-%m-%d}T14:00',
        qty=qty,rates=[str(x) for x in rates['rates']],per_pcs=str(per),wage=str(wage),bom=rates['bom'],bom_created=rates['bom_created'],
        bank=bank,bank_code=bank_code(cur,bank),capital=str(capital),opened_closed=str(opened),previous_closed=text(prev),
        quiet=dict(attendance=len(quiet['attendance']),approved=len(quiet['approved']),work_payrolls=len(quiet['work_payrolls']),refused=quiet['refused']),
        seed_attendance_backfill=backfill)

def browser_sewing_state(cur,p):
    c=cp17();c.b.api.admin(cur);day=p['day']
    works=cur.execute("""select id::text,(physical_at at time zone 'Asia/Jakarta')::date::text from erp.work_completion_events
        where cutting_group_id=%s and status='POSTED' order by created_at,id""",(p['group'],)).fetchall()
    completion=None
    if works:
        lines=cur.execute("""select l.rate_snapshot::text,l.qty_completed from erp.work_completion_lines l join erp.po_work_component_snapshots s on s.id=l.po_component_snapshot_id
            where l.completion_id=%s order by s.sequence_no,s.id""",(works[0][0],)).fetchall()
        completion=dict(day=works[0][1],qty=int(lines[0][1]) if lines else 0,rates=[r for r,_ in lines])
    sewn=c.sewn_ready(cur,dict(group=p['group'])) or (0,0)
    note=row(cur,'select status,posted_payroll_id::text from cp7_payroll.notes where contractor_id=%s order by created_at desc limit 1',(p['mandor'],))
    pay=row(cur,"""select id::text,payroll_number,status,period_start::text,period_end::text,labor_total::text,net_payable::text,payment_date::text,
        payment_cash_account_id::text from erp.payroll_settlements where contractor_id=%s order by created_at desc limit 1""",(p['mandor'],))
    payment=cash_journal(cur,"j.source_type='PAYROLL_PAYMENT' and j.source_id=%s and j.status='POSTED'",(pay[0],)) if pay else None
    payable=row(cur,"""select coalesce(sum(l.credit-l.debit),0)::text from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
        where j.status in('POSTED','REVERSED') and l.contractor_id=%s and l.account_id=erp.account_id('CONTRACTOR_PAYABLE')""",(p['mandor'],))[0]
    # What the Kas & Bank page totals for the chain day and the owner report shows as of it, from the journal lines.
    cash_day=row(cur,f"""select coalesce(sum(l.debit),0)::text,coalesce(sum(l.credit),0)::text from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
        where j.status in('POSTED','REVERSED') and j.transaction_date=%s and l.account_id in {CASH}""",(day,))
    report=row(cur,f"""select coalesce(sum(l.debit-l.credit) filter(where l.account_id in {CASH}),0)::text,
        coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('WIP')),0)::text from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
        where j.status in('POSTED','REVERSED') and j.transaction_date<=%s""",(day,))
    return dict(sewn=int(sewn[0] or 0),ready=int(sewn[1] or 0),posted_work=len(works),completion=completion,
        wage_journal=[[str(x) for x in c.wage_journal(cur,w)] for w,_ in works],
        note=None if not note else dict(status=note[0],payroll=note[1]),
        payroll=None if not pay else dict(id=pay[0],number=pay[1],status=pay[2],period_start=pay[3],period_end=pay[4],labor=pay[5],net=pay[6],payment_date=pay[7],bank=pay[8]),
        payment=payment,capital=cash_journal(cur,'j.id=%s',(p['capital'],)),bank_balance=bank_balance(cur,p['bank']),mandor_payable=payable,
        cash_day=dict(debit=cash_day[0],credit=cash_day[1]),report=dict(cash=report[0],wip=report[1]),
        closed_through=text(closed(cur)),filings_on_day=row(cur,'select count(*) from erp.accounting_close_filings_v1 where closed_through=%s',(day,))[0])


# ---------------------------------------------------------------- chain (b): FG -> invoice -> customer payment -> cash -> AR zero
def browser_sale_prepare(cur,today):
    import cp7_fg_cases as fg
    c=cp17();tag='R3S'+uuid.uuid4().hex[:8].upper()
    f=fg.fixture(cur,today,5);c.b.api.admin(cur)
    customer=str(fg.base.create_customer(cur,tag));c.b.api.admin(cur)
    bank=str(c.bc.bank_account(cur,tag));c.b.api.admin(cur)
    return dict(code=tag,customer=customer,product=f['product'],lot=f['lot'],sku=f['sku'],location=str(f['location']),stock=5,qty=2,price='15000',total='30000.00',
        bank=bank,bank_code=bank_code(cur,bank),day=str(today))

def browser_sale_state(cur,p):
    cp17().b.api.admin(cur)
    sale=row(cur,"""select h.id::text,h.status,(select coalesce(sum(i.qty_pcs),0) from erp.sales_items i where i.sale_id=h.id),
        (select coalesce(sum(i.qty_pcs*i.unit_price_snapshot-i.discount_amount),0) from erp.sales_items i where i.sale_id=h.id)::text
        from erp.sales_headers h where h.sale_number=%s""",(p['code'],))
    payments=[list(r) for r in cur.execute("""select payment_number,amount::text,status,cash_account_id::text from erp.sales_payments
        where sale_id=%s order by payment_number""",(sale[0],)).fetchall()] if sale else []
    ar=row(cur,"""select coalesce(sum(l.debit),0)::text,coalesce(sum(l.credit),0)::text,coalesce(sum(l.debit-l.credit),0)::text from erp.journal_lines l
        join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED') and l.customer_id=%s and l.account_id=erp.account_id('AR_CUSTOMER')""",(p['customer'],))
    receipt=cash_journal(cur,"j.status='POSTED' and exists(select 1 from erp.journal_lines x where x.journal_entry_id=j.id and x.account_id=(select coa_account_id from erp.cash_accounts where id=%s))",(p['bank'],))
    return dict(sale=None if not sale else dict(id=sale[0],status=sale[1],qty=int(sale[2]),total=sale[3]),payments=payments,
        stock=int(row(cur,'select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',(p['lot'],))[0]),
        ar=dict(debit=ar[0],credit=ar[1],balance=ar[2]),bank_balance=bank_balance(cur,p['bank']),receipt=receipt)


# ---------------------------------------------------------------- guards (c): D14-2, D14-3/D15-1, D15-5 on the screens
def browser_guard_prepare(cur,today):
    import cp7_cash_funding as funding
    c=cp17();c.b.api.admin(cur);prev=closed(cur)
    f,pid,net=c.approved_payroll(cur,today,attendance=False);c.b.api.admin(cur)
    # Oracle: the day the payroll's last payable was recognised, from the contractor's own accrual journals.
    accrued=c.accrued_day(cur,f['contractor']);c.b.api.admin(cur)
    label='Mandor R3-03 Penjaga '+uuid.uuid4().hex[:8].upper()
    cur.execute('update erp.contractors set contractor_name=%s where id=%s',(label,f['contractor']))
    tag=uuid.uuid4().hex[:8].upper()
    # Codes start with 0 so the banks and the category sort first in the paged pickers of Jurnal & Transaksi Lain.
    funded,empty,shifted=(str(c.bc.bank_account(cur,'0R3'+k+tag)) for k in ('F','E','K'));c.b.api.admin(cur)
    # D15-1: capital dated inside a closed period is booked on the first open day; the period is then reopened before
    # it, so a kasbon on the capital's own date fits the economic-date balance but not the book-date balance.
    capital_day,kasbon_day=accrued-timedelta(days=8),accrued-timedelta(days=8)
    set_closed(cur,accrued-timedelta(days=6),'CP17 R3-03 modal di periode tertutup');funding.fund(cur,shifted,'2500.00',capital_day);c.b.api.admin(cur)
    set_closed(cur,accrued-timedelta(days=10),'CP17 R3-03 periode dibuka sebelum tanggal modal')
    funding.fund(cur,funded,str(net),accrued-timedelta(days=3));c.b.api.admin(cur)
    category=str(row(cur,"""insert into erp.misc_finance_categories(category_code,category_name,category_type,default_account_id)
        values(%s,%s,'OTHER_INCOME',erp.account_id('OTHER_INCOME'))returning id""",('0R3G'+tag,'R3-03 pendapatan lain '+tag))[0])
    return dict(payroll=str(pid),payroll_number=row(cur,'select payroll_number from erp.payroll_settlements where id=%s',(pid,))[0],
        contractor=str(f['contractor']),mandor_label=label,net=str(net),accrued=str(accrued),early=str(accrued-timedelta(days=1)),
        bank_f=funded,bank_f_code=bank_code(cur,funded),bank_e=empty,bank_e_code=bank_code(cur,empty),bank_e_name=bank_name(cur,empty),
        bank_k=shifted,bank_k_code=bank_code(cur,shifted),bank_k_name=bank_name(cur,shifted),kasbon_day=str(kasbon_day),kasbon_amount='2500.00',
        e_minus=str(D(bank_balance(cur,empty))-D(str(net))),k_minus=str(D('0.00')-D('2500.00')),
        category=category,misc_number='R3G-'+tag,previous_closed=text(prev),opened_closed=text(closed(cur)))

def browser_guard_cutover(cur,p):
    """D15-5 step only: the official cutover date at the latest day the books allow (the first operational day), through
    the cutover command as the owner; the case moves it back to 2000-01-03 with the existing cutover_reset operation."""
    import cp7_cutover_cases as cutover
    o=cutover.owner(cur);latest=cutover.latest(cur)[0];v,d=cutover.control(cur)
    if d!=latest:cutover.put(cur,o,latest,v,'CP17 R3-03 batas tanggal mulai pakai untuk uji layar')
    v2,d2=cutover.control(cur);cp17().b.api.admin(cur);assert d2==latest,(d2,latest)
    return dict(cutover_date=str(d2),before_day=str(d2-timedelta(days=1)),version=v2,previous_version=v,previous_date=text(d))

def browser_guard_state(cur,p):
    c=cp17();c.b.api.admin(cur)
    pay=row(cur,"""select status,payment_date::text,payment_cash_account_id::text,net_payable::text,row_version::text,md5(to_jsonb(s)::text)
        from erp.payroll_settlements s where id=%s""",(p['payroll'],))
    journals=[list(r) for r in cur.execute("""select source_type,status,count(*) from erp.journal_entries where source_id=%s group by 1,2 order by 1,2""",(p['payroll'],)).fetchall()]
    misc=row(cur,'select id::text,status,(physical_at at time zone \'Asia/Jakarta\')::date::text,amount::text from erp.misc_finance_transactions where transaction_number=%s',(p['misc_number'],))
    cut=row(cur,'select version,cutover_date::text from cp7_cutover.control where singleton_id=1')
    return dict(payroll=dict(status=pay[0],payment_date=pay[1],bank=pay[2],net=pay[3],version=pay[4],row_md5=pay[5]),payroll_journals=journals,
        banks={k:dict(balance=bank_balance(cur,p[k]),book=bank_book(cur,p[k])) for k in ('bank_f','bank_e','bank_k')},
        kasbon=row(cur,'select count(*) from cp7_kasbon.advances where contractor_id=%s',(p['contractor'],))[0],
        receivable=str(c.receivable(cur,p['contractor'])),
        misc=None if not misc else dict(id=misc[0],status=misc[1],day=misc[2],amount=misc[3],
            journals=row(cur,"select count(*) from erp.journal_entries where source_type='MISC_FINANCE' and source_id=%s",(misc[0],))[0]),
        cutover=dict(version=cut[0],date=cut[1]),journals=row(cur,'select count(*) from erp.journal_entries')[0],lines=row(cur,'select count(*) from erp.journal_lines')[0])


def browser_restore(cur,p):
    """Harness state back: the closed-through date the copy had before the case."""
    set_closed(cur,p['previous_closed'],'CP17 R3-03 harness state restored')
    return dict(closed_through=p['previous_closed'])
