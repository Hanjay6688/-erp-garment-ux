import original from'./nativeAnalysisStandin.json'
export function nativeEpisodeFixture(request='00000000-0000-4000-8000-000000000801',analysis:unknown=original){
 const at='2026-10-01T00:00:00+00:00'
 return{contract_version:'cp7.native-obligation-observation.v1',actor_scope_id:original.analysis.scope.actor_scope_id,analysis:structuredClone(analysis),rule_version:'cp7.native-obligation.v1',read_kind:'SAVED_OBSERVATION',read_at:at,
  result:{request_id:request,status:'COMMITTED',domain:'AR',source_status:'COMPLETE',source_hash:'a'.repeat(64)as string|null,as_of:'2026-10-01'as string|null,source_read_at:at as string|null,observed_at:at as string|null,source_total:'1'as string|null,
   rows:[{source_id:'00000000-0000-4000-8000-000000000201',source_label:'AR-SUMBER-1',condition_state:'OVERDUE',freshness:'KNOWN',reason:'NATIVE_CONDITION_REQUIRES_REVIEW',source_revision:'9007199254740993',native_source_hash:'b'.repeat(64)as string|null,business_resolved:false,transition:'OPENED',episode:{id:'00000000-0000-4000-8000-000000000901',number:'1',previous_episode_id:null as string|null,state:'ACTIVE',freshness:'KNOWN',first_observed_at:at,last_observed_at:at,last_known_observed_at:at as string|null,closed_at:null as string|null,revision:'1'}}]}}
}
