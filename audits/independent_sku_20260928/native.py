"""Own SKU oracle execution. Product functions are the subject, never the oracle.
Seeded cutting/pickup prerequisites are explicitly NOT acceptance of those UIs.
"""
from pathlib import Path
import sys,json,traceback,copy,time,threading,hashlib
from datetime import datetime,timezone,timedelta
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
import psycopg
from psycopg.types.json import Jsonb
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'audits/independent_bd_20260927')]
import suite as s
import daily as d
C=s.CTX;R=[];E=s.EVENTS;F={};OUT=s.OUT;uid=s.uid;eq=s.eq;admin=s.admin
CANDIDATE='23e9c9830c32dce10604c43d17e4476d2707b55d'
def save():
 (OUT/'sku-native-results.json').write_text(json.dumps({'candidate':CANDIDATE,'oracle_sha256':hashlib.sha256((Path(__file__).parent/'ORACLE.md').read_bytes()).hexdigest(),'results':R,'production_go':False},indent=2,default=str))
 (OUT/'sku-native-events.json').write_text(json.dumps(E,indent=2,default=str))
 (OUT/'sku-fixture.json').write_text(json.dumps({'identity':C,'fixtures':F},indent=2,default=str))
s.save=save
def case(id,title,fn,requires=()):
 row={'id':id,'title':title,'layer':'Unprivileged authenticated SQL RPC and independent readback'}
 missing=[x for x in requires if not any(r['id']==x and r['status']=='PASS' for r in R)]
 if missing:row.update(status='BLOCKED',missing=missing)
 else:
  try:row.update(status='PASS',observation=s.clean(fn()))
  except Exception as e:row.update(status='FAIL',error=str(e),traceback=traceback.format_exc())
 R.append(row);save();print(json.dumps(row,default=str),flush=True)

def at(offset=0):return (datetime.fromisoformat(C['base'])+timedelta(seconds=offset)).isoformat()
def rpc(name,payload,who='owner'):
 with s.actor_conn(who) as c:return c.execute('select public.'+name+'(%s)',(Jsonb(payload),)).fetchone()[0]
def action(a,p,request=None,who='owner'):
 req=request or uid();ev={'api':'erp_save_sku_action_v1','action':a,'payload':p,'request':req,'actor':who}
 try:
  with s.actor_conn(who) as c:r=c.execute('select public.erp_save_sku_action_v1(%s,%s,%s::uuid)',(a,Jsonb(p),req)).fetchone()[0]
  ev['response']=r;return r
 except psycopg.Error as e:ev.update(error=str(e),sqlstate=e.sqlstate);raise
 finally:E.append(ev)
def workspace(p=None,who='owner'):return rpc('erp_get_sku_workspace_v1',p or {},who)
def hpp(p=None,who='owner'):return rpc('erp_get_sku_hpp_v1',p or {},who)
def fp():
 names=['bf_skus_v1','bf_sku_versions_v1','bf_sku_members_v1','bf_requests_v1','bf_wave_skus_v1','bf_context_v1','product_price_versions','accessory_bom_versions','accessory_bom_items','fg_stock_movements','fg_lots','hpp_versions','journal_entries','journal_lines']
 return {n:admin("select md5(coalesce(string_agg(to_jsonb(t)::text,'' order by to_jsonb(t)::text),'')) from erp."+n+' t',one=True) for n in names}
def refuse(fn,contains=None):
 before=fp()
 try:fn()
 except psycopg.Error as e:
  assert e.sqlstate in ('P0001','42501','23514','23505'),(e.sqlstate,str(e))
  if contains:assert contains in str(e),str(e)
  eq(fp(),before,'Atomic refusal');return {'sqlstate':e.sqlstate,'message':str(e),'unchanged':True}
 raise AssertionError('Expected safe refusal but accepted')
def group(gid,roots,settings=None,sku=None,when=None):
 when=when or at();p=admin('select brand_id::text,model_id::text,color_name from erp.products where id=%s',(roots[0] if roots else C['roots'][0],))[0]
 revision=admin('select coalesce((select revision from erp.bf_skus_v1 where id=%s),0)',(gid,),one=True)
 return {'id':gid,'expected_version':str(revision),'brand_id':p[0],'model_id':p[1],'color_name':p[2],'sku':sku or 'AUD-SKU-RANGE','members':roots,'settings':copy.deepcopy(settings or C['settings']),'legacy_basis':workspace({'roots':roots,'at':when})['legacy_basis']}
def payload(groups,when=None):return {'effective_from':when or at(),'reason':'Independent SKU audit decision','groups':groups}
def setup():
 s.setup();original=d.precursor;d.precursor=lambda key:None
 try:d.setup()
 finally:d.precursor=original
 C['base']=(datetime.now(timezone.utc)-timedelta(seconds=210)).isoformat();C['sku_id']=uid();C['s3']=uid();C['s4']=uid()
 C['roots']=[]
 with psycopg.connect(s.DSN) as c:
  c.execute("select set_config('app.change_reason','Independent size fixture',true)")
  for key,code in [('s1','31'),('s2','32')]:c.execute('update erp.sizes set size_code=%s where id=%s',(code,C[key]))
  for key,code in [('s1','31'),('s2','32'),('s3','33'),('s4','34')]:
   if key in ['s3','s4']:
    c.execute('insert into erp.sizes(id,size_code,sort_order) values(%s,%s,%s)',(C[key],code,int(code)))
    c.execute('insert into erp.product_model_sizes(model_id,size_id) values(%s,%s)',(C['model'],C[key]))
   pid=uid();C['products'][C[key]+':'+C['brand']]=pid
   c.execute("insert into erp.products(id,identity_root_id,sku,model_id,brand_id,color_name,size_id,product_name,effective_from) values(%s,%s,'AUD-SKU-PHYSICAL',%s,%s,'AUD-NAVY',%s,'Independent range member','2026-09-01T00:00Z')",(pid,pid,C['model'],C['brand'],C[key]))
   c.execute("insert into erp.accessory_bom_versions(product_id,version_label,effective_from,created_by) values(%s,'NONE','2026-09-01T00:00Z',%s)",(pid,C['app_owner']))
   if key!='s4':C['roots'].append(pid)
  rid=c.execute('select role_id from erp.app_users where auth_user_id=%s',(C['staff'],)).fetchone()[0]
  c.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'master.product.view') on conflict do nothing",(rid,))
 C['settings']={'price':'87654.32','bom':[],'work_rates':[{'work_component_id':C['work_component'],'rate':'127.19'}],'laundry_rates':[{'vendor_id':C['daily_vendor'],'kind':'COMPONENT','ref_id':C['daily_wash'],'rate_status':'KNOWN','rate':'101.23','reason':None},{'vendor_id':C['daily_vendor'],'kind':'COMPONENT','ref_id':C['daily_finish'],'rate_status':'KNOWN','rate':'913.27','reason':None}]}
 return {'physical_sizes':[31,32,33,34],'uneven_quantities':[5,8,3],'base':C['base'],'seed_boundary':'Own prior master/cut/pickup fixtures; business posting is independently executed below.'}
def adoption():
 C['initial_payload']=payload([group(C['sku_id'],C['roots'])]);C['initial_request']=uid();r=action('SAVE_GROUPS',C['initial_payload'],C['initial_request']);C['v1']=str(admin('select id from erp.bf_sku_versions_v1 where sku_id=%s and revision=1',(C['sku_id'],),one=True))
 rows=admin('select p.id::text,p.size_id::text,m.price_version_id::text,v.price,m.bom_version_id::text from erp.bf_sku_members_v1 m join erp.products p on p.id=m.product_root join erp.product_price_versions v on v.id=m.price_version_id where m.version_id=%s',(C['v1'],))
 eq({x[0] for x in rows},set(C['roots']));eq([x[3] for x in rows],[D('87654.32')]*3);eq(len({x[2] for x in rows}),3);eq(len({x[4] for x in rows}),3)
 eq(admin('select count(*) from erp.fg_stock_movements',one=True),0);return {'response':r,'physical_members':rows}
def replay():
 before=fp();r=action('SAVE_GROUPS',C['initial_payload'],C['initial_request']);eq(r['replayed'],True);eq(fp(),before);return r
def read_security():
 w=workspace({},'staff');eq(w['can_edit'],False);eq(w['lookups'],None);eq(w['legacy_basis'],None);assert all(g['settings'] is None for g in w['groups']);refuse(lambda:hpp({},'staff'));refuse(lambda:workspace({'roots':C['roots']},'staff'));refuse(lambda:action('SAVE_GROUPS',C['initial_payload'],who='staff'));return w
def revoked_replay():
 old=admin('select role,role_id from erp.app_users where auth_user_id=%s',(C['owner'],))[0];staff=admin('select role_id from erp.app_users where auth_user_id=%s',(C['staff'],),one=True)
 admin("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(staff,C['owner']))
 try:return refuse(lambda:action('SAVE_GROUPS',C['initial_payload'],C['initial_request']))
 finally:admin('update erp.app_users set role=%s,role_id=%s where auth_user_id=%s',(old[0],old[1],C['owner']))
def invalid_master(kind):
 g=group(C['sku_id'],C['roots'],when=at(3));p=payload([g],at(3))
 if kind=='stale':g['expected_version']='0'
 if kind=='duplicate':g['members'].append(g['members'][0])
 if kind=='cross-brand':g['members'].append(C['products'][C['s1']+':'+C['brand2']])
 if kind=='basis':g['legacy_basis'][0]['price']='0.01'
 if kind=='unknown-zero':g['settings']['laundry_rates'][0].update(rate_status='UNKNOWN',rate='0.00')
 if kind=='free-reason':g['settings']['laundry_rates'][0].update(rate_status='FREE',rate='0.00',reason=None)
 return refuse(lambda:action('SAVE_GROUPS',p))
def legacy_write_guard():
 return refuse(lambda:admin("insert into erp.product_price_versions(product_id,price,effective_from) values(%s,1,now())",(C['roots'][0],)),'BF_SHARED_MASTER')
def new_wave(key='A',mixed=False):
 f={k:uid() for k in ['po','group','cb','roll','groll','pickup','batch','work','base_snap']};F[key]=f
 with psycopg.connect(s.DSN) as c:
  c.execute("select set_config('app.change_reason','Independent controlled prerequisite',true)");c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],))
  c.execute("insert into erp.production_orders(id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at) values(%s,%s,%s,%s,16,'SEWING','SEWING',%s)",(f['po'],'AUD-SKU-'+key,C['model'],C['mandor'],at(5)))
  c.execute('insert into erp.cutting_batches(id,po_id,batch_number,cut_at) values(%s,%s,%s,%s)',(f['cb'],f['po'],'AUD-SKU-CUT-'+key,at(5)))
  c.execute("insert into erp.cutting_groups(id,po_id,group_number,cut_at,status,cutting_batch_id,pattern_id,source_location_id,material_issue_posted) values(%s,%s,%s,%s,'CUT',%s,%s,%s,false)",(f['group'],f['po'],'AUD-SKU-WAVE-'+key,at(5),f['cb'],C['pattern'],C['rawloc']))
  c.execute('insert into erp.material_rolls(id,material_id,roll_number,original_qty,cached_qty,received_at) values(%s,%s,%s,16,0,%s)',(f['roll'],C['material'],'AUD-SKU-ROLL-'+key,at(1)))
  c.execute('insert into erp.cutting_group_rolls(id,cutting_group_id,roll_id,qty_issued,qty_consumed,qty_reported_remaining,unit_cost_snapshot) values(%s,%s,%s,16,16,0,0)',(f['groll'],f['group'],f['roll']))
  c.execute("insert into erp.cutting_pickups(id,cutting_group_id,contractor_id,picked_up_at,allocation_mode,status,created_by) values(%s,%s,%s,%s,'SIZE','DRAFT',%s)",(f['pickup'],f['group'],C['mandor'],at(6),C['app_owner']))
  c.execute('insert into erp.cutting_distribution_batches(id,pickup_id,batch_no) values(%s,%s,1)',(f['batch'],f['pickup']))
  for slot,(size,qty) in enumerate(zip([C['s1'],C['s2'],C['s3']],[5,8,3]),1):
   sid,yid=uid(),uid();c.execute('insert into erp.cutting_group_size_slots(id,cutting_group_id,slot_no,size_id,drawing_no) values(%s,%s,%s,%s,1)',(sid,f['group'],slot,size));c.execute('insert into erp.cutting_roll_yields(id,cutting_group_roll_id,size_slot_id,qty_pcs) values(%s,%s,%s,%s)',(yid,f['groll'],sid,qty));c.execute('insert into erp.cutting_distribution_allocations(batch_id,cutting_roll_yield_id,qty_pcs) values(%s,%s,%s)',(f['batch'],yid,qty))
  c.execute("update erp.cutting_pickups set status='POSTED',posted_by=%s,posted_at=%s where id=%s",(C['app_owner'],at(6),f['pickup']));c.execute("update erp.cutting_groups set material_issue_posted=true,picked_up_at=%s,status='SEWING' where id=%s",(at(6),f['group']))
  c.execute("insert into erp.wip_stage_events(po_id,cutting_group_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by) values(%s,%s,'CUTTING','SEWING',16,%s,'AUDIT_PREREQUISITE',%s,%s,%s)",(f['po'],f['group'],C['mandor'],f['pickup'],at(6),C['app_owner']))
  c.execute('insert into erp.po_work_component_snapshots(id,po_id,work_component_id,rate_per_pcs_snapshot,committed_at) values(%s,%s,%s,100,%s)',(f['base_snap'],f['po'],C['work_component'],at(6)))
 before=admin('select count(*) from erp.fg_lots',one=True);w=workspace({'wave_id':f['group']})['wave'];f['bind_payload']={'cutting_group_id':f['group'],'expected_version':w['revision'],'references':[{'sku_id':C['sku_id'],'size_id':C[x]} for x in ['s1','s2','s3']]}
 r=action('BIND_WAVE',f['bind_payload']);eq(admin('select count(*) from erp.fg_lots',one=True),before);eq(admin('select total_pcs from erp.v_cutting_group_totals where cutting_group_id=%s',(f['group'],),one=True),16);return r

def work(key='A'):
 f=F[key]
 with psycopg.connect(s.DSN) as c:
  c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));c.execute("select set_config('app.change_reason','Independent SKU work completion',true)")
  c.execute('select erp.bf_ensure_work_v1(%s,%s)',(f['po'],at(10)))
  snap=c.execute('select id,rate_per_pcs_snapshot,bf_sku_version_id from erp.po_work_component_snapshots where po_id=%s and bf_sku_version_id is not null',(f['po'],)).fetchone();eq(snap[1],D('127.19'));eq(str(snap[2]),C['v1']);f['snap']=str(snap[0])
  c.execute('insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,created_by) values(%s,%s,%s,%s,%s,%s,%s)',(f['work'],'AUD-SKU-WORK-'+key,f['po'],C['mandor'],f['group'],at(10),C['app_owner']))
  c.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot) values(%s,%s,%s,16,16,%s)',(f['work'],snap[0],C['work_component'],snap[1]))
  c.execute('select erp.post_work_completion(%s)',(f['work'],));r=c.execute('select erp.record_sewing_terminal_v1(%s,%s::uuid)',(Jsonb({'work_completion_id':f['work'],'qty_pcs':16,'reason':'Independent complete sewing'}),uid())).fetchone()[0]
 eq(admin('select unsent_ready_qty_pcs from erp.v_wip_control_status_v1 where cutting_group_id=%s',(f['group'],),one=True),16)
 return {'result':r,'expected_labor':'2035.04','snap':f['snap'],'layer':'Native real work posting after own seeded cut/pickup'}
def shipment(key='A'):
 f=F[key];p={'expected_version':str(d.ver('cutting_groups',f['group'])),'delivery':{'distribution_batch_id':f['batch'],'vendor_id':C['daily_vendor'],'wash_process_id':C['process'],'target_dyeing_color':'AUD-NAVY','physical_at':at(20),'reason':'Independent SKU scoped pricing','lines':[{'size_id':C[k],'qty_sent_pcs':n} for k,n in zip(['s1','s2','s3'],[5,8,3])]},'pricing':{'components':[{'component_id':C['daily_wash'],'covered_qty':16},{'component_id':C['daily_finish'],'covered_qty':3,'coverage':[{'size_id':C['s2'],'qty':3}]}]}}
 r=s.command('POST_PRICED_DELIVERY',p);f['delivery']=r['delivery_id'];f['delivery_line']=admin('select id::text from erp.laundry_delivery_lines where delivery_id=%s',(f['delivery'],),one=True)
 eq(D(r['pricing']['total_known']),D('4359.49'));eq(D(r['estimated_cost']),D('4359.49'))
 rows=admin('select ref_id::text,unit_rate,covered_qty,amount,bf_sku_version_id::text from erp.bd_laundry_charge_lines_v1 where delivery_line_id=%s order by line_no',(f['delivery_line'],));return {'response':r,'charges':rows}
def receive(key='A'):
 f=F[key];xs=admin('select id::text,qty_sent_pcs from erp.laundry_delivery_batch_size_lines where delivery_line_id=%s order by size_id',(f['delivery_line'],))
 p={'delivery_id':f['delivery'],'wash_process_id':C['process'],'physical_at':at(30),'reason':'Independent uneven SKU receipt','lines':[{'delivery_batch_size_line_id':i,'qty_good_received':n,'qty_bs_laundry':0,'bs_product_id':None} for i,n in xs]}
 r=d.rpc('POST_RECEIPT',p,d.ver('laundry_deliveries',f['delivery']));f['receipt']=r['receipt_id'];f['receipt_line']=admin('select id::text from erp.laundry_receipt_lines where receipt_id=%s',(f['receipt'],),one=True);eq(D(r['actual_cost']),D('4359.49'));return r
def qc(key='A'):
 f=F[key];xs=admin('select id::text,size_id::text,qty_good_received from erp.laundry_receipt_batch_size_lines where receipt_line_id=%s',(f['receipt_line'],))
 p={'cutting_group_id':f['group'],'destination_location_id':C['fg'],'physical_at':at(40),'reason':'Independent exact-size FG','good_qty_pcs':16,'completion_mode':'ALL_READY','lines':[{'final_product_id':C['products'][size+':'+C['brand']],'qty_good_pcs':n,'qty_bs_pcs':0,'source_laundry_receipt_line_id':f['receipt_line'],'source_laundry_receipt_batch_size_line_id':i} for i,size,n in xs]}
 r=d.rpc('POST_FINAL_SKU',p,d.ver('cutting_groups',f['group']));f['qc']=r
 rows=admin('select l.product_id::text,l.initial_qty_pcs,h.total_cost,l.id::text from erp.fg_lots l join erp.hpp_versions h on h.lot_id=l.id and h.is_current where l.po_id=%s',(f['po'],));f['lots']={x[0]:x[3] for x in rows}
 expected={C['roots'][0]:(5,D('1142.10')),C['roots'][1]:(8,D('4567.17')),C['roots'][2]:(3,D('685.26'))};eq({p:(q,t.quantize(D('.01'))) for p,q,t,_ in rows},expected,'Only three middle-size PCS receive 2739.81 extra cost');return {'response':r,'rows':rows,'independent_total':'6394.53'}
def hpp_current():
 r=hpp({'query':'AUD-SKU-RANGE'});eq(r['total'],1);g=r['groups'][0];eq(int(g['qty']),16);eq(D(g['value']).quantize(D('.01')),D('6394.53'));eq(D(g['hpp_per_pcs']).quantize(D('.000001')),D('399.658125'));eq({x['size']:int(x['qty']) for x in g['lots']},{'31':5,'32':8,'33':3});return r
def hpp_filters():
 r=hpp({'query':'AUD-SKU-RANGE','location_id':C['rawloc']});eq(r['total'],0)
 r=hpp({'query':'AUD-SKU-RANGE','location_id':C['fg'],'grade':'GOOD'});eq(int(r['groups'][0]['qty']),16)
 eq(hpp({'brand_id':C['brand2']})['total'],0);refuse(lambda:hpp({'at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}));return r
def historical_hpp_observation():
 r=hpp({'query':'AUD-SKU-RANGE','at':at(45)});eq(int(r['groups'][0]['qty']),16)
 return {'observation_only':'Historical stock exists before current system calculation. Null cost is system-time semantics, contract decision must be checked before calling a bug.','response':r}
def rename_range():
 oldqty=admin('select sum(qty_signed) from erp.fg_stock_movements',one=True);oldlots=admin('select id::text,product_id::text,initial_qty_pcs from erp.fg_lots order by id');roots=C['roots']+[C['products'][C['s4']+':'+C['brand']]]
 g=group(C['sku_id'],roots,when=at(80));g['settings']['price']='90123.45';r=action('SAVE_GROUPS',payload([g],at(80)));C['v2']=r['groups'][0].get('version_id')
 eq(admin('select sum(qty_signed) from erp.fg_stock_movements',one=True),oldqty);eq(admin('select id::text,product_id::text,initial_qty_pcs from erp.fg_lots order by id'),oldlots)
 eq(str(admin('select erp.bf_version_at_v1(%s,%s)',(C['roots'][0],at(40)),one=True)),C['v1']);eq(admin('select count(*) from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id where v.sku_id=%s and v.revision=2',(C['sku_id'],),one=True),4)
 eq(admin('select bf_sku_version_id::text from erp.po_work_component_snapshots where id=%s',(F['A']['snap'],),one=True),C['v1']);return r
def race():
 # Same revision and basis: exactly one writer succeeds, other is stale.
 current=admin('select revision from erp.bf_skus_v1 where id=%s',(C['sku_id'],),one=True);roots=C['roots']+[C['products'][C['s4']+':'+C['brand']]];when=at(100)
 p1=payload([group(C['sku_id'],roots,when=when)],when);p2=copy.deepcopy(p1);p1['groups'][0]['settings']['price']='91234.56';p2['groups'][0]['settings']['price']='92345.67';barrier=threading.Barrier(2)
 def run(p):
  barrier.wait()
  try:return {'ok':True,'result':action('SAVE_GROUPS',p)}
  except psycopg.Error as e:return {'ok':False,'sqlstate':e.sqlstate,'error':str(e)}
 with ThreadPoolExecutor(2) as pool:out=list(pool.map(run,[p1,p2]))
 eq(sum(x['ok'] for x in out),1);eq(admin('select revision from erp.bf_skus_v1 where id=%s',(C['sku_id'],),one=True),current+1);assert 'STALE_VERSION' in next(x['error'] for x in out if not x['ok']);eq(admin('select count(*) from erp.bf_context_v1',one=True),0);return out

def main():
 case('SKU.SETUP','Independent synthetic masters and separate physical size roots',setup)
 case('SKU.M01','One shared master applies price and explicit empty recipe to three sizes',adoption,['SKU.SETUP'])
 case('SKU.M02','Identical request replay has exactly one effect',replay,['SKU.M01'])
 case('SKU.A01','Viewer can read identity but cannot read or change economic settings',read_security,['SKU.M01'])
 case('SKU.A02','Revoked owner cannot replay old successful UUID',revoked_replay,['SKU.M01'])
 for k in ['stale','duplicate','cross-brand','basis','unknown-zero','free-reason']:case('SKU.N.'+k,'Invalid group update refused atomically: '+k,lambda k=k:invalid_master(k),['SKU.M01'])
 case('SKU.M03','Legacy per-size price bypass refused',legacy_write_guard,['SKU.M01'])
 case('SKU.W01','Wave keeps physical 5/8/3 PCS while sharing tariff reference',new_wave,['SKU.M01'])
 case('SKU.W02','Native work completion pins shared 127.19 rate',work,['SKU.W01'])
 case('SKU.W03','Used wave rejects replacement references',lambda:refuse(lambda:action('BIND_WAVE',{**F['A']['bind_payload'],'expected_version':workspace({'wave_id':F['A']['group']})['wave']['revision'],'references':[]}),'BF_WAVE_USED'),['SKU.W02'])
 case('SKU.L01','Real shipment computes 16 wash plus 3 middle-size finishing PCS',shipment,['SKU.W02'])
 case('SKU.L02','Receipt retains agreed SKU tariff',receive,['SKU.L01'])
 case('SKU.L03','Final FG costs follow physical recipients exactly',qc,['SKU.L02'])
 case('SKU.H01','Current SKU summary is weighted by actual remaining stock',hpp_current,['SKU.L03'])
 case('SKU.H02','Location brand grade and future-date boundaries',hpp_filters,['SKU.L03'])
 case('SKU.H03.OBS','Historical stock versus calculation-time cost observation',historical_hpp_observation,['SKU.L03'])
 case('SKU.R01','Range 31-33 to 31-34 leaves old lots and snapshots unchanged',rename_range,['SKU.L03'])
 case('SKU.C01','Two concurrent group edits have one winner and one stale refusal',race,['SKU.R01'])
 save()
if __name__=='__main__':main()
