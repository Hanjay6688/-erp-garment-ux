#!/usr/bin/env node

import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'

const baseUrl = (process.env.SUPABASE_URL || '').replace(/\/$/, '')
const browserKey = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_PUBLISHABLE_KEY || ''
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || ''
const pgurl = process.env.PGURL || ''
const reportPath = process.env.CP5_AUTH_REPORT || 'cp5-auth-permission-e2e.json'
const classification = process.env.CP5_PROOF_CLASSIFICATION || 'LOCAL_FULL_SCHEMA_AUTH_VERIFIED'
const uatHost = 'siimvrusnzxexizpyoib.supabase.co'
const legacyHost = 'vlxdhpkjeevubjxexnfo.supabase.co'

assert.ok(/^https?:\/\//.test(baseUrl), 'SUPABASE_URL is required')
assert.ok(browserKey.length > 20, 'Supabase browser key is required')
assert.ok(serviceKey.length > 20, 'SUPABASE_SERVICE_ROLE_KEY is required')
assert.ok(pgurl.startsWith('postgresql://'), 'PGURL is required')
assert.ok([
  'LOCAL_FULL_SCHEMA_AUTH_VERIFIED',
  'MANUAL_HOSTED_UAT_VERIFIED',
  'HOSTED_CI_VERIFIED',
].includes(classification), 'Unsupported CP5 proof classification')

const target = new URL(baseUrl)
assert.notEqual(target.hostname, legacyHost, 'Legacy ERP-Garment project is forbidden')
if (classification !== 'LOCAL_FULL_SCHEMA_AUTH_VERIFIED') {
  assert.equal(target.protocol, 'https:', 'Hosted proof requires HTTPS')
  assert.equal(target.hostname, uatHost, 'Hosted proof must target ERP Enteng UAT')
}

const runId = `${Date.now()}-${randomBytes(4).toString('hex')}`
const safeRunId = runId.replace(/[^a-zA-Z0-9-]/g, '')
const password = () => `Cp5!${randomBytes(24).toString('base64url')}9a`
const users = []
const sessions = []
const appUserIds = []
const roleIds = []
const requestIds = []
const bsCaseIds = []
const resolutionIds = []
const cases = []

async function request(path, { key = browserKey, token, method = 'GET', body } = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      apikey: key,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const text = await response.text()
  let json = null
  try { json = text ? JSON.parse(text) : null } catch { json = null }
  return { status: response.status, text, json }
}

function record(name, response, expectedStatuses) {
  assert.ok(expectedStatuses.includes(response.status), `${name}: HTTP ${response.status}: ${response.text}`)
  cases.push({ name, status: response.status })
}

function sql(statement) {
  return execFileSync('psql', [pgurl, '-X', '-qAt', '-v', 'ON_ERROR_STOP=1', '-c', statement], {
    encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
  }).trim()
}

function quotedUuidList(values) {
  return values
    .filter((value) => /^[0-9a-f-]{36}$/i.test(value))
    .map((value) => `'${value}'::uuid`)
    .join(',')
}

function uuidCondition(column, values) {
  const list = quotedUuidList(values)
  return list ? `${column} in (${list})` : 'false'
}

async function createAuthUser(label) {
  const email = `cp5-${label}-${safeRunId}@example.invalid`
  const userPassword = password()
  const response = await request('/auth/v1/admin/users', {
    key: serviceKey, token: serviceKey, method: 'POST',
    body: {
      email, password: userPassword, email_confirm: true,
      user_metadata: { full_name: `CP5 ${safeRunId} ${label}` },
    },
  })
  record(`auth-admin-create-${label}`, response, [200])
  assert.match(response.json?.id || '', /^[0-9a-f-]{36}$/i)
  const user = { id: response.json.id, email, password: userPassword, label }
  users.push(user)
  return user
}

function bootstrapOwner(authId) {
  const appId = randomUUID()
  appUserIds.push(appId)
  sql(`insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
       select '${appId}'::uuid,'${authId}'::uuid,'CP5 ${safeRunId} owner','OWNER',id,true
       from erp.app_roles where role_code='OWNER';`)
  return appId
}

async function signIn(user) {
  const response = await request('/auth/v1/token?grant_type=password', {
    method: 'POST', body: { email: user.email, password: user.password },
  })
  record(`auth-signin-${user.label}`, response, [200])
  assert.ok(response.json?.access_token)
  assert.ok(response.json?.refresh_token)
  const session = {
    label: user.label,
    accessToken: response.json.access_token,
    refreshToken: response.json.refresh_token,
  }
  sessions.push(session)
  return session
}

async function rpc(name, token, body = {}) {
  return request(`/rest/v1/rpc/${name}`, { token, method: 'POST', body })
}

async function myAccess(session, expected) {
  const response = await rpc('erp_get_my_access_v1', session.accessToken)
  record(`rpc-my-access-${session.label}`, response, [200])
  assert.equal(response.json?.allowed, expected.allowed)
  if (expected.reason) assert.equal(response.json?.reason, expected.reason)
  if (expected.role) assert.equal(response.json?.profile?.role_code, expected.role)
  return response.json
}

async function createViewerRole(ownerToken) {
  const requestId = randomUUID()
  requestIds.push(requestId)
  const suffix = safeRunId.replaceAll('-', '').slice(-10).toUpperCase()
  const response = await rpc('erp_save_role_v1', ownerToken, {
    p_payload: {
      code: `CP5_V_${suffix}`, name: `CP5 Viewer ${safeRunId}`,
      description: `CP5 synthetic ${safeRunId}`,
      permission_keys: ['production.bs_rework.view', 'master.pattern.view'],
      change_reason: `CP5 ${safeRunId} view-only role`,
    },
    p_client_request_id: requestId, p_expected_version: null,
  })
  record('rpc-create-viewer-role', response, [200])
  assert.match(response.json?.role_id || '', /^[0-9a-f-]{36}$/i)
  roleIds.push(response.json.role_id)
  return response.json.role_id
}

async function mapUser(ownerToken, authUser, roleId) {
  const requestId = randomUUID()
  requestIds.push(requestId)
  const response = await rpc('erp_save_app_user_v3', ownerToken, {
    p_payload: {
      auth_user_id: authUser.id, full_name: `CP5 ${safeRunId} ${authUser.label}`,
      role_id: roleId, is_active: true,
      change_reason: `CP5 ${safeRunId} Auth mapping`,
    },
    p_client_request_id: requestId, p_expected_version: null,
  })
  record(`rpc-map-user-${authUser.label}`, response, [200])
  assert.match(response.json?.app_user_id || '', /^[0-9a-f-]{36}$/i)
  appUserIds.push(response.json.app_user_id)
  return response.json.app_user_id
}

async function saveAction(token, action, payload, expectedVersion, requestId = randomUUID(), expectedStatuses = [200]) {
  requestIds.push(requestId)
  const response = await rpc('erp_save_bs_resolution_action_v1', token, {
    p_action: action, p_payload: payload,
    p_client_request_id: requestId, p_expected_version: expectedVersion,
  })
  record(`rpc-cp5-${action.toLowerCase()}`, response, expectedStatuses)
  return response
}

function cleanupDatabase() {
  const apps = quotedUuidList(appUserIds)
  const roles = quotedUuidList(roleIds)
  const requests = quotedUuidList(requestIds)
  const bsCases = quotedUuidList(bsCaseIds)
  const resolutions = quotedUuidList(resolutionIds)
  sql(`begin;
    set local erp.cp45_allow_synthetic_cleanup='on';
    ${bsCases ? `delete from erp.rework_component_lines where rework_order_id in(select id from erp.rework_orders where bs_case_id in(${bsCases}));` : ''}
    ${bsCases ? `delete from erp.rework_orders where bs_case_id in(${bsCases});` : ''}
    ${resolutions || bsCases ? `delete from erp.bs_resolutions where ${resolutions ? `id in(${resolutions})` : 'false'} or ${bsCases ? `bs_case_id in(${bsCases})` : 'false'};` : ''}
    ${bsCases ? `delete from erp.bs_case_components where bs_case_id in(${bsCases});` : ''}
    ${bsCases ? `delete from erp.bs_cases where id in(${bsCases});` : ''}
    delete from erp.audit_logs
      where ${apps ? `changed_by in(${apps})` : 'false'}
         or ${bsCases ? `entity_id in(${bsCases})` : 'false'}
         or ${resolutions ? `entity_id in(${resolutions})` : 'false'}
         or change_reason like 'CP5 ${safeRunId}%';
    ${apps ? `delete from erp.app_access_audit where actor_app_user_id in(${apps}) or (entity_type='USER_ACCESS' and entity_id in(${apps}));` : ''}
    ${roles ? `delete from erp.app_access_audit where entity_type='ROLE' and entity_id in(${roles});` : ''}
    ${roles ? `delete from erp.app_role_permissions where role_id in(${roles});` : ''}
    ${roles ? `update erp.app_roles set created_by=null,updated_by=null where id in(${roles});` : ''}
    ${apps ? `delete from erp.app_users where id in(${apps});` : ''}
    ${roles ? `delete from erp.app_roles where id in(${roles});` : ''}
    ${requests ? `delete from erp.idempotency_requests where client_request_id in(${requests});` : ''}
    commit;`)
}

async function cleanupAuth() {
  for (const user of [...users].reverse()) {
    try {
      await request(`/auth/v1/admin/users/${user.id}`, {
        key: serviceKey, token: serviceKey, method: 'DELETE',
      })
    } catch {
      // Targeted residue checks below are authoritative.
    }
  }
}

let failure
try {
  const owner = await createAuthUser('owner')
  const operator = await createAuthUser('operator')
  const viewer = await createAuthUser('viewer')
  const unmapped = await createAuthUser('unmapped')

  bootstrapOwner(owner.id)
  const ownerSession = await signIn(owner)
  const ownerAccess = await myAccess(ownerSession, { allowed: true, role: 'OWNER' })
  assert.ok(ownerAccess.permissions.includes('production.bs_rework.reverse'))

  const viewerRoleId = await createViewerRole(ownerSession.accessToken)
  const productionRoleId = sql("select id from erp.app_roles where role_code='PRODUKSI_QC'")
  assert.match(productionRoleId, /^[0-9a-f-]{36}$/i)
  await mapUser(ownerSession.accessToken, operator, productionRoleId)
  await mapUser(ownerSession.accessToken, viewer, viewerRoleId)

  const operatorSession = await signIn(operator)
  const viewerSession = await signIn(viewer)
  const unmappedSession = await signIn(unmapped)
  const operatorAccess = await myAccess(operatorSession, { allowed: true, role: 'PRODUKSI_QC' })
  const viewerAccess = await myAccess(viewerSession, { allowed: true })
  await myAccess(unmappedSession, { allowed: false, reason: 'APP_USER_NOT_FOUND' })
  assert.ok(operatorAccess.permissions.includes('production.bs_rework.post'))
  assert.ok(!operatorAccess.permissions.includes('production.bs_rework.reverse'))
  assert.deepEqual([...viewerAccess.permissions].sort(), ['master.pattern.view', 'production.bs_rework.view'].sort())

  const anonymousRead = await rpc('erp_get_bs_resolution_workspace_v1', null, {
    p_filter: 'ACTIVE', p_kind: 'ALL', p_pattern_id: null, p_query: null, p_limit: 50, p_offset: 0,
  })
  record('rpc-anonymous-workspace-denied', anonymousRead, [401, 403, 404])

  const unmappedRead = await rpc('erp_get_bs_resolution_workspace_v1', unmappedSession.accessToken, {
    p_filter: 'ACTIVE', p_kind: 'ALL', p_pattern_id: null, p_query: null, p_limit: 50, p_offset: 0,
  })
  record('rpc-unmapped-workspace-denied', unmappedRead, [400, 401, 403])

  const directTable = await request('/rest/v1/bs_cases?select=id', { token: operatorSession.accessToken })
  record('rest-direct-bs-table-denied', directTable, [401, 403, 404])
  const privateFunction = await rpc('create_manual_bs_case_v2', operatorSession.accessToken, {})
  record('rpc-private-writer-denied', privateFunction, [401, 403, 404])

  const legacyReference = `CP5-${safeRunId}`
  const createRequestId = randomUUID()
  const manualPayload = {
    untracked_type: 'LEGACY', legacy_reference: legacyReference, qty_pcs: 2,
    physical_at: new Date().toISOString(),
    change_reason: `CP5 ${safeRunId} physical reconciliation`,
    notes: `CP5 ${safeRunId} real Auth/JWT fixture`, components: [],
  }
  const created = await saveAction(operatorSession.accessToken, 'CREATE_MANUAL_BS', manualPayload, null, createRequestId)
  const replay = await saveAction(operatorSession.accessToken, 'CREATE_MANUAL_BS', manualPayload, null, createRequestId)
  assert.deepEqual(replay.json, created.json)
  const bsCaseId = created.json?.result?.bs_case_id
  assert.match(bsCaseId || '', /^[0-9a-f-]{36}$/i)
  bsCaseIds.push(bsCaseId)
  let bsVersion = created.json.result.row_version

  const conflictingReplay = await saveAction(
    operatorSession.accessToken, 'CREATE_MANUAL_BS', { ...manualPayload, qty_pcs: 3 },
    null, createRequestId, [400, 409],
  )
  assert.match(conflictingReplay.text, /different payload/i)

  const viewerRead = await rpc('erp_get_bs_resolution_workspace_v1', viewerSession.accessToken, {
    p_filter: 'ACTIVE', p_kind: 'BS', p_pattern_id: null,
    p_query: legacyReference, p_limit: 50, p_offset: 0,
  })
  record('rpc-viewer-workspace-allowed', viewerRead, [200])
  assert.equal(viewerRead.json?.total, 1)
  assert.equal(viewerRead.json?.rows?.[0]?.id, bsCaseId)

  const wrongPattern = await rpc('erp_get_bs_resolution_workspace_v1', operatorSession.accessToken, {
    p_filter: 'ALL', p_kind: 'ALL',
    p_pattern_id: 'c6b00000-0000-4000-8000-000000000099',
    p_query: legacyReference, p_limit: 50, p_offset: 0,
  })
  record('rpc-server-pattern-filter-empty', wrongPattern, [200])
  assert.equal(wrongPattern.json?.total, 0)
  assert.deepEqual(wrongPattern.json?.rows, [])

  const viewerRequestId = randomUUID()
  const viewerMutation = await saveAction(viewerSession.accessToken, 'DISPOSE_BS', {
    bs_case_id: bsCaseId, resolution_type: 'SCRAP', qty_pcs: 1,
    compensation_amount: 0, source_laundry_claim_id: null,
    physical_at: new Date().toISOString(), change_reason: `CP5 ${safeRunId} viewer must fail`,
  }, bsVersion, viewerRequestId, [400, 401, 403])
  assert.match(viewerMutation.text, /PERMISSION_DENIED|production\.bs_rework\.post/i)

  const disposition = await saveAction(operatorSession.accessToken, 'DISPOSE_BS', {
    bs_case_id: bsCaseId, resolution_type: 'SCRAP', qty_pcs: 1,
    compensation_amount: 0, source_laundry_claim_id: null,
    physical_at: new Date().toISOString(), change_reason: `CP5 ${safeRunId} one-piece disposition`,
  }, bsVersion)
  assert.equal(disposition.json?.result?.status, 'PARTIAL')
  const resolutionId = disposition.json?.result?.bs_resolution_id
  assert.match(resolutionId || '', /^[0-9a-f-]{36}$/i)
  resolutionIds.push(resolutionId)
  const disposedVersion = disposition.json.result.row_version

  const operatorReverse = await saveAction(operatorSession.accessToken, 'REVERSE_DISPOSITION', {
    resolution_id: resolutionId, change_reason: `CP5 ${safeRunId} operator reverse must fail`,
  }, disposedVersion, randomUUID(), [400, 401, 403])
  assert.match(operatorReverse.text, /PERMISSION_DENIED|production\.bs_rework\.reverse/i)

  const staleReverse = await saveAction(ownerSession.accessToken, 'REVERSE_DISPOSITION', {
    resolution_id: resolutionId, change_reason: `CP5 ${safeRunId} stale owner reverse`,
  }, bsVersion, randomUUID(), [400, 409])
  assert.match(staleReverse.text, /STALE_VERSION/i)

  const reversed = await saveAction(ownerSession.accessToken, 'REVERSE_DISPOSITION', {
    resolution_id: resolutionId, change_reason: `CP5 ${safeRunId} owner reversal`,
  }, disposedVersion)
  assert.equal(reversed.json?.result?.status, 'REVERSED')
  assert.equal(reversed.json?.result?.bs_case_status, 'OPEN')
  bsVersion = reversed.json.result.row_version
  assert.ok(bsVersion > disposedVersion)

  const finalRead = await rpc('erp_get_bs_resolution_workspace_v1', operatorSession.accessToken, {
    p_filter: 'ACTIVE', p_kind: 'BS', p_pattern_id: null,
    p_query: legacyReference, p_limit: 50, p_offset: 0,
  })
  record('rpc-final-refetch-authoritative', finalRead, [200])
  assert.equal(finalRead.json?.rows?.[0]?.status, 'OPEN')
  assert.equal(finalRead.json?.rows?.[0]?.resolved_qty, 0)
  assert.equal(finalRead.json?.rows?.[0]?.row_version, bsVersion)
  assert.equal(sql('select count(*) from erp.bs_resolution_execution_context'), '0')
} catch (error) {
  failure = error
} finally {
  try { cleanupDatabase() } catch (error) { failure ||= error }
  try { await cleanupAuth() } catch (error) { failure ||= error }
}

let residue
try {
  residue = JSON.parse(sql(`select jsonb_build_object(
    'auth_users',(select count(*) from auth.users where ${uuidCondition('id', users.map((user) => user.id))}),
    'auth_identities',(select count(*) from auth.identities where ${uuidCondition('user_id', users.map((user) => user.id))}),
    'auth_sessions',(select count(*) from auth.sessions where ${uuidCondition('user_id', users.map((user) => user.id))}),
    'auth_refresh_tokens',(select count(*) from auth.refresh_tokens where ${uuidCondition('user_id', users.map((user) => user.id))}),
    'app_users',(select count(*) from erp.app_users where ${uuidCondition('id', appUserIds)}),
    'custom_roles',(select count(*) from erp.app_roles where ${uuidCondition('id', roleIds)}),
    'bs_cases',(select count(*) from erp.bs_cases where ${uuidCondition('id', bsCaseIds)}),
    'bs_resolutions',(select count(*) from erp.bs_resolutions where ${uuidCondition('id', resolutionIds)} or ${uuidCondition('bs_case_id', bsCaseIds)}),
    'bs_components',(select count(*) from erp.bs_case_components where ${uuidCondition('bs_case_id', bsCaseIds)}),
    'rework_orders',(select count(*) from erp.rework_orders where ${uuidCondition('bs_case_id', bsCaseIds)}),
    'rework_components',(select count(*) from erp.rework_component_lines where rework_order_id in(
      select id from erp.rework_orders where ${uuidCondition('bs_case_id', bsCaseIds)}
    )),
    'hold_events',(select count(*) from erp.bs_case_hold_events where ${uuidCondition('bs_case_id', bsCaseIds)}),
    'audit_logs',(select count(*) from erp.audit_logs
      where ${uuidCondition('changed_by', appUserIds)}
         or ${uuidCondition('entity_id', bsCaseIds)}
         or ${uuidCondition('entity_id', resolutionIds)}
         or change_reason like 'CP5 ${safeRunId}%'),
    'access_audit',(select count(*) from erp.app_access_audit
      where ${uuidCondition('actor_app_user_id', appUserIds)}
         or ${uuidCondition('entity_id', appUserIds)}
         or ${uuidCondition('entity_id', roleIds)}),
    'role_permissions',(select count(*) from erp.app_role_permissions where ${uuidCondition('role_id', roleIds)}),
    'idempotency',(select count(*) from erp.idempotency_requests where ${uuidCondition('client_request_id', requestIds)}),
    'execution_context',(select count(*) from erp.bs_resolution_execution_context)
  );`))
} catch (error) {
  failure ||= error
  residue = { residue_query_failed: true }
}

const residueClean = Object.values(residue).every((value) => value === 0)
const report = {
  status: failure || !residueClean ? 'FAIL' : 'PASS',
  classification,
  classified_as_ci: classification === 'HOSTED_CI_VERIFIED',
  target: classification === 'LOCAL_FULL_SCHEMA_AUTH_VERIFIED' ? 'DISPOSABLE_LOCAL_SUPABASE' : uatHost,
  cases,
  residue,
  secrets_persisted: false,
  real_owner_invited: false,
  production_go: false,
  tested: {
    real_auth_password_sessions: true,
    access_profile_owner_operator_viewer_unmapped: true,
    anonymous_and_unmapped_denial: true,
    view_only_read_and_mutation_denial: true,
    private_table_and_writer_denial: true,
    manual_bs_idempotency_and_conflict: true,
    server_side_pattern_empty_state: true,
    operator_disposition_and_reverse_denial: true,
    owner_stale_rejection_and_reversal: true,
    authoritative_refetch: true,
    synthetic_identity_session_token_and_business_cleanup: true,
  },
  ...(failure ? { failure: failure instanceof Error ? failure.message : String(failure) } : {}),
}

writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`)
if (report.status !== 'PASS') {
  throw failure || new Error(`CP5 Auth/JWT cleanup residue: ${JSON.stringify(residue)}`)
}

console.log(`CP5 Auth/JWT E2E passed: ${cases.length} HTTP assertions; zero targeted synthetic residue.`)
