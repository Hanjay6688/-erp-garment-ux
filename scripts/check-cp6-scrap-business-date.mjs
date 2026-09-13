import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const read=p=>readFileSync(p,'utf8'),sha=s=>createHash('sha256').update(s).digest('hex')
const migrationPath='supabase/migrations/20260913173840_erp_v2_6_20w_cp6_scrap_business_date.sql'
const rollbackPath='supabase/rollbacks/20260913173840_erp_v2_6_20w_cp6_scrap_business_date.rollback.sql'
const migration=read(migrationPath),rollback=read(rollbackPath)
for(const [path,hash,bytes] of [
 [migrationPath,'ed858948f60990578ceeb9cbc94a3748b928fae0dcf32a8474079cd7ce31fe08',21930],
 [rollbackPath,'07fcf6c91efe03eea30fb4c1ed3635c6d63421f73407e4d2054ee92861b31153',12904],
 ['supabase/migrations/20260913135850_erp_v2_6_20v_cp6_misc_finance_business_date.sql','3bd29c1280e09bd8d36e8303c4e5e4cfdd2be951c3f852c8ce38fe170ab3648d',19196],
 ['supabase/rollbacks/20260913135850_erp_v2_6_20v_cp6_misc_finance_business_date.rollback.sql','4fb8f0ded3e452dca1d44214711bd79ffcf0f3b68d956283da9bbce5e4444f7b',12741],
 ['scripts/cp6_v2620v_scrap_adversarial.py','8e1e2ceee9cdf71fb7d0c670d2097fafa4185b4548e786a8b2370aad611c67c5',13100],
]){assert.equal(sha(read(path)),hash,path);assert.equal(Buffer.byteLength(read(path)),bytes,path)}
for(const token of ['W_REQUIRES_EXACT_V_WITHOUT_W_RESIDUE','W_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED',
 'W_TRUSTED_U_FUNCTION_OWNER_ACL_MISMATCH','W_TRUSTED_V_FUNCTION_OWNER_ACL_MISMATCH',
 'W_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH','W_INHERITED_T_SECURITY_MISMATCH',
 'W_FINANCIAL_REPORT_SCOPE_NOT_CONNECTED','W_SCRAP_DAY_ANCHOR','V2620W_SCRAP_BUSINESS_DATE',
 'erp._cp3_business_date(s.physical_at)',"or r.check_name like 'V2620W_%'",'count(*) from erp.cp6_v2620w_rollback_capsule)<>3',
 'revoke all on erp.cp6_v2620w_rollback_capsule from public,anon,authenticated,service_role;'])assert.ok(migration.includes(token),token)
for(const token of ['jsonb_object_keys(v_expected))<>80','W_POST_USE_ROLLBACK_REFUSED','W_TRUSTED_PREDECESSOR_PIN_MISMATCH',
 'W_ROLLBACK_RESTORE_HASH_MISMATCH','W_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH',"'cp6_v2620v_rollback_capsule','scrap_batches','scrap_sales'",
 'drop table erp.cp6_v2620w_rollback_capsule;'])assert.ok(rollback.includes(token),token)
const runner=read('scripts/cp6_v2620w_scrap_business_date_regression.py')
for(const token of ["phase not in ('BEFORE_W','AFTER_W')","'KNOWN_V_BUG_REPRODUCED'",'shared.identity',
 'full_boundary_restored','entire_unseeded_runtime_restored','W_UPGRADE_PROBE_LEFT_RESIDUE','CLOSED_PERIOD_ECONOMIC_DATE',
 'DETECTOR_REVERSED','ACL_CONTRACT','REVERSE_REPLAY','NON_OWNER_POST_DENIED','QUANTITY_OVER_CAPACITY',
 'FULL_WEIGHT_REVERSE','supabase_admin','W_EXACT_DISPOSABLE_ENDPOINT_REQUIRED'])assert.ok(runner.includes(token),token)
const races=read('scripts/cp6_v2620w_scrap_races.py')
for(const token of ['POST_THEN_REVERSE','POST_THEN_POST','POST_ABORT_THEN_POST','pg_blocking_pids(pid)',
 "SOURCE_GENERATION = 'X'",'matrix.verify_setup_source(SOURCE_GENERATION)','first.rollback()',
 'manual_prelock_count=0,retry_count=0','REAL_AUTHENTICATED_SESSION_OWNER'])assert.ok(races.includes(token),token)
for(const g of ['m','n','o','p','q','r','s','t','u','v'])assert.ok(read(`scripts/cp6_v2620${g}_runtime.py`).includes('pre_w_installed_sha256'),g)
assert.ok(read('scripts/cp6_v2620v_runtime.py').includes("w_runtime.predecessor_snapshot(cur, 'V', successor)"))
const maintenance=read('scripts/cp6_preuse_rollback_maintenance.py')
for(const token of ["'W': {","'capsule_count': 3","'predecessor': 'v2.6.20v'",sha(rollback),
 'from cp6_v2620w_runtime import verify_extra_objects'])assert.ok(maintenance.includes(token),token)
const workflow=read('.github/workflows/cp6-full-schema-validation.yml')
let previous=-1
for(const token of ['Apply v2.6.20v canonical','Reproduce native V paid scrap counterexamples before W',
 'Apply v2.6.20w canonical paid scrap','Prove native W paid scrap dates','Prove native V cash dates',
 'Prove native U canonical','Run post-CP6 real Auth','Prove native W paid scrap document races',
 'Qualify exact F G H I J K L M N O P Q R S T U V W and X rollback',
 'Prove trusted W capsule before exact W restore to V','Prove trusted V capsule before exact V restore to U']){
 const at=workflow.indexOf(token);assert.ok(at>previous,token);previous=at
}
for(const token of ["len(schedules['cases'])==380","'expected':95,'observed':95",'CP6_V2620X_RUNTIME_MANIFEST.json',
 "len(wp['expanded_cases'])==21","len(wr['cases'])==3","len(wg['guards'])==7","len(wg['extra_object_preflight_guards'])==9",
 'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620X','W_COMPLETE_V_CATALOG_RESTORE_MISMATCH',
 "setup_unit['completed_case_count']==setup_unit['expected_case_count']==208",
 "sum(c['status']=='KNOWN_V_BUG_REPRODUCED' for c in wb['cases'].values())==2",
 "w_restore['complete_function_count']==533","'v2620w_application'","'v2620w_platform'","'v2620w_capsule'",
 "and to_regclass('erp.cp6_v2620w_rollback_capsule') is null",'FAIL_P2_SCRAP_CASH_BUSINESS_DATE',
 'bc44b878844b6f7f31a87510d54cc9fe14f16e703bbbfe50c1584624844e25d5'])assert.ok(workflow.includes(token),token)
for(const path of [migrationPath,rollbackPath,'docs/cp6-w-scrap-business-date.md',
 'scripts/check-cp6-scrap-business-date.mjs','scripts/cp6_v2620w_runtime.py',
 'scripts/cp6_v2620w_scrap_business_date_regression.py','scripts/cp6_v2620w_scrap_races.py',
 'scripts/cp6_v2620w_rollback_guards.py','scripts/cp6_v2620v_scrap_adversarial.py'])assert.ok(workflow.includes(`            '${path}',`),path)
console.log(JSON.stringify({status:'PASS',classification:'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',replaced_functions:3,
 boundary_tables:80,native_cases:4,expanded_native_cases:21,known_v_paths:2,controls:2,native_document_races:3,
 maintenance_schedules:380,writer_body_entries:95,rollback_setup_units:208,production_go:false}))
