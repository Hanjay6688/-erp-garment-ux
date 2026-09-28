import { execFileSync } from 'node:child_process'
const fixture=(op,payload)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp6_bf_supplier_fixture.py',op,JSON.stringify(payload)],{cwd:'../writer',encoding:'utf8'}).trim())
async function allocate(ui,today,mobile){
 const f=fixture('create',{today,fabric:!mobile}),user=await ui.login('OWNER',{label:'supplier-credit-'+mobile,mobile})
 try{
  const p=user.page,menu=p.getByRole('button',{name:'Buka menu',exact:true})
  await ui.expect(p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'})).toBeAttached({timeout:20000})
  if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• Hutang Supplier & Vendor',exact:true})
  if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Keuangan'}).click()
  await link.click();await ui.expect(p.getByRole('heading',{name:'Utang & kredit retur supplier',exact:true})).toBeVisible()
  const select=p.getByLabel('Supplier kredit',{exact:true}),ready=()=>ui.expect(select).toBeEnabled({timeout:20000})
  await ready();await select.selectOption(f.supplier);await ready()
  const credit=f.view.credits[0],targets=f.purchases.slice(1).map(id=>f.view.purchases.find(p=>p.id===id))
  const open=()=>p.getByRole('button',{name:'Atur alokasi '+credit.return_number,exact:true}).click()
  await open()
  for(const [i,target]of targets.entries())await p.getByLabel('Kredit untuk '+target.number,{exact:true}).fill(i===0?'12':'8')
  await p.getByLabel('Alasan pengalihan kredit',{exact:true}).fill('Split return credit over same supplier purchases')
  await p.getByLabel('Saya sudah memeriksa pembelian asal, tujuan, dan nominal kredit.').check()
  await p.getByRole('button',{name:'Simpan alokasi kredit',exact:true}).click()
  await ui.expect.poll(()=>fixture('read',f).credits[0].allocations.length,{timeout:20000}).toBe(2)
  await ready();const split=fixture('read',f)
  await open()
  for(const target of targets)await p.getByLabel('Kredit untuk '+target.number,{exact:true}).fill('')
  await p.getByLabel('Alasan pengalihan kredit',{exact:true}).fill('Restore credit to original purchase')
  await p.getByLabel('Saya sudah memeriksa pembelian asal, tujuan, dan nominal kredit.').check()
  await p.getByRole('button',{name:'Simpan alokasi kredit',exact:true}).click()
  await ui.expect.poll(()=>fixture('read',f).credits[0].allocations.length,{timeout:20000}).toBe(0)
  await ready();const restored=fixture('read',f),checks={split:split.credits[0].original_purchase_credit==='0.00',original:restored.credits[0].original_purchase_credit==='20.00',history:restored.credits[0].events.length===4}
  return {status:Object.values(checks).every(Boolean)?'PASS':'FAIL',checks,mobile}
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [['SUPPLIER_BROWSER:FABRIC_SPLIT_INVERSE_DESKTOP',()=>allocate(ui,today,false)],['SUPPLIER_BROWSER:ACCESSORY_SPLIT_INVERSE_MOBILE',()=>allocate(ui,today,true)]]}
