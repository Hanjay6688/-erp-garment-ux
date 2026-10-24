import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {cases as lists} from '../ab-quote-browser-qualification/browser.mjs'
import {cases as correction} from '../ow05-browser-qualification/browser.mjs'
import {cases as guidance} from '../ow05b-browser-qualification/browser.mjs'
import {cases as transfer} from '../ow06-browser-qualification/browser.mjs'
const expected=JSON.parse(readFileSync(new URL('./EXPECTED.json',import.meta.url),'utf8')).case_ids
export async function cases(ui,today){
 const all=[]
 for(const family of [lists,correction,guidance,transfer])all.push(...await family(ui,today))
 assert.deepEqual(all.map(([id])=>id),expected)
 assert.equal(new Set(expected).size,19)
 return all
}
