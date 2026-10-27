import assert from 'node:assert/strict'
import{cases as all,IDS}from'./browser.mjs'
export async function cases(ui,today){const rows=await all(ui,today);assert.deepEqual(rows.map(x=>x[0]),IDS);return[rows[0]]}
