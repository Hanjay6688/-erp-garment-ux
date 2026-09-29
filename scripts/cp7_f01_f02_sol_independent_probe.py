"""Independent frozen F01/F02 cross checks. Disposable DB only."""
from pathlib import Path
import hashlib, json, traceback, uuid
import psycopg
import cp7_wip_bundle as bundle
import cp7_snapshot_cases as snap
import cp7_identity_cases as identity
import cp7_wip_cases as kernel
import cp7_wip_production_cases as production
import cp7_wip_source_cases as cutting
import cp6_auditor_runner as native
import cp6_t3_package_run as package
import cp7_p03_identity_probe as policy

OUT=Path(__file__).resolve().parents[1]/'cp6-proof/t3/CP7_F01_F02_SOL_INDEPENDENT.json'
def refs(tag):
    return [{'kind':'INDEPENDENT_ORACLE','id':tag,'revision':'1'}]

def probes(cur,today):
    def f01_f02_cross_identity():
        f=identity.fixture(cur,today)
        sku=f['skus'][0]
        row=identity.row(identity.get(cur,f['skus']),sku)
        identity.apply(cur,[identity.proposal(row,state='STOPPED')])
        first=snap.create(cur,f['root'])
        frozen=snap.stored(cur,first['run_id'])
        assert first['source_state']=='CURRENT',first
        identity.move(cur,f)
        now=identity.row(identity.get(cur,f['skus']),sku)
        archived=snap.read(cur,first['run_id'])
        assert now['policy']['quality']=='MEMBERSHIP_CHANGED' and now['policy']['state'] is None,now
        assert archived['source_state']=='ARCHIVED_STALE' and snap.stored(cur,first['run_id'])==frozen,archived
        assert archived['page']['rows']==first['page']['rows'],archived
        return {'status':'PASS','oracle':'membership update does not rewrite capture or preserve STOPPED applicability',
                'policy_quality':now['policy']['quality'],'source_state':archived['source_state']}

    def f02_mixed_origin_permutation():
        c=cutting.fixture(cur,today)
        o=production.opening(cur,today)
        scope=production.scope([c['group']],[o['item']])
        first=production.capture(cur,scope)
        again=production.capture(cur,scope,first['request_id'])
        assert first['run_id']==again['run_id'],(first,again)
        assert production.vector(first)==[108,88,15,5,0,0],first
        assert len({p['pool_key'] for p in first['result']['totals']})==3,first
        return {'status':'PASS','oracle':'one source capture, immutable same-key replay, true-origin conservation',
                'vector':production.vector(first),'run_id':first['run_id']}

    def f02_match_binding():
        g=kernel.graph()
        physical=kernel.call(cur,'reconcile',g)
        policy_yield={'position_key':'A-sew','eligible_input_pcs':'20','numerator':'1','denominator':'1',
                      'basis':'ASSUMED','assumption_id':'independent-full-yield','refs':refs('yield')}
        projected=kernel.call(cur,'yield',physical,[policy_yield])
        source={'key':'A-sew','quality':'COMPLETE','size_id':'31','confirmed_target':None,
                'constraints':[{'field':'color','value':'RED','required':True,'basis':'FACT'}],'refs':refs('source')}
        target={'key':'SKU-BLUE','size_id':'31','constraints':[{'field':'color','value':'BLUE','required':True,'basis':'FACT'}],
                'refs':refs('target')}
        hard_match=kernel.call(cur,'match',source,target)
        assert hard_match['match']=='INCOMPATIBLE',hard_match
        edge={'key':'E','position_key':'A-sew','target_key':'SKU-BLUE','size_id':'31','input_pcs':'10',
              'projected_good_pcs':'10','match':'CANDIDATE_MATCH','refs':refs('allocation')}
        scenario={'scenario_id':'cross-check','scope_id':'all','complete_scope':True,'edges':[edge]}
        allocation=kernel.call(cur,'allocate',projected,scenario)
        assert allocation['status']=='FEASIBLE',allocation
        edge['match']='INCOMPATIBLE'
        kernel.check(cur,lambda:kernel.call(cur,'allocate',projected,scenario),'CP7_WIP_INELIGIBLE_ALLOCATION')
        return {'status':'PASS','oracle':'hard FACT color mismatch must be bound to allocation edge',
                'match_target':hard_match,'forged_label_allocation':allocation['status'],
                'finding':'ALLOCATOR_TRUSTS_CALLER_MATCH_LABEL'}

    return [('SOL_F01_F02_CROSS_IDENTITY',f01_f02_cross_identity),
            ('SOL_F02_MIXED_ORIGIN_REPLAY',f02_mixed_origin_permutation),
            ('SOL_F02_MATCH_LABEL_BINDING',f02_match_binding)]

def verify(cur):
    return policy.verify(cur)

def run():
    report={'label':'CP7_F01_F02_SOL_INDEPENDENT','status':'INCOMPLETE','candidate_source_commit':'17e85404c9c5f088875099d7875be6342ca6b266',
            'bundle_sha256':hashlib.sha256(bundle.bundle().encode()).hexdigest(),'production_go':False}
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            policy.bf.verified(cur)
            before=package.boundary.snapshot(cur)
            public_before=native.public_state(cur)
            conn.rollback()
            cur.execute(bundle.bundle(),prepare=False);conn.commit();installed=True
            verify(cur);conn.rollback()
        report['native']=native.strict_group('CP7_F01_F02_SOL_INDEPENDENT',probes,verify)
    except Exception as e:
        report.update(error=str(e),traceback=traceback.format_exc())
    finally:
        if installed:
            with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
                cur.execute('drop owned by cp7_policy cascade;drop role cp7_policy;drop owned by cp7_capture cascade;drop role cp7_capture',prepare=False)
                conn.commit()
                report['cp6_restored']=package.boundary.snapshot(cur)==before and native.public_state(cur)==public_before
                conn.rollback();policy.bf.verified(cur);conn.rollback()
        group=report.get('native',{})
        report['status']='PROBED_WITH_FINDING' if group.get('status')=='PASS' and report.get('cp6_restored') else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({'status':report['status'],'native':group.get('counts'),'cp6_restored':report.get('cp6_restored'),'error':report.get('error'),'traceback':report.get('traceback')},default=str),flush=True)
    assert report['status']=='PROBED_WITH_FINDING',report
    return {'status':'PASS','audit_disposition':'F02_MATCH_BINDING_FOUND','native_cases':group.get('counts'),\
            'cp6_restored':True,'independent_acceptance':False,'production_go':False}
if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
