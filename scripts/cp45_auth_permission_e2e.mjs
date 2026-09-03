#!/usr/bin/env node

import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'

const baseUrl = (process.env.SUPABASE_URL || '').replace(/\/$/, '')
const browserKey = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_PUBLISHABLE_KEY || ''
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || ''
const pgurl = process.env.PGURL || ''
const reportPath = process.env.CP45_AUTH_REPORT || 'cp45-auth-permission-e2e.json'
const classification = process.env.CP45_PROOF_CLASSIFICATION || 'LOCAL_FULL_SCHEMA_AUTH_VERIFIED'

assert.ok(/^https?:\/\//.test(baseUrl), 'SUPABASE_URL is required')
assert.ok(browserKey.length > 20, 'SUPABASE browser key is required')
assert.ok(serviceKey.length > 20, 'SUPABASE_SERVICE_ROLE_KEY is required')
assert.ok(pgurl.startsWith('postgresql://'), 'PGURL is required')
assert.ok([
  'LOCAL_FULL_SCHEMA_AUTH_VERIFIED',
  'MANUAL_HOSTED_UAT_VERIFIED',
  'HOSTED_CI_VERIFIED',
].includes(classification), 'Unsupported CP45 proof classification')

const runId = `${Date.now()}-${randomBytes(4).toString('hex')}`
const safeRunId = runId.replace(/[^a-zA-Z0-9-]/g, '')
const password = () => `Cp45!${randomBytes(24).toString('base64url')}9a`
const users = []
const sessions = []
const appUserIds = []
const roleIds = []
const patternIds = []
const requestIds = []
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
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim()
}

function quotedUuidList(values) {
  return values
    .filter((value) => /^[0-9a-f-]{36}$/i.test(value))
    .map((value) => `'${value}'::uuid`)
    .join(',')
}

async function createAuthUser(label) {
  const email = `cp45-${label}-${safeRunId}@example.invalid`
  const userPassword = password()
  const response = await request('/auth/v1/admin/users', {
    key: serviceKey,
    token: serviceKey,
    method: 'POST',
    body: {
      email,
      password: userPassword,
      email_confirm: true,
      user_metadata: { full_name: `CP45 ${safeRunId} ${label}` },
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
       select '${appId}'::uuid,'${authId}'::uuid,'CP45 ${safeRunId} owner','OWNER',id,true
       from erp.app_roles where role_code='OWNER';`)
  return appId
}

async function signIn(user) {
  const response = await request('/auth/v1/token?grant_type=password', {
    method: 'POST',
    body: { email: user.email, password: user.password },
  })
  record(`auth-signin-${user.label}`, response, [200])
  assert.ok(response.json?.access_token)
  assert.ok(response.json?.refresh_token)
  const session = { label: user.label, accessToken: response.json.access_token, refreshToken: response.json.refresh_token }
  sessions.push(session)
  return session
}

async function rpc(name, token, body = {}) {
  return request(`/rest/v1/rpc/${name}`, { token, method: 'POST', body })
}

async function saveRole(ownerToken, payload, expectedVersion = null, requestId = randomUUID()) {
  requestIds.push(requestId)
  const response = await rpc('erp_save_role_v1', ownerToken, {
    p_payload: payload,
    p_client_request_id: requestId,
    p_expected_version: expectedVersion,
  })
  record(`rpc-save-role-${payload.code || payload.id}`, response, [200])
  assert.match(response.json?.role_id || '', /^[0-9a-f-]{36}$/i)
  if (!roleIds.includes(response.json.role_id)) roleIds.push(response.json.role_id)
  return response.json
}

async function savePattern(ownerToken, payload, expectedVersion = null, requestId = randomUUID()) {
  requestIds.push(requestId)
  const response = await rpc('erp_save_pattern_v1', ownerToken, {
    p_payload: payload,
    p_client_request_id: requestId,
    p_expected_version: expectedVersion,
  })
  record(`rpc-save-pattern-${payload.code || payload.id}`, response, [200])
  assert.match(response.json?.pattern_id || '', /^[0-9a-f-]{36}$/i)
  if (!patternIds.includes(response.json.pattern_id)) patternIds.push(response.json.pattern_id)
  return response.json
}

async function mapUser(ownerToken, authUser, roleId, { active = true, label = authUser.label } = {}) {
  const requestId = randomUUID()
  requestIds.push(requestId)
  const response = await rpc('erp_save_app_user_v3', ownerToken, {
    p_payload: {
      auth_user_id: authUser.id,
      full_name: `CP45 ${safeRunId} ${label}`,
      role_id: roleId,
      is_active: active,
      change_reason: 'CP45 hosted Auth permission acceptance',
    },
    p_client_request_id: requestId,
    p_expected_version: null,
  })
  record(`rpc-map-user-${authUser.label}`, response, [200])
  assert.match(response.json?.app_user_id || '', /^[0-9a-f-]{36}$/i)
  appUserIds.push(response.json.app_user_id)
  return response.json
}

async function myAccess(session, expected) {
  const response = await rpc('erp_get_my_access_v1', session.accessToken)
  record(`rpc-my-access-${session.label}`, response, [200])
  assert.equal(response.json?.allowed, expected.allowed)
  if (expected.reason) assert.equal(response.json?.reason, expected.reason)
  if (expected.role) assert.equal(response.json?.profile?.role_code, expected.role)
  return response.json
}

async function globalLogout(session) {
  const response = await request('/auth/v1/logout?scope=global', {
    token: session.accessToken,
    method: 'POST',
  })
  record(`auth-global-logout-${session.label}`, response, [204])
}

function cleanupDatabase() {
  const appIds = quotedUuidList(appUserIds)
  const customRoles = quotedUuidList(roleIds)
  const patterns = quotedUuidList(patternIds)
  const requests = quotedUuidList(requestIds)
  const auditEntities = quotedUuidList([...new Set([...appUserIds, ...roleIds, ...patternIds])])
  if (!appIds && !customRoles && !patterns && !requests) return
  sql(`begin;
    set local erp.cp45_allow_synthetic_cleanup='on';
    ${appIds || auditEntities ? `delete from erp.audit_logs where ${appIds ? `changed_by in (${appIds})` : 'false'} or ${auditEntities ? `entity_id in (${auditEntities})` : 'false'};` : ''}
    ${patterns ? `delete from erp.production_pattern_audit where pattern_id in (${patterns}) or entity_id in (${patterns});` : ''}
    ${patterns ? `delete from erp.production_patterns where id in (${patterns});` : ''}
    ${appIds ? `delete from erp.app_access_audit where actor_app_user_id in (${appIds}) or (entity_type='USER_ACCESS' and entity_id in (${appIds}));` : ''}
    ${customRoles ? `delete from erp.app_access_audit where entity_type='ROLE' and entity_id in (${customRoles});` : ''}
    ${customRoles ? `delete from erp.app_role_permissions where role_id in (${customRoles});` : ''}
    ${customRoles ? `update erp.app_roles set created_by=null,updated_by=null where id in (${customRoles});` : ''}
    ${appIds ? `delete from erp.app_users where id in (${appIds});` : ''}
    ${customRoles ? `delete from erp.app_roles where id in (${customRoles});` : ''}
    ${requests ? `delete from erp.idempotency_requests where client_request_id in (${requests});` : ''}
    -- The first pass releases audit FKs; this pass removes delete tombstones.
    ${appIds || auditEntities ? `delete from erp.audit_logs where ${appIds ? `changed_by in (${appIds})` : 'false'} or ${auditEntities ? `entity_id in (${auditEntities})` : 'false'};` : ''}
    commit;`)
}

async function cleanupAuth() {
  for (const user of [...users].reverse()) {
    try {
      await request(`/auth/v1/admin/users/${user.id}`, {
        key: serviceKey,
        token: serviceKey,
        method: 'DELETE',
      })
    } catch {
      // The residue query below is authoritative.
    }
  }
}

let failure
try {
  const owner = await createAuthUser('owner')
  const custom = await createAuthUser('custom')
  const viewOnly = await createAuthUser('view-only')
  const inactive = await createAuthUser('inactive')
  const unmapped = await createAuthUser('unmapped')

  const ownerAppId = bootstrapOwner(owner.id)
  const ownerSession = await signIn(owner)
  const customSession = await signIn(custom)
  const viewSession = await signIn(viewOnly)
  const inactiveSession = await signIn(inactive)
  const unmappedSession = await signIn(unmapped)

  const ownerAccess = await myAccess(ownerSession, { allowed: true, role: 'OWNER' })
  assert.ok(ownerAccess.permissions.includes('settings.access.manage'))
  assert.ok(ownerAccess.permissions.includes('finance.payroll.pay'))

  const adminRead = await rpc('erp_get_access_admin_v1', ownerSession.accessToken)
  record('rpc-owner-access-admin', adminRead, [200])
  assert.ok(Array.isArray(adminRead.json?.permissions))

  const emptyPatterns = await rpc('erp_list_patterns_v1', ownerSession.accessToken, {
    p_status: 'ALL', p_query: null, p_limit: 100, p_offset: 0,
  })
  record('rpc-pattern-master-empty-start', emptyPatterns, [200])
  assert.equal(emptyPatterns.json?.total, 0)
  assert.deepEqual(emptyPatterns.json?.rows, [])

  const quickRequestId = randomUUID()
  const quickPayload = {
    code: `QK${safeRunId.replaceAll('-', '').slice(-8).toUpperCase()}`,
    revision: 'R1', name: `CP45 Quick ${safeRunId}`, sort_order: 100,
    change_reason: 'CP45 quick-create hosted acceptance',
  }
  const quickPattern = await savePattern(ownerSession.accessToken, quickPayload, null, quickRequestId)
  const quickReplay = await savePattern(ownerSession.accessToken, quickPayload, null, quickRequestId)
  assert.deepEqual(quickReplay, quickPattern)

  const racePayload = {
    code: `RC${safeRunId.replaceAll('-', '').slice(-8).toUpperCase()}`,
    revision: 'R1', name: `CP45 Race ${safeRunId}`, sort_order: 101,
    change_reason: 'CP45 concurrent pattern creation',
  }
  const raceRequestIds = [randomUUID(), randomUUID()]
  requestIds.push(...raceRequestIds)
  const raceResponses = await Promise.all(raceRequestIds.map((requestId) => rpc('erp_save_pattern_v1', ownerSession.accessToken, {
    p_payload: racePayload, p_client_request_id: requestId, p_expected_version: null,
  })))
  assert.deepEqual(raceResponses.map((response) => response.status).sort((a, b) => a - b), [200, 409])
  raceResponses.forEach((response, index) => cases.push({ name: `rpc-pattern-concurrent-create-${index + 1}`, status: response.status }))
  const raceWinner = raceResponses.find((response) => response.status === 200)
  const raceLoser = raceResponses.find((response) => response.status === 409)
  assert.match(raceWinner?.json?.pattern_id || '', /^[0-9a-f-]{36}$/i)
  patternIds.push(raceWinner.json.pattern_id)
  assert.match(raceLoser?.text || '', /PATTERN_CODE_REVISION|duplicate|unique/i)

  const roleSuffix = safeRunId.replaceAll('-', '').slice(-10).toUpperCase()
  const customRole = await saveRole(ownerSession.accessToken, {
    code: `CP45_C_${roleSuffix}`,
    name: `CP45 Custom ${safeRunId}`,
    description: `CP45 synthetic ${safeRunId}`,
    change_reason: 'CP45 hosted custom role',
    confirm_high_risk: true,
    permission_keys: [
      'production.cutting.view',
      'production.wip.view',
      'production.wip.adjust',
      'master.pattern.view',
      'warehouse.stock.view',
    ],
  })
  const viewRole = await saveRole(ownerSession.accessToken, {
    code: `CP45_V_${roleSuffix}`,
    name: `CP45 View ${safeRunId}`,
    description: `CP45 synthetic ${safeRunId}`,
    change_reason: 'CP45 hosted view-only role',
    permission_keys: ['production.wip.view', 'master.pattern.view'],
  })

  await mapUser(ownerSession.accessToken, custom, customRole.role_id)
  await mapUser(ownerSession.accessToken, viewOnly, viewRole.role_id)
  await mapUser(ownerSession.accessToken, inactive, ownerAccess.profile.role_id, { active: false })

  const customAccess = await myAccess(customSession, { allowed: true, role: customRole.role_code })
  assert.ok(customAccess.permissions.includes('production.cutting.view'))
  assert.ok(customAccess.permissions.includes('production.wip.view'))
  assert.ok(!customAccess.permissions.includes('master.pattern.manage'))
  const viewAccess = await myAccess(viewSession, { allowed: true, role: viewRole.role_code })
  assert.ok(viewAccess.permissions.every((key) => key.endsWith('.view')))
  await myAccess(inactiveSession, { allowed: false, reason: 'APP_USER_INACTIVE' })
  await myAccess(unmappedSession, { allowed: false, reason: 'APP_USER_NOT_FOUND' })

  const customWip = await rpc('erp_get_wip_control_v1', customSession.accessToken, {
    p_filter: 'ACTIVE', p_pattern_id: null, p_sort: 'PATTERN', p_query: null,
  })
  record('rpc-custom-wip-allowed', customWip, [200])
  assert.ok(Array.isArray(customWip.json?.rows))

  const cuttingPatternLookup = await rpc('erp_list_patterns_v1', customSession.accessToken, {
    p_status: 'ACTIVE', p_query: null, p_limit: 30, p_offset: 0,
  })
  record('rpc-cutting-user-pattern-lookup-allowed', cuttingPatternLookup, [200])
  assert.ok(Array.isArray(cuttingPatternLookup.json?.rows))

  const customPatternWrite = await rpc('erp_save_pattern_v1', customSession.accessToken, {
    p_payload: { code: 'DENIED', name: 'Denied', sort_order: 1, change_reason: 'must fail' },
    p_client_request_id: randomUUID(), p_expected_version: null,
  })
  record('rpc-custom-pattern-manage-denied', customPatternWrite, [400, 401, 403])
  assert.match(customPatternWrite.text, /PERMISSION_DENIED|master\.pattern\.manage/i)

  const viewMutation = await rpc('erp_set_wip_control_flag_v1', viewSession.accessToken, {
    p_payload: {
      cutting_group_id: randomUUID(), flag_type: 'OPERATOR_ACTION', status: 'OPEN',
      note: 'must fail before domain lookup', change_reason: 'must fail',
    },
    p_client_request_id: randomUUID(), p_expected_version: null,
  })
  record('rpc-view-only-mutation-denied', viewMutation, [400, 401, 403])
  assert.match(viewMutation.text, /PERMISSION_DENIED|production\.wip\.adjust/i)

  const anonymousAccess = await rpc('erp_get_my_access_v1', null)
  record('rpc-anonymous-denied', anonymousAccess, [401, 403, 404])

  const privateResolver = await rpc('has_permission', ownerSession.accessToken, { p_permission_key: 'dashboard.view' })
  record('private-permission-resolver-not-exposed', privateResolver, [404])
  const directRoleTable = await request('/rest/v1/app_roles?select=*', { token: ownerSession.accessToken })
  record('private-role-table-not-exposed', directRoleTable, [404])

  const revokedRole = await saveRole(ownerSession.accessToken, {
    id: customRole.role_id,
    code: customRole.role_code,
    name: customRole.role_name,
    description: `CP45 synthetic ${safeRunId} revoked`,
    change_reason: 'CP45 next-request revocation',
    permission_keys: ['master.pattern.view', 'warehouse.stock.view'],
  }, customRole.row_version)
  assert.ok(!revokedRole.permissions.includes('production.wip.view'))
  const revokedWip = await rpc('erp_get_wip_control_v1', customSession.accessToken, {
    p_filter: 'ACTIVE', p_pattern_id: null, p_sort: 'PATTERN', p_query: null,
  })
  record('rpc-revocation-next-request', revokedWip, [400, 401, 403])
  assert.match(revokedWip.text, /PERMISSION_DENIED|production\.wip\.view/i)

  const lastOwnerAttemptId = randomUUID()
  requestIds.push(lastOwnerAttemptId)
  const lastOwnerAttempt = await rpc('erp_save_app_user_v3', ownerSession.accessToken, {
    p_payload: {
      id: ownerAppId,
      full_name: `CP45 ${safeRunId} owner`,
      role_code: 'ADMIN',
      is_active: true,
      change_reason: 'must protect last owner',
    },
    p_client_request_id: lastOwnerAttemptId,
    p_expected_version: ownerAccess.profile.row_version,
  })
  record('rpc-last-owner-protected', lastOwnerAttempt, [400, 401, 403])
  assert.match(lastOwnerAttempt.text, /LAST_ACTIVE_OWNER_PROTECTED/i)

  const lastOwnerAuthDelete = await request(`/auth/v1/admin/users/${owner.id}`, {
    key: serviceKey,
    token: serviceKey,
    method: 'DELETE',
  })
  record('auth-last-owner-delete-protected', lastOwnerAuthDelete, [400, 403, 409, 422, 500])
  await myAccess(ownerSession, { allowed: true, role: 'OWNER' })

  const refresh = await request('/auth/v1/token?grant_type=refresh_token', {
    method: 'POST',
    body: { refresh_token: ownerSession.refreshToken },
  })
  record('auth-refresh-rotation', refresh, [200])
  assert.ok(refresh.json?.access_token)
  assert.ok(refresh.json?.refresh_token)
  ownerSession.accessToken = refresh.json.access_token
  ownerSession.refreshToken = refresh.json.refresh_token

  for (const session of sessions) await globalLogout(session)
  const refreshAfterLogout = await request('/auth/v1/token?grant_type=refresh_token', {
    method: 'POST',
    body: { refresh_token: ownerSession.refreshToken },
  })
  record('auth-refresh-after-global-logout-denied', refreshAfterLogout, [400, 401])
} catch (error) {
  failure = error
} finally {
  try { cleanupDatabase() } catch (error) { failure ||= error }
  try { await cleanupAuth() } catch (error) { failure ||= error }
}

let residue
try {
  residue = JSON.parse(sql(`select jsonb_build_object(
    'auth_users',(select count(*) from auth.users),
    'auth_identities',(select count(*) from auth.identities),
    'auth_sessions',(select count(*) from auth.sessions),
    'auth_refresh_tokens',(select count(*) from auth.refresh_tokens),
    'app_users',(select count(*) from erp.app_users),
    'audit_logs',(select count(*) from erp.audit_logs),
    'custom_roles',(select count(*) from erp.app_roles where description like 'CP45 synthetic ${safeRunId}%'),
    'access_audit',(select count(*) from erp.app_access_audit),
    'patterns',(select count(*) from erp.production_patterns),
    'pattern_audit',(select count(*) from erp.production_pattern_audit)
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
  run_label: `cp45-${safeRunId}`,
  cases,
  residue,
  secrets_persisted: false,
  real_owner_invited: false,
  production_go: false,
  tested: {
    owner_full_bundle: true,
    custom_multi_module: true,
    view_only: true,
    inactive_and_unmapped: true,
    anonymous: true,
    allowed_and_denied_rpc: true,
    direct_bypass: true,
    empty_pattern_master: true,
    pattern_quick_create_idempotency: true,
    concurrent_pattern_creation: true,
    cutting_view_without_pattern_manage: true,
    next_request_revocation: true,
    last_owner: true,
    refresh_rotation: true,
    global_logout: true,
    refresh_after_logout: true,
    synthetic_cleanup: true,
  },
  ...(failure ? { failure: failure instanceof Error ? failure.message : String(failure) } : {}),
}

writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`)

if (report.status !== 'PASS') {
  throw failure || new Error(`CP4.5 Auth/permission cleanup residue: ${JSON.stringify(residue)}`)
}

console.log(`CP4.5 Auth/permission E2E passed: ${cases.length} HTTP/JWT assertions; zero synthetic residue.`)
