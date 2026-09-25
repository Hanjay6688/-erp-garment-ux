"""AUDITOR SCENARIO xaudit_6 rev3 — CP6-19 through the LEGITIMATE application path.
rev1 (run 36080176237) and rev2 (run 36080510340) were INCOMPLETE: the edited file was refused by the product's own import
validation (rev1: WIP cost origin 4x10=40 > new WIP amount 20 'ORIGIN_OVER_VALUE'; rev2: origin halved to 2 but the
UNINVOICED_RECEIPT rule 'receipt qty = remaining material stock + all cost origins' (20ap:4413) then failed 12 <> 4+2+2+2).
rev3 makes the edit balance-consistent, exactly as an operator would have to: WIP 8 pcs/40.00 -> 4 pcs/20.00, WIP cost origin
4 -> 2 material units, material stock row 4 -> 6 units, controls WIP 4/20.00 and STOCK 6/60.00 (GRNI 12/120.00 unchanged).
Owner text: M:1024-1025 'Draft boleh diedit sampai disahkan. Finalisasi wajib memakai isi terakhir di bawah lock, memeriksa
rincian melawan total, dan tidak menggandakan stok atau uang'; M:3817 'Prepare tetap DRAFT dan editable; perubahan
staging/item harus membuat prepared preview lama stale; validasi/prepare terbaru menentukan yang diposting'.
Path = the UI's own actions only: CREATE -> SAVE_FILE -> VALIDATE -> SAVE_FILE again (edit = re-upload, as the UI editor does)
-> VALIDATE -> FINALIZE. No direct SQL edits of any table, no test-only grants.
Case 1: edit after VALIDATE. Oracle: posted opening WIP item qty 4 / 20.00, production source qty 4, wip_stage_events 4,
exactly one WIP row (no residue of 8).
Case 2: a prepared DRAFT exists first, reached ONLY through the RPC the product itself exposes to authenticated users
(erp.prepare_migration_opening_balance, ACL authenticated=X, after apply_migration_master_rows/apply_migration_open_pos, the
same sequence GPT's SI-04 used) — then the operator edits through SAVE_FILE and finalizes. Oracle (M:1025/M:3817): either the
product refuses the edit explicitly (refusal recorded, PASS: no silent stale posting) or it accepts it and posts the LAST
content (4). Accepting the edit but posting the stale prepared 8 = COUNTEREXAMPLE."""
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

def reupload(cur,f,qty='4',amount='20.00',origin_qty='2',stock_qty='6',stock_amount='60.00'):
    rows=[]
    for r in f['rows']:
        if r.get('balance_type')=='WIP':rows.append(dict(r,qty=qty,amount=amount))
        elif r.get('balance_type')=='MATERIAL':rows.append(dict(r,qty=stock_qty))
        else:rows.append(r)
    api.upload(cur,f['batch'],'OPENING_BALANCE_ITEM',rows)
    origins=[dict(o,qty=origin_qty) if o.get('target_source_key')=='WIP' else o for o in f['origins']]
    api.upload(cur,f['batch'],'OPENING_COST_ORIGIN',origins)
    controls=[]
    for c in f['controls']:
        if c.get('control_key')=='WIP':controls.append(dict(c,qty=qty,amount=amount))
        elif c.get('control_key')=='STOCK':controls.append(dict(c,qty=stock_qty,amount=stock_amount))
        else:controls.append(c)
    api.upload(cur,f['batch'],'OPENING_CONTROL',controls)

def errors(cur,batch):
    api.admin(cur)
    ws=api.read(cur,batch)
    out=[]
    for k,v in (ws.items() if isinstance(ws,dict) else []):
        if isinstance(v,list):
            for row in v:
                if isinstance(row,dict) and (row.get('validation_errors') or row.get('errors')):out.append(dict(entity=k,errors=str(row.get('validation_errors') or row.get('errors'))[:200]))
    if not out:
        rows=cur.execute("select entity_type,validation_errors::text from erp.migration_staging_rows where batch_id=%s and validation_status='ERROR'",(batch,)).fetchall()
        out=[dict(entity=r[0],errors=r[1][:200]) for r in rows]
    return out[:8]

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
    r0,e0=attempt(cur,lambda:reupload(cur,f))
    if e0:return dict(status='INCOMPLETE',reason='re-upload refused',error=e0,validate1=str(v1)[:150])
    v2=api.invoke(cur,'VALIDATE',f['batch'])
    r,err=attempt(cur,lambda:api.invoke(cur,'FINALIZE',f['batch']))
    if err:return dict(status='INCOMPLETE',error=err,validate1=str(v1)[:150],validate2=str(v2)[:150])
    if r.get('status')!='POSTED':return dict(status='INCOMPLETE',reason='edited file refused by validation (fixture, not product): see validation_errors',finalize=str(r)[:200],validation_errors=errors(cur,f['batch']),validate_after_edit=str(v2)[:150])
    out=check(cur,f,r);out.update(validate_before_edit=str(v1)[:150],validate_after_edit=str(v2)[:150]);return out

def prepared_rows(cur,batch):
    api.admin(cur)
    return [[str(x) for x in p] for p in cur.execute("""select h.status,i.balance_type,i.qty::text,i.amount::text from erp.opening_balance_headers h
        left join erp.opening_balance_items i on i.opening_id=h.id where h.migration_batch_id=%s order by i.balance_type""",(batch,)).fetchall()]

def edit_after_exposed_prepare(cur,today):
    f=pt.fixture(api,cur,today)
    v1=api.invoke(cur,'VALIDATE',f['batch'])
    def prepare():
        api.ordinary(cur)
        cur.execute('select erp.apply_migration_master_rows(%s)',(f['batch'],))
        cur.execute('select erp.apply_migration_open_pos(%s)',(f['batch'],))
        return str(cur.execute('select erp.prepare_migration_opening_balance(%s,null)',(f['batch'],)).fetchone()[0])
    header,e1=attempt(cur,prepare)
    if e1:return dict(status='INCOMPLETE',reason='exposed prepare RPC refused for the ordinary authenticated actor',error=e1,validate1=str(v1)[:150])
    before=prepared_rows(cur,f['batch'])
    r0,e0=attempt(cur,lambda:reupload(cur,f))
    if e0:
        return dict(status='INCOMPLETE',verdict='EDIT_REFUSED_NO_STALE_POST_BUT_EDITABILITY_UNPROVEN',refusal=e0,prepared_before_edit=before,
                    expected='M:1025/M:3817: no silent stale posting — the product either rebuilds from the last content or refuses the edit explicitly; here it refuses (message recorded). Note for handoff: after the exposed prepare the UI re-upload path is closed, so the only way to edit a prepared draft is a direct table edit (GPT SI-04).')
    after_edit=prepared_rows(cur,f['batch'])
    v2=api.invoke(cur,'VALIDATE',f['batch'])
    r,err=attempt(cur,lambda:api.invoke(cur,'FINALIZE',f['batch']))
    if err:return dict(status='INCOMPLETE',error=err,prepared_before_edit=before,prepared_after_edit=after_edit,validate2=str(v2)[:150])
    if r.get('status')!='POSTED':return dict(status='INCOMPLETE',reason='edited file refused by validation: see validation_errors',finalize=str(r)[:200],validation_errors=errors(cur,f['batch']),prepared_before_edit=before,prepared_after_edit=after_edit)
    out=check(cur,f,r);out.update(prepared_before_edit=before,prepared_after_edit=after_edit,validate1=str(v1)[:150],validate2=str(v2)[:150]);return out

def cases(cur,today):
    def wrap(fn):
        def run():
            try:return fn(cur,today)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1500:])
        return run
    return [('XA6:CP6-19_LEGIT_EDIT_AFTER_VALIDATE_WIP_8_TO_4',wrap(edit_after_validate)),
            ('XA6:CP6-19_EDIT_AFTER_EXPOSED_PREPARE_WIP_8_TO_4',wrap(edit_after_exposed_prepare))]
