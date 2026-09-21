import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
const baseSha = '6d4cda118f5d28d1f039cc0ecf318d0866f55c2c'
const baseTree = '6d90546ecd7e55e16a9e6062599ee09b2e9b505d'
const manifestRelative = 'docs/evidence/public_github_hardening_source_hashes.json'
const ownershipRelative = 'docs/evidence/backend_source_ownership_v4.json'
const frozenOwnershipRelative = 'docs/evidence/backend_source_ownership_v3.json'
const hardeningPaths = [
  '.github/SECURITY.md',
  '.github/workflows/ci.yml',
  '.github/workflows/cp3-r4-full-schema-validation.yml',
  '.github/workflows/cp4-full-schema-validation.yml',
  '.github/workflows/cp45-full-schema-validation.yml',
  '.github/workflows/cp5-full-schema-validation.yml',
  '.github/workflows/cutting-bridge-full-schema-validation.yml',
  'package-lock.json',
  'package.json',
  'scripts/check-backend-ownership-v4.mjs',
  'scripts/render-public-github-hardening-source-hashes.mjs',
].sort()

const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim()
const lines = (value) => value.split('\n').map((line) => line.trim()).filter(Boolean)
const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex')
const excluded = new Set([manifestRelative, ownershipRelative])

assert.equal(git('rev-parse', `${baseSha}^{tree}`), baseTree, 'Public-hardening base tree drift')
const changed = [...new Set([
  ...lines(git('diff', '--name-only', '--diff-filter=ACMRTUXB', baseSha, '--')),
  ...lines(git('ls-files', '--others', '--exclude-standard')),
])]
  .filter((path) => !excluded.has(path))
  .filter((path) => existsSync(resolve(root, path)) && statSync(resolve(root, path)).isFile())
  .sort()
assert.deepEqual(changed, hardeningPaths, 'Public-hardening delta contains an unexpected or missing file')

const files = Object.fromEntries(hardeningPaths.map((path) => {
  const bytes = readFileSync(resolve(root, path))
  return [path, { bytes: bytes.length, sha256: sha256(bytes) }]
}))
const manifest = {
  format: 'PUBLIC_GITHUB_HARDENING_SOURCE_HASHES_V1',
  candidate_branch: 'security/public-github-hardening-20260909',
  source_base_sha: baseSha,
  source_base_tree: baseTree,
  scope: 'PUBLIC_GITHUB_SECURITY_HARDENING',
  hosted_database_mutated: false,
  legacy_mutated: false,
  production_go: false,
  files,
}
writeFileSync(resolve(root, manifestRelative), `${JSON.stringify(manifest, null, 2)}\n`)

const manifestBytes = readFileSync(resolve(root, manifestRelative))
const frozenBytes = readFileSync(resolve(root, frozenOwnershipRelative))
assert.equal(frozenBytes.length, 896, 'Frozen ownership V3 byte length drift')
assert.equal(
  sha256(frozenBytes),
  'b858502ad4ee46f9804b43357a9f94cddd78ed661a264984d3c32a5493c6ae8d',
  'Frozen ownership V3 SHA-256 drift',
)
const ownership = {
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
}
writeFileSync(resolve(root, ownershipRelative), `${JSON.stringify(ownership, null, 2)}\n`)

console.log(`Rendered public GitHub hardening proof: ${hardeningPaths.length} byte-bound files over immutable ownership V3.`)
