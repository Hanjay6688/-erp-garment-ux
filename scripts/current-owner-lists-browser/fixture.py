"""Native fixtures and independent whole-list oracles, only on the disposable browser copy."""
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
import json,os,sys,uuid
operation=sys.argv[1]if len(sys.argv)==2 else None
sys.argv=sys.argv[:1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from cp7_ow09_lists import cases as native
from cp7_ab_bounded_chain import composition as product


def oracles(rows,source):
    indexed={r['id']:r for r in rows}
    return {order:[dict(id=i,number=indexed[i]['label'],status=indexed[i]['status'])
        for i in native.ordered(rows,order,source)]for order in native.ORDERS}


def prepare(cur,today):
    n,a,c,issue=native.notas,native.fgadj,native.counts,native.issue
    tags={k:'OW09PAGE-'+k+'-'+uuid.uuid4().hex[:10]for k in('notes','fg','count')}
    nf=n.source.repair(cur,today);n.source.ax.post(cur,n.source.ax.repair_payload(nf,1))
    np=n.payload(cur,nf,today);np['notes']=tags['notes']
    for i in range(31):n.act(cur,'VOID'if i<30 else'POST',n.command(cur,'SAVE',np))
    ff=a.fg.fixture(cur,today)
    for i in range(1,32):
        p=a.payload(cur,ff,'1');p['adjustment_number']=tags['fg']+'-'+str(i)
        p['notes']=tags['fg']+' movement '+str(i)
        d=a.command(cur,'SAVE',p)
        if i<=30:
            posted=a.action(cur,'POST',d)
            if i==1:a.action(cur,'REVERSE',posted)
    cf=c.raw.fixture(cur,today)
    for i in range(1,32):
        p=c.payload(cur,cf,'8'if i==31 else'5');p['adjustment_number']=tags['count']+'-'+str(i)
        d=c.command(cur,'SAVE',p)
        if i==31:c.action(cur,'POST',d)
    af=issue.receipt(cur,today,qty='100');tags['accessory']=af['code']
    for i in range(1,57):
        p=issue.payload(af);p.update(number=af['code']+'-PAGE-'+str(i),location_id=af['main'])
        p['items'][0]['qty']='1';d=issue.bc.note_call(cur,'SAVE_DRAFT',p)
        if i==56:
            p.update(id=d['id'],expected_version=d['row_version']);issue.bc.note_call(cur,'POST',p)
    native.b.api.admin(cur)
    result={}
    for kind,table,label,day,query,expected,filtered,filtered_count in [
            ('notes','cp7_payroll.notes','note_number','created_at',"where strpos(coalesce(notes,''),%s)>0",31,'VOID',30),
            ('fg','erp.fg_adjustments','adjustment_number','physical_at','where strpos(adjustment_number,%s)>0',31,'POSTED',29),
            ('count','erp.material_adjustments','adjustment_number','physical_at','where strpos(adjustment_number,%s)>0',31,'DRAFT',30)]:
        def rows(where='',args=()):
            return [dict(id=str(i),label=x,status=s,date=t)for i,x,s,t in cur.execute(
                f'select id,{label},status,{day} from {table} '+where,args).fetchall()]
        whole=rows();selected=rows(query,(tags[kind],))
        assert len(selected)==expected and sum(r['status']==filtered for r in selected)==filtered_count
        if kind=='fg':assert sorted(r['status']for r in selected)==['DRAFT']+['POSTED']*29+['REVERSED']
        result[kind]=dict(query=tags[kind],count=expected,limit=25,filter=filtered,filtered_count=filtered_count,
            matched=oracles(selected,[('date',True),('id',False)]),whole=oracles(whole,[('date',True),('id',False)]))
    every=[dict(id=str(i),label=x,status=s,date=str(t))for i,x,s,t in cur.execute("""
        select h.id,h.issue_number,h.status,(h.physical_at at time zone 'Asia/Jakarta')::date
        from erp.contractor_material_issues h where not exists(select 1 from erp.contractor_material_issue_items i
        join erp.materials m on m.id=i.material_id join erp.uom_definitions u on u.unit_code=m.unit_code
        where i.issue_id=h.id and(m.material_type<>'ACCESSORY'or u.dimension<>'COUNT'))""").fetchall()]
    chosen=[r for r in every if r['label'].startswith(tags['accessory']+'-PAGE-')]
    assert len(chosen)==56 and sum(r['status']=='DRAFT'for r in chosen)==55
    result['accessory']=dict(query=tags['accessory'],count=56,limit=50,filter='DRAFT',filtered_count=55,
        matched=oracles(chosen,[('date',True),('id',False)]),whole=oracles(every,[('date',True),('id',False)]))
    movements=[dict(id=str(i),label=f'{sku} {customer or ""} {kind}',status=kind,physical=ph,recorded=rc,source=str(sid),delta=int(qty))
        for i,ph,rc,kind,sid,customer,sku,qty in cur.execute("""select m.id,m.physical_at,m.system_created_at,m.movement_type,m.source_id,
        c.customer_name,erp.bf_commercial_sku_at_v1(m.product_id,m.physical_at),m.qty_signed
        from erp.fg_stock_movements m left join erp.customers c on c.id=m.customer_id
        where m.product_id=%s and m.lot_id=%s and m.location_id=%s and m.quality_grade='GRADE_A'
        and m.physical_at<=statement_timestamp()""",(ff['product'],ff['lot'],ff['location'])).fetchall()]
    assert len(movements)==32 and not cur.execute('select 1 from cp7_fg.correction_movements c join erp.fg_stock_movements m on m.id=c.member_id where m.lot_id=%s',(ff['lot'],)).fetchone()
    kinds={k:sum(r['status']==k for r in movements)for k in {r['status']for r in movements}}
    assert sorted(kinds.values())==[1,31],('EXPECTED_OPENING_AND_30_POSITIVE_PLUS_ONE_INVERSE',kinds)
    kind=max(kinds,key=kinds.get)
    order=oracles(movements,[('physical',False),('recorded',False),('id',False)])
    by_id={r['id']:r for r in movements};balances={};balance=0
    for row in order['SOURCE']:
        delta=by_id[row['id']]['delta'];balance+=delta
        balances[row['id']]=dict(delta=delta,balance=balance)
    assert balance==39
    second=next(r for r in movements if r['id']==order['SOURCE'][25]['id'])
    result['card']=dict(query='',count=32,limit=25,filter=kind,filtered_count=31,matched=order,whole=order,
        sku=ff['sku'],position={k:ff[k]for k in('product','lot','location')},search=second['source'],search_id=second['id'],balances=balances)
    return result


def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('127.0.0.1','localhost')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    args=json.load(sys.stdin)
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        native.b.api.admin(cur)
        if operation=='prepare':
            acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
            had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            if not had:cur.execute('grant usage on schema erp to authenticated')
            answer=prepare(cur,date.fromisoformat(args['today']))
            native.b.api.admin(cur);cur.execute('set constraints all immediate')
            if not had:cur.execute('revoke usage on schema erp from authenticated')
            assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
            conn.commit()
        elif operation=='state':
            answer=dict(sha256=product.catalog.digest(product.catalog._data(cur)));conn.rollback()
        else:raise ValueError('UNKNOWN_OPERATION')
        print(json.dumps(answer,default=str))


if __name__=='__main__':main()
