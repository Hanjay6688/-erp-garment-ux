#!/usr/bin/env node

import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'

const baseUrl = (process.env.SUPABASE_URL || '').replace(/\/$/, '')
const browserKey = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_PUBLISHABLE_KEY || ''
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || ''
const pgurl = process.env.PGURL || ''
const reportPath = process.env.CP6_AUTH_REPORT || 'cp6-auth-permission-e2e.json'

assert.ok(/^https?:\/\//.test(baseUrl), 'SUPABASE_URL is required')
assert.ok(browserKey.length > 20, 'Supabase browser/publishable key is required')
assert.ok(serviceKey.length > 20, 'SUPABASE_SERVICE_ROLE_KEY is required')
assert.ok(pgurl.startsWith('postgresql://'), 'PGURL is required')
assert.notEqual(new URL(baseUrl).hostname, 'vlxdhpkjeevubjxexnfo.supabase.co', 'Legacy is read-only forever')

const runId = `${Date.now()}-${randomBytes(4).toString('hex')}`
const safeRunId = runId.replace(/[^a-zA-Z0-9-]/g, '')
const users = []
const appUserIds = []
const roleIds = []
const requestIds = []
const cases = []

function sql(statement) {
  return execFileSync('psql', [pgurl, '-X', '-qAt', '-v', 'ON_ERROR_STOP=1', '-c', statement], {
    encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
  }).trim()
}

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

function textUuidCondition(column, values) {
  const list = values
    .filter((value) => /^[0-9a-f-]{36}$/i.test(value))
    .map((value) => `'${value}'`)
    .join(',')
  return list ? `${column}::text in (${list})` : 'false'
}

async function createAuthUser(label) {
  const email = `cp6-${label}-${safeRunId}@example.invalid`
  const password = `Cp6!${randomBytes(24).toString('base64url')}9a`
  const response = await request('/auth/v1/admin/users', {
    key: serviceKey,
    token: serviceKey,
    method: 'POST',
    body: {
      email, password, email_confirm: true,
      user_metadata: { full_name: `CP6 ${safeRunId} ${label}` },
    },
  })
  record(`auth-admin-create-${label}`, response, [200])
  assert.match(response.json?.id || '', /^[0-9a-f-]{36}$/i)
  const user = { id: response.json.id, email, password, label }
  users.push(user)
  return user
}

async function signIn(user) {
  const response = await request('/auth/v1/token?grant_type=password', {
    method: 'POST', body: { email: user.email, password: user.password },
  })
  record(`auth-signin-${user.label}`, response, [200])
  assert.ok(response.json?.access_token)
  return { label: user.label, accessToken: response.json.access_token }
}

async function rpc(name, token, body = {}) {
  return request(`/rest/v1/rpc/${name}`, { token, method: 'POST', body })
}

function bootstrapOwner(authId) {
  const appId = randomUUID()
  appUserIds.push(appId)
  sql(`insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
       select '${appId}'::uuid,'${authId}'::uuid,'CP6 ${safeRunId} owner','OWNER',id,true
       from erp.app_roles where role_code='OWNER';`)
}

async function createRole(ownerToken, label, permissionKeys) {
  const requestId = randomUUID()
  requestIds.push(requestId)
  // Keep the semantic label outside the truncated run suffix. Putting the
  // label before `.slice(-12)` made viewer/operator collapse to the same code.
  const suffix = safeRunId.replace(/[^a-zA-Z0-9]/g, '').slice(-12).toUpperCase()
  const roleCode = `CP6_${label.toUpperCase()}_${suffix}`
  assert.match(roleCode, /^[A-Z][A-Z0-9_]{1,31}$/)
  const response = await rpc('erp_save_role_v1', ownerToken, {
    p_payload: {
      code: roleCode,
      name: `CP6 ${label} ${safeRunId}`,
      description: `CP6 real JWT ${label}`,
      permission_keys: permissionKeys,
      // Posting/creating production facts is intentionally high-risk. This
      // mirrors the explicit Access Control UX acknowledgement; omitting it
      // must remain a backend rejection, not a test bypass.
      confirm_high_risk: true,
      change_reason: `CP6 ${safeRunId} create ${label} role`,
    },
    p_client_request_id: requestId,
    p_expected_version: null,
  })
  record(`rpc-create-${label}-role`, response, [200])
  assert.match(response.json?.role_id || '', /^[0-9a-f-]{36}$/i)
  roleIds.push(response.json.role_id)
  return response.json.role_id
}

async function mapUser(ownerToken, authUser, roleId) {
  const requestId = randomUUID()
  requestIds.push(requestId)
  const response = await rpc('erp_save_app_user_v3', ownerToken, {
    p_payload: {
      auth_user_id: authUser.id,
      full_name: `CP6 ${safeRunId} ${authUser.label}`,
      role_id: roleId,
      is_active: true,
      change_reason: `CP6 ${safeRunId} map ${authUser.label}`,
    },
    p_client_request_id: requestId,
    p_expected_version: null,
  })
  record(`rpc-map-${authUser.label}`, response, [200])
  assert.match(response.json?.app_user_id || '', /^[0-9a-f-]{36}$/i)
  appUserIds.push(response.json.app_user_id)
  return response.json.app_user_id
}

async function myAccess(session, expectedAllowed, expectedReason) {
  const response = await rpc('erp_get_my_access_v1', session.accessToken)
  record(`rpc-my-access-${session.label}`, response, [200])
  assert.equal(response.json?.allowed, expectedAllowed)
  if (expectedReason) assert.equal(response.json?.reason, expectedReason)
  return response.json
}

async function workspace(session, scope, expectedStatuses = [200]) {
  const response = await rpc('erp_get_laundry_qc_workspace_v1', session?.accessToken, {
    p_scope: scope, p_query: null,
  })
  record(`rpc-${session?.label || 'anonymous'}-${scope.toLowerCase()}-workspace`, response, expectedStatuses)
  return response
}

function cleanupDatabase() {
  const apps = quotedUuidList(appUserIds)
  const roles = quotedUuidList(roleIds)
  const requests = quotedUuidList(requestIds)
  sql(`begin;
    set local erp.cp45_allow_synthetic_cleanup='on';
    delete from erp.audit_logs
      where ${apps ? `changed_by in(${apps})` : 'false'}
         or change_reason like 'CP6 ${safeRunId}%';
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
      // The catalog residue query below is authoritative.
    }
  }
}

let failure
try {
  const owner = await createAuthUser('owner')
  const operator = await createAuthUser('operator')
  const viewer = await createAuthUser('viewer')
  const inactive = await createAuthUser('inactive')
  const unmapped = await createAuthUser('unmapped')

  bootstrapOwner(owner.id)
  const ownerSession = await signIn(owner)
  await myAccess(ownerSession, true)

  const viewerRoleId = await createRole(ownerSession.accessToken, 'viewer', [
    'production.laundry.view', 'production.final_sku.view',
  ])
  const operatorRoleId = await createRole(ownerSession.accessToken, 'operator', [
    'production.laundry.view', 'production.laundry.create', 'production.laundry.post',
    'production.final_sku.view', 'production.final_sku.post',
  ])
  await mapUser(ownerSession.accessToken, operator, operatorRoleId)
  await mapUser(ownerSession.accessToken, viewer, viewerRoleId)
  const inactiveAppId = await mapUser(ownerSession.accessToken, inactive, viewerRoleId)
  sql(`begin; set local app.change_reason='CP6 ${safeRunId} inactive actor proof';
       update erp.app_users set is_active=false where id='${inactiveAppId}'::uuid; commit;`)

  const operatorSession = await signIn(operator)
  const viewerSession = await signIn(viewer)
  const inactiveSession = await signIn(inactive)
  const unmappedSession = await signIn(unmapped)
  const operatorAccess = await myAccess(operatorSession, true)
  const viewerAccess = await myAccess(viewerSession, true)
  await myAccess(inactiveSession, false, 'APP_USER_INACTIVE')
  await myAccess(unmappedSession, false, 'APP_USER_NOT_FOUND')
  assert.ok(operatorAccess.permissions.includes('production.laundry.post'))
  assert.ok(operatorAccess.permissions.includes('production.final_sku.post'))
  assert.deepEqual(
    [...viewerAccess.permissions].sort(),
    ['production.final_sku.view', 'production.laundry.view'].sort(),
  )

  await workspace(null, 'LAUNDRY', [401, 403, 404])
  await workspace(unmappedSession, 'LAUNDRY', [400, 401, 403])
  await workspace(inactiveSession, 'QC', [400, 401, 403])
  const viewerLaundry = await workspace(viewerSession, 'LAUNDRY')
  const viewerQc = await workspace(viewerSession, 'QC')
  assert.equal(viewerLaundry.json?.contract_version, 'CP6_V2620')
  assert.equal(viewerQc.json?.contract_version, 'CP6_V2620')
  await workspace(operatorSession, 'LAUNDRY')
  await workspace(operatorSession, 'QC')

  const nonexistent = randomUUID()
  const validNegativePayload = {
    distribution_batch_id: nonexistent,
    vendor_id: randomUUID(),
    wash_process_id: randomUUID(),
    target_dyeing_color: 'NAVY',
    physical_at: '2026-09-01T11:00:00Z',
    reason: 'CP6 real JWT negative mutation proof',
    notes: 'No business row may survive this domain failure',
    lines: [{ size_id: randomUUID(), qty_sent_pcs: 1 }],
  }

  const viewerRequestId = randomUUID()
  requestIds.push(viewerRequestId)
  const viewerMutation = await rpc('erp_save_laundry_qc_action_v1', viewerSession.accessToken, {
    p_action: 'POST_DELIVERY', p_payload: validNegativePayload,
    p_client_request_id: viewerRequestId, p_expected_version: 1,
  })
  record('rpc-viewer-cp6-mutation-denied', viewerMutation, [400, 401, 403])
  assert.match(viewerMutation.text, /PERMISSION_DENIED|production\.laundry\.(create|post)/i)

  const operatorRequestId = randomUUID()
  requestIds.push(operatorRequestId)
  const operatorMutation = await rpc('erp_save_laundry_qc_action_v1', operatorSession.accessToken, {
    p_action: 'POST_DELIVERY', p_payload: validNegativePayload,
    p_client_request_id: operatorRequestId, p_expected_version: 1,
  })
  record('rpc-operator-reaches-domain-guard', operatorMutation, [400, 409])
  assert.match(operatorMutation.text, /Authoritative POSTED distribution batch was not found/)
  assert.doesNotMatch(operatorMutation.text, /PERMISSION_DENIED|Internal ERP access required/i)

  for (const table of [
    'laundry_delivery_batch_size_lines', 'laundry_receipt_batch_size_lines',
    'laundry_failed_wash_attempts', 'laundry_failed_wash_batch_size_lines',
  ]) {
    const direct = await request(`/rest/v1/${table}?select=id&limit=1`, {
      token: operatorSession.accessToken,
    })
    record(`rest-direct-${table}-denied`, direct, [401, 403, 404])
  }

  const privateWriter = await rpc('save_laundry_qc_action_v1', operatorSession.accessToken, {})
  record('rpc-private-cp6-writer-denied', privateWriter, [401, 403, 404])
  const privateInvoicePost = await rpc('post_vendor_invoice', operatorSession.accessToken, {
    p_invoice_id: randomUUID(),
  })
  record('rpc-private-vendor-invoice-post-denied', privateInvoicePost, [400, 401, 403, 404])
  if (privateInvoicePost.status === 400) {
    assert.match(privateInvoicePost.text, /Internal ERP access required|permission denied/i)
  }
  const privateInvoiceReverse = await rpc('reverse_vendor_invoice', operatorSession.accessToken, {
    p_invoice_id: randomUUID(), p_reason: 'CP6 JWT private reversal denial',
  })
  record('rpc-private-vendor-invoice-reverse-denied', privateInvoiceReverse, [400, 401, 403, 404])
  if (privateInvoiceReverse.status === 400) {
    assert.match(privateInvoiceReverse.text, /OWNER|ADMIN|permission denied/i)
  }

  assert.equal(sql(`select count(*) from erp.idempotency_requests
    where client_request_id in('${viewerRequestId}'::uuid,'${operatorRequestId}'::uuid)`), '0')
  assert.equal(sql('select count(*) from erp.cp6_laundry_qc_execution_context'), '0')
  assert.equal(sql(`select count(*) from erp.laundry_deliveries
    where id='${nonexistent}'::uuid or special_instruction like 'CP6 ${safeRunId}%'`), '0')
} catch (error) {
  failure = error
} finally {
  try { cleanupDatabase() } catch (error) { failure ||= error }
  try { await cleanupAuth() } catch (error) { failure ||= error }
}

let residue
try {
  residue = JSON.parse(sql(`select jsonb_build_object(
    'auth_users',(select count(*) from auth.users where ${uuidCondition('id', users.map((u) => u.id))}),
    'auth_identities',(select count(*) from auth.identities where ${uuidCondition('user_id', users.map((u) => u.id))}),
    'auth_sessions',(select count(*) from auth.sessions where ${uuidCondition('user_id', users.map((u) => u.id))}),
    'auth_refresh_tokens',(select count(*) from auth.refresh_tokens where ${textUuidCondition('user_id', users.map((u) => u.id))}),
    'app_users',(select count(*) from erp.app_users where ${uuidCondition('id', appUserIds)}),
    'custom_roles',(select count(*) from erp.app_roles where ${uuidCondition('id', roleIds)}),
    'role_permissions',(select count(*) from erp.app_role_permissions where ${uuidCondition('role_id', roleIds)}),
    'access_audit',(select count(*) from erp.app_access_audit
      where ${uuidCondition('actor_app_user_id', appUserIds)}
         or ${uuidCondition('entity_id', appUserIds)}
         or ${uuidCondition('entity_id', roleIds)}),
    'audit_logs',(select count(*) from erp.audit_logs
      where ${uuidCondition('changed_by', appUserIds)}
         or change_reason like 'CP6 ${safeRunId}%'),
    'idempotency',(select count(*) from erp.idempotency_requests
      where ${uuidCondition('client_request_id', requestIds)}),
    'execution_context',(select count(*) from erp.cp6_laundry_qc_execution_context)
  );`))
} catch (error) {
  failure ||= error
  residue = { residue_query_failed: true }
}

const residueClean = Object.values(residue).every((value) => value === 0)
const report = {
  status: failure || !residueClean ? 'FAIL' : 'PASS',
  classification: 'LOCAL_POST_CP6_REAL_AUTH_JWT_HTTP',
  target: 'DISPOSABLE_LOCAL_SUPABASE_AFTER_V2620A',
  cases,
  residue,
  secrets_persisted: false,
  real_owner_invited: false,
  production_go: false,
  tested: {
    post_cp6_apply: true,
    real_password_sessions_and_bearer_jwt: true,
    anonymous_unmapped_inactive_denial: true,
    viewer_laundry_and_qc_read_only: true,
    non_admin_operator_reaches_domain_guard: true,
    direct_cp6_table_denial: true,
    private_cp6_and_invoice_writer_denial: true,
    negative_mutation_transaction_residue_zero: true,
    auth_app_role_audit_idempotency_context_cleanup_zero: true,
  },
  ...(failure ? { failure: failure instanceof Error ? failure.message : String(failure) } : {}),
}

writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`)
if (report.status !== 'PASS') {
  throw failure || new Error(`CP6 Auth/JWT cleanup residue: ${JSON.stringify(residue)}`)
}

console.log(`CP6 post-install Auth/JWT/HTTP E2E passed: ${cases.length} assertions; zero targeted residue.`)
