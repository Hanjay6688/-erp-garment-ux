import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const read=p=>readFileSync(p,'utf8')
const hash=s=>createHash('sha256').update(s).digest('hex')
const name='20260911070622_erp_v2_6_20l_cp6_exact_ledger_conservation'
const migration=read(`supabase/migrations/${name}.sql`)
const rollback=read(`supabase/rollbacks/${name}.rollback.sql`)
assert.equal(hash(migration),'f46e70911e9e582fa9b7dd742c9a94d455662fa52eac256afd86f590f4d4b815')
assert.equal(hash(rollback),'d6aa1e6bf6aa0dc4d2fffc7cf2432dd1f6e8eed89bfe0471cad0ebbfb7e58531')
for(const token of ['L_PREDECESSOR_K_CAPSULE_SOURCE_PIN_MISMATCH',
 'L_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH','JOURNAL_FINITE_NONNEGATIVE_MONEY_REQUIRED',
 'V2620L_NONFINITE_LEDGER_MONEY','V2620L_NEGATIVE_VENDOR_AP',
 'L_PREEXISTING_LEDGER_REVIEW_REQUIRED','v_ap_balance<c.compensation_amount'])
 assert.ok(migration.includes(token),token)
assert.doesNotMatch(migration,/\b(?:delete from|truncate|drop table)\b/i)
assert.doesNotMatch(rollback,/\b(?:delete from|drop table|truncate) erp\.(?:sales_|journal_|wip_|fg_|laundry_)/i)
assert.ok(rollback.includes('(select count(*) from jsonb_object_keys(v_expected))<>37'))
const workflow=read('.github/workflows/cp6-full-schema-validation.yml')
const authTarget=read('scripts/cp6_auth_permission_e2e.mjs').match(/target: '([^']+)'/)?.[1]
assert.equal(authTarget,'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620M')
assert.equal(workflow.match(/assert report\['target'\]=='([^']+)'/)?.[1],authTarget,
 'Native Auth producer and workflow validator must bind the same generation')
let previous=-1
for(const label of ['Apply v2.6.20k payment date','Reproduce independent K ledger',
 'Apply v2.6.20l exact ledger','Run post-CP6 real Auth','Prove native L exact money',
 'Qualify exact F G H I J K L and M rollback','Prove trusted L capsule','Prove trusted K capsule']) {
 const position=workflow.indexOf(label);assert.ok(position>previous,label);previous=position
}
for(const token of ['CP6_V2620M_RUNTIME_PROOF_V1',"len(schedules['cases'])==160",
 "'expected':40,'observed':40",'CP6_V2620L_K_COUNTEREXAMPLES.json',
 'CP6_V2620L_LEDGER_REGRESSION.json',"len(l['cases'])==15", "'v2620l_restored_function_owner_acl_count':3"])
 assert.ok(workflow.includes(token),token)
const sql=read('supabase/tests/cp6_exact_ledger_conservation.sql')
for(const token of ['CENT_CONTROL','NORMALIZED_CONTROL','SPLIT_HALF_CENT','NONFINITE',
 'NEGATIVE_INPUT','MALFORMED_LINES','CACHE_CENT','JOURNAL_WASH','EMPTY_JOURNAL',
 'NONFINITE_CACHE','NEGATIVE_AP_FAULT','AP_OVERDRAW','AP_ZERO_CONTROL',
 'CLAIM_OVERDRAW','CLAIM_ZERO_CONTROL','KNOWN_K_BUG_REPRODUCED'])assert.ok(sql.includes(token),token)
assert.ok(read('scripts/cp6_v2620h_adversarial_regression.py').includes('l_runtime.extend_items(l_successor, functions)'))
console.log(JSON.stringify({status:'PASS',classification:'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',production_go:false}))
