// Transport/lock waits are bounded independently of the total analysis time.
export const FROZEN_RPC_WAIT_MS=30_000
export const FROZEN_WAIT_MESSAGE='Server belum memberi jawaban. Hasil permintaan belum diketahui. Buka perhitungan tersimpan untuk memeriksa pekerjaan yang sama; jangan membuat ulang.'
export const FROZEN_LOCK_MESSAGE='Permintaan masih dikunci tab lain. Pemantauan dihentikan; buka kembali pekerjaan tersimpan yang sama setelah tab tersebut selesai.'
type Abortable<T>=PromiseLike<T>&{abortSignal?:(signal:AbortSignal)=>PromiseLike<T>}
export async function boundedFrozenReply<T>(start:()=>Abortable<T>,waitMs=FROZEN_RPC_WAIT_MS):Promise<T>{
 const controller=new AbortController()
 let timer:ReturnType<typeof setTimeout>|undefined
 try{
  const request=start(),reply=request.abortSignal?request.abortSignal(controller.signal):request
  const timeout=new Promise<never>((_,reject)=>{timer=setTimeout(()=>{reject(Error(FROZEN_WAIT_MESSAGE));controller.abort()},waitMs)})
  return await Promise.race([reply,timeout])
 }finally{if(timer!==undefined)clearTimeout(timer)}
}
export async function boundedFrozenLock<T>(key:string,action:()=>T|PromiseLike<T>,waitMs=FROZEN_RPC_WAIT_MS):Promise<T>{
 const locks=globalThis.navigator?.locks
 if(!locks)throw Error('Penyimpanan permintaan belum dapat dikunci. Buka kembali aplikasi pada peramban yang mendukung penguncian.')
 const controller=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined
 try{
  const timeout=new Promise<never>((_,reject)=>{timer=setTimeout(()=>{reject(Error(FROZEN_LOCK_MESSAGE));controller.abort()},waitMs)})
  const pending=locks.request(key,{mode:'exclusive',signal:controller.signal},async()=>{
   // A late/nonconforming lock implementation must not execute a timed-out
   // queued callback. Once acquired, the lock stays held for the whole action.
   if(controller.signal.aborted)throw Error(FROZEN_LOCK_MESSAGE)
   if(timer!==undefined)clearTimeout(timer)
   return await action()
  })
  return await Promise.race([pending,timeout])
 }finally{if(timer!==undefined)clearTimeout(timer)}
}
