import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const read = (path) => readFileSync(path, 'utf8')
const hook = read('src/useProductionMutation.ts')
const storage = read('src/productionRecovery.ts')
for (const token of [
  'busyRef.current', '!readyRef.current', 'sessionRef.current !== session',
  "mode: 'exclusive', ifAvailable: true", 'current.signature !== readySignature.current',
  'if (!input || !isDefiniteInitialRejection(result.error))',
  'handlers.validate(result.data, envelope)', 'handlers.retire(result.data, envelope)',
  'clearProductionEnvelope(scope, domain, envelope)', 'await handlers.reload()',
]) assert.ok(hook.includes(token), `Shared production recovery guard missing: ${token}`)
assert.ok(hook.indexOf('handlers.retire(result.data, envelope)') < hook.lastIndexOf('await handlers.reload()'), 'Committed forms must retire before refresh')
for (const token of [
  "'erp.cp5'", "'erp.cp6'", 'pending-mutation.v1:', 'erp.production.revision.v1:',
  'value.fingerprint !== JSON.stringify', 'current?.id !== envelope.id',
  'current.fingerprint !== envelope.fingerprint', "globalThis.addEventListener('storage'",
]) assert.ok(storage.includes(token), `Shared production storage contract missing: ${token}`)
for (const [path, domain] of [
  ['src/ConnectedBsResolutionPage.tsx', 'BS'], ['src/ConnectedCuttingPage.tsx', 'CUTTING'],
  ['src/ConnectedPickupPage.tsx', 'PICKUP'], ['src/ConnectedWipStatusPage.tsx', 'WIP'],
  ['src/useLaundryQcWorkspace.ts', 'LAUNDRY_QC'],
  ['src/ConnectedInitialImportPage.tsx', 'INITIAL_IMPORT'],
  ['src/ConnectedPocketFabricPage.tsx', 'POCKET_FABRIC'],
]) {
  const source = read(path)
  assert.ok(source.includes(`useProductionMutation('${domain}')`), `${path} bypasses shared recovery`)
  for (const token of ['beginRead()', 'finishRead(ticket)', 'p_client_request_id: envelope.id', 'p_payload: envelope.payload']) {
    assert.ok(source.includes(token), `${path} omits ${token}`)
  }
  assert.doesNotMatch(source, /p_client_request_id:\s*globalThis\.crypto\.randomUUID/, `${path} bypasses persistent UUID`)
}
for (const path of ['src/ConnectedCuttingPage.tsx', 'src/ConnectedPickupPage.tsx', 'src/ConnectedBsResolutionPage.tsx']) {
  assert.doesNotMatch(read(path), /event\.target\.value\.replace\(/, `${path} silently rewrites numeric input`)
}
console.log('Production recovery ownership passed: seven connected writer domains, exact envelope, shared lock and stale-read generation.')
