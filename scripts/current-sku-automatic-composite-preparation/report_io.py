"""Exact complete-packet/group output without a whole JSON string buffer.

No transaction, verification, actor or recovery operation is changed. The
encoder primitive is copied exactly from the current Afui source; retaining
its output bytes does not itself qualify an ERP package.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import CodeType, FunctionType
import ast
import importlib.util
import json
import os
import tempfile

ORIGINAL_R1 = (29829, '451d3d5cbf34fed8f6ba0bf6445cee08e5198d6979f1fd1fbc68f9e299d3724b')
EXPECTED_ENGINES = {
    'mandor17': '568e1bcab4dd8c9db21e0a7f6d16f54f7259eecbe7b5a8ccc25ded276b691dfc',
    'money19': '0bd4bb1d4106a1dd507d3377216b7e1809ba75b3f3811e4c80ec4ca5fc574fd0',
}
HELPER = '_current_stage_stream_complete_report'
PACKET_BEFORE = "OUT.write_text(json.dumps(report,indent=2,default=str)+'\\n')"
GROUP_BEFORE = "(OUT/(name+'.json')).write_text(json.dumps(value,indent=2,default=str)+'\\n')"
AFUI_PRIMITIVE_SOURCE_HEAD = 'e0cfa98382e977933d63e9f828de17a0faba9ef9'
AFUI_PRIMITIVE_SOURCE_SHA256 = 'cb1b5ff9da13188b798413d85d7f26701c7a8399ad3fbc5524b9e450bbc35c66'
AFUI_PRIMITIVE_AST_SHA256 = '1dd970c0e382fa6976c4bf0867c3d5b6558327f7bcec5cc403016879476aeb59'
COMPLETE_ORIGINALS_PATH = Path(__file__).resolve().parents[2].parent / 'qualified-afui-parent/scripts/cp7_accessory_nonpayable/complete_original_io.py'
COMPLETE_ORIGINALS_PIN = (5951, 'f7c732004e1f5f0f2fe7ac7e08a6f049e6d41f0074fca7336c66736aaf522170')
COMPLETE_ORIGINALS_HEAD = 'f17ac6cc13cffe10a32deca1c04ff63d220285fe'
COMPLETE_ORIGINALS_TREE = '82bbcc0e53c07ddb2b52d0ea26e2263ed11681c7'


def complete_originals():
    path = COMPLETE_ORIGINALS_PATH
    if (not path.is_file() or path.is_symlink()
            or (path.stat().st_size, sha256(path.read_bytes()).hexdigest()) != COMPLETE_ORIGINALS_PIN):
        raise ValueError('CURRENT_STAGE_EXACT_AFUI_COMPLETE_ORIGINAL_COPY_SOURCE_REQUIRED')
    spec = importlib.util.spec_from_file_location('automatic_exact_current_Afui_complete_originals', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

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


def primitive_contract():
    tree = ast.parse(Path(__file__).read_bytes())
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'write_complete']
    if len(selected) != 1 or sha256(ast.dump(selected[0], include_attributes=False).encode()).hexdigest() != AFUI_PRIMITIVE_AST_SHA256:
        raise ValueError('CURRENT_STAGE_EXACT_AFUI_ENCODER_PRIMITIVE_REQUIRED')
    return dict(encoder_source_head=AFUI_PRIMITIVE_SOURCE_HEAD,
                encoder_source_sha256=AFUI_PRIMITIVE_SOURCE_SHA256,
                encoder_function_AST_sha256=AFUI_PRIMITIVE_AST_SHA256,
                actual_ERP_cases=0, production_go=False)


def derive_packet(source, kind):
    if kind not in EXPECTED_ENGINES or sha256(source.encode()).hexdigest() != EXPECTED_ENGINES[kind]:
        raise ValueError('CURRENT_STAGE_EXACT_COMPLETE_PREPARED_ENGINE_REQUIRED')
    after = HELPER + '(OUT,report)'
    if source.count(PACKET_BEFORE) != 1 or HELPER in source:
        raise ValueError('CURRENT_STAGE_ONE_COMPLETE_PACKET_SAVE_REQUIRED')
    changed = source.replace(PACKET_BEFORE, after, 1)
    if changed.replace(after, PACKET_BEFORE, 1) != source:
        raise ValueError('CURRENT_STAGE_COMPLETE_PACKAGE_SOURCE_NOT_RECOVERED')
    compile(changed, 'current-stage-streamed-complete-packet', 'exec', dont_inherit=True)
    return changed, dict(kind=kind, original_sha256=EXPECTED_ENGINES[kind],
                         derived_sha256=sha256(changed.encode()).hexdigest(),
                         exact_save_expression_routes=1, complete_original_recovered=True,
                         financial_cases_and_full_recovery_unchanged=True,
                         encoder=primitive_contract(), actual_ERP_cases=0, production_go=False)


def function_code(source, filename, name):
    compiled = compile(source, filename, 'exec', dont_inherit=True)
    selected = [code for code in compiled.co_consts if isinstance(code, CodeType) and code.co_name == name]
    if len(selected) != 1:
        raise ValueError('CURRENT_STAGE_FULL_COMPILER_CONTEXT_FUNCTION_REQUIRED')
    return selected[0]


@contextmanager
def group_scope(module):
    path = Path(module.__file__)
    raw = path.read_bytes()
    if (not path.as_posix().endswith('/scripts/cp6_au_r1_probe.py') or path.is_symlink()
            or (len(raw), sha256(raw).hexdigest()) != ORIGINAL_R1):
        raise ValueError('CURRENT_STAGE_EXACT_OWNING_R1_SOURCE_REQUIRED')
    source = raw.decode()
    if source.count(GROUP_BEFORE) != 1 or HELPER in source or HELPER in module.__dict__:
        raise ValueError('CURRENT_STAGE_ONE_GROUP_SAVE_SCOPE_REQUIRED')
    after = HELPER + "(OUT/(name+'.json'),value)"
    changed = source.replace(GROUP_BEFORE, after, 1)
    if changed.replace(after, GROUP_BEFORE, 1) != source:
        raise ValueError('CURRENT_STAGE_COMPLETE_GROUP_SOURCE_NOT_RECOVERED')
    old = module.save
    if old.__globals__ is not module.__dict__ or old.__code__ != function_code(source, str(path), 'save'):
        raise ValueError('CURRENT_STAGE_ACTUAL_OWNING_R1_COMPILER_CONTEXT_REQUIRED')
    primitive_contract()
    new = FunctionType(function_code(changed, str(path), 'save'), module.__dict__,
                       old.__name__, old.__defaults__, old.__closure__)
    new.__kwdefaults__ = old.__kwdefaults__
    module.__dict__[HELPER] = write_complete
    module.save = new
    try:
        yield dict(complete_original_group_source_recovered=True, exact_group_save_routes=1,
                   actual_ERP_cases=0, production_go=False)
    finally:
        module.save = old
        del module.__dict__[HELPER]
