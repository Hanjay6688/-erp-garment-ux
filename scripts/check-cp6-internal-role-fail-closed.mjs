import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const read=p=>readFileSync(p,'utf8'),sha=s=>createHash('sha256').update(s).digest('hex')
const migrationPath='supabase/migrations/20260913202948_erp_v2_6_20x_cp6_internal_role_fail_closed.sql'
const rollbackPath='supabase/rollbacks/20260913224854_erp_v2_6_20x_cp6_internal_role_fail_closed_rollback_r2.rollback.sql'
const frozenRollbackPath='supabase/rollbacks/20260913202948_erp_v2_6_20x_cp6_internal_role_fail_closed.rollback.sql'
const migration=read(migrationPath),rollback=read(rollbackPath)
const frozenRollback=read(frozenRollbackPath)
const originalSelector="select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620x_rollback_capsule') order by c.relname"
const qualifiedSelector="select relation.relname from pg_class relation join pg_namespace namespace on namespace.oid=relation.relnamespace where namespace.nspname='erp' and relation.relkind in('r','p') and relation.relname not in('schema_migrations','cp6_v2620x_rollback_capsule') order by relation.relname"
const originalBody=rollback.slice(rollback.indexOf('-- REVIEWED PRE-USE ROLLBACK:'))
assert.equal(frozenRollback.split(originalSelector).length-1,3)
assert.equal(originalBody.split(qualifiedSelector).length-1,3)
assert.equal(originalBody.replaceAll(qualifiedSelector,originalSelector),frozenRollback,'R2 must preserve every other rollback byte')
for(const [p,h,n] of [
 [migrationPath,'53af147202671e5919a49080ed135ab9896399867bbb71065ef2da57f6543117',22114],
 [frozenRollbackPath,'8107dc0d884ee624328b2a0a4c7fd03bed4e8d88f428282a7c00660c43b4200a',10723],
 [rollbackPath,'915fbba9398885e1ce4deef0650c38d6237729781c5985beb2acdec0c911e43a',11356],
 ['supabase/migrations/20260913173840_erp_v2_6_20w_cp6_scrap_business_date.sql','ed858948f60990578ceeb9cbc94a3748b928fae0dcf32a8474079cd7ce31fe08',21930],
 ['supabase/rollbacks/20260913173840_erp_v2_6_20w_cp6_scrap_business_date.rollback.sql','07fcf6c91efe03eea30fb4c1ed3635c6d63421f73407e4d2054ee92861b31153',12904],
]){assert.equal(sha(read(p)),h,p);assert.equal(Buffer.byteLength(read(p)),n,p)}
for(const t of ['X_REQUIRES_EXACT_W_WITHOUT_X_RESIDUE','X_INTERNAL_ROLE_GUARD_ANCHOR',
 "if coalesce(v_app_role,'') not in('OWNER','ADMIN','STAFF') then",'X_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH',
 'count(*) from erp.cp6_v2620x_rollback_capsule)<>1',
 'revoke all on erp.cp6_v2620x_rollback_capsule from public,anon,authenticated,service_role;'])assert.ok(migration.includes(t),t)
for(const t of ['jsonb_object_keys(v_expected))<>209','X_POST_USE_ROLLBACK_REFUSED','X_TRUSTED_PREDECESSOR_PIN_MISMATCH',
 'X_ROLLBACK_RESTORE_HASH_MISMATCH','X_ROLLBACK_POSTCONDITION_FUNCTION_MISMATCH',
 'drop table erp.cp6_v2620x_rollback_capsule;'])assert.ok(rollback.includes(t),t)
for(const p of ['erp.current_app_role()','erp.current_app_user_id()','erp.has_permission(text)','erp._idempotency_actor_key()'])assert.ok(migration.includes(p),p)
const runner=read('scripts/cp6_v2620x_internal_role_regression.py')
for(const t of ['BEFORE_X','AFTER_X','KNOWN_W_AUTH_BUG_REPRODUCED','UNMAPPED_SUBJECT','MISSING_SUBJECT','INACTIVE_USER','INACTIVE_ROLE',
 'SPOOFED_APP_ROLE','INACTIVE_LEGACY_STAFF','EXTERNAL_ROLE','OWNER_CONTROL','ADMIN_CONTROL','STAFF_CONTROL','X_ACTOR_ORACLE',
 'X_EXPECTED_INACTIVE_LEGACY_STAFF_BASELINE','X_ROLE_FIXTURE_ACTIVITY_MISMATCH','conditional_disposable_role_activation',
 'X_REFUSAL_NOT_ATOMIC','entire_unseeded_runtime_restored','schema_usage_restored','X_EXACT_DISPOSABLE_ENDPOINT_REQUIRED'])assert.ok(runner.includes(t),t)
const maintenance=read('scripts/cp6_preuse_rollback_maintenance.py')
for(const t of ["'X': {","'capsule_count': 1",sha(rollback),'from cp6_v2620x_runtime import verify_extra_objects'])assert.ok(maintenance.includes(t),t)
const workflow=read('.github/workflows/cp6-full-schema-validation.yml');let previous=-1
for(const t of ['Apply v2.6.20w canonical','Reproduce W NULL-role posting before X','Apply v2.6.20x fail-closed internal role',
 'Prove X internal-role denial','Prove native W paid scrap dates','Prove native V cash dates','Prove native U canonical',
 'Run post-CP6 real Auth','Qualify exact F G H I J K L M N O P Q R S T U V W X Y and Z rollback',
 'Prove trusted X capsule before exact X restore to W','Prove trusted W capsule before exact W restore to V']){
 const at=workflow.indexOf(t);assert.ok(at>previous,t);previous=at
}
for(const t of ["len(schedules['cases'])==420","'expected':105,'observed':105",'CP6_V2620Z_RUNTIME_MANIFEST.json',
 "setup_unit['completed_case_count']==setup_unit['expected_case_count']==251","len(xg['guards'])==8","len(xg['extra_object_preflight_guards'])==11",
 "x_restore['complete_function_count']==533",'X_COMPLETE_W_CATALOG_RESTORE_MISMATCH','PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620Z',
 "'v2620x_application'","'v2620x_platform'","'v2620x_capsule'",'FAIL_P2_NULL_INTERNAL_ROLE_AUTHORIZATION',
 '2a0781380132b2967a34017c4743727ed5ab24e332dba0051802f139ffa27606'])assert.ok(workflow.includes(t),t)
for(const p of [migrationPath,rollbackPath,frozenRollbackPath,'scripts/cp6_v2620x_runtime.py','scripts/cp6_v2620x_internal_role_regression.py',
 'scripts/cp6_v2620x_rollback_guards.py','scripts/check-cp6-internal-role-fail-closed.mjs','docs/cp6-x-internal-role-fail-closed.md'])assert.ok(workflow.includes(`            '${p}',`),p)
console.log(JSON.stringify({status:'PASS',classification:'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',replaced_functions:1,
 rollback_revision:'R2',frozen_original_rollback_preserved:true,qualified_catalog_aliases:3,
 boundary_tables:209,paired_cases:10,known_null_role_paths:6,controls:4,after_denials:7,authorized_controls:3,
 maintenance_schedules:420,writer_body_entries:105,rollback_setup_units:251,production_go:false}))
