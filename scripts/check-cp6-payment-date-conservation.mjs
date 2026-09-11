import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const read=p=>readFileSync(p,'utf8')
const name='20260911023222_erp_v2_6_20k_cp6_payment_date_conservation'
const migration=read(`supabase/migrations/${name}.sql`)
const rollback=read(`supabase/rollbacks/${name}.rollback.sql`)
const hash=x=>createHash('sha256').update(x).digest('hex')
assert.equal(hash(migration),'567ede242847e7f0a428e673f896d61886f4cbb23e8bb55becf06c34a358b880')
assert.equal(hash(rollback),'9c08f543e4635d59f5e65857a0e3c13f76f52af019eccbe249acc313aac8f01d')
assert.equal((migration.match(/alter function .* set timezone='UTC';/g)||[]).length,4)
assert.ok(migration.includes('j.transaction_date is distinct from prior_reversal.reversal_transaction_date'))
assert.ok(migration.includes('K_PREEXISTING_ALLOCATION_DATE_REVIEW_REQUIRED'))
assert.ok(migration.includes('K_PREDECESSOR_CAPSULE_SOURCE_PIN_MISMATCH'))
assert.doesNotMatch(migration,/\b(?:delete from|truncate|drop table)\b/i)
assert.doesNotMatch(rollback,/\b(?:delete from|drop table|truncate) erp\.(?:sales_|journal_|wip_|fg_|laundry_)/i)
assert.ok(rollback.includes('(select count(*) from jsonb_object_keys(v_expected))<>30'))
const workflow=read('.github/workflows/cp6-full-schema-validation.yml')
const order=['Apply v2.6.20j immutable','Apply v2.6.20k payment date','Run post-CP6 real Auth',
 'Prove native K per-date','Qualify exact F G H I J K L and M rollback','Prove trusted K capsule','Prove trusted J capsule']
let position=-1
for(const label of order){const next=workflow.indexOf(label);assert.ok(next>position,label);position=next}
for(const token of ['CP6_V2620M_RUNTIME_PROOF_V1','CP6_V2620K_PAYMENT_DATE_REGRESSION.json',
 'CP6_V2620K_ROLLBACK_GUARDS.json',"len(schedules['cases'])==160","'expected':40,'observed':40"])
 assert.ok(workflow.includes(token),token)
for(const token of ['LATE_ALLOCATION','MULTI_HOP','COHERENT_DATE_FAULT','ATOMIC_INVALID','CLOSED_PERIOD','TIMEZONE'])
 assert.ok(read('supabase/tests/cp6_payment_date_conservation.sql').includes(token),token)
console.log(JSON.stringify({status:'PASS',classification:'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',production_go:false}))
