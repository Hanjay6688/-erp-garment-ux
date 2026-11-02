"""Plan only own FREE40 after exact actual DE30 acceptance; no ERP/ref writes."""
from hashlib import sha1
from pathlib import Path
import argparse,json
from intake_common import GitBytes,exact,fields,pin,require
from intake_sku27 import strict
from prepare_de_activation import literal_route
import intake_free3 as child
import intake_complete_de30 as parent

ACTUAL_ACCEPTED_DE_RECEIPT={'bytes': 19912, 'sha256': 'b63c44c459a36ad285c788890132ae4910569044f432e9851dff90f8061192e2'}
NS=child.NS
RECEIPT=NS+'DE30_PARENT_ROOT_ACTUAL_INTAKE.json'
WORKFLOW=child.WORKFLOW
NESTED_PARENT_MANIFESTS=(
    ('scripts/cp7_special_free_date_on_de/SOURCE.json',(NS+'admission.py',)),
    ('scripts/cp7_current_de_free_date/SOURCE.json',(
        'scripts/cp7_special_free_date_on_de/SOURCE.json',NS+'admission.py',NS+'source.py')),
)


def rebind_nested_parent_manifests(values,before):
    """Rebind exactly four existing pins, from the leaf manifest upward."""
    routes=[]
    for path,dependencies in NESTED_PARENT_MANIFESTS:
        raw=before[path];value=strict(raw)
        exact((json.dumps(value,indent=2)+'\n').encode(),raw,'FREE_ACTIVATION_CANONICAL_NESTED_MANIFEST:'+path)
        own=[]
        for name in dependencies:
            previous=pin(before[name]);following=pin(values[name])
            exact(value['files'][name],previous,'FREE_ACTIVATION_EXACT_OLD_NESTED_PIN:'+path+':'+name)
            require(previous!=following,'FREE_ACTIVATION_NESTED_DEPENDENCY_MUST_CHANGE:'+name)
            value['files'][name]=following
            own.append(dict(path=path,key=['files',name],before=previous,after=following,
                only_existing_parent_pin_changed=True,exact_original_recovered=True))
        values[path]=(json.dumps(value,indent=2)+'\n').encode()
        for route in reversed(own):value['files'][route['key'][1]]=route['before']
        exact((json.dumps(value,indent=2)+'\n').encode(),raw,'FREE_ACTIVATION_ENTIRE_NESTED_MANIFEST_RECOVERED:'+path)
        routes.extend(own)
    exact(len(routes),4,'FREE_ACTIVATION_EXACT_FOUR_NESTED_PARENT_PINS')
    return routes


def accepted_parent(raw):
    require(ACTUAL_ACCEPTED_DE_RECEIPT is not None,'FREE_ACTIVATION_ACTUAL_DE30_ROOT_PIN_PENDING')
    exact(pin(raw),ACTUAL_ACCEPTED_DE_RECEIPT,'FREE_ACTIVATION_EXACT_ROOT_ACCEPTED_DE30_BYTES')
    require(all(v is not None for v in(parent.HEAD,parent.TREE,parent.RUN,parent.JOB)),
        'FREE_ACTIVATION_ACTUAL_DE30_IDENTITY_PENDING')
    value=strict(raw)
    fields(value,dict(status='ROOT_VERIFIED_CURRENT_COMPLETE_D1_E_NATIVE30_ALL5',head=parent.HEAD,
        tree=parent.TREE,run_id=parent.RUN,job_id=parent.JOB,actual_Native_cases=30,actual_D1_cases=13,
        actual_E_cases=17,actual_browser_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        package_all_five=True,prior_runs_aggregated=False,retained_permanent6_fresh_case_credit=0,
        D_complete=False,E_complete=False,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False),'FREE_ACTIVATION_ACTUAL_ACCEPTED_CURRENT_DE30')
    for key in('qualified_complete_DE_sources','source_admission','runtime_supervision','read_only_system_metadata'):
        require(type(value.get(key))is dict and bool(value[key]),'FREE_ACTIVATION_COMPLETE_ACTUAL_EVIDENCE:'+key)
    require(value.get('synthetic_receipt_not_an_actual_qualification')is not True,'FREE_ACTIVATION_SYNTHETIC_RECEIPT_REFUSED')
    return value


def plan(root,prepared_head,prepared_tree,raw_receipt):
    receipt=accepted_parent(raw_receipt)
    exact(prepared_tree,child.PREPARED_TREE,'FREE_ACTIVATION_EXACT_CURRENT_OWN38_TREE')
    require(child.PARENT_HEAD is None and child.PARENT_TREE is None,'FREE_ACTIVATION_CHILD_MUST_STILL_BE_UNARMED')
    with GitBytes(root,prepared_head,prepared_tree)as g:
        before_source=child.source(g);declaration=strict(g.read(NS+'SOURCE.json'))
        old_paths=set(declaration['files'])|{NS+'SOURCE.json'};exact(len(old_paths),38,'FREE_ACTIVATION_EXACT_OWN38')
        values={name:g.read(name)for name in sorted(old_paths)};before=dict(values)
        base=g.entries(receipt['head']);exact(len(base),14265,'FREE_ACTIVATION_COMPLETE_CURRENT_DE_PARENT14265')
        exact(g.git('rev-parse',receipt['head']+'^{tree}').decode().strip(),receipt['tree'],'FREE_ACTIVATION_EXACT_ACTUAL_DE_TREE')
        require(not(old_paths|{RECEIPT,WORKFLOW})&set(base),'FREE_ACTIVATION_DISJOINT_ADDITIVE_OWN_SOURCE')
        routes=[]
        for name,bindings in((NS+'admission.py',(
            ('PARENT_HEAD',None,receipt['head']),('PARENT_RECEIPT',None,pin(raw_receipt)))),
            (NS+'source.py',(
            ('BASE',declaration['base_head'],receipt['head']),('TREE',declaration['base_tree'],receipt['tree'])))):
            for key,old,new in bindings:
                values[name],route=literal_route(values[name],key,old,new);routes.append(dict(path=name,**route))
        nested=rebind_nested_parent_manifests(values,before)
        origin=strict(values[NS+'ORIGIN.json']);guard=origin['source_preflight_origin']
        exact(len(guard['changes']),12,'FREE_ACTIVATION_PRESERVE_ALL_TWELVE_SOURCE_ROUTES')
        for key,old,new in(('BASE',declaration['base_head'],receipt['head']),('TREE',declaration['base_tree'],receipt['tree'])):
            previous=key+'='+repr(old);following=key+'='+repr(new)
            matches=[item for item in guard['changes']if item['after']==previous]
            exact(len(matches),1,'FREE_ACTIVATION_UPDATE_EXISTING_SOURCE_ROUTE_ONLY:'+key)
            matches[0]['after']=following
        # Replay all twelve from the immutable original, rather than append a
        # thirteenth route that loses or duplicates earlier workflow controls.
        original=g.read(guard['path'],guard['head']);text=original.decode()
        exact(pin(original),{k:guard[k]for k in('bytes','sha256')},'FREE_ACTIVATION_EXACT_ORIGINAL_SOURCE_GUARD')
        for route in guard['changes']:
            exact(text.count(route['before']),route['count'],'FREE_ACTIVATION_EXACT_SOURCE_GUARD_ROUTE')
            text=text.replace(route['before'],route['after'],route['count'])
        exact(text.encode(),values[NS+'source.py'],'FREE_ACTIVATION_ALL_TWELVE_ROUTES_PRESERVE_NEW_GUARD')
        for route in reversed(guard['changes']):
            exact(text.count(route['after']),route['count'],'FREE_ACTIVATION_EXACT_GUARD_ROUTE_REVERSE')
            text=text.replace(route['after'],route['before'],route['count'])
        exact(text.encode(),original,'FREE_ACTIVATION_WHOLE_ORIGINAL_GUARD_RECOVERED')
        actual=dict(head=receipt['head'],tree=receipt['tree'],run_id=receipt['run_id'],job_id=receipt['job_id'],receipt=pin(raw_receipt))
        origin['actual_DE30_parent_binding']=dict(actual,source_preparation_not_FREE_acceptance=True,
            unchanged_parent_blobs_and_modes=14265,own_paths=40,own_source_pins=39,literal_routes=routes,
            nested_parent_pin_routes=nested,
            financial_SQL_or_Native_callbacks_changed=False,actual_FREE_cases=0,production_go=False,independent_acceptance=False)
        values[NS+'ORIGIN.json']=(json.dumps(origin,indent=2)+'\n').encode()
        values[RECEIPT]=raw_receipt;values[WORKFLOW]=values[NS+'native3.workflow.yml.txt']
        declaration['base_head']=receipt['head'];declaration['base_tree']=receipt['tree'];declaration['actual_parent_qualification']=actual
        declaration['files']={name:pin(raw)for name,raw in sorted(values.items())if name!=NS+'SOURCE.json'}
        exact(len(declaration['files']),39,'FREE_ACTIVATION_EXACT39_PINS')
        values[NS+'SOURCE.json']=(json.dumps(declaration,indent=2)+'\n').encode()
        changed=sorted(name for name in old_paths if values[name]!=before[name])
        exact(changed,sorted([path for path,_ in NESTED_PARENT_MANIFESTS]+
            [NS+n for n in('admission.py','source.py','SOURCE.json','ORIGIN.json')]),
            'FREE_ACTIVATION_ONLY_FOUR_OWN_BINDING_FILES_AND_TWO_NESTED_MANIFESTS_CHANGE')
        exact(len(values),40,'FREE_ACTIVATION_EXACT_OWN40')
        elements=[]
        for name,raw in sorted(values.items()):
            item=dict(path=name,mode='100644',type='blob')
            if name in before and before[name]==raw:item['sha']=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            else:item['content']=raw.decode()
            elements.append(item)
    request=dict(repository_full_name='Hanjay6688/-erp-garment-ux',base_tree_sha=receipt['tree'],tree_elements=elements)
    review=dict(status='FREE40_ACTUAL_DE30_BOUND_TREE_PLAN_ONLY_NOT_EXECUTED',prepared_source_head=prepared_head,
        prepared_source_tree=prepared_tree,parent_head=receipt['head'],parent_tree=receipt['tree'],parent_root_receipt=pin(raw_receipt),
        source_before=before_source,unchanged_parent_blobs_and_modes=14265,own_paths=40,own_source_pins=39,
        unchanged_own_files=32,changed_own_files=changed,new_paths=[RECEIPT,WORKFLOW],literal_routes=routes,
        nested_parent_pin_routes=nested,
        source_guard_routes=12,complete_original_guard_recovered=True,workflow_equal_reviewed_template=True,
        actual_FREE_cases=0,must_materialize_check_entire_source_and_Root_gate_before_activation=True,
        production_go=False,independent_acceptance=False)
    return request,review


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--prepared-head',required=True)
    p.add_argument('--prepared-tree',required=True);p.add_argument('--parent-root-receipt',type=Path,required=True)
    p.add_argument('--tree-output',type=Path,required=True);p.add_argument('--review-output',type=Path,required=True);a=p.parse_args()
    require(not a.tree_output.exists()and not a.review_output.exists(),'FREE_ACTIVATION_EXISTING_PLAN_NOT_OVERWRITTEN')
    request,review=plan(a.source,a.prepared_head,a.prepared_tree,a.parent_root_receipt.read_bytes())
    with a.tree_output.open('x')as out:out.write(json.dumps(request,ensure_ascii=False))
    with a.review_output.open('x')as out:out.write(json.dumps(review,indent=2)+'\n')
    print(json.dumps({k:review[k]for k in('status','own_paths','own_source_pins','unchanged_own_files','actual_FREE_cases')}))
