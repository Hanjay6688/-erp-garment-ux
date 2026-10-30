// Existing normal full-App journeys; no response fixtures or alternate host.
import assert from 'node:assert/strict'
import {cases as sku,IDS as SKU} from './browser.mjs'
import {cases as ai,IDS as AI} from './staged_ai_cases.mjs'
export const IDS=Object.freeze([...SKU,...AI])
export async function cases(ui,today){
  const planned=[...await sku(ui,today),...await ai(ui,today)]
  assert.equal(planned.length,4);assert.equal(new Set(planned.map(([id])=>id)).size,4)
  assert.deepEqual(planned.map(([id])=>id),IDS)
  return planned
}
