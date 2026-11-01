// Local CSS counterexample and repair only: no server, Auth, RPC or ERP case credit.
import assert from 'node:assert/strict'
import { chromium } from 'playwright-core'
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { readable } from '../../current-sku-pair-browser-qualification/evidence.mjs'
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const [directory, executablePath, argsFile, widthList='1440,390,320', receiptName='LOCAL_VISUAL_CONTROL.json', fixtureList='variants,zero,empty,no_good'] = process.argv.slice(2)
assert.ok(directory && executablePath && argsFile, 'EXPLICIT_LOCAL_INPUTS_AND_BROWSER_REQUIRED')
const widths=widthList.split(',').map(Number)
const labels=fixtureList.split(',')
assert.ok(widths.length>0&&new Set(widths).size===widths.length&&widths.every(w=>[1440,390,320].includes(w)))
assert.ok(labels.length>0&&new Set(labels).size===labels.length&&labels.every(l=>['variants','zero','empty','no_good'].includes(l)))
assert.match(receiptName,/^LOCAL_VISUAL_[A-Z_]*CONTROL\.json$/)
const sha = x => createHash('sha256').update(x).digest('hex')
const main = readFileSync(resolve(root, 'src/main.tsx'), 'utf8')
const cssPaths = [...main.matchAll(/import '\.\/(.+\.css)'/g)].map(x => 'src/'+x[1])
const globals = cssPaths.map(p => readFileSync(resolve(root, p), 'utf8')).join('\n')
const original = execFileSync('git', ['-C', root, 'show', 'b25eaae55a144aa03cc05f8f77109f5d0b02fbfb:src/accessory-standard-report.css'], {encoding:'utf8'})
const fixed = readFileSync(resolve(root, 'src/accessory-standard-report.css'), 'utf8')
let browser
const report = {status:'INCOMPLETE', browser:null, widths, labels, retained_fixture_visual_adapter:true, actual_ERP_cases:0,
  actual_Auth_cases:0, actual_full_App_cases:0, production_go:false, independent_acceptance:false,
  sources:Object.fromEntries([...cssPaths, 'src/ConnectedAccessoryStandardReportPage.tsx', 'src/accessory-standard-report.css'].map(p=>[p,sha(readFileSync(resolve(root,p)))])),
  original_css_sha256:sha(original), current_css_sha256:sha(fixed), counterexample:{}, cases:[]}
mkdirSync(directory, {recursive:true})
try {
  for (const width of widths) {
    // The standalone local binary uses --single-process. Closing its only
    // context can exit that process; each viewport therefore owns a browser.
    browser=await chromium.launch({executablePath, args:JSON.parse(readFileSync(argsFile,'utf8')),headless:true})
    if(report.browser!==null)assert.equal(browser.version(),report.browser)
    report.browser=browser.version()
    const context=await browser.newContext({viewport:{width,height:900},isMobile:width<500,deviceScaleFactor:1})
    const page=await context.newPage()
    await page.route('**/*',route=>route.abort())
    try {
      for (const kind of ['original','fixed']) for (const label of kind==='original'?['variants']:labels) {
        const html=readFileSync(resolve(directory,label+'.html'),'utf8')
        await page.setContent('<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+globals+'\n'+(kind==='fixed'?fixed:original)+'</style></head><body><div class="app-shell"><aside class="sidebar"></aside><main class="main-panel"><div class="page-wrap">'+html+'</div></main></div></body></html>')
        const panel=page.getByRole('region',{name:'Laporan aksesori mandor',exact:true})
        if (kind==='original') {
          if(width===1440) { let failure;try{await readable(panel)}catch(e){failure=String(e)}assert.match(failure??'',/UNMEASURED_SKU_TEXT_SURFACE/);report.counterexample.desktop=failure }
          if(width===390) {const size=await page.evaluate(()=>({inner:innerWidth,page:document.documentElement.scrollWidth}));assert.ok(size.inner>390||size.page>390,JSON.stringify(size));report.counterexample.mobile390=size}
          continue
        }
        for (const expanded of [false,true]) {
          if(expanded)await panel.locator('details').evaluateAll(elements=>elements.forEach(el=>{el.open=true}))
          const size=await page.evaluate(()=>({inner:innerWidth,page:document.documentElement.scrollWidth}))
          assert.equal(size.inner,width);assert.ok(size.page<=width,JSON.stringify({label,expanded,width,...size}))
          const measured=await readable(panel)
          const controls=await panel.locator('input,select,button').evaluateAll(els=>els.filter(el=>!el.disabled).map(el=>({tag:el.tagName,width:el.getBoundingClientRect().width,parent:el.parentElement.getBoundingClientRect().width})))
          assert.ok(controls.every(el=>el.width<=el.parent+1),JSON.stringify(controls))
          const path=resolve(directory,`${label}-${width}-${expanded?'sources':'summary'}.png`)
          await page.screenshot({path,fullPage:true})
          report.cases.push({label,width,expanded,status:'PASS',size,min_text_contrast:Math.min(...measured.rows.map(x=>x.ratio)),measured_text_nodes:measured.rows.length,screenshot:path.split('/').at(-1)})
        }
      }
    }finally{await context.close();await browser.close();browser=null}
  }
  assert.equal(report.cases.length,widths.length*labels.length*2);report.status='PASS'
}catch(e){report.error=String(e.stack||e);throw e}
finally{writeFileSync(resolve(directory,receiptName),JSON.stringify(report,null,2)+'\n');await browser?.close()}
console.log(JSON.stringify({status:report.status,cases:report.cases.length,counterexample:report.counterexample,actual_ERP_cases:0}))
