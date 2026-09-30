// @vitest-environment node
import { afterEach, expect, it, vi } from 'vitest'
import { readComputedYieldDemo } from './yieldHttpPort'
import { readYieldFixture, yieldFixtureInput } from './cuttingYieldFixtures'

const context={runId:'test-run',actorScope:'test-scope',accessEpoch:'test-epoch'}
afterEach(()=>vi.unstubAllGlobals())
it('sends only the input and context to the same-origin demo endpoint',async()=>{
 const input=yieldFixtureInput('small','NORMAL'), result=await readYieldFixture(input,context,'small','NORMAL')
 const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>result});vi.stubGlobal('fetch',fetch)
 expect(await readComputedYieldDemo(input,context,'small','NORMAL')).toEqual(result)
 const [url,options]=fetch.mock.calls[0];expect(url).toBe('/__cp7_demo_yield')
 expect(Object.keys(JSON.parse(options.body)).sort()).toEqual(['context','example','input','inputKey'])
 expect(options.cache).toBe('no-store')
})
it('does not fall back to supplied display ranges on backend failure',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:503}))
 await expect(readComputedYieldDemo(yieldFixtureInput('small','NORMAL'),context,'small','NORMAL')).rejects.toThrow('unavailable')
})
it('rejects a response for a different access epoch',async()=>{
 const input=yieldFixtureInput('small','NORMAL'), result=await readYieldFixture(input,context,'small','NORMAL')
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({...result,context:{...context,accessEpoch:'old'}})}))
 await expect(readComputedYieldDemo(input,context,'small','NORMAL')).rejects.toThrow('Konteks')
})
it('rejects malformed status instead of showing backend text as a result',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({status:'GUESS',reason:'normal'})}))
 await expect(readComputedYieldDemo(yieldFixtureInput('small','NORMAL'),context,'small','NORMAL')).rejects.toThrow('tidak valid')
})
