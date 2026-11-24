import { Icon } from '../components/AppIcon'
import CuttingPatternPicker, { hasCanonicalPattern } from '../CuttingPatternPicker'
import type { CuttingPatternChoice } from '../CuttingPatternPicker'
import { Field, MultiCheckFilter } from './controls'
import {ReasonDialog} from './planner/ReasonDialog'
import { AdviceBox, pickupPath } from './planner/ProductionAdvice'
import { articles, articleChoice, cutArticle, planningPattern, rangeLabel, cutRolls, lotLabel, lotPattern, modelSeries, patternFor, plan, productFor, recordCut, rolls, seriesLabel, suggestedCut, yardsLeft, type Plan } from './planner/model'
import { usePlannerSession, changeSession } from './planner/session'
import {
  cuttingSizes,
  drawingLabel,
  initialCuttingSizeSlots,
} from './cuttingAllocation'
import type { CuttingSizeSlot, FabricRoll } from './cuttingAllocation'
import { cleanDecimalInput, dozenPieces, formatQuantity, parseDecimal } from './format'
import type { QtyTuple } from './productionModel'
import { ChevronDown } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type {
  CSSProperties,
  ClipboardEvent as ReactClipboardEvent,
  KeyboardEvent as ReactKeyboardEvent,
  PointerEvent as ReactPointerEvent,
} from 'react'

const blankSlots = (sizes: string[]) => sizes.map(size=>({key:crypto.randomUUID(),size}))

const fabricRollSuppliers=Array.from(new Set(rolls.map(roll=>roll.supplier)))
const fabricRollMaterials=rolls.map(roll=>roll.material)
type CuttingDraft = { sku:string; brand:string; model:string; date:string; notes?:string; eta?:string; selectedPattern:CuttingPatternChoice|null; ids:string[]; yards:Record<string,string>; slots:CuttingSizeSlot[]; amounts:Record<string,number[]> }
const draftKey='atelier.cutting-draft.nov24.1'
function readDraft(): CuttingDraft|null {
  try {return JSON.parse(sessionStorage.getItem(draftKey)??'null')} catch {return null}
}
export function CuttingRollPage() {
  const session=usePlannerSession()
  const fabricRollCatalog:FabricRoll[]=rolls.map((roll,index)=>({...roll,sequence:index+1,yards:yardsLeft(roll.id,session),receivedAt:'23 Nov 2026',allocation:[0,0,0,0,0,0]}))
  const [draft]=useState(readDraft)
  const [savedDraft,setSavedDraft]=useState(Boolean(draft)),[deleteDraft,setDeleteDraft]=useState(false)
  function restoreDraft(){const d=readDraft();if(!d){setSavedDraft(false);return}
    setSku(d.sku);setBrand(d.brand);setModel(d.model);setDate(d.date);setNotes(d.notes??'');setEta(d.eta??'');setSelectedPattern(d.selectedPattern);setSelectedRollIds(d.ids);setSizeSlots(d.slots);setRollYardUsage(d.yards);setAllocations(d.amounts);setSavedId('');setSizeNotice('');requestId.current=crypto.randomUUID();setNotice('Draft dibuka untuk diedit.')
  }
  const [sku,setSku]=useState(draft?.sku??'')
  const [brand,setBrand]=useState(draft?.brand??'')
  const hasSampleRoll=!draft&&yardsLeft('ORI-021',session)>=27
  const [model,setModel]=useState(draft?.model??(hasSampleRoll?'Kulot Jumbo':''))
  const [date,setDate]=useState(draft?.date??'2026-11-24')
  const [notes,setNotes]=useState(draft?.notes??'')
  const [eta,setEta]=useState(draft?.eta??'')
  const linked=cutArticle(sku)
  const series=linked&&linked.model===model ? {name:linked.sizes.length===1?'khusus':modelSeries[model].name,sizes:linked.sizes} : modelSeries[model]
  const cuttingSizeOptions=series?.sizes??[]
  const [notice,setNotice]=useState('')
  const [savedId,setSavedId]=useState('')
  const requestId=useRef(crypto.randomUUID())
  const formRef=useRef<HTMLElement>(null)
  const [query,setQuery]=useState('')
  const [selectedPattern,setSelectedPattern]=useState<CuttingPatternChoice|null>(draft?.selectedPattern??null)
  const [sizeNotice,setSizeNotice]=useState('')
  const [selectedSuppliers,setSelectedSuppliers]=useState([...fabricRollSuppliers])
  const [selectedMaterials,setSelectedMaterials]=useState([...fabricRollMaterials])
  const [selectedRollIds,setSelectedRollIds]=useState(()=>draft?.ids??(hasSampleRoll?['ORI-021']:[]))
  const [rollYardUsage,setRollYardUsage]=useState<Record<string,string>>(()=>draft?.yards??Object.fromEntries(fabricRollCatalog.map((roll)=>[roll.id,String(hasSampleRoll&&roll.id==='ORI-021'?27:roll.yards).replace('.',',')])))
  const [sizeSlots,setSizeSlots]=useState<CuttingSizeSlot[]>(()=>draft?.slots??(hasSampleRoll?blankSlots(modelSeries['Kulot Jumbo'].sizes):[]))
  const nextSlotKeyRef=useRef(initialCuttingSizeSlots.length+1)
  const [allocations,setAllocations]=useState<Record<string,number[]>>(()=>draft?.amounts??(hasSampleRoll?{'ORI-021':[4,8,6]}:{}))
  const [fillRange,setFillRange]=useState<{source:number;target:number}|null>(null)
  function useAdvice(row:Plan, material?:string, scroll=true) {
    const p=row.product, {route,roll,qty}=suggestedCut(row,session,material)
    if(!qty||!row.reference)return
    setSku(p.sku);setBrand(p.brand);setModel(patternFor(route.pattern).name);setDate('2026-11-24')
    setSelectedPattern(patternFor(row.reference));setSelectedRollIds([roll.id])
    setSelectedSuppliers([...fabricRollSuppliers]);setSelectedMaterials([...fabricRollMaterials]);setQuery('')
    const sizes=modelSeries[patternFor(route.pattern).name].sizes
    setSizeSlots(blankSlots(sizes));setAllocations({[roll.id]:sizes.map(size=>size===p.size?qty:0)})
    setEta(p.due);setNotes('');setSizeNotice('')
    setRollYardUsage({[roll.id]:String(qty*roll.yardPerPiece)})
    requestId.current=crypto.randomUUID()
    setSavedId('');setNotice('Form terisi untuk '+p.brand+' '+p.sku+'. Periksa jumlah dan yard sebelum menyimpan.')
    if(scroll) requestAnimationFrame(()=>formRef.current?.scrollIntoView({block:'start'}))
  }
  useEffect(()=>{
    const p=productFor(new URLSearchParams(window.location.search).get('sku')??'')
    if(p){
      const row=plan(p,session)
      if(row.short>0&&row.reference&&!row.review.length)useAdvice(row,new URLSearchParams(window.location.search).get('bahan')??undefined,false)
      window.history.replaceState(window.history.state,'',window.location.pathname)
    }
  },[])
  const fillRangeRef=useRef<{source:number;target:number}|null>(null)
  const fillDraggedRef=useRef(false)
  const [columnFillRange,setColumnFillRange]=useState<{source:number;target:number}|null>(null)
  const columnFillRangeRef=useRef<{source:number;target:number}|null>(null)
  const columnFillDraggedRef=useRef(false)
  const selectedIdSet=useMemo(()=>new Set(selectedRollIds),[selectedRollIds])
  const visibleRolls=useMemo(()=>fabricRollCatalog.filter((roll)=>{
    const matchesQuery=`${roll.id} roll ${roll.sequence} ${roll.supplier} ${roll.material} ${roll.yards}`.toLowerCase().includes(query.toLowerCase())
    return matchesQuery&&selectedSuppliers.includes(roll.supplier)&&selectedMaterials.includes(roll.material)
  }),[query,selectedSuppliers,selectedMaterials,session.cuts.length])
  const selectedRolls=fabricRollCatalog.filter((roll)=>selectedIdSet.has(roll.id))
  const rollUsageRows=selectedRolls.map((roll)=>{
    const input=rollYardUsage[roll.id]??''
    const used=parseDecimal(input)
    const valid=input.trim()!==''&&used>0&&used<=roll.yards
    return {roll,input,used,balance:Math.max(0,roll.yards-used),valid,partial:valid&&used<roll.yards}
  })
  const totalSourceYards=selectedRolls.reduce((sum,roll)=>sum+roll.yards,0)
  const totalUsedYards=rollUsageRows.reduce((sum,row)=>sum+(row.valid?row.used:0),0)
  const totalBalanceYards=rollUsageRows.reduce((sum,row)=>sum+(row.valid?row.balance:row.roll.yards),0)
  const yardUsageValid=rollUsageRows.length>0&&rollUsageRows.every((row)=>row.valid)
  const partialRollCount=rollUsageRows.filter((row)=>row.partial).length
  const displayedSizeSlots=useMemo(()=>sizeSlots.map((slot,slotIndex)=>{
    const sameSizeCount=sizeSlots.filter((candidate)=>candidate.size===slot.size).length
    const drawingNo=sizeSlots.slice(0,slotIndex+1).filter((candidate)=>candidate.size===slot.size).length
    return {...slot,drawingNo,image:sameSizeCount>1?drawingLabel(drawingNo):''}
  }),[sizeSlots])
  const selectedCuttingSizes=cuttingSizeOptions.filter((size)=>sizeSlots.some((slot)=>slot.size===size))
  const slotTotals=sizeSlots.map((_,slotIndex)=>selectedRolls.reduce((sum,roll)=>sum+(allocations[roll.id]?.[slotIndex]??0),0))
  const sizeTotalByName=Object.fromEntries(selectedCuttingSizes.map((size)=>[size,sizeSlots.reduce((sum,slot,slotIndex)=>sum+(slot.size===size?slotTotals[slotIndex]:0),0)])) as Record<string,number>
  const totalPieces=slotTotals.reduce((sum,qty)=>sum+qty,0)
  function selectModel(name:string,sizes=modelSeries[name]?.sizes??[],fromArticle=false) {
    if(!fromArticle&&linked&&name!==linked.model){setSizeNotice('Kosongkan SKU rencana dulu untuk memilih model lain.');return false}
    if(name===model&&sizes.length===new Set(sizeSlots.map(s=>s.size)).size&&sizeSlots.every(s=>sizes.includes(s.size)))return true
    if(sizeSlots.some((slot,i)=>!sizes.includes(slot.size)&&Object.values(allocations).some(values=>values[i]>0))){
      setSizeNotice('Kosongkan hasil ukuran di luar seri baru sebelum mengganti model.');return false
    }
    const newSlots=sizes.flatMap(size=>{
      const same=sizeSlots.filter(slot=>slot.size===size)
      return same.length ? same : blankSlots([size])
    })
    setAllocations(current=>Object.fromEntries(Object.entries(current).map(([id,values])=>[id,newSlots.map(slot=>values[sizeSlots.indexOf(slot)]??0)])))
    setModel(name);setSizeSlots(newSlots);setSizeNotice('');return true
  }
  function selectSku(value:string) {
    if(!value){setSku('');setSizeNotice('');return}
    const article=cutArticle(value)
    if(!article)return
    if(!selectModel(article.model,article.sizes,true))return
    setSku(value)
    const ref=planningPattern(article,session)
    if(!selectedPattern&&ref)setSelectedPattern(patternFor(ref))
  }
  function storeCut() {
    if(savedId)return
    try {
      if(!selectedPattern||!series)throw Error('Pilih model, seri dan pola.')
      const next=changeSession(current=>recordCut(current,{
        requestId:requestId.current,sku:linked?.sku,articleKey:linked?.key,brand,model,series,pattern:selectedPattern,date,notes,eta,
        location:'Gudang Kain',slots:sizeSlots.map(slot=>slot.size),
        rolls:rollUsageRows.map(({roll,used})=>({id:roll.id,yards:used,quantities:sizeSlots.map((_,i)=>allocations[roll.id]?.[i]??0)})),
      }))
      const id=next.cuts.find(l=>l.requestId===requestId.current)!.id
      sessionStorage.removeItem(draftKey);setSavedDraft(false)
      setSavedId(id);setNotice(id+' tersimpan. '+totalPieces+' pcs sekarang menunggu mandor. Saran potong sudah dihitung ulang.')
    } catch(error){setNotice((error as Error).message)}
  }
  function storeDraft(){
    if(sku && brand && linked?.brand!==brand){setNotice('Periksa kecocokan merek dan SKU rencana.');return}
    const data:CuttingDraft={sku,brand,model,date,eta,notes,selectedPattern,ids:selectedRollIds,yards:rollYardUsage,slots:sizeSlots,amounts:allocations}
    sessionStorage.setItem(draftKey,JSON.stringify(data));setSavedDraft(true);setNotice('Draft tersimpan di tab ini. Jumlah WIP tetap sama sampai hasil potong disimpan.')
  }
  const slotGridStyle={'--cutting-slot-count':displayedSizeSlots.length} as CSSProperties
  const sizeSummaryStyle={'--cutting-size-columns':Math.min(3,Math.max(1,selectedCuttingSizes.length))} as CSSProperties
  const allVisibleSelected=visibleRolls.length>0&&visibleRolls.every((roll)=>selectedIdSet.has(roll.id))
  const toggleRoll=(id:string)=>setSelectedRollIds((current)=>current.includes(id)?current.filter((rollId)=>rollId!==id):fabricRollCatalog.filter((roll)=>current.includes(roll.id)||roll.id===id).map((roll)=>roll.id))
  const toggleVisible=()=>setSelectedRollIds((current)=>{
    const next=new Set(current)
    visibleRolls.forEach((roll)=>allVisibleSelected?next.delete(roll.id):next.add(roll.id))
    return fabricRollCatalog.filter((roll)=>next.has(roll.id)).map((roll)=>roll.id)
  })
  const updateRollYardUsage=(rollId:string,value:string)=>setRollYardUsage((current)=>({...current,[rollId]:cleanDecimalInput(value)}))
  const useFullRoll=(roll:FabricRoll)=>setRollYardUsage((current)=>({...current,[roll.id]:String(hasSampleRoll&&roll.id==='ORI-021'?27:roll.yards).replace('.',',')}))
  const activateSize=(size:string)=>{
    if(sizeSlots.some((slot)=>slot.size===size))return
    const targetOrder=cuttingSizeOptions.indexOf(size)
    const firstLaterSlot=sizeSlots.findIndex((slot)=>cuttingSizeOptions.indexOf(slot.size)>targetOrder)
    const insertIndex=firstLaterSlot<0?sizeSlots.length:firstLaterSlot
    const nextSlot={key:`${size}-${nextSlotKeyRef.current++}`,size}
    setSizeSlots((current)=>[...current.slice(0,insertIndex),nextSlot,...current.slice(insertIndex)])
    setAllocations((current)=>Object.fromEntries(Object.entries(current).map(([rollId,row])=>[rollId,[...row.slice(0,insertIndex),0,...row.slice(insertIndex)]])))
    setSizeNotice(`Size ${size} aktif. Satu kolom multiplier baru sudah disiapkan.`)
    setColumnFillRange(null)
    columnFillRangeRef.current=null
  }
  const deactivateSize=(size:string)=>{
    if(selectedCuttingSizes.length<=1){setSizeNotice('Minimal satu ukuran harus tetap dipilih.');return}
    const matchingIndexes=sizeSlots.map((slot,index)=>slot.size===size?index:-1).filter((index)=>index>=0)
    const hasQuantity=selectedRolls.some((roll)=>matchingIndexes.some((index)=>(allocations[roll.id]?.[index]??0)>0))
    if(hasQuantity){setSizeNotice(`Size ${size} belum bisa dilepas. Kosongkan hasil potong pada kolom size ini dulu.`);return}
    const removed=new Set(matchingIndexes)
    setSizeSlots((current)=>current.filter((_,index)=>!removed.has(index)))
    setAllocations((current)=>Object.fromEntries(Object.entries(current).map(([rollId,row])=>[rollId,row.filter((_,index)=>!removed.has(index))])))
    setSizeNotice(`Size ${size} dilepas karena seluruh hasil potongnya masih kosong.`)
    setColumnFillRange(null)
    columnFillRangeRef.current=null
  }
  const toggleCuttingSize=(size:string)=>sizeSlots.some((slot)=>slot.size===size)?deactivateSize(size):activateSize(size)
  const addSizeSlot=(size:string)=>{
    let insertIndex=sizeSlots.length
    sizeSlots.forEach((slot,index)=>{if(slot.size===size)insertIndex=index+1})
    const nextSlot={key:`${size}-${nextSlotKeyRef.current++}`,size}
    setSizeSlots((current)=>[...current.slice(0,insertIndex),nextSlot,...current.slice(insertIndex)])
    setAllocations((current)=>Object.fromEntries(Object.entries(current).map(([rollId,row])=>[rollId,[...row.slice(0,insertIndex),0,...row.slice(insertIndex)]])))
    setColumnFillRange(null)
    columnFillRangeRef.current=null
  }
  const removeSizeSlot=(size:string)=>{
    const matchingIndexes=sizeSlots.map((slot,index)=>slot.size===size?index:-1).filter((index)=>index>=0)
    if(matchingIndexes.length<=1)return
    const removeIndex=matchingIndexes[matchingIndexes.length-1]
    const mergeIndex=matchingIndexes[matchingIndexes.length-2]
    setSizeSlots((current)=>current.filter((_,index)=>index!==removeIndex))
    setAllocations((current)=>Object.fromEntries(Object.entries(current).map(([rollId,row])=>{
      const next=[...row]
      next[mergeIndex]=(next[mergeIndex]??0)+(next[removeIndex]??0)
      next.splice(removeIndex,1)
      return [rollId,next]
    })))
    setColumnFillRange(null)
    columnFillRangeRef.current=null
  }
  const updateAllocation=(roll:FabricRoll,slotIndex:number,value:string)=>setAllocations((current)=>{
    const next=[...(current[roll.id]??sizeSlots.map((_,index)=>roll.allocation[index]??0))]
    const normalized=value.replace(/[^0-9]/g,'').replace(/^0+(?=\d)/,'')
    next[slotIndex]=normalized===''?0:Math.max(0,Math.round(Number(normalized)||0))
    return {...current,[roll.id]:next}
  })
  const focusAllocationCell=(rollIndex:number,slotIndex:number)=>{
    const input=document.querySelector<HTMLInputElement>(`[data-cutting-row="${rollIndex}"][data-cutting-slot="${slotIndex}"]`)
    if(!input)return
    input.focus()
    input.select()
  }
  const handleAllocationKey=(event:ReactKeyboardEvent<HTMLInputElement>,rollIndex:number,slotIndex:number)=>{
    if(event.ctrlKey||event.metaKey||event.altKey)return
    let nextRoll=rollIndex
    let nextSlot=slotIndex
    if(event.key==='Enter')nextRoll+=event.shiftKey?-1:1
    else if(event.key==='ArrowDown')nextRoll+=1
    else if(event.key==='ArrowUp')nextRoll-=1
    else if(event.key==='ArrowRight')nextSlot+=1
    else if(event.key==='ArrowLeft')nextSlot-=1
    else return
    if(nextRoll<0||nextRoll>=selectedRolls.length||nextSlot<0||nextSlot>=sizeSlots.length)return
    event.preventDefault()
    focusAllocationCell(nextRoll,nextSlot)
  }
  const pasteAllocationGrid=(event:ReactClipboardEvent<HTMLInputElement>,startRoll:number,startSlot:number)=>{
    const clipboard=event.clipboardData.getData('text').replace(/\r/g,'').replace(/\n+$/,'')
    if(!clipboard)return
    event.preventDefault()
    const pastedRows=clipboard.split('\n').map((line)=>line.split('\t'))
    setAllocations((current)=>{
      const next={...current}
      pastedRows.forEach((cells,rowOffset)=>{
        const roll=selectedRolls[startRoll+rowOffset]
        if(!roll)return
        const row=[...(next[roll.id]??sizeSlots.map((_,index)=>roll.allocation[index]??0))]
        cells.forEach((cell,columnOffset)=>{
          const slotIndex=startSlot+columnOffset
          if(slotIndex>=sizeSlots.length)return
          const normalized=cell.trim().replace(/[^0-9]/g,'').replace(/^0+(?=\d)/,'')
          row[slotIndex]=normalized===''?0:Math.max(0,Math.round(Number(normalized)||0))
        })
        next[roll.id]=row
      })
      return next
    })
  }
  const fillRowsFromSource=(sourceIndex:number,targetIndex:number)=>{
    if(targetIndex===sourceIndex)return
    setAllocations((current)=>{
      const sourceRoll=selectedRolls[sourceIndex]
      if(!sourceRoll)return current
      const sourceValues=[...(current[sourceRoll.id]??sizeSlots.map((_,index)=>sourceRoll.allocation[index]??0))]
      const next={...current}
      const start=Math.min(sourceIndex,targetIndex)
      const end=Math.max(sourceIndex,targetIndex)
      for(let rowIndex=start;rowIndex<=end;rowIndex+=1){
        if(rowIndex===sourceIndex)continue
        const targetRoll=selectedRolls[rowIndex]
        if(targetRoll)next[targetRoll.id]=[...sourceValues]
      }
      return next
    })
  }
  const beginRowFill=(event:ReactPointerEvent<HTMLButtonElement>,sourceIndex:number)=>{
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    fillDraggedRef.current=false
    const range={source:sourceIndex,target:sourceIndex}
    fillRangeRef.current=range
    setFillRange(range)
  }
  const moveRowFill=(event:ReactPointerEvent<HTMLButtonElement>)=>{
    const range=fillRangeRef.current
    if(!range)return
    const rowElement=document.elementFromPoint(event.clientX,event.clientY)?.closest<HTMLElement>('[data-allocation-row-index]')
    const hoveredIndex=Number(rowElement?.dataset.allocationRowIndex)
    if(!Number.isFinite(hoveredIndex))return
    const target=Math.max(0,Math.min(selectedRolls.length-1,hoveredIndex))
    if(target===range.target)return
    const nextRange={source:range.source,target}
    fillRangeRef.current=nextRange
    setFillRange(nextRange)
  }
  const finishRowFill=(event:ReactPointerEvent<HTMLButtonElement>)=>{
    const range=fillRangeRef.current
    if(range&&range.target!==range.source){
      fillRowsFromSource(range.source,range.target)
      fillDraggedRef.current=true
    }
    fillRangeRef.current=null
    setFillRange(null)
    if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const cancelRowFill=(event:ReactPointerEvent<HTMLButtonElement>)=>{
    fillRangeRef.current=null
    setFillRange(null)
    if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const clickRowFill=(sourceIndex:number)=>{
    if(fillDraggedRef.current){fillDraggedRef.current=false;return}
    const targetIndex=sourceIndex<selectedRolls.length-1?sourceIndex+1:sourceIndex-1
    fillRowsFromSource(sourceIndex,targetIndex)
  }
  const fillColumnsFromSource=(sourceSlot:number,targetSlot:number)=>{
    if(targetSlot===sourceSlot)return
    setAllocations((current)=>{
      const next={...current}
      const start=Math.min(sourceSlot,targetSlot)
      const end=Math.max(sourceSlot,targetSlot)
      selectedRolls.forEach((roll)=>{
        const row=[...(current[roll.id]??sizeSlots.map((_,index)=>roll.allocation[index]??0))]
        const sourceValue=row[sourceSlot]
        for(let slotIndex=start;slotIndex<=end;slotIndex+=1){
          if(slotIndex!==sourceSlot)row[slotIndex]=sourceValue
        }
        next[roll.id]=row
      })
      return next
    })
  }
  const beginColumnFill=(event:ReactPointerEvent<HTMLButtonElement>,sourceSlot:number)=>{
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    columnFillDraggedRef.current=false
    const range={source:sourceSlot,target:sourceSlot}
    columnFillRangeRef.current=range
    setColumnFillRange(range)
  }
  const moveColumnFill=(event:ReactPointerEvent<HTMLButtonElement>)=>{
    const range=columnFillRangeRef.current
    if(!range)return
    const slotElement=document.elementFromPoint(event.clientX,event.clientY)?.closest<HTMLElement>('[data-column-fill-slot]')
    const hoveredSlot=Number(slotElement?.dataset.columnFillSlot)
    if(!Number.isFinite(hoveredSlot))return
    const target=Math.max(0,Math.min(sizeSlots.length-1,hoveredSlot))
    if(target===range.target)return
    const nextRange={source:range.source,target}
    columnFillRangeRef.current=nextRange
    setColumnFillRange(nextRange)
  }
  const finishColumnFill=(event:ReactPointerEvent<HTMLButtonElement>)=>{
    const range=columnFillRangeRef.current
    if(range&&range.target!==range.source){
      fillColumnsFromSource(range.source,range.target)
      columnFillDraggedRef.current=true
    }
    columnFillRangeRef.current=null
    setColumnFillRange(null)
    if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const cancelColumnFill=(event:ReactPointerEvent<HTMLButtonElement>)=>{
    columnFillRangeRef.current=null
    setColumnFillRange(null)
    if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId)
  }
  const clickColumnFill=(sourceSlot:number)=>{
    if(columnFillDraggedRef.current){columnFillDraggedRef.current=false;return}
    const targetSlot=sourceSlot<sizeSlots.length-1?sourceSlot+1:sourceSlot-1
    fillColumnsFromSource(sourceSlot,targetSlot)
  }
  const clearForm=()=>{
    setSku('');setBrand('');setModel('');setSelectedPattern(null);setSelectedRollIds([]);setSizeSlots([]);setAllocations({});setEta('');setNotes('');setSizeNotice('')
    setRollYardUsage(Object.fromEntries(fabricRollCatalog.map(r=>[r.id,String(r.yards)])))
    setSavedId('');requestId.current=crypto.randomUUID()
    setNotice('Form kosong siap diisi.')
  }
  const heading=<section className="hero-copy compact cutting-hero"><div className="eyebrow">PRODUKSI · CUTTING</div><h1>Buat Potongan</h1><p>Pilih model dan serinya, lalu catat hasil potong dari roll yang dipakai.</p>{!savedId&&<button type="button" className="gar-text" onClick={clearForm}>Mulai form kosong</button>}</section>
  const saved=session.cuts.find(lot=>lot.id===savedId)
  if(saved)return <>{heading}<div className="gar-success" role="status">{notice} <a href={pickupPath+'?pot='+saved.id}>Bagi {saved.id}</a></div>
    <section className="panel gar-panel"><div className="gar-panel-head"><h2>{saved.id} · {lotLabel(saved)}</h2><span>Menunggu mandor</span></div>
      <p>{saved.qty} pcs · {seriesLabel(saved.series!)} · {lotPattern(saved).name}</p>{cutRolls(saved).map(r=><div key={r.id}><p>Roll {r.id} · {r.sourceYards} yd sebelum dipotong · dipakai {r.usedYards} yd · sisa {r.remainingYards} yd.</p><small>{r.slots.filter(s=>s.qty>0).map(s=>s.size+s.image+' = '+s.qty+' pcs').join(' · ')}</small></div>)}
      <div className="gar-actions"><a className="gar-button" href="/analisis/planner/">Lihat perubahan di Planner</a><button type="button" className="gar-button" disabled>Simpan Potongan ke WIP · sudah tersimpan</button></div></section>
    <AdviceBox mode="cut" session={session} onCut={useAdvice}/></>
  return <>{heading}
    <AdviceBox mode="cut" session={session} onCut={useAdvice}/>
    {notice&&<div role="status" className="gar-success">{notice}</div>}
    <section className="cutting-flow-rail panel" aria-label="Alur Buat Potongan">{['Pilih roll','Tentukan yard used','Catat hasil per roll','Simpan ke WIP'].map((label,index)=><div className={index===0?'active':''} key={label}><span>{String(index+1).padStart(2,'0')}</span><strong>{label}</strong>{index<3&&<Icon name="arrow"/>}</div>)}</section>
    <section className="roll-first-layout">
      <div className="panel roll-catalog-panel">
        <div className="cutting-panel-head"><div><span>01 · SUMBER KAIN</span><h2>Pilih roll yang mau dipotong</h2><p>Satu roll tetap satu baris. Urutan dan yard asal tidak digabung.</p></div><span className="selection-pill">{selectedRolls.length} dipilih</span></div>
        <div className="roll-catalog-toolbar"><div className="roll-search"><Icon name="search"/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari roll, pabrik, bahan, atau yard..."/></div><div className="roll-filters"><MultiCheckFilter label="Pabrik" options={fabricRollSuppliers} selected={selectedSuppliers} onChange={setSelectedSuppliers}/><MultiCheckFilter label="Bahan" options={fabricRollMaterials} selected={selectedMaterials} onChange={setSelectedMaterials}/></div></div>
        <div className="roll-list-caption"><span>{visibleRolls.length} roll tersedia</span><button type="button" onClick={toggleVisible}>{allVisibleSelected?'Batalkan hasil tampil':'Pilih semua hasil'}</button></div>
        <div className="cutting-roll-list">{visibleRolls.map((roll)=>{const selected=selectedIdSet.has(roll.id);return <button type="button" aria-pressed={selected} className={`stock-roll-row ${selected?'selected':''}`} key={roll.id} onClick={()=>toggleRoll(roll.id)}><span className="roll-select-box">{selected&&<Icon name="check"/>}</span><span className="stock-roll-seq">{String(roll.sequence).padStart(2,'0')}</span><span className="stock-roll-name"><strong>{roll.material}</strong><small>{roll.supplier} · {roll.id} · masuk {roll.receivedAt}</small></span><span className="stock-roll-yard"><strong>{formatQuantity(roll.yards,2)} yd</strong><small>{selected?'Masuk pembagian':'Siap dipilih'}</small></span></button>})}{visibleRolls.length===0&&<div className="catalog-empty"><Icon name="search"/><strong>Roll tidak ditemukan</strong><small>Periksa pencarian atau pilihan filter pabrik dan bahan.</small></div>}</div>
      </div>
      <aside className="panel cutting-live-summary">
        <div className="eyebrow">BATCH PRODUKSI</div><h2>{model||'Potongan baru'}</h2><p>{series?seriesLabel(series):'Seri belum dipilih'}{linked?' · '+linked.key+' · '+linked.colour:''}</p><p>Hasil cutting ini belum didistribusikan ke batch Mandor.</p>
        <div className="cutting-summary-main"><div><span>YARD USED</span><strong>{formatQuantity(totalUsedYards,2)} yd</strong><small>{selectedRolls.length} roll · {partialRollCount} split</small></div><div><span>TOTAL POTONGAN</span><strong>{totalPieces} pcs</strong><small>{dozenPieces(totalPieces)}</small></div></div>
        <div className="cutting-summary-sizes" style={sizeSummaryStyle}>{selectedCuttingSizes.map((size)=><div key={size}><span>SIZE {size}</span><strong>{sizeTotalByName[size]} pcs</strong><small>{dozenPieces(sizeTotalByName[size])}</small></div>)}</div>
        <div className="po-preview"><Icon name="warehouse"/><div><strong>Tujuan berikutnya: WIP Potongan</strong><span>Setelah disimpan, hasil ini menunggu mandor mengambil. Pembagian batch dilakukan saat pickup.</span></div></div>
        <button type="button" className="primary-btn cutting-next" disabled={selectedRolls.length===0} onClick={()=>document.getElementById('roll-issue-workbench')?.scrollIntoView({behavior:'smooth',block:'start'})}>Atur yard yang dipakai <Icon name="arrow"/></button>
      </aside>
    </section>
    <section className="panel roll-issue-workbench" id="roll-issue-workbench" data-keyboard-scope>
      <div className="cutting-panel-head roll-issue-head"><div><span>02 · YARD USED PER ROLL</span><h2>Pakai seluruh roll atau ambil sebagian</h2><p>Default-nya satu roll dipakai utuh. Kalau hanya dipakai sebagian, masukkan yard aktual; sisanya tetap menjadi Stock On Hand pada nomor roll yang sama.</p></div><span className={yardUsageValid?'issue-ready-pill':'issue-error-pill'}>{yardUsageValid?'Siap dipotong':'Periksa yard'}</span></div>
      <div className="roll-issue-rule"><Icon name="audit"/><div><strong>Golden rule: whole roll first</strong><span>Split hanya saat memang dibutuhkan di lapangan. Identitas roll tidak berubah dan total yard harus tetap rekonsiliasi.</span></div></div>
      <div className="roll-issue-table-head"><span>ROLL SOURCE</span><span>STOCK ON HAND</span><span>USED FOR CUTTING</span><span>REMAINING</span><span>STATUS</span></div>
      <div className="roll-issue-list" data-keyboard-grid>{rollUsageRows.map(({roll,input,used,balance,valid,partial},index)=><article className={`${valid?'':'invalid'} ${partial?'partial':''}`} key={roll.id}>
        <div className="roll-issue-identity"><span>{String(index+1).padStart(2,'0')}</span><div><strong>{roll.id} · {roll.material}</strong><small>{roll.supplier} · masuk {roll.receivedAt}</small></div></div>
        <div className="roll-issue-number"><small>STOCK ON HAND</small><strong>{formatQuantity(roll.yards,2)} yd</strong></div>
        <label className="roll-used-input"><span>USED FOR CUTTING</span><div><input data-grid-row={index} data-grid-col={0} inputMode="decimal" value={input} placeholder="0" aria-invalid={!valid} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateRollYardUsage(roll.id,event.target.value)}/><b>yd</b></div></label>
        <div className="roll-issue-number remaining"><small>REMAINING</small><strong>{valid?formatQuantity(balance,2):'—'} yd</strong></div>
        <div className="roll-issue-state"><em className={!valid?'error':partial?'split':'whole'}>{!valid?'INVALID':partial?'SPLIT':'WHOLE ROLL'}</em><button type="button" disabled={valid&&!partial&&used===roll.yards} onClick={()=>useFullRoll(roll)}>Use full roll</button></div>
      </article>)}{selectedRolls.length===0&&<div className="allocation-empty"><Icon name="ruler"/><strong>Belum ada roll dipilih</strong><small>Pilih roll pada Browse Roll di atas.</small></div>}</div>
      <div className="roll-issue-footer"><div><span>SOURCE SELECTED<strong>{formatQuantity(totalSourceYards,2)} yd</strong></span><i>−</i><span>USED<strong>{formatQuantity(totalUsedYards,2)} yd</strong></span><i>=</i><span className="remaining">REMAINING<strong>{formatQuantity(totalBalanceYards,2)} yd</strong></span></div><button type="button" className="primary-btn" disabled={!yardUsageValid} onClick={()=>document.getElementById('allocation-workbench')?.scrollIntoView({behavior:'smooth',block:'start'})}>Lanjut catat hasil <Icon name="arrow"/></button></div>
    </section>
    <section ref={formRef} className="panel allocation-workbench" id="allocation-workbench">
      <div className="cutting-panel-head allocation-head"><div><span>03 · HASIL POTONG PER ROLL</span><h2>Catat hasil satu seri</h2><p>Pilih seri sekali. Isi jumlah aktual pada kolom roll. Ukuran tanpa hasil boleh nol.</p></div><span className="draft-pill">Draft</span></div>
      <div className="cutting-meta-grid">
        <Field label="Model dan seri · wajib"><select required aria-label="Model dan seri" className="erp-input" value={model} onChange={e=>selectModel(e.target.value)}><option value="">Pilih model dan seri</option>{Object.entries(modelSeries).map(([name,set])=><option key={name} value={name}>{name} · {seriesLabel(linked&&linked.model===name&&series?series:set)}</option>)}</select></Field>
        <CuttingPatternPicker value={selectedPattern} onChange={setSelectedPattern}/>
        <Field label="Merek rencana · opsional"><select aria-label="Merek rencana" className="erp-input" value={brand} onChange={e=>{const next=e.target.value;setBrand(next);if(next&&linked&&linked.brand!==next)setSku('')}}><option value="">Belum ditentukan</option><option>Vivo</option><option>Widie</option></select></Field>
        <Field label="SKU rencana · opsional"><select aria-label="SKU rencana" className="erp-input" value={sku} onChange={e=>selectSku(e.target.value)}><option value="">Belum ditentukan</option>{articles.filter(a=>!brand||a.brand===brand).map(a=><option key={a.key} value={articleChoice(a)}>{a.key} · {a.colour}</option>)}</select></Field>
        {linked&&<Field label="Identitas dari Master SKU"><span>{linked.colour} · {linked.sizes.length===1?'Ukuran khusus':'Rentang'} {rangeLabel(linked.sizes)} · {planningPattern(linked,session)?patternFor(planningPattern(linked,session)!).name:'Pola rencana kosong'}</span></Field>}
        <Field label="Lokasi sumber"><span>Gudang Kain</span></Field>
        <Field label="Tanggal potong · wajib"><input aria-label="Tanggal potong" required max="2026-11-24" className="erp-input" type="date" value={date} onChange={e=>setDate(e.target.value)}/></Field>
        <Field label="Perkiraan siap · opsional"><input aria-label="Perkiraan siap" className="erp-input" type="date" value={eta} onChange={e=>setEta(e.target.value)}/></Field>
        <Field label="Catatan · opsional"><input aria-label="Catatan potongan" className="erp-input" value={notes} onChange={e=>setNotes(e.target.value)}/></Field></div>
      {sizeNotice&&<p role="status" className="cutting-size-notice">{sizeNotice}</p>}
      <details className="cutting-size-picker"><summary>Atur anggota seri dan gambar</summary>
        <div className="cutting-size-options">{cuttingSizeOptions.map((size)=>{const checked=selectedCuttingSizes.includes(size);return <label className={checked?'active':''} key={size}><input type="checkbox" checked={checked} onChange={()=>toggleCuttingSize(size)}/><span>{checked&&<Icon name="check"/>}</span><strong>{size}</strong><small>{checked?`${sizeSlots.filter((slot)=>slot.size===size).length} kolom`:'Tidak dipakai'}</small></label>})}</div>
      <div className="size-slot-builder"><div className="size-slot-builder-copy"><span>MULTIPLIER KOLOM</span><strong>Tambah atau kurangi gambar per size terpilih</strong><small>Tombol minus menggabungkan isi kolom terakhir ke kolom sebelumnya—total size tetap aman.</small></div><div className="size-slot-controls">{selectedCuttingSizes.map((size)=>{const count=sizeSlots.filter((slot)=>slot.size===size).length;return <div className="size-slot-control" key={size}><div><span>SIZE {size}</span><strong>{count===1?'1 kolom':`${count} kolom`}</strong><small>{count===1?'Tanpa label gambar':`Gambar A–${drawingLabel(count)}`}</small></div><div><button type="button" disabled={count<=1} aria-label={`Kurangi slot Size ${size}`} title="Gabungkan kolom terakhir ke kolom sebelumnya" onClick={()=>removeSizeSlot(size)}>−</button><b>{count}</b><button type="button" aria-label={`Tambah slot Size ${size}`} title="Tambah kolom gambar baru" onClick={()=>addSizeSlot(size)}>+</button></div></div>})}</div></div>
      </details>
      <div className="cutting-grid-shortcuts"><span><kbd>Enter</kbd> turun</span><span><kbd>Tab</kbd> ke kanan</span><span><kbd>↑ ↓ ← →</kbd> pindah sel</span><span><Icon name="drag"/> Tarik baris ke atas / bawah</span><span>Tarik kolom ke kiri / kanan</span><span>Paste blok Excel didukung</span></div>
      <div className="column-fill-toolbar"><div><span>FILL SATU KOLOM</span><small>Klik untuk satu kolom · tarik kiri/kanan untuk beberapa</small></div><div className="column-fill-grid" style={slotGridStyle}>{displayedSizeSlots.map((slot,slotIndex)=>{const isSource=columnFillRange?.source===slotIndex;const isPreview=Boolean(columnFillRange&&slotIndex!==columnFillRange.source&&slotIndex>=Math.min(columnFillRange.source,columnFillRange.target)&&slotIndex<=Math.max(columnFillRange.source,columnFillRange.target));const drawingCopy=slot.image?` gambar ${slot.image}`:'';return <button type="button" tabIndex={-1} data-column-fill-slot={slotIndex} className={`${isSource?'fill-source':''} ${isPreview?'fill-preview':''}`} key={slot.key} aria-label={`Salin seluruh kolom size ${slot.size}${drawingCopy}`} title="Klik: salin ke kolom sebelah · tarik: isi beberapa kolom" onPointerDown={(event)=>beginColumnFill(event,slotIndex)} onPointerMove={moveColumnFill} onPointerUp={finishColumnFill} onPointerCancel={cancelColumnFill} onClick={()=>clickColumnFill(slotIndex)}><span>{slot.size}{slot.image&&<small>{slot.image}</small>}</span><Icon name="drag"/></button>})}</div><span>{displayedSizeSlots.length} kolom aktif</span></div>
      <div className="slot-legend"><div><span>SLOT UKURAN</span><small>Jumlah gambar mengikuti susunan di atas</small></div>{displayedSizeSlots.map((slot)=><span key={slot.key}><strong>{slot.size}</strong>{slot.image&&<small>Gbr {slot.image}</small>}</span>)}<b>TOTAL</b></div>
      <div className="allocation-roll-list">{selectedRolls.map((roll,index)=>{
        const row=allocations[roll.id]??sizeSlots.map((_,slotIndex)=>roll.allocation[slotIndex]??0)
        const rowTotal=row.reduce((sum,qty)=>sum+qty,0)
        const isFillSource=fillRange?.source===index
        const isFillPreview=Boolean(fillRange&&index!==fillRange.source&&index>=Math.min(fillRange.source,fillRange.target)&&index<=Math.max(fillRange.source,fillRange.target))
        return <article data-allocation-row-index={index} className={`allocation-roll-row ${isFillSource?'fill-source':''} ${isFillPreview?'fill-preview':''}`} key={roll.id}>
          <div className="allocation-roll-identity"><span>{String(index+1).padStart(2,'0')}</span><div><strong>Roll {String(roll.sequence).padStart(2,'0')} · {roll.material}</strong><small>{formatQuantity(rollUsageRows[index]?.used??0,2)} yd used · {formatQuantity(rollUsageRows[index]?.balance??roll.yards,2)} yd remaining</small></div></div>
          <div className="allocation-slot-grid" style={slotGridStyle}>{displayedSizeSlots.map((slot,slotIndex)=>{
            const isColumnSource=columnFillRange?.source===slotIndex
            const isColumnPreview=Boolean(columnFillRange&&slotIndex!==columnFillRange.source&&slotIndex>=Math.min(columnFillRange.source,columnFillRange.target)&&slotIndex<=Math.max(columnFillRange.source,columnFillRange.target))
            const drawingCopy=slot.image?`, gambar ${slot.image}`:''
            return <label className={`${isColumnSource?'column-fill-source':''} ${isColumnPreview?'column-fill-preview':''}`} key={slot.key}><span>{slot.size}{slot.image&&<small>{slot.image}</small>}</span><input data-cutting-row={index} data-cutting-slot={slotIndex} aria-label={`Roll ${roll.sequence}, size ${slot.size}${drawingCopy}`} inputMode="numeric" type="text" pattern="[0-9]*" value={row[slotIndex]??0} onFocus={(event)=>{if((row[slotIndex]??0)===0)event.currentTarget.select()}} onClick={(event)=>{if((row[slotIndex]??0)===0)event.currentTarget.select()}} onKeyDown={(event)=>handleAllocationKey(event,index,slotIndex)} onPaste={(event)=>pasteAllocationGrid(event,index,slotIndex)} onChange={(event)=>updateAllocation(roll,slotIndex,event.target.value)}/></label>
          })}</div>
          <div className="allocation-row-total"><span>TOTAL ROLL</span><strong>{rowTotal} pcs</strong><small>{dozenPieces(rowTotal)}</small></div>
          <button type="button" tabIndex={-1} className="row-fill-handle" aria-label={`Salin isi Roll ${roll.sequence} ke baris atas atau bawah`} title="Klik: salin ke baris terdekat · tarik: isi ke atas atau bawah" onPointerDown={(event)=>beginRowFill(event,index)} onPointerMove={moveRowFill} onPointerUp={finishRowFill} onPointerCancel={cancelRowFill} onClick={()=>clickRowFill(index)}><Icon name="drag"/><span/></button>
        </article>
      })}{selectedRolls.length===0&&<div className="allocation-empty"><Icon name="ruler"/><strong>Belum ada roll dipilih</strong><small>Pilih minimal satu roll di bagian atas untuk mulai membagi ukuran.</small></div>}</div>
      <div className="cutting-totals-row">{selectedCuttingSizes.map((size)=><div key={size}><span>JUMLAH SIZE {size}</span><strong>{sizeTotalByName[size]} pcs</strong></div>)}<div><span>TOTAL BATCH</span><strong>{totalPieces} pcs</strong><small>{dozenPieces(totalPieces)}</small></div></div>
      <section className="cutting-wip-destination" aria-label="Tujuan hasil cutting">
        <div><span>04 · SIMPAN HASIL CUTTING</span><h2>Masuk WIP Produksi, belum menjadi Batch Distribusi</h2><p>Jejak roll, yard issued, sisa roll, dan size tetap melekat pada Batch Produksi. Mandor serta Batch Distribusi baru dicatat saat fisik benar-benar diambil.</p></div>
        <div className="cutting-wip-card"><span className="wip-state-dot"/><div><small>STATUS SETELAH DISIMPAN</small><strong>Menunggu mandor mengambil</strong><span>{selectedRolls.length} roll · {formatQuantity(totalUsedYards,2)} yd used · {totalPieces} pcs · {selectedPattern ? `Pola ${selectedPattern.code}/${selectedPattern.revision}` : 'Pola wajib dipilih sebelum simpan'}</span></div></div>
      </section>
      {savedDraft&&<div className="document-actions"><strong>Draft potongan</strong><button type="button" onClick={restoreDraft}>Edit draft tersimpan</button><button type="button" onClick={()=>setDeleteDraft(true)}>Hapus draft</button></div>}
      {deleteDraft&&<ReasonDialog title="Hapus draft potongan?" closeLabel="Kembali" onClose={()=>setDeleteDraft(false)}><p>Draft ini bisa dibuang sebelum hasil potongan masuk ke WIP.</p><button type="button" onClick={()=>{sessionStorage.removeItem(draftKey);setSavedDraft(false);setDeleteDraft(false);clearForm();setNotice('Draft potongan dihapus.')}}>Ya, hapus draft ini</button></ReasonDialog>}
      <div className="allocation-footer"><small>Latihan per pesanan · hasil simpan berlaku di tab ini.</small><div><button type="button" className="soft-btn" onClick={storeDraft} disabled={Boolean(savedId)||!series||!hasCanonicalPattern(selectedPattern)||!date||!yardUsageValid||!selectedRolls.every(r=>allocations[r.id]?.some(n=>n>0))}>Simpan draft cutting</button><button type="button" className="primary-btn" onClick={storeCut} disabled={Boolean(savedId)||!hasCanonicalPattern(selectedPattern)||!series||!date||!yardUsageValid||!selectedRolls.every(r=>allocations[r.id]?.some(n=>n>0))}>Simpan Potongan ke WIP <Icon name="arrow"/></button></div></div>
      {notice&&<p className="gar-success">{notice} {savedId&&<a href={pickupPath+'?pot='+savedId}>Buka Bagi Potongan</a>}</p>}
    </section>
  </>
}

export function RollBatchQuickMenu({rollId,batchCount,currentBatch,split,onAssign}:{rollId:string;batchCount:number;currentBatch:number|null;split:boolean;onAssign:(batchIndex:number)=>void}) {
  const label=split?'Pecah':currentBatch===null?'Pilih':String(currentBatch+1)
  return <label className="roll-batch-quick"><span className="sr-only">Pilih batch untuk {rollId}</span><select aria-label={`Pilih batch untuk ${rollId}`} value={!split&&currentBatch!==null?String(currentBatch):''} onChange={(event)=>onAssign(Number(event.target.value))}><option value="" disabled>Batch: {label}</option>{Array.from({length:batchCount},(_,batchIndex)=><option value={batchIndex} key={batchIndex}>Batch: {batchIndex+1}</option>)}</select><ChevronDown/></label>
}

type UnassignedRollCardProps = {
  sizeLabels?: readonly string[]
  row: { roll: FabricRoll; sizes: QtyTuple; quantity: number }
  batchCount: number
  onAssignWhole: (rollId: string, targetBatch: number) => void
  onOpenSplit: (rollId: string) => void
  onDragStart: (event: ReactPointerEvent<HTMLButtonElement>, rollId: string) => void
  onDragMove: (event: ReactPointerEvent<HTMLButtonElement>) => void
  onDragEnd: (event: ReactPointerEvent<HTMLButtonElement>) => void
  onDragCancel: (event: ReactPointerEvent<HTMLButtonElement>) => void
}

export function UnassignedRollCard({
  sizeLabels=cuttingSizes,
  row,
  batchCount,
  onAssignWhole,
  onOpenSplit,
  onDragStart,
  onDragMove,
  onDragEnd,
  onDragCancel,
}: UnassignedRollCardProps) {
  const rollLabel = `Roll ${String(row.roll.sequence).padStart(2, '0')}`
  const instructionId = `wip-roll-${row.roll.id.replace(/[^a-zA-Z0-9_-]/g, '-')}-instruction`

  return <article className="wip-roll-token" aria-labelledby={`${instructionId}-title`}>
    <div className="wip-roll-token-body">
      <div className="wip-roll-token-total">
        <span>PANJANG ROLL</span>
        <strong>{formatQuantity(row.roll.yards, 2)}<small>yd</small></strong>
        <em>{row.quantity} pcs hasil potong</em>
      </div>
      <div className="wip-roll-token-sizes" aria-label={`Rincian ukuran ${rollLabel}`}>
        {sizeLabels.map((size, index) => <span key={size}><small>SIZE {size}</small><strong>{row.sizes[index]}</strong><em>pcs</em></span>)}
      </div>
      <p id={`${instructionId}-title`} className="wip-roll-token-code">{rollLabel} · {row.roll.id}</p>
      <p id={instructionId}>Pindahkan utuh lewat pilihan Batch. Drag hanya alternatif desktop.</p>
    </div>
    <footer className="wip-roll-token-actions">
      <RollBatchQuickMenu rollId={row.roll.id} batchCount={batchCount} currentBatch={null} split={false} onAssign={(batchIndex) => onAssignWhole(row.roll.id, batchIndex)}/>
      <button type="button" className="wip-roll-split-btn" onClick={() => onOpenSplit(row.roll.id)}><Icon name="ruler"/><span><strong>Atur pecahan</strong><small>Bagi size manual</small></span><Icon name="arrow"/></button>
      <button
        type="button"
        className="wip-roll-drag-handle"
        aria-label={`Tarik ${rollLabel} ke batch`}
        aria-describedby={instructionId}
        title="Tahan lalu tarik ke kartu batch"
        onPointerDown={(event) => onDragStart(event, row.roll.id)}
        onPointerMove={onDragMove}
        onPointerUp={onDragEnd}
        onPointerCancel={onDragCancel}
      >
        <Icon name="drag"/>
        <span className="sr-only">Tarik ke batch</span>
      </button>
    </footer>
  </article>
}
