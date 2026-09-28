"""Inspect legitimate configured-free entry points without inventing a free policy.

Positive controls and zero/status probes run as authenticated OWNER inside one
rolled-back transaction. A missing enabling contract is BLOCKED acceptance, not
a demonstrated financial bug. This supplements original IND-08, not a new bug.
"""
import json, traceback, hashlib
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb
import suite as s
import daily as d

EVENTS=[]; RESULTS=[]
def save():
    out={'candidate':'e96db5a270da5aa6d0f12c3812ac1c0542df938e','origin':'own remaining-gap contract investigation','results':RESULTS,'production_go':False,
         'boundary':'Supported positive controls plus discovery; never substitutes a seeded zero for legitimate free configuration'}
    (s.OUT/'free-contract-results.json').write_text(json.dumps(out,indent=2,default=str)+'\n')
    (s.OUT/'free-contract-events.json').write_text(json.dumps(EVENTS,indent=2,default=str)+'\n')

def main():
    fixture=json.loads((s.OUT/'daily-fixture.json').read_text());s.CTX.update(fixture['identity'])
    vendor=s.uid()
    with psycopg.connect(s.DSN) as setup:
        setup.execute("select set_config('app.change_reason','Independent free contract master prerequisite',true)")
        setup.execute("insert into erp.laundry_vendors(id,vendor_code,vendor_name) values(%s,'AUD-FREE-CONTRACT','Independent free contract vendor')",(vendor,))
    # Real positive batch source from our own already-verified physical adapter.
    d.precursor('GF');f=d.F['GF'];C=s.CTX
    policies=s.admin('select policy_key,status,value,version from erp.bd_policy_settings_v1 order by policy_key')
    versions={x[0]:x[3] for x in policies};before=s.counts()
    def run_probe(c,label,action,payload,accepted_required=False):
        event={'label':label,'api':'public.erp_save_laundry_bd_action_v1','action':action,'payload':payload,'request':s.uid()}
        try:
            with c.transaction():
                result=c.execute('select public.erp_save_laundry_bd_action_v1(%s,%s,%s::uuid)',(action,Jsonb(payload),event['request'])).fetchone()[0]
                event.update(accepted=True,response=result)
        except psycopg.Error as e:
            if e.sqlstate in ('42601','42703','42P01','42883'):raise
            event.update(accepted=False,sqlstate=e.sqlstate,error=str(e))
        EVENTS.append(event)
        if accepted_required:assert event['accepted'],event
        return event.get('response')
    with s.actor_conn() as c:
        try:
            c.execute('select 1') # Establish outer transaction before savepoints.
            def rpc(label,action,payload,positive=False):return run_probe(c,label,action,payload,positive)
            reason='Independent explicit price contract inspection; transaction rolled back'
            for key,value in [('LAU_DEC01',{'units':['BATCH','MINIMUM']}),('LAU_DEC05',{'scopes':['MODEL'],'fallback':'BASE_RATE'})]:
                rpc('legitimate supported policy control','SET_POLICY',{'policy_key':key,'operation':'SET','expected_version':str(versions[key]),'value':value,'reason':reason},True)
            comp=rpc('valid component','SAVE_COMPONENT',{'vendor_id':vendor,'component_code':'AUD-FREE-C','component_name':'Independent fee','is_active':True,'reason':reason},True)['component_id']
            pkg=rpc('valid package','SAVE_PACKAGE',{'vendor_id':vendor,'package_code':'AUD-FREE-P','package_name':'Independent package','component_ids':[comp],'is_active':True,'reason':reason},True)['package_id']
            base={'effective_from':'2026-09-01T08:00:00+07:00','reason':reason}
            routes=[('component','SAVE_COMPONENT_RATE',{'component_id':comp,'rate_status':'KNOWN'}),
                    ('package','SAVE_PACKAGE_RATE',{'package_id':pkg}),
                    ('process','SAVE_PROCESS_RATE',{'vendor_id':vendor,'wash_process_id':C['process']}),
                    ('scoped','SAVE_SCOPED_RATE',{'vendor_id':vendor,'wash_process_id':C['process'],'scope':'MODEL','model_id':C['model']})]
            for name,action,payload in routes:
                rpc(name+' positive control',action,{**payload,**base,'rate_per_pcs':'1.37'},True)
                rpc(name+' zero probe',action,{**payload,**base,'effective_from':'2026-09-02T08:00:00+07:00','rate_per_pcs':'0.00'})
            for status in ('FREE','WAIVED','UNKNOWN'):
                p={'component_id':comp,**base,'effective_from':'2026-09-03T08:00:00+07:00','rate_status':status}
                if status!='UNKNOWN':p['rate_per_pcs']='0.00'
                rpc('explicit '+status+' status','SAVE_COMPONENT_RATE',p,status=='UNKNOWN')
            terms={'vendor_id':vendor,'pricing_mode':'RATE','pricing_unit':'BATCH','expected_version':'0','reason':reason,'minimum_charge':'1.37'}
            r=rpc('minimum positive control','SAVE_VENDOR_TERMS',terms,True)
            rpc('minimum zero probe','SAVE_VENDOR_TERMS',{**terms,'expected_version':str(r['row_version']),'minimum_charge':'0.00'})
            # Both pricing paths have identical valid physical inputs; price alone differs.
            dl=d.dp('GF')['delivery'];dl['vendor_id']=vendor
            version=s.admin('select row_version from erp.cutting_groups where id=%s',(f['group'],),one=True)
            rpc('batch zero probe','POST_PRICED_DELIVERY',{'delivery':dl,'expected_version':str(version),'pricing':{'lump_sum':'0.00'}})
            rpc('batch positive lifecycle control','POST_PRICED_DELIVERY',{'delivery':dl,'expected_version':str(version),'pricing':{'lump_sum':'23.57'}},True)
            workspace=c.execute('select public.erp_get_laundry_bd_workspace_v1(%s)',(Jsonb({'vendor_id':vendor}),)).fetchone()[0]
            RESULTS.append({'id':'GAP-FREE.CONTROLS','status':'PASS','title':'Valid controls for every supported price surface examined','observation':{'positive_routes':['component','package','process','scoped','minimum','batch public shipment','UNKNOWN null'],'workspace_keys':sorted(workspace),'policies':policies}})
        finally:c.rollback()
    s.eq(s.counts(),before,'Price/policy probes fully rolled back')
    s.eq(s.admin('select policy_key,status,value,version from erp.bd_policy_settings_v1 order by policy_key'),policies,'Policy state fully restored')
    zero=[x for x in EVENTS if 'zero probe' in x['label'] or x['label'] in ('explicit FREE status','explicit WAIVED status')]
    accepted=[x for x in zero if x['accepted']]
    if accepted:
        RESULTS.append({'id':'GAP-FREE.CONFIGURED','status':'BLOCKED','title':'An accepted zero route requires semantic/lifecycle evaluation','observation':accepted,'reason':'Do not infer legitimate free policy merely from accepted zero; evaluate actual supported contract next.'})
    else:
        RESULTS.append({'id':'GAP-FREE.CONFIGURED','status':'BLOCKED','title':'Legitimate configured-free lifecycle prerequisite remains absent','reason':'All examined price surfaces require positive known amounts; component status is KNOWN/UNKNOWN; six public policy schemas have no free/waiver enabling field. Zero/status refusals are observations, not a proven configured-free financial bug.','observation':{'probes':len(zero),'accepted':0,'policies_examined':[x[0] for x in policies],'legacy_free_rewash':'separate PASS evidence in edges-results.json'}})

if __name__=='__main__':
    try:main()
    except Exception as e:RESULTS.append({'id':'GAP-FREE.SETUP','status':'BLOCKED','classification':'auditor fixture/adapter; inspect traceback','error':str(e),'traceback':traceback.format_exc()})
    finally:save();print(json.dumps(RESULTS,default=str),flush=True)
    raise SystemExit(0 if all(x['status']=='PASS' for x in RESULTS) else 1)
