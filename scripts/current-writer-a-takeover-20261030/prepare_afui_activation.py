"""Plan the existing Afui15 on the actual accepted FREE3; no ERP/ref writes."""
from hashlib import sha1
from pathlib import Path
import argparse,json
from intake_common import GitBytes,exact,fields,pin,require
from intake_sku27 import strict
from prepare_de_activation import literal_route
import intake_afui15 as child
import intake_free_focused as parent

ACTUAL_ACCEPTED_FREE_RECEIPT={'bytes': 11136, 'sha256': '680e161ba747bba2e12c01406fbdb69b38858031a52b44d0aafef9bd6674f350'}
NS=child.NS
RECEIPT=NS+'FREE3_PARENT_ROOT_ACTUAL_INTAKE.json'
WORKFLOW=child.WORKFLOW


def focused_parent_admission(raw):
    """One exact typed-receipt route; all five identity bindings stay unarmed.

    This changes only how a future actual, fully accepted parent describes
    its retained cases. It does not accept the failed origin or create proof.
    """
    before="""    expected = dict(status='ROOT_VERIFIED_CURRENT_COMPLETE_DE_FREE_DATE_NATIVE3_ALL5',
        head=PARENT_HEAD, tree=PARENT_TREE, run_id=PARENT_RUN, job_id=PARENT_JOB,
        actual_Native_cases=3, actual_business_cases=3, actual_browser_cases=0,
        actual_Auth_HTTP_cases=0, actual_two_session_races=0, complete3_qualified=True,
        package_all_five=True, prior_runs_aggregated=False, retained_DE30_fresh_case_credit=0,"""
    after="""    expected = dict(status='ROOT_VERIFIED_CURRENT_COMPLETE_DE_FREE_DATE_RETAINED3_COMMITTED_ALL5',
        head=PARENT_HEAD, tree=PARENT_TREE, run_id=PARENT_RUN, job_id=PARENT_JOB,
        actual_Native_cases=0, actual_business_cases=0, actual_browser_cases=0,
        actual_Auth_HTTP_cases=0, actual_two_session_races=0, complete3_qualified=True,
        retained_Native_cases=3, retained_cases_are_not_fresh=True, candidate_case_coverage=3,
        source_invariant_reuse=True, financial_groups_rerun=False, actual_new_committed_witness=True,
        retained_original_run_conclusion='failure', failed_run_relabelled_PASS=False,
        package_all_five=True, prior_runs_aggregated=True, retained_DE30_fresh_case_credit=0,"""
    text=raw.decode();exact(text.count(before),1,'AFUI_FOCUSED_PARENT_EXACT_ORIGINAL_TYPED_RECEIPT_BLOCK')
    require(after not in text,'AFUI_FOCUSED_PARENT_RECEIPT_ROUTE_APPLIED_ONCE')
    derived=text.replace(before,after,1)
    exact(derived.count(after),1,'AFUI_FOCUSED_PARENT_EXACT_REVERSE_ANCHOR')
    exact(derived.replace(after,before,1).encode(),raw,'AFUI_FOCUSED_PARENT_ENTIRE_ORIGINAL_ADMISSION_RECOVERED')
    compile(derived,'Afui-exact-focused-parent-admission-source','exec')
    return derived.encode(),dict(before=before,after=after,count=1,
        retained_cases=3,fresh_cases=0,failed_origin_accepted=False,actual_parent_still_required=True)


def accepted_parent(raw):
    require(ACTUAL_ACCEPTED_FREE_RECEIPT is not None,'AFUI_ACTIVATION_ACTUAL_FREE3_ROOT_PIN_PENDING')
    exact(pin(raw),ACTUAL_ACCEPTED_FREE_RECEIPT,'AFUI_ACTIVATION_EXACT_ACCEPTED_CURRENT_FREE3_BYTES')
    require(all(v is not None for v in(parent.HEAD,parent.TREE,parent.RUN,parent.JOB)),
        'AFUI_ACTIVATION_ACTUAL_FREE3_IDENTITY_PENDING')
    value=strict(raw)
    fields(value,dict(status='ROOT_VERIFIED_CURRENT_COMPLETE_DE_FREE_DATE_RETAINED3_COMMITTED_ALL5',head=parent.HEAD,
        tree=parent.TREE,run_id=parent.RUN,job_id=parent.JOB,actual_Native_cases=0,actual_business_cases=0,
        actual_browser_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        retained_Native_cases=3,retained_cases_are_not_fresh=True,candidate_case_coverage=3,
        source_invariant_reuse=True,financial_groups_rerun=False,actual_new_committed_witness=True,
        retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        complete3_qualified=True,package_all_five=True,prior_runs_aggregated=True,retained_DE30_fresh_case_credit=0,
        GOOD_eligibility_policy_decided=False,Afui_GOOD_nonpayable_path_complete=False,D_complete=False,E_complete=False,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False),
        'AFUI_ACTIVATION_EXACT_ACTUAL_FREE3_ROOT_ACCEPTANCE')
    for key in('qualified_complete_DE_FREE_date_sources','source_admission','runtime_supervision',
        'retained_actual_full22_case_boundaries','actual_used_refusal_raw_boundary','retained_root_receipt'):
        require(type(value.get(key))is dict and bool(value[key]),'AFUI_ACTIVATION_COMPLETE_ACTUAL_ROOT_EVIDENCE:'+key)
    require(value.get('synthetic_receipt_not_an_actual_qualification')is not True,'AFUI_ACTIVATION_SYNTHETIC_RECEIPT_REFUSED')
    return value


def plan(root,prepared_head,prepared_tree,raw_receipt):
    receipt=accepted_parent(raw_receipt)
    exact(prepared_tree,child.PREPARED_TREE,'AFUI_ACTIVATION_EXACT_REVIEWED_OWN89_AND_UI_TREE')
    require(all(v is None for v in(child.PARENT_HEAD,child.PARENT_TREE,child.PARENT_RUN,child.PARENT_JOB)),
        'AFUI_ACTIVATION_CHILD_STILL_UNARMED')
    with GitBytes(root,prepared_head,prepared_tree)as g:
        source=child.source(g);old_base=g.entries(child.PREPARED_BASE)
        own=set(g.tree)-set(old_base);exact(len(own),89,'AFUI_ACTIVATION_EXACT_REPAIRED_OWN89')
        values={name:g.read(name)for name in sorted(own|child.UI_CHANGED)};before=dict(values)
        base=g.entries(receipt['head']);exact(len(base),14310,'AFUI_ACTIVATION_ENTIRE_CURRENT_FREE45_PARENT14310')
        exact(g.git('rev-parse',receipt['head']+'^{tree}').decode().strip(),receipt['tree'],'AFUI_ACTIVATION_EXACT_CURRENT_PARENT_TREE')
        require(not(own|{RECEIPT,WORKFLOW})&set(base),'AFUI_ACTIVATION_ONLY_ADDITIVE_OWN_NAMESPACES')
        for name in child.UI_CHANGED:
            exact(base[name],old_base[name],'AFUI_ACTIVATION_CURRENT_UI_PREDECESSOR_UNCHANGED:'+name)
        routes=[]
        values[NS+'admission.py'],semantic_route=focused_parent_admission(values[NS+'admission.py'])
        for key,value in(('PARENT_HEAD',receipt['head']),('PARENT_TREE',receipt['tree']),
            ('PARENT_RUN',receipt['run_id']),('PARENT_JOB',receipt['job_id']),('PARENT_RECEIPT',pin(raw_receipt))):
            values[NS+'admission.py'],route=literal_route(values[NS+'admission.py'],key,None,value);routes.append(route)
        values[RECEIPT]=raw_receipt;values[WORKFLOW]=values[NS+'afui15.workflow.yml.txt']
        declaration=strict(values[NS+'SOURCE.json'])
        declaration['base_head']=receipt['head'];declaration['base_tree']=receipt['tree']
        # The existing manifest enumerates executable/template inputs. The
        # new JSON receipt is bound by the exact five admission literals.
        declaration['files']={name:pin(values[name])for name in sorted(set(declaration['files'])|{WORKFLOW})}
        exact(len(declaration['files']),58,'AFUI_ACTIVATION_EXACT58_EXECUTABLE_AND_TEMPLATE_PINS')
        values[NS+'SOURCE.json']=(json.dumps(declaration,indent=2)+'\n').encode()
        changed=sorted(name for name in before if values[name]!=before[name])
        exact(changed,sorted(NS+n for n in('admission.py','SOURCE.json')),'AFUI_ACTIVATION_ONLY_TWO_OWN_BINDING_FILES_CHANGE')
        exact(len(values),95,'AFUI_ACTIVATION_EXACT_OWN91_PLUS_FOUR_EXISTING_UI_BLOBS')
        elements=[]
        for name,raw in sorted(values.items()):
            item=dict(path=name,mode='100644',type='blob')
            if name in before and before[name]==raw:item['sha']=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            else:item['content']=raw.decode()
            elements.append(item)
    request=dict(repository_full_name='Hanjay6688/-erp-garment-ux',base_tree_sha=receipt['tree'],tree_elements=elements)
    review=dict(status='AFUI91_ACTUAL_FOCUSED_FREE45_BOUND_TREE_PLAN_ONLY_NOT_EXECUTED',prepared_source_head=prepared_head,
        prepared_source_tree=prepared_tree,parent_head=receipt['head'],parent_tree=receipt['tree'],parent_root_receipt=pin(raw_receipt),
        source_before=source,unchanged_parent_paths=14306,own_paths=91,source_pins=58,unchanged_own_paths=87,
        exact_original_UI_derivations_retained=4,new_UI_paths_retained=5,changed_own_paths=changed,
        new_paths=[RECEIPT,WORKFLOW],literal_routes=routes,typed_parent_receipt_route=semantic_route,
        parent_retained_Native_cases=3,parent_actual_fresh_Native_cases=0,workflow_equal_reviewed_template=True,
        actual_Afui_cases=0,financial_SQL_Native_callbacks_or_UI_changed=False,
        must_materialize_check_entire_source_and_Root_gate_before_activation=True,production_go=False,independent_acceptance=False)
    return request,review


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--prepared-head',required=True)
    p.add_argument('--prepared-tree',required=True);p.add_argument('--parent-root-receipt',type=Path,required=True)
    p.add_argument('--tree-output',type=Path,required=True);p.add_argument('--review-output',type=Path,required=True);a=p.parse_args()
    require(not a.tree_output.exists()and not a.review_output.exists(),'AFUI_ACTIVATION_EXISTING_PLAN_NOT_OVERWRITTEN')
    request,review=plan(a.source,a.prepared_head,a.prepared_tree,a.parent_root_receipt.read_bytes())
    with a.tree_output.open('x')as out:out.write(json.dumps(request,ensure_ascii=False))
    with a.review_output.open('x')as out:out.write(json.dumps(review,indent=2)+'\n')
    print(json.dumps({k:review[k]for k in('status','own_paths','source_pins','unchanged_own_paths','actual_Afui_cases')}))
