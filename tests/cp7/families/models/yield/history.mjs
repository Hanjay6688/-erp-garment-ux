// Synthetic finished-cut records, never factory evidence. Ranges are computed
// by the SQL kernel; these fixture observations are not expert thresholds.
export const context = { runId:'yield-demo-run', actorScope:'yield-demo-scope', accessEpoch:'yield-demo-epoch' }
export const policy = { version:'demo-policy-not-factory-calibrated-v1', minimumPeers:'20', lowerQuantile:'0.1', upperQuantile:'0.9', windowStart:'2026-03-01', asOf:'2026-09-01' }
export const mixes = { small:['28','28','29','29','30','30'], unique:['28','29','29','29','30','30'], jumbo:['31','31','32','32','33','33'], all30:['30','30','30','30','30','30'] }
export function input(mix='small', width=null, length='100', actual='100') {
  return { rollId:'fixture-yield-current-roll', rollRevision:'fixture-r1', materialId:'fixture-fabric-A',
    patternId:'fixture-pattern-A', patternRevision:'fixture-pattern-r1', consumed:{value:length,unit:'M'},
    usableWidthCm:width, markerRevision:`fixture-layout-${mix}-r1`, sizeSlots:mixes[mix], observedCutPcs:actual, outputComplete:true,
    materialFamily:{brandId:'fixture-brand-A',millId:'fixture-mill-A',behaviourBasis:'FIXTURE_MATERIAL_HISTORY_NOT_VERIFIED'},
    measurements:{issuedDeclaredM:'100',issuedMeasuredM:length,remainingMeasuredM:'0',familyWidthCm:'150',evidence:'FIXTURE_ONLY',refs:['fixture-length-proof@r1']} }
}
export function demoHistory(actorScope=context.actorScope) {
  const rows=[]
  const groups=[['small',null,'100',[80,100,120]],['small','150','100',[90,100,110]],['small','140','100',[84,94,104]],
    ['unique',null,'100',[74,94,114]],['unique','150','100',[84,94,104]],
    ['jumbo',null,'100',[60,80,100]],['jumbo','150','100',[70,80,90]],
    ['small',null,'80',[64,80,96]],['small','150','80',[72,80,88]]]
  for(const [mix,width,length,pcs] of groups) for(let index=0;index<24;index++) {
    const rollId=`fixture-${mix}-${width??'unknown'}-${length}-${index+1}`
    rows.push({actorScope,sourceRevision:'fixture-r1',revisionSequence:'1',state:'ACTIVE',
      occurredOn:`2026-0${3+Math.floor(index/8)}-${String(1+index%8).padStart(2,'0')}`,knownOn:'2026-08-01',
      input:{...input(mix,width,length,String(pcs[Math.floor(index/8)])),rollId} })
  }
  return rows
}
export function request(i=input(), history=demoHistory(), ctx=context) {
  return {contract:'f04.yield-history-request.v1',input:i,inputKey:'kernel-test-input',context:ctx,history,policy}
}
