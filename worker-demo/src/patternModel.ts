export type PatternRow = {
  id: string
  code: string
  revision: string
  name: string
  sort_order: number
  is_active: boolean
  row_version: number
  updated_at: string
  updated_by: string | null
  usage_count: number
}

export function parsePatternRows(value: unknown): PatternRow[] {
  const source = Array.isArray(value)
    ? value
    : value && typeof value === 'object' && !Array.isArray(value) && Array.isArray((value as Record<string, unknown>).rows)
      ? (value as { rows: unknown[] }).rows
      : null
  if (!source) throw new Error('Respons Master Pola tidak valid.')
  return source.map((row) => {
    if (!row || typeof row !== 'object' || Array.isArray(row)) throw new Error('Baris Master Pola tidak valid.')
    const item = row as Record<string, unknown>
    if (typeof item.id !== 'string' || typeof item.code !== 'string' || typeof item.name !== 'string') throw new Error('Identitas Pola tidak lengkap.')
    return {
      id: item.id,
      code: item.code,
      revision: typeof item.revision === 'string' ? item.revision : 'R1',
      name: item.name,
      sort_order: Number(item.sort_order),
      is_active: item.is_active === true,
      row_version: Number(item.row_version),
      updated_at: String(item.updated_at ?? ''),
      updated_by: typeof item.updated_by === 'string' ? item.updated_by : null,
      usage_count: Number(item.usage_count ?? 0),
    }
  })
}

export function sortPatternRows(rows: readonly PatternRow[]) {
  return [...rows].sort((a, b) => a.sort_order - b.sort_order || a.code.localeCompare(b.code) || a.revision.localeCompare(b.revision) || a.id.localeCompare(b.id))
}

export function parsePatternTotal(value: unknown, rows: readonly PatternRow[]) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return rows.length
  const total = Number((value as Record<string, unknown>).total)
  if (!Number.isSafeInteger(total) || total < 0) throw new Error('Total Master Pola tidak valid.')
  return total
}
