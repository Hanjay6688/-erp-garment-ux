import type { QtyTuple, SizeTuple } from './productionModel'

type SlotAllocation = [number, number, number, number, number, number]

export type CuttingSizeSlot = { key: string; size: string }

export type AllocationMatrix = Record<string, string[]>

export type RollBatchSizeMatrix = Record<string, string[][]>

export type FabricRoll = {
  physicalCode?: string
  id: string
  sequence: number
  supplier: string
  material: string
  yards: number
  receivedAt: string
  sizeQuantities?: number[]
  allocation: SlotAllocation
}

export const initialCuttingSizeSlots: CuttingSizeSlot[] = [
  { key: '31-1', size: '31' }, { key: '31-2', size: '31' },
  { key: '32-1', size: '32' }, { key: '32-2', size: '32' },
  { key: '33-1', size: '33' }, { key: '33-2', size: '33' },
]

export const cuttingSizes: SizeTuple = ['31','32','33']

export const drawingLabel = (drawingNo: number) => {
  let value = Math.max(1, drawingNo)
  let label = ''
  while (value > 0) {
    value -= 1
    label = String.fromCharCode(65 + (value % 26)) + label
    value = Math.floor(value / 26)
  }
  return label
}

export const rollSizeQuantities = (allocation: SlotAllocation): QtyTuple => [
  allocation[0] + allocation[1], allocation[2] + allocation[3], allocation[4] + allocation[5],
]

export const quantitiesForRoll = (roll:FabricRoll) => roll.sizeQuantities ?? rollSizeQuantities(roll.allocation)

export const cellQuantity = (value: string | undefined) => Math.max(0, Math.round(Number(value) || 0))

export const balancedBatchTargets = (total: number, count: number) => {
  const base = Math.floor(total / count)
  const remainder = total % count
  return Array.from({ length: count }, (_, index) => base + (index < remainder ? 1 : 0))
}

function allocateWholeSources(sources: { key: string; qty: number }[], count: number): AllocationMatrix {
  const loads: number[] = Array(count).fill(0)
  const matrix: AllocationMatrix = Object.fromEntries(sources.map(({ key }) => [key, Array(count).fill('0')]))
  for (const { key, qty } of sources.sort((a, b) => b.qty - a.qty)) {
    const lightest = loads.reduce((best, load, index) => load < loads[best] ? index : best, 0)
    matrix[key][lightest] = String(qty)
    loads[lightest] += qty
  }
  return matrix
}

function createRollAllocationMatrix(rolls: FabricRoll[], count: number): AllocationMatrix {
  return allocateWholeSources(rolls.map(roll => ({
    key: roll.id,
    qty: quantitiesForRoll(roll).reduce((sum, qty) => sum + qty, 0),
  })), count)
}

export function createSizeAllocationMatrix(sizeTotals: QtyTuple, count: number, sizeNames: readonly string[]=cuttingSizes): AllocationMatrix {
  const sources = sizeNames.map((size, index) => ({ key: size, qty: sizeTotals[index] }))
  return allocateWholeSources(sources, Math.max(1, count))
}

export function createRollBatchSizeMatrix(rolls: FabricRoll[], count: number): RollBatchSizeMatrix {
  const wholeRollPlan = createRollAllocationMatrix(rolls, count)
  return Object.fromEntries(rolls.map((roll) => {
    const assignedBatch = (wholeRollPlan[roll.id] ?? []).findIndex((value) => cellQuantity(value) > 0)
    const sourceSizes = quantitiesForRoll(roll)
    return [roll.id, Array.from({ length: count }, (_, batchIndex) => batchIndex === assignedBatch ? sourceSizes.map(String) : sourceSizes.map(()=>'0'))]
  }))
}

export function createEmptyRollBatchSizeMatrix(rolls: FabricRoll[], count: number): RollBatchSizeMatrix {
  const safeCount = Math.max(1, count)
  return Object.fromEntries(rolls.map((roll) => [roll.id, Array.from({ length: safeCount }, () => quantitiesForRoll(roll).map(()=>'0'))]))
}

export const fabricRollCatalog: FabricRoll[] = [
  { id:'LCY-001',sequence:1,supplier:'Sinaran',material:'Lucy',yards:101.5,receivedAt:'25 Agu 2026',allocation:[13,13,12,11,10,10] },
  { id:'LCY-002',sequence:2,supplier:'Sinaran',material:'Lucy',yards:108.5,receivedAt:'25 Agu 2026',allocation:[13,13,12,12,12,12] },
  { id:'LCY-003',sequence:3,supplier:'Sinaran',material:'Lucy',yards:104,receivedAt:'25 Agu 2026',allocation:[11,11,12,12,12,12] },
  { id:'LCY-004',sequence:4,supplier:'Sinaran',material:'Lucy',yards:109.5,receivedAt:'25 Agu 2026',allocation:[13,13,12,12,12,12] },
  { id:'LCY-005',sequence:5,supplier:'Sinaran',material:'Lucy',yards:140,receivedAt:'25 Agu 2026',allocation:[15,15,16,16,16,16] },
  { id:'LCY-006',sequence:6,supplier:'Sinaran',material:'Lucy',yards:121.5,receivedAt:'25 Agu 2026',allocation:[15,15,13,13,13,13] },
  { id:'LCY-007',sequence:7,supplier:'Sinaran',material:'Lucy',yards:131.5,receivedAt:'25 Agu 2026',allocation:[14,14,15,15,15,15] },
  { id:'LCY-008',sequence:8,supplier:'Sinaran',material:'Lucy',yards:96.5,receivedAt:'25 Agu 2026',allocation:[10,10,11,11,11,11] },
  { id:'LCY-009',sequence:9,supplier:'Sinaran',material:'Lucy',yards:90,receivedAt:'25 Agu 2026',allocation:[11,10,10,10,10,10] },
  { id:'LCY-010',sequence:10,supplier:'Sinaran',material:'Lucy',yards:119,receivedAt:'26 Agu 2026',allocation:[0,0,0,0,0,0] },
  { id:'ZDK-011',sequence:11,supplier:'Sumber Cahaya',material:'Zodiak KW',yards:103,receivedAt:'25 Agu 2026',allocation:[0,0,0,0,0,0] },
  { id:'ZDK-012',sequence:12,supplier:'Sumber Cahaya',material:'Zodiak KW',yards:98,receivedAt:'25 Agu 2026',allocation:[0,0,0,0,0,0] },
]

export const fabricRollSuppliers=Array.from(new Set(fabricRollCatalog.map((roll)=>roll.supplier)))

export const fabricRollMaterials=Array.from(new Set(fabricRollCatalog.map((roll)=>roll.material)))
