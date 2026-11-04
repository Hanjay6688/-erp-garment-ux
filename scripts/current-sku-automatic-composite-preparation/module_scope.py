"""Select exact inherited qualifier modules and restore process imports."""
from contextlib import contextmanager
from pathlib import Path
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType
import sys

NAMES = ('admission', 'assembly', 'component', 'package_engine', 'package_identity', 'advisor_review')
_active = []


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
