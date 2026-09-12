import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const read=p=>readFileSync(p,'utf8')
const hash=s=>createHash('sha256').update(s).digest('hex')
const pinned={
  "supabase/migrations/20260912132445_erp_v2_6_20s_cp6_supplier_payment_business_date.sql": "c9e35612100f0e387a7fdb80fda382ea1212df0cf5200ebceeaf67df9f77cf1f",
  "supabase/rollbacks/20260912132445_erp_v2_6_20s_cp6_supplier_payment_business_date.rollback.sql": "0711ddf3bb3fff97b27e3f576c1875aa34d7d16a4a018155a5ea2f24cbb2f66e",
  "supabase/tests/cp6_supplier_payment_business_date.sql": "49891a24dc73cc77d49e603fc550a6ecb284164b5d24074b7684fa29eb78622f",
  "supabase/migrations/20260912114635_erp_v2_6_20r_cp6_receipt_invoice_dependency.sql": "0c5551ef49da417310e0bcf8c8aa9d655f551ff66ca6e7ca79679ffd331f788b",
  "supabase/rollbacks/20260912114635_erp_v2_6_20r_cp6_receipt_invoice_dependency.rollback.sql": "ec3663694758cffef6509a4bc560aad257dd30b46be236c38abd4bf7c0e7e33e"
}
for(const [p,sha] of Object.entries(pinned)) assert.equal(hash(read(p)),sha,p)
const migration=read(Object.keys(pinned)[0]),rollback=read(Object.keys(pinned)[1]),oracle=read(Object.keys(pinned)[2])
for(const token of ['S_REQUIRES_EXACT_R_WITHOUT_S_RESIDUE','S_PREEXISTING_PAYMENT_DATE_REVIEW_REQUIRED',"erp.post_journal('SUPPLIER_PAYMENT',p.id,erp._cp3_business_date(p.payment_date),",'V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE',"or r.check_name like 'V2620S_%'",...["2eb47603dcfefe58ea89e8f3cf832aca187f397d66b99bd7a4ab3bb5d6c428ad", "ad780c4b00261b6ee1890391cac1c459c23d06b041859399e6ccc2f73d67f421", "e5f4d8749851824e11bb7b76bb3614963aa26feca7034962f47cc198a7962e89"]]) assert.ok(migration.includes(token),token)
for(const token of ['jsonb_object_keys(v_expected))<>69','S_POST_USE_ROLLBACK_REFUSED','S_TRUSTED_PREDECESSOR_PIN_MISMATCH','FG_HPP_SALES_V2620C']) assert.ok(rollback.includes(token),token)
const runner=read('scripts/cp6_v2620s_supplier_payment_business_date_regression.py')
for(const name of ["UTC_LOCAL_MIDNIGHT", "NEW_YORK_LOCAL_MIDNIGHT", "UTC_EVENING", "REVERSED_WRONG_ORIGINAL", "DETECTOR_POSTED_DATE", "DETECTOR_REVERSED_DATE", "JAKARTA_LOCAL_MIDNIGHT", "TOKYO_LOCAL_MIDNIGHT", "MIDDAY_UTC", "EQUIVALENT_OFFSET", "DRAFT_NO_JOURNAL", "OVERPAY_ATOMIC"]) {assert.ok(oracle.includes(name),name);assert.ok(runner.includes(name),name)}
for(const g of ['m','n','o','p','q','r']) assert.ok(read(`scripts/cp6_v2620${g}_runtime.py`).includes('pre_s_installed_sha256'),g)
assert.ok(read('scripts/cp6_v2620m_runtime.py').includes("payment_identity = 'erp.post_supplier_payment(uuid)'"))
assert.ok(read('scripts/cp6_v2620r_runtime.py').includes("s_runtime.predecessor_snapshot(cur, 'R', successor)"))
assert.ok(read('scripts/cp6_v2620s_runtime.py').includes('_cp3_business_date(timestamp with time zone)'))
const workflow=read('.github/workflows/cp6-full-schema-validation.yml')
const coverage=workflow.slice(workflow.indexOf('      - name: Confirm every broad regression'),workflow.indexOf('      - name: Re-prove native C01-C06'))
const counts=[...coverage.matchAll(/where (?:version|name) in\(([^)]+)\).* = '(\d+)'/g)]
assert.equal(counts.length,3);for(const [,names,count] of counts)assert.equal(names.split(',').length,Number(count))
let previous=-1
for(const token of ['Apply v2.6.20r receipt invoice dependency','Reproduce independent R supplier payment business-date','Apply v2.6.20s supplier payment canonical business date','Run post-CP6 real Auth','Prove native S supplier payment canonical business date','Qualify exact F G H I J K L M N O P Q R S and T rollback','Prove trusted S capsule','Prove trusted R capsule']) {const at=workflow.indexOf(token);assert.ok(at>previous,token);previous=at}
for(const token of ["len(schedules['cases'])==300","'expected':75,'observed':75","setup_unit['completed_case_count']==setup_unit['expected_case_count']==134","sum(c['upgrade_guard']['invalid_history_refused'] for c in s_before['cases'].values())==4",'CP6_V2620T_RUNTIME_MANIFEST.json','CP6_V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE_REGRESSION.json','PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620T','CP6_M_RACE_SOURCE_GENERATION: T',"rr['source_generation']=='T'"])assert.ok(workflow.includes(token),token)
for(const p of ["docs/cp6-s-supplier-payment-business-date.md", "scripts/check-cp6-supplier-payment-business-date.mjs", "scripts/cp6_v2620s_runtime.py", "scripts/cp6_v2620s_supplier_payment_business_date_regression.py", "scripts/cp6_v2620s_rollback_guards.py", "supabase/migrations/20260912132445_erp_v2_6_20s_cp6_supplier_payment_business_date.sql", "supabase/rollbacks/20260912132445_erp_v2_6_20s_cp6_supplier_payment_business_date.rollback.sql", "supabase/tests/cp6_supplier_payment_business_date.sql"])assert.ok(workflow.includes("            '"+p+"',"),p)
console.log(JSON.stringify({status:'PASS',classification:'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',replaced_functions:3,boundary_tables:69,native_cases:12,known_r_paths:6,controls:6,maintenance_schedules:300,writer_body_entries:75,production_go:false}))
