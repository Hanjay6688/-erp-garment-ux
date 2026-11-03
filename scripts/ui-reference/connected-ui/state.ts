import { recoveryIdentity } from '../../../tests/fixtures/productionRecovery'
import { states,type State } from './data'
const params=new URLSearchParams(location.search)
export const state=(params.get('state')??'ready') as State
export const form=params.get('form')??'pocket'
if(!states.includes(state)||!['pocket','import'].includes(form))throw Error('UNDECLARED_UI_FIXTURE_STATE')
const initial=structuredClone(recoveryIdentity)
initial.identity.permissions.push('warehouse.stock.adjust','finance.hpp.manage')
let snapshot={...initial,identity:{...initial.identity,profile:{...initial.identity.profile,role:String(initial.identity.profile.role),authUserId:'11111111-1111-4111-8111-111111111111',fullName:'Pemilik fixture UI',roleId:'22222222-2222-4222-8222-222222222222',roleName:'Owner fixture',rowVersion:1,roleRowVersion:1}}}
if(state==='denied')snapshot={...snapshot,identity:{...snapshot.identity,profile:{...snapshot.identity.profile,role:'VIEWER'},permissions:[]}}
const listeners=new Set<()=>void>()
export const subscribe=(listener:()=>void)=>{listeners.add(listener);return ()=>{listeners.delete(listener)}}
export const getSnapshot=()=>snapshot
export function revoke(){snapshot={...snapshot,identity:{...snapshot.identity,permissions:[],profile:{...snapshot.identity.profile,role:'VIEWER',rowVersion:2}}};for(const listener of listeners)listener()}
export const calls:Array<{name:string;args:Record<string,unknown>}> = []
export const violations:string[]=[]
