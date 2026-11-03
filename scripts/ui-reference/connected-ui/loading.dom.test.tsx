// @vitest-environment jsdom
import {act} from 'react'
import {createRoot} from 'react-dom/client'
import {it,expect,vi} from 'vitest'
import Pocket from '../../../src/ConnectedPocketFabricPage'
import {recoveryIdentity} from '../../../tests/fixtures/productionRecovery'
vi.mock('../../../src/auth/AuthProvider',()=>({useAuth:()=>({...recoveryIdentity,identity:{...recoveryIdentity.identity,permissions:[...recoveryIdentity.identity.permissions,'warehouse.stock.adjust']}})}))
vi.mock('../../../src/lib/supabase',()=>({getUatSupabaseClient:()=>({rpc:()=>new Promise(()=>{})})}))
it('does not label an unresolved pocket read as zero allocations or known empty stock',async()=>{
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});localStorage.clear();const host=document.createElement('div');document.body.append(host);const root=createRoot(host)
 try{await act(async()=>root.render(<Pocket/>));expect(host.textContent).not.toContain('0 dari 0 alokasi');expect(host.textContent).not.toContain('Belum ada stok kain kantong');expect(host.querySelector('[role="status"]')?.textContent).toContain('Menyiapkan data')}
 finally{await act(async()=>root.unmount());host.remove();localStorage.clear()}
})
