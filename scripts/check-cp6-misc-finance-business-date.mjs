import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const read=p=>readFileSync(p,'utf8'),sha=s=>createHash('sha256').update(s).digest('hex')
const migrationPath='supabase/migrations/20260913135850_erp_v2_6_20v_cp6_misc_finance_business_date.sql'
const rollbackPath='supabase/rollbacks/20260913135850_erp_v2_6_20v_cp6_misc_finance_business_date.rollback.sql'
const migration=read(migrationPath),rollback=read(rollbackPath)
for(const [path,hash,bytes] of [
 [migrationPath,'3bd29c1280e09bd8d36e8303c4e5e4cfdd2be951c3f852c8ce38fe170ab3648d',19196],
 [rollbackPath,'4fb8f0ded3e452dca1d44214711bd79ffcf0f3b68d956283da9bbce5e4444f7b',12741],
 ['supabase/migrations/20260913070000_erp_v2_6_20u_cp6_canonical_business_date.sql','972b5189a065e078590c0742f67722684eb14a1d0df21f5fb1ebd42bf7f3bbaa',23568],
 ['supabase/rollbacks/20260913070000_erp_v2_6_20u_cp6_canonical_business_date.rollback.sql','e69035e7402c1d04ee3771145ad19bf3e83d6f303076dabdb8e05b1b251dcd76',14731],
]){assert.equal(sha(read(path)),hash,path);assert.equal(Buffer.byteLength(read(path)),bytes,path)}
for(const token of ['V_REQUIRES_EXACT_U_WITHOUT_V_RESIDUE','V_PREEXISTING_CANONICAL_DATE_REVIEW_REQUIRED',
 'V_TRUSTED_U_FUNCTION_OWNER_ACL_MISMATCH','V_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH','V_INHERITED_T_SECURITY_MISMATCH',
 'V_FINANCIAL_REPORT_SCOPE_NOT_CONNECTED','V_MISC_FINANCE_DAY_ANCHOR','V2620V_MISC_FINANCE_BUSINESS_DATE',
 'erp._cp3_business_date(t.physical_at)',"or r.check_name like 'V2620V_%'",'count(*) from erp.cp6_v2620v_rollback_capsule)<>3',
 'revoke all on erp.cp6_v2620v_rollback_capsule from public,anon,authenticated,service_role;'])assert.ok(migration.includes(token),token)
for(const token of ['jsonb_object_keys(v_expected))<>77','V_POST_USE_ROLLBACK_REFUSED','V_TRUSTED_PREDECESSOR_PIN_MISMATCH',
 'V_ROLLBACK_RESTORE_HASH_MISMATCH','V_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH',"'misc_finance_transactions','misc_finance_categories'",
 'drop table erp.cp6_v2620v_rollback_capsule;'])assert.ok(rollback.includes(token),token)
const runner=read('scripts/cp6_v2620v_misc_finance_business_date_regression.py')
for(const token of ["phase not in ('BEFORE_V','AFTER_V')","'KNOWN_U_BUG_REPRODUCED'",'set session authorization authenticated',
 'full_boundary_restored','entire_unseeded_runtime_restored','V_UPGRADE_PROBE_LEFT_RESIDUE','CLOSED_PERIOD_ECONOMIC_DATE',
 'DETECTOR_REVERSED','ACL_CONTRACT','REVERSE_REPLAY_EXPENSE','NON_OWNER_POST_DENIED','supabase_admin','V_CANONICAL_DISPOSABLE_ENDPOINT_REQUIRED'])assert.ok(runner.includes(token),token)
assert.ok(read('scripts/cp6_v2620m_subledger_races.py').includes("SOURCE_GENERATION not in ('M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X')"), 'M race source admission must include exact verified X')
const races=read('scripts/cp6_v2620v_misc_finance_races.py')
for(const token of ['POST_THEN_REVERSE','POST_THEN_POST','POST_ABORT_THEN_POST','pg_blocking_pids(pid)',
 "SOURCE_GENERATION = 'X'",'matrix.verify_setup_source(SOURCE_GENERATION)','first.rollback()',"manual_prelock_count=0,retry_count=0",'REAL_AUTHENTICATED_SESSION_OWNER'])assert.ok(races.includes(token),token)
for(const g of ['m','n','o','p','q','r','s','t','u'])assert.ok(read(`scripts/cp6_v2620${g}_runtime.py`).includes('pre_v_installed_sha256'),g)
assert.ok(read('scripts/cp6_v2620u_runtime.py').includes("v_runtime.predecessor_snapshot(cur, 'U', successor)"))
const maintenance=read('scripts/cp6_preuse_rollback_maintenance.py')
for(const token of ["'V': {","'capsule_count': 3","'predecessor': 'v2.6.20u'",sha(rollback),
 'from cp6_v2620w_runtime import verify_extra_objects'])assert.ok(maintenance.includes(token),token)
const workflow=read('.github/workflows/cp6-full-schema-validation.yml')
for(const token of ['def cash_delta_equal(expected, actual):','left.is_finite() and right.is_finite() and left == right',
 "cash_delta_equal(d['expected_cash_delta'],d['actual_cash_delta'])",
 "cash_delta_equal(d['expected'],d['actual'])",'cp6_v_failed159_recovery.py --unit',
 'Recover immutable failed159 evidence'])assert.ok(workflow.includes(token),token)
let previous=-1
for(const token of ['Apply v2.6.20u canonical','Reproduce native U misc cash counterexamples before V',
 'Apply v2.6.20v canonical miscellaneous cash','Prove native V cash dates','Prove native U canonical',
 'Run post-CP6 real Auth','Prove native V misc cash document races','Qualify exact F G H I J K L M N O P Q R S T U V W and X rollback',
 'Prove trusted V capsule before exact V restore to U','Prove trusted U capsule before exact U restore to T']){
 const at=workflow.indexOf(token);assert.ok(at>previous,token);previous=at
}
for(const token of ["len(schedules['cases'])==380","'expected':95,'observed':95",'CP6_V2620X_RUNTIME_MANIFEST.json',
 "len(vp['expanded_cases'])==21","len(vr['cases'])==3","len(vg['guards'])==7","len(vg['extra_object_preflight_guards'])==9",
 'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620X','V_COMPLETE_U_CATALOG_RESTORE_MISMATCH',
 'setup_unit[\'completed_case_count\']==setup_unit[\'expected_case_count\']==208'])assert.ok(workflow.includes(token),token)
for(const path of [migrationPath,rollbackPath,'docs/cp6-v-misc-finance-business-date.md',
 'scripts/check-cp6-misc-finance-business-date.mjs','scripts/cp6_v2620v_runtime.py',
 'scripts/cp6_v2620v_misc_finance_business_date_regression.py','scripts/cp6_v2620v_misc_finance_races.py',
 'scripts/cp6_v2620v_rollback_guards.py','scripts/cp6_v_failed159_recovery.py'])assert.ok(workflow.includes(`            '${path}',`),path)
console.log(JSON.stringify({status:'PASS',classification:'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',replaced_functions:3,
 boundary_tables:77,native_cases:8,expanded_native_cases:21,known_u_paths:4,controls:4,native_document_races:3,
 maintenance_schedules:380,writer_body_entries:95,rollback_setup_units:208,production_go:false}))
