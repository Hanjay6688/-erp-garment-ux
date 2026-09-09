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

const migrationPath = 'supabase/migrations/20260909113933_erp_v2_6_20e_cp6_counterexample_closure.sql'
const rollbackPath = 'supabase/rollbacks/20260909113933_erp_v2_6_20e_cp6_counterexample_closure.rollback.sql'
const workflowPath = '.github/workflows/cp6-full-schema-validation.yml'
const migration = read(migrationPath)
const rollback = read(rollbackPath)
const workflow = read(workflowPath)

const migrationFileSha = '488090981e73e9bcd122f67bf10ec1247f8a403179839bd9552c33fbebdaaa0f'
const migrationLedgerSha = 'd83bcd12f26ec00f596c0ff3a3755d981b62892a97c6bbb48c0b4c561eae0a71'
const rollbackFileSha = 'ef7188ae26b9ef20fc5beb8db3a3acae0457839b326ea6dc0d9dfa0b651a52e3'

assert.equal(Buffer.byteLength(migration), 79924)
assert.equal(Buffer.byteLength(rollback), 11703)
assert.equal(sha256(migration), migrationFileSha)
assert.equal(sha256(Buffer.from(migration).subarray(0, -1)), migrationLedgerSha)
assert.equal(sha256(rollback), rollbackFileSha)
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
  readdirSync(resolve(root, 'supabase/migrations')).filter((name) => name.startsWith('20260909113933_')),
  [migrationPath.split('/').at(-1)],
)
assert.deepEqual(
  readdirSync(resolve(root, 'supabase/rollbacks')).filter((name) => name.startsWith('20260909113933_')),
  [rollbackPath.split('/').at(-1)],
)
assert.doesNotMatch(migration, /\btruncate\b|\bdrop\s+(?:table|function|schema|index|trigger)\b/i)
assert.doesNotMatch(migration,
  /delete\s+from\s+erp\.(?:laundry_|qc_|fg_|hpp_|journal_|sales_|sale_|po_)/i)

requireTokens(migration, 'exact D boundary and capsule', [
  'Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.',
  "version='v2.6.20d'", "version='v2.6.20e'",
  'eab866385d3a462aea5815dc5069d5d7a774f7aa88c43d983c665469f4469465',
  'create table erp.cp6_v2620e_rollback_capsule(',
  '(select count(*) from erp.cp6_v2620e_rollback_capsule)<>8',
])

requireTokens(migration, 'C01 append-only release/reassignment', [
  'create table erp.laundry_redispatch_participant_events(',
  "event_type text not null check(event_type in('ALLOCATE','RELEASE'))",
  "message='REDISPATCH_PARTICIPANT_EVENT_IS_APPEND_ONLY'",
  "'SUCCESSOR_CANCELLED_BEFORE_RECEIPT'",
  "and not exists(select 1 from erp.laundry_receipts r where r.delivery_id=new.id)",
  'erp.allocate_laundry_redispatch_participants_v2620e',
  'effective_allocations as(',
  'erp.cp6_lot_failed_wash_cost_v2620e(r.id)',
  "'V2620E_REDISPATCH_EVENT_MISMATCH'",
])

requireTokens(migration, 'C02 mixed/non-PO HPP', [
  'where i.sale_id=h.id and fl.po_id is null',
  'where i.return_id=h.id and fl.po_id is null',
  "'V2620E_NON_PO_SALE_HPP_BOOK_MISMATCH'",
  'create function erp.compute_po_hpp_gl_book_v2620e',
])

requireTokens(migration, 'C03 conserved cent carry', [
  'v_delta_cogs+v_delta_fg+v_delta_other',
  "jsonb_build_object('mapping_key','OTHER_INCOME'",
  "'Every Sale lifecycle journal must conserve FG/COGS/disposition independently inside each PO or non-PO dimension'",
])

requireTokens(migration, 'C04 exact refund ceiling', [
  'v_prior_product_refund+v_current_product_refund>v_product_sale_value',
  "'V2620E_SALES_RETURN_VALUE_EXCEEDS_SALE'",
])
assert.equal(
  occurrences(migration,
    'v_prior_product_refund+v_current_product_refund>v_product_sale_value+0.01'),
  1,
  'the predecessor +0.01 guard may appear only once as the dynamic-patch anchor',
)
assert.equal(
  occurrences(migration,
    "v_replacement:='v_prior_product_refund+v_current_product_refund>v_product_sale_value';"),
  1,
  'the exact refund ceiling replacement must be installed once',
)

requireTokens(migration, 'C05 zero-journal inverse', [
  'A sub-cent allocation whose',
  'filter(where fl.po_id is null)',
  'perform erp.assert_po_hpp_target_book_v2620e(v_po);',
  "'Every posted return with a monetary or rounded non-PO HPP effect requires its SALES_RETURN journal'",
])

requireTokens(migration, 'C06 opening-aware report', [
  "fl.lot_origin='PRODUCTION'",
  "'V2620E_OPENING_HPP_LINEAGE_MISMATCH'",
  "'V2620E_OPENING_FG_GL_MISMATCH'",
  'erp.resolve_opening_fg_unit_hpp(oi.id,oh.opening_date)',
])

requireTokens(rollback, 'reviewed rollback', [
  'v2.6.20e rollback refused: platform ledger identity is ambiguous',
  'v2.6.20e rollback refused: a successor migration is already installed',
  'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20e installed object/capsule drift',
  'v2.6.20e rollback refused: post-install/imported lineage or business history exists',
  'drop table erp.laundry_redispatch_participant_events;',
  "delete from erp.schema_migrations where version='v2.6.20e';",
])

console.log(JSON.stringify({
  status: 'PASS',
  boundary: 'CP6_V2620E_C01_C06_COUNTEREXAMPLE_CLOSURE',
  migration_sha256: migrationFileSha,
  rollback_sha256: rollbackFileSha,
  production_go: false,
}))
