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
// Explicit, closed read-refusal probe. It never changes the Auth provider.
const probeReaders={workspace:'erp_get_pocket_fabric_workspace_v1','period-page':'erp_get_pocket_periods_v1','period-preview':'erp_preview_pocket_fabric_period_v1'} as const
export const refusalProbe=params.get('refusal_probe')==='1'
export const probeCase=params.get('probe_case')??'read'
export const probeTarget=params.get('probe_target')??'workspace'
export const probeStatus=Number(params.get('probe_status')??0)
if(refusalProbe&&(form!=='pocket'||state!=='ready'||!['read','recovery'].includes(probeCase)||!Object.hasOwn(probeReaders,probeTarget)||![401,403].includes(probeStatus)))throw Error('UNDECLARED_REFUSAL_PROBE')
let readRefused=refusalProbe&&params.get('start_refused')==='1'
export function refuseRead(){if(!refusalProbe)throw Error('REFUSAL_PROBE_NOT_ENABLED');readRefused=true}
export const isRefusedRead=(name:string)=>readRefused&&name===probeReaders[probeTarget as keyof typeof probeReaders]
export const probeMeta=()=>({enabled:refusalProbe,kind:probeCase,target:probeTarget,status:probeStatus,armed:readRefused})
