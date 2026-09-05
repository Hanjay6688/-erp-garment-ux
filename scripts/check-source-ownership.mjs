import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, extname, relative, resolve } from 'node:path'

const root = resolve('src')
const sourceExtensions = new Set(['.ts', '.tsx', '.css'])
const sourceFiles = []

function walk(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const file = resolve(directory, entry.name)
    if (entry.isDirectory()) walk(file)
    else if (sourceExtensions.has(extname(file))) sourceFiles.push(file)
  }
}

walk(root)

const sourceSet = new Set(sourceFiles)
const dependencies = new Map(sourceFiles.map((file) => [file, []]))
const importPattern = /(?:import|export)\s+(?:[^'";]*?\s+from\s+)?['"]([^'"]+)['"]|import\(\s*['"]([^'"]+)['"]\s*\)/g

function resolveImport(importer, specifier) {
  if (!specifier.startsWith('.')) return null
  const candidate = resolve(dirname(importer), specifier)
  for (const file of [
    candidate,
    `${candidate}.ts`,
    `${candidate}.tsx`,
    `${candidate}.css`,
    resolve(candidate, 'index.ts'),
    resolve(candidate, 'index.tsx'),
  ]) {
    if (sourceSet.has(file)) return file
  }
  return null
}

for (const file of sourceFiles) {
  const source = readFileSync(file, 'utf8')
  for (const match of source.matchAll(importPattern)) {
    const dependency = resolveImport(file, match[1] ?? match[2])
    if (dependency) dependencies.get(file).push(dependency)
  }
}

const reachable = new Set()
const pending = [resolve(root, 'main.tsx')]
while (pending.length > 0) {
  const file = pending.pop()
  if (!file || reachable.has(file)) continue
  reachable.add(file)
  pending.push(...(dependencies.get(file) ?? []))
}

const isTestSource = (file) => /(?:\.test\.|\.d\.ts$)/.test(file)
const orphaned = sourceFiles
  .filter((file) => !isTestSource(file) && !reachable.has(file))
  .map((file) => relative(process.cwd(), file))
  .sort()

assert.deepEqual(
  orphaned,
  [],
  `Runtime source is not owned by the main import graph:\n${orphaned.join('\n')}`,
)

const unsafeRendering = /\b(?:innerHTML|insertAdjacentHTML|dangerouslySetInnerHTML|document\.write)\b/
const dataReads = []
const rpcOwnership = new Set()

for (const file of sourceFiles.filter((candidate) => !isTestSource(candidate) && extname(candidate) !== '.css')) {
  const source = readFileSync(file, 'utf8')
  const name = relative(process.cwd(), file)
  assert.equal(unsafeRendering.test(source), false, `Unsafe HTML rendering boundary in ${name}`)
  assert.equal(/\.schema\s*\(/.test(source), false, `Direct schema boundary opened in ${name}`)
  for (const match of source.matchAll(/\.from\s*\(\s*['"]([^'"]+)['"]\s*\)/g)) {
    dataReads.push({ file: name, relation: match[1] })
  }
  const rpcInvocations = [...source.matchAll(/\.rpc\s*\(/g)]
  const literalRpcInvocations = [...source.matchAll(/\.rpc\s*\(\s*['"]([^'"]+)['"]/g)]
  assert.equal(
    rpcInvocations.length,
    literalRpcInvocations.length,
    `Dynamic/unowned RPC name in ${name}`,
  )
  literalRpcInvocations.forEach((match) => rpcOwnership.add(`${name}:${match[1]}`))
}

assert.deepEqual(dataReads, [], 'Browser code must not read ERP tables/views directly')

assert.deepEqual([...rpcOwnership].sort(), [
  'src/AccessControlPage.tsx:erp_deactivate_role_v1',
  'src/AccessControlPage.tsx:erp_get_access_admin_v1',
  'src/AccessControlPage.tsx:erp_save_app_user_v3',
  'src/AccessControlPage.tsx:erp_save_role_v1',
  'src/ConnectedCuttingPage.tsx:erp_get_cutting_workspace_v1',
  'src/ConnectedCuttingPage.tsx:erp_save_cutting_group_before_sewing_v2',
  'src/ConnectedBsResolutionPage.tsx:erp_get_bs_resolution_workspace_v1',
  'src/ConnectedBsResolutionPage.tsx:erp_save_bs_resolution_action_v1',
  'src/ConnectedPatternFilter.tsx:erp_list_patterns_v1',
  'src/ConnectedPickupPage.tsx:erp_get_cutting_pickup_queue_v1',
  'src/ConnectedPickupPage.tsx:erp_save_cutting_pickup_v1',
  'src/ConnectedWipStatusPage.tsx:erp_get_wip_control_v1',
  'src/ConnectedWipStatusPage.tsx:erp_set_wip_control_flag_v1',
  'src/CuttingPatternPicker.tsx:erp_list_patterns_v1',
  'src/CuttingPatternPicker.tsx:erp_save_pattern_v1',
  'src/PatternPage.tsx:erp_deactivate_pattern_v1',
  'src/PatternPage.tsx:erp_list_patterns_v1',
  'src/PatternPage.tsx:erp_save_pattern_v1',
  'src/auth/AuthProvider.tsx:erp_get_my_access_v1',
  'src/useLaundryQcWorkspace.ts:erp_get_laundry_qc_workspace_v1',
  'src/useLaundryQcWorkspace.ts:erp_save_laundry_qc_action_v1',
  'src/useLaundryQcWorkspace.ts:erp_search_final_sku_products_v1',
].sort(), 'Browser RPC ownership drift')

console.log(`Source ownership passed: ${reachable.size} runtime files, ${rpcOwnership.size} owned RPC boundaries, no orphan or direct table access.`)
