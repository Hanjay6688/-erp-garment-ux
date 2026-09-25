"""AUDITOR SCENARIO xaudit_6 — CP6-19 through the LEGITIMATE application path (owner: M:1024-1025 'Draft boleh diedit sampai
disahkan. Finalisasi wajib memakai isi terakhir di bawah lock, memeriksa rincian melawan total, dan tidak menggandakan stok
atau uang'; M:3817 'Prepare tetap DRAFT dan editable; perubahan staging/item harus membuat prepared preview lama stale;
validasi/prepare terbaru menentukan yang diposting').
Path = the UI's own actions only: CREATE -> SAVE_FILE (upload) -> VALIDATE / FINALIZE -> SAVE_FILE again (edit = re-upload of
the entity file, as the UI editor does) -> FINALIZE. No direct SQL edits, no native prepare call.
Cases: (1) edit after VALIDATE: WIP 8 -> 4 then FINALIZE; (2) edit after a FINALIZE that was refused on control mismatch
(prepared header exists): fix item+control 8 -> 4 then FINALIZE. Oracle: posted opening item qty = 4, production source qty = 4,
wip_stage_events for the opening = 4, opening value 20.00, no residue of the 8-row (no double stock)."""
from datetime import timedelta
import json,traceback,uuid
import psycopg
import cp6_aw_probe as awp
import cp6_initial_import_production_trial as pt
api=awp.api

def attempt(cur,fn):
    api.admin(cur);cur.execute('savepoint xa6')
    try:
        r=fn();cur.execute('release savepoint xa6');api.admin(cur);return r,None
    except psycopg.Error as exc:
        cur.execute('rollback to savepoint xa6');api.admin(cur);return None,dict(sqlstate=exc.sqlstate,message=(exc.diag.message_primary or str(exc))[:300])

def reupload(cur,f,qty,amount,control_amount):
    rows=[dict(r,qty=qty,amount=amount) if r.get('balance_type')=='WIP' else r for r in f['rows']]
    api.upload(cur,f['batch'],'OPENING_BALANCE_ITEM',rows)
    controls=[dict(c,qty=qty,amount=control_amount) if c.get('control_key')=='WIP' else c for c in f['controls']]
    api.upload(cur,f['batch'],'OPENING_CONTROL',controls)

def facts(cur,batch):
    api.admin(cur)
    return cur.execute("""select i.qty::text,i.amount::text,s.qty_pcs,s.original_amount::text,h.status,
        (select coalesce(sum(qty_pcs),0) from erp.wip_stage_events where source_type='INITIAL_IMPORT_WIP_OPENING' and source_id=i.id),
        (select count(*) from erp.opening_balance_items x join erp.opening_balance_headers hx on hx.id=x.opening_id where hx.migration_batch_id=%s and x.balance_type='WIP')
      from erp.opening_balance_headers h join erp.opening_balance_items i on i.opening_id=h.id and i.balance_type='WIP'
      join erp.initial_import_production_sources s on s.opening_item_id=i.id where h.migration_batch_id=%s""",(batch,batch)).fetchall()

def check(cur,f,r):
    rows=facts(cur,f['batch'])
    ok=len(rows)==1 and rows[0][4]=='POSTED' and float(rows[0][0])==4 and rows[0][2]==4 and float(rows[0][3])==20 and float(rows[0][5])==4 and rows[0][6]==1
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',finalize=str(r)[:200],posted_wip_rows=[[str(x) for x in row] for row in rows],
                expected='M:1024-1025/M:3817: the LAST uploaded content (WIP 4 pcs / 20.00) is what is posted: item qty 4, source qty 4, stage events 4, one WIP row, no residue of 8')

def edit_after_validate(cur,today):
    f=pt.fixture(api,cur,today)
    v1=api.invoke(cur,'VALIDATE',f['batch'])
    reupload(cur,f,'4','20.00','20.00')
    v2=api.invoke(cur,'VALIDATE',f['batch'])
    r,err=attempt(cur,lambda:api.invoke(cur,'FINALIZE',f['batch']))
    if err:return dict(status='INCOMPLETE',error=err,validate1=str(v1)[:150],validate2=str(v2)[:150])
    out=check(cur,f,r);out.update(validate_before_edit=str(v1)[:150],validate_after_edit=str(v2)[:150]);return out

def edit_after_refused_finalize(cur,today):
    f=pt.fixture(api,cur,today)
    # first FINALIZE refused by a control mismatch (WIP control 99.99): the prepared header/items exist in DRAFT state
    controls=[dict(c,amount='99.99') if c.get('control_key')=='WIP' else c for c in f['controls']]
    api.upload(cur,f['batch'],'OPENING_CONTROL',controls)
    r1,e1=attempt(cur,lambda:api.invoke(cur,'FINALIZE',f['batch']))
    api.admin(cur)
    prepared=cur.execute("select h.status,count(i.*) from erp.opening_balance_headers h left join erp.opening_balance_items i on i.opening_id=h.id where h.migration_batch_id=%s group by h.status",(f['batch'],)).fetchall()
    # then the operator fixes the file: WIP 4 pcs / 20.00 and control 4 / 20.00, and finalizes
    reupload(cur,f,'4','20.00','20.00')
    r2,e2=attempt(cur,lambda:api.invoke(cur,'FINALIZE',f['batch']))
    if e2:return dict(status='INCOMPLETE',error=e2,first_finalize=str(r1)[:200],first_error=e1,prepared_after_first=[[str(x) for x in p] for p in prepared])
    out=check(cur,f,r2);out.update(first_finalize=str(r1)[:200],first_error=e1,prepared_after_first=[[str(x) for x in p] for p in prepared]);return out

def cases(cur,today):
    def wrap(fn):
        def run():
            try:return fn(cur,today)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1500:])
        return run
    return [('XA6:CP6-19_LEGIT_EDIT_AFTER_VALIDATE_WIP_8_TO_4',wrap(edit_after_validate)),
            ('XA6:CP6-19_LEGIT_EDIT_AFTER_REFUSED_FINALIZE_WIP_8_TO_4',wrap(edit_after_refused_finalize))]
