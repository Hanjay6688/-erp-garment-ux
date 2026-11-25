import { simulationPatternSnapshots } from './productionModel'
import type { ProductionPatternSnapshot, QtyTuple, SizeTuple } from './productionModel'

export type SewingBatchSeed = {
  id: string
  number: number
  qty: number
  sizes: QtyTuple
  completed: number
  note: string
}

export type SewingParentSeed = {
  id: string
  sequence: number
  plannedBrand?: string
  pattern: ProductionPatternSnapshot | null
  model: string
  material: string
  mandor: string
  pickupAt: string
  sizes: SizeTuple
  batches: SewingBatchSeed[]
}

export const sewingWipSeeds: SewingParentSeed[] = [
  { id:'POT-260827-042',sequence:42,plannedBrand:'Widie',pattern:simulationPatternSnapshots.lucyRegular,model:'Kulot Lucy',material:'Lucy',mandor:'Mandor Afat',pickupAt:'27 Agu 2026 · 10:30',sizes:['31','32','33'],batches:[
    {id:'042-01',number:1,qty:229,sizes:[229,0,0],completed:188,note:'Warna navy · stik pinggang 2 jalur'},
    {id:'042-02',number:2,qty:225,sizes:[0,225,0],completed:225,note:'Warna maroon · obras rapat'},
    {id:'042-03',number:3,qty:222,sizes:[0,0,222],completed:0,note:'Warna hitam · cek sambungan samping'},
  ]},
  { id:'POT-260826-041',sequence:41,pattern:simulationPatternSnapshots.malibuRegular,model:'Malibu Regular',material:'Malibu',mandor:'Mandor Asep',pickupAt:'26 Agu 2026 · 14:15',sizes:['28','29','30'],batches:[
    {id:'041-01',number:1,qty:244,sizes:[82,81,81],completed:244,note:'Biru muda · benang senada · obras rapat'},
    {id:'041-02',number:2,qty:244,sizes:[81,81,82],completed:244,note:'Biru tua · cek kantong kanan kiri'},
  ]},
  { id:'POT-260825-039',sequence:39,plannedBrand:'Vivo',pattern:simulationPatternSnapshots.zodiakJumbo,model:'Zodiak Jumbo',material:'Zodiak KW',mandor:'Mandor Dedi',pickupAt:'25 Agu 2026 · 09:40',sizes:['34','35','36'],batches:[
    {id:'039-01',number:1,qty:114,sizes:[38,38,38],completed:114,note:'Stone · stik bawah 2 jalur'},
    {id:'039-02',number:2,qty:114,sizes:[38,38,38],completed:114,note:'Charcoal · sambungan samping dobel'},
    {id:'039-03',number:3,qty:114,sizes:[38,38,38],completed:0,note:'Black · gunakan benang hitam pekat'},
  ]},
]

export const laundryVendorNames = ['Laundry Berkah', 'Laundry Intan', 'Cemerlang Wash', 'Laundry Bersih Jaya']
