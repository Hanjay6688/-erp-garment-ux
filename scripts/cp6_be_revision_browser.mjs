import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
const { cases: regression } = await import(pathToFileURL(resolve('scripts/cp6_bf_browser.mjs')).href)
const fixture=(op,payload)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp6_be_revision_browser_fixture.py',op,JSON.stringify(payload)],{cwd:'../writer',encoding:'utf8',maxBuffer:16*1024*1024}).trim())
let prepared
async function oldPeriod(ui,today,mobile){
 const f=prepared??=fixture('create',{today}),user=await ui.login('OWNER',{label:'be-old-period-'+mobile,mobile}),p=user.page
 try{
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• Kain kantong',exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click();await link.click()
  const search=p.locator('form').filter({has:p.getByLabel('Cari kain kantong',{exact:true})}).getByRole('button',{name:'Cari',exact:true})
  const ready=()=>ui.expect(search).toBeEnabled({timeout:30000})
  await ready()
  const cancel=p.getByRole('button',{name:'Batalkan alokasi '+f.start,exact:true})
  if(!mobile){
   await ui.expect(cancel).toHaveCount(0)
   await p.getByLabel('Alasan pembagian kain kantong',{exact:true}).fill('Draft survives history paging')
   await p.getByRole('button',{name:'Muat periode berikutnya',exact:true}).click()
   await ui.expect(cancel).toBeVisible({timeout:30000})
   await ui.expect(p.getByLabel('Alasan pembagian kain kantong',{exact:true})).toHaveValue('Draft survives history paging')
  }
  await p.getByLabel('Cari kain kantong',{exact:true}).fill(mobile?f.id:f.end)
  await search.click()
  await ui.expect(cancel).toBeVisible({timeout:30000})
  if(!mobile)return {status:'PASS',checks:{old_active_paged:true,date_search:true,draft_preserved:true},id:f.id}
  await cancel.click();await p.getByLabel('Alasan pembatalan alokasi',{exact:true}).fill('Cancel old active allocation from mobile search')
  await p.getByRole('button',{name:'Sahkan pembatalan alokasi',exact:true}).click()
  await ui.expect.poll(()=>fixture('read',f).state.status,{timeout:30000}).toBe('CANCELLED')
  const after=fixture('read',f)
  const cents=v=>Math.round(Number(v)*100)
  const delta=Object.fromEntries(Object.keys(f.before).map(k=>[k,cents(after.ledger[k])-cents(f.before[k])]))
  const checks={id_search:true,once:after.cancellations===1,no_stock:after.stock===f.stock,
   exact_cost_inverse:delta.WIP===-562&&delta.FG_INVENTORY===-338&&delta.COGS===-225&&delta.OTHER_EXPENSE===1125}
  return {status:Object.values(checks).every(Boolean)?'PASS':'FAIL',checks,delta}
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [...await regression(ui,today),['BE_REV_BROWSER:OLD_PERIOD_DESKTOP_PAGE_DATE',()=>oldPeriod(ui,today,false)],['BE_REV_BROWSER:OLD_PERIOD_MOBILE_ID_CANCEL',()=>oldPeriod(ui,today,true)]]}
