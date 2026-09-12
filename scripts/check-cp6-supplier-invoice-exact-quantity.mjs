import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const read=p=>readFileSync(p,'utf8')
const hash=s=>createHash('sha256').update(s).digest('hex')
const pinned={
  "supabase/migrations/20260912084719_erp_v2_6_20q_cp6_supplier_invoice_exact_quantity.sql": "26faa6601494521d46813ecef194eb1c33ea7c9f71b98c3ef13ee90f869b5188",
  "supabase/rollbacks/20260912084719_erp_v2_6_20q_cp6_supplier_invoice_exact_quantity.rollback.sql": "d3c2cc7a18281f357b2b47e23179a2e4c86d5a16b035b0fc1e05dc3bf8d8dcb4",
  "supabase/tests/cp6_supplier_invoice_exact_quantity.sql": "0fac50fbd7ef872a70429ad59518986fce789e52feaefdef91c39d4a712792ef"
}
for(const [p,sha] of Object.entries(pinned)) assert.equal(hash(read(p)),sha,p)
const migration=read(Object.keys(pinned)[0]), rollback=read(Object.keys(pinned)[1]), oracle=read(Object.keys(pinned)[2])
for(const token of ["Q_REQUIRES_EXACT_P_WITHOUT_Q_RESIDUE", "Q_PREEXISTING_INVOICE_QUANTITY_REVIEW_REQUIRED", "v_matched+r.qty_invoiced>v_capacity", "v_matched<v_capacity", "x.matched<x.capacity", "'V267_PAYMENT_EXCEEDS_FINAL_AP','V267_INVOICE_MATCH_OVER_RECEIPT'", "edefb0fa134200d5d541bfdb6ab1b4b81e28b8cd912eff0a7c1ef59106744917", "727382a2c3b8464526bb5a8a66c68813be439fb931ca94d993898fecc1e41faf", "351dc9ea86baa9cda11047468f58db5f69044c9860ce5ca7315dcc9ec6e1acd5", "04115f87a2dd4777a56ed3667b461f71fb972887eccd1c9b5281878660a3acc3"]) assert.ok(migration.includes(token),token)
for(const token of ['jsonb_object_keys(v_expected))<>67','Q_POST_USE_ROLLBACK_REFUSED','Q_TRUSTED_PREDECESSOR_PIN_MISMATCH']) assert.ok(rollback.includes(token),token)
const runner=read('scripts/cp6_v2620q_supplier_invoice_exact_quantity_regression.py')
for(const name of ["OVER_ONE_MICRO", "SPLIT_OVER_ONE_MICRO", "RETURN_ADJUSTED_OVER_ONE_MICRO", "MICRO_REMAINDER_STATUS", "REVERSED_COMPLETION_STATUS", "DETECTOR_MICRO_OVER", "DETECTOR_MICRO_STATUS", "EXACT_CAPACITY", "EXACT_SPLIT_COMPLETION", "OVER_TWO_MICRO_REFUSED", "FULL_RETURN_MICRO_SPLIT"]) { assert.ok(oracle.includes(name),name); assert.ok(runner.includes(name),name) }
const workflow=read('.github/workflows/cp6-full-schema-validation.yml')
const runtimeCoverage=workflow.slice(workflow.indexOf('      - name: Confirm every broad regression'),workflow.indexOf('      - name: Re-prove native C01-C06'))
const ledgerCounts=[...runtimeCoverage.matchAll(/where (?:version|name) in\(([^)]+)\).* = '(\d+)'/g)]
assert.equal(ledgerCounts.length,3,'all three runtime ledger checks are required')
for(const [,names,count] of ledgerCounts) assert.equal(names.split(',').length,Number(count),'runtime ledger count must match its pinned generations')
let previous=-1
for(const token of ["Apply v2.6.20p supplier return match", "Reproduce independent P exact supplier invoice quantity", "Apply v2.6.20q exact supplier invoice quantity", "Run post-CP6 real Auth", "Prove native Q exact supplier invoice quantity", "Qualify exact F G H I J K L M N O P Q R and S rollback", "Prove trusted Q capsule", "Prove trusted P capsule"]) {const at=workflow.indexOf(token);assert.ok(at>previous,token);previous=at}
for(const token of ["len(schedules['cases'])==280", "'expected':70,'observed':70", "setup_unit['completed_case_count']==setup_unit['expected_case_count']==118", "sum(c['upgrade_guard']['invalid_history_refused'] for c in q_before['cases'].values())==5", "CP6_V2620S_RUNTIME_MANIFEST.json", "CP6_V2620Q_SUPPLIER_INVOICE_QUANTITY_REGRESSION.json", "PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620S", "CP6_M_RACE_SOURCE_GENERATION: S"]) assert.ok(workflow.includes(token),token)
for(const path of ["docs/cp6-q-supplier-invoice-exact-quantity.md", "scripts/check-cp6-supplier-invoice-exact-quantity.mjs", "scripts/cp6_v2620q_runtime.py", "scripts/cp6_v2620q_supplier_invoice_exact_quantity_regression.py", "scripts/cp6_v2620q_rollback_guards.py", "supabase/migrations/20260912084719_erp_v2_6_20q_cp6_supplier_invoice_exact_quantity.sql", "supabase/rollbacks/20260912084719_erp_v2_6_20q_cp6_supplier_invoice_exact_quantity.rollback.sql", "supabase/tests/cp6_supplier_invoice_exact_quantity.sql"]) assert.ok(workflow.includes("            '"+path+"',"),path)
console.log(JSON.stringify({status:'PASS',classification:'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',replaced_functions:4,boundary_tables:67,native_cases:11,known_p_paths:7,controls:4,maintenance_schedules:280,writer_body_entries:70,production_go:false}))
