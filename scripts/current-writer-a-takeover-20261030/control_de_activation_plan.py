"""Pure DE tree assembly model, never actual parent or Native acceptance."""
from pathlib import Path
from unittest.mock import patch
from hashlib import sha256,sha1
import argparse,json
import prepare_de_activation as planner


def control(root,head,tree):
    real_git=planner.GitBytes
    with real_git(root,head,tree)as git:
        declaration=planner.strict(git.read(planner.NS+'SOURCE.json'))
    base=declaration['base_head'];base_tree=declaration['base_tree']
    model_head='f'*40;model_tree='e'*40
    # Intentionally not JSON and not a valid Git parent. The request exists
    # only in memory and cannot pass any actual Root or runtime gate.
    model_raw=b'SYNTHETIC_ASSEMBLY_ONLY_NOT_A_JSON_RECEIPT'
    model_receipt=dict(head=model_head,tree=model_tree,run_id=1,job_id=1)

    class ModelGit:
        def __init__(self,*args):self.real=real_git(*args)
        def __enter__(self):self.real.__enter__();return self
        def __exit__(self,*args):return self.real.__exit__(*args)
        def read(self,*args):return self.real.read(*args)
        def entries(self,ref):return self.real.entries(base if ref==model_head else ref)
        def git(self,*args):
            if args==('rev-parse',model_head+'^{tree}'):return model_tree.encode()+b'\n'
            return self.real.git(*args)

    original_source=planner.child.source
    def source(model):return original_source(model.real)
    with patch.multiple(planner.child,PARENT_HEAD=None,PARENT_TREE=None,PREPARED_HEAD=head,
            PREPARED_TREE=tree,PREPARED_BASE=base,PREPARED_BASE_TREE=base_tree), \
         patch.object(planner,'accepted_parent',return_value=model_receipt), \
         patch.object(planner,'GitBytes',ModelGit),patch.object(planner.child,'source',side_effect=source):
        request,review=planner.plan(root,head,tree,model_raw)
    planner.exact([review['own_paths'],review['own_source_pins'],review['unchanged_own_files']],
        [96,95,90],'DE96_MODEL_EXACT_COUNTS')
    entries={row['path']:row for row in request['tree_elements']}
    planner.exact(len(entries),96,'DE96_MODEL_NO_DUPLICATE_TREE_PATH')
    planner.exact(entries[planner.RECEIPT]['content'].encode(),model_raw,'DE96_MODEL_RAW_RECEIPT_BYTES')
    with real_git(root,head,tree)as git:
        old=set(declaration['files'])|{planner.NS+'SOURCE.json'}
        manifest=planner.strict(entries[planner.NS+'SOURCE.json']['content'].encode())
        planner.exact(set(manifest['files']),set(entries)-{planner.NS+'SOURCE.json'},'DE96_MODEL_ALL_SOURCE_PINS')
        preserved=0
        for name,row in entries.items():
            if'content'in row:raw=row['content'].encode()
            else:
                raw=git.read(name)
                planner.exact(row['sha'],sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
                    'DE96_MODEL_UNCHANGED_OWN_GIT_BLOB:'+name)
                preserved+=1
            if name!=planner.NS+'SOURCE.json':
                planner.exact(planner.pin(raw),manifest['files'][name],'DE96_MODEL_ACTUAL_SOURCE_PIN:'+name)
        planner.exact(preserved,90,'DE96_MODEL_UNCHANGED_OWN90')
        planner.exact(entries[planner.WORKFLOW]['content'].encode(),git.read(planner.NS+'native30.workflow.yml.txt'),
            'DE96_MODEL_WORKFLOW_EXACT_TEMPLATE')
        planner.exact(set(entries)-old,{planner.RECEIPT,planner.WORKFLOW},'DE96_MODEL_ONLY_TWO_NEW_PATHS')
        planner.exact({name for name in old if'content'in entries[name]},set(review['changed_own_files']),
            'DE96_MODEL_ONLY_DECLARED_FOUR_CHANGES')
    digest=sha256(json.dumps(request,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    return dict(status='DE96_PURE_ASSEMBLY_MODEL_PASS_NOT_PARENT_ACCEPTANCE',own_paths=96,pins=95,
        unchanged_own90=90,manifest_all95_actual_bytes_match=True,workflow_exact_template=True,
        planned_tree_request_sha256=digest,synthetic_request_never_saved=True,
        actual_parent_receipt_not_accepted=True,Git_mutations=0,SQL=0,ERP_cases=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--head',required=True);parser.add_argument('--tree',required=True);args=parser.parse_args()
    print(json.dumps(control(args.source,args.head,args.tree)))
