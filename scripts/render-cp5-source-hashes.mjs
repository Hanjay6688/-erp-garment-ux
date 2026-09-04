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
const hostedEvidenceRelative = 'docs/evidence/cp5_hosted_uat_auth_e2e.json'
const lineageMigrationRelative = 'supabase/migrations/20260903151034_erp_v2_6_19a_cp5_rework_accessory_lineage.sql'
const lineageRollbackRelative = 'supabase/rollbacks/20260903151034_erp_v2_6_19a_cp5_rework_accessory_lineage.rollback.sql'
const lineageEvidenceRelative = 'docs/evidence/cp5_v2619a_uat_acceptance.json'
const reliabilityMigrationRelative = 'supabase/migrations/20260904012525_erp_v2_6_19b_cp5_reliability_closure.sql'
const reliabilityRollbackRelative = 'supabase/rollbacks/20260904012525_erp_v2_6_19b_cp5_reliability_closure.rollback.sql'
const reliabilityEvidenceRelative = 'docs/evidence/cp5_v2619b_uat_acceptance.json'
const atomicMigrationRelative = 'supabase/migrations/20260904061346_erp_v2_6_19c_cp5_atomic_reversal_reconciliation.sql'
const atomicRollbackRelative = 'supabase/rollbacks/20260904061346_erp_v2_6_19c_cp5_atomic_reversal_reconciliation.rollback.sql'
const atomicEvidenceRelative = 'docs/evidence/cp5_v2619c_uat_acceptance.json'
const v2619aCodeHeadSha = '2175bd8f199f6a5d860e7f517042e2efe35916e7'
const v2619aCodeHeadTree = 'd845b1ff613774a150b999dbfa2b41b772e416e9'

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
const hostedEvidence = JSON.parse(readFileSync(resolve(root, hostedEvidenceRelative), 'utf8'))
const lineageEvidence = JSON.parse(readFileSync(resolve(root, lineageEvidenceRelative), 'utf8'))
const reliabilityEvidence = existsSync(resolve(root, reliabilityEvidenceRelative))
  ? JSON.parse(readFileSync(resolve(root, reliabilityEvidenceRelative), 'utf8'))
  : null
const reliabilityRecorded = reliabilityEvidence !== null
const atomicEvidence = existsSync(resolve(root, atomicEvidenceRelative))
  ? JSON.parse(readFileSync(resolve(root, atomicEvidenceRelative), 'utf8'))
  : null
const atomicRecorded = atomicEvidence !== null
assert.equal(hostedEvidence.format, 'CP5_HOSTED_UAT_AUTH_E2E_V1')
assert.equal(hostedEvidence.status, 'PASS')
assert.equal(hostedEvidence.mode, 'MANUAL_HOSTED_UAT_VERIFIED')
assert.equal(hostedEvidence.classified_as_ci, false)
assert.equal(hostedEvidence.target_project_ref, 'siimvrusnzxexizpyoib')
assert.equal(hostedEvidence.case_count, 31)
assert.equal(hostedEvidence.case_passed, 31)
for (const field of [
  'auth_users', 'auth_identities', 'auth_sessions', 'auth_refresh_tokens',
  'app_users', 'custom_roles', 'bs_cases', 'bs_resolutions', 'bs_components',
  'rework_orders', 'rework_components', 'hold_events', 'idempotency',
  'execution_context', 'synthetic_access_audit', 'synthetic_audit_logs',
  'temporary_http_extensions', 'new_audit_rows_after_cleanup', 'waiting_locks',
  'transactions_over_5m',
]) assert.equal(hostedEvidence.cleanup[field], 0, `CP5 hosted proof contains residue: ${field}`)
assert.equal(hostedEvidence.cleanup.preexisting_audit_rows_preserved, 36)
assert.equal(lineageEvidence.format, 'CP5_V2619A_UAT_ACCEPTANCE_V1')
assert.equal(lineageEvidence.status, 'PASS')
assert.equal(lineageEvidence.mode, 'HOSTED_UAT_RECORDED_MIGRATION_AND_TRANSACTIONAL_SQL')
assert.equal(lineageEvidence.target_project_ref, 'siimvrusnzxexizpyoib')
assert.equal(lineageEvidence.correction.application_version, 'v2.6.19a')
assert.equal(lineageEvidence.correction.platform_ledger_version, '20260903151034')
assert.equal(lineageEvidence.hosted_http_auth_retest, false)
assert.ok(Object.values(lineageEvidence.post_proof_residue).every((value) => value === 0))
assert.equal(lineageEvidence.legacy_mutated, false)
assert.equal(lineageEvidence.production_go, false)
if (reliabilityRecorded) {
  assert.equal(reliabilityEvidence.format, 'CP5_V2619B_UAT_ACCEPTANCE_V1')
  assert.equal(reliabilityEvidence.status, 'PASS')
  assert.equal(reliabilityEvidence.mode, 'EXACT_CODE_HEAD_CI_AND_HOSTED_UAT_RECORDED_MIGRATION')
  assert.equal(reliabilityEvidence.target_project_ref, 'siimvrusnzxexizpyoib')
  assert.equal(reliabilityEvidence.correction.application_version, 'v2.6.19b')
  assert.equal(reliabilityEvidence.correction.source_ledger_version, '20260904012525')
  assert.equal(reliabilityEvidence.correction.source_path, reliabilityMigrationRelative)
  assert.equal(reliabilityEvidence.correction.source_bytes, 42021)
  assert.equal(reliabilityEvidence.correction.source_sha256, 'b1bde1a6ccd1f60dd001d99b72d479ffa0a18a6ea46bf93cd80e406e2ef0ce1d')
  assert.equal(reliabilityEvidence.correction.connector_ledger_sha256, '89ed4535720e12722bc1cbedd1bbcb5b7920f9ee4b6b19754214d05ac82b0e8d')
  assert.equal(reliabilityEvidence.code_ci.status, 'PASS')
  assert.match(reliabilityEvidence.code_ci.runtime_head_sha, /^[0-9a-f]{40}$/)
  assert.match(reliabilityEvidence.code_ci.runtime_head_tree, /^[0-9a-f]{40}$/)
  assert.equal(reliabilityEvidence.code_ci.unit_tests.files, 25)
  assert.equal(reliabilityEvidence.code_ci.unit_tests.passed, 172)
  assert.deepEqual(reliabilityEvidence.code_ci.browser_tests, { cp45: 2, pre_cp5: 2, cp5: 6, total: 10 })
  assert.ok(Object.values(reliabilityEvidence.post_proof_residue).every((value) => value === 0))
  assert.equal(reliabilityEvidence.legacy_read_only.legacy_mutated, false)
  assert.equal(reliabilityEvidence.production_go, false)
}
if (atomicRecorded) {
  assert.equal(atomicEvidence.format, 'CP5_V2619C_UAT_ACCEPTANCE_V1')
  assert.equal(atomicEvidence.status, 'PASS')
  assert.equal(atomicEvidence.mode, 'EXACT_CODE_HEAD_CI_AND_HOSTED_UAT_RECORDED_MIGRATION')
  assert.equal(atomicEvidence.target_project_ref, 'siimvrusnzxexizpyoib')
  assert.equal(atomicEvidence.correction.application_version, 'v2.6.19c')
  assert.equal(atomicEvidence.correction.source_ledger_version, '20260904061346')
  assert.equal(atomicEvidence.correction.source_path, atomicMigrationRelative)
  assert.equal(atomicEvidence.correction.source_bytes, 13864)
  assert.equal(atomicEvidence.correction.source_sha256, '1b66c8bd8c12c2acef47e97e7e0ff15e82e5ef12618d11fea288750b862732e7')
  assert.equal(atomicEvidence.correction.connector_ledger_sha256, 'ee26bce863a95d5994b61f2794de3fa42811cd08fc127f4148897ba4becc5fb6')
  assert.equal(atomicEvidence.code_ci.status, 'PASS')
  assert.match(atomicEvidence.code_ci.runtime_head_sha, /^[0-9a-f]{40}$/)
  assert.match(atomicEvidence.code_ci.runtime_head_tree, /^[0-9a-f]{40}$/)
  assert.deepEqual(atomicEvidence.code_ci.unit_tests, { files: 25, passed: 172 })
  assert.deepEqual(atomicEvidence.code_ci.browser_tests, { cp45: 2, pre_cp5: 2, cp5: 8, total: 12 })
  assert.ok(Object.values(atomicEvidence.post_proof_residue).every((value) => value === 0))
  assert.equal(atomicEvidence.legacy_read_only.legacy_mutated, false)
  assert.equal(atomicEvidence.production_go, false)
}

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
const lineageMigrationBytes = readFileSync(resolve(root, lineageMigrationRelative))
const reliabilityMigrationBytes = readFileSync(resolve(root, reliabilityMigrationRelative))
const atomicMigrationBytes = readFileSync(resolve(root, atomicMigrationRelative))
const cuttingMigrationHash = sha256(cuttingMigrationBytes)
const correctionMigrationHash = sha256(correctionMigrationBytes)
const cp5MigrationHash = sha256(cp5MigrationBytes)
const lineageMigrationHash = sha256(lineageMigrationBytes)
const reliabilityMigrationHash = sha256(reliabilityMigrationBytes)
const atomicMigrationHash = sha256(atomicMigrationBytes)
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
bindRollback(
  lineageRollbackRelative, '__REWORK_ACCESSORY_LINEAGE_MIGRATION_SHA256__',
  previous?.migrations?.rework_accessory_lineage?.source_sha256, lineageMigrationHash,
)
bindRollback(
  reliabilityRollbackRelative, '__CP5_RELIABILITY_CLOSURE_MIGRATION_SHA256__',
  previous?.migrations?.reliability_closure?.connector_ledger_sha256, '89ed4535720e12722bc1cbedd1bbcb5b7920f9ee4b6b19754214d05ac82b0e8d',
)
bindRollback(
  atomicRollbackRelative, '__CP5_ATOMIC_REVERSAL_MIGRATION_SHA256__',
  previous?.migrations?.atomic_reversal?.connector_ledger_sha256, 'ee26bce863a95d5994b61f2794de3fa42811cd08fc127f4148897ba4becc5fb6',
)
assert.equal(lineageMigrationBytes.length, 55354, 'Recorded UAT v2.6.19a source byte length drift')
assert.equal(lineageMigrationHash, '204b9246f3c8c6464476da1a7f1574f5e0ae4c46f024c082704795b3eef5210f', 'Recorded UAT v2.6.19a source SHA-256 drift')
assert.equal(reliabilityMigrationBytes.length, 42021, 'v2.6.19b source byte length drift')
assert.equal(reliabilityMigrationHash, 'b1bde1a6ccd1f60dd001d99b72d479ffa0a18a6ea46bf93cd80e406e2ef0ce1d', 'v2.6.19b source SHA-256 drift')
assert.equal(atomicMigrationBytes.length, 13864, 'v2.6.19c source byte length drift')
assert.equal(atomicMigrationHash, '1b66c8bd8c12c2acef47e97e7e0ff15e82e5ef12618d11fea288750b862732e7', 'v2.6.19c source SHA-256 drift')

const materializedPaths = lines(process.env.CP5_MATERIALIZED_CHANGED_PATHS ?? '')
const materializedMode = !existsSync(resolve(root, '.git'))
if (materializedMode) {
  assert.ok(previous, 'Materialized rendering requires the preceding manifest')
  assert.ok(materializedPaths.length > 0, 'Materialized rendering requires CP5_MATERIALIZED_CHANGED_PATHS')
  assert.ok(process.env.CP5_GENERATION_PARENT_SHA, 'Materialized rendering requires CP5_GENERATION_PARENT_SHA')
}
const sourceBaseSha = previous?.source_base_sha ?? git('rev-parse', 'HEAD')
const sourceBaseTree = previous?.source_base_tree ?? git('rev-parse', `${sourceBaseSha}^{tree}`)
const generationParentSha = process.env.CP5_GENERATION_PARENT_SHA || git('rev-parse', 'HEAD')
assert.match(sourceBaseSha, /^[0-9a-f]{40}$/)
assert.match(sourceBaseTree, /^[0-9a-f]{40}$/)
assert.match(generationParentSha, /^[0-9a-f]{40}$/)

const deleted = materializedMode ? [] : lines(git('diff', '--name-only', '--diff-filter=D', sourceBaseSha, '--'))
assert.deepEqual(deleted, [], 'CP5 manifest does not conceal deletions; record or restore deleted files first')
const trackedDelta = materializedMode
  ? [...Object.keys(previous.files), ...materializedPaths]
  : lines(git('diff', '--name-only', '--diff-filter=ACMRTUXB', sourceBaseSha, '--'))
const untracked = materializedMode ? [] : lines(git('ls-files', '--others', '--exclude-standard'))
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
      uat_applied: true,
      uat_platform_ledger_version: '20260903105741',
      uat_platform_statement_count: 1,
      uat_business_facts_observed: 0,
    },
    bs_resolution: {
      version: '20260903070932', application_version: 'v2.6.19',
      name: 'erp_v2_6_19_cp5_bs_resolution_recovery',
      source_path: cp5MigrationRelative,
      source_bytes: cp5MigrationBytes.length,
      source_sha256: cp5MigrationHash,
      rollback_path: cp5RollbackRelative,
      acceptance_path: 'supabase/tests/cp5_bs_resolution_recovery_rollback.sql',
      uat_applied: true,
      uat_platform_ledger_version: '20260903105814',
      uat_platform_statement_count: 1,
      uat_business_facts_observed: 0,
    },
    rework_accessory_lineage: {
      version: '20260903151034', application_version: 'v2.6.19a',
      name: 'erp_v2_6_19a_cp5_rework_accessory_lineage',
      source_path: lineageMigrationRelative,
      source_bytes: lineageMigrationBytes.length,
      source_sha256: lineageMigrationHash,
      rollback_path: lineageRollbackRelative,
      acceptance_path: 'supabase/tests/cp5_rework_accessory_lineage_rollback.sql',
      uat_applied: true,
      uat_platform_ledger_version: '20260903151034',
      uat_platform_statement_count: 1,
      uat_business_facts_observed: 0,
    },
    reliability_closure: {
      version: '20260904012525', application_version: 'v2.6.19b',
      name: 'erp_v2_6_19b_cp5_reliability_closure',
      source_path: reliabilityMigrationRelative,
      source_bytes: reliabilityMigrationBytes.length,
      source_sha256: reliabilityMigrationHash,
      connector_ledger_sha256: '89ed4535720e12722bc1cbedd1bbcb5b7920f9ee4b6b19754214d05ac82b0e8d',
      rollback_path: reliabilityRollbackRelative,
      acceptance_paths: [
        'supabase/tests/cp5_bs_resolution_recovery_rollback.sql',
        'supabase/tests/cp5_rework_accessory_lineage_rollback.sql',
      ],
      uat_applied: reliabilityRecorded,
      uat_platform_ledger_version: reliabilityRecorded ? reliabilityEvidence.correction.platform_ledger_version : null,
      uat_platform_statement_count: reliabilityRecorded ? reliabilityEvidence.correction.platform_statement_count : null,
      uat_business_facts_observed: 0,
    },
    atomic_reversal: {
      version: '20260904061346', application_version: 'v2.6.19c',
      name: 'erp_v2_6_19c_cp5_atomic_reversal_reconciliation',
      source_path: atomicMigrationRelative,
      source_bytes: atomicMigrationBytes.length,
      source_sha256: atomicMigrationHash,
      connector_ledger_sha256: 'ee26bce863a95d5994b61f2794de3fa42811cd08fc127f4148897ba4becc5fb6',
      rollback_path: atomicRollbackRelative,
      acceptance_paths: [
        'supabase/tests/cp5_bs_resolution_recovery_rollback.sql',
        'scripts/cp5_bs_resolution_concurrency.py',
      ],
      uat_applied: atomicRecorded,
      uat_platform_ledger_version: atomicRecorded ? atomicEvidence.correction.platform_ledger_version : null,
      uat_platform_statement_count: atomicRecorded ? atomicEvidence.correction.platform_statement_count : null,
      uat_business_facts_observed: 0,
    },
  },
  verification: {
    status: atomicRecorded
      ? 'V2619C_CODE_HEAD_CI_AND_UAT_PASS_READY_FOR_INDEPENDENT_REAUDIT'
      : 'V2619C_CODE_CANDIDATE_AWAITING_EXACT_HEAD_CI_AND_UAT',
    required_local_commands: ['npm test', 'npm run build', 'npm run test:security'],
    full_schema_acceptance_executed: true,
    hosted_uat_executed: true,
    hosted_uat_evidence_path: hostedEvidenceRelative,
    forward_correction_uat_evidence_path: lineageEvidenceRelative,
    forward_correction_hosted_http_auth_retest: false,
    forward_correction_full_schema_ci: 'PASS',
    forward_correction_ci_head_sha: v2619aCodeHeadSha,
    forward_correction_ci_head_tree: v2619aCodeHeadTree,
    reliability_correction_uat_evidence_path: reliabilityRecorded ? reliabilityEvidenceRelative : null,
    reliability_correction_full_schema_ci: reliabilityRecorded ? 'PASS' : 'PENDING',
    reliability_correction_ci_head_sha: reliabilityRecorded ? reliabilityEvidence.code_ci.runtime_head_sha : null,
    reliability_correction_ci_head_tree: reliabilityRecorded ? reliabilityEvidence.code_ci.runtime_head_tree : null,
    atomic_reversal_uat_evidence_path: atomicRecorded ? atomicEvidenceRelative : null,
    atomic_reversal_full_schema_ci: atomicRecorded ? 'PASS' : 'PENDING',
    atomic_reversal_ci_head_sha: atomicRecorded ? atomicEvidence.code_ci.runtime_head_sha : null,
    atomic_reversal_ci_head_tree: atomicRecorded ? atomicEvidence.code_ci.runtime_head_tree : null,
    read_only_uat_preflight_executed: true,
    read_only_uat_preflight_path: 'docs/evidence/cp5_uat_readonly_preflight.json',
  },
  candidate_apply_status: atomicRecorded
    ? 'RECORDED_V2618_V2618A_V2619_V2619A_V2619B_V2619C'
    : 'RECORDED_V2618_V2618A_V2619_V2619A_V2619B_V2619C_PENDING',
  uat_recorded_state: {
    application_versions: atomicRecorded
      ? ['v2.6.18', 'v2.6.18a', 'v2.6.19', 'v2.6.19a', 'v2.6.19b', 'v2.6.19c']
      : ['v2.6.18', 'v2.6.18a', 'v2.6.19', 'v2.6.19a', 'v2.6.19b'],
    platform_versions: atomicRecorded
      ? ['20260903060213', '20260903105741', '20260903105814', '20260903151034', reliabilityEvidence.correction.platform_ledger_version, atomicEvidence.correction.platform_ledger_version]
      : ['20260903060213', '20260903105741', '20260903105814', '20260903151034', reliabilityEvidence.correction.platform_ledger_version],
    latest_installed_at: atomicRecorded
      ? atomicEvidence.correction.installed_at
      : reliabilityEvidence.correction.installed_at,
  },
  closure_status: atomicRecorded
    ? 'READY_FOR_INDEPENDENT_REAUDIT_NO_GO'
    : 'V2619C_CORRECTION_PENDING_CI_UAT_NO_GO',
  hosted_auth_permission_e2e: {
    status: hostedEvidence.status,
    mode: hostedEvidence.mode,
    classified_as_ci: hostedEvidence.classified_as_ci,
    evidence_path: hostedEvidenceRelative,
    case_count: hostedEvidence.case_count,
    case_passed: hostedEvidence.case_passed,
    synthetic_cleanup_zero: true,
  },
  ci_runtime: atomicRecorded ? atomicEvidence.code_ci : reliabilityRecorded ? reliabilityEvidence.code_ci : {
    status: 'PASS',
    scope: 'LAST_RECORDED_V2619A_CODE_HEAD_HISTORICAL',
    runtime_head_sha: v2619aCodeHeadSha,
    runtime_head_tree: v2619aCodeHeadTree,
    unit_tests: { files: 25, passed: 168 },
    browser_tests: { cp45: 2, pre_cp5: 2, cp5: 6, total: 10 },
    build_push: {
      run_id: 33774390975, job_id: 100712335950,
      dist_artifact_id: 9901021365,
      dist_artifact_digest_sha256: '9729560d4f063e673603c685f4ff803613806105bcc89d3d8455c388ae71d7e4',
      browser_artifact_id: 9901019172,
      browser_artifact_digest_sha256: '31914693f2cee7acdd42a8f8eb42680cbf351739e4e553748853f484b9ca9f23',
    },
    build_pr: {
      run_id: 33774401928, job_id: 100712374137,
      dist_artifact_id: 9901045905,
      dist_artifact_digest_sha256: '4f90cca51a0ba9c2ec7799b6636ac4205e36b6dfdc598e4db282ee1216ba1c1b',
      browser_artifact_id: 9901043335,
      browser_artifact_digest_sha256: 'bd04387cb5912fff80fc001fa04d2931d890e2e1496386cf504ed830135399cd',
    },
    cp5_full_schema: {
      run_id: 33774390811, job_id: 100712335295,
      artifact_id: 9901122437,
      artifact_digest_sha256: '979d3ac9e23bbe86dcafbd01bddd52eb77ec2bf478a391b1d4424bbae1205a87',
    },
    pre_cp5_full_schema: {
      run_id: 33774401624, job_id: 100712374712,
      artifact_id: 9901057447,
      artifact_digest_sha256: 'e232cf72bff897c399763bb65d417e6a11f6c0aa94696adb4b91d55b98fe0c17',
    },
    workers_build: {
      check_id: 100712911183,
      build_id: 'f1ee6e8f-9308-4a48-82eb-f01ed7837a82',
    },
  },
  pre_v2619a_ci_runtime: {
    status: hostedEvidence.source_ci.status,
    scope: 'HISTORICAL_PRE_V2619A_BASELINE_ONLY',
    runtime_head_sha: hostedEvidence.source_ci.head_sha,
    runtime_head_tree: hostedEvidence.source_ci.head_tree,
    build_push_run_id: hostedEvidence.source_ci.build_push.run_id,
    full_schema_run_id: hostedEvidence.source_ci.cp5_full_schema.run_id,
    full_schema_artifact_id: hostedEvidence.source_ci.cp5_full_schema.artifact_id,
    full_schema_artifact_digest_sha256: hostedEvidence.source_ci.cp5_full_schema.artifact_digest_sha256,
  },
  cloudflare_preview: {
    status: 'PASS',
    version_id: hostedEvidence.cloudflare_preview.version_id,
    immutable_preview_url: hostedEvidence.cloudflare_preview.immutable_preview_url,
    observed_runtime_identity: hostedEvidence.cloudflare_preview.observed_runtime_identity,
    promoted_to_canonical_worker: hostedEvidence.cloudflare_preview.promoted_to_canonical_worker,
  },
  source_only: false,
  uat_applied: true,
  uat_applied_at: atomicRecorded
    ? atomicEvidence.correction.installed_at
    : reliabilityRecorded
      ? reliabilityEvidence.correction.installed_at
      : '2026-09-03T15:10:34.973034Z',
  current_correction_uat_applied: atomicRecorded,
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
  uat_applied: true,
  candidate_apply_status: manifest.candidate_apply_status,
  production_go: false,
}
writeFileSync(ownershipPath, `${JSON.stringify(ownership, null, 2)}\n`)

console.log(`Rendered CP5 source ownership: ${candidates.length} byte-bound files; migration ledgers ${cuttingMigrationHash.slice(0, 12)} / ${correctionMigrationHash.slice(0, 12)} / ${cp5MigrationHash.slice(0, 12)} / ${lineageMigrationHash.slice(0, 12)} / ${reliabilityMigrationHash.slice(0, 12)} / ${atomicMigrationHash.slice(0, 12)}; v2.6.19c ${atomicRecorded ? 'RECORDED' : 'PENDING'}.`)
