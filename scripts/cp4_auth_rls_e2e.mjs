#!/usr/bin/env node

import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'

const baseUrl = (process.env.SUPABASE_URL || '').replace(/\/$/, '')
const anonKey = process.env.SUPABASE_ANON_KEY || ''
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || ''
const pgurl = process.env.PGURL || ''
const reportPath = process.env.CP4_AUTH_REPORT || 'cp4-auth-rls-e2e.json'

assert.ok(/^https?:\/\//.test(baseUrl), 'SUPABASE_URL is required')
assert.ok(anonKey.length > 20, 'SUPABASE_ANON_KEY is required')
assert.ok(serviceKey.length > 20, 'SUPABASE_SERVICE_ROLE_KEY is required')
assert.ok(pgurl.startsWith('postgresql://'), 'PGURL is required')

const runId = `${Date.now()}-${randomBytes(4).toString('hex')}`
const password = () => `Cp4!${randomBytes(24).toString('base64url')}9a`
const createdUsers = []
const appUserIds = []
const cases = []

async function request(path, { key = anonKey, token, method = 'GET', body } = {}) {
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

async function createUser(label) {
  const email = `cp4-${label}-${runId}@example.invalid`
  const userPassword = password()
  const response = await request('/auth/v1/admin/users', {
    key: serviceKey,
    token: serviceKey,
    method: 'POST',
    body: { email, password: userPassword, email_confirm: true, user_metadata: { full_name: `CP4 ${label}` } },
  })
  record(`admin-create-${label}`, response, [200])
  assert.match(response.json?.id || '', /^[0-9a-f-]{36}$/i)
  createdUsers.push(response.json.id)
  return { id: response.json.id, email, password: userPassword }
}

function sql(statement) {
  return execFileSync('psql', [pgurl, '-X', '-qAt', '-v', 'ON_ERROR_STOP=1', '-c', statement], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim()
}

function mapUser(authId, fullName, role, isActive = true) {
  assert.match(authId, /^[0-9a-f-]{36}$/i)
  const appId = randomUUID()
  appUserIds.push(appId)
  const safeName = fullName.replaceAll("'", "''")
  sql(`insert into erp.app_users(id,auth_user_id,full_name,role,is_active) values ('${appId}'::uuid,'${authId}'::uuid,'${safeName}','${role}',${isActive});`)
  return appId
}

async function signIn(user, label) {
  const response = await request('/auth/v1/token?grant_type=password', {
    method: 'POST',
    body: { email: user.email, password: user.password },
  })
  record(`signin-${label}`, response, [200])
  assert.ok(response.json?.access_token)
  assert.ok(response.json?.refresh_token)
  return response.json
}

async function profile(token, label) {
  const response = await request('/rest/v1/v_erp_my_profile?select=id,auth_user_id,full_name,role,is_active,row_version', { token })
  record(`profile-${label}`, response, [200])
  assert.ok(Array.isArray(response.json))
  return response.json
}

async function preview({ key = anonKey, token } = {}) {
  return request('/rest/v1/rpc/erp_preview_attendance_hpp_pool_v1', {
    key,
    token,
    method: 'POST',
    body: { p_period_start: '2026-01-01', p_period_end: '2026-01-01' },
  })
}

async function cleanup() {
  if (appUserIds.length) {
    const ids = appUserIds.filter((id) => /^[0-9a-f-]{36}$/i.test(id)).map((id) => `'${id}'::uuid`).join(',')
    if (ids) sql(`delete from erp.app_users where id in (${ids});`)
  }
  for (const id of [...createdUsers].reverse()) {
    try {
      await request(`/auth/v1/admin/users/${id}`, { key: serviceKey, token: serviceKey, method: 'DELETE' })
    } catch {
      // The final database residue assertion below catches an incomplete cleanup.
    }
  }
}

let failure
try {
  const owner = await createUser('owner')
  const staff = await createUser('staff')
  const inactive = await createUser('inactive')
  const unmapped = await createUser('unmapped')

  mapUser(owner.id, 'CP4 Owner', 'OWNER', true)
  mapUser(staff.id, 'CP4 Staff', 'STAFF', true)
  mapUser(inactive.id, 'CP4 Inactive Owner', 'OWNER', false)

  const ownerSession = await signIn(owner, 'owner')
  const staffSession = await signIn(staff, 'staff')
  const inactiveSession = await signIn(inactive, 'inactive')
  const unmappedSession = await signIn(unmapped, 'unmapped')

  const ownerProfile = await profile(ownerSession.access_token, 'owner')
  assert.equal(ownerProfile.length, 1)
  assert.equal(ownerProfile[0].auth_user_id, owner.id)
  assert.equal(ownerProfile[0].role, 'OWNER')
  assert.equal(ownerProfile[0].is_active, true)

  const staffProfile = await profile(staffSession.access_token, 'staff')
  assert.equal(staffProfile.length, 1)
  assert.equal(staffProfile[0].role, 'STAFF')

  const inactiveProfile = await profile(inactiveSession.access_token, 'inactive')
  assert.equal(inactiveProfile.length, 1)
  assert.equal(inactiveProfile[0].is_active, false)

  const unmappedProfile = await profile(unmappedSession.access_token, 'unmapped')
  assert.deepEqual(unmappedProfile, [])

  const anonProfile = await request('/rest/v1/v_erp_my_profile?select=*')
  record('profile-anon-denied', anonProfile, [401, 403])
  const serviceProfile = await request('/rest/v1/v_erp_my_profile?select=*', { key: serviceKey, token: serviceKey })
  // Hosted UAT denies SELECT to service_role directly. The local Supabase role
  // graph may still route this self-filtered view and return HTTP 200 []; both
  // are fail-closed. Any visible profile row is a security failure.
  record('profile-service-role-no-profile-leak', serviceProfile, [200, 401, 403])
  if (serviceProfile.status === 200) {
    assert.deepEqual(serviceProfile.json, [])
  }

  const ownerPreview = await preview({ token: ownerSession.access_token })
  record('rpc-owner-authorized-domain-guard', ownerPreview, [400])
  assert.match(ownerPreview.text, /No eligible normal-Mandor attendance payroll cost exists/i)

  const servicePreview = await preview({ key: serviceKey, token: serviceKey })
  record('rpc-service-role-authorized-domain-guard', servicePreview, [400])
  assert.match(servicePreview.text, /No eligible normal-Mandor attendance payroll cost exists/i)

  for (const [label, token] of [
    ['staff', staffSession.access_token],
    ['inactive', inactiveSession.access_token],
    ['unmapped', unmappedSession.access_token],
  ]) {
    const response = await preview({ token })
    record(`rpc-${label}-denied`, response, [400, 401, 403])
    assert.match(response.text, /OWNER or ADMIN access required/i)
  }

  const anonPreview = await preview()
  record('rpc-anon-denied', anonPreview, [401, 403])

  const privateInner = await request('/rest/v1/rpc/preview_attendance_hpp_pool_v1', {
    key: serviceKey,
    token: serviceKey,
    method: 'POST',
    body: { p_period_start: '2026-01-01', p_period_end: '2026-01-01' },
  })
  record('private-inner-rpc-not-exposed', privateInner, [404])

  const genericReverse = await request('/rest/v1/rpc/reverse_journal', {
    key: serviceKey,
    token: serviceKey,
    method: 'POST',
    body: { p_journal_entry_id: randomUUID(), p_reason: 'must remain private' },
  })
  record('generic-reversal-rpc-not-exposed', genericReverse, [404])

  const refreshed = await request('/auth/v1/token?grant_type=refresh_token', {
    method: 'POST',
    body: { refresh_token: ownerSession.refresh_token },
  })
  record('auth-refresh', refreshed, [200])
  assert.ok(refreshed.json?.access_token)
  assert.ok(refreshed.json?.refresh_token)

  const recovery = await request('/auth/v1/recover', {
    method: 'POST',
    body: { email: owner.email },
  })
  record('auth-recovery', recovery, [200])

  const logout = await request('/auth/v1/logout', {
    token: refreshed.json.access_token,
    method: 'POST',
  })
  record('auth-logout', logout, [204])
  const refreshAfterLogout = await request('/auth/v1/token?grant_type=refresh_token', {
    method: 'POST',
    body: { refresh_token: refreshed.json.refresh_token },
  })
  record('auth-refresh-after-logout-denied', refreshAfterLogout, [400, 401])

  const signup = await request('/auth/v1/signup', {
    method: 'POST',
    body: { email: `cp4-signup-${runId}@example.invalid`, password: password() },
  })
  if (signup.json?.user?.id) createdUsers.push(signup.json.user.id)
  record('public-signup-disabled', signup, [400, 403, 422])
  assert.match(signup.text, /signup|signups|disabled|not allowed/i)
} catch (error) {
  failure = error
} finally {
  await cleanup()
}

const residue = JSON.parse(sql(`select jsonb_build_object(
  'auth_users',(select count(*) from auth.users where email like 'cp4-%@example.invalid'),
  'app_users',(select count(*) from erp.app_users where full_name like 'CP4 %')
);`))

const report = {
  status: failure || residue.auth_users !== 0 || residue.app_users !== 0 ? 'FAIL' : 'PASS',
  cases,
  residue,
  tested: {
    login: true,
    refresh: true,
    logout: true,
    recovery: true,
    signup_disabled: true,
    self_profile: true,
    unmapped_user: true,
    inactive_user: true,
    owner_rpc: true,
    staff_denial: true,
    anon_denial: true,
    service_role_boundary: true,
    private_inner_rpc: true,
    generic_reversal_not_exposed: true,
  },
  ...(failure ? { failure: failure instanceof Error ? failure.message : String(failure) } : {}),
}
writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`)

if (report.status !== 'PASS') {
  throw failure || new Error(`CP4 Auth/RLS cleanup residue: ${JSON.stringify(residue)}`)
}

console.log(`CP4 Auth/RLS E2E passed: ${cases.length} HTTP/JWT assertions; zero synthetic residue.`)
