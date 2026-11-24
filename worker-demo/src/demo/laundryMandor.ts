import { sewingWipSeeds } from './sewingModel'

export const LAUNDRY_ALL_MANDORS = 'Semua mandor'
export const LAUNDRY_NO_MANDOR = 'Tanpa mandor'

/** Mandor penanggung jawab batch laundry: pakai data batch, lalu Batch Produksi asal, lalu label eksplisit. */
export const laundryMandorOf = (row:{mandor?:string|null;parentId:string}) =>
  row.mandor?.trim() || sewingWipSeeds.find((parent)=>parent.id===row.parentId)?.mandor?.trim() || LAUNDRY_NO_MANDOR

export const laundryMandorOptions = (rows:Array<{mandor?:string|null;parentId:string}>) =>
  Array.from(new Set(rows.map(laundryMandorOf))).sort((left,right)=>left===LAUNDRY_NO_MANDOR?1:right===LAUNDRY_NO_MANDOR?-1:left.localeCompare(right,'id'))

export const matchesLaundryMandor = (row:{mandor?:string|null;parentId:string},mandorFilter:string) =>
  mandorFilter===LAUNDRY_ALL_MANDORS||laundryMandorOf(row)===mandorFilter

