import { useEffect, useId, useRef, useState } from 'react'
import './select-search.css'

const fold=(value:string)=>value.normalize('NFKD').replace(/\p{M}/gu,'').toLocaleLowerCase('id').trim()
function optionsFor(select:HTMLSelectElement) {
  return Array.from(select.options).map((option,index)=>({
    index,value:option.value,label:option.label,selected:option.selected,
    group:option.parentElement instanceof HTMLOptGroupElement?option.parentElement.label:'',
    disabled:option.disabled||option.closest('optgroup')?.disabled===true,hidden:option.hidden,
  }))
}
function searchLabel(select:HTMLSelectElement) {
  const label=select.labels?.[0]?.cloneNode(true) as HTMLElement|undefined
  label?.querySelectorAll('select,input,textarea,button').forEach(el=>el.remove())
  return select.getAttribute('aria-label') || select.getAttribute('aria-labelledby')?.split(/\s+/).map(id=>document.getElementById(id)?.textContent).filter(Boolean).join(' ') || label?.textContent?.trim() || 'Pilihan'
}
export default function SelectSearch() {
  const [active,setActive]=useState<{select:HTMLSelectElement;initial:string}|null>(null)
  useEffect(()=>{
    const find=(event:Event)=>event.target instanceof HTMLSelectElement&&!event.target.matches(':disabled')?event.target:null
    const onPointer=(event:PointerEvent)=>{
      const select=find(event)
      if(select&&event.button===0){event.preventDefault();setActive({select,initial:''})}
    }
    const onClick=(event:MouseEvent)=>{
      const select=find(event);if(select){event.preventDefault();setActive({select,initial:''})}
    }
    const onKey=(event:KeyboardEvent)=>{
      const select=find(event)
      if(!select||event.ctrlKey||event.metaKey||event.isComposing)return
      if(['Enter',' ','ArrowDown','ArrowUp','F4'].includes(event.key)||event.key.length===1){
        event.preventDefault();setActive({select,initial:event.key.length===1&&event.key!==' '?event.key:''})
      }
    }
    document.addEventListener('pointerdown',onPointer,true);document.addEventListener('click',onClick,true);document.addEventListener('keydown',onKey,true)
    return ()=>{document.removeEventListener('pointerdown',onPointer,true);document.removeEventListener('click',onClick,true);document.removeEventListener('keydown',onKey,true)}
  },[])
  return active?<ChoiceList select={active.select} initial={active.initial} close={()=>setActive(null)}/>:null
}
function ChoiceList({select,initial,close}:{select:HTMLSelectElement;initial:string;close:()=>void}) {
  const [query,setQuery]=useState(initial),[cursor,setCursor]=useState(0)
  const [,refresh]=useState(0)
  const dialog=useRef<HTMLDialogElement>(null),input=useRef<HTMLInputElement>(null)
  const identifier=useId(),title=searchLabel(select)
  const terms=fold(query).split(/\s+/).filter(Boolean)
  const shown=optionsFor(select).filter(o=>!o.hidden&&terms.every(term=>fold(o.group+' '+o.label).includes(term)))
  const eligible=shown.filter(o=>!o.disabled),current=eligible[Math.min(cursor,eligible.length-1)]
  const closeRef=useRef(close);closeRef.current=close
  useEffect(()=>{
    const el=dialog.current
    el?.showModal();input.current?.focus()
    const observer=new MutationObserver(()=>{if(!select.isConnected||select.matches(':disabled'))closeRef.current();else refresh(x=>x+1)})
    observer.observe(select,{childList:true,subtree:true,characterData:true,attributes:true})
    const onNavigation=()=>closeRef.current()
    window.addEventListener('popstate',onNavigation)
    return ()=>{observer.disconnect();window.removeEventListener('popstate',onNavigation);el?.close();if(select.isConnected)select.focus({preventScroll:true})}
  },[select])
  function choose(index:number) {
    const option=select.options[index]
    if(!select.isConnected||select.matches(':disabled')||!option||option.disabled||option.closest('optgroup')?.disabled)return
    if(select.multiple)option.selected=!option.selected;else select.selectedIndex=index
    select.dispatchEvent(new Event('input',{bubbles:true}));select.dispatchEvent(new Event('change',{bubbles:true}))
    if(select.multiple)refresh(x=>x+1);else close()
  }
  const empty=Array.from(select.options).findIndex(o=>o.value===''&&!o.disabled&&!o.hidden&&!o.closest('optgroup')?.disabled)
  function clear(){
    if(!select.multiple){if(empty>=0)choose(empty);return}
    for(const option of Array.from(select.options))if(!option.disabled&&!option.closest('optgroup')?.disabled)option.selected=false
    select.dispatchEvent(new Event('input',{bubbles:true}));select.dispatchEvent(new Event('change',{bubbles:true}));refresh(n=>n+1)
  }
  function move(step:number) {
    const index=Math.max(0,Math.min(eligible.length-1,cursor+step))
    setCursor(index)
    document.getElementById(identifier+'-'+eligible[index]?.index)?.scrollIntoView({block:'nearest'})
  }
  return <dialog ref={dialog} className="select-search" aria-labelledby={identifier+'-title'} onCancel={e=>{e.preventDefault();close()}}
    onClick={e=>{if(e.target!==e.currentTarget)return;const b=e.currentTarget.getBoundingClientRect();if(e.clientX<b.left||e.clientX>b.right||e.clientY<b.top||e.clientY>b.bottom)close()}}>
    <header><strong id={identifier+'-title'}>{title}</strong><button type="button" onClick={close} aria-label="Tutup pilihan">Tutup</button></header>
    <input ref={input} role="combobox" aria-label={'Cari '+title} aria-expanded="true" aria-controls={identifier} aria-autocomplete="list" aria-activedescendant={current?identifier+'-'+current.index:undefined}
      placeholder="Ketik untuk mencari…" value={query} onChange={e=>{setQuery(e.target.value);setCursor(0)}} onKeyDown={e=>{
        if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();move(e.key==='ArrowDown'?1:-1)}
        if(e.key==='Enter'&&!e.nativeEvent.isComposing){e.preventDefault();if(current)choose(current.index)}
      }}/>
    {!select.required&&(select.multiple||empty>=0)&&<button type="button" className="select-clear-choice" onClick={clear}>Kosongkan pilihan</button>}
    <div id={identifier} role="listbox" aria-label={title} aria-multiselectable={select.multiple||undefined}>
      {shown.map(o=><button key={o.index} type="button" id={identifier+'-'+o.index} role="option" aria-selected={o.selected} disabled={o.disabled} data-cursor={current?.index===o.index} onClick={()=>choose(o.index)}>{o.group&&<small>{o.group} · </small>}{o.label||'Kosongkan'}{o.selected&&<span aria-hidden="true"> ✓</span>}</button>)}
    </div>{!shown.length&&<p role="status">Pilihan tidak ditemukan.</p>}
  </dialog>
}
