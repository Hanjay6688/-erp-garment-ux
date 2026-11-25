import { useEffect, useId, useRef, type ReactNode } from 'react'

export function ReasonDialog({title,children,onClose,closeLabel,className,icon}:{title:string;children:ReactNode;onClose:()=>void;closeLabel?:string;className?:string;icon?:ReactNode}) {
  const ref=useRef<HTMLDialogElement>(null)
  const titleId=useId()
  useEffect(()=>{
    const dialog=ref.current
    const previous=document.activeElement instanceof HTMLElement?document.activeElement:null
    dialog?.showModal()
    return ()=>{dialog?.close();previous?.focus({preventScroll:true})}
  },[])
  return <dialog className={className ? 'gar-modal ' + className : 'gar-modal'} ref={ref} aria-labelledby={titleId} onCancel={event=>{event.preventDefault();onClose()}}
    onClick={event=>{if(event.target!==ref.current)return;const box=event.currentTarget.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)onClose()}}>
    <header>
      {icon&&<i className="gar-modal-icon" aria-hidden="true">{icon}</i>}
      <h2 id={titleId}>{title}</h2>
      <button type="button" className="gar-button" onClick={onClose} aria-label={closeLabel??"Tutup alasan"}>{closeLabel??"Tutup"}</button>
    </header>
    {children}
  </dialog>
}
