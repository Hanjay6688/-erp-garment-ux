"""Plan the exact DE96 tree after the current Permanent Root receipt passes.

Produces reviewable Git-tree input only. Never edits a checkout, changes a
branch, contacts GitHub, imports ERP, or starts a qualification. The existing
source/whole-graph/Root gates must still pass on the materialized result.
"""
from hashlib import sha1
from pathlib import Path
import argparse,ast,json

from intake_common import GitBytes,exact,pin,require
from intake_sku27 import strict
import intake_complete_de30 as child
import intake_permanent_focused as parent

NS=child.NS
RECEIPT=NS+'PERMANENT_PARENT_ROOT_ACTUAL_INTAKE.json'
WORKFLOW=child.WORKFLOW
# Populate only after the exact current Permanent canonical Root intake passes.
# A plausible JSON status or an older passing receipt cannot arm this planner.
ACTUAL_ACCEPTED_PARENT_RECEIPT=None

# Exact bounded protocol route on the old unarmed DE caller. No financial,
# SQL, reader, Native callback, privilege or runtime change is supplied.
PARENT_PROTOCOL_BEFORE="""    required=dict(status='ROOT_VERIFIED_PERMANENT_S05_NATIVE4_BROWSER2_ALL5',head=PARENT_HEAD,
        complete6_qualified=True,actual_Native_cases=4,actual_browser_cases=2,
        retained_join37_fresh_case_credit=0,package_all_five=True,prior_runs_aggregated=False,
        production_go=False,independent_acceptance=False)"""
PARENT_PROTOCOL_AFTER="""    required=dict(status='ROOT_VERIFIED_PERMANENT_S05_RETAINED4_FRESH_BROWSER2_ALL5',head=PARENT_HEAD,
        complete6_qualified=True,actual_Native_cases=0,actual_browser_cases=2,fresh_cases=2,
        retained_Native_cases=4,retained_cases=4,retained_cases_are_not_fresh=True,candidate_case_coverage=6,
        fresh6_one_attempt=False,prior_runs_aggregated=True,source_invariant_reuse=True,financial_groups_rerun=False,
        retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        retained_join37_fresh_case_credit=0,package_all_five=True,
        production_go=False,independent_acceptance=False)"""


def protocol_route(raw):
    text=raw.decode();exact(text.count(PARENT_PROTOCOL_BEFORE),1,'DE_ACTIVATION_EXACT_ORIGINAL_PARENT_PROTOCOL')
    result=text.replace(PARENT_PROTOCOL_BEFORE,PARENT_PROTOCOL_AFTER,1)
    exact(result.count(PARENT_PROTOCOL_AFTER),1,'DE_ACTIVATION_ONE_TRUTHFUL_RETAINED4_FRESH2_PROTOCOL')
    exact(result.replace(PARENT_PROTOCOL_AFTER,PARENT_PROTOCOL_BEFORE,1).encode(),raw,
        'DE_ACTIVATION_ENTIRE_ORIGINAL_PARENT_PROTOCOL_RECOVERED')
    compile(result,'DE-activation-retained4-fresh2-protocol-only','exec')
    return result.encode(),dict(before=PARENT_PROTOCOL_BEFORE,after=PARENT_PROTOCOL_AFTER,count=1,
        exact_original_recovered=True,financial_SQL_or_Native_callbacks_changed=False)


def typed(value,expected,label):
    require(type(value)is type(expected)and value==expected,'DE_ACTIVATION_EXACT_TYPED_'+label)


def accepted_parent(raw):
    require(ACTUAL_ACCEPTED_PARENT_RECEIPT is not None,'DE_ACTIVATION_ACTUAL_PARENT_ROOT_PIN_PENDING')
    exact(pin(raw),ACTUAL_ACCEPTED_PARENT_RECEIPT,'DE_ACTIVATION_EXACT_ACCEPTED_ROOT_RECEIPT_BYTES')
    value=strict(raw)
    required=dict(status='ROOT_VERIFIED_PERMANENT_S05_RETAINED4_FRESH_BROWSER2_ALL5',
        head=parent.HEAD,tree=parent.TREE,run_id=parent.RUN,job_id=parent.JOB,
        actual_Native_cases=0,actual_browser_cases=2,fresh_cases=2,retained_Native_cases=4,retained_cases=4,
        retained_cases_are_not_fresh=True,candidate_case_coverage=6,complete6_qualified=True,package_all_five=True,
        fresh6_one_attempt=False,prior_runs_aggregated=True,source_invariant_reuse=True,financial_groups_rerun=False,
        retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,retained_root_receipt=parent.ROOT_PIN,
        retained_join37_fresh_case_credit=0,
        reader_remains_installed=True,global_writer_or_permission_or_lock_closure=False,
        Afui_positive_HPP_zero_reimbursement_coverage=False,D1_E_qualified=False,
        production_go=False,independent_acceptance=False)
    require(all(v is not None for v in(parent.HEAD,parent.TREE,parent.RUN,parent.JOB)),
        'DE_ACTIVATION_ACTUAL_PARENT_IDENTITY_UNBOUND')
    require(type(value)is dict,'DE_ACTIVATION_ACTUAL_ROOT_RECEIPT_OBJECT_REQUIRED')
    for name,expected in required.items():typed(value.get(name),expected,'PARENT_'+name)
    for name in('qualified_complete_sources','qualified_parent37','actual_current_browser_raw_assets'):
        require(type(value.get(name))is dict and bool(value[name]),'DE_ACTIVATION_COMPLETE_ROOT_EVIDENCE_REQUIRED:'+name)
    require(value.get('synthetic_receipt_not_an_actual_qualification')is not True,
        'DE_ACTIVATION_SYNTHETIC_RECEIPT_REFUSED')
    return value


def literal_route(raw,name,before,after):
    matches=[n for n in ast.parse(raw).body if isinstance(n,ast.Assign)and len(n.targets)==1
        and isinstance(n.targets[0],ast.Name)and n.targets[0].id==name]
    exact(len(matches),1,'DE_ACTIVATION_ONE_LITERAL:'+name);node=matches[0].value
    typed(ast.literal_eval(node),before,'ORIGINAL_LITERAL_'+name)
    lines=raw.splitlines(keepends=True)
    start=sum(map(len,lines[:node.lineno-1]))+node.col_offset
    end=sum(map(len,lines[:node.end_lineno-1]))+node.end_col_offset
    previous=raw[start:end];following=repr(after).encode()
    require(previous!=following,'DE_ACTIVATION_LITERAL_MUST_CHANGE:'+name)
    result=raw[:start]+following+raw[end:]
    compile(result,'DE-activation-source-only/'+name,'exec')
    exact(result[:start]+previous+result[start+len(following):],raw,'DE_ACTIVATION_EXACT_LITERAL_REVERSE:'+name)
    return result,dict(name=name,before=previous.decode(),after=following.decode(),exact_original_recovered=True)


def plan(root,prepared_head,prepared_tree,raw_receipt):
    # Fail before Git/source access for an older, partial, or wrong receipt.
    receipt=accepted_parent(raw_receipt)
    typed(prepared_tree,child.PREPARED_TREE,'PREPARED_TREE')
    require(child.PARENT_HEAD is None and child.PARENT_TREE is None,'DE_ACTIVATION_EXPECTS_UNARMED_CHILD_ROOT_GATE')
    with GitBytes(root,prepared_head,prepared_tree)as git:
        original=child.source(git)
        declaration=strict(git.read(NS+'SOURCE.json'))
        old_paths=set(declaration['files'])|{NS+'SOURCE.json'}
        exact(len(old_paths),94,'DE_ACTIVATION_ORIGINAL_OWN94')
        values={name:git.read(name)for name in sorted(old_paths)};before=dict(values)
        parent_entries=git.entries(receipt['head'])
        exact(git.git('rev-parse',receipt['head']+'^{tree}').decode().strip(),receipt['tree'],'DE_ACTIVATION_ACTUAL_PARENT_TREE')
        exact(len(parent_entries),14169,'DE_ACTIVATION_ENTIRE_CURRENT_PARENT14169')
        require(not(old_paths|{RECEIPT,WORKFLOW})&set(parent_entries),'DE_ACTIVATION_ADDITIVE_NAMESPACES_ONLY')
        routes=[]
        for name,bindings in((NS+'admission.py',(
            ('PARENT_HEAD',None,receipt['head']),('PARENT_RECEIPT',None,pin(raw_receipt)))),
            (NS+'source.py',(
            ('BASE',declaration['base_head'],receipt['head']),('TREE',declaration['base_tree'],receipt['tree'])))):
            for key,old,new in bindings:
                values[name],route=literal_route(values[name],key,old,new);routes.append(dict(path=name,**route))
        values[NS+'admission.py'],protocol=protocol_route(values[NS+'admission.py'])
        values[RECEIPT]=raw_receipt
        values[WORKFLOW]=values[NS+'native30.workflow.yml.txt']
        origin=strict(values[NS+'REPAIRED_PERMANENT_REBASE_ORIGIN.json'])
        origin['actual_permanent_parent_binding']=dict(head=receipt['head'],tree=receipt['tree'],
            run_id=receipt['run_id'],job_id=receipt['job_id'],receipt=pin(raw_receipt),
            source_preparation_not_DE_acceptance=True,unchanged_parent_blobs_and_modes=14169,
            own_paths=96,own_source_pins=95,literal_routes=routes,parent_protocol_route=protocol,actual_DE_cases=0,
            production_go=False,independent_acceptance=False)
        values[NS+'REPAIRED_PERMANENT_REBASE_ORIGIN.json']=(json.dumps(origin,indent=2)+'\n').encode()
        declaration['base_head']=receipt['head'];declaration['base_tree']=receipt['tree']
        declaration['actual_parent_qualification']=dict(head=receipt['head'],tree=receipt['tree'],
            run_id=receipt['run_id'],job_id=receipt['job_id'],receipt=pin(raw_receipt))
        declaration['files']={name:pin(raw)for name,raw in sorted(values.items())if name!=NS+'SOURCE.json'}
        exact(len(declaration['files']),95,'DE_ACTIVATION_EXACT_OWN95_PINS')
        values[NS+'SOURCE.json']=(json.dumps(declaration,indent=2)+'\n').encode()
        exact(len(values),96,'DE_ACTIVATION_EXACT_OWN96')
        changed=sorted(name for name in old_paths if values[name]!=before[name])
        exact(changed,sorted(NS+n for n in('SOURCE.json','REPAIRED_PERMANENT_REBASE_ORIGIN.json','admission.py','source.py')),
            'DE_ACTIVATION_ONLY_FOUR_OWN_BINDING_FILES_CHANGE')
        elements=[]
        for name,raw in sorted(values.items()):
            item=dict(path=name,mode='100644',type='blob')
            if name in before and before[name]==raw:item['sha']=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            else:item['content']=raw.decode()
            elements.append(item)
    request=dict(repository_full_name='Hanjay6688/-erp-garment-ux',base_tree_sha=receipt['tree'],tree_elements=elements)
    review=dict(status='DE96_ACTUAL_PARENT_BOUND_TREE_PLAN_ONLY_NOT_EXECUTED',
        prepared_source_head=prepared_head,prepared_source_tree=prepared_tree,parent_head=receipt['head'],
        parent_tree=receipt['tree'],parent_root_receipt=pin(raw_receipt),
        source_before=original,unchanged_parent_blobs_and_modes=14169,own_paths=96,own_source_pins=95,
        unchanged_own_files=90,changed_own_files=changed,new_paths=[RECEIPT,WORKFLOW],
        literal_routes=routes,parent_protocol_route=protocol,workflow_bytes_equal_reviewed_template=True,actual_DE_cases=0,
        must_materialize_check_entire_source_and_Root_gate_before_activation=True,
        production_go=False,independent_acceptance=False)
    return request,review


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--prepared-head',required=True);parser.add_argument('--prepared-tree',required=True)
    parser.add_argument('--parent-root-receipt',type=Path,required=True);parser.add_argument('--tree-output',type=Path,required=True)
    parser.add_argument('--review-output',type=Path,required=True);args=parser.parse_args()
    require(not args.tree_output.exists()and not args.review_output.exists(),'DE_ACTIVATION_EXISTING_PLAN_NOT_OVERWRITTEN')
    request,review=plan(args.source,args.prepared_head,args.prepared_tree,args.parent_root_receipt.read_bytes())
    with args.tree_output.open('x')as output:output.write(json.dumps(request,ensure_ascii=False))
    with args.review_output.open('x')as output:output.write(json.dumps(review,indent=2)+'\n')
    print(json.dumps({key:review[key]for key in('status','own_paths','own_source_pins','unchanged_own_files','actual_DE_cases')}))


if __name__=='__main__':main()
