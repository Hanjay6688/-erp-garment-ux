import NativeFrozenQuantityPanel from '../../cp7_frozen_quantity_ui/client/NativeFrozenQuantityPanel'
import NativePlanDraftPanel from '../../../src/NativePlanDraftPanel'
import './frozen-cutting.css'
import type {NativeDemandQuery} from '../../../src/nativeDemandHistory'

type Props={query:NativeDemandQuery;onSourceReadStart:()=>void;onSourceReadEnd:()=>void;onClose:()=>void}
// Explicit disposable preparation. No default screen imports this component.
// The one existing form keeps its exact checked SAVE and recovery route.
export default function NativeFrozenCuttingPanel(props:Props){
 return <NativeFrozenQuantityPanel {...props} renderCuttingPlan={(context,onClose,onAccessLost)=><div className="frozen-cutting-plan"><NativePlanDraftPanel context={context} requireCurrentSave onSourceReadStart={props.onSourceReadStart} onSourceReadEnd={props.onSourceReadEnd} onClose={onClose} onAccessLost={onAccessLost}/></div>}/>
}
