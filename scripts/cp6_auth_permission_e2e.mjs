#!/usr/bin/env node

import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import { writeFileSync } from 'node:fs'

const baseUrl = (process.env.SUPABASE_URL || '').replace(/\/$/, '')
const authBaseUrl = (process.env.SUPABASE_AUTH_URL || baseUrl).replace(/\/$/, '')
const restBaseUrl = (process.env.SUPABASE_REST_URL || baseUrl).replace(/\/$/, '')
const restPrefix = process.env.SUPABASE_REST_PREFIX ?? '/rest/v1'
const browserKey = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_PUBLISHABLE_KEY || ''
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || ''
const pgurl = process.env.CP6_AUTH_PGURL || process.env.PGURL || ''
const authPgurl = process.env.CP6_AUTH_CONTROL_PGURL || process.env.PGURL || ''
const disposableDatabase = process.env.CP6_AUTH_DATABASE_NAME || ''
const reportPath = process.env.CP6_AUTH_REPORT || 'cp6-auth-permission-e2e.json'

assert.ok(/^https?:\/\//.test(baseUrl), 'SUPABASE_URL is required')
assert.ok(/^https?:\/\//.test(authBaseUrl), 'SUPABASE_AUTH_URL is invalid')
assert.ok(/^https?:\/\//.test(restBaseUrl), 'SUPABASE_REST_URL is invalid')
assert.ok(browserKey.length > 20, 'Supabase browser/publishable key is required')
assert.ok(serviceKey.length > 20, 'SUPABASE_SERVICE_ROLE_KEY is required')
assert.ok(pgurl.startsWith('postgresql://'), 'PGURL is required')
assert.ok(authPgurl.startsWith('postgresql://'), 'CP6_AUTH_CONTROL_PGURL is required')
assert.ok(disposableDatabase, 'CP6_AUTH_DATABASE_NAME is required; positive Auth writes only run in a disposable clone')
assert.notEqual(new URL(authBaseUrl).hostname, 'vlxdhpkjeevubjxexnfo.supabase.co', 'Legacy is read-only forever')
assert.notEqual(new URL(restBaseUrl).hostname, 'vlxdhpkjeevubjxexnfo.supabase.co', 'Legacy is read-only forever')

const runId = `${Date.now()}-${randomBytes(4).toString('hex')}`
const safeRunId = runId.replace(/[^a-zA-Z0-9-]/g, '')
const users = []
const appUserIds = []
const roleIds = []
const roleCodes = new Set()
const requestIds = []
const cases = []
const facadeRoleMatrix = []
let positiveEvidence = null
let privateSchemaEvidence = null
const fixture = {
  po: 'c8c40000-0000-4000-8000-000000000001',
  group: 'c8c40000-0000-4000-8000-000000000003',
  batch: 'c8c40000-0000-4000-8000-000000000008',
  size: 'c8c10000-0000-4000-8000-000000000002',
  vendor: 'c8c20000-0000-4000-8000-000000000002',
  process: 'c8c20000-0000-4000-8000-000000000003',
  location: 'c8c20000-0000-4000-8000-000000000001',
  product: 'c8c10000-0000-4000-8000-000000000004',
}

function runSql(url, statement) {
  return execFileSync('psql', [url, '-X', '-qAt', '-v', 'ON_ERROR_STOP=1', '-c', statement], {
    encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
  }).trim()
}

const sql = (statement) => runSql(pgurl, statement)
const authSql = (statement) => runSql(authPgurl, statement)
const physicalNow = () => sql(
  `select to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')`,
)

if (disposableDatabase) {
  assert.equal(sql('select current_database()'), disposableDatabase,
    'Positive CP6 Auth proof must target its exact disposable clone')
  assert.notEqual(disposableDatabase, 'postgres', 'Positive CP6 Auth proof refuses the primary database')
}

async function request(path, {
  key = browserKey, token, method = 'GET', body, headers = {},
} = {}) {
  const origin = path.startsWith('/auth/') ? authBaseUrl : restBaseUrl
  const response = await fetch(`${origin}${path}`, {
    method,
    headers: {
      apikey: key,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const text = await response.text()
  let json = null
  try { json = text ? JSON.parse(text) : null } catch { json = null }
  return { status: response.status, text, json }
}

function record(name, response, expectedStatuses) {
  const observedStatus = expectedStatuses.find((status) => status === response.status)
  assert.notEqual(observedStatus, undefined, `${name}: unexpected HTTP status`)
  // Persist only the independently matched numeric status, never response text.
  cases.push({ name, status: observedStatus })
  return observedStatus
}

function recordFacadeRole(facade, role, expectation, response, expectedStatuses, detail = null) {
  const name = `facade-${facade}-${role}-${expectation.toLowerCase()}`
  const observedStatus = record(name, response, expectedStatuses)
  facadeRoleMatrix.push({ facade, role, expectation, status: observedStatus, ...(detail ? { detail } : {}) })
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
  return request(`${restPrefix}/rpc/${name}`, { token, method: 'POST', body })
}

async function privateRpc(name, token, body = {}) {
  return request(`${restPrefix}/rpc/${name}`, {
    token,
    method: 'POST',
    body,
    headers: { 'Accept-Profile': 'erp', 'Content-Profile': 'erp' },
  })
}

async function cp6Action(session, action, payload, expectedVersion) {
  const clientRequestId = randomUUID()
  requestIds.push(clientRequestId)
  const response = await rpc('erp_save_laundry_qc_action_v1', session.accessToken, {
    p_action: action,
    p_payload: payload,
    p_client_request_id: clientRequestId,
    p_expected_version: expectedVersion,
  })
  recordFacadeRole('erp_save_laundry_qc_action_v1', session.label, 'ALLOW', response, [200],
    `action=${action}`)
  assert.equal(response.json?.contract_version, 'CP6_V2620')
  assert.equal(response.json?.action, action)
  assert.equal(response.json?.client_request_id, clientRequestId)
  assert.equal(response.json?.committed, true)
  return response.json
}

async function dedicatedFinalSku(session, payload, expectedVersion) {
  const clientRequestId = randomUUID()
  requestIds.push(clientRequestId)
  const response = await rpc('erp_post_final_sku_allocation_v1', session.accessToken, {
    p_payload: payload,
    p_client_request_id: clientRequestId,
    p_expected_version: expectedVersion,
  })
  recordFacadeRole('erp_post_final_sku_allocation_v1', session.label, 'ALLOW', response, [200],
    'valid-source-positive-transaction')
  assert.equal(response.json?.contract_version, 'CP6_V2620')
  assert.equal(response.json?.action, 'POST_FINAL_SKU')
  assert.equal(response.json?.client_request_id, clientRequestId)
  assert.equal(response.json?.committed, true)
  return response.json
}

function findQueueRow(workspaceResponse) {
  const queue = workspaceResponse.json?.qc_queue
  assert.ok(Array.isArray(queue) && queue.length > 0, 'Real QC workspace lost its source queue')
  const row = queue.find((candidate) => candidate.cutting_group_id === fixture.group)
  assert.ok(row, 'Real QC source row was not returned through JWT/HTTP')
  return row
}

function financialState() {
  return JSON.parse(sql(`select jsonb_build_object(
    'delivery_status',(select status from erp.laundry_deliveries
      where po_id='${fixture.po}'::uuid order by created_at desc,id desc limit 1),
    'receipt_status',(select r.status from erp.laundry_receipts r
      join erp.laundry_deliveries d on d.id=r.delivery_id
      where d.po_id='${fixture.po}'::uuid order by r.created_at desc,r.id desc limit 1),
    'posted_qc',(select count(*) from erp.qc_inspections
      where po_id='${fixture.po}'::uuid and status='POSTED'),
    'reversed_qc',(select count(*) from erp.qc_inspections
      where po_id='${fixture.po}'::uuid and status='REVERSED'),
    'fg_qty',(select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m
      join erp.fg_lots l on l.id=m.lot_id where l.po_id='${fixture.po}'::uuid),
    'active_laundry_hpp',(select coalesce(sum(
        c.total_cost*greatest(coalesce(stock.qty,0),0)/nullif(h.qty_basis_pcs,0)
      ),0)
      from erp.hpp_versions h
      join erp.hpp_version_components c on c.hpp_version_id=h.id
        and c.component_type='LAUNDRY'
      join erp.fg_lots l on l.id=h.lot_id
      left join lateral(select sum(m.qty_signed)::numeric qty
        from erp.fg_stock_movements m where m.lot_id=l.id) stock on true
      where l.po_id='${fixture.po}'::uuid and h.is_current),
    'wip_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
      where l.po_id='${fixture.po}'::uuid and l.account_id=erp.account_id('WIP')),
    'fg_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
      where l.po_id='${fixture.po}'::uuid and l.account_id=erp.account_id('FG_INVENTORY')),
    'accrued_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
      where l.po_id='${fixture.po}'::uuid and l.account_id=erp.account_id('ACCRUED_MANUFACTURING')),
    'physical_ready',(select coalesce(unsent_ready_qty_pcs,0)
      from erp.v_wip_control_status_v1 where cutting_group_id='${fixture.group}'::uuid),
    'execution_context',(select count(*) from erp.cp6_laundry_qc_execution_context),
    'unbalanced_journals',(select count(*) from(
      select e.id from erp.journal_entries e join erp.journal_lines l
        on l.journal_entry_id=e.id
      where exists(
        select 1 from erp.journal_lines scoped
        where scoped.journal_entry_id=e.id
          and scoped.po_id='${fixture.po}'::uuid
      )
      group by e.id having sum(l.debit)<>sum(l.credit)
    ) x)
  );`))
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
  const suffix = safeRunId.replace(/[^a-zA-Z0-9]/g, '').slice(-8).toUpperCase()
  const roleCode = `CP6_${label.toUpperCase().slice(0, 4)}_${suffix}`
  assert.match(roleCode, /^[A-Z][A-Z0-9_]{1,31}$/)
  assert.ok(roleCode.length <= 20, 'role code must fit legacy app_users.role varchar(20)')
  assert.ok(!roleCodes.has(roleCode), `duplicate generated role code: ${roleCode}`)
  roleCodes.add(roleCode)
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
  recordFacadeRole(
    'erp_get_laundry_qc_workspace_v1', session?.label || 'anonymous',
    expectedStatuses.length === 1 && expectedStatuses[0] === 200 ? 'ALLOW' : 'DENY',
    response, expectedStatuses, `scope=${scope}`,
  )
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
    'production.laundry.reverse',
    'production.final_sku.view', 'production.final_sku.post', 'production.final_sku.reverse',
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
  assert.ok(operatorAccess.permissions.includes('production.laundry.reverse'))
  assert.ok(operatorAccess.permissions.includes('production.final_sku.post'))
  assert.ok(operatorAccess.permissions.includes('production.final_sku.reverse'))
  assert.deepEqual(
    [...viewerAccess.permissions].sort(),
    ['production.final_sku.view', 'production.laundry.view'].sort(),
  )

  await workspace(null, 'LAUNDRY', [401, 403, 404])
  await workspace(null, 'QC', [401, 403, 404])
  await workspace(unmappedSession, 'LAUNDRY', [400, 401, 403])
  await workspace(unmappedSession, 'QC', [400, 401, 403])
  await workspace(inactiveSession, 'LAUNDRY', [400, 401, 403])
  await workspace(inactiveSession, 'QC', [400, 401, 403])
  const ownerLaundry = await workspace(ownerSession, 'LAUNDRY')
  const ownerQc = await workspace(ownerSession, 'QC')
  const viewerLaundry = await workspace(viewerSession, 'LAUNDRY')
  const viewerQc = await workspace(viewerSession, 'QC')
  assert.equal(ownerLaundry.json?.contract_version, 'CP6_V2620')
  assert.equal(ownerQc.json?.contract_version, 'CP6_V2620')
  assert.equal(viewerLaundry.json?.contract_version, 'CP6_V2620')
  assert.equal(viewerQc.json?.contract_version, 'CP6_V2620')
  const operatorLaundryBefore = await workspace(operatorSession, 'LAUNDRY')
  await workspace(operatorSession, 'QC')

  // Full positive chain through a real password session, bearer JWT, HTTP,
  // public facade, private writer, stock/HPP/journal rebuild, and the granular
  // reverse permissions. The database is a physical disposable clone and is
  // destroyed by the workflow after this proof.
  const readyBatch = operatorLaundryBefore.json?.ready_batches?.find(
    (candidate) => candidate.distribution_batch_id === fixture.batch,
  )
  assert.ok(readyBatch, 'Disposable Auth clone is missing the seeded CP6 ready batch')
  const delivery = await cp6Action(operatorSession, 'POST_DELIVERY', {
    distribution_batch_id: fixture.batch,
    vendor_id: fixture.vendor,
    wash_process_id: fixture.process,
    target_dyeing_color: 'NAVY',
    physical_at: '2026-09-01T11:00:00Z',
    reason: `CP6 ${safeRunId} positive JWT dispatch`,
    notes: 'Real Auth/JWT/HTTP positive chain',
    lines: [{ size_id: fixture.size, qty_sent_pcs: 10 }],
  }, Number(readyBatch.cutting_group_row_version))

  const laundryAfterDelivery = await workspace(operatorSession, 'LAUNDRY')
  const deliveryRow = laundryAfterDelivery.json?.deliveries?.find(
    (candidate) => candidate.delivery_id === delivery.delivery_id,
  )
  assert.ok(deliveryRow, 'Posted JWT delivery did not return through the HTTP workspace')
  const deliverySize = deliveryRow.sizes?.find((candidate) => candidate.size_id === fixture.size)
  assert.ok(deliverySize, 'Posted JWT delivery lost exact batch/size lineage')

  const laundrySearchBody = {
    p_delivery_batch_size_line_id: deliverySize.delivery_batch_size_line_id,
    p_physical_at: '2026-09-01T11:30:00Z',
    p_query: 'CP6-RACE-SKU', p_after_sort_key: null, p_limit: 50,
  }
  for (const session of [ownerSession, operatorSession, viewerSession]) {
    const response = await rpc(
      'erp_search_laundry_bs_products_v1', session.accessToken, laundrySearchBody,
    )
    recordFacadeRole('erp_search_laundry_bs_products_v1', session.label, 'ALLOW', response, [200],
      'valid-outstanding-delivery-size-source')
    assert.equal(response.json?.contract_version, 'CP6_LAUNDRY_BS_PRODUCT_SEARCH_V2620C')
    assert.equal(response.json?.source_delivery_batch_size_line_id,
      deliverySize.delivery_batch_size_line_id)
    assert.deepEqual(response.json?.products?.map((candidate) => candidate.id), [fixture.product])
  }
  for (const session of [null, unmappedSession, inactiveSession]) {
    const role = session?.label || 'anonymous'
    const response = await rpc(
      'erp_search_laundry_bs_products_v1', session?.accessToken, laundrySearchBody,
    )
    recordFacadeRole('erp_search_laundry_bs_products_v1', role, 'DENY', response,
      [400, 401, 403, 404], 'valid-outstanding-delivery-size-source')
    assert.notEqual(response.status, 200)
  }

  const receipt = await cp6Action(operatorSession, 'POST_RECEIPT', {
    delivery_id: delivery.delivery_id,
    wash_process_id: fixture.process,
    physical_at: '2026-09-01T12:00:00Z',
    reason: `CP6 ${safeRunId} positive JWT receipt`,
    lines: [{
      delivery_batch_size_line_id: deliverySize.delivery_batch_size_line_id,
      qty_good_received: 10,
      qty_bs_laundry: 0,
      bs_product_id: null,
    }],
  }, Number(delivery.row_version))

  const qcBefore = await workspace(operatorSession, 'QC')
  const sourceBefore = findQueueRow(qcBefore)
  assert.equal(sourceBefore.available_for_qc_qty_pcs, 10)
  const finalSearchBody = {
    p_source_laundry_receipt_batch_size_line_id: sourceBefore.source_batch_size_line_id,
    p_physical_at: '2026-09-01T13:00:00Z',
    p_query: 'CP6-RACE-SKU', p_after_sort_key: null, p_limit: 50,
  }
  for (const session of [ownerSession, operatorSession, viewerSession]) {
    const response = await rpc(
      'erp_search_final_sku_products_v1', session.accessToken, finalSearchBody,
    )
    recordFacadeRole('erp_search_final_sku_products_v1', session.label, 'ALLOW', response, [200],
      'valid-live-qc-source')
    assert.equal(response.json?.contract_version, 'CP6_PRODUCT_SEARCH_V2620B')
    assert.equal(response.json?.source_laundry_receipt_batch_size_line_id,
      sourceBefore.source_batch_size_line_id)
    assert.deepEqual(response.json?.products?.map((candidate) => candidate.id), [fixture.product])
  }
  for (const session of [null, unmappedSession, inactiveSession]) {
    const role = session?.label || 'anonymous'
    const response = await rpc(
      'erp_search_final_sku_products_v1', session?.accessToken, finalSearchBody,
    )
    recordFacadeRole('erp_search_final_sku_products_v1', role, 'DENY', response,
      [400, 401, 403, 404], 'valid-live-qc-source')
    assert.notEqual(response.status, 200)
  }
  const qcAfterProductSearch = await workspace(operatorSession, 'QC')
  assert.equal(findQueueRow(qcAfterProductSearch).source_batch_size_line_id,
    sourceBefore.source_batch_size_line_id,
    'Product lookup must not mutate or hide the QC source queue')

  const firstFinalPayload = {
    cutting_group_id: fixture.group,
    destination_location_id: fixture.location,
    physical_at: '2026-09-01T13:00:00Z',
    reason: `CP6 ${safeRunId} positive JWT operator partial Final SKU`,
    good_qty_pcs: 4,
    completion_mode: 'PARTIAL_SELECTION',
    lines: [{
      final_product_id: fixture.product,
      qty_good_pcs: 4, qty_bs_pcs: 0,
      source_laundry_receipt_line_id: sourceBefore.receipt_line_id,
      source_laundry_receipt_batch_size_line_id: sourceBefore.source_batch_size_line_id,
      notes: 'Exact real Auth operator partial lineage',
    }],
  }
  const dedicatedDeniedRequestIds = []
  for (const session of [null, unmappedSession, inactiveSession, viewerSession]) {
    const role = session?.label || 'anonymous'
    const deniedRequestId = randomUUID()
    dedicatedDeniedRequestIds.push(deniedRequestId)
    requestIds.push(deniedRequestId)
    const response = await rpc('erp_post_final_sku_allocation_v1', session?.accessToken, {
      p_payload: firstFinalPayload,
      p_client_request_id: deniedRequestId,
      p_expected_version: Number(sourceBefore.cutting_group_row_version),
    })
    recordFacadeRole('erp_post_final_sku_allocation_v1', role, 'DENY', response,
      [400, 401, 403, 404], 'valid-live-qc-source-and-payload')
    assert.notEqual(response.status, 200)
  }
  const firstQc = await dedicatedFinalSku(
    operatorSession, firstFinalPayload, Number(sourceBefore.cutting_group_row_version),
  )
  const partialState = financialState()
  assert.deepEqual(partialState, {
    delivery_status: 'RETURNED', receipt_status: 'POSTED',
    posted_qc: 1, reversed_qc: 0, fg_qty: 4, active_laundry_hpp: 28,
    wip_net: 42, fg_net: 28, accrued_net: -70, physical_ready: 0,
    execution_context: 0, unbalanced_journals: 0,
  })

  const qcPartial = await workspace(operatorSession, 'QC')
  const sourcePartial = findQueueRow(qcPartial)
  assert.equal(sourcePartial.available_for_qc_qty_pcs, 6)
  const ownerFinalPayload = {
    cutting_group_id: fixture.group,
    destination_location_id: fixture.location,
    physical_at: '2026-09-01T13:30:00Z',
    reason: `CP6 ${safeRunId} positive owner dedicated Final SKU`,
    good_qty_pcs: 1,
    completion_mode: 'PARTIAL_SELECTION',
    lines: [{
      final_product_id: fixture.product,
      qty_good_pcs: 1, qty_bs_pcs: 0,
      source_laundry_receipt_line_id: sourcePartial.receipt_line_id,
      source_laundry_receipt_batch_size_line_id: sourcePartial.source_batch_size_line_id,
      notes: 'Exact real Auth owner-positive dedicated lineage',
    }],
  }
  const ownerQcPosted = await dedicatedFinalSku(
    ownerSession, ownerFinalPayload, Number(sourcePartial.cutting_group_row_version),
  )
  const ownerPositiveState = financialState()
  assert.deepEqual(ownerPositiveState, {
    delivery_status: 'RETURNED', receipt_status: 'POSTED',
    posted_qc: 2, reversed_qc: 0, fg_qty: 5, active_laundry_hpp: 35,
    wip_net: 35, fg_net: 35, accrued_net: -70, physical_ready: 0,
    execution_context: 0, unbalanced_journals: 0,
  })

  const qcAfterOwner = await workspace(operatorSession, 'QC')
  const sourceAfterOwner = findQueueRow(qcAfterOwner)
  assert.equal(sourceAfterOwner.available_for_qc_qty_pcs, 5)
  const secondQc = await cp6Action(operatorSession, 'POST_FINAL_SKU', {
    cutting_group_id: fixture.group,
    destination_location_id: fixture.location,
    physical_at: '2026-09-01T14:00:00Z',
    reason: `CP6 ${safeRunId} positive JWT remaining Final SKU`,
    good_qty_pcs: 5,
    completion_mode: 'ALL_READY',
    lines: [{
      final_product_id: fixture.product,
      qty_good_pcs: 5, qty_bs_pcs: 0,
      source_laundry_receipt_line_id: sourceAfterOwner.receipt_line_id,
      source_laundry_receipt_batch_size_line_id: sourceAfterOwner.source_batch_size_line_id,
      notes: 'Exact real Auth remaining lineage',
    }],
  }, Number(sourceAfterOwner.cutting_group_row_version))
  const completeState = financialState()
  assert.deepEqual(completeState, {
    delivery_status: 'RETURNED', receipt_status: 'POSTED',
    posted_qc: 3, reversed_qc: 0, fg_qty: 10, active_laundry_hpp: 70,
    wip_net: 0, fg_net: 70, accrued_net: -70, physical_ready: 0,
    execution_context: 0, unbalanced_journals: 0,
  })

  await cp6Action(operatorSession, 'REVERSE_FINAL_SKU', {
    qc_inspection_id: secondQc.qc_inspection_id,
    reason: `CP6 ${safeRunId} granular reverse second Final SKU`,
  }, Number(secondQc.qc_row_version))
  await cp6Action(ownerSession, 'REVERSE_FINAL_SKU', {
    qc_inspection_id: ownerQcPosted.qc_inspection_id,
    reason: `CP6 ${safeRunId} owner reverse dedicated Final SKU`,
  }, Number(ownerQcPosted.qc_row_version))
  await cp6Action(operatorSession, 'REVERSE_FINAL_SKU', {
    qc_inspection_id: firstQc.qc_inspection_id,
    reason: `CP6 ${safeRunId} granular reverse first Final SKU`,
  }, Number(firstQc.qc_row_version))
  await cp6Action(operatorSession, 'REVERSE_RECEIPT', {
    receipt_id: receipt.receipt_id,
    reason: `CP6 ${safeRunId} granular reverse receipt`,
  }, Number(receipt.receipt_row_version))
  const laundryBeforeDeliveryReverse = await workspace(operatorSession, 'LAUNDRY')
  const reversibleDelivery = laundryBeforeDeliveryReverse.json?.deliveries?.find(
    (candidate) => candidate.delivery_id === delivery.delivery_id,
  )
  assert.ok(reversibleDelivery?.reversible, 'Granular operator should see delivery reversal ready')
  await cp6Action(operatorSession, 'REVERSE_DELIVERY', {
    delivery_id: delivery.delivery_id,
    reason: `CP6 ${safeRunId} granular reverse delivery`,
  }, Number(reversibleDelivery.row_version))
  const reversedState = financialState()
  assert.deepEqual(reversedState, {
    delivery_status: 'REVERSED', receipt_status: 'REVERSED',
    posted_qc: 0, reversed_qc: 3, fg_qty: 0, active_laundry_hpp: 0,
    wip_net: 0, fg_net: 0, accrued_net: 0, physical_ready: 10,
    execution_context: 0, unbalanced_journals: 0,
  })

  // Exercise the seventh mutation action through the same real custom-role
  // bearer token. A paid RETRY_AT_VENDOR attempt creates cost history without
  // physical Good/BS/FG; reversing its charge and then its delivery must leave
  // the complete physical and financial state balanced again.
  const retryLaundryBefore = await workspace(operatorSession, 'LAUNDRY')
  const retryBatch = retryLaundryBefore.json?.ready_batches?.find(
    (candidate) => candidate.distribution_batch_id === fixture.batch,
  )
  assert.ok(retryBatch, 'Granular operator lost the returned batch before failed-wash proof')
  // The reversals above append their physical correction at commit time. Use
  // an explicit operator timestamp sampled after that commit; a fixed historic
  // timestamp here would correctly be rejected as an impossible redispatch.
  const retryDeliveryPhysicalAt = physicalNow()
  const retryDelivery = await cp6Action(operatorSession, 'POST_DELIVERY', {
    distribution_batch_id: fixture.batch,
    vendor_id: fixture.vendor,
    wash_process_id: fixture.process,
    target_dyeing_color: 'NAVY',
    physical_at: retryDeliveryPhysicalAt,
    reason: `CP6 ${safeRunId} positive JWT failed-wash dispatch`,
    notes: 'Real Auth paid failed-wash source',
    lines: [{ size_id: fixture.size, qty_sent_pcs: 10 }],
  }, Number(retryBatch.cutting_group_row_version))
  const retryLaundrySent = await workspace(operatorSession, 'LAUNDRY')
  const retryDeliveryRow = retryLaundrySent.json?.deliveries?.find(
    (candidate) => candidate.delivery_id === retryDelivery.delivery_id,
  )
  const retrySize = retryDeliveryRow?.sizes?.find(
    (candidate) => candidate.size_id === fixture.size,
  )
  assert.ok(retrySize, 'Failed-wash HTTP proof lost its exact delivery batch/size')
  const failedWashPhysicalAt = physicalNow()
  const failedWash = await cp6Action(operatorSession, 'POST_FAILED_WASH', {
    delivery_id: retryDelivery.delivery_id,
    wash_process_id: fixture.process,
    custody_outcome: 'RETRY_AT_VENDOR',
    physical_at: failedWashPhysicalAt,
    reason: `CP6 ${safeRunId} positive JWT paid failed wash`,
    lines: [{
      delivery_batch_size_line_id: retrySize.delivery_batch_size_line_id,
      qty_attempted_pcs: 10,
    }],
  }, Number(retryDelivery.row_version))
  const failedWashCostState = financialState()
  assert.deepEqual(failedWashCostState, {
    delivery_status: 'SENT', receipt_status: 'POSTED',
    posted_qc: 0, reversed_qc: 3, fg_qty: 0, active_laundry_hpp: 0,
    // The paid failed attempt is 70 and the still-open retry dispatch carries
    // another 70 estimate. Both remain in WIP until the next physical result.
    wip_net: 140, fg_net: 0, accrued_net: -140, physical_ready: 0,
    execution_context: 0, unbalanced_journals: 0,
  })
  await cp6Action(operatorSession, 'REVERSE_RECEIPT', {
    receipt_id: failedWash.receipt_id,
    reason: `CP6 ${safeRunId} granular reverse paid failed wash`,
  }, Number(failedWash.receipt_row_version))
  const retryBeforeDeliveryReverse = await workspace(operatorSession, 'LAUNDRY')
  const retryReversibleDelivery = retryBeforeDeliveryReverse.json?.deliveries?.find(
    (candidate) => candidate.delivery_id === retryDelivery.delivery_id,
  )
  assert.ok(retryReversibleDelivery?.reversible,
    'Failed-wash charge reversal did not reopen granular delivery reversal')
  await cp6Action(operatorSession, 'REVERSE_DELIVERY', {
    delivery_id: retryDelivery.delivery_id,
    reason: `CP6 ${safeRunId} granular reverse failed-wash delivery`,
  }, Number(retryReversibleDelivery.row_version))
  const allActionsReversedState = financialState()
  assert.deepEqual(allActionsReversedState, reversedState)
  positiveEvidence = {
    partial_hpp_wip: partialState,
    owner_dedicated_final_sku: ownerPositiveState,
    completed_hpp_wip: completeState,
    fully_reversed: reversedState,
    failed_wash_cost_only: failedWashCostState,
    all_actions_fully_reversed: allActionsReversedState,
    source_queue_preserved_during_product_search: true,
    positive_facade_actions: 14,
    granular_reverse_actions: 7,
    mutation_action_kinds: [
      'POST_DELIVERY', 'POST_RECEIPT', 'POST_FAILED_WASH', 'POST_FINAL_SKU',
      'REVERSE_DELIVERY', 'REVERSE_RECEIPT', 'REVERSE_FINAL_SKU',
    ],
  }

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

  const viewerNegativeActions = [
    ['POST_DELIVERY', validNegativePayload],
    ['POST_RECEIPT', {
      delivery_id: nonexistent, wash_process_id: randomUUID(),
      physical_at: '2026-09-01T12:00:00Z', reason: 'CP6 viewer receipt denial',
      lines: [{ delivery_batch_size_line_id: randomUUID(), qty_good_received: 1,
        qty_bs_laundry: 0, bs_product_id: null }],
    }],
    ['POST_FAILED_WASH', {
      delivery_id: nonexistent, wash_process_id: randomUUID(),
      custody_outcome: 'RETRY_AT_VENDOR', physical_at: '2026-09-01T12:00:00Z',
      reason: 'CP6 viewer failed wash denial',
      lines: [{ delivery_batch_size_line_id: randomUUID(), qty_attempted_pcs: 1 }],
    }],
    ['POST_FINAL_SKU', {
      cutting_group_id: nonexistent, destination_location_id: randomUUID(),
      physical_at: '2026-09-01T13:00:00Z', reason: 'CP6 viewer Final SKU denial',
      good_qty_pcs: 1, completion_mode: 'ALL_READY',
      lines: [{ final_product_id: randomUUID(), qty_good_pcs: 1, qty_bs_pcs: 0,
        source_laundry_receipt_line_id: randomUUID(),
        source_laundry_receipt_batch_size_line_id: randomUUID() }],
    }],
    ['REVERSE_DELIVERY', { delivery_id: nonexistent, reason: 'CP6 viewer delivery reversal denial' }],
    ['REVERSE_RECEIPT', { receipt_id: nonexistent, reason: 'CP6 viewer receipt reversal denial' }],
    ['REVERSE_FINAL_SKU', { qc_inspection_id: nonexistent, reason: 'CP6 viewer QC reversal denial' }],
  ]
  const viewerRequestIds = []
  for (const [actionName, payload] of viewerNegativeActions) {
    const viewerRequestId = randomUUID()
    viewerRequestIds.push(viewerRequestId)
    requestIds.push(viewerRequestId)
    const viewerMutation = await rpc(
      'erp_save_laundry_qc_action_v1', viewerSession.accessToken, {
        p_action: actionName, p_payload: payload,
        p_client_request_id: viewerRequestId, p_expected_version: 1,
      },
    )
    recordFacadeRole('erp_save_laundry_qc_action_v1', viewerSession.label, 'DENY',
      viewerMutation, [400, 401, 403], `action=${actionName};valid-shape`)
    assert.match(viewerMutation.text,
      /PERMISSION_DENIED|production\.(laundry|final_sku)\.(create|post|reverse)/i)
  }
  positiveEvidence.viewer_denied_action_kinds = viewerNegativeActions
    .map(([actionName]) => actionName)

  const unauthenticatedMutationRequestIds = []
  for (const session of [null, unmappedSession, inactiveSession]) {
    const role = session?.label || 'anonymous'
    const deniedRequestId = randomUUID()
    unauthenticatedMutationRequestIds.push(deniedRequestId)
    requestIds.push(deniedRequestId)
    const response = await rpc('erp_save_laundry_qc_action_v1', session?.accessToken, {
      p_action: 'POST_DELIVERY', p_payload: validNegativePayload,
      p_client_request_id: deniedRequestId, p_expected_version: 1,
    })
    recordFacadeRole('erp_save_laundry_qc_action_v1', role, 'DENY', response,
      [400, 401, 403, 404], 'action=POST_DELIVERY;valid-shape')
    assert.notEqual(response.status, 200)
  }

  const operatorRequestId = randomUUID()
  requestIds.push(operatorRequestId)
  const operatorMutation = await rpc('erp_save_laundry_qc_action_v1', operatorSession.accessToken, {
    p_action: 'POST_DELIVERY', p_payload: validNegativePayload,
    p_client_request_id: operatorRequestId, p_expected_version: 1,
  })
  recordFacadeRole('erp_save_laundry_qc_action_v1', operatorSession.label,
    'AUTHORIZED_DOMAIN_REJECTION', operatorMutation, [400, 409],
    'action=POST_DELIVERY;nonexistent-authoritative-source')
  assert.match(operatorMutation.text, /Authoritative POSTED distribution batch was not found/)
  assert.doesNotMatch(operatorMutation.text, /PERMISSION_DENIED|Internal ERP access required/i)

  for (const table of [
    'laundry_delivery_batch_size_lines', 'laundry_receipt_batch_size_lines',
    'laundry_failed_wash_attempts', 'laundry_failed_wash_batch_size_lines',
  ]) {
    const direct = await request(`${restPrefix}/${table}?select=id&limit=1`, {
      token: operatorSession.accessToken,
    })
    record(`rest-direct-${table}-denied`, direct, [401, 403, 404])
  }

  const privateWriterRequestId = randomUUID()
  requestIds.push(privateWriterRequestId)
  const privateWriterBody = {
    p_action: 'POST_DELIVERY',
    p_payload: validNegativePayload,
    p_client_request_id: privateWriterRequestId,
    p_expected_version: 1,
  }
  const privateWriter = await rpc(
    'save_laundry_qc_action_v1', operatorSession.accessToken, privateWriterBody,
  )
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

  // Expose `erp` only on the disposable proof PostgREST instance and prove
  // that schema selection still cannot bypass private function ACLs. A 404
  // through the public schema alone is not sufficient defense-in-depth proof.
  const privateProfiles = [
    ['save_laundry_qc_action_v1', privateWriterBody],
    ['reverse_laundry_delivery', {
      p_delivery_id: randomUUID(), p_reason: 'CP6 private-schema denial',
    }],
    ['reverse_laundry_receipt', {
      p_receipt_id: randomUUID(), p_reason: 'CP6 private-schema denial',
    }],
    ['reverse_qc', {
      p_qc_id: randomUUID(), p_reason: 'CP6 private-schema denial',
    }],
    ['post_vendor_invoice', { p_invoice_id: randomUUID() }],
    ['reverse_vendor_invoice', {
      p_invoice_id: randomUUID(), p_reason: 'CP6 private-schema denial',
    }],
  ]
  const privateProfileStatuses = {}
  for (const [name, body] of privateProfiles) {
    const response = await privateRpc(name, operatorSession.accessToken, body)
    const observedStatus = record(`rpc-explicit-erp-schema-${name}-denied`, response, [401, 403, 404, 406])
    assert.notEqual(response.status, 200, `${name} became executable through private schema`)
    privateProfileStatuses[name] = observedStatus
  }
  const privateAcl = JSON.parse(sql(`select jsonb_build_object(
    'save_writer',has_function_privilege('authenticated',
      'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','EXECUTE'),
    'reverse_delivery',has_function_privilege('authenticated',
      'erp.reverse_laundry_delivery(uuid,text)','EXECUTE'),
    'reverse_receipt',has_function_privilege('authenticated',
      'erp.reverse_laundry_receipt(uuid,text)','EXECUTE'),
    'reverse_qc',has_function_privilege('authenticated',
      'erp.reverse_qc(uuid,text)','EXECUTE'),
    'post_invoice',has_function_privilege('authenticated',
      'erp.post_vendor_invoice(uuid)','EXECUTE'),
    'reverse_invoice',has_function_privilege('authenticated',
      'erp.reverse_vendor_invoice(uuid,text)','EXECUTE')
  );`))
  assert.ok(Object.values(privateAcl).every((allowed) => allowed === false),
    `Private ERP ACL unexpectedly executable: ${JSON.stringify(privateAcl)}`)
  privateSchemaEvidence = {
    schema_profile_requested: 'erp',
    http_statuses: privateProfileStatuses,
    authenticated_execute_acl: privateAcl,
  }

  assert.equal(sql(`select count(*) from erp.idempotency_requests
    where client_request_id in(${[
      ...viewerRequestIds, ...unauthenticatedMutationRequestIds,
      ...dedicatedDeniedRequestIds, operatorRequestId,
    ]
      .map((value) => `'${value}'::uuid`).join(',')})`), '0')
  assert.equal(sql('select count(*) from erp.cp6_laundry_qc_execution_context'), '0')
  assert.equal(sql(`select count(*) from erp.laundry_deliveries
    where id='${nonexistent}'::uuid or special_instruction like 'CP6 ${safeRunId}%'`), '0')
} catch (error) {
  failure = error
} finally {
  // Business facts are never hand-deleted. The workflow destroys the exact
  // physical clone and proves pg_database residue zero after this process.
  if (!disposableDatabase) {
    try { cleanupDatabase() } catch (error) { failure ||= error }
  }
  try { await cleanupAuth() } catch (error) { failure ||= error }
}

let residue
try {
  const authResidue = JSON.parse(authSql(`select jsonb_build_object(
    'auth_users',(select count(*) from auth.users where ${uuidCondition('id', users.map((u) => u.id))}),
    'auth_identities',(select count(*) from auth.identities where ${uuidCondition('user_id', users.map((u) => u.id))}),
    'auth_sessions',(select count(*) from auth.sessions where ${uuidCondition('user_id', users.map((u) => u.id))}),
    'auth_refresh_tokens',(select count(*) from auth.refresh_tokens where ${textUuidCondition('user_id', users.map((u) => u.id))})
  );`))
  const cloneTransientResidue = JSON.parse(sql(`select jsonb_build_object(
    'execution_context',(select count(*) from erp.cp6_laundry_qc_execution_context),
    'in_progress_idempotency',(select count(*) from erp.idempotency_requests
      where status='IN_PROGRESS' and ${uuidCondition('client_request_id', requestIds)}),
    'unbalanced_journals',(select count(*) from(
      select e.id from erp.journal_entries e join erp.journal_lines l
        on l.journal_entry_id=e.id
      group by e.id having sum(l.debit)<>sum(l.credit)
    ) x)
  );`))
  residue = { ...authResidue, ...cloneTransientResidue }
} catch (error) {
  failure ||= error
  residue = { residue_query_failed: true }
}

const residueClean = Object.values(residue).every((value) => value === 0)
const report = {
  // J retains the proven Auth boundary while testing the complete final runtime.
  status: failure || !residueClean ? 'FAIL' : 'PASS',
  classification: 'LOCAL_POST_CP6_REAL_AUTH_JWT_HTTP',
  target: 'PHYSICAL_DISPOSABLE_CP6_AUTH_CLONE_AFTER_V2620N',
  disposable_database: disposableDatabase,
  database_disposal_required: true,
  cases,
  facade_role_matrix: facadeRoleMatrix,
  positive_evidence: positiveEvidence,
  private_schema_evidence: privateSchemaEvidence,
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
    operator_positive_delivery_receipt_partial_and_remaining_final_sku: true,
    owner_positive_dedicated_final_sku_and_reverse: true,
    source_bound_product_search_preserves_qc_queue: true,
    valid_source_resolver_role_matrix_final_and_laundry_bs: true,
    dedicated_final_sku_facade_positive_and_denial_matrix: true,
    public_facade_matrix_records_role_expectation_and_http_status: true,
    partial_laundry_hpp_and_wip_conservation: true,
    granular_reverse_permissions_positive: true,
    all_seven_mutation_actions_positive_for_granular_operator: true,
    all_seven_mutation_actions_denied_for_viewer: true,
    direct_cp6_table_denial: true,
    private_cp6_and_invoice_writer_denial: true,
    explicit_private_schema_and_sql_acl_denial: true,
    negative_mutation_transaction_residue_zero: true,
    auth_identity_and_clone_transient_residue_zero: true,
  },
  ...(failure ? { failure: failure instanceof Error ? failure.message : String(failure) } : {}),
}

writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`)
if (report.status !== 'PASS') {
  throw failure || new Error(`CP6 Auth/JWT cleanup residue: ${JSON.stringify(residue)}`)
}

console.log(`CP6 post-install Auth/JWT/HTTP E2E passed: ${cases.length} assertions across ${facadeRoleMatrix.length} facade/role cases; positive post/reverse chain balanced and transient residue zero; physical clone disposal required.`)
