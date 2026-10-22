"""Counted substitutions of the installed transaction-source reader (OW-08b, kasbon).

cp7_transaction_source.resolve(jsonb), as left by the qualified OW06 stage, learns one more source family: CP7_KASBON
(and, through the existing journal-inverse walk, its cancellation). It opens domain KASBON on Payroll & Kasbon with
the kasbon focused in its Mandor's list. Every other family, check and message stays byte-for-byte.
"""
SOURCE='cp7_transaction_source.resolve(jsonb)'
SIGNATURES=(SOURCE,)
STEPS=(
 ('domain',
  "  domain:='CUTTING';route:='mandor-wip';permission:='production.distribution.view';\n else\n",
  "  domain:='CUTTING';route:='mandor-wip';permission:='production.distribution.view';\n"
  " when kind='CP7_KASBON'then\n"
  "  -- OW-08b: a kasbon journal opens the kasbon on Payroll & Kasbon (the panel is OWNER/ADMIN only).\n"
  "  domain:='KASBON';route:='finance-payroll';permission:='finance.payroll.view';\n else\n"),
 ('rights',
  "  or(domain='MISC_FINANCE'and(not erp.has_permission('finance.cash.view')or a->'profile'->>'role_code'not in('OWNER','ADMIN')))\n",
  "  or(domain='MISC_FINANCE'and(not erp.has_permission('finance.cash.view')or a->'profile'->>'role_code'not in('OWNER','ADMIN')))\n"
  "  or(domain='KASBON'and a->'profile'->>'role_code'not in('OWNER','ADMIN'))\n"),
 ('document',
  " when'LAUNDRY'then select to_jsonb(h),h.delivery_number into doc,label from erp.laundry_deliveries h where h.id=parent_id;\n",
  " when'LAUNDRY'then select to_jsonb(h),h.delivery_number into doc,label from erp.laundry_deliveries h where h.id=parent_id;\n"
  " when'KASBON'then select k,k->>'number' into doc,label from cp7_kasbon_source.document_v1(parent_id)k;\n"),
 ('focus',
  " if domain='CUTTING'then\n",
  " if domain='KASBON'then\n"
  "  focus:=jsonb_build_object('kind','KASBON','id',parent_id,'parent_id',doc->>'contractor_id');\n"
  " end if;\n"
  " if domain='CUTTING'then\n"),
 ('offset',
  "  when'REWORK_ORDER'then\n",
  "  when'KASBON'then\n"
  "   -- The kasbon panel lists every kasbon of one Mandor on one page.\n"
  "   focus_offset:=0;\n"
  "  when'REWORK_ORDER'then\n"),
)


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW08B_KASBON_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW08B_KASBON_DELTA_SET_CHANGED')
    body=originals[SOURCE]
    if 'CP7_KASBON' in body or 'cp7_kasbon_source' in body:raise ValueError('OW08B_KASBON_ALREADY_PATCHED')
    if 'CP7_SUPPLIER_TRANSFER' not in body:raise ValueError('OW08B_KASBON_NEEDS_OW06_READER')
    for label,old,new in STEPS:body=once(body,old,new,label)
    return {SOURCE:body}
