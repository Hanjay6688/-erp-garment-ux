import {test} from 'node:test'
import assert from 'node:assert/strict'
import {resolve} from 'node:path'
import {frozenAnalogImporters,frozenAnalogResolution,frozenAnalogPlugin,provider} from './test_resolution.mjs'

const root=process.cwd()
test('only explicit frozen consumers use the exact parser used by the qualified UI host',()=>{
 const plugin=frozenAnalogPlugin(root)
 for(const importer of frozenAnalogImporters){
  assert.equal(plugin.resolveId('../../../src/nativeProductAnalog',resolve(root,importer)),resolve(root,provider))
  assert.equal(plugin.resolveId('../../../src/nativeProductAnalog.ts',resolve(root,importer)+'?import'),resolve(root,provider))
 }
})

test('default application, its tests, old vendor graphs and unrelated dependencies keep their own resolution',()=>{
 for(const importer of ['src/nativeProductAnalog.test.ts','src/NativeProductAnalogPanel.tsx',
  'scripts/cp7_current_frozen_finance_ui/vendor/scripts/cp7_frozen_analysis_readers_v2/client/nativeFrozenAnalog.ts',
  'scripts/cp7_current_progress_finance_ui/vendor/scripts/cp7_frozen_analysis_readers_v2/client/nativeFrozenAnalog.ts']){
  assert.equal(frozenAnalogResolution(root,'./nativeProductAnalog',resolve(root,importer)),null)
  assert.equal(frozenAnalogResolution(root,'../../../src/nativeProductAnalog',resolve(root,importer)),null)
 }
 const importer=resolve(root,[...frozenAnalogImporters][0])
 assert.equal(frozenAnalogResolution(root,'../../../src/nativeTargetDemand',importer),null)
 assert.equal(frozenAnalogResolution(root,'react',importer),null)
 assert.equal(frozenAnalogResolution(root,'../../../src/nativeProductAnalog',undefined),null)
})
