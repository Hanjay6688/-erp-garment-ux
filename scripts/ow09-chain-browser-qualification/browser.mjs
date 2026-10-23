import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {cases as cash} from '../cp7_f03_cash_browser.mjs'
import {cases as sales} from '../cp7_p11_returns_browser.mjs'
import {cases as fg} from '../cp7_p10_browser.mjs'
import {cases as nota} from '../cp7_p12_browser.mjs'
import {cases as procurement} from '../cp7_p09_browser.mjs'
import {cases as accessory} from '../cp6_bc_browser.mjs'
const expected=JSON.parse(readFileSync(new URL('./EXPECTED.json',import.meta.url),'utf8')).case_ids
export async function cases(ui,today){
 const all=[]
 for(const family of [cash,sales,fg,nota,procurement,accessory])all.push(...await family(ui,today))
 const selected=expected.map(id=>{
  const matches=all.filter(([name])=>name===id)
  assert.equal(matches.length,1,`Expected one retained case ${id}`)
  return matches[0]
 })
 assert.equal(new Set(selected.map(([id])=>id)).size,expected.length)
 return selected
}
