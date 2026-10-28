import assert from 'node:assert/strict'
import test from 'node:test'
import {gradientBounds,boundedTextContrast}from './gradient.mjs'
import {renderedTextContrast}from './visual.mjs'
const black={color:[0,0,0],opacity:1}
const panel={color:[0,0,0,0],opacity:1,backgroundImage:'linear-gradient(145deg, rgba(21, 26, 42, 0.91), rgba(14, 18, 29, 0.94))'}
const body={color:[10,12,20],opacity:1,backgroundImage:'radial-gradient(at 76% -20%, rgba(98, 111, 221, 0.14), rgba(0, 0, 0, 0) 30%)'}
const bound=(f,l)=>boundedTextContrast(f,l,renderedTextContrast)
test('opaque solid measurements remain exact',()=>assert.deepEqual(bound([255,255,255],[black]),renderedTextContrast([255,255,255],[black])))
test('transparent stops are premultiplied and enclose every interpolation',()=>{
 const b=gradientBounds(body.backgroundImage)
 for(let i=0;i<=1000;i++){const t=i/1000;for(const[k,x]of[98*.14*t,111*.14*t,221*.14*t,.14*t].entries())assert.ok(x>=b.lo[k]-1e-12&&x<=b.hi[k]+1e-12)}
})
test('actual page gradients give a conservative readable bound for normal text',()=>{
 const b=bound([244,246,251],[panel,body]);assert.ok(b.ratio>15);assert.equal(b.contributing_gradients,2)
})
test('low contrast still fails and overlap inside a gradient cannot pass from endpoints',()=>{
 assert.ok(bound([233,239,248],[{color:[32,51,79],opacity:.5},panel,body]).ratio<4.5)
 assert.equal(bound([128,128,128],[{color:[0,0,0],opacity:1,backgroundImage:'linear-gradient(90deg, rgb(0, 0, 0), rgb(255, 255, 255))'}]).ratio,1)
})
test('unknown images, non-sRGB interpolation and incomplete gradients stay refused',()=>{
 for(const image of['url(example.png)','linear-gradient(in oklab, rgb(0, 0, 0), rgb(255, 255, 255))','linear-gradient(90deg, color(display-p3 1 0 0), rgb(0, 0, 0))','linear-gradient(90deg, rgb(0, 0, 0))','linear-gradient(...),url(example.png)'])assert.throws(()=>gradientBounds(image),/UNMEASURED/)
})
test('unknown images behind fully opaque text and background remain irrelevant',()=>assert.equal(bound([255,255,255],[black,{color:[0,0,0,0],opacity:1,backgroundImage:'url(example.png)'}]).ratio,21))
test('gradient enclosures contain dense independent exact nested-opacity samples',()=>{
 const b=bound([220,230,240],[{color:[20,40,60],opacity:.7},panel,body])
 for(let i=0;i<=80;i++)for(let j=0;j<=80;j++){
  const t=i/80,a=.91*(1-t)+.94*t,p=[21,26,42].map((x,k)=>(x*.91*(1-t)+[14,18,29][k]*.94*t)/a)
  const exact=renderedTextContrast([220,230,240],[{color:[20,40,60],opacity:.7},{color:[...p,a],opacity:1},{color:[98,111,221,.14*j/80],opacity:1},body.color?{color:body.color,opacity:1}:black])
  assert.ok(exact.ratio>=b.ratio&&exact.ratio<=b.ratio_upper_bound)
  for(const[k,v]of exact.foreground.entries())assert.ok(v>=b.foreground_range.min[k]&&v<=b.foreground_range.max[k])
  for(const[k,v]of exact.background.entries())assert.ok(v>=b.background_range.min[k]&&v<=b.background_range.max[k])
 }
})
test('opaque disabled button text stays readable without changing native disabled behavior',()=>assert.ok(bound([233,239,248],[{color:[32,51,79],opacity:1},panel,body]).ratio>=4.5))
