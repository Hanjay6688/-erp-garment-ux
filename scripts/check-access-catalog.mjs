import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
const migration = readFileSync(resolve(root, 'supabase/migrations/20260902104937_erp_v2_6_17_access_pattern_wip_control.sql'), 'utf8')
const catalog = readFileSync(resolve(root, 'src/auth/accessCatalog.ts'), 'utf8')
const app = readFileSync(resolve(root, 'src/App.tsx'), 'utf8')
const evidence = JSON.parse(readFileSync(resolve(root, 'docs/evidence/cp45_access_route_action_ownership.json'), 'utf8'))

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

assert.equal(evidence.format, 'CP45_ACCESS_ROUTE_ACTION_OWNERSHIP_V1')
assert.equal(evidence.production_go, false)
assert.equal(evidence.counts.backend_permissions, permissionRows.length)
assert.equal(evidence.counts.navigation_labels, navMap.size)
assert.equal(evidence.counts.protected_routes, pageMap.size)
assert.equal(evidence.counts.sensitive_actions, actionMap.size)
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
assert.equal(evidence.invariants.grandfathered_history_requires_bulk_import, false)
assert.match(migration, /PATTERN_ID_REQUIRED_FOR_CUTTING_TRANSACTION/)
assert.match(app, /disabled=\{!hasCanonicalPattern\(selectedPattern\)\|\|!yardUsageValid\|\|totalPieces===0\}/)

console.log(`Access ownership passed: ${permissionRows.length} backend permissions, ${navMap.size} nav labels, ${pageMap.size} routes, ${actionMap.size} sensitive actions; zero stale owners.`)
