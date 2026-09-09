import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
const read = (path) => readFileSync(resolve(root, path), 'utf8')
const sha256 = (value) => createHash('sha256').update(value).digest('hex')
const occurrences = (source, token) => source.split(token).length - 1
const requireTokens = (source, label, tokens) => {
  for (const token of tokens) assert.ok(source.includes(token), `${label} missing: ${token}`)
}

const migrationPath = 'supabase/migrations/20260908160000_erp_v2_6_20d_cp6_reaudit_business_closure.sql'
const rollbackPath = 'supabase/rollbacks/20260908160000_erp_v2_6_20d_cp6_reaudit_business_closure.rollback.sql'
const regressionPath = 'supabase/tests/cp6_v2620d_reaudit_business_closure_rollback.sql'
const workflowPath = '.github/workflows/cp6-full-schema-validation.yml'
const authPath = 'scripts/cp6_auth_permission_e2e.mjs'
const rollbackRacePath = 'scripts/cp6_v2620c_live_rollback_race.py'
const v20cRunnerPath = 'scripts/run_cp6_v2620c_live_rollback_races.sh'
const v20dRunnerPath = 'scripts/run_cp6_v2620d_live_rollback_races.sh'
const clonePath = 'scripts/clone-cp6-disposable-database.sh'

const migration = read(migrationPath)
const rollback = read(rollbackPath)
const regression = read(regressionPath)
const workflow = read(workflowPath)
const auth = read(authPath)
const rollbackRace = read(rollbackRacePath)
const v20cRunner = read(v20cRunnerPath)
const v20dRunner = read(v20dRunnerPath)
const clone = read(clonePath)

const migrationFileSha = 'eab866385d3a462aea5815dc5069d5d7a774f7aa88c43d983c665469f4469465'
const migrationLedgerSha = 'f3f1ba8f889440c8694ba2932fc787ea5bdfab980b2d94f24cd9bfabf1bbf222'
const rollbackFileSha = '793cd96c44c4babcf78789ab01e3e932c04c1598cdc1dbe73afeedba18640fb7'
const regressionFileSha = '4fabe97f112ff8afae94b4e929f4976356edd51fcb8b86b93533ad4ec433fd2a'
const migrationBytes = Buffer.from(migration)

assert.equal(Buffer.byteLength(migration), 85944)
assert.equal(Buffer.byteLength(rollback), 12395)
assert.equal(Buffer.byteLength(regression), 37979)
assert.equal(sha256(migrationBytes), migrationFileSha)
assert.equal(sha256(migrationBytes.subarray(0, -1)), migrationLedgerSha)
assert.equal(sha256(rollback), rollbackFileSha)
assert.equal(sha256(regression), regressionFileSha)
assert.equal(occurrences(rollback, migrationFileSha), 4)
assert.equal(occurrences(rollback, migrationLedgerSha), 4)
assert.ok(occurrences(workflow, migrationFileSha) >= 1)
assert.ok(occurrences(workflow, migrationLedgerSha) >= 1)

for (const [path, sql] of [[migrationPath, migration], [rollbackPath, rollback]]) {
  assert.ok(sql.endsWith('\n'), `${path} must retain its terminal LF`)
  const quoteCounts = new Map()
  for (const match of sql.matchAll(/\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$/g)) {
    quoteCounts.set(match[0], (quoteCounts.get(match[0]) ?? 0) + 1)
  }
  assert.deepEqual([...quoteCounts].filter(([, count]) => count % 2), [],
    `${path} has unbalanced dollar quotes`)
  assert.match(sql, /^begin;$/mi, `${path} must open one transaction`)
  assert.match(sql, /\bcommit;\s*$/i, `${path} must commit once at EOF`)
}
assert.deepEqual(
  readdirSync(resolve(root, 'supabase/migrations')).filter((name) => name.startsWith('20260908160000_')),
  [migrationPath.split('/').at(-1)],
)
assert.deepEqual(
  readdirSync(resolve(root, 'supabase/rollbacks')).filter((name) => name.startsWith('20260908160000_')),
  [rollbackPath.split('/').at(-1)],
)
assert.doesNotMatch(migration, /\btruncate\b|\bdrop\s+(?:table|function|schema|index|trigger)\b/i)
assert.doesNotMatch(migration,
  /delete\s+from\s+erp\.(?:laundry_|qc_|fg_|hpp_|journal_|sales_|sale_|po_)/i)

requireTokens(migration, 'v20d exact boundary and rollback capsule', [
  'Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.',
  "version='v2.6.20c'", "version='v2.6.20d'",
  '1571c09b7a36c2bed7eee35c5c964e5d0a36b1cae08c58e0c74d028911430250',
  'b90cd6c4aa535eb97226d001fdfb5a5bfed783be28ef38dc7c121a7020368aba',
  "('erp.compute_po_hpp_gl_targets(uuid)','3141556f4ac3d68bc55ca2f25182a41ec7d4e7565e5b12daffb38e53dffdf018')",
  'create table erp.cp6_v2620d_rollback_capsule(',
  'alter table erp.cp6_v2620d_rollback_capsule enable row level security;',
  '(select count(*) from erp.cp6_v2620d_rollback_capsule)<>10',
  'installed_definition_sha256',
])

requireTokens(migration, 'B01 physical redispatch cost lineage', [
  'create table erp.laundry_redispatch_participant_allocations(',
  "allocation_basis in('MIGRATION_BACKFILL','LIVE_FIFO')",
  "message='REDISPATCH_PARTICIPANT_LINEAGE_IS_APPEND_ONLY'",
  '(v_source.delivery_at,v_source.delivery_created_at,v_source.delivery_id)',
  '>=(v_successor.delivery_at,v_successor.delivery_created_at,v_successor.delivery_id)',
  '(ld.physical_at,ld.created_at,ld.id)',
  '<(d.successor_at,d.successor_created_at,d.successor_delivery_id)',
  'order by ld.physical_at,ld.created_at,ld.id,sx.size_id,sx.id',
  'create function erp.allocate_laundry_redispatch_participants_v2620d(p_delivery_line_id uuid)',
  "where version='v2.6.20d'",
  "DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20d redispatch allocator is missing",
  'perform erp.allocate_laundry_redispatch_participants_v2620d(v_delivery_line_id);',
  'create function erp.cp6_lot_failed_wash_cost_v2620d(p_lot_id uuid)',
  'not a.source_delivery_batch_size_line_id=any(m.path)',
  "erp.cp6_lot_failed_wash_cost_v2620d(r.id)",
  "'V2620D_REDISPATCH_PARTICIPANT_LINEAGE_MISMATCH'",
])
assert.doesNotMatch(migration, /cardinality\([^\n]*path[^\n]*\)\s*<\s*128/i,
  'Physical redispatch lineage may not silently truncate after 128 legs')

requireTokens(migration, 'B03 conserved minor-unit HPP', [
  'create function erp.compute_po_hpp_gl_targets_v2620d(p_po_id uuid)',
  'round(coalesce(cogs_value,0)+coalesce(other_out_value,0),2)::numeric total_out',
  'select qty,hpp,(hpp-total_out)::numeric,cogs,(total_out-cogs)::numeric',
  'create function erp.sale_lifecycle_po_hpp_amount_v2620d(',
  'sum(raw_value) over(order by po_id rows unbounded preceding) cumulative_value',
  'create function erp.compute_po_hpp_gl_book_v2620d(p_po_id uuid)',
  "'Sales to customer/toko · cumulative exact HPP target'",
  "'Sales return from customer · cumulative exact HPP target'",
  "'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH'",
])

requireTokens(migration, 'B02 signed posting-period report reconciliation', [
  'with sale_events as(', 'with return_events as(',
  "original.status in('POSTED','REVERSED')",
  'v_operational_net_sales:=round(v_gross_sales-v_discounts-v_sales_returns,2);',
  'v_sales_revenue_bridge:=round(v_operational_net_sales-v_sales_revenue,2);',
  "'V2620D_PERIOD_SALES_REVENUE_BRIDGE_MISMATCH'",
  "when v_critical>0 then 'BLOCKED'",
  "'performance_lifecycle_basis','SIGNED_JOURNAL_LIFECYCLE_EVENTS_IN_POSTING_PERIOD'",
  "'sales_revenue_bridge_delta',v_sales_revenue_bridge",
  "'sales_revenue_reconciled',abs(v_sales_revenue_bridge)<=0.005",
])

requireTokens(migration, 'v20d forward reconciliation', [
  "where c.check_name in(",
  "'V2620D_REDISPATCH_PARTICIPANT_LINEAGE_MISMATCH'",
  "'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH'",
  "'CP6 independent re-audit closure: redispatch cost lineage, signed report bridge, conserved cumulative sale cents, executable rollback proof'",
])

requireTokens(rollback, 'v20d fail-closed executable rollback', [
  'lock table erp.schema_migrations,',
  'erp.laundry_redispatch_participant_allocations,',
  'erp.laundry_delivery_batch_size_lines,',
  'erp.app_users',
  'in access exclusive mode;',
  'DROP TABLE removes those FK triggers from the referenced relations',
  'v2.6.20d rollback refused: platform ledger identity is ambiguous',
  'v2.6.20d rollback refused: a successor migration is already installed',
  'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20d installed object/capsule drift',
  'v2.6.20d rollback refused: post-install lineage/business/HPP history exists',
  'for r in select * from erp.cp6_v2620d_rollback_capsule order by object_identity',
  "execute format('alter function %s owner to %I'",
  "execute format('grant execute on function %s to %s%s'",
  'drop table erp.laundry_redispatch_participant_allocations;',
  'drop table erp.cp6_v2620d_rollback_capsule;',
  'v2.6.20d rollback left schema or ledger residue',
])
assert.match(
  rollback,
  /lock table\s+erp\.laundry_redispatch_participant_allocations,\s+erp\.cp6_v2620d_rollback_capsule,\s+erp\.laundry_delivery_batch_size_lines,\s+erp\.app_users\s+in access exclusive mode;/,
  'v20d rollback must acquire final locks for the dropped tables and every FK dependency first',
)

requireTokens(regression, 'independent re-audit counterexample regression', [
  'from erp.laundry_redispatch_participant_events a',
  "where a.event_type='ALLOCATE'",
  "x.event_type='RELEASE' and x.releases_allocation_event_id=a.id",
  'or exists(select 1 from erp.laundry_redispatch_participant_allocations a',
  "raise exception 'v20d B01 did not persist the exact active E-ledger participant interval'",
  "raise notice 'CP6_V2620D_B01_REDISPATCH_COST_PASS %'",
  'if v_hpp<>140 or v_wip<>0 or v_fg<>140 or v_accrual<>140',
  "raise notice 'CP6_V2620D_ADJACENT_MULTICYCLE_PASS %'",
  'if v_hpp<>182 or v_wip<>0 or v_fg<>182 or v_accrual<>182',
  'if v_hpp<>0.11 then',
  'if v_fg<>0.01 or v_cogs<>0.10 then',
  "'reason_code','LOSS'",
  'perform erp.post_fg_adjustment(v_adjustment);',
  'if v_fg<>0 or v_cogs<>0.06 or v_other<>0.05',
  "(v_report#>>'{performance,sales_revenue_bridge_delta}')::numeric<>0",
  "raise notice 'CP6_V2620D_B02_B03_LIFECYCLE_PASS %'",
  'or exists(select 1 from erp.laundry_redispatch_participant_events)',
  "raise notice 'CP6_V2620D_REAUDIT_RESIDUE_ZERO'",
  'rollback;',
])

requireTokens(auth, 'real owner and operator Auth proof', [
  "target: 'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620F'",
  'const validNegativePayload = {',
  "headers: { 'Accept-Profile': 'erp', 'Content-Profile': 'erp' }",
  'owner_dedicated_final_sku: ownerPositiveState',
  'owner_positive_dedicated_final_sku_and_reverse: true',
  'posted_qc: 1, reversed_qc: 0, fg_qty: 4, active_laundry_hpp: 28',
  'wip_net: 42, fg_net: 28, accrued_net: -70',
  'posted_qc: 2, reversed_qc: 0, fg_qty: 5, active_laundry_hpp: 35',
  'positive_facade_actions: 14', 'granular_reverse_actions: 7',
])

requireTokens(clone, 'exact physical clone allowlist', [
  'cp6_preflight|cp6_race|cp6_auth|cp6_rollback',
  "'cp6_rollback|postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'",
])
requireTokens(rollbackRace, 'native reusable rollback race', [
  "CP6_ROLLBACK_TARGET_VERSION", "CP6_ROLLBACK_PLATFORM_NAME",
  "CP6_ROLLBACK_PREDECESSOR_VERSION", "CP6_ROLLBACK_TARGET_REG_KIND",
  "CP6_ROLLBACK_TARGET_REG_IDENTITY", "CP6_ROLLBACK_GATE_RELATION",
  "select public.erp_get_laundry_qc_workspace_v1('LAUNDRY',null)",
  "expected_version = int(ready_batch['cutting_group_row_version'])",
  'ROLLBACK_FIRST_BLOCK_TIMEOUT_SECONDS = 8.0',
  "'AUTHENTICATED_PUBLIC_WORKSPACE_BEFORE_ROLLBACK_GATE'",
  "re.fullmatch(r'erp\\.[a-z0-9_]+', GATE_RELATION)",
  "gate_cur.execute(f'lock table {GATE_RELATION} in access exclusive mode')",
])
assert.doesNotMatch(rollbackRace, /select\s+row_version\s+from\s+erp\.cutting_groups/i,
  'Rollback race must not bypass the authenticated public workspace')

for (const [label, runner] of [['v20c', v20cRunner], ['v20d', v20dRunner]]) {
  requireTokens(runner, `${label} physical rollback cleanup`, [
    "remaining_databases='UNKNOWN'", 'drop_clone',
    'cleanup_status=FAIL', "test \"$remaining_databases\" = '0'",
  ])
  assert.doesNotMatch(runner, /remaining_databases=['"]?0['"]?\s*$/m,
    `${label} runner may not manufacture cleanup residue zero`)
}
requireTokens(v20dRunner, 'v20d two-order facade rollback proof', [
  "database_name='cp6_rollback'",
  "CP6_ROLLBACK_TARGET_VERSION='v2.6.20d'",
  "CP6_ROLLBACK_PREDECESSOR_VERSION='v2.6.20c'",
  "CP6_ROLLBACK_TARGET_REG_IDENTITY='erp.laundry_redispatch_participant_allocations'",
  'run_race WRITER_FIRST V2620D_LIVE_ROLLBACK_WRITER_FIRST.json',
  'run_race ROLLBACK_FIRST V2620D_LIVE_ROLLBACK_ROLLBACK_FIRST.json',
  "rollback['writer_committed_under_restored_predecessor']=='v2.6.20c'",
])

requireTokens(workflow, 'v20d exact-SHA native evidence contract', [
  'Apply v2.6.20d independent re-audit business closure once and reject replay',
  "test \"$(wc -c < \"$migration_source\")\" = '85944'",
  'V2620D_MIGRATION_SHA256.txt', 'V2620D_REPLAY_REJECTION.log',
  'CP6_V2620D_REAUDIT_REGRESSION.log',
  'CP6_V2620D_B01_REDISPATCH_COST_PASS',
  'CP6_V2620D_ADJACENT_MULTICYCLE_PASS',
  'CP6_V2620D_B02_B03_LIFECYCLE_PASS',
  'bash scripts/run_cp6_v2620d_live_rollback_races.sh',
  'V2620D_ROLLBACK_SUCCESSOR_REJECTION.log',
  'V2620D_ROLLBACK_WRONG_NAME_REJECTION.log',
  'V2620D_ROLLBACK_TAMPER_REJECTION.log',
  'V2620D_ROLLBACK_CAPSULE_DRIFT_REJECTION.log',
  'CP6_STACK_STOP.log', 'CP6_STACK_CLEANUP.txt',
  "remaining_databases=UNKNOWN",
  'postgrest_container_remaining=%s',
  "'format':'CP6_V2620D_RUNTIME_PROOF_V1'",
  "'actual_business_facade_rollback_race_orders':6",
  "'reaudit_business_counterexamples':3",
  "'adjacent_multicycle_redispatch':True",
  "'mixed_outflow_cumulative_rounding':True",
  "'owner_positive_dedicated_final_sku':True",
  "'physical_stack_cleanup':True",
  "'uat_v2620a_v2620b_v2620c_v2620d_state':'NOT_TESTED_OR_APPLIED_BY_THIS_RUN'",
  "'production_go':False",
])
assert.ok(
  workflow.indexOf('Apply v2.6.20d independent re-audit business closure once and reject replay')
    < workflow.indexOf('Run post-CP6 real Auth JWT HTTP permissions and residue-zero E2E'),
  'Auth proof must execute after v20d is applied',
)
assert.ok(
  workflow.indexOf('CP6_V2620D_REAUDIT_REGRESSION.log')
    < workflow.indexOf('bash scripts/run_cp6_v2620d_live_rollback_races.sh'),
  'Business counterexamples must run before rollback release proofs',
)
assert.ok(
  workflow.indexOf('bash scripts/run_cp6_v2620d_live_rollback_races.sh')
    < workflow.indexOf('bash scripts/run_cp6_v2620c_live_rollback_races.sh'),
  'v20d must be released and proven before the predecessor rollback ladder',
)
assert.ok(
  workflow.indexOf('Stop disposable stack and prove physical cleanup')
    < workflow.indexOf('Bind successful CP6 proof to the exact runtime SHA'),
  'Physical stack cleanup must complete before a PASS manifest is emitted',
)
assert.doesNotMatch(workflow,
  /postgrest_container_removed=true\\nsecrets_persisted=false\\nstatus=%s/,
  'Auth clone proof may not hard-code PostgREST cleanup success')

console.log(JSON.stringify({
  status: 'PASS_STATIC_SOURCE_OWNERSHIP_ONLY',
  migration: { bytes: Buffer.byteLength(migration), sha256: migrationFileSha,
    platform_ledger_sha256: migrationLedgerSha },
  rollback: { bytes: Buffer.byteLength(rollback), sha256: rollbackFileSha },
  regression: { bytes: Buffer.byteLength(regression), sha256: regressionFileSha },
  native_runtime_proven_by_this_check: false,
  production_go: false,
}))
