"""Bound report serialization memory without dropping a captured value.

Catalog containers remain independent snapshots. Only immutable strings can
share storage with an already retained catalog. Every original comparison,
case result and complete JSON report is kept.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import FunctionType
import ast,json,os,tempfile

ROOT=Path(__file__).resolve().parents[2]
ORIGINAL=('scripts/cp6_au_r1_probe.py',29829,
    '451d3d5cbf34fed8f6ba0bf6445cee08e5198d6979f1fd1fbc68f9e299d3724b')
HELPER='_afui_stream_complete_group_report'
BEFORE="(OUT/(name+'.json')).write_text(json.dumps(value,indent=2,default=str)+'\\n')"
AFTER=HELPER+"(OUT/(name+'.json'),value)"


def share_strings(actual,retained):
    """Reuse equal long strings; never share or alter a mutable container.

    The pool contains only existing strings, and cannot grow with new values.
    Catalog mismatches keep their exact values for the original oracle.
    """
    pool={};stack=[retained]
    while stack:
        value=stack.pop()
        if type(value)is dict:stack.extend(value.values())
        elif type(value)is list:stack.extend(value)
        elif type(value)is str and len(value)>=256:pool[value]=value
    stack=[actual]
    while stack:
        value=stack.pop()
        if type(value)is dict:
            for key,item in value.items():
                if type(item)is str and len(item)>=256:value[key]=pool.get(item,item)
                elif type(item)in(dict,list):stack.append(item)
        elif type(value)is list:
            for key,item in enumerate(value):
                if type(item)is str and len(item)>=256:value[key]=pool.get(item,item)
                elif type(item)in(dict,list):stack.append(item)
    return actual


def write_complete(target,value):
    """Exactly json.dumps(indent=2,default=str)+'\\n', in bounded chunks.

    An interrupted or failed encoder cannot truncate the last complete group
    report. The unique partial remains available as failure evidence.
    """
    target=Path(target)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=target.parent,
            prefix='.'+target.name+'.',suffix='.partial',delete=False)as stream:
        partial=Path(stream.name)
        for part in json.JSONEncoder(indent=2,default=str).iterencode(value):stream.write(part)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(partial,target)


def derive(raw,filename=None):
    if(len(raw)!=ORIGINAL[1]or sha256(raw).hexdigest()!=ORIGINAL[2]):
        raise ValueError('AFUI_REPORT_IO_EXACT_ORIGINAL_SOURCE_REQUIRED')
    source=raw.decode()
    if source.count(BEFORE)!=1 or AFTER in source:
        raise ValueError('AFUI_REPORT_IO_ONE_EXACT_SAVE_EXPRESSION_REQUIRED')
    changed=source.replace(BEFORE,AFTER,1)
    if changed.replace(AFTER,BEFORE,1).encode()!=raw:
        raise ValueError('AFUI_REPORT_IO_COMPLETE_ORIGINAL_RECOVERY_REQUIRED')
    old,new=ast.parse(source),ast.parse(changed)
    old_save=[n for n in old.body if isinstance(n,ast.FunctionDef)and n.name=='save']
    new_save=[n for n in new.body if isinstance(n,ast.FunctionDef)and n.name=='save']
    if(len(old_save)!=1 or len(new_save)!=1 or ast.dump(ast.Module(body=[n for n in old.body if n is not old_save[0]],type_ignores=[]))!=
            ast.dump(ast.Module(body=[n for n in new.body if n is not new_save[0]],type_ignores=[]))):
        raise ValueError('AFUI_REPORT_IO_ONLY_GROUP_SERIALIZATION_MAY_CHANGE')
    from .case_output import function_code
    filename=str(ROOT/ORIGINAL[0])if filename is None else str(filename)
    return function_code(old,filename,'save'),function_code(new,filename,'save')


def derive_engine(text):
    """Stream the final whole packet too; retain both original engine routes."""
    from . import package_engine
    expected,_=package_engine.derive((ROOT/package_engine.ORIGINAL).read_bytes())
    before="OUT.write_text(json.dumps(report,indent=2,default=str)+'\\n')"
    after=HELPER+'(OUT,report)'
    if text!=expected or text.count(before)!=1 or HELPER in text:
        raise ValueError('AFUI_REPORT_IO_EXACT_PREPARED_WHOLE_ENGINE_REQUIRED')
    changed=text.replace(before,after,1)
    if changed.replace(after,before,1)!=text:
        raise ValueError('AFUI_REPORT_IO_WHOLE_ENGINE_ORIGINAL_RECOVERY_REQUIRED')
    compile(changed,str(ROOT/package_engine.ORIGINAL),'exec',dont_inherit=True)
    return changed,dict(status='COMPLETE_WHOLE_PACKET_JSON_STREAMED_WITH_UNCHANGED_RESTORE',
        source_sha256=sha256(text.encode()).hexdigest(),derived_sha256=sha256(changed.encode()).hexdigest(),
        reversible_save_expression_changes=1,complete_prepared_engine_recovered=True,
        actual_case_credit=0,full_restore_verified=False,production_go=False)


def binding(module):
    path=Path(module.__file__).resolve()
    if not path.as_posix().endswith('/'+ORIGINAL[0])or path.is_symlink():
        raise ValueError('AFUI_REPORT_IO_EXACT_OWNING_MODULE_REQUIRED')
    old,new=derive(path.read_bytes(),path);original=module.save
    if (original.__globals__ is not module.__dict__ or original.__code__!=old or HELPER in module.__dict__):
        raise ValueError('AFUI_REPORT_IO_ORIGINAL_OWNING_CALLABLE_REQUIRED')
    return original,new,dict(status='COMPLETE_GROUP_JSON_STREAMED_WITH_UNCHANGED_RESULTS',
        actual_source_path=str(path),original_source_sha256=ORIGINAL[2],complete_original_source_recovered=True,
        complete_owning_module_compiler_context=True,actual_case_credit=0,full_restore_verified=False,production_go=False)


@contextmanager
def scope(module):
    original,new,proof=binding(module)
    adapted=FunctionType(new,module.__dict__,original.__name__,original.__defaults__,original.__closure__)
    adapted.__kwdefaults__=original.__kwdefaults__
    module.__dict__[HELPER]=write_complete;module.save=adapted
    try:yield proof
    finally:module.save=original;del module.__dict__[HELPER]
