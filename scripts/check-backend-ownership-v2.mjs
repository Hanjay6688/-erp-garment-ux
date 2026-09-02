import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { readFileSync, readdirSync } from 'node:fs'
import { extname, join, relative, resolve } from 'node:path'

const root = process.cwd()
const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim()
const hash = (algorithm, bytes) => createHash(algorithm).update(bytes).digest('hex')
const posix = (path) => path.split('\\').join('/')
const readJson = (path) => JSON.parse(readFileSync(resolve(root, path), 'utf8'))

const ownershipV1Path = 'docs/evidence/backend_source_ownership.json'
const ownershipV2Path = 'docs/evidence/backend_source_ownership_v2.json'
const ownershipV1Bytes = readFileSync(resolve(root, ownershipV1Path))
const ownershipV2 = readJson(ownershipV2Path)
const ownershipV1 = JSON.parse(ownershipV1Bytes)

assert.equal(hash('sha256', ownershipV1Bytes), '5da3ee5d3b906ebdd1f4bfb55d35a91b3ce6d715c03b98463e6dee35ad04dd1e')
assert.equal(ownershipV1.format, 'ERP_BACKEND_SOURCE_OWNERSHIP_V1')
assert.equal(ownershipV2.format, 'ERP_BACKEND_SOURCE_OWNERSHIP_V2')
assert.deepEqual(ownershipV2.frozen_v1, {
  path: ownershipV1Path,
  bytes: 3894,
  sha256: '5da3ee5d3b906ebdd1f4bfb55d35a91b3ce6d715c03b98463e6dee35ad04dd1e',
})
assert.equal(ownershipV2.target_project_ref, 'siimvrusnzxexizpyoib')
assert.equal(ownershipV2.legacy_project_ref, 'vlxdhpkjeevubjxexnfo')
assert.equal(ownershipV2.production_go, false)

const cp3ManifestBytes = readFileSync(resolve(root, ownershipV1.reviewed_cp3_manifest.path))
const cp3Manifest = JSON.parse(cp3ManifestBytes)
const cp4ManifestBytes = readFileSync(resolve(root, ownershipV1.candidate_cp4_manifest.path))
const cp4Manifest = JSON.parse(cp4ManifestBytes)
assert.equal(hash('sha256', cp3ManifestBytes), ownershipV1.reviewed_cp3_manifest.sha256)
assert.equal(hash('sha256', cp4ManifestBytes), ownershipV1.candidate_cp4_manifest.sha256)
assert.equal(cp3Manifest.format, 'CP3_R5_CURRENT_MAIN_FIXED_SOURCE_HASHES_V1')
assert.equal(cp4Manifest.format, 'CP4_R1_SOURCE_HASHES_V1')
assert.equal(cp4Manifest.production_go, false)
assert.equal(cp4Manifest.legacy_mutated, false)

const candidateManifestBytes = readFileSync(resolve(root, ownershipV2.candidate_cp45_manifest.path))
const candidate = JSON.parse(candidateManifestBytes)
const cp45aRollbackSource = readFileSync(resolve(
  root,
  'supabase/rollbacks/20260902180726_erp_v2_6_17a_cp45_pattern_assignment_immutability.rollback.sql',
), 'utf8')
const cp45aWorkflowSource = readFileSync(resolve(root, '.github/workflows/cp45-full-schema-validation.yml'), 'utf8')
const normalizeSql = (value) => value.replace(/\s+/g, ' ').trim()
const guardLedgerPredicate = cp45aRollbackSource.match(
  /select count\(\*\) into v_match_count\s+from supabase_migrations\.schema_migrations m\s+where ([\s\S]*?);\s+select count\(\*\) into v_conflict_count/,
)
const deleteLedgerPredicate = cp45aRollbackSource.match(
  /delete from supabase_migrations\.schema_migrations m\s+where ([\s\S]*?);\s+drop table erp\.cp45_v2617a_rollback_capsule/,
)
assert.ok(guardLedgerPredicate, 'CP4.5a rollback guard ledger predicate is missing')
assert.ok(deleteLedgerPredicate, 'CP4.5a rollback DELETE ledger predicate is missing')
assert.equal(
  normalizeSql(deleteLedgerPredicate[1]),
  normalizeSql(guardLedgerPredicate[1]),
  'CP4.5a rollback DELETE predicate diverges from the guarded ledger match',
)
assert.match(
  normalizeSql(guardLedgerPredicate[1]),
  /m\.version='20260902180726' and m\.name='erp_v2_6_17a_cp45_pattern_assignment_immutability'/,
)
assert.match(cp45aWorkflowSource, /set name='WRONG_MIGRATION'/)
assert.match(cp45aWorkflowSource, /CP45A_ROLLBACK_WRONG_LOCAL_NAME_REJECTION\.log/)
assert.equal(candidateManifestBytes.length, ownershipV2.candidate_cp45_manifest.bytes)
assert.equal(hash('sha256', candidateManifestBytes), ownershipV2.candidate_cp45_manifest.sha256)
assert.equal(candidate.format, 'CP45_R1_SOURCE_HASHES_V1')
assert.equal(candidate.candidate_branch, 'cp4.5/rbac-production-identity-wip-r1-20260902')
assert.equal(candidate.source_base_sha, '57d8346a7cdf4ee86519f2dd2a1b54d39ebbb6cc')
assert.equal(candidate.source_base_tree, '48fc87507dc8a18d5829d518e53f298ad0c7e01a')
assert.equal(candidate.target_project_ref, 'siimvrusnzxexizpyoib')
assert.equal(candidate.legacy_project_ref, 'vlxdhpkjeevubjxexnfo')
assert.equal(candidate.migration_version, '20260902104937')
assert.equal(candidate.application_version, 'v2.6.17')
assert.equal(candidate.integrity_correction.defect_id, 'P2-CP45-001')
assert.equal(candidate.integrity_correction.migration_version, '20260902180726')
assert.equal(candidate.integrity_correction.application_version, 'v2.6.17a')
assert.equal(candidate.integrity_correction.hosted_auth_permission_e2e.mode, 'MANUAL_HOSTED_UAT_VERIFIED')
assert.equal(candidate.integrity_correction.hosted_auth_permission_e2e.classified_as_ci, false)
assert.equal(candidate.integrity_correction.hosted_auth_permission_e2e.github_service_role_secret_used, false)
if (candidate.integrity_correction.uat_applied) {
  assert.equal(candidate.integrity_correction.source_only, false)
  assert.match(candidate.integrity_correction.uat_applied_at, /^2026-09-02T/)
  assert.equal(candidate.integrity_correction.exact_head_ci.status, 'PASS')
  assert.equal(candidate.integrity_correction.hosted_auth_permission_e2e.status, 'PASS')
  assert.equal(candidate.integrity_correction.platform_ledger.version, '20260902185106')
  assert.equal(candidate.integrity_correction.platform_ledger.name, 'erp_v2_6_17a_cp45_pattern_assignment_immutability')
  assert.equal(candidate.integrity_correction.platform_ledger.source_bytes, 18304)
  assert.equal(candidate.integrity_correction.platform_ledger.source_sha256, '62a25994d2b3be0986ca83492f4d29d2ebad17c1795543045827a77d55ef816a')
  assert.equal(candidate.integrity_correction.hosted_auth_permission_e2e.evidence_path, 'docs/evidence/cp45a_hosted_uat_auth_e2e.json')
  assert.equal(candidate.integrity_correction.hosted_auth_permission_e2e.case_count, 10)
  assert.equal(candidate.integrity_correction.hosted_auth_permission_e2e.case_passed, 10)
  assert.equal(candidate.integrity_correction.hosted_auth_permission_e2e.cleanup_verified, true)
  assert.equal(candidate.integrity_correction.status, 'PASS_READY_FOR_INDEPENDENT_AUDIT')
  assert.equal(candidate.integrity_correction.proof_delta_ci.status, 'PASS')
  assert.equal(candidate.integrity_correction.proof_delta_ci.head_sha, 'ab97d1d08936c05c609c004477f974361340d203')
  assert.equal(candidate.integrity_correction.proof_delta_ci.head_tree, '70fbaee6366b904ad558a65471bafe38994e3090')
  assert.equal(candidate.integrity_correction.proof_delta_ci.parent_sha, candidate.integrity_correction.exact_head_ci.head_sha)
  assert.equal(candidate.integrity_correction.proof_delta_ci.build_ux.run_id, 33672264605)
  assert.equal(candidate.integrity_correction.proof_delta_ci.full_schema.run_id, 33672264683)
  assert.equal(candidate.integrity_correction.proof_delta_ci.hosted_platform_ledger_shape_rollback, 'PASS')
  const rollbackIdentity = candidate.integrity_correction.rollback_ledger_identity_correction
  assert.equal(rollbackIdentity.defect_id, 'P2-CP45-002')
  assert.equal(rollbackIdentity.status, 'SOURCE_PATCH_PENDING_EXACT_HEAD_CI')
  assert.equal(rollbackIdentity.runtime_changed, false)
  assert.equal(rollbackIdentity.uat_reapply_required, false)
  assert.equal(rollbackIdentity.hosted_auth_rerun_required, false)
  assert.deepEqual(rollbackIdentity.local_ledger_identity, {
    version: '20260902180726',
    name: 'erp_v2_6_17a_cp45_pattern_assignment_immutability',
    match_requirement: 'VERSION_AND_NAME',
  })
  assert.deepEqual(rollbackIdentity.connector_ledger_identity, {
    name: 'erp_v2_6_17a_cp45_pattern_assignment_immutability',
    source_sha256: '62a25994d2b3be0986ca83492f4d29d2ebad17c1795543045827a77d55ef816a',
    match_requirement: 'NAME_AND_SOURCE_SHA256',
  })
  assert.equal(rollbackIdentity.delete_predicate_matches_guard, true)
  assert.deepEqual(rollbackIdentity.negative_test, {
    status: 'PENDING_EXACT_HEAD_FULL_SCHEMA',
    case: 'LOCAL_VERSION_CORRECT_NAME_WRONG',
    expected: 'ROLLBACK_REFUSED',
  })
  assert.equal(rollbackIdentity.exact_head_ci.status, 'PENDING')
  assert.equal(candidate.closure_status, 'NO_GO_PENDING_CP45A_ROLLBACK_LEDGER_IDENTITY_CI')
} else {
  assert.equal(candidate.integrity_correction.source_only, true)
  assert.equal(candidate.integrity_correction.uat_applied_at, null)
  assert.equal(candidate.integrity_correction.exact_head_ci.status, 'PENDING')
  assert.equal(candidate.integrity_correction.hosted_auth_permission_e2e.status, 'PENDING')
  assert.equal(candidate.closure_status, 'NO_GO_PENDING_CP45A_CORRECTION_PROOF')
}

if (candidate.integrity_correction.hosted_auth_permission_e2e.evidence_path) {
  const correctionEvidence = readJson(candidate.integrity_correction.hosted_auth_permission_e2e.evidence_path)
  assert.equal(correctionEvidence.format, 'CP45A_HOSTED_UAT_AUTH_E2E_V1')
  assert.equal(correctionEvidence.status, 'PASS')
  assert.equal(correctionEvidence.mode, 'MANUAL_HOSTED_UAT_VERIFIED')
  assert.equal(correctionEvidence.target_project_ref, candidate.target_project_ref)
  assert.equal(correctionEvidence.runtime_source_head, candidate.integrity_correction.exact_head_ci.head_sha)
  assert.equal(correctionEvidence.runtime_source_tree, candidate.integrity_correction.exact_head_ci.head_tree)
  assert.equal(correctionEvidence.migration_version, candidate.integrity_correction.migration_version)
  assert.equal(correctionEvidence.application_version, candidate.integrity_correction.application_version)
  assert.deepEqual(correctionEvidence.platform_ledger, {
    version: '20260902185106',
    name: 'erp_v2_6_17a_cp45_pattern_assignment_immutability',
    statement_count: 1,
    source_bytes: 18304,
    source_sha256: '62a25994d2b3be0986ca83492f4d29d2ebad17c1795543045827a77d55ef816a',
  })
  assert.equal(correctionEvidence.verification_boundary.classified_as_ci, false)
  assert.equal(correctionEvidence.verification_boundary.github_service_role_secret_used, false)
  assert.equal(correctionEvidence.verification_boundary.service_role_key_used, false)
  assert.equal(correctionEvidence.verification_boundary.real_http_jwt, true)
  assert.equal(correctionEvidence.verification_boundary.synthetic_identities, 2)
  assert.equal(correctionEvidence.verification_boundary.real_owner_invited, false)
  assert.equal(correctionEvidence.verification_boundary.credentials_or_jwt_recorded, false)
  assert.equal(correctionEvidence.case_count, 10)
  assert.equal(correctionEvidence.case_passed, 10)
  assert.equal(correctionEvidence.cases.length, 10)
  assert.equal(new Set(correctionEvidence.cases.map(({ name }) => name)).size, 10)
  assert.equal(correctionEvidence.cases.every(({ ok }) => ok === true), true)
  assert.equal(correctionEvidence.assertions.first_assignment_binds_canonical_pattern_and_snapshot, true)
  assert.equal(correctionEvidence.assertions.first_assignment_replay_is_idempotent, true)
  assert.equal(correctionEvidence.assertions.second_assignment_is_rejected, true)
  assert.equal(correctionEvidence.assertions.rejected_reassignment_preserves_pattern_a_snapshot, true)
  assert.equal(correctionEvidence.assertions.sewing_fact_blocks_initial_assignment, true)
  assert.equal(correctionEvidence.assertions.view_only_user_cannot_assign_pattern, true)
  for (const key of [
    'auth_users', 'auth_identities', 'auth_sessions', 'auth_refresh_tokens',
    'app_users', 'patterns', 'pattern_audit', 'assignment_idempotency',
    'cutting_groups', 'work_completion_events', 'temporary_http_extensions',
  ]) assert.equal(correctionEvidence.cleanup[key], 0, `Hosted correction cleanup residue: ${key}`)
  assert.equal(correctionEvidence.cleanup.temporary_credentials_retained, false)
  assert.equal(correctionEvidence.uat_post_cleanup.writer_sessions, 0)
  assert.equal(correctionEvidence.uat_post_cleanup.idle_in_transaction, 0)
  assert.equal(correctionEvidence.uat_post_cleanup.waiting_locks, 0)
  assert.equal(correctionEvidence.uat_post_cleanup.write_capable_locks, 0)
  assert.equal(correctionEvidence.legacy_isolation.mutated, false)
  assert.equal(correctionEvidence.legacy_isolation.platform_cp45_ledger, 0)
  assert.equal(correctionEvidence.legacy_isolation.application_cp45_ledger, 0)
  assert.equal(correctionEvidence.advisor_snapshot.security.correction_specific, 0)
  assert.equal(correctionEvidence.advisor_snapshot.performance.correction_specific, 0)
  assert.deepEqual(correctionEvidence.proof_delta_ci, candidate.integrity_correction.proof_delta_ci)
  assert.equal(correctionEvidence.production_go, false)
}
assert.equal(candidate.legacy_mutated, false)
assert.equal(candidate.production_go, false)
assert.equal(candidate.hygiene.branch_protection_status_enforcement, false)
assert.equal(candidate.hygiene.severity, 'P3')
assert.equal(candidate.hygiene.cloudflare_dry_run_environment, 'uat-auth')
assert.equal(candidate.hygiene.production_deploy_authorized, false)
if (candidate.uat_applied) {
  assert.equal(candidate.source_only, false)
  assert.match(candidate.uat_applied_at, /^2026-09-02T/)
  assert.match(candidate.generation_parent_sha, /^[0-9a-f]{40}$/)
  if (process.env.GITHUB_ACTIONS === 'true') {
    assert.equal(candidate.generation_parent_sha, git('rev-parse', 'HEAD^'))
  }
  assert.equal(candidate.ci_runtime.status, 'PASS')
  assert.equal(candidate.ci_runtime.head_sha, '4cda99fcf6f96f053981787f8cc2cbd39b809928')
  assert.equal(candidate.ci_runtime.head_tree, 'c9b7aae6e3ea3db64d4abe6de4987f378166a9bf')
  assert.equal(candidate.ci_runtime.build_ux.run_id, 33643332136)
  assert.equal(candidate.ci_runtime.full_schema.run_id, 33643332142)
  assert.equal(candidate.hosted_auth_permission_e2e.status, 'PASS')
  assert.equal(candidate.hosted_auth_permission_e2e.mode, 'MANUAL_HOSTED_UAT_VERIFIED')
  assert.equal(candidate.hosted_auth_permission_e2e.classified_as_ci, false)
  assert.equal(candidate.hosted_auth_permission_e2e.github_service_role_secret_used, false)
  assert.equal(candidate.hosted_auth_permission_e2e.evidence_path, 'docs/evidence/cp45_hosted_uat_auth_e2e.json')
  assert.equal(candidate.hosted_auth_permission_e2e.case_count, 44)
  assert.equal(candidate.hosted_auth_permission_e2e.case_passed, 44)
  assert.equal(candidate.hosted_auth_permission_e2e.cleanup_verified, true)
} else {
  assert.equal(candidate.source_only, true)
  assert.equal(candidate.uat_applied_at, null)
  assert.equal(candidate.hosted_auth_permission_e2e.status, 'PENDING')
}

if (candidate.hosted_auth_permission_e2e.evidence_path) {
  const evidenceBytes = readFileSync(resolve(root, candidate.hosted_auth_permission_e2e.evidence_path))
  const evidence = JSON.parse(evidenceBytes)
  assert.equal(evidence.format, 'CP45_HOSTED_UAT_AUTH_E2E_V1')
  assert.equal(evidence.status, 'PASS')
  assert.equal(evidence.mode, 'MANUAL_HOSTED_UAT_VERIFIED')
  assert.equal(evidence.target_project_ref, candidate.target_project_ref)
  assert.equal(evidence.runtime_source_head, candidate.ci_runtime.head_sha)
  assert.equal(evidence.runtime_source_tree, candidate.ci_runtime.head_tree)
  assert.equal(evidence.migration_version, candidate.migration_version)
  assert.equal(evidence.application_version, candidate.application_version)
  assert.equal(evidence.verification_boundary.classified_as_ci, false)
  assert.equal(evidence.verification_boundary.github_service_role_secret_used, false)
  assert.equal(evidence.verification_boundary.service_role_key_used, false)
  assert.equal(evidence.verification_boundary.auth_fixture, 'DIRECT_HOSTED_AUTH_ROWS_WITH_REAL_PASSWORD_GRANT')
  assert.equal(evidence.verification_boundary.real_http_jwt, true)
  assert.equal(evidence.verification_boundary.synthetic_identities, 5)
  assert.equal(evidence.verification_boundary.real_owner_invited, false)
  assert.equal(evidence.verification_boundary.credentials_or_jwt_recorded, false)
  assert.equal(evidence.case_count, 44)
  assert.equal(evidence.case_passed, 44)
  assert.equal(evidence.cases.length, 44)
  assert.equal(new Set(evidence.cases.map(({ name }) => name)).size, 44)
  assert.equal(evidence.cases.every(({ ok }) => ok === true), true)
  const concurrency = evidence.cases.filter(({ scope }) => scope === 'CONCURRENCY')
  assert.equal(concurrency.length, 3)
  assert.deepEqual(concurrency.at(-1).observed_statuses, [200, 409])
  assert.equal(evidence.assertions.empty_pattern_master_supported, true)
  assert.equal(evidence.assertions.pattern_quick_create_uses_master_source, true)
  assert.equal(evidence.assertions.created_pattern_auto_selectable, true)
  assert.equal(evidence.assertions.pattern_double_click_idempotent, true)
  assert.equal(evidence.assertions.concurrent_pattern_creation_one_winner, true)
  assert.equal(evidence.assertions.cutting_access_does_not_imply_pattern_manage, true)
  assert.equal(evidence.assertions.inactive_pattern_hidden_normally_and_visible_in_history_filter, true)
  assert.equal(evidence.coverage_boundaries.cutting_ui_final_save, 'SIMULATION_ONLY')
  assert.equal(evidence.coverage_boundaries.cutting_pattern_picker_and_quick_create, 'UAT_RPC_CONNECTED')
  for (const key of [
    'auth_users', 'auth_identities', 'auth_sessions', 'auth_refresh_tokens',
    'app_users', 'custom_roles', 'access_audit', 'patterns', 'pattern_audit',
    'idempotency_requests', 'wip_flags', 'temporary_http_extensions',
  ]) assert.equal(evidence.cleanup[key], 0, `Hosted cleanup residue: ${key}`)
  assert.equal(evidence.cleanup.temporary_credentials_retained, false)
  assert.equal(evidence.uat_post_cleanup.writer_sessions, 0)
  assert.equal(evidence.uat_post_cleanup.idle_in_transaction, 0)
  assert.equal(evidence.uat_post_cleanup.waiting_sessions, 0)
  assert.equal(evidence.uat_post_cleanup.write_capable_locks, 0)
  assert.equal(evidence.uat_post_cleanup.platform_cp45_ledger, 1)
  assert.equal(evidence.uat_post_cleanup.application_cp45_ledger, 1)
  assert.equal(evidence.uat_post_cleanup.platform_source_bytes, 98728)
  assert.equal(evidence.uat_post_cleanup.platform_source_sha256, '66175dcc5c73d2fb3bad493c1c6bd6a1ad14877251b0c690c0b642ae226c849a')
  assert.equal(evidence.uat_post_cleanup.rollback_capsule_rows, 3)
  assert.equal(evidence.uat_post_cleanup.rollback_capsule_valid, 3)
  assert.deepEqual(evidence.source_ci, candidate.ci_runtime)
  assert.equal(evidence.legacy_isolation.mutated, false)
  assert.equal(evidence.legacy_isolation.platform_cp45_ledger, 0)
  assert.equal(evidence.legacy_isolation.application_cp45_ledger, 0)
  assert.equal(evidence.legacy_isolation.cp4_cp45_objects, 0)
  assert.equal(evidence.production_go, false)
}

const fixedEntries = [
  ...ownershipV1.uat_recorded_sources,
  ...ownershipV1.recorded_migration_regressions,
  ...ownershipV1.uat_provenance,
]
const frozenFiles = {
  ...cp3Manifest.files,
  ...cp4Manifest.files,
  ...Object.fromEntries(fixedEntries.map((entry) => [entry.path, entry])),
}
assert.equal(Object.keys(frozenFiles).length, Object.keys(cp3Manifest.files).length + Object.keys(cp4Manifest.files).length + fixedEntries.length)
for (const [path, expected] of Object.entries(frozenFiles)) {
  const bytes = readFileSync(resolve(root, path))
  assert.equal(bytes.length, expected.bytes, `Frozen byte length drift: ${path}`)
  assert.equal(hash('sha256', bytes), expected.sha256, `Frozen SHA-256 drift: ${path}`)
  if (expected.ledger_version) {
    assert.ok(path.split('/').at(-1).startsWith(`${expected.ledger_version}_`), `Ledger filename mismatch: ${path}`)
    assert.equal(hash('md5', bytes), expected.md5, `Frozen UAT ledger byte mismatch: ${path}`)
  }
}

const candidatePaths = Object.keys(candidate.files).sort()
assert.equal(candidatePaths.length > 0, true, 'CP4.5 candidate manifest is empty')
assert.equal(new Set(candidatePaths).size, candidatePaths.length)
assert.equal(candidatePaths.some((path) => path.startsWith('supabase/.temp/')), false)
assert.equal(candidatePaths.includes(ownershipV2.candidate_cp45_manifest.path), false)
assert.equal(candidatePaths.includes(ownershipV2Path), false)
assert.deepEqual(candidatePaths.filter((path) => path in frozenFiles), [], 'CP4.5 manifest overlaps a frozen backend artifact')
for (const [path, expected] of Object.entries(candidate.files)) {
  const bytes = readFileSync(resolve(root, path))
  assert.equal(bytes.length, expected.bytes, `CP4.5 byte length drift: ${path}`)
  assert.equal(hash('sha256', bytes), expected.sha256, `CP4.5 SHA-256 drift: ${path}`)
}

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
  ...walk(resolve(root, 'scripts'), (path) => /^cp45_.*\.py$/.test(path.split('/').at(-1))),
  ...walk(resolve(root, 'scripts'), (path) => /^cp(?:4|45)_.*\.mjs$/.test(path.split('/').at(-1))),
  'scripts/check-backend-ownership.mjs',
  'scripts/check-backend-ownership-v2.mjs',
  '.github/workflows/cp3-r4-full-schema-validation.yml',
  '.github/workflows/cp4-full-schema-validation.yml',
  '.github/workflows/cp45-full-schema-validation.yml',
  'docs/evidence/cp4_hosted_uat_auth_e2e.json',
  ...(candidate.hosted_auth_permission_e2e.evidence_path ? [candidate.hosted_auth_permission_e2e.evidence_path] : []),
  ...(candidate.integrity_correction.hosted_auth_permission_e2e.evidence_path
    ? [candidate.integrity_correction.hosted_auth_permission_e2e.evidence_path]
    : []),
].sort()
const expectedFrozen = Object.keys(frozenFiles).sort()
const backendCandidate = candidatePaths.filter((path) => (
  path.startsWith('supabase/migrations/')
  || path.startsWith('supabase/rollbacks/')
  || path.startsWith('supabase/tests/')
  || path.startsWith('ops/supabase/')
  || /^scripts\/cp45_.*\.mjs$/.test(path)
  || /^scripts\/cp45_.*\.py$/.test(path)
  || path === 'scripts/check-backend-ownership-v2.mjs'
  || path === '.github/workflows/cp45-full-schema-validation.yml'
  || path === candidate.hosted_auth_permission_e2e.evidence_path
  || path === candidate.integrity_correction.hosted_auth_permission_e2e.evidence_path
)).sort()
const backendOwnedUnique = new Set([...expectedFrozen, ...backendCandidate])
assert.equal(
  backendOwnedUnique.size,
  expectedFrozen.length + backendCandidate.length,
  'Frozen and CP4.5 backend ownership sets overlap',
)
assert.deepEqual(discovered, [...expectedFrozen, ...backendCandidate].sort(), 'Backend source/proof file is unowned or stale')

assert.deepEqual(candidatePaths.filter((path) => path.startsWith('supabase/migrations/20260902104937_')), [
  'supabase/migrations/20260902104937_erp_v2_6_17_access_pattern_wip_control.sql',
])
assert.deepEqual(candidatePaths.filter((path) => path.startsWith('supabase/migrations/20260902180726_')), [
  'supabase/migrations/20260902180726_erp_v2_6_17a_cp45_pattern_assignment_immutability.sql',
])
assert.deepEqual(candidatePaths.filter((path) => path.startsWith('supabase/rollbacks/20260902104937_')), [
  'supabase/rollbacks/20260902104937_erp_v2_6_17_access_pattern_wip_control.rollback.sql',
])
assert.deepEqual(candidatePaths.filter((path) => path.startsWith('supabase/rollbacks/20260902180726_')), [
  'supabase/rollbacks/20260902180726_erp_v2_6_17a_cp45_pattern_assignment_immutability.rollback.sql',
])
assert.ok(candidatePaths.includes('supabase/tests/access_pattern_wip_control_rollback.sql'))
assert.ok(candidatePaths.includes('supabase/tests/cp45_pattern_assignment_immutability_rollback.sql'))
assert.ok(candidatePaths.includes('scripts/cp45_auth_permission_e2e.mjs'))
assert.ok(candidatePaths.includes('scripts/cp45_pattern_assignment_concurrency.py'))
assert.ok(candidatePaths.includes('.github/workflows/cp45-full-schema-validation.yml'))

const onlyCp3 = process.argv.includes('--cp3-only')
if (onlyCp3) {
  console.log(`Frozen CP3 backend passed: ${Object.keys(cp3Manifest.files).length} byte-bound files.`)
} else {
  console.log(`Backend ownership v2 passed: ${backendOwnedUnique.size} unique backend/proof files (${expectedFrozen.length} frozen + ${backendCandidate.length} CP4.5, overlap 0); CP4.5 manifest separately byte-binds ${candidatePaths.length} candidate files across all scopes; zero unowned backend artifacts.`)
}
