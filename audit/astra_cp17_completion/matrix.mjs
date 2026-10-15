import assert from 'node:assert/strict'
import {readFileSync,mkdirSync,writeFileSync} from 'node:fs'

const menus=JSON.parse(readFileSync(new URL('./MENUS.json',import.meta.url)))
const sessions=new Map()
async function open(page,row){
  const mobile=page.getByRole('button',{name:'Buka menu',exact:true})
  if(await mobile.isVisible())await mobile.click()
  if(!row.section){await page.locator('.sidebar .nav-main').filter({hasText:/^Dashboard$/}).click();return}
  const link=page.getByRole('button',{name:'• '+row.label,exact:true})
  if(!await link.isVisible())await page.locator('.sidebar .nav-main').filter({hasText:row.section}).click()
  await link.click()
}
async function inspect(ui,row,index,mobile){
  const key=mobile?'MOBILE':'DESKTOP'
  if(!sessions.has(key))sessions.set(key,await ui.login('OWNER',{label:'astra-matrix-'+key,mobile}))
  const {page}=sessions.get(key),responses=[],errors=[],pending=new Set();let lastNetworkEvent=Date.now()
  const started=r=>{pending.add(r);lastNetworkEvent=Date.now()},finished=r=>{pending.delete(r);lastNetworkEvent=Date.now()}
  page.on('request',started);page.on('requestfinished',finished);page.on('requestfailed',finished)
  const response=r=>{if(r.url().includes('/rest/v1/rpc/'))responses.push({rpc:new URL(r.url()).pathname.split('/').at(-1),status:r.status()})}
  const error=e=>errors.push(String(e.message))
  page.on('response',response);page.on('pageerror',error)
  const name=`ASTRA_MATRIX_${ui.mode}_${key}_${String(index+1).padStart(2,'0')}`
  mkdirSync('cp6-proof/t3/matrix',{recursive:true})
  try{
    await open(page,row)
    await ui.expect(page.locator('.top-title strong')).toHaveText(row.title)
    // Qualification v2: header/navigation alone does not mean a lazy workspace loaded.
    await ui.expect(page.locator('.page-wrap')).not.toContainText('Memuat workspace dan guardrail transaksi.',{timeout:30000})
    await ui.expect.poll(()=>pending.size===0&&Date.now()-lastNetworkEvent>=800,{timeout:30000,intervals:[100,200,300]}).toBe(true)
    const state=await page.locator('.page-wrap').evaluate(el=>{
      const visible=x=>Boolean(x.getClientRects().length)&&getComputedStyle(x).visibility!=='hidden'
      return {
        text:el.innerText,
        headings:[...el.querySelectorAll('h1,h2,h3')].filter(visible).map(x=>x.textContent),
        controls:[...el.querySelectorAll('input,select,textarea,button')].filter(visible).map(x=>({tag:x.tagName,type:x.getAttribute('type'),label:x.getAttribute('aria-label')||x.labels?.[0]?.innerText||x.textContent,disabled:x.disabled,placeholder:x.getAttribute('placeholder')})),
        alerts:[...el.querySelectorAll('[role=alert],.error')].filter(visible).map(x=>x.innerText),
        root_classes:[...el.children].map(x=>x.className),
        viewport:innerWidth,scroll_width:document.documentElement.scrollWidth,
        horizontal_overflow:document.documentElement.scrollWidth>innerWidth+1,
        overflowing_elements:[...el.querySelectorAll('*')].filter(visible).filter(x=>x.getBoundingClientRect().right>innerWidth+1&&x.clientWidth>0).slice(0,12).map(x=>({tag:x.tagName,cls:x.className,text:x.innerText?.slice(0,100),right:x.getBoundingClientRect().right})),
      }
    })
    assert.ok(state.text.trim().length>0,'EMPTY_RENDER')
    assert.ok(!state.text.includes('Memuat workspace dan guardrail transaksi.'),'LAZY_WORKSPACE_NOT_READY')
    const counter=state.horizontal_overflow||errors.length>0||responses.some(r=>r.status>=500)
    const result={status:counter?'COUNTEREXAMPLE':'PASS',evidence_origin:'ASTRA_REAL_BROWSER_ENTRY_INVENTORY',scope:'Entry render, initial controls, network errors and layout only; not all form mutations',mode:ui.mode,mobile,menu:row.label,...state,rpc_responses:responses,page_errors:errors,screenshot:'matrix/'+name+'.png'}
    await page.screenshot({path:'cp6-proof/t3/'+result.screenshot,fullPage:true})
    writeFileSync('cp6-proof/t3/matrix/'+name+'.json',JSON.stringify(result,null,2))
    return result
  }catch(e){
    const detail={status:'INCOMPLETE',mode:ui.mode,mobile,menu:row.label,error:String(e),body:await page.locator('body').innerText().catch(()=>''),rpc_responses:responses,page_errors:errors}
    writeFileSync('cp6-proof/t3/matrix/'+name+'_FAILURE.json',JSON.stringify(detail,null,2))
    await page.screenshot({path:'cp6-proof/t3/matrix/'+name+'_FAILURE.png',fullPage:true}).catch(()=>{})
    return detail
  }finally{page.off('response',response);page.off('pageerror',error);page.off('request',started);page.off('requestfinished',finished);page.off('requestfailed',finished)}
}
export function cases(ui){assert.equal(menus.length,48);return [false,true].flatMap(mobile=>menus.map((row,index)=>[`ASTRA_MATRIX_${ui.mode}_${mobile?'MOBILE':'DESKTOP'}_${String(index+1).padStart(2,'0')}`,()=>inspect(ui,row,index,mobile)]))}
