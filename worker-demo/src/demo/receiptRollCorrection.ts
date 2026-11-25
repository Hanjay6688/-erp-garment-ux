export type ReceiptRoll = {id:string;length:number;physicalCode?:string}
export type RollReceiptCorrection = {
  id:string;roll:string;length:number;physicalCode?:string;beforeLength:number;beforeCode?:string;reason:string;at:string
}
export type ReceiptReversal = {reason:string;at:string}
export type StockSourceLink = {label:string;href:string}

export function receiptRolls<T extends ReceiptRoll>(receipt:{rolls:T[];corrections?:RollReceiptCorrection[]}):T[] {
  if(!receipt.corrections?.length)return receipt.rolls
  const byRoll=new Map(receipt.corrections.map(row=>[row.roll,row]))
  return receipt.rolls.map(roll=>{
    const last=byRoll.get(roll.id)
    return last?{...roll,length:last.length,physicalCode:last.physicalCode}:roll
  })
}

export function reviewRollReceiptCorrection(roll:ReceiptRoll,candidate:{id:string;length:number;code:string;reason:string;at:string},stock:ReceiptRoll[],used:number) {
  const code=candidate.code.trim()
  const length=candidate.length
  const reason=candidate.reason.trim()
  if(!Number.isSafeInteger(Math.round(length*1e6))||length<=0||length+1e-7<used||!code||code.length>90||reason.length<4)
    throw Error('Isi nomor fisik, panjang yang menutup pemakaian tercatat, dan alasan koreksi.')
  const physicalCode=code===roll.id?undefined:code
  if(stock.some(item=>item.id!==roll.id&&[item.id,item.physicalCode].some(value=>value?.toLowerCase()===code.toLowerCase())))
    throw Error('Nomor roll fisik ini sudah dipakai oleh roll lain.')
  if(length===roll.length&&physicalCode===roll.physicalCode)throw Error('Ubah panjang atau nomor roll sebelum menyimpan.')
  return {id:candidate.id,roll:roll.id,length,physicalCode,beforeLength:roll.length,beforeCode:roll.physicalCode,reason,at:candidate.at}
}

export const cutDocumentPath=(cut:string)=>'/produksi/buat-potongan/?pot='+encodeURIComponent(cut)
export const switchRollPath=(cut?:string,roll?:string)=>'/gudang/bahan-roll/?'+new URLSearchParams({koreksi:'ganti-roll',...(cut?{pot:cut}:{}),...(roll?{roll}:{})})
export const receiptDocumentPath=(number:string,kind:'kain'|'kantong'|'aksesori'='kain',roll?:string)=>
  '/gudang/pembelian-penerimaan/?'+new URLSearchParams({jenis:kind,surat:number,...(roll?{roll}:{})})+'#dokumen-penerimaan'
export const pocketIssuePath=(issue:string)=>'/gudang/kain-kantong/?pakai='+encodeURIComponent(issue)+'#pemakaian-kantong'
export const pocketAllocationPath=(allocation:string)=>'/gudang/kain-kantong/?pembagian='+encodeURIComponent(allocation)+'#pembagian-kantong'
export const stockEventPath=(kind:'adjust'|'convert',id:string)=>'/gudang/'+(kind==='adjust'?'stock-adjustment':'ganti-merek')+'/?mutasi='+encodeURIComponent(id)+'#riwayat-konversi'
