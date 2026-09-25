import baseCatalog from './initialImportCatalog.json'
import bbCatalog from './initialImportCatalogBB.json'
import bcCatalog from './initialImportCatalogBC.json'

type CatalogSpec = { label: string; required: readonly string[]; fields: Record<string, string> }
const { _extend: bbExtensions, ...bbEntities } = bbCatalog
type Entity = keyof typeof baseCatalog | keyof typeof bbEntities | keyof typeof bcCatalog

/** The server's catalog (BB, BC): the AP catalog, the BB and BC files, and the BB fields added to AP files after their own fields. */
function mergeCatalog(): Record<Entity, CatalogSpec> {
  const merged: Record<string, CatalogSpec> = {}
  for (const [key, spec] of Object.entries(baseCatalog) as [string, CatalogSpec][]) merged[key] = { ...spec, fields: { ...spec.fields } }
  for (const [key, spec] of [...Object.entries(bbEntities), ...Object.entries(bcCatalog)] as [string, CatalogSpec][]) {
    if (key in merged) throw new Error(`Katalog impor ganda: ${key}`)
    merged[key] = spec
  }
  for (const [key, more] of Object.entries(bbExtensions) as [string, { fields: Record<string, string> }][]) {
    if (!(key in merged) || Object.keys(more.fields).some(field => field in merged[key].fields)) throw new Error(`Perluasan katalog impor tidak valid: ${key}`)
    merged[key].fields = { ...merged[key].fields, ...more.fields }
  }
  return merged as Record<Entity, CatalogSpec>
}
const catalog = mergeCatalog()

export { catalog as initialImportCatalog }
export type InitialImportEntity = Entity
export type InitialImportRow = { source_row_no: number; payload: Record<string, string> }
export const MAX_IMPORT_BYTES = 5 * 1024 * 1024
export const MAX_IMPORT_ROWS = 5000

type CsvRecord = { line: number; cells: string[] }
function records(text: string, delimiter: string): CsvRecord[] {
  const result: CsvRecord[] = []
  let cells: string[] = [], cell = '', quoted = false, closed = false, line = 1, start = 1
  const field = () => { cells.push(cell); cell = ''; closed = false }
  const row = () => {
    field()
    if (cells.some((value) => value.trim() !== '')) result.push({ line: start, cells })
    cells = []; start = line + 1
    if (result.length > MAX_IMPORT_ROWS + 1) throw new Error(`Maksimal ${MAX_IMPORT_ROWS} baris per file.`)
  }
  for (let i = 0; i < text.length; i++) {
    const c = text[i]
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') { cell += '"'; i++ } else { quoted = false; closed = true }
      } else {
        cell += c
        if (c === '\n' || c === '\r' && text[i + 1] !== '\n') line++
      }
    } else if (c === delimiter) field()
    else if (c === '\n' || c === '\r') { row(); if (c === '\r' && text[i + 1] === '\n') i++; line++ }
    else if (c === '"' && cell === '' && !closed) quoted = true
    else {
      if (c === '"' || closed) throw new Error(`Baris ${line}: tanda kutip atau pemisah kolom tidak lengkap.`)
      cell += c
    }
  }
  if (quoted) throw new Error(`Baris ${start}: tanda kutip penutup belum ada.`)
  if (cell !== '' || cells.length || closed) row()
  return result
}

const headerKey = (value: string) => value.trim().toLocaleLowerCase('id-ID')
function mapHeaders(record: CsvRecord, entity: InitialImportEntity) {
  const spec = catalog[entity]
  const aliases = new Map(Object.entries(spec.fields).flatMap(([key, label]) => [[headerKey(key), key], [headerKey(label), key]]))
  const keys = record.cells.map((cell) => {
    const key = aliases.get(headerKey(cell))
    if (!key) throw new Error(`Baris ${record.line}: kolom “${cell}” tidak dikenal. Gunakan template ${spec.label}.`)
    return key
  })
  if (new Set(keys).size !== keys.length) throw new Error(`Baris ${record.line}: ada kolom yang ditulis dua kali.`)
  const missing = spec.required.filter((key) => !keys.includes(key))
  if (missing.length) throw new Error(`Kolom wajib belum ada: ${missing.map((key) => spec.fields[key]).join(', ')}.`)
  return keys
}

/** Monetary and quantity cells remain decimal text through the entire transport. */
export function parseInitialImportCsv(source: string, entity: InitialImportEntity): InitialImportRow[] {
  if (new TextEncoder().encode(source).length > MAX_IMPORT_BYTES) throw new Error('Ukuran file maksimal 5 MB.')
  const text = source.replace(/^﻿/, '')
  if (/[\u0000-\u0008\u000B\u000C\u000E-\u001F�]/u.test(text)) throw new Error('File memuat karakter rusak. Simpan ulang sebagai CSV UTF-8 dari Excel.')
  const candidates: { rows: CsvRecord[]; keys: string[] }[] = []
  const failures: Error[] = []
  for (const delimiter of [',', ';', '\t']) {
    try {
      const rows = records(text, delimiter)
      if (!rows.length) throw new Error('File kosong.')
      const keys = mapHeaders(rows[0], entity)
      if (rows.some((row) => row.cells.length !== keys.length)) {
        const row = rows.find((row) => row.cells.length !== keys.length)!
        throw new Error(`Baris ${row.line}: jumlah kolom ${row.cells.length}; seharusnya ${keys.length}. Angka desimal dengan koma harus diapit tanda kutip.`)
      }
      candidates.push({ rows, keys })
    } catch (error) { failures.push(error instanceof Error ? error : new Error('File tidak dapat dibaca.')) }
  }
  if (!candidates.length) throw failures[0]
  // A one-column file can have several equivalent delimiter interpretations.
  const first = JSON.stringify(candidates[0])
  if (candidates.some((candidate) => JSON.stringify(candidate) !== first)) throw new Error('Pemisah kolom ambigu. Simpan ulang memakai template.')
  const { rows, keys } = candidates[0]
  if (rows.length < 2) throw new Error('Template belum berisi data.')
  return rows.slice(1).map((row) => ({
    source_row_no: row.line,
    payload: Object.fromEntries(keys.map((key, i) => [key, row.cells[i].trim()])),
  }))
}

export async function readInitialImportFile(file: File, entity: InitialImportEntity) {
  if (file.size > MAX_IMPORT_BYTES) throw new Error('Ukuran file maksimal 5 MB.')
  let text: string
  try { text = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer()) }
  catch { throw new Error('File harus berformat CSV UTF-8. Pilih “CSV UTF-8” saat menyimpan dari Excel.') }
  return parseInitialImportCsv(text, entity)
}

export function initialImportTemplate(entity: InitialImportEntity) {
  return '﻿' + Object.values(catalog[entity].fields).map((label) => `"${label.replaceAll('"', '""')}"`).join(',') + '\r\n'
}
