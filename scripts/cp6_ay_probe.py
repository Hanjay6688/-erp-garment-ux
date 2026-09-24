"""AY T1_FAMILY probe: PO HPP corrections dated from the goods (owner, 24 Sep 2026).

Owner decision (quoted): "Saya pilih Geser tanggal recost. Jangan catat penurunan nilai barang jadi pada 23 Agustus
ketika barang jadinya baru ada 24 Agustus. Alokasikan koreksi ke barang jadi sejak tanggal fisiknya dan ke HPP untuk
bagian yang terjual, dengan tanggal jurnal mengikuti aturan periode terbuka/tertutup yang sudah diputuskan. Pertahankan
pemeriksaan saldo negatif per tanggal. Tolong uji ulang empat kasus INVOICE, saldo harian, laporan menurut tanggal, serta
tutup buku sebelum menyatakan beres."

Label T1_FAMILY: targeted family evidence on the disposable chain AN -> AU -> AV -> AW -> AX (+ AY in phase 'after'),
never release evidence. Fixture: the AA recipe (chain.production) reused unchanged, the one the AW B04 case uses:
estimated receipt of 10 units at 10 on day d (23:30), cutting, sewing, laundry, 5 FG on d+1 and 2 of them sold on d+1;
seed and fixture open items cleared by awp.quiet_seed (attendance OFF, approved payroll, nothing paid). A late supplier
invoice for all 10 units then arrives with the invoice date d. The AA value oracle (chain.production.differences) is
reused unchanged. Per piece HPP = unit price + 7 (laundry), so a change of the price by x changes FG by 3x and COGS by 2x.
Checks per case: the AA oracle at the invoice price; every new PO HPP event is dated on or after the FG day (open
receipt day) or on the recognition day (closed receipt day); FG and COGS in the report of day d are untouched by the
invoice and the report of d+1 moves by exactly 3x and 2x (open receipt day) or not at all (closed receipt day, whether
d+1 is closed too or still open: the decided rule recognizes the whole correction of a closed receipt on the invoice's
recognition day, so no report before it changes); the AW engine shows no negative daily inventory balance and is READY;
the close is accepted afterwards. Phase 'before' (without AY) must show the finding on the open lower-price case.
closed: False (nothing closed), 'goods' (closed through d+1) or 'receipt' (closed through d only, d+1 open; added after
T2 run 8, 35950787577, showed the first AY text dating part of such a correction on d+1).
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import argparse,json,os,subprocess,sys,traceback,uuid
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_aw_probe as awp
import cp6_ax_probe as axp
r1,api,boundary,prior,chain=awp.r1,awp.api,awp.boundary,awp.prior,awp.chain

OUT=AUDITOR/'cp6-proof/ay'
AY_SQL=AUDITOR/'supabase/dev/cp6_ay_t1_family.sql'
LABEL='T1_FAMILY'


def ay_installed(cur):
    return cur.execute("select to_regprocedure('erp.po_hpp_gl_leg_add_v1(jsonb,date,numeric,numeric,numeric)') is not null").fetchone()[0]


def sync_source():
    text=AY_SQL.read_text()
    head=text.index('CREATE OR REPLACE FUNCTION erp.sync_po_hpp_to_gl(')
    start=text.index('AS $function$',head)+len('AS $function$');end=text.index('$function$;',start)
    return text[start:end]


def ay_verified(cur):
    base=axp.ax_verified(cur)
    assert cur.execute("select count(*) from erp.schema_migrations where version='v2.6.20ay'").fetchone()[0]==1,'AY_T1_MARKER'
    src=cur.execute("select prosrc from pg_proc where oid='erp.sync_po_hpp_to_gl(uuid,date)'::regprocedure").fetchone()[0]
    assert 'po_hpp_gl_leg_add_v1' in src,'AY_T1_SYNC_NOT_INSTALLED'
    # The installed body is exactly the committed AY text (a stale AY install, e.g. an older package, is refused).
    assert src==sync_source(),'AY_T1_SYNC_NOT_CURRENT'
    import hashlib
    return dict(base,stage='AV_PLUS_AW_AX_AY_T1',ay_sql_sha256=hashlib.sha256(AY_SQL.read_bytes()).hexdigest())


def install_ay():
    with psycopg.connect(boundary.PG,autocommit=True) as conn,conn.cursor() as cur:cur.execute(AY_SQL.read_text(),prepare=False)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        result=ay_verified(cur);conn.rollback()
    return result


def dec(v):return Decimal(str(v))


def late_invoice(cur,today,price,closed,zone='Asia/Jakarta'):
    assert closed in (False,'goods','receipt'),closed
    prod=chain.production
    d=today-timedelta(days=3);d2=d+timedelta(days=1)
    boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    quiet_items=awp.quiet_seed(cur,d,d2,exclude=[prod.CONTRACTOR])
    ledger_baseline=prod.ledger(cur);report_baseline=prod.reports(cur,today)
    fx=prod.estimated_receipt(cur,today)
    assert fx['purchase_day']==d,('AY_PURCHASE_DAY',fx['purchase_day'],d)
    fx.update(ledger_baseline=ledger_baseline,report_baseline=report_baseline)
    prod.partial_production(awp.OrdinaryDraftCursor(cur),fx);api.admin(cur)
    quiet_fixture=awp.quiet_seed(cur,d,d2)
    ready=awp.preflight(cur,d2)
    if ready is None or ready['status']!='READY':
        return dict(status='INCOMPLETE',reason='fixture not READY before the invoice',blockers=awp.blockers_brief(ready),quiet=[quiet_items,quiet_fixture])
    closed_through={'goods':d2,'receipt':d}.get(closed)
    closed_before=awp.close(cur,closed_through,'AY close before the late invoice') if closed else None
    if closed and closed_before[0]!='ACCEPTED':
        return dict(status='INCOMPLETE',reason='fixture close refused',closed_before=closed_before)
    eve=today-timedelta(days=1)
    before=prod.observe(cur,fx,today)
    pre_errors=prod.differences(before,10,True,False)
    day_d_before=awp.snapshot_values(cur,d);day_d2_before=awp.snapshot_values(cur,d2);eve_before=awp.snapshot_values(cur,eve)
    events=lambda:[(str(r[0]),r[1],dec(r[2]),dec(r[3]),dec(r[4])) for r in cur.execute(
        'select id,effective_date,fg_delta,cogs_delta,other_delta from erp.po_hpp_gl_events where po_id=%s order by effective_date,id',(fx['po'],)).fetchall()]
    old={e[0] for e in events()}
    version=int(cur.execute('select row_version from erp.material_purchase_headers where id=%s',(fx['purchase'],)).fetchone()[0])
    payload=dict(purchase_id=fx['purchase'],supplier_invoice_number='AY-'+uuid.uuid4().hex[:12],invoice_date=d,
                 received_at=prod.at(today-timedelta(days=1),15),reason='AY late supplier invoice at '+price,
                 lines=[dict(purchase_item_id=fx['item'],qty_invoiced=10,final_unit_price=price)])
    prod.zone(cur,zone)
    response=prod.rpc(cur,'erp.finalize_material_purchase_invoice_v2',payload,uuid.uuid4(),version)
    api.admin(cur)
    prod.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)
    after=prod.observe(cur,fx,today)
    errors=prod.differences(after,price,True,True)
    new=[e for e in events() if e[0] not in old]
    journals=[(str(r[0]),r[1],r[2]) for r in cur.execute(
        "select e.id,j.economic_date,j.transaction_date from erp.po_hpp_gl_events e join erp.journal_entries j on j.id=e.journal_entry_id"
        " where j.source_type='PO_HPP_GL_SYNC' and e.id=any(%s::uuid[]) order by j.transaction_date",([e[0] for e in new],)).fetchall()]
    day_d_after=awp.snapshot_values(cur,d);day_d2_after=awp.snapshot_values(cur,d2);eve_after=awp.snapshot_values(cur,eve)
    # Negative daily inventory balances: the AS_OF check over every balance date up to today. Readiness and the close
    # are judged on the fixture's own window (d..d+1, cleared by quiet_seed); later seed days are not part of the case.
    pre_today=awp.preflight(cur,today)
    negative=[b for b in pre_today['blockers'] if b['code']=='GL_INVENTORY_NEGATIVE_ASOF']
    pre_d2=awp.preflight(cur,d2)
    own=awp.own_blockers(pre_d2,[fx['po']])
    close_after=awp.close(cur,d2,'AY close after the late invoice') if closed!='goods' else ('ALREADY_CLOSED',None)
    x=dec(price)-10
    fg_move=dec(day_d2_after['FG_INVENTORY'])-dec(day_d2_before['FG_INVENTORY'])
    cogs_move=dec(day_d2_after['COGS'])-dec(day_d2_before['COGS'])
    first_allowed=str(today) if closed else str(d2)
    checks=dict(values_at_estimate=not pre_errors,values_at_invoice=not errors,
                hpp_events_created=bool(new),
                hpp_events_not_before_goods=bool(new) and all(str(e[1])>=first_allowed for e in new),
                hpp_event_totals=sum(e[2] for e in new)==3*x and sum(e[3] for e in new)==2*x,
                report_receipt_day_fg_cogs_unchanged=(day_d_before['FG_INVENTORY'],day_d_before['COGS'])==(day_d_after['FG_INVENTORY'],day_d_after['COGS']),
                report_fg_day=(fg_move,cogs_move)==((Decimal(0),Decimal(0)) if closed else (3*x,2*x)),
                no_negative_daily_inventory=not negative,engine_ready_fg_day=pre_d2['status']=='READY',
                close_after_invoice=close_after[0] in ('ACCEPTED','ALREADY_CLOSED'))
    # Journal dates: a closed receipt keeps its economic date d and is posted on the recognition day (today), as before AY
    # (the AR oracles); an open one is dated from the goods, economic and posting date equal.
    checks['journal_dates']=len(journals)==len(new) and all((ec,tr)==((d,today) if closed else (tr,tr)) and (closed or tr>=d2) for _,ec,tr in journals)
    if closed=='goods':checks['closed_day_gl_unchanged']=day_d2_before==day_d2_after
    if closed:checks['history_before_invoice_unchanged']=(day_d2_before,eve_before)==(day_d2_after,eve_after)
    ok=all(checks.values())
    status='PASS' if ok else ('COUNTEREXAMPLE' if not ay_installed(cur) else 'FAIL')
    return dict(status=status,price=price,receipt_day=str(d),fg_and_sale_day=str(d2),closed_through_before_invoice=str(closed_through) if closed else None,
                checks=checks,errors=errors,pre_errors=pre_errors,new_hpp_events=[[str(v) for v in e] for e in new],
                hpp_journals=[[str(v) for v in j] for j in journals],
                report_receipt_day=dict(before=day_d_before,after=day_d_after),report_fg_day=dict(before=day_d2_before,after=day_d2_after),
                report_day_before_today=dict(day=str(eve),before=eve_before,after=eve_after),
                fg_move=str(fg_move),cogs_move=str(cogs_move),expected_move=dict(fg=str(3*x),cogs=str(2*x)),
                negative_blockers=negative,own_blockers=own,engine_status_fg_day=pre_d2['status'],blockers_fg_day=awp.blockers_brief(pre_d2),
                close_after=close_after,
                closed_before=closed_before,invoice=response,quiet=[quiet_items,quiet_fixture])


def cases(cur,today):
    return [('AY:LATE_INVOICE_LOWER_OPEN_RECEIPT_DAY',lambda:late_invoice(cur,today,'8.25',False)),
            ('AY:LATE_INVOICE_LOWER_OPEN_KIRITIMATI',lambda:late_invoice(cur,today,'8.25',False,'Pacific/Kiritimati')),
            ('AY:LATE_INVOICE_HIGHER_OPEN_RECEIPT_DAY',lambda:late_invoice(cur,today,'10.70',False)),
            ('AY:LATE_INVOICE_LOWER_CLOSED_HISTORY',lambda:late_invoice(cur,today,'8.25','goods')),
            ('AY:LATE_INVOICE_HIGHER_CLOSED_HISTORY',lambda:late_invoice(cur,today,'10.70','goods')),
            ('AY:LATE_INVOICE_LOWER_CLOSED_RECEIPT_OPEN_GOODS',lambda:late_invoice(cur,today,'8.25','receipt')),
            ('AY:LATE_INVOICE_HIGHER_CLOSED_RECEIPT_OPEN_GOODS',lambda:late_invoice(cur,today,'10.70','receipt','Pacific/Kiritimati'))]


def run(phase):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    r1.OUT=OUT
    report=dict(status='INCOMPLETE',label=LABEL,phase=phase,source=r1.source(),production_go=False,independent_acceptance=False,release_evidence=False)
    r1.save('RESULT_'+phase.upper(),report)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        r1.writer.install_at()
        control_url=os.environ['CP6_ADMISSION_CONTROL_PGURL']
        report['au_install']=awp.au_runtime.change('install',boundary.PG,control_url)['status']
        report['av_install']=awp.av_runtime.change('install',boundary.PG,control_url)['status']
        report['aw_install']=awp.install_aw();report['ax_install']=axp.install_ax();verify=axp.ax_verified
        if phase=='after':report['ay_install']=install_ay();verify=ay_verified
        r1.save('RESULT_'+phase.upper(),report)
        print(json.dumps(dict(ay_probe_setup={k:report.get(k) for k in ('au_install','av_install','aw_install','ax_install','ay_install')}),default=str),flush=True)
        group=r1.group('AY_CASES_'+phase.upper(),cases,verify)
        report['ay_cases']={k:group[k] for k in ('status','counts')}
        report['status']='REVIEW_COMPLETE' if group['status']!='INCOMPLETE' else 'INCOMPLETE'
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        r1.save('RESULT_'+phase.upper(),report)
    print(json.dumps(dict(ay_probe_phase=phase,**report),default=str),flush=True)
    assert report['status']=='REVIEW_COMPLETE',report.get('error','AY_PROBE_INCOMPLETE')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('before','after'),required=True)
    run(parser.parse_args().phase)
