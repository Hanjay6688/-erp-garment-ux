import {defineConfig} from 'vitest/config'
import main from '../../vite.config.ts'
import {frozenAnalogPlugin} from './test_resolution.mjs'

export default defineConfig(async environment=>{
 if(environment.mode!=='test')throw Error('QUALIFICATION_TEST_CONFIG_ONLY')
 const original=typeof main==='function'?await main(environment):await main
 return {...original,plugins:[...(original.plugins??[]),frozenAnalogPlugin(process.cwd())]}
})
