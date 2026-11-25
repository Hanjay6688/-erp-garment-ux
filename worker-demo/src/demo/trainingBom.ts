export type BomLine={id:string;category:string;quantity:number;uom:string}
export const productStore='erp.demo.master-products.records.v1'
export const defaultBom=(prefix:string):BomLine[]=>[
  {id:`${prefix}-button`,category:'Kancing',quantity:1,uom:'pcs'},
  {id:`${prefix}-zipper`,category:'Sleting',quantity:1,uom:'pcs'},
  {id:`${prefix}-hang-tag`,category:'Hang Tag',quantity:1,uom:'pcs'},
]
const trainingKeys=['Vivo 73001','Vivo 73002','Widie 73006']
export function trainingBom(sku:string,seedOnly=false) {
  const key=sku.replace(/\s*·\s*/,' ').split(' ').slice(0,2).join(' ')
  const records: {code:string;values:{brand:string};bom?:BomLine[]}[] = seedOnly||typeof sessionStorage==='undefined'?[]:JSON.parse(sessionStorage.getItem(productStore)??'[]')
  const master=records.find(row=>`${row.values.brand} ${row.code}`===key)
  return master?master.bom??[]:trainingKeys.includes(key)?defaultBom(key.split(' ')[1]):[]
}
