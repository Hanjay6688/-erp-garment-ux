"""Keep complete case output bytes off the Actions annotation matcher.

Only three original per-case print sites are routed. Case results, the saved
group report, strict checks, transactions and cleanup remain byte-for-byte
source-equivalent. No stdout/Auth masking or subprocess output is intercepted.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import CodeType,FunctionType
import ast,json,os,re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'cp6-proof/t3/AFUI_CASE_STDOUT'
HELPER='_afui_retain_complete_case_stdout'
SOURCES={
    'native':('scripts/cp6_auditor_runner.py',14911,
        '2c74439f7e919e2adb2484bc774bef4881e71237124f2e6b6dabdab141348ea7',
        '_strict_group_once','name',2),
    'copies':('scripts/current-s03-sku-s05-composite-qualification/modes.py',23300,
        '5f4f45edcc99d24987908369fbec687f8373c6ffb37ce01d5e0fe63d79c6afb4',
        'strict_rows','group',1),
}


def require(value,message):
    if not value:raise ValueError(message)


def derive(kind,raw):
    path,size,digest,name,group,count=SOURCES[kind]
    require(len(raw)==size and sha256(raw).hexdigest()==digest,'AFUI_CASE_OUTPUT_EXACT_ORIGINAL_SOURCE:'+kind)
    source=raw.decode();before='print(json.dumps(dict(group='+group+',case=key,**row),default=str),flush=True)'
    after=HELPER+'('+group+',key,row)'
    require(source.count(before)==count and after not in source,'AFUI_CASE_OUTPUT_EXACT_PRINT_SITES:'+kind)
    derived=source.replace(before,after)
    require(derived.replace(after,before).encode()==raw,'AFUI_CASE_OUTPUT_COMPLETE_ORIGINAL_RECOVERED')
    original=ast.parse(source);changed=ast.parse(derived)
    old=[n for n in original.body if isinstance(n,ast.FunctionDef)and n.name==name]
    new=[n for n in changed.body if isinstance(n,ast.FunctionDef)and n.name==name]
    require(len(old)==len(new)==1,'AFUI_CASE_OUTPUT_ONE_OWNING_FUNCTION')
    # Every other statement, including masking and group persistence, is exact.
    require(ast.dump(ast.Module(body=[n for n in original.body if n is not old[0]],type_ignores=[]))==
        ast.dump(ast.Module(body=[n for n in changed.body if n is not new[0]],type_ignores=[])),
        'AFUI_CASE_OUTPUT_ONLY_SELECTED_FUNCTION_CHANGED')
    return old[0],new[0],dict(path=path,original_bytes=size,original_sha256=digest,
        routed_print_sites=count,complete_original_source_recovered=True,
        case_results_group_persistence_oracles_and_cleanup_unchanged=True)


def sources():
    return dict(status='AFUI_COMPLETE_CASE_FILES_BOUNDED_CONSOLE_SOURCE_ONLY',
        originals={kind:derive(kind,(ROOT/value[0]).read_bytes())[2]for kind,value in SOURCES.items()},
        routed_print_sites=3,actual_Native_cases=0,production_go=False,independent_acceptance=False)


def retain(group,case,row):
    require(all(type(v)is str and re.fullmatch(r'[A-Za-z0-9_-]{1,180}',v)for v in(group,case)),
        'AFUI_CASE_OUTPUT_FIXED_GROUP_AND_CASE_IDENTITIES')
    require(isinstance(row,dict),'AFUI_CASE_OUTPUT_ORIGINAL_ROW_OBJECT_REQUIRED')
    # Same object and encoder options as the original print(json.dumps(...)).
    value=dict(group=group,case=case,**row)
    require(OUT.is_absolute()and OUT.resolve()==OUT and not any(p.is_symlink()for p in(OUT,*OUT.parents)),
        'AFUI_CASE_OUTPUT_REGULAR_FIXED_ARTIFACT_DIRECTORY')
    OUT.mkdir(parents=True,exist_ok=True)
    key=sha256((group+'\0'+case).encode()).hexdigest();target=OUT/(key+'.jsonl');partial=OUT/(key+'.partial')
    require(not target.exists()and not partial.exists(),'AFUI_CASE_OUTPUT_FIRST_ORIGINAL_OVERWRITE_REFUSED')
    digest=sha256();size=0
    with partial.open('xb',buffering=1024*1024)as stream:
        for part in json.JSONEncoder(default=str).iterencode(value):
            raw=part.encode();stream.write(raw);digest.update(raw);size+=len(raw)
        stream.write(b'\n');digest.update(b'\n');size+=1
        stream.flush();os.fsync(stream.fileno())
    # Hard-link creation is exclusive; even a concurrent target cannot be replaced.
    os.link(partial,target);partial.unlink()
    receipt=dict(group=group,case=case,status=row.get('status'),complete_original_file=target.name,
        original_bytes=size,original_sha256=digest.hexdigest(),case_error_present=bool(row.get('error')),
        console_is_only_a_receipt=True)
    text=json.dumps(receipt,default=str)
    require(len(text.encode())<2048,'AFUI_CASE_OUTPUT_BOUNDED_RECEIPT_REQUIRED')
    print(text,flush=True)
    return receipt


def function_code(node,filename):
    compiled=compile(ast.Module(body=[node],type_ignores=[]),filename,'exec')
    values=[x for x in compiled.co_consts if isinstance(x,CodeType)and x.co_name==node.name]
    require(len(values)==1,'AFUI_CASE_OUTPUT_EXACT_FUNCTION_CODE')
    return values[0]


def binding(module,kind):
    expected=SOURCES[kind];path=Path(module.__file__).resolve()
    require(path.as_posix().endswith('/'+expected[0])and not path.is_symlink(),
        'AFUI_CASE_OUTPUT_OWNING_SOURCE_PATH_REQUIRED')
    old,new,proof=derive(kind,path.read_bytes());original=getattr(module,expected[3])
    require(original.__globals__ is module.__dict__ and original.__code__.co_filename==str(path)
        and original.__code__==function_code(old,str(path))and HELPER not in module.__dict__,
        'AFUI_CASE_OUTPUT_UNCHANGED_ORIGINAL_CALLABLE_REQUIRED')
    return original,new,proof


@contextmanager
def scope(module,kind):
    original,new,proof=binding(module,kind);name=SOURCES[kind][3]
    adapted=FunctionType(function_code(new,original.__code__.co_filename),module.__dict__,
        original.__name__,original.__defaults__,original.__closure__)
    adapted.__kwdefaults__=original.__kwdefaults__
    module.__dict__[HELPER]=retain;setattr(module,name,adapted)
    try:yield proof
    finally:
        setattr(module,name,original);del module.__dict__[HELPER]
