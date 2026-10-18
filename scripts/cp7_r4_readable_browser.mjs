// R4-04 (Astra ASTRA-R3-03): every connected screen's text must be readable on its own background. Astra saw the
// connected WIP KPIs, sewing facts and names nearly white on white cards (the cards set a white background and the text
// inherited the app's light foreground #f4f6fb). This case walks every menu as OWNER, desktop 1440 and phone 390, after
// the other cases left real rows in the copy, and measures each visible text against the background it is painted on
// (WCAG relative luminance). Refused: any text below 2:1 on any menu (practically unreadable; Astra's case was about
// 1.07:1). On WIP & Sewing the figures Astra named (KPI numbers, PO names, cut/sew facts, the sewing panel) must reach
// 4.5:1. A gradient counts as each of its stops (the worst is taken). Text inside a disabled control, a faded element
// (opacity below 1) or on an image is not measured and is counted.
import assert from'node:assert/strict'
import{mkdirSync,writeFileSync}from'node:fs'
const FLOOR=2,WIP_FLOOR=4.5
const WIP_TEXT=['.cwip-kpis strong','.cwip-kpis span','.cwip-list h2','.cwip-facts strong','.cwip-sewing p','.cwip-sewing h3','.cwip-sewing-facts dd']
// Runs in the page: contrast of every element that holds its own text, against the colour it is painted on.
export function measure({selector}){
 const parse=c=>{const m=/^rgba?\(([^)]+)\)$/.exec(c);if(!m)return null;const p=m[1].split(/[\s,/]+/).filter(Boolean).map(Number);return{r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}}
 const over=(t,u)=>({r:t.r*t.a+u.r*(1-t.a),g:t.g*t.a+u.g*(1-t.a),b:t.b*t.a+u.b*(1-t.a),a:1})
 const lum=c=>{const f=v=>{v/=255;return v<=0.03928?v/12.92:((v+0.055)/1.055)**2.4};return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b)}
 // The colours a text may be painted on: its own and its ancestors' backgrounds down to the first opaque one; a gradient
 // counts as each of its stops (the worst is taken), an image is not measured.
 const behind=el=>{const layers=[];let opaque=false
  for(let e=el;e&&!opaque;e=e.parentElement){const s=getComputedStyle(e),root=e===document.body||e===document.documentElement
   if(!root&&s.backgroundImage!=='none'){if(/url\(/.test(s.backgroundImage))return null
    const stops=[...s.backgroundImage.matchAll(/rgba?\([^)]+\)/g)].map(m=>parse(m[0])).filter(Boolean)
    if(stops.length){layers.push(stops);if(stops.every(c=>c.a>=1))opaque=true}}
   const c=parse(s.backgroundColor);if(!opaque&&c&&c.a>0){layers.push([c]);if(c.a>=1)opaque=true}}
  let base=opaque?layers.pop():[parse(getComputedStyle(document.documentElement).backgroundColor)]
  for(let i=layers.length-1;i>=0;i--)base=base.flatMap(u=>layers[i].map(t=>over(t,u)))
  return base}
 const label=e=>`${e.tagName.toLowerCase()}${e.className&&typeof e.className==='string'?'.'+e.className.trim().split(/\s+/).join('.'):''}`
 const rows=[];let skipped=0
 for(const el of document.querySelectorAll(selector)){
  if(![...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim()))continue
  const r=el.getBoundingClientRect(),s=getComputedStyle(el);if(r.width<1||r.height<1||s.visibility!=='visible')continue
  let faded=false;for(let e=el;e;e=e.parentElement)if(Number(getComputedStyle(e).opacity)<1)faded=true
  const fg=parse(s.color),under=behind(el)
  if(faded||el.closest(':disabled,[aria-disabled="true"],[aria-hidden="true"]')||!fg||!under){skipped++;continue}
  let ratio=Infinity,bg=under[0]
  for(const u of under){const a=lum(fg.a<1?over(fg,u):fg),b=lum(u),r=(Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);if(r<ratio){ratio=r;bg=u}}
  rows.push({ratio:Math.round(ratio*100)/100,text:[...el.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join(' ').trim().slice(0,60),
   color:s.color,background:`rgb(${Math.round(bg.r)}, ${Math.round(bg.g)}, ${Math.round(bg.b)})`,element:label(el),parent:el.parentElement?label(el.parentElement):''})
 }
 return{measured:rows.length,skipped,rows}
}
async function walk(ui,page,mobile,name){
 const openMenu=async()=>{if(await page.locator('.sidebar.sidebar-open').count())return;const b=page.getByRole('button',{name:'Buka menu',exact:true});if(await b.isVisible())await b.click()}
 const settle=async()=>{await page.waitForLoadState('networkidle',{timeout:15000}).catch(()=>{});await page.waitForTimeout(500)}
 const menus=[],low=[],wip=[];let measured=0,skipped=0
 const check=async menu=>{
  const r=await page.evaluate(measure,{selector:'.main-panel *'});measured+=r.measured;skipped+=r.skipped
  const bad=r.rows.filter(x=>x.ratio<FLOOR);low.push(...bad.map(x=>({menu,...x})));menus.push({menu,measured:r.measured,skipped:r.skipped,below_floor:bad.length})
  if(menu.endsWith('WIP & Sewing')){
   const w=await page.evaluate(measure,{selector:WIP_TEXT.join(',')});wip.push(...w.rows.map(x=>({menu,...x})))
   await page.screenshot({path:`cp6-proof/t3/${name}_WIP.png`,fullPage:true})
  }
 }
 await settle();await check('Dashboard')
 await openMenu()
 const sections=await page.locator('.sidebar .nav-section > button.nav-main').allInnerTexts()
 for(const raw of sections){
  const section=raw.replace(/[›⌄]/g,'').trim()
  await openMenu();await page.locator('.sidebar .nav-section > button.nav-main').filter({hasText:section}).first().click()
  const items=await page.locator('.sidebar .submenu > button').allInnerTexts()
  for(const item of items){
   await openMenu()
   const sub=page.locator('.sidebar .submenu > button').filter({hasText:item.trim()})
   if(!await sub.first().isVisible())await page.locator('.sidebar .nav-section > button.nav-main').filter({hasText:section}).first().click()
   await sub.first().click();await settle()
   await check(`${section} › ${item.replace(/^•\s*/,'').trim()}`)
  }
 }
 return{menus,low,wip,measured,skipped}
}
async function journey(ui,mobile,h){
 const name=`CP17_BROWSER_R4_04_CONNECTED_TEXT_READABLE_${mobile?'MOBILE':'DESKTOP'}`,seen={}
 const owner=await ui.login('OWNER',{label:'cp17-r4-04-'+(mobile?'mobile':'desktop'),mobile}),page=owner.page
 try{
  mkdirSync('cp6-proof/t3',{recursive:true})
  const r=await walk(ui,page,mobile,name);Object.assign(seen,{menus:r.menus.length,low:r.low,wip:r.wip})
  writeFileSync(`cp6-proof/t3/${name}.json`,JSON.stringify(r,null,1)+'\n')
  assert.ok(r.menus.length>=40,r.menus.length)
  assert.deepEqual(r.low,[],'CP17_R4_04_TEXT_BELOW_2_TO_1')
  const wipKpi=r.wip.filter(x=>x.parent.includes('cwip-kpis')||x.element.startsWith('strong'))
  assert.ok(wipKpi.length>0,'CP17_R4_04_WIP_FIGURES_NOT_FOUND')
  assert.deepEqual(r.wip.filter(x=>x.ratio<WIP_FLOOR),[],'CP17_R4_04_WIP_TEXT_BELOW_4_5_TO_1')
  return{status:'PASS',finding:'ASTRA-R3-03',phone:mobile,menus:r.menus.length,texts_measured:r.measured,texts_not_measured:r.skipped,
   floor_all_menus:FLOOR,floor_wip_figures:WIP_FLOOR,wip_texts:r.wip.length,lowest_wip_ratio:Math.min(...r.wip.map(x=>x.ratio))}
 }catch(error){await h.failure(page,name,error,seen,[]);throw error}
 finally{await owner.context.close().catch(()=>{})}
}
export function cases(ui,today,h){
 return[['CP17_BROWSER_R4_04_CONNECTED_TEXT_READABLE_DESKTOP',()=>journey(ui,false,h)],['CP17_BROWSER_R4_04_CONNECTED_TEXT_READABLE_MOBILE',()=>journey(ui,true,h)]]
}
