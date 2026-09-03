import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'
import { extname, join, resolve } from 'node:path'

const root = process.cwd()
const migration = readFileSync(resolve(root, 'supabase/migrations/20260902104937_erp_v2_6_17_access_pattern_wip_control.sql'), 'utf8')
const integrityCorrection = readFileSync(resolve(root, 'supabase/migrations/20260902180726_erp_v2_6_17a_cp45_pattern_assignment_immutability.sql'), 'utf8')
const catalog = readFileSync(resolve(root, 'src/auth/accessCatalog.ts'), 'utf8')
const app = readFileSync(resolve(root, 'src/App.tsx'), 'utf8')
const cp45EvidencePath = resolve(root, 'docs/evidence/cp45_access_route_action_ownership.json')
const cp45EvidenceBytes = readFileSync(cp45EvidencePath)
const cp45Evidence = JSON.parse(cp45EvidenceBytes)
const evidence = JSON.parse(readFileSync(resolve(root, 'docs/evidence/cp5_access_route_action_ownership.json'), 'utf8'))

function between(source, start, end) {
  const from = source.indexOf(start)
  const to = source.indexOf(end, from + start.length)
  assert.ok(from >= 0 && to > from, `Cannot resolve source block: ${start}`)
  return source.slice(from, to)
}

function objectEntries(source, name) {
  const body = between(source, `export const ${name}`, '})')
  const entries = [...body.matchAll(/^\s*(?:'([^']+)'|([A-Za-z][A-Za-z0-9 ]*)):\s*'([^']+)'/gm)]
    .map((match) => [match[1] ?? match[2], match[3]])
  assert.ok(entries.length > 0, `${name} is empty or unparsable`)
  assert.equal(new Set(entries.map(([key]) => key)).size, entries.length, `${name} has duplicate keys`)
  return new Map(entries)
}

const permissionSection = between(migration, 'insert into erp.app_permissions', 'insert into erp.app_roles')
const permissionRows = [...permissionSection.matchAll(/\('([^']+)','([^']*)','([^']*)','([^']*)','([^']*)','([^']*)',(true|false),(\d+)\)/g)]
  .map((match) => ({ key: match[1], module: match[2], action: match[4], highRisk: match[7] === 'true' }))
assert.ok(permissionRows.length >= 90, 'Permission catalog unexpectedly small')
assert.equal(new Set(permissionRows.map((row) => row.key)).size, permissionRows.length, 'Backend permission key is duplicated')

const backendKeys = new Set(permissionRows.map((row) => row.key))
const highRiskKeys = new Set(permissionRows.filter((row) => row.highRisk).map((row) => row.key))
const navMap = objectEntries(catalog, 'NAV_PERMISSION_BY_LABEL')
const pageMap = objectEntries(catalog, 'PAGE_PERMISSION_BY_ID')
const actionMap = objectEntries(catalog, 'SENSITIVE_ACTION_PERMISSION')

for (const [owner, permission] of [...navMap, ...pageMap, ...actionMap]) {
  assert.ok(backendKeys.has(permission), `Frontend owner ${owner} points to missing permission ${permission}`)
}
for (const [action, permission] of actionMap) {
  assert.ok(highRiskKeys.has(permission), `Sensitive action ${action} is not high-risk in backend catalog: ${permission}`)
}

const navBlock = between(app, 'const nav:', 'const salesPageByLabel')
const navLabels = new Set([
  'Dashboard',
  ...[...navBlock.matchAll(/'([^']+)'/g)].map((match) => match[1]),
  ...[...between(app, 'const adminNav', 'const salesViews').matchAll(/'([^']+)'/g)].map((match) => match[1]),
])
for (const section of ['Produksi', 'Gudang', 'Penjualan', 'Keuangan', 'Master Data']) navLabels.delete(section)
assert.deepEqual([...navMap.keys()].sort(), [...navLabels].sort(), 'Sidebar label ownership is stale or incomplete')

const discoveredRoutes = new Set([...app.matchAll(/(?:page\s*===|setPage\()\s*'([^']+)'/g)].map((match) => match[1]))
discoveredRoutes.delete('placeholder')
for (const route of discoveredRoutes) {
  assert.ok(pageMap.has(route), `Protected route has no permission owner: ${route}`)
}

const missingRouteConsumers = [...pageMap.keys()].filter((route) => !app.includes(`'${route}'`))
assert.deepEqual(missingRouteConsumers, [], 'Permission points to a missing route')

assert.equal(cp45EvidenceBytes.length, 1242, 'Frozen CP4.5 access evidence byte length drift')
assert.equal(
  createHash('sha256').update(cp45EvidenceBytes).digest('hex'),
  '349f7d653adbf132e21d3ee2adb740bf9f2185445d612e5dce73a674fa178184',
  'Frozen CP4.5 access evidence SHA-256 drift',
)
assert.equal(cp45Evidence.format, 'CP45_ACCESS_ROUTE_ACTION_OWNERSHIP_V1')
assert.equal(cp45Evidence.counts.sensitive_actions, 17)
assert.equal(cp45Evidence.production_go, false)

function sourceFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) return sourceFiles(path)
    return ['.ts', '.tsx'].includes(extname(path)) && !/(?:\.test\.|\.d\.ts$)/.test(path) ? [path] : []
  })
}

const rpcBoundaries = new Set()
for (const path of sourceFiles(resolve(root, 'src'))) {
  const source = readFileSync(path, 'utf8')
  for (const match of source.matchAll(/\.rpc\s*\(\s*['"]([^'"]+)['"]/g)) {
    rpcBoundaries.add(`${path.slice(root.length + 1)}:${match[1]}`)
  }
}

assert.equal(evidence.format, 'CP5_ACCESS_ROUTE_ACTION_OWNERSHIP_V1')
assert.equal(evidence.production_go, false)
assert.equal(evidence.counts.backend_permissions, permissionRows.length)
assert.equal(evidence.counts.navigation_labels, navMap.size)
assert.equal(evidence.counts.protected_routes, pageMap.size)
assert.equal(evidence.counts.sensitive_actions, actionMap.size)
assert.equal(evidence.counts.browser_rpc_boundaries, rpcBoundaries.size)
for (const [route, permission] of Object.entries(evidence.critical_routes)) {
  assert.equal(pageMap.get(route), permission, `Critical route evidence drift: ${route}`)
}
for (const [action, permission] of Object.entries(evidence.critical_actions)) {
  assert.equal(actionMap.get(action), permission, `Critical action evidence drift: ${action}`)
}
assert.equal(evidence.invariants.cutting_view_does_not_grant_pattern_manage, true)
assert.notEqual(pageMap.get('cutting-roll'), actionMap.get('quickCreatePattern'))
assert.equal(evidence.invariants.quick_create_uses_master_save_rpc, true)
assert.match(readFileSync(resolve(root, 'src/CuttingPatternPicker.tsx'), 'utf8'), /\.rpc\('erp_save_pattern_v1'/)
assert.equal(evidence.invariants.cutting_transaction_pattern_id_required, true)
assert.equal(evidence.invariants.pattern_snapshot_visible_in_pickup_and_wip, true)
assert.equal(evidence.invariants.grandfathered_history_requires_bulk_import, false)
assert.match(migration, /PATTERN_ID_REQUIRED_FOR_CUTTING_TRANSACTION/)
const initialAssignmentGuard = between(
  integrityCorrection,
  'create function erp.assert_pattern_initial_assignment_allowed',
  'create or replace function erp.guard_pattern_assignment_snapshot',
)
for (const table of [
  'cutting_qty_correction_lines', 'work_completion_events', 'sewing_terminal_events',
  'laundry_delivery_lines', 'qc_inspection_items', 'fg_lots', 'bs_cases',
  'attendance_hpp_pool_allocations', 'wip_stage_events', 'wip_control_flags', 'scrap_batches',
]) assert.match(initialAssignmentGuard, new RegExp(`erp\\.${table}`), `Missing initial-assignment blocker: ${table}`)
assert.doesNotMatch(initialAssignmentGuard, /cutting_group_(?:rolls|size_slots)/)
assert.match(initialAssignmentGuard, /for update/i)
assert.match(integrityCorrection, /PATTERN_IDENTITY_ALREADY_BOUND/)
assert.match(integrityCorrection, /PATTERN_ASSIGNMENT_SNAPSHOT_IMMUTABLE/)
assert.match(integrityCorrection, /revoke all on function erp\.assert_pattern_initial_assignment_allowed\(uuid\)/)
assert.match(app, /disabled=\{!hasCanonicalPattern\(selectedPattern\)\|\|!yardUsageValid\|\|totalPieces===0\}/)
assert.match(app, /className="wip-selected-pattern" data-pattern-snapshot=/)
assert.match(app, /className="sewing-parent-pattern" data-pattern-snapshot=/)

assert.equal(evidence.invariants.cp45_evidence_remains_frozen, true)
assert.equal(evidence.invariants.module_specific_runtime_routing, true)
assert.match(app, /runtime\.cuttingMode === 'CONNECTED'/)
assert.match(app, /runtime\.distributionMode === 'CONNECTED'/)
assert.match(app, /runtime\.wipStatusMode === 'CONNECTED'/)
assert.match(app, /runtime\.bsResolutionMode === 'CONNECTED'/)
assert.equal(evidence.invariants.connected_pattern_filter_cutting_pickup, true)
assert.match(readFileSync(resolve(root, 'src/ConnectedPickupPage.tsx'), 'utf8'), /ConnectedPatternFilter/)
assert.equal(evidence.invariants.connected_pattern_filter_wip, true)
assert.match(readFileSync(resolve(root, 'src/ConnectedWipStatusPage.tsx'), 'utf8'), /ConnectedPatternFilter/)
assert.equal(evidence.invariants.connected_pattern_filter_bs_resolution, true)
const bsPage = readFileSync(resolve(root, 'src/ConnectedBsResolutionPage.tsx'), 'utf8')
assert.match(bsPage, /ConnectedPatternFilter/)
assert.match(bsPage, /erp_get_bs_resolution_workspace_v1/)
assert.match(bsPage, /erp_save_bs_resolution_action_v1/)
assert.equal(evidence.invariants.simulation_pattern_filter_laundry, true)
assert.match(app, /aria-label="Filter Pola Laundry"/)
assert.equal(evidence.invariants.simulation_pattern_filter_qc, true)
assert.match(readFileSync(resolve(root, 'src/QcFinalPage.tsx'), 'utf8'), /aria-label="Filter Pola QC"/)
assert.equal(evidence.invariants.bs_resolution_uses_two_public_rpc_facades, true)
assert.equal([...bsPage.matchAll(/\.rpc\s*\(\s*['"]([^'"]+)['"]/g)].length, 2)
assert.equal(evidence.invariants.laundry_and_qc_writers_connected, false)
assert.equal(evidence.invariants.source_only, false)
assert.equal(evidence.invariants.uat_applied, false)
assert.equal(evidence.invariants.uat_partial_state, 'RECORDED_V2618_ONLY')

console.log(`Access ownership passed: frozen CP4.5 proof intact; CP5 owns ${permissionRows.length} backend permissions, ${navMap.size} nav labels, ${pageMap.size} routes, ${actionMap.size} sensitive actions, and ${rpcBoundaries.size} browser RPC boundaries.`)
