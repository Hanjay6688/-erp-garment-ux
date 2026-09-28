"""Independent B11 REST boundary, with real public positive controls."""
import uuid

def run(b,C):
    names={'be_post_conversion_v1','be_set_redye_price_v1','save_product_conversion_action_v1','bd_set_charge_price_v1','bc_value_custody_v1','save_pocket_fabric_action_v1'}
    helpers=b.sql("select p.proname,p.oid::regprocedure::text,p.proargnames,p.pronargs,pg_get_function_identity_arguments(p.oid) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp' and p.proname=any(%s) order by p.proname",(sorted(names),))
    assert {r[0] for r in helpers}==names,helpers
    public=b.rpc('erp_get_product_conversion_workspace_v1',{'p_filters':{}});assert isinstance(public,dict)
    outcomes=[]
    for who in ['owner','viewer','anonymous']:
        token=b.KEYS['ANON_KEY'] if who=='anonymous' else b.TOKENS[who]
        base={'apikey':b.KEYS['ANON_KEY'],'Authorization':'Bearer '+token}
        for name,signature,args,nargs,identity in helpers:
            payload={k:({} if k in ['p_payload','p_filters'] else 'POST' if k in ['p_action'] else 'FG' if k=='p_origin' else None if k=='p_rework' else str(uuid.uuid4())) for k in args[:nargs]}
            for profile in [None,'erp']:
                headers={**base,**({'Content-Profile':profile} if profile else {})}
                status,body=b.request('http://127.0.0.1:54328/rest/v1/rpc/'+name,payload,headers)
                assert status in (401,403,404,406),{'actor':who,'helper':name,'status':status,'body':body}
                if profile=='erp':assert isinstance(body,dict) and body.get('code')=='PGRST106',(status,body)
                outcomes.append({'actor':who,'private_signature':signature,'profile':profile or 'public default','http_status':status,'response':body})
        status,body=b.request('http://127.0.0.1:54328/rest/v1/be_redye_services_v1?select=id',headers={**base,'Accept-Profile':'erp'},method='GET')
        assert status==406 and body.get('code')=='PGRST106',(status,body)
        outcomes.append({'actor':who,'private_table':'be_redye_services_v1','profile':'erp','http_status':status,'response':body})
    return {'public_owner_positive':True,'real_helper_signatures':[r[1] for r in helpers],'checks':outcomes,'schema_configuration':'Only public exposed, explicit erp profile also tested; no widening during audit','sql_helper_permissions':'Separately exercised in baseline native AUTH.PRIVATE'}
