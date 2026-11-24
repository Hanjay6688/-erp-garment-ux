export const browseText=(value:string)=>value.normalize('NFKD').replace(/\p{M}/gu,'').toLocaleLowerCase('id').trim()
const compact=(value:string)=>value.replace(/[^\p{L}\p{N}]/gu,'')
export function browseMatch(query:string,...values:(string|number|null|undefined)[]){
  const terms=browseText(query).split(/\s+/).filter(Boolean)
  const fields=values.filter(v=>v!=null).map(v=>browseText(String(v)))
  return terms.every(term=>fields.some(field=>field.includes(term)||(compact(term).length>0&&compact(field).includes(compact(term)))))
}
