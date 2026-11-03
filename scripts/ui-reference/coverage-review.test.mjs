import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {expectedKeys,validateCoverage} from './coverage-review.mjs'
const config=JSON.parse(fs.readFileSync('scripts/ui-reference/FAMILIES.json'))
const views=expectedKeys(config).map(k=>{const [variant,surface,width]=k.split('/');return {variant,surface,width:Number(width)}})
test('exact route/dialog/state/width matrix accepts 323 identities; WIP is not a popup',()=>{const result=validateCoverage(views,config);assert.equal(result.actual,323);assert.equal(result.dialog_views,36);assert(views.some(x=>x.surface==='mandor-wip'))})
test('missing actual page view is refused',()=>assert.throws(()=>validateCoverage(views.slice(1),config)))
test('duplicate view cannot conceal missing identity',()=>assert.throws(()=>validateCoverage([views[0],...views.slice(0,-1)],config)))
test('wrong state identity cannot satisfy same count',()=>assert.throws(()=>validateCoverage(views.map((v,i)=>i? v:{...v,surface:'mandor-invented'}),config)))
