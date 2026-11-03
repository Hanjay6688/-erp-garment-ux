import {createRoot} from 'react-dom/client'
import Pocket from '../../../src/ConnectedPocketFabricPage'
import Import from '../../../src/ConnectedInitialImportPage'
import {calls,violations,form,state,revoke,refuseRead,probeMeta,getSnapshot} from './state'
import '../../../src/theme.css'
import '../../../src/styles.css'
import '../../../src/global-readability.css'
import './frame.css'
import {readProductionRecovery} from '../../../src/productionRecovery'
Object.assign(window,{__writerBUI:{calls,violations,revoke,form,state,refuseRead,probeMeta,identityStatus:()=>getSnapshot().identity.status,recovery:()=>readProductionRecovery('disposable:actor-1')}})
createRoot(document.getElementById('root')!).render(<><aside className="fixture-notice">FIXTURE UI TERISOLASI • komponen asli • Auth/RPC tiruan • tanpa database</aside><main className="fixture-workspace">{form==='pocket'?<Pocket/>:<Import/>}</main></>)
