// Writer BE browser cases, real Auth and product RPC. Native commands are fixture setup only.
import { execFileSync } from 'node:child_process'
const fixture=(op,payload)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp6_be_browser_fixture.py',op,JSON.stringify(payload)],{cwd:'../writer',encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim())
const money=s=>{const [a,b='']=String(s).split('.');return BigInt(a)*1000000n+BigInt(b.padEnd(6,'0'))}
async function navigate(p,name,group='Gudang'){
  const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
  const link=p.getByRole('button',{name:'• '+name,exact:true})
  if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:group}).click()
  await link.click()
}
async function conversion(ui,today,mobile,timezoneId){
  const f=fixture('create',{kind:'conversion',today}),owner=await ui.login('OWNER',{label:'be-conversion-'+timezoneId.replaceAll('/','-'),mobile,timezoneId}),p=owner.page
  const previewReplies=[]
  p.on('response',async r=>{if(r.url().includes('/rpc/erp_get_product_conversion_workspace_v1')){try{const req=r.request().postDataJSON();if(req.p_filters?.preview)previewReplies.push({status:r.status(),body:await r.json(),payload:req.p_filters.preview})}catch{}}})
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
  }catch(e){throw new Error(String(e)+'; alerts='+JSON.stringify(await p.getByRole('alert').allTextContents())+'; previews='+JSON.stringify(previewReplies))}finally{await owner.context.close()}
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
async function rework(ui,today,redye){
  const f=fixture('create',{kind:redye?'redye':'rework',today}),owner=await ui.login('OWNER',{label:redye?'be-redye-mobile':'be-rework',mobile:redye,timezoneId:'Pacific/Honolulu'}),p=owner.page
  try{
    await navigate(p,'Barang BS & Rework','Produksi')
    await ui.expect(p.getByRole('button',{name:'Refetch',exact:true})).toBeEnabled({timeout:20000})
    await p.locator('.cbsr-tabs').getByRole('button',{name:'Semua',exact:true}).click()
    await p.getByPlaceholder('Nomor, PO, model, Pola, pihak…').fill(f.bs_number)
    await p.locator('.cbsr-search').getByRole('button',{name:'Cari',exact:true}).click()
    await p.locator('.cbsr-list button').filter({hasText:f.bs_number}).click()
    await p.locator('.cbsr-route-tabs').getByRole('button',{name:redye?'Rewash':'Rework',exact:true}).click()
    const form=p.locator('.cbsr-route-form')
    await form.getByLabel('NOMOR ORDER · WAJIB',{exact:true}).fill(f.number)
    await form.getByLabel(redye?/^VENDOR REWASH/:/^MANDOR REWORK/).selectOption(redye?f.vendor:f.contractor)
    await form.getByLabel('QTY DIKIRIM',{exact:true}).fill('4')
    await form.getByLabel('WAKTU FISIK · WIB',{exact:true}).fill(f.day+'T14:00')
    await form.getByLabel(/^GUDANG FG BILA GOOD/).selectOption(f.location)
    await form.getByLabel('CATATAN / ALASAN',{exact:true}).fill('BE browser pekerjaan nyata ke SKU baru')
    if(!redye)await form.locator('fieldset.cbsr-checks').filter({has:p.getByText('KOMPONEN KERJA YANG DIULANG · DASAR UPAH REWORK',{exact:true})}).getByRole('checkbox').first().check()
    for(const box of await form.locator('.cbsr-accessories input[type=checkbox]').all())await box.uncheck()
    await form.getByRole('checkbox',{name:'Hasil GOOD menjadi SKU lain',exact:true}).check()
    await ui.expect(form.getByRole('button',{name:'Cari SKU hasil',exact:true})).toBeEnabled()
    await form.getByLabel('Cari SKU hasil',{exact:true}).fill(f.target_sku)
    await form.getByRole('button',{name:'Cari SKU hasil',exact:true}).click()
    await ui.expect(form.getByLabel(/^SKU hasil baru/)).toBeEnabled()
    await form.getByLabel(/^SKU hasil baru/).selectOption(f.target)
    if(redye){await form.getByLabel(/^Proses celup berbayar/).selectOption(f.process);await form.getByLabel(/^Harga jasa/).selectOption('UNKNOWN')}
    await form.getByRole('button',{name:redye?'Buat order celup ulang':'Buat order rework',exact:true}).click()
    const completion=()=>p.locator('.cbsr-completion-form').filter({hasText:f.number})
    await ui.expect(completion()).toBeVisible({timeout:20000})
    await completion().getByLabel('GOOD KUMULATIF',{exact:true}).fill('1')
    await completion().getByLabel('BS KUMULATIF',{exact:true}).fill('0')
    await completion().getByLabel('ALASAN HASIL FISIK',{exact:true}).fill('BE satu dari empat kembali')
    await completion().getByRole('button',{name:'Simpan partial',exact:true}).click()
    await ui.expect.poll(()=>fixture('read',f).orders[0]?.[2],{timeout:20000}).toBe(1)
    const partial=fixture('read',f)
    await completion().getByLabel('GOOD KUMULATIF',{exact:true}).fill('2')
    await completion().getByLabel('BS KUMULATIF',{exact:true}).fill('2')
    await completion().getByLabel('WAKTU SELESAI · WIB',{exact:true}).fill(f.day+'T16:00')
    await completion().getByLabel('ALASAN HASIL FISIK',{exact:true}).fill('BE pemeriksaan akhir dua good dua BS')
    await completion().getByRole('button',{name:'Post hasil & recovery',exact:true}).click()
    await ui.expect.poll(()=>fixture('read',f).qty,{timeout:20000}).toBe(2)
    const completed=fixture('read',f)
    let final
    if(redye){
      await navigate(p,'Laundry','Produksi')
      await p.getByRole('button',{name:'Harga & tagihan',exact:true}).click()
      await ui.expect(p.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled({timeout:20000})
      await p.getByLabel('Vendor harga laundry',{exact:true}).selectOption(f.vendor)
      await ui.expect(p.getByRole('button',{name:'Muat ulang harga',exact:true})).toBeEnabled()
      await p.getByRole('button',{name:'Invoice vendor',exact:true}).click()
      await p.getByLabel('Tarif celup '+f.number,{exact:true}).fill('50.00')
      await p.getByLabel('Alasan pembatalan invoice',{exact:true}).fill('BE harga jasa diterima sesudah barang')
      await p.getByRole('button',{name:'Isi tarif celup '+f.number,exact:true}).click()
      await ui.expect.poll(()=>fixture('read',f).cost,{timeout:20000}).toBe('200.00')
      final=fixture('read',f)
    }else{
      const done=p.locator('.cbsr-rework-complete')
      await done.getByPlaceholder('Alasan reversal Owner/Admin').fill('BE inverse hasil fisik')
      await done.getByRole('button',{name:'Reverse',exact:true}).click()
      await ui.expect.poll(()=>fixture('read',f).qty,{timeout:20000}).toBe(0)
      final=fixture('read',f)
    }
    const checks={partial_no_fg:partial.conversions.length===0&&partial.orders[0][4]===null,
      completed_once:completed.orders[0][1]==='COMPLETED'&&completed.conversions.length===1&&completed.qty===2,
      target:completed.product===f.target,final:redye?completed.rate==='None'&&final.rate==='50.000000'&&final.cost==='200.00':final.qty===0&&final.conversions[0][1]==='REVERSED'}
    return{status:Object.values(checks).every(Boolean)?'PASS':'FAIL',checks,partial,completed,final}
  }finally{await owner.context.close()}
}
export async function cases(ui,today){return[
  ['BE_BROWSER:CONVERSION_DESKTOP_UTC_REVERSE',()=>conversion(ui,today,false,'UTC')],
  ['BE_BROWSER:CONVERSION_MOBILE_HONOLULU_REVERSE',()=>conversion(ui,today,true,'Pacific/Honolulu')],
  ['BE_BROWSER:POCKET_HISTORY_ALLOCATE_CORRECT_MOBILE',()=>pocket(ui,today)],
  ['BE_BROWSER:REWORK_SKU_PARTIAL_COMPLETE_REVERSE',()=>rework(ui,today,false)],
  ['BE_BROWSER:REDYE_SKU_UNKNOWN_THEN_PRICE_MOBILE',()=>rework(ui,today,true)],
]}
