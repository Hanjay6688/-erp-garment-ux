import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { extname, join, relative, resolve } from 'node:path'

const root = process.cwd()
const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim()
const gitBytes = (...args) => execFileSync('git', args, { cwd: root })
const hash = (algorithm, bytes) => createHash(algorithm).update(bytes).digest('hex')
const posix = (path) => path.split('\\').join('/')
const readJson = (path) => JSON.parse(readFileSync(resolve(root, path), 'utf8'))
const lines = (value) => value.split('\n').map((line) => line.trim()).filter(Boolean)

const ownershipV1Path = 'docs/evidence/backend_source_ownership.json'
const ownershipV2Path = 'docs/evidence/backend_source_ownership_v2.json'
const ownershipV3Path = 'docs/evidence/backend_source_ownership_v3.json'
const ownershipV1Bytes = readFileSync(resolve(root, ownershipV1Path))
const ownershipV2Bytes = readFileSync(resolve(root, ownershipV2Path))
const ownershipV1 = JSON.parse(ownershipV1Bytes)
const ownershipV2 = JSON.parse(ownershipV2Bytes)
const ownershipV3 = readJson(ownershipV3Path)

assert.equal(ownershipV1Bytes.length, 3894)
assert.equal(hash('sha256', ownershipV1Bytes), '5da3ee5d3b906ebdd1f4bfb55d35a91b3ce6d715c03b98463e6dee35ad04dd1e')
assert.equal(ownershipV2Bytes.length, 546)
assert.equal(hash('sha256', ownershipV2Bytes), '55cc9196c9097415780cee4739c235d358e6831a9a07006459d5f86761dd91f9')
assert.equal(ownershipV1.format, 'ERP_BACKEND_SOURCE_OWNERSHIP_V1')
assert.equal(ownershipV2.format, 'ERP_BACKEND_SOURCE_OWNERSHIP_V2')
assert.equal(ownershipV3.format, 'ERP_BACKEND_SOURCE_OWNERSHIP_V3')
assert.deepEqual(ownershipV3.frozen_v2, {
  path: ownershipV2Path,
  bytes: 546,
  sha256: '55cc9196c9097415780cee4739c235d358e6831a9a07006459d5f86761dd91f9',
})
assert.deepEqual(ownershipV3.candidate_cutting_bridge_manifest, {
  path: 'docs/evidence/cutting_bridge_v2618_source_hashes.json',
  bytes: 8515,
  sha256: 'b33061e457bd0225546d361e0385921c7ebcdd127efa23f4610bf3ba06ce653d',
})
for (const ownership of [ownershipV2, ownershipV3]) {
  assert.equal(ownership.target_project_ref, 'siimvrusnzxexizpyoib')
  assert.equal(ownership.legacy_project_ref, 'vlxdhpkjeevubjxexnfo')
  assert.equal(ownership.production_go, false)
}
assert.equal(ownershipV3.source_only, false)
assert.equal(ownershipV3.uat_applied, false)
assert.equal(ownershipV3.candidate_apply_status, 'PARTIAL_RECORDED_V2618_ONLY')

const cp3ManifestBytes = readFileSync(resolve(root, ownershipV1.reviewed_cp3_manifest.path))
const cp4ManifestBytes = readFileSync(resolve(root, ownershipV1.candidate_cp4_manifest.path))
const cp45ManifestBytes = readFileSync(resolve(root, ownershipV2.candidate_cp45_manifest.path))
assert.equal(hash('sha256', cp3ManifestBytes), ownershipV1.reviewed_cp3_manifest.sha256)
assert.equal(hash('sha256', cp4ManifestBytes), ownershipV1.candidate_cp4_manifest.sha256)
assert.equal(cp45ManifestBytes.length, ownershipV2.candidate_cp45_manifest.bytes)
assert.equal(hash('sha256', cp45ManifestBytes), ownershipV2.candidate_cp45_manifest.sha256)
const cp3Manifest = JSON.parse(cp3ManifestBytes)
const cp4Manifest = JSON.parse(cp4ManifestBytes)
const cp45Manifest = JSON.parse(cp45ManifestBytes)
assert.equal(cp3Manifest.format, 'CP3_R5_CURRENT_MAIN_FIXED_SOURCE_HASHES_V1')
assert.equal(cp4Manifest.format, 'CP4_R1_SOURCE_HASHES_V1')
assert.equal(cp45Manifest.format, 'CP45_R1_SOURCE_HASHES_V1')
assert.equal(cp45Manifest.production_go, false)

const fixedEntries = [
  ...ownershipV1.uat_recorded_sources,
  ...ownershipV1.recorded_migration_regressions,
  ...ownershipV1.uat_provenance,
]
const preCp45Frozen = {
  ...cp3Manifest.files,
  ...cp4Manifest.files,
  ...Object.fromEntries(fixedEntries.map((entry) => [entry.path, entry])),
}

function isCp45Backend(path) {
  return path.startsWith('supabase/migrations/')
    || path.startsWith('supabase/rollbacks/')
    || path.startsWith('supabase/tests/')
    || path.startsWith('ops/supabase/')
    || /^scripts\/cp45_.*\.mjs$/.test(path)
    || /^scripts\/cp45_.*\.py$/.test(path)
    || path === 'scripts/check-backend-ownership-v2.mjs'
    || path === '.github/workflows/cp45-full-schema-validation.yml'
    || path === cp45Manifest.hosted_auth_permission_e2e.evidence_path
    || path === cp45Manifest.integrity_correction.hosted_auth_permission_e2e.evidence_path
}

const cuttingManifestPath = ownershipV3.candidate_cutting_bridge_manifest.path
const cuttingManifestBytes = readFileSync(resolve(root, cuttingManifestPath))
assert.equal(cuttingManifestBytes.length, ownershipV3.candidate_cutting_bridge_manifest.bytes)
assert.equal(hash('sha256', cuttingManifestBytes), ownershipV3.candidate_cutting_bridge_manifest.sha256)
const cutting = JSON.parse(cuttingManifestBytes)
const candidateManifestBytes = readFileSync(resolve(root, ownershipV3.candidate_cp5_manifest.path))
assert.equal(candidateManifestBytes.length, ownershipV3.candidate_cp5_manifest.bytes)
assert.equal(hash('sha256', candidateManifestBytes), ownershipV3.candidate_cp5_manifest.sha256)
const candidate = JSON.parse(candidateManifestBytes)
const cuttingPaths = Object.keys(cutting.files).sort()
const candidatePaths = Object.keys(candidate.files).sort()
const cuttingOverrides = new Set(cuttingPaths)
const cp5Overrides = new Set(candidatePaths)

assert.equal(cutting.format, 'CUTTING_BRIDGE_V2618_SOURCE_HASHES_V1')
assert.equal(cutting.candidate_branch, 'pre-cp5/cutting-persistence-pickup-wip-r1-20260903')
assert.equal(cutting.source_base_sha, 'd5c48ce5c8daa7e6da92dc9d690d9b36879e74c1')
assert.equal(cutting.source_base_tree, '70f7bf3c0265520eac5aafff747f448ed8be3e6b')
assert.equal(cutting.target_project_ref, 'siimvrusnzxexizpyoib')
assert.equal(cutting.legacy_project_ref, 'vlxdhpkjeevubjxexnfo')
assert.equal(cutting.migration_version, '20260903022604')
assert.equal(cutting.migration_name, 'erp_v2_6_18_cutting_persistence_pickup_wip')
assert.equal(cutting.application_version, 'v2.6.18')
assert.equal(cutting.source_only, false)
assert.equal(cutting.uat_applied, true)
assert.equal(cutting.legacy_mutated, false)
assert.equal(cutting.production_go, false)
assert.equal(cutting.ci_runtime.status, 'PASS')
assert.equal(cutting.hosted_auth_permission_e2e.status, 'PASS')
assert.equal(cutting.hosted_auth_permission_e2e.case_count, 14)
assert.equal(cutting.hosted_auth_permission_e2e.case_passed, 14)

const frozenBackend = {
  ...preCp45Frozen,
  ...Object.fromEntries(Object.entries(cp45Manifest.files).filter(([path]) => isCp45Backend(path))),
}
for (const [path, expected] of Object.entries(frozenBackend)) {
  if (cuttingOverrides.has(path) || cp5Overrides.has(path)) continue
  const bytes = readFileSync(resolve(root, path))
  assert.equal(bytes.length, expected.bytes, `Frozen backend byte length drift: ${path}`)
  assert.equal(hash('sha256', bytes), expected.sha256, `Frozen backend SHA-256 drift: ${path}`)
  if (expected.ledger_version) {
    assert.ok(path.split('/').at(-1).startsWith(`${expected.ledger_version}_`), `Frozen ledger filename mismatch: ${path}`)
    assert.equal(hash('md5', bytes), expected.md5, `Frozen UAT ledger bytes drift: ${path}`)
  }
}
assert.equal(candidate.format, 'CP5_R1_SOURCE_HASHES_V1')
assert.equal(candidate.candidate_branch, 'pre-cp5/cutting-persistence-pickup-wip-r1-20260903')
assert.equal(candidate.source_base_sha, '8bfac13b91ea1be92111139e2fddcabccf9ae19a')
assert.equal(candidate.source_base_tree, 'a9b193010266bb686c57709865a992769a835855')
assert.equal(candidate.generation_parent_sha, candidate.source_base_sha)
assert.equal(git('rev-parse', `${candidate.source_base_sha}^{tree}`), candidate.source_base_tree)
assert.equal(candidate.target_project_ref, 'siimvrusnzxexizpyoib')
assert.equal(candidate.legacy_project_ref, 'vlxdhpkjeevubjxexnfo')
assert.equal(candidate.source_only, false)
assert.equal(candidate.uat_applied, false)
assert.equal(candidate.uat_applied_at, null)
assert.equal(candidate.candidate_apply_status, 'PARTIAL_RECORDED_V2618_ONLY')
assert.deepEqual(candidate.uat_partial_state, {
  recorded_application_version: 'v2.6.18',
  recorded_platform_version: '20260903060213',
  correction_pending: 'v2.6.18a',
  cp5_pending: 'v2.6.19',
})
assert.equal(candidate.legacy_mutated, false)
assert.equal(candidate.production_go, false)
assert.equal(candidate.verification.status, 'SOURCE_RECONCILED_PENDING_FULL_SCHEMA_CI_AND_UAT_V2618A_CP5')
assert.equal(candidate.verification.full_schema_acceptance_executed, false)
assert.equal(candidate.verification.hosted_uat_executed, false)
assert.equal(candidate.verification.read_only_uat_preflight_executed, true)
assert.equal(candidate.verification.read_only_uat_preflight_path, 'docs/evidence/cp5_uat_readonly_preflight.json')
const uatPreflight = readJson(candidate.verification.read_only_uat_preflight_path)
assert.equal(uatPreflight.format, 'CP5_UAT_READONLY_PREFLIGHT_V1')
assert.equal(uatPreflight.query_class, 'SELECT_ONLY')
assert.deepEqual(uatPreflight.application_versions, ['v2.6.18'])
assert.deepEqual(uatPreflight.platform_entries, [{
  version: '20260903060213',
  name: 'erp_v2_6_18_cutting_persistence_pickup_wip',
  statement_count: 1,
  source_bytes: 80392,
  source_sha256: '6a568a78ad0b9baa2ef5ee958ee967d7c997cc1f4dfb7f0e4ef5e6ff69e5038f',
}])
assert.ok(Object.values(uatPreflight.business_facts).every((value) => value === 0))
assert.deepEqual(uatPreflight.activity, { waiting_on_lock: 0, transactions_over_5m: 0 })
assert.deepEqual(uatPreflight.conclusion, {
  exact_recorded_source_matches_local: true,
  v2618a_absent: true,
  v2619_absent: true,
  unused_reconciliation_boundary: true,
  uat_mutated_by_preflight: false,
  production_go: false,
})

const cuttingManifestAtCp5Base = gitBytes('show', `${candidate.source_base_sha}:${cuttingManifestPath}`)
assert.equal(cuttingManifestAtCp5Base.length, cuttingManifestBytes.length)
assert.equal(hash('sha256', cuttingManifestAtCp5Base), hash('sha256', cuttingManifestBytes))
for (const [path, expected] of Object.entries(cutting.files)) {
  const baseBytes = gitBytes('show', `${candidate.source_base_sha}:${path}`)
  assert.equal(baseBytes.length, expected.bytes, `Cutting Bridge base byte length drift: ${path}`)
  assert.equal(hash('sha256', baseBytes), expected.sha256, `Cutting Bridge base SHA-256 drift: ${path}`)
  if (cp5Overrides.has(path)) continue
  const bytes = readFileSync(resolve(root, path))
  assert.equal(bytes.length, expected.bytes, `Unchanged Cutting Bridge byte length drift: ${path}`)
  assert.equal(hash('sha256', bytes), expected.sha256, `Unchanged Cutting Bridge SHA-256 drift: ${path}`)
}

const githubSourceBranch = process.env.GITHUB_HEAD_REF || process.env.GITHUB_REF_NAME
if (process.env.GITHUB_ACTIONS === 'true' && githubSourceBranch === candidate.candidate_branch) {
  assert.equal(candidate.generation_parent_sha, git('rev-parse', 'HEAD^'))
}

assert.ok(candidatePaths.length > 0, 'CP5 candidate manifest is empty')
assert.equal(new Set(candidatePaths).size, candidatePaths.length)
assert.equal(candidatePaths.some((path) => path.startsWith('supabase/.temp/')), false)
assert.equal(candidatePaths.includes(ownershipV3Path), false)
assert.equal(candidatePaths.includes(ownershipV3.candidate_cp5_manifest.path), false)
assert.deepEqual(
  candidatePaths.filter((path) => path in frozenBackend && !cuttingOverrides.has(path)),
  [],
  'CP5 candidate overlaps an immutable pre-Cutting backend artifact',
)
for (const [path, expected] of Object.entries(candidate.files)) {
  const bytes = readFileSync(resolve(root, path))
  assert.equal(bytes.length, expected.bytes, `CP5 byte length drift: ${path}`)
  assert.equal(hash('sha256', bytes), expected.sha256, `CP5 SHA-256 drift: ${path}`)
}

const deleted = lines(git('diff', '--name-only', '--diff-filter=D', candidate.source_base_sha, '--'))
assert.deepEqual(deleted, [], 'CP5 candidate has an unowned deletion')
const expectedCandidatePaths = [...new Set([
  ...lines(git('diff', '--name-only', '--diff-filter=ACMRTUXB', candidate.source_base_sha, '--')),
  ...lines(git('ls-files', '--others', '--exclude-standard')),
])]
  .filter((path) => ![ownershipV3Path, ownershipV3.candidate_cp5_manifest.path].includes(path))
  .filter((path) => !path.startsWith('supabase/.temp/'))
  .filter((path) => existsSync(resolve(root, path)) && statSync(resolve(root, path)).isFile())
  .sort()
assert.deepEqual(candidatePaths, expectedCandidatePaths, 'CP5 manifest is stale or omits a source delta')

for (const [key, expected] of Object.entries({
  cutting_bridge: {
    version: '20260903022604', application_version: 'v2.6.18',
    name: 'erp_v2_6_18_cutting_persistence_pickup_wip',
  },
  cutting_bridge_reconciliation: {
    version: '20260903070931', application_version: 'v2.6.18a',
    name: 'erp_v2_6_18a_cutting_bridge_reconciliation',
  },
  bs_resolution: {
    version: '20260903070932', application_version: 'v2.6.19',
    name: 'erp_v2_6_19_cp5_bs_resolution_recovery',
  },
})) {
  const migration = candidate.migrations[key]
  assert.equal(migration.version, expected.version)
  assert.equal(migration.application_version, expected.application_version)
  assert.equal(migration.name, expected.name)
  const bytes = readFileSync(resolve(root, migration.source_path))
  assert.equal(migration.source_bytes, bytes.length)
  assert.equal(migration.source_sha256, hash('sha256', bytes))
  assert.ok(cuttingOverrides.has(migration.source_path) || cp5Overrides.has(migration.source_path))
  assert.ok(cuttingOverrides.has(migration.rollback_path) || cp5Overrides.has(migration.rollback_path))
  assert.ok(cuttingOverrides.has(migration.acceptance_path) || cp5Overrides.has(migration.acceptance_path))
}
assert.deepEqual(candidate.migrations.cutting_bridge, {
  ...candidate.migrations.cutting_bridge,
  uat_applied: true,
  uat_platform_ledger_version: '20260903060213',
  uat_platform_statement_count: 1,
  uat_business_facts_observed: 0,
})
assert.equal(candidate.migrations.cutting_bridge.source_bytes, 80392)
assert.equal(candidate.migrations.cutting_bridge.source_sha256, '6a568a78ad0b9baa2ef5ee958ee967d7c997cc1f4dfb7f0e4ef5e6ff69e5038f')
assert.equal(candidate.migrations.cutting_bridge_reconciliation.uat_applied, false)
assert.equal(candidate.migrations.bs_resolution.uat_applied, false)

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
  ...walk(resolve(root, 'scripts'), (path) => /^(?:cp3_|test_cp3_|cp4_|cp45_|cp5_|cutting_bridge_).*\.(?:mjs|py)$/.test(path.split('/').at(-1))),
  'scripts/check-backend-ownership.mjs',
  'scripts/check-backend-ownership-v2.mjs',
  'scripts/check-backend-ownership-v3.mjs',
  'scripts/check-cp5-boundary.mjs',
  'scripts/render-cp5-source-hashes.mjs',
  'scripts/render-cutting-bridge-source-hashes.mjs',
  '.github/workflows/cp3-r4-full-schema-validation.yml',
  '.github/workflows/cp4-full-schema-validation.yml',
  '.github/workflows/cp45-full-schema-validation.yml',
  '.github/workflows/cutting-bridge-full-schema-validation.yml',
  '.github/workflows/cp5-full-schema-validation.yml',
  'docs/evidence/cp4_hosted_uat_auth_e2e.json',
  ...(cp45Manifest.hosted_auth_permission_e2e.evidence_path ? [cp45Manifest.hosted_auth_permission_e2e.evidence_path] : []),
  ...(cp45Manifest.integrity_correction.hosted_auth_permission_e2e.evidence_path
    ? [cp45Manifest.integrity_correction.hosted_auth_permission_e2e.evidence_path]
    : []),
  cutting.hosted_evidence_path,
  candidate.verification.read_only_uat_preflight_path,
].sort()

function isCuttingBackend(path) {
  return path.startsWith('supabase/migrations/')
    || path.startsWith('supabase/rollbacks/')
    || path.startsWith('supabase/tests/')
    || path.startsWith('ops/supabase/')
    || /^scripts\/(?:cp45_|cutting_bridge_).*\.(?:mjs|py)$/.test(path)
    || path === 'scripts/check-backend-ownership-v3.mjs'
    || path === 'scripts/render-cutting-bridge-source-hashes.mjs'
    || path === '.github/workflows/cutting-bridge-full-schema-validation.yml'
    || path === cutting.hosted_evidence_path
}

function isCp5Backend(path) {
  return path.startsWith('supabase/migrations/')
    || path.startsWith('supabase/rollbacks/')
    || path.startsWith('supabase/tests/')
    || path.startsWith('ops/supabase/')
    || /^scripts\/cp5_.*\.(?:mjs|py)$/.test(path)
    || path === 'scripts/check-backend-ownership-v3.mjs'
    || path === 'scripts/check-cp5-boundary.mjs'
    || path === 'scripts/render-cp5-source-hashes.mjs'
    || path === '.github/workflows/cp5-full-schema-validation.yml'
    || path === candidate.verification.read_only_uat_preflight_path
}

const candidateBackend = candidatePaths.filter(isCp5Backend)
const cuttingBackend = cuttingPaths.filter(isCuttingBackend)
const backendOwned = new Set([...Object.keys(frozenBackend), ...cuttingBackend, ...candidateBackend])
const unowned = discovered.filter((path) => !backendOwned.has(path))
assert.deepEqual(unowned, [], `Backend source/proof artifact is unowned: ${unowned.join(', ')}`)

const cp5Check = execFileSync(process.execPath, ['scripts/check-cp5-boundary.mjs'], {
  cwd: root,
  encoding: 'utf8',
}).trim()
console.log(cp5Check)
console.log(`Backend ownership v3 passed: ${Object.keys(frozenBackend).length} inherited + ${cuttingBackend.length} Cutting Bridge + ${candidateBackend.length} CP5 backend/proof entries; ${backendOwned.size} effective unique files, ${candidatePaths.length} CP5 source files byte-bound, zero unowned.`)
