"""Retain full prerequisite and changed-output bytes in all three frozen trees."""
from pathlib import Path
import argparse,importlib.util,json
import sku_current_parent_runtime as runtime

ROOT=Path(__file__).resolve().parents[2]
OWN=ROOT/'cp6-proof/t3'
MANIFEST=OWN/'SKU_CURRENT_PARENT_PREREQUISITE_FILES.json'
RETAINED=OWN/'SKU_CURRENT_PARENT_FROZEN_EXECUTION'
FOLDERS=('qualified-mandor-parent','qualified-afui-parent','qualified-sku-moving-average')


def helpers():
    path=ROOT/'scripts/current-mandor-shop-native-qualification/parent_artifacts.py'
    # Only the exact path/inventory/copy functions are inherited. Loading the
    # module cannot import its unrelated, closed bare-named Mandor qualifier.
    raw=path.read_text()
    old='import materialize_parent,qualification'
    if raw.count(old)!=1:raise ValueError('SKU_COMPOSITE_EXACT_ORIGINAL_COPY_HELPER_IMPORT')
    text=raw.replace(old,'# Unused parent orchestration imports omitted; exact copy functions retained.',1)
    import types
    module=types.ModuleType('sku_exact_full_file_retention');module.__file__=str(path)
    exec(compile(text,str(path)+':copy-functions','exec'),module.__dict__)
    return module


def prepare():
    runtime.actual_inputs()
    h=helpers();h.require(not MANIFEST.exists()and not RETAINED.exists(),'SKU_COMPOSITE_SINGLE_ARTIFACT_PREPARATION')
    sources=h.inventory(OWN);states={}
    for folder in FOLDERS:
        frozen=ROOT.parent/folder
        h.require(frozen.is_dir()and not frozen.is_symlink(),'SKU_COMPOSITE_FROZEN_ARTIFACT_TREE_REQUIRED')
        parent=frozen/'cp6-proof/t3';h.regular(parent,frozen);parent.mkdir(parents=True,exist_ok=True)
        copied=[]
        for name,expected in sources.items():
            if h.copy_exact(OWN/name,parent/name,OWN,parent,expected):copied.append(name)
        states[folder]=dict(before_runtime=h.inventory(parent),copied=copied)
    result=dict(status='EXACT_CURRENT_PARENT_PREREQUISITE_BYTES',source_files=sources,frozen=states,
        actual_composite_cases=0,production_go=False)
    with MANIFEST.open('x')as stream:stream.write(json.dumps(result,indent=2)+'\n')
    return dict(status=result['status'],source_files=len(sources),frozen_trees=len(states),actual_composite_cases=0)


def retain():
    if not MANIFEST.exists():return dict(status='CURRENT_PARENT_EXECUTION_NOT_PREPARED',actual_composite_cases=0)
    h=helpers();h.regular(MANIFEST,OWN);baseline=json.loads(MANIFEST.read_bytes())
    h.require(baseline['status']=='EXACT_CURRENT_PARENT_PREREQUISITE_BYTES'and set(baseline['frozen'])==set(FOLDERS),
        'SKU_COMPOSITE_EXACT_RETENTION_BASELINE')
    result={}
    for folder in FOLDERS:
        parent=ROOT.parent/folder/'cp6-proof/t3';current=h.inventory(parent);before=baseline['frozen'][folder]['before_runtime']
        changed={n:p for n,p in current.items()if before.get(n)!=p}
        for name,expected in changed.items():h.copy_exact(parent/name,RETAINED/folder/name,parent,RETAINED,expected)
        result[folder]=dict(files=changed,missing_baseline_files=sorted(set(before)-set(current)))
    value=dict(status='ALL_NEW_OR_CHANGED_CURRENT_PARENT_OUTPUT_BYTES_RETAINED',frozen=result,
        files_overwritten=False,JSON_or_row_projection=False,actual_composite_cases=0,production_go=False)
    receipt=OWN/'SKU_CURRENT_PARENT_FROZEN_EXECUTION_RECEIPT.json';raw=(json.dumps(value,indent=2)+'\n').encode()
    if receipt.exists():h.require(receipt.read_bytes()==raw,'SKU_COMPOSITE_RETENTION_RECEIPT_CHANGED')
    else:
        with receipt.open('xb')as out:out.write(raw)
    return dict(status=value['status'],retained_files=sum(len(v['files'])for v in result.values()),
        missing_baseline_files=sum(len(v['missing_baseline_files'])for v in result.values()),actual_composite_cases=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--retain',action='store_true');args=parser.parse_args()
    print(json.dumps(prepare()if args.prepare else retain(),sort_keys=True))
