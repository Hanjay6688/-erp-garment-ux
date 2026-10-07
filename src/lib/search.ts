// Search that matches what the row shows: the query is split into words and
// every word must appear somewhere in the row's displayed fields, in any order
// ("siap laundry 225", "02b hitam", "bandung nisa").

export type SearchPart = string | number | null | undefined | false | readonly SearchPart[]

const flatten = (parts: readonly SearchPart[]): string[] => parts.flatMap((part) =>
  Array.isArray(part) ? flatten(part) : part === null || part === undefined || part === false ? [] : [String(part)])

export const normalizeSearch = (value: string) => value.toLocaleLowerCase('id-ID').normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, ' ').trim()

export function searchTokens(query: string): string[] {
  return normalizeSearch(query).split(' ').filter(Boolean)
}

export function matchesSearch(query: string, ...parts: SearchPart[]): boolean {
  const tokens = searchTokens(query)
  if (tokens.length === 0) return true
  const haystack = normalizeSearch(flatten(parts).join(' '))
  return tokens.every((token) => haystack.includes(token))
}

// Every value a list row is built from, as searchable text: strings as-is,
// numbers both raw and in id-ID format ("6480000" and "6.480.000"), nested
// arrays/objects (sizes, lines) included. Used together with the row's
// display labels so whatever a row shows can be found.
export function searchValues(value: unknown, depth = 0): string[] {
  if (value === null || value === undefined || depth > 4) return []
  if (typeof value === 'string') return [value]
  if (typeof value === 'number') return Number.isFinite(value) ? [String(value), value.toLocaleString('id-ID')] : []
  if (Array.isArray(value)) return value.flatMap((item) => searchValues(item, depth + 1))
  if (typeof value === 'object') return Object.values(value as Record<string, unknown>).flatMap((item) => searchValues(item, depth + 1))
  return []
}
