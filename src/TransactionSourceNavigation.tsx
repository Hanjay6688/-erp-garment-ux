import {createContext,useCallback,useContext,useEffect,useMemo,useRef,useState,type ReactNode} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {parseTransactionSource,sourceId,type SourceReference,type TransactionDocument,type TransactionDomain} from './transactionSource'

type Selection={document:TransactionDocument;scope:string;key:string;epoch:number}
type Navigation={scope:string|null;selection:Selection|null;isCurrent:(scope:string)=>boolean;open:(document:TransactionDocument,scope:string)=>void}
const Context=createContext<Navigation|null>(null)
export function TransactionSourceProvider({scope,children,onNavigate,epoch=0}:{scope:string|null;epoch?:number;children:ReactNode;onNavigate:(route:TransactionDocument['route'])=>void}){
 const generation=scope===null?null:`${scope}:NAV:${epoch}`
 const [selection,setSelection]=useState<Selection|null>(null),current=useRef(generation)
 current.current=generation
 const isCurrent=useCallback((wanted:string)=>current.current===wanted,[])
 const open=useCallback((document:TransactionDocument,wanted:string)=>{if(current.current!==wanted)return;onNavigate(document.route);setSelection({document,scope:wanted,key:crypto.randomUUID(),epoch})},[onNavigate,epoch])
 const value=useMemo(()=>({scope:generation,selection:selection?.scope===generation&&selection.epoch===epoch?selection:null,isCurrent,open}),[generation,selection,isCurrent,open,epoch])
 return <Context.Provider value={value}>{children}</Context.Provider>
}
export function useTransactionSource(domain:TransactionDomain){
 const navigation=useContext(Context),selected=navigation?.selection
 return navigation?.scope&&selected?.scope===navigation.scope&&selected.document.domain===domain?selected:null
}
export default function TransactionSourceLink({sourceType,sourceId:identifier,disabled=false,label='Buka transaksi asal'}:{sourceType:string;sourceId:string|null;disabled?:boolean;label?:string}){
 const {runtime,identity}=useAuth(),navigation=useContext(Context)
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),seq=useRef(0)
 useEffect(()=>{++seq.current;setBusy(false);setError('');return()=>{++seq.current}},[navigation?.scope,sourceType,identifier,disabled])
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!navigation?.scope)return null
 const open=async()=>{
  if(disabled||busy||!sourceId(identifier)||!navigation.scope)return
  const scope=navigation.scope,ticket=++seq.current,reference:SourceReference={source_type:sourceType,source_id:identifier}
  setBusy(true);setError('')
  try{
   const r=await getUatSupabaseClient(runtime).rpc('erp_cp7_resolve_transaction_source_v1',{p_source:reference})
   if(ticket!==seq.current||!navigation.isCurrent(scope))return
   if(r.error)throw r.error
   const result=parseTransactionSource(r.data,reference,identity.profile.authUserId)
   if(!result.document){setError('Jenis transaksi asal ini belum dapat dibuka dari buku. Referensi asli tetap ditampilkan.');return}
   navigation.open(result.document,scope)
  }catch(e){if(ticket===seq.current&&navigation.isCurrent(scope))setError(normalizeClientError(e).message)}
  finally{if(ticket===seq.current&&navigation.isCurrent(scope))setBusy(false)}
 }
 return <div className="cproc-inline"><button type="button" disabled={disabled||busy||!sourceId(identifier)}onClick={()=>void open()}>{busy?'Memeriksa transaksi asal…':label}</button>{error?<small role="alert">{error}</small>:null}</div>
}
