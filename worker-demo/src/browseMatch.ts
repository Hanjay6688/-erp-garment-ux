export const browseText=(value:string)=>value.normalize('NFKD').replace(/\p{M}/gu,'').toLocaleLowerCase('id').trim()
const compact=(value:string)=>value.replace(/[^\p{L}\p{N}]/gu,'')
type BrowseField = string | number | null | undefined

export function browseMatch(query:string,...values:BrowseField[]){
  const terms=browseText(query).split(/\s+/).filter(Boolean)
  const fields=values.filter(v=>v!=null).map(v=>browseText(String(v)))
  return terms.every(term=>fields.some(field=>field.includes(term)||(compact(term).length>0&&compact(field).includes(compact(term)))))
}

export function browseMatchPieces(query: string, quantities: readonly number[], ...fields: BrowseField[]) {
  const terms = browseText(query).replace(/(^|\s)(\d+(?:\.\d{3})*)\s+(pcs|potong)(?=\s|$)/g, '$1$2$3').split(/\s+/)
  return terms.every(term => {
    const amount = /^(\d+(?:\.\d{3})*)(pcs|potong)?$/.exec(term)
    const matchesAmount = amount && quantities.includes(Number(amount[1].replaceAll('.', '')))
    return matchesAmount || (!amount?.[2] && browseMatch(term, ...fields))
  })
}
