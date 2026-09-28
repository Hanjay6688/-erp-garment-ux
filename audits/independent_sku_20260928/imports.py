"""Independent consumer import cross-checks, after own oracle was frozen.
No writer/peer test script or fixture is executed.
"""
import native as n
from psycopg.types.json import Jsonb
import json,sys,copy
from decimal import Decimal as D
n.s.DSN=n.s.DSN.replace('/cp6_rollback','/cp6_sku_edges');n.OUT=n.ROOT/'audit-results'/'sku-import-consumers';n.OUT.mkdir(exist_ok=True)
f=json.loads((n.ROOT/'audit-results/sku-fixture.json').read_text());n.C.update(f['identity']);n.F.update(f['fixtures']);C=n.C;eq=n.eq;admin=n.admin;uid=n.uid

def imp(action,p,request=None):
 req=request or uid()
 with n.s.actor_conn() as c:r=c.execute('select public.erp_save_initial_import_action_v1(%s,%s,%s::uuid)',(action,Jsonb(p),req)).fetchone()[0]
 n.E.append({'api':'erp_save_initial_import_action_v1','action':action,'payload':p,'request':req,'result':r});return r

def batch(code,entities):
 b=imp('CREATE',{'batch_code':'AUD-SKU-'+code,'cutover_date':'2026-09-10','notes':'Independent exact physical identity input'})
 for entity,rows in entities:
  b=imp('SAVE_FILE',{'batch_id':b['batch_id'],'expected_revision':b['revision'],'entity':entity,'filename':entity+'.csv','rows':[{'source_row_no':i,'payload':r} for i,r in enumerate(rows,1)]})
 b=imp('VALIDATE',{'batch_id':b['batch_id'],'expected_revision':b['revision']});rows=admin('select entity_type,validation_status,validation_errors,normalized_payload from erp.migration_staging_rows where batch_id=%s order by entity_type,source_row_no',(b['batch_id'],));return b,rows

def post(b):
 eq(b['error_rows'],0);p={'batch_id':b['batch_id'],'expected_revision':b['revision']};req=uid();r=imp('FINALIZE',p,req);eq(r['status'],'POSTED');before=n.fp();replay=imp('FINALIZE',p,req);eq(n.fp(),before);eq(replay['batch_id'],b['batch_id']);return r

def open_sales(exact=True,over=False):
 code='SALES-'+('AMBIG' if not exact else 'OVER' if over else 'EXACT');stock={'balance_type':'FINISHED_GOODS','product_sku':'AUD-SKU-PHYSICAL','brand_code':'AUD-brand','model_code':'AUD-DAY','color_name':'AUD-SKU-INDIGO','size_code':'32','location_code':'AUD-fg','qty':'6','unit_cost':'123.47','hpp_input_method':'MANUAL','quality_grade':'GRADE_A','opening_source_key':code,'control_key':'FG'}
 sale={'draft_number':code,'line_number':'1','draft_date':'2026-09-09','customer_code':'AUD-DAY','location_code':'AUD-fg','product_sku':'AUD-SKU-PHYSICAL','qty_pcs':'999999' if over else '2','unit_price':'987.65'}
 if exact:sale['size_code']='32'
 b,rows=batch(code,[('OPENING_BALANCE_ITEM',[stock]),('OPENING_CONTROL',[{'control_key':'FG','balance_type':'FINISHED_GOODS','qty':'6','amount':'740.82'}]),('OPEN_SALES_DRAFT',[sale])])
 if not exact:
  assert b['error_rows']>0 and 'SIZE_ALLOCATION_REQUIRED' in json.dumps(rows),rows
  return {'invalid_before_post':True,'rows':rows}
 eq(b['error_rows'],0)
 if over:
  before=admin('select count(*) from erp.sales_headers',one=True);r=n.refuse(lambda:imp('FINALIZE',{'batch_id':b['batch_id'],'expected_revision':b['revision']}));eq(admin('select count(*) from erp.sales_headers',one=True),before);return {'stock_refusal':r,'no_partial_sale':True}
 r=post(b);got=admin('select i.product_id::text,i.qty_pcs from erp.sales_items i join erp.sales_headers h on h.id=i.sale_id where h.sale_number=%s',(code,));eq(got,[(C['roots'][1],2)]);return {'posted':r,'exact_size32_sale':got}

def pocket(exact=True):
 code='POCKET-'+('EXACT' if exact else 'AMBIG');row={'document_number':code,'line_number':'1','physical_date':'2026-09-08','contractor_code':'AUD-DAY','qty':'7','target_kind':'COGS','product_sku':'AUD-SKU-PHYSICAL','sold_reference':'Independent historical sale of seven size32','control_key':'SEW','control_qty':'7'}
 if exact:row['size_code']='32'
 b,rows=batch(code,[('OPENING_POCKET_SEWING',[row])])
 if not exact:
  assert b['error_rows']>0 and 'SIZE_ALLOCATION_REQUIRED' in json.dumps(rows),rows;return {'invalid_before_post':True,'rows':rows}
 r=post(b);got=admin('select product_id::text,qty,target_kind from erp.be_pocket_sewing_v1 where batch_id=%s',(b['batch_id'],));eq(got,[(C['roots'][1],7,'COGS')]);return {'posted':r,'exact_size32_history':got}

def custody(kind):
 code='CUSTODY-'+kind;row={'custody_kind':'CUSTOMER_GARMENT','custody_key':code,'customer_code':'AUD-DAY','description':'Independent exact customer garment','qty':'3','count_sheet':code,'sheet_line':'1'}
 if kind!='DESCRIPTION':row['product_sku']='AUD-SKU-PHYSICAL'
 if kind=='EXACT':row['size_code']='32'
 b,rows=batch(code,[('OPENING_ACCESSORY_CUSTODY',[row])])
 if kind=='AMBIG':
  assert b['error_rows']>0 and 'SIZE_ALLOCATION_REQUIRED' in json.dumps(rows),rows;return {'invalid_before_post':True,'rows':rows}
 r=post(b);got=admin('select product_id::text,qty_received from erp.bc_customer_custody_v1 where batch_id=%s',(b['batch_id'],));eq(got,[(None if kind=='DESCRIPTION' else C['roots'][1],3)]);return {'posted':r,'custody':got}

n.case('SKU.X.SR03.AMBIG','Ambiguous open-sales import rejected before posting',lambda:open_sales(False))
n.case('SKU.X.SR03.EXACT','Open-sales import retains exact size32 and replay has one effect',open_sales)
n.case('SKU.X.SR03.OVER','Insufficient stock import refuses atomically',lambda:open_sales(True,True))
n.case('SKU.X.SR04.POCKET_AMBIG','Ambiguous historical COGS input rejected',lambda:pocket(False))
n.case('SKU.X.SR04.POCKET_EXACT','Historical COGS input and replay retain exact size32',pocket)
for k in ['AMBIG','EXACT','DESCRIPTION']:n.case('SKU.X.SR04.CUSTODY_'+k,'Customer custody input '+k,lambda k=k:custody(k))
n.save()
