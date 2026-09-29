import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {mkdirSync,writeFileSync} from 'node:fs'

const fixture=(op,p)=>JSON.parse(execFileSync('python',['../auditor/scripts/cp7_p12_browser_fixture.py',op,JSON.stringify(p)],{cwd:'../writer',encoding:'utf8'}).trim())
const changed=(a,b)=>Object.fromEntries([...new Set([...Object.keys(a),...Object.keys(b)])].sort().flatMap(k=>{const v=Number(b[k]??0)-Number(a[k]??0);return v?[[k,v]]:[]}))
const csv=rows=>{
 const keys=[...new Set(rows.flatMap(row=>Object.keys(row)))],escape=v=>'"'+String(v??'').replaceAll('"','""')+'"'
 return [keys,...rows.map(row=>keys.map(key=>row[key]??''))].map(row=>row.map(escape).join(',')).join('\n')
}
async function open(ui,p,section,label,selector){
 const menu=p.getByRole('button',{name:'Buka menu',exact:true});if(await menu.isVisible())await menu.click()
 const link=p.getByRole('button',{name:'• '+label,exact:true});if(!await link.isVisible())await p.locator('.sidebar .nav-main').filter({hasText:section}).click()
 await link.click();await ui.expect(p.locator(selector).getByRole('heading',{name:label,exact:true})).toBeVisible()
}
async function lifecycle(ui,today,mobile){
 // Setup only creates mandor, existing FG work cards and payment account.
 // Every opening CSV, validation, posting, allocation and payroll action is UI.
 const f=fixture('create_opening_source',{today}),user=await ui.login('OWNER',{label:'p12-opening-'+mobile,mobile,timezoneId:mobile?'America/Los_Angeles':'Asia/Jakarta'}),p=user.page
 const suffix=mobile?'MOBILE':'DESKTOP',imp=p.locator('.initial-import'),pay=p.locator('.cpay'),detail=pay.getByRole('region',{name:'Rincian payroll'})
 const read=()=>fixture('read_opening_pipeline',f)
 async function confirm(label,setup){
  await detail.getByRole('button',{name:label,exact:true}).click();const form=detail.getByRole('region',{name:'Periksa tindakan payroll'})
  if(setup)await setup(form)
  await form.getByLabel('Alasan tindakan payroll',{exact:true}).fill('P12 sumber saldo awal dan kerja baru sudah diperiksa')
  await form.getByLabel('Rincian payroll sudah diperiksa',{exact:true}).check()
  await form.getByRole('button',{name:label==='Koreksi payroll lunas'?'Batalkan payroll dan pembayaran sekarang':label+' sekarang',exact:true}).click()
 }
 try{
  await open(ui,p,'Pengaturan & Audit','Impor data awal','.initial-import')
  await imp.getByLabel('Kode batch',{exact:true}).fill(f.batch_code);await imp.getByLabel('Tanggal saldo awal',{exact:true}).fill(f.cutover)
  await imp.getByRole('button',{name:'Buat draft',exact:true}).click()
  await ui.expect(imp.getByLabel('Batch impor',{exact:true})).not.toHaveValue('');f.batch=await imp.getByLabel('Batch impor',{exact:true}).inputValue()
  for(const [entity,rows] of Object.entries(f.import_rows)){
   await imp.getByLabel('Jenis data',{exact:true}).selectOption(entity)
   await imp.getByLabel('Pilih file CSV',{exact:true}).setInputFiles({name:entity+'.csv',mimeType:'text/csv',buffer:Buffer.from(csv(rows))})
   await imp.getByRole('button',{name:'Simpan perubahan draft',exact:true}).click()
   await ui.expect(imp.getByRole('button',{name:'Simpan perubahan draft',exact:true})).toHaveCount(0)
  }
  await imp.getByRole('button',{name:'Periksa seluruh draft',exact:true}).click()
  await ui.expect(imp.getByRole('button',{name:'Sahkan data awal',exact:true})).toBeEnabled()
  await imp.getByRole('button',{name:'Sahkan data awal',exact:true}).click();await ui.expect(imp).toContainText('Sudah disahkan')
  const baseline=read();f.balances=baseline.balances;f.entitlement=baseline.entitlement
  assert.deepEqual(Object.fromEntries(Object.entries(baseline.remaining).map(([k,v])=>[k,Number(v)])),{'UPAH-OLD':65,'REIMB-OLD':20,'KASBON-OLD':30});assert.equal(Number(baseline.carry),4);assert.deepEqual(baseline.physical,f.physical)

  await open(ui,p,'Produksi','Susun Nota FG','.cnota');const nota=p.locator('.cnota')
  await nota.getByLabel('Cari kartu nota',{exact:true}).fill(f.label);await nota.getByRole('button',{name:'Cari kartu',exact:true}).click();await ui.expect(nota.locator('.cnota-source')).toHaveCount(2)
  await nota.locator('.cnota-source').first().getByRole('button',{name:'Tambahkan ke nota',exact:true}).click();await nota.locator('.cnota-source').getByRole('button',{name:'Tambahkan ke nota',exact:true}).click()
  await nota.getByRole('button',{name:'Simpan draft nota',exact:true}).click();await ui.expect(nota.locator('.cnota-review')).toContainText('Draft')
  await nota.getByLabel('Nota sudah diperiksa',{exact:true}).check();await nota.getByRole('button',{name:'Posting ke payroll',exact:true}).click()
  await ui.expect.poll(()=>fixture('read',f).notes[0]?.status).toBe('POSTED');const posted=fixture('read',f);assert.equal(posted.payroll.length,1);f.payroll=posted.notes[0].payroll_id

  await open(ui,p,'Pengaturan & Audit','Impor data awal','.initial-import');await imp.getByLabel('Batch impor',{exact:true}).selectOption(f.batch)
  const payable=imp.getByRole('region',{name:'Saldo awal dokumen'})
  for(const [kind,amount] of [['UPAH-OLD','65'],['REIMB-OLD','20']]){
   await payable.getByLabel('Dokumen saldo awal',{exact:true}).selectOption(f.balances[kind]);await payable.getByLabel('Tindakan saldo awal',{exact:true}).selectOption('ALLOCATE_PAYROLL')
   await payable.getByLabel('Payroll saldo awal',{exact:true}).selectOption(f.payroll);await payable.getByLabel('Nominal saldo awal',{exact:true}).fill(amount)
   await payable.getByLabel('Alasan pelunasan saldo awal',{exact:true}).fill('P12 utang lama dibayar bersama payroll')
   await payable.getByRole('button',{name:'Bayar lewat payroll',exact:true}).click();await ui.expect(payable.getByRole('button',{name:/^Lepas dari /})).toHaveCount(1)
  }
  const advance=imp.getByRole('region',{name:'Kasbon tunai saldo awal'}),carry=imp.getByRole('region',{name:'Hak upah sebelum saldo awal'})
  await advance.getByLabel('Payroll untuk kasbon',{exact:true}).selectOption(f.payroll);await advance.getByLabel('Nominal alokasi kasbon',{exact:true}).fill('30')
  await advance.getByRole('button',{name:'Simpan alokasi kasbon',exact:true}).click();await ui.expect(advance.getByRole('button',{name:/^Lepas alokasi /})).toHaveCount(1)
  await carry.getByLabel('Payroll carry',{exact:true}).selectOption(f.payroll);await carry.getByLabel('Jumlah carry',{exact:true}).fill('2')
  let first=null,replay=null,lost=false
  if(mobile)await p.route('**/rest/v1/rpc/erp_save_initial_import_action_v1',async route=>{
   const body=route.request().postDataJSON()
   if(body.p_action==='PAYROLL_ENTITLEMENT'&&!lost){first=body;const response=await route.fetch();assert.equal(response.status(),200);lost=true;await route.abort('failed')}
   else{if(body.p_action==='PAYROLL_ENTITLEMENT'&&replay===null)replay=body;await route.continue()}
  })
  await carry.getByRole('button',{name:'Simpan carry ke payroll',exact:true}).click();await ui.expect.poll(()=>read().document.net_payable).toBe('6060.00')
  if(mobile){
   await ui.expect(imp.getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeVisible();await p.reload();await open(ui,p,'Pengaturan & Audit','Impor data awal','.initial-import')
   await imp.getByRole('button',{name:'Reconcile transaksi',exact:true}).click();await ui.expect(imp.getByRole('button',{name:'Reconcile transaksi',exact:true})).toHaveCount(0)
   assert.ok(lost);assert.deepEqual(replay,first)
  }else await ui.expect(carry.getByRole('button',{name:/^Lepas carry dari /})).toHaveCount(1)
  assert.equal(Number(read().carry),2);assert.deepEqual(changed(baseline.gl,read().gl),{})

  await open(ui,p,'Keuangan','Payroll & Kasbon','.cpay');await pay.getByLabel('Cari payroll',{exact:true}).fill(f.label);await pay.getByRole('button',{name:'Cari payroll',exact:true}).click()
  await ui.expect(pay.locator('.cproc-receipt')).toHaveCount(1);await pay.locator('.cproc-receipt').click();await detail.getByRole('button',{name:'Hitung sumber',exact:true}).click()
  await ui.expect(detail.locator('.cpay-net')).toHaveText('Bersih payrollRp6.060')
  await ui.expect.poll(()=>pay.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&document.documentElement.scrollWidth<=innerWidth+1})).toBe(true)
  mkdirSync('cp6-proof/t3',{recursive:true});await p.evaluate(()=>window.scrollTo(0,0));await p.screenshot({path:`cp6-proof/t3/P12_OPENING_${suffix}.png`,fullPage:true})
  await confirm('Setujui payroll');await ui.expect(detail.getByRole('button',{name:'Lunasi payroll',exact:true})).toBeEnabled()
  assert.deepEqual(changed(baseline.gl,read().gl),{[f.labor]:5,[f.payable]:-5})
  await confirm('Lunasi payroll',async form=>{
   await ui.expect(form.getByLabel('Tanggal pembayaran payroll',{exact:true})).toHaveValue(today)
   await form.getByLabel('Cari akun pembayaran payroll',{exact:true}).fill(f.bank_code);await form.getByRole('button',{name:'Cari akun pembayaran',exact:true}).click()
   await ui.expect(form.locator('.cpay-cash-row')).toHaveCount(1);await form.locator('.cpay-cash-row').click()
  })
  await ui.expect(detail.locator('.cpay-net')).toHaveText('Jumlah dilunasiRp6.060');let actual=read()
  assert.ok(Object.values(actual.remaining).every(v=>Number(v)===0));assert.equal(Number(actual.carry),2)
  assert.deepEqual(changed(baseline.gl,actual.gl),{[f.labor]:5,[f.payable]:6085,[f.receivable]:-30,[f.bank_coa]:-6060})
  await confirm('Koreksi payroll lunas');await ui.expect(detail.locator('.cpay-net')).toHaveText('Jumlah pada dokumen batalRp6.060');actual=read()
  assert.equal(actual.document.status,'REVERSED');assert.deepEqual(actual.remaining,baseline.remaining);assert.equal(Number(actual.carry),4)
  assert.deepEqual(changed(baseline.gl,actual.gl),{});assert.deepEqual(actual.physical,baseline.physical);assert.deepEqual(actual.opening_journals,baseline.opening_journals)
  return {status:'PASS',mobile,browser_csv_create_validate_finalize:true,browser_nota_and_three_opening_source_allocations:true,browser_prepare_approve_pay_reverse:true,cash:'6060',only_new_carry_expense:'5',old_payables_not_reaccrued:true,inverse_restores_opening_balances_carry_gl:true,stock_hpp_opening_journals_unchanged:true,exact_lost_allocation_reply_replay:mobile?true:null,screenshot:`P12_OPENING_${suffix}.png`}
 }catch(error){
  mkdirSync('cp6-proof/t3',{recursive:true});writeFileSync(`cp6-proof/t3/P12_OPENING_${suffix}_FAILURE.json`,JSON.stringify({error:String(error),import:await imp.innerText().catch(()=>''),payroll:await pay.innerText().catch(()=>''),source:f.batch?read():null},null,2))
  await p.screenshot({path:`cp6-proof/t3/P12_OPENING_${suffix}_FAILURE.png`,fullPage:true});throw error
 }finally{await user.context.close()}
}
export async function cases(ui,today){return [['P12_OPENING_BROWSER_DESKTOP_CYCLE',()=>lifecycle(ui,today,false)],['P12_OPENING_BROWSER_MOBILE_RECOVERY',()=>lifecycle(ui,today,true)]]}
