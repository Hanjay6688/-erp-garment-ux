import {lazy,Suspense,useState} from 'react'
import './procurement-connected.css'
const Material=lazy(()=>import('./ConnectedMaterialCountPage'))
const Finished=lazy(()=>import('./ConnectedFgAdjustmentPage'))
export default function ConnectedStockAdjustmentPage(){
 const [kind,setKind]=useState<'MATERIAL'|'FG'>('MATERIAL')
 return <div className="cproc"><nav className="panel cproc-pagination" aria-label="Jenis persediaan"><button aria-pressed={kind==='MATERIAL'} onClick={()=>setKind('MATERIAL')}>Bahan dan aksesori</button><button aria-pressed={kind==='FG'} onClick={()=>setKind('FG')}>Barang jadi</button></nav><Suspense fallback={<p role="status">Memuat penyesuaian…</p>}>{kind==='FG'?<Finished/>:<Material/>}</Suspense></div>
}
