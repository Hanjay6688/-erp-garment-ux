import {useMemo,type ComponentProps} from 'react'
import {useAuth} from '../../../src/auth/AuthProvider'
import {getUatSupabaseClient} from '../../../src/lib/supabase'
import NativeFrozenAnalogPanel from '../../cp7_frozen_choice_ui/client/NativeFrozenAnalogPanel'
import NativeFrozenChoicePanel from '../../cp7_frozen_choice_ui/client/NativeFrozenChoicePanel'
import {ChoicePreparationGate} from './PreparedFrozenChoicePanel'

type Props=ComponentProps<typeof NativeFrozenAnalogPanel>
const permissions=['master.product.view','production.wip.view','warehouse.stock.view','sales.invoice.view']
// Explicit caller for the optional SQL delta: prepare BEFORE reading candidates.
// The same persisted input then serves page reads and the later checked SAVE.
export default function PreparedFrozenAnalogPanel(props:Props){
 const{runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED'||identity.profile.authUserId!==props.context.actor||props.context.sourceMethod!=='FROZEN_V2'||!permissions.every(p=>identity.permissions.includes(p)))return null
 return <Workspace {...props} key={JSON.stringify([runtime.projectRef,identity.profile.rowVersion,identity.profile.roleRowVersion,identity.permissions,props.context])}/>
}
function Workspace(props:Props){
 const{runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')throw Error('Sesi produk pembanding belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),scope='product-analog:'+runtime.projectRef
 return <section className="native-production-result frozen-choice-panel" aria-label="Persiapan produk pembanding">
  <header><h4>Produk pembanding untuk {props.label}</h4><button onClick={props.onClose}>Tutup persiapan pembanding</button></header>
  <ChoicePreparationGate client={client} context={props.context} scope={scope} enabled onAccessLost={props.onAccessLost}>
   {ready=>ready?<NativeFrozenAnalogPanel {...props}/>:<NativeFrozenChoicePanel client={client} context={props.context} candidates={null} scope={scope} canManage={identity.permissions.includes('master.product.manage')} onAccessLost={props.onAccessLost}/>}
  </ChoicePreparationGate>
 </section>
}
