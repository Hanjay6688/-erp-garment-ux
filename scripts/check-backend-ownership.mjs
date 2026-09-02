import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'
import { extname, join, relative, resolve } from 'node:path'

const root = process.cwd()
const ownershipPath = resolve(root, 'docs/evidence/backend_source_ownership.json')
const ownership = JSON.parse(readFileSync(ownershipPath, 'utf8'))
const cp3ManifestPath = resolve(root, ownership.reviewed_cp3_manifest.path)
const cp3ManifestBytes = readFileSync(cp3ManifestPath)
const cp3Manifest = JSON.parse(cp3ManifestBytes)
const cp4ManifestPath = resolve(root, ownership.candidate_cp4_manifest.path)
const cp4ManifestBytes = readFileSync(cp4ManifestPath)
const cp4Manifest = JSON.parse(cp4ManifestBytes)

const hash = (algorithm, bytes) => createHash(algorithm).update(bytes).digest('hex')
const posix = (path) => path.split('\\').join('/')

assert.equal(ownership.format, 'ERP_BACKEND_SOURCE_OWNERSHIP_V1')
assert.equal(ownership.uat_mutated, false)
assert.equal(ownership.legacy_mutated, false)
assert.equal(hash('sha256', cp3ManifestBytes), ownership.reviewed_cp3_manifest.sha256)
assert.equal(cp3Manifest.format, 'CP3_R5_CURRENT_MAIN_FIXED_SOURCE_HASHES_V1')
assert.equal(cp3Manifest.source_only, true)
assert.equal(cp3Manifest.uat_applied, false)
assert.equal(cp4ManifestBytes.length, ownership.candidate_cp4_manifest.bytes)
assert.equal(hash('sha256', cp4ManifestBytes), ownership.candidate_cp4_manifest.sha256)
assert.equal(cp4Manifest.format, 'CP4_R1_SOURCE_HASHES_V1')
assert.equal(cp4Manifest.parent_sha, '92e49047941c09f18a306a9b2998f101c62e6ffe')
assert.equal(cp4Manifest.parent_tree, '8625bd6053c256456f67185d60e0bb95f9bc574e')
assert.equal(cp4Manifest.candidate_first_sha, 'da8ed9055738c26ce882ad8b1adda047fe000c72')
assert.equal(cp4Manifest.candidate_generation_parent_sha, 'c2eea97f79d4c54dd8cda003c0a5b3030206134b')
assert.deepEqual(cp4Manifest.hosted_uat_require_owner_admin, {
  definition_md5: '8c22fb34fb8adf2085ca5703e32d38a5',
  acl: '{postgres=X/postgres,service_role=X/postgres}',
  owner: 'postgres',
})
assert.equal(cp4Manifest.target_project_ref, 'siimvrusnzxexizpyoib')
assert.equal(cp4Manifest.legacy_project_ref, 'vlxdhpkjeevubjxexnfo')
assert.equal(cp4Manifest.source_only, true)
assert.equal(cp4Manifest.uat_applied, false)
assert.equal(cp4Manifest.legacy_mutated, false)
assert.equal(cp4Manifest.production_go, false)

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
  ...walk(resolve(root, 'scripts'), (path) => /^(?:cp3_|test_cp3_).*\.py$/.test(path.split('/').at(-1))),
  ...walk(resolve(root, 'scripts'), (path) => /^cp4_.*\.mjs$/.test(path.split('/').at(-1))),
  'scripts/check-backend-ownership.mjs',
  '.github/workflows/cp3-r4-full-schema-validation.yml',
  '.github/workflows/cp4-full-schema-validation.yml',
].sort()

const fixedEntries = [
  ...ownership.uat_recorded_sources,
  ...ownership.recorded_migration_regressions,
  ...ownership.uat_provenance,
]
const expected = [
  ...Object.keys(cp3Manifest.files),
  ...Object.keys(cp4Manifest.files),
  ...fixedEntries.map((entry) => entry.path),
].sort()

assert.equal(new Set(expected).size, expected.length, 'Backend ownership contains duplicate paths')
assert.deepEqual(discovered, expected, 'Backend source/proof file is missing ownership or a stale path remains')

for (const [path, expectedFile] of Object.entries(cp3Manifest.files)) {
  const bytes = readFileSync(resolve(root, path))
  assert.equal(bytes.length, expectedFile.bytes, `Byte length drift: ${path}`)
  assert.equal(hash('sha256', bytes), expectedFile.sha256, `SHA-256 drift: ${path}`)
}

for (const [path, expectedFile] of Object.entries(cp4Manifest.files)) {
  const bytes = readFileSync(resolve(root, path))
  assert.equal(bytes.length, expectedFile.bytes, `CP4 byte length drift: ${path}`)
  assert.equal(hash('sha256', bytes), expectedFile.sha256, `CP4 SHA-256 drift: ${path}`)
}

for (const entry of fixedEntries) {
  const bytes = readFileSync(resolve(root, entry.path))
  assert.equal(bytes.length, entry.bytes, `Byte length drift: ${entry.path}`)
  assert.equal(hash('sha256', bytes), entry.sha256, `SHA-256 drift: ${entry.path}`)
  if (entry.ledger_version) {
    assert.ok(entry.path.split('/').at(-1).startsWith(`${entry.ledger_version}_`), `Ledger filename mismatch: ${entry.path}`)
    assert.equal(hash('md5', bytes), entry.md5, `UAT ledger byte mismatch: ${entry.path}`)
  }
}

const cp3Migrations = Object.keys(cp3Manifest.files)
  .filter((path) => path.startsWith('supabase/migrations/20260901023'))
  .sort()

assert.deepEqual(cp3Migrations, [
  'supabase/migrations/20260901023000_erp_v2_6_14_attendance_hpp_sewing_terminal_foundation.sql',
  'supabase/migrations/20260901023100_erp_v2_6_14b_attendance_hpp_candidate_hardening.sql',
  'supabase/migrations/20260901023200_erp_v2_6_14c_attendance_hpp_uat_alignment.sql',
  'supabase/migrations/20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql',
])

const onlyCp3 = process.argv.includes('--cp3-only')
if (onlyCp3) {
  console.log(`Frozen CP3 backend passed: ${Object.keys(cp3Manifest.files).length} byte-bound files; ${cp3Migrations.length} exact migrations.`)
} else {
  console.log(`Backend ownership passed: ${expected.length} files; ${cp3Migrations.length} frozen CP3 migrations; ${Object.keys(cp4Manifest.files).length} byte-bound CP4 files; zero unowned backend artifacts.`)
}
