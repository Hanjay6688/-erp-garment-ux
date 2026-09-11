import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
const manifestPath = resolve(root, 'docs/evidence/cp45_r1_source_hashes.json')
const ownershipPath = resolve(root, 'docs/evidence/backend_source_ownership_v2.json')
const frozenOwnershipPath = resolve(root, 'docs/evidence/backend_source_ownership.json')
const manifestRelative = 'docs/evidence/cp45_r1_source_hashes.json'
const ownershipRelative = 'docs/evidence/backend_source_ownership_v2.json'
const frozenOwnershipRelative = 'docs/evidence/backend_source_ownership.json'

const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex')
const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim()
const lines = (value) => value.split('\n').map((line) => line.trim()).filter(Boolean)
const baseline = git('rev-list', '--max-parents=0', 'HEAD').split('\n').at(-1)
const generationParent = process.env.CP45_GENERATION_PARENT_SHA || git('rev-parse', 'HEAD')
if (!/^[0-9a-f]{40}$/.test(generationParent)) throw new Error('CP45_GENERATION_PARENT_SHA must be an exact commit SHA')
const trackedDelta = lines(git('diff', '--name-only', '--diff-filter=ACMRTUXB', baseline, '--'))
const untracked = lines(git('ls-files', '--others', '--exclude-standard'))
const excluded = new Set([manifestRelative, ownershipRelative])
const candidates = [...new Set([...trackedDelta, ...untracked])]
  .filter((path) => !excluded.has(path))
  .filter((path) => !path.startsWith('supabase/.temp/'))
  .filter((path) => existsSync(resolve(root, path)) && statSync(resolve(root, path)).isFile())
  .sort()

let previous = {}
try {
  previous = JSON.parse(readFileSync(manifestPath, 'utf8'))
} catch (error) {
  if (error.code !== 'ENOENT') throw error
}
const files = Object.fromEntries(candidates.map((path) => {
  const bytes = readFileSync(resolve(root, path))
  return [path, { bytes: bytes.length, sha256: sha256(bytes) }]
}))

const manifest = {
  format: 'CP45_R1_SOURCE_HASHES_V1',
  candidate_branch: 'cp4.5/rbac-production-identity-wip-r1-20260902',
  source_base_sha: '57d8346a7cdf4ee86519f2dd2a1b54d39ebbb6cc',
  source_base_tree: '48fc87507dc8a18d5829d518e53f298ad0c7e01a',
  generation_parent_sha: generationParent,
  target_project_ref: 'siimvrusnzxexizpyoib',
  target_environment: 'ERP Enteng UAT',
  legacy_project_ref: 'vlxdhpkjeevubjxexnfo',
  migration_version: '20260902104937',
  application_version: 'v2.6.17',
  integrity_correction: previous.integrity_correction ?? {
    defect_id: 'P2-CP45-001',
    status: 'SOURCE_CANDIDATE_PENDING_EXACT_HEAD_CI_AND_UAT',
    migration_version: '20260902180726',
    application_version: 'v2.6.17a',
    source_only: true,
    uat_applied: false,
    uat_applied_at: null,
    exact_head_ci: { status: 'PENDING' },
    hosted_auth_permission_e2e: {
      status: 'PENDING',
      mode: 'MANUAL_HOSTED_UAT_VERIFIED',
      classified_as_ci: false,
      github_service_role_secret_used: false,
    },
  },
  closure_status: previous.closure_status ?? 'NO_GO_PENDING_CP45A_CORRECTION_PROOF',
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
  format: 'ERP_BACKEND_SOURCE_OWNERSHIP_V2',
  frozen_v1: {
    path: frozenOwnershipRelative,
    bytes: frozenOwnershipBytes.length,
    sha256: sha256(frozenOwnershipBytes),
  },
  candidate_cp45_manifest: {
    path: manifestRelative,
    bytes: manifestBytes.length,
    sha256: sha256(manifestBytes),
  },
  target_project_ref: 'siimvrusnzxexizpyoib',
  legacy_project_ref: 'vlxdhpkjeevubjxexnfo',
  production_go: false,
}
writeFileSync(ownershipPath, `${JSON.stringify(ownership, null, 2)}\n`)

console.log(`Rendered CP4.5 proof ownership: ${candidates.length} byte-bound candidate files.`)
