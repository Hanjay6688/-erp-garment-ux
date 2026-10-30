"""Load only the selected real backend package; never alter its sources() or code.

The normal UI checkout stays frozen. Seven exact public runtime files and its
unchanged Python package entry live in a dedicated component root, whose actual
HERE/ROOT naturally produce the same canonical source keys. The complete real
predecessor graph still comes from the normal checkout and must compare exactly
with the admitted actual Native14 Original before any database is opened.
"""
from hashlib import sha256
from importlib import import_module
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKAGE = 'cp7_attendance_period_choice'
NAMES = ('choice.sql', 'readers.sql', 'native_delta.py', 'catalog_contract.py',
    'NEW_CATALOG_IDENTITIES.json', 'composition.py', 'installer_ddl.py')
CANONICAL = {'scripts/' + PACKAGE + '/' + name for name in NAMES}


def retained(expected):
    """Pure byte/path check. Prepared pins alone authorize no import or SQL."""
    declaration = json.loads((HERE / 'RUNTIME_SOURCE.json').read_bytes())
    files = declaration['runtime_files']
    if (set(files) != CANONICAL or set(expected) != CANONICAL
            or {name: pin['sha256'] for name, pin in files.items()} != expected
            or declaration.get('whole_tree_overlay') is not False
            or declaration.get('product_sources_override') is not False):
        raise ValueError('S03_BROWSER4_EXACT_SELECTED_ACTUAL_RUNTIME7_REQUIRED')
    component = (ROOT / declaration['component_root']).resolve()
    if component != (HERE / 'runtime-backend7').resolve():
        raise ValueError('S03_BROWSER4_DEDICATED_COMPONENT_ROOT_REQUIRED')
    for name, pin in [*files.items(), (declaration['package_entry']['path'], declaration['package_entry'])]:
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:
            raise ValueError('S03_BROWSER4_SAFE_CANONICAL_RUNTIME_PATH_REQUIRED')
        path = (ROOT / pin['retained']).resolve()
        if path != component / name or not path.is_relative_to(component):
            raise ValueError('S03_BROWSER4_EXACT_RUNTIME_SOURCE_ROUTE_REQUIRED')
        raw = path.read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('S03_BROWSER4_RETAINED_ACTUAL_RUNTIME_CHANGED:' + name)
    if declaration['package_entry']['path'] != 'scripts/' + PACKAGE + '/__init__.py':
        raise ValueError('S03_BROWSER4_EXACT_PUBLIC_PACKAGE_ENTRY_REQUIRED')
    return dict(component_root=component, scripts=component / 'scripts', package=component / 'scripts' / PACKAGE,
        runtime_files=expected, entry_sha256=declaration['package_entry']['sha256'])


@contextmanager
def actual_backend(proof):
    if (proof.get('status') != 'EXACT_ACTUAL_BACKEND14_AND_ALL5_ORIGINALS_ADMITTED'
            or proof.get('actual_parent_Native_cases') != 14):
        raise ValueError('S03_BROWSER4_ACTUAL_ADMISSION_BEFORE_BACKEND_IMPORT_REQUIRED')
    route = retained(proof['current_installation']['files'])
    # Never unload/replace a cached old implementation or patch its globals.
    for name, module in tuple(sys.modules.items()):
        if name == PACKAGE or name.startswith(PACKAGE + '.'):
            path = getattr(module, '__file__', None)
            if not path or not Path(path).resolve().is_relative_to(route['package']):
                raise ValueError('S03_BROWSER4_CACHED_NONCURRENT_BACKEND_IMPORT_REFUSED:' + name)
    before_modules, before_path, before_argv = dict(sys.modules), list(sys.path), sys.argv
    try:
        # The retained ERP harness parses argv while importing. Scope that
        # inherited behavior without discarding the caller's real arguments.
        sys.argv = sys.argv[:1]
        sys.path.insert(0, str(ROOT / 'scripts'))
        sys.path.insert(0, str(route['scripts']))
        product = import_module(PACKAGE + '.composition')
        for name in (PACKAGE, *(PACKAGE + '.' + file[:-3] for file in NAMES if file.endswith('.py'))):
            module = sys.modules.get(name)
            if module is None or not getattr(module, '__file__', None):
                raise ValueError('S03_BROWSER4_ACTUAL_BACKEND_MODULE_MISSING:' + name)
            expected = route['package'] / ('__init__.py' if name == PACKAGE else name.rsplit('.', 1)[1] + '.py')
            if Path(module.__file__).resolve() != expected:
                raise ValueError('S03_BROWSER4_ACTUAL_BACKEND_MODULE_SOURCE_CHANGED:' + name)
        if product.sources() != proof['current_installation']:
            raise ValueError('S03_BROWSER4_WHOLE_REAL_PRODUCT_SOURCE_GRAPH_CHANGED')
        yield product
    finally:
        # Source-only controls and every actual exit keep the caller's import
        # environment exact. No old package is evicted to make admission pass.
        for name in set(sys.modules) - set(before_modules):sys.modules.pop(name, None)
        for name, module in before_modules.items():
            if sys.modules.get(name) is not module:sys.modules[name] = module
        sys.path[:] = before_path
        sys.argv = before_argv
