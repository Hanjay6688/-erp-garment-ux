export const browseText=(value:string)=>value.normalize('NFKD').replace(/\p{M}/gu,'').toLocaleLowerCase('id').trim()
const compact=(value:string)=>value.replace(/[^\p{L}\p{N}]/gu,'')
type BrowseField = string | number | null | undefined
export const isPieceUnit = (unit: string) => unit.trim().toLowerCase() === 'pcs'

export function browseMatch(query:string,...values:BrowseField[]){
  const terms=browseText(query).split(/\s+/).filter(Boolean)
  const fields=values.filter(v=>v!=null).map(v=>browseText(String(v)))
  return terms.every(term=>fields.some(field=>field.includes(term)||(compact(term).length>0&&compact(field).includes(compact(term)))))
}

export function browseMatchPieces(query: string, quantities: readonly number[], ...fields: BrowseField[]) {
  const terms = browseText(query).replaceAll('−', '-')
    .replace(/(^|\s)([+-]?\d+(?:\.\d{3})*)\s+(pcs|potong)(?=\s|$)/g, '$1$2$3')
    .split(/\s+/).filter(Boolean)
  return terms.every(term => {
    const amount = /^([+-]?)(\d+(?:\.\d{3})*)(pcs|potong)?$/.exec(term)
    if (amount) {
      const [, sign, digits, unit] = amount
      const value = Number(digits.replaceAll('.', ''))
      const matches = quantities.some(quantity =>
        sign === '-' ? quantity === -value : sign === '+' ? quantity === value : Math.abs(quantity) === value)
      if (matches || unit) return matches
    }
    return browseMatch(term, ...fields)
  })
}
