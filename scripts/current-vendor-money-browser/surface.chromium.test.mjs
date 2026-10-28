// Cheap real-Chromium CSS-instrument preflight before the 30-minute installer.
// This is a paint fixture, never an Auth/backend/money/browser-journey PASS.
import assert from 'node:assert/strict'
import test from 'node:test'
import {chromium}from '@playwright/test'
import {readable}from './visual.mjs'

test('actual Chromium normal lists, none layers, opacity and negative surfaces',async()=>{
 const browser=await chromium.launch({headless:true})
 try{
  const page=await browser.newPage();await page.setContent(`<!doctype html><style>
   html{background:rgb(10,12,20)}body{color:rgb(244,246,251);background-color:rgb(10,12,20);background-image:radial-gradient(circle at 76% -20%,rgba(98,111,221,.14),rgba(0,0,0,0) 30%),none}
   section{background:linear-gradient(145deg,rgba(21,26,42,.91),rgba(14,18,29,.94));padding:20px}
   button{color:rgb(233,239,248);background:rgb(32,51,79);opacity:1}
   </style><section aria-label="Paint fixture"><p>Kredit klaim yang sudah disetujui boleh memotong tagihan vendor yang sama yang belum lunas</p><button disabled>Catat uang diterima dari vendor</button></section>`)
  const box=page.getByRole('region',{name:'Paint fixture',exact:true})
  const actual=await page.evaluate(()=>({image:getComputedStyle(document.body).backgroundImage,blend:getComputedStyle(document.body).backgroundBlendMode}))
  assert.match(actual.image,/, none$/);assert.equal(actual.blend,'normal, normal')
  const rows=await readable(box);assert.ok(rows.length>=2&&rows.every(r=>r.ratio>=4.5));assert.equal(await box.getByRole('button').isDisabled(),true)
  await page.evaluate(()=>document.body.style.backgroundBlendMode='normal, multiply')
  await assert.rejects(()=>readable(box),/UNMEASURED_FINANCE_TEXT_SURFACE/)
  await page.evaluate(()=>{document.body.style.backgroundBlendMode='normal, normal';document.querySelector('button').style.opacity='.3'})
  await assert.rejects(()=>readable(box),/AssertionError/)
  await page.evaluate(()=>{document.querySelector('button').style.opacity='1';document.body.style.filter='brightness(.9)'})
  await assert.rejects(()=>readable(box),/UNMEASURED_FINANCE_TEXT_SURFACE/)
  await page.close()
 }finally{await browser.close()}
})
