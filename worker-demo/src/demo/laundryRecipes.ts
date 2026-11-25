import type { Article } from './planner/model'
import { laundryProcesses } from './laundryModel'
import { laundryVendorNames } from './sewingModel'
import { dayOk } from './warehouseDay'

export const laundryRecipePath = '/master/supplier-vendor/?bagian=laundry'
const masterKey = 'erp.demo.laundry-colour-master.v2'
const legacyKey = 'erp.demo.laundry-recipes.v1'

export type LaundryInstructions = { colourProcess: string; colour: string; service: string }
export type LaundryColourType = { id: string; vendor: string; name: string; note: string; benchmark?: number }
export type LaundryColourLink = { vendor: string; sku: string; from: string; typeId: string; colour: string; service: string; removed?: boolean }
export type LaundryColourMaster = { types: LaundryColourType[]; links: LaundryColourLink[] }
export const emptyInstructions: LaundryInstructions = { colourProcess: '', colour: '', service: '' }

const types: LaundryColourType[] = [
  { id: 'intan-celup', vendor: 'Laundry Intan', name: 'Celup', note: '' },
  { id: 'intan-celup-ulang', vendor: 'Laundry Intan', name: 'Celup ulang', note: '' },
  { id: 'berkah-tinting', vendor: 'Laundry Berkah', name: 'Tinting', note: '' },
  { id: 'berkah-celup', vendor: 'Laundry Berkah', name: 'Celup', note: '' },
]

const sampleLinks: LaundryColourLink[] = [
  { vendor: 'Laundry Intan', sku: 'Widie 66001', from: '2026-08-01', typeId: 'intan-celup', colour: 'Biru muda', service: 'Bio Wash' },
  { vendor: 'Laundry Berkah', sku: 'Widie 66001', from: '2026-08-01', typeId: 'berkah-tinting', colour: 'Biru muda', service: 'Stone Wash' },
]

const nameKey = (name: string) => name.trim().replace(/\s+/g, ' ').toLocaleLowerCase('id-ID')

export function readLaundryColourMaster(): LaundryColourMaster {
  const saved = localStorage.getItem(masterKey)
  if (saved) return JSON.parse(saved)
  const legacy = sessionStorage.getItem(legacyKey)
  if (!legacy) return { types, links: sampleLinks }
  const oldRows = JSON.parse(legacy) as Array<LaundryInstructions & { vendor: string; sku: string; from: string }>
  const catalogue = [...types]
  const links = oldRows.map(({ colourProcess, ...link }) => {
    let typeId = ''
    if (colourProcess.trim()) {
      let type = catalogue.find(item => item.vendor === link.vendor && nameKey(item.name) === nameKey(colourProcess))
      if (!type) {
        type = { id: 'legacy-' + catalogue.length, vendor: link.vendor, name: colourProcess.trim(), note: '' }
        catalogue.push(type)
      }
      typeId = type.id
    }
    return { ...link, typeId }
  })
  return { types: catalogue, links }
}

function storeMaster(master: LaundryColourMaster) {
  localStorage.setItem(masterKey, JSON.stringify(master))
  return master
}

export function saveLaundryColourType(draft: LaundryColourType) {
  const master = readLaundryColourMaster()
  const name = draft.name.trim().replace(/\s+/g, ' ')
  if (!laundryVendorNames.includes(draft.vendor) || !name || name.length > 100) throw Error('Isi nama jenis pewarnaan untuk laundry ini.')
  if (draft.benchmark !== undefined && (!Number.isSafeInteger(draft.benchmark) || draft.benchmark < 0)) throw Error('Isi harga acuan dalam rupiah per pcs.')
  const existing = master.types.find(type => type.id === draft.id)
  if (draft.id && (!existing || existing.vendor !== draft.vendor)) throw Error('Jenis pewarnaan sudah berubah. Pilih lagi dari katalog.')
  if (master.types.some(type => type.vendor === draft.vendor && type.id !== draft.id && nameKey(type.name) === nameKey(name))) {
    throw Error('Jenis pewarnaan dengan nama ini sudah ada di laundry tersebut.')
  }
  const type = { ...draft, id: draft.id || crypto.randomUUID(), name, note: draft.note.trim() }
  const nextTypes = existing ? master.types.map(item => item.id === type.id ? type : item) : [...master.types, type]
  return { master: storeMaster({ ...master, types: nextTypes }), type }
}

export function saveLaundryColourLink(draft: LaundryColourLink, previousTypeId?: string) {
  const master = readLaundryColourMaster()
  if (!draft.sku || !dayOk(draft.from) || !master.types.some(type => type.id === draft.typeId && type.vendor === draft.vendor)) {
    throw Error('Pilih jenis pewarnaan dari laundry ini, SKU, dan tanggal mulai yang sah.')
  }
  if (draft.service && !laundryProcesses.includes(draft.service)) throw Error('Pilih layanan laundry yang tersedia.')
  const sameVersion = (link: LaundryColourLink) => link.vendor === draft.vendor && link.sku === draft.sku && link.from === draft.from
  const prior = master.links.find(sameVersion)
  if (prior && !prior.removed && prior.typeId && prior.typeId !== draft.typeId && prior.typeId !== previousTypeId) {
    throw Error('SKU sudah punya default lain pada tanggal ini. Edit default itu atau pilih tanggal berikutnya.')
  }
  return storeMaster({ ...master, links: [{ ...draft, colour: draft.colour.trim() }, ...master.links.filter(link => !sameVersion(link))] })
}

export function removeLaundryColourDefault(link: LaundryColourLink, from: string) {
  const master = readLaundryColourMaster()
  if (!dayOk(from) || from <= link.from) throw Error('Pilih tanggal setelah awal berlakunya default.')
  const related = master.links.filter(item => item.vendor === link.vendor && item.sku === link.sku && item.from <= from)
    .sort((a, b) => b.from.localeCompare(a.from))
  if (!related[0] || related[0].typeId !== link.typeId || related[0].removed) throw Error('SKU sudah memakai default lain pada tanggal itu.')
  return storeMaster({ ...master, links: [{ vendor: link.vendor, sku: link.sku, from, typeId: '', colour: '', service: '', removed: true }, ...master.links] })
}

export function instructionsFor(master: LaundryColourMaster, sku: Article | undefined, vendor: string, physicalTime: string) {
  if (!sku) return { ...emptyInstructions, source: '', typeId: '' }
  const day = physicalTime.slice(0, 10)
  const link = master.links.filter(item => item.vendor === vendor && item.sku === sku.key && item.from <= day)
    .sort((a, b) => b.from.localeCompare(a.from))[0]
  if (link && !link.removed) {
    const type = master.types.find(item => item.id === link.typeId && item.vendor === vendor)
    return { colourProcess: type?.name ?? '', typeId: type?.id ?? '', colour: link.colour || sku.colour, service: link.service,
      source: type ? `Default ${sku.key} · ${vendor} · berlaku ${link.from}` : 'Warna dari Master SKU' }
  }
  return { ...emptyInstructions, typeId: '', colour: sku.colour, source: 'Warna dari Master SKU · pilih jenis pewarnaan bila perlu' }
}
