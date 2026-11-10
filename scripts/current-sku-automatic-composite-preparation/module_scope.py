"""Select exact inherited qualifier modules and restore process imports."""
from contextlib import contextmanager
from pathlib import Path
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType
import ast
import sys

NAMES = ('admission', 'assembly', 'component', 'package_engine', 'package_identity', 'advisor_review',
         'cases', 'additional_cases', 'oracle', 'native_fixture', 'runtime_prerequisites',
         'access_cases', 'access_runtime', 'http_cases', 'browser_preflight')
_active = []
HARNESS_NAMES = ('cp6_t3_package_run', 'cp6_run_identity', 'cp6_aw_probe', 'cp6_ax_probe',
                 'cp6_g01_fingerprint', 'cp6_t3_backup_restore_drill', 'cp6_t3_release_package',
                 'cp6_t3_browser', 'cp6_t3_aligned_install')


@contextmanager
def harness_scope(root):
    """Keep the retained harness on its real source while preserving writer cwd.

    These nine names are exactly the frozen parent's owning_harness contract.
    Its nested imports prepend cwd/scripts, so sys.path priority alone cannot
    select them. Return ordinary file specs for those names only; do not
    replace modules, rewrite qualified source, or change runtime identities.
    """
    root = Path(root)
    if not root.is_dir() or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('SKU_AUTOMATIC_EXACT_HARNESS_ROOT_REQUIRED')
    root = root.resolve()
    contract = root / 'scripts/current-final-s03-sku-s05-preparation/parent_import.py'
    if not contract.is_file() or contract.is_symlink():
        raise ValueError('SKU_AUTOMATIC_EXACT_HARNESS_CONTRACT_REQUIRED')
    tree = ast.parse(contract.read_bytes())
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'owning_harness']
    names = [n.value for f in functions for n in f.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == 'names' for t in n.targets)]
    if len(functions) != 1 or len(names) != 1 or ast.literal_eval(names[0]) != HARNESS_NAMES:
        raise ValueError('SKU_AUTOMATIC_COMPLETE_HARNESS_IMPORT_CONTRACT_REQUIRED')
    paths = {name: root / 'scripts' / (name + '.py') for name in HARNESS_NAMES}
    for name, path in paths.items():
        if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('SKU_AUTOMATIC_REGULAR_HARNESS_SOURCE_REQUIRED:' + name)

    def check_loaded():
        for name, path in paths.items():
            existing = sys.modules.get(name)
            if existing is not None and (not getattr(existing, '__file__', None)
                                         or Path(existing.__file__).resolve() != path):
                raise ValueError('SKU_AUTOMATIC_FROZEN_HARNESS_COLLISION:' + name)

    check_loaded()

    class ExactHarness(MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname in paths:
                return spec_from_file_location(fullname, paths[fullname])
            return None

    finder = ExactHarness()
    sys.meta_path.insert(0, finder)
    try:
        yield
        check_loaded()
    finally:
        # Remove only our own resolver, including nested contexts and failures.
        sys.meta_path.remove(finder)


def require_import_closure(qualifier):
    """Cover every bare local import reachable from the actual parent entry."""
    qualifier = Path(qualifier).resolve()
    local = {path.stem for path in qualifier.glob('*.py')}
    visited, dependencies, pending = set(), set(), ['qualification']
    while pending:
        name = pending.pop()
        if name in visited:continue
        visited.add(name)
        path = qualifier / (name + '.py')
        if not path.is_file() or path.is_symlink():
            raise ValueError('SKU_AUTOMATIC_REGULAR_INHERITED_IMPORT_SOURCE_REQUIRED:' + name)
        for node in ast.walk(ast.parse(path.read_bytes())):
            found = []
            if isinstance(node, ast.Import):found = [item.name for item in node.names if item.name in local]
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module in local:found = [node.module]
            for item in found:
                dependencies.add(item);pending.append(item)
    if dependencies != set(NAMES):
        raise ValueError('SKU_AUTOMATIC_COMPLETE_INHERITED_BARE_IMPORT_CLOSURE_REQUIRED')
    return dict(reachable_local_modules=sorted(visited), scoped_bare_modules=sorted(dependencies),
                all_actual_parent_local_imports_selected_and_restored=True, actual_ERP_cases=0)


@contextmanager
def scope(qualifier):
    qualifier = Path(qualifier).resolve()
    previous_path = list(sys.path)
    previous = {name: sys.modules[name] for name in NAMES if name in sys.modules}
    if _active and _active[-1] != qualifier:
        raise ValueError('SKU_AUTOMATIC_ANOTHER_INHERITED_SCOPE_ALREADY_ACTIVE')
    for name, module in previous.items():
        if not getattr(module, '__file__', None) or Path(module.__file__).resolve() != qualifier / (name + '.py'):
            raise ValueError('SKU_AUTOMATIC_INHERITED_MODULE_COLLISION:' + name)
    # Position zero is required: this qualifier also contains an admission.py.
    # Existing modules from another checkout are refused rather than replaced.
    sys.path.insert(0, str(qualifier))
    outermost = not _active
    _active.append(qualifier)
    try:
        yield
    finally:
        sys.path[:] = previous_path
        _active.pop()
        if outermost:
            for name in NAMES:
                if name in previous:
                    sys.modules[name] = previous[name]
                else:
                    sys.modules.pop(name, None)


def select_package(name, directory):
    """Select a real regular/namespace package from just one frozen checkout."""
    directory = Path(directory)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError('SKU_AUTOMATIC_EXACT_FROZEN_PACKAGE_DIRECTORY:' + name)
    directory = directory.resolve()
    for key, module in list(sys.modules.items()):
        if key == name:
            paths = tuple(Path(item).resolve() for item in getattr(module, '__path__', ()))
            if paths != (directory,):
                raise ValueError('SKU_AUTOMATIC_FROZEN_PACKAGE_COLLISION:' + name)
        elif key.startswith(name + '.'):
            filename = getattr(module, '__file__', None)
            if not filename or not Path(filename).resolve().is_relative_to(directory):
                raise ValueError('SKU_AUTOMATIC_FROZEN_SUBMODULE_COLLISION:' + key)
    if name in sys.modules:
        return sys.modules[name]
    initializer = directory / '__init__.py'
    if initializer.is_file():
        if initializer.is_symlink():
            raise ValueError('SKU_AUTOMATIC_FROZEN_PACKAGE_INITIALIZER_SYMLINK:' + name)
        spec = spec_from_file_location(name, initializer, submodule_search_locations=[str(directory)])
        package = module_from_spec(spec)
        sys.modules[name] = package
        try:
            spec.loader.exec_module(package)
        except BaseException:
            sys.modules.pop(name, None)
            raise
    else:
        # Namespace packages genuinely have no __init__.py or source file.
        package = ModuleType(name)
        package.__package__ = name
        package.__path__ = [str(directory)]
        package.__file__ = None
        package.__loader__ = None
        package.__spec__ = ModuleSpec(name, loader=None, is_package=True)
        package.__spec__.submodule_search_locations = package.__path__
        sys.modules[name] = package
    return package
