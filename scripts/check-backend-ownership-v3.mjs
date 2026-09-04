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
assert.equal(ownershipV3.uat_applied, true)
assert.ok([
  'RECORDED_V2618_V2618A_V2619_V2619A_V2619B_PENDING',
  'RECORDED_V2618_V2618A_V2619_V2619A_V2619B',
  'RECORDED_V2618_V2618A_V2619_V2619A_V2619B_V2619C_PENDING',
  'RECORDED_V2618_V2618A_V2619_V2619A_V2619B_V2619C',
].includes(ownershipV3.candidate_apply_status))

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
const reliabilityRecorded = candidate.migrations?.reliability_closure?.uat_applied === true
const atomicRecorded = candidate.current_correction_uat_applied === true
assert.equal(reliabilityRecorded, true, 'Recorded v2.6.19b predecessor disappeared from the v2.6.19c boundary')
const expectedApplyStatus = atomicRecorded
  ? 'RECORDED_V2618_V2618A_V2619_V2619A_V2619B_V2619C'
  : 'RECORDED_V2618_V2618A_V2619_V2619A_V2619B_V2619C_PENDING'
assert.equal(ownershipV3.candidate_apply_status, expectedApplyStatus)
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
assert.match(candidate.generation_parent_sha, /^[0-9a-f]{40}$/)
assert.equal(git('rev-parse', `${candidate.source_base_sha}^{tree}`), candidate.source_base_tree)
assert.equal(candidate.target_project_ref, 'siimvrusnzxexizpyoib')
assert.equal(candidate.legacy_project_ref, 'vlxdhpkjeevubjxexnfo')
assert.equal(candidate.source_only, false)
assert.equal(candidate.uat_applied, true)
assert.equal(candidate.candidate_apply_status, expectedApplyStatus)
assert.equal(candidate.legacy_mutated, false)
assert.equal(candidate.production_go, false)
assert.equal(candidate.verification.status, atomicRecorded
  ? 'V2619C_CODE_HEAD_CI_AND_UAT_PASS_READY_FOR_INDEPENDENT_REAUDIT'
  : 'V2619C_CODE_CANDIDATE_AWAITING_EXACT_HEAD_CI_AND_UAT')
assert.equal(candidate.closure_status, atomicRecorded
  ? 'READY_FOR_INDEPENDENT_REAUDIT_NO_GO'
  : 'V2619C_CORRECTION_PENDING_CI_UAT_NO_GO')
assert.equal(candidate.verification.full_schema_acceptance_executed, true)
assert.equal(candidate.verification.hosted_uat_executed, true)
assert.equal(candidate.verification.hosted_uat_evidence_path, 'docs/evidence/cp5_hosted_uat_auth_e2e.json')
assert.equal(candidate.verification.forward_correction_uat_evidence_path, 'docs/evidence/cp5_v2619a_uat_acceptance.json')
assert.equal(candidate.verification.forward_correction_hosted_http_auth_retest, false)
assert.equal(candidate.verification.forward_correction_full_schema_ci, 'PASS')
assert.equal(candidate.verification.forward_correction_ci_head_sha, '2175bd8f199f6a5d860e7f517042e2efe35916e7')
assert.equal(candidate.verification.forward_correction_ci_head_tree, 'd845b1ff613774a150b999dbfa2b41b772e416e9')
assert.equal(candidate.verification.reliability_correction_full_schema_ci, 'PASS')
assert.equal(candidate.verification.reliability_correction_uat_evidence_path, 'docs/evidence/cp5_v2619b_uat_acceptance.json')
assert.equal(candidate.verification.atomic_reversal_full_schema_ci, atomicRecorded ? 'PASS' : 'PENDING')
assert.equal(candidate.verification.atomic_reversal_uat_evidence_path, atomicRecorded
  ? 'docs/evidence/cp5_v2619c_uat_acceptance.json'
  : null)
if (!atomicRecorded) {
  assert.equal(candidate.verification.atomic_reversal_ci_head_sha, null)
  assert.equal(candidate.verification.atomic_reversal_ci_head_tree, null)
  assert.equal(candidate.uat_applied_at, '2026-09-04T03:21:10.200423Z')
  assert.deepEqual(candidate.uat_recorded_state, {
    application_versions: ['v2.6.18', 'v2.6.18a', 'v2.6.19', 'v2.6.19a', 'v2.6.19b'],
    platform_versions: ['20260903060213', '20260903105741', '20260903105814', '20260903151034', '20260904032110'],
    latest_installed_at: '2026-09-04T03:21:10.200423Z',
  })
}
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

const hostedEvidence = readJson(candidate.verification.hosted_uat_evidence_path)
const lineageEvidence = readJson(candidate.verification.forward_correction_uat_evidence_path)
assert.equal(hostedEvidence.format, 'CP5_HOSTED_UAT_AUTH_E2E_V1')
assert.equal(hostedEvidence.status, 'PASS')
assert.equal(hostedEvidence.mode, 'MANUAL_HOSTED_UAT_VERIFIED')
assert.equal(hostedEvidence.classified_as_ci, false)
assert.equal(hostedEvidence.closure_status, 'READY_FOR_INDEPENDENT_AUDIT_NO_GO')
assert.equal(hostedEvidence.target_project_ref, 'siimvrusnzxexizpyoib')
assert.equal(hostedEvidence.reviewed_runtime_source.remote_head_sha, 'e2745a2f3cf77735913967dfb57151069513bbf1')
assert.equal(hostedEvidence.reviewed_runtime_source.head_tree, 'f0bbaefdc2a44d101f762342e4b82f96d3eddfdd')
assert.equal(hostedEvidence.reviewed_runtime_source.tree_equal, true)
assert.equal(hostedEvidence.case_count, 31)
assert.equal(hostedEvidence.case_passed, 31)
assert.equal(hostedEvidence.cases.length, 31)
assert.ok(hostedEvidence.cases.every(({ ok }) => ok === true))
assert.equal(hostedEvidence.assertions.server_side_pattern_filter_has_true_empty_state, true)
assert.equal(hostedEvidence.assertions.synthetic_cleanup_returns_exact_zero, true)
for (const field of [
  'auth_users', 'auth_identities', 'auth_sessions', 'auth_refresh_tokens',
  'app_users', 'custom_roles', 'bs_cases', 'bs_resolutions', 'bs_components',
  'rework_orders', 'rework_components', 'hold_events', 'idempotency',
  'execution_context', 'synthetic_access_audit', 'synthetic_audit_logs',
  'temporary_http_extensions', 'new_audit_rows_after_cleanup', 'waiting_locks',
  'transactions_over_5m',
]) assert.equal(hostedEvidence.cleanup[field], 0, `CP5 hosted cleanup residue: ${field}`)
assert.equal(hostedEvidence.cleanup.preexisting_audit_rows_preserved, 36)
assert.equal(hostedEvidence.cleanup.temporary_credentials_retained, false)
assert.equal(hostedEvidence.source_ci.status, 'PASS')
assert.equal(hostedEvidence.source_ci.unit_tests.passed, 165)
assert.equal(hostedEvidence.source_ci.cp5_full_schema.real_two_connection_disposition_race, 'PASS')
assert.equal(hostedEvidence.source_ci.cp5_full_schema.real_two_connection_damage_capacity_race, 'PASS')
assert.equal(hostedEvidence.cloudflare_preview.observed_runtime_identity, 'ERP ENTENG · UAT AUTH')
assert.equal(hostedEvidence.cloudflare_preview.promoted_to_canonical_worker, false)
assert.equal(hostedEvidence.cloudflare_preview.temporary_environment_file_active, false)
assert.equal(hostedEvidence.legacy_mutated, false)
assert.equal(hostedEvidence.production_go, false)
assert.equal(lineageEvidence.format, 'CP5_V2619A_UAT_ACCEPTANCE_V1')
assert.equal(lineageEvidence.status, 'PASS')
assert.equal(lineageEvidence.mode, 'HOSTED_UAT_RECORDED_MIGRATION_AND_TRANSACTIONAL_SQL')
assert.equal(lineageEvidence.correction.application_version, 'v2.6.19a')
assert.equal(lineageEvidence.correction.platform_ledger_version, '20260903151034')
assert.equal(lineageEvidence.correction.source_bytes, 55354)
assert.equal(lineageEvidence.correction.source_sha256, '204b9246f3c8c6464476da1a7f1574f5e0ae4c46f024c082704795b3eef5210f')
assert.equal(lineageEvidence.predecessor_preserved.rewritten_or_deleted, false)
assert.ok(lineageEvidence.transactional_proofs.every(({ status, state_effect }) => status === 'PASS' && state_effect.includes('ROLLED_BACK')))
assert.ok(Object.values(lineageEvidence.assertions).every((value) => value === true))
assert.ok(Object.values(lineageEvidence.post_proof_residue).every((value) => value === 0))
assert.equal(lineageEvidence.hosted_http_auth_retest, false)
assert.equal(lineageEvidence.legacy_mutated, false)
assert.equal(lineageEvidence.production_go, false)
assert.deepEqual(candidate.hosted_auth_permission_e2e, {
  status: 'PASS',
  mode: 'MANUAL_HOSTED_UAT_VERIFIED',
  classified_as_ci: false,
  evidence_path: candidate.verification.hosted_uat_evidence_path,
  case_count: 31,
  case_passed: 31,
  synthetic_cleanup_zero: true,
})
const historicalV2619aCiRuntime = {
  status: 'PASS',
  scope: 'LAST_RECORDED_V2619A_CODE_HEAD_HISTORICAL',
  runtime_head_sha: '2175bd8f199f6a5d860e7f517042e2efe35916e7',
  runtime_head_tree: 'd845b1ff613774a150b999dbfa2b41b772e416e9',
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
}
let reliabilityEvidence = null
if (reliabilityRecorded) {
  reliabilityEvidence = readJson(candidate.verification.reliability_correction_uat_evidence_path)
  assert.equal(reliabilityEvidence.format, 'CP5_V2619B_UAT_ACCEPTANCE_V1')
  assert.equal(reliabilityEvidence.status, 'PASS')
  assert.equal(reliabilityEvidence.mode, 'EXACT_CODE_HEAD_CI_AND_HOSTED_UAT_RECORDED_MIGRATION')
  assert.equal(reliabilityEvidence.target_project_ref, 'siimvrusnzxexizpyoib')
  assert.equal(reliabilityEvidence.legacy_project_ref, 'vlxdhpkjeevubjxexnfo')
  assert.equal(reliabilityEvidence.correction.application_version, 'v2.6.19b')
  assert.equal(reliabilityEvidence.correction.source_ledger_version, '20260904012525')
  assert.equal(reliabilityEvidence.correction.source_path, 'supabase/migrations/20260904012525_erp_v2_6_19b_cp5_reliability_closure.sql')
  assert.equal(reliabilityEvidence.correction.source_bytes, 42021)
  assert.equal(reliabilityEvidence.correction.source_sha256, 'b1bde1a6ccd1f60dd001d99b72d479ffa0a18a6ea46bf93cd80e406e2ef0ce1d')
  assert.equal(reliabilityEvidence.correction.connector_ledger_sha256, '89ed4535720e12722bc1cbedd1bbcb5b7920f9ee4b6b19754214d05ac82b0e8d')
  assert.equal(reliabilityEvidence.correction.platform_statement_count, 1)
  assert.match(reliabilityEvidence.correction.platform_ledger_version, /^\d{14}$/)
  assert.match(reliabilityEvidence.correction.installed_at, /^2026-/)
  assert.equal(reliabilityEvidence.code_ci.status, 'PASS')
  assert.equal(reliabilityEvidence.code_ci.scope, 'CURRENT_V2619B_CODE_HEAD')
  assert.match(reliabilityEvidence.code_ci.runtime_head_sha, /^[0-9a-f]{40}$/)
  assert.match(reliabilityEvidence.code_ci.runtime_head_tree, /^[0-9a-f]{40}$/)
  assert.deepEqual(reliabilityEvidence.code_ci.unit_tests, { files: 25, passed: 172 })
  assert.deepEqual(reliabilityEvidence.code_ci.browser_tests, { cp45: 2, pre_cp5: 2, cp5: 6, total: 10 })
  assert.equal(candidate.verification.reliability_correction_ci_head_sha, reliabilityEvidence.code_ci.runtime_head_sha)
  assert.equal(candidate.verification.reliability_correction_ci_head_tree, reliabilityEvidence.code_ci.runtime_head_tree)
  assert.ok(Object.values(reliabilityEvidence.post_proof_residue).every((value) => value === 0))
  assert.equal(reliabilityEvidence.legacy_read_only.legacy_mutated, false)
  assert.equal(reliabilityEvidence.production_go, false)
} else {
  assert.deepEqual(candidate.ci_runtime, historicalV2619aCiRuntime)
}
let atomicEvidence = null
if (atomicRecorded) {
  atomicEvidence = readJson(candidate.verification.atomic_reversal_uat_evidence_path)
  assert.equal(atomicEvidence.format, 'CP5_V2619C_UAT_ACCEPTANCE_V1')
  assert.equal(atomicEvidence.status, 'PASS')
  assert.equal(atomicEvidence.mode, 'EXACT_CODE_HEAD_CI_AND_HOSTED_UAT_RECORDED_MIGRATION')
  assert.equal(atomicEvidence.target_project_ref, 'siimvrusnzxexizpyoib')
  assert.equal(atomicEvidence.legacy_project_ref, 'vlxdhpkjeevubjxexnfo')
  assert.equal(atomicEvidence.correction.application_version, 'v2.6.19c')
  assert.equal(atomicEvidence.correction.source_ledger_version, '20260904061346')
  assert.equal(atomicEvidence.correction.source_path, 'supabase/migrations/20260904061346_erp_v2_6_19c_cp5_atomic_reversal_reconciliation.sql')
  assert.equal(atomicEvidence.correction.source_bytes, 13864)
  assert.equal(atomicEvidence.correction.source_sha256, '1b66c8bd8c12c2acef47e97e7e0ff15e82e5ef12618d11fea288750b862732e7')
  assert.equal(atomicEvidence.correction.connector_ledger_sha256, 'ee26bce863a95d5994b61f2794de3fa42811cd08fc127f4148897ba4becc5fb6')
  assert.equal(atomicEvidence.correction.platform_statement_count, 1)
  assert.match(atomicEvidence.correction.platform_ledger_version, /^\d{14}$/)
  assert.match(atomicEvidence.correction.installed_at, /^2026-/)
  assert.equal(atomicEvidence.code_ci.status, 'PASS')
  assert.equal(atomicEvidence.code_ci.scope, 'CURRENT_V2619C_CODE_HEAD')
  assert.match(atomicEvidence.code_ci.runtime_head_sha, /^[0-9a-f]{40}$/)
  assert.match(atomicEvidence.code_ci.runtime_head_tree, /^[0-9a-f]{40}$/)
  assert.deepEqual(atomicEvidence.code_ci.unit_tests, { files: 25, passed: 172 })
  assert.deepEqual(atomicEvidence.code_ci.browser_tests, { cp45: 2, pre_cp5: 2, cp5: 8, total: 12 })
  assert.equal(candidate.verification.atomic_reversal_ci_head_sha, atomicEvidence.code_ci.runtime_head_sha)
  assert.equal(candidate.verification.atomic_reversal_ci_head_tree, atomicEvidence.code_ci.runtime_head_tree)
  assert.deepEqual(candidate.ci_runtime, atomicEvidence.code_ci)
  assert.equal(candidate.uat_applied_at, atomicEvidence.correction.installed_at)
  assert.deepEqual(candidate.uat_recorded_state, {
    application_versions: ['v2.6.18', 'v2.6.18a', 'v2.6.19', 'v2.6.19a', 'v2.6.19b', 'v2.6.19c'],
    platform_versions: ['20260903060213', '20260903105741', '20260903105814', '20260903151034', reliabilityEvidence.correction.platform_ledger_version, atomicEvidence.correction.platform_ledger_version],
    latest_installed_at: atomicEvidence.correction.installed_at,
  })
  assert.ok(Object.values(atomicEvidence.post_proof_residue).every((value) => value === 0))
  assert.equal(atomicEvidence.legacy_read_only.legacy_mutated, false)
  assert.equal(atomicEvidence.production_go, false)
} else {
  assert.deepEqual(candidate.ci_runtime, reliabilityEvidence.code_ci)
}
assert.deepEqual(candidate.pre_v2619a_ci_runtime, {
  status: hostedEvidence.source_ci.status,
  scope: 'HISTORICAL_PRE_V2619A_BASELINE_ONLY',
  runtime_head_sha: hostedEvidence.source_ci.head_sha,
  runtime_head_tree: hostedEvidence.source_ci.head_tree,
  build_push_run_id: hostedEvidence.source_ci.build_push.run_id,
  full_schema_run_id: hostedEvidence.source_ci.cp5_full_schema.run_id,
  full_schema_artifact_id: hostedEvidence.source_ci.cp5_full_schema.artifact_id,
  full_schema_artifact_digest_sha256: hostedEvidence.source_ci.cp5_full_schema.artifact_digest_sha256,
})
assert.equal(candidate.cloudflare_preview.status, 'PASS')
assert.equal(candidate.cloudflare_preview.promoted_to_canonical_worker, false)

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
  rework_accessory_lineage: {
    version: '20260903151034', application_version: 'v2.6.19a',
    name: 'erp_v2_6_19a_cp5_rework_accessory_lineage',
  },
  reliability_closure: {
    version: '20260904012525', application_version: 'v2.6.19b',
    name: 'erp_v2_6_19b_cp5_reliability_closure',
  },
  atomic_reversal: {
    version: '20260904061346', application_version: 'v2.6.19c',
    name: 'erp_v2_6_19c_cp5_atomic_reversal_reconciliation',
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
  const acceptancePaths = migration.acceptance_paths ?? [migration.acceptance_path]
  assert.ok(acceptancePaths.length > 0)
  for (const acceptancePath of acceptancePaths) {
    assert.ok(cuttingOverrides.has(acceptancePath) || cp5Overrides.has(acceptancePath))
  }
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
assert.deepEqual(candidate.migrations.cutting_bridge_reconciliation, {
  ...candidate.migrations.cutting_bridge_reconciliation,
  uat_applied: true,
  uat_platform_ledger_version: '20260903105741',
  uat_platform_statement_count: 1,
  uat_business_facts_observed: 0,
})
assert.deepEqual(candidate.migrations.bs_resolution, {
  ...candidate.migrations.bs_resolution,
  uat_applied: true,
  uat_platform_ledger_version: '20260903105814',
  uat_platform_statement_count: 1,
  uat_business_facts_observed: 0,
})
assert.deepEqual(candidate.migrations.rework_accessory_lineage, {
  ...candidate.migrations.rework_accessory_lineage,
  uat_applied: true,
  uat_platform_ledger_version: '20260903151034',
  uat_platform_statement_count: 1,
  uat_business_facts_observed: 0,
})
assert.equal(candidate.migrations.rework_accessory_lineage.source_bytes, 55354)
assert.equal(candidate.migrations.rework_accessory_lineage.source_sha256, '204b9246f3c8c6464476da1a7f1574f5e0ae4c46f024c082704795b3eef5210f')
assert.deepEqual(candidate.migrations.reliability_closure, {
  ...candidate.migrations.reliability_closure,
  connector_ledger_sha256: '89ed4535720e12722bc1cbedd1bbcb5b7920f9ee4b6b19754214d05ac82b0e8d',
  uat_applied: reliabilityRecorded,
  uat_platform_ledger_version: reliabilityRecorded ? reliabilityEvidence.correction.platform_ledger_version : null,
  uat_platform_statement_count: reliabilityRecorded ? 1 : null,
  uat_business_facts_observed: 0,
})
assert.equal(candidate.migrations.reliability_closure.source_bytes, 42021)
assert.equal(candidate.migrations.reliability_closure.source_sha256, 'b1bde1a6ccd1f60dd001d99b72d479ffa0a18a6ea46bf93cd80e406e2ef0ce1d')
assert.deepEqual(candidate.migrations.atomic_reversal, {
  ...candidate.migrations.atomic_reversal,
  connector_ledger_sha256: 'ee26bce863a95d5994b61f2794de3fa42811cd08fc127f4148897ba4becc5fb6',
  uat_applied: atomicRecorded,
  uat_platform_ledger_version: atomicRecorded ? atomicEvidence.correction.platform_ledger_version : null,
  uat_platform_statement_count: atomicRecorded ? 1 : null,
  uat_business_facts_observed: 0,
})
assert.equal(candidate.migrations.atomic_reversal.source_bytes, 13864)
assert.equal(candidate.migrations.atomic_reversal.source_sha256, '1b66c8bd8c12c2acef47e97e7e0ff15e82e5ef12618d11fea288750b862732e7')

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
  candidate.verification.hosted_uat_evidence_path,
  candidate.verification.forward_correction_uat_evidence_path,
  ...(candidate.verification.reliability_correction_uat_evidence_path
    ? [candidate.verification.reliability_correction_uat_evidence_path]
    : []),
  ...(candidate.verification.atomic_reversal_uat_evidence_path
    ? [candidate.verification.atomic_reversal_uat_evidence_path]
    : []),
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
    || path === candidate.verification.hosted_uat_evidence_path
    || path === candidate.verification.forward_correction_uat_evidence_path
    || path === candidate.verification.reliability_correction_uat_evidence_path
    || path === candidate.verification.atomic_reversal_uat_evidence_path
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
