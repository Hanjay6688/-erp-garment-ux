// Exact compiled application CSS, minimal markup copied from the two panels.
// This is a paint diagnostic only: no Auth, DB, write or journey PASS.
import assert from 'node:assert/strict'
import {readFileSync,readdirSync,writeFileSync}from 'node:fs'
import {resolve}from 'node:path'
import {createHash}from 'node:crypto'
import {chromium}from '@playwright/test'
import {readable}from '../current-vendor-money-browser/visual.mjs'

const root=resolve('cp7-paint-preflight-build/assets')
const cssFiles=readdirSync(root).filter(p=>p.endsWith('.css')).sort()
assert.ok(cssFiles.length>0)
const css=cssFiles.map(p=>readFileSync(resolve(root,p),'utf8')).join('\n')
const report={kind:'ACTUAL_CHROMIUM_COMPILED_CSS_PAINT_ONLY',Auth:false,database:false,actual_journey_credit:0,production_go:false,
 source_head:process.env.GITHUB_SHA,css:cssFiles.map(p=>({path:p,sha256:createHash('sha256').update(readFileSync(resolve(root,p))).digest('hex')})),cases:[]}
const browser=await chromium.launch({headless:true})
try{
 for(const width of[1440,390]){
  const page=await browser.newPage({viewport:{width,height:1000}})
  await page.setContent('<!doctype html><html><head></head><body><div id="root"><div class="app"><main class="workspace">'+
   '<section class="connected-laundry-qc-page"><section class="clq-history"><article data-qc-inspection-id="paint-only"><div class="clq-reversal"><span><small>KOREKSI TRANSAKSI TERSIMPAN</small><strong>Penjualan dan penyesuaian masih memakai stok ini</strong></span><input disabled value="Alasan pembatalan"><button disabled>Batalkan finalisasi</button></div></article></section></section>'+
   '<section class="initial-import"><section class="panel" aria-label="Cuci gagal harga belum diketahui"><p>Belum diketahui · biaya belum dihitung · HPP belum final</p><button disabled>Isi harga cuci gagal LAUNDRY-PAINT</button></section></section>'+
   '</main></div></div></body></html>')
  await page.addStyleTag({content:css})
  for(const[scope,selector]of[['QC_DISABLED_REVERSAL','[data-qc-inspection-id="paint-only"]'],['WASH_DISABLED_PRICING','[aria-label="Cuci gagal harga belum diketahui"]']]){
   const box=page.locator(selector);const button=box.getByRole('button');assert.equal(await button.isDisabled(),true)
   const computed=await button.evaluate(e=>{const s=getComputedStyle(e);return{color:s.color,background:s.backgroundColor,opacity:s.opacity,disabled:e.disabled}})
   let rows=[],error=null
   try{rows=await readable(box)}catch(e){error=String(e);try{rows=JSON.parse(e.message)}catch{}}
   report.cases.push({scope,width,computed,passes_prepared_4_5_oracle:error===null,rows,error})
  }
  await page.close()
 }
}finally{await browser.close()}
writeFileSync('CP7_OW08_PAINT_PREFLIGHT.json',JSON.stringify(report,null,2)+'\n',{flag:'wx'})
console.log(JSON.stringify({kind:report.kind,cases:report.cases.map(r=>({scope:r.scope,width:r.width,passes_prepared_4_5_oracle:r.passes_prepared_4_5_oracle,minimum_ratio:Math.min(...r.rows.map(x=>x.ratio)),computed:r.computed})),actual_journey_credit:0}))
assert.ok(report.cases.every(r=>r.passes_prepared_4_5_oracle),'OW08_PREPARED_PAINT_ORACLE_NOT_MET_SEE_ORIGINAL_REPORT')
