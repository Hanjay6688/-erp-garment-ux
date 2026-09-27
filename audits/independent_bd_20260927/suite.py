"""Independent BD native tests. Expected values come from PLAN.md, not product functions.

Phase one exercises public master commands, authorization and pricing calculation.
Pricing helper observations are explicitly NOT proof of physical or financial posting.
"""
from pathlib import Path
from decimal import Decimal as D
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,os,sys,time,traceback,uuid,threading
import psycopg
from psycopg.types.json import Jsonb

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'audit-results';OUT.mkdir(exist_ok=True)
DSN='postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
RESULTS=[];EVENTS=[];CTX={}
def uid():return str(uuid.uuid4())
def clean(v):return json.loads(json.dumps(v,default=str))
def save():
    (OUT/'independent-results.json').write_text(json.dumps({'candidate':'08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec',
      'plan_sha256':hashlib.sha256((Path(__file__).parent/'PLAN.md').read_bytes()).hexdigest(),
      'phase':'native masters and pricing; lifecycle coverage reported separately','results':RESULTS,
      'scope_not_run':['physical delivery/receipt','invoice/payment/reversal','downstream HPP/sales','HTTP/browser','full lifecycle concurrency','rollback'],
      'production_go':False},indent=2,default=str)+'\n')
    (OUT/'independent-events.json').write_text(json.dumps(EVENTS,indent=2,default=str)+'\n')
def admin(sql,args=(),one=False):
    with psycopg.connect(DSN) as c:
        q=c.execute(sql,args)
        return q.fetchone()[0] if one else q.fetchall() if q.description else None
def actor_conn(who='owner'):
    # Connect as the same unprivileged gateway principal used by PostgREST.
    # postgres cannot SET SESSION AUTHORIZATION; merely SET ROLE from postgres
    # would also leave session_user on the product's privileged bypass list.
    c=psycopg.connect(DSN.replace('postgres:postgres@','authenticator:postgres@'))
    c.execute('set role authenticated')
    claims={'sub':CTX[who],'role':'authenticated'}
    c.execute("select set_config('request.jwt.claims',%s,false)",(json.dumps(claims),))
    c.execute("select set_config('request.jwt.claim.sub',%s,false)",(CTX[who],))
    identity=c.execute('select session_user,current_user').fetchone()
    assert identity==('authenticator','authenticated'),identity
    c.commit();return c
def command(action,payload,request=None,who='owner'):
    request=request or uid();start=time.monotonic()
    event={'action':action,'payload':payload,'request':request,'actor':who}
    try:
        with actor_conn(who) as c:
            r=c.execute('select public.erp_save_laundry_bd_action_v1(%s,%s,%s::uuid)',(action,Jsonb(payload),request)).fetchone()[0]
        event['response']=r;return r
    except psycopg.Error as e:
        event.update(error=str(e),sqlstate=e.sqlstate);raise
    finally:
        event['seconds']=round(time.monotonic()-start,4);EVENTS.append(event)
def eq(actual,expected,label=''):
    if actual!=expected:raise AssertionError({'label':label,'expected':expected,'actual':actual})
    return {'expected':clean(expected),'actual':clean(actual)}
def case(key,title,fn,layer='public SQL RPC'):
    row={'id':key,'title':title,'layer':layer};start=time.monotonic()
    try:row.update(status='PASS',observation=clean(fn()))
    except Exception as e:row.update(status='FAIL',error=str(e),traceback=traceback.format_exc())
    row['seconds']=round(time.monotonic()-start,4);RESULTS.append(row);save()
    print(json.dumps({k:row.get(k) for k in ['id','title','layer','status','error']},default=str),flush=True)
def counts():
    names=['bd_requests_v1','bd_laundry_components_v1','bd_laundry_component_rates_v1','bd_laundry_packages_v1','bd_policy_setting_events_v1']
    return {n:admin('select count(*) from erp.'+n,one=True) for n in names}
def reject(fn):
    before=counts()
    try:fn()
    except psycopg.Error as e:
        if e.sqlstate in ('42601','42703','42P01','42883'):raise AssertionError('Test adapter/schema error, not intended business refusal: '+str(e))
        after=counts();eq(after,before,'Rejected command atomicity')
        return {'refused':True,'sqlstate':e.sqlstate,'message':str(e),'before':before,'after':after}
    raise AssertionError('Expected refusal but operation was accepted')
def component(vendor,code):
    return command('SAVE_COMPONENT',{'vendor_id':vendor,'component_code':code,'component_name':code,'is_active':True,'reason':'Independent synthetic audit'})['component_id']
def rate(comp,amount,at='2026-09-01T08:00:00+07:00',status='KNOWN'):
    p={'component_id':comp,'rate_status':status,'effective_from':at,'reason':'Independent audit agreement'}
    if amount is not None:p['rate_per_pcs']=amount
    return command('SAVE_COMPONENT_RATE',p)
def terms(mode,unit='PCS',vendor=None,version='0'):
    return command('SAVE_VENDOR_TERMS',{'vendor_id':vendor or CTX['v1'],'pricing_mode':mode,'pricing_unit':unit,'minimum_charge':None,'expected_version':version,'reason':'Synthetic audit terms'})
def policy(key,value,who='owner'):
    version=admin('select version from erp.bd_policy_settings_v1 where policy_key=%s',(key,),one=True)
    return command('SET_POLICY',{'policy_key':key,'operation':'SET','expected_version':str(version),'reason':'Synthetic audit configuration, not live owner settings','value':value},who=who)
def delivery(vendor=None,sizes=None,at='2026-09-15T08:00:00+07:00'):
    return {'vendor_id':vendor or CTX['v1'],'wash_process_id':CTX['process'],'distribution_batch_id':CTX['nonphysical_batch'],
            'physical_at':at,'target_dyeing_color':'AUD-NAVY',
            'lines':sizes or [{'size_id':CTX['s1'],'qty_sent_pcs':7},{'size_id':CTX['s2'],'qty_sent_pcs':6}]}
def pricing(p,d=None):
    # Helper-level calculation only. The nonphysical batch is not claimed as a posted source.
    r=admin('select erp.bd_compute_pricing_v1(%s,%s)',(Jsonb(d or delivery()),Jsonb(p)),one=True)
    EVENTS.append({'internal_pricing_input':p,'delivery_input':d or delivery(),'response':r});return r
def comps(extra=None):return {'components':extra or [{'component_id':CTX['wash'],'covered_qty':13},{'component_id':CTX['finish'],'covered_qty':5}]}
def setup():
    CTX.update(owner=uid(),admin=uid(),staff=uid(),v1=uid(),v2=uid(),process=uid(),s1=uid(),s2=uid(),nonphysical_batch=uid())
    with psycopg.connect(DSN) as c:
        c.execute("select set_config('app.change_reason','Independent synthetic audit fixture',true)")
        operator_role=uid()
        c.execute("insert into erp.app_roles(id,role_code,role_name,is_active) values(%s,'AUD_OPERATOR','Independent laundry viewer',true)",(operator_role,))
        c.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'production.laundry.view')",(operator_role,))
        for who,role in [('owner','OWNER'),('admin','ADMIN'),('staff','STAFF')]:
            rid=(operator_role,) if who=='staff' else c.execute('select id from erp.app_roles where role_code=%s and is_active',(role,)).fetchone()
            assert rid,('Missing supported role',role)
            rolecode=c.execute('select role_code from erp.app_roles where id=%s',rid).fetchone()[0]
            c.execute('insert into erp.app_users(auth_user_id,full_name,role,role_id) values(%s,%s,%s,%s)',(CTX[who],'AUD-'+who,'STAFF' if who=='staff' else rolecode,rid[0]))
        for key,name in [('v1','CEDAR'),('v2','BIRCH')]:
            c.execute('insert into erp.laundry_vendors(id,vendor_code,vendor_name) values(%s,%s,%s)',(CTX[key],'AUD-'+name,'AUD-'+name))
        c.execute('insert into erp.wash_processes(id,process_code,process_name) values(%s,%s,%s)',(CTX['process'],'AUD-WASH','Independent audit wash'))
        for n,k in enumerate(['s1','s2']):c.execute('insert into erp.sizes(id,size_code,sort_order) values(%s,%s,%s)',(CTX[k],'AUD-'+str(n+1),n))
    CTX['wash']=component(CTX['v1'],'AUD-WASH');CTX['finish']=component(CTX['v1'],'AUD-FINISH');CTX['unknown']=component(CTX['v1'],'AUD-UNKNOWN')
    CTX['foreign']=component(CTX['v2'],'AUD-FOREIGN')
    rate(CTX['wash'],'4321.09');rate(CTX['finish'],'678.91');rate(CTX['unknown'],None,status='UNKNOWN');rate(CTX['foreign'],'99.17')
    terms('COMPONENTS');terms('COMPONENTS',vendor=CTX['v2'])
    # Positive controls: a refusal for an inactive/missing identity is not proof
    # of the financial permission boundary. Confirm all ERP actors exist first.
    for who in ('owner','admin','staff'):
        with actor_conn(who) as c:
            authid,appid,rolecode=c.execute('select auth.uid(),erp.current_app_user_id(),erp.current_app_role()').fetchone()
            assert str(authid)==CTX[who] and appid is not None,(who,authid,appid,rolecode)
            EVENTS.append({'fixture_actor':who,'auth_id':str(authid),'erp_user_id':str(appid),'erp_role':rolecode,'session_user':'authenticator','current_user':'authenticated'})
    with actor_conn('staff') as c:
        visible=c.execute('select public.erp_get_laundry_bd_workspace_v1(%s)',(Jsonb({'vendor_id':CTX['v1']}),)).fetchone()[0]
        eq(visible['money_visible'],False);eq(visible['can_manage_master'],False)
        EVENTS.append({'fixture_operator_positive_control':{'can_read_laundry':True,'money_visible':visible['money_visible'],'can_manage_master':visible['can_manage_master']}})
    (OUT/'fixture-identities.json').write_text(json.dumps(CTX,indent=2)+'\n')
def known_total():
    r=pricing(comps());eq(D(r['total_known']),D('59568.72'));eq(r['qty'],13);eq(r['complete'],True)
    return {'total':r['total_known'],'qty':r['qty'],'complete':r['complete'],'charges':r['charges']}
def unknown_total():
    r=pricing(comps([{'component_id':CTX['wash'],'covered_qty':13},{'component_id':CTX['unknown'],'covered_qty':5}]))
    eq(D(r['total_known']),D('56174.17'));eq(r['complete'],False);eq(r['avg_rate'],None)
    eq(r['charges'][1]['amount'],None);return r
def helper_refuse(p,d=None):
    try:pricing(p,d)
    except psycopg.Error as e:return {'refused':True,'sqlstate':e.sqlstate,'message':str(e)}
    raise AssertionError('Expected pricing refusal, calculation accepted')
def exact_shares():
    r=pricing(comps())
    for c in r['charges']:eq(sum(D(x['amount']) for x in c['shares']),D(c['amount']))
    return r['charges']
def version_snapshot():
    before=pricing(comps())
    rate(CTX['wash'],'9000.17','2026-09-20T08:00:00+07:00')
    old=pricing(comps());new=pricing(comps(),delivery(at='2026-09-21T08:00:00+07:00'))
    eq(old,before);eq(D(new['total_known']),13*D('9000.17')+5*D('678.91'))
    return {'old':old['total_known'],'new':new['total_known'],'note':'Version lookup, not a posted-snapshot lifecycle proof'}
def free_price():
    c=component(CTX['v1'],'AUD-FREE')
    return rate(c,'0.00')
def replay():
    p={'vendor_id':CTX['v1'],'component_code':'AUD-IDEMP','component_name':'AUD-IDEMP','is_active':True,'reason':'Independent replay test'}
    req=uid();a=command('SAVE_COMPONENT',p,req);before=counts();b=command('SAVE_COMPONENT',p,req)
    eq(a['component_id'],b['component_id']);eq(counts(),before)
    CTX['replay_request']=req;CTX['replay_payload']=p
    return {'first':a,'replay':b,'counts':before}
def changed_replay():
    p={**CTX['replay_payload'],'component_name':'CHANGED'}
    return reject(lambda:command('SAVE_COMPONENT',p,CTX['replay_request']))
def atomic_bad_package():
    p={'vendor_id':CTX['v1'],'package_code':'AUD-BAD','package_name':'AUD-BAD','component_ids':[CTX['wash'],CTX['foreign']],
       'is_active':True,'reason':'Atomic mixed vendor input'}
    return reject(lambda:command('SAVE_PACKAGE',p))
def concurrent_replay():
    p={'vendor_id':CTX['v1'],'component_code':'AUD-RACE','component_name':'AUD-RACE','is_active':True,'reason':'Independent same-request concurrency'}
    req=uid();barrier=threading.Barrier(2)
    def call():barrier.wait();return command('SAVE_COMPONENT',p,req)
    with ThreadPoolExecutor(max_workers=2) as ex:a,b=list(ex.map(lambda _:call(),range(2)))
    eq(a['component_id'],b['component_id']);eq(admin('select count(*) from erp.bd_requests_v1 where request_id=%s',(req,),one=True),1)
    return [a,b]
def package_total():
    r=command('SAVE_PACKAGE',{'vendor_id':CTX['v1'],'package_code':'AUD-PACK','package_name':'AUD-PACK','component_ids':[CTX['wash'],CTX['finish']],
                            'is_active':True,'reason':'Independent package test'})
    CTX['pkg']=r['package_id']
    command('SAVE_PACKAGE_RATE',{'package_id':CTX['pkg'],'rate_per_pcs':'8712.35','effective_from':'2026-09-01T08:00:00+07:00','reason':'Agreed synthetic package'})
    version=admin('select row_version from erp.bd_laundry_vendor_terms_v1 where vendor_id=%s',(CTX['v1'],),one=True)
    terms('PACKAGE',version=str(version));r=pricing({'package_id':CTX['pkg']})
    eq(D(r['total_known']),D('113260.55'));eq(len(r['charges']),1);return r
def batch_amount():
    policy('LAU_DEC01',{'units':['BATCH']})
    version=admin('select row_version from erp.bd_laundry_vendor_terms_v1 where vendor_id=%s',(CTX['v1'],),one=True)
    terms('RATE','BATCH',version=str(version));r=pricing({'lump_sum':'1000.01'})
    eq(D(r['total_known']),D('1000.01'));eq(sum(D(x['amount']) for x in r['charges'][0]['shares']),D('1000.01'))
    return r
def main():
    try:setup()
    except Exception as e:
        RESULTS.append({'id':'SETUP','status':'BLOCKED','error':str(e),'traceback':traceback.format_exc()});save();raise
    case('IND-01.CALC','13 PCS with partial 5 PCS component, independent total',known_total,'pricing function')
    case('IND-01.SHARES','Component allocation conserves exact cents',exact_shares,'pricing function')
    case('IND-07.CALC','Unknown component is not zero and not final',unknown_total,'pricing function')
    case('IND-04.CALC','Component from another vendor refused',lambda:helper_refuse(comps([{'component_id':CTX['foreign'],'covered_qty':5}])),'pricing function')
    case('IND-12.OVER','Component coverage above physical quantity refused',lambda:helper_refuse(comps([{'component_id':CTX['wash'],'covered_qty':14}])),'pricing function')
    case('IND-12.NEG','Negative physical component quantity refused',lambda:helper_refuse(comps([{'component_id':CTX['wash'],'covered_qty':-1}])),'pricing function')
    case('IND-12.FRACTION','Fractional PCS refused',lambda:helper_refuse(comps([{'component_id':CTX['wash'],'covered_qty':1.5}])),'pricing function')
    case('IND-03.DUP','Duplicate selected component refused',lambda:helper_refuse(comps([{'component_id':CTX['wash'],'covered_qty':13},{'component_id':CTX['wash'],'covered_qty':1}])),'pricing function')
    case('IND-19.MASTER','Identical request has one effect',replay)
    case('IND-20.MASTER','Request reused with changed payload refused',changed_replay)
    case('IND-23.MASTER','Two simultaneous identical requests have one effect',concurrent_replay)
    case('IND-18.MASTER','Mixed valid/foreign package creation is atomic',atomic_bad_package)
    case('IND-39.ADMIN','Administrator cannot change owner-only policy',lambda:reject(lambda:policy('LAU_DEC04',{'sale_with_unknown_laundry':'ALLOW_PENDING'},'admin')))
    case('IND-38.STAFF','Staff cannot change master pricing',lambda:reject(lambda:command('SAVE_COMPONENT',{'vendor_id':CTX['v1'],'component_code':'AUD-DENY','component_name':'AUD-DENY','is_active':True,'reason':'Unauthorized attempt'},who='staff')))
    case('IND-37.BATCH','Unconfigured batch policy fails closed',lambda:reject(lambda:terms('COMPONENTS','BATCH',version='1')))
    case('IND-05.VERSION','New master version does not change old pricing date',version_snapshot,'public master RPC + pricing function')
    case('IND-08.FREE','Explicit free master price with recorded reason is supported',free_price)
    case('IND-02.CALC','Package included processes charged once',package_total,'public master RPC + pricing function')
    if 'pkg' in CTX:
        case('IND-03.INCLUDED','Included process cannot be billed again as extra',lambda:helper_refuse({'package_id':CTX['pkg'],'extras':[{'component_id':CTX['wash'],'covered_qty':13,'reason':'Duplicate included'}]}),'pricing function')
    case('IND-36.CALC','Batch amount conserved across 13 PCS',batch_amount,'public configuration RPC + pricing function')
    save()
    print(json.dumps({'status_counts':{s:sum(r['status']==s for r in RESULTS) for s in ['PASS','FAIL','BLOCKED']},'unexecuted_domains_remain':True}),flush=True)
    return 1 if any(r['status']!='PASS' for r in RESULTS) else 0
if __name__=='__main__':raise SystemExit(main())
