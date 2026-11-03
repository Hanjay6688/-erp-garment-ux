/* UI-only inputs derived from the existing connected-page DOM fixtures. */
export const ID='11111111-1111-4111-8111-111111111111'
export const ROW='22222222-2222-4222-8222-222222222222'
export const revision=(n:number)=>n.toString(16).padStart(64,'0')
export const states=['ready','long','empty','loading','error','pending','denied','revoked'] as const
export type State=typeof states[number]
export function pocketData(state:State){
  const long=state==='long'
  return {rolls:state==='empty'?[]:[{id:ID,material_id:ID,location_id:ID,roll_number:'KKT-FIXTURE-001',material_name:long?'Kain kantong universal untuk celana produksi — bahan uji panjang agar seluruh identitas tetap terbaca':'Kain kantong universal',unit_code:'YD',location_name:'Gudang kain • fixture UI',qty:'20.000000',revision:revision(1)}],roll_count:state==='empty'?0:1,
    materials:state==='empty'?[]:[{id:ID,sku:'KANTONG-FIXTURE',name:'Kain kantong khusus — data contoh'}],
    history:state==='empty'?[]:[{id:ROW,number:'KKT-FIXTURE-0001',status:'POSTED',row_version:'9007199254740993',date:'2026-09-21',reason:long?'Pemakaian bersama dengan keterangan panjang untuk pemeriksaan tampilan pada layar sempit':'Pemakaian bersama • fixture',roll_id:ID,roll_number:'KKT-FIXTURE-001',material_name:'Kain kantong universal',unit_code:'YD',issued_quantity:'5.000000',current_cost:'11.25',cost_policy:'PERIOD_EXPENSE'}],
    periods:state==='empty'?[]:[{id:ROW,period_start:'2026-09-01',period_end:'2026-09-20',status:'ACTIVE',reason:'Alokasi contoh UI',quantity:'10',original_amount:'11.25',current_amount:'11.25',per_piece:'1.125000',revision:revision(8)}]}
}
export function importData(state:State,selected:boolean){
  return {recent:state==='empty'?[]:[{id:ID,batch_code:'AWAL-FIXTURE-UI',status:'DRAFT'}],batch:!selected||state==='empty'?null:{id:ID,code:'AWAL-FIXTURE-UI',status:'DRAFT',cutover_at:'2026-09-20T00:00:00+07:00',revision:revision(1),rows:Array.from({length:state==='long'?12:2},(_,i)=>({id:`22222222-2222-4222-8222-${String(i+1).padStart(12,'0')}`,entity:'MATERIAL',source_row_no:i+2,payload:{material_sku:'KAIN-'+(i+1),material_name:state==='long'?'Kain universal panjang untuk pengecekan kolom, identitas dan pembacaan rincian sumber':'Kain fixture '+(i+1),material_type:'FABRIC',unit_code:'YD',accessory_category_code:'',is_active:'true'},validation_status:i?'PENDING':'VALID',errors:[],applied:false})),cash_advances:[],advance_payrolls:[],prepayments:[],prepayment_cash_accounts:[],production_sources:[]}}
}
const current={version:1,cutover_date:'2026-09-01',previous_date:null,reason:'Tanggal tetap data fixture UI',set_at:'2026-09-01T00:00:00+07:00',set_by:'Owner fixture'}
export const cutoverData={contract_version:'cp7.cutover-workspace.v1',today:'2026-11-03',can_set:false,version:1,current,history:[current],earliest_operational:null,earliest_import:{date:'2026-09-20',batch_code:'AWAL-FIXTURE-UI'},latest_allowed:'2026-09-20',business_DML:false}
export const periodPreview={period_start:'2026-09-01',period_end:'2026-09-20',amount:'11.25',quantity:'10',per_piece:'1.125000',source_count:1,blocked:false,can_post:true,revision:revision(8)}
