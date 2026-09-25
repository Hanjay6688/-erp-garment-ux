"""AUDITOR SCENARIO xaudit_9 (round 9, Fable, independent): W9 changed_since_filing (C0 D01 3.4, ratified addendum).
Tool head d1bc8ad. Oracle (addendum C0 D01 3.4, owner-ratified): when E is already closed, every part of a correction keeps the
economic date E and is booked on the recognition day in the open period; the filing and the closed snapshot are not overwritten;
the report marks `changed_since_filing`. D01 5: the report on date D uses corrected facts dated <= D.
Cases (own fixture: a direct FINAL receipt of 10 units @10 two days before the close date d, seed quieted, owner close of d):
 A  a cost correction to 12 whose invoice date is inside the closed period, processed -> report(d).changed_since_filing is True;
    the filed values of d and the filing row are unchanged; the correction journal carries economic date E and a transaction date
    after d (one journal per part).
 B  control: no change after the filing -> False (also after the recalc queue is processed).
 C  adversarial: a correction whose invoice date is d+1 (open, after the filed date) -> report(d) stays False, because the filed
    picture of d is not corrected (D01 5: facts dated <= D only); the correction itself posts on d+1.
Every unexpected error is INCOMPLETE; refusals recorded verbatim."""
from datetime import timedelta
from decimal import Decimal
import json,traceback,uuid
import psycopg
import cp6_aw_probe as awp
import cp6_az_probe as azp
api=awp.api;chain=awp.chain;prod=chain.production
D=Decimal

def attempt(cur,fn):
    api.admin(cur);cur.execute('savepoint xa9')
    try:
        r=fn();cur.execute('release savepoint xa9');api.admin(cur);return r,None
    except psycopg.Error as exc:
        cur.execute('rollback to savepoint xa9');api.admin(cur);return None,dict(sqlstate=exc.sqlstate,message=(exc.diag.message_primary or str(exc))[:400])

def correction(cur,fx,day,price):
    api.admin(cur);cid=uuid.uuid4()
    cur.execute("insert into erp.material_purchase_cost_corrections(id,correction_number,purchase_id,supplier_invoice_number,invoice_date,reason,status) values(%s,%s,%s,%s,%s,'XA9 cost correction','DRAFT')",(cid,'XA9-CC-'+cid.hex[:12],fx['purchase'],'XA9-CCINV-'+cid.hex[:12],day))
    cur.execute('insert into erp.material_purchase_cost_correction_items(correction_id,purchase_item_id,new_unit_price) values(%s,%s,%s)',(cid,fx['item'],price))
    prod.owner(cur);cur.execute('select erp.post_material_purchase_cost_correction(%s)',(cid,));api.admin(cur);return cid

def journals_since(cur,marker):
    api.admin(cur)
    return [list(map(str,r)) for r in cur.execute("""select source_type,economic_date,transaction_date,status from erp.journal_entries
        where id<>all(%s::uuid[]) and status in('POSTED','REVERSED') order by transaction_date,economic_date,source_type""",(marker,)).fetchall()]

def w9(cur,today,mode):
    d=today-timedelta(days=1);receipt_day=d-timedelta(days=2)
    awp.boundary.historical.prior.set_open_period(cur,receipt_day-timedelta(days=1))
    fx=azp.final_receipt(cur,receipt_day,qty=10,price=10)
    quiet=awp.quiet_seed(cur,receipt_day,d)
    ready=awp.preflight(cur,d)
    if ready is None or ready['status']!='READY':return dict(status='INCOMPLETE',reason='fixture not READY before the close',blockers=awp.blockers_brief(ready) if ready else None,quiet=quiet)
    closed=awp.close(cur,d,'XA9 close before a later correction')
    if closed[0]!='ACCEPTED':return dict(status='INCOMPLETE',reason='close refused',close=closed)
    values_before=awp.snapshot_values(cur,d);filed_before=awp.filings(cur);at_close=awp.report(cur,d)
    api.admin(cur);known=[str(r[0]) for r in cur.execute("select id from erp.journal_entries").fetchall()]
    inv_day={'A':receipt_day,'C':d+timedelta(days=1)}.get(mode)
    r,err=(None,None)
    if inv_day is not None:
        r,err=attempt(cur,lambda:correction(cur,fx,inv_day,'12'))
        if err:return dict(status='INCOMPLETE',mode=mode,reason='correction refused',refusal=err,invoice_date=str(inv_day),at_close=at_close)
    prod.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)
    later=journals_since(cur,known);done=awp.preflight(cur,d);rep=awp.report(cur,d)
    values_after=awp.snapshot_values(cur,d);filed_after=awp.filings(cur)
    ev=dict(mode=mode,closed_through=str(d),receipt_day=str(receipt_day),correction_invoice_date=str(inv_day) if inv_day else None,report_at_close=at_close,report_after=rep,
            engine_after=done and done['status'],journals_after_filing=later,values_unchanged=values_before==values_after,values_at_d=values_after,
            filing_unchanged=filed_before==filed_after and len(filed_after)==1,filings=filed_after)
    base=at_close['changed_since_filing'] is False and ev['values_unchanged'] and ev['filing_unchanged']
    if mode=='A':
        parts_ok=bool(later) and all(x[1]==str(receipt_day) and x[2]>str(d) for x in later)
        checks=dict(base_unchanged_filing_and_values=base,correction_booked_after_d_with_economic_date_E=parts_ok,marked_changed_since_filing=rep['changed_since_filing'] is True,report_ready=rep['status']=='READY')
        exp='C0 D01 3.4: closed E -> economic date E, booked on the recognition day; filing and snapshot untouched; report(d) marks changed_since_filing after the correction is processed'
    elif mode=='B':
        checks=dict(base_unchanged_filing_and_values=base,no_journal_after_filing=not later,not_marked=rep['changed_since_filing'] is False,report_ready=rep['status']=='READY')
        exp='Control: nothing booked after the filing -> changed_since_filing False'
    else:
        parts_ok=bool(later) and all(x[1]==str(inv_day) for x in later)
        checks=dict(base_unchanged_filing_and_values=base,correction_dated_after_d=parts_ok,not_marked_for_d=rep['changed_since_filing'] is False,report_ready=rep['status']=='READY')
        exp='C0 D01 5: a correction dated after d does not change the filed picture of d -> changed_since_filing False for d (marker must be specific to the filed picture)'
    return dict(ev,status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,expected=exp)

def cases(cur,today):
    def wrap(fn,*a):
        def run():
            try:return fn(cur,today,*a)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1500:])
        return run
    return [('XA9:W9_A_CORRECTION_IN_CLOSED_PERIOD_MARKS_FILED_DATE',wrap(w9,'A')),
            ('XA9:W9_B_NO_CHANGE_CONTROL',wrap(w9,'B')),
            ('XA9:W9_C_CORRECTION_AFTER_FILED_DATE_DOES_NOT_MARK',wrap(w9,'C'))]
