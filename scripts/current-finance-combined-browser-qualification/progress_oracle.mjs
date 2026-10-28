import assert from 'node:assert/strict'

export const PROGRESS='erp_cp7_get_frozen_analysis_progress_v1'
const number=n=>new Intl.NumberFormat('id-ID',{useGrouping:true}).format(n)
const timestamp=s=>new Intl.DateTimeFormat('id-ID',{timeZone:'Asia/Jakarta',dateStyle:'medium',timeStyle:'short',hour12:false}).format(new Date(s))+' WIB'
const micros=s=>{
  const m=/^(.+:\d{2})(?:\.(\d{1,6}))?(Z|[+-]\d{2}:\d{2})$/.exec(s)
  assert.ok(m,'SERVER_TIMESTAMP_REQUIRED')
  return BigInt(Date.parse(m[1]+m[3]))*1000n+BigInt((m[2]??'').padEnd(6,'0'))
}
const duration=ms=>{
  const seconds=Math.floor(ms/1000)
  if(seconds<60)return `${seconds} detik`
  if(seconds<3600)return `${Math.floor(seconds/60)} menit ${seconds%60} detik`
  return `${Math.floor(seconds/3600)} jam ${Math.floor(seconds/60)%60} menit`
}

// Read the real response captured by route.fetch(), independently of the UI's
// parser/projection. This helper never manufactures an RPC reply or advances work.
export function expectedProgress(wire,request,state){
  assert.equal(wire.contract_version,'cp7.frozen-analysis-progress.v1')
  assert.equal(wire.policy_id,'D17-18-20261026')
  assert.equal(wire.status.request_id,request)
  assert.equal(wire.production_go,false)
  const job=wire.status,side=job.finance_capture
  assert.equal(job.state,'DONE')
  const phases=[{name:'produksi',done:job.units_done,total:job.plan_final?job.unit_count:null}]
  if(state==='ACCESS_REVOKED'){
    assert.equal(side.state,'ACCESS_REVOKED')
    assert.equal(side.capture,null);assert.equal(side.result,null);assert.equal(wire.finance,null)
  }else{
    assert.equal(side.state,state==='RUNNING'?'RUNNING':'READY')
    if(state!=='RUNNING')assert.equal(side.result.readiness,state==='BLOCKED'?'BLOCKED':'READY')
    assert.equal(wire.finance.capture_id,side.capture.capture_id)
    phases.push({name:'keuangan dan hpp',done:side.capture.units_done,total:side.capture.units_total})
  }
  for(const p of phases){
    assert.ok(Number.isSafeInteger(p.done)&&p.done>=0)
    if(p.total!==null)assert.ok(Number.isSafeInteger(p.total)&&p.total>=p.done)
  }
  const texts=phases.map(p=>`${number(p.done)} langkah selesai${p.total===null?'; jumlah akhir belum diketahui.':` dari ${number(p.total)}.`}`)
  const bars=phases.filter(p=>p.total!==null&&p.total>0)
  const percentages=bars.map(p=>`${Number(BigInt(p.done)*10000n/BigInt(p.total))/100}% bagian ${p.name}.`)
  texts.push(...percentages)
  texts.push('Status server diperiksa '+timestamp(wire.observed_at)+'.')
  let elapsedMs=null
  if(state!=='ACCESS_REVOKED'){
    const terminal=state!=='RUNNING'
    assert.equal(wire.finance.finished_at!==null,terminal)
    const ends=terminal?[wire.operational.finished_at,wire.finance.finished_at]:[wire.observed_at]
    const end=ends.map(micros).reduce((a,b)=>a>b?a:b)
    const delta=end-micros(wire.operational.created_at)
    assert.ok(delta>=0n)
    const elapsed=Number(delta/1000n)
    elapsedMs=elapsed
    texts.push(`${terminal?'Waktu pemrosesan':'Waktu berjalan yang tercatat'}: ${duration(elapsed)}.`)
  }
  return {texts,bars,percentages,elapsedMs,state,request,observed_at:wire.observed_at}
}

export async function assertCombinedProgress(ui,page,calls,request,state){
  const panel=page.getByRole('region',{name:'Kemajuan analisis gabungan',exact:true})
  await ui.expect(panel).toHaveAttribute('data-combined-state',state)
  let matched
  // UI rendering may follow the recorded HTTP completion. Compare a complete
  // rendered observation against actual successful responses for this UUID.
  await ui.expect.poll(async()=>{
    const text=await panel.innerText()
    const observations=calls.filter(c=>c.name===PROGRESS&&c.status===200&&c.args.p_request===request)
    for(const call of observations.slice().reverse()){
      let wanted
      try{wanted=expectedProgress(call.body,request,state)}catch{continue}
      if(wanted.texts.every(t=>text.includes(t))){matched=wanted;return true}
    }
    return false
  }).toBe(true)
  assert.ok(matched)
  assert.deepEqual((await panel.locator('p').allTextContents()).filter(t=>t.includes('%')).sort(),matched.percentages.slice().sort())
  await ui.expect(panel.getByRole('progressbar')).toHaveCount(matched.bars.length)
  for(const p of matched.bars){
    const bar=panel.getByRole('progressbar',{name:'Kemajuan '+p.name,exact:true})
    await ui.expect(bar).toHaveAttribute('value',String(p.done))
    await ui.expect(bar).toHaveAttribute('max',String(p.total))
  }
  await ui.expect(panel).toContainText('Kemajuan setiap bagian dihitung terpisah.')
  if(state==='RUNNING')await ui.expect(panel).toContainText('Analisis gabungan masih menunggu laporan keuangan resmi.')
  if(state==='ACCESS_REVOKED'){
    await ui.expect(panel).not.toContainText('Waktu pemrosesan:')
    await ui.expect(panel).not.toContainText('Waktu berjalan yang tercatat:')
  }
  return {...matched,real_RPC_response:true,DOM_counts_exact:true,extra_overall_progressbar:false}
}
