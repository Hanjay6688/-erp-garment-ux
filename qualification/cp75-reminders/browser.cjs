const [app, out, origin] = process.argv.slice(2)
const { createRequire } = require('node:module')
const path = require('node:path')
const fs = require('node:fs')
const assert = require('node:assert/strict')
const fromApp = createRequire(path.join(app, 'package.json'))
const { chromium, expect } = fromApp('@playwright/test')
const observations = []
const entry = `
import {createRoot} from 'react-dom/client'
import ConnectedRemindersPage from './src/ConnectedRemindersPage'
createRoot(document.getElementById('root')).render(<ConnectedRemindersPage/>)
`
const identity = `import {recoveryIdentity} from './tests/fixtures/productionRecovery'
const identity = {...recoveryIdentity,identity:{...recoveryIdentity.identity,permissions:['settings.reminder.view','settings.reminder.manage']}}
export const useAuth=()=>identity`
const transport = `const client={rpc:async(name,args)=>{
  const reply=await fetch('/rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,args})});
  if(!reply.ok)throw Error('Synthetic RPC error '+reply.status);return reply.json()
}};export const getUatSupabaseClient=()=>client`
function record(item) {
  observations.push(item)
  fs.writeFileSync(path.join(out,'browser.json'), JSON.stringify(observations,null,2)+'\n')
}
async function ctl(route,args={}) {
  const res=await fetch(origin+route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(args)})
  const data=await res.json()
  assert.ok(res.ok,JSON.stringify(data))
  return data
}
async function run() {
  await fromApp('esbuild').build({absWorkingDir:app,stdin:{contents:entry,loader:'tsx',resolveDir:app},
    outfile:path.join(out,'ui.js'),bundle:true,jsx:'automatic',define:{'process.env.NODE_ENV':'"production"'},
    plugins:[{name:'loopback-fixture',setup(build){
      build.onResolve({filter:/\/auth\/AuthProvider$|^\.\/AuthProvider$/},()=>({path:'identity',namespace:'fixture'}))
      build.onResolve({filter:/\/lib\/supabase$/},()=>({path:'transport',namespace:'fixture'}))
      build.onLoad({filter:/.*/,namespace:'fixture'},args=>({contents:args.path==='identity'?identity:transport,resolveDir:app}))
    }}]})
  const browser=await chromium.launch({executablePath:process.env.CHROME_BIN || undefined})
  const page=await browser.newPage({timezoneId:'Asia/Jakarta'})
  page.setDefaultTimeout(12000)
  const btn=name=>page.getByRole('button',{name,exact:true})
  const list=page.getByRole('region',{name:'Daftar pengingat'}).locator('article')
  const labels=async()=>list.evaluateAll(nodes=>nodes.map(n=>n.getAttribute('aria-label').replace(/^Pengingat /,'')))
  const snap=async()=>{
    await expect(page.getByText('Memuat pengingat…',{exact:true})).toHaveCount(0)
    await expect(page.getByRole('region',{name:'Daftar pengingat'})).toBeVisible()
  }
  const queries=[]
  page.on('request',r=>{if(r.url()===origin+'/rpc'){const b=r.postDataJSON();if(b.name==='erp_cp7_get_reminders_v1')queries.push(b.args.p_query)}})
  async function start(n) {
    await ctl('/seed',{n}); await page.goto(origin); await btn('Belum selesai').click(); await snap()
  }
  try {
    for (const n of [26,51,1]) {
      await start(n)
      for(let i=25;i<n;i+=25){await btn('Pengingat berikutnya').click();await snap()}
      await btn('Tandai selesai R'+(n-1)).click()
      const offset=Math.max(0,n-26)
      const heading=n===1?'Tidak ada pengingat':(offset+1)+'–'+(n-1)+' dari '+(n-1)
      await expect(page.getByText(heading,{exact:true})).toBeVisible()
      await btn('Muat ulang pengingat').click();await snap()
      const facts=await ctl('/facts')
      assert.equal(facts.length,n-1);assert.deepEqual(await labels(),facts.slice(offset,offset+25).map(r=>r.title))
      assert.deepEqual(queries.at(-1),{filter:'OPEN',limit:25,offset})
      record({case:'page after save',initial:n,heading,offset,visible:await labels(),sqlOpen:facts.length,refreshQuery:queries.at(-1)})
    }
    for(const mode of ['remove','insert','reorder']) {
      await start(27); await ctl('/change',{mode}); await btn('Pengingat berikutnya').click()
      await expect(page.getByText('Urutan pengingat berubah. Daftar terbaru ditampilkan dari awal.')).toBeVisible()
      const first=await labels();await btn('Pengingat berikutnya').click();await snap()
      const seen=[...first,...await labels()], facts=await ctl('/facts')
      assert.deepEqual(seen,facts.map(r=>r.title));assert.equal(new Set(seen).size,seen.length)
      record({case:'two sessions change ordering',mode,sql:seen.length,unique:new Set(seen).size,returnedToFirst:true})
    }
    await start(26);await btn('Pengingat berikutnya').click();await snap();await ctl('/change',{mode:'remove'})
    await btn('Muat ulang pengingat').click()
    await expect(page.getByText('1–25 dari 25',{exact:true})).toBeVisible()
    assert.deepEqual(await labels(),(await ctl('/facts')).map(r=>r.title))
    record({case:'refresh after second session removes row',visible:await labels(),query:queries.at(-1)})
    for(const mode of ['title','note','midnight']) {
      await start(1);const [before]=await ctl('/facts')
      await btn('Ubah R0').click()
      if(mode==='title')await page.getByLabel('Judul pengingat',{exact:true}).fill('Judul baru')
      if(mode==='note')await page.getByLabel('Catatan pengingat',{exact:true}).fill('Catatan baru')
      if(mode==='midnight')await page.getByLabel('Jatuh tempo pengingat (WIB)',{exact:true}).fill('2026-11-21T00:00')
      await btn('Simpan perubahan').click()
      await expect(page.getByText(/Perubahan pengingat .* disimpan\./)).toBeVisible();await snap()
      const [after]=await ctl('/facts')
      assert.equal(before.due,'2026-11-20T07:00:32.942069+00:00')
      assert.equal(after.due,mode==='midnight'?'2026-11-20T17:00:00+00:00':before.due)
      assert.equal(after.version,before.version+1);assert.equal(after.id,before.id)
      assert.equal(after.title,mode==='title'?'Judul baru':before.title)
      assert.equal(after.note,mode==='note'?'Catatan baru':before.note)
      record({case:'committed edit read on a new connection',mode,before,after})
    }
    await start(1)
    // Base this control on a genuine overdue reminder, independent of the runner's wall clock.
    await btn('Ubah R0').click();await page.getByLabel('Jatuh tempo pengingat (WIB)',{exact:true}).fill('2020-01-01T00:00')
    await btn('Simpan perubahan').click();await expect(page.getByText(/Perubahan pengingat .* disimpan\./)).toBeVisible();await snap()
    await expect(page.getByText('Lewat jatuh tempo',{exact:true})).toBeVisible()
    record({case:'unmodified SQL response',visible:await labels()})
    for(const kind of ['zero_count','wrong_state','impossible_date','no_timezone']) {
      await page.route('**/rpc',async route=>{
        const response=await route.fetch(),reply=await response.json()
        assert.equal(reply.data.items.length,1)
        if(kind==='zero_count')reply.data.due.overdue=0
        if(kind==='wrong_state')reply.data.items[0].due_state='LATER'
        if(kind==='impossible_date')reply.data.today='2026-02-30'
        if(kind==='no_timezone')reply.data.items[0].due_at=reply.data.items[0].due_at.replace(/(?:Z|[+-]\d{2}:\d{2})$/,'')
        await route.fulfill({response,json:reply})
      },{times:1})
      await btn('Muat ulang pengingat').click()
      await expect(page.getByRole('alert')).toBeVisible()
      await expect(page.getByRole('region',{name:'Ringkasan pengingat'})).toHaveCount(0)
      await expect(list).toHaveCount(0)
      await btn('Muat ulang pengingat').click();await snap()
      assert.deepEqual(await labels(),['R0'])
      record({case:'reader rejection and recovery',kind,mutatedAt:'browser transport',recovered:true})
    }
  } finally {await browser.close()}
}
run().catch(error=>{console.error(error);process.exitCode=1})
