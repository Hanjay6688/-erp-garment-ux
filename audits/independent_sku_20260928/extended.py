"""Additional own SKU cases on a clone, preserving browser fixture independence."""
import native as n
import json,sys,copy,traceback
from decimal import Decimal as D
from datetime import datetime,timezone,timedelta
from psycopg.types.json import Jsonb
import psycopg
mode=sys.argv[1];n.s.DSN=n.s.DSN.replace('/cp6_rollback','/cp6_sku_edges');n.OUT=n.ROOT/'audit-results'/('sku-edges-'+mode);n.OUT.mkdir(exist_ok=True)
f=json.loads((n.ROOT/'audit-results/sku-fixture.json').read_text());n.C.update(f['identity']);n.F.update(f['fixtures']);C=n.C;F=n.F;admin=n.admin;eq=n.eq;uid=n.uid

def sales():
 f=F['A'];p={'sale_number':'AUD-SKU-SALE','customer_id':C['customer'],'source_location_id':C['fg'],'sale_date':n.at(120),'reason':'Independent SKU FIFO','items':[{'product_id':C['roots'][1],'qty_pcs':4,'unit_price_snapshot':'99999.99','discount_amount':'0.00'}]}
 with psycopg.connect(n.s.DSN) as c:
  c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));r=c.execute('select erp.save_sale_draft_v2(%s,%s::uuid,null)',(Jsonb(p),uid())).fetchone()[0];f['sale']=r['sale_id'];c.execute('select erp.post_sale(%s)',(f['sale'],))
 alloc=admin('select a.id::text,a.lot_id::text,a.qty_pcs,a.unit_hpp_snapshot from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s',(f['sale'],));eq(len(alloc),1);eq(alloc[0][1],f['lots'][C['roots'][1]]);eq(alloc[0][2],4);eq(alloc[0][3].quantize(D('.000001')),D('570.896250'))
 h=n.hpp({'query':'AUD-SKU-RANGE'})['groups'][0];eq(int(h['qty']),12);eq(D(h['value']).quantize(D('.000001')),D('4110.945000'));f['sale_allocation']=alloc[0][0];return {'allocation':alloc,'summary':h,'layer':'Native sales with owner identity, not HTTP authorization proof'}
def lateinvoice():
 f=F['A'];p={'vendor_id':C['daily_vendor'],'invoice_number':'AUD-SKU-LATE','invoice_date':datetime.now(timezone.utc).date().isoformat(),'header_total':'4519.49','lines':[{'line_kind':'BILL','receipt_line_id':f['receipt_line'],'category':'GOOD','qty':16,'amount':'4519.49','note':'Independent 160 recost after SKU range revision and sale'}]}
 draft=n.s.command('SAVE_INVOICE_DRAFT',p);r=n.s.command('POST_INVOICE',{'invoice_id':draft['invoice_id'],'expected_version':str(draft['row_version'])});f['invoice']=r
 rows=admin('select l.product_id::text,h.total_cost from erp.fg_lots l join erp.hpp_versions h on h.lot_id=l.id and h.is_current where l.po_id=%s',(f['po'],));eq(sum(x[1] for x in rows).quantize(D('.01')),D('6554.53'))
 eq(int(n.hpp({'query':'AUD-SKU-RANGE'})['groups'][0]['qty']),12);return {'response':r,'costs':rows,'expected_total':'6554.53','no_stock_change':True}
def returned():
 f=F['A'];ret=uid()
 with psycopg.connect(n.s.DSN) as c:
  c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));c.execute("select set_config('app.change_reason','Independent SKU linked return',true)")
  c.execute('insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,created_by) values(%s,%s,%s,%s,%s,%s)',(ret,'AUD-SKU-RETURN',f['sale'],C['customer'],n.at(160),C['app_owner']))
  c.execute('insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,refund_amount) select %s,a.id,l.product_id,l.id,a.location_id,1,99999.99 from erp.sale_stock_allocations a join erp.fg_lots l on l.id=a.lot_id where a.id=%s',(ret,f['sale_allocation']));c.execute('select erp.post_sales_return(%s)',(ret,))
 h=n.hpp({'query':'AUD-SKU-RANGE'})['groups'][0];eq(int(h['qty']),13);eq({x['size']:int(x['qty']) for x in h['lots']},{'31':5,'32':5,'33':3})
 gl={k:admin("select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.po_id=%s and l.account_id=erp.account_id(%s) and j.status in('POSTED','REVERSED')",(f['po'],k),one=True) for k in ['WIP','FG_INVENTORY','COGS']};eq(gl['WIP'],D(0));eq(gl['FG_INVENTORY']+gl['COGS'],D('6554.53'));return {'returned_exact_size':True,'summary':h,'independent_ledger':gl}
def move():
 when=(datetime.now(timezone.utc)-timedelta(seconds=2)).isoformat();allroots=C['roots']+[C['products'][C['s4']+':'+C['brand']]];gid=uid()
 target=n.group(gid,[C['roots'][2]],sku='AUD-SKU-SINGLE33',when=when);source=n.group(C['sku_id'],[x for x in allroots if x!=C['roots'][2]],when=when)
 before=admin('select lot_id::text,product_id::text,sum(qty_signed) from erp.fg_stock_movements group by 1,2 order by 1,2')
 refused=n.refuse(lambda:n.action('SAVE_GROUPS',n.payload([target],when)))
 r=n.action('SAVE_GROUPS',n.payload([target,source],when));eq(admin('select lot_id::text,product_id::text,sum(qty_signed) from erp.fg_stock_movements group by 1,2 order by 1,2'),before)
 h=n.hpp({'query':'AUD-SKU-'});groups={g['sku']:g for g in h['groups']};eq(int(groups['AUD-SKU-RANGE']['qty']),13);eq(int(groups['AUD-SKU-SINGLE33']['qty']),3);eq(sum(D(g['value']) for g in groups.values()).quantize(D('.01')),D('6394.53'));return {'one_sided_refused':refused,'atomic_move':r,'stock_and_cost_preserved':h}
def import_resolution():
 # Import resolver helper-level read, not full import posting; full consumer separately in regressions.
 with n.s.actor_conn() as c:
  made=c.execute('select public.erp_save_initial_import_action_v1(%s,%s,%s::uuid)',('CREATE',Jsonb({'batch_code':'AUD-SKU-IMPORT','cutover_date':datetime.now(timezone.utc).date().isoformat(),'notes':'Independent exact member input'}),uid())).fetchone()[0]
 batch=made['batch_id']
 outcomes=[]
 for size,root in zip(['31','32','33'],C['roots']):
  p={'product_sku':'AUD-SKU-PHYSICAL','size_code':size};r=admin('select erp.bf_resolve_import_product_v1(%s,%s)',(batch,Jsonb(p)),one=True);eq(str(r),root);outcomes.append({'input':p,'resolved':str(r)})
 for p in [{'product_sku':'AUD-SKU-PHYSICAL'},{'product_id':C['roots'][0],'size_code':'32'},{'product_sku':'AUD-SKU-PHYSICAL','size_code':'99'}]:
  outcomes.append({'refusal':n.refuse(lambda p=p:admin('select erp.bf_resolve_import_product_v1(%s,%s)',(batch,Jsonb(p)),one=True)),'input':p})
 return {'layer':'Native import product resolver; not full row/post pipeline','results':outcomes}
def private_sql():
 rows=admin("select p.oid::regprocedure::text,has_function_privilege('authenticated',p.oid,'EXECUTE'),has_function_privilege('anon',p.oid,'EXECUTE') from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp' and (p.proname like 'bf_%' or p.proname in ('save_sku_action_v1','get_sku_workspace_v1','get_sku_hpp_v1')) order by 1")
 assert rows and all(not a and not b for _,a,b in rows),rows
 tables=admin("select tablename,has_table_privilege('authenticated','erp.'||tablename,'SELECT,INSERT,UPDATE,DELETE') from pg_tables where schemaname='erp' and tablename like 'bf_%' order by 1");assert all(not allowed for _,allowed in tables),tables
 return {'helpers':rows,'private_tables':tables}
if mode=='sales':
 n.case('SKU.S01','Sale uses exact middle-size FIFO cost, summary recomputes remaining weighted cost',sales)
 n.case('SKU.S02','Late invoice after range change recosts all source cost, without stock change',lateinvoice,['SKU.S01'])
 n.case('SKU.S03','Linked return retains size, lot and total FG plus COGS after recost',returned,['SKU.S02'])
elif mode=='move':n.case('SKU.R02','Member moves atomically between groups without duplicate stock/cost',move)
elif mode=='import':n.case('SKU.I01','Import exact size selection and ambiguity refusal',import_resolution)
elif mode=='access':n.case('SKU.A03','Direct helper SQL and table grants remain private',private_sql)
n.save()
