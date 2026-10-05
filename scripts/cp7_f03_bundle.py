"""Explicit combined F03 development stack; no automatic predecessor fallback."""
import hashlib
import cp7_procurement_bundle as procurement
import cp7_attendance_write_bundle as attendance
import cp7_settlement_bundle as settlement
import cp7_nota_bundle as nota
import cp7_sales_bundle as sales
import cp7_finance_bundle as finance
import cp7_period_bundle as period
import cp7_recost_bundle as recost
import cp7_journal_bundle as journal
import cp7_misc_bundle as misc
import cp7_installment_bundle as installment
import cp7_note_report_bundle as note_report
import cp7_transaction_source_bundle as transaction_source
import cp7_misc_correction_bundle as misc_correction
import cp7_sales_chain_bundle as sales_chain
ROOT=finance.ROOT

def attendance_internal_body():
 body=settlement.expected_internal()
 return attendance.patched_internal(settlement.patched_internal(body))

def sales_after_attendance():
 # The standalone P11 guard requires exactly P09. In this one declared order,
 # require exactly P09 + Nota + settlement + attendance instead. Preserve all
 # admission predicates and the entire P11 extension; change only that hash.
 base=(ROOT/'scripts/cp7-src/procurement/accepted-deltas.sql').read_text().split('as $function$',1)[1].split('$function$',1)[0]
 old_hash=hashlib.sha256(base.encode()).hexdigest();new_hash=hashlib.sha256(attendance_internal_body().encode()).hexdigest();sql=sales.extension()
 assert old_hash!=new_hash and sql.count(old_hash)==1
 assert all(s in attendance_internal_body() for s in ('cp7_payroll.execution_context','cp7_payroll.settlement_context','cp7_attendance.command_context'))
 return sql.replace(old_hash,new_hash,1)

def extension():
 prefix=procurement.bundle();full=attendance.bundle();assert full.startswith(prefix+'\n')
 return full[len(prefix)+1:]+'\n'+sales_after_attendance()+'\n'+finance.extension()+'\n'+period.extension()+'\n'+recost.extension()+'\n'+journal.extension()+'\n'+misc.extension()+'\n'+installment.extension()+'\n'+(ROOT/'scripts/cp7-src/sales/correction.sql').read_text()+'\n'+(ROOT/'scripts/cp7-src/sales/correction-lines.sql').read_text()+'\n'+(ROOT/'scripts/cp7-src/sales/return-correction.sql').read_text()+'\n'+note_report.extension()+'\n'+(ROOT/'scripts/cp7-src/sales/correction-actors.sql').read_text()+'\n'+transaction_source.extension()+'\n'+misc_correction.extension()+'\n'+(ROOT/'scripts/cp7-src/sales/chain-reversal.sql').read_text()
def bundle():return procurement.bundle()+'\n'+extension()
def patched_internal(definition):return sales.patched_internal(attendance.patched_internal(settlement.patched_internal(nota.patched_internal(definition))))

ROLES=('cp7_recost_write','cp7_recost_read','cp7_period_write','cp7_period_read','cp7_finance_read','cp7_sales_write','cp7_sales_read','cp7_attendance_write','cp7_roster_write','cp7_attendance_read','cp7_payroll_write','cp7_nota_write','cp7_payroll_header','cp7_payroll_read','cp7_fg_write','cp7_fg_read','cp7_return_write','cp7_return_read','cp7_invoice_write','cp7_invoice_read','cp7_material_write','cp7_material_read','cp7_procure_write','cp7_procure_read','cp7_policy','cp7_capture')
ROLES=('cp7_misc_write','cp7_misc_read','cp7_journal_read',)+ROLES
ROLES=(transaction_source.ROLE,'cp7_installment_write','cp7_installment_read',)+ROLES
BASE_GRANTS=('auth.uid()','auth.jwt()','erp.get_my_access_v1()','erp.has_permission(text)')
GRANTS={role:BASE_GRANTS for role in ('cp7_fg_read','cp7_fg_write','cp7_payroll_read','cp7_nota_write','cp7_payroll_header','cp7_payroll_write','cp7_attendance_read','cp7_roster_write','cp7_attendance_write')}
GRANTS['cp7_fg_read']+=('erp.bf_commercial_sku_at_v1(uuid,timestamptz)','erp.bd_lot_laundry_unknown_v1(uuid)','erp.get_hpp_completeness(uuid)')
GRANTS['cp7_fg_write']+=('erp.save_fg_adjustment_draft_v2(jsonb,uuid,bigint)','erp.post_fg_adjustment_v2(uuid,uuid,bigint,text)','erp.reverse_fg_adjustment_v2(uuid,text,uuid,bigint)','erp.move_fg_stock_card_row_to_position(uuid,integer)','erp.reset_fg_stock_mutation_book_order()')
GRANTS['cp7_nota_write']+=('erp.merge_eligible_work_into_payroll_v2(uuid,jsonb,uuid,bigint)',)
GRANTS.update(cp7_sales_read=sales.GRANTS,cp7_sales_write=('auth.uid()',),cp7_finance_read=finance.GRANTS)

GRANTS.update(cp7_period_read=period.READ_GRANTS,cp7_period_write=period.WRITE_GRANTS)

GRANTS.update(cp7_recost_read=recost.READ_GRANTS,cp7_recost_write=recost.WRITE_GRANTS)
GRANTS['cp7_journal_read']=journal.GRANTS
GRANTS.update(cp7_misc_read=misc.READ_GRANTS,cp7_misc_write=misc.WRITE_GRANTS)
GRANTS.update(cp7_installment_read=installment.READ_GRANTS,cp7_installment_write=installment.WRITE_GRANTS)

GRANTS[transaction_source.ROLE]=transaction_source.GRANTS
GRANTS['postgres']=(sales_chain.OWNING_FACADE,)
