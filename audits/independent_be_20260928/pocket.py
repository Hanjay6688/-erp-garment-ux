"""Independent pocket stock, historical period, correction and lock checks."""
import native as n, flows as f, suite as s, daily as d
import json,threading,time,copy
from decimal import Decimal as D
from concurrent.futures import ThreadPoolExecutor
from psycopg.types.json import Jsonb
import psycopg
C=n.C;X=f.X;A=n.A;eq=n.eq;uid=n.uid

def ws(q='',who='owner'):return n.rpc('erp_get_pocket_fabric_workspace_v1',[q],who)
def preview(start='2026-09-05',end='2026-09-09',who='owner'):return n.rpc('erp_preview_pocket_fabric_period_v1',[start,end],who)
def live_payload(mode='USED',quantity='6.75',**changes):
    roll=next(x for x in ws()['rolls'] if x['id']==C['pocket_roll'])
    return {'roll_id':roll['id'],'location_id':roll['location_id'],'expected_revision':roll['revision'],'mode':mode,'quantity':quantity,'date':'2026-09-12','reason':'Independent actual shared pocket fabric issue',**changes}
def live_stock():
    r=n.pocket('REGISTER',{'material_id':C['pocket_material'],'reason':'Independent dedicated pocket fabric'})
    before=f.matqty(C['pocket_material']);beforefg=n.fp(['fg_stock_movements','fg_lots','hpp_versions']);p=live_payload();q=uid();post=n.pocket('POST',p,q)
    X['pocket_live']={'request':q,'payload':p,'response':post};eq(f.matqty(C['pocket_material']),before-D('6.75'));eq(n.fp(['fg_stock_movements','fg_lots','hpp_versions']),beforefg)
    journal=A("select j.id::text,j.transaction_date::text,l.debit,l.credit from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.source_id=%s and l.account_id=erp.account_id('OTHER_EXPENSE')",(post['id'],));eq(sum(z[2]-z[3] for z in journal),D('116.71'))
    hist=next(x for x in ws()['history'] if x['id']==post['id']);eq(D(hist['current_cost']),D('116.71'));eq(D(hist['issued_quantity']),D('6.75'))
    before=n.fp();eq(n.pocket('POST',p,q),post);eq(n.fp(),before)
    return {'register':r,'post':post,'history':hist,'direct_expense_journal':journal,'raw_input_value':'116.7075','stock_now':f.matqty(C['pocket_material']),'fg_hpp_unchanged':True}
def remaining_zero():
    p=live_payload('REMAINING','0',date='2026-09-13');before=f.matqty(C['pocket_material']);r=n.pocket('POST',p);eq(f.matqty(C['pocket_material']),D(0));h=next(x for x in ws()['history'] if x['id']==r['id']);eq(D(h['issued_quantity']),before)
    rv=n.pocket('REVERSE',{'id':r['id'],'expected_version':h['row_version'],'reason':'Independent inverse of complete-roll issue'});eq(f.matqty(C['pocket_material']),before)
    return {'post':r,'zero_stock':True,'issued':before,'reversal':rv,'stock_restored':before}

def history_setup():
    # Genuine historical sewing sheets, one normal and one special contractor.
    special=uid();C['special']=special
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('app.change_reason','Independent special-contractor prerequisite',true)");c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],))
        c.execute("insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required) values(%s,'BE-AUD-AFUI','Independent special contractor','MANDOR',false)",(special,))
        c.execute("insert into erp.contractor_hpp_policy_versions(contractor_id,is_special,effective_from,contractor_role_snapshot,attendance_required_snapshot,reason) values(%s,true,'2026-09-01','MANDOR',false,'Explicit synthetic special-contractor policy')",(special,))
    ent=[('OPENING_BALANCE_ITEM',[{'balance_type':'FINISHED_GOODS','product_sku':'BE-AUD-POCKET-FG','brand_code':'AUD-brand','model_code':'AUD-DAY','color_name':'BE-POCKET','size_code':'AUD-1','location_code':'AUD-fg','qty':'7','unit_cost':'1234.57','hpp_input_method':'MANUAL','quality_grade':'GRADE_A','opening_source_key':'BE-AUD-HIST-FG','control_key':'FG'}]),
      ('OPENING_CONTROL',[{'control_key':'FG','balance_type':'FINISHED_GOODS','qty':'7','amount':'8641.99'}]),
      ('OPENING_POCKET_USAGE',[{'document_number':'BE-AUD-HIST-USE','line_number':'1','physical_date':'2026-09-06','material_sku':'BE-AUD-POCKET','qty':'6.75','amount':'116.71','allocation_status':'UNALLOCATED','control_key':'USE','control_qty':'6.75','control_amount':'116.71'}]),
      ('OPENING_POCKET_SEWING',[{'document_number':'BE-AUD-HIST-SEW','line_number':'1','physical_date':'2026-09-07','contractor_code':'AUD-DAY','qty':'7','target_kind':'FINISHED_GOODS','target_source_key':'BE-AUD-HIST-FG','control_key':'SEW','control_qty':'13'}, {'document_number':'BE-AUD-HIST-SEW','line_number':'2','physical_date':'2026-09-08','contractor_code':'BE-AUD-AFUI','qty':'6','target_kind':'COGS','product_sku':'BE-AUD-POCKET-FG','sold_reference':'Independent historical dispatch and sale six PCS','control_key':'SEW','control_qty':'13'}])]
    before=f.matqty(C['pocket_material']);native_sew=A('select count(*) from erp.sewing_terminal_events',one=True);b=f.imported('POCKET-HISTORY',ent)
    eq(f.matqty(C['pocket_material']),before,'Historical use cannot issue current fabric again');eq(A('select count(*) from erp.sewing_terminal_events',one=True),native_sew)
    usage=A('select id::text from erp.be_pocket_usage_v1 where batch_id=%s',(b['batch_id'],),one=True)
    lot=A("select m.lot_id::text from erp.fg_stock_movements m join erp.initial_import_opening_stock_sources k on k.opening_item_id=m.source_id where k.batch_id=%s and k.source_key='BE-AUD-HIST-FG'",(b['batch_id'],),one=True)
    X['pocket_history']={'batch':b['batch_id'],'usage':usage,'lot':lot};eq(n.value(lot),D('8641.99'))
    return {'import':b,'source':X['pocket_history'],'source_material_stock_unchanged':before,'native_sewing_count_unchanged':native_sew}
def preview_clean():
    before=n.fp();r=preview();eq(n.fp(),before);eq(D(r['amount']),D('116.71'));eq(D(r['quantity']),D(13));eq(r['can_post'],True);eq(r['economic_date'],'2026-09-10');X['pocket_preview']=r
    return r
def allocate():
    p=preview();before=n.fp(['material_stock_movements','fg_stock_movements','sewing_terminal_events']);req=uid();payload={'period_start':p['period_start'],'period_end':p['period_end'],'expected_revision':p['revision'],'reason':'Independent allocation based on 7 plus 6 actual historical sewing'}
    r=n.pocket('POST_PERIOD',payload,req);X['pocket_period']={'result':r,'payload':payload,'request':req};eq(n.fp(['material_stock_movements','fg_stock_movements','sewing_terminal_events']),before)
    check=shares('62.84','53.87');eq(n.value(X['pocket_history']['lot']),D('8704.83'))
    journals=A('select j.transaction_date::text,j.economic_date::text from erp.pocket_period_events e join erp.journal_entries j on j.id=e.journal_entry_id where e.pool_id=%s',(r['id'],));eq(journals,[('2026-09-10','2026-09-10')])
    snap=n.fp();eq(n.pocket('POST_PERIOD',payload,req),r);eq(n.fp(),snap)
    return {'post':r,'shares':check,'journal_dates':journals,'physical_unchanged':before,'replay_one_effect':True}
def shares(good,sold):
    pool=X['pocket_period']['result']['id']
    # Direct target-event amounts and COGS journal; calculation helper is not oracle.
    fg=A('select coalesce(sum(e.new_amount-e.previous_amount),0) from erp.be_pocket_target_events_v1 e where pool_id=%s',(pool,),one=True)
    cogs=A("select coalesce(sum(l.debit-l.credit),0) from erp.pocket_period_events e join erp.journal_entries j on j.id=e.journal_entry_id join erp.journal_lines l on l.journal_entry_id=j.id where e.pool_id=%s and l.account_id=erp.account_id('COGS') and j.status in('POSTED','REVERSED')",(pool,),one=True)
    eq(fg,D(good));eq(cogs,D(sold));return {'finished_goods':fg,'historically_sold_cogs':cogs,'total':fg+cogs}
def correction(amount,expected,shares_expected):
    h=X['pocket_history'];before=n.fp(['material_stock_movements','fg_stock_movements','sewing_terminal_events']);p={'usage_id':h['usage'],'amount':amount,'economic_date':'2026-09-19','expected_amount':expected,'reason':'Independent documented historical source correction'}
    req=uid();r=n.pocket('CORRECT_OPENING_USAGE',p,req);eq(n.fp(['material_stock_movements','fg_stock_movements','sewing_terminal_events']),before);check=shares(*shares_expected)
    snap=n.fp();eq(n.pocket('CORRECT_OPENING_USAGE',p,req),r);eq(n.fp(),snap)
    return {'correction':r,'allocated':check,'physical_unchanged':before,'replay_no_effect':True}
def cancel():
    ident=X['pocket_period']['result']['id'];state=next(p for p in ws()['periods'] if p['id']==ident);before=n.fp(['material_stock_movements','fg_stock_movements','sewing_terminal_events']);r=n.pocket('CANCEL_PERIOD',{'id':ident,'expected_revision':state['revision'],'reason':'Independent period cancellation with no physical reversal'})
    eq(n.fp(['material_stock_movements','fg_stock_movements','sewing_terminal_events']),before);eq(n.value(X['pocket_history']['lot']),D('8641.99'));check=shares('0','0')
    return {'cancel':r,'net_cost_shares':check,'base_fg_restored':'8641.99','physical_unchanged':True}
def overlap():return n.reject(lambda:n.pocket('POST_PERIOD',{**X['pocket_period']['payload'],'reason':'Independent overlapping period'}),'tumpang tindih')
def stale_correct():return n.reject(lambda:n.pocket('CORRECT_OPENING_USAGE',{'usage_id':X['pocket_history']['usage'],'amount':'131.00','expected_amount':'116.71','economic_date':'2026-09-19','reason':'Independent stale source amount'}),'STALE_VERSION')
def race():
    p=preview();payload={'period_start':p['period_start'],'period_end':p['period_end'],'expected_revision':p['revision'],'reason':'Independent two-operator allocation race'};bar=threading.Barrier(2)
    controls=[]
    for who in ['owner','admin']:
        with s.actor_conn(who) as c:
            control=c.execute('select public.erp_save_pocket_fabric_action_v1(%s,%s,%s::uuid)',('POST_PERIOD',Jsonb(payload),uid())).fetchone()[0];controls.append({'actor':who,'positive_response':control,'rolled_back':True});c.rollback()
    n.E.append({'pocket_race_positive_controls':controls})
    def go(who):
        bar.wait()
        try:return {'actor':who,'accepted':True,'response':n.pocket('POST_PERIOD',payload,who=who)}
        except psycopg.Error as e:return {'actor':who,'accepted':False,'error':str(e),'sqlstate':e.sqlstate}
    with ThreadPoolExecutor(2) as pool:rs=list(pool.map(go,['owner','admin']))
    eq(sum(x['accepted'] for x in rs),1);assert all('PERMISSION' not in x.get('error','') for x in rs),rs;X['pocket_period']={'result':next(x['response'] for x in rs if x['accepted']),'payload':payload}
    return {'actors':[C['owner'],C['admin']],'results':rs}
def source_guard():
    r=n.imp('CREATE',{'batch_code':'BE-AUD-BLOCKED-HIST','cutover_date':'2026-09-10','notes':'Independent historical membership conflict'})
    r=n.imp('SAVE_FILE',{'batch_id':r['batch_id'],'expected_revision':r['revision'],'entity':'OPENING_POCKET_USAGE','filename':'additional.csv','rows':[{'source_row_no':1,'payload':{'document_number':'BE-AUD-CONFLICT','line_number':'1','physical_date':'2026-09-07','material_sku':'BE-AUD-POCKET','qty':'1','amount':'17.29','allocation_status':'UNALLOCATED','control_key':'C','control_qty':'1','control_amount':'17.29'}}]})
    before=n.fp();v=n.imp('VALIDATE',{'batch_id':r['batch_id'],'expected_revision':r['revision']});eq(n.fp(),before);eq(v['error_rows'],1);errors=A('select validation_errors from erp.migration_staging_rows where batch_id=%s',(r['batch_id'],));assert 'BE_POCKET_PERIOD_ACTIVE' in str(errors),errors
    return {'validation':v,'errors':errors,'no_business_effect':True}
def unrelated_import():
    b=f.imported('UNRELATED',[('CUSTOMER',[{'customer_code':'BE-AUD-UNRELATED','customer_name':'Independent unrelated customer'}])]);return {'import':b,'other_domain_works_while_pocket_active':True}

def run():
    f.load()
    f.case('POCKET-01','6.75 units at 17.29 book 116.71 expense and leave garment HPP unchanged',live_stock)
    f.case('POCKET-02','Remaining zero consumes only balance; inverse restores it',remaining_zero)
    for name,changes in [('NEG',{'quantity':'-1'}),('EXCESS',{'quantity':'999'}),('FUTURE',{'date':'2099-01-01'}),('BEFORE_SOURCE',{'date':'2026-09-09'}),('STALE',{'expected_revision':'stale'}),('FRACTION_TEXT',{'quantity':'NaN'})]:
        f.case('POCKET-14.'+name,'Invalid pocket stock input '+name,lambda changes=changes:n.reject(lambda:n.pocket('POST',live_payload(**changes))))
    f.case('SETUP-POCKET-HISTORICAL','Own historical source and 7 normal plus 6 special-contractor sewing sheets',history_setup)
    f.case('POCKET-03-06-10','Historical preview uses 13 actual sewing and first books at cutover',preview_clean)
    f.case('POCKET-04-05-08','Allocation splits 62.84 FG plus 53.87 COGS without reissuing stock',allocate)
    f.case('POCKET-12.OVERLAP','Overlapping active allocation refused',overlap)
    f.case('POCKET-09.UP','Historical source increase to 130.34 reaches 70.18 FG and 60.16 COGS',lambda:correction('130.34','116.71',('70.18','60.16')))
    f.case('POCKET-12.STALE','Stale source correction refused',stale_correct)
    f.case('POCKET-09.DOWN','Historical source decrease restores 62.84 FG and 53.87 COGS',lambda:correction('116.71','130.34',('62.84','53.87')))
    f.case('POCKET-13','Adding history inside an active period is blocked',source_guard)
    f.case('NONPO-12.CONTROL','Unrelated import remains available during active allocation',unrelated_import)
    f.case('POCKET-11','Cancelling allocation restores expense, FG and COGS without stock changes',cancel)
    f.case('POCKET-12.RACE','Owner and admin cannot both allocate the same period',race)
    f.case('POCKET-15','Active replacement allocation can also be cancelled',cancel)
    f.case('ACCESS-POCKET.VIEW','Regular viewer cannot read financial pocket workspace',lambda:n.reject(lambda:ws(who='staff')))
    f.case('ACCESS-POCKET.PREVIEW','Regular viewer cannot run allocation preview',lambda:n.reject(lambda:preview(who='staff')))
    f.persist()
if __name__=='__main__':run()
