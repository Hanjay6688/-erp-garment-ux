import type { Article } from './planner/model'
import { laundryPhysicalTime, laundryProcesses, type LaundryDelivery } from './laundryModel'
import { laundryVendorNames } from './sewingModel'
import { dayOk } from './warehouseDay'

export const colourProcesses = ['Celup', 'Celup ulang', 'Tinting']
export const laundryRecipePath = '/master/supplier-vendor/?bagian=laundry'
const recipeKey = 'erp.demo.laundry-recipes.v1'

export type LaundryInstructions = { colourProcess: string; colour: string; service: string }
export type LaundryRecipe = LaundryInstructions & { vendor: string; sku: string; from: string }
export const emptyInstructions: LaundryInstructions = { colourProcess: '', colour: '', service: '' }

const samples: LaundryRecipe[] = [
  { vendor: 'Laundry Intan', sku: 'Widie 66001', from: '2026-08-01', colourProcess: 'Celup', colour: 'Biru muda', service: 'Bio Wash' },
  { vendor: 'Laundry Berkah', sku: 'Widie 66001', from: '2026-08-01', colourProcess: 'Tinting', colour: 'Biru muda', service: 'Stone Wash' },
]

export function readLaundryRecipes(): LaundryRecipe[] {
  return JSON.parse(sessionStorage.getItem(recipeKey) ?? 'null') ?? samples
}

export function saveLaundryRecipe(draft: LaundryRecipe) {
  const record = {
    ...draft, colourProcess: draft.colourProcess.trim(), colour: draft.colour.trim(),
  }
  if (!laundryVendorNames.includes(record.vendor) || !record.sku || !dayOk(record.from)) {
    throw Error('Pilih laundry, SKU, dan tanggal mulai yang sah.')
  }
  if (record.service && !laundryProcesses.includes(record.service)) throw Error('Pilih layanan laundry yang tersedia.')
  if (!record.colourProcess && !record.colour && !record.service) throw Error('Isi setidaknya satu instruksi laundry.')
  const rows = readLaundryRecipes()
  const same = (old: LaundryRecipe) => old.vendor === record.vendor && old.sku === record.sku && old.from === record.from
  const next = [record, ...rows.filter(old => !same(old))]
  sessionStorage.setItem(recipeKey, JSON.stringify(next))
  return next
}

export function instructionsFor(rows: LaundryRecipe[], deliveries: LaundryDelivery[], sku: Article | undefined, vendor: string, physicalTime: string) {
  if (!sku) return { ...emptyInstructions, source: '' }
  const day = physicalTime.slice(0, 10)
  const configured = rows.filter(r => r.vendor === vendor && r.sku === sku.key && r.from <= day)
    .sort((a, b) => b.from.localeCompare(a.from))[0]
  if (configured) return { ...configured, source: 'Master proses · ' + vendor + ' · berlaku ' + configured.from }
  const historical = deliveries.filter(d =>
    d.skuRef === sku.key && d.vendor === vendor && d.reversed < d.qty &&
    Boolean(d.targetColor || d.colourProcess || d.process) && Boolean(laundryPhysicalTime(d.sentAt)) && laundryPhysicalTime(d.sentAt) <= physicalTime
  ).sort((a, b) => laundryPhysicalTime(b.sentAt).localeCompare(laundryPhysicalTime(a.sentAt)))[0]
  if (historical) return {
    colourProcess: historical.colourProcess ?? '', colour: historical.targetColor ?? sku.colour,
    service: historical.process, source: 'Riwayat ' + vendor + ' · ' + historical.id,
  }
  return { ...emptyInstructions, colour: sku.colour, source: 'Warna dari Master SKU. Proses warna untuk laundry ini masih kosong.' }
}
