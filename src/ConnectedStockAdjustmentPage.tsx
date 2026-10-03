import {lazy,Suspense,useEffect,useState} from 'react'
import './procurement-connected.css'
import {useTransactionSource} from './TransactionSourceNavigation'
const Material=lazy(()=>import('./ConnectedMaterialCountPage'))
const Finished=lazy(()=>import('./ConnectedFgAdjustmentPage'))
export default function ConnectedStockAdjustmentPage(){
 const fg=useTransactionSource('FG_ADJUSTMENT'),material=useTransactionSource('MATERIAL_COUNT')
 const [kind,setKind]=useState<'MATERIAL'|'FG'>(fg?'FG':'MATERIAL')
 useEffect(()=>{if(fg)setKind('FG');else if(material)setKind('MATERIAL')},[fg?.key,material?.key])
 return <div className="cproc"><nav className="panel cproc-pagination" aria-label="Jenis persediaan"><button aria-pressed={kind==='MATERIAL'} onClick={()=>setKind('MATERIAL')}>Bahan dan aksesori</button><button aria-pressed={kind==='FG'} onClick={()=>setKind('FG')}>Barang jadi</button></nav><Suspense fallback={<p role="status">Memuat penyesuaian…</p>}>{kind==='FG'?<Finished/>:<Material/>}</Suspense></div>
}
