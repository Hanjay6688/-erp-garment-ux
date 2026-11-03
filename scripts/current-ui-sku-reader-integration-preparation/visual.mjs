// Measured CSS/markup adapter. No live RPC, authentication or database.
import{chromium}from'playwright-core';
import{readFileSync,writeFileSync,readdirSync}from'node:fs';
import{resolve,dirname}from'node:path';
import{fileURLToPath}from'node:url';
import{createHash}from'node:crypto';
import assert from'node:assert/strict';
import{readable}from'../current-sku-pair-browser-qualification/evidence.mjs';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const directory=process.env.CP7_UI_FG_CAPTURE_DIRECTORY;assert(directory);
const modes=['known','unknown','empty','loading','error','pending','operations'],widths=[320,390,768,1440];
const assets=resolve(root,'dist/assets'),names=readdirSync(assets);
const cssNames=['index','procurement-connected','fg-connected','RecordTools','ConnectedFgStockPage','fg-reorder'].map(prefix=>{
 const matches=names.filter(n=>n.startsWith(prefix+'-')&&n.endsWith('.css'));assert.equal(matches.length,1,prefix);return matches[0];
});
const css=cssNames.map(name=>readFileSync(resolve(assets,name),'utf8')).join('\n');
const report={status:'INCOMPLETE',classification:'REAL_COMPONENT_MARKUP_AND_BUILT_THEME_CSS_WITH_SYNTHETIC_PROVIDERS',widths,modes,
 css:Object.fromEntries(cssNames.map(name=>[name,createHash('sha256').update(readFileSync(resolve(assets,name))).digest('hex')])),cases:[],actual_ERP_cases:0,actual_Auth_cases:0,actual_full_App_cases:0,production_go:false};
const browser=await chromium.launch({headless:true});
try{
 report.browser=browser.version();
 for(const width of widths){
  const context=await browser.newContext({viewport:{width,height:900},isMobile:width<500,deviceScaleFactor:1});const page=await context.newPage();
  await page.route('**/*',r=>r.abort());
  try{for(const mode of modes){
   const html=readFileSync(resolve(directory,mode+'.html'),'utf8');
   await page.setContent(`<!doctype html><html lang="id"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>${css}</style></head><body><div class="app-shell"><aside class="sidebar"><div class="brand-row"><div><strong>HANSEN</strong><span>ERP GARMENT</span></div></div><div class="nav-caption">GUDANG</div><button class="nav-main">Kartu Stok FG</button></aside><main class="main-panel"><div class="page-wrap"><p>Data uji terisolasi · ${mode}</p>${html}</div></main></div></body></html>`);
   const panel=page.locator('section.cfg');await panel.waitFor({state:'visible'});
   for(const expanded of mode==='known'?[false,true]:[false]){
    if(expanded)await panel.locator('details').evaluateAll(list=>list.forEach(el=>{el.open=true}));
    const size=await page.evaluate(()=>({inner:innerWidth,document:document.documentElement.scrollWidth}));
    assert.equal(size.inner,width);assert(size.document<=width,JSON.stringify({mode,width,expanded,size}));
    const measured=await readable(panel);
    const controls=await panel.locator('button,input,select').evaluateAll(list=>list.filter(e=>e.getClientRects().length).map(e=>({label:e.getAttribute('aria-label')??e.textContent,width:e.getBoundingClientRect().width,parent:e.parentElement.getBoundingClientRect().width})));
    assert(controls.every(c=>c.width<=c.parent+1),JSON.stringify({mode,width,controls}));
    const text=await panel.innerText();if(mode==='known')assert(text.includes('HPP SKU saat ini Rp23,75'));
    if(mode==='unknown'||mode==='operations')assert(!text.includes('Rp0'));
    if(mode==='operations')assert(!text.includes('Rp'));
    const file=`${mode}-${width}${expanded?'-details':''}.png`;await page.screenshot({path:resolve(directory,file),fullPage:true});
    report.cases.push({mode,width,expanded,status:'PASS',size,minimum_contrast:Math.min(...measured.rows.map(r=>r.ratio)),measured_text_nodes:measured.rows.length,screenshot:file});
   }
  }}finally{await context.close();}
 }
 assert.equal(report.cases.length,32);report.status='PASS';
}catch(error){report.error=String(error.stack??error);throw error;}
finally{writeFileSync(resolve(directory,'FG_VISUAL_CAPTURE.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}
console.log(JSON.stringify({status:report.status,cases:report.cases.length,actual_ERP_cases:0}));
