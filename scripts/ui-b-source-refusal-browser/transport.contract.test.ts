// @vitest-environment jsdom
import {afterEach,it,expect,vi} from 'vitest'
const base='form=pocket&state=ready&refusal_probe=1&probe_case=read&probe_target=workspace&probe_status='
async function fixture(query:string){vi.resetModules();history.replaceState({},'','/?'+query);const state=await import('../ui-reference/connected-ui/state');const {getUatSupabaseClient}=await import('../ui-reference/connected-ui/client');return {state,client:getUatSupabaseClient()}}
afterEach(()=>{history.replaceState({},'','/');vi.restoreAllMocks()})
it('leaves the normal fixture closed to writes and refusal controls',async()=>{
 const {state,client}=await fixture('form=pocket&state=ready');expect(()=>state.refuseRead()).toThrow('REFUSAL_PROBE_NOT_ENABLED')
 await expect(client.rpc('erp_save_pocket_fabric_action_v1',{p_action:'POST'})).rejects.toThrow('UNEXPECTED_WRITE');expect(state.violations).toHaveLength(1)
})
it.each([401,403])('models source %i while retaining the identical authorized provider',async status=>{
 const {state,client}=await fixture(base+status),before=structuredClone(state.getSnapshot())
 expect((await client.rpc('erp_get_pocket_fabric_workspace_v1')).error).toBeNull();state.refuseRead()
 expect((await client.rpc('erp_get_pocket_fabric_workspace_v1')).error).toMatchObject({status})
 expect(state.getSnapshot()).toEqual(before);expect(state.getSnapshot().identity.status).toBe('AUTHORIZED');expect(state.violations).toEqual([])
})
it('keeps a lost save response distinct from a persisted source refusal after reload',async()=>{
 const {client,state}=await fixture(base.replace('probe_case=read','probe_case=recovery')+'403&start_refused=1')
 expect((await client.rpc('erp_get_pocket_fabric_workspace_v1')).error).toMatchObject({status:403})
 expect((await client.rpc('erp_save_pocket_fabric_action_v1',{p_action:'POST'})).error).toMatchObject({status:503})
 expect(state.getSnapshot().identity.status).toBe('AUTHORIZED');expect(state.violations).toEqual([])
})
it('refuses undeclared probe identities before admitting a client',async()=>{
 await expect(fixture(base+'500')).rejects.toThrow('UNDECLARED_REFUSAL_PROBE')
 const {client,state}=await fixture(base+'401');await expect(client.rpc('arbitrary_product_write')).rejects.toThrow('UNDECLARED_RPC');expect(state.violations).toHaveLength(1)
})
