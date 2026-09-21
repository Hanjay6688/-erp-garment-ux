import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

const root = process.cwd()
const baseSha = '6d4cda118f5d28d1f039cc0ecf318d0866f55c2c'
const baseTree = '6d90546ecd7e55e16a9e6062599ee09b2e9b505d'
const manifestRelative = 'docs/evidence/public_github_hardening_source_hashes.json'
const ownershipRelative = 'docs/evidence/backend_source_ownership_v4.json'
const frozenOwnershipRelative = 'docs/evidence/backend_source_ownership_v3.json'
const workflowPaths = [
  '.github/workflows/ci.yml',
  '.github/workflows/cp3-r4-full-schema-validation.yml',
  '.github/workflows/cp4-full-schema-validation.yml',
  '.github/workflows/cp45-full-schema-validation.yml',
  '.github/workflows/cp5-full-schema-validation.yml',
  '.github/workflows/cutting-bridge-full-schema-validation.yml',
]
const hardeningPaths = [
  '.github/SECURITY.md',
  ...workflowPaths,
  'package-lock.json',
  'package.json',
  'scripts/check-backend-ownership-v4.mjs',
  'scripts/render-public-github-hardening-source-hashes.mjs',
].sort()
const pinnedActions = [
  ['actions/checkout', 'v4', '11d5960a326750d5838078e36cf38b85af677262'],
  ['actions/download-artifact', 'v4', 'd3f86a106a0bac45b974a628896c90dbdf5c8093'],
  ['actions/setup-node', 'v4', '49933ea5288caeca8642d1e84afbd3f7d6820020'],
  ['actions/setup-python', 'v5', 'a26af69be951a213d495a4c3e4e4022e16d87065'],
  ['actions/upload-artifact', 'v4', 'ea165f8d65b6e75b540449e92b4886f43607fa02'],
  ['supabase/setup-cli', 'v1', 'ab058987d8d6c725971f6cf9d0b5c98467e30bd1'],
]

const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim()
const gitBytes = (...args) => execFileSync('git', args, { cwd: root })
const lines = (value) => value.split('\n').map((line) => line.trim()).filter(Boolean)
const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex')
const readJson = (path) => JSON.parse(readFileSync(resolve(root, path), 'utf8'))

assert.equal(git('rev-parse', `${baseSha}^{tree}`), baseTree, 'Public-hardening base tree drift')
const frozenBytes = readFileSync(resolve(root, frozenOwnershipRelative))
assert.equal(frozenBytes.length, 896, 'Frozen ownership V3 byte length drift')
assert.equal(
  sha256(frozenBytes),
  'b858502ad4ee46f9804b43357a9f94cddd78ed661a264984d3c32a5493c6ae8d',
  'Frozen ownership V3 SHA-256 drift',
)

const ownership = readJson(ownershipRelative)
const manifestBytes = readFileSync(resolve(root, manifestRelative))
const manifest = JSON.parse(manifestBytes)
assert.deepEqual(ownership, {
  format: 'ERP_BACKEND_SOURCE_OWNERSHIP_V4',
  frozen_v3: {
    path: frozenOwnershipRelative,
    bytes: frozenBytes.length,
    sha256: sha256(frozenBytes),
  },
  public_hardening_manifest: {
    path: manifestRelative,
    bytes: manifestBytes.length,
    sha256: sha256(manifestBytes),
  },
  target_project_ref: 'siimvrusnzxexizpyoib',
  legacy_project_ref: 'vlxdhpkjeevubjxexnfo',
  hosted_database_mutated: false,
  legacy_mutated: false,
  production_go: false,
})
assert.equal(manifest.format, 'PUBLIC_GITHUB_HARDENING_SOURCE_HASHES_V1')
assert.equal(manifest.candidate_branch, 'security/public-github-hardening-20260909')
assert.equal(manifest.source_base_sha, baseSha)
assert.equal(manifest.source_base_tree, baseTree)
assert.equal(manifest.scope, 'PUBLIC_GITHUB_SECURITY_HARDENING')
assert.equal(manifest.hosted_database_mutated, false)
assert.equal(manifest.legacy_mutated, false)
assert.equal(manifest.production_go, false)
assert.deepEqual(Object.keys(manifest.files).sort(), hardeningPaths)
for (const [path, expected] of Object.entries(manifest.files)) {
  const bytes = readFileSync(resolve(root, path))
  assert.equal(bytes.length, expected.bytes, `Public-hardening byte length drift: ${path}`)
  assert.equal(sha256(bytes), expected.sha256, `Public-hardening SHA-256 drift: ${path}`)
}

const changed = [...new Set([
  ...lines(git('diff', '--name-only', '--diff-filter=ACMRTUXB', baseSha, '--')),
  ...lines(git('ls-files', '--others', '--exclude-standard')),
])]
  .filter((path) => existsSync(resolve(root, path)) && statSync(resolve(root, path)).isFile())
  .sort()
assert.deepEqual(changed, [...hardeningPaths, manifestRelative, ownershipRelative].sort(), 'Public-hardening source delta drift')
assert.deepEqual(lines(git('diff', '--name-only', '--diff-filter=D', baseSha, '--')), [], 'Public-hardening contains a deletion')

for (const path of workflowPaths) {
  const current = readFileSync(resolve(root, path), 'utf8')
  const uses = [...current.matchAll(/\buses:\s*([^\s#]+)/g)].map((match) => match[1])
  assert.ok(uses.length > 0, `Workflow has no action references: ${path}`)
  assert.ok(uses.every((value) => /^[^@\s]+@[0-9a-f]{40}$/.test(value)), `Workflow action is not pinned to a full SHA: ${path}`)

  let normalized = current
  for (const [action, tag, sha] of pinnedActions) {
    normalized = normalized.replaceAll(`${action}@${sha} # ${tag}`, `${action}@${tag}`)
  }
  if (path === '.github/workflows/ci.yml') {
    const permissionBlock = '\npermissions:\n  contents: read\n\njobs:\n'
    assert.equal(current.split(permissionBlock).length - 1, 1, 'Build workflow must declare one top-level read-only permission block')
    normalized = normalized.replace(permissionBlock, '\njobs:\n')
  }
  if (path === '.github/workflows/cutting-bridge-full-schema-validation.yml') {
    const branchGuard = "    if: github.event_name == 'workflow_dispatch' || github.head_ref == 'pre-cp5/cutting-persistence-pickup-wip-r1-20260903'\n"
    assert.equal(current.split(branchGuard).length - 1, 1, 'Cutting Bridge workflow must skip unrelated pull requests')
    normalized = normalized.replace(branchGuard, '')
  }
  const baseline = gitBytes('show', `${baseSha}:${path}`).toString('utf8')
  assert.equal(normalized, baseline, `Workflow changed beyond approved SHA pins/permissions: ${path}`)
}

const basePackage = JSON.parse(gitBytes('show', `${baseSha}:package.json`).toString('utf8'))
const currentPackage = readJson('package.json')
assert.deepEqual(currentPackage.overrides, { sharp: '0.35.4' })
const normalizedPackage = structuredClone(currentPackage)
delete normalizedPackage.overrides
normalizedPackage.scripts['check:backend'] = 'node scripts/check-backend-ownership-v3.mjs'
assert.deepEqual(normalizedPackage, basePackage, 'package.json changed beyond the audited hardening scope')

const packageLock = readJson('package-lock.json')
assert.equal(packageLock.lockfileVersion, 3)
assert.equal(packageLock.packages['node_modules/miniflare'].dependencies.sharp, '0.35.2')
assert.equal(packageLock.packages['node_modules/sharp'].version, '0.35.4')
for (const [path, metadata] of Object.entries(packageLock.packages)) {
  if (/^node_modules\/@img\/sharp-(?!libvips)/.test(path)) assert.equal(metadata.version, '0.35.4', `Stale sharp binary package: ${path}`)
  if (/^node_modules\/@img\/sharp-libvips-/.test(path)) assert.equal(metadata.version, '1.3.3', `Stale libvips package: ${path}`)
}

const baselineRoot = mkdtempSync(join(tmpdir(), 'erp-backend-v3-'))
try {
  execFileSync('git', ['worktree', 'add', '--detach', baselineRoot, baseSha], { cwd: root, stdio: 'pipe' })
  const output = execFileSync(process.execPath, ['scripts/check-backend-ownership-v3.mjs'], {
    cwd: baselineRoot,
    encoding: 'utf8',
  })
  assert.match(output, /Backend ownership v3 passed:/, 'Immutable ownership V3 baseline no longer validates')
} finally {
  try {
    execFileSync('git', ['worktree', 'remove', '--force', baselineRoot], { cwd: root, stdio: 'pipe' })
  } finally {
    rmSync(baselineRoot, { recursive: true, force: true })
  }
}

console.log(`Backend ownership V4 passed: immutable V3 revalidated; ${hardeningPaths.length} public-hardening files byte-bound; all workflow actions commit-pinned; production_go:false.`)
