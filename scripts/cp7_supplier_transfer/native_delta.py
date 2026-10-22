"""Narrow, counted substitutions of the verified installed predecessor bodies.

The Native per-receipt capacity/funding/date/status checks remain byte-for-byte.
The parent owns one real journal; individual allocations cannot be corrected.
"""
POST='erp.post_supplier_payment(uuid)'
REVERSE='erp.reverse_supplier_payment(uuid,text)'
JOURNAL='erp.reverse_journal(uuid,text)'
DETAIL='cp7_invoice.payment_detail(uuid,jsonb)'
INDIVIDUAL='cp7_invoice.reverse_payment_locked(jsonb)'
CORRECT='cp7_supplier_payment_correction.apply(jsonb,uuid)'
TRUTH='erp.run_v267_financial_truth_checks()'
BLOCKERS='cp7_receipt_fix.blockers(uuid)'
SOURCE='cp7_transaction_source.resolve(jsonb)'
SIGNATURES=(POST,REVERSE,JOURNAL,DETAIL,INDIVIDUAL,CORRECT,TRUTH,BLOCKERS,SOURCE)


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW06_PREDECESSOR_SOURCE_CHANGED: '+label)
    return body.replace(old,new,1)


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW06_NATIVE_DELTA_SET_CHANGED')
    result=dict(originals)
    post="""  perform erp.post_journal('SUPPLIER_PAYMENT',p.id,erp._cp3_business_date(p.payment_date),'Material supplier payment',jsonb_build_array(
    jsonb_build_object('mapping_key','AP_SUPPLIER','debit',p.amount,'credit',0),jsonb_build_object('account_id',v_cash,'debit',0,'credit',p.amount)));
"""
    result[POST]=once(result[POST],post,
        '  if not cp7_supplier_transfer.delegate_post_v1(p.id,v_cash)then\n'+post+'  end if;\n',POST)
    reverse="""  select id into v_journal from erp.journal_entries
  where source_type='SUPPLIER_PAYMENT' and source_id=p.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_journal is null then raise exception 'Jurnal pembayaran supplier tidak ditemukan; reversal dibatalkan agar kas/hutang tidak rusak'; end if;

  if erp.initial_prepayment_account_v1(p.id) is not null then perform erp._cp3_r4_reverse_journal_internal(v_journal,p_reason);else perform erp.reverse_journal(v_journal,p_reason);end if;
"""
    result[REVERSE]=once(result[REVERSE],reverse,
        '  if not cp7_supplier_transfer.delegate_reverse_v1(p.id,p_reason)then\n'+reverse+'  end if;\n',REVERSE)
    anchor="  if v_source_type is null then raise exception 'Journal entry not found'; end if;\n"
    result[JOURNAL]=once(result[JOURNAL],anchor,anchor+"""  if v_source_type='CP7_SUPPLIER_TRANSFER'and not cp7_supplier_transfer.context_allows_v1(
    (select source_id from erp.journal_entries where id=p_journal_entry_id),'REVERSE')then
    raise exception 'CP7_SUPPLIER_TRANSFER_USE_PARENT: balik Transfer supplier melalui dokumen asal.';end if;
  if v_source_type in('CP7_SUPPLIER_TRANSFER_TIME_NEUTRAL','CP7_SUPPLIER_TRANSFER_EFFECTIVE')then
    raise exception 'CP7_SUPPLIER_TRANSFER_HISTORY_IMMUTABLE';end if;
""",JOURNAL)
    anchor=' perform cp7_invoice.payment_access();\n'
    result[DETAIL]=once(result[DETAIL],anchor,anchor+" r:=cp7_supplier_transfer.child_detail_v1(p_payment,p_ap);\n if r is not null then return r;end if;\n",DETAIL)
    anchor=' a:=cp7_invoice.payment_access();\n'
    result[INDIVIDUAL]=once(result[INDIVIDUAL],anchor,anchor+" perform cp7_supplier_transfer.deny_individual_v1((p_payload->>'payment_id')::uuid);\n",INDIVIDUAL)
    anchor=' a:=cp7_supplier_payment_correction.access_now();perform cp7_supplier_payment_correction.validate(p);\n'
    result[CORRECT]=once(result[CORRECT],anchor,anchor+" perform cp7_supplier_transfer.deny_individual_v1((p->>'payment_id')::uuid);\n",CORRECT)
    # Every original payment is still checked: standalone rows retain their old
    # oracle; grouped allocations are covered by the aggregate x row AND the
    # exact child/parent/link detector below. No critical check is discarded.
    anchor="    from erp.supplier_payments p\n    union all\n    select s.id,s.status,s.amount,s.cash_account_id,'OPENING_SUBLEDGER_SETTLEMENT',"
    replacement="""    from erp.supplier_payments p where not exists(select 1 from cp7_supplier_transfer.allocations_v1 a where a.payment_id=p.id)
    union all
    select t.id,t.status,t.amount,t.cash_account_id,'CP7_SUPPLIER_TRANSFER',
      (select erp.account_id('AP_SUPPLIER')),false,null::uuid,null::uuid,null::uuid
    from cp7_supplier_transfer.transfers_v1 t
    union all
    select s.id,s.status,s.amount,s.cash_account_id,'OPENING_SUBLEDGER_SETTLEMENT',"""
    result[TRUTH]=once(result[TRUTH],anchor,replacement,TRUTH+':money-source')
    anchor="    (j.source_type='SUPPLIER_PAYMENT' and not exists(select 1 from erp.supplier_payments p where p.id=j.source_id))\n"
    result[TRUTH]=once(result[TRUTH],anchor,anchor+"""    or(j.source_type='CP7_SUPPLIER_TRANSFER'and not exists(select 1 from cp7_supplier_transfer.transfers_v1 t where t.id=j.source_id and t.journal_id=j.id))
    or(j.source_type in('CP7_SUPPLIER_TRANSFER_TIME_NEUTRAL','CP7_SUPPLIER_TRANSFER_EFFECTIVE')and not exists(
      select 1 from cp7_supplier_transfer.corrections_v1 c where c.original_id=j.source_id and j.id=case when j.source_type='CP7_SUPPLIER_TRANSFER_TIME_NEUTRAL'then c.time_neutral_id else c.effective_inverse_id end))
""",TRUTH+':orphan')
    # Insert additional named detectors before the original final semicolon.
    tail=' UNION ALL SELECT * FROM erp.pocket_fabric_checks_v1();'
    checks="""
  union all
  select 'OW06_SUPPLIER_TRANSFER_FACTS','CRITICAL',count(*)::bigint,
    'A supplier transfer must retain every exact Native allocation and its one cash journal'
  from cp7_supplier_transfer.transfers_v1 t where not cp7_supplier_transfer.valid_transfer_v1(t.id)
  union all
  select 'OW06_SUPPLIER_TRANSFER_CORRECTION','CRITICAL',count(*)::bigint,
    'Supplier transfer successors must retain exact lineage and economic-date correction journals'
  from cp7_supplier_transfer.corrections_v1 c where not cp7_supplier_transfer.valid_correction_v1(c.original_id)
"""
    result[TRUTH]=once(result[TRUTH],tail,tail[:-1]+checks+';',TRUTH+':final-detectors')
    anchor="   union all select 'CP7_RECEIPT_FIX_OPENING_IMPORT_USE_IMPORT_WORKFLOW','OPENING_IMPORT',h.receipt_number from erp.initial_import_receipt_headers h\n"
    result[BLOCKERS]=once(result[BLOCKERS],anchor,"""   union all select 'CP7_SUPPLIER_TRANSFER_USE_PARENT','SUPPLIER_TRANSFER',t.number
    from cp7_supplier_transfer.allocations_v1 a join cp7_supplier_transfer.transfers_v1 t on t.id=a.transfer_id
    where a.purchase_id=p_purchase and t.status='POSTED'
"""+anchor,BLOCKERS)
    anchor=' end loop;\n -- Economic-date entries belong to the exact ordinary payment correction.\n'
    result[SOURCE]=once(result[SOURCE],anchor,""" end loop;
 if kind in('CP7_SUPPLIER_TRANSFER','CP7_SUPPLIER_TRANSFER_TIME_NEUTRAL','CP7_SUPPLIER_TRANSFER_EFFECTIVE')then
  ident:=cp7_supplier_transfer.source_payment_v1(ident);kind:='SUPPLIER_PAYMENT';
 end if;
 -- Economic-date entries belong to the exact ordinary payment correction.
""",SOURCE)
    return result
