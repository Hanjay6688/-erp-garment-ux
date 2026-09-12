import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const read=p=>readFileSync(p,'utf8')
const hash=s=>createHash('sha256').update(s).digest('hex')
const pinned={
  "supabase/migrations/20260912114635_erp_v2_6_20r_cp6_receipt_invoice_dependency.sql": "0c5551ef49da417310e0bcf8c8aa9d655f551ff66ca6e7ca79679ffd331f788b",
  "supabase/rollbacks/20260912114635_erp_v2_6_20r_cp6_receipt_invoice_dependency.rollback.sql": "ec3663694758cffef6509a4bc560aad257dd30b46be236c38abd4bf7c0e7e33e",
  "supabase/tests/cp6_receipt_invoice_dependency.sql": "7a4b9981467273c0f27da558bb6dd993b0feaab3789fcb2f5e14d85bb7b51170",
  "supabase/migrations/20260912084719_erp_v2_6_20q_cp6_supplier_invoice_exact_quantity.sql": "26faa6601494521d46813ecef194eb1c33ea7c9f71b98c3ef13ee90f869b5188",
  "supabase/rollbacks/20260912084719_erp_v2_6_20q_cp6_supplier_invoice_exact_quantity.rollback.sql": "d3c2cc7a18281f357b2b47e23179a2e4c86d5a16b035b0fc1e05dc3bf8d8dcb4"
}
for(const [p,sha] of Object.entries(pinned)) assert.equal(hash(read(p)),sha,p)
const migration=read(Object.keys(pinned)[0]), rollback=read(Object.keys(pinned)[1]), oracle=read(Object.keys(pinned)[2])
for(const token of ["R_REQUIRES_EXACT_Q_WITHOUT_R_RESIDUE", "R_PREEXISTING_INVOICE_SOURCE_REVIEW_REQUIRED", "Reverse posted supplier invoices before reversing this receipt", "where pi.purchase_id=h.id and ih.status='POSTED'", "V2620R_SUPPLIER_INVOICE_SOURCE_STATE", "or r.check_name like 'V2620R_%'", ...["8b3617725cd9061137dc55d6e2b5af75a87453929c93918b9e0acddea34f3cb2", "5ed3d75116f42f558829e1707f58c28fd1c81a2c66004ae54cf52069b147d4e1", "ce489ade327609230a40a0e804b1b67a9cecb11bb08a42bb470b9ba556183066"]]) assert.ok(migration.includes(token),token)
for(const token of ['jsonb_object_keys(v_expected))<>68','R_POST_USE_ROLLBACK_REFUSED','R_TRUSTED_PREDECESSOR_PIN_MISMATCH','FG_HPP_SALES_V2620C']) assert.ok(rollback.includes(token),token)
const runner=read('scripts/cp6_v2620r_receipt_invoice_dependency_regression.py')
for(const name of ["POSTED_FULL_INVOICE", "POSTED_PARTIAL_INVOICE", "MULTI_RECEIPT_INVOICE", "REMAINING_POSTED_INVOICE", "DETECTOR_SOURCE_STATE", "REVERSE_INVOICE_THEN_RECEIPT", "REVERSED_AND_DRAFT_INVOICES", "DRAFT_INVOICE_LATE_POST", "DIRECT_FINAL_NO_INVOICE", "RECEIPT_REPEAT_REVERSE", "POSTED_RETURN_GUARD", "POSTED_PAYMENT_GUARD", "POSTED_CORRECTION_GUARD"]) { assert.ok(oracle.includes(name),name); assert.ok(runner.includes(name),name) }
assert.ok(runner.includes('import cp6_v2620q_runtime as q_runtime'))
assert.ok(runner.includes('import cp6_v2620r_runtime as r_runtime'))
assert.ok(read('scripts/cp6_v2620q_runtime.py').includes("r_runtime.predecessor_snapshot(cur, 'Q', successor)"))
for(const g of ['m','n','o','p','q']) assert.ok(read(`scripts/cp6_v2620${g}_runtime.py`).includes('pre_r_installed_sha256'),g)
const workflow=read('.github/workflows/cp6-full-schema-validation.yml')
const coverage=workflow.slice(workflow.indexOf('      - name: Confirm every broad regression'),workflow.indexOf('      - name: Re-prove native C01-C06'))
const ledgerCounts=[...coverage.matchAll(/where (?:version|name) in\(([^)]+)\).* = '(\d+)'/g)]
assert.equal(ledgerCounts.length,3)
for(const [,names,count] of ledgerCounts) assert.equal(names.split(',').length,Number(count))
let previous=-1
for(const token of ['Apply v2.6.20q exact supplier invoice quantity','Reproduce independent Q receipt invoice dependency','Apply v2.6.20r receipt invoice dependency','Run post-CP6 real Auth','Prove native R receipt invoice dependency','Prove native R invoice posting versus receipt reversal','Qualify exact F G H I J K L M N O P Q and R rollback','Prove trusted R capsule','Prove trusted Q capsule']) {const at=workflow.indexOf(token);assert.ok(at>previous,token);previous=at}
for(const token of ["len(schedules['cases'])==260", "'expected':65,'observed':65", "setup_unit['completed_case_count']==setup_unit['expected_case_count']==103", "sum(c['upgrade_guard']['invalid_history_refused'] for c in r_before['cases'].values())==4", "CP6_V2620R_RUNTIME_MANIFEST.json", "CP6_V2620R_RECEIPT_INVOICE_DEPENDENCY_REGRESSION.json", "PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620R", "CP6_M_RACE_SOURCE_GENERATION: R", "len(rr['cases'])==2"]) assert.ok(workflow.includes(token),token)
for(const path of ["docs/cp6-r-receipt-invoice-dependency.md", "scripts/check-cp6-receipt-invoice-dependency.mjs", "scripts/cp6_v2620r_runtime.py", "scripts/cp6_v2620r_receipt_invoice_dependency_regression.py", "scripts/cp6_v2620r_receipt_invoice_races.py", "scripts/cp6_v2620r_rollback_guards.py", "supabase/migrations/20260912114635_erp_v2_6_20r_cp6_receipt_invoice_dependency.sql", "supabase/rollbacks/20260912114635_erp_v2_6_20r_cp6_receipt_invoice_dependency.rollback.sql", "supabase/tests/cp6_receipt_invoice_dependency.sql"]) assert.ok(workflow.includes("            '"+path+"',"),path)
const races=read('scripts/cp6_v2620r_receipt_invoice_races.py')
for(const token of ['INVOICE_POST_FIRST','RECEIPT_REVERSE_FIRST','pg_blocking_pids(pid)','contender_business_boundary_unchanged',"matrix.verify_setup_source('R')"]) assert.ok(races.includes(token),token)
console.log(JSON.stringify({status:'PASS',classification:'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',replaced_functions:3,boundary_tables:68,native_cases:13,known_q_paths:5,controls:8,receipt_invoice_native_races:2,maintenance_schedules:260,writer_body_entries:65,production_go:false}))
