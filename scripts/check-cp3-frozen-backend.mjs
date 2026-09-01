import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'

const manifestPath = resolve('docs/evidence/cp3_r4_source_hashes.json')
const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))

assert.equal(manifest.format, 'CP3_R5_CURRENT_MAIN_FIXED_SOURCE_HASHES_V1')
assert.equal(manifest.source_only, true)
assert.equal(manifest.uat_applied, false)
assert.equal(manifest.legacy_mutated, false)

for (const [relativePath, expected] of Object.entries(manifest.files)) {
  const bytes = readFileSync(resolve(relativePath))
  const actualHash = createHash('sha256').update(bytes).digest('hex')
  assert.equal(bytes.length, expected.bytes, `Byte length drift: ${relativePath}`)
  assert.equal(actualHash, expected.sha256, `SHA-256 drift: ${relativePath}`)
}

const cp3MigrationNames = readdirSync(resolve('supabase/migrations'))
  .filter((name) => /^20260901023(?:000|100|200|400)_/.test(name))
  .sort()

assert.deepEqual(cp3MigrationNames, [
  '20260901023000_erp_v2_6_14_attendance_hpp_sewing_terminal_foundation.sql',
  '20260901023100_erp_v2_6_14b_attendance_hpp_candidate_hardening.sql',
  '20260901023200_erp_v2_6_14c_attendance_hpp_uat_alignment.sql',
  '20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql',
])

console.log(`Frozen CP3 backend passed: ${Object.keys(manifest.files).length} byte-bound files; ${cp3MigrationNames.length} exact migrations.`)
