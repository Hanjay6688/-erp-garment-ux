"""Read-only static import/literal-path inventory; never import ERP code.

The complete public base tree is also immutable. This adds explicit byte pins
for inherited qualifier/oracle imports beyond the selected backend package.
"""
import ast
from functools import cache
from hashlib import sha256
import json
from pathlib import Path


def historical_inputs(root):
    """The inherited exact24 workflow originals plus exact4 vendor originals."""
    root = Path(root)
    prefix = root / 'scripts/current-attendance-period-choice-native11-qualification'
    declaration = json.loads((prefix / 'SOURCE.json').read_bytes())
    result = dict(declaration['inherited_untracked_workflow_proof_inputs'])
    for name in declaration['untracked_historical_proof_inputs']:
        raw = (prefix / 'retained41c' / Path(name).name).read_bytes()
        result[name] = dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
    if len(result) != 28 or {Path(name).suffix for name in result} != {'.gz', '.yml'}:
        raise ValueError('S03_BROWSER4_EXACT28_INHERITED_NONCODE_INPUTS_REQUIRED')
    return result


def inventory(root, seeds, component_scripts, excluded=()):
    root = Path(root).resolve()
    component_scripts = Path(component_scripts).resolve()
    excluded = {Path(path).resolve() for path in excluded}
    found = set(seeds)
    pending = list(seeds)
    parsed = set()

    # These caches exist only for this complete scan. Every later admission
    # rereads source and discovers imports added or removed since the last call.
    @cache
    def add(path):
        path = path.resolve()
        # These are generated runtime outputs, independently checked by the
        # closed output adapter. Their later appearance cannot turn them into
        # source inputs. Unknown files still fail the whole caller's Git scope.
        if any(path.is_relative_to(root / name) for name in ('cp6-proof', 'cp6-ui-build')):return
        if path in excluded or not path.is_file() or not path.is_relative_to(root):return
        name = str(path.relative_to(root))
        if name not in found:
            found.add(name);pending.append(name)

    @cache
    def module(name):
        if not name:return
        parts = name.split('.')
        scripts = component_scripts if parts[0] == 'cp7_attendance_period_choice' else root / 'scripts'
        for index in range(1, len(parts) + 1):add(scripts.joinpath(*parts[:index], '__init__.py'))
        add(scripts.joinpath(*parts).with_suffix('.py'))

    def literal(node, here):
        if isinstance(node, ast.Name):
            return {'ROOT': root, 'REPO': root, 'HERE': here}.get(node.id)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left, right = literal(node.left, here), literal(node.right, here)
            if isinstance(left, Path) and isinstance(right, str):return left / right
        return None

    while pending:
        name = pending.pop()
        if name in parsed or not name.endswith('.py'):continue
        parsed.add(name);path = root / name
        tree = ast.parse(path.read_text(), filename=name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:module(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    package = path.parent
                    for _ in range(node.level - 1):package = package.parent
                    if node.module:package = package.joinpath(*node.module.split('.'))
                    add(package.with_suffix('.py'));add(package / '__init__.py')
                    for alias in node.names:add((package / alias.name).with_suffix('.py'))
                else:
                    module(node.module)
                    for alias in node.names:module((node.module + '.' if node.module else '') + alias.name)
            elif isinstance(node, ast.BinOp):
                value = literal(node, path.parent)
                if isinstance(value, Path) and value.suffix in ('.py', '.mjs', '.json', '.sql', '.gz'):
                    add(value)
    return found, dict(static_python_files_parsed=len(parsed),
        imported_qualifier_oracle_paths_explicitly_pinned=True, ERP_imports_executed=0)
