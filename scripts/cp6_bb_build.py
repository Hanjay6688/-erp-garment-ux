#!/usr/bin/env python3
"""Build the BB T1 family install: the open cutover states of ALL (owner decision 25 Sep 2026: every ALL state built and tested
in CP6, "gw mau semuanya dibikin sekarang dan diuji di cp 6 termasuk all 22"), first the financial part.

New objects come from scripts/cp6_bb_objects_*.sql; every existing function is taken from the definition the chain currently
runs (AP, AR, AC migrations and the BA T1 file) with checked substitutions only, like the BA builder:
  F1 (ALL-P02/S01, bug found while designing BB) erp.post_opening_subledger_settlement: every settlement of an opening
     balance, from any caller, is dated on or after the balance's cutover and document date and not after today
     (BB_OSS_DATE_OUT_OF_RANGE; before BB only a cash advance repayment checked its date), may not use money already
     promised to an unpaid payroll, and keeps the dated outstanding amount non-negative on its date and every later day
     (BB_OSS_DATED_CAPACITY, D02 as BA A9 for advances). A non-cash settlement (credit note, allowance, customer credit
     applied; erp.bb_opening_credits_v1) posts its own lines instead of cash.
  F2 erp.post_opening_financial_correction / erp.reverse_opening_financial_correction: the same dated floor after a
     correction or its reversal.
  F3 (ALL-Y01) erp.approve_payroll, erp.post_payroll_payment, erp.reverse_paid_payroll: an imported CONTRACTOR_PAYABLE
     may be paid inside payroll as an OPENING_PAYABLE line (like the AP cash advance deduction): approval does not accrue
     it a second time, payment settles the opening balance, reversal restores it.
  F4 import pipeline (erp.save_initial_import_action_v1, erp.stage_migration_row, erp._validate_migration_batch_base,
     erp.finalize_migration_batch, erp.initial_import_revision_v1, erp.get_initial_import_workspace_v1): three new files
     LEGACY_DOCUMENT (ALL-A03), OPENING_CUSTOMER_CREDIT and OPENING_SALE_RETURN (ALL-S03) and three new actions
     OPENING_SETTLEMENT (settle, reverse, credit, pay through payroll), CUSTOMER_CREDIT (refund, apply to an opening
     receivable, reverse) and OPENING_RETURN (receive, reverse) on the existing browser RPC; no new browser RPC.
  F5 erp.run_v267_financial_truth_checks (V2620M_PAYMENT_SOURCE_JOURNAL_MISMATCH): a non-cash opening settlement is checked
     against its exact counter account (SALES_REVENUE for a customer allowance, MATERIAL_PURCHASE_VARIANCE for a supplier
     allowance, OTHER_INCOME for a laundry vendor allowance, the customer credit account for an applied credit) where a cash
     settlement is checked against its cash account; every other condition of the detector is unchanged.
  P03 (ALL-P03) one receipt part invoiced before cutover: UNINVOICED_RECEIPT names the imported SUPPLIER_PAYABLE document
     of the invoiced part (invoice_document_number, invoiced_qty). The receipt stays one purchase item of its full quantity
     (unbilled + invoiced = stock + consumed origins); the invoiced part counts as matched quantity at its invoiced price
     (erp.material_purchase_posted_invoice_qty, erp.material_purchase_current_unit_cost, erp.refresh_material_purchase_item_match_state,
     from the CP4.5a fixture text with v2.6.20q's in-place edit), so the stock carries the blended cost and the opening GRNI
     (erp.sync_material_purchase_grni_on_status and the AP_OPENING_RECEIPT_* detectors) covers only the unbilled part; the
     invoiced money stays the imported document, settled by OPENING_SETTLEMENT. erp.check_initial_import_receipt_v1 and
     erp.apply_initial_import_receipts_v1 carry the part.
  F6 erp.assert_new_stock_cutoff_coverage_v1 (BA's version): the two new product references are classified (a return right
     is a SOURCE_DOCUMENT whose stock fact is the RETURN lot validated as NEW_STOCK at receipt; a receipt is DERIVED).
Label T1_FAMILY: development install on the disposable chain AN -> AU -> AV -> AW..BA, not a release package.

Usage: python3 scripts/cp6_bb_build.py            # writes supabase/dev/cp6_bb_t1_family.sql
       python3 scripts/cp6_bb_build.py --check
"""
from pathlib import Path
import gzip,hashlib,json,re,sys

ROOT=Path(__file__).resolve().parents[1]
AP=ROOT/'supabase/migrations/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql'
AR=ROOT/'supabase/migrations/20260922185015_erp_v2_6_20ar_cp6_opening_overlap.sql'
AC=ROOT/'supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
BA=ROOT/'supabase/dev/cp6_ba_t1_family.sql'
CATALOG=ROOT/'src/initialImportCatalog.json'
CATALOG_BB=ROOT/'src/initialImportCatalogBB.json'
OBJECTS=[ROOT/'scripts/cp6_bb_objects_financial.sql',ROOT/'scripts/cp6_bb_objects_purchase.sql']
FIXTURE=ROOT/'supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz'
OUT=ROOT/'supabase/dev/cp6_bb_t1_family.sql'
VERSION='v2.6.20bb'
NEW_ENTITIES=['LEGACY_DOCUMENT','OPENING_CUSTOMER_CREDIT','OPENING_SALE_RETURN']
NEW_ACTIONS=['OPENING_SETTLEMENT','CUSTOMER_CREDIT','OPENING_RETURN']

# ---------------------------------------------------------------- F1 erp.post_opening_subledger_settlement (AP)
OSS_HEAD='CREATE OR REPLACE FUNCTION erp.post_opening_subledger_settlement(p_settlement_id uuid)'
OSS_DECLARE_OLD='v_cash uuid;v_remaining numeric(20,2);v_lines jsonb;\nBEGIN'
OSS_DECLARE_NEW='v_cash uuid;v_remaining numeric(20,2);v_lines jsonb;v_ctx jsonb;v_day date;v_credit boolean;\nBEGIN'
OSS_REMAINING_OLD='v_remaining:=b.original_amount-b.settled_amount;'
OSS_REMAINING_NEW="""v_remaining:=b.original_amount-b.settled_amount-erp.bb_opening_balance_reserved_v1(b.id);
-- BB (ALL-P02/S01): a settlement from any caller is dated on or after the balance's cutover and document date and not after
-- today; money already promised to an unpaid payroll is not available; a non-cash credit posts its own lines below.
v_ctx:=erp.bb_opening_balance_context_v1(b.id);v_day:=erp._cp3_business_date(s.physical_at);
IF v_day<(v_ctx->>'min_date')::date OR v_day>erp.bb_business_today_v1() THEN
  RAISE EXCEPTION 'BB_OSS_DATE_OUT_OF_RANGE: tanggal pelunasan % harus antara % dan hari ini',v_day,v_ctx->>'min_date';END IF;
v_credit:=exists(select 1 from erp.bb_opening_credits_v1 where settlement_id=s.id);
"""
OSS_CASH_OLD='v_cash:=erp.initial_prepayment_funding_v1('
OSS_CASH_NEW='IF v_credit THEN v_lines:=erp.bb_opening_credit_lines_v1(s.id);ELSE\nv_cash:=erp.initial_prepayment_funding_v1('
OSS_LINES_OLD="ELSE RAISE EXCEPTION 'Unsupported opening subledger direction/party combination';END IF;"
OSS_LINES_NEW=OSS_LINES_OLD+'END IF;'
OSS_END_OLD='WHERE id=b.id;END;$function$;'
OSS_END_NEW='WHERE id=b.id;\n-- BB: the dated outstanding amount stays non-negative on the settlement date and every later day.\nPERFORM erp.bb_assert_opening_balance_floor_v1(b.id,v_day);END;$function$;'

# ---------------------------------------------------------------- F2 opening financial corrections (AC)
CORR_HEAD='CREATE OR REPLACE FUNCTION erp.post_opening_financial_correction(p_opening_item_id uuid, p_corrected_amount numeric, p_reason text, p_effective_date date DEFAULT ((statement_timestamp() AT TIME ZONE \'Asia/Jakarta\'::text))::date)'
CORR_OLD="""    where id=b.id;
  end if;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('opening_balance_items',i.id,'UPDATE',"""
CORR_NEW="""    where id=b.id;
    -- BB: a correction may not leave the dated outstanding amount negative on its effective date or any later day.
    perform erp.bb_assert_opening_balance_floor_v1(b.id,p_effective_date);
  end if;
  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('opening_balance_items',i.id,'UPDATE',"""
UNCORR_HEAD='CREATE OR REPLACE FUNCTION erp.reverse_opening_financial_correction(p_correction_id uuid, p_reason text)'
UNCORR_OLD="  update erp.opening_financial_corrections set status='REVERSED',reversed_at=clock_timestamp(),reversal_reason=p_reason where id=c.id;\n"
UNCORR_NEW=UNCORR_OLD+"""  -- BB: reversing an increase may not leave the dated outstanding amount negative from the corrected date onward.
  if b.id is not null then perform erp.bb_assert_opening_balance_floor_v1(b.id,c.effective_date); end if;
"""

# ---------------------------------------------------------------- F3 payroll (AP)
APPROVE_HEAD='CREATE OR REPLACE FUNCTION erp.approve_payroll(p_payroll_id uuid)'
APPROVE_CHECK_OLD='  perform erp.check_opening_cash_advance_payroll_v1(p.id);\n'
APPROVE_CHECK_NEW=APPROVE_CHECK_OLD+'  perform erp.bb_check_opening_payable_payroll_v1(p.id);\n'
APPROVE_ACCRUAL_OLD="  where payroll_id=p.id and source_type<>'ACCESSORY_BOM';"
APPROVE_ACCRUAL_NEW="""  -- BB (ALL-Y01): an imported contractor payable was recognized at cutover; paying it through payroll accrues nothing again.
  where payroll_id=p.id and source_type not in('ACCESSORY_BOM','OPENING_PAYABLE');"""
PAY_HEAD='CREATE OR REPLACE FUNCTION erp.post_payroll_payment(p_payroll_id uuid)'
PAY_CHECK_OLD=APPROVE_CHECK_OLD
PAY_CHECK_NEW=APPROVE_CHECK_NEW
PAY_SETTLE_OLD="""    where payroll_id=p.id and deduction_type='CASH_ADVANCE' group by opening_cash_advance_balance_id) x where b.id=x.id;
"""
PAY_SETTLE_NEW=PAY_SETTLE_OLD+"""  -- BB (ALL-Y01): imported contractor payables paid by this payroll, then the dated floor of every opening balance it touched.
  update erp.opening_subledger_balances b set settled_amount=b.settled_amount+x.amount,
    status=case when b.settled_amount+x.amount=b.original_amount then 'SETTLED' else 'PARTIAL' end,updated_at=statement_timestamp()
  from(select opening_payable_balance_id id,sum(amount) amount from erp.payroll_reimbursements
    where payroll_id=p.id and source_type='OPENING_PAYABLE' group by opening_payable_balance_id) x where b.id=x.id;
  for r in select z.id from(select opening_payable_balance_id id from erp.payroll_reimbursements where payroll_id=p.id and opening_payable_balance_id is not null
      union select opening_cash_advance_balance_id from erp.payroll_deductions where payroll_id=p.id and opening_cash_advance_balance_id is not null) z order by z.id
  loop perform erp.bb_assert_opening_balance_floor_v1(r.id,p.payment_date); end loop;
"""
REVERSE_HEAD='CREATE OR REPLACE FUNCTION erp.reverse_paid_payroll(p_payroll_id uuid, p_reason text)'
REVERSE_LOCK_OLD="""  perform 1 from erp.opening_subledger_balances b where exists(select 1 from erp.payroll_deductions d
    where d.payroll_id=p.id and d.opening_cash_advance_balance_id=b.id) order by b.id for update;"""
REVERSE_LOCK_NEW="""  perform 1 from erp.opening_subledger_balances b where exists(select 1 from erp.payroll_deductions d
    where d.payroll_id=p.id and d.opening_cash_advance_balance_id=b.id) or exists(select 1 from erp.payroll_reimbursements pr
    where pr.payroll_id=p.id and pr.opening_payable_balance_id=b.id) order by b.id for update;"""
REVERSE_SETTLE_OLD=PAY_SETTLE_OLD
REVERSE_SETTLE_NEW=PAY_SETTLE_OLD+"""  -- BB (ALL-Y01): the imported contractor payables this payroll paid are open again.
  update erp.opening_subledger_balances b set settled_amount=b.settled_amount-x.amount,
    status=case when b.settled_amount-x.amount=b.original_amount then 'SETTLED' when b.settled_amount-x.amount>0 then 'PARTIAL' else 'OPEN' end,
    updated_at=statement_timestamp()
  from(select opening_payable_balance_id id,sum(amount) amount from erp.payroll_reimbursements
    where payroll_id=p.id and source_type='OPENING_PAYABLE' group by opening_payable_balance_id) x where b.id=x.id;
"""

# ---------------------------------------------------------------- F4 import pipeline
REV_HEAD='CREATE OR REPLACE FUNCTION erp.initial_import_revision_v1(p_batch_id uuid)'
REV_OLD="""     where h.migration_batch_id=p_batch_id),'[]'::jsonb)
 )::text"""
REV_NEW="""     where h.migration_batch_id=p_batch_id),'[]'::jsonb),
   'bb',erp.bb_financial_revision_part_v1(p_batch_id)
 )::text"""
WS_HEAD='CREATE OR REPLACE FUNCTION erp.get_initial_import_workspace_v1(p_batch_id uuid DEFAULT NULL)'
WS_OLD='   ) into v_batch;\n end if;'
WS_NEW='   ) into v_batch;\n   -- BB: opening balances with their settlements and payroll lines, customer credits, return rights, legacy documents.\n   v_batch:=v_batch||erp.bb_financial_workspace_v1(b.id);\n end if;'
STAGE_HEAD='CREATE OR REPLACE FUNCTION erp.stage_migration_row(p_batch_id uuid, p_entity_type text, p_source_row_no integer, p_legacy_key text, p_source_payload jsonb, p_normalized_payload jsonb)'
STAGE_OLD="'LAUNDRY_VENDOR','LOCATION','CHART_ACCOUNT','CASH_ACCOUNT') then\n    raise exception 'Unsupported migration entity_type %',v_type;"
STAGE_NEW="'LAUNDRY_VENDOR','LOCATION','CHART_ACCOUNT','CASH_ACCOUNT',"+','.join("'%s'"%e for e in NEW_ENTITIES)+") then\n    raise exception 'Unsupported migration entity_type %',v_type;"
BASE_HEAD='CREATE OR REPLACE FUNCTION erp._validate_migration_batch_base(p_batch_id uuid)'
BASE_OLD="entity_type not in('MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPENING_CONTROL','OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','OPENING_ADVANCE')"
BASE_NEW="entity_type not in('MATERIAL_ROLL','OPENING_BALANCE_ITEM','OPENING_CONTROL','OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','OPENING_ADVANCE',"+','.join("'%s'"%e for e in NEW_ENTITIES)+")"
FINAL_HEAD='CREATE OR REPLACE FUNCTION erp.finalize_migration_batch(p_batch_id uuid)'
FINAL_OLD="'OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','OPENING_ADVANCE') and posted_entity_id is null)"
FINAL_NEW="'OPENING_COST_ORIGIN','UNINVOICED_RECEIPT','OPENING_ADVANCE',"+','.join("'%s'"%e for e in NEW_ENTITIES)+") and posted_entity_id is null)"

ROUTER_HEAD='CREATE OR REPLACE FUNCTION erp.save_initial_import_action_v1(p_action text, p_payload jsonb, p_client_request_id uuid)'
ROUTER_ACTIONS_OLD="if v_action is null or v_action not in('CREATE','SAVE_FILE','VALIDATE','FINALIZE','ALLOCATE_CASH_ADVANCE','PREPAYMENT','WIP_OUTPUT') then"
ROUTER_ACTIONS_NEW="if v_action is null or v_action not in('CREATE','SAVE_FILE','VALIDATE','FINALIZE','ALLOCATE_CASH_ADVANCE','PREPAYMENT','WIP_OUTPUT',"+','.join("'%s'"%a for a in NEW_ACTIONS)+") then"
ROUTER_LOCK_OLD="if v_action in('FINALIZE','WIP_OUTPUT') then\n   perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));"
ROUTER_LOCK_NEW="if v_action in('FINALIZE','WIP_OUTPUT','OPENING_RETURN') then\n   perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));"
ROUTER_BRANCH_OLD=" elsif v_action='PREPAYMENT' then\n"
ROUTER_BRANCH_NEW=""" elsif v_action in('OPENING_SETTLEMENT','CUSTOMER_CREDIT','OPENING_RETURN') then
   -- BB: continuations of a posted import (ALL-P02/S01/S03/Y01), one transaction and one request identity each.
   v_batch:=(p_payload->>'batch_id')::uuid;
   select * into b from erp.migration_batches where id=v_batch for update;
   if b.id is null or b.status<>'POSTED' then raise exception 'BB_IMPORT_NOT_POSTED: lanjutan hanya untuk impor yang sudah disahkan';end if;
   if p_payload->>'expected_revision' is distinct from erp.initial_import_revision_v1(b.id) then
     raise exception 'STALE_VERSION: saldo impor berubah; muat ulang sebelum melanjutkan';end if;
   v_result:=case v_action when 'OPENING_SETTLEMENT' then erp.bb_manage_opening_settlement_v1(p_payload,p_client_request_id)
     when 'CUSTOMER_CREDIT' then erp.bb_manage_customer_credit_v1(p_payload,p_client_request_id)
     else erp.bb_manage_opening_sale_return_v1(p_payload,p_client_request_id) end;
   v_result:=v_result||jsonb_build_object('request_id',p_client_request_id,'action',v_action,'batch_id',v_batch,'status','POSTED',
     'revision',erp.initial_import_revision_v1(v_batch));
   return erp._idempotency_complete('save_initial_import_action_v1',p_client_request_id,v_result);
 elsif v_action='PREPAYMENT' then
"""
ROUTER_NUMERIC_OLD="if v_field in('qty','opening_qty','unit_cost','amount','original_amount','settled_before_cutover','hpp_percent_of_price','target_dozens','target_qty_pcs','sort_order') and v_text<>'' then"
ROUTER_NUMERIC_NEW="if v_field in('qty','opening_qty','unit_cost','amount','original_amount','settled_before_cutover','hpp_percent_of_price','target_dozens','target_qty_pcs','sort_order','credit_unit_price') and v_text<>'' then"
ROUTER_PRECISION_OLD="if (v_field in('amount','original_amount','settled_before_cutover') and v_number<>round(v_number,2))"
ROUTER_PRECISION_NEW="if (v_field in('amount','original_amount','settled_before_cutover','credit_unit_price') and v_number<>round(v_number,2))"
ROUTER_VALIDATE_OLD='     perform erp.validate_initial_prepayments_v1(b.id);\n'
ROUTER_VALIDATE_NEW=ROUTER_VALIDATE_OLD+'     perform erp.bb_validate_financial_imports_v1(b.id);\n'
ROUTER_APPLY_OLD='       perform erp.apply_initial_prepayments_v1(b.id);\n'
ROUTER_APPLY_NEW=ROUTER_APPLY_OLD+'       perform erp.bb_apply_financial_imports_v1(b.id);\n'

# ---------------------------------------------------------------- P03 one receipt, part invoiced before cutover
# Native purchase helpers restored from the CP4.5a catalog fixture (their current text; v2.6.20q edited the match refresh
# in place, reproduced below), then checked substitutions.
POSTED_QTY_HEAD='CREATE OR REPLACE FUNCTION erp.material_purchase_posted_invoice_qty(p_purchase_item_id uuid)'
POSTED_QTY_OLD='select coalesce(sum(l.qty_invoiced),0)::numeric\nfrom erp.material_supplier_invoice_lines l'
POSTED_QTY_NEW='select (coalesce(sum(l.qty_invoiced),0)+erp.bb_receipt_invoiced_qty_v1($1))::numeric\nfrom erp.material_supplier_invoice_lines l'
UNIT_COST_HEAD='CREATE OR REPLACE FUNCTION erp.material_purchase_current_unit_cost(p_purchase_item_id uuid)'
UNIT_COST_EXISTS_OLD="    where l.purchase_item_id=i.id and h.status='POSTED'\n  ) then"
UNIT_COST_EXISTS_NEW="    where l.purchase_item_id=i.id and h.status='POSTED'\n  ) or exists(select 1 from erp.bb_receipt_invoiced_parts_v1 p where p.purchase_item_id=i.id) then"
UNIT_COST_RETURN_OLD='    return greatest(((v_basis_qty*i.unit_price)+v_invoice_delta)/v_basis_qty,0);'
UNIT_COST_RETURN_NEW=('    -- BB (ALL-P03): a part invoiced before cutover enters the cost like a posted invoice line at its invoiced amount.\n'
  '    v_invoice_delta:=v_invoice_delta+coalesce((select p.invoiced_amount-p.invoiced_qty*i.unit_price from erp.bb_receipt_invoiced_parts_v1 p\n'
  '      where p.purchase_item_id=i.id),0);\n'+UNIT_COST_RETURN_OLD)
MATCH_HEAD='CREATE OR REPLACE FUNCTION erp.refresh_material_purchase_item_match_state(p_purchase_item_id uuid)'
MATCH_V2620Q=('v_matched<v_capacity-0.000001','v_matched<v_capacity')
MATCH_OLD="  where l.purchase_item_id=i.id and h.status='POSTED';\n\n  if v_matched<=0 then"
MATCH_NEW=("  where l.purchase_item_id=i.id and h.status='POSTED';\n"
  "  -- BB (ALL-P03): the part invoiced before cutover is matched quantity at its invoiced price.\n"
  "  if exists(select 1 from erp.bb_receipt_invoiced_parts_v1 p where p.purchase_item_id=i.id) then\n"
  "    select v_matched+p.invoiced_qty,(coalesce(v_actual_avg*v_matched,0)+p.invoiced_amount)/(v_matched+p.invoiced_qty)\n"
  "    into v_matched,v_actual_avg from erp.bb_receipt_invoiced_parts_v1 p where p.purchase_item_id=i.id;\n"
  "  end if;\n\n  if v_matched<=0 then")
GRNI_HEAD='CREATE OR REPLACE FUNCTION erp.sync_material_purchase_grni_on_status()'
GRNI_OLD='      select round(sum(qty*unit_price),2) into v_estimated from erp.material_purchase_items where purchase_id=new.id;'
GRNI_NEW=('      -- BB (ALL-P03): the opening GRNI covers only the unbilled part; the invoiced part is its imported payable document.\n'
  '      select round(sum((qty-erp.bb_receipt_invoiced_qty_v1(id))*unit_price),2) into v_estimated from erp.material_purchase_items where purchase_id=new.id;')
CHECKS_GRNI_OLD='cross join lateral(select round(sum(qty*unit_price),2) value from erp.material_purchase_items where purchase_id=rh.purchase_id) v'
CHECKS_GRNI_NEW='cross join lateral(select round(sum((qty-erp.bb_receipt_invoiced_qty_v1(id))*unit_price),2) value from erp.material_purchase_items where purchase_id=rh.purchase_id) v'
CHECKS_COST_OLD='pi.unit_price is distinct from oi.unit_cost_snapshot'
CHECKS_COST_NEW='erp.bb_receipt_opening_unit_cost_v1(pi.id) is distinct from oi.unit_cost_snapshot'
RCHECK_HEAD='CREATE OR REPLACE FUNCTION erp.check_initial_import_receipt_v1(p_batch_id uuid,p_row_id uuid)'
RCHECK_DECLARE_OLD=' j jsonb;v_cutover date;v_party uuid;v_key text;v_number text;v_line text;v_date date;v_qty numeric;v_cost numeric;k text;'
RCHECK_DECLARE_NEW=RCHECK_DECLARE_OLD+'\n v_part jsonb;v_invoiced numeric:=0;v_blend numeric;'
RCHECK_PART_OLD=' perform v_qty::numeric(18,6);perform v_cost::numeric(18,6);\n'
RCHECK_PART_NEW=RCHECK_PART_OLD+(" -- BB (ALL-P03): a part of this line invoiced before cutover (its imported SUPPLIER_PAYABLE document): the line keeps\n"
  " -- its full quantity (unbilled + invoiced = stock + consumed origins) and its stock carries the blended cost.\n"
  " v_part:=erp.bb_receipt_row_invoiced_part_v1(p_batch_id,p_row_id);\n"
  " v_invoiced:=coalesce((v_part->>'invoiced_qty')::numeric,0);\n"
  " v_blend:=case when v_part is null then v_cost else round((v_qty*v_cost+(v_part->>'invoiced_amount')::numeric)/(v_qty+v_invoiced),6) end;\n")
RCHECK_COST_OLD=("   or (s.normalized_payload->>'unit_cost')::numeric is distinct from v_cost then\n"
  "   raise exception 'opening_source_key: bahan, gudang, dan biaya harus sama dengan stok awal';end if;")
RCHECK_COST_NEW=("   or (s.normalized_payload->>'unit_cost')::numeric is distinct from v_blend then\n"
  "   raise exception 'opening_source_key: bahan, gudang, dan biaya harus sama dengan stok awal (biaya per satuan %)',v_blend;end if;")
RCHECK_QTY_OLD=' if v_qty is distinct from coalesce((s.normalized_payload->>case'
RCHECK_QTY_NEW=' if v_qty+v_invoiced is distinct from coalesce((s.normalized_payload->>case'
RAPPLY_HEAD='CREATE OR REPLACE FUNCTION erp.apply_initial_import_receipts_v1(p_batch_id uuid)'
RAPPLY_DECLARE_OLD='declare b erp.migration_batches%rowtype;r record;j jsonb;v_supplier uuid;v_purchase uuid;v_item uuid;'
RAPPLY_DECLARE_NEW=RAPPLY_DECLARE_OLD+'v_part jsonb;v_blend numeric;'
RAPPLY_PART_OLD='   j:=r.normalized_payload;\n   select id into strict v_supplier'
RAPPLY_PART_NEW=("   j:=r.normalized_payload;\n"
  "   v_part:=erp.bb_receipt_row_invoiced_part_v1(b.id,r.id);\n"
  "   v_blend:=case when v_part is null then (j->>'unit_cost')::numeric else round(((j->>'qty')::numeric*(j->>'unit_cost')::numeric\n"
  "     +(v_part->>'invoiced_amount')::numeric)/((j->>'qty')::numeric+(v_part->>'invoiced_qty')::numeric),6) end;\n"
  "   select id into strict v_supplier")
RAPPLY_COST_OLD="if v_opening.id is not null and (v_opening.unit_cost_snapshot<>(j->>'unit_cost')::numeric"
RAPPLY_COST_NEW="if v_opening.id is not null and (v_opening.unit_cost_snapshot<>v_blend"
RAPPLY_ITEM_OLD="values(v_purchase,v_material,(j->>'qty')::numeric,(j->>'unit_cost')::numeric,'ESTIMATED','MANUAL_ESTIMATE',j->>'notes') returning id into v_item;"
RAPPLY_ITEM_NEW="values(v_purchase,v_material,(j->>'qty')::numeric+coalesce((v_part->>'invoiced_qty')::numeric,0),(j->>'unit_cost')::numeric,'ESTIMATED','MANUAL_ESTIMATE',j->>'notes') returning id into v_item;"
RAPPLY_LINE_OLD="     values(v_item,v_purchase,r.id,v_opening.id,j->>'receipt_line_number');\n"
RAPPLY_LINE_NEW=RAPPLY_LINE_OLD+("   if v_part is not null then\n"
  "     insert into erp.bb_receipt_invoiced_parts_v1(purchase_item_id,source_row_id,financial_source_id,invoiced_qty,invoiced_amount)\n"
  "     select v_item,r.id,f.id,(v_part->>'invoiced_qty')::numeric,(v_part->>'invoiced_amount')::numeric\n"
  "     from erp.initial_import_financial_sources f where f.batch_id=b.id and f.source_row_id=(v_part->>'document_row_id')::uuid\n"
  "       and f.balance_type='SUPPLIER_PAYABLE' and f.party_id=v_supplier;\n"
  "     if not found then raise exception 'P03_INVOICE_DOC_REQUIRED: dokumen invoice asal belum dibukukan';end if;\n"
  "     perform erp.refresh_material_purchase_item_match_state(v_item);\n"
  "   end if;\n")
RAPPLY_ORIGIN_OLD="values(v_origin.id,v_item,v_target,(v_origin.normalized_payload->>'qty')::numeric,(j->>'unit_cost')::numeric);"
RAPPLY_ORIGIN_NEW="values(v_origin.id,v_item,v_target,(v_origin.normalized_payload->>'qty')::numeric,v_blend);"
ROUTER_P03_NUMERIC=("'sort_order','credit_unit_price') and v_text<>'' then","'sort_order','credit_unit_price','invoiced_qty') and v_text<>'' then")
ROUTER_P03_PRECISION=("or (v_field in('qty','opening_qty','unit_cost','target_dozens') and v_number<>round(v_number,6))",
                      "or (v_field in('qty','opening_qty','unit_cost','target_dozens','invoiced_qty') and v_number<>round(v_number,6))")

# ---------------------------------------------------------------- F6 the AV new-stock coverage registry (BA's version)
COVER_HEAD='CREATE OR REPLACE FUNCTION erp.assert_new_stock_cutoff_coverage_v1()'
COVER_OLD='''"erp.fg_stock_movements.product_id":{"class":"MOVEMENT","reason":"Movement of an existing lot"},'''
COVER_NEW=COVER_OLD+'''"erp.bb_opening_sale_return_rights_v1.product_id":{"class":"SOURCE_DOCUMENT","reason":"Return right of an old invoice; the stock fact is the RETURN lot in fg_lots, validated as NEW_STOCK at receipt"},"erp.bb_opening_sale_return_receipts_v1.product_id":{"class":"DERIVED","reason":"Provenance of a return receipt; the stock fact is its fg_lots lot"},'''

# ---------------------------------------------------------------- F5 the V2620M payment/journal detector (AP)
CHECKS_HEAD='CREATE OR REPLACE FUNCTION erp.run_v267_financial_truth_checks()'
CHECKS_SOURCE_OLD="(ca.id is null and erp.initial_prepayment_account_v1(x.id) is null)"
CHECKS_SOURCE_NEW="(ca.id is null and erp.initial_prepayment_account_v1(x.id) is null and erp.bb_opening_credit_account_v1(x.id) is null)"
CHECKS_ACCOUNT_OLD="coalesce(erp.initial_prepayment_account_v1(x.id),ca.coa_account_id)"
CHECKS_ACCOUNT_NEW="coalesce(erp.initial_prepayment_account_v1(x.id),erp.bb_opening_credit_account_v1(x.id),ca.coa_account_id)"

REPLACED=['erp.post_opening_subledger_settlement(uuid)','erp.post_opening_financial_correction(uuid,numeric,text,date)',
          'erp.reverse_opening_financial_correction(uuid,text)','erp.approve_payroll(uuid)','erp.post_payroll_payment(uuid)',
          'erp.reverse_paid_payroll(uuid,text)','erp.initial_import_revision_v1(uuid)','erp.get_initial_import_workspace_v1(uuid)',
          'erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)','erp._validate_migration_batch_base(uuid)',
          'erp.finalize_migration_batch(uuid)','erp.save_initial_import_action_v1(text,jsonb,uuid)','erp.run_v267_financial_truth_checks()',
          'erp.assert_new_stock_cutoff_coverage_v1()','erp.material_purchase_posted_invoice_qty(uuid)',
          'erp.material_purchase_current_unit_cost(uuid)','erp.refresh_material_purchase_item_match_state(uuid)',
          'erp.sync_material_purchase_grni_on_status()','erp.check_initial_import_receipt_v1(uuid,uuid)','erp.apply_initial_import_receipts_v1(uuid)']
NEW_TABLES=['bb_receipt_invoiced_parts_v1','bb_legacy_documents_v1','bb_customer_credits_v1','bb_customer_credit_events_v1','bb_opening_sale_return_rights_v1',
            'bb_opening_sale_return_receipts_v1','bb_opening_credits_v1']


def objects():
    return '\n'.join(p.read_text().rstrip('\n') for p in OBJECTS)


def new_functions():
    """Signatures of the functions the objects files create (verified in the database by the probe)."""
    text=objects();found=[]
    for m in re.finditer(r'(?i)create or replace function (erp\.[a-z0-9_]+)\(',text):found.append(m.group(1))
    return found


def function(path,head,subs,end='$function$;'):
    text=path.read_text()
    assert text.count(head)==1,(path.name,head)
    start=text.index(head);stop=text.index(end,start)+len(end)
    body=text[start:stop]
    for old,new in subs:
        assert body.count(old)==1,(head[:80],old[:70],body.count(old))
        body=body.replace(old,new)
    return body


def catalog():
    """The import catalog after BB: the unchanged AP catalog (read by the historical builders) plus the BB entities."""
    base=json.loads(CATALOG.read_text());extra=json.loads(CATALOG_BB.read_text())
    extend=extra.pop('_extend',{})
    assert not set(base)&set(extra),'BB_CATALOG_OVERLAP'
    for entity,more in extend.items():
        assert entity in base and not set(more['fields'])&set(base[entity]['fields']),('BB_CATALOG_EXTEND',entity)
        base[entity]['fields'].update(more['fields'])
    return {**base,**extra}


def fixture_function(head,subs,edits=()):
    """A function as the CP4.5a catalog fixture defines it, with documented later in-place edits, then substitutions."""
    text=gzip.open(FIXTURE,'rt').read()
    assert text.count(head)==1,('FIXTURE',head)
    start=text.index(head);stop=text.index('$function$;',start)+len('$function$;')
    body=text[start:stop]
    for old,new in list(edits)+list(subs):
        assert body.count(old)==1,(head[:80],old[:70],body.count(old))
        body=body.replace(old,new)
    return body


def catalog_constant():
    return "'"+json.dumps(catalog(),ensure_ascii=False).replace("'","''")+"'"


def router():
    body=function(AR,ROUTER_HEAD,[(ROUTER_ACTIONS_OLD,ROUTER_ACTIONS_NEW),(ROUTER_LOCK_OLD,ROUTER_LOCK_NEW),
        (ROUTER_BRANCH_OLD,ROUTER_BRANCH_NEW),(ROUTER_NUMERIC_OLD,ROUTER_NUMERIC_NEW),(ROUTER_PRECISION_OLD,ROUTER_PRECISION_NEW),
        (ROUTER_VALIDATE_OLD,ROUTER_VALIDATE_NEW),(ROUTER_APPLY_OLD,ROUTER_APPLY_NEW),ROUTER_P03_NUMERIC,ROUTER_P03_PRECISION])
    old=re.search(r"v_catalog constant jsonb:=('.*?')::jsonb;",body,re.S)
    assert old and body.count(old.group(0))==1
    merged=catalog()
    for e in NEW_ENTITIES:assert e in merged,('CATALOG_ENTITY_MISSING',e)
    return body.replace(old.group(0),'v_catalog constant jsonb:='+catalog_constant()+'::jsonb;')


def build():
    oss=function(AP,OSS_HEAD,[(OSS_DECLARE_OLD,OSS_DECLARE_NEW),(OSS_REMAINING_OLD,OSS_REMAINING_NEW),(OSS_CASH_OLD,OSS_CASH_NEW),
                              (OSS_LINES_OLD,OSS_LINES_NEW),(OSS_END_OLD,OSS_END_NEW)])
    corr=function(AC,CORR_HEAD,[(CORR_OLD,CORR_NEW)])
    uncorr=function(AC,UNCORR_HEAD,[(UNCORR_OLD,UNCORR_NEW)])
    approve=function(AP,APPROVE_HEAD,[(APPROVE_CHECK_OLD,APPROVE_CHECK_NEW),(APPROVE_ACCRUAL_OLD,APPROVE_ACCRUAL_NEW)])
    pay=function(AP,PAY_HEAD,[(PAY_CHECK_OLD,PAY_CHECK_NEW),(PAY_SETTLE_OLD,PAY_SETTLE_NEW)])
    reverse=function(AP,REVERSE_HEAD,[(REVERSE_LOCK_OLD,REVERSE_LOCK_NEW),(REVERSE_SETTLE_OLD,REVERSE_SETTLE_NEW)])
    revision=function(AP,REV_HEAD,[(REV_OLD,REV_NEW)])
    workspace=function(BA,WS_HEAD,[(WS_OLD,WS_NEW)])
    stage=function(AP,STAGE_HEAD,[(STAGE_OLD,STAGE_NEW)])
    base=function(AP,BASE_HEAD,[(BASE_OLD,BASE_NEW)])
    final=function(AP,FINAL_HEAD,[(FINAL_OLD,FINAL_NEW)])
    checks=function(AP,CHECKS_HEAD,[(CHECKS_SOURCE_OLD,CHECKS_SOURCE_NEW),(CHECKS_GRNI_OLD,CHECKS_GRNI_NEW),(CHECKS_COST_OLD,CHECKS_COST_NEW)])
    assert checks.count(CHECKS_ACCOUNT_OLD)==2,'BB_CHECKS_ACCOUNT_SITES'
    checks=checks.replace(CHECKS_ACCOUNT_OLD,CHECKS_ACCOUNT_NEW)
    cover=function(BA,COVER_HEAD,[(COVER_OLD,COVER_NEW)])
    posted_qty=fixture_function(POSTED_QTY_HEAD,[(POSTED_QTY_OLD,POSTED_QTY_NEW)])
    unit_cost=fixture_function(UNIT_COST_HEAD,[(UNIT_COST_EXISTS_OLD,UNIT_COST_EXISTS_NEW),(UNIT_COST_RETURN_OLD,UNIT_COST_RETURN_NEW)])
    match=fixture_function(MATCH_HEAD,[(MATCH_OLD,MATCH_NEW)],edits=[MATCH_V2620Q])
    grni=function(AP,GRNI_HEAD,[(GRNI_OLD,GRNI_NEW)])
    rcheck=function(AP,RCHECK_HEAD,[(RCHECK_DECLARE_OLD,RCHECK_DECLARE_NEW),(RCHECK_PART_OLD,RCHECK_PART_NEW),(RCHECK_COST_OLD,RCHECK_COST_NEW),
                                    (RCHECK_QTY_OLD,RCHECK_QTY_NEW)])
    rapply=function(AP,RAPPLY_HEAD,[(RAPPLY_DECLARE_OLD,RAPPLY_DECLARE_NEW),(RAPPLY_PART_OLD,RAPPLY_PART_NEW),(RAPPLY_COST_OLD,RAPPLY_COST_NEW),
                                    (RAPPLY_ITEM_OLD,RAPPLY_ITEM_NEW),(RAPPLY_LINE_OLD,RAPPLY_LINE_NEW),(RAPPLY_ORIGIN_OLD,RAPPLY_ORIGIN_NEW)])
    parts=['-- CP6 BB open cutover states of ALL (owner decision 25 Sep 2026): T1_FAMILY development install (NOT a release package).',
           '-- Generated by scripts/cp6_bb_build.py from scripts/cp6_bb_objects_*.sql, the AP/AR/AC migrations and the BA T1 file; do not edit by hand.',
           'begin;',"set local lock_timeout='10s';set local statement_timeout='240s';set local search_path='';",
           'do $t1_guard$','begin',
           f" if not exists(select 1 from erp.schema_migrations where version='v2.6.20ba') then raise exception 'BB_T1_REQUIRES_BA'; end if;",
           f" if exists(select 1 from erp.schema_migrations where version='{VERSION}') or to_regclass('erp.bb_legacy_documents_v1') is not null then raise exception 'BB_T1_ALREADY_INSTALLED'; end if;",
           'end $t1_guard$;',objects(),oss,corr,uncorr,approve,pay,reverse,revision,workspace,stage,base,final,checks,cover,posted_qty,unit_cost,match,grni,rcheck,rapply,router(),
           'do $coverage$ begin perform erp.assert_new_stock_cutoff_coverage_v1(); end $coverage$;',
           f"insert into erp.schema_migrations(version,description) values('{VERSION}',"
           "'T1_FAMILY development install of BB (ALL open cutover states: opening settlement facade with dated guards, credits and allowances, legacy settled documents, customer return credits and rights, imported contractor payables through payroll); not a release package');",'commit;','']
    return '\n'.join(parts)


if __name__=='__main__':
    text=build()
    if '--check' in sys.argv:
        assert OUT.read_text()==text,'supabase/dev/cp6_bb_t1_family.sql is stale; rerun scripts/cp6_bb_build.py'
        print('fresh',hashlib.sha256(text.encode()).hexdigest())
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(text)
        print(OUT.relative_to(ROOT),len(text),hashlib.sha256(text.encode()).hexdigest())
