// Read-only diagnostics on the current loopback page; never reads storage/tokens.
import assert from 'node:assert/strict'
import {writeFileSync} from 'node:fs'
export function observePage(page,id){
 const consoleErrors=[],pageErrors=[],workspaceResponses=[],pending=[]
 page.on('console',message=>{if(message.type()==='error')consoleErrors.push(message.text())})
 page.on('pageerror',error=>pageErrors.push({message:String(error),stack:error.stack??null}))
 page.on('response',response=>{
  if(response.url().split('/rpc/')[1]==='erp_get_bs_resolution_workspace_v1')pending.push(response.json().then(body=>workspaceResponses.push({status:response.status(),body})).catch(error=>workspaceResponses.push({read_error:String(error)})))
 })
 async function capture(phase){
  await Promise.all(pending)
  let dom
  try{
   dom=await page.evaluate(()=>{
    const copy=document.documentElement.cloneNode(true)
    // Only the clone is changed. Script/style payload is irrelevant to DOM
    // identity and is omitted; no local/session storage or request headers.
    for(const item of copy.querySelectorAll('script,style'))item.textContent='[OMITTED_SCRIPT_OR_STYLE_TEXT]'
    return{url:location.href,title:document.title,body_text:document.body?.innerText??null,main_count:document.querySelectorAll('main').length,root_children:document.getElementById('root')?.childElementCount??null,root_html_with_script_style_payload_omitted:copy.outerHTML,dialog_labels:[...document.querySelectorAll('[role="dialog"] label')].map(label=>({text:label.textContent,span:[...label.querySelectorAll(':scope>span')].map(x=>x.textContent),controls:[...label.querySelectorAll('input,select,textarea')].map(x=>({tag:x.tagName,aria_label:x.getAttribute('aria-label'),value:x.value,disabled:x.disabled}))}))}
   })
  }catch(error){dom={read_error:String(error),url:page.url()}}
  const report={id,phase,consoleErrors,pageErrors,workspaceResponses,dom,read_only:true,actual_dom_not_modified:true,storage_or_headers_read:false}
  writeFileSync(`cp6-proof/t3/${id}_Q3_DOM_${phase}.json`,JSON.stringify(report,null,2))
  return report
 }
 return{capture,async complete(){const result=await capture('complete');assert.deepEqual(result.consoleErrors,[],'Q3_CONSOLE_ERRORS');assert.deepEqual(result.pageErrors,[],'Q3_PAGE_ERRORS');return result}}
}
