"""Lossless readonly metadata for the current owning D1/E qualification.

This is a new metadata caller. It does not invoke or alter the old runtime
loader/admission, install hooks or issue an explicit LOCK. It does not prove
the absence of implicit type-output, provider or system calls.
"""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
import ast,importlib.util,json,os,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RETAINED=HERE/'retained-global-census'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def source():
    origin=json.loads((RETAINED/'ORIGIN.json').read_bytes())
    if(origin['head']!='3d7066b852176d9f343ec831d2f63aee6665579b'
       or origin['actual_Native_cases']!=0 or origin['metadata_SQL_queries_changed']is not False):
        raise ValueError('COMPLETE_DE_EXACT_GLOBAL_METADATA_SOURCE_REQUIRED')
    raw={}
    for name,pin in origin['files'].items():
        path=RETAINED/name;data=path.read_bytes()
        original=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',origin['head']+':'+pin['path']],
            env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0'))
        if(path.is_symlink()or len(data)!=pin['bytes']or sha256(data).hexdigest()!=pin['sha256']or data!=original):
            raise ValueError('COMPLETE_DE_UNCHANGED_GLOBAL_METADATA_HELPER_REQUIRED:'+name)
        raw[name]=data
    if set(raw)!={'capture.py','census.py','multiset.py','derive.py.txt'}:
        raise ValueError('COMPLETE_DE_EXACT_FOUR_GLOBAL_METADATA_ORIGINALS_REQUIRED')
    tree=ast.parse(raw['derive.py.txt'])
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in('replace_exact','capture')]
    if [n.name for n in selected]!=origin['pure_selected_functions']:
        raise ValueError('COMPLETE_DE_EXACT_TWO_PURE_GLOBAL_METADATA_DERIVERS_REQUIRED')
    builder=ModuleType('complete_DE_pure_recorded_multiset_source_derivation')
    # Both globals route only source/data files in this new caller's closed
    # namespace. No ERP module or prior runtime guard is modified or imported.
    builder.__dict__.update(sha256=sha256,ROOT=ROOT,
        HELPER=str(RETAINED.relative_to(ROOT)),NS=str(RETAINED.relative_to(ROOT/'scripts')))
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(RETAINED/'derive.py.txt'),'exec'),builder.__dict__)
    text,derivation=builder.capture()
    module=ModuleType('complete_DE_current_readonly_lossless_capture');module.__file__=str(RETAINED/'capture.py')
    exec(compile(text,module.__file__,'exec'),module.__dict__)
    original=load('complete_DE_exact_unmodified_metadata_query_source',RETAINED/'capture.py')
    if(module.QUERIES!=original.QUERIES or len(module.QUERIES)!=19
       or Path(module.census.__file__).resolve()!=RETAINED/'census.py'
       or Path(module.multiset.__file__).resolve()!=RETAINED/'multiset.py'):
        raise ValueError('COMPLETE_DE_ALL19_UNCHANGED_METADATA_QUERIES_AND_NATURAL_HELPERS_REQUIRED')
    return module,dict(classification='RECORDED_GLOBAL_METADATA_SOURCE_ONLY_NOT_RUNTIME',
        origin_head=origin['head'],byte_exact_original_files=4,selected_original_pure_functions=2,
        owning_source_routes=dict(helper=builder.HELPER,codec=builder.NS),derivation=derivation,
        unchanged_SQL_queries=19,query_sha256={k:sha256(v.encode()).hexdigest()for k,v in module.QUERIES.items()},
        prior_runtime_loader_or_admission_used=False,prior_runtime_guards_modified=False,
        actual_Native_cases=0,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False)


def capture_once(url,catalog,directory):
    receipt=load('complete_DE_actual_parent_before_global_metadata',HERE/'admission.py').parent_receipt()
    load('complete_DE_closed_source_before_global_metadata',HERE/'source.py').preflight()
    capture,binding=source()
    inherited,_,_=load('complete_DE_exact_readonly_connection_source',HERE/'system_metadata.py').source()
    targets=inherited.local_urls(url)
    if targets[0][0]!='candidate':raise ValueError('COMPLETE_DE_EXACT_CANDIDATE_METADATA_TARGET_REQUIRED')
    directory=Path(directory);expected=ROOT/'cp6-proof/t3'
    if directory.parent!=expected or directory.name not in('DE_GLOBAL_BEFORE_NATIVE30','DE_GLOBAL_AFTER_COMMITTED_E_USE'):
        raise ValueError('COMPLETE_DE_DECLARED_GLOBAL_METADATA_OUTPUT_DIRECTORY_REQUIRED')
    if any(path.is_symlink()for path in(directory,*directory.parents)):
        raise ValueError('COMPLETE_DE_GLOBAL_METADATA_OUTPUT_SYMLINK_REFUSED')
    import psycopg
    result=dict(classification='READONLY_CURRENT_DE_RAW_DEPENDENCIES_NOT_WRITER_CLOSURE',
        permanent_parent_head=receipt['head'],source=binding,transaction_writes=False,
        observed_catalog_includes_qualification_overlays=True,
        global_hook_installation_or_explicit_LOCK_statement=False,
        provider_or_system_call_closure_proven=False,actual_Native_cases=0,
        global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False)
    def observe(cur):
        cur.execute("set local search_path=''");cur.execute("set local TimeZone='UTC'")
        isolation,snapshot=cur.execute("select pg_catalog.current_setting('transaction_isolation'),pg_catalog.pg_current_snapshot()::text").fetchone()
        if isolation!='repeatable read':raise ValueError('COMPLETE_DE_GLOBAL_METADATA_REPEATABLE_READ_REQUIRED')
        before=dict(actual_all22=catalog._catalog_rows(cur),full_data_and_sequences=catalog._data(cur))
        result['before']=before
        supplement=capture.capture(cur,before['actual_all22'],raw_directory=directory)
        # The retained helper persists the raw pairs before validation. Both
        # dependency bags preserve every occurrence, including repeated IDs.
        capture.multiset.require_projection(directory,supplement,before['actual_all22'],capture.QUERIES)
        after=dict(actual_all22=catalog._catalog_rows(cur),full_data_and_sequences=catalog._data(cur))
        result['after']=after
        if before!=after:raise ValueError('COMPLETE_DE_GLOBAL_METADATA_RAW_BOUNDARY_CHANGED')
        end=cur.execute("select pg_catalog.current_setting('transaction_isolation'),pg_catalog.pg_current_snapshot()::text").fetchone()
        if end!=(isolation,snapshot):raise ValueError('COMPLETE_DE_GLOBAL_METADATA_SNAPSHOT_CHANGED')
        return dict(supplement=supplement,repeatable_read_snapshot=snapshot,
            all22_ALL_rows_ALL_sequences_equal=True,all19_queries_captured=True,
            raw_original=directory.name+'/'+capture.multiset.RAW_NAME)
    try:
        result.update(inherited.one(psycopg,targets[0][1],observe),status='RAW_READONLY_METADATA_CAPTURED')
    except (psycopg.Error,ValueError,AssertionError)as error:
        # An unavailable observation cannot close any global claim. It also
        # cannot replace or hide an original financial case's result.
        result.update(status='RAW_READONLY_METADATA_UNAVAILABLE',error_type=type(error).__name__,
            sqlstate=getattr(error,'sqlstate',None),error_text_or_connection_details_retained=False)
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/'CALLER_RAW_BOUNDARY_OBSERVATION.json'
    with path.open('x')as output:output.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return dict(classification=result['classification'],status=result['status'],
        observation=dict(name=directory.name+'/'+path.name,bytes=path.stat().st_size,
            sha256=sha256(path.read_bytes()).hexdigest()),source=binding,
        actual_Native_cases=0,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False)
