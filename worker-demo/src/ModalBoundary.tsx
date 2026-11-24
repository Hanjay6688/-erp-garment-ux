import {useEffect} from 'react'
import './form-clarity.css'
const layers=['role-editor-layer','bsr-dialog-layer','cbsr-modal-layer','ci-backdrop','biz-modal-backdrop','md-backdrop','mm-backdrop','pattern-editor-layer','simatch-backdrop','wh-return-backdrop','wip-control-backdrop','wip-detail-backdrop','wh-stock-drawer-backdrop']
const interactive='button:not(:disabled),a[href],input:not(:disabled),textarea:not(:disabled),select:not(:disabled),[tabindex]:not([tabindex="-1"])'
// Promote only the backdrop owned by a dialog. The page and its action bars remain outside it.
export default function ModalBoundary(){
  useEffect(()=>{
    const opened=new Map<HTMLElement,{dialog:HTMLElement;trigger:HTMLElement|null}>()
    const selector=layers.map(c=>'.'+c).join(',')
    function visible(el:HTMLElement){return !!el.getClientRects().length&&!el.closest('[hidden],[inert]')}
    function update(){
      for(const [layer,state] of opened){if(!layer.isConnected||!state.dialog.isConnected){opened.delete(layer);if(state.trigger?.isConnected)state.trigger.focus({preventScroll:true})}}
      for(const layer of document.querySelectorAll<HTMLElement>(selector)){
        const d=layer.querySelector<HTMLElement>('[role="dialog"],[role="alertdialog"]');if(!d||d.closest(selector)!==layer||opened.has(layer))continue
        const trigger=document.activeElement instanceof HTMLElement?document.activeElement:null
        layer.classList.add('erp-modal-boundary');opened.set(layer,{dialog:d,trigger})
        if(typeof layer.showPopover==='function'){layer.popover='manual';layer.showPopover()}
        if(!d.contains(document.activeElement)){const f=Array.from(d.querySelectorAll<HTMLElement>(interactive)).find(visible);(f??d).focus({preventScroll:true})}
      }
    }
    function handle(e:KeyboardEvent){if(document.querySelector('dialog[open]'))return
      const entry=Array.from(opened.values()).at(-1);if(!entry)return;const {dialog}=entry
      const items=Array.from(dialog.querySelectorAll<HTMLElement>(interactive)).filter(visible)
      if(e.key==='Tab'&&items.length){const first=items[0],last=items[items.length-1];if(!dialog.contains(document.activeElement)||(!e.shiftKey&&document.activeElement===last)||(e.shiftKey&&document.activeElement===first)){e.preventDefault();(e.shiftKey?last:first).focus()}}
      if(e.key==='Escape'&&!e.defaultPrevented){const close=items.find(b=>b.tagName==='BUTTON'&&/^(tutup|kembali|close|batal$)/i.test((b.getAttribute('aria-label')||b.textContent||'').trim()));if(close){e.preventDefault();e.stopPropagation();close.click()}}
    }
    const o=new MutationObserver(update);o.observe(document.body,{childList:true,subtree:true});update();document.addEventListener('keydown',handle,true)
    return()=>{o.disconnect();document.removeEventListener('keydown',handle,true);for(const layer of opened.keys()){if(layer.matches(':popover-open'))layer.hidePopover();layer.removeAttribute('popover');layer.classList.remove('erp-modal-boundary')}}
  },[]);return null
}
