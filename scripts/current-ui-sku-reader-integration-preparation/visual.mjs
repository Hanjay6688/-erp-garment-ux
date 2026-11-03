// Measured CSS/markup adapter. No live RPC, authentication or database.
import{chromium}from'playwright-core';
import{readFileSync,writeFileSync,readdirSync}from'node:fs';
import{resolve,dirname}from'node:path';
import{fileURLToPath}from'node:url';
import{createHash}from'node:crypto';
import assert from'node:assert/strict';
import{readable}from'./contrast.mjs';
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
    const file=`${mode}-${width}${expanded?'-details':''}.png`;
    const result={mode,width,expanded,status:'INCOMPLETE',screenshot:file};report.cases.push(result);
    try{
    // Retain the visible first result even when a measurement refuses it.
    await page.screenshot({path:resolve(directory,file),fullPage:true});
    const size=await page.evaluate(()=>({inner:innerWidth,document:document.documentElement.scrollWidth}));
    result.size=size;
    assert.equal(size.inner,width);assert(size.document<=width,JSON.stringify({mode,width,expanded,size}));
    const measured=await readable(panel);
    const controls=await panel.locator('button,input,select').evaluateAll(list=>list.filter(e=>e.getClientRects().length).map(e=>({label:e.getAttribute('aria-label')??e.textContent,width:e.getBoundingClientRect().width,parent:e.parentElement.getBoundingClientRect().width})));
    assert(controls.every(c=>c.width<=c.parent+1),JSON.stringify({mode,width,controls}));
    const selections=await panel.locator('select').evaluateAll(list=>list.filter(el=>el.getClientRects().length).map(el=>{
     const style=getComputedStyle(el),context=document.createElement('canvas').getContext('2d');context.font=style.font;
     return{label:el.getAttribute('aria-label'),width:el.clientWidth,required:context.measureText(el.selectedOptions[0]?.textContent??'').width+parseFloat(style.paddingLeft)+parseFloat(style.paddingRight)+24};
    }));
    result.selected_text=selections;
    assert(selections.every(row=>row.width>=row.required),'STOCK_TOOLBAR_SELECTED_TEXT_CLIPPED:'+JSON.stringify({mode,width,selections}));
    const explanations=await panel.locator('.record-tools>small').evaluateAll(list=>list.map(el=>{
     const box=el.getBoundingClientRect(),form=el.parentElement,style=getComputedStyle(form);
     return{width:box.width,height:box.height,available:form.clientWidth-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight)};
    }));
    result.toolbar_explanations=explanations;
    assert(explanations.length>0&&explanations.every(row=>row.width>=row.available-1),'STOCK_TOOLBAR_EXPLANATION_SQUEEZED:'+JSON.stringify({mode,width,explanations}));
    const text=await panel.innerText();if(mode==='known')assert(text.includes('HPP SKU saat ini Rp23,75'));
    if(mode==='unknown'||mode==='operations')assert(!text.includes('Rp0'));
    if(mode==='operations')assert(!text.includes('Rp'));
    Object.assign(result,{status:'PASS',minimum_contrast:Math.min(...measured.rows.map(r=>r.ratio)),measured_text_nodes:measured.rows.length});
    }catch(error){result.error=String(error.stack??error);}
   }
  }}finally{await context.close();}
 }
 assert.equal(report.cases.length,32);assert.equal(report.cases.filter(row=>row.status!=='PASS').length,0,'INCOMPLETE_VISUAL_CASES');report.status='PASS';
}catch(error){report.error=String(error.stack??error);throw error;}
finally{writeFileSync(resolve(directory,'FG_VISUAL_CAPTURE.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}
console.log(JSON.stringify({status:report.status,cases:report.cases.length,actual_ERP_cases:0}));
