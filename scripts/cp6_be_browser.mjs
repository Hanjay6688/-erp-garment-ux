// Writer BE browser cases, real Auth and product RPC. Native commands are fixture setup only.
import { execFileSync } from 'node:child_process'
const fixture=(op,payload)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp6_be_browser_fixture.py',op,JSON.stringify(payload)],{cwd:'../writer',encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim())
const money=s=>{const [a,b='']=String(s).split('.');return BigInt(a)*1000000n+BigInt(b.padEnd(6,'0'))}
async function navigate(p,name){
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• '+name,exact:true})
  if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:'Gudang'}).click()
  await link.click()
}
async function conversion(ui,today,mobile,timezoneId){
  const f=fixture('create',{kind:'conversion',today}),owner=await ui.login('OWNER',{label:'be-conversion-'+timezoneId.replaceAll('/','-'),mobile,timezoneId}),p=owner.page
  try{
    await navigate(p,'Ganti Merek')
    const ready=()=>ui.expect(p.getByRole('button',{name:'Muat ulang',exact:true})).toBeEnabled({timeout:20000})
    await ready();await p.getByLabel('Cari lot / SKU',{exact:true}).fill(f.sku);await p.getByRole('button',{name:'Cari lot',exact:true}).click();await ready()
    await p.getByLabel(/^Lot dan gudang/).selectOption(f.lot+':'+f.location);await ready()
    await p.getByLabel('Cari SKU tujuan',{exact:true}).fill(f.target_sku);await p.getByRole('button',{name:'Cari tujuan',exact:true}).click();await ready()
    await p.getByLabel(/^SKU tujuan/).selectOption(f.target)
    await p.getByLabel('Jumlah PCS',{exact:true}).fill('6');await p.getByLabel('Waktu fisik · WIB',{exact:true}).fill(f.day+'T15:00')
    await p.getByLabel('Alasan',{exact:true}).fill('BE browser enam potong fisik')
    await p.getByRole('button',{name:'Lihat pratinjau',exact:true}).click()
    const post=p.getByRole('button',{name:'Catat konversi fisik',exact:true});await ui.expect(post).toBeEnabled({timeout:20000});await post.click()
    await ui.expect.poll(()=>fixture('read',f).source_qty,{timeout:20000}).toBe(4);await ready()
    const after=fixture('read',f)
    await ui.expect(p.getByText('Biaya bersumber sampai saat ini',{exact:false})).toBeVisible()
    await p.getByRole('button',{name:'Batalkan '+f.sku,exact:true}).click();await p.getByLabel('Alasan pembatalan',{exact:true}).fill('BE inverse browser fisik')
    await p.getByRole('button',{name:'Konfirmasi pembatalan',exact:true}).click()
    await ui.expect.poll(()=>fixture('read',f).source_qty,{timeout:20000}).toBe(10)
    const inverse=fixture('read',f)
    const checks={one_document:after.documents.length===1,quantity:after.source_qty===4&&after.target_qty===6,
      value:money(after.target_value)*10n===money(f.value)*6n,wib_date:after.documents[0][2]===f.day&&after.documents[0][3]==='15:00:00',
      inverse:inverse.target_qty===0&&inverse.documents[0][1]==='REVERSED'}
    return{status:Object.values(checks).every(Boolean)?'PASS':'FAIL',checks,mobile,timezoneId,after,inverse}
  }finally{await owner.context.close()}
}
async function pocket(ui,today){
  const f=fixture('create',{kind:'pocket',today}),owner=await ui.login('OWNER',{label:'be-pocket-mobile',mobile:true}),p=owner.page
  try{
    await navigate(p,'Kain kantong')
    await ui.expect(p.getByLabel('Awal periode kain kantong')).toBeEnabled({timeout:20000})
    await p.getByLabel('Cari kain kantong',{exact:true}).fill(f.code)
    await p.locator('form').filter({has:p.getByLabel('Cari kain kantong',{exact:true})}).getByRole('button',{name:'Cari',exact:true}).click()
    await ui.expect(p.getByText('KELUAR-'+f.code+' / 1',{exact:true})).toBeVisible({timeout:20000})
    await p.getByLabel('Awal periode kain kantong').fill(f.period);await p.getByLabel('Akhir periode kain kantong').fill(f.period)
    await p.getByLabel('Alasan pembagian kain kantong').fill('BE browser sumber sejarah lengkap')
    await p.getByRole('button',{name:'Lihat pembagian',exact:true}).click()
    await ui.expect(p.getByText('Tanggal ekonomi pembagian: '+f.cut,{exact:false})).toBeVisible()
    await p.getByRole('button',{name:'Sahkan pembagian ke HPP',exact:true}).click()
    await ui.expect.poll(()=>fixture('read',f).pools.length,{timeout:20000}).toBe(1)
    await p.getByRole('button',{name:'Koreksi KELUAR-'+f.code+' / 1',exact:true}).click()
    await p.getByLabel('Nilai sumber kain kantong').fill('15.00');await p.getByLabel('Tanggal koreksi kain kantong').fill(today)
    await p.getByLabel('Alasan koreksi kain kantong').fill('BE browser koreksi lembar sumber')
    await p.getByRole('button',{name:'Sahkan koreksi nilai',exact:true}).click()
    await ui.expect.poll(()=>fixture('read',f).amount,{timeout:20000}).toBe('15.00')
    const after=fixture('read',f),delta=k=>money(after.ledger[k])-money(f.before[k])
    const checks={wip:delta('WIP')===7500000n,fg:delta('FG_INVENTORY')===4500000n,cogs:delta('COGS')===3000000n,cutover:after.pools[0][2]===f.cut,source:after.amount==='15.00'}
    return{status:Object.values(checks).every(Boolean)?'PASS':'FAIL',checks,after}
  }finally{await owner.context.close()}
}
export async function cases(ui,today){return[
  ['BE_BROWSER:CONVERSION_DESKTOP_UTC_REVERSE',()=>conversion(ui,today,false,'UTC')],
  ['BE_BROWSER:CONVERSION_MOBILE_HONOLULU_REVERSE',()=>conversion(ui,today,true,'Pacific/Honolulu')],
  ['BE_BROWSER:POCKET_HISTORY_ALLOCATE_CORRECT_MOBILE',()=>pocket(ui,today)],
]}
