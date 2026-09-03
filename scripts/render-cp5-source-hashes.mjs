import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
const manifestRelative = 'docs/evidence/cp5_r1_source_hashes.json'
const ownershipRelative = 'docs/evidence/backend_source_ownership_v3.json'
const frozenV2Relative = 'docs/evidence/backend_source_ownership_v2.json'
const cuttingManifestRelative = 'docs/evidence/cutting_bridge_v2618_source_hashes.json'
const manifestPath = resolve(root, manifestRelative)
const ownershipPath = resolve(root, ownershipRelative)
const frozenV2Path = resolve(root, frozenV2Relative)
const cuttingManifestPath = resolve(root, cuttingManifestRelative)
const cuttingMigrationRelative = 'supabase/migrations/20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.sql'
const cuttingRollbackRelative = 'supabase/rollbacks/20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.rollback.sql'
const correctionMigrationRelative = 'supabase/migrations/20260903070931_erp_v2_6_18a_cutting_bridge_reconciliation.sql'
const correctionRollbackRelative = 'supabase/rollbacks/20260903070931_erp_v2_6_18a_cutting_bridge_reconciliation.rollback.sql'
const cp5MigrationRelative = 'supabase/migrations/20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.sql'
const cp5RollbackRelative = 'supabase/rollbacks/20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.rollback.sql'

const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex')
const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim()
const lines = (value) => value.split('\n').map((line) => line.trim()).filter(Boolean)

const frozenV2Bytes = readFileSync(frozenV2Path)
const cuttingManifestBytes = readFileSync(cuttingManifestPath)
assert.equal(frozenV2Bytes.length, 546, 'Frozen ownership v2 byte length drift')
assert.equal(
  sha256(frozenV2Bytes),
  '55cc9196c9097415780cee4739c235d358e6831a9a07006459d5f86761dd91f9',
  'Frozen ownership v2 SHA-256 drift',
)
assert.equal(cuttingManifestBytes.length, 8515, 'Frozen Cutting Bridge manifest byte length drift')
assert.equal(
  sha256(cuttingManifestBytes),
  'b33061e457bd0225546d361e0385921c7ebcdd127efa23f4610bf3ba06ce653d',
  'Frozen Cutting Bridge manifest SHA-256 drift',
)

const previous = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, 'utf8')) : null

function bindRollback(rollbackRelative, placeholder, previousHash, nextHash) {
  const path = resolve(root, rollbackRelative)
  const source = readFileSync(path, 'utf8')
  if (source.includes(nextHash)) {
    assert.equal(source.split(nextHash).length - 1, 3, `${rollbackRelative} must contain exactly three guarded ledger hash bindings`)
    return
  }
  const needle = source.includes(placeholder) ? placeholder : previousHash
  assert.match(needle ?? '', /^(?:__[A-Z0-9_]+__|[0-9a-f]{64})$/, `No prior ledger hash is available for ${rollbackRelative}`)
  assert.equal(source.split(needle).length - 1, 3, `${rollbackRelative} must contain exactly three guarded ledger hash bindings`)
  const rendered = source.split(needle).join(nextHash)
  if (rendered !== source) writeFileSync(path, rendered)
}

const cuttingMigrationBytes = readFileSync(resolve(root, cuttingMigrationRelative))
const correctionMigrationBytes = readFileSync(resolve(root, correctionMigrationRelative))
const cp5MigrationBytes = readFileSync(resolve(root, cp5MigrationRelative))
const cuttingMigrationHash = sha256(cuttingMigrationBytes)
const correctionMigrationHash = sha256(correctionMigrationBytes)
const cp5MigrationHash = sha256(cp5MigrationBytes)
assert.equal(cuttingMigrationBytes.length, 80392, 'Recorded UAT v2.6.18 source byte length drift')
assert.equal(cuttingMigrationHash, '6a568a78ad0b9baa2ef5ee958ee967d7c997cc1f4dfb7f0e4ef5e6ff69e5038f', 'Recorded UAT v2.6.18 source SHA-256 drift')
bindRollback(
  cuttingRollbackRelative, '__CUTTING_BRIDGE_MIGRATION_SHA256__',
  previous?.migrations?.cutting_bridge?.source_sha256, cuttingMigrationHash,
)
bindRollback(
  correctionRollbackRelative, '__CUTTING_BRIDGE_RECONCILIATION_MIGRATION_SHA256__',
  previous?.migrations?.cutting_bridge_reconciliation?.source_sha256, correctionMigrationHash,
)
bindRollback(
  cp5RollbackRelative, '__BS_RESOLUTION_MIGRATION_SHA256__',
  previous?.migrations?.bs_resolution?.source_sha256, cp5MigrationHash,
)

const sourceBaseSha = previous?.source_base_sha ?? git('rev-parse', 'HEAD')
const sourceBaseTree = previous?.source_base_tree ?? git('rev-parse', `${sourceBaseSha}^{tree}`)
const generationParentSha = process.env.CP5_GENERATION_PARENT_SHA || git('rev-parse', 'HEAD')
assert.match(sourceBaseSha, /^[0-9a-f]{40}$/)
assert.match(sourceBaseTree, /^[0-9a-f]{40}$/)
assert.match(generationParentSha, /^[0-9a-f]{40}$/)

const deleted = lines(git('diff', '--name-only', '--diff-filter=D', sourceBaseSha, '--'))
assert.deepEqual(deleted, [], 'CP5 manifest does not conceal deletions; record or restore deleted files first')
const trackedDelta = lines(git('diff', '--name-only', '--diff-filter=ACMRTUXB', sourceBaseSha, '--'))
const untracked = lines(git('ls-files', '--others', '--exclude-standard'))
const excluded = new Set([manifestRelative, ownershipRelative])
const candidates = [...new Set([...trackedDelta, ...untracked])]
  .filter((path) => !excluded.has(path))
  .filter((path) => !path.startsWith('supabase/.temp/'))
  .filter((path) => existsSync(resolve(root, path)) && statSync(resolve(root, path)).isFile())
  .sort()
assert.ok(candidates.length > 0, 'CP5 candidate file set is empty')

const files = Object.fromEntries(candidates.map((path) => {
  const bytes = readFileSync(resolve(root, path))
  return [path, { bytes: bytes.length, sha256: sha256(bytes) }]
}))

const manifest = {
  format: 'CP5_R1_SOURCE_HASHES_V1',
  candidate_branch: previous?.candidate_branch ?? git('branch', '--show-current'),
  source_base_sha: sourceBaseSha,
  source_base_tree: sourceBaseTree,
  generation_parent_sha: generationParentSha,
  target_project_ref: 'siimvrusnzxexizpyoib',
  target_environment: 'ERP Enteng UAT',
  legacy_project_ref: 'vlxdhpkjeevubjxexnfo',
  migrations: {
    cutting_bridge: {
      version: '20260903022604', application_version: 'v2.6.18',
      name: 'erp_v2_6_18_cutting_persistence_pickup_wip',
      source_path: cuttingMigrationRelative,
      source_bytes: cuttingMigrationBytes.length,
      source_sha256: cuttingMigrationHash,
      rollback_path: cuttingRollbackRelative,
      acceptance_path: 'supabase/tests/cutting_bridge_persistence_pickup_wip_rollback.sql',
      uat_applied: true,
      uat_platform_ledger_version: '20260903060213',
      uat_platform_statement_count: 1,
      uat_business_facts_observed: 0,
    },
    cutting_bridge_reconciliation: {
      version: '20260903070931', application_version: 'v2.6.18a',
      name: 'erp_v2_6_18a_cutting_bridge_reconciliation',
      source_path: correctionMigrationRelative,
      source_bytes: correctionMigrationBytes.length,
      source_sha256: correctionMigrationHash,
      rollback_path: correctionRollbackRelative,
      acceptance_path: 'supabase/tests/cutting_bridge_persistence_pickup_wip_rollback.sql',
      uat_applied: false,
    },
    bs_resolution: {
      version: '20260903070932', application_version: 'v2.6.19',
      name: 'erp_v2_6_19_cp5_bs_resolution_recovery',
      source_path: cp5MigrationRelative,
      source_bytes: cp5MigrationBytes.length,
      source_sha256: cp5MigrationHash,
      rollback_path: cp5RollbackRelative,
      acceptance_path: 'supabase/tests/cp5_bs_resolution_recovery_rollback.sql',
      uat_applied: false,
    },
  },
  verification: {
    status: 'SOURCE_RECONCILED_PENDING_FULL_SCHEMA_CI_AND_UAT_V2618A_CP5',
    required_local_commands: ['npm test', 'npm run build', 'npm run test:security'],
    full_schema_acceptance_executed: false,
    hosted_uat_executed: false,
    read_only_uat_preflight_executed: true,
    read_only_uat_preflight_path: 'docs/evidence/cp5_uat_readonly_preflight.json',
  },
  candidate_apply_status: 'PARTIAL_RECORDED_V2618_ONLY',
  uat_partial_state: {
    recorded_application_version: 'v2.6.18',
    recorded_platform_version: '20260903060213',
    correction_pending: 'v2.6.18a',
    cp5_pending: 'v2.6.19',
  },
  source_only: false,
  uat_applied: false,
  uat_applied_at: null,
  legacy_mutated: false,
  production_go: false,
  files,
}
writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`)

const manifestBytes = readFileSync(manifestPath)
const ownership = {
  format: 'ERP_BACKEND_SOURCE_OWNERSHIP_V3',
  frozen_v2: {
    path: frozenV2Relative,
    bytes: frozenV2Bytes.length,
    sha256: sha256(frozenV2Bytes),
  },
  candidate_cutting_bridge_manifest: {
    path: cuttingManifestRelative,
    bytes: cuttingManifestBytes.length,
    sha256: sha256(cuttingManifestBytes),
  },
  candidate_cp5_manifest: {
    path: manifestRelative,
    bytes: manifestBytes.length,
    sha256: sha256(manifestBytes),
  },
  target_project_ref: 'siimvrusnzxexizpyoib',
  legacy_project_ref: 'vlxdhpkjeevubjxexnfo',
  source_only: false,
  uat_applied: false,
  candidate_apply_status: 'PARTIAL_RECORDED_V2618_ONLY',
  production_go: false,
}
writeFileSync(ownershipPath, `${JSON.stringify(ownership, null, 2)}\n`)

console.log(`Rendered CP5 source ownership: ${candidates.length} byte-bound files; migration ledgers ${cuttingMigrationHash.slice(0, 12)} / ${correctionMigrationHash.slice(0, 12)} / ${cp5MigrationHash.slice(0, 12)}.`)
