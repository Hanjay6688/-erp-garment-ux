"""Additional independently authored native cases; arithmetic in GAPS_NATIVE_NOTES.md.

Only our prior adapter/fixtures are reused. Never repairs product or disables guards.
"""
import json, traceback, time, threading, hashlib, secrets, subprocess
from decimal import Decimal as D
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import psycopg
from psycopg.types.json import Jsonb
import suite as s
import daily as d

C=s.CTX; F=d.F; E=s.EVENTS; R=[]; G={}
eq=s.eq; admin=s.admin; cmd=s.command; uid=s.uid
REPORT_DAYS=['2026-09-21','2026-09-22','2026-09-23']

class SetupBlocked(Exception): pass

def save():
    (s.OUT/'gaps-native-results.json').write_text(json.dumps({'candidate':'e96db5a270da5aa6d0f12c3812ac1c0542df938e',
        'oracle_sha256':hashlib.sha256((s.Path(__file__).parent/'GAPS_NATIVE_NOTES.md').read_bytes()).hexdigest(),
        'scope':'Own daily partial/multisource invoices, correction down, selected actual as-of snapshots, authenticated races, legitimate receipt browser fixture',
        'results':R,'production_go':False},indent=2,default=str)+'\n')
    (s.OUT/'gaps-native-events.json').write_text(json.dumps(E,indent=2,default=str)+'\n')
    (s.OUT/'gaps-native-fixture.json').write_text(json.dumps({'identity':C,'sources':F,'gaps':G},indent=2,default=str)+'\n')
s.save=save

def case(key,title,fn,needs=()):
    missing=[n for n in needs if n not in G]
    if missing:R.append({'id':key,'title':title,'status':'BLOCKED','classification':'previous prerequisite missing','missing':missing});save();return
    started=time.monotonic();r={'id':key,'title':title}
    try:r.update(status='PASS',observation=s.clean(fn()))
    except SetupBlocked as e:r.update(status='BLOCKED',classification='own adapter/setup',error=str(e),traceback=traceback.format_exc())
    except psycopg.Error as e:r.update(status='BLOCKED' if e.sqlstate in ('42601','42703','42P01','42883') else 'FAIL',classification='schema/adapter' if e.sqlstate in ('42601','42703','42P01','42883') else 'runtime business failure',error=str(e),sqlstate=e.sqlstate,traceback=traceback.format_exc())
    except Exception as e:r.update(status='FAIL',error=str(e),traceback=traceback.format_exc())
    r['seconds']=round(time.monotonic()-started,4);R.append(r);save();print(json.dumps({k:r.get(k) for k in ['id','title','status','classification','error']},default=str),flush=True)

def vendor_setup(code):
    vendor=uid()
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('app.change_reason','Independent supplemental vendor master',true)")
        c.execute('insert into erp.laundry_vendors(id,vendor_code,vendor_name) values(%s,%s,%s)',(vendor,code,code))
    C['daily_vendor']=vendor
    C['daily_wash']=s.component(vendor,code+'-WASH');C['daily_finish']=s.component(vendor,code+'-FINISH')
    s.rate(C['daily_wash'],'4321.09');s.rate(C['daily_finish'],'678.91');s.terms('COMPONENTS',vendor=vendor)
    return vendor

def setup():
    state=json.loads((s.OUT/'daily-fixture.json').read_text());C.update(state['identity'])
    for key in ['model','mandor','work_component','rawloc','fg','pattern','material','products','app_owner']:
        if key not in C:raise SetupBlocked('Prior independent daily master missing: '+key)
    G['vendor']=vendor_setup('AUD-GAPS')
    s.policy('LAU_DEC02',{'billable':['GOOD']});s.policy('LAU_DEC06',{'variance_mode':'PRODUCT_COST','after_payment':'CORRECTION_DOCUMENT'})
    return {'vendor':G['vendor'],'fixture_boundary':'Own controlled cutting/pickup, actual work/sewing; public laundry RPCs'}

def build_source(key,receive=True,fg=False):
    try:d.precursor(key)
    except Exception as e:raise SetupBlocked('Own cutting/pickup/work/sewing adapter: '+str(e)) from e
    shipped=d.ship(key);f=F[key]
    if receive:d.receive(key)
    if fg:
        response=d.rpc('POST_FINAL_SKU',d.qp(key),d.ver('cutting_groups',f['group']));f['qc']=response['qc_inspection_id']
        eq(d.qty(key),13);d.costeq(key,'60868.72')
    E.append({'independent_source_ready':key,'po':f['po'],'delivery':f['delivery'],'receipt':f.get('receipt'),'fg':fg,'oracle_initial_laundry':'59568.72','oracle_labor':'1300.00'})
    return f

def invoice_line(key,qty,amount,kind='BILL'):
    return {'line_kind':kind,'receipt_line_id':F[key]['receipt_line'],'category':'GOOD','qty':qty,'amount':amount,'note':'Independent remaining-coverage '+key}

def post_invoice(name,lines,total,date,corrects=None,connection=None):
    p={'vendor_id':G['vendor'],'invoice_number':'AUD-GAPS-'+name,'invoice_date':date,'header_total':total,'lines':lines}
    if corrects:p['corrects_invoice_id']=corrects
    def invoke(action,payload):
        if connection is None:return cmd(action,payload)
        request=uid();event={'api':'public.erp_save_laundry_bd_action_v1','action':action,'payload':payload,'request':request,'layer':'privileged private transaction, rolled back'}
        try:r=connection.execute('select public.erp_save_laundry_bd_action_v1(%s,%s,%s::uuid)',(action,Jsonb(payload),request)).fetchone()[0];event['response']=r;return r
        except psycopg.Error as e:event.update(error=str(e),sqlstate=e.sqlstate);raise
        finally:E.append(event)
    draft=invoke('SAVE_INVOICE_DRAFT',p)
    return invoke('POST_INVOICE',{'invoice_id':draft['invoice_id'],'expected_version':str(draft['row_version'])})

def po_accounts(key):
    return {mapping:admin("select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.po_id=%s and l.account_id=erp.account_id(%s) and j.status in('POSTED','REVERSED')",(F[key]['po'],mapping),one=True) for mapping in ['WIP','FG_INVENTORY','COGS','ACCRUED_MANUFACTURING']}

def vendor_ap():
    return admin("select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.vendor_id=%s and l.account_id=erp.account_id('AP_VENDOR') and j.status in('POSTED','REVERSED')",(G['vendor'],),one=True)

def invoice_journal(invoice,expected,connection=None):
    q="select case when l.account_id=erp.account_id('AP_VENDOR') then 'AP_VENDOR' when l.account_id=erp.account_id('WIP') then 'WIP' else a.account_code end,sum(l.debit),sum(l.credit) from erp.journal_lines l join erp.chart_accounts a on a.id=l.account_id where l.journal_entry_id=%s group by l.account_id,a.account_code order by 1"
    rows=connection.execute(q,(invoice['journal_id'],)).fetchall() if connection else admin(q,(invoice['journal_id'],))
    eq({a:(x,y) for a,x,y in rows},expected,'Independent journal debit/credit oracle')
    return rows

def financial_report(day,connection=None):
    sql='select erp.get_owner_financial_snapshot_v2(%s::date,%s::date,%s::date)';args=('2026-09-01',day,day)
    if connection:answer=connection.execute(sql,args).fetchone()[0]
    else:
        with s.actor_conn() as c:answer=c.execute(sql,args).fetchone()[0]
    E.append({'api':'erp.get_owner_financial_snapshot_v2','parameters':args,'layer':'actual report reader via SQL; not browser/HTTP','response':answer})
    eq(answer['basis']['balance_sheet_as_of'],day);return answer

def reports(days):return {day:financial_report(day) for day in days}

def check_report_delta(before,after,expected_by_day):
    observations={}
    for day,delta in expected_by_day.items():
        b=before[day]['financial_position'];a=after[day]['financial_position']
        fields={'fg_inventory':D(delta),'assets':D(delta),'liabilities':D(delta),'wip_inventory':D(0),'current_earnings':D(0),'recorded_equity':D(0),'balance_difference':D(0)}
        actual={k:D(a[k])-D(b[k]) for k in fields};eq(actual,fields,'Actual as-of reader delta '+day);observations[day]=actual
    return observations

def partial_source():
    f=build_source('GAP_PART',fg=True);G['partial_source']=f;G['report_before_partial']=reports(REPORT_DAYS)
    return {'source':f,'hpp':d.hpp('GAP_PART'),'accounts':po_accounts('GAP_PART')}

def partial_seven():
    key='GAP_PART';before=d.qty(key);r=post_invoice('PART7',[invoice_line(key,7,'32978.74')],'32978.74','2026-09-22');G['part7']=r
    line=admin('select qty,released_estimate,variance,product_variance from erp.bd_laundry_invoice_lines_v1 where invoice_id=%s',(r['invoice_id'],))[0];eq(line,(7,D('32075.46'),D('903.28'),D('903.28')))
    eq(d.qty(key),before);d.costeq(key,'61772.00');eq(vendor_ap(),D('32978.74'))
    account=po_accounts(key);eq(account,{'WIP':D(0),'FG_INVENTORY':D('61772.00'),'COGS':D(0),'ACCRUED_MANUFACTURING':-D('27493.26')})
    journal=invoice_journal(r,{'WIP':(D('32978.74'),D(0)),'AP_VENDOR':(D(0),D('32978.74'))})
    after=reports(REPORT_DAYS);delta=check_report_delta(G['report_before_partial'],after,{'2026-09-21':'0','2026-09-22':'903.28','2026-09-23':'903.28'});G['report_after_seven']=after
    return {'invoice':r,'line_readback':line,'journal':journal,'accounts':account,'actual_asof_report_deltas':delta,'quantity_unchanged':before}

def partial_six():
    key='GAP_PART';before=d.qty(key);r=post_invoice('PART6',[invoice_line(key,6,'28267.50')],'28267.50','2026-09-23');G['part6']=r
    line=admin('select qty,released_estimate,variance,product_variance from erp.bd_laundry_invoice_lines_v1 where invoice_id=%s',(r['invoice_id'],))[0];eq(line,(6,D('27493.26'),D('774.24'),D('774.24')))
    sums=admin("select sum(x.qty),sum(x.net_amount),sum(x.released_estimate),sum(x.variance) from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 h on h.id=x.invoice_id where h.status='POSTED' and x.receipt_line_id=%s",(F[key]['receipt_line'],))[0]
    eq(sums,(13,D('61246.24'),D('59568.72'),D('1677.52')));eq(d.qty(key),before);d.costeq(key,'62546.24');eq(vendor_ap(),D('61246.24'))
    account=po_accounts(key);eq(account,{'WIP':D(0),'FG_INVENTORY':D('62546.24'),'COGS':D(0),'ACCRUED_MANUFACTURING':D(0)})
    journal=invoice_journal(r,{'WIP':(D('28267.50'),D(0)),'AP_VENDOR':(D(0),D('28267.50'))})
    after=reports(REPORT_DAYS);delta=check_report_delta(G['report_after_seven'],after,{'2026-09-21':'0','2026-09-22':'0','2026-09-23':'774.24'});G['partial_complete']=True
    return {'invoice':r,'line_readback':line,'all_billed_source_totals':sums,'journal':journal,'accounts':account,'actual_asof_report_deltas':delta,'quantity_unchanged':before}

def paid_original():
    r=G['part7'];cash=admin('select id::text from erp.cash_accounts where is_active order by cash_account_code limit 1',one=True)
    response=cmd('PAY_VENDOR_DOCUMENT',{'target_kind':'VENDOR_INVOICE','target_id':r['invoice_id'],'amount':'32978.74','date':'2026-09-24','cash_account_id':cash,'reason':'Independent full payment before downward correction'})
    eq(D(response['remaining']),D(0));eq(vendor_ap(),D('28267.50'));d.costeq('GAP_PART','62546.24');eq(d.qty('GAP_PART'),13)
    G['paid_original']=d.row('bd_laundry_invoices_v1',r['invoice_id']);G['paid_payment_rows']=admin('select to_jsonb(t) from erp.vendor_payments t where vendor_invoice_id=%s order by id',(r['invoice_id'],));G['paid_journal_rows']=admin('select to_jsonb(t) from erp.journal_lines t where journal_entry_id=%s order by id',(r['journal_id'],))
    return {'payment':response,'payable_after_payment':'28267.50','current_hpp':'62546.24','qty':13}

def correction_down():
    days=['2026-09-24','2026-09-25'];before=reports(days);physical=d.qty('GAP_PART')
    r=post_invoice('CORRECTION-DOWN',[invoice_line('GAP_PART',0,'-113.57','CORRECTION')],'-113.57','2026-09-25',G['part7']['invoice_id']);G['down']=r
    eq(r['corrects_invoice_id'],G['part7']['invoice_id']);eq(r['status'],'POSTED');eq(vendor_ap(),D('28153.93'))
    eq(d.row('bd_laundry_invoices_v1',G['part7']['invoice_id']),G['paid_original'],'Paid original remains identical')
    eq(admin('select to_jsonb(t) from erp.vendor_payments t where vendor_invoice_id=%s order by id',(G['part7']['invoice_id'],)),G['paid_payment_rows'])
    eq(admin('select to_jsonb(t) from erp.journal_lines t where journal_entry_id=%s order by id',(G['part7']['journal_id'],)),G['paid_journal_rows'])
    eq(d.qty('GAP_PART'),physical);values=d.costeq('GAP_PART','62432.67')
    journal=invoice_journal(r,{'WIP':(D(0),D('113.57')),'AP_VENDOR':(D('113.57'),D(0))})
    with s.actor_conn() as c:workspace=c.execute('select public.erp_get_laundry_bd_workspace_v1(%s)',(Jsonb({'vendor_id':G['vendor']}),)).fetchone()[0]
    E.append({'api':'public.erp_get_laundry_bd_workspace_v1','vendor':G['vendor'],'response':workspace})
    ledger=workspace['payables']['ledger'];eq(D(ledger['ap_balance']),D('28153.93'));eq(D(ledger['credit_available']),D('113.57'));eq(D(ledger['documents_remaining']),D('28267.50'));eq(ledger['matches'],True)
    delta=check_report_delta(before,reports(days),{'2026-09-24':'0','2026-09-25':'-113.57'})
    return {'correction':r,'journal':journal,'hpp':values,'public_payables':ledger,'actual_asof_report_deltas':delta,'quantity_unchanged':physical,'paid_original_preserved':True}

def correction_closed():
    # Only the isolated cutoff prerequisite and native transaction differ. The
    # tested correction command is the same public router. Never certifies close.
    today=datetime.now(ZoneInfo('Asia/Jakarta')).date().isoformat();origin=G['part7']['invoice_id']
    cutoff_before=admin('select to_jsonb(t) from erp.accounting_period_control t')
    with psycopg.connect(s.DSN) as c:
        try:
            c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));c.execute("select set_config('app.change_reason','Independent closed correction rollback fixture',true)")
            old=c.execute('select to_jsonb(t) from erp.bd_laundry_invoices_v1 t where id=%s',(origin,)).fetchall();payment=c.execute('select to_jsonb(t) from erp.vendor_payments t where vendor_invoice_id=%s order by id',(origin,)).fetchall()
            closed_sql="select to_jsonb(j),coalesce((select jsonb_agg(to_jsonb(l) order by l.id) from erp.journal_lines l where l.journal_entry_id=j.id),'[]') from erp.journal_entries j where j.transaction_date<='2026-09-25' and j.status in('POSTED','REVERSED') order by j.id"
            balance_sql="select to_jsonb(t) from erp.account_daily_balances t where balance_date<='2026-09-25' order by balance_date,account_id"
            history=c.execute(closed_sql).fetchall();balances=c.execute(balance_sql).fetchall()
            before={day:financial_report(day,c) for day in ['2026-09-25',today]}
            c.execute("update erp.accounting_period_control set closed_through='2026-09-25',change_reason='Independent rolled-back closed correction prerequisite' where singleton_id=1")
            r=post_invoice('CLOSED-DOWN',[invoice_line('GAP_PART',0,'-9.13','CORRECTION')],'-9.13','2026-09-25',origin,c)
            journal=invoice_journal(r,{'WIP':(D(0),D('9.13')),'AP_VENDOR':(D('9.13'),D(0))},c)
            dates=c.execute('select transaction_date::text,economic_date::text from erp.journal_entries where id=%s',(r['journal_id'],)).fetchone();eq(dates,(today,'2026-09-25'))
            eq(c.execute(closed_sql).fetchall(),history);eq(c.execute(balance_sql).fetchall(),balances)
            eq(c.execute('select to_jsonb(t) from erp.bd_laundry_invoices_v1 t where id=%s',(origin,)).fetchall(),old);eq(c.execute('select to_jsonb(t) from erp.vendor_payments t where vendor_invoice_id=%s order by id',(origin,)).fetchall(),payment)
            after={day:financial_report(day,c) for day in ['2026-09-25',today]};delta=check_report_delta(before,after,{'2026-09-25':'0',today:'-9.13'})
            observation={'correction':r,'journal':journal,'dates':dates,'closed_journal_count_unchanged':len(history),'closed_daily_balances_unchanged':True,'paid_original_and_payments_unchanged':True,'actual_asof_report_deltas':delta,'boundary':'Synthetic cutoff, native privileged session, full rollback; no closing-workflow acceptance'}
        finally:c.rollback()
    eq(admin('select to_jsonb(t) from erp.accounting_period_control t'),cutoff_before);eq(admin("select count(*) from erp.bd_laundry_invoices_v1 where invoice_number='AUD-GAPS-CLOSED-DOWN'",one=True),0)
    return observation

def multi_source_invoice():
    a=build_source('GAP_MULTI_A',fg=True);b=build_source('GAP_MULTI_B',fg=True);before_ap=vendor_ap()
    r=post_invoice('MULTI',[invoice_line('GAP_MULTI_A',13,'61246.24'),invoice_line('GAP_MULTI_B',13,'62002.31')],'123248.55','2026-09-23');G['multi']=r
    rows=admin('select receipt_line_id::text,qty,net_amount,released_estimate,variance from erp.bd_laundry_invoice_lines_v1 where invoice_id=%s order by line_no',(r['invoice_id'],))
    eq(rows,[(a['receipt_line'],13,D('61246.24'),D('59568.72'),D('1677.52')),(b['receipt_line'],13,D('62002.31'),D('59568.72'),D('2433.59'))])
    eq(sum(x[3] for x in rows),D('119137.44'));eq(sum(x[4] for x in rows),D('4111.11'))
    d.costeq('GAP_MULTI_A','62546.24');d.costeq('GAP_MULTI_B','63302.31');eq(d.qty('GAP_MULTI_A')+d.qty('GAP_MULTI_B'),26);eq(vendor_ap()-before_ap,D('123248.55'))
    ledgers={k:po_accounts(k) for k in ['GAP_MULTI_A','GAP_MULTI_B']}
    eq(sum(x['FG_INVENTORY'] for x in ledgers.values()),D('125848.55'));eq(sum(x['WIP'] for x in ledgers.values()),D(0));eq(sum(x['COGS'] for x in ledgers.values()),D(0));eq(sum(x['ACCRUED_MANUFACTURING'] for x in ledgers.values()),D(0))
    journal=invoice_journal(r,{'WIP':(D('123248.55'),D(0)),'AP_VENDOR':(D(0),D('123248.55'))})
    return {'invoice':r,'source_lines':rows,'journal':journal,'po_ledgers':ledgers,'combined_qty':26,'combined_fg_cost':'125848.55'}

def two_sessions(sql,argsets,events,actors=('owner','owner')):
    gate=threading.Barrier(2)
    def work(i):
        who=actors[i]
        with s.actor_conn(who) as c:
            authid,appid,role,pid=c.execute('select auth.uid()::text,erp.current_app_user_id()::text,erp.current_app_role(),pg_backend_pid()').fetchone()
            eq(authid,C[who]);eq(role,'OWNER');assert appid is not None
            identity={'actor':who,'auth_id':authid,'erp_user_id':appid,'erp_role':role,'backend_pid':pid}
            c.commit();gate.wait(timeout=20)
            try:r=c.execute(sql,argsets[i]).fetchone()[0];c.commit();answer={**identity,'accepted':True,'response':r}
            except psycopg.Error as e:c.rollback();answer={**identity,'accepted':False,'sqlstate':e.sqlstate,'error':str(e)}
            E.append({**events[i],**answer,'layer':'distinct authenticator/authenticated sessions'});return answer
    with ThreadPoolExecutor(max_workers=2) as pool:out=list(pool.map(work,range(2)))
    eq(len({x['backend_pid'] for x in out}),2);eq(sum(x['accepted'] for x in out),1);return out

def receipt_race():
    key='GAP_RACE';f=build_source(key,receive=False);p=d.rp(key);version=d.ver('laundry_deliveries',f['delivery']);requests=[uid(),uid()]
    before=po_accounts(key)
    out=two_sessions('select public.erp_save_laundry_qc_action_v1(%s,%s,%s::uuid,%s)',[('POST_RECEIPT',Jsonb(p),r,version) for r in requests],[{'api':'public.erp_save_laundry_qc_action_v1','action':'POST_RECEIPT','payload':p,'request':r,'expected_version':version} for r in requests])
    loser=next(x for x in out if not x['accepted']);eq(loser['sqlstate'],'P0001')
    if not any(token in loser['error'] for token in ['STALE_VERSION','active SENT/PARTIAL_RETURN','exceeds remaining']):raise AssertionError('Unexpected receipt-race refusal: '+loser['error'])
    rows=admin("select count(*),coalesce(sum(l.qty_good_received),0),coalesce(sum(l.qty_bs_laundry),0) from erp.laundry_receipts h join erp.laundry_receipt_lines l on l.receipt_id=h.id where h.delivery_id=%s and h.status='POSTED'",(f['delivery'],))[0];eq(rows,(1,13,0));eq(d.qty(key),0);eq(po_accounts(key),before)
    return {'sessions':out,'posted_receipt_count_good_bs':rows,'accrual_and_wip_cost_preserved':before,'fg_qty':0}

def policy_race():
    original=admin("select to_jsonb(t) from erp.bd_policy_settings_v1 t where policy_key='LAU_DEC01'",one=True);version=str(original['version']);requests=[uid(),uid()]
    payloads=[{'policy_key':'LAU_DEC01','operation':'SET','expected_version':version,'reason':'Independent simultaneous owner policy edit '+str(i),'value':{'units':[v]}} for i,v in enumerate(['BATCH','MINIMUM'])]
    event_count=admin("select count(*) from erp.bd_policy_setting_events_v1 where policy_key='LAU_DEC01'",one=True)
    try:
        out=two_sessions('select public.erp_save_laundry_bd_action_v1(%s,%s,%s::uuid)',[('SET_POLICY',Jsonb(p),r) for p,r in zip(payloads,requests)],[{'api':'public.erp_save_laundry_bd_action_v1','action':'SET_POLICY','payload':p,'request':r} for p,r in zip(payloads,requests)])
        loser=next(x for x in out if not x['accepted']);eq(loser['sqlstate'],'P0001');assert 'STALE_VERSION' in loser['error'],loser
        current=admin("select to_jsonb(t) from erp.bd_policy_settings_v1 t where policy_key='LAU_DEC01'",one=True);eq(int(current['version']),int(original['version'])+1)
        eq(admin("select count(*) from erp.bd_policy_setting_events_v1 where policy_key='LAU_DEC01'",one=True),event_count+1)
        winner=next(i for i,x in enumerate(out) if x['accepted']);eq(current['value'],payloads[winner]['value']);again=cmd('SET_POLICY',payloads[winner],requests[winner])
        eq(again.get('replayed') is True,True,'Replay explicitly identifies the saved response')
        eq(again,{**out[winner]['response'],'replayed':True},'Replay preserves every original response field')
        eq(admin("select to_jsonb(t) from erp.bd_policy_settings_v1 t where policy_key='LAU_DEC01'",one=True),current,'Replay leaves policy state and version unchanged')
        eq(admin("select count(*) from erp.bd_policy_setting_events_v1 where policy_key='LAU_DEC01'",one=True),event_count+1)
        observation={'sessions':out,'winning_value':current['value'],'version_increased_by_one':True,'one_setting_event':True,'same_request_replay':again,'replay_state_and_event_count_unchanged':True}
    finally:
        current_version=admin("select version from erp.bd_policy_settings_v1 where policy_key='LAU_DEC01'",one=True)
        p={'policy_key':'LAU_DEC01','operation':'SET' if original['status']=='SET' else 'CLEAR','expected_version':str(current_version),'reason':'Restore independent fixture policy after concurrency test'}
        if original['status']=='SET':p['value']=original['value']
        cmd('SET_POLICY',p)
    return observation

def local_auth_request(path,payload,apikey,bearer=None):
    # Authentication setup only. Never append credentials, keys, or tokens to E.
    data=None if payload is None else json.dumps(payload).encode()
    req=Request('http://127.0.0.1:54321/auth/v1/'+path,data=data,
        headers={'Content-Type':'application/json','apikey':apikey,'Authorization':'Bearer '+(bearer or apikey)},
        method='GET' if payload is None else 'POST')
    try:
        with urlopen(req,timeout=30) as response:status,body=response.status,response.read()
    except HTTPError as e:status,body=e.code,e.read()
    except (URLError,TimeoutError):raise SetupBlocked('Isolated local Auth endpoint unavailable') from None
    try:answer=json.loads(body)
    except (ValueError,UnicodeDecodeError):raise SetupBlocked('Isolated local Auth returned non-JSON') from None
    if status not in (200,201):raise SetupBlocked('Isolated local Auth '+path+' returned HTTP '+str(status))
    return answer

def distinct_owner_controls():
    actors=('race_owner_a','race_owner_b')
    if 'two_operators' not in G:
        # Auth uses the already running disposable GoTrue service. ERP role rows
        # live in cp6_rollback and are inserted with all normal guards enabled.
        try:help_result=subprocess.run(['supabase','status','--help'],capture_output=True,text=True,timeout=30)
        except (OSError,subprocess.TimeoutExpired):raise SetupBlocked('Cannot inspect local Supabase status command') from None
        if help_result.returncode or any(flag not in help_result.stdout for flag in ['--output','--workdir']):
            raise SetupBlocked('Local Supabase status command contract unavailable')
        try:runtime=subprocess.run(['supabase','status','--workdir',str(s.ROOT.parent/'base'/'cp5-local'),'--output','json'],capture_output=True,text=True,timeout=30)
        except (OSError,subprocess.TimeoutExpired):raise SetupBlocked('Cannot inspect isolated local Auth runtime') from None
        if runtime.returncode:raise SetupBlocked('Cannot read isolated local Auth runtime configuration')
        try:keys=json.loads(runtime.stdout)
        except ValueError:raise SetupBlocked('Local Auth runtime configuration is not JSON') from None
        if not keys.get('ANON_KEY') or not keys.get('SERVICE_ROLE_KEY'):raise SetupBlocked('Isolated local Auth keys unavailable')
        rid=admin("select id from erp.app_roles where role_code='OWNER' and is_active",one=True)
        if not rid:raise SetupBlocked('Active OWNER role missing')
        identities={}
        for who in actors:
            email='bd-gap-'+who+'-'+uid()[:8]+'@example.test';password='Bd-Audit-'+secrets.token_hex(16)+'!'
            user=local_auth_request('admin/users',{'email':email,'password':password,'email_confirm':True},keys['SERVICE_ROLE_KEY'])
            authid=user.get('id')
            if not authid:raise SetupBlocked('Local Auth creation did not return a user ID')
            session=local_auth_request('token?grant_type=password',{'email':email,'password':password},keys['ANON_KEY'])
            if session.get('user',{}).get('id')!=authid or not session.get('access_token'):
                raise SetupBlocked('Local Auth password control did not identify the created operator')
            verified=local_auth_request('user',None,keys['ANON_KEY'],session['access_token'])
            if verified.get('id')!=authid:raise SetupBlocked('Local Auth token control returned a different operator')
            try:
                with psycopg.connect(s.DSN) as c:
                    c.execute("select set_config('app.change_reason','Independent distinct-operator audit prerequisite',true)")
                    appid=c.execute("insert into erp.app_users(auth_user_id,full_name,role,role_id) values(%s,%s,'OWNER',%s) returning id::text",
                        (authid,'AUD-GAPS-'+who,rid)).fetchone()[0]
            except psycopg.Error as e:raise SetupBlocked('Guarded independent ERP actor prerequisite: '+str(e)) from e
            C[who]=authid;identities[who]={'auth_id':authid,'erp_user_id':appid,'role_id':str(rid),'real_password_authentication':True,'auth_token_user_verified':True}
            E.append({'distinct_operator_fixture':who,**identities[who],'boundary':'Local GoTrue Auth prerequisite plus guarded ERP app-user insert; races use native SQL actor context'})
        eq(len({x['auth_id'] for x in identities.values()}|{C['owner']}),3,'Two operators and original owner have distinct Auth IDs')
        eq(len({x['erp_user_id'] for x in identities.values()}|{C['app_owner']}),3,'Two operators and original owner have distinct ERP app-user IDs')
        G['two_operators']=identities
    controls=[]
    for who in actors:
        with s.actor_conn(who) as c:
            identity=c.execute("select auth.uid()::text,erp.current_app_user_id()::text,erp.current_app_role()").fetchone()
            access=c.execute('select public.erp_get_my_access_v1()').fetchone()[0]
            workspace=c.execute('select public.erp_get_laundry_bd_workspace_v1(%s)',(Jsonb({'vendor_id':G['vendor']}),)).fetchone()[0]
        expected=G['two_operators'][who]
        eq(identity,(expected['auth_id'],expected['erp_user_id'],'OWNER'),'Per-operator identity and active role control')
        eq(access['allowed'],True);eq(access['profile']['is_active'],True)
        eq(access['profile']['id'],expected['erp_user_id']);eq(access['profile']['auth_user_id'],expected['auth_id']);eq(access['profile']['role_code'],'OWNER')
        permissions=set(access['permissions'])
        eq({'production.laundry.post','settings.erp.manage'}.issubset(permissions),True,'Permissions from the supported public access reader')
        eq(workspace['is_owner'],True);eq(workspace['money_visible'],True)
        control={'actor':who,**expected,'erp_role':identity[2],'can_post_laundry':'production.laundry.post' in permissions,'can_manage_settings':'settings.erp.manage' in permissions,'authorization_reader':'public.erp_get_my_access_v1','workspace_is_owner':workspace['is_owner'],'money_visible':workspace['money_visible']}
        controls.append(control);E.append({'distinct_operator_positive_control':control})
    return actors,controls

def assert_distinct_operators(out):
    eq(len({x['auth_id'] for x in out}),2);eq(len({x['erp_user_id'] for x in out}),2)
    for row in out:
        expected=G['two_operators'][row['actor']]
        eq(row['auth_id'],expected['auth_id']);eq(row['erp_user_id'],expected['erp_user_id']);eq(row['erp_role'],'OWNER')

def two_actor_receipt_race():
    actors,controls=distinct_owner_controls();key='GAP_RACE_ACTORS';f=build_source(key,receive=False)
    p=d.rp(key);version=d.ver('laundry_deliveries',f['delivery']);requests=[uid(),uid()]
    before=po_accounts(key);eq(before,{'WIP':D('60868.72'),'FG_INVENTORY':D(0),'COGS':D(0),'ACCRUED_MANUFACTURING':-D('59568.72')})
    sql='select public.erp_save_laundry_qc_action_v1(%s,%s,%s::uuid,%s)'
    out=two_sessions(sql,[('POST_RECEIPT',Jsonb(p),r,version) for r in requests],
        [{'api':'public.erp_save_laundry_qc_action_v1','action':'POST_RECEIPT','payload':p,'request':r,'expected_version':version} for r in requests],actors)
    assert_distinct_operators(out);winner=next(i for i,x in enumerate(out) if x['accepted']);loser=out[1-winner]
    eq(loser['sqlstate'],'P0001')
    if not any(token in loser['error'] for token in ['STALE_VERSION','active SENT/PARTIAL_RETURN','exceeds remaining']):raise AssertionError('Unexpected two-operator receipt refusal: '+loser['error'])
    winner_app=out[winner]['erp_user_id'];receipt_id=out[winner]['response']['receipt_id']
    def state():
        rows=admin("select count(*),coalesce(sum(l.qty_good_received),0),coalesce(sum(l.qty_bs_laundry),0),min(h.created_by::text) from erp.laundry_receipts h join erp.laundry_receipt_lines l on l.receipt_id=h.id where h.delivery_id=%s and h.status='POSTED'",(f['delivery'],))[0]
        return {'posted_count_good_bs_actor':rows,'delivery':d.row('laundry_deliveries',f['delivery']),'receipt':d.row('laundry_receipts',receipt_id),'accounts':po_accounts(key),'fg_qty':d.qty(key)}
    after=state();eq(after['posted_count_good_bs_actor'],(1,13,0,winner_app));eq(after['delivery']['row_version'],version+1)
    eq(after['delivery']['status'],'RETURNED');eq(after['accounts'],before);eq(after['fg_qty'],0)
    with s.actor_conn(actors[winner]) as c:replay=c.execute(sql,('POST_RECEIPT',Jsonb(p),requests[winner],version)).fetchone()[0]
    E.append({'api':'public.erp_save_laundry_qc_action_v1','action':'POST_RECEIPT','actor':actors[winner],'auth_id':out[winner]['auth_id'],'erp_user_id':winner_app,'request':requests[winner],'payload':p,'expected_version':version,'response':replay,'layer':'winning distinct operator replay via native SQL'})
    eq(replay,out[winner]['response'],'Receipt replay preserves the winning operator response');eq(state(),after,'Receipt replay has no additional physical/version/cost effect')
    return {'controls':controls,'sessions':out,'winning_app_user':winner_app,'posted_receipt_count_good_bs':after['posted_count_good_bs_actor'][:3],'delivery_version_before':version,'delivery_version_after':after['delivery']['row_version'],'accounts':after['accounts'],'fg_qty':0,'winner_replay':replay,'replay_state_unchanged':True}

def two_actor_policy_race():
    actors,controls=distinct_owner_controls()
    original=admin("select to_jsonb(t) from erp.bd_policy_settings_v1 t where policy_key='LAU_DEC01'",one=True);version=int(original['version']);requests=[uid(),uid()]
    payloads=[{'policy_key':'LAU_DEC01','operation':'SET','expected_version':str(version),'reason':'Independent distinct operator policy edit '+str(i),'value':{'units':[v]}} for i,v in enumerate(['BATCH','MINIMUM'])]
    event_count=admin("select count(*) from erp.bd_policy_setting_events_v1 where policy_key='LAU_DEC01'",one=True)
    event_sql="select version,set_by::text,request_id::text,value from erp.bd_policy_setting_events_v1 where policy_key='LAU_DEC01' and version>%s order by version"
    request_sql="select request_id::text,actor::text,action from erp.bd_requests_v1 where request_id in(%s::uuid,%s::uuid) order by request_id"
    try:
        out=two_sessions('select public.erp_save_laundry_bd_action_v1(%s,%s,%s::uuid)',[('SET_POLICY',Jsonb(p),r) for p,r in zip(payloads,requests)],
            [{'api':'public.erp_save_laundry_bd_action_v1','action':'SET_POLICY','payload':p,'request':r} for p,r in zip(payloads,requests)],actors)
        assert_distinct_operators(out);winner=next(i for i,x in enumerate(out) if x['accepted']);loser=out[1-winner]
        eq(loser['sqlstate'],'P0001');assert 'STALE_VERSION' in loser['error'],loser
        current=admin("select to_jsonb(t) from erp.bd_policy_settings_v1 t where policy_key='LAU_DEC01'",one=True)
        eq(int(current['version']),version+1);eq(current['value'],payloads[winner]['value']);eq(current['set_by'],out[winner]['erp_user_id'])
        eq(admin("select count(*) from erp.bd_policy_setting_events_v1 where policy_key='LAU_DEC01'",one=True),event_count+1)
        events=admin(event_sql,(version,));eq(events,[(version+1,out[winner]['erp_user_id'],requests[winner],payloads[winner]['value'])])
        request_rows=admin(request_sql,tuple(requests));eq(request_rows,[(requests[winner],out[winner]['erp_user_id'],'SET_POLICY')])
        replay=cmd('SET_POLICY',payloads[winner],requests[winner],who=actors[winner])
        eq(replay.get('replayed') is True,True);eq(replay,{**out[winner]['response'],'replayed':True})
        eq(admin("select to_jsonb(t) from erp.bd_policy_settings_v1 t where policy_key='LAU_DEC01'",one=True),current)
        eq(admin("select count(*) from erp.bd_policy_setting_events_v1 where policy_key='LAU_DEC01'",one=True),event_count+1)
        eq(admin(event_sql,(version,)),events);eq(admin(request_sql,tuple(requests)),request_rows)
        observation={'controls':controls,'sessions':out,'version_before':version,'version_after':int(current['version']),'one_setting_event':events,'one_request_row':request_rows,'winning_actor_replay':replay,'replay_policy_events_requests_unchanged':True}
    finally:
        current_version=admin("select version from erp.bd_policy_settings_v1 where policy_key='LAU_DEC01'",one=True)
        p={'policy_key':'LAU_DEC01','operation':'SET' if original['status']=='SET' else 'CLEAR','expected_version':str(current_version),'reason':'Original owner restores policy after independent two-operator race'}
        if original['status']=='SET':p['value']=original['value']
        restored=cmd('SET_POLICY',p,who='owner')
        restored_row=admin("select to_jsonb(t) from erp.bd_policy_settings_v1 t where policy_key='LAU_DEC01'",one=True)
        eq(restored_row['status'],original['status']);eq(restored_row['value'],original['value']);eq(restored_row['set_by'],C['app_owner'])
    observation['restored_by_original_owner']={'auth_id':C['owner'],'erp_user_id':C['app_owner'],'response':restored}
    return observation

def build_browser_receipts(count=201):
    if count!=201:raise SetupBlocked('Browser fixture expectation fixed at 201')
    vendor=vendor_setup('AUD-GAPS-BROWSER');receipt_ids=[];line_ids=[];provenance=[];sources=[]
    for group_no in range(16):
        key='GAP_BROWSE_'+str(group_no+1).zfill(2);start=len(E);f=build_source(key,receive=False);sources.append({'po_id':f['po'],'delivery_id':f['delivery'],'capacity':13})
        pieces=admin('select id::text,qty_sent_pcs from erp.laundry_delivery_batch_size_lines where delivery_line_id=%s order by size_id',(f['delivery_line'],))
        for size_line,qty in pieces:
            for _ in range(qty):
                if len(line_ids)>=count:break
                p={'delivery_id':f['delivery'],'wash_process_id':C['process'],'physical_at':'2026-09-21T08:00:00+07:00','reason':'Independent legitimate single-piece receipt for pagination audit','lines':[{'delivery_batch_size_line_id':size_line,'qty_good_received':1,'qty_bs_laundry':0,'bs_product_id':None}]}
                r=d.rpc('POST_RECEIPT',p,d.ver('laundry_deliveries',f['delivery']));eq(r['good_qty_pcs'],1);eq(r['bs_qty_pcs'],0)
                receipt_ids.append(r['receipt_id']);line_ids.append(admin('select id::text from erp.laundry_receipt_lines where receipt_id=%s',(r['receipt_id'],),one=True))
        provenance.extend({'api':e.get('api','public.erp_save_laundry_bd_action_v1'),'action':e.get('action'),'request':e.get('request')} for e in E[start:] if e.get('action') in ['POST_PRICED_DELIVERY','POST_RECEIPT'])
        print(json.dumps({'browser_receipt_fixture_progress':len(line_ids),'target':count}),flush=True)
        save()
    eq(len(set(line_ids)),201);eq(len(set(receipt_ids)),201)
    valid=admin("select count(*),sum(l.qty_good_received),sum(l.qty_bs_laundry),count(*) filter(where l.actual_cost is not null and l.actual_cost_status='ESTIMATED') from erp.laundry_receipt_lines l join erp.laundry_receipts h on h.id=l.receipt_id join erp.laundry_deliveries v on v.id=h.delivery_id where v.vendor_id=%s and h.status='POSTED'",(vendor,))[0];eq(valid,(201,201,0,201))
    eq(admin("select count(*) from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 h on h.id=x.invoice_id where h.vendor_id=%s and h.status='POSTED'",(vendor,),one=True),0)
    payload={'vendor_id':vendor,'receipt_line_ids':line_ids,'receipt_ids':receipt_ids,'expected_count':201,'expected_good_pcs':201,'source_capacity_pcs':208,'expected_still_at_laundry_pcs':7,'sources':sources,'provenance':provenance,'boundary':'Controlled cutting/pickup prerequisites; every delivery and receipt through public authenticated SQL RPC; known estimate, GOOD and unbilled'}
    path=s.OUT/'remaining-fixture.json';existing=json.loads(path.read_text()) if path.exists() else {};existing['browser_receipts']=payload;path.write_text(json.dumps(existing,indent=2,default=str)+'\n');G['browser_receipts']=payload
    return {'vendor':vendor,'eligible_receipt_count':201,'good_pcs':201,'unbilled':True,'source_capacity':208,'remaining_custody':7,'fixture_file':'remaining-fixture.json'}

def main():
    try:E.append({'setup':setup()});save()
    except Exception as e:R.append({'id':'SETUP.GAPS','status':'BLOCKED','error':str(e),'traceback':traceback.format_exc()});save();return 1
    case('GAP.PARTIAL.SOURCE','Own daily physical source and baseline actual as-of reports',partial_source)
    case('GAP.PARTIAL.7','Daily 7-PCS invoice releases exact estimate and recosts only from its date',partial_seven,['partial_source'])
    case('GAP.PARTIAL.6','Remaining 6-PCS invoice conserves final source cost and prior report dates',partial_six,['part7','report_after_seven'])
    case('GAP.DOWN.PAID','Pay original 7-PCS invoice without extra product cost',paid_original,['partial_complete'])
    case('GAP.DOWN.OPEN','Downward correction after payment preserves original and moves current cost/AP',correction_down,['paid_original'])
    case('GAP.DOWN.CLOSED','Closed-period downward correction preserves old journals and actual as-of report',correction_closed,['down'])
    case('GAP.MULTI-SOURCE','One positive invoice over two real receipt sources conserves cost, HPP and quantity',multi_source_invoice)
    case('GAP.RACE.RECEIPT','Two authenticated sessions compete for the same receipt capacity',receipt_race)
    case('GAP.RACE.POLICY','Two authenticated policy updates have one event/version and replay one effect',policy_race)
    case('GAP.RACE.RECEIPT.TWO-ACTORS','Two distinct authorized operators compete for one fresh receipt capacity',two_actor_receipt_race)
    case('GAP.RACE.POLICY.TWO-ACTORS','Two distinct authorized owners produce one policy version/event and replay as winner',two_actor_policy_race,['two_operators'])
    case('GAP.BROWSER.SOURCES','Build 201 legitimate known-priced unbilled receipt lines for live UI check',build_browser_receipts)
    save();return int(any(r['status']!='PASS' for r in R))

if __name__=='__main__':raise SystemExit(main())
