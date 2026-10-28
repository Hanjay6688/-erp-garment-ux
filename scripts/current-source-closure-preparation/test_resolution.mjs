// Qualification-only dependency resolution. Default application imports stay unchanged.
import {dirname,relative,resolve} from 'node:path'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'

export const frozenAnalogImporters=new Set([
 'scripts/cp7_frozen_analysis_readers_v2/client/nativeFrozenAnalog.ts',
 'scripts/cp7_frozen_analysis_readers_v2/client/nativeFrozenAnalog.test.ts',
 'scripts/cp7_frozen_choice_ui/client/fixtures.ts',
 'scripts/cp7_frozen_choice_ui/client/NativeFrozenAnalogPanel.tsx',
 'scripts/cp7_frozen_choice_ui/client/NativeFrozenChoicePanel.tsx',
 'scripts/cp7_frozen_quantity_ui/client/nativeFrozenQuantity.ts',
 'scripts/cp7_frozen_quantity_ui/client/NativeFrozenQuantityPanel.tsx',
 'scripts/cp7_frozen_choice_preparation/client/nativeFrozenChoicePreparation.ts',
 'scripts/cp7_frozen_analysis_choice_v2/client/nativeFrozenChoice.ts',
])
export const provider='scripts/cp7_current_progress_finance_ui/vendor/src/nativeProductAnalog.ts'
export const providerSha256='149277f173bbfcdc91a68157d973eb1ceffd08d66c0b44a1bdfa074f4d9befd9'

export function frozenAnalogResolution(root,source,importer){
 if(!importer||!source.startsWith('.'))return null
 const original=importer.split('?',1)[0]
 if(!frozenAnalogImporters.has(relative(root,original).replaceAll('\\','/')))return null
 const target=resolve(dirname(original),source)
 if(target!==resolve(root,'src/nativeProductAnalog')&&target!==resolve(root,'src/nativeProductAnalog.ts'))return null
 return resolve(root,provider)
}

export function frozenAnalogPlugin(root){
 const digest=createHash('sha256').update(readFileSync(resolve(root,provider))).digest('hex')
 if(digest!==providerSha256)throw Error('FROZEN_TEST_PARSER_SOURCE_CHANGED')
 return {name:'exact-frozen-analog-test-dependency',enforce:'pre',
  resolveId(source,importer){return frozenAnalogResolution(root,source,importer)}}
}
