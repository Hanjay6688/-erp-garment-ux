"""Use the byte-equivalent SKU digest encoder in the private qualification."""

import ast
from hashlib import sha256
from pathlib import Path


PACKAGE_PIN = (14239, '0f81933b4990a2e47c604dceb7fbe14ea5b7db3ef963de29665e2687b8e307cb')
OPTIMIZED_PIN = (15712, '0ca725aeb50bb1132979434b01ce216c34d35575911855a7c621d060b7f671a1')
REVIEWED_ENCODER = Path(__file__).with_name('sku_digest_reviewed.py')


def exact(path, expected):
    if not path.is_file() or any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError('GLOBAL_PARENT_EXACT_SKU_DIGEST_REGULAR_FILE_REQUIRED')
    raw = path.read_bytes()
    if (len(raw), sha256(raw).hexdigest()) != expected:
        raise ValueError('GLOBAL_PARENT_EXACT_SKU_DIGEST_BYTES_REQUIRED')
    return raw


def bind(entry):
    package = entry.package_source
    exact(Path(package.__file__), PACKAGE_PIN)
    tree = ast.parse(exact(REVIEWED_ENCODER, OPTIMIZED_PIN), filename=str(REVIEWED_ENCODER))
    digest, = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'state_digest']
    sys_import, = [node for node in tree.body if isinstance(node, ast.Import)
                   and [item.name for item in node.names] == ['sys']]
    namespace = dict(vars(package))
    fragment = ast.Module(body=[sys_import, digest], type_ignores=[])
    exec(compile(fragment, str(REVIEWED_ENCODER), 'exec', dont_inherit=True), namespace)
    return entry.money_binding.private_module(package, {'state_digest': namespace['state_digest']})
