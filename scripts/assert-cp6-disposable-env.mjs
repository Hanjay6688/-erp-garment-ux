import assert from 'node:assert/strict'
import { assertNoForbiddenBuildSecrets } from './build-preflight.mjs'

assertNoForbiddenBuildSecrets()
assert.equal(process.env.VITE_ERP_RUNTIME_MODE, 'DISPOSABLE_TEST')
const port=process.env.VITE_DISPOSABLE_API_PORT||'54328'
assert.ok(/^[1-9][0-9]{4}$/.test(port)&&Number(port)>=32768&&Number(port)<=65535&&!['54321','54322','54323','54329'].includes(port),'Exact disposable loopback proxy port required')
assert.equal(process.env.VITE_SUPABASE_URL, 'http://127.0.0.1:'+port)
assert.equal(process.env.VITE_SUPABASE_PUBLISHABLE_KEY || '', '')
const key = process.env.VITE_SUPABASE_ANON_KEY || ''
let payload
try { payload = JSON.parse(Buffer.from(key.split('.')[1], 'base64url').toString()) } catch { /* fail below without printing key */ }
assert.ok(payload?.role === 'anon' && (payload.ref === undefined || payload.ref === 'local'), 'Disposable local anon key required')
console.log('PASS disposable build environment: exact declared loopback proxy, local anon only, no server credentials')
