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

const migrationPath = 'supabase/migrations/20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.sql'
const rollbackPath = 'supabase/rollbacks/20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.rollback.sql'
const scalePath = 'supabase/tests/cp6_workspace_scale_rollback.sql'
const workflowPath = '.github/workflows/cp6-full-schema-validation.yml'
const modelPath = 'src/laundryQcModel.ts'
const hookPath = 'src/useLaundryQcWorkspace.ts'
const laundryPagePath = 'src/ConnectedLaundryPage.tsx'
const qcPagePath = 'src/ConnectedQcFinalPage.tsx'
const domTestPath = 'src/ConnectedLaundryQcSelectors.dom.test.tsx'
const modelTestPath = 'src/laundryQcModel.test.ts'
const browserTestPath = 'tests/browser/cp6-laundry-qc.spec.ts'
const preconnectPath = 'src/types/database.preconnect.ts'
const authPath = 'scripts/cp6_auth_permission_e2e.mjs'
const laundryRacePath = 'scripts/cp6_laundry_qc_concurrency.py'
const reversalRacePath = 'scripts/cp6_reversal_concurrency_matrix.py'
const reversalSeedPath = 'supabase/tests/cp6_reversal_concurrency_seed.sql'
const rollbackRacePath = 'scripts/cp6_v2620c_live_rollback_race.py'
const rollbackRaceRunnerPath = 'scripts/run_cp6_v2620c_live_rollback_races.sh'

const migration = read(migrationPath)
const rollback = read(rollbackPath)
const scale = read(scalePath)
const workflow = read(workflowPath)
const model = read(modelPath)
const hook = read(hookPath)
const laundryPage = read(laundryPagePath)
const qcPage = read(qcPagePath)
const domTest = read(domTestPath)
const modelTest = read(modelTestPath)
const browserTest = read(browserTestPath)
const preconnect = read(preconnectPath)
const auth = read(authPath)
const laundryRace = read(laundryRacePath)
const reversalRace = read(reversalRacePath)
const reversalSeed = read(reversalSeedPath)
const rollbackRace = read(rollbackRacePath)
const rollbackRaceRunner = read(rollbackRaceRunnerPath)

const expectedFileSha = '19622d833325b9739ff39c0bad0f11435c1722d99dfe0acd48a18a6fb1f74218'
const expectedLedgerSha = '6668d496ba3fece68d121077256a30d405b2f084c1a900cd4eb20a17792dc1a1'
const migrationBytes = Buffer.from(migration)

assert.equal(Buffer.byteLength(migration), 78011)
assert.ok(migration.endsWith('\n'), 'v20c migration must retain its terminal LF')
assert.equal(sha256(migrationBytes), expectedFileSha)
assert.equal(sha256(migrationBytes.subarray(0, -1)), expectedLedgerSha)
assert.equal(occurrences(rollback, expectedFileSha), 4)
assert.equal(occurrences(rollback, expectedLedgerSha), 4)
assert.ok(occurrences(workflow, expectedFileSha) >= 1)
assert.ok(occurrences(workflow, expectedLedgerSha) >= 1)
assert.equal(workflow.includes('234358b12fa95b00d5f843237a6820ea2843c30d493942bcef10251375390534'), false)
assert.equal(workflow.includes('000b368fb2725a3fd42428f4e1e8f1eb8a7e0e997147e1a2c82ab5cb63dcd9cd'), false)

for (const [path, sql] of [[migrationPath, migration], [rollbackPath, rollback]]) {
  assert.ok(sql.endsWith('\n'), `${path} must retain one terminal LF`)
  const quoteCounts = new Map()
  for (const match of sql.matchAll(/\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$/g)) {
    quoteCounts.set(match[0], (quoteCounts.get(match[0]) ?? 0) + 1)
  }
  assert.deepEqual([...quoteCounts].filter(([, count]) => count % 2), [], `${path} has unbalanced dollar quotes`)
  assert.match(sql, /\bbegin;[\s\S]*\bcommit;\s*$/i, `${path} must be one transaction`)
}
assert.deepEqual(
  readdirSync(resolve(root, 'supabase/migrations')).filter((name) => name.startsWith('20260907190000_')),
  [migrationPath.split('/').at(-1)],
)
assert.deepEqual(
  readdirSync(resolve(root, 'supabase/rollbacks')).filter((name) => name.startsWith('20260907190000_')),
  [rollbackPath.split('/').at(-1)],
)
assert.doesNotMatch(migration, /\btruncate\b|\bdrop\s+(?:table|function|schema|index|trigger)\b/i)
assert.doesNotMatch(migration, /delete\s+from\s+erp\.(?:laundry_|qc_|fg_|hpp_|journal_|sales_|vendor_)/i)

requireTokens(migration, 'v20c identity/capsule', [
  'Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.',
  "version='v2.6.20b'", "version='v2.6.20c'",
  '22c87dd49ba233d000bac665fae805798a9ac91458d00efa7ad0cbb8bf467cc6',
  'create table erp.cp6_v2620c_rollback_capsule(',
  'alter table erp.cp6_v2620c_rollback_capsule enable row level security;',
  '(select count(*) from erp.cp6_v2620c_rollback_capsule)<>15',
  'installed_definition_sha256',
  "values('v2.6.20c','CP6 deep-business repair: source-owned HPP, sale valuation order, exact money, historical report basis, Laundry-BS paging, capsule RLS')",
])
const predecessorRuntimeHashes = new Map([
  ['erp._release_sale_draft_reservations(uuid,text)', '71cf2f7dd6dbfdf89d1fa971f2c92687b011c77713c2ac4b09b45a3b9cdaa2ca'],
  ['erp._reserve_sale_draft(uuid)', '6a4bc57b13f60cd7eabcc6c8baf3bc477317b04278ab3647c2c07c92e1541628'],
  ['erp.save_sale_draft_v2(jsonb,uuid,bigint)', '6b37f148e5ab878ab291cccd4ada13d56ad234c2aaed688fdef0e92486c23391'],
  ['erp.cancel_sale_draft_v2(uuid,text,uuid,bigint)', '4c868283f35c93cfe1579fb3a6e1c82d238602674ea346ee4ad6eb8666c17b3b'],
  ['erp.compute_po_hpp_gl_targets(uuid)', 'b70b577c5d4f2b6676cb31fc3eb829170c0cfa9e1b1e3da49a4698e596dd4360'],
  ['erp.get_owner_financial_snapshot_v2(date,date,date)', '90310a979ce13205ddaa93cdf59d9adc09498cb07ab1ea0c097642e894602153'],
  ['erp.post_sale(uuid)', '8fe49a80c46a2e4c614bab8e7e00c3a5d86a1dcd1fae363b1ce92b305c2b5cad'],
  ['erp.post_sale_v2(uuid,uuid,bigint)', '509193022c70546d7a3f6ad3da814a6f7fed43d4736526aea06283d0ed63cbb9'],
  ['erp.post_vendor_payment(uuid)', '3438c40881e3f2afc8e571cc6aa70883c2c5c8979716409fb415d356ec23096d'],
  ['erp.rebuild_po_hpp(uuid,text)', 'fc200d2251276d20b79120635a1c13103fad54c58fe2d1e3d6df1e60deb794bb'],
  ['erp.refresh_po_hpp_gl_baseline(uuid)', '55e511ef6bf360a11092d494ca27f1d2d9668a1bb2f154a58a6a81dcf3e24e36'],
  ['erp.reverse_sale(uuid,text)', '65d9a5cb7342b5a1b69417152bf7b76c48218cc1668cbbcc2e00020f722925a1'],
  ['erp.reverse_vendor_payment(uuid,text)', 'ff12b8ee921b4ab08c43800bde403acae57d11f7d176a907b4fa8771bfe13e68'],
  ['erp.run_v268_financial_report_checks()', '9d82ca324cc2097f2fbdf98bf20d8c63d0a2474b897cfeb39290683c8e499a44'],
  ['erp.sync_po_hpp_to_gl(uuid,date)', '4b3912b73efdb02456128d6d3c3a2f87bd7ad69a6bdf1ba31af5e16c07cfdf39'],
])
for (const [identity, hash] of predecessorRuntimeHashes) {
  assert.ok(migration.includes(`('${identity}','${hash}')`), `runtime predecessor hash missing: ${identity}`)
}
assert.equal(migration.includes('f76c65655360dd1f90986b8ba3df082362e9d3653bee5ecd4df744c52f8c19a7'), false)
assert.equal(migration.includes('488a682df22fe4be03dca7d8b251e95716e6a5312ed63e15d1d079ff008407b2'), false)
for (const table of [
  'cp3_r4_rollback_capsule', 'cp4_v2616_rollback_capsule',
  'cp45_v2617_rollback_capsule', 'cp45_v2617a_rollback_capsule',
]) requireTokens(migration, 'N06 deny-by-default capsule RLS', [`alter table erp.${table} enable row level security;`])

// N01: labor, commission, attendance, rework, and shared PO cost follow their
// immutable physical source intervals. A partial FG lot cannot absorb unfinished cost.
requireTokens(migration, 'N01 source-owned HPP', [
  'create function erp.cp6_po_source_qty_v2620c(p_po_id uuid)',
  'create function erp.cp6_lot_work_cost_v2620c(p_lot_id uuid,p_category text)',
  'create function erp.cp6_lot_attendance_cost_v2620c(p_lot_id uuid)',
  'create function erp.cp6_lot_rework_cost_v2620c(p_lot_id uuid)',
  'rows between unbounded preceding and 1 preceding',
  'greatest(least(', 's.source_start+s.source_qty', 'a.source_start+a.source_qty',
  "v_lot_labor:=erp.cp6_lot_work_cost_v2620c(r.id,'LABOR');",
  "v_lot_commission:=erp.cp6_lot_work_cost_v2620c(r.id,'COMMISSION');",
  'v_lot_rework:=erp.cp6_lot_rework_cost_v2620c(r.id);',
  'v_lot_attendance_hpp:=erp.cp6_lot_attendance_cost_v2620c(r.id);',
  'CP6 source-owned HPP allocation violates cost conservation',
  "'po_physical_source_qty',v_po_source_qty",
])

// N02: failed-wash cost is matched to the exact delivery-size stream and the
// receipt/attempt interval, never merely to batch+size capacity.
const failedWash = migration.slice(
  migration.indexOf('create function erp.cp6_lot_failed_wash_cost_v2620c'),
  migration.indexOf('create function erp.cp6_lot_rework_cost_v2620c'),
)
requireTokens(failedWash, 'N02 failed-wash lineage', [
  'rx.delivery_batch_size_line_id', 'receipt_interval as(',
  'where px.delivery_batch_size_line_id=s.delivery_batch_size_line_id',
  '(ph.physical_at,ph.id,px.id)<(s.receipt_at,s.receipt_id,s.receipt_batch_size_id)',
  'on ax.delivery_batch_size_line_id=s.delivery_batch_size_line_id',
  's.receipt_start+s.receipt_qty', 'a.attempt_start+a.attempt_qty',
])
assert.doesNotMatch(failedWash, /distribution_batch_id\s*=\s*ls\.distribution_batch_id/)

// N07/N08: Draft reserves quantity only; POST freezes current HPP; all sales,
// recost, cancellation, and reversal paths share one lock and exact minor units.
const targets = migration.slice(
  migration.indexOf('create or replace function erp.compute_po_hpp_gl_targets'),
  migration.indexOf('do $patch_sales_lock_order$'),
)
requireTokens(targets, 'N07 Draft valuation targets', [
  "fm.movement_type='SALE_RESERVE'",
  "sh.status in('POSTED','PARTIAL_PAID','PAID')",
  "sr.status='POSTED'",
  '(base.total-vals.fg_val-vals.cogs_val)::numeric',
])
const saleLocks = migration.slice(
  migration.indexOf('do $patch_sales_lock_order$'),
  migration.indexOf('create or replace function erp.post_sale(p_sale_id uuid)'),
)
for (const identity of [
  'erp._release_sale_draft_reservations(uuid,text)', 'erp._reserve_sale_draft(uuid)',
  'erp.save_sale_draft_v2(jsonb,uuid,bigint)', 'erp.cancel_sale_draft_v2(uuid,text,uuid,bigint)',
  'erp.post_sale_v2(uuid,uuid,bigint)', 'erp.reverse_sale(uuid,text)',
]) assert.ok(saleLocks.includes(identity), `N07 shared sale lock missing: ${identity}`)
requireTokens(saleLocks, 'N07 sale/rebuild lock order', [
  "pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))",
  'select round(coalesce(sum(a.qty_pcs*a.unit_hpp_snapshot),0),2)',
])
const postSale = migration.slice(
  migration.indexOf('create or replace function erp.post_sale(p_sale_id uuid)'),
  migration.indexOf('create or replace function erp.refresh_po_hpp_gl_baseline'),
)
requireTokens(postSale, 'N07 authoritative sale POST', [
  "if h.id is null or h.status<>'DRAFT' then raise exception 'Sale must be DRAFT'",
  'set unit_hpp_snapshot=coalesce(erp.lock_current_hpp_per_pcs(a.lot_id),0)',
  "set movement_type='SALE',notes='Sale posted · quantity reserved in Draft; HPP frozen at POST'",
  'select fl.po_id,round(sum(a.qty_pcs*a.unit_hpp_snapshot),2) cogs',
  "perform erp.post_journal('SALE',h.id,h.sale_date::date",
])
assert.ok(postSale.indexOf('set unit_hpp_snapshot=coalesce(erp.lock_current_hpp_per_pcs')
  < postSale.indexOf("set movement_type='SALE'"), 'N07 HPP must freeze before Draft reserve becomes SALE')
const sync = migration.slice(
  migration.indexOf('create or replace function erp.sync_po_hpp_to_gl'),
  migration.indexOf('create or replace function erp.post_vendor_payment'),
)
requireTokens(sync, 'N08 cumulative minor-unit HPP/GL', [
  'v_target_hpp:=round(coalesce(t.hpp_total_cost,0),2);',
  'v_target_fg:=round(coalesce(t.fg_value,0),2);',
  'v_target_cogs:=round(coalesce(t.cogs_value,0),2);',
  'v_target_other:=v_target_hpp-v_target_fg-v_target_cogs;',
  'v_df:=v_target_fg-round(coalesce(s.fg_value,0),2);',
  'Latest corrected HPP allocation · exact minor-unit targets',
  'values(p_po_id,v_target_qty,v_target_hpp,v_target_fg,v_target_cogs,v_target_other,now())',
])

// N09: payment status and overpayment use exact NUMERIC(20,2) comparisons.
const payments = migration.slice(
  migration.indexOf('create or replace function erp.post_vendor_payment'),
  migration.indexOf('create or replace function erp.run_v268_financial_report_checks'),
)
requireTokens(payments, 'N09 exact vendor payment lifecycle', [
  'v_paid numeric(20,2);', 'if v_paid+p.amount>h.total_amount then',
  "when v_paid=total_amount then 'PAID' else 'PARTIAL_PAID' end",
  "when v_paid=h.total_amount then 'PAID'",
  "when v_paid>0 then 'PARTIAL_PAID' else 'POSTED' end",
])
assert.doesNotMatch(payments, /total_amount\s*[+-]\s*0\.01/)

// N10/N12/N11: confidence is tied to books and independent sources; historical
// performance and Laundry outstanding have explicit immutable as-of bases.
requireTokens(migration, 'N10 financial confidence gate', [
  "'V2620C_PO_HPP_TARGET_STATE_MISMATCH','CRITICAL'",
  "'V2620C_HPP_COMPONENT_SUM_MISMATCH','CRITICAL'",
  "'V2620C_PO_HPP_BOOK_MISMATCH','CRITICAL'",
  "'V2620C_WIP_SOURCE_CONSERVATION_MISMATCH','CRITICAL'",
  "'V2620C_SALE_REVENUE_REPORT_INPUT_MISMATCH','CRITICAL'",
  "'V2620C_SALES_RETURN_REPORT_INPUT_MISMATCH','CRITICAL'",
  "'V2620C_DRAFT_SALE_VALUE_LEAK','CRITICAL'",
  "'V2620C_VENDOR_PAYMENT_EXACT_STATUS_MISMATCH','CRITICAL'",
  "'V2620C_HPP_STATE_HAS_SUBCENT','CRITICAL'",
  "'failed_checks',v_failed_checks",
])
requireTokens(migration, 'N12 historical report basis', [
  "original.source_type='SALE'", "original.source_type='SALES_RETURN'",
  'reversal.transaction_date<=p_to',
  "'performance_lifecycle_basis','JOURNAL_EVENT_STATE_AS_OF_PERIOD_END'",
])
requireTokens(migration, 'N11 authoritative Laundry outstanding', [
  "when w.stage_to='LAUNDRY' then w.qty_pcs",
  "when w.stage_from='LAUNDRY' then -w.qty_pcs",
  'where w.physical_at::date<=p_as_of',
  "'laundry_outstanding_basis','IMMUTABLE_WIP_STAGE_EVENT_NET_AS_OF_BALANCE_DATE'",
  "'laundry_outstanding_pcs',v_laundry_outstanding",
  "'legacy_receipt_stuck_pcs',v_laundry_stuck",
])

// R03 + N03/N04: both selectors are source/time bound and paged; stale requests
// release loading; completion intent uses the global authoritative remainder.
requireTokens(migration, 'R03 Laundry-BS resolver', [
  'create function erp.search_laundry_bs_products_v2620c(',
  'create function public.erp_search_laundry_bs_products_v1(',
  "perform erp.require_permission('production.laundry.view');",
  "d.status in('SENT','PARTIAL_RETURN') and d.physical_at<=p_physical_at",
  "'CP6_LAUNDRY_BS_PRODUCT_SEARCH_V2620C'", 'limit p_limit+1',
  "grant execute on function public.erp_search_laundry_bs_products_v1(uuid,timestamptz,text,text,integer)",
])
requireTokens(model, 'R03 frontend contract parser', [
  'export type Cp6LaundryBsProductSearchPage',
  "contract_version: 'CP6_LAUNDRY_BS_PRODUCT_SEARCH_V2620C'",
  'export function parseLaundryBsProductSearch',
  'Pencarian SKU Laundry-BS mencampur Model atau ukuran sumber pengiriman.',
])
requireTokens(hook, 'R03 frontend RPC binding', [
  'const searchLaundryBsProducts = useCallback(async (',
  "client.rpc('erp_search_laundry_bs_products_v1'",
  'p_delivery_batch_size_line_id: deliveryBatchSizeLineId',
  'const page = parseLaundryBsProductSearch(data)',
  'Respons pencarian SKU Laundry-BS tidak cocok dengan sumber/waktu yang diminta.',
])
requireTokens(preconnect, 'R03 generated preconnect surface', [
  'erp_search_laundry_bs_products_v1:', 'p_delivery_batch_size_line_id: string',
])
requireTokens(laundryPage, 'R03/N04 Laundry-BS UI', [
  'export function LaundryBsProductSelector', 'requestRef.current += 1',
  'setLoading(false)', 'Muat 50 SKU berikutnya',
  'Server mengembalikan SKU di luar Model/ukuran sumber Laundry.',
  'tidak dibatasi 500 produk awal',
])
requireTokens(qcPage, 'N03/N04 Final-SKU UI', [
  'export const qcCompletionMode = (selectedQty: number, authoritativeRemainingQty: number)',
  "selectedQty > 0 && selectedQty === authoritativeRemainingQty ? 'ALL_READY' : 'PARTIAL_SELECTION'",
  'const authoritativeRemaining = group?.remaining ?? 0',
  'setLoading(false)', 'requestRef.current += 1',
])
requireTokens(domTest, 'R03/N03/N04 DOM regression', [
  'keeps filtered QC selection partial when global authoritative remaining is larger',
  'clears a stale Final-SKU loading state when the query invalidates an in-flight request',
  'finds and selects a valid Laundry-BS SKU beyond the bounded initial lookup',
  'rejects a Laundry-BS resolver response outside the exact source Model/size',
])
requireTokens(modelTest, 'R03 parser regression', [
  'accepts only a bounded source-bound page with one Model and size',
  'rejects mixed source dimensions and contradictory pagination',
])
requireTokens(browserTest, 'R03 Laundry-BS browser locator identity', [
  "page.getByLabel('SKU BS size S', { exact: true })",
])

// R05: valid source parameters exercise each role class over HTTP, including
// the dedicated Final-SKU facade, not only the shared action dispatcher.
requireTokens(auth, 'R05 Auth facade × role matrix', [
  'const facadeRoleMatrix = []',
  "recordFacadeRole('erp_search_laundry_bs_products_v1'",
  "recordFacadeRole('erp_search_final_sku_products_v1'",
  "recordFacadeRole('erp_post_final_sku_allocation_v1'",
  'for (const session of [ownerSession, operatorSession, viewerSession])',
  'for (const session of [null, unmappedSession, inactiveSession])',
  'for (const session of [null, unmappedSession, inactiveSession, viewerSession])',
  'valid-outstanding-delivery-size-source', 'valid-live-qc-source',
  'valid-live-qc-source-and-payload',
  'negative_mutation_transaction_residue_zero: true',
  'facade_role_matrix: facadeRoleMatrix',
])

// R06: only native runtime-acquired locks count as races; failed-statement
// abort behavior is an explicit qualification and never a fabricated pre-lock.
requireTokens(laundryRace, 'R06 Laundry race evidence', [
  'threading.Barrier(2)', 'concurrent_backdate_qualification',
  'REJECT_ABORT_SEMANTICS_NOT_A_RUNTIME_LOCK_RACE',
  "'manual_prelock_used': False", "'pg_blocking_pids_claimed': False",
  "report['race_count'] != 12",
])
requireTokens(reversalRace, 'R06 reversal race evidence', [
  'def run_reject_abort_qualification(',
  'REJECT_ABORT_SEMANTICS_QUALIFICATION_NOT_A_RUNTIME_LOCK_RACE',
  "report['qualification_probe_count'] = len(report['qualification_probes'])",
  "report['manual_prelock_count'] = 0",
  'twenty-two native runtime-lock schedules (including eight Sales Draft/HPP/invoice schedules) plus two explicit reject/abort qualifications',
  "report['race_count'] != 22",
  "'partial_nonzero_labor_laundry_cost'",
  "('INVOICE_SALE_SAVE', 'invoice_vs_save_sale_draft', 'SAVE', True)",
  "('SALE_POST_INVOICE', 'post_sale_draft_vs_invoice', 'POST', False)",
  "('INVOICE_SALE_CANCEL', 'invoice_vs_cancel_sale_draft', 'CANCEL', True)",
  "('SALE_REVERSE_INVOICE', 'reverse_sale_vs_invoice', 'REVERSE', False)",
  'allocation_hpp=50',
  "w.locktype='advisory'", 'shared_advisory_lock_observed',
  'require_advisory_lock=True',
])
requireTokens(reversalSeed, 'N01/N07 native fixture foundation', [
  "'PARTIAL_LABOR_COST'", "'SALE_SAVE_INVOICE'", "'INVOICE_SALE_SAVE'",
  "'SALE_POST_INVOICE'", "'INVOICE_SALE_POST'",
  "'SALE_CANCEL_INVOICE'", "'INVOICE_SALE_CANCEL'",
  "'SALE_REVERSE_INVOICE'", "'INVOICE_SALE_REVERSE'",
  "case when v_case='PARTIAL_LABOR_COST' then 2 else 0 end",
  "where po_number like 'CP6-MX-%')<>33",
])
assert.doesNotMatch(laundryRace, /canonical_fence_prelocked|F02_CONCURRENT_BACKDATES/)
assert.doesNotMatch(reversalRace, /def cp6flow_prelock|def invoice_post_prelock|holder_prelock_label/)

// N05: rollback ordering is observed against the actual public business facade
// in both orders, with exact blocker PIDs and zero synthetic marker claims.
requireTokens(rollbackRace, 'N05 live business rollback race', [
  "'select public.erp_save_laundry_qc_action_v1(%s,%s::jsonb,%s::uuid,%s)'",
  "'notes': 'Actual public business facade; no synthetic marker'",
  "'ordering': 'BUSINESS_WRITER_THEN_ROLLBACK'",
  "'ordering': 'ROLLBACK_LOCKS_THEN_BUSINESS_WRITER'",
  "'actual_facade': 'public.erp_save_laundry_qc_action_v1'",
  "'synthetic_business_marker_used': False",
  'pg_blocking_pids_observed', 'writer_blocked_by_exact_rollback_pid',
  'pre_use_rollback_committed', "'production_go': False",
])
requireTokens(rollbackRaceRunner, 'N05 rollback race runner', [
  'prepare_clone V2620C_WRITER_FIRST_BOUNDARY',
  'CP6_ROLLBACK_RACE_MODE=WRITER_FIRST',
  'prepare_clone V2620C_ROLLBACK_FIRST_BOUNDARY',
  'CP6_ROLLBACK_RACE_MODE=ROLLBACK_FIRST',
  "assert writer['actual_facade']=='public.erp_save_laundry_qc_action_v1'",
  "assert rollback['writer_blocked_by_exact_rollback_pid'] is True",
  'V2620C_LIVE_ROLLBACK_CLONE_CLEANUP.txt',
])

// Executable scale acceptance intentionally corrupts three independent inputs
// inside rollback-only subtransactions and requires the confidence gate to fire.
requireTokens(scale, 'N10 executable confidence corruption probes', [
  "'clean_critical_issue_count',v_gate_issue_count",
  "'hpp_state_vs_actual_book_detected',v_hpp_book_gate_rejected",
  "'wip_source_conservation_detected',v_wip_gate_rejected",
  "'sale_revenue_input_detected',v_revenue_gate_rejected",
  "'corruption_probe_residue',0",
  "check_name='V2620C_PO_HPP_BOOK_MISMATCH'",
  "check_name='V2620C_WIP_SOURCE_CONSERVATION_MISMATCH'",
  "check_name='V2620C_SALE_REVENUE_REPORT_INPUT_MISMATCH'",
  'rollback;',
])

requireTokens(rollback, 'v20c fail-closed rollback', [
  'lock table erp.schema_migrations,',
  'v2.6.20c rollback refused: platform ledger identity is ambiguous',
  'v2.6.20c rollback refused: a successor migration is already installed',
  'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20c installed object/capsule drift',
  'v2.6.20c rollback refused: post-install business/HPP history exists',
  'for r in select * from erp.cp6_v2620c_rollback_capsule order by object_identity',
  "execute format('grant execute on function %s to %s%s'",
  'drop function public.erp_search_laundry_bs_products_v1(uuid,timestamptz,text,text,integer);',
  'drop table erp.cp6_v2620c_rollback_capsule;',
  'v2.6.20c rollback left schema, RLS, or ledger residue',
])

requireTokens(workflow, 'v20c exact-SHA CI proof', [
  'Apply v2.6.20c deep-business reliability repair once and reject replay',
  "test \"$(wc -c < \"$migration_source\")\" = '78011'",
  'V2620C_MIGRATION_SHA256.txt', 'V2620C_REPLAY_REJECTION.log',
  'Run thirty-four native CP6 races plus three abort qualifications',
  "report['race_count']==22", "report['race_count'] == 12",
  "partial=report['states']['partial_nonzero_labor_laundry_cost']",
  "'invoice_vs_save_sale_draft','save_sale_draft_vs_invoice'",
  "'invoice_vs_post_sale_draft','post_sale_draft_vs_invoice'",
  "'invoice_vs_cancel_sale_draft','cancel_sale_draft_vs_invoice'",
  "'invoice_vs_reverse_sale','reverse_sale_vs_invoice'",
  "report['races'][key]['shared_advisory_lock_observed'] is True",
  "report['qualification_probe_count']==2", "report['manual_prelock_count']==0",
  "assert report['confidence_gate']=={",
  'bash scripts/run_cp6_v2620c_live_rollback_races.sh',
  "'format':'CP6_V2620C_RUNTIME_PROOF_V1'",
  "'native_runtime_race_schedules':34", "'reject_abort_qualifications':3",
  "'actual_business_facade_rollback_race_orders':2",
  "'financial_confidence_corruption_probes':3",
  "'uat_v2620a_v2620b_v2620c_state':'NOT_TESTED_OR_APPLIED_BY_THIS_RUN'",
  "'production_go':False",
])
assert.ok(
  workflow.indexOf('Apply v2.6.20c deep-business reliability repair once and reject replay')
    < workflow.indexOf('Run post-CP6 real Auth JWT HTTP permissions and residue-zero E2E'),
  'Auth proof must execute after v20c is applied',
)
assert.ok(
  workflow.indexOf('bash scripts/run_cp6_v2620c_live_rollback_races.sh')
    < workflow.indexOf('tee cp6-proof/V2620C_MAIN_PRE_USE_ROLLBACK.log'),
  'Live rollback races must precede the final pre-use ladder proof',
)

console.log(
  `CP6 deep-business repair passed: v20c ${expectedFileSha.slice(0, 12)} closes N01–N12/R03/R05/R06/N05 `
  + 'with source-owned cost, exact books, historical report basis, source-bound UI, honest concurrency, and actual-facade rollback proof.',
)
