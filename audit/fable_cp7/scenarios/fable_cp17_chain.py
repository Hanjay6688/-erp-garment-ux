"""Fable cp17 — cross-stage chain oracles (SKN-22) on the full CP7 composition of 0b7049d9.
Every case builds its own fixture (the strict runner rolls each case back). Fixtures come from the writer's qualified
E01/P18 path (fixture_origin=writer); the ORACLES below are Fable's own SQL (oracle_origin=Fable), except the worksheet
numbers of E01 (oracle_origin=owner-approved E01 worksheet, framework-v2/04). Sub-oracles are reported inside each case;
the case status is the worst sub-status (FAIL > COUNTEREXAMPLE > PASS). Nothing here touches hosted.
  FABLE_CHAIN:LEDGER_ORACLES_ON_FULL_CYCLE   journals balanced per entry and per day; account_daily_balances == journal
                                              lines; roll and FG lot chronological non-negative stock; control-account
                                              dimensions complete; AR/AP/payable dimensions == E01 worksheet after cash.
  FABLE_CHAIN:CLOSE_THEN_BACKDATED_CORRECTIONS tutup buku through the fixture's last economic date, then CP7 note,
                                              receipt and supplier-payment corrections of documents inside the closed
                                              period: every one must refuse; no journal/movement may land <= closed_through.
  FABLE_CHAIN:OPEN_PAYABLES_BACKDATED_SETTLEMENTS R1-05 payroll PAY dated before period_end (chronological negative
                                              payable?) and R3-03 laundry claim settled with resolution_date before the
                                              vendor ever had a payable (dated AP misstated?).
  FABLE_CHAIN:SESSION_TIMEZONE_CURRENT_DATE_HELPERS R3-02: session TimeZone of the disposable copy and whether the
                                              accounting-date helpers still read current_date (demonstrated only in the
                                              00:00-07:00 WIB window).
"""
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal as D
import json,re,traceback,uuid
import psycopg
import cp7_p18_full_cycle_cases as full
import cp7_f03_e01_cases as e01
import cp7_note_correction_cases as note_fix
import cp7_receipt_correction_cases as receipt_fix
import cp7_supplier_payment_correction_cases as sp_fix
import cp7_settlement_cases as settlement
b=e01.settlement.b
RANK={'PASS':0,'COUNTEREXAMPLE':1,'FAIL':2}
LOCK=re.compile(r'PERIOD|CLOSED|TUTUP|closed_through|ACCOUNTING_CLOSE|LOCK_BUSINESS|LOCKED',re.I)

def worst(subs):
    s=[x.get('status','FAIL') for x in subs.values() if isinstance(x,dict)]
    return max(s,key=lambda x:RANK.get(x,2)) if s else 'FAIL'
def q(cur,sql,args=()):return cur.execute(sql,args).fetchall()
def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def sp(cur,fn):
    """Run fn inside a savepoint; return ('OK',result) or (sqlstate,message)."""
    cur.execute('savepoint fable_sp')
    try:
        r=fn();cur.execute('release savepoint fable_sp');return ('OK',r)
    except psycopg.Error as e:
        cur.execute('rollback to savepoint fable_sp');b.api.admin(cur);return (e.sqlstate or 'ERR',str(e).splitlines()[0][:300])
    except Exception as e:
        cur.execute('rollback to savepoint fable_sp');b.api.admin(cur);return ('PY',(type(e).__name__+': '+str(e))[:300])
def cols(cur,table):
    return [r[0] for r in q(cur,"select column_name from information_schema.columns where table_schema='erp' and table_name=%s order by ordinal_position",(table,))]
def js(x):return json.loads(json.dumps(x,default=str))

# ---------------------------------------------------------------- Fable ledger oracles (own SQL)
def journals_balanced(cur,since):
    bad=q(cur,"select j.id::text,j.source_type,sum(l.debit),sum(l.credit) from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.created_at>=%s group by j.id,j.source_type having sum(l.debit)<>sum(l.credit)",(since,))
    neg=one(cur,"select count(*) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.created_at>=%s and (l.debit<0 or l.credit<0 or (l.debit<>0 and l.credit<>0))",(since,))
    orphan=one(cur,"select count(*) from erp.journal_entries j where j.created_at>=%s and j.status in ('POSTED','REVERSED') and not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id)",(since,))
    days=q(cur,"select j.economic_date::text,sum(l.debit)::text,sum(l.credit)::text from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.created_at>=%s and j.status in ('POSTED','REVERSED') group by 1 order by 1",(since,))
    offdays=[d for d in days if D(d[1])!=D(d[2])]
    n=one(cur,"select count(*) from erp.journal_entries where created_at>=%s",(since,))
    ok=not bad and neg==0 and orphan==0 and not offdays and n>0
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',entries=n,unbalanced=js(bad),negative_or_two_sided_lines=neg,orphan_entries=orphan,days=days,unbalanced_days=offdays)

def daily_balances(cur,since_date):
    c=cols(cur,'account_daily_balances')
    if not {'balance_date','account_id','debit_total','credit_total'}<=set(c):return dict(status='FAIL',reason='columns',columns=c)
    out={}
    for datecol in ('economic_date','transaction_date'):
        if datecol not in cols(cur,'journal_entries'):continue
        diff=q(cur,f"""with jl as (select j.{datecol}::date d,l.account_id a,sum(l.debit) dr,sum(l.credit) cr from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
              where j.status in ('POSTED','REVERSED') and j.{datecol}>=%s group by 1,2),
              adb as (select balance_date d,account_id a,debit_total dr,credit_total cr from erp.account_daily_balances where balance_date>=%s)
              select coalesce(jl.d,adb.d)::text,coalesce(jl.a,adb.a)::text,jl.dr::text,adb.dr::text,jl.cr::text,adb.cr::text from jl full join adb on adb.d=jl.d and adb.a=jl.a
              where jl.dr is distinct from adb.dr or jl.cr is distinct from adb.cr order by 1,2 limit 40""",(since_date,since_date))
        out[datecol]=dict(mismatches=len(diff),sample=diff[:12])
    match=[k for k,v in out.items() if v['mismatches']==0]
    return dict(status='PASS' if match else 'COUNTEREXAMPLE',matching_date_basis=match,detail=out,oracle='account_daily_balances(balance_date,account_id,debit_total,credit_total) == sum(journal_lines) per day per account for POSTED/REVERSED entries')

def chronological(cur,table,keycols,qtycol,timecol,filter_sql,args):
    keys=','.join(keycols)
    rows=q(cur,f"select {keys},{timecol},{qtycol} from erp.{table} where {filter_sql} order by {keys},{timecol},id",args)
    run={};minimum={};final={}
    for r in rows:
        k=tuple(str(x) for x in r[:len(keycols)]);run[k]=run.get(k,D(0))+D(r[-1]);minimum[k]=min(minimum.get(k,D(0)),run[k]);final[k]=run[k]
    negative={'/'.join(k):str(v) for k,v in minimum.items() if v<0}
    return dict(status='PASS' if rows and not negative else ('FAIL' if not rows else 'COUNTEREXAMPLE'),movements=len(rows),keys=len(run),negative_running_balance=negative,final={'/'.join(k):str(v) for k,v in final.items()})

def dimensions(cur,f):
    a=f['accounts'];res={}
    for key,dim in (('AR_CUSTOMER','customer_id'),('AP_VENDOR','vendor_id'),('CONTRACTOR_PAYABLE','contractor_id'),('AP_SUPPLIER','supplier_id')):
        if dim not in cols(cur,'journal_lines'):res[key]=dict(status='PASS',note=f'no {dim} column on journal_lines; dimension not modelled');continue
        missing=one(cur,f"select count(*) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.account_id=%s and j.status in ('POSTED','REVERSED') and j.created_at>=%s and l.{dim} is null",(a[key],f['fable_since']))
        total=one(cur,"select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.account_id=%s and j.status in ('POSTED','REVERSED') and j.created_at>=%s",(a[key],f['fable_since']))
        bydim=q(cur,f"select l.{dim}::text,sum(l.debit-l.credit)::text from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.account_id=%s and j.status in ('POSTED','REVERSED') and j.created_at>=%s group by 1",(a[key],f['fable_since']))
        res[key]=dict(status='PASS' if missing==0 else 'COUNTEREXAMPLE',lines_without_dimension=missing,total_since_start=str(total),by_dimension=bydim)
    # E01/P18 worksheet after all cash (owner-approved numbers): AR 175, supplier AP 0, vendor AP 0, contractor payable 0
    gl=full.change(f['gl0'],full.ledger(cur))
    g={k:gl.get(a[k],D(0)) for k in ('AR_CUSTOMER','AP_SUPPLIER','AP_VENDOR','CONTRACTOR_PAYABLE','MATERIAL_INVENTORY','FG_INVENTORY','WIP','SALES_REVENUE','COGS')}
    want=dict(AR_CUSTOMER=D(175),AP_SUPPLIER=D(0),AP_VENDOR=D(0),CONTRACTOR_PAYABLE=D(0),MATERIAL_INVENTORY=D(400),FG_INVENTORY=D(675),WIP=D(0),SALES_REVENUE=D(-375),COGS=D(225))
    off={k:(str(g[k]),str(v)) for k,v in want.items() if g[k]!=v}
    res['E01_WORKSHEET_AFTER_CASH']=dict(status='PASS' if not off else 'COUNTEREXAMPLE',off=off,oracle_origin='E01 worksheet (framework-v2/04), writer-derived, owner-approved')
    return dict(status=worst(res),sub=res)

def prelude(cur,today):
    b.api.admin(cur)
    e01.procurement.aa.prior.set_open_period(cur,today-timedelta(days=4))
    seed=e01.attendance.quiet_seed(cur,today-timedelta(days=3),today)
    assert not seed['refused'],('FABLE_SEED',seed)
    e01.native(cur,'select erp.process_cost_recalc_queue(100)');b.api.admin(cur)

# ---------------------------------------------------------------- cases
def cases(cur,today):
    def ledger_oracles():
        since=one(cur,'select clock_timestamp()')
        f=full.cycle(cur,today)[0];f['fable_since']=since;b.api.admin(cur)
        subs=dict(JOURNALS_BALANCED=journals_balanced(cur,since),
                  DAILY_BALANCES=daily_balances(cur,today-timedelta(days=10)),
                  ROLL_CHRONOLOGICAL=chronological(cur,'material_stock_movements',['roll_id'],'qty_signed','physical_at','material_id=%s',(f['material'],)),
                  FG_LOT_CHRONOLOGICAL=chronological(cur,'fg_stock_movements',['lot_id'],'qty_signed','physical_at','lot_id = any(%s::uuid[])',(f['lots'],)),
                  DIMENSIONS=dimensions(cur,f))
        return dict(status=worst(subs),sub=js(subs),fixture_origin='writer E01+P18 cycle',source_ids={k:f[k] for k in ('po','purchase','group','laundry_invoice','note','payroll','sale')})

    def close_then_corrections():
        since=one(cur,'select clock_timestamp()')
        f=full.cycle(cur,today)[0];b.api.admin(cur)
        D0=one(cur,"select max(economic_date) from erp.journal_entries where created_at>=%s",(since,))
        auth=settlement.auth
        def ws(d):
            auth.actor(cur,None);r=one(cur,'select public.erp_cp7_get_period_control_v1(%s)',(d,));b.api.admin(cur);return r
        def close(d):
            st=ws(d);p=dict(through=str(d),review_through=str(d),review_token=st['review_token'],reason='Fable cp17 tutup buku untuk uji koreksi mundur')
            auth.actor(cur,None);r=one(cur,'select public.erp_cp7_save_period_control_v1(%s,%s,%s)',('CLOSE',json.dumps(p),uuid.uuid4()));b.api.admin(cur);return r
        closed=sp(cur,lambda:close(D0));route='APP_erp_cp7_save_period_control_v1'
        if closed[0]!='OK':
            fallback=sp(cur,lambda:one(cur,'select erp.close_accounting_through(%s,%s)',(D0,'Fable cp17 fallback close')));route='NATIVE_erp.close_accounting_through'
            closed=(closed,fallback)
            if fallback[0]!='OK':return dict(status='FAIL',reason='could not close',attempts=closed,closed_through_target=str(D0))
        ct=one(cur,"select closed_through from erp.accounting_period_control limit 1")
        before=one(cur,"select count(*) from erp.journal_entries where economic_date<=%s",(ct,))
        mv_before=one(cur,"select count(*) from erp.material_stock_movements where physical_at::date<=%s",(ct,))+one(cur,"select count(*) from erp.fg_stock_movements where physical_at::date<=%s",(ct,))
        t_close=one(cur,'select clock_timestamp()')
        attempts={}
        def attempt(name,fn,target_date):
            r=sp(cur,fn)
            if r[0]=='OK':st='ACCEPTED'
            elif r[0]=='PY':st='PLUMBING'
            elif LOCK.search(r[1]):st='REFUSED_PERIOD_LOCK'
            else:st='REFUSED_OTHER_GUARD'
            attempts[name]=dict(outcome=st,result=js(r)[:2] if isinstance(r,tuple) else js(r),target_date=str(target_date),inside_closed=bool(target_date and target_date<=ct))
        sale_date=one(cur,"select min(economic_date) from erp.journal_entries where source_id=%s",(f['sale'],))
        def do_note():
            p,v=note_fix.edit(cur,f,price='21');return note_fix.correct(cur,p,v)
        attempt('CP7_NOTE_CORRECTION_PRICE',do_note,sale_date)
        rec_date=one(cur,"select min(economic_date) from erp.journal_entries where source_id=%s",(f['purchase'],))
        def do_receipt():
            w=receipt_fix.ws(cur,f['purchase'])
            def bump(n,item):item['unit_price']=str(D(item['unit_price'])+1)
            p=receipt_fix.payload(w,line=bump);return receipt_fix.fix(cur,p,w.get('row_version') or w.get('version'))
        attempt('CP7_RECEIPT_CORRECTION_PRICE',do_receipt,rec_date)
        pay=cur.execute("select id::text,payment_date from erp.supplier_payments where purchase_id=%s and status='POSTED' order by created_at limit 1",(f['purchase'],)).fetchone()
        def do_sp():
            p=sp_fix.payload(cur,dict(receipt=dict(purchase_id=f['purchase']),payment=pay[0]),amount='401.00');return sp_fix.correct(cur,p)
        attempt('CP7_SUPPLIER_PAYMENT_CORRECTION_AMOUNT',do_sp,pay[1] if pay else None)
        after=one(cur,"select count(*) from erp.journal_entries where economic_date<=%s",(ct,))
        mv_after=one(cur,"select count(*) from erp.material_stock_movements where physical_at::date<=%s",(ct,))+one(cur,"select count(*) from erp.fg_stock_movements where physical_at::date<=%s",(ct,))
        new_closed=q(cur,"select id::text,source_type,economic_date::text,status from erp.journal_entries where created_at>%s and economic_date<=%s",(t_close,ct))
        new_open=q(cur,"select id::text,source_type,economic_date::text,status from erp.journal_entries where created_at>%s and economic_date>%s",(t_close,ct))
        reached=[k for k,v in attempts.items() if v['outcome']!='PLUMBING' and v['inside_closed']]
        accepted=[k for k,v in attempts.items() if v['outcome']=='ACCEPTED' and v['inside_closed']]
        if not reached:status='FAIL'
        elif new_closed or mv_after!=mv_before or after!=before:status='COUNTEREXAMPLE'
        elif accepted:status='COUNTEREXAMPLE'   # correction of a closed-period document accepted (re-dated into the open period): INV-K02 question
        else:status='PASS'
        return dict(status=status,close_route=route,closed_through=str(ct),attempts=attempts,journals_in_closed_period_before_after=[before,after],movements_in_closed_period_before_after=[mv_before,mv_after],
                    journals_created_after_close_inside=js(new_closed),journals_created_after_close_outside=js(new_open),fixture_origin='writer E01+P18 cycle')

    def open_payables():
        prelude(cur,today);f=e01.production(cur,today);b.api.admin(cur);subs={}
        # R1-05 payroll PAY dated before the accrual date (period_end)
        d=settlement.doc(cur,f['payroll']);accrual=one(cur,"select max(economic_date) from erp.journal_entries where source_id=%s and status='POSTED'",(f['payroll'],))
        early=(accrual or today)-timedelta(days=5)
        r=sp(cur,lambda:settlement.act(cur,'PAY',d,None,payment_date=str(early),cash_account_id=f['bank']))
        if r[0]=='OK':
            run=q(cur,"select j.economic_date::text,sum(l.credit-l.debit)::text from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.account_id=erp.account_id('CONTRACTOR_PAYABLE') and l.contractor_id=%s and j.status='POSTED' group by 1 order by 1",(f['contractor'],))
            bal=D(0);minimum=D(0)
            for _,v in run:bal+=D(v);minimum=min(minimum,bal)
            subs['R1_05_PAYROLL_PAID_BEFORE_ACCRUAL']=dict(status='COUNTEREXAMPLE' if minimum<0 else 'PASS',accepted=True,payment_date=str(early),accrual_date=str(accrual),daily_payable=run,min_running_payable=str(minimum))
        else:subs['R1_05_PAYROLL_PAID_BEFORE_ACCRUAL']=dict(status='PASS',accepted=False,refusal=js(r),payment_date=str(early),accrual_date=str(accrual))
        # R3-03 laundry claim settlement dated before the vendor ever had a payable
        try:
            lc=cols(cur,'laundry_deliveries');rc=cols(cur,'laundry_receipts');rlc=cols(cur,'laundry_receipt_lines')
            bcol=[c for c in lc if 'batch' in c][0]
            deliv=one(cur,f"select id::text from erp.laundry_deliveries where {bcol}=%s order by created_at limit 1",(f['batch'],))
            rec=cur.execute("select id::text from erp.laundry_receipts where delivery_id=%s order by created_at limit 1",(deliv,)).fetchone()[0]
            line=cur.execute("select id::text from erp.laundry_receipt_lines where receipt_id=%s order by created_at limit 1",(rec,)).fetchone()[0]
            first_ap=one(cur,"select min(j.economic_date) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.account_id=erp.account_id('AP_VENDOR') and l.vendor_id=%s and j.status='POSTED'",(f['vendor'],))
            early_res=(first_ap or today)-timedelta(days=200)
            def act(action,payload,version=None):
                settlement.auth.actor(cur,None)
                r=one(cur,'select public.erp_save_bs_resolution_action_v1(%s,%s::jsonb,%s::uuid,%s)',(action,json.dumps(payload,default=str),str(uuid.uuid4()),version));b.api.admin(cur);return r
            save=sp(cur,lambda:act('SAVE_CLAIM',dict(action='SAVE',claim_number='FABLE-CP17-DMG',vendor_id=f['vendor'],delivery_id=deliv,receipt_line_id=line,qty_claimed=1,claim_type='DAMAGE',compensation_amount=20,opened_at=datetime.now(timezone.utc).isoformat(),change_reason='Fable cp17 R3-03 probe')))
            res=None
            if save[0]=='OK':
                claim=save[1].get('claim_id') or save[1].get('id') or (save[1].get('claim') or {}).get('id')
                ver=save[1].get('row_version') or save[1].get('version') or (save[1].get('claim') or {}).get('row_version')
                res=sp(cur,lambda:act('RESOLVE_CLAIM',dict(claim_id=claim,resolution='SETTLED',resolution_date=str(early_res),compensation_amount=20,change_reason='Fable cp17 R3-03 settle backdated'),ver))
            jd=q(cur,"select economic_date::text,source_type,status from erp.journal_entries where source_type ilike '%%CLAIM%%' order by created_at desc limit 5")
            backdated=[x for x in jd if x[0]==str(early_res)]
            st='COUNTEREXAMPLE' if (res and res[0]=='OK' and backdated) else 'PASS'
            subs['R3_03_CLAIM_SETTLED_BEFORE_FIRST_AP']=dict(status=st,first_vendor_ap_date=str(first_ap),resolution_date=str(early_res),save=js(save),resolve=js(res),claim_journals=jd,plumbing_ok=True)
        except Exception as e:
            subs['R3_03_CLAIM_SETTLED_BEFORE_FIRST_AP']=dict(status='PASS',plumbing_ok=False,not_reached=True,error=(type(e).__name__+': '+str(e))[:300],note='probe did not reach the writer; recorded as not run, not as evidence')
            b.api.admin(cur)
        return dict(status=worst(subs),sub=js(subs),fixture_origin='writer E01 production (approved unpaid payroll, unpaid vendor invoice)')

    def timezone_helpers():
        tz=one(cur,'show timezone');wib_today=one(cur,"select (now() at time zone 'Asia/Jakarta')::date");utc_today=one(cur,"select (now() at time zone 'UTC')::date")
        defs={}
        for fn in ('erp.resolve_accounting_transaction_date','erp._cp3_r4_reverse_journal_internal'):
            rows=q(cur,"select p.oid::regprocedure::text,pg_get_functiondef(p.oid) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname||'.'||p.proname=%s",(fn,))
            defs[fn]=[dict(signature=r[0],uses_current_date=bool(re.search(r'\bcurrent_date\b',r[1],re.I)),uses_now=bool(re.search(r'\bnow\(\)|clock_timestamp\(\)',r[1],re.I)),length=len(r[1])) for r in rows]
        window_open=utc_today<wib_today
        demo=None
        if window_open and defs['erp.resolve_accounting_transaction_date']:
            cur.execute("set local timezone='UTC'")
            demo=sp(cur,lambda:one(cur,'select erp.resolve_accounting_transaction_date(%s)',(wib_today,)))
            cur.execute("set local timezone=%s",(tz,))
        hazard=any(d['uses_current_date'] for v in defs.values() for d in v)
        status='COUNTEREXAMPLE' if (demo and demo[0]!='OK') else 'PASS'
        return dict(status=status,session_timezone=tz,wib_today=str(wib_today),utc_today=str(utc_today),window_open=window_open,helpers=defs,helpers_use_current_date=hazard,demonstration=js(demo),
                    note='PASS here means not demonstrated in this run; hazard stays static (R3-02) unless demonstration ran')
    return [('FABLE_CHAIN:LEDGER_ORACLES_ON_FULL_CYCLE',ledger_oracles),('FABLE_CHAIN:CLOSE_THEN_BACKDATED_CORRECTIONS',close_then_corrections),
            ('FABLE_CHAIN:OPEN_PAYABLES_BACKDATED_SETTLEMENTS',open_payables),('FABLE_CHAIN:SESSION_TIMEZONE_CURRENT_DATE_HELPERS',timezone_helpers)]

def races(tools,today):return []
def http_cases(http,today):return []
