import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { readFileSync, readdirSync } from 'node:fs'
import { extname, join, relative, resolve } from 'node:path'
import { gunzipSync } from 'node:zlib'

const root = process.cwd()
const posix = (path) => path.split('\\').join('/')
const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim()
const hash = (algorithm, bytes) => createHash(algorithm).update(bytes).digest('hex')
const readJson = (path) => JSON.parse(readFileSync(resolve(root, path), 'utf8'))
const shaFile = (path) => hash('sha256', readFileSync(resolve(root, path)))
const ownershipV1Path = 'docs/evidence/backend_source_ownership.json'
const ownershipV2Path = 'docs/evidence/backend_source_ownership_v2.json'
const ownershipV3Path = 'docs/evidence/backend_source_ownership_v3.json'

const ownershipV1Bytes = readFileSync(resolve(root, ownershipV1Path))
const ownershipV2Bytes = readFileSync(resolve(root, ownershipV2Path))
const ownershipV3 = readJson(ownershipV3Path)
const ownershipV1 = JSON.parse(ownershipV1Bytes)
const ownershipV2 = JSON.parse(ownershipV2Bytes)

assert.equal(hash('sha256', ownershipV1Bytes), '5da3ee5d3b906ebdd1f4bfb55d35a91b3ce6d715c03b98463e6dee35ad04dd1e')
assert.equal(hash('sha256', ownershipV2Bytes), '55cc9196c9097415780cee4739c235d358e6831a9a07006459d5f86761dd91f9')
assert.equal(ownershipV1.format, 'ERP_BACKEND_SOURCE_OWNERSHIP_V1')
assert.equal(ownershipV2.format, 'ERP_BACKEND_SOURCE_OWNERSHIP_V2')
assert.equal(ownershipV3.format, 'ERP_BACKEND_SOURCE_OWNERSHIP_V3')
assert.deepEqual(ownershipV3.frozen_v2, {
  path: ownershipV2Path,
  bytes: 546,
  sha256: '55cc9196c9097415780cee4739c235d358e6831a9a07006459d5f86761dd91f9',
})
assert.equal(ownershipV3.target_project_ref, 'siimvrusnzxexizpyoib')
assert.equal(ownershipV3.legacy_project_ref, 'vlxdhpkjeevubjxexnfo')
assert.equal(ownershipV3.production_go, false)

const cp3ManifestBytes = readFileSync(resolve(root, ownershipV1.reviewed_cp3_manifest.path))
const cp4ManifestBytes = readFileSync(resolve(root, ownershipV1.candidate_cp4_manifest.path))
const cp45ManifestBytes = readFileSync(resolve(root, ownershipV2.candidate_cp45_manifest.path))
assert.equal(hash('sha256', cp3ManifestBytes), ownershipV1.reviewed_cp3_manifest.sha256)
assert.equal(hash('sha256', cp4ManifestBytes), ownershipV1.candidate_cp4_manifest.sha256)
assert.equal(hash('sha256', cp45ManifestBytes), ownershipV2.candidate_cp45_manifest.sha256)
const cp3Manifest = JSON.parse(cp3ManifestBytes)
const cp4Manifest = JSON.parse(cp4ManifestBytes)
const cp45Manifest = JSON.parse(cp45ManifestBytes)

const candidateManifestPath = ownershipV3.candidate_cutting_bridge_manifest.path
const candidateManifestBytes = readFileSync(resolve(root, candidateManifestPath))
assert.equal(candidateManifestBytes.length, ownershipV3.candidate_cutting_bridge_manifest.bytes)
assert.equal(hash('sha256', candidateManifestBytes), ownershipV3.candidate_cutting_bridge_manifest.sha256)
const candidate = JSON.parse(candidateManifestBytes)
assert.equal(candidate.format, 'CUTTING_BRIDGE_V2618_SOURCE_HASHES_V1')
assert.equal(candidate.candidate_branch, 'pre-cp5/cutting-persistence-pickup-wip-r1-20260903')
assert.equal(candidate.source_base_sha, 'd5c48ce5c8daa7e6da92dc9d690d9b36879e74c1')
assert.equal(candidate.source_base_tree, '70f7bf3c0265520eac5aafff747f448ed8be3e6b')
assert.match(candidate.generation_parent_sha, /^[0-9a-f]{40}$/)
assert.equal(candidate.target_project_ref, 'siimvrusnzxexizpyoib')
assert.equal(candidate.legacy_project_ref, 'vlxdhpkjeevubjxexnfo')
assert.equal(candidate.migration_version, '20260903022604')
assert.equal(candidate.migration_name, 'erp_v2_6_18_cutting_persistence_pickup_wip')
assert.equal(candidate.application_version, 'v2.6.18')
assert.equal(candidate.scope, 'PRE_CP5_CUTTING_PERSISTENCE_PICKUP_WIP_BRIDGE')
assert.equal(candidate.cp5_scope, 'BS_RESOLUTION_NOT_STARTED')
assert.equal(candidate.legacy_mutated, false)
assert.equal(candidate.production_go, false)
assert.deepEqual(candidate.truth_boundary, {
  cutting_final_save: 'UAT_RPC_CONNECTED',
  pickup_distribution: 'UAT_RPC_CONNECTED',
  wip_control: 'UAT_RPC_CONNECTED',
  pickup_pattern_filter: 'SERVER_SIDE_PATTERN_ID',
  wip_pattern_filter: 'SERVER_SIDE_PATTERN_ID',
  laundry_pattern_filter: 'SIMULATION_ONLY',
  qc_pattern_filter: 'SIMULATION_ONLY',
})
assert.equal(candidate.hygiene.cloudflare_dry_run_environment, 'uat-auth')
assert.equal(candidate.hygiene.production_deploy_authorized, false)

const githubSourceBranch = process.env.GITHUB_HEAD_REF || process.env.GITHUB_REF_NAME
if (process.env.GITHUB_ACTIONS === 'true' && githubSourceBranch === candidate.candidate_branch) {
  assert.equal(candidate.generation_parent_sha, git('rev-parse', 'HEAD^'))
}

const candidatePaths = Object.keys(candidate.files).sort()
assert.ok(candidatePaths.length > 0, 'Cutting Bridge manifest is empty')
assert.equal(new Set(candidatePaths).size, candidatePaths.length)
assert.equal(candidatePaths.includes(candidateManifestPath), false)
assert.equal(candidatePaths.includes(ownershipV3Path), false)
assert.equal(candidatePaths.some((path) => path.startsWith('supabase/.temp/')), false)
assert.equal(candidatePaths.some((path) => path.startsWith('cp45-browser-proof/')), false)
for (const [path, expected] of Object.entries(candidate.files)) {
  const bytes = readFileSync(resolve(root, path))
  assert.equal(bytes.length, expected.bytes, `Cutting Bridge byte length drift: ${path}`)
  assert.equal(hash('sha256', bytes), expected.sha256, `Cutting Bridge SHA-256 drift: ${path}`)
}

const deltaPaths = git('diff', '--name-only', '--diff-filter=ACMRTUXB', candidate.source_base_tree, 'HEAD', '--')
  .split('\n').map((path) => path.trim()).filter(Boolean)
  .filter((path) => ![candidateManifestPath, ownershipV3Path].includes(path))
  .sort()
assert.deepEqual(candidatePaths, deltaPaths, 'Manifest does not bind the exact candidate delta')

const fixedEntries = [
  ...ownershipV1.uat_recorded_sources,
  ...ownershipV1.recorded_migration_regressions,
  ...ownershipV1.uat_provenance,
]
const baseFiles = {
  ...cp3Manifest.files,
  ...cp4Manifest.files,
  ...Object.fromEntries(fixedEntries.map((entry) => [entry.path, entry])),
  ...cp45Manifest.files,
}
const overridden = new Set(candidatePaths)
for (const [path, expected] of Object.entries(baseFiles)) {
  if (overridden.has(path)) continue
  const bytes = readFileSync(resolve(root, path))
  assert.equal(bytes.length, expected.bytes, `Frozen byte length drift: ${path}`)
  assert.equal(hash('sha256', bytes), expected.sha256, `Frozen SHA-256 drift: ${path}`)
  if (expected.ledger_version) assert.equal(hash('md5', bytes), expected.md5, `Frozen ledger MD5 drift: ${path}`)
}

function walk(directory, accept) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) return walk(path, accept)
    return accept(path) ? [posix(relative(root, path))] : []
  })
}

const discovered = [
  ...walk(resolve(root, 'supabase/migrations'), (path) => extname(path) === '.sql'),
  ...walk(resolve(root, 'supabase/rollbacks'), (path) => extname(path) === '.sql'),
  ...walk(resolve(root, 'supabase/tests'), (path) => extname(path) === '.sql'),
  ...walk(resolve(root, 'ops/supabase'), (path) => extname(path) === '.sql'),
  ...walk(resolve(root, 'scripts'), (path) => /^(?:cp3_|test_cp3_|cp4_|cp45_|cutting_bridge_).*\.(?:py|mjs)$/.test(path.split('/').at(-1))),
  ...walk(resolve(root, 'scripts'), (path) => /^check-backend-ownership(?:-v\d+)?\.mjs$/.test(path.split('/').at(-1))),
  ...walk(resolve(root, '.github/workflows'), (path) => /^(?:cp3|cp4|cp45|cutting-bridge).*\.ya?ml$/.test(path.split('/').at(-1))),
  ...walk(resolve(root, 'docs/evidence'), (path) => /^(?:cp4|cp45|cutting_bridge).*hosted.*e2e\.json$/.test(path.split('/').at(-1))),
].sort()
const owned = new Set([
  ...Object.keys(baseFiles),
  ...candidatePaths,
  'scripts/check-backend-ownership.mjs',
  'scripts/check-backend-ownership-v2.mjs',
  'scripts/check-backend-ownership-v3.mjs',
  '.github/workflows/cp3-r4-full-schema-validation.yml',
  '.github/workflows/cp4-full-schema-validation.yml',
  '.github/workflows/cp45-full-schema-validation.yml',
  '.github/workflows/cutting-bridge-full-schema-validation.yml',
  'docs/evidence/cp4_hosted_uat_auth_e2e.json',
])
const unowned = discovered.filter((path) => !owned.has(path))
assert.deepEqual(unowned, [], `Backend source/proof file is unowned: ${unowned.join(', ')}`)

const migrationPath = 'supabase/migrations/20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.sql'
const rollbackPath = 'supabase/rollbacks/20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.rollback.sql'
const acceptancePath = 'supabase/tests/cutting_bridge_persistence_pickup_wip_rollback.sql'
for (const path of [migrationPath, rollbackPath, acceptancePath]) assert.ok(candidatePaths.includes(path), `${path} is not byte-bound`)
assert.deepEqual(candidatePaths.filter((path) => path.startsWith('supabase/migrations/20260903022604_')), [migrationPath])
assert.deepEqual(candidatePaths.filter((path) => path.startsWith('supabase/rollbacks/20260903022604_')), [rollbackPath])
assert.ok(candidatePaths.includes('src/ConnectedCuttingPage.tsx'))
assert.ok(candidatePaths.includes('src/ConnectedPickupPage.tsx'))
assert.ok(candidatePaths.includes('src/ConnectedWipStatusPage.tsx'))
assert.ok(candidatePaths.includes('src/ConnectedPatternFilter.tsx'))
assert.ok(candidatePaths.includes('tests/browser/cutting-bridge.spec.ts'))
assert.ok(candidatePaths.includes('.github/workflows/cutting-bridge-full-schema-validation.yml'))

const ledgerFixturePath = 'supabase/tests/fixtures/erp_enteng_pre_cp3_schema_ledger.sql.gz'
const ledgerFixtureManifestPath = 'supabase/tests/fixtures/erp_enteng_pre_cp3_schema_ledger.manifest.json'
assert.ok(candidatePaths.includes(ledgerFixturePath))
assert.ok(candidatePaths.includes(ledgerFixtureManifestPath))
assert.ok(candidatePaths.includes('scripts/cutting_bridge_build_ledger_bootstrap.py'))
const ledgerFixtureManifest = readJson(ledgerFixtureManifestPath)
const ledgerFixture = readFileSync(resolve(root, ledgerFixturePath))
const ledgerSql = gunzipSync(ledgerFixture)
assert.equal(ledgerFixtureManifest.format, 'ERP_ENTENG_PRE_CP3_SCHEMA_LEDGER_BOOTSTRAP_V1')
assert.equal(ledgerFixtureManifest.source_project_ref, 'siimvrusnzxexizpyoib')
assert.equal(ledgerFixtureManifest.source_kind, 'SUPABASE_PLATFORM_LEDGER_SCHEMA_SOURCE_ONLY')
assert.equal(ledgerFixtureManifest.contains_business_rows, false)
assert.equal(ledgerFixtureManifest.contains_credentials, false)
assert.equal(ledgerFixtureManifest.first_version, '20260826112217')
assert.equal(ledgerFixtureManifest.last_version, '20260831032949')
assert.equal(ledgerFixtureManifest.executable_migration_count, 48)
assert.equal(ledgerFixtureManifest.platform_marker_count, 7)
assert.equal(ledgerFixtureManifest.expected_platform_count, 55)
assert.equal(ledgerFixtureManifest.ledger_manifest_sha256, '103b938b48303d75bb056db1e30265a34ccecd9c52db070f842db4d5977197b8')
assert.equal(ledgerFixture.length, ledgerFixtureManifest.gzip_bytes)
assert.equal(hash('sha256', ledgerFixture), ledgerFixtureManifest.gzip_sha256)
assert.equal(ledgerSql.length, ledgerFixtureManifest.sql_bytes)
assert.equal(hash('sha256', ledgerSql), ledgerFixtureManifest.sql_sha256)
assert.equal(ledgerFixtureManifest.migrations.length, 48)
assert.equal(ledgerFixtureManifest.platform_markers.length, 7)

const migration = readFileSync(resolve(root, migrationPath), 'utf8')
const rollback = readFileSync(resolve(root, rollbackPath), 'utf8')
assert.match(migration, /perform erp\.require_permission\('production\.cutting\.post'\)/)
assert.match(migration, /perform erp\.require_permission\('production\.distribution\.post'\)/)
assert.match(migration, /p_pattern_id uuid default null/)
assert.match(migration, /if tg_op='DELETE' then return old; end if;/)
assert.doesNotMatch(rollback, /__CUTTING_BRIDGE_MIGRATION_SHA256__/)
const normalizeSql = (value) => value.replace(/\s+/g, ' ').trim()
const guardPredicate = rollback.match(/select count\(\*\) into v_match_count\s+from supabase_migrations\.schema_migrations m\s+where ([\s\S]*?);\s+select count\(\*\) into v_conflict_count/)
const deletePredicate = rollback.match(/delete from supabase_migrations\.schema_migrations m\s+where ([\s\S]*?);\s+drop table erp\.cutting_bridge_v2618_rollback_capsule/)
assert.ok(guardPredicate, 'Cutting Bridge rollback ledger guard is missing')
assert.ok(deletePredicate, 'Cutting Bridge rollback ledger DELETE is missing')
assert.equal(normalizeSql(guardPredicate[1]), normalizeSql(deletePredicate[1]), 'Rollback guard and DELETE ledger predicates differ')

const activeBaseFiles = Object.keys(baseFiles).filter((path) => !overridden.has(path))
const effectiveOwned = new Set([...activeBaseFiles, ...candidatePaths])
console.log(`Backend ownership v3 passed: ${effectiveOwned.size} effective unique source/proof files (${activeBaseFiles.length} inherited + ${candidatePaths.length} Cutting Bridge, ${Object.keys(baseFiles).length - activeBaseFiles.length} overrides); ${discovered.length} backend artifacts discovered, zero unowned.`)
