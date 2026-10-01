// Receiver/DOM fixture only. Native qualification uses the original ERP writers.
import analysisFixture from './nativeAnalysisStandin.json'
export function attentionFixture(analysis:typeof analysisFixture=structuredClone(analysisFixture)){
 return{contract_version:'cp7.analysis-attention.v1',analysis:structuredClone(analysis),rows:analysis.analysis.actions.map(a=>({action_key:a.key,condition:analysis.source_state==='ARCHIVED_STALE'?'SOURCE_CHANGED':'REVIEW_REQUIRED',attention:{state:'NEW',resume_at:null as string|null,resume_due:false,revision:'0',updated_at:null as string|null},manual:null as null|Record<string,unknown>,business_resolved:false})),read_at:analysis.analysis.snapshot.effective_as_of,native_manual_page_complete:true,delivery:{status:'NOT_CONFIGURED',sent:false}}
}
