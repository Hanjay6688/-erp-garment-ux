import type { PocketUnit } from './pocketReceipts'

export type PocketBenchmarks = Partial<Record<PocketUnit, number>>
export type PocketMaterial = { id: string; name: string; factory: string; supplier: string; benchmarks?: PocketBenchmarks }

export const pocketMasterPath = '/master/kain-benchmark/?bagian=kain-kantong'
const pocketMasterKey = 'erp.demo.pocket.materials.v1'
const startingMaterials: PocketMaterial[] = [
  { id: 'Kain kantong putih', name: 'Kain kantong putih', factory: '', supplier: 'Sinaran', benchmarks: { yd: 9000 } },
  { id: 'Kain kantong hitam', name: 'Kain kantong hitam', factory: '', supplier: 'Sinaran', benchmarks: { yd: 10500 } },
]

export function readPocketMaterials(): PocketMaterial[] {
  try {
    const rows: PocketMaterial[] = JSON.parse(sessionStorage.getItem(pocketMasterKey) ?? 'null') ?? startingMaterials
    return rows.map(item => ({ ...item, benchmarks: item.benchmarks ?? startingMaterials.find(seed => seed.id === item.id)?.benchmarks ?? {} }))
  }
  catch { return startingMaterials }
}

export const pocketMaterialLabel = (item: PocketMaterial) => item.factory ? `${item.name} · ${item.factory}` : item.name

export function savePocketMaterial(id: string | null, input: Omit<PocketMaterial, 'id'>) {
  const fields = { name: input.name.trim(), factory: input.factory.trim(), supplier: input.supplier.trim(), benchmarks: input.benchmarks ?? {} }
  if (!fields.name || !fields.factory) throw new Error('Isi nama bahan dan pabrik asal.')
  if (Object.values(fields.benchmarks).some(rate => !Number.isFinite(rate) || rate < 0 || !Number.isSafeInteger(Math.round(rate * 100)))) {
    throw new Error('Harga acuan harus berupa angka rupiah yang sah.')
  }
  const rows = readPocketMaterials()
  const same = (a: string, b: string) => a.localeCompare(b, 'id', { sensitivity: 'accent' }) === 0
  if (rows.some(item => item.id !== id && same(item.name, fields.name) && same(item.factory, fields.factory))) {
    throw new Error('Bahan dengan nama dan pabrik ini sudah ada.')
  }
  const item = { id: id ?? crypto.randomUUID(), ...fields }
  const next = id ? rows.map(row => row.id === id ? item : row) : [...rows, item]
  sessionStorage.setItem(pocketMasterKey, JSON.stringify(next))
  return item
}
