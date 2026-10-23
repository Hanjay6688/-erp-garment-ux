"""Counted substitutions of ten installed Native functions (OW-08b, failed wash with an unknown vendor price).

Each anchor must occur exactly once in the predecessor's own pg_get_functiondef text, else the stage refuses. The
predecessor is the qualified OW07 product: erp.period_blockers_v1 already carries OW07's HPP-pool line, and this delta
refuses when that line is missing. Every old path keeps its text and refusal messages; a new path starts only from the
explicit request key price_status='UNKNOWN', from a row this stage registers, or from the new BD action.

  erp.save_laundry_qc_action_v1      POST_FAILED_WASH: optional price_status 'UNKNOWN' (closed payload gate, type check);
                                     no effective rate + that key = no rate, no cost, status PENDING, registered; one rate +
                                     that key = refused (the price is known); more than one rate = the old refusal;
                                     response cost/hpp status says the price is unknown.
  erp.validate_laundry_receipt_line  the facade context that says UNKNOWN stores the attempt without rate and cost
                                     (PENDING); an unknown attempt leaves PENDING only through its recorded price.
  erp.guard_cp6_laundry_receipt_lineage_on_post_v2620
                                     posting: an attempt registered UNKNOWN must post exactly with no rate, no cost,
                                     PENDING; every other attempt keeps the exact zero-output estimate (all other checks stay).
  erp.period_blockers_v1             + cp7_laundry_unknown_wash.blockers_v1 (close waits; state detector).
  erp.rebuild_po_hpp                 an unknown attempt keeps the PO's HPP not final (ESTIMATED).
  erp.bd_lot_laundry_unknown_v1      goods of that PO are "laundry price unknown" (sale guard LAU-DEC04, provisional HPP).
  erp.bd_pending_cost_json_v1        that PO's goods appear in "HPP belum final".
  erp.bd_save_invoice_draft_v1       the attempt is not billed before its price is set (named refusal).
  erp.save_laundry_bd_action_v1      action SET_FAILED_WASH_PRICE (owner/admin + finance.hpp.manage, request replay).
  erp.get_laundry_bd_workspace_v1    + 'failed_wash_prices' (Laundry > Harga & tagihan > Harga belum diketahui).
"""
SAVE_QC='erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'
VALIDATE='erp.validate_laundry_receipt_line()'
LINEAGE='erp.guard_cp6_laundry_receipt_lineage_on_post_v2620()'
BLOCKERS='erp.period_blockers_v1(date,date)'
HPP='erp.rebuild_po_hpp(uuid,text)'
LOT='erp.bd_lot_laundry_unknown_v1(uuid)'
PENDING='erp.bd_pending_cost_json_v1(uuid,boolean)'
DRAFT='erp.bd_save_invoice_draft_v1(jsonb,uuid)'
ROUTER='erp.save_laundry_bd_action_v1(text,jsonb,uuid)'
WORKSPACE='erp.get_laundry_bd_workspace_v1(jsonb)'
SIGNATURES=(SAVE_QC,VALIDATE,LINEAGE,BLOCKERS,HPP,LOT,PENDING,DRAFT,ROUTER,WORKSPACE)
SCHEMA='cp7_laundry_unknown_wash'
CODES=('LAUNDRY_FAILED_WASH_PRICE_UNKNOWN','LAUNDRY_FAILED_WASH_PRICE_STATE_MISMATCH')
ACTION='SET_FAILED_WASH_PRICE'
OW07_MARKER="  return query select * from cp7_hpp_close.blockers_v1(p_through);\n\n"
GRNI="  -- GRNI: owner allows close with an estimate; reported, never blocking.\n"
UNKNOWN="p_payload->>'price_status'='UNKNOWN'"
PLACE='Produksi › Laundry › Harga & tagihan › Harga belum diketahui'

STEPS={
 SAVE_QC:(
  ('payload-key',
   "      array['delivery_id','wash_process_id','custody_outcome','physical_at','reason','lines'],\n"
   "      array['delivery_id','wash_process_id','custody_outcome','physical_at','reason','lines'],\n"
   "      'CP6 POST_FAILED_WASH payload'\n",
   "      array['delivery_id','wash_process_id','custody_outcome','physical_at','reason','lines'],\n"
   "      array['delivery_id','wash_process_id','custody_outcome','physical_at','reason','lines','price_status'],\n"
   "      'CP6 POST_FAILED_WASH payload'\n"),
  ('payload-type',
   "      raise exception 'CP6 POST_FAILED_WASH payload has invalid field types';\n    end if;\n",
   "      raise exception 'CP6 POST_FAILED_WASH payload has invalid field types';\n    end if;\n"
   "    -- OW-08b (LAU-DEC04): optional price_status; its only value says the vendor rate is not known yet.\n"
   "    if p_payload ? 'price_status' and(jsonb_typeof(p_payload->'price_status') is distinct from 'string'\n"
   "       or p_payload->>'price_status'<>'UNKNOWN') then\n"
   "      raise exception 'CP7_FAILED_WASH_PRICE_STATUS: price_status hanya boleh UNKNOWN (tarif vendor belum diketahui)';\n"
   "    end if;\n"),
  ('rate',
   "    if v_rate_count<>1 then\n"
   "      raise exception 'Exactly one authoritative failed-wash rate must be effective for this vendor/process/time; found %',v_rate_count;\n"
   "    end if;\n",
   "    -- OW-08b (LAU-DEC04): no effective rate is recorded as an unknown price only when the request says so (never zero);\n"
   "    -- a known rate is never recorded as unknown, and more than one effective rate stays refused (ambiguity is not unknown).\n"
   "    if v_rate_count=0 and "+UNKNOWN+" then\n"
   "      v_rate:=null;\n"
   "    elsif v_rate_count=1 and "+UNKNOWN+" then\n"
   "      raise exception 'CP7_FAILED_WASH_RATE_KNOWN: tarif vendor untuk proses dan waktu ini sudah ada; catat cuci gagal dengan tarif itu, bukan sebagai harga belum diketahui';\n"
   "    elsif v_rate_count<>1 then\n"
   "      raise exception 'Exactly one authoritative failed-wash rate must be effective for this vendor/process/time; found %',v_rate_count;\n"
   "    end if;\n"),
  ('line-status',
   "      0,0,0,0,v_rate,'ESTIMATED',round(v_total*v_rate,2),\n",
   "      0,0,0,0,v_rate,case when "+UNKNOWN+" then 'PENDING' else 'ESTIMATED' end,round(v_total*v_rate,2),\n"),
  ('register',
   "    insert into erp.laundry_failed_wash_attempts(\n"
   "      id,receipt_id,receipt_line_id,delivery_id,custody_outcome,\n"
   "      qty_attempted_pcs,reason,created_by\n"
   "    ) values(\n"
   "      v_failed_wash_attempt_id,v_receipt_id,v_receipt_line_id,v_delivery.id,\n"
   "      v_custody_outcome,v_total,v_reason,v_actor\n"
   "    );\n",
   "    insert into erp.laundry_failed_wash_attempts(\n"
   "      id,receipt_id,receipt_line_id,delivery_id,custody_outcome,\n"
   "      qty_attempted_pcs,reason,created_by\n"
   "    ) values(\n"
   "      v_failed_wash_attempt_id,v_receipt_id,v_receipt_line_id,v_delivery.id,\n"
   "      v_custody_outcome,v_total,v_reason,v_actor\n"
   "    );\n"
   "    -- OW-08b: the unknown price is registered with the attempt (who, when, why); owner/admin sets it later, once.\n"
   "    if "+UNKNOWN+" then\n"
   "      insert into cp7_laundry_unknown_wash.prices_v1(attempt_id,receipt_line_id,po_id,recorded_by,recorded_reason)\n"
   "      values(v_failed_wash_attempt_id,v_receipt_line_id,v_delivery.po_id,v_actor,v_reason);\n"
   "    end if;\n"),
  ('response-cost',
   "      'cost_status','ESTIMATED_UNBILLED',\n",
   "      'cost_status',case when "+UNKNOWN+" then 'PRICE_UNKNOWN' else 'ESTIMATED_UNBILLED' end,\n"),
  ('response-hpp',
   "      'hpp_effect','FAILED_WASH_COST_REBUILT_WITHOUT_GOOD_BS_OR_FG'\n    );\n",
   "      'hpp_effect',case when "+UNKNOWN+" then 'FAILED_WASH_COST_UNKNOWN_HPP_NOT_FINAL'\n"
   "        else 'FAILED_WASH_COST_REBUILT_WITHOUT_GOOD_BS_OR_FG' end\n    );\n"),
 ),
 VALIDATE:(
  ('unknown-context',
   "  if v_failed_context_count>0 then\n    if v_failed_context_count<>1 or v_failed_qty<=0\n",
   "  if v_failed_context_count>0 then\n"
   "    -- OW-08b (LAU-DEC04): the facade request that says the vendor rate is not known yet stores the attempt with no rate,\n"
   "    -- no cost and cost status PENDING (never zero); every other zero-output rule of the attempt stays.\n"
   "    if v_failed_context_count=1 and new.actual_rate_snapshot is null and exists(\n"
   "      select 1 from erp.cp6_laundry_qc_execution_context c\n"
   "      where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current()\n"
   "        and c.actor_key=erp._idempotency_actor_key() and c.action='POST_FAILED_WASH'\n"
   "        and c.permission_key='production.laundry.post' and erp.has_permission(c.permission_key)\n"
   "        and (c.payload->>'delivery_id')::uuid=v_receipt_delivery\n"
   "        and (c.payload->>'wash_process_id')::uuid=new.actual_wash_process_id\n"
   "        and c.payload->>'price_status'='UNKNOWN') then\n"
   "      if v_failed_qty<=0 or new.qty_good_received<>0 or new.qty_bs_laundry<>0\n"
   "         or new.qty_stuck<>0 or new.qty_missing<>0 or new.actual_cost_status<>'PENDING' then\n"
   "        raise exception 'Paid failed-wash cost requires one exact zero-output facade context';\n"
   "      end if;\n"
   "      new.actual_cost:=null;\n"
   "      return new;\n"
   "    end if;\n"
   "    if v_failed_context_count<>1 or v_failed_qty<=0\n"),
  ('unknown-leaves-only-priced',
   "  if v_existing_failed_qty is not null then\n    if new.qty_good_received<>0 or new.qty_bs_laundry<>0\n",
   "  -- OW-08b: an attempt recorded with an unknown price leaves PENDING only through its recorded price\n"
   "  -- (cp7_laundry_unknown_wash.prices_v1, set once by owner/admin); it is never billed or valued before that.\n"
   "  if v_existing_failed_qty is not null and tg_op='UPDATE' and old.actual_cost_status='PENDING' and old.actual_rate_snapshot is null\n"
   "     and not exists(select 1 from cp7_laundry_unknown_wash.prices_v1 p\n"
   "       where p.receipt_line_id=new.id and p.price_status<>'UNKNOWN' and p.rate_per_pcs=new.actual_rate_snapshot\n"
   "         and new.actual_cost_status='ESTIMATED') then\n"
   "    raise exception 'CP7_FAILED_WASH_PRICE_UNKNOWN: harga cuci gagal ini belum diketahui; isi dulu di "+PLACE+"';\n"
   "  end if;\n"
   "  if v_existing_failed_qty is not null then\n    if new.qty_good_received<>0 or new.qty_bs_laundry<>0\n"),
 ),
 LINEAGE:(
  ('unknown-shape',
   "        or l.actual_wash_process_id is null\n"
   "        or l.actual_rate_snapshot is null or l.actual_rate_snapshot<0\n"
   "        or l.actual_cost_status<>'ESTIMATED'\n"
   "        or l.actual_cost is distinct from round(r.qty_attempted_pcs*l.actual_rate_snapshot,2)\n"
   "      )\n",
   "        or l.actual_wash_process_id is null\n"
   "        -- OW-08b (LAU-DEC04): an attempt this stage registered with an unknown vendor price posts with exactly no rate,\n"
   "        -- no cost and status PENDING (never zero); every other attempt keeps the exact zero-output estimate below.\n"
   "        or (case when exists(select 1 from cp7_laundry_unknown_wash.prices_v1 ow\n"
   "            where ow.attempt_id=r.id and ow.receipt_line_id=l.id and ow.price_status='UNKNOWN')\n"
   "          then l.actual_rate_snapshot is not null or l.actual_cost is not null or l.actual_cost_status<>'PENDING'\n"
   "          else l.actual_rate_snapshot is null or l.actual_rate_snapshot<0\n"
   "        or l.actual_cost_status<>'ESTIMATED'\n"
   "        or l.actual_cost is distinct from round(r.qty_attempted_pcs*l.actual_rate_snapshot,2) end)\n"
   "      )\n"),
 ),
 BLOCKERS:(
  ('close',
   OW07_MARKER+GRNI,
   OW07_MARKER+
   "  -- OW-08b (cp7_laundry_unknown_wash): a failed wash recorded with an unknown vendor price (LAU-DEC04: never zero, HPP not\n"
   "  -- final, close waits for the price) and the state detector of those attempts.\n"
   "  return query select * from cp7_laundry_unknown_wash.blockers_v1(p_through);\n\n"+GRNI),
 ),
 HPP:(
  ('pending',
   "    where ld.po_id=p_po_id and rl.actual_cost_status='ESTIMATED' and not erp.bd_receipt_invoiced_v1(rl.id)\n  );\n",
   "    where ld.po_id=p_po_id and rl.actual_cost_status='ESTIMATED' and not erp.bd_receipt_invoiced_v1(rl.id)\n  );\n"
   "  -- OW-08b (LAU-DEC04): a failed wash whose vendor price is still unknown keeps this PO's HPP not final.\n"
   "  v_pending:=v_pending or cp7_laundry_unknown_wash.po_pending_v1(p_po_id);\n"),
 ),
 LOT:(
  ('po-unknown',
   "erp.bd_delivery_line_price_unknown_v1(dl.id)))\n",
   "erp.bd_delivery_line_price_unknown_v1(dl.id)))\n"
   "    -- OW-08b (LAU-DEC04): goods of a PO with a failed wash whose vendor price is still unknown.\n"
   "    or exists(select 1 from erp.fg_lots ow_lot where ow_lot.id=p_lot and cp7_laundry_unknown_wash.po_pending_v1(ow_lot.po_id))\n"),
 ),
 PENDING:(
  ('po-unknown',
   "    where d.status not in('DRAFT','REVERSED') and (p_vendor is null or d.vendor_id=p_vendor) and erp.bd_delivery_line_price_unknown_v1(dl.id)),\n",
   "    where d.status not in('DRAFT','REVERSED') and (p_vendor is null or d.vendor_id=p_vendor) and erp.bd_delivery_line_price_unknown_v1(dl.id)\n"
   "    -- OW-08b: the PO of a failed wash whose vendor price is still unknown.\n"
   "    union select u.po_id from cp7_laundry_unknown_wash.unknown_v1() u where p_vendor is null or u.vendor_id=p_vendor),\n"),
 ),
 DRAFT:(
  ('not-billed',
   "    if v_rl.vendor_id<>v_vendor then raise exception 'BD_INVOICE_VENDOR: baris penerimaan milik vendor lain';end if;\n",
   "    if v_rl.vendor_id<>v_vendor then raise exception 'BD_INVOICE_VENDOR: baris penerimaan milik vendor lain';end if;\n"
   "    -- OW-08b: a failed wash whose vendor price is still unknown is not billed before its price is set.\n"
   "    if exists(select 1 from cp7_laundry_unknown_wash.unknown_v1() u where u.receipt_line_id=v_rl.id) then\n"
   "      raise exception 'CP7_FAILED_WASH_PRICE_UNKNOWN: harga cuci gagal pada baris penerimaan ini belum diketahui; isi dulu di "+PLACE+"';end if;\n"),
 ),
 ROUTER:(
  ('action',
   "    'APPLY_CLAIM_CREDIT','PAY_VENDOR_DOCUMENT','REVERSE_VENDOR_SETTLEMENT') then\n",
   "    'APPLY_CLAIM_CREDIT','PAY_VENDOR_DOCUMENT','REVERSE_VENDOR_SETTLEMENT','SET_FAILED_WASH_PRICE') then\n"),
  ('dispatch',
   "    when 'SET_CHARGE_PRICE' then erp.bd_set_charge_price_v1(p_payload,p_client_request_id)\n",
   "    when 'SET_CHARGE_PRICE' then erp.bd_set_charge_price_v1(p_payload,p_client_request_id)\n"
   "    -- OW-08b: the price of a failed wash recorded with an unknown vendor price (owner/admin + finance.hpp.manage, as above).\n"
   "    when 'SET_FAILED_WASH_PRICE' then cp7_laundry_unknown_wash.set_price_v1(p_payload,p_client_request_id)\n"),
 ),
 WORKSPACE:(
  ('list',
   "    'pending_cost',erp.bd_pending_cost_json_v1(v_vendor,v_money));\n",
   "    'pending_cost',erp.bd_pending_cost_json_v1(v_vendor,v_money),\n"
   "    -- OW-08b: failed washes recorded with an unknown vendor price (waiting first), and their price history.\n"
   "    'failed_wash_prices',cp7_laundry_unknown_wash.workspace_v1(v_vendor,v_money));\n"),
 ),
}


def once(body,old,new,label):
    if body.count(old)!=1:
        raise ValueError('OW08B_WASH_PREDECESSOR_SOURCE_CHANGED: '+label+' (found '+str(body.count(old))+')')
    return body.replace(old,new,1)


def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('OW08B_WASH_NATIVE_DELTA_SET_CHANGED')
    result=dict(originals)
    for sig in SIGNATURES:
        if SCHEMA in result[sig] or ACTION in result[sig]:raise ValueError('OW08B_WASH_ALREADY_PATCHED: '+sig)
    if result[BLOCKERS].count(OW07_MARKER)!=1:raise ValueError('OW08B_WASH_NEEDS_OW07_BLOCKERS')
    if "'price_status'" in result[SAVE_QC]:raise ValueError('OW08B_WASH_PAYLOAD_KEY_ALREADY_PRESENT')
    for sig in SIGNATURES:
        for label,old,new in STEPS[sig]:result[sig]=once(result[sig],old,new,sig+':'+label)
    return result
