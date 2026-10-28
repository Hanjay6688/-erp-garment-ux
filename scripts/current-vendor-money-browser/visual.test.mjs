import assert from 'node:assert/strict'
import test from 'node:test'
import {renderedTextContrast as contrast} from './visual.mjs'
const black={color:[0,0,0],opacity:1}
test('opaque white on black preserves WCAG contrast 21',()=>assert.equal(contrast([255,255,255],[black]).ratio,21))
test('half-opacity text composites to gray on the actual black parent',()=>{
 const x=contrast([255,255,255],[{color:[0,0,0,0],opacity:.5},black])
 assert.deepEqual(x.foreground,[127.5,127.5,127.5]);assert.deepEqual(x.background,[0,0,0]);assert.ok(Math.abs(x.ratio-5.280822809644651)<1e-12)
})
test('group opacity composites text and its own background separately',()=>{
 const x=contrast([255,255,255],[{color:[100,100,100],opacity:.5},black])
 assert.deepEqual(x.foreground,[127.5,127.5,127.5]);assert.deepEqual(x.background,[50,50,50]);assert.ok(x.ratio<4.5)
})
test('nested group and foreground alpha both affect the painted pixel',()=>{
 const x=contrast([200,200,200,.5],[{color:[0,0,0,0],opacity:.5},{color:[100,100,100,1],opacity:.5},black])
 assert.deepEqual(x.foreground,[62.5,62.5,62.5]);assert.deepEqual(x.background,[50,50,50])
})
test('unknown canvas or invalid opacity stays refused',()=>{
 assert.throws(()=>contrast([255,255,255],[{color:[0,0,0,0],opacity:1}]),/MISSING_OPAQUE/)
 assert.throws(()=>contrast([255,255,255],[{color:[0,0,0],opacity:NaN}]),/INVALID_TEXT_SURFACE/)
})

test('irrelevant image behind an opaque painted surface does not change pixels',()=>{
 assert.equal(contrast([255,255,255],[black,{color:[0,0,0,0],opacity:1,backgroundImage:'linear-gradient(...)'}]).ratio,21)
})
test('image contributing to a transparent painted surface stays refused',()=>{
 assert.throws(()=>contrast([255,255,255],[{color:[0,0,0,0],opacity:.5},{color:[0,0,0,0],opacity:1,backgroundImage:'linear-gradient(...)'}]),/UNMEASURED_FINANCE_BACKGROUND_IMAGE/)
})
