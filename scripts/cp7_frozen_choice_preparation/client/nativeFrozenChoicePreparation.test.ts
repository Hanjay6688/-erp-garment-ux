import {expect,it,vi} from 'vitest'
import {analogContext} from '../../../tests/fixtures/nativeProductAnalog'
import {parseChoicePreparation,choicePreparationRPC,driveChoicePreparation} from './nativeFrozenChoicePreparation'
const context=()=>({...analogContext(),sourceMethod:'FROZEN_V2' as const})
import {prepReply} from './preparationFixture'
it('uses original source request and current access for request/get/step',async()=>{
 const rpc=vi.fn().mockResolvedValue({data:prepReply(),error:null}),c=context()
 for(const verb of['request','get','step']as const)await choicePreparationRPC({rpc},verb,c)
 expect(rpc.mock.calls.map(x=>x[1])).toEqual(Array(3).fill({p_source_request:c.requestId,p_access:c.accessEpoch}))
})
it.each(['source_request','run_id','stage','unit_count','choice_saved','production_go','state','worker_active','unit_attempts','created_at'])('rejects contradictory %s before showing success',key=>{
 const value={...prepReply('READY'),[key]:key==='choice_saved'||key==='production_go'?true:'invalid'}
 expect(()=>parseChoicePreparation(value,context())).toThrow()
})
it('rejects foreign source clock/hash and partial READY totals',()=>{
 const a=prepReply('READY');expect(()=>parseChoicePreparation({...a,units_done:0},context())).toThrow()
 for(const reference of[{...a.reference,source_hash:'f'.repeat(64)},{...a.reference,captured_at:'2026-10-24T00:00:00.123457Z'}])expect(()=>parseChoicePreparation({...a,reference},context())).toThrow()
 expect(()=>parseChoicePreparation({...a,failure_code:'CP7_FAILED'},context())).toThrow()
})
it('reports actual queued/running units and never sends SAVE',async()=>{
 const replies=[prepReply(),prepReply('RUNNING'),prepReply('READY')],rpc=vi.fn(async()=>({data:replies.shift(),error:null})),status=vi.fn(),pause=vi.fn().mockResolvedValue(undefined)
 expect((await driveChoicePreparation({rpc},context(),{current:()=>true,status,pause}))?.state).toBe('READY')
 expect(status.mock.calls.map(([x])=>[x.state,x.unitsDone])).toEqual([['QUEUED',0],['RUNNING',0],['READY',1]])
 expect(rpc.mock.calls).toHaveLength(3);expect(pause).toHaveBeenCalledOnce()
})
it('stops a stale response after closing or changing the source',async()=>{
 let finish!:(x:unknown)=>void;let current=true
 const rpc=vi.fn(()=>new Promise(resolve=>{finish=resolve})),status=vi.fn()
 const pending=driveChoicePreparation({rpc},context(),{current:()=>current,status});current=false;finish({data:prepReply('READY'),error:null})
 expect(await pending).toBeNull();expect(status).not.toHaveBeenCalled();expect(rpc).toHaveBeenCalledOnce()
})
it('lost request delivery retries the same durable source without manufacturing a command UUID',async()=>{
 const rpc=vi.fn().mockRejectedValueOnce(Error('lost reply')).mockResolvedValueOnce({data:prepReply('READY'),error:null})
 await expect(driveChoicePreparation({rpc},context(),{current:()=>true,status:()=>{}})).rejects.toThrow('lost reply')
 expect((await driveChoicePreparation({rpc},context(),{current:()=>true,status:()=>{}}))?.state).toBe('READY')
 expect(rpc.mock.calls[1]).toEqual(rpc.mock.calls[0])
})
it('no-progress timeout stops only monitoring without replacing or declaring the server job failed',async()=>{
 let clock=0
 const rpc=vi.fn().mockResolvedValue({data:prepReply('RUNNING'),error:null}),status=vi.fn()
 await expect(driveChoicePreparation({rpc},context(),{current:()=>true,status,now:()=>clock,pause:async()=>{clock+=120000}})).rejects.toThrow('proses server belum dinyatakan gagal')
 expect(rpc.mock.calls.map(([name])=>name)).toEqual(['erp_cp7_request_frozen_choice_preparation_v1','erp_cp7_get_frozen_choice_preparation_v1'])
 expect(status.mock.calls.every(([s])=>s.state==='RUNNING'&&s.unitsDone===0)).toBe(true)
})
it('failure is terminal for this work and does not run another step',async()=>{
 const rpc=vi.fn().mockResolvedValue({data:prepReply('FAILED'),error:null})
 expect((await driveChoicePreparation({rpc},context(),{current:()=>true,status:()=>{}}))?.state).toBe('FAILED');expect(rpc).toHaveBeenCalledOnce()
})
