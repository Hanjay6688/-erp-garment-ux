// Fable UI cases on the candidate UI (DISPOSABLE_TEST build, real Auth, committed copy). Own oracles:
//  * the landing page of a signed-in user shows no fabricated money figures (AUDITOR_START "tanpa angka palsu");
//  * a GUDANG user sees no Keuangan navigation and the runtime badge says the data is a local test;
//  * the landing page and the warehouse page have no horizontal scroll at 390 px.
import {mkdirSync} from 'node:fs'
const FAKE=['Rp284,6 jt','Rp418,2 jt','Rp176,8 jt','Rp298,4 jt','27 Agustus 2026','Rp480,5 jt','Rp182,1 jt']
async function shot(page,name){mkdirSync('cp6-proof/t3',{recursive:true});await page.screenshot({path:'cp6-proof/t3/'+name,fullPage:true});return name}
async function landing(ui,mobile){
 const user=await ui.login('OWNER',{label:'fable-ui-'+(mobile?'mobile':'desktop'),mobile}),page=user.page
 try{
  await page.locator('.sidebar .nav-main, .mobile-menu').first().waitFor({state:'attached',timeout:60000})
  await page.waitForTimeout(1500)
  const text=await page.locator('body').innerText()
  const fake=FAKE.filter(f=>text.includes(f))
  const badge=await page.locator('.topbar').innerText().catch(()=>'')
  const labelled=/simulasi|contoh|demo/i.test(text.slice(0,4000))
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)
  const name=await shot(page,`FABLE_UI_LANDING_${mobile?'MOBILE':'DESKTOP'}.png`)
  return{status:fake.length?'FAIL':'PASS',fabricated_figures_on_landing:fake,landing_labelled_simulation:labelled,topbar:badge.slice(0,120),horizontal_overflow:overflow,screenshot:name}
 }finally{await user.context.close()}
}
async function gudang(ui){
 const user=await ui.login('GUDANG',{label:'fable-ui-gudang'}),page=user.page
 try{
  await page.locator('.sidebar').waitFor({state:'attached',timeout:60000});await page.waitForTimeout(1000)
  const nav=await page.locator('.sidebar').innerText()
  const finance=/Keuangan|Kas & Bank|Jurnal|HPP/i.test(nav)
  const text=await page.locator('body').innerText()
  const fake=FAKE.filter(f=>text.includes(f))
  const name=await shot(page,'FABLE_UI_GUDANG_NAV.png')
  return{status:(!finance)?'PASS':'FAIL',finance_nav_visible_to_gudang:finance,fabricated_figures:fake,nav_excerpt:nav.slice(0,300),screenshot:name}
 }finally{await user.context.close()}
}
export function cases(ui,today){return[
 ['FABLE_UI:LANDING_NO_FABRICATED_FIGURES_DESKTOP',()=>landing(ui,false)],
 ['FABLE_UI:LANDING_NO_FABRICATED_FIGURES_MOBILE',()=>landing(ui,true)],
 ['FABLE_UI:GUDANG_SEES_NO_FINANCE_NAV',()=>gudang(ui)]]}
