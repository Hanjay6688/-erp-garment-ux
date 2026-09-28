"""Independent BE audit. Frozen business oracle, public RPCs, own synthetic inputs."""
import json,traceback,time,uuid,copy,threading,hashlib
from decimal import Decimal as D
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb
import suite as s
import daily as d
C=s.CTX;E=s.EVENTS;R=s.RESULTS;F={};A=s.admin;eq=s.eq;uid=s.uid
PRODUCT='e96db5a270da5aa6d0f12c3812ac1c0542df938e'
class Blocked(Exception):pass

def save():
    (s.OUT/'be-native-results.json').write_text(json.dumps({'candidate':PRODUCT,'oracle_sha256':hashlib.sha256((Path(__file__).parent/'ORACLE.md').read_bytes()).hexdigest(),'results':R,'production_go':False},indent=2,default=str)+'\n')
    (s.OUT/'be-native-events.json').write_text(json.dumps(E,indent=2,default=str)+'\n')
    (s.OUT/'be-fixtures.json').write_text(json.dumps({'identity':C,'sources':F,'daily':d.F},indent=2,default=str)+'\n')
s.save=save

def case(key,title,fn,layer='authenticated public SQL RPC'):
    row={'id':key,'title':title,'layer':layer};t=time.monotonic()
    try:row.update(status='PASS',observation=s.clean(fn()))
    except Blocked as e:row.update(status='BLOCKED',error=str(e))
    except Exception as e:row.update(status='FAIL',error=str(e),sqlstate=getattr(e,'sqlstate',None),traceback=traceback.format_exc())
    row['seconds']=round(time.monotonic()-t,3);R.append(row);save();print(json.dumps({k:row.get(k) for k in ('id','status','error')},default=str),flush=True)

def rpc(name,args,who='owner'):
    event={'rpc':name,'args':args,'actor':who};t=time.monotonic()
    try:
        params=[Jsonb(a) if isinstance(a,(dict,list)) else a for a in args]
        with s.actor_conn(who) as c:out=c.execute('select public.'+name+'('+','.join(['%s']*len(params))+')',params).fetchone()[0]
        event['response']=out;return out
    except psycopg.Error as e:event.update(error=str(e),sqlstate=e.sqlstate);raise
    finally:event['seconds']=round(time.monotonic()-t,4);E.append(event)

def cmd(action,payload,request=None,who='owner'):return rpc('erp_save_product_conversion_action_v1',[action,payload,request or uid()],who)
def ws(filters=None,who='owner'):return rpc('erp_get_product_conversion_workspace_v1',[filters or {}],who)
def bs(action,payload,version=None,request=None,who='owner'):
    r=rpc('erp_save_bs_resolution_action_v1',[action,payload,request or uid(),version],who);return r.get('result',r)
def pocket(action,payload,request=None,who='owner'):return rpc('erp_save_pocket_fabric_action_v1',[action,payload,request or uid()],who)
def imp(action,payload,request=None,who='owner'):return rpc('erp_save_initial_import_action_v1',[action,payload,request or uid()],who)

def fp(tables=None):
    tables=tables or ['product_conversions','product_conversion_allocations','be_conversion_sources_v1','be_conversion_returns_v1','be_conversion_cost_sources_v1','be_conversion_cost_events_v1','be_nonpo_transfer_events_v1','be_rework_targets_v1','be_redye_services_v1','be_redye_price_events_v1','fg_stock_movements','fg_lots','hpp_versions','journal_entries','journal_lines','bs_cases','bs_resolutions','rework_orders','material_stock_movements','pocket_periods','pocket_period_events']
    return {n:A("select md5(coalesce(string_agg(to_jsonb(t)::text,'' order by to_jsonb(t)::text),'')) from erp."+n+' t',one=True) for n in tables}
def reject(fn,contains=None,states=('P0001','42501')):
    before=fp()
    try:r=fn()
    except psycopg.Error as e:
        if e.sqlstate not in states:raise AssertionError({'unexpected_sql_error':str(e),'sqlstate':e.sqlstate})
        if contains and contains.lower() not in str(e).lower():raise AssertionError({'wrong_refusal':str(e),'wanted':contains})
        eq(fp(),before,'Rejected transaction atomicity')
        return {'refused':True,'sqlstate':e.sqlstate,'message':str(e),'unchanged':before}
    raise AssertionError({'expected':'Refusal','actual':r})
def lotqty(lot):return A('select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',(lot,),one=True)
def lotcost(lot):return A('select hpp_per_pcs,total_cost,qty_basis_pcs,cost_state from erp.hpp_versions where lot_id=%s and is_current',(lot,))[0]
def value(lot):return (D(lotqty(lot))*lotcost(lot)[0]).quantize(D('.01'))
def source(key):
    if key not in F or 'lot' not in F[key]:raise Blocked('Missing successful independent source fixture '+key)
    return F[key]
def pconv(key,qty=5,**changes):
    f=source(key);rows=ws({'source_lot_id':f['lot']})['lots'];l=next(x for x in rows if x['location_id']==C['fg'])
    return {'source_lot_id':f['lot'],'target_product_id':C['target'],'location_id':C['fg'],'qty_pcs':qty,'physical_at':'2026-09-15T08:00:00+07:00','reason':'Independent BE conversion '+key,'expected_version':l['source_revision'],**changes}

def setup():
    s.setup();d.setup();C['product']=C['products'][C['s1']+':'+C['brand']];C['target']=C['products'][C['s1']+':'+C['brand2']];C['wrongsize']=C['products'][C['s2']+':'+C['brand2']]
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('app.change_reason','Independent BE roles prerequisite',true)")
        rid=c.execute('select role_id from erp.app_users where auth_user_id=%s',(C['staff'],)).fetchone()[0]
        c.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'warehouse.brand_conversion.view')",(rid,))
        arid=c.execute('select role_id from erp.app_users where auth_user_id=%s',(C['admin'],)).fetchone()[0]
        c.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'warehouse.stock.adjust') on conflict do nothing",(arid,))
    # All base lots are established before any conversion adds or removes cost.
    keys=['MAIN','EMPTY','REV','CHAIN','STALE','RACE','SAME','AUTH','DATE','BAD','UI','UI_MOBILE','SALE','RETURNS','EXTRA']
    for index,key in enumerate(keys):
        p={'source_kind':'FOUND_AT_OPNAME','product_id':C['product'],'location_id':C['fg'],'qty_pcs':13,'physical_at':'2026-09-13T08:00:00+07:00','reason':'Independent found-stock prerequisite '+key}
        p.update(owner_unit_value='1234.57',owner_value_reason='Synthetic explicit owner amount; found-stock lots are not production comparators')
        r=rpc('erp_post_fg_unsourced_receipt_v1',[p,uid()]);eq(D(r['unit_value']),D('1234.57'));eq(D(r['total_value']),D('16049.41'))
        F[key]={'lot':r['lot_id'],'receipt':r['receipt_id'],'original':r}
    return {'sources':F,'no_fake_po':A('select count(*) from erp.production_orders',one=True),'basis':'Real public AX found-stock receipts, before BE conversion; controlled master records only'}

def preview():
    p=pconv('MAIN');before=fp();r=ws({'preview':p})['preview'];eq(fp(),before);eq(D(r['cost']['source_value']),D('6172.85'));eq(r['qty_pcs'],5)
    F['MAIN']['payload']=p;return r

def post_main():
    p=pconv('MAIN');q=uid();r=cmd('POST',p,q);F['MAIN'].update(payload=p,request=q,response=r,targetlot=r['destination_lot_id'],conversion=r['conversion_id'])
    eq(lotqty(F['MAIN']['lot']),8);eq(lotqty(r['destination_lot_id']),5);eq(value(F['MAIN']['lot']),D('9876.56'));eq(value(r['destination_lot_id']),D('6172.85'))
    eq(A('select po_id from erp.fg_lots where id=%s',(r['destination_lot_id'],),one=True),None)
    a=A('select c.from_product_id::text,c.to_product_id::text,a.source_lot_id::text,a.destination_lot_id::text,a.qty_pcs from erp.product_conversions c join erp.product_conversion_allocations a on a.conversion_id=c.id where c.id=%s',(r['conversion_id'],))[0]
    eq(a,(C['product'],C['target'],F['MAIN']['lot'],r['destination_lot_id'],5))
    return {'response':r,'lineage':a,'source_remaining_value':value(F['MAIN']['lot']),'target_value':value(r['destination_lot_id'])}
def replay():
    f=source('MAIN');before=fp();r=cmd('POST',f['payload'],f['request']);eq(r,f['response']);eq(fp(),before);return r

def reverse():
    p=pconv('REV');r=cmd('POST',p);beforeh=lotcost(source('REV')['lot']);rv=cmd('REVERSE',{'conversion_id':r['conversion_id'],'reason':'Independent physical inverse'})
    eq(lotqty(source('REV')['lot']),13);eq(lotqty(r['destination_lot_id']),0);eq(lotcost(source('REV')['lot']),beforeh)
    return {'post':r,'reverse':rv,'source_restored':13,'target':0}
def chain():
    p=pconv('CHAIN',qty=7);r=cmd('POST',p);q={**p,'source_lot_id':r['destination_lot_id'],'target_product_id':C['product'],'qty_pcs':3,'physical_at':'2026-09-16T08:00:00+07:00'}
    q['expected_version']=ws({'source_lot_id':r['destination_lot_id']})['lots'][0]['source_revision'];rr=cmd('POST',q)
    eq([lotqty(x) for x in [source('CHAIN')['lot'],r['destination_lot_id'],rr['destination_lot_id']]],[6,4,3]);eq(sum(value(x) for x in [source('CHAIN')['lot'],r['destination_lot_id'],rr['destination_lot_id']]),D('16049.41'))
    F['CHAIN'].update(first=r,second=rr)
    blocked=reject(lambda:cmd('REVERSE',{'conversion_id':r['conversion_id'],'reason':'Independent ancestor reversal with active descendant'}))
    return {'first':r,'second':rr,'reverse_parent':blocked}
def stale():
    p=pconv('STALE');first=cmd('POST',p);r=reject(lambda:cmd('POST',p),'STALE_VERSION');return {'first':first,'stale':r}

def race(key,same=False):
    p=pconv(key,qty=9);barrier=threading.Barrier(2);req=uid()
    def go(i):
        barrier.wait()
        try:return {'actor':'owner' if same or i==0 else 'admin','accepted':True,'response':cmd('POST',p,req if same else uid(),'owner' if same or i==0 else 'admin')}
        except psycopg.Error as e:return {'actor':'owner' if same or i==0 else 'admin','accepted':False,'error':str(e),'sqlstate':e.sqlstate}
    with ThreadPoolExecutor(2) as pool:rs=list(pool.map(go,[0,1]))
    eq(sum(x['accepted'] for x in rs),2 if same else 1);eq(lotqty(source(key)['lot']),4)
    targets=A('select a.destination_lot_id::text from erp.product_conversion_allocations a where a.source_lot_id=%s',(source(key)['lot'],));eq(len(targets),1);eq(lotqty(targets[0][0]),9)
    return {'sessions':rs,'remaining':4,'target':9,'independent_actor_ids':[C['owner'],C['admin']] if not same else [C['owner']]}

def viewer():
    r=ws({'source_lot_id':source('AUTH')['lot']},'staff');eq(len(r['lots']),1);eq(r['lots'][0]['unit_hpp'],None)
    p=pconv('AUTH');before=fp();preview=ws({'preview':p},'staff');eq(preview['preview']['cost'],{});eq(fp(),before)
    for x in r['documents']:eq(x['target_value'],None);eq(x['extra_cost'],None)
    return {'workspace':r,'preview':preview,'post_refused':reject(lambda:cmd('POST',p,who='staff'))}
def revoke():
    p=pconv('AUTH');q=uid();r=cmd('POST',p,q,who='admin')
    own=A('select role,role_id from erp.app_users where auth_user_id=%s',(C['admin'],))[0];viewer_role=A('select role_id from erp.app_users where auth_user_id=%s',(C['staff'],),one=True)
    try:
        with psycopg.connect(s.DSN) as c:
            c.execute("select set_config('app.change_reason','Independent permission revocation fixture',true)")
            c.execute("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(viewer_role,C['admin']))
        denied=reject(lambda:cmd('POST',p,q,who='admin'));fresh=reject(lambda:cmd('POST',p,who='admin'))
    finally:
        with psycopg.connect(s.DSN) as c:
            c.execute("select set_config('app.change_reason','Restore disposable owner after permission test',true)")
            c.execute('update erp.app_users set role=%s,role_id=%s where auth_user_id=%s',(*own,C['admin']))
    return {'positive':r,'revoked_replay':denied,'revoked_fresh':fresh}
def direct():
    out=[]
    for q,args in [('select erp.be_source_revision_v1(%s,%s)',(source('AUTH')['lot'],C['fg'])),('select * from erp.be_conversion_sources_v1',())]:
        def call():
            with s.actor_conn() as c:return c.execute(q,args).fetchall()
        out.append(reject(call,states=('42501',)))
    return out

def run():
    installation=json.loads((s.OUT/'installation.json').read_text());assert installation['status']=='READY_FOR_INDEPENDENT_TESTS'
    assert A("select count(*) from erp.schema_migrations where version='v2.6.20be'",one=True)==1
    case('SETUP','Independent master and real non-PO source prerequisites',setup,'Controlled masters + authenticated public found-stock RPC')
    if not F:return
    case('CONV-02','Preview is free of stock and journal effects',preview)
    case('CONV-01-03-04-08','Partial same-SKU different-brand conversion conserves stock and value',post_main)
    case('CONV-11.REPLAY','Identical UUID returns one physical conversion',replay)
    case('CONV-11.MISMATCH','Changed payload under old UUID is refused',lambda:reject(lambda:cmd('POST',{**F['MAIN']['payload'],'qty_pcs':4},F['MAIN']['request'])))
    for key,changes in [('OVER',{'qty_pcs':14}),('ZERO',{'qty_pcs':0}),('NEG',{'qty_pcs':-1}),('FRACTION',{'qty_pcs':1.5}),('SAME_SKU',{'target_product_id':C['product']}),('SIZE',{'target_product_id':C['wrongsize']}),('LOCATION',{'location_id':C['rawloc']}),('BEFORE',{'physical_at':'2026-09-12T08:00:00+07:00'}),('FUTURE',{'physical_at':'2099-01-01T08:00:00+07:00'}),('INJECTED_COST',{'conversion_cost_total':'143.29'})]:
        case('CONV-09-10.'+key,'Invalid conversion input '+key,lambda changes=changes:reject(lambda:cmd('POST',pconv('BAD',**changes))))
    case('CONV-12','Stale source version refuses a second operation',stale)
    case('CONV-13','Unused conversion reverses exactly',reverse)
    case('CONV-14-16','Conversion descendants preserve source value and prevent premature inverse',chain)
    case('RACE-CONV.DISTINCT','Two authorized actors compete for 9 of 13 PCS',lambda:race('RACE'))
    case('RACE-CONV.UUID','Concurrent same UUID creates one target',lambda:race('SAME',True))
    case('ACCESS-CONV.VIEW','Read-only role can preview with monetary redaction; cannot post',viewer)
    case('ACCESS-CONV.REVOKE','Revoked actor denied fresh and cached mutations',revoke)
    case('ACCESS-CONV.PRIVATE','Private helpers and facts inaccessible to gateway role',direct)
    save()
if __name__=='__main__':
    run();print(json.dumps({'results':len(R),'counts':{x:sum(r['status']==x for r in R) for x in ['PASS','FAIL','BLOCKED']}}),flush=True)
