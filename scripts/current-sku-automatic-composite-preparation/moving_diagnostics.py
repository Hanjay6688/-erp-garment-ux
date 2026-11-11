"""Measure the existing private moving installer without changing its operations."""
from hashlib import sha256
from pathlib import Path
from types import CodeType, ModuleType
import ast
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DERIVER = ROOT / 'scripts/current-sku-composite-preparation/sku_current_parent_derive.py'
DERIVER_SHA256 = '86c42eb2caa7171cb94bdbd6c6e8e6680cab5faeaf27df99720c81426edf529f'
DERIVED_SHA256 = 'c72fe581f195ded0e7b1317df70683b439d7d88e357cea838acbc40d937aa97c'
OBSERVER = '_cp7_observe_moving_install'
GROUPS = (
    ('LOCKS', 0, 1),
    ('VERIFY_MANDOR', 1, 2),
    ('CAPTURE_BEFORE', 2, 5),
    ('PREPARE_DEFINITIONS', 5, 11),
    ('DDL_AND_GRANTS', 11, 12),
    ('CAPTURE_AND_BIND_STATE', 12, 13),
    ('VERIFY_MOVING', 13, 15),
)


def timed(label, statements):
    call = ast.Call(func=ast.Name(id=OBSERVER, ctx=ast.Load()),
                    args=[ast.Constant(value='SKU_MOVING_' + label)], keywords=[])
    return ast.With(items=[ast.withitem(context_expr=call)], body=statements)


def bind(moving, observe):
    expected = ROOT.parent / 'qualified-sku-money/scripts/cp7_sku_moving_average/composition.py'
    if (type(moving) is not ModuleType or moving.__name__ != 'current_mandor_moving_for_money'
            or Path(moving.__file__) != expected or OBSERVER in moving.__dict__):
        raise ValueError('SKU_MOVING_DIAGNOSTIC_EXACT_PRIVATE_MODULE_REQUIRED')
    if sha256(DERIVER.read_bytes()).hexdigest() != DERIVER_SHA256:
        raise ValueError('SKU_MOVING_DIAGNOSTIC_EXACT_PARENT_DERIVER_REQUIRED')
    spec = importlib.util.spec_from_file_location('sku_moving_exact_parent_deriver', DERIVER)
    deriver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(deriver)
    source, _ = deriver.derive(expected.read_bytes())
    if sha256(source.encode()).hexdigest() != DERIVED_SHA256:
        raise ValueError('SKU_MOVING_DIAGNOSTIC_EXACT_DERIVED_SOURCE_REQUIRED')
    original = moving.install_delta
    filename = original.__code__.co_filename
    code, = [item for item in compile(source, filename, 'exec', dont_inherit=True).co_consts
             if isinstance(item, CodeType) and item.co_name == 'install_delta']
    if original.__globals__ is not moving.__dict__ or original.__code__ != code:
        raise ValueError('SKU_MOVING_DIAGNOSTIC_EXACT_ACTIVE_INSTALLER_REQUIRED')

    installer, = [item for item in ast.parse(source).body
                  if isinstance(item, ast.FunctionDef) and item.name == 'install_delta']
    runtime, atomic = installer.body
    statements = atomic.body
    installer.body[0] = timed('RUNTIME_SOURCE', [runtime])
    atomic.body = [timed(name, statements[start:end]) for name, start, end in GROUPS] + statements[15:]
    namespace = {}
    tree = ast.fix_missing_locations(ast.Module(body=[installer], type_ignores=[]))
    exec(compile(tree, filename, 'exec', dont_inherit=True), moving.__dict__, namespace)
    moving.__dict__[OBSERVER] = observe
    moving.install_delta = namespace['install_delta']
    return dict(derived_source_sha256=DERIVED_SHA256, measured_subphases=1 + len(GROUPS),
                actual_case_credit=0, restoration_verified=False)
