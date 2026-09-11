import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
const read = (path) => readFileSync(resolve(root, path), 'utf8')
const sha256 = (value) => createHash('sha256').update(value).digest('hex')
const occurrences = (source, token) => source.split(token).length - 1

const v20Path = 'supabase/migrations/20260904111157_erp_v2_6_20_cp6_laundry_qc_fg_authoritative.sql'
const v20aPath = 'supabase/migrations/20260905110913_erp_v2_6_20a_cp6_audit_reliability_closure.sql'
const migrationPath = 'supabase/migrations/20260905170334_erp_v2_6_20b_cp6_reaudit_reliability_closure.sql'
const rollbackPath = 'supabase/rollbacks/20260905170334_erp_v2_6_20b_cp6_reaudit_reliability_closure.rollback.sql'
const racePath = 'scripts/cp6_laundry_qc_concurrency.py'
const matrixPath = 'scripts/cp6_reversal_concurrency_matrix.py'
const matrixSeedPath = 'supabase/tests/cp6_reversal_concurrency_seed.sql'
const authPath = 'scripts/cp6_auth_permission_e2e.mjs'
const scalePath = 'supabase/tests/cp6_workspace_scale_rollback.sql'
const loadPath = 'scripts/cp6_workspace_operator_load.py'
const workflowPath = '.github/workflows/cp6-full-schema-validation.yml'
const browserPath = 'tests/browser/cp6-laundry-qc.spec.ts'
const hookPath = 'src/useLaundryQcWorkspace.ts'
const pagePath = 'src/ConnectedQcFinalPage.tsx'
const modelPath = 'src/laundryQcModel.ts'

const v20 = read(v20Path)
const v20a = read(v20aPath)
const migration = read(migrationPath)
const rollback = read(rollbackPath)
const race = read(racePath)
const matrix = read(matrixPath)
const matrixSeed = read(matrixSeedPath)
const auth = read(authPath)
const scale = read(scalePath)
const load = read(loadPath)
const workflow = read(workflowPath)
const browser = read(browserPath)
const hook = read(hookPath)
const page = read(pagePath)
const model = read(modelPath)

assert.equal(sha256(v20), '52e51f56f4b8b08b7797b1a92ca9b9e26cbe611e81615c3379c728b95877ada1')
assert.equal(Buffer.byteLength(v20), 251923)
assert.equal(sha256(v20a), '03e0dcaaafecb9107d08d0c44e55b719fbaed63cd8881872423a0e9457a429cd')
assert.equal(Buffer.byteLength(v20a), 25850)

for (const [path, sql] of [[migrationPath, migration], [rollbackPath, rollback]]) {
  assert.ok(sql.endsWith('\n'), `${path} must retain one terminal LF`)
  const quotes = new Map()
  for (const match of sql.matchAll(/\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$/g)) {
    quotes.set(match[0], (quotes.get(match[0]) ?? 0) + 1)
  }
  assert.deepEqual([...quotes].filter(([, count]) => count % 2), [], `${path} has unbalanced dollar quotes`)
  assert.match(sql, /\bbegin;[\s\S]*\bcommit;\s*$/i, `${path} is not one transaction`)
}

const migrationBytes = Buffer.from(migration)
const migrationFileSha = sha256(migrationBytes)
const migrationLedgerSha = sha256(migrationBytes.subarray(0, -1))
assert.equal(migrationFileSha, '67c2b8eeb4a473c20a6ac312b863ef8f3b7eccf2a6d8805e921b3996e9eca406')
assert.equal(migrationLedgerSha, 'fedd509515694fb8f03d90ebccfcc260c8e13f0784d589d04f61b9ece8d2ed25')
assert.equal(occurrences(rollback, migrationFileSha), 4)
assert.equal(occurrences(rollback, migrationLedgerSha), 4)
assert.ok(occurrences(workflow, migrationFileSha) >= 2)
assert.ok(occurrences(workflow, migrationLedgerSha) >= 1)

assert.deepEqual(
  readdirSync(resolve(root, 'supabase/migrations')).filter((name) => name.startsWith('20260905170334_')),
  [migrationPath.split('/').at(-1)],
)
assert.deepEqual(
  readdirSync(resolve(root, 'supabase/rollbacks')).filter((name) => name.startsWith('20260905170334_')),
  [rollbackPath.split('/').at(-1)],
)
assert.doesNotMatch(migration, /\btruncate\b|\bdrop\s+(?:table|function|schema|index|trigger)\b/i)
assert.doesNotMatch(
  migration,
  /delete\s+from\s+erp\.(?:laundry_|qc_|fg_|hpp_|journal_|products|production_orders)/i,
  'Forward patch may clean only its transaction-scoped execution context, never business facts',
)

for (const token of [
  'VENI. VIDI. VICI. ERP. — I CONQUERED ERP.',
  'Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.',
  "version='v2.6.20a'", "version='v2.6.20b'",
  'cp6_v2620b_rollback_capsule',
  "count(*) from erp.cp6_v2620b_rollback_capsule)<>9",
  'installed_definition_sha256',
  "'erp.require_internal()'::regprocedure",
  "'erp.rebuild_po_hpp(uuid,text)'::regprocedure",
  "'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure",
  "'erp.get_laundry_qc_workspace_v1(text,text)'::regprocedure",
  "'erp.reverse_laundry_delivery(uuid,text)'::regprocedure",
  "'erp.reverse_laundry_receipt(uuid,text)'::regprocedure",
  "'erp.reverse_qc(uuid,text)'::regprocedure",
  "'erp.post_vendor_invoice(uuid)'::regprocedure",
  "'erp.reverse_vendor_invoice(uuid,text)'::regprocedure",
  'revoke all on function erp.post_vendor_invoice(uuid)',
  'revoke all on function erp.reverse_vendor_invoice(uuid,text)',
]) assert.ok(migration.includes(token), `v20b guarded-capsule contract missing: ${token}`)

const timeline = migration.slice(
  migration.indexOf('create function erp.assert_cp6_dispatch_timeline_v2620b'),
  migration.indexOf('do $patch_writer$'),
)
for (const token of [
  'raw_events as(', 'events as(', 'prefixes as(',
  'group by size_id,event_at', 'rows unbounded preceding',
  'where event_at>=p_physical_at and remaining_qty<0',
  "d.status<>'DRAFT'", "d.status='REVERSED'",
  "source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'",
  'future distribution batch/size history negative',
  'future Potongan WIP history negative',
]) assert.ok(timeline.includes(token), `Full future-prefix invariant missing: ${token}`)

const writerPatch = migration.slice(
  migration.indexOf('do $patch_writer$'),
  migration.indexOf('$patch_writer$;', migration.indexOf('do $patch_writer$') + 10),
)
for (const token of [
  'Preserve the specific, operator-facing',
  'Laundry send time predates sufficient authoritative sewing output.',
  'perform erp.assert_cp6_dispatch_timeline_v2620b(',
  'v_delivery_id:=gen_random_uuid();',
]) assert.ok(writerPatch.includes(token), `Dispatch guard ordering contract missing: ${token}`)
assert.ok(
  writerPatch.indexOf('Laundry send time predates sufficient authoritative sewing output.')
    < writerPatch.indexOf('perform erp.assert_cp6_dispatch_timeline_v2620b('),
  'Specific chronology UX guard must precede the general future-prefix replay',
)

const hpp = migration.slice(
  migration.indexOf('do $patch_partial_hpp$'),
  migration.indexOf('-- The source/history query'),
)
for (const token of [
  "actual_cost_status in('PENDING','ESTIMATED')",
  'v_cp6_lineage boolean:=false', 'v_laundry_allocated numeric(24,6):=0',
  'source_laundry_receipt_batch_size_line_id',
  'v_lot_cp6_receipt_laundry', 'v_lot_cp6_attempt_laundry',
  'from capacity cp6_capacity', 'cp6_capacity.size_cost',
  'v_laundry_allocated:=v_laundry_allocated+v_lot_laundry',
  'unfinished cost remains WIP',
  'CP6 Laundry HPP allocation violates cost conservation',
  "'laundry_remaining_in_wip',v_laundry-v_laundry_allocated",
]) assert.ok(hpp.includes(token), `Partial HPP/WIP invariant missing: ${token}`)

for (const token of [
  "c.action in('REVERSE_DELIVERY','REVERSE_RECEIPT')",
  "c.action='REVERSE_FINAL_SKU'",
  "v_anchor:='  perform erp.require_owner_admin();'",
  "v_replacement:='  perform erp.require_internal();'",
  "'REVERSE_DELIVERY','REVERSE_RECEIPT','REVERSE_FINAL_SKU'",
  "has_function_privilege(\n       'authenticated','erp.reverse_laundry_delivery(uuid,text)','EXECUTE'",
]) assert.ok(migration.includes(token), `Granular reverse contract missing: ${token}`)

for (const token of [
  'create function erp.search_final_sku_products_v2620b(',
  'create function public.erp_search_final_sku_products_v1(',
  "'CP6_PRODUCT_SEARCH_V2620B'", 'p_after_sort_key', 'limit p_limit+1',
  "'transaction_query_scope','SOURCE_QUEUE_AND_HISTORY'",
  "'product_query_decoupled',true",
  'idx_products_qc_model_size_effective_v2620b',
]) assert.ok(migration.includes(token), `Source-bound product resolver missing: ${token}`)
for (const token of [
  'searchFinalSkuProducts', 'erp_search_final_sku_products_v1',
  'Date.parse(page.physical_at) !== Date.parse(physicalAt)',
]) assert.ok(hook.includes(token), `Frontend resolver hook missing: ${token}`)
for (const token of [
  'CP6_PRODUCT_SEARCH_V2620B', 'SOURCE_QUEUE_AND_HISTORY', 'product_query_decoupled',
]) assert.ok(model.includes(token), `Frontend resolver parser missing: ${token}`)
for (const token of [
  'ProductSelector', 'Muat 50 SKU berikutnya', 'Ganti waktu QC akan mengosongkan pilihan SKU',
]) assert.ok(page.includes(token), `QC product-selection UX missing: ${token}`)
for (const token of [
  'finds an SKU beyond the initial catalog without hiding its source queue',
  'productBeyond500', "p_query: '73999'", 'antrean QC dan pilihan sumber tidak berubah',
]) assert.ok(browser.includes(token), `QC product-search browser proof missing: ${token}`)

for (const token of [
  "'physical_at': '2026-09-01T10:30:00Z'",
  'before_first_rejected', 'between_dispatch_and_return_rejected',
  'threading.Barrier(2)', 'concurrent_backdate_qualification',
  'REJECT_ABORT_SEMANTICS_NOT_A_RUNTIME_LOCK_RACE',
  "'manual_prelock_used': False", "'pg_blocking_pids_claimed': False",
  "len({call.get('backend_pid') for call in rejected_calls}) != 2",
  'future distribution batch/size history negative',
  "'rejected_request_rows': 0", "report['race_count'] = len(report['races'])",
  "value.get('pg_blocking_pids_observed') is True",
  'where scoped.journal_entry_id=e.id and scoped.po_id=%s::uuid',
]) assert.ok(race.includes(token), `Temporal/main-race evidence missing: ${token}`)
assert.equal(race.includes('where l.po_id=%s::uuid group by e.id having'), false)
assert.doesNotMatch(race, /canonical_fence_prelocked|F02_CONCURRENT_BACKDATES/)
assert.doesNotMatch(race, /pg_advisory_xact_lock\(hashtextextended\('CP6FLOW:/)
for (const token of [
  "'holder_outcome': 'PASS'",
  'def run_reject_abort_qualification(',
  'REJECT_ABORT_SEMANTICS_QUALIFICATION_NOT_A_RUNTIME_LOCK_RACE',
  "'manual_prelock_used': False", "'pg_blocking_pids_claimed': False",
  "'qualification_probes': {}",
  "'reverse_receipt_reject_then_reverse_qc'",
  "'replacement_post_reject_then_invoice_reversal'",
  "'reverse_receipt_vs_reverse_qc'", "'replacement_post_vs_invoice_reversal'",
  "current_cost_state='ESTIMATED', fg_net=35, wip_net=35, accrued_net=-70",
  'def require_reversed_hpp_history(actual: dict[str, Any])',
  "actual.get('reversed_lot_count') != 1",
  "actual.get('reversed_lot_hpp_rows', 0) < 1",
  "l.lot_origin='VOIDED_PRODUCTION'",
  "report['race_count'] = len(report['races'])",
  "report['qualification_probe_count'] = len(report['qualification_probes'])",
  "report['manual_prelock_count'] = 0",
  'twenty-two native runtime-lock schedules (including eight Sales Draft/HPP/invoice schedules) plus two explicit reject/abort qualifications',
]) assert.ok(matrix.includes(token), `Inverse/partial race evidence missing: ${token}`)
assert.doesNotMatch(matrix, /def cp6flow_prelock|def invoice_post_prelock|holder_prelock_label/)
assert.doesNotMatch(matrix, /holder_outcome\s*==\s*['"]REJECT['"]/)
assert.equal(occurrences(matrix, 'fg_qty=5, current_hpp=70'), 0,
  'Reversed historical HPP must not be counted as current stock HPP')
assert.equal(occurrences(matrix, 'fg_qty=5, current_hpp=35, active_laundry_hpp=35'), 4,
  'Both partial starting states and both serialized final states must conserve 35 FG / 35 WIP')
for (const token of [
  'REVRECEIPT_REVQC', 'REPLACEMENT_INVERSE',
  'SCALE_OP_01', 'SCALE_OP_08', "'CP6_SCALE_OPERATOR'", '<>33',
]) assert.ok(matrixSeed.includes(token), `Matrix/scale seed missing: ${token}`)

for (const token of [
  'SUPABASE_AUTH_URL', 'SUPABASE_REST_URL', 'CP6_AUTH_CONTROL_PGURL',
  "target: 'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620O'",
  'operator_positive_delivery_receipt_partial_and_remaining_final_sku',
  'owner_positive_dedicated_final_sku_and_reverse',
  'partial_laundry_hpp_and_wip_conservation', 'granular_reverse_permissions_positive',
  'all_seven_mutation_actions_positive_for_granular_operator',
  'all_seven_mutation_actions_denied_for_viewer',
  'positive_facade_actions: 14', 'granular_reverse_actions: 7',
  'viewer_denied_action_kinds',
  'wip_net: 140, fg_net: 0, accrued_net: -140',
  'const physicalNow = ()', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"',
  'retryDeliveryPhysicalAt = physicalNow()', 'failedWashPhysicalAt = physicalNow()',
  "'Accept-Profile': 'erp'", 'explicit_private_schema_and_sql_acl_denial',
  "active_laundry_hpp: 28", 'wip_net: 42, fg_net: 28',
  'owner_dedicated_final_sku: ownerPositiveState',
  "active_laundry_hpp: 35", 'wip_net: 35, fg_net: 35',
  'where scoped.journal_entry_id=e.id',
  "and scoped.po_id='${fixture.po}'::uuid",
  'Business facts are never hand-deleted',
]) assert.ok(auth.includes(token), `Real Auth/JWT/HTTP proof missing: ${token}`)
assert.equal(auth.includes("where l.po_id='${fixture.po}'::uuid group by e.id having"), false)

for (const token of [
  'cp6_workspace_scale_seen_products', 'v_generated_seen<>700',
  'public.erp_search_final_sku_products_v1', 'CP6-SCALE-PRODUCT-0700',
  'Beyond-first-500 SKU posted through authoritative facade',
  'CP6-SCALE-NO-ACCESSORY-0700', 'explicit_empty_bom_products',
  "'active_laundry_hpp',7", "'wip_net',63", "'fg_net',7",
  'where scoped.journal_entry_id=e.id and scoped.po_id=v_po',
  'group by e.id having sum(j.debit)<>sum(j.credit)',
  'idx_products_qc_model_size_effective_v2620b',
  "current_setting('enable_seqscan')<>'on'", "'natural_plan',v_plan",
  'rollback;',
]) assert.ok(scale.includes(token), `Scale paging/transaction proof missing: ${token}`)
assert.equal(scale.includes('enable_seqscan\',\'off'), false)
assert.equal(scale.includes('where j.po_id=v_po group by e.id'), false)
for (const token of [
  'DISPOSABLE_CP6_EIGHT_OPERATOR_WRITE_LOAD', 'threading.Barrier(len(CASES))',
  'if params:', 'cur.execute(query, params)', 'cur.execute(query)',
  "like 'cp6-scale-op-%'",
  "state='idle in transaction'", 'cardinality(pg_blocking_pids(pid))>0',
  "'active_transactions': 8", "'idle_transactions': 1",
  "'active_writers': 7", "'blocked_transactions': 7",
  'ONE_COMMIT_HOLDER_SEVEN_SERIALIZED_WAITERS_ON_SHARED_FG_BALANCE',
  "'blocking_edges'", "len(observation['blocking_edges']) != 7",
  "'posted_qc': 8", "'fg_qty': 80", "'current_hpp': 560",
  "'wip_net': 0", "'fg_net': 560", "'accrued_net': -560",
  'where scoped.journal_entry_id=e.id',
  'and scoped.po_id in(select id from target_po)',
]) assert.ok(load.includes(token), `Eight-operator write/load proof missing: ${token}`)
assert.equal(load.includes('where j.po_id in(select id from target_po)\n            group by e.id having'), false)
assert.equal(load.includes("'all_idle_in_transaction'"), false)
assert.equal(load.includes("'blocked_transactions': 0"), false)

for (const token of [
  migrationPath, rollbackPath, 'V2620B_MIGRATION_SHA256.txt',
  'supabase/migrations/20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.sql',
  'supabase/rollbacks/20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.rollback.sql',
  'V2620C_MIGRATION_SHA256.txt', 'V2620C_APPLY.log', 'V2620C_REPLAY_REJECTION.log',
  'CP6_AUTH_PGURL', "CP6_AUTH_DATABASE_NAME='cp6_auth'",
  "SUPABASE_REST_URL='http://127.0.0.1:54329'", "SUPABASE_REST_PREFIX=''",
  "PGRST_DB_SCHEMAS", 'CP6_AUTH_CLONE_CLEANUP.txt', 'remaining_databases=%s',
  'Run thirty-four native CP6 races plus three abort qualifications, temporal, paging, and scale proofs',
  "report['race_count']==22", "report['race_count'] == 12",
  "report['qualification_probe_count']==2", "report['manual_prelock_count']==0",
  "qualification['classification']=='REJECT_ABORT_SEMANTICS_NOT_A_RUNTIME_LOCK_RACE'",
  "qualification['manual_prelock_used'] is False",
  "qualification['pg_blocking_pids_claimed'] is False",
  "report['positive_evidence']['failed_wash_cost_only']['wip_net']==140",
  "set(report['positive_evidence']['mutation_action_kinds'])==expected_actions",
  "set(report['positive_evidence']['viewer_denied_action_kinds'])==expected_actions",
  "report['confidence_gate']=={",
  "'hpp_state_vs_actual_book_detected':True",
  "'wip_source_conservation_detected':True",
  "'sale_revenue_input_detected':True",
  'scripts/cp6_workspace_operator_load.py', 'V2620B_ROLLBACK_CONCURRENCY.json',
  'scripts/run_cp6_v2620c_live_rollback_races.sh',
  'V2620C_LIVE_ROLLBACK_WRITER_FIRST.json',
  'V2620C_LIVE_ROLLBACK_ROLLBACK_FIRST.json',
  "['idle_transactions']==1", "['active_writers']==7",
  "['blocked_transactions']==7", "['blocking_edges'])==7",
  'V2620B_ROLLBACK_SUCCESSOR_REJECTION.log', 'V2620B_ROLLBACK_TAMPER_REJECTION.log',
  'Bind successful CP6 proof to the exact runtime SHA',
  "'format':'CP6_V2620D_RUNTIME_PROOF_V1'",
  "'status':'PASS_EXACT_LOCAL_DISPOSABLE_CI'",
  'relative_path=path.relative_to(proof)', "part.startswith('.')",
  "'include_hidden_files':False",
  "'manifest_excludes_hidden_path_components':True",
  'include-hidden-files: false',
  "'native_runtime_race_schedules':34", "'reject_abort_qualifications':3",
  "'manual_prelock_count':0", "'actual_business_facade_rollback_race_orders':6",
  "'financial_confidence_corruption_probes':3", "'browser_executions':26",
  "'uat_v2620a_v2620b_v2620c_v2620d_state':'NOT_TESTED_OR_APPLIED_BY_THIS_RUN'",
  "'legacy_state':'NOT_TESTED_OR_MUTATED_BY_THIS_RUN'",
  "'production_go':False",
]) assert.ok(workflow.includes(token), `CI v20b ownership missing: ${token}`)
assert.ok(
  workflow.indexOf('Apply v2.6.20b re-audit reliability closure once and reject replay')
    < workflow.indexOf('Run post-CP6 real Auth JWT HTTP permissions and residue-zero E2E'),
)
assert.ok(
  workflow.indexOf('Authenticate and execute exact pre-use v2.6.20b rollback')
    < workflow.indexOf('Reject v2.6.20a rollback after relevant post-install history'),
)

for (const token of [
  'v2.6.20b rollback refused: platform ledger identity is ambiguous',
  'v2.6.20b rollback refused: a successor migration is already installed',
  'v2.6.20b rollback refused: post-install business/HPP history exists',
  'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20b installed object/capsule drift',
  "drop function public.erp_search_final_sku_products_v1",
  "drop table erp.cp6_v2620b_rollback_capsule",
  'v2.6.20b rollback left schema or ledger residue',
]) assert.ok(rollback.includes(token), `v20b fail-closed rollback guard missing: ${token}`)

console.log(
  `CP6 re-audit closure passed: v20b ${migrationFileSha.slice(0, 12)} owns full temporal prefixes, `
  + 'partial Laundry HPP/WIP lineage and granular reverse Auth; v20c CI adds 34 native runtime races, '
  + 'three reject/abort qualifications, actual-facade rollback races, and deep financial confidence probes.',
)
