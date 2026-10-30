import assert from 'node:assert/strict'
import {test} from 'node:test'
import {spawnSync} from 'node:child_process'
import {observeResponseWaits} from './response_waits.mjs'

test('response observer preserves promise, response, predicate, receiver and restoration', async () => {
  const response = {status: 200}, pending = Promise.resolve(response), predicate = () => true
  const page = {waitForResponse(...args) { assert.equal(this, page); assert.deepEqual(args, [predicate]); return pending }}
  const original = page.waitForResponse, stop = observeResponseWaits(page)
  assert.equal(page.waitForResponse(predicate), pending)
  assert.equal(await pending, response)
  stop(); assert.equal(page.waitForResponse, original)
})

test('response rejection and synchronous exceptions still fail their caller', async () => {
  const error = new Error('ACTUAL_RESPONSE_FAILURE'), pending = Promise.reject(error)
  const page = {waitForResponse() { return pending }}
  const stop = observeResponseWaits(page)
  await assert.rejects(page.waitForResponse(), actual => actual === error)
  stop()
  const sync = {waitForResponse() { throw error }}
  const restore = observeResponseWaits(sync)
  assert.throws(() => sync.waitForResponse(), actual => actual === error)
  restore()
})

test('old timeout race kills cleanup; observed original rejection keeps failure and reaches cleanup', () => {
  const url = new URL('./response_waits.mjs', import.meta.url).href
  function run(observe) {
    const script = `
      import {setTimeout as delay} from 'node:timers/promises';
      import {observeResponseWaits} from ${JSON.stringify(url)};
      const page={waitForResponse(){return new Promise((_,reject)=>setTimeout(()=>reject(new Error('PAGE_CLOSED')),1))}};
      ${observe ? 'observeResponseWaits(page);' : ''}
      let failed=false;
      try {const response=page.waitForResponse();await delay(30);await response}
      catch(error){failed=error.message==='PAGE_CLOSED'}
      finally{console.log(JSON.stringify({case:failed?'INCOMPLETE':'WRONG',cleanup_reached:true}));process.exitCode=1}
    `
    return spawnSync(process.execPath, ['--unhandled-rejections=strict', '--input-type=module', '-e', script], {encoding: 'utf8'})
  }
  const old = run(false)
  assert.equal(old.status, 1); assert.equal(old.stdout, ''); assert.match(old.stderr, /PAGE_CLOSED/)
  const current = run(true)
  assert.equal(current.status, 1); assert.equal(current.stderr, '')
  assert.deepEqual(JSON.parse(current.stdout), {case: 'INCOMPLETE', cleanup_reached: true})
})
