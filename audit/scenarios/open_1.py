"""AUDITOR SCENARIO — OPENING OVERLAP + CONTROL TOTALS (GATE-01, AUD-B01..B03) + FG reversal diagnostic (independent auditor).
Oracle: M:138 'buktikan perlindungan tumpang tindih saldo awal pada semua jalur lama'; M:43-46 (import posts the last draft,
detail must match the control total, the control total is never posted as a transaction); AQ M:92 (control total mismatch
blocks the posting). Data generator: the writer's cp6_opening_overlap_probe.imported (import RPC path) and
duplicate_via_legacy (direct legacy erp.post_opening_balance with owner claims); the writer wrote the latter as a
COUNTEREXAMPLE probe on AQ; on the candidate (AR installed) the auditor expects the legacy duplicate to be REFUSED with
no ledger change and no second POSTED header. Expected texts are recorded verbatim (unknown a priori)."""
from datetime import timedelta
import json,traceback,uuid
import psycopg
import cp6_aw_probe as awp
import cp6_ax_probe as axp
import cp6_opening_overlap_probe as ovp
api,r1,chain=awp.api,awp.r1,awp.chain
KINDS=('MATERIAL','FINISHED_GOODS','BS','WIP','CASH_BANK','CUSTOMER_RECEIVABLE','SUPPLIER_PAYABLE','VENDOR_PAYABLE','CONTRACTOR_RECEIVABLE','CONTRACTOR_PAYABLE')

def ledger(cur):
    api.admin(cur);return api.production.ledger(cur)

def attempt(cur,fn):
    api.admin(cur);cur.execute('savepoint aud_open')
    try:
        r=fn();cur.execute('release savepoint aud_open');api.admin(cur);return r,None
    except psycopg.Error as exc:
        cur.execute('rollback to savepoint aud_open');api.admin(cur);return None,dict(sqlstate=exc.sqlstate,message=(exc.diag.message_primary or str(exc))[:300])

def overlap_case(cur,today,kind):
    first=ovp.imported(cur,today,kind)
    api.admin(cur)
    before=ledger(cur);headers_before=cur.execute("select count(*) from erp.opening_balance_headers where status='POSTED'").fetchone()[0]
    second,err=attempt(cur,lambda:ovp.duplicate_via_legacy(cur,first))
    api.admin(cur)
    after=ledger(cur);headers_after=cur.execute("select count(*) from erp.opening_balance_headers where status='POSTED'").fetchone()[0]
    items=cur.execute('select count(*) from erp.opening_balance_items where opening_id=%s',(first,)).fetchone()[0]
    checks=dict(import_posted=headers_before>=1,legacy_duplicate_refused=err is not None,no_second_posted_header=headers_after==headers_before,ledger_unchanged=before==after)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',kind=kind,checks=checks,refusal=err,first_items=items,
                expected='M:138: a legacy direct opening overlapping an imported opening (same party/material/product/model/date) is refused atomically; ledger and POSTED headers unchanged')

def import_twice(cur,today):
    """Same item imported in a second batch (import path overlap): the second FINALIZE must be refused."""
    kind='MATERIAL';first=ovp.imported(cur,today,kind)
    api.admin(cur);before=ledger(cur)
    second,err=attempt(cur,lambda:ovp.imported(cur,today,kind))   # a new tag each time -> different material; so also try same material below
    api.admin(cur)
    # exact same material/location as the first: rebuild rows from the first header
    row=cur.execute("select m.material_sku,l.location_code,i.qty,i.unit_cost_snapshot from erp.opening_balance_items i join erp.materials m on m.id=i.material_id join erp.locations l on l.id=i.location_id where i.opening_id=%s",(first,)).fetchone()
    def same():
        tag='OV'+uuid.uuid4().hex[:12]
        batch=api.call(cur,'CREATE',dict(batch_code=tag,cutover_date=str(today-timedelta(days=1))))['batch_id']
        api.upload(cur,batch,'OPENING_BALANCE_ITEM',[dict(balance_type='MATERIAL',control_key='CHECK',material_sku=row[0],location_code=row[1],qty=str(row[2]),unit_cost=str(row[3]))])
        api.upload(cur,batch,'OPENING_CONTROL',[dict(balance_type='MATERIAL',control_key='CHECK',qty=str(row[2]),amount=str(row[2]*row[3]))])
        return api.invoke(cur,'FINALIZE',batch)
    result,err2=attempt(cur,same)
    after=ledger(cur)
    posted=result and result.get('status')=='POSTED'
    checks=dict(second_batch_same_material_not_posted=not posted,refused_or_rejected=(err2 is not None) or (result is not None and result.get('status')!='POSTED'),ledger_unchanged_by_second=before==after or (err is None and second is not None))
    return dict(status='PASS' if checks['second_batch_same_material_not_posted'] else 'COUNTEREXAMPLE',checks=checks,second_result=str(result)[:300] if result else None,refusal=err2,
                expected='M:138/M:1043: the same material+location opening cannot be posted twice through the import path; refusal recorded verbatim')

def control_mismatch(cur,today):
    tag='OV'+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=tag,cutover_date=str(today-timedelta(days=1))))['batch_id']
    api.upload(cur,batch,'LOCATION',[dict(location_code=tag,location_name='auditor raw',location_type='RAW_MATERIAL_WAREHOUSE')])
    api.upload(cur,batch,'MATERIAL',[dict(material_sku=tag,material_name='auditor accessory',material_type='OTHER',unit_code='PCS')])
    api.upload(cur,batch,'OPENING_BALANCE_ITEM',[dict(balance_type='MATERIAL',control_key='CHECK',material_sku=tag,location_code=tag,qty='7',unit_cost='2.25')])
    api.upload(cur,batch,'OPENING_CONTROL',[dict(balance_type='MATERIAL',control_key='CHECK',qty='7',amount='99.99')])
    api.admin(cur);before=ledger(cur)
    result,err=attempt(cur,lambda:api.invoke(cur,'FINALIZE',batch))
    api.admin(cur);after=ledger(cur)
    ws=api.read(cur,batch);api.admin(cur)
    posted=result and result.get('status')=='POSTED'
    # fix the control and finalize: the ledger must move by exactly the items (15.75), never by the control amount
    api.upload(cur,batch,'OPENING_CONTROL',[dict(balance_type='MATERIAL',control_key='CHECK',qty='7',amount='15.75')])
    fixed,err3=attempt(cur,lambda:api.invoke(cur,'FINALIZE',batch))
    api.admin(cur);after2=ledger(cur)
    delta={k:str(after2[k]-after[k]) for k in after2 if after2[k]!=after[k]}
    checks=dict(mismatch_not_posted=not posted,ledger_unchanged_on_mismatch=before==after,fixed_control_posted=bool(fixed) and fixed.get('status')=='POSTED',
                control_total_not_a_transaction=all(str(v) not in ('99.99','-99.99') for v in delta.values()))
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,mismatch_result=str(result)[:300] if result else None,mismatch_refusal=err,workspace_status=(ws.get('batch') or {}).get('status') if isinstance(ws,dict) else None,
                fixed_result=str(fixed)[:200] if fixed else None,fixed_refusal=err3,ledger_delta_after_fix=delta,
                expected='M:43-46 / M:92: control total mismatch blocks FINALIZE with no ledger change; after the fix the ledger moves by the items only (control never posted)')

def fg_reverse_diagnostic(cur,today):
    f=axp.stocked_product(cur,today);product=str(f['product']);at=r1.now(cur)-timedelta(minutes=10)
    before=ledger(cur);cb=axp.counts(cur)
    r=axp.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=chain.base.LOCATION,qty_pcs=2,physical_at=at.isoformat(),reason='auditor diag'))
    mid=ledger(cur);cm=axp.counts(cur)
    back=axp.reverse(cur,r['receipt_id'],'auditor diag reverse')
    after=ledger(cur);ca=axp.counts(cur)
    api.admin(cur)
    je=cur.execute("select id,status,reversal_of_id from erp.journal_entries where id=%s or reversal_of_id=%s",(r['journal_entry_id'],r['journal_entry_id'])).fetchall()
    lot=cur.execute("select lot_origin,status from erp.fg_lots where id=%s",(r['lot_id'],)).fetchone() if cur.execute("select count(*) from information_schema.columns where table_schema='erp' and table_name='fg_lots' and column_name='status'").fetchone()[0] else cur.execute("select lot_origin from erp.fg_lots where id=%s",(r['lot_id'],)).fetchone()
    diff_ledger={k:(str(before.get(k)),str(after.get(k))) for k in set(before)|set(after) if before.get(k)!=after.get(k)}
    diff_counts={k:(str(cb.get(k)),str(ca.get(k))) for k in set(cb)|set(ca) if cb.get(k)!=ca.get(k)} if isinstance(cb,dict) else dict(before=str(cb),after=str(ca))
    return dict(status='PASS' if not diff_ledger else 'COUNTEREXAMPLE',ledger_diff_after_reversal=diff_ledger,counts_diff=diff_counts,journals=[[str(x) for x in j] for j in je],lot=[str(x) for x in lot] if lot else None,
                expected='reversal restores every account balance exactly (net of POSTED+REVERSED entries); counts may differ only by the voided lot/receipt rows')

def cases(cur,today):
    def wrap(fn,*a):
        def run():
            try:return fn(cur,today,*a)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1200:])
        return run
    out=[('OPEN:OVERLAP_LEGACY_AFTER_IMPORT:'+k,wrap(overlap_case,k)) for k in KINDS]
    out+=[('OPEN:IMPORT_SAME_MATERIAL_TWICE',wrap(import_twice)),('OPEN:CONTROL_TOTAL_MISMATCH_AND_NOT_POSTED',wrap(control_mismatch)),('FG:REVERSE_DIAGNOSTIC',wrap(fg_reverse_diagnostic))]
    return out
