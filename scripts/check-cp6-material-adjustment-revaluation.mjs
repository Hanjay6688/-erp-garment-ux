import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const read=p=>readFileSync(p,'utf8')
const hash=s=>createHash('sha256').update(s).digest('hex')
const pinned={
  "supabase/migrations/20260912171034_erp_v2_6_20t_cp6_material_adjustment_revaluation.sql": "e888fa66bd40abda0ba1152662df9d0855193325dcf1c8491d47b522cdd00add",
  "supabase/rollbacks/20260912171034_erp_v2_6_20t_cp6_material_adjustment_revaluation.rollback.sql": "ed8f45bfb46721a5a23381db8ec607b86b7fe2756863dea48f2c8f5fa8db7b56",
  "supabase/tests/cp6_material_adjustment_revaluation.sql": "c670d6598a0f993bd14e1db51c73204350c0ae56b1e58c6df180e510857d253d"
}
for(const [p,sha] of Object.entries(pinned)) assert.equal(hash(read(p)),sha,p)
const [migration,rollback,oracle]=Object.keys(pinned).map(read)
for(const token of ['T_REQUIRES_EXACT_S_WITHOUT_T_RESIDUE','T_TRUSTED_S_FUNCTION_OWNER_ACL_MISMATCH',
  'T_PREEXISTING_ADJUSTMENT_OR_BUSINESS_DATE_REVIEW_REQUIRED',
  'T_PROTECTED_REVALUATION_JOURNAL_USE_SOURCE_WORKFLOW','T_ZERO_NET_INVERSE_ANCHOR',
  'T_REVALUATION_DEAD_BRANCH_ANCHOR','MATERIAL_ADJUSTMENT_REVALUE|',
  'V2620T_MATERIAL_ADJUSTMENT_REVALUATION','V2620T_MATERIAL_ADJUSTMENT_FACT_LEDGER',
  'V2620T_JOURNAL_FUTURE_BUSINESS_DATE',"or r.check_name like 'V2620T_%'",
  'erp._cp3_business_date(current_timestamp)']) assert.ok(migration.includes(token),token)
for(const token of ['jsonb_object_keys(v_expected))<>73','T_POST_USE_ROLLBACK_REFUSED',
  'T_TRUSTED_PREDECESSOR_PIN_MISMATCH','T_ADJUSTMENT_FACT_SECURITY_MISMATCH']) assert.ok(rollback.includes(token),token)
for(const fn of ['_cp6_material_adjustment_revaluation_state(uuid)',
  '_cp6_sync_material_adjustment_revaluation(uuid,uuid)',
  'guard_material_adjustment_revaluation_fact_v2620t()']) assert.ok(rollback.includes('drop function erp.'+fn+';'),fn)
assert.ok(rollback.includes('drop table erp.material_adjustment_revaluation_facts;'))
const runner=read('scripts/cp6_v2620t_material_adjustment_revaluation_regression.py')
const cases=['MULTI_MATERIAL_A_FIRST','MULTI_MATERIAL_B_FIRST','MISSING_NONZERO_JOURNAL',
  'COST_SPLIT','COST_SINGLE_ENDPOINT','COST_HALF_YARD','COST_DECREASE','COST_PARTIAL',
  'COST_SINGLE_ROLL_CONTROL','COST_INTEGER_CONTROL','LINKED_INVERSE','ADJUSTMENT_FIRST_INVERSE',
  'FACT_GUARDS','DETECTOR_COST','ZERO_NET_INVERSE','ZERO_NET_CORRECTED_INVERSE','POSITIVE_CONTROL',
  'REAL_DAY_BOUNDARY','CLOSED_PERIOD_DAY','JAKARTA_TODAY_CONTROL','FUTURE_REFUSAL_CONTROL']
for(const c of cases){assert.ok(oracle.includes(c),c);assert.ok(runner.includes(c),c)}
for(const gen of ['m','n','o','p','q','r','s','t']) assert.ok(read(`scripts/cp6_v2620${gen}_runtime.py`).includes('pre_t_installed_sha256'),gen)
assert.ok(read('scripts/cp6_v2620s_runtime.py').includes("t_runtime.predecessor_snapshot(cur, 'S', successor)"))
const races=read('scripts/cp6_v2620t_material_adjustment_races.py')
for(const token of ['MATERIAL_A_FIRST','MATERIAL_B_FIRST','MATERIAL_A_ABORT','pg_blocking_pids(pid)',
  "matrix.verify_setup_source('T')",'first.rollback()','idempotent_replay']) assert.ok(races.includes(token),token)
const matrix=read('scripts/cp6_v2620h_maintenance_rollback_matrix.py')
for(const token of ['expected_body_entries = len(TARGETS) * len(OPERATIONS)',
  "'expected': expected_body_entries",'writer_first_body_entry == expected_body_entries'])
  assert.ok(matrix.includes(token),`matrix aggregate count contract: ${token}`)
const workflow=read('.github/workflows/cp6-full-schema-validation.yml')
const countJsonbBuildObjectArgs=(source,callAt)=>{
  const open=source.indexOf('(',callAt)
  assert.ok(open>=0,'jsonb_build_object opening parenthesis')
  let depth=0,inString=false,args=1
  for(let i=open+1;i<source.length;i++){
    const char=source[i]
    if(inString){
      if(char==="'"&&source[i+1]==="'"){i++;continue}
      if(char==="'") inString=false
      continue
    }
    if(char==="'"){inString=true;continue}
    if(char==='('){depth++;continue}
    if(char===')'){
      if(depth===0) return {args,end:i}
      depth--;continue
    }
    if(char===','&&depth===0) args++
  }
  assert.fail('unterminated jsonb_build_object call')
}
const finalGate=workflow.indexOf('Record final no-residue and no-production-GO boundary')
const firstBuilderAt=workflow.indexOf('jsonb_build_object(',finalGate)
const firstBuilder=countJsonbBuildObjectArgs(workflow,firstBuilderAt)
const secondBuilderAt=workflow.indexOf('jsonb_build_object(',firstBuilder.end)
const secondBuilder=countJsonbBuildObjectArgs(workflow,secondBuilderAt)
for(const [name,builder] of [['first',firstBuilder],['second',secondBuilder]]){
  assert.ok(builder.args<=100,`${name} final JSON builder exceeds PostgreSQL argument limit`)
  assert.equal(builder.args%2,0,`${name} final JSON builder has an unmatched key/value argument`)
}
assert.deepEqual([firstBuilder.args,secondBuilder.args],[60,60],
  'final reconciliation JSON split drifted')
let previous=-1
for(const token of ['Apply v2.6.20s supplier payment canonical business date',
  'Reproduce independent S material adjustment and accounting-day',
  'Apply v2.6.20t material adjustment document cents','Run post-CP6 real Auth',
  'Prove native T material adjustment document cents','Prove native T shared adjustment',
  'Qualify exact F G H I J K L M N O P Q R S and T rollback',
  'Prove trusted T capsule','Prove trusted S capsule']){
  const at=workflow.indexOf(token);assert.ok(at>previous,token);previous=at
}
for(const token of ["len(schedules['cases'])==300","'expected':75,'observed':75",
  "setup_unit['completed_case_count']==setup_unit['expected_case_count']==134",
  'CP6_V2620T_RUNTIME_MANIFEST.json','CP6_V2620T_MATERIAL_ADJUSTMENT_REVALUATION_REGRESSION.json',
  'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620T','CP6_M_RACE_SOURCE_GENERATION: T',
  "len(tr['cases'])==3","len(tp['cases'])==21","len(tg['extra_object_preflight_guards'])==9",
  'T_COMPLETE_S_CATALOG_RESTORE_MISMATCH',') || jsonb_build_object(',
  "to_regclass('erp.cp6_v2620t_rollback_capsule') is null",
  "to_regclass('erp.material_adjustment_revaluation_facts') is null",
  "to_regprocedure('erp._cp6_material_adjustment_revaluation_state(uuid)') is null",
  "to_regprocedure('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)') is null",
  "to_regprocedure('erp.guard_material_adjustment_revaluation_fact_v2620t()') is null",
  "'v2620t_fact_guard',to_regprocedure('erp.guard_material_adjustment_revaluation_fact_v2620t()') is not null",
  'compression-level: 9'])
  assert.ok(workflow.includes(token),token)
for(const p of [...Object.keys(pinned),'docs/cp6-t-material-adjustment-revaluation.md',
  'scripts/check-cp6-material-adjustment-revaluation.mjs','scripts/cp6_v2620t_runtime.py',
  'scripts/cp6_v2620t_material_adjustment_revaluation_regression.py','scripts/cp6_v2620t_rollback_guards.py',
  'scripts/cp6_v2620t_material_adjustment_races.py']) assert.ok(workflow.includes("            '"+p+"',"),p)
console.log(JSON.stringify({status:'PASS',classification:'STATIC_SOURCE_CONTRACT_NOT_NATIVE_PROOF',
  replaced_functions:6,new_private_functions:3,boundary_tables:73,native_cases:21,
  known_s_paths:15,controls:6,shared_document_native_races:3,maintenance_schedules:300,
  writer_body_entries:75,production_go:false}))
