"""Real signed-JWT HTTP overlaps, synchronized by observed PostgreSQL waits."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
import copy,json,os,time,traceback,uuid
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import psycopg
from psycopg import sql
from cp6_ap_flow_fixture import PG,ADMIN,OUT,state,identities
from cp6_ao_ap_inventory import data

assert os.environ.get('CP6_AP_FLOW_CONFIRM')=='cp6_rollback'
TOKEN=os.environ['CP6_AP_FLOW_TOKEN'];ANON=os.environ['SUPABASE_ANON_KEY']
with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:F=identities(cur)
report=dict(status='INCOMPLETE',cases=[],production_go=False,independent_acceptance=False)
def save():(OUT/'RACES.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
def rpc(name,args):
    req=Request('http://127.0.0.1:54329/rpc/'+name,data=json.dumps(args).encode(),headers={'apikey':ANON,'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json'})
    try:
        with urlopen(req,timeout=35) as r:return dict(status=r.status,value=json.load(r))
    except HTTPError as exc:return dict(status=exc.code,value=json.load(exc))
def ok(result):
    assert result['status']==200,result
    return result['value']
def cmd(family,action,payload,key=None):return ('erp_save_'+family+'_action_v1',dict(p_action=action,p_payload=payload,p_client_request_id=str(key or uuid.uuid4())))
def call(*args,**kwargs):return ok(rpc(*cmd(*args,**kwargs)))
def workspace(batch):return ok(rpc('erp_get_initial_import_workspace_v1',dict(p_batch_id=batch)))['batch']
def current():
    with psycopg.connect(ADMIN) as c,c.cursor() as cur:return state(cur)
def boundary():
    with psycopg.connect(ADMIN) as c,c.cursor() as cur:return data(cur)
def pass_case(name,**details):report['cases'].append(dict(id=name,status='PASS',**details));save()

def pair(table,ident,first,second):
    """Neither request is released until both real server sessions are waiting."""
    observed=[]
    with psycopg.connect(ADMIN) as blocker,blocker.cursor() as cur,psycopg.connect(ADMIN,autocommit=True) as observer,ThreadPoolExecutor(max_workers=2) as pool:
        cur.execute(sql.SQL('select id from erp.{} where id=%s for update').format(sql.Identifier(table)),(ident,))
        blocker_pid=cur.execute('select pg_backend_pid()').fetchone()[0]
        def waiting(count):
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                rows=observer.execute("select pid,wait_event_type,wait_event,pg_blocking_pids(pid) from pg_stat_activity where datname='cp6_rollback' and usename='authenticator' and wait_event_type='Lock' and position(%s in query)>0",(first[0],)).fetchall()
                if len(rows)>=count:
                    assert any(blocker_pid in x[3] for x in rows),'NO_REAL_ROW_BLOCKER'
                    return [dict(pid=x[0],wait_type=x[1],event=x[2],blockers=x[3]) for x in rows]
                time.sleep(.025)
            raise AssertionError('HTTP_REQUESTS_DID_NOT_REACH_EXPECTED_LOCK_BARRIER')
        try:
            one=pool.submit(rpc,*first);waiting(1)
            two=pool.submit(rpc,*second);observed=waiting(2)
        finally:blocker.rollback()
        return one.result(),two.result(),observed

def ready():
    batch=call('initial_import','CREATE',dict(batch_code='RACE-'+uuid.uuid4().hex,cutover_date=F['day']))['batch_id']
    code='R'+uuid.uuid4().hex[:12]
    for entity,rows in {
      'CUSTOMER':[dict(customer_code=code,customer_name='Before concurrent edit')],
      'OPENING_BALANCE_ITEM':[dict(balance_type='CUSTOMER_RECEIVABLE',customer_code=code,amount='14.25',control_key='AR')],
      'OPENING_CONTROL':[dict(control_key='AR',balance_type='CUSTOMER_RECEIVABLE',amount='14.25')],
    }.items():call('initial_import','SAVE_FILE',dict(batch_id=batch,expected_revision=workspace(batch)['revision'],entity=entity,filename=entity+'.csv',rows=[dict(source_row_no=i+2,payload=r) for i,r in enumerate(rows)]))
    call('initial_import','VALIDATE',dict(batch_id=batch,expected_revision=workspace(batch)['revision']))
    return batch,code

def import_races():
    batch,code=ready();payload=dict(batch_id=batch,expected_revision=workspace(batch)['revision'])
    c=cmd('initial_import','FINALIZE',payload)
    one,two,waits=pair('migration_batches',batch,c,c)
    assert one==two and ok(one)['status']=='POSTED',(one,two)
    before=boundary();assert rpc(*c)==one and boundary()==before
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        assert cur.execute('select count(*) from erp.customers where customer_code=%s',(code,)).fetchone()==(1,)
        assert cur.execute('select count(*),sum(i.amount) from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id where h.migration_batch_id=%s',(batch,)).fetchone()==(1,Decimal('14.25'))
    pass_case('IMPORT_SAME_UUID_FINALIZE',observed_waits=waits,one_customer=True,one_balance='14.25',exact_replay=True)
    batch,code=ready();revision=workspace(batch)['revision']
    edit=cmd('initial_import','SAVE_FILE',dict(batch_id=batch,expected_revision=revision,entity='CUSTOMER',filename='new.csv',rows=[dict(source_row_no=2,payload=dict(customer_code=code,customer_name='Latest concurrent edit'))]))
    final=cmd('initial_import','FINALIZE',dict(batch_id=batch,expected_revision=revision))
    one,two,waits=pair('migration_batches',batch,edit,final)
    ok(one);assert two['status']==400 and 'STALE_VERSION' in two['value']['message'],two
    assert workspace(batch)['status']=='DRAFT'
    posted=call('initial_import','FINALIZE',dict(batch_id=batch,expected_revision=workspace(batch)['revision']))
    assert posted['status']=='POSTED',posted
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        assert cur.execute('select customer_name from erp.customers where customer_code=%s',(code,)).fetchone()==('Latest concurrent edit',)
    pass_case('IMPORT_EDIT_BEFORE_FINALIZE',observed_waits=waits,stale_finalize_refused=True,refreshed_finalize_uses_latest=True)

def accessory_races():
    f=F['accessory'];baseline=current()
    def payload(qty):return dict(id=None,expected_version=None,number='RACE-'+uuid.uuid4().hex,contractor_id=f['contractor'],location_id=f['location'],po_id=None,physical_at=F['day']+'T10:15:00+07:00',reason='Real HTTP contention',notes='Disposable',items=[dict(material_id=f['material'],qty=str(qty),mode='MANUAL',manual_price='3.25')])
    c1=cmd('accessory_issue','POST',payload(200));c2=cmd('accessory_issue','POST',payload(200))
    one,two,waits=pair('materials',f['material'],c1,c2)
    assert one['status']==200 and two['status']==400,(one,two)
    assert two['value']['code'] not in ('42501','PGRST202','40P01'),two
    assert 'negative' in two['value']['message'].lower() or 'insufficient' in two['value']['message'].lower(),two
    assert Decimal(current()['accessory_stock'])==100
    with psycopg.connect(ADMIN) as conn,conn.cursor() as cur:
        assert cur.execute('select count(*) from erp.contractor_material_issues where issue_number=%s',(c2[1]['p_payload']['number'],)).fetchone()==(0,)
    posted=one['value'];call('accessory_issue','REVERSE',dict(id=posted['id'],expected_version=posted['row_version'],reason='Restore contention fixture'))
    assert current()['all_ledger']==baseline['all_ledger'] and Decimal(current()['accessory_stock'])==300
    pass_case('ACCESSORY_COMPETING_STOCK',observed_waits=waits,winner_pcs=200,loser_atomic=True,remaining_pcs=100,inverse_restored=True)
    c=cmd('accessory_issue','POST',payload(7));one,two,waits=pair('materials',f['material'],c,c)
    assert one==two and ok(one)['status']=='POSTED',(one,two)
    assert Decimal(current()['accessory_stock'])==293
    posted=one['value'];call('accessory_issue','REVERSE',dict(id=posted['id'],expected_version=posted['row_version'],reason='Restore duplicate request'))
    assert current()['all_ledger']==baseline['all_ledger'] and Decimal(current()['accessory_stock'])==300
    pass_case('ACCESSORY_SAME_UUID',observed_waits=waits,physical_pcs=7,exact_replay=True)

def pocket_races():
    f=F['pocket'];baseline=current()
    w=ok(rpc('erp_get_pocket_fabric_workspace_v1',dict(p_query=f['code'])))
    roll=next(x for x in w['rolls'] if x['id']==f['roll_id'])
    p=dict(roll_id=roll['id'],location_id=roll['location_id'],expected_revision=roll['revision'],mode='USED',quantity='5',date=F['day'],reason='Concurrent warehouse outflow')
    one,two,waits=pair('materials',f['material_id'],cmd('pocket_fabric','POST',p),cmd('pocket_fabric','POST',p))
    assert one['status']==200 and two['status']==400 and 'STALE_VERSION' in two['value']['message'],(one,two)
    issued=current();assert Decimal(issued['pocket_stock'])==15
    for k in ('WIP','FG_INVENTORY','COGS'):assert issued['ledger'][k]==baseline['ledger'][k]
    pass_case('POCKET_COMPETING_REVISION',observed_waits=waits,one_outflow=True,stock=15,product_hpp_unchanged=True)
    v=ok(rpc('erp_preview_pocket_fabric_period_v1',dict(p_period_start=F['period_start'],p_period_end=F['day'])))
    command=cmd('pocket_fabric','POST_PERIOD',dict(period_start=F['period_start'],period_end=F['day'],expected_revision=v['revision'],reason='Period busy and retry'))
    before=boundary()
    with psycopg.connect(ADMIN) as holder:
        holder.execute("select pg_advisory_xact_lock(hashtextextended('POCKET_HPP_PERIOD_V1',0))")
        denied=rpc(*command);assert denied['status']==400 and 'POCKET_PERIOD_BUSY' in denied['value']['message'],denied
        assert boundary()==before;holder.rollback()
    posted=ok(rpc(*command));assert posted['status']=='ACTIVE'
    w=ok(rpc('erp_get_pocket_fabric_workspace_v1',dict(p_query=f['code'])))
    period=next(x for x in w['periods'] if x['id']==posted['id'])
    call('pocket_fabric','CANCEL_PERIOD',dict(id=period['id'],expected_revision=period['revision'],reason='Restore period race'))
    h=next(x for x in w['history'] if x['id']==one['value']['id'])
    call('pocket_fabric','REVERSE',dict(id=h['id'],expected_version=h['row_version'],reason='Restore stock race'))
    assert current()['all_ledger']==baseline['all_ledger'] and Decimal(current()['pocket_stock'])==20
    pass_case('POCKET_PERIOD_BUSY_THEN_RETRY',real_second_session_mutex=True,refusal_atomic=True,retry_same_uuid=True,all_accounts_restored=True)

try:
    import_races();accessory_races();pocket_races();assert current()['unbalanced']==0;report['status']='PASS'
except Exception as exc:
    report.update(error=str(exc),traceback=traceback.format_exc());raise
finally:save()
