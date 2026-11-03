import assert from 'node:assert/strict'
export const dialogStates=['ready','long','empty','loading','error','stale','approved','review','pending']
export const cp7Surfaces=['prioritas-produksi','stok-saran-sku','panel-potongan','business-report','reminder','tanya-ai','sambungan-whatsapp','benchmark-metode'].map(x=>'cp7-'+x).concat(['empty','partial','stale','error'].map(x=>'cp7-state-'+x),['operations','denied'].map(x=>'cp7-access-'+x))
export const key=x=>`${x.variant}/${x.surface}/${x.width}`
export function expectedKeys(config){
  const keys=[]
  for(const width of config.widths){
    for(const s of config.before_surfaces)keys.push(`before/${s}/${width}`)
    for(const s of ['ready','review'])keys.push(`before/mandor-${s}/${width}`)
    for(const s of config.surfaces)keys.push(`after/${s.id}/${width}`)
    for(const s of dialogStates)keys.push(`after/mandor-${s}/${width}`)
    for(const s of cp7Surfaces)keys.push(`after/${s}/${width}`)
    if(width<=860)keys.push(`after/mobile-navigation/${width}`)
  }
  return keys.sort()
}
export function validateCoverage(variants,config){
  const actual=variants.map(key).sort(),expected=expectedKeys(config)
  assert.equal(new Set(actual).size,actual.length,'No duplicate view keys')
  assert.deepEqual(actual,expected,'Exact route/dialog/state/role/width identities required')
  return {expected:expected.length,actual:actual.length,dialog_views:variants.filter(x=>x.variant==='after'&&dialogStates.some(s=>x.surface==='mandor-'+s)).length}
}
