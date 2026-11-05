"""Complete Mandor output with exact frozen serializers and case print scopes.

No transaction, actor, grants, assertions or restoration step is adapted.
Only complete JSON/gzip publication and two known case-print functions change.
"""
from contextlib import ExitStack, contextmanager
from hashlib import sha256
from pathlib import Path
from types import CellType, FunctionType, ModuleType
import ast
import importlib.util
import os

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = {
    'complete_original_io.py': (5848, '93e44e72ed2312fffab4d6905a0241ba75d1fba46d4d2fe5f9c9f40867c1420b'),
    'case_output.py': (6200, '53cad5f461603efbf84533d6c5804612901137d495af59a0de942f7df52baca5'),
}
RETENTION = 'scripts/current-mandor-shop-native-qualification/access_cases.py'
RETENTION_PIN = (18914, '66ada107055893b894a51789a539e0c9b30b52d9c6f363e9ec2a85539ed839b1')
GZIP_HELPER = '_current_mandor_complete_gzip_original'
FIXED = ('MANDOR_SESSION4_ORIGINAL.json', 'MANDOR_HTTP2_ORIGINAL.json', 'MANDOR_BROWSER_FIXTURE.json',
         'MANDOR_BROWSER_STATE.json', 'MANDOR_BROWSER2_ORIGINAL.json')
RETENTION_ROUTES = (
    ("    raw=(json.dumps(dict(before=before,after=after),sort_keys=True,default=str)+'\\n').encode()\n"
     "    packed=gzip.compress(raw,mtime=0);name='MANDOR_ACCESS_'+label+'_'+uuid.uuid4().hex+'.json.gz'\n",
     "    name='MANDOR_ACCESS_'+label+'_'+uuid.uuid4().hex+'.json.gz'\n"),
    ("    with (directory/name).open('xb')as output:output.write(packed)\n",
     '    complete=' + GZIP_HELPER + '(directory/name,dict(before=before,after=after))\n'),
    ("        original=dict(name=name,raw_bytes=len(raw),raw_sha256=sha256(raw).hexdigest(),\n"
     "            gzip_bytes=len(packed),gzip_sha256=sha256(packed).hexdigest()),actual_all22_groups=22)",
     "        original=dict(name=name,raw_bytes=complete['bytes'],raw_sha256=complete['sha256'],\n"
     "            gzip_bytes=complete['gzip_bytes'],gzip_sha256=complete['gzip_sha256']),actual_all22_groups=22)"),
)


def require(value, message):
    if not value:
        raise ValueError(message)


def private_module(original, replacements):
    private = ModuleType(original.__name__ + '_private_output')
    private.__dict__.update(original.__dict__)
    def clone(value, namespace, closure):
        copied = FunctionType(value.__code__, namespace, value.__name__, value.__defaults__, closure)
        copied.__kwdefaults__ = value.__kwdefaults__
        copied.__annotations__ = dict(value.__annotations__)
        copied.__dict__.update(value.__dict__)
        copied.__qualname__ = value.__qualname__
        copied.__module__ = value.__module__
        copied.__doc__ = value.__doc__
        return copied

    for name, value in original.__dict__.items():
        if name in replacements or not isinstance(value, FunctionType):
            continue
        if value.__globals__ is original.__dict__:
            private.__dict__[name] = clone(value, private.__dict__, value.__closure__)
            continue
        wrapped = getattr(value, '__wrapped__', None)
        if isinstance(wrapped, FunctionType) and wrapped.__globals__ is original.__dict__:
            # contextmanager's wrapper lives in contextlib; its sole function
            # cell must follow the rebound generator, rather than old globals.
            rebound = clone(wrapped, private.__dict__, wrapped.__closure__)
            cells = tuple(CellType(rebound) if cell.cell_contents is wrapped else cell
                          for cell in value.__closure__ or ())
            if not any(cell.cell_contents is wrapped for cell in value.__closure__ or ()):
                raise ValueError('PRIVATE_MODULE_DECORATOR_FUNCTION_CELL_REQUIRED')
            copied = clone(value, value.__globals__, cells)
            copied.__wrapped__ = rebound
            private.__dict__[name] = copied
    private.__dict__.update(replacements)
    return private


def frozen_source(name):
    path = ROOT / 'scripts/cp7_accessory_nonpayable' / name
    require(path.is_file() and not path.is_symlink()
            and (path.stat().st_size, sha256(path.read_bytes()).hexdigest()) == SOURCES[name],
            'MANDOR_OUTPUT_EXACT_CURRENT_AFUI_SOURCE_REQUIRED:' + name)
    spec = importlib.util.spec_from_file_location('mandor_exact_Afui_' + name.removesuffix('.py'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_exact(source, target):
    complete = frozen_source('complete_original_io.py')
    receipt = complete.copy_exact(source, target, 'MANDOR_NATIVE_FIRST_STRICT_ORIGINAL_CHANGED')
    # The mutable R1 report becomes publishable only after strict_group has
    # returned and this existing complete-copy operation retains its bytes.
    if Path(target).name in ('CP7_FG_MANDOR_NATIVE9_STRICT.json', 'CP7_FG_MANDOR_NATIVE9_STRICT_BUSINESS_DAY_FIRST_ATTEMPT.json'):
        output = ROOT / 'cp6-proof/t3/MANDOR_CASE_STDOUT'
        output.mkdir(parents=True, exist_ok=True)
        complete.copy_exact(target, output / Path(target).name, 'MANDOR_COMPLETED_STRICT_GROUP_PUBLICATION_CONFLICT')
    return receipt


def finish_exclusive(partial, target, conflict):
    # Match the original xb refusal even for an identical concurrent original.
    os.link(partial, target)
    partial.unlink()


def save_access(value, name):
    require(name in FIXED, 'MANDOR_FIXED_ACCESS_ORIGINAL_NAME')
    path = ROOT / 'cp6-proof/t3' / name
    require(not path.exists(), 'MANDOR_FIRST_SESSION_ORIGINAL_OVERWRITE_REFUSED')
    path.parent.mkdir(parents=True, exist_ok=True)
    complete = private_module(frozen_source('complete_original_io.py'), dict(finish=finish_exclusive))
    reference=complete.save_sorted(path, value, 'MANDOR_FIRST_SESSION_ORIGINAL_OVERWRITE_REFUSED')
    if name=='MANDOR_BROWSER_STATE.json':
        state_io=load_state_io()
        state_io.save(value,reference,path.parent)
    return reference


def load_state_io():
    spec=importlib.util.spec_from_file_location('mandor_current_complete_state_io',HERE/'state_io.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def function_code(source, path, name):
    module = compile(source, str(path), 'exec', dont_inherit=True)
    found = [code for code in module.co_consts if isinstance(code, type(module)) and code.co_name == name]
    require(len(found) == 1, 'MANDOR_OUTPUT_COMPLETE_MODULE_COMPILER_CONTEXT_REQUIRED')
    return found[0]


def derive_retention(raw):
    require((len(raw), sha256(raw).hexdigest()) == RETENTION_PIN, 'MANDOR_OUTPUT_EXACT_ACCESS_RETENTION_SOURCE_REQUIRED')
    text = raw.decode()
    for before, after in RETENTION_ROUTES:
        require(text.count(before) == 1 and after not in text, 'MANDOR_OUTPUT_ONE_EXACT_RETENTION_ROUTE_REQUIRED')
        text = text.replace(before, after, 1)
    restored = text
    for before, after in reversed(RETENTION_ROUTES):
        restored = restored.replace(after, before, 1)
    require(restored.encode() == raw, 'MANDOR_OUTPUT_COMPLETE_ACCESS_RETENTION_NOT_RECOVERED')
    original = next(node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name == 'retain')
    derived = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == 'retain')
    calls = lambda node: [ast.dump(n) for n in ast.walk(node) if isinstance(n, ast.Call)
                          and isinstance(n.func, ast.Name) and n.func.id == 'require']
    require(calls(original) == calls(derived), 'MANDOR_OUTPUT_ALL_FINANCIAL_BOUNDARY_ASSERTIONS_MUST_REMAIN_EXACT')
    return text


@contextmanager
def retention_scope(module):
    path = Path(module.__file__).resolve()
    require(path == ROOT / RETENTION and not path.is_symlink() and GZIP_HELPER not in module.__dict__,
            'MANDOR_OUTPUT_EXACT_OWNING_RETENTION_MODULE_REQUIRED')
    raw = path.read_bytes()
    source = derive_retention(raw)
    original = module.retain
    require(original.__globals__ is module.__dict__ and original.__code__ == function_code(raw, path, 'retain'),
            'MANDOR_OUTPUT_ACTUAL_RETENTION_COMPILER_CONTEXT_REQUIRED')
    updated = FunctionType(function_code(source, path, 'retain'), module.__dict__, original.__name__, original.__defaults__, original.__closure__)
    updated.__kwdefaults__ = original.__kwdefaults__
    module.__dict__[GZIP_HELPER] = frozen_source('complete_original_io.py').save_gzip_sorted
    module.retain = updated
    try:
        yield
    finally:
        module.retain = original
        del module.__dict__[GZIP_HELPER]


@contextmanager
def case_scope(module, kind, *, retention=None):
    output = private_module(frozen_source('case_output.py'), dict(OUT=ROOT / 'cp6-proof/t3/MANDOR_CASE_STDOUT'))
    with ExitStack() as stack:
        proof = stack.enter_context(output.scope(module, kind))
        if retention is not None:
            stack.enter_context(retention_scope(retention))
        yield proof
