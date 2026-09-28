"""Vendor authority and optional details; invoices settle actual source cost."""
from cp6_bc_build import last_definition, substitute

REPLACED = ['erp.bd_priced_line_json_v1(uuid)', 'erp.bd_compute_pricing_v1(jsonb,jsonb)',
 'erp.bd_attach_delivery_pricing_v1(uuid)', 'erp.bd_refresh_size_estimates_v1(uuid)',
 'erp.bd_line_complete_v1(uuid)', 'erp.bd_delivery_line_price_unknown_v1(uuid)',
 'erp.bd_post_invoice_v1(jsonb,uuid)', 'erp.bd_set_charge_price_v1(jsonb,uuid)',
 'erp.period_blockers_v1(date,date)']

def changed(bd):
    be = bd.with_name('cp6_be_t1_family.sql')
    # Preserve BD vendor selection and explicit policy guards; no SKU override.
    compute = substitute(last_definition(bd, 'bd_compute_pricing_v1'), [
      ("  if v_unit='BATCH' then", """  if p_pricing ? 'deferred' then
    perform erp._cp3_assert_closed_json_object(p_pricing,array['deferred'],array['deferred'],'deferred pricing');
    if p_pricing->'deferred' is distinct from 'true'::jsonb then raise exception 'BD_PRICING_INVALID: deferred harus true';end if;
    v_mode:='PENDING';v_unit:='PCS';
  elsif p_pricing ? 'components' then
    v_mode:='COMPONENTS';v_unit:='PCS';
    if p_pricing->'components'='[]'::jsonb then
      perform erp._cp3_assert_closed_json_object(p_pricing,array['components'],array['components'],'deferred components');
      v_mode:='PENDING';
    end if;
  elsif p_pricing ? 'package_id' then v_mode:='PACKAGE';v_unit:='PCS';
  elsif p_pricing='{}'::jsonb and v_mode in('PACKAGE','COMPONENTS') then v_mode:='PENDING';v_unit:='PCS';
  end if;
  if v_mode='PENDING' then
    -- No synthetic charge. Known subtotal is zero; unknown price stays NULL.
    v_complete:=false;
  elsif v_unit='BATCH' then"""),
      ("  if t.minimum_charge is not null then", "  if t.minimum_charge is not null and v_mode<>'PENDING' then"),
      ("jsonb_build_object('mode',v_mode,'unit'", "jsonb_build_object('mode',case when v_mode='PENDING' then 'COMPONENTS' else v_mode end,'deferred',v_mode='PENDING','unit'")
    ], 'BF vendor pricing or deferred details')
    attach = substitute(last_definition(bd, 'bd_attach_delivery_pricing_v1'), [
      ('  perform erp.bd_refresh_size_estimates_v1(l.id);', """  insert into erp.bf_laundry_delivery_sources_v1(delivery_line_id,details_pending)
    values(l.id,coalesce((p->>'deferred')::boolean,false));
  perform erp.bd_refresh_size_estimates_v1(l.id);""")
    ], 'BF pending details without fabricated charges')
    refresh = substitute(last_definition(bd, 'bd_refresh_size_estimates_v1'), [
      ('bool_and(sh.amount is not null)', 'count(sh.charge_line_id)>0 and bool_and(sh.amount is not null)'),
      ('s join erp.bd_laundry_charge_shares_v1 sh', 's left join erp.bd_laundry_charge_shares_v1 sh')
    ], 'BF pending size allocations')
    complete = substitute(last_definition(bd, 'bd_line_complete_v1'), [
      (',true) $function$;', ',true) or erp.bf_delivery_invoiced_v1(p_delivery_line) $function$;')
    ], 'BF invoice final cost without quote')
    unknown = substitute(last_definition(bd, 'bd_delivery_line_price_unknown_v1'), [
      ('select dl.estimated_rate_snapshot is null or not erp.bd_line_complete_v1(dl.id)',
       'select not erp.bf_delivery_invoiced_v1(dl.id) and (dl.estimated_rate_snapshot is null or not erp.bd_line_complete_v1(dl.id))')
    ], 'BF invoice clears current unknown cost')
    invoice = substitute(last_definition(be, 'bd_post_invoice_v1'), [
      ("    if not erp.bd_line_complete_v1(l.delivery_line_id) then\n      raise exception 'BD_PRICE_UNKNOWN_SET_FIRST: harga komponen kiriman ini belum diketahui; isi harganya sebelum menagih';end if;",
       """    -- Unknown estimates are billed directly; actual cost follows the goods.
    if not erp.bd_line_complete_v1(l.delivery_line_id) and v_dec06->>'variance_mode'<>'PRODUCT_COST' then
      raise exception 'BF_UNKNOWN_INVOICE_PRODUCT_COST: biaya yang belum diketahui harus mengikuti biaya produk';end if;""")
    ], 'BF kontra bon settles pending source cost')
    price = substitute(last_definition(bd, 'bd_set_charge_price_v1'), [
      ('  select * into ch from erp.bd_laundry_charge_lines_v1', """  perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||l.cutting_group_id::text,0))
    from erp.bd_laundry_charge_lines_v1 c join erp.laundry_delivery_lines l on l.id=c.delivery_line_id
    where c.id=erp.bd_uuid_v1(p_payload,'charge_line_id',true);
  select * into ch from erp.bd_laundry_charge_lines_v1"""),
      ("  if v_status not in('KNOWN','FREE','WAIVED')", """  if exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 i on i.id=x.invoice_id
    join erp.laundry_receipt_lines receipt on receipt.id=x.receipt_line_id where receipt.delivery_line_id=ch.delivery_line_id and i.status='POSTED') then
    raise exception 'BD_ALREADY_INVOICED: biaya sudah berasal dari kontra bon; gunakan dokumen koreksi';end if;
  if v_status not in('KNOWN','FREE','WAIVED')""")
    ], 'BF immutable quote after any billing')
    blocker = substitute(last_definition(be, 'period_blockers_v1'), [
      ("where not bp.total_complete and ld.status", "where not bp.total_complete and not erp.bf_delivery_invoiced_v1(bp.delivery_line_id,p_through) and ld.status")
    ], 'BF dated invoice completeness')
    reader = substitute(last_definition(bd, 'bd_priced_line_json_v1'), [
      ("'mode',p.pricing_mode", "'mode',case when exists(select 1 from erp.bf_laundry_delivery_sources_v1 b where b.delivery_line_id=p.delivery_line_id and b.details_pending) then 'PENDING' else p.pricing_mode end"),
      ("'total_complete',p.total_complete", "'total_complete',p.total_complete,'cost_invoiced',erp.bf_delivery_invoiced_v1(p.delivery_line_id),'has_invoice',exists(select 1 from erp.bd_laundry_invoice_lines_v1 x join erp.bd_laundry_invoices_v1 i on i.id=x.invoice_id join erp.laundry_receipt_lines r on r.id=x.receipt_line_id where r.delivery_line_id=p.delivery_line_id and i.status='POSTED')")
    ], 'BF invoice completion separate from quote')
    return [compute, attach, refresh, complete, unknown, invoice, price, blocker, reader]
