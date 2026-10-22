"""OW-09 (owner D17-16) Native cases: sort and filter apply to the whole matching list before the page is cut.

Each case builds more matching rows than one page through the accepted writers (pages of 2-4 rows), then walks every
page of every order, status/type filter and search through the public reader as the real actor. The oracle is computed
independently from the Native tables with the readers' documented natural label key (digit runs by value, text runs
lower-cased, byte order, then the existing source order). Count, matching sums and the list echo must equal the oracle.
Every old call (no new key) is read on the patched reader and, inside a rolled-back savepoint, on the exact original
definitions the stage replaced: the answers must be equal apart from the statement read time. Reading changes no
business row. Fixture rows are prepared for isolation only; these cases do not claim that an operator created them
from the screen.
"""
from datetime import timedelta
from decimal import Decimal as D
import json,re,uuid
import cp7_finance_analysis_cases as analysis
import cp7_sales_payment_cases as payments
import cp7_sales_return_cases as returns
import cp7_nota_cases as notas
import cp7_fg_adjustment_cases as fgadj
import cp7_material_count_cases as counts
import cp7_f03_e24_issue_cases as issue
from cp7_ow09_lists import native_delta

IDS=('OW09_CASH_LEDGER_WHOLE_PERIOD','OW09_INVOICE_PAYMENTS_WHOLE_HISTORY','OW09_INVOICE_RETURNS_WHOLE_HISTORY',
     'OW09_SAVED_NOTES_WHOLE_LIST','OW09_FG_DOCUMENTS_AND_CARD_WHOLE_LIST','OW09_MATERIAL_COUNT_DOCUMENTS_WHOLE_LIST',
     'OW09_ACCESSORY_NOTES_WHOLE_HISTORY','OW09_READERS_PRIVATE_AND_ACCESS_UNCHANGED')
ORDERS=('SOURCE','LABEL_ASC','LABEL_DESC')
ORIGINALS=None  # set by the probe: the exact definitions this stage replaced
REPLACE=None    # set by the probe: installs definitions as their verified existing owners
b=payments.b


def natural(label):
    """The readers' natural label key, written independently of the SQL."""
    def part(p):
        if p[0] in '0123456789':
            digits=p.lstrip('0');return str(len(digits)).rjust(10,'0')+digits
        return p.lower()
    return ''.join(part(p) for p in re.findall(r'[0-9]+|[^0-9]+',label))


def ordered(rows,order,source):
    """source: [(field, descending)] most significant first; ties on the label keep the source order."""
    rows=list(rows)
    for field,descending in reversed(source):rows.sort(key=lambda r:r[field],reverse=descending)
    if order!='SOURCE':rows.sort(key=lambda r:natural(r['label']).encode(),reverse=order=='LABEL_DESC')
    return [r['id'] for r in rows]


def text_match(q,*values):
    return not q or q.lower() in ' '.join(str(v) for v in values if v is not None).lower()


def walk(read,page_of,limit):
    """Every page through next_offset: same total and echo on each page, contiguous offsets, no row twice."""
    ids,totals,echoes,offset,pages=[],set(),set(),0,0
    while True:
        p=page_of(read(offset));pages+=1
        assert p['offset']==offset and p['limit']==limit and len(p['rows'])<=limit,(offset,p['offset'],p['limit'])
        totals.add(p['total']);echoes.add(json.dumps(p.get('list'),sort_keys=True));ids+=[r['id'] for r in p['rows']]
        if p['next_offset'] is None:break
        assert p['next_offset']==offset+len(p['rows']) and p['rows'];offset=p['next_offset']
    assert len(totals)==1 and len(echoes)==1 and len(ids)==len(set(ids)),(totals,echoes)
    return dict(ids=ids,total=totals.pop(),pages=pages,list=json.loads(echoes.pop()))


def check(read,page_of,limit,want,echo):
    got=walk(read,page_of,limit)
    assert got['ids']==want,('OW09_ORDER_OR_FILTER_DIFFERS',got['ids'],want)
    assert got['total']==str(len(want)) and got['list']==echo,(got['total'],len(want),got['list'],echo)
    return got['pages']


def timeless(value):
    """Read times are the statement time of each call; everything else must be equal."""
    if isinstance(value,dict):return {k:timeless(v)for k,v in value.items()if k not in('read_at','captured_at')}
    if isinstance(value,list):return [timeless(v)for v in value]
    return value


def pages(read,page_of):
    """Every raw answer of an old call through next_offset."""
    out,offset=[],0
    while True:
        r=read(offset);out.append(timeless(r));offset=page_of(r).get('next_offset')
        if offset is None:return out


def original(cur,fn):
    """The same state read through the exact original definitions, then restored."""
    name='ow09_original_'+uuid.uuid4().hex
    b.api.admin(cur);cur.execute('savepoint '+name)
    try:
        REPLACE(cur,ORIGINALS)
        b.api.admin(cur)
        return fn()
    finally:
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);b.api.admin(cur)


def same_old(cur,fn,least=2):
    """An old call answers exactly as the original reader on the same rows (fn returns every answer it read)."""
    now=fn();before=original(cur,fn)
    assert now==before,('OW09_OLD_CALL_CHANGED',now,before)
    assert len(now)>=least,len(now)
    return len(now)


def cases(cur,today):
    def cash_ledger():
        # Seven cash journals on one day with distinct values; two are reversed.
        day=today-timedelta(days=1);analysis.receipt.aa.prior.set_open_period(cur,day-timedelta(days=2));tag='OW09KAS'+uuid.uuid4().hex[:10]
        made=[str(analysis.journal(cur,day,[dict(mapping_key='CASH',debit=f'{i}.25'),dict(mapping_key='OPENING_EQUITY',credit=f'{i}.25')],tag))for i in range(1,8)]
        for jid in made[:2]:analysis.fixture_journal_call(cur,'select erp.reverse_journal(%s,%s)',(jid,'OW-09 list status fixture'))
        b.api.admin(cur);base=analysis.query(day)
        cash=cur.execute("select array_agg(x.id)from(select coa_account_id id from erp.cash_accounts union select erp.account_id('CASH'))x").fetchone()[0]
        rows=[dict(id=str(i),label=n,status=s,source_type=t,source_id=sid,economic=str(e),transaction=str(td),posting=p,debit=d,credit=c)
              for i,n,s,t,sid,e,td,p,d,c in cur.execute("""select j.id,j.journal_number,j.status,j.source_type,j.source_id,j.economic_date,j.transaction_date,j.posting_at,sum(l.debit),sum(l.credit)
               from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
               where j.status in('POSTED','REVERSED')and j.transaction_date between %s and %s and l.account_id=any(%s) group by j.id""",(day,day,cash)).fetchall()]
        source=[('transaction',False),('posting',False),('id',False)];before=b.boundary.snapshot(cur);combos=0
        old=walk(lambda o:analysis.read(cur,dict(base,offset=o,limit=3)),lambda r:r['cash']['entries'],3)
        assert old['ids']==ordered(rows,'SOURCE',source) and old['list'] is None
        same=same_old(cur,lambda:pages(lambda o:analysis.read(cur,dict(base,offset=o,limit=3)),lambda r:r['cash']['entries']))
        period=analysis.read(cur,base)['cash']
        for order in ORDERS:
            for status in (None,'POSTED','REVERSED'):
                for q in ('',tag):
                    keep=[r for r in rows if(status is None or r['status']==status)and text_match(q,r['label'],r['source_type'],r['source_id'],r['economic'],r['transaction'])]
                    query=dict(base,limit=3,entry_q=q,entry_status=status,entry_order=order)
                    check(lambda o:analysis.read(cur,dict(query,offset=o)),lambda r:r['cash']['entries'],3,ordered(keep,order,source),dict(q=q,status=status,order=order))
                    first=analysis.read(cur,dict(query,offset=0))['cash'];sums=first['entries']['sums']
                    assert (D(sums['debit']),D(sums['credit']))==(sum((r['debit']for r in keep),D(0)),sum((r['credit']for r in keep),D(0)))
                    assert D(sums['net'])==D(sums['debit'])-D(sums['credit'])
                    assert [first[k]for k in('opening','closing','debit','credit')]==[period[k]for k in('opening','closing','debit','credit')]
                    combos+=1
        mine=[r for r in rows if r['source_type'].lower()==tag.lower()];assert len(mine)==7 and sum(r['status']=='REVERSED'for r in mine)==2
        for bad in (dict(entry_status='DRAFT'),dict(entry_order='RANDOM'),dict(entry_q=3),dict(entry_order=None)):
            analysis.auth.refused(cur,lambda:analysis.read(cur,dict(base,**bad)),'CP7_FINANCE_ANALYSIS_QUERY')
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',journals_in_period=len(rows),fixture_journals=7,reversed=2,page_rows=3,combinations=combos,
                    old_call_pages_equal_to_original_reader=same,count_and_matching_sums_equal_oracle=True,period_balances_unfiltered=True,no_business_side_effect=True)

    def invoice_payments():
        f=payments.fixture(cur,today,qty=4,price='20');tag=f['tag'];ids=[]
        for n in ('1','2','10','11','3','20','7','07'):
            p,v=payments.payment_payload(cur,f,'1');p['payment_number']=f'{tag}-{n}';p['notes']='OW09 jarum' if n in('2','20','07')else None
            ids.append(payments.cmd.command(cur,'PAYMENT',p,v)['payment_id'])
        for pid in ids[:2]:payments.inverse(cur,f,pid)
        b.api.admin(cur)
        rows=[dict(id=str(i),label=n,status=s,date=d,search=(n,r,t,a))for i,n,s,d,r,t,a in cur.execute("""select p.id,p.payment_number,p.status,p.payment_date,p.reference_number,p.notes,(select c.cash_account_name from erp.cash_accounts c where c.id=p.cash_account_id)
          from erp.sales_payments p where p.sale_id=%s""",(f['sale'],)).fetchall()]
        source=[('date',True),('id',False)];before=b.boundary.snapshot(cur);combos=0
        old=walk(lambda o:payments.cash(cur,f,payment_offset=o,payment_limit=3),lambda r:r['payments'],3)
        assert old['ids']==ordered(rows,'SOURCE',source) and old['list'] is None
        same=same_old(cur,lambda:pages(lambda o:payments.cash(cur,f,payment_offset=o,payment_limit=3),lambda r:r['payments']))
        for order in ORDERS:
            for status in (None,'POSTED','REVERSED','DRAFT'):
                for q in ('','JARUM',tag+'-1'):
                    keep=[r for r in rows if(status is None or r['status']==status)and text_match(q,*r['search'])]
                    check(lambda o:payments.cash(cur,f,payment_offset=o,payment_limit=3,payment_q=q,payment_status=status,payment_order=order),lambda r:r['payments'],3,ordered(keep,order,source),dict(q=q,status=status,order=order));combos+=1
        for bad in (dict(payment_status='PAID'),dict(payment_order='NEWEST'),dict(payment_q=None)):
            payments.auth.refused(cur,lambda:payments.cash(cur,f,**bad),'CP7_SALES_CASH_QUERY')
        assert b.boundary.snapshot(cur)==before
        # Access is unchanged: an actor without payment view is refused before any list work.
        subject,role=payments.auth.custom_actor(cur);cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.ar.view')",(role,))
        denied=b.boundary.snapshot(cur);payments.auth.refused(cur,lambda:payments.cash(cur,f,subject,payment_order='LABEL_ASC'),'CP7_SALES_CASH_DENIED');assert b.boundary.snapshot(cur)==denied
        return dict(status='PASS',payments=len(rows),reversed=2,page_rows=3,combinations=combos,natural_order_and_tie_on_7_and_07=True,
                    old_call_pages_equal_to_original_reader=same,access_unchanged=True,no_business_side_effect=True)

    def invoice_returns():
        f=returns.source.fixture(cur,today,qty=9);returns.source.fg.post_sale(cur,f['draft']);f['destination']=returns.location(cur);f['allocations']=returns.read(cur,f)['page']['rows']
        tag=f['tag'];made=[]
        for n in ('R1','R2','R10','R11','R3','R20','R07'):
            p,v=returns.payload(cur,f,qty='1',refund='1');p['return_number']=f'{tag}-{n}';p['notes']='OW09 jarum' if n in('R2','R20')else None
            made.append(returns.cmd.command(cur,'RETURN',p,v)['return_id'])
        for rid in made[:2]:returns.inverse(cur,f,rid)
        b.api.admin(cur)
        lines={}
        for rid,sku,lot,loc,notes in cur.execute("""select i.return_id,p.sku,l.lot_number,w.location_name,i.notes from erp.sales_return_items i join erp.products p on p.id=i.product_id
          join erp.fg_lots l on l.id=i.lot_id join erp.locations w on w.id=i.location_id join erp.sales_returns r on r.id=i.return_id where r.sale_id=%s""",(f['sale'],)).fetchall():
            lines.setdefault(str(rid),[]).append((sku,lot,loc,notes))
        rows=[dict(id=str(i),label=n,status=s,date=d,notes=t)for i,n,s,d,t in cur.execute('select id,return_number,status,physical_at,notes from erp.sales_returns where sale_id=%s',(f['sale'],)).fetchall()]
        source=[('date',True),('id',False)];before=b.boundary.snapshot(cur);combos=0;lot=f['allocations'][0]['lot_number']
        old=walk(lambda o:returns.read(cur,f,'RETURNS',offset=o,limit=2),lambda r:r['page'],2)
        assert old['ids']==ordered(rows,'SOURCE',source) and old['list'] is None
        same=same_old(cur,lambda:pages(lambda o:returns.read(cur,f,'RETURNS',offset=o,limit=2),lambda r:r['page'])
            +[timeless(returns.read(cur,f,'LOCATIONS'))])
        for order in ORDERS:
            for status in (None,'POSTED','REVERSED'):
                for q in ('','jarum',lot):
                    keep=[r for r in rows if(status is None or r['status']==status)and(text_match(q,r['label'],r['notes'])or any(text_match(q,*x)for x in lines.get(r['id'],[])))]
                    check(lambda o:returns.read(cur,f,'RETURNS',offset=o,limit=2,q='',history_q=q,history_status=status,history_order=order),lambda r:r['page'],2,ordered(keep,order,source),dict(q=q,status=status,order=order));combos+=1
        returns.auth.refused(cur,lambda:returns.read(cur,f,'LOCATIONS',history_order='SOURCE'),'CP7_SALES_RETURN_QUERY')
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',returns=len(rows),reversed=2,page_rows=2,combinations=combos,line_search_on_every_page=True,
                    old_call_pages_equal_to_original_reader=same,other_kinds_refuse_history_keys=True,no_business_side_effect=True)

    def saved_notes():
        f=notas.source.repair(cur,today);notas.source.ax.post(cur,notas.source.ax.repair_payload(f,1));p=notas.payload(cur,f,today)
        for _ in range(5):notas.act(cur,'VOID',notas.command(cur,'SAVE',p))
        notas.act(cur,'POST',notas.command(cur,'SAVE',dict(p,notes='OW09 jarum')))
        b.api.admin(cur)
        rows=[dict(id=str(i),label=n,status=s,created=c,search=(n,name,t))for i,n,s,c,name,t in cur.execute("""select h.id,h.note_number,h.status,h.created_at,c.contractor_name,h.notes
          from cp7_payroll.notes h join erp.contractors c on c.id=h.contractor_id where h.contractor_id=%s""",(f['contractor'],)).fetchall()]
        assert len(rows)==6;source=[('created',True),('id',False)];before=b.boundary.snapshot(cur);combos=0
        old=walk(lambda o:notas.read(cur,'NOTES',contractor_id=f['contractor'],offset=o,limit=2),lambda r:r['page'],2)
        assert old['ids']==ordered(rows,'SOURCE',source) and old['list'] is None
        same=same_old(cur,lambda:pages(lambda o:notas.read(cur,'NOTES',contractor_id=f['contractor'],offset=o,limit=2),lambda r:r['page']))
        for order in ORDERS:
            for status in (None,'DRAFT','POSTED','VOID'):
                for q in ('','jarum'):
                    keep=[r for r in rows if(status is None or r['status']==status)and text_match(q,*r['search'])]
                    check(lambda o:notas.read(cur,'NOTES',contractor_id=f['contractor'],q=q,offset=o,limit=2,status=status,order=order),lambda r:r['page'],2,ordered(keep,order,source),dict(q=q,status=status,order=order));combos+=1
        notas.auth.refused(cur,lambda:notas.read(cur,'PAYROLLS',contractor_id=f['contractor'],order='SOURCE'),'CP7_NOTA_QUERY')
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',notes=6,void=5,posted=1,page_rows=2,combinations=combos,empty_status_answers_zero=True,
                    old_call_pages_equal_to_original_reader=same,no_business_side_effect=True)

    def fg_documents_and_card():
        f=fgadj.fg.fixture(cur,today);tag='OW09A'+uuid.uuid4().hex[:10]
        def save(n,note=None):
            p=fgadj.payload(cur,f,'-1');p['adjustment_number']=f'{tag}-{n}'
            if note:p['notes']=note
            return fgadj.command(cur,'SAVE',p)
        fgadj.action(cur,'REVERSE',fgadj.action(cur,'POST',save('1')));fgadj.action(cur,'POST',save('10','OW09 jarum'))
        for n in ('2','11','3','03'):save(n)
        b.api.admin(cur)
        docs=[dict(id=str(i),label=n,status=s,date=d)for i,n,s,d in cur.execute('select id,adjustment_number,status,physical_at from erp.fg_adjustments where strpos(lower(adjustment_number),lower(%s))>0',(tag,)).fetchall()]
        source=[('date',True),('id',False)];before=b.boundary.snapshot(cur);combos=0
        old=walk(lambda o:fgadj.read(cur,None,q=tag,offset=o,limit=2),lambda r:r['page'],2)
        assert old['ids']==ordered(docs,'SOURCE',source) and old['list'] is None
        same=same_old(cur,lambda:pages(lambda o:fgadj.read(cur,None,q=tag,offset=o,limit=2),lambda r:r['page']))
        for order in ORDERS:
            for status in (None,'DRAFT','POSTED','REVERSED'):
                for q in (tag,tag+'-1'):
                    keep=[r for r in docs if(status is None or r['status']==status)and text_match(q,r['label'])]
                    check(lambda o:fgadj.read(cur,None,q=q,offset=o,limit=2,status=status,order=order),lambda r:r['page'],2,ordered(keep,order,source),dict(q=q,status=status,order=order));combos+=1
        # The same position's movement card: opening stock, two posted adjustments and one reversal.
        assert cur.execute('select count(*)from cp7_fg.correction_movements c join erp.fg_stock_movements m on m.id=c.member_id where m.lot_id=%s',(f['lot'],)).fetchone()[0]==0
        moves=[dict(id=str(i),physical=ph,recorded=rc,type=t,label=f'{sku} {cust or ""} {t}',search=(st,str(sid)if sid else None,cust,notes,t,sku))
               for i,ph,rc,t,st,sid,cust,notes,sku in cur.execute("""select m.id,m.physical_at,m.system_created_at,m.movement_type,m.source_type,m.source_id,c.customer_name,m.notes,erp.bf_commercial_sku_at_v1(m.product_id,m.physical_at)
                from erp.fg_stock_movements m left join erp.customers c on c.id=m.customer_id
                where m.product_id=%s and m.lot_id=%s and m.location_id=%s and m.quality_grade='GRADE_A' and m.physical_at<=statement_timestamp()""",(f['product'],f['lot'],f['location'])).fetchall()]
        kinds=sorted({m['type']for m in moves},key=str.encode);assert len(moves)>=4 and len(kinds)>=2,(len(moves),kinds)
        position=dict(product_id=f['product'],lot_id=f['lot'],location_id=f['location'],quality_grade='GRADE_A')
        def card(**q):
            fgadj.auth.actor(cur);r=cur.execute('select public.erp_cp7_get_fg_ledger_v2(%s::jsonb)',(json.dumps(dict(position,purpose='CARD',**q)),)).fetchone()[0];b.api.admin(cur);return r
        whole=card();movement=[('physical',False),('recorded',False),('id',False)]
        old=walk(lambda o:card(offset=o,limit=2),lambda r:r['page'],2);assert old['ids']==ordered(moves,'SOURCE',movement) and old['list'] is None
        same+=same_old(cur,lambda:pages(lambda o:card(offset=o,limit=2),lambda r:r['page']))
        for order in ORDERS:
            for kind in (None,*kinds):
                for q in ('','fg_adjustment'):
                    keep=[m for m in moves if(kind is None or m['type']==kind)and text_match(q,*m['search'])]
                    check(lambda o:card(q=q,offset=o,limit=2,movement_type=kind,order=order),lambda r:r['page'],2,ordered(keep,order,movement),dict(q=q,movement_type=kind,order=order,movement_types=kinds))
                    assert card(q=q,limit=2,movement_type=kind,order=order)['balances']==whole['balances'];combos+=1
        fgadj.auth.refused(cur,lambda:card(movement_type='sale'),'CP7_FG_QUERY');fgadj.auth.refused(cur,lambda:fgadj.read(cur,None,status='VOID'),'CP7_FG_ADJUST_QUERY')
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',documents=len(docs),movements=len(moves),movement_types=kinds,page_rows=2,combinations=combos,
                    card_balances_keep_complete_prefix=True,old_call_pages_equal_to_original_reader=same,no_business_side_effect=True)

    def material_count_documents():
        f=counts.raw.fixture(cur,today);tag=f['tag']
        def save(n):p=counts.payload(cur,f);p['adjustment_number']=f'{tag}-N{n}';return counts.command(cur,'SAVE',p)
        counts.action(cur,'REVERSE',counts.action(cur,'POST',save('1')));counts.action(cur,'POST',save('10'))
        for n in ('2','11','3','03'):save(n)
        b.api.admin(cur)
        docs=[dict(id=str(i),label=n,status=s,date=d)for i,n,s,d in cur.execute('select id,adjustment_number,status,physical_at from erp.material_adjustments where strpos(lower(adjustment_number),lower(%s))>0',(tag,)).fetchall()]
        source=[('date',True),('id',False)];before=b.boundary.snapshot(cur);combos=0
        old=walk(lambda o:counts.read(cur,None,q=tag,offset=o,limit=2),lambda r:r['page'],2)
        assert old['ids']==ordered(docs,'SOURCE',source) and old['list'] is None and len(docs)==6
        same=same_old(cur,lambda:pages(lambda o:counts.read(cur,None,q=tag,offset=o,limit=2),lambda r:r['page']))
        for order in ORDERS:
            for status in (None,'DRAFT','POSTED','REVERSED'):
                for q in (tag,tag+'-N1'):
                    keep=[r for r in docs if(status is None or r['status']==status)and text_match(q,r['label'])]
                    check(lambda o:counts.read(cur,None,q=q,offset=o,limit=2,status=status,order=order),lambda r:r['page'],2,ordered(keep,order,source),dict(q=q,status=status,order=order));combos+=1
        counts.auth.refused(cur,lambda:counts.read(cur,None,order='NEWEST'),'CP7_COUNT_QUERY')
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',documents=6,page_rows=2,combinations=combos,old_call_pages_equal_to_original_reader=same,no_business_side_effect=True)

    def accessory_notes():
        # Eight accessory notes through the connected note writer: three drafts, three posted, two posted then reversed,
        # on three business days; labels tie on 7 = 07 so the source order (date desc, id) must break the tie.
        f=issue.receipt(cur,today,qty='30');tag=f['code'];bc=issue.bc;made=[]
        for k,n in enumerate(('1','2','10','11','3','20','7','07')):
            p=issue.payload(f);p.update(number=f'{tag}-N{n}',location_id=f['main'],physical_at=bc.local_at(today-timedelta(days=1+k%3),9+k),
                reason='OW-09 list fixture '+n,notes='OW09')
            p['items'][0]['qty']='1'
            draft=bc.note_call(cur,'SAVE_DRAFT',p);made.append(str(draft['id']))
            if k%3:
                p.update(id=draft['id'],expected_version=draft['row_version']);posted=bc.note_call(cur,'POST',p)
                if k in(1,4):bc.note_call(cur,'REVERSE',dict(id=posted['id'],expected_version=posted['row_version'],reason='OW-09 list status fixture'))
        b.api.admin(cur)
        # Oracle: the reader's documented accessory scope (no line outside COUNT accessories), read from the tables.
        every=[dict(id=str(i),label=n,status=s,date=str(d),contractor=c)for i,n,s,d,c in cur.execute("""select h.id,h.issue_number,h.status,(h.physical_at at time zone 'Asia/Jakarta')::date,c.contractor_name
          from erp.contractor_material_issues h join erp.contractors c on c.id=h.contractor_id where not exists(select 1 from erp.contractor_material_issue_items i
          join erp.materials m on m.id=i.material_id join erp.uom_definitions u on u.unit_code=m.unit_code where i.issue_id=h.id and(m.material_type<>'ACCESSORY'or u.dimension<>'COUNT'))""").fetchall()]
        rows=[r for r in every if r['id']in made];assert len(rows)==8 and sorted(r['status']for r in rows)==['DRAFT']*3+['POSTED']*3+['REVERSED']*2,rows
        source=[('date',True),('id',False)];before=b.boundary.snapshot(cur);combos=0
        read=lambda **q:bc.note_read(cur,q)
        page_of=lambda r:dict(rows=r['history'],total=str(r['history_count']),**r['history_page'])
        old=read(query=tag);assert [h['id']for h in old['history']]==ordered(rows,'SOURCE',source)and old['history_count']==8 and 'history_page' not in old
        plain=lambda r:timeless({k:v for k,v in r.items()if k!='physical_local'})
        same=same_old(cur,lambda:[plain(read(**q))for q in(dict(query=tag),dict(query=tag+'-N1'),dict(id=made[2]),dict(),
            dict(contractor_id=f['mandor'],location_id=f['main'],physical_at=bc.local_at(today,8),material_ids=[f['material']],material_query=''))],least=5)
        for order in ORDERS:
            for status in (None,'DRAFT','POSTED','REVERSED'):
                for q in (tag,tag+'-N1'):
                    keep=[r for r in rows if(status is None or r['status']==status)and text_match(q,r['label'],r['contractor'])]
                    check(lambda o:read(query=q,history_status=status,history_order=order,history_offset=o,history_limit=2),page_of,2,
                          ordered(keep,order,source),dict(q=q,status=status,order=order));combos+=1
        # The whole accessory history (every note in this database), beyond the old cap of 50 when there are more.
        whole=check(lambda o:read(history_offset=o,history_limit=50),page_of,50,ordered(every,'SOURCE',source),dict(q='',status=None,order='SOURCE'))
        capped=read();assert capped['history_count']==len(every)and len(capped['history'])==min(50,len(every))
        listed=read(query=tag,history_order='LABEL_ASC',history_offset=0,history_limit=2)
        assert [sorted(h)for h in listed['history']]==[sorted(h)for h in old['history'][:2]]and listed['filters']==dict(query=tag,history_order='LABEL_ASC',history_offset=0,history_limit=2)
        for bad in (dict(history_status='VOID'),dict(history_status=3),dict(history_order=None),dict(history_order='NEWEST'),dict(history_offset=-1),
                    dict(history_offset=1.5),dict(history_offset='0'),dict(history_offset=2000000),dict(history_limit=0),dict(history_limit=51),dict(history_limit='5')):
            payments.auth.refused(cur,lambda:read(**bad),'Daftar nota tidak valid')
        for bad in (dict(limit=5),dict(offset=0),dict(status='POSTED')):payments.auth.refused(cur,lambda:read(**bad),'unexpected key')
        assert b.boundary.snapshot(cur)==before
        # Access is unchanged: without the view permission the reader refuses before any list work.
        subject,_=payments.auth.custom_actor(cur);denied=b.boundary.snapshot(cur)
        payments.auth.refused(cur,lambda:bc.note_read(cur,dict(history_order='LABEL_ASC'),auth=subject),'PERMISSION_DENIED: finance.contractor_accessory.view')
        assert b.boundary.snapshot(cur)==denied
        return dict(status='PASS',notes=8,drafts=3,posted=3,reversed=2,page_rows=2,combinations=combos,accessory_notes_in_database=len(every),
                    whole_history_pages_of_50=whole,old_cap_still_50_for_old_calls=True,old_calls_equal_to_original_reader=same,
                    access_unchanged=True,no_business_side_effect=True)

    def private():
        details=[]
        for sig in native_delta.SIGNATURES:
            name,args=sig.split('(')[0],sig.split('(')[1].rstrip(')').split(',')
            values=["'NOTES'"if a=='text'else"'{}'::jsonb"for a in args]
            def attempt(sql='select '+name+'('+','.join(values)+')'):
                payments.auth.actor(cur);return cur.execute(sql).fetchone()[0]
            details.append(dict(reader=sig,refusal=payments.auth.refused(cur,attempt,'permission denied')))
        b.api.admin(cur)
        granted={sig:cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')",(sig,)).fetchone()[0]for sig in native_delta.PUBLIC.values()}
        assert all(granted.values()),granted
        return dict(status='PASS',authenticated_direct_call_refused=details,public_readers_still_executable=granted)

    operations=(cash_ledger,invoice_payments,invoice_returns,saved_notes,fg_documents_and_card,material_count_documents,accessory_notes,private)
    assert len(operations)==len(IDS)
    return list(zip(IDS,operations))
