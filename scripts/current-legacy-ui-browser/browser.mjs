// Retain the existing complete migration UI composition and every assertion.
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {cases as retained} from '../cp7_prefreeze_legacy_browser.mjs'
const expected=JSON.parse(readFileSync(new URL('./EXPECTED.json',import.meta.url),'utf8')).case_ids
export async function cases(ui,today){
 const all=await retained(ui,today)
 assert.deepEqual(all.map(([id])=>id),expected)
 assert.equal(all.length,31)
 return all
}
