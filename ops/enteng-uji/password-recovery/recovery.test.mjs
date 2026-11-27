import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { build } from 'esbuild'
import { JSDOM } from 'jsdom'

const origin = 'https://erp-garment-ux-enteng-uji-build-check.zrpf6sbtjb.workers.dev'
const route = origin + '/auth/atur-sandi/'
const html = await readFile(new URL('index.html', import.meta.url), 'utf8')
const { outputFiles } = await build({
  entryPoints: [fileURLToPath(new URL('page.mjs', import.meta.url))],
  bundle: true, format: 'iife', write: false, define: { __UJI_PUBLISHABLE_KEY__: '"public-test-key"' },
  plugins: [{ name: 'offline-auth', setup(plugin) {
    plugin.onResolve({ filter: /^@supabase\/supabase-js$/ }, () => ({ path: 'client', namespace: 'fixture' }))
    plugin.onLoad({ filter: /.*/, namespace: 'fixture' }, () => ({ contents: 'export const createClient = window.authFixture' }))
  } }],
})
const settle = () => new Promise(resolve => setImmediate(resolve))

function page(url, auth) {
  const dom = new JSDOM(html, { url, runScripts: 'outside-only' })
  const w = dom.window
  w.authFixture = (_project, _key, opts) => {
    assert.equal(opts.auth.flowType, 'pkce')
    assert.equal(opts.auth.detectSessionInUrl, false)
    const storage = opts.auth.storage
    storage.setItem('atelier-uat-pemulihan', 'offline-session')
    assert.equal(w.localStorage.getItem('atelier-uat-pemulihan'), null)
    return { auth }
  }
  w.eval(outputFiles[0].text)
  return { document:w.document, submit:form => form.dispatchEvent(new w.Event('submit',{cancelable:true})), close:() => w.close() }
}

test('sends recovery to the exact callback for the entered email', async () => {
  let call
  const ui = page(route, { async resetPasswordForEmail(...args) { call=args; return { error:null } } })
  const request = ui.document.querySelector('#request')
  request.elements.email.value = 'operator@example.test'
  ui.submit(request); await settle()
  assert.deepEqual([...call.slice(0,1)], ['operator@example.test'])
  assert.equal(call[1].redirectTo, route)
  assert.equal(request.hidden, true)
  ui.close()
})

test('only a matching recovery identity can change its password', async () => {
  const code = 'a'.repeat(36)
  const user = { id:'test-id', email:'operator@example.test' }
  for (const same of [true,false]) {
    let updates=0
    const ui = page(route + '?code=' + code, {
      async exchangeCodeForSession(value) { assert.equal(value,code); return { data:{ session:{}, user, redirectType:'recovery' } } },
      async getUser() { return { data:{ user: same ? user : { id:'other-test-id' } } } },
      async updateUser() { updates++; return { data:{ user } } },
      async signOut() {},
    })
    await settle()
    assert.equal(ui.document.location.search,'')
    const form=ui.document.querySelector('#change')
    assert.equal(form.hidden,false)
    form.elements.password.value = 'Synthetic-Only-19!'
    form.elements.repeat.value = 'different'
    ui.submit(form); await settle()
    assert.equal(updates,0)
    form.elements.repeat.value = form.elements.password.value
    ui.submit(form); await settle()
    assert.equal(updates,Number(same))
    assert.equal(form.hidden,true)
    ui.close()
  }
})

test('invalid fragments and duplicate codes are discarded without exchange', async () => {
  for (const suffix of ['#access_token=fixture','?code=a&code=b','?next=elsewhere']) {
    const ui=page(route+suffix,{})
    await settle()
    assert.equal(ui.document.location.href,route)
    assert.equal(ui.document.querySelector('#change').hidden,true)
    assert.equal(ui.document.querySelector('#request').hidden,false)
    ui.close()
  }
})

test('an ordinary sign-in callback cannot set a password', async () => {
  const ui=page(route+'?code='+'x'.repeat(36),{
    async exchangeCodeForSession() { return {data:{ user:{id:'test'}, session:{},redirectType:null }} },
    async signOut() {},
  })
  await settle()
  assert.equal(ui.document.querySelector('#change').hidden,true)
  assert.equal(ui.document.querySelector('#request').hidden,false)
  ui.close()
})
