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
 rows=admin("select p.oid::regprocedure::text,has_function_privilege('authenticated',p.oid,'EXECUTE'),has_function_privilege('anon',p.oid,'EXECUTE') from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp' and (p.proname like 'bf_%%' or p.proname in ('save_sku_action_v1','get_sku_workspace_v1','get_sku_hpp_v1')) order by 1")
 assert rows and all(not a and not b for _,a,b in rows),rows
 tables=admin("select tablename,has_table_privilege('authenticated','erp.'||tablename,'SELECT,INSERT,UPDATE,DELETE') from pg_tables where schemaname='erp' and tablename like 'bf_%%' order by 1");assert all(not allowed for _,allowed in tables),tables
 return {'helpers':rows,'private_tables':tables}
def new_sku_context(recipe=False):
 C['base']=(datetime.now(timezone.utc)-timedelta(seconds=60)).isoformat();when=n.at();allroots=C['roots']+[C['products'][C['s4']+':'+C['brand']]]
 if recipe:
  cat=uid();admin("insert into erp.accessory_categories(id,category_code,category_name,base_uom_code) values(%s,'AUD-SKU-TAG','Independent SKU tag','PCS')",(cat,))
  settings=copy.deepcopy(C['settings']);settings['bom']=[{'category_id':cat,'qty_per_good_fg_base':'2','hpp_method':'BOM_STANDARD','hpp_standard_rate':'17.31','hpp_uom_code':'PCS','reimbursement_rate':'17.31','reimbursement_uom_code':'PCS'}]
  r=n.action('SAVE_GROUPS',n.payload([n.group(C['sku_id'],allroots,settings,when=when)],when));C['v1']=r['groups'][0]['version_id'];C['recipe_cat']=cat
 else:
  gid=uid();settings=copy.deepcopy(C['settings']);settings['work_rates'][0]['rate']='500.03';settings['laundry_rates'][0]['rate']='197.43'
  groups=[n.group(C['sku_id'],[x for x in allroots if x!=C['roots'][2]],when=when),n.group(gid,[C['roots'][2]],settings,sku='AUD-SKU-MIXED33',when=when)]
  r=n.action('SAVE_GROUPS',n.payload(groups,when));C['wave_sku_by_size']={C['s3']:gid};C['v1']=r['groups'][0]['version_id']
 n.new_wave('B')
 if recipe:F['B']['expected_size_costs']=['1315.20','4844.13','789.12']
 else:F['B'].update(expected_laundry='4648.09',expected_size_costs=['1142.10','4567.17','2092.38'])
 return r

def mixed_work_combined():
 f=F['B']
 with psycopg.connect(n.s.DSN) as c:
  c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));c.execute("select set_config('app.change_reason','Independent mixed SKU work',true)")
  c.execute('select erp.bf_ensure_work_v1(%s,%s)',(f['po'],n.at(10)))
  snaps=c.execute('select x.id,x.rate_per_pcs_snapshot,v.sku_id::text from erp.po_work_component_snapshots x join erp.bf_sku_versions_v1 v on v.id=x.bf_sku_version_id where x.po_id=%s',(f['po'],)).fetchall();eq(len(snaps),2)
  c.execute('insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,created_by) values(%s,%s,%s,%s,%s,%s,%s)',(f['work'],'AUD-SKU-MIXED-WORK',f['po'],C['mandor'],f['group'],n.at(10),C['app_owner']))
  for sid,rate,sku in snaps:
   q=13 if sku==C['sku_id'] else 3;eq(rate,D('127.19' if q==13 else '500.03'))
   c.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot) values(%s,%s,%s,%s,%s,%s)',(f['work'],sid,C['work_component'],q,q,rate))
  c.execute('select erp.post_work_completion(%s)',(f['work'],));r=c.execute('select erp.record_sewing_terminal_v1(%s,%s::uuid)',(Jsonb({'work_completion_id':f['work'],'qty_pcs':16,'reason':'Independent mixed SKU sewing'}),uid())).fetchone()[0]
 return {'snapshots':snaps,'result':r,'expected_labor':'3153.56'}
def mixed_work():
 f=F['B'];out=[]
 with psycopg.connect(n.s.DSN) as c:
  c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));c.execute("select set_config('app.change_reason','Independent separate SKU completion events',true)")
  c.execute('select erp.bf_ensure_work_v1(%s,%s)',(f['po'],n.at(10)))
  snaps=c.execute('select x.id,x.rate_per_pcs_snapshot,v.sku_id::text from erp.po_work_component_snapshots x join erp.bf_sku_versions_v1 v on v.id=x.bf_sku_version_id where x.po_id=%s',(f['po'],)).fetchall();eq(len(snaps),2)
  for sid,rate,sku in snaps:
   q=13 if sku==C['sku_id'] else 3;event=uid();eq(rate,D('127.19' if q==13 else '500.03'))
   c.execute('insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,created_by) values(%s,%s,%s,%s,%s,%s,%s)',(event,'AUD-MIX-'+event,f['po'],C['mandor'],f['group'],n.at(10),C['app_owner']))
   c.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot) values(%s,%s,%s,%s,%s,%s)',(event,sid,C['work_component'],q,q,rate))
   c.execute('select erp.post_work_completion(%s)',(event,));r=c.execute('select public.erp_record_sewing_terminal_v1(%s,%s::uuid)',(Jsonb({'work_completion_id':event,'qty_pcs':q,'reason':'Independent scoped completion per SKU'}),uid())).fetchone()[0];out.append(r)
 eq(admin('select unsent_ready_qty_pcs from erp.v_wip_control_status_v1 where cutting_group_id=%s',(f['group'],),one=True),16)
 return {'actual_completion_events':out,'expected_total_physical':16,'expected_labor':'3153.56','boundary':'Two SKU-specific completion events in the same physical wave'}

def pinned_recipe():
 rows=admin('select po_id::text,sku_id::text,version_id::text from erp.bf_po_boms_v1 where po_id=any(%s::uuid[]) order by po_id',([F['A']['po'],F['B']['po']],));eq(len(rows),2);assert len({x[2] for x in rows})==2,rows
 old=admin('select sum(h.total_cost) from erp.hpp_versions h join erp.fg_lots l on l.id=h.lot_id where l.po_id=%s and h.is_current',(F['A']['po'],),one=True);eq(old.quantize(D('.01')),D('6394.53'))
 return {'old_new_po_recipe_versions':rows,'old_cost_preserved':old}
def identities():
 size,root,gid=uid(),uid(),uid();when=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
 with psycopg.connect(n.s.DSN) as c:
  c.execute("select set_config('app.change_reason','Independent singleton27 boundary',true)")
  c.execute("insert into erp.sizes(id,size_code,sort_order) values(%s,'27',27)",(size,));c.execute('insert into erp.product_model_sizes(model_id,size_id) values(%s,%s)',(C['model'],size))
  c.execute("insert into erp.products(id,identity_root_id,sku,model_id,brand_id,color_name,size_id,product_name,effective_from) values(%s,%s,'AUD-SPECIAL-27',%s,%s,'AUD-SKU-INDIGO',%s,'Independent singleton','2026-09-01T00:00Z')",(root,root,C['model'],C['brand'],size))
 settings=copy.deepcopy(C['settings']);settings['price']='45678.91';before=admin('select revision from erp.bf_skus_v1 where id=%s',(C['sku_id'],),one=True)
 singleton=n.action('SAVE_GROUPS',n.payload([n.group(gid,[root],settings,sku='AUD-SPECIAL-27',when=when)],when))
 otherroots=[C['products'][C[x]+':'+C['brand2']] for x in ['s1','s2']];other=n.action('SAVE_GROUPS',n.payload([n.group(uid(),otherroots,settings,sku='AUD-SKU-RANGE',when=when)],when))
 eq(admin('select revision from erp.bf_skus_v1 where id=%s',(C['sku_id'],),one=True),before)
 eq(admin("select count(*) from erp.bf_skus_v1 where sku='AUD-SKU-RANGE'",one=True),2)
 eq(admin('select count(*) from erp.bf_sku_members_v1 where version_id=%s',(singleton['groups'][0]['version_id'],),one=True),1)
 return {'singleton27':singleton,'same_code_other_brand':other,'primary_group_unchanged':True}
def free_context():
 C['base']=(datetime.now(timezone.utc)-timedelta(seconds=60)).isoformat();when=n.at();settings=copy.deepcopy(C['settings'])
 for r,status in zip(settings['laundry_rates'],['FREE','WAIVED']):r.update(rate_status=status,rate='0.00',reason='Independent explicitly approved synthetic '+status)
 roots=C['roots']+[C['products'][C['s4']+':'+C['brand']]];r=n.action('SAVE_GROUPS',n.payload([n.group(C['sku_id'],roots,settings,when=when)],when));C['v1']=r['groups'][0]['version_id'];n.new_wave('B');F['B'].update(expected_laundry='0.00',expected_size_costs=['635.95','1017.52','381.57']);return r
if mode=='sales':
 n.case('SKU.S01','Sale uses exact middle-size FIFO cost, summary recomputes remaining weighted cost',sales)
 n.case('SKU.S02','Late invoice after range change recosts all source cost, without stock change',lateinvoice,['SKU.S01'])
 n.case('SKU.S03','Linked return retains size, lot and total FG plus COGS after recost',returned,['SKU.S02'])
elif mode=='move':n.case('SKU.R02','Member moves atomically between groups without duplicate stock/cost',move)
elif mode=='import':n.case('SKU.I01','Import exact size selection and ambiguity refusal',import_resolution)
elif mode=='identities':n.case('SKU.M04','Singleton27 and same commercial code on another brand stay independent',identities)
elif mode in ['mixed','recipe','free']:
 n.case('SKU.'+mode+'.SETUP','Separate mixed-wave rates or nonempty shared recipe',free_context if mode=='free' else lambda:new_sku_context(mode=='recipe'))
 n.case('SKU.'+mode+'.WORK','Actual scoped work completion',mixed_work if mode=='mixed' else lambda:n.work('B'),['SKU.'+mode+'.SETUP'])
 n.case('SKU.'+mode+'.SHIP','Actual mixed SKU or recipe shipment',lambda:n.shipment('B'),['SKU.'+mode+'.WORK'])
 n.case('SKU.'+mode+'.RECEIVE','Actual physical receipt',lambda:n.receive('B'),['SKU.'+mode+'.SHIP'])
 n.case('SKU.'+mode+'.QC','Independent per-size work laundry and recipe arithmetic',lambda:n.qc('B'),['SKU.'+mode+'.RECEIVE'])
 if mode=='recipe':n.case('SKU.RECIPE.PIN','Old PO recipe and cost remain while new PO uses new shared recipe',pinned_recipe,['SKU.recipe.QC'])
elif mode=='access':n.case('SKU.A03','Direct helper SQL and table grants remain private',private_sql)
n.save()
