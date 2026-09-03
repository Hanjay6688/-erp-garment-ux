#!/usr/bin/env node

import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'

const baseUrl = (process.env.SUPABASE_URL || '').replace(/\/$/, '')
const browserKey = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_PUBLISHABLE_KEY || ''
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || ''
const pgurl = process.env.PGURL || ''
const reportPath = process.env.CUTTING_BRIDGE_AUTH_REPORT || 'cutting-bridge-auth-e2e.json'

assert.ok(/^https?:\/\//.test(baseUrl), 'SUPABASE_URL is required')
assert.ok(browserKey.length > 20, 'Supabase browser key is required')
assert.ok(serviceKey.length > 20, 'SUPABASE_SERVICE_ROLE_KEY is required for disposable local Auth')
assert.ok(pgurl.startsWith('postgresql://'), 'PGURL is required')

const runId = `${Date.now()}-${randomBytes(4).toString('hex')}`
const safeRunId = runId.replace(/[^a-zA-Z0-9-]/g, '')
const users = []
const sessions = []
const appUserIds = []
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

async function createUser(label, roleCode = null) {
  const email = `cutting-bridge-${label}-${safeRunId}@example.invalid`
  const password = `Cb18!${randomBytes(24).toString('base64url')}9a`
  const response = await request('/auth/v1/admin/users', {
    key: serviceKey,
    token: serviceKey,
    method: 'POST',
    body: { email, password, email_confirm: true, user_metadata: { full_name: `Cutting Bridge ${label}` } },
  })
  record(`auth-create-${label}`, response, [200])
  assert.match(response.json?.id || '', /^[0-9a-f-]{36}$/i)
  const user = { id: response.json.id, email, password, label }
  users.push(user)
  if (roleCode) {
    const appId = randomUUID()
    appUserIds.push(appId)
    sql(`insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
         select '${appId}'::uuid,'${user.id}'::uuid,'Cutting Bridge ${label}','${roleCode}',id,true
         from erp.app_roles where role_code='${roleCode}'`)
  }
  return user
}

async function signIn(user) {
  const response = await request('/auth/v1/token?grant_type=password', {
    method: 'POST', body: { email: user.email, password: user.password },
  })
  record(`auth-signin-${user.label}`, response, [200])
  assert.ok(response.json?.access_token)
  const session = { label: user.label, accessToken: response.json.access_token }
  sessions.push(session)
  return session
}

async function rpc(name, token, body = {}) {
  return request(`/rest/v1/rpc/${name}`, { token, method: 'POST', body })
}

async function cleanup() {
  for (const session of sessions) {
    try { await request('/auth/v1/logout?scope=global', { token: session.accessToken, method: 'POST' }) } catch { /* residue is checked below */ }
  }
  if (appUserIds.length) {
    const ids = appUserIds.map((id) => `'${id}'::uuid`).join(',')
    sql(`begin;
      set local erp.cp45_allow_synthetic_cleanup='on';
      delete from erp.audit_logs where changed_by in (${ids}) or entity_id in (${ids});
      delete from erp.app_access_audit where actor_app_user_id in (${ids}) or entity_id in (${ids});
      delete from erp.app_users where id in (${ids});
      -- The first pass releases audit FKs; this pass removes delete tombstones.
      delete from erp.audit_logs where changed_by in (${ids}) or entity_id in (${ids});
      commit;`)
  }
  for (const user of [...users].reverse()) {
    try {
      await request(`/auth/v1/admin/users/${user.id}`, {
        key: serviceKey, token: serviceKey, method: 'DELETE',
      })
    } catch { /* residue is checked below */ }
  }
}

let failure
try {
  const production = await createUser('production', 'PRODUKSI_QC')
  const customer = await createUser('customer', 'CUSTOMER')
  const unmapped = await createUser('unmapped')
  const productionSession = await signIn(production)
  const customerSession = await signIn(customer)
  const unmappedSession = await signIn(unmapped)

  const access = await rpc('erp_get_my_access_v1', productionSession.accessToken)
  record('production-profile', access, [200])
  assert.equal(access.json?.allowed, true)
  assert.ok(access.json?.permissions?.includes('production.cutting.view'))
  assert.ok(access.json?.permissions?.includes('production.distribution.view'))

  const workspace = await rpc('erp_get_cutting_workspace_v1', productionSession.accessToken, {
    p_roll_query: null, p_location_id: null, p_limit: 10, p_offset: 0,
  })
  record('production-cutting-workspace', workspace, [200])
  assert.ok(Array.isArray(workspace.json?.orders))

  const pickup = await rpc('erp_get_cutting_pickup_queue_v1', productionSession.accessToken, {
    p_filter: 'ALL', p_pattern_id: null, p_query: null, p_limit: 10, p_offset: 0,
  })
  record('production-pickup-queue', pickup, [200])
  assert.ok(Array.isArray(pickup.json?.rows))

  const wip = await rpc('erp_get_wip_control_v1', productionSession.accessToken, {
    p_filter: 'ALL', p_pattern_id: null, p_sort: 'PATTERN', p_query: null,
  })
  record('production-connected-wip', wip, [200])
  assert.ok(Array.isArray(wip.json?.rows))

  for (const [label, token] of [
    ['customer', customerSession.accessToken],
    ['unmapped', unmappedSession.accessToken],
  ]) {
    const denied = await rpc('erp_get_cutting_workspace_v1', token, {
      p_roll_query: null, p_location_id: null, p_limit: 10, p_offset: 0,
    })
    record(`${label}-cutting-workspace-denied`, denied, [400, 401, 403])
  }
} catch (error) {
  failure = error
} finally {
  try { await cleanup() } catch (cleanupError) { failure ||= cleanupError }
}

const authIds = users.map(({ id }) => `'${id}'::uuid`).join(',') || 'null::uuid'
const appIds = appUserIds.map((id) => `'${id}'::uuid`).join(',') || 'null::uuid'
const residue = JSON.parse(sql(`select jsonb_build_object(
  'auth_users',(select count(*) from auth.users where id in (${authIds})),
  'auth_identities',(select count(*) from auth.identities where user_id in (${authIds})),
  'auth_sessions',(select count(*) from auth.sessions where user_id in (${authIds})),
  'auth_refresh_tokens',(select count(*) from auth.refresh_tokens where user_id::text in (${users.map(({ id }) => `'${id}'`).join(',') || "''"})),
  'app_users',(select count(*) from erp.app_users where id in (${appIds})),
  'audit_logs',(select count(*) from erp.audit_logs where changed_by in (${appIds}) or entity_id in (${appIds}))
)`))

const report = {
  format: 'CUTTING_BRIDGE_LOCAL_AUTH_E2E_V1',
  status: failure ? 'FAIL' : 'PASS',
  mode: 'LOCAL_FULL_SCHEMA_AUTH_VERIFIED',
  classified_as_ci: true,
  case_count: cases.length,
  case_passed: failure ? Math.max(0, cases.length - 1) : cases.length,
  cases,
  assertions: {
    production_profile_has_cutting_and_distribution_permissions: !failure,
    cutting_workspace_reached_through_real_http_jwt: !failure,
    pickup_queue_reached_through_real_http_jwt: !failure,
    connected_wip_reached_through_real_http_jwt: !failure,
    customer_and_unmapped_fail_closed: !failure,
  },
  cleanup: residue,
  credentials_or_jwt_recorded: false,
  production_go: false,
}
writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`)
assert.deepEqual(residue, { auth_users: 0, auth_identities: 0, auth_sessions: 0, auth_refresh_tokens: 0, app_users: 0, audit_logs: 0 })
if (failure) throw failure
console.log(`Cutting Bridge local Auth/JWT E2E PASS: ${cases.length}/${cases.length}; residue zero.`)
