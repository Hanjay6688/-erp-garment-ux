"""Exact unchanged product plus closed qualification routing; no ERP imports."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-s03-sku-s05-composite-qualification'
BASE='50c77207e088af16988d7d91a5b06f72e8e30ecc'
TREE='28295dd44a59f1832bebb86af24bd85df4471f4b'
PREFIX='scripts/current-s05-css-followup-qualification/'
WORKFLOW='.github/workflows/cp7-s05-css-followup.yml'
ROUTING=('scripts/current-s03-sku-s05-composite-qualification/source.py',
         'scripts/current-s03-sku-s05-composite-qualification/freeze.py')
MANIFEST='scripts/current-s03-sku-s05-composite-qualification/SOURCE.json'
READER_MANIFEST='scripts/cp7_s05_s03_sku_composition/SOURCE.json'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def preflight():
    original=load('focused_closed_whole_current_source',PARENT/'source.py')
    observation=original.preflight()
    p=load('focused_source_typed_primitives',PARENT/'parents.py')
    p.exact(original.git('rev-parse',BASE+'^{tree}').decode().strip(),TREE,'EXACT_CSS_QUALIFIED_SOURCE_TREE')
    base=original.entries(BASE);current=original.entries('HEAD')
    p.exact(len(base),14086,'EXACT_PREPARED_PRODUCT_BASE14086')
    changed=set(ROUTING)|{MANIFEST,READER_MANIFEST}
    for name,entry in base.items():
        if name not in changed:p.exact(current.get(name),entry,'UNCHANGED_PRODUCT_OR_PREPARED_ORACLE:'+name)
    declaration=p.strict((HERE/'ROUTING_ORIGIN.json').read_bytes())
    p.exact(set(declaration['files']),set(ROUTING),'ONLY_TWO_REVIEWED_ADMISSION_ROUTING_FILES')
    for name,item in declaration['files'].items():
        raw=original.git('show',BASE+':'+name);p.exact(sha256(raw).hexdigest(),item['original_sha256'],'ROUTING_ORIGINAL')
        text=raw.decode()
        for before,after in item['changes']:
            p.exact(text.count(before),1,'SINGLE_SOURCE_ROUTING_ANCHOR');text=text.replace(before,after,1)
        actual=original.raw(name);p.exact(text.encode(),actual,'ONLY_DECLARED_QUALIFICATION_ROUTING')
        p.exact(sha256(actual).hexdigest(),item['derived_sha256'],'ROUTING_DERIVED_DIGEST')
        for before,after in reversed(item['changes']):
            p.exact(text.count(after),1,'SINGLE_SOURCE_ROUTING_INVERSE');text=text.replace(after,before,1)
        p.exact(text.encode(),raw,'EXACT_ROUTING_ORIGINAL_RECOVERED')
    before=p.strict(original.git('show',BASE+':'+MANIFEST));after=p.strict(original.raw(MANIFEST))
    p.exact({k:v for k,v in after.items()if k!='files'},{k:v for k,v in before.items()if k!='files'},
            'ORIGINAL_FULL37_PLAN_AND_SOURCE_METADATA_RETAINED')
    for name,digest in before['files'].items():
        if name not in ROUTING:p.exact(after['files'].get(name),digest,'UNCHANGED_PRIOR_SOURCE_PIN:'+name)
    added={name for name in after['files']if name.startswith(PREFIX)or name==WORKFLOW}
    p.exact(set(current)-set(base),added,'CLOSED_FOCUSED_NAMESPACE_AND_ONE_WORKFLOW')
    p.exact(set(after['files'])-set(before['files']),added|{READER_MANIFEST},'ONLY_EXPLICIT_ADDITIONAL_SOURCE_PINS')
    reader=load('focused_current_reader_binding_before_any_ERP',HERE/'reader_binding.py').preflight()
    return dict(status='EXACT_S05_ONLY_CSS_PRODUCT_AND_RETAINED35_SOURCE_INVARIANCE',
        base_head=BASE,base_tree=TREE,unchanged_base_blobs_and_modes=len(base)-4,
        modified_old_qualification_files=3,added_focused_paths=len(added),
        modified_current_reader_manifests=1,current_reader_source_binding=reader,
        whole_current_source=observation,backend_and_all_UI_unchanged_from_CSS_candidate=True,
        retained35_source_invariance=True,actual_new_cases=0,production_go=False,independent_acceptance=False)

if __name__=='__main__':print(json.dumps(preflight(),sort_keys=True))
