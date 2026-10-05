import assert from 'node:assert/strict'

// Decode the complete handoff and compare with the real Native envelope;
// substring matching cannot establish integrity once source text is escaped.
export function assertQuotedNativePrompt(prompt,original,question){
 assert.deepEqual(prompt.match(/<\/?DATA_ERP_JSON>/g),['<DATA_ERP_JSON>','</DATA_ERP_JSON>'])
 assert.deepEqual(prompt.match(/<\/?PERTANYAAN_JSON>/g),['<PERTANYAAN_JSON>','</PERTANYAAN_JSON>'])
 const source=prompt.split('<DATA_ERP_JSON>\n\n')[1].split('\n\n</DATA_ERP_JSON>')[0]
 const quotedQuestion=prompt.split('<PERTANYAAN_JSON>\n\n')[1].split('\n\n</PERTANYAAN_JSON>')[0]
 assert.ok(!/[<>&\u2028\u2029\n]/.test(source));assert.ok(!/[<>&\u2028\u2029\n]/.test(quotedQuestion))
 const data=JSON.parse(source),coverage=JSON.parse(prompt.split('CAKUPAN SUMBER\n\n')[1].split('\n\n')[0])
 assert.deepEqual(Object.keys(data).sort(),['analysis','analysis_report','financial_source','product_labels'])
 assert.deepEqual(data.analysis,original.analysis);assert.deepEqual(data.financial_source,original.financial_source);assert.deepEqual(data.product_labels,original.product_labels)
 assert.equal(JSON.parse(quotedQuestion),question)
 assert.equal(typeof data.analysis_report,'string');assert.ok(data.analysis_report.includes(original.analysis.semantic_hash))
 assert.equal(coverage.contract_version,'cp7.native-ai-handoff.v2');assert.equal(coverage.source_encoding,'JSON_ESCAPED_FRAMING_CHARACTERS')
 assert.equal(coverage.serialized_source_utf8_bytes,Buffer.byteLength(source,'utf8'))
 return{data,coverage,source}
}

// Actual Chromium navigation with an explicit provider-only network fault.
// Loopback ERP/Auth stays live; no external provider response is fabricated.
export async function offlineManualHandoff(ui,{context,panel,original,question,state,shot,suffix}){
 const destination='https://chatgpt.com/',pattern=destination+'**'
 const requests=[],failures=[],before=state()
 const manual=panel.getByLabel('Salinan manual pertanyaan dan sumber ERP',{exact:true})
 const prompt=await manual.inputValue()
 assertQuotedNativePrompt(prompt,original,question)
 const link=panel.getByRole('link',{name:'Tautan manual ChatGPT',exact:true})
 assert.equal(await link.getAttribute('href'),destination)
 assert.equal(await link.getAttribute('target'),'_blank')
 assert.equal(await link.getAttribute('rel'),'noopener noreferrer')
 const refuse=async route=>{
  const request=route.request()
  requests.push({url:request.url(),method:request.method(),post_data:request.postData()})
  await route.abort('internetdisconnected')
 }
 const failed=request=>{
  if(request.url().startsWith(destination))failures.push({url:request.url(),error:request.failure()?.errorText})
 }
 let popup=null
 context.on('requestfailed',failed)
 await context.route(pattern,refuse)
 try{
  const opening=context.waitForEvent('page')
  opening.catch(()=>{}) // Register rejection before the click can itself fail.
  await link.click();popup=await opening
  await ui.expect.poll(()=>requests.length).toBeGreaterThan(0)
  await ui.expect.poll(()=>failures.length).toBeGreaterThan(0)
  assert.ok(requests.every(r=>r.url===destination&&r.method==='GET'&&r.post_data===null))
  assert.ok(failures.every(r=>r.url===destination&&r.error?.includes('ERR_INTERNET_DISCONNECTED')))
  await ui.expect(manual).toBeVisible()
  assert.equal(await manual.inputValue(),prompt)
  assert.equal(await panel.getByLabel('Pertanyaan analisis ERP',{exact:true}).inputValue(),question)
  assert.deepEqual(state(),before)
  await shot(`P17_MANUAL_PROVIDER_OFFLINE_${suffix}.png`)
  return{fault:'DECLARED_PROVIDER_ONLY_CHROMIUM_ROUTE_ABORT_INTERNETDISCONNECTED',
   actual_browser_failed_navigation:failures,actual_destination_requests:requests,
   complete_prompt_and_question_unchanged:true,complete_Native_business_and_capture_count_unchanged:true,
   static_URL_GET_without_ERP_data:true,provider_network_contact:false,
   provider_outage_measured:false,full_E18_acceptance:false}
 }finally{
  try{if(popup&&!popup.isClosed())await popup.close()}
  finally{
   context.off('requestfailed',failed)
   await context.unroute(pattern,refuse)
  }
 }
}
