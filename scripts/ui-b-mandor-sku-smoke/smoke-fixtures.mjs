import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {stripTypeScriptTypes} from 'node:module'
import {shopId, shopPayroll, shopMandor, shopSale, shopWorkspace} from './sku/tests/fixtures/mandorShop.ts'

const read=path=>readFileSync(new URL(path,import.meta.url),'utf8')
export function slice(text,start,end){
 const a=text.indexOf(start),b=text.indexOf(end,a+start.length)
 assert(a>=0&&b>a,`SOURCE_ANCHOR_MISSING ${start} -> ${end}`)
 return text.slice(a,b)
}
const evaluate=(src,names)=>new Function(stripTypeScriptTypes(src)+`\nreturn {${names}}`)()
const payrollTest=read('./sku/src/ConnectedPayrollPage.dom.test.tsx')
const payrollFixture=evaluate(slice(payrollTest,"const id='11111111",'let root:Root')+slice(payrollTest,'function installmentSource','function server()'), 'h,work,payload,installmentSource')
const skuTest=read('./sku/src/ConnectedSkuConversion.dom.test.tsx')
const skuFixture=evaluate(slice(skuTest,'const u =','let root:')+'\nlet available=9;\n'+slice(skuTest,'function workspace','const ok =')+slice(skuTest,'  const one =','  let current:'),'u,source,targets,workspace,detail,one,two,other')
const {u,source,targets,one,two,other}=skuFixture
export const mandor={payroll_id:shopPayroll,payroll_number:'PAY-EPI-W2',sale_id:shopSale,sale_number:'INV-EPI-01'}
export const sku={groups:[one,two],group_labels:{[one.id]:one,[two.id]:two},source:source.product_id,target:targets[0].id,other:targets[1].id,location:source.location_id,
 products:{source, target:{...targets[0],brand:targets[0].brand_name},other:targets[1]},physical_local:'2026-10-20T07:00'}
const header={...payrollFixture.h,id:shopPayroll,payroll_number:mandor.payroll_number,contractor_id:shopMandor,contractor_name:'Epi',
 period_start:'2026-11-09',period_end:'2026-11-15',labor_total:'2000000.00',net_payable:'2000000.00'}
const work=payrollFixture.work.map((row,i)=>({...row,rate:i?'500000.00':'1000000.00',amount:'1000000.00'}))
const emptyPage={rows:[],total:'0',offset:0,limit:25,next_offset:null}

export function createFixture(kind,role){
 const authId=shopId(90),permissions=kind==='mandor'
  ?['finance.payroll.view','finance.payroll.approve','finance.ar.view']
  :['master.product.view','master.product.manage','warehouse.brand_conversion.view','warehouse.brand_conversion.post','warehouse.brand_conversion.reverse','finance.hpp.view']
 const user={id:authId,aud:'authenticated',role:'authenticated',email:'browser-fixture@example.invalid',app_metadata:{provider:'email'},user_metadata:{},created_at:'2026-10-20T00:00:00Z'}
 const jwt='eyJhbGciOiJub25lIn0.'+Buffer.from(JSON.stringify({sub:authId,role:'authenticated',exp:Math.floor(Date.now()/1000)+3600})).toString('base64url')+'.fixture'
 const access={allowed:true,profile:{id:shopId(91),auth_user_id:authId,full_name:'Aktor fixture browser',role_id:shopId(92),role_code:role,role_name:role,is_active:true,row_version:1,role_row_version:1},permissions,
  external_portals:{mandor:'NOT CONNECTED',laundry:'NOT CONNECTED',store:'NOT CONNECTED'}}
 let pair=false
 const state={reserved:false,requests:[],unknown:[],simulatedWrites:[]}
 function rpc(name,args){
  state.requests.push({name,section:args.p_section??null,action:args.p_action??null})
  if(name==='erp_get_my_access_v1')return access
  if(kind==='mandor'){
   if(name==='erp_cp7_get_sales_v1'){
    assert.equal(args.p_query.sale_id,null)
    return {contract_version:'cp7.sales-workspace.v1',read_at:'2026-11-06T00:00:00Z',financial_captured:true,read_only:true,page:emptyPage,detail:null}
   }
   if(name==='erp_cp7_get_payroll_workspace_v1'){
    const section=args.p_section
    const rows=section==='PAYROLLS'?[header]:section==='WORK'?work:[]
    return {...payrollFixture.payload(section,header,rows),capabilities:{approve:true,pay:false}}
   }
   if(name==='erp_cp7_get_mandor_shop_payroll_v1'){
    assert.equal(args.p_payroll,shopPayroll)
    return shopWorkspace(state.reserved)
   }
   if(name==='erp_cp7_get_payroll_installments_v1')return payrollFixture.installmentSource(header,false)
  } else {
   if(name==='erp_get_sku_workspace_v1'){
    const f=args.p_filters,g=f.query===two.sku?two:one
    const current=pair?(g.id===one.id?two:one):null
    return {at:'2026-10-20T00:00:00Z',page:1,page_size:50,groups_total:1,products_total:0,can_edit:false,products:[],selected_products:[],related_groups:[],lookups:null,legacy_basis:null,
     groups:[{...g,brand_id:u(31),model_id:u(41),color_name:'Blue',revision:'1',effective_from:'2026-01-01T00:00:00Z',members:g.members.map((m,i)=>({...m,size_id:u(51+i)})),settings:null,counterpart:current}],
     pairing:{revision:pair?'revision-two':'revision-one',source:f.pair_source_id?g:null,current,options:f.pair_query?[one,two,other].filter(x=>x.sku===f.pair_query):[one,two,other].filter(x=>x.id!==g.id),total:3,page:1,page_size:50,can_edit:true}}
   }
   if(name==='erp_save_sku_action_v1'){
    assert.equal(args.p_action,'SAVE_PAIR')
    assert.equal(args.p_payload.source_group_id,one.id)
    assert.equal(args.p_payload.target_group_id,two.id)
    assert.equal(args.p_payload.expected_version,'revision-one')
    assert.match(args.p_client_request_id,/^[0-9a-f-]{36}$/i)
    state.simulatedWrites.push(name);pair=true
    return {...args.p_payload,request_id:args.p_client_request_id,action:'SAVE_PAIR',status:'SAVED',revision:'revision-two',removed:[]}
   }
   if(name==='erp_get_product_conversion_workspace_v1'){
    const f=args.p_filters
    if(f.preview)return {preview:skuFixture.detail(f.preview)}
    const out=skuFixture.workspace(f)
    if(f.target_query){out.targets=out.targets.filter(x=>x.sku===f.target_query);out.targets_total=out.targets.length}
    return out
   }
  }
  state.unknown.push(name)
  throw Error('UNDECLARED_FIXTURE_RPC '+name)
 }
 return {state,rpc,user,session:{access_token:jwt,token_type:'bearer',expires_in:3600,refresh_token:'fixture',user},emptyPage}
}
