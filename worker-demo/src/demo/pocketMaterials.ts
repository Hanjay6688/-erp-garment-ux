export type PocketMaterial = { id: string; name: string; factory: string; supplier: string }

export const pocketMasterPath = '/master/kain-benchmark/?bagian=kain-kantong'
const pocketMasterKey = 'erp.demo.pocket.materials.v1'
const startingMaterials: PocketMaterial[] = ['Kain kantong putih', 'Kain kantong hitam'].map(name => ({
  id: name, name, factory: '', supplier: 'Sinaran',
}))

export function readPocketMaterials(): PocketMaterial[] {
  try { return JSON.parse(sessionStorage.getItem(pocketMasterKey) ?? 'null') ?? startingMaterials }
  catch { return startingMaterials }
}

export const pocketMaterialLabel = (item: PocketMaterial) => item.factory ? `${item.name} · ${item.factory}` : item.name

export function savePocketMaterial(id: string | null, input: Omit<PocketMaterial, 'id'>) {
  const fields = { name: input.name.trim(), factory: input.factory.trim(), supplier: input.supplier.trim() }
  if (!fields.name || !fields.factory) throw new Error('Isi nama bahan dan pabrik asal.')
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
