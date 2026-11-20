import fixture from './nativeAnalysisStandin.json'

// Synthetic receiver input, never a Native installation/stock oracle.
export function materialAnalysisStandin(value=fixture){
 const x=structuredClone(value),row=x.analysis.material_needs[0],category='00000000-0000-4000-8000-00000000b001'
 const refs=[...row.gross.refs,{kind:'erp.accessory_bom_versions',id:'00000000-0000-4000-8000-00000000b002',revision:'a'.repeat(64)},
  {kind:'erp.accessory_bom_items',id:'00000000-0000-4000-8000-00000000b003',revision:'b'.repeat(64)},
  {kind:'erp.accessory_categories',id:category,revision:'1'}]
 const unknown={state:'UNKNOWN',unit:'PCS',reason:'SOURCE_INPUT_NOT_PROVEN',refs}
 Object.assign(row,{material_key:'ACCESSORY_CATEGORY:'+category,reason:'Kancing: kebutuhan BOM untuk rencana; pemasangan belum terbukti. Pengeluaran bukan pemasangan.',
  gross:{state:'ASSUMED',value:'186.000000',unit:'PCS',refs,assumption_ids:[x.analysis.assumptions[0].id]},
  installed_proven:structuredClone(unknown),unused_allocated_proven:structuredClone(unknown),additional_external:structuredClone(unknown)})
 return x
}
