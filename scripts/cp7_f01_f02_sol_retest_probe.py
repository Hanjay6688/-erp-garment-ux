"""Independent F01/F02 retest on frozen ee869982. Disposable database only."""
from copy import deepcopy
from pathlib import Path
import hashlib, json, traceback, uuid
import psycopg
import cp7_wip_bundle as bundle
import cp7_snapshot_cases as snap
import cp7_wip_cases as kernel
import cp7_wip_source_cases as cutting
import cp6_auditor_runner as native
import cp6_t3_package_run as package
import cp7_p03_identity_probe as policy

OUT=Path(__file__).resolve().parents[1]/'cp6-proof/t3/CP7_F01_F02_SOL_RETEST.json'
FROZEN='ee8699829bc53799e5f840bb5490059e456fa81a'

def refs(k):
    return [{'kind':'INDEPENDENT_RETEST','id':k,'revision':'1'}]

def vector(r):
    return [kernel.total(r,k+'_pcs') for k in ('input','wip','fg','bs')]

def normalize(cur,facts):
    return cur.execute('select cp7_wip.normalize_cutting(%s::jsonb)',(json.dumps(facts),)).fetchone()[0]

def cases(cur,today):
    def finance_and_stale():
        f=snap.fixture(cur,today)
        subject,role=snap.custom_actor(cur,finance=True)
        r=snap.create(cur,f['root'],subject=subject)
        frozen=deepcopy(snap.stored(cur,r['run_id']))
        assert 'lot_cost' in frozen['sources'] and 'lot_cost' in r['counts'],r
        assert snap.read(cur,r['run_id'],'lot_cost',subject=subject)['page']['rows']
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.view'",(role,))
        a=snap.read(cur,r['run_id'],subject=subject)
        assert 'lot_cost' not in a['counts'] and not a['financial_captured'],a
        snap.refused(cur,lambda:snap.read(cur,r['run_id'],'lot_cost',subject=subject),'CP7_FINANCIAL_ACCESS_DENIED')
        snap.mutate(cur,f,6)
        later=snap.read(cur,r['run_id'],'sales_lines',subject=subject)
        assert later['source_state']=='ARCHIVED_STALE' and snap.stored(cur,r['run_id'])==frozen,later
        assert int(later['page']['rows'][0]['qty_pcs'])==2,later
        return {'status':'PASS','revoked_cost_denied':True,'operational_projection_redacted':True,
                'backdated_source_change_archived':True,'original_sales_pcs':2}

    def matcher_recompute():
        physical=kernel.call(cur,'reconcile',kernel.graph())
        policy_yield={'position_key':'A-sew','eligible_input_pcs':'20','numerator':'1','denominator':'1',
                      'basis':'ASSUMED','assumption_id':'sol-retest-yield','refs':refs('yield')}
        positions=kernel.call(cur,'yield',physical,[policy_yield])
        n=next(x for x in positions['positions'] if x['key']=='A-sew')
        source={'key':n['key'],'quality':'COMPLETE','size_id':n['size_id'],'confirmed_target':None,
                'constraints':[{'field':'color','value':'RED','required':True,'basis':'FACT'}],
                'refs':deepcopy(n['refs'])}
        target={'key':'SKU-RED','size_id':n['size_id'],
                'constraints':[{'field':'color','value':'RED','required':True,'basis':'FACT'}],
                'refs':refs('target-v1')}
        edge={'key':'E','position_key':n['key'],'target_key':target['key'],'size_id':n['size_id'],
              'input_pcs':'10','projected_good_pcs':'10','match':'CANDIDATE_MATCH',
              'refs':source['refs']+target['refs']}
        a={'scenario_id':'sol-retest','scope_id':'all','complete_scope':True,'edges':[edge],
           'matching':{'snapshot_id':positions['snapshot_id'],'sources':[source],'targets':[target]}}
        assert kernel.call(cur,'match',source,target)['match']=='CANDIDATE_MATCH'
        good=kernel.call(cur,'allocate',positions,a)
        assert good['status']=='FEASIBLE',good
        wrong=deepcopy(a);wrong['matching']['targets'][0]['constraints'][0]['value']='BLUE'
        assert kernel.call(cur,'match',source,wrong['matching']['targets'][0])['match']=='INCOMPATIBLE'
        kernel.check(cur,lambda:kernel.call(cur,'allocate',positions,wrong),'CP7_WIP_INELIGIBLE_ALLOCATION')
        forged=deepcopy(a);forged['edges'][0]['match']='CONFIRMED_TARGET'
        kernel.check(cur,lambda:kernel.call(cur,'allocate',positions,forged),'CP7_WIP_MATCH_STALE')
        stale=deepcopy(a);stale['matching']['snapshot_id']='old-snapshot'
        kernel.check(cur,lambda:kernel.call(cur,'allocate',positions,stale),'CP7_WIP_MATCH_SNAPSHOT')
        missing=deepcopy(a);del missing['matching']
        result=kernel.call(cur,'allocate',positions,missing)
        assert result=={'status':'UNKNOWN','reason':'MATCHING_FACTS_REQUIRED'},result
        return {'status':'PASS','compatible':'FEASIBLE','hard_fact_mismatch':'DENIED',
                'forged_label':'DENIED','old_snapshot':'DENIED','legacy_label_only':result}

    def matcher_reference_integrity():
        physical=kernel.call(cur,'reconcile',kernel.graph())
        positions=kernel.call(cur,'yield',physical,[{'position_key':'A-sew','eligible_input_pcs':'20',
            'numerator':'1','denominator':'1','basis':'ASSUMED','assumption_id':'sol-ref-yield','refs':refs('yield')}])
        n=next(x for x in positions['positions'] if x['key']=='A-sew')
        s={'key':n['key'],'quality':'COMPLETE','size_id':n['size_id'],'confirmed_target':None,
           'constraints':[],'refs':deepcopy(n['refs'])}
        t={'key':'SKU-31','size_id':n['size_id'],'constraints':[],'refs':refs('target')}
        a={'scenario_id':'sol-refs','scope_id':'all','complete_scope':True,
           'edges':[{'key':'E','position_key':n['key'],'target_key':t['key'],'size_id':n['size_id'],
                     'input_pcs':'3','projected_good_pcs':'3','match':'CANDIDATE_MATCH','refs':s['refs']+t['refs']}],
           'matching':{'snapshot_id':positions['snapshot_id'],'sources':[s],'targets':[t]}}
        assert kernel.call(cur,'allocate',positions,a)['status']=='FEASIBLE'
        tests=[]
        for kind in ('source_revision','target_edge_revision','duplicate_source','missing_target'):
            x=deepcopy(a)
            if kind=='source_revision':x['matching']['sources'][0]['refs']=refs('falsified')
            elif kind=='target_edge_revision':x['matching']['targets'][0]['refs']=refs('target-v2')
            elif kind=='duplicate_source':x['matching']['sources'].append(deepcopy(s))
            else:x['matching']['targets']=[]
            code={'source_revision':'CP7_WIP_MATCH_BINDING','target_edge_revision':'CP7_WIP_MATCH_BINDING',
                  'duplicate_source':'CP7_WIP_MATCH_DUPLICATE','missing_target':'CP7_WIP_MATCH_FACTS'}[kind]
            kernel.check(cur,lambda x=x:kernel.call(cur,'allocate',positions,x),code)
            tests.append(kind)
        return {'status':'PASS','rejected':tests}

    def cancelled_source_metaphor():
        f=cutting.fixture(cur,today)
        capture=cutting.capture(cur,[f['group']])
        assert vector(capture['result'])==[100,80,15,5],capture
        facts=deepcopy(cur.execute('select facts from cp7_wip.runs where id=%s',(capture['run_id'],)).fetchone()[0])
        qc=next(q for q in facts['facts']['qc'] if int(q['bs_pcs'])==5)
        bs=next(b for b in facts['facts']['bs'] if b['qc_item_id']==qc['id'])
        qc['status']='REVERSED';bs['status']='CANCELLED'
        reversed_only=normalize(cur,facts)
        assert reversed_only['status']=='COMPLETE' and vector(reversed_only)==[100,100,0,0],reversed_only
        negative=deepcopy(facts);negative['facts']['qc'][-1]['status']='POSTED'
        rejected=normalize(cur,negative)
        assert rejected['status']=='CONFLICT' and rejected['reason']=='CANCELLED_BS_SOURCE_UNPROVEN',rejected
        active=deepcopy(facts)
        new_qc=deepcopy(qc);new_qc['id']=str(uuid.uuid4());new_qc['status']='POSTED'
        new_qc['good_pcs']='7';new_qc['bs_pcs']='3'
        new_bs=deepcopy(bs);new_bs['id']=str(uuid.uuid4());new_bs['qc_item_id']=new_qc['id']
        new_bs['qty_pcs']='3';new_bs['status']='OPEN'
        active['facts']['qc'].append(new_qc);active['facts']['bs'].append(new_bs)
        current=normalize(cur,active)
        assert current['status']=='COMPLETE' and vector(current)==[100,90,7,3],current
        assert cutting.read(cur,capture['run_id'])['result']==capture['result']
        return {'status':'PASS','baseline':[100,80,15,5],
                'reversed_cancelled':[100,100,0,0],'new_active_after_cancel':[100,90,7,3],
                'unproven_cancel':'CONFLICT','archived_run_unchanged':True}

    return [('SOL_F01_FINANCE_REVOCATION_STALE',finance_and_stale),
            ('SOL_F02_MATCH_RECOMPUTED',matcher_recompute),
            ('SOL_F02_MATCH_REF_INTEGRITY',matcher_reference_integrity),
            ('SOL_F02_CANCELLED_BS_NEW_SOURCE',cancelled_source_metaphor)]

def run():
    report={'label':'CP7_F01_F02_SOL_RETEST','status':'INCOMPLETE','candidate_source_commit':FROZEN,
            'bundle_sha256':hashlib.sha256(bundle.bundle().encode()).hexdigest(),'production_go':False}
    installed=False
    try:
        with psycopg.connect(package.boundary.ADMIN) as conn,conn.cursor() as cur:
            policy.bf.verified(cur)
            before=package.boundary.snapshot(cur)
            public_before=native.public_state(cur)
            conn.rollback()
            cur.execute(bundle.bundle(),prepare=False);conn.commit();installed=True
            policy.verify(cur);conn.rollback()
        report['native']=native.strict_group('CP7_F01_F02_SOL_RETEST',cases,policy.verify)
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
        report['status']='PASS' if group.get('status')=='PASS' and report.get('cp6_restored') else 'INCOMPLETE'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({'status':report['status'],'counts':group.get('counts'),'cp6_restored':report.get('cp6_restored'),
                          'error':report.get('error'),'traceback':report.get('traceback')},default=str),flush=True)
    assert report['status']=='PASS',report
    return {'status':'PASS','audit_disposition':'BOUNDED_RETEST_PASS','native_cases':group.get('counts'),
            'cp6_restored':True,'independent_acceptance':False,'production_go':False}

if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
