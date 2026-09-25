// Genuine browser -> HTTP -> candidate database. Product replies never mocked.
// Fixtures use ordinary native commands in their own copy, then restore grants.
import { execFileSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'

const here=dirname(fileURLToPath(import.meta.url))
const literal=v=>"'"+String(v).replaceAll("'","''")+"'"
const fixture=(kind,today)=>{
  const text=execFileSync('python',[resolve(here,'gpt_browser_fixture.py'),kind,String(today)],
    {cwd:resolve(process.cwd(),'../writer'),encoding:'utf8',maxBuffer:4*1024*1024})
  return JSON.parse(text.trim().split('\n').at(-1))
}
async function navigation(page,label){
  const menu=page.getByRole('button',{name:/^Buka menu$/})
  if(await menu.isVisible()) await menu.click()
  const target=page.locator('.sidebar .submenu button').filter({hasText:label})
  if(!await target.isVisible()) await page.locator('.sidebar .nav-main').filter({hasText:'Produksi'}).click()
  await target.click()
}
async function resultFor(page,fn,action,click){
  const waiting=page.waitForResponse(r=>{
    if(!r.url().endsWith('/rpc/'+fn)||r.request().method()!=='POST')return false
    const data=r.request().postDataJSON()
    return (data.p_action??data.p_payload?.action)===action
  })
  await click()
  const response=await waiting
  return {http_status:response.status(),request:response.request().postDataJSON(),body:await response.json()}
}

export async function cases(ui,today){
  const businessDay=new Date(Date.parse(String(today)+'T00:00:00Z')-86400000).toISOString().slice(0,10)
  const input=businessDay+'T00:30'
  const expected=new Date(input+':00+07:00').toISOString()
  const rows=[]
  for(const zone of ['Asia/Jakarta','UTC','Etc/GMT+12','Pacific/Kiritimati']){
    for(const kind of ['cutting','pickup','bs']){
      rows.push(['G8UI:WIB:'+kind+':'+zone,async()=>{
        const f=fixture(kind,today)
        const user=await ui.login('OWNER',{label:'g8-'+kind,timezoneId:zone,mobile:false})
        const page=user.page
        let network,stored,field
        try{
          if(kind==='cutting'){
            await navigation(page,'Buat Potongan')
            await ui.expect(page.getByRole('heading',{name:'Buat Potongan',exact:true})).toBeVisible()
            await page.getByLabel('Cari draft Potongan',{exact:true}).fill(f.po_number)
            await page.getByRole('button',{name:'Cari draft',exact:true}).click()
            await page.locator('.ccut-drafts button').filter({hasText:f.group_number}).click()
            await page.getByLabel('Waktu potong (WIB)',{exact:true}).fill(input)
            network=await resultFor(page,'erp_save_cutting_group_before_sewing_v2','SAVE_DRAFT',
              ()=>page.getByRole('button',{name:'Simpan draft',exact:true}).click())
            field=network.request.p_payload.cut_at
            stored=ui.sql(`select to_char(cut_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') from erp.cutting_groups where id=${literal(f.group)}`)
          }else if(kind==='pickup'){
            await navigation(page,'Bagi Potongan')
            await ui.expect(page.getByRole('heading',{name:'Bagi Potongan',exact:true})).toBeVisible()
            await page.getByPlaceholder('Nomor Potongan, PO, model, Pola, Mandor…',{exact:true}).fill(f.po_number)
            await page.locator('.cpick-search').getByRole('button',{name:'Cari',exact:true}).click()
            await page.locator('.cpick-queue button').filter({hasText:f.group_number}).click()
            await page.getByLabel('Mandor',{exact:true}).selectOption(f.contractor)
            await page.getByLabel('Waktu fisik diambil (WIB)',{exact:true}).fill(input)
            network=await resultFor(page,'erp_save_cutting_pickup_v1','SAVE_DRAFT',
              ()=>page.getByRole('button',{name:'Simpan draft',exact:true}).click())
            field=network.request.p_payload.picked_up_at
            stored=ui.sql(`select to_char(picked_up_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') from erp.cutting_pickups where id=${literal(network.body.pickup_id)}`)
          }else{
            await navigation(page,'Barang BS & Rework')
            await ui.expect(page.getByRole('heading',{name:'Barang BS & Rework',exact:true})).toBeVisible()
            await page.getByRole('button',{name:'BS legacy',exact:true}).click()
            const dialog=page.getByRole('dialog'),tag='G8BS-'+randomUUID()
            await dialog.getByLabel('REFERENSI LEGACY · WAJIB',{exact:true}).fill(tag)
            await dialog.getByLabel('QTY PCS',{exact:true}).fill('1')
            await dialog.getByLabel('WAKTU FISIK DITEMUKAN · WIB',{exact:true}).fill(input)
            await dialog.getByLabel('ALASAN PENCATATAN · WAJIB',{exact:true}).fill('Independent WIB browser check')
            network=await resultFor(page,'erp_save_bs_resolution_action_v1','CREATE_MANUAL_BS',
              ()=>dialog.getByRole('button',{name:'Simpan kasus authoritative',exact:true}).click())
            field=network.request.p_payload.physical_at
            stored=ui.sql(`select to_char(physical_at at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') from erp.bs_cases where legacy_reference=${literal(tag)}`)
          }
          const ok=network.http_status===200&&new Date(field).toISOString()===expected&&stored===expected
          return {status:ok?'PASS':'COUNTEREXAMPLE',zone,kind,input_wib:input,expected_utc:expected,
            browser_payload_time:field,stored_utc:stored,http_status:network.http_status,response:network.body,
            fixture:f,oracle:'M3820 and CP6-01/A2: same WIB form value must persist the same physical instant in every device timezone',
            browser_form_clicked:true,product_response_mocked:false}
        }finally{await user.context.close()}
      }])
    }
  }
  return rows
}
