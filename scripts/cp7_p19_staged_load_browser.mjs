import assert from 'node:assert/strict'

// Start at the actual trusted control click, finish only after the verified
// first page has rendered and two paint frames. An acknowledgement is not a load.
export async function armStagedResultOpen(button,key,runId){
 await button.evaluate((element,{key,runId})=>{
  const all=window.__p19StagedOpens??=Object.create(null)
  if(all[key])throw Error('P19_STAGED_OPEN_DUPLICATE_MEASUREMENT')
  element.addEventListener('click',event=>{
   const r=all[key]={t0:performance.now(),trusted_click:event.isTrusted,elapsed_ms:null,run_id:null}
   let queued=false
   const ready=()=>{
    const root=document.querySelector('[aria-label="Hasil analisis bertahap"]')
    return root?.dataset.runId===runId&&root.querySelector('[data-page-index="0"]')?root:null
   }
   const observer=new MutationObserver(()=>{
    if(queued||!ready())return
    queued=true;requestAnimationFrame(()=>requestAnimationFrame(()=>{
     const root=ready();if(root){r.run_id=root.dataset.runId;r.elapsed_ms=performance.now()-r.t0;observer.disconnect()}else queued=false
    }))
   });observer.observe(document.body,{subtree:true,attributes:true,childList:true,characterData:true})
  },{capture:true,once:true})
 },{key,runId})
}
export async function readStagedResultOpen(page,key){
 // Owner 8 Oct: 3 s is a goal, not a mandatory acceptance gate. The driver
 // still waits for real verified content and records the full measured time.
 await page.waitForFunction(key=>window.__p19StagedOpens?.[key]?.elapsed_ms!=null,key,{timeout:30000,polling:50})
 const r=await page.evaluate(key=>window.__p19StagedOpens[key],key)
 assert.equal(r.trusted_click,true);assert.ok(Number.isFinite(r.elapsed_ms))
 return{...r,target_ms:3000,within_target:r.elapsed_ms<3000}
}
