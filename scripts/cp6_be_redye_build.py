"""Counted predecessor changes for the real BE redye service source of BD invoices."""
from pathlib import Path
from cp6_bc_build import last_definition,substitute
from cp6_be_pocket_build import filter_native
ROOT=Path(__file__).resolve().parents[1];BD=ROOT/'supabase/dev/cp6_bd_t1_family.sql'
REPLACED=['erp.get_laundry_bd_workspace_v1(jsonb)','erp.save_laundry_bd_action_v1(text,jsonb,uuid)','erp.bd_save_invoice_draft_v1(jsonb,uuid)','erp.bd_check_correction_sources_v1(uuid)',
 'erp.bd_invoice_lines_json_v1(uuid)','erp.bd_post_invoice_v1(jsonb,uuid)','erp.bd_invoice_resync_v1(uuid,date)',
 'erp.bd_reverse_invoice_v1(jsonb,uuid)','erp.desired_laundry_accrual(uuid)','erp.rebuild_po_hpp(uuid,text)',
 'erp.bd_lot_laundry_unknown_v1(uuid)','erp.cp6_lot_rework_cost_v2620c(uuid)','erp.period_blockers_v1(date,date)']
def patched(name,subs):return substitute(last_definition(BD,name),subs,'BE redye '+name)
def build(old_definition):
    draft=patched('bd_save_invoice_draft_v1',[
      ('v_origins uuid[];', 'v_redye erp.be_redye_services_v1%rowtype;v_origins uuid[];'),
      ("or b.opening_uninvoiced_id=erp.bd_uuid_v1(x,'opening_uninvoiced_id',false))", "or b.opening_uninvoiced_id=erp.bd_uuid_v1(x,'opening_uninvoiced_id',false) or b.rework_service_id=erp.bd_uuid_v1(x,'rework_service_id',false))"),
      ("array['line_kind','receipt_line_id','opening_uninvoiced_id','category','qty','amount','note']", "array['line_kind','receipt_line_id','opening_uninvoiced_id','rework_service_id','category','qty','amount','note']"),
      ("if (v_x ? 'receipt_line_id')=(v_x ? 'opening_uninvoiced_id') then", "if (v_x ? 'receipt_line_id')::int+(v_x ? 'opening_uninvoiced_id')::int+(v_x ? 'rework_service_id')::int<>1 then"),
      ("    if v_x ? 'opening_uninvoiced_id' then", """    if v_x ? 'rework_service_id' then
      select * into v_redye from erp.be_redye_services_v1 where id=erp.bd_uuid_v1(v_x,'rework_service_id',true);
      if v_redye.id is null then raise exception 'BD_INVOICE_SOURCE: jasa celup ulang tidak ditemukan';end if;
      if v_redye.vendor_id<>v_vendor then raise exception 'BD_INVOICE_VENDOR';end if;
      insert into erp.bd_laundry_invoice_lines_v1(invoice_id,line_no,line_kind,rework_service_id,category,qty,amount,note,po_id)
      values(i.id,v_no,v_kind,v_redye.id,v_x->>'category',v_qty,v_amount,nullif(btrim(coalesce(v_x->>'note','')),''),v_redye.po_id);
      continue;
    end if;
    if v_x ? 'opening_uninvoiced_id' then""")])
    correction=patched('bd_check_correction_sources_v1',[("b.opening_uninvoiced_id=l.opening_uninvoiced_id)","b.opening_uninvoiced_id=l.opening_uninvoiced_id or b.rework_service_id=l.rework_service_id)")])
    lines=patched('bd_invoice_lines_json_v1',[("'opening_uninvoiced_id',l.opening_uninvoiced_id,", "'opening_uninvoiced_id',l.opening_uninvoiced_id,'rework_service_id',l.rework_service_id,")])
    post=patched('bd_post_invoice_v1',[
      ("  -- Lock the sources in a fixed order", "  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));\n  perform 1 from erp.be_redye_services_v1 where id in(select rework_service_id from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id) order by id for update;\n  -- Lock the sources in a fixed order"),
      ("    -- ALL-W05: an opening record", "    if l.rework_service_id is not null then perform erp.be_invoice_redye_line_v1(l.id,v_billable,v_dec06);continue;end if;\n    -- ALL-W05: an opening record")])
    resync=patched('bd_invoice_resync_v1',[
      ("declare v_po uuid;", "declare v_po uuid;v_service uuid;"),
      ("begin\n", "begin\n  for v_service in select distinct rework_service_id from erp.bd_laundry_invoice_lines_v1 where invoice_id=p_invoice and rework_service_id is not null order by 1 loop\n    perform erp.be_redye_resync_v1(v_service,p_date);\n  end loop;\n")])
    reverse=patched('bd_reverse_invoice_v1',[
      ("  -- A later invoice", "  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));\n  perform 1 from erp.be_redye_services_v1 where id in(select rework_service_id from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id) order by id for update;\n  -- A later invoice"),
      ("or x.opening_uninvoiced_id=any(v_open_ids))", "or x.opening_uninvoiced_id=any(v_open_ids) or x.rework_service_id in(select rework_service_id from erp.bd_laundry_invoice_lines_v1 where invoice_id=i.id))")])
    accrual=patched('desired_laundry_accrual',[("select a.amount+f.amount", "select a.amount+f.amount+erp.be_redye_accrual_v1(p_po_id)")])
    rebuild=patched('rebuild_po_hpp',[
      ("  select coalesce(sum(adjustment_amount),0),", "  v_rework:=v_rework+erp.be_redye_po_cost_v1(p_po_id);\n  v_pending:=v_pending or exists(select 1 from erp.be_redye_services_v1 bs join erp.rework_orders br on br.id=bs.id\n    where bs.po_id=p_po_id and br.status<>'CANCELLED' and erp.be_redye_accrual_v1(p_po_id)<>0)\n    or exists(select 1 from erp.be_redye_services_v1 bs join erp.rework_orders br on br.id=bs.id where bs.po_id=p_po_id and br.status<>'CANCELLED' and erp.be_redye_rate_v1(bs.id) is null);\n  select coalesce(sum(adjustment_amount),0),")])
    rebuild=filter_native(rebuild)
    C=ROOT/'supabase/migrations/20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.sql'
    cost=old_definition(C,'cp6_lot_rework_cost_v2620c')
    cost=substitute(cost,[("sum(rcl.amount_payable::numeric*fl.initial_qty_pcs/nullif(ro.qty_sent,0)),0)::numeric", "sum(rcl.amount_payable::numeric*fl.initial_qty_pcs/nullif(ro.qty_sent,0)),0)::numeric\n    +coalesce((select erp.be_redye_cost_v1(rs.id)*rr.qty_good_returned/nullif(rr.qty_sent,0) from erp.be_redye_services_v1 rs join erp.rework_orders rr on rr.id=rs.id where rr.good_fg_lot_id=p_lot_id and rr.status<>'CANCELLED' and rr.cost_posted),0)")],'BE exact redye good lot')
    blocker=patched('period_blockers_v1',[("  -- LAUNDRY: a delivery rate", """  return query
  select 'LAUNDRY'::text,'BE_REDYE_PRICE_UNKNOWN'::text,'POLICY'::text,'AS_OF'::text,erp._cp3_business_date(s.sent_at),
    jsonb_build_object('rework_service_id',s.id,'vendor_id',s.vendor_id,'po_id',s.po_id),
    'Harga jasa celup ulang belum diketahui; isi harga sumber sebelum tutup buku.'::text
  from erp.be_redye_services_v1 s join erp.rework_orders r on r.id=s.id
  where r.status<>'CANCELLED' and s.sent_at<v_end and erp.be_redye_rate_v1(s.id) is null;

  -- LAUNDRY: a delivery rate""")])
    unknown=patched('bd_lot_laundry_unknown_v1',[("  select coalesce(","  select exists(select 1 from erp.fg_lots be_lot join erp.be_redye_services_v1 be_s on be_s.po_id=be_lot.po_id join erp.rework_orders be_r on be_r.id=be_s.id where be_lot.id=p_lot and be_r.status<>'CANCELLED' and erp.be_redye_rate_v1(be_s.id) is null) or coalesce(")])
    workspace=patched('get_laundry_bd_workspace_v1',[("    'filters',coalesce(p_filters", "    'redye_services',erp.be_redye_workspace_v1(v_vendor,v_money),\n    'filters',coalesce(p_filters")])
    router=patched('save_laundry_bd_action_v1',[
      ("if v_action not in('SET_POLICY'", "if v_action not in('SET_REDYE_PRICE','SET_POLICY'"),
      ("  perform pg_advisory_xact_lock(hashtextextended('BDREQ:'", "  if v_action='SET_REDYE_PRICE' then perform erp.require_owner_admin();perform erp.require_permission('finance.hpp.manage');perform erp.require_permission('warehouse.brand_conversion.post');end if;\n  perform pg_advisory_xact_lock(hashtextextended('BDREQ:'"),
      ("    when 'SET_POLICY' then", "    when 'SET_REDYE_PRICE' then erp.save_product_conversion_action_v1('SET_REDYE_PRICE',p_payload,p_client_request_id)\n    when 'SET_POLICY' then")])
    return '\n'.join([draft,correction,lines,post,resync,reverse,accrual,rebuild,cost,blocker,unknown,workspace,router])
