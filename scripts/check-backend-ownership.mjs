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

const hash = (algorithm, bytes) => createHash(algorithm).update(bytes).digest('hex')
const posix = (path) => path.split('\\').join('/')

assert.equal(ownership.format, 'ERP_BACKEND_SOURCE_OWNERSHIP_V1')
assert.equal(ownership.uat_mutated, false)
assert.equal(ownership.legacy_mutated, false)
assert.equal(hash('sha256', cp3ManifestBytes), ownership.reviewed_cp3_manifest.sha256)
assert.equal(cp3Manifest.format, 'CP3_R5_CURRENT_MAIN_FIXED_SOURCE_HASHES_V1')
assert.equal(cp3Manifest.source_only, true)
assert.equal(cp3Manifest.uat_applied, false)

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
  '.github/workflows/cp3-r4-full-schema-validation.yml',
].sort()

const fixedEntries = [
  ...ownership.uat_recorded_sources,
  ...ownership.recorded_migration_regressions,
  ...ownership.uat_provenance,
]
const expected = [
  ...Object.keys(cp3Manifest.files),
  ...fixedEntries.map((entry) => entry.path),
].sort()

assert.equal(new Set(expected).size, expected.length, 'Backend ownership contains duplicate paths')
assert.deepEqual(discovered, expected, 'Backend source/proof file is missing ownership or a stale path remains')

for (const [path, expectedFile] of Object.entries(cp3Manifest.files)) {
  const bytes = readFileSync(resolve(root, path))
  assert.equal(bytes.length, expectedFile.bytes, `Byte length drift: ${path}`)
  assert.equal(hash('sha256', bytes), expectedFile.sha256, `SHA-256 drift: ${path}`)
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
  console.log(`Backend ownership passed: ${expected.length} files; 4 ledger-aligned UAT sources; ${cp3Migrations.length} exact CP3 migrations; zero unowned backend artifacts.`)
}
