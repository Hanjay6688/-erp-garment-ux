import assert from 'node:assert/strict'
import { createHmac, webcrypto } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { build } from 'esbuild'
import { JSDOM } from 'jsdom'

const origin = 'https://erp-garment-ux-enteng-uji-build-check.zrpf6sbtjb.workers.dev'
const route = origin + '/auth/atur-sandi/'
const issuer = 'https://jxzlajjuuaexiwfjseav.supabase.co/auth/v1'
const email = 'operator@example.test'
const userId = '80000000-0000-4000-a000-000000000001'
const fixtureKey = 'offline-test-signature-only'
const html = await readFile(new URL('index.html', import.meta.url), 'utf8')
const { outputFiles } = await build({
  entryPoints: [fileURLToPath(new URL('page.mjs', import.meta.url))],
  bundle: true, format: 'iife', write: false,
  define: { __UJI_PUBLISHABLE_KEY__: '"offline-publishable-key"' },
})

function signature(input) { return createHmac('sha256', fixtureKey).update(input).digest('base64url') }
function issue(method = 'otp', issued = Math.floor(Date.now() / 1000)) {
  const enc = value => Buffer.from(JSON.stringify(value)).toString('base64url')
  const segments = [enc({ alg: 'HS256', typ: 'JWT' }), enc({
    sub: userId, iss: issuer, aud: 'authenticated', role: 'authenticated', email,
    iat: issued, exp: issued + 3600, amr: [{ method, timestamp: issued }],
  })]
  return [...segments, signature(segments.join('.'))].join('.')
}

function provider() {
  const now = new Date().toISOString()
  const state = {
    user: { id: userId, email, email_confirmed_at: now, recovery_sent_at: now },
    requested: null, changed: 0, loggedOut: 0, reads: 0, throttle: false, updateStatus: 200,
    async fetch(url, options = {}) {
      const endpoint = new URL(typeof url === 'string' || url instanceof URL ? url : url.url)
      assert.equal(endpoint.origin + '/auth/v1', issuer)
      const path = endpoint.pathname.replace('/auth/v1', '')
      const method = options.method || 'GET'
      const headers = new Headers(options.headers)
      const result = (data, status = 200) => new Response(JSON.stringify(data), {
        status, headers: { 'Content-Type': 'application/json', 'X-Supabase-Api-Version': '2024-01-01' },
      })
      if (path === '/recover' && method === 'POST') {
        state.requested = { payload: JSON.parse(options.body), target: endpoint.searchParams.get('redirect_to') }
        if (state.throttle) return result({ code:'over_email_send_rate_limit', message:'Limited' }, 429)
        return result({})
      }
      if (path === '/token' && endpoint.searchParams.get('grant_type') === 'pkce') {
        assert.ok(JSON.parse(options.body).code_verifier)
        return result({ access_token: issue('recovery'), refresh_token: 'legacy-fixture', expires_in: 3600,
          token_type: 'bearer', user: state.user })
      }
      const jwt = (headers.get('Authorization') || '').replace(/^Bearer /, '')
      const parts = jwt.split('.')
      if (parts.length !== 3 || parts[2] !== signature(parts.slice(0,2).join('.'))) {
        return result({ code:'bad_jwt', message:'Invalid grant' }, 401)
      }
      if (path === '/user' && method === 'GET') { state.reads++; return result(state.user) }
      if (path === '/user' && method === 'PUT') {
        assert.equal(options.credentials, 'omit')
        assert.equal(options.referrerPolicy, 'no-referrer')
        assert.equal(options.redirect, 'error')
        assert.equal(JSON.parse(options.body).password, 'Synthetic-Only-19!')
        if (state.updateStatus !== 200) return result({code:'weak_password'}, state.updateStatus)
        state.changed++
        return result(state.user)
      }
      if (path === '/logout' && method === 'POST') {
        assert.equal(endpoint.searchParams.get('scope'), 'local')
        state.loggedOut++
        return new Response(null, { status: 204 })
      }
      throw new Error('Unexpected offline endpoint ' + path)
    },
  }
  return state
}

function openPage(url, server, beforeLoad) {
  const dom = new JSDOM(html, { url, runScripts: 'outside-only' })
  const w = dom.window
  Object.assign(w, { fetch: server.fetch.bind(server), Headers, Request, Response, TextEncoder, TextDecoder, structuredClone })
  Object.defineProperty(w, 'crypto', { value: webcrypto })
  beforeLoad?.(w)
  w.eval(outputFiles[0].text)
  return { dom, w, document:w.document, change:w.document.querySelector('#change'), request:w.document.querySelector('#request') }
}

async function until(predicate) {
  for (let i = 0; i < 150 && !predicate(); i++) await new Promise(r => setTimeout(r, 6))
  assert.ok(predicate(), 'expected page state')
}
function submit(page, form) { form.dispatchEvent(new page.w.Event('submit', {cancelable:true})) }
function enter(page, repeat = 'Synthetic-Only-19!') {
  page.change.elements.password.value = 'Synthetic-Only-19!'
  page.change.elements.repeat.value = repeat
  submit(page, page.change)
}
function link(jwt) {
  return route + '#' + new URLSearchParams({ access_token:jwt, refresh_token:'unused-fixture',
    token_type:'bearer', expires_in:'3600', type:'recovery', sb:'' })
}

test('a request and its recovery can finish in two independent browsers with the shipped SDK', async t => {
  const server = provider()
  const first = openPage(route, server)
  t.after(() => first.w.close())
  first.request.elements.email.value = email
  submit(first, first.request)
  await until(() => first.request.hidden)
  assert.equal(server.requested.target, route)
  assert.equal(server.requested.payload.email, email)
  assert.equal(server.requested.payload.code_challenge, null)
  assert.equal(first.w.localStorage.length, 0)
  const second = openPage(link(issue()), server)
  t.after(() => second.w.close())
  await until(() => !second.change.hidden)
  assert.equal(second.w.location.href, route)
  assert.equal(second.document.querySelector('#identity').textContent, email)
  assert.equal(second.w.localStorage.length + second.w.sessionStorage.length, 0)
  enter(second, 'different')
  assert.equal(server.changed, 0)
  enter(second)
  await until(() => server.loggedOut === 1)
  assert.equal(server.changed, 1)
  assert.equal(second.change.hidden, true)
  assert.match(second.document.title, /Enteng Uji/)
  assert.match(second.document.querySelector('#title').textContent, /sudah tersimpan/)
})

test('old PKCE email still works in its original browser', async t => {
  const server = provider()
  const page = openPage(route + '?code=' + 'a'.repeat(36), server, w =>
    w.localStorage.setItem('atelier-uat-pemulihan-code-verifier', JSON.stringify('test-verifier/recovery')))
  t.after(() => page.w.close())
  await until(() => !page.change.hidden)
  enter(page)
  await until(() => server.loggedOut === 1)
})

test('expired, incomplete, non-recovery and ordinary sessions never show the email form as a silent fallback', async t => {
  const server = provider()
  for (const suffix of ['?code=' + 'a'.repeat(36), '?code=a&code=b', '#error=access_denied&error_code=otp_expired&sb=',
    '#access_token=fixture', '?next=elsewhere', link(issue('password')).slice(route.length),
    link(issue()).slice(route.length).replace('type=recovery','type=signup'),
    link(issue('otp', Math.floor(Date.now()/1000) - 86400)).slice(route.length)]) {
    const page = openPage(route + suffix, server)
    t.after(() => page.w.close())
    await until(() => !page.document.querySelector('#again').hidden)
    assert.equal(page.change.hidden, true)
    assert.equal(page.request.hidden, true)
    assert.equal(page.w.location.href, route)
  }
  assert.equal(server.changed, 0)
})

test('an identity change prevents writing a password and a provider failure never reports success', async t => {
  for (const sameUser of [true, false]) {
    const server = provider()
    const page = openPage(link(issue()), server)
    t.after(() => page.w.close())
    await until(() => !page.change.hidden)
    if (sameUser) server.updateStatus = 422
    else server.user = { ...server.user, id: 'other-user' }
    enter(page)
    await until(() => page.document.querySelector('#status').textContent.length > 0)
    assert.equal(server.changed, 0)
    assert.doesNotMatch(page.document.querySelector('#title').textContent, /sudah tersimpan/)
  }
})

test('a mail rate limit never reports a successful delivery', async t => {
  const server = provider()
  server.throttle = true
  const page = openPage(route, server)
  t.after(() => page.w.close())
  page.request.elements.email.value = email
  submit(page, page.request)
  await until(() => /membatasi/.test(page.document.querySelector('#status').textContent))
  assert.equal(page.request.hidden, false)
})
