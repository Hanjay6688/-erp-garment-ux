"""OW-08b Native cases (D17-13 2.21): FG corrections open from the ledger and a refused QC reversal names its blockers.

Business rows come only from retained Native writers: the CP17 laundry/QC chain (c17.finish_fixture), the sale draft
writer and its cancellation, the CP7 FG adjustment, sale and return commands, the qualified rework chain, PO finish and
reopen, and REVERSE_FINAL_SKU. The exact predecessor functions (the kasbon-stage reader, the AZ erp.reverse_qc and the
CP6 QC workspace) are read side by side on the same state inside a rolled-back savepoint: every refusal keeps its
condition, SQLSTATE and first sentence and only gains names; an FG inverse the old reader called UNSUPPORTED now opens
exactly what its original movement opens.
"""
from pathlib import Path
import json
import re
import uuid

import psycopg

import cp7_cp17_fix_cases as c17
import cp7_fg_adjustment_cases as fgadj
import cp7_fg_cases as fgc
import cp7_procurement_cases as procurement
import cp7_sales_return_cases as returns
import cp7_transaction_source_cases as ts
from cp7_fg_correction_source import native_delta as d

auth,b=c17.auth,c17.b
IDS=('OW08B_FG_QC_REFUSAL_NAMES_SALE_AND_ADJUSTMENT_THEN_UNDO',
     'OW08B_FG_INVERSE_OPENS_SALE_ADJUSTMENT_QC',
     'OW08B_FG_INVERSE_OPENS_RETURN_AND_SALE_REVERSAL',
     'OW08B_FG_QC_REFUSAL_NAMES_REWORK_AND_REWORK_INVERSE_OPENS',
     'OW08B_FG_QC_REFUSAL_NAMES_FINISHED_PO_THEN_REOPEN',
     'OW08B_FG_INVERSE_RIGHTS_AND_UNKNOWN_REFUSED',
     'OW08B_FG_OTHER_SOURCES_UNCHANGED_CENSUS',
     'OW08B_FG_QC_REFUSAL_CENSUS_SAME_CONDITIONS',
     'OW08B_FG_CORRECTION_READERS_PRIVATE')
ORIGINALS=None    # set by the probe: the exact predecessor definitions this stage replaced
AS_OWNER=None     # set by the probe: OW06's verified function_ddl (the reader as its own owner)
AS_POSTGRES=None  # set by the probe: the verified installer switch to postgres (the harness admin role cannot run DDL)
BEFORE=None       # set by the probe: the captured catalog the DDL owner check reads
APP=Path(__file__).resolve().parents[2]/'src/App.tsx'
REASON='OW08b koreksi barang jadi di QC'
NAMES=' Yang harus dibetulkan dulu: 1) '


def one(cur,sql,args=()):
    return cur.execute(sql,args).fetchone()[0]


def nav():
    """The app's own menu: section -> items, read from src/App.tsx (the sidebar the operator sees)."""
    text=APP.read_text()
    block=re.search(r"\n  Produksi: \[.*?\n  Keuangan: \[[^\]]*\],",text,re.S).group(0)
    return {m.group(1):re.findall(r"'([^']+)'",m.group(2))for m in re.finditer(r"\n  ([A-Za-z]+): \[([^\]]*)\]",block)}


def menus_in(text,menu):
    """Every 'Section › Item' named in a text must be an actual sidebar item."""
    found=[]
    for m in re.finditer(r'([A-Z][a-z]+) › ',text):
        items=menu.get(m.group(1))
        assert items is not None,('OW08B_UNKNOWN_MENU_SECTION',m.group(1),text)
        hit=[i for i in items if text[m.end():].startswith(i)]
        assert hit,('OW08B_UNKNOWN_MENU_ITEM',m.group(1),text[m.end():m.end()+40])
        found.append(m.group(1)+' › '+max(hit,key=len))
    return found


def original(cur,fn):
    """The same read through the exact predecessor functions, then restored."""
    name='ow08b_fg_original_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:
        with AS_POSTGRES(cur,'postgres'):
            for sig in d.SIGNATURES:
                if sig==d.SOURCE:
                    with AS_OWNER(cur,sig,BEFORE):cur.execute(ORIGINALS[sig],prepare=False)
                else:cur.execute(ORIGINALS[sig],prepare=False)
        b.api.admin(cur)
        return fn()
    finally:
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);b.api.admin(cur)


def attempt(cur,fn):
    """One call in a rolled-back savepoint: its answer, or its refusal (SQLSTATE, sentence, DETAIL)."""
    name='ow08b_fg_try_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:out=dict(ok=True,result=fn())
    except psycopg.Error as error:
        out=dict(ok=False,sqlstate=error.sqlstate,message=error.diag.message_primary,detail=error.diag.message_detail)
    finally:
        cur.execute('rollback to savepoint '+name);cur.execute('release savepoint '+name);b.api.admin(cur)
    return out


def resolve(cur,kind,ident,subject=None):
    auth.actor(cur,subject)
    r=one(cur,'select public.erp_cp7_resolve_transaction_source_v1(%s::jsonb)',(json.dumps(dict(source_type=kind,source_id=str(ident))),))
    b.api.admin(cur);return r


def read(cur,kind,ident,subject=None):
    """The reader's answer, or its refusal sentence (the same refusal must then come from the compared reader)."""
    r=attempt(cur,lambda:resolve(cur,kind,ident,subject))
    return r['result']if r['ok']else dict(refused=r['message'])


def strip(r):
    return {k:v for k,v in r.items()if k not in('read_at','source')}


def same(a,b_):
    return a==b_ if'refused'in a or'refused'in b_ else strip(a)==strip(b_)


# ---------------------------------------------------------------- Native chain helpers
def chain(cur,today,label):
    """Ten pieces of one PO through sewing, laundry and QC into one FG lot (the retained CP17 chain)."""
    f=c17.finish_fixture(cur,today,label='OW08B-'+label);b.api.admin(cur)
    qc,number,item=cur.execute("""select q.id::text,q.inspection_number,i.id::text from erp.fg_lots l
        join erp.qc_inspection_items i on i.id=l.qc_item_id join erp.qc_inspections q on q.id=i.inspection_id where l.id=%s""",(f['lot'],)).fetchone()
    movement,location=cur.execute("""select id::text,location_id::text from erp.fg_stock_movements
        where source_type='QC_ITEM'and source_id=%s and movement_type='QC_GOOD'and lot_id=%s""",(item,f['lot'])).fetchone()
    return dict(f,qc=qc,qc_number=number,item=item,movement=movement,location=location)


def history(cur,f):
    auth.actor(cur);w=one(cur,"select public.erp_get_laundry_qc_workspace_v1('QC',%s)",(f['qc_number'],));b.api.admin(cur)
    return next(r for r in w['qc_history']if r['qc_inspection_id']==f['qc'])


def reverse(cur,f,key=None):
    """REVERSE_FINAL_SKU from the QC screen: the row version the screen reads, the same reason."""
    version=history(cur,f)['row_version'];auth.actor(cur)
    r=one(cur,"select public.erp_save_laundry_qc_action_v1('REVERSE_FINAL_SKU',%s::jsonb,%s,%s)",
        (json.dumps(dict(qc_inspection_id=f['qc'],reason=REASON)),str(key or uuid.uuid4()),version))
    b.api.admin(cur);return r


def draft_sale(cur,f,qty):
    """A draft invoice reserving goods of the lot (Native erp.save_sale_draft_v2, as P10)."""
    s=fgc.draft(cur,dict(location=f['location'],product=f['product']),qty);b.api.admin(cur)
    s['number']=one(cur,'select sale_number from erp.sales_headers where id=%s',(s['sale_id'],))
    s['movement']=one(cur,"""select m.id::text from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
        where i.sale_id=%s and m.source_type='SALE_ITEM'and m.lot_id=%s""",(s['sale_id'],f['lot']))
    return s


def adjust(cur,f,qty):
    """A posted FG adjustment of the lot (the CP7 FG adjustment command)."""
    saved,_=fgadj.draft(cur,dict(location=f['location'],lot=f['lot'],product=f['product']),qty)
    posted=fgadj.action(cur,'POST',saved)
    return dict(id=saved['adjustment_id'],posted=posted,
        number=one(cur,'select adjustment_number from erp.fg_adjustments where id=%s',(saved['adjustment_id'],)),
        movement=one(cur,"""select m.id::text from erp.fg_stock_movements m join erp.fg_adjustment_items i on i.id=m.source_id
            where i.adjustment_id=%s and m.source_type='FG_ADJUSTMENT_ITEM'and m.reversal_of_id is null""",(saved['adjustment_id'],)))


# ---------------------------------------------------------------- shared oracles
def refusal(cur,f,menu):
    """REVERSE_FINAL_SKU and the QC history row through the patched and the exact original functions, same state."""
    new=attempt(cur,lambda:reverse(cur,f))
    old=original(cur,lambda:attempt(cur,lambda:reverse(cur,f)))
    assert not new['ok']and not old['ok']and new['sqlstate']==old['sqlstate']=='P0001',(new,old)
    assert new['message'].startswith(old['message']+NAMES)and old['detail']is None,(new,old)
    items=json.loads(new['detail'])
    assert items and all(set(x)>={'kind','id','number','menu','source','step'}for x in items),items
    for n,x in enumerate(items[:8],1):
        assert str(n)+') '+x['step']in new['message'],(n,x)
        named=menus_in(x['step'],menu)
        assert(x['menu']is None and'belum'in x['step'])or(menus_in(x['menu'],menu)==[x['menu']]and x['menu']in named),x
    opened={}
    for x in items:
        if x['source']is None:continue
        r=resolve(cur,x['source']['source_type'],x['source']['source_id'])
        assert r['status']=='AVAILABLE',(x,r)
        opened[x['kind']+':'+str(x['number'])]=dict(route=r['document']['route'],number=r['document']['number'])
    row=history(cur,f);old_row=original(cur,lambda:history(cur,f))
    assert row['reversible']is False and old_row['reversible']is False,(row,old_row)
    assert row['reversal_blocker'].startswith(old_row['reversal_blocker']+NAMES),(row,old_row)
    # The screen shows the same list the refusal carries.
    assert row['reversal_blocker'][len(old_row['reversal_blocker']):]==new['message'][len(old['message']):]
    assert {k:v for k,v in row.items()if k!='reversal_blocker'}=={k:v for k,v in old_row.items()if k!='reversal_blocker'}
    return dict(new=new,old=old,items=items,opened=opened,screen=row['reversal_blocker'],old_screen=old_row['reversal_blocker'])


def unblocked(cur,f):
    """Both readers offer the reversal again and both functions commit the same answer for the same request."""
    row=history(cur,f);old_row=original(cur,lambda:history(cur,f))
    assert row==old_row and row['reversible']is True and row['reversal_blocker']is None,(row,old_row)
    key=uuid.uuid4()
    was=original(cur,lambda:attempt(cur,lambda:reverse(cur,f,key)))
    done=reverse(cur,f,key)
    assert was['ok']and was['result']==done and done['status']=='REVERSED',(was,done)
    return done


def compare(cur,f):
    """REVERSE_FINAL_SKU once through each function set, same state and request: same outcome, same condition."""
    key=uuid.uuid4()
    new=attempt(cur,lambda:reverse(cur,f,key));old=original(cur,lambda:attempt(cur,lambda:reverse(cur,f,key)))
    assert new['ok']==old['ok'],(f,new,old)
    if new['ok']:
        assert new['result']==old['result'],(f,new,old);return'REVERSED'
    assert new['sqlstate']==old['sqlstate'],(f,new,old)
    if new['message']==old['message']:
        assert new['detail']==old['detail'],(new,old);return'UNCHANGED:'+old['message'][:60]
    assert new['message'].startswith(old['message']+NAMES)and old['detail']is None and json.loads(new['detail']),(new,old)
    return'NAMED:'+old['message'][:60]


def opens(cur,family,movement,expect,old_supported=False):
    """The FG inverse of `movement` opens exactly what the movement's own source opens."""
    kind,ident=cur.execute('select source_type,source_id::text from erp.fg_stock_movements where id=%s',(movement,)).fetchone()
    assert kind==family and one(cur,"""select count(*)from erp.fg_stock_movements
        where source_type='FG_MOVEMENT_REVERSAL'and source_id=%s and reversal_of_id=%s""",(movement,movement))==1,(kind,movement)
    new=resolve(cur,'FG_MOVEMENT_REVERSAL',movement);direct=resolve(cur,kind,ident)
    assert new['status']=='AVAILABLE'and new['business_DML']is False and strip(new)==strip(direct),(new,direct)
    assert {k:new['document'][k]for k in expect}==expect,(new,expect)
    old=original(cur,lambda:read(cur,'FG_MOVEMENT_REVERSAL',movement))
    if old_supported:assert same(old,new),(old,new)
    else:assert old.get('status')=='UNSUPPORTED_SOURCE'and old['document']is None,old
    return dict(family=family,before=old.get('status'),after=new['document'])


def cases(cur,today):
    menu=nav()

    def sale_and_adjustment():
        f=chain(cur,today,'SA')
        start=history(cur,f);assert start['reversible']is True,start
        s=draft_sale(cur,f,2);a=adjust(cur,f,'-1')
        r=refusal(cur,f,menu)
        assert r['old']['message']=='FG hasil QC masih dipakai transaksi downstream aktif. Reverse transaksi downstream terlebih dahulu.',r['old']
        assert r['old_screen']=='FG hasil QC masih dipakai transaksi downstream aktif.',r['old_screen']
        later=[(x['number'],x['menu'])for x in r['items']if x['kind']=='FG_DOWNSTREAM']
        # Latest use first, in the order of the movements' own physical times.
        order=[n for n,in cur.execute("""select case when id=%s then %s else %s end from erp.fg_stock_movements
            where id in(%s,%s)order by physical_at desc,id desc""",(a['movement'],a['number'],s['number'],a['movement'],s['movement'])).fetchall()]
        menus={a['number']:'Gudang › Stock Adjustment',s['number']:'Penjualan › Penjualan & Invoice'}
        assert later==[(n,menus[n])for n in order],(r['items'],order)
        assert 'Batalkan koreksi FG'in r['new']['message']and'Batalkan draft invoice'in r['new']['message']
        # Undo exactly what was named, latest first: the reversal is offered again and behaves as before.
        fgadj.action(cur,'REVERSE',a['posted']);fgc.cancel(cur,s);b.api.admin(cur)
        done=unblocked(cur,f)
        return dict(status='PASS',qc=f['qc_number'],before=r['old']['message'],after=r['new']['message'],screen=r['screen'],
            named=[x['number']for x in r['items']],opened=r['opened'],undo_then_reverse=done['status'],same_condition_and_sqlstate=True)

    def inverse_documents():
        f=chain(cur,today,'INV')
        s=draft_sale(cur,f,2);fgc.cancel(cur,s);b.api.admin(cur)
        a=adjust(cur,f,'-1');fgadj.action(cur,'REVERSE',a['posted'])
        reverse(cur,f)
        rows=[opens(cur,'SALE_ITEM',s['movement'],dict(domain='SALE',route='sales-invoice',id=s['sale_id'],number=s['number'],focus=None)),
              opens(cur,'FG_ADJUSTMENT_ITEM',a['movement'],dict(domain='FG_ADJUSTMENT',route='stock-adjustment',id=a['id'],number=a['number'],focus=None)),
              opens(cur,'QC_ITEM',f['movement'],dict(domain='QC',route='qc',id=f['qc'],number=f['qc_number'],focus=None),old_supported=True)]
        return dict(status='PASS',inverses=rows,previously_unsupported=['SALE_ITEM','FG_ADJUSTMENT_ITEM'],qc_unchanged=True)

    def return_and_sale():
        f=returns.fixture(cur,today);r=returns.returned(cur,f,qty='1',refund='20')
        number=one(cur,'select sale_number from erp.sales_headers where id=%s',(f['sale'],))
        moved=one(cur,"""select m.id::text from erp.sales_return_items i join erp.fg_stock_movements m on m.source_id=i.id
            and m.source_type='SALES_RETURN_ITEM'where i.return_id=%s and m.reversal_of_id is null""",(r['return_id'],))
        assert not one(cur,'select exists(select 1 from cp7_sales_return_correction.links where original_id=%s)',(r['return_id'],))
        returns.inverse(cur,f,r['return_id'])
        ret=opens(cur,'SALES_RETURN_ITEM',moved,dict(domain='SALE',route='sales-returns',id=str(f['sale']),number=number))
        assert ret['after']['focus']['kind']=='SALES_RETURN'and ret['after']['focus']['id']==str(r['return_id']),ret
        returns.reverse_sale(cur,f)
        sold=one(cur,"""select m.id::text from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
            where i.sale_id=%s and m.source_type='SALE_ITEM'and m.movement_type<>'SALE_RESERVE'
            and exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)order by m.physical_at desc,m.id limit 1""",(f['sale'],))
        sale=opens(cur,'SALE_ITEM',sold,dict(domain='SALE',route='sales-invoice',id=str(f['sale']),number=number,focus=None))
        return dict(status='PASS',return_inverse=ret,sale_inverse=sale,uncorrected_return_was_unsupported=True)

    def rework():
        w=ts.rework_fixture(cur,today);b.api.admin(cur)
        qc,number=cur.execute("""select q.id::text,q.inspection_number from erp.bs_cases bc join erp.qc_inspection_items i on i.id=bc.qc_item_id
            join erp.qc_inspections q on q.id=i.inspection_id where bc.id=%s""",(w['bs'],)).fetchone()
        f=dict(qc=qc,qc_number=number)
        r=refusal(cur,f,menu)
        mine=[x for x in r['items']if x['kind']=='REWORK_ORDER'and x['number']==w['number']]
        assert len(mine)==1 and mine[0]['menu']=='Produksi › Barang BS & Rework'and'Periksa pembatalan hasil'in mine[0]['step'],r['items']
        assert w['number']in r['new']['message']and w['number']in r['screen']
        chain_=ts.production.b.chain
        chain_.bs_action(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=w['rework'],change_reason=REASON),chain_.version(cur,'rework_orders',w['rework']))
        b.api.admin(cur)
        inv=opens(cur,'REWORK_ORDER',w['movement']['id'],dict(domain='BS_REWORK',route='bs-rework',id=w['bs']))
        assert inv['after']['focus']['kind']=='REWORK_ORDER'and inv['after']['focus']['id']==w['rework'],inv
        again=compare(cur,f)
        return dict(status='PASS',qc=number,before=r['old']['message'],after=r['new']['message'],named=[x['number']for x in r['items']],
            rework_inverse=inv,after_completion_reversed=again)

    def finished_po():
        f=chain(cur,today,'PO')
        c17.finish_command(cur,c17.finish_workspace(cur,f['po']),reason=REASON+' PO selesai')
        assert c17.po_state(cur,f['po'])['status']=='FINISHED'
        r=refusal(cur,f,menu)
        assert r['old']['message']=='PO sudah FINISHED. Reopen/koreksi downstream terlebih dahulu sebelum reversal QC.',r['old']
        po=[x for x in r['items']if x['kind']=='PO_FINISHED']
        assert len(po)==1 and po[0]['number']==f['number']and po[0]['menu']=='Keuangan › HPP & Rekalkulasi'and'Buka ulang PO'in po[0]['step'],r['items']
        c17.reopen_command(cur,c17.reopen_workspace(cur,f['po']),reason=REASON+' PO dibuka ulang')
        done=unblocked(cur,f)
        return dict(status='PASS',po=f['number'],before=r['old']['message'],after=r['new']['message'],screen=r['screen'],
            reopen_then_reverse=done['status'])

    def rights():
        f=chain(cur,today,'RT');s=draft_sale(cur,f,1);fgc.cancel(cur,s);b.api.admin(cur)
        unknown=auth.refused(cur,lambda:resolve(cur,'FG_MOVEMENT_REVERSAL',uuid.uuid4()),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
        sales_only,_=procurement.custom(cur,('sales.invoice.view',))
        no_warehouse=auth.refused(cur,lambda:resolve(cur,'FG_MOVEMENT_REVERSAL',s['movement'],sales_only),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
        stock_only,_=procurement.custom(cur,('warehouse.stock.view',))
        no_sales=auth.refused(cur,lambda:resolve(cur,'FG_MOVEMENT_REVERSAL',s['movement'],stock_only),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
        # The old reader told this warehouse-only actor "unsupported"; the sale is now refused, never shown.
        old=original(cur,lambda:read(cur,'FG_MOVEMENT_REVERSAL',s['movement'],stock_only))
        assert old.get('status')=='UNSUPPORTED_SOURCE',old
        both,_=procurement.custom(cur,('warehouse.movement.view','sales.invoice.view'))
        opened=resolve(cur,'FG_MOVEMENT_REVERSAL',s['movement'],both)
        assert opened['document']['domain']=='SALE'and opened['document']['id']==s['sale_id'],opened
        qc_less,_=procurement.custom(cur,('warehouse.stock.view','sales.invoice.view'))
        reverse(cur,f)
        no_qc=auth.refused(cur,lambda:resolve(cur,'FG_MOVEMENT_REVERSAL',f['movement'],qc_less),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
        return dict(status='PASS',unknown=unknown,without_warehouse_view=no_warehouse,without_sales_view=no_sales,
            without_qc_view=no_qc,warehouse_and_sales_view_opens=opened['document']['number'])

    def unchanged():
        # Every source the patched reader answers, compared with the exact kasbon-stage reader on the same state: a real
        # document of every journal and FG movement family present after the chains below are written through their own
        # writers, an unknown id of every family the original reader dispatches on, and a real inverse of all five FG
        # families it now follows. (Native9 fe95ba50: the bare clone held 9 direct families, so a count of 10 was never
        # reachable; every family compared there matched. No count is assumed now.)
        b.api.admin(cur)
        bare={k for k,in cur.execute("""select distinct source_type from erp.journal_entries where source_id is not null
            union select distinct source_type from erp.fg_stock_movements where source_id is not null""").fetchall()}
        f=chain(cur,today,'CEN');s=draft_sale(cur,f,1);fgc.cancel(cur,s);b.api.admin(cur)
        a=adjust(cur,f,'-1');fgadj.action(cur,'REVERSE',a['posted']);reverse(cur,f)
        g=chain(cur,today,'CENPO');c17.finish_command(cur,c17.finish_workspace(cur,g['po']),reason=REASON+' PO selesai');b.api.admin(cur)
        assert c17.po_state(cur,g['po'])['status']=='FINISHED'
        r=returns.fixture(cur,today);done=returns.returned(cur,r,qty='1',refund='20');returns.inverse(cur,r,done['return_id']);returns.reverse_sale(cur,r)
        w=ts.rework_fixture(cur,today);b.api.admin(cur);chain_=ts.production.b.chain
        chain_.bs_action(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=w['rework'],change_reason=REASON),chain_.version(cur,'rework_orders',w['rework']))
        b.api.admin(cur)
        def compare(kind,source):
            now=read(cur,kind,source);before=original(cur,lambda:read(cur,kind,source))
            assert same(now,before),(kind,source,now,before)
            return now.get('status',now.get('refused'))
        direct=cur.execute("""select * from(select distinct on(source_type)'JOURNAL'origin,source_type,source_id::text from erp.journal_entries
            where source_id is not null order by source_type,created_at desc,id)j
            union all select * from(select distinct on(source_type)'FG_MOVEMENT',source_type,source_id::text from erp.fg_stock_movements
            where source_id is not null and source_type<>'FG_MOVEMENT_REVERSAL'order by source_type,physical_at desc,id)m""").fetchall()
        real={origin+':'+kind:compare(kind,source)for origin,kind,source in direct}
        body=ORIGINALS[d.SOURCE]
        dispatched=set(re.findall(r"kind ?= ?'([A-Z][A-Z0-9_]+)'",body))
        for group in re.findall(r"kind ?(?:not )?in ?\(([^)]*)\)",body):dispatched|=set(re.findall(r"'([A-Z][A-Z0-9_]+)'",group))
        assert{'FG_MOVEMENT_REVERSAL','JOURNAL_REVERSAL','CP7_KASBON','QC_ITEM','SALE_ITEM','REWORK_ORDER'}<=dispatched,sorted(dispatched)
        unknown={kind:compare(kind,uuid.uuid4())for kind in sorted(dispatched)}
        inverses={}
        for family,movement,source in cur.execute("""select distinct on(o.source_type)o.source_type,o.id::text,o.source_id::text
            from erp.fg_stock_movements v join erp.fg_stock_movements o on o.id=v.source_id and o.reversal_of_id is null
            where v.source_type='FG_MOVEMENT_REVERSAL'order by o.source_type,v.physical_at desc,v.id""").fetchall():
            now=read(cur,'FG_MOVEMENT_REVERSAL',movement);before=original(cur,lambda:read(cur,'FG_MOVEMENT_REVERSAL',movement))
            if family in d.FAMILIES:
                assert same(now,read(cur,family,source)),(family,now)
                corrected=family=='SALES_RETURN_ITEM'and one(cur,"""select exists(select 1 from erp.sales_return_items i
                    join cp7_sales_return_correction.links l on l.original_id=i.return_id where i.id=%s)""",(source,))
                if family=='QC_ITEM'or corrected:assert same(now,before),(family,now,before)
                else:assert before.get('status')=='UNSUPPORTED_SOURCE'or'refused'in before,(family,before)
            else:
                assert same(now,before)and now.get('status')=='UNSUPPORTED_SOURCE',(family,now,before)
            inverses[family]=dict(before=before.get('status',before.get('refused')),after=now.get('status',now.get('refused')))
        written={k.split(':',1)[1]for k in real}
        assert written>bare and{'FG_ADJUSTMENT_ITEM','SALES_RETURN_ITEM','REWORK_ORDER','SALE_ITEM','QC_ITEM'}<=written,(sorted(bare),sorted(real))
        assert set(d.FAMILIES)<=set(inverses),inverses  # all five newly followed families on real inverses
        return dict(status='PASS',real_document_families=real,families_before_chains=sorted(bare),unknown_id_families=len(unknown),
            fg_inverse_families=inverses,unsupported_fg_families_seen=sorted(set(inverses)-set(d.FAMILIES)))

    def refusal_census():
        free=chain(cur,today,'RC1');held=chain(cur,today,'RC2');draft_sale(cur,held,1)
        rows=cur.execute("""select q.id::text,q.inspection_number from erp.qc_inspections q where q.status='POSTED'
            and(select count(distinct i.cutting_group_id)from erp.qc_inspection_items i where i.inspection_id=q.id)=1
            and not exists(select 1 from erp.qc_inspection_items i where i.inspection_id=q.id and i.source_laundry_receipt_batch_size_line_id is null)
            order by q.id in(%s,%s)desc,q.created_at desc,q.id limit 20""",(free['qc'],held['qc'])).fetchall()
        outcome={}
        for qc,number in rows:
            label=compare(cur,dict(qc=qc,qc_number=number));outcome[label]=outcome.get(label,0)+1
        assert outcome.get('REVERSED',0)>=1 and any(k.startswith('NAMED:')for k in outcome),outcome
        def window():
            auth.actor(cur);w=one(cur,"select public.erp_get_laundry_qc_workspace_v1('QC',null)");b.api.admin(cur);return w['qc_history']
        now,before=window(),original(cur,window)
        assert [r['qc_inspection_id']for r in now]==[r['qc_inspection_id']for r in before]
        screen={}
        for a,o in zip(now,before):
            assert {k:v for k,v in a.items()if k!='reversal_blocker'}=={k:v for k,v in o.items()if k!='reversal_blocker'},(a,o)
            if o['reversal_blocker']is None or o['reversal_blocker']=='Finalisasi QC bukan POSTED aktif.':assert a==o,(a,o)
            else:assert a['reversal_blocker'].startswith(o['reversal_blocker']+NAMES),(a,o)
            label=str(o['reversal_blocker'])[:60];screen[label]=screen.get(label,0)+1
        assert len(now)>=2 and sum(n for k,n in screen.items()if k.startswith('FG hasil QC'))>=1,screen
        reached=[k for k in('PO sudah FINISHED','BS hasil QC','FG hasil QC','Reimbursement aksesori')if any(x.startswith(k)for x in screen)]
        return dict(status='PASS',reversals_compared=len(rows),outcome=outcome,screen_rows=len(now),screen=screen,
            screen_kinds_reached=reached,not_reached_with_real_rows=['not POSTED (no writer leaves a QC outside POSTED/REVERSED)']
            +([] if'Reimbursement aksesori'in reached else['accessory right in payroll (no real chain in this state)']))

    def private():
        details=[]
        for sql in('select cp7_fg_correction_source.qc_blockers_v1(%s)','select cp7_fg_correction_source.qc_blocker_text_v1(%s)'):
            def call(sql=sql):
                auth.actor(cur);return one(cur,sql,(str(uuid.uuid4()),))
            details.append(auth.refused(cur,call,'permission denied'))
        b.api.admin(cur)
        return dict(status='PASS',authenticated_direct_call_refused=details)

    operations=(sale_and_adjustment,inverse_documents,return_and_sale,rework,finished_po,rights,unchanged,refusal_census,private)
    assert len(operations)==len(IDS)
    return list(zip(IDS,operations))
