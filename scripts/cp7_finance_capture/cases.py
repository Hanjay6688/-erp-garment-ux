"""OW-12a Native cases: the staged finance capture gives the official report's figures in bounded steps.

The capture functions are private (owned by cp7_capture, as the staged jobs that call them); cases call them as that
owner with the actor's Auth claims, exactly as a staged job does. Business Report v2 is driven through its public
RPCs. Figures are compared with the accepted owner report reader and the direct analysis' own source on the same state;
the book signature is recomputed independently here from the same rows.
"""
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
import uuid

import psycopg
from psycopg.pq import TransactionStatus

import cp7_analysis_cases as analysis
import cp7_analysis_finance_cases as finance_cases
import cp7_cp17_fix_cases as c17
import cp7_p19_native_load_cases as load
import cp7_p19_report_v2_cases as rv2

auth,b=c17.auth,c17.b
IDS=('OW12A_CAPTURE_SAME_FIGURES_AS_FINANCE_REPORT',
     'OW12A_CAPTURE_REFUSES_BOOK_CHANGE_DURING_SCAN',
     'OW12A_CAPTURE_ACCESS_AND_PRIVACY',
     'OW12A_REPORT_V2_FINANCE_THROUGH_CAPTURE',
     'OW12A_REPORT_V2_DEFERRED_UNCHANGED',
     'OW12A_RUNNER_STEPS_CAPTURE_AS_ITS_ACTOR',
     'OW12A_REPORT_V2_PERIOD_COMPARISON')
CHUNK=10000
FAMILIES=('journal','line','book','cash')


def operator():
    return auth.base.OPERATOR_AUTH


@contextmanager
def as_capture(cur,subject=None):
    """The actor's Auth claims under the capture owner role, as inside a staged job."""
    b.api.admin(cur)
    cur.execute("select set_config('request.jwt.claim.sub','',true)")
    cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=subject or operator(),role='authenticated')),))
    cur.execute('set local role cp7_capture')
    try:yield
    finally:
        if cur.connection.info.transaction_status!=TransactionStatus.INERROR:
            cur.execute('reset role');b.api.admin(cur)


def call(cur,sql,args=(),subject=None):
    with as_capture(cur,subject):return cur.execute(sql,args,prepare=False).fetchone()[0]


def query(today):
    return dict(from_date=str(today-timedelta(days=30)),through_date=str(today),group_mode='AS_SOLD')


def start(cur,q,kind='STAGED_ANALYSIS',owner=None,subject=None):
    return call(cur,'select cp7_finance_capture.start(%s,%s,%s::jsonb,clock_timestamp())',(kind,owner or uuid.uuid4(),json.dumps(q)),subject)


def step(cur,cid,subject=None):
    return call(cur,'select cp7_finance_capture.step(%s)',(cid,),subject)


def run(cur,cid,subject=None,limit=400):
    trail=[]
    for _ in range(limit):
        s=step(cur,cid,subject);trail.append((s['state'],s['units_done'],s['units_total']))
        if s['state']!='RUNNING':return s,trail
        assert len(trail)<2 or trail[-1][1]>trail[-2][1],trail[-2:]  # every step stores one unit
    raise AssertionError('OW12A_CAPTURE_DID_NOT_FINISH')


def given(cur,today,amount='1500.00'):
    """A real finance posting through the retained kasbon writer (journal, lines, daily balances)."""
    f=c17.s.review.fixture(cur,today);c=f['contractor'];day=c17.accrued_day(cur,c);bank=c17.s.cash(cur)
    kday=max(c17.funding.open_day(cur),day-timedelta(days=1))
    k=c17.kasbon_give(cur,c,bank,amount,kday)['advance'];b.api.admin(cur)
    return dict(contractor=c,bank=bank,day=kday,kasbon=k)


def independent_signature(cur,as_of):
    """The sealed signature recomputed here: same rows, keys, facts, chunk boundaries and join.

    book_chunk renders rows with TimeZone 'UTC' (its own setting), so the recompute does too: a fixture that left the session
    on another zone (Native7 2cd58e47, after the kasbon fixture) would render timestamptz columns differently."""
    b.api.admin(cur)
    zone=cur.execute('show TimeZone').fetchone()[0]
    cur.execute("select set_config('TimeZone','UTC',true)")
    try:return _signature(cur,as_of)
    finally:
        if cur.connection.info.transaction_status!=TransactionStatus.INERROR:cur.execute("select set_config('TimeZone',%s,true)",(zone,))


def _signature(cur,as_of):
    rows={
     'journal':cur.execute("select 'journal:'||j.id||':'||encode(sha256(convert_to(to_jsonb(j)::text,'UTF8')),'hex')from erp.journal_entries j where j.transaction_date<=%s order by j.id",(as_of,)).fetchall(),
     'line':cur.execute("select 'line:'||l.id||':'||encode(sha256(convert_to(to_jsonb(l)::text,'UTF8')),'hex')from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.transaction_date<=%s order by l.id",(as_of,)).fetchall(),
     'book':cur.execute("select 'book:'||b.account_id||':'||b.balance_date||':'||encode(sha256(convert_to(to_jsonb(b)::text,'UTF8')),'hex')from erp.account_daily_balances b where b.balance_date<=%s order by b.account_id,b.balance_date",(as_of,)).fetchall(),
     'cash':cur.execute("select 'cash:'||a.id||':'||encode(sha256(convert_to(to_jsonb(a)::text,'UTF8')),'hex')from erp.cash_accounts a order by a.id").fetchall()}
    parts,unit=[],1
    for fam in FAMILIES:
        lines=[r[0]for r in rows[fam]];k=-(-len(lines)//CHUNK)
        for i in range(k):
            chunk=lines[i*CHUNK:(i+1)*CHUNK]if i<k-1 else lines[i*CHUNK:]
            parts.append(f'{fam}:{unit}:{len(chunk)}:'+hashlib.sha256('\n'.join(chunk).encode()).hexdigest());unit+=1
    return hashlib.sha256('\n'.join(parts).encode()).hexdigest(),{fam:len(rows[fam])for fam in FAMILIES}


def metrics(cur,source):
    b.api.admin(cur)
    v=cur.execute("""select cp7_analysis_native.finance_apply(jsonb_build_object('metrics','[]'::jsonb,'financial_readiness',null,'quality','{}'::jsonb,
      'snapshot',jsonb_build_object('fact_count',0),'dependencies','[]'::jsonb,'generation_warnings','[]'::jsonb),jsonb_build_object('financial_source',%s::jsonb))""",
      (json.dumps(source),)).fetchone()[0]
    return {m['metric_id']:m['value']for m in v['metrics']},v['financial_readiness']


def official(cur,dates):
    auth.actor(cur)
    r=cur.execute('select public.erp_cp7_get_finance_report_v1(%s)',(json.dumps(dates),)).fetchone()[0]
    b.api.admin(cur);return r


def publish_finance(cur,r,subject=None):
    """A finance report v2 driven to DONE through its public step (ACTUALS waits on the capture; rv2.drive expects a unit per step)."""
    key=uuid.uuid4();last=rv2.publish(cur,rv2.payload(r,finance='INCLUDED'),key,subject)
    for _ in range(800):
        if last['state']!='RUNNING':break
        last=rv2.step(cur,key,subject)
    assert last['state']=='DONE',last
    return key,last['publication_id']


def compare(cur,before,after,subject=None):
    auth.actor(cur,subject)
    try:return cur.execute('select public.erp_cp7_compare_reports_v2(%s,%s)',(before,after)).fetchone()[0]
    finally:
        # A refused pair aborts the transaction; the refusal helper rolls back and restores the role itself (Native7 f45577cd).
        if cur.connection.info.transaction_status!=TransactionStatus.INERROR:b.api.admin(cur)


def cases(cur,today):
    def same_figures():
        g=given(cur,today);q=query(today)
        cid=start(cur,q);done,trail=run(cur,cid)
        assert done['state']=='READY'and done['failure_code']is None,done
        r=call(cur,'select cp7_finance_capture.result(%s)',(cid,))
        assert r['contract_version']=='cp7.native-analysis-finance.v2'and set(r)=={'contract_version','dates','book_signature','source_hash','report','capture'},r.keys()
        # The book is re-signed independently right after the capture (as the runner case does): Native7 8438a4a7 re-signed
        # it only after the official and direct reads below and differed, so whether those reads touch the book is recorded.
        signature,counts=independent_signature(cur,r['dates']['as_of'])
        plan_rows={fam:r['capture']['plan'][fam]['rows']for fam in FAMILIES}
        assert r['book_signature']==signature,(r['book_signature'],signature,plan_rows,counts)
        assert plan_rows==counts,(r['capture']['plan'],counts)
        native=official(cur,r['dates'])
        for part in('performance','financial_position','basis','data_confidence'):
            assert r['report']['snapshot'][part]==native['snapshot'][part],part
        # The direct analysis' own source on the same state (one statement) gives the same metric values.
        b.api.admin(cur)
        direct=call(cur,'select cp7_analysis_native.financial_source(%s::jsonb,%s::timestamptz)',(json.dumps(q),r['report']['captured_at']))
        mine,ready=metrics(cur,r);theirs,ready2=metrics(cur,direct)
        # Each fact names its own source in refs: the capture's sealed hash differs by design from the one-statement
        # scan hash (Native7 f45577cd), so figures are compared without refs and each side must cite its own source.
        bare=lambda m:{k:{f:v[f]for f in v if f!='refs'}for k,v in m.items()}
        assert bare(mine)==bare(theirs)and ready==ready2,({k:(bare(mine)[k],bare(theirs)[k])for k in mine if bare(mine).get(k)!=bare(theirs).get(k)},ready,ready2)
        assert all(v['refs']==mine[next(iter(mine))]['refs']and r['source_hash']in json.dumps(v['refs'])for v in mine.values())
        assert all(direct['source_hash']in json.dumps(v['refs'])for v in theirs.values())
        after_reads,counts_after=independent_signature(cur,r['dates']['as_of'])
        b.api.admin(cur)
        fp=cur.execute('select cp7_analysis_native.financial_fingerprint(%s::jsonb,%s)',(json.dumps(r['report']),r['book_signature'])).fetchone()[0]
        assert fp==r['source_hash'],(fp,r['source_hash'])
        assert done['units_total']==2+sum(r['capture']['plan'][fam]['chunks']for fam in FAMILIES)and len(trail)==done['units_total']
        return dict(status='PASS',units=done['units_total'],rows=counts,readiness=ready,report_read_at=r['capture']['report_read_at'],
            same_as_owner_report=True,same_metrics_as_direct_analysis_source=len(mine),independent_book_signature=True,kasbon=g['kasbon']['number'],
            book_unchanged_by_report_reads=after_reads==signature,rows_after_report_reads=counts_after)

    def refuses_change():
        q=query(today);given(cur,today,'700.00')
        cid=start(cur,q);first=step(cur,cid)
        assert first['state']=='RUNNING'and first['units_done']==1 and first['units_total']>=2,first
        later=given(cur,today,'900.00')  # posted after the report was read, before any chunk is scanned
        done,trail=run(cur,cid)
        assert done['state']=='FAILED'and done['failure_code']=='CP7_FINANCE_CAPTURE_SOURCE_CHANGED',done
        refused=auth.refused(cur,lambda:call(cur,'select cp7_finance_capture.result(%s)',(cid,)),'CP7_FINANCE_CAPTURE_NOT_READY')
        again=start(cur,q);fresh,_=run(cur,again)
        assert fresh['state']=='READY',fresh
        return dict(status='PASS',failed_with=done['failure_code'],failed_at_unit=done['units_done'],result_refused=refused,
            later_kasbon=later['kasbon']['number'],new_capture_ready=True)

    def access_privacy():
        q=query(today)
        staff,_=auth.custom_actor(cur)
        denied=auth.refused(cur,lambda:start(cur,q,subject=staff),'CP7_FINANCE_CAPTURE_ACCESS')
        admin,admin_role=finance_cases.admin_actor(cur,analysis)
        cid=start(cur,q,subject=admin)
        other=auth.refused(cur,lambda:call(cur,'select cp7_finance_capture.status(%s)',(cid,),staff),'CP7_FINANCE_CAPTURE_UNAVAILABLE')
        b.api.admin(cur)
        owner=cur.execute('select owner_id from cp7_finance_capture.captures where id=%s',(cid,)).fetchone()[0]
        changed=auth.refused(cur,lambda:start(cur,dict(q,from_date=str(today-timedelta(days=10))),owner=owner,subject=admin),'CP7_FINANCE_CAPTURE_CHANGED')
        first=step(cur,cid,admin);assert first['state']=='RUNNING'and first['units_done']==1,first
        # The actor loses owner finance in the middle: the capture fails, nothing is sealed.
        b.api.admin(cur)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'",(admin_role,))
        try:after=step(cur,cid,admin)
        except psycopg.Error as error:
            b.api.admin(cur);after=dict(raised=str(error).splitlines()[0])
        b.api.admin(cur)
        state,code,sealed=cur.execute('select state,failure_code,source_hash from cp7_finance_capture.captures where id=%s',(cid,)).fetchone()
        assert state=='FAILED'and code=='CP7_FINANCE_CAPTURE_ACCESS_CHANGED'and sealed is None,(state,code,after)
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.reports.view')",(admin_role,))
        refused_after=auth.refused(cur,lambda:call(cur,'select cp7_finance_capture.result(%s)',(cid,),admin),'CP7_FINANCE_CAPTURE_NOT_READY')
        exposed={}
        for r in('anon','authenticated','service_role'):
            exposed[r]=cur.execute("select has_schema_privilege(%s,'cp7_finance_capture','USAGE')or has_function_privilege(%s,'cp7_finance_capture.step(uuid)','EXECUTE')",(r,r)).fetchone()[0]
        assert not any(exposed.values()),exposed
        return dict(status='PASS',ops_actor=denied,other_actor=other,changed_query=changed,permission_lost_mid_capture=code,
            failed_capture_result=refused_after,public_roles_exposed=exposed)

    def report_through_capture():
        load.real_workload(cur,today)
        r=rv2.staged_run(cur,today)
        key=uuid.uuid4();first=rv2.publish(cur,rv2.payload(r,finance='INCLUDED'),key)
        assert first['state']=='RUNNING'and first['stage']=='ACTUALS'and first['finance_capture']is None,first
        last,waits,progress=first,0,[]
        while last['state']=='RUNNING':
            nxt=rv2.step(cur,key)
            if nxt['stage']=='ACTUALS':
                waits+=1;fc=nxt['finance_capture'];progress.append((fc['state'],fc['units_done'],fc['units_total']))
                assert nxt['units_done']==0 and fc['state']in('RUNNING','READY'),nxt
            assert waits<500,'OW12A_REPORT_DRIVER_BOUND'
            last=nxt
        assert last['state']=='DONE',last
        assert progress and progress[0][1]==1 and all(b_[1]>a_[1]for a_,b_ in zip(progress,progress[1:])),progress
        d,_=rv2.document(cur,last['publication_id'])
        a=rv2.actuals(cur,key);fin=a['finance']
        b.api.admin(cur)
        cap=cur.execute("select id,source_hash,report_read_at from cp7_finance_capture.captures where owner_kind='STAGED_REPORT'and owner_id=(select id from cp7_analysis_stage.report_jobs where request_id=%s)",(key,)).fetchone()
        assert fin['contract_version']=='cp7.native-analysis-finance.v2'and fin['source_hash']==cap[1]==d['financial_source_hash'],(fin['source_hash'],cap,d['financial_source_hash'])
        native=official(cur,fin['dates'])
        for part in('performance','financial_position','basis'):
            assert fin['report']['snapshot'][part]==native['snapshot'][part],part
        assert fin['dates']['as_of']==d['report_date'],(fin['dates'],d['report_date'])
        line='Angka keuangan dan HPP dari laporan Native ERP untuk tanggal laporan '+d['report_date']+', dibaca '+rv2.wib(cap[2])
        assert line in d['summary'],line
        position,performance=native['snapshot']['financial_position'],native['snapshot']['performance']
        for label,value in(('Saldo kas tercatat',position['cash']),('HPP penjualan tercatat',performance['cogs_gl'])):
            assert label+': '+value+' IDR;'in d['summary'],(label,value)
        return dict(status='PASS',actuals_waited_steps=waits,capture_units=progress[-1][2],publication=d['id'],
            finance_hash_from_capture=True,figures_equal_owner_report=True,summary_names_finance_read_time=True)

    def deferred_unchanged():
        load.real_workload(cur,today)
        r=rv2.staged_run(cur,today)
        key=uuid.uuid4();first=rv2.publish(cur,rv2.payload(r),key)
        assert first['finance_capture']is None,first
        last,seen=first,[first['units_done']]
        while last['state']=='RUNNING':
            nxt=rv2.step(cur,key);assert nxt['units_done']==last['units_done']+1 and nxt['finance_capture']is None,(last,nxt)
            last=nxt;seen.append(nxt['units_done'])
        assert last['state']=='DONE'and seen==list(range(0,r['pages']+4)),(last,seen)
        b.api.admin(cur)
        n=cur.execute("select count(*)from cp7_finance_capture.captures where owner_id=(select id from cp7_analysis_stage.report_jobs where request_id=%s)",(key,)).fetchone()[0]
        d,_=rv2.document(cur,last['publication_id'])
        assert n==0 and d['finance']=='DEFERRED'and d['financial_source_hash']is None and 'Keuangan dan HPP tidak dimasukkan'in d['summary'],(n,d['finance'])
        return dict(status='PASS',units=seen[-1],captures=n,finance='DEFERRED')

    def runner():
        q=query(today);cid=start(cur,q);b.api.admin(cur)
        outcomes=[]
        for _ in range(400):
            cur.execute("set local statement_timeout='8s'")
            o=cur.execute('select cp7_background.run_next()').fetchone()[0];b.api.admin(cur)
            if o.get('family')=='FINANCE':outcomes.append(o['outcome'])
            state=cur.execute('select state from cp7_finance_capture.captures where id=%s',(cid,)).fetchone()[0]
            if state!='RUNNING':break
        assert state=='READY'and outcomes and outcomes[-1]=='JOB_DONE'and set(outcomes[:-1])<={'UNIT_STORED'},(state,outcomes)
        r=call(cur,'select cp7_finance_capture.result(%s)',(cid,))
        signature,_=independent_signature(cur,r['dates']['as_of'])
        assert r['book_signature']==signature
        return dict(status='PASS',runner_units=len(outcomes),result_contract=r['contract_version'],independent_book_signature=True)

    def period_comparison():
        load.real_workload(cur,today)
        base=rv2.staged.query(today);f0,t0=date.fromisoformat(base['from_date']),date.fromisoformat(base['through_date'])
        prev=dict(base,from_date=str(f0-timedelta(days=(t0-f0).days+1)),through_date=str(f0-timedelta(days=1)))
        earlier,now=rv2.staged_run(cur,today,q=prev),rv2.staged_run(cur,today)
        k1,p1=publish_finance(cur,earlier);k2,p2=publish_finance(cur,now)
        _,ops,_=rv2.published(cur,now)
        c=compare(cur,p1,p2)
        assert c['contract_version']=='cp7.report-comparison.v2'and c['before']['id']==p1 and c['after']['id']==p2 and 'summary'not in c['before'],c.keys()
        m1,_=metrics(cur,rv2.actuals(cur,k1)['finance']);m2,_=metrics(cur,rv2.actuals(cur,k2)['finance'])
        assert {row['metric_id']for row in c['rows']}==set(m1)|set(m2)
        known=0
        for row in c['rows']:
            x,y=m1.get(row['metric_id']),m2.get(row['metric_id']);d=row['difference']
            assert row['before']['value']==x and row['after']['value']==y,row
            if x['state']in('KNOWN','ASSUMED')and y['state']in('KNOWN','ASSUMED')and x.get('value')is not None and y.get('value')is not None:
                assert d['state']in('KNOWN','ASSUMED')and Decimal(d['value'])==Decimal(y['value'])-Decimal(x['value']),(row,x,y);known+=1
            else:
                assert d=={'state':'UNKNOWN','unit':'IDR','reason':'ONE_OR_BOTH_VALUES_UNKNOWN'},row
        assert known>0,'OW12A_NO_KNOWN_METRIC_COMPARED'
        bp=[r['before']['period_start']for r in c['rows']if r['metric_id'].startswith('NATIVE_FINANCE:performance:')]
        assert bp and set(bp)=={prev['from_date']},bp
        half=compare(cur,p1,ops['publication_id'])
        assert half['rows']and all(r['difference']=={'state':'UNKNOWN','unit':'IDR','reason':'FINANCE_NOT_IN_BOTH_REPORTS'}and r['after']is None for r in half['rows']),half['rows'][:2]
        same=auth.refused(cur,lambda:compare(cur,p2,p2),'CP7_REPORT_COMPARE_PAIR')
        staff,_=auth.custom_actor(cur)
        other=auth.refused(cur,lambda:compare(cur,p1,p2,staff),'CP7_REPORT_UNAVAILABLE')
        return dict(status='PASS',metrics_compared=len(c['rows']),known_differences=known,previous_period=[prev['from_date'],prev['through_date']],
            finance_vs_operations_only='FINANCE_NOT_IN_BOTH_REPORTS',same_report=same,other_actor=other)

    operations=(same_figures,refuses_change,access_privacy,report_through_capture,deferred_unchanged,runner,period_comparison)
    assert len(operations)==len(IDS)
    return list(zip(IDS,operations))
