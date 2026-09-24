"""AUDITOR SCENARIO — CLOSE + ACCESS (independent auditor, blind phase 1).
Contract oracles: AUD-S06 (M:6049-6071) one preflight and a re-check of ALL blockers inside the close; AUD-B04 (M:6144-6169)
no READY while per-date allocation inconsistent; filed snapshot preserved / latest-corrected wins (M:1054-1090, R4 §5);
AQ access rule (M:98): writer attempts by anon/viewer/unmapped/inactive are refused and every ERP table stays intact;
AUD-G07 (M:6356-6380). Expected refusal texts are taken from the candidate SQL itself (exact match), never from writer tests."""
from datetime import timedelta
from decimal import Decimal
import json,traceback,uuid
import cp6_aw_probe as awp
import cp6_az_probe as azp
api,boundary,chain,r1=awp.api,awp.boundary,awp.chain,awp.r1
D=lambda v:Decimal(str(v))

def claims(cur,payload):
    cur.execute("select set_config('request.jwt.claim.sub','',true)")
    cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(payload),))

def as_authenticated(cur,sub):
    api.admin(cur);claims(cur,dict(sub=sub,role='authenticated'));cur.execute('set local session authorization authenticated')

def as_anon(cur):
    api.admin(cur);claims(cur,dict(role='anon'));cur.execute('set local session authorization anon')

def attempt(cur,fn):
    result,error=r1.peer.attempt(cur,fn);api.admin(cur);return result,error

def app_user_columns(cur):
    api.admin(cur)
    return [r[0] for r in cur.execute("select column_name from information_schema.columns where table_schema='erp' and table_name='app_users' order by ordinal_position").fetchall()]

def non_owner_sub(cur):
    """A seeded app user whose role is not OWNER/ADMIN, if any (returns (sub, role, is_active))."""
    api.admin(cur);cols=app_user_columns(cur)
    idcol=next((c for c in ('auth_user_id','auth_id','user_id','auth_uid') if c in cols),None)
    rolecol=next((c for c in ('role','app_role','role_code') if c in cols),None)
    actcol=next((c for c in ('is_active','active') if c in cols),None)
    if not idcol or not rolecol:return None,None,None,cols
    rows=cur.execute(f"select {idcol}::text,{rolecol}::text,{actcol if actcol else 'true'} from erp.app_users where {rolecol}::text not in ('OWNER','ADMIN') order by 2 limit 1").fetchall()
    return (rows[0][0],rows[0][1],rows[0][2],cols) if rows else (None,None,None,cols)

def snapshot_control(cur):
    api.admin(cur)
    return dict(closed_through=str(cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]),
                filings=cur.execute('select count(*) from erp.accounting_close_filings_v1').fetchone()[0],
                estimates=cur.execute('select count(*) from erp.laundry_rate_owner_estimates_v1').fetchone()[0],
                fg_unsourced=cur.execute('select count(*) from erp.fg_unsourced_receipts_v1').fetchone()[0])

FACADES=[('preflight',lambda cur:cur.execute("select public.erp_accounting_close_preflight_v1(current_date-1)").fetchone()[0]),
         ('close',lambda cur:cur.execute("select public.erp_close_accounting_through_v1(current_date-1,'auditor access probe')").fetchone()[0]),
         ('laundry_estimate',lambda cur:cur.execute("select public.erp_set_laundry_rate_owner_estimate_v1(%s,1.5,'auditor access probe')",(uuid.uuid4(),)).fetchone()[0]),
         ('fg_preview',lambda cur:cur.execute("select public.erp_preview_fg_unsourced_value_v1(%s,statement_timestamp())",(uuid.uuid4(),)).fetchone()[0]),
         ('fg_post',lambda cur:cur.execute("select public.erp_post_fg_unsourced_receipt_v1(%s::jsonb,%s)",('{}',uuid.uuid4())).fetchone()[0]),
         ('fg_reverse',lambda cur:cur.execute("select public.erp_reverse_fg_unsourced_receipt_v1(%s,'auditor',%s)",(uuid.uuid4(),uuid.uuid4())).fetchone()[0])]

def access_case(cur,today,who):
    before=snapshot_control(cur);out={};sub=None;role=None;active=None
    if who=='unmapped':sub=str(uuid.uuid4())
    if who=='non_owner':
        sub,role,active,cols=non_owner_sub(cur)
        if sub is None:return dict(status='INCOMPLETE',error='no seeded non-owner app user found',app_users_columns=cols)
    for name,fn in FACADES:
        if who=='anon':as_anon(cur)
        else:as_authenticated(cur,sub)
        result,error=attempt(cur,lambda:fn(cur))
        out[name]=dict(refused=error is not None,message=(error or {}).get('message'),sqlstate=(error or {}).get('sqlstate') or (error or {}).get('code'),result=None if error else str(result)[:200])
    after=snapshot_control(cur)
    expected_msg='OWNER or ADMIN access required'
    all_refused=all(v['refused'] for v in out.values())
    exact=all((v['message'] or '').startswith(expected_msg) or 'permission denied' in (v['message'] or '') for v in out.values())
    return dict(status='PASS' if all_refused and exact and before==after else 'COUNTEREXAMPLE',who=who,sub=sub,role=role,active=active,calls=out,control_before=before,control_after=after,
                expected="every facade refused: authenticated non-owner/unmapped -> 'OWNER or ADMIN access required' (require_owner_admin, migrations 20260902043000 l.144); anon -> permission denied (execute revoked from anon); control tables unchanged")

def owner_positive(cur,today):
    """Positive control: the seeded operator (api.ordinary) can read the preflight; result shape recorded."""
    api.ordinary(cur)
    r,e=attempt(cur,lambda:cur.execute("select public.erp_accounting_close_preflight_v1(%s)",(today-timedelta(days=1),)).fetchone()[0])
    return dict(status='PASS' if e is None and isinstance(r,dict) and 'status' in r else 'COUNTEREXAMPLE',error=e,status_field=(r or {}).get('status') if isinstance(r,dict) else None,keys=sorted(r.keys())[:20] if isinstance(r,dict) else None,expected='operator/owner session gets a readiness object with status')

def close_fixture(cur,today):
    d=today-timedelta(days=3)
    boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    awp.quiet_seed(cur,d,today-timedelta(days=1))
    return d

def close_ready_then_close(cur,today):
    d=close_fixture(cur,today);day=today-timedelta(days=1)
    pre=awp.preflight(cur,day)
    if pre is None or pre['status']!='READY':return dict(status='INCOMPLETE',error='fixture not READY',codes=awp.codes(pre))
    before=snapshot_control(cur)
    accepted,err=awp.close(cur,day,'auditor close READY')
    after=snapshot_control(cur)
    api.admin(cur)
    filing=cur.execute("select closed_through::text,previous_closed_through::text,readiness->>'status',jsonb_typeof(gl_balances) from erp.accounting_close_filings_v1 order by filed_at desc limit 1").fetchone()
    # second call to an EARLIER date must be refused with the exact reopen message
    r2,e2=attempt(cur,lambda:(api.ordinary(cur),cur.execute('select erp.close_accounting_through(%s,%s)',(day-timedelta(days=1),'auditor earlier'))))
    # a close for today (not before today) must be refused
    r3,e3=attempt(cur,lambda:(api.ordinary(cur),cur.execute('select erp.close_accounting_through(%s,%s)',(today,'auditor today'))))
    checks=dict(close_accepted=accepted=='ACCEPTED',closed_through_moved=after['closed_through']==str(day),one_filing_added=after['filings']==before['filings']+1,
                filing_snapshot_ready=bool(filing) and filing[2]=='READY' and filing[3]=='object',
                earlier_close_refused_exact=bool(e2) and (e2.get('message') or '').startswith('Untuk membuka kembali periode gunakan reopen_accounting_through(); periode saat ini sudah ditutup sampai '),
                today_close_refused_exact=bool(e3) and (e3.get('message') or '')=='Tutup buku hanya boleh sampai tanggal sebelum hari ini')
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,accepted=accepted,err=err,filing=filing,e2=(e2 or {}).get('message'),e3=(e3 or {}).get('message'),
                expected='READY -> close accepted, filing row with readiness snapshot; earlier date refused (reopen message, AW l.632); today refused (AW l.628)')

def close_blocked_and_recheck(cur,today):
    """S06: blocker introduced AFTER a READY preflight must still stop the close (re-check inside the close)."""
    d=close_fixture(cur,today);day=today-timedelta(days=1)
    pre0=awp.preflight(cur,day)
    if pre0 is None or pre0['status']!='READY':return dict(status='INCOMPLETE',error='fixture not READY',codes=awp.codes(pre0))
    # introduce an open item dated inside the period: a paid attendance day of a new contractor not covered by any payroll
    contractor,worker=awp.contractor_with_worker(cur,d,'AUD close blocker')
    awp.post_attendance(cur,contractor,d,d,status='PRESENT')
    pre1=awp.preflight(cur,day);codes1=awp.codes(pre1)
    before=snapshot_control(cur)
    accepted,err=awp.close(cur,day,'auditor close with blocker')
    after=snapshot_control(cur)
    msg=(err or {}).get('message') or ''
    checks=dict(blocker_visible_in_preflight=bool(pre1) and pre1['status']!='READY' and bool(codes1),
                close_refused=accepted!='ACCEPTED',
                refusal_is_close_blocked_exact=msg.startswith('CLOSE_BLOCKED: tutup buku sampai %s ditolak, '%day) and 'penghalang' in msg,
                refusal_names_preflight_codes=all(c in msg for c in (codes1 or [])),
                control_unchanged=before==after)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,preflight_after_blocker=codes1,message=msg[:600],expected='S06: close re-evaluates readiness itself; CLOSE_BLOCKED lists the blocker codes; closed_through and filings unchanged')

def filing_immutable(cur,today):
    d=close_fixture(cur,today);day=today-timedelta(days=1)
    pre=awp.preflight(cur,day)
    if pre is None or pre['status']!='READY':return dict(status='INCOMPLETE',error='fixture not READY',codes=awp.codes(pre))
    accepted,err=awp.close(cur,day,'auditor close for immutability')
    if accepted!='ACCEPTED':return dict(status='INCOMPLETE',error='close refused',err=err)
    api.admin(cur)
    r1_,e1=attempt(cur,lambda:cur.execute("update erp.accounting_close_filings_v1 set reason='tampered' where closed_through=%s",(day,)))
    r2_,e2=attempt(cur,lambda:cur.execute("delete from erp.accounting_close_filings_v1 where closed_through=%s",(day,)))
    exp='CLOSE_FILING_IMMUTABLE: snapshot tutup buku tidak boleh diubah atau dihapus'
    checks=dict(update_refused_exact=bool(e1) and (e1.get('message') or '')==exp,delete_refused_exact=bool(e2) and (e2.get('message') or '')==exp)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,e1=(e1 or {}).get('message'),e2=(e2 or {}).get('message'),expected='filed snapshot never overwritten (contract latest-corrected wins, filed snapshot preserved; AW l.40)')

def closed_correction_confidence(cur,today):
    """After a close, a supplier invoice dated inside the closed period: filed snapshot unchanged, report shows changed_since_filing."""
    prod=chain.production
    d=today-timedelta(days=3);d1=d+timedelta(days=1)
    boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    awp.quiet_seed(cur,d,today-timedelta(days=1),exclude=[prod.CONTRACTOR])
    fx=prod.estimated_receipt(cur,today)
    po=azp.cut(cur,fx,d1,4)
    awp.quiet_seed(cur,d,today-timedelta(days=1))
    pre=awp.preflight(cur,d1)
    if pre is None or pre['status']!='READY':return dict(status='INCOMPLETE',error='fixture not READY',codes=awp.codes(pre))
    accepted,err=awp.close(cur,d1,'auditor close before closed-period invoice')
    if accepted!='ACCEPTED':return dict(status='INCOMPLETE',error='close refused',err=err)
    api.admin(cur)
    filed_before=cur.execute('select gl_balances::text,readiness::text from erp.accounting_close_filings_v1 where closed_through=%s',(d1,)).fetchone()
    rep_before=awp.report(cur,d1)
    azp.invoice(cur,fx,today,'12',d)   # invoice dated d, inside the closed period
    api.admin(cur)
    filed_after=cur.execute('select gl_balances::text,readiness::text from erp.accounting_close_filings_v1 where closed_through=%s',(d1,)).fetchone()
    rep_after=awp.report(cur,d1)
    posted_inside=cur.execute("select count(*) from erp.journal_entries where transaction_date<=%s and created_at>=statement_timestamp()-interval '2 minutes'",(d1,)).fetchone()[0]
    checks=dict(filed_snapshot_unchanged=filed_before==filed_after,report_marks_changed_since_filing=bool(rep_after.get('changed_since_filing')),
                report_had_filing=rep_after.get('filing') is not None,no_journal_posted_inside_closed_period=posted_inside==0)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,report_before=rep_before,report_after=rep_after,posted_inside=posted_inside,
                expected='closed period: controlled adjustment posted outside the closed days; filed snapshot immutable; dated report flags changed_since_filing (contract: filed snapshot preserved, latest-corrected wins)')

def cases(cur,today):
    def wrap(fn,*a):
        def run():
            try:return fn(cur,today,*a)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1200:])
        return run
    return [('ACCESS:ANON_ALL_FACADES',wrap(access_case,'anon')),
            ('ACCESS:UNMAPPED_AUTHENTICATED_ALL_FACADES',wrap(access_case,'unmapped')),
            ('ACCESS:NON_OWNER_APP_USER_ALL_FACADES',wrap(access_case,'non_owner')),
            ('ACCESS:OWNER_POSITIVE_PREFLIGHT',wrap(owner_positive)),
            ('CLOSE:READY_THEN_CLOSE_AND_EXACT_REFUSALS',wrap(close_ready_then_close)),
            ('CLOSE:S06_BLOCKER_AFTER_PREFLIGHT_RECHECKED',wrap(close_blocked_and_recheck)),
            ('CLOSE:FILING_IMMUTABLE',wrap(filing_immutable)),
            ('CLOSE:CLOSED_PERIOD_CORRECTION_CONFIDENCE',wrap(closed_correction_confidence))]
