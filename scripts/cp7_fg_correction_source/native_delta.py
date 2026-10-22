"""Counted substitutions of three installed functions (OW-08b, D17-13 2.21: FG corrections at QC).

A. cp7_transaction_source.resolve(jsonb), as left by the kasbon stage: an FG inverse (FG_MOVEMENT_REVERSAL) opens what
   its original movement opens whenever that family is a finished-goods document the reader's own CASE supports (QC,
   sale, sales return, FG adjustment, rework). The CASE, its domains, routes and view rights stay byte-for-byte; other
   FG families (product conversion, opening, unsourced receipt, import) keep UNSUPPORTED_SOURCE.
B. erp.reverse_qc(uuid,text) and erp.get_laundry_qc_workspace_v1(text,text): every refusal keeps its condition and its
   first sentence; the sentence gets the blocking document numbers and the real menu where each is undone
   (cp7_fg_correction_source.qc_blocker_text_v1) and the refusal a JSON DETAIL with the same list.
"""
from hashlib import sha256
import re

SOURCE='cp7_transaction_source.resolve(jsonb)'
REVERSE='erp.reverse_qc(uuid,text)'
WORKSPACE='erp.get_laundry_qc_workspace_v1(text,text)'
SIGNATURES=(SOURCE,REVERSE,WORKSPACE)
# The installed predicate the blocker list mirrors (erp.fg_lot_has_active_downstream, pinned in the AN-AP catalogs).
DOWNSTREAM='erp.fg_lot_has_active_downstream(uuid,text,text,uuid)'
DOWNSTREAM_SHA256='f65dc3f4888809d0566095f7d5c7a59a6103cfa83f688aef679845d6fba85045'
# Every family Native FG writers put on erp.fg_stock_movements that this reader already opens, with its CASE domain.
FAMILIES={'QC_ITEM':'QC','SALE_ITEM':'SALE','SALES_RETURN_ITEM':'SALE','FG_ADJUSTMENT_ITEM':'FG_ADJUSTMENT','REWORK_ORDER':'BS_REWORK'}
# Native FG families the reader has no document for; they stay UNSUPPORTED_SOURCE.
UNSUPPORTED=('PRODUCT_CONVERSION','OPENING_BALANCE_ITEM','FG_UNSOURCED_RECEIPT','INITIAL_IMPORT_WIP','BB_OPENING_SALE_RETURN')
TEXT='cp7_fg_correction_source.qc_blocker_text_v1'
LIST='cp7_fg_correction_source.qc_blockers_v1'

SOURCE_STEPS=(
 ('comment',
  " -- A Native FG inverse references the original movement UUID, not a QC\n"
  " -- inspection. Follow that actual immutable link only for the qualified QC\n"
  " -- source family. Other FG inverse families stay explicitly unsupported.\n",
  " -- OW-08b (D17-13 2.21): a Native FG inverse references the original movement UUID. It opens what that\n"
  " -- original opens when its family is a finished-goods document this reader opens below (QC, sale, sales\n"
  " -- return, FG adjustment, rework); that family's own view rights still apply after the warehouse right.\n"
  " -- Other FG families (product conversion, opening, unsourced receipt, import) stay explicitly unsupported.\n"),
 ('families',
  "  if kind<>'QC_ITEM'and not(kind='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i\n"
  "   join cp7_sales_return_correction.links l on l.original_id=i.return_id where i.id=ident))then\n",
  "  if kind not in("+','.join("'"+k+"'"for k in FAMILIES)+")then\n"),
)


def refusal(old,indent,qc):
    """`raise exception '<old>';` keeps its condition and sentence; the names and a JSON list are appended."""
    return (indent+"raise exception '"+old+"';\n",
            indent+"raise exception using message='"+old+"'||"+TEXT+"("+qc+"),detail="+LIST+"("+qc+")::text;\n")


REVERSE_STEPS=(
 ('not-posted',
  "  if h.status<>'POSTED' then raise exception 'Hanya QC POSTED yang dapat direverse'; end if;\n",
  "  if h.status<>'POSTED' then raise exception using message='Hanya QC POSTED yang dapat direverse. QC '||coalesce(h.inspection_number,'')||' berstatus '||h.status||'.'; end if;\n"),
 ('po-finished',
  "  if v_po_status='FINISHED' then raise exception 'PO sudah FINISHED. Reopen/koreksi downstream terlebih dahulu sebelum reversal QC.'; end if;\n",
  "  if v_po_status='FINISHED' then raise exception using message='PO sudah FINISHED. Reopen/koreksi downstream terlebih dahulu sebelum reversal QC.'||"
  +TEXT+"(h.id),detail="+LIST+"(h.id)::text; end if;\n"),
 ('bs',)+refusal('BS hasil QC ini sudah diproses/rework. Batalkan downstream BS terlebih dahulu.','      ','h.id'),
 ('fg',)+refusal('FG hasil QC masih dipakai transaksi downstream aktif. Reverse transaksi downstream terlebih dahulu.','      ','h.id'),
 ('accessory',)+refusal('Hak reimbursement aksesori dari QC ini sudah masuk payroll. Cancel/reverse payroll terlebih dahulu.','      ','h.id'),
)


def named(old):
    return ("          ) then '"+old+"'\n","          ) then '"+old+"'||"+TEXT+"(q.id)\n")


WORKSPACE_STEPS=(
 ('po-finished',
  "          when q.status<>'POSTED' then 'Finalisasi QC bukan POSTED aktif.'\n"
  "          when po.status='FINISHED' then 'PO sudah FINISHED; reopen downstream terlebih dahulu.'\n",
  "          when q.status<>'POSTED' then 'Finalisasi QC bukan POSTED aktif.'\n"
  "          when po.status='FINISHED' then 'PO sudah FINISHED; reopen downstream terlebih dahulu.'||"+TEXT+"(q.id)\n"),
 ('bs',)+named('BS hasil QC sudah diproses; reverse downstream BS terlebih dahulu.'),
 ('fg',)+named('FG hasil QC masih dipakai transaksi downstream aktif.'),
 ('accessory',)+named('Reimbursement aksesori sudah masuk payroll; reverse payroll terlebih dahulu.'),
)
STEPS={SOURCE:SOURCE_STEPS,REVERSE:REVERSE_STEPS,WORKSPACE:WORKSPACE_STEPS}


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW08B_FG_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def case_domains(body):
    """kind -> domain of the reader's own CASE (the families it opens)."""
    found={}
    for kinds,domain in re.findall(r"when kind in\(([^)]*)\)then\s*(?:--[^\n]*\n\s*)*domain:='([A-Z_]+)'",body):
        for kind in re.findall(r"'([A-Z_0-9]+)'",kinds):
            if kind in found:raise ValueError('OW08B_FG_CASE_KIND_TWICE: '+kind)
            found[kind]=domain
    return found


def require_downstream(definition):
    if sha256(definition.encode()).hexdigest()!=DOWNSTREAM_SHA256:raise ValueError('OW08B_FG_DOWNSTREAM_PREDICATE_CHANGED')


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW08B_FG_DELTA_SET_CHANGED')
    result=dict(originals)
    if 'D17-13 2.21' in result[SOURCE]:raise ValueError('OW08B_FG_ALREADY_PATCHED: '+SOURCE)
    for sig in (REVERSE,WORKSPACE):
        if 'cp7_fg_correction_source' in result[sig]:raise ValueError('OW08B_FG_ALREADY_PATCHED: '+sig)
    if 'CP7_KASBON' not in result[SOURCE]or 'cp7_kasbon_source' not in result[SOURCE]:raise ValueError('OW08B_FG_NEEDS_KASBON_READER')
    domains=case_domains(result[SOURCE])
    if {k:domains.get(k)for k in FAMILIES}!=FAMILIES or any(k in domains for k in UNSUPPORTED):
        raise ValueError('OW08B_FG_READER_FAMILIES_CHANGED: '+repr({k:domains.get(k)for k in tuple(FAMILIES)+UNSUPPORTED if k in domains or k in FAMILIES}))
    for sig,steps in STEPS.items():
        for label,old,new in steps:result[sig]=once(result[sig],old,new,sig+':'+label)
    if case_domains(result[SOURCE])!=domains:raise ValueError('OW08B_FG_CASE_CHANGED')
    return result
