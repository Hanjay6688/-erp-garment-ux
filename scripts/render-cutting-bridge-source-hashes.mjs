import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
const manifestRelative = 'docs/evidence/cutting_bridge_v2618_source_hashes.json'
const ownershipRelative = 'docs/evidence/backend_source_ownership_v3.json'
const frozenOwnershipRelative = 'docs/evidence/backend_source_ownership_v2.json'
const hostedEvidenceRelative = 'docs/evidence/cutting_bridge_hosted_uat_auth_e2e.json'
const manifestPath = resolve(root, manifestRelative)
const ownershipPath = resolve(root, ownershipRelative)
const frozenOwnershipPath = resolve(root, frozenOwnershipRelative)
const sourceBaseTree = '70f7bf3c0265520eac5aafff747f448ed8be3e6b'

const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex')
const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim()
const lines = (value) => value.split('\n').map((line) => line.trim()).filter(Boolean)
const generationParent = process.env.CUTTING_BRIDGE_GENERATION_PARENT_SHA || git('rev-parse', 'HEAD')
if (!/^[0-9a-f]{40}$/.test(generationParent)) {
  throw new Error('CUTTING_BRIDGE_GENERATION_PARENT_SHA must be an exact commit SHA')
}

const trackedDelta = lines(git('diff', '--name-only', '--diff-filter=ACMRTUXB', sourceBaseTree, '--'))
const untracked = lines(git('ls-files', '--others', '--exclude-standard'))
const excluded = new Set([manifestRelative, ownershipRelative])
const candidates = [...new Set([...trackedDelta, ...untracked])]
  .filter((path) => !excluded.has(path))
  .filter((path) => !path.startsWith('supabase/.temp/'))
  .filter((path) => !path.startsWith('cp45-browser-proof/'))
  .filter((path) => existsSync(resolve(root, path)) && statSync(resolve(root, path)).isFile())
  .sort()

const previous = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, 'utf8')) : {}
const files = Object.fromEntries(candidates.map((path) => {
  const bytes = readFileSync(resolve(root, path))
  return [path, { bytes: bytes.length, sha256: sha256(bytes) }]
}))

const manifest = {
  format: 'CUTTING_BRIDGE_V2618_SOURCE_HASHES_V1',
  candidate_branch: 'pre-cp5/cutting-persistence-pickup-wip-r1-20260903',
  source_base_sha: 'd5c48ce5c8daa7e6da92dc9d690d9b36879e74c1',
  source_base_tree: sourceBaseTree,
  generation_parent_sha: generationParent,
  target_project_ref: 'siimvrusnzxexizpyoib',
  target_environment: 'ERP Enteng UAT',
  legacy_project_ref: 'vlxdhpkjeevubjxexnfo',
  migration_version: '20260903022604',
  migration_name: 'erp_v2_6_18_cutting_persistence_pickup_wip',
  application_version: 'v2.6.18',
  scope: 'PRE_CP5_CUTTING_PERSISTENCE_PICKUP_WIP_BRIDGE',
  cp5_scope: 'BS_RESOLUTION_NOT_STARTED',
  hosted_evidence_path: hostedEvidenceRelative,
  closure_status: previous.closure_status ?? 'NO_GO_PENDING_EXACT_HEAD_CI_UAT_AND_INDEPENDENT_AUDIT',
  source_only: previous.source_only ?? true,
  uat_applied: previous.uat_applied ?? false,
  uat_applied_at: previous.uat_applied_at ?? null,
  legacy_mutated: false,
  production_go: false,
  ci_runtime: previous.ci_runtime ?? { status: 'PENDING' },
  hosted_auth_permission_e2e: previous.hosted_auth_permission_e2e ?? {
    status: 'PENDING',
    mode: 'MANUAL_HOSTED_UAT_VERIFIED',
    classified_as_ci: false,
    github_service_role_secret_used: false,
  },
  truth_boundary: {
    cutting_final_save: 'UAT_RPC_CONNECTED',
    pickup_distribution: 'UAT_RPC_CONNECTED',
    wip_control: 'UAT_RPC_CONNECTED',
    pickup_pattern_filter: 'SERVER_SIDE_PATTERN_ID',
    wip_pattern_filter: 'SERVER_SIDE_PATTERN_ID',
    laundry_pattern_filter: 'SIMULATION_ONLY',
    qc_pattern_filter: 'SIMULATION_ONLY',
  },
  hygiene: {
    branch_protection_status_enforcement: false,
    severity: 'P3',
    cloudflare_dry_run_environment: 'uat-auth',
    production_deploy_authorized: false,
  },
  files,
}
writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`)

const manifestBytes = readFileSync(manifestPath)
const frozenOwnershipBytes = readFileSync(frozenOwnershipPath)
const ownership = {
  format: 'ERP_BACKEND_SOURCE_OWNERSHIP_V3',
  frozen_v2: {
    path: frozenOwnershipRelative,
    bytes: frozenOwnershipBytes.length,
    sha256: sha256(frozenOwnershipBytes),
  },
  candidate_cutting_bridge_manifest: {
    path: manifestRelative,
    bytes: manifestBytes.length,
    sha256: sha256(manifestBytes),
  },
  target_project_ref: manifest.target_project_ref,
  legacy_project_ref: manifest.legacy_project_ref,
  production_go: false,
}
writeFileSync(ownershipPath, `${JSON.stringify(ownership, null, 2)}\n`)

console.log(`Rendered pre-CP5 Cutting Bridge proof: ${candidates.length} byte-bound candidate files.`)
