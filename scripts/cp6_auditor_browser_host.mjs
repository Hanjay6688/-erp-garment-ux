// Browser mode of the auditor runtime (independent audit B4, GATE-04/08): the auditor's own Playwright cases against the
// candidate UI of this branch, real Auth and the real public PostgREST, on a committed copy of the installed clone.
// Started by scripts/cp6_auditor_modes.py (run_browser), which makes the copy and its PostgREST container (port 54329)
// and removes both afterwards. Label AUDITOR_SCENARIO: not release evidence, production_go=false.
//
// The auditor's module (AUDITOR_BROWSER_SCRIPT, an ES module) exports
//   export async function cases(ui, today) { return [[caseId, async () => ({ status, ...evidence })], ...] }
// ui gives:
//   ui.origin, ui.api                 the served UI and the loopback API (Auth + public RPC only, as the product uses them)
//   await ui.login(roleCode, opts)    a user created in the stack's real Auth (admin API), bound to erp.app_users with that
//                                     role on the copy, signed in through the real login form in a fresh browser context;
//                                     returns { page, context, user: { id, role }, rpc(name, args) }; opts: label, mobile,
//                                     timezoneId (default Asia/Jakarta)
//   await ui.anonPage(opts)           a fresh context on the login page, nobody signed in
//   await ui.anonRpc(name, args)      the public RPC as anon; rpc() results are { status, body }
//   ui.sql(query)                     psql on the disposable copy (fixtures and read-back only; nothing leaves the job)
//   ui.expect                         Playwright's expect
// Each case returns an object whose status is PASS, FAIL, COUNTEREXAMPLE or INCOMPLETE; a thrown error, another status or
// a non-object is INCOMPLETE; duplicate case ids refuse the run. One JSON line per case is printed
// ({"group":"AUDITOR_BROWSER_<PHASE>","case":...}); keys, passwords and tokens are masked. Every created Auth user is
// deleted, the browser, the UI server and the proxy are stopped.
import assert from 'node:assert/strict'
import { execFileSync, spawn } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import { mkdirSync, writeFileSync } from 'node:fs'
import http from 'node:http'
import { dirname, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { chromium, expect } from '@playwright/test'

const script = process.env.AUDITOR_BROWSER_SCRIPT, db = process.env.AUDITOR_BROWSER_DB_URL, out = process.env.AUDITOR_BROWSER_OUT
const phase = (process.env.AUDITOR_BROWSER_PHASE || 'after').toUpperCase(), today = process.env.AUDITOR_BROWSER_TODAY
const anon = process.env.SUPABASE_ANON_KEY, service = process.env.SUPABASE_SERVICE_ROLE_KEY
assert.ok(script && db && out && anon && service, 'AUDITOR_BROWSER_ENVIRONMENT')
assert.match(db, /\/cp6_auditor_browser$/, 'AUDITOR_BROWSER_ONLY_ON_ITS_COPY')
const origin = 'http://127.0.0.1:4177', api = 'http://127.0.0.1:54328', restPort = 54329, authPort = 54321
const VOCABULARY = ['PASS', 'FAIL', 'COUNTEREXAMPLE', 'INCOMPLETE']
const secrets = [anon, service], users = []
const report = { status: 'INCOMPLETE', label: 'AUDITOR_SCENARIO', mode: 'BROWSER', phase, planned: [], cases: {}, console_errors: [],
  auth_cleanup_failures: [], real_auth: true, product_responses_mocked: false, production_go: false, release_evidence: false }
const save = () => { mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 2) + '\n') }
const mask = value => { if (value) { secrets.push(value); console.log('::add-mask::' + value) } }
function safe(value) {
  let text = typeof value === 'string' ? value : JSON.stringify(value)
  for (const s of secrets) if (s) text = text.replaceAll(s, '[REDACTED]')
  return text.replace(/eyJ[\w-]+\.[\w-]+\.[\w-]+/g, '[JWT]')
}
const sql = query => execFileSync('psql', [db, '-X', '-qAt', '-v', 'ON_ERROR_STOP=1', '-c', query],
  { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()
const literal = value => "'" + String(value).replaceAll("'", "''") + "'"

async function auth(path, body, admin = false, method = 'POST') {
  const key = admin ? service : anon
  const res = await fetch(`http://127.0.0.1:${authPort}/auth/v1/` + path, { method, headers: { apikey: key, Authorization: `Bearer ${key}`,
    'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) })
  const text = await res.text()
  return { status: res.status, body: text ? JSON.parse(text) : {} }
}
async function rpc(token, name, args = {}) {
  const res = await fetch(`http://127.0.0.1:${restPort}/rpc/` + name, { method: 'POST', headers: { apikey: anon,
    Authorization: `Bearer ${token || anon}`, 'Content-Type': 'application/json' }, body: JSON.stringify(args) })
  const text = await res.text()
  let body; try { body = text ? JSON.parse(text) : null } catch { body = text.slice(0, 2000) }
  return { status: res.status, body }
}
async function createUser(role, label) {
  const email = `cp6-auditor-browser-${String(label).toLowerCase()}-${randomUUID()}@example.invalid`
  const password = `Ab!${randomBytes(24).toString('hex')}`
  mask(email); mask(password)
  const created = await auth('admin/users', { email, password, email_confirm: true }, true)
  assert.ok([200, 201].includes(created.status) && created.body.id, `AUDITOR_BROWSER_AUTH_CREATE_${created.status}`)
  const user = { id: created.body.id, email, password, role, label }; users.push(user)
  const bound = sql(`insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
    select gen_random_uuid(),${literal(user.id)},${literal('Auditor browser ' + label)},role_code,id,true
    from erp.app_roles where role_code=${literal(role)} and is_active returning id`)
  assert.ok(bound, `AUDITOR_BROWSER_UNKNOWN_OR_INACTIVE_ROLE_${role}`)
  const session = await auth('token?grant_type=password', { email, password })
  assert.equal(session.status, 200, 'AUDITOR_BROWSER_LOGIN')
  user.token = session.body.access_token; mask(user.token)
  return user
}

let proxy, preview, browser
async function start() {
  proxy = http.createServer((req, res) => {
    const allowed = req.headers.origin === origin
    const cors = allowed ? { 'access-control-allow-origin': origin, vary: 'Origin',
      'access-control-allow-headers': 'authorization,apikey,content-type,x-client-info,x-supabase-api-version,accept-profile,content-profile',
      'access-control-allow-methods': 'GET,POST,PUT,DELETE,OPTIONS' } : {}
    if (req.method === 'OPTIONS') { res.writeHead(allowed ? 204 : 403, cors); res.end(); return }
    const isAuth = req.url.startsWith('/auth/v1/'), isRest = req.url.startsWith('/rest/v1/rpc/')
    if (!isAuth && !isRest) { res.writeHead(404, cors); res.end(); return }
    const headers = { ...req.headers }; delete headers.host; delete headers.origin
    const upstream = http.request({ hostname: '127.0.0.1', port: isAuth ? authPort : restPort, path: isAuth ? req.url : req.url.slice(8),
      method: req.method, headers }, reply => {
      const clean = { ...reply.headers, ...cors }; delete clean['access-control-allow-credentials']
      res.writeHead(reply.statusCode, clean); reply.pipe(res)
    })
    upstream.on('error', () => { if (!res.headersSent) res.writeHead(502, cors); res.end() }); req.pipe(upstream)
  })
  await new Promise((ok, no) => { proxy.once('error', no); proxy.listen(54328, '127.0.0.1', ok) })
  await expect.poll(async () => { try { return (await fetch(`http://127.0.0.1:${restPort}/`)).status } catch { return 0 } }, { timeout: 30000 }).toBe(200)
  const safeEnv = Object.fromEntries(['PATH', 'HOME', 'CI', 'TMPDIR', 'RUNNER_TEMP', 'PLAYWRIGHT_BROWSERS_PATH'].filter(k => process.env[k]).map(k => [k, process.env[k]]))
  execFileSync('npm', ['run', 'build:cp6-disposable'], { env: { ...safeEnv, VITE_ERP_RUNTIME_MODE: 'DISPOSABLE_TEST', VITE_SUPABASE_URL: api,
    VITE_SUPABASE_ANON_KEY: anon }, stdio: ['ignore', 'pipe', 'pipe'] })
  preview = spawn(resolve('node_modules/.bin/vite'), ['preview', '--outDir', 'cp6-ui-build', '--host', '127.0.0.1', '--port', '4177', '--strictPort'],
    { env: safeEnv, stdio: 'ignore' })
  await expect.poll(async () => { try { return (await fetch(origin)).status } catch { return 0 } }, { timeout: 30000 }).toBe(200)
  browser = await chromium.launch()
}
async function context({ mobile = false, timezoneId = 'Asia/Jakarta' } = {}) {
  const ctx = await browser.newContext({ viewport: mobile ? { width: 390, height: 844 } : { width: 1440, height: 1000 }, timezoneId,
    isMobile: mobile, hasTouch: mobile })
  // Only the served UI and the loopback API; nothing else leaves the browser.
  await ctx.route('**/*', route => [origin, api].includes(new URL(route.request().url()).origin) ? route.continue() : route.abort('blockedbyclient'))
  const page = await ctx.newPage(); page.setDefaultTimeout(20000)
  page.on('pageerror', e => report.console_errors.push(safe(e.message).slice(0, 500)))
  return { ctx, page }
}
const ui = {
  origin, api, today, expect, sql,
  async anonPage(opts = {}) { const { ctx, page } = await context(opts); await page.goto(origin); return { page, context: ctx } },
  anonRpc: (name, args) => rpc(null, name, args),
  async login(role, { label = 'auditor', ...opts } = {}) {
    const user = await createUser(role, label)
    const { ctx, page } = await context(opts)
    await page.goto(origin)
    await page.getByLabel('Email akun ERP').fill(user.email); await page.getByLabel('Kata sandi').fill(user.password)
    await page.getByRole('button', { name: 'Masuk', exact: true }).click()
    await expect(page.locator('.top-title strong')).toBeVisible()
    return { page, context: ctx, user: { id: user.id, role }, rpc: (name, args) => rpc(user.token, name, args) }
  },
}

async function main() {
  await start()
  const module = await import(pathToFileURL(resolve(script)).href)
  assert.equal(typeof module.cases, 'function', 'AUDITOR_BROWSER_NEEDS_cases')
  const planned = await module.cases(ui, today)
  assert.ok(Array.isArray(planned), 'AUDITOR_BROWSER_cases_RETURNS_A_LIST')
  report.planned = planned.map(([id]) => id)
  const duplicates = [...new Set(report.planned.filter((id, i) => report.planned.indexOf(id) !== i))]
  if (duplicates.length) { report.error = 'AUDITOR_DUPLICATE_CASE_IDS'; report.duplicates = duplicates; return }
  for (const [id, operation] of planned) {
    let row
    try {
      row = await operation()
      if (!row || typeof row !== 'object' || Array.isArray(row)) row = { status: 'INCOMPLETE', error: 'AUDITOR_CASE_RESULT_NOT_AN_OBJECT', result: safe(row).slice(0, 500) }
    } catch (error) { row = { status: 'INCOMPLETE', error: safe(error?.stack || String(error)).slice(0, 3000) } }
    if (!VOCABULARY.includes(row.status)) row = { ...row, status_outside_vocabulary: row.status, status: 'INCOMPLETE' }
    report.cases[id] = JSON.parse(safe(row))
    console.log(JSON.stringify({ group: 'AUDITOR_BROWSER_' + phase, case: id, ...report.cases[id] }))
    save()
  }
}

try {
  await main()
  const missing = report.planned.filter(id => !(id in report.cases))
  report.missing = missing
  report.status = report.error || missing.length ? 'INCOMPLETE' : 'RUN_COMPLETE'
} catch (error) {
  report.error = safe(error?.stack || String(error)).slice(0, 3000)
} finally {
  try { await browser?.close() } catch { /* recorded by the status */ }
  preview?.kill(); proxy?.close()
  for (const user of users) {
    try { const r = await auth('admin/users/' + user.id, undefined, true, 'DELETE'); if (![200, 204].includes(r.status)) report.auth_cleanup_failures.push(user.label) }
    catch { report.auth_cleanup_failures.push(user.label) }
  }
  if (report.auth_cleanup_failures.length) report.status = 'INCOMPLETE'
  report.users_created = users.length
  save()
  console.log(JSON.stringify({ group: 'AUDITOR_BROWSER_' + phase, planned: report.planned, final: Object.fromEntries(Object.entries(report.cases).map(([k, v]) => [k, v.status])),
    status: report.status, error: report.error, console_errors: report.console_errors.length, users_created: users.length,
    auth_cleanup_failures: report.auth_cleanup_failures }))
}
process.exit(report.status === 'RUN_COMPLETE' ? 0 : 1)
