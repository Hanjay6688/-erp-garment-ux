"""File-only API/quote/callback boundary. No imports of business runtimes."""
from pathlib import Path
from hashlib import sha256
import ast
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def api_signatures(raw, expected):
    text = raw.decode(); nodes = ast.parse(text).body
    for name, pin in expected.items():
        node = next((n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == name), None)
        if node is None or ast.dump(node.args) != pin['parameters'] or sha256(ast.get_source_segment(text, node).encode()).hexdigest() != pin['function_sha256']:
            raise ValueError('D1_CAP_NATIVE_API_CHANGED:' + name)


def admit():
    source = json.loads((HERE/'SOURCE.json').read_bytes())
    assert source['Native_executed'] is False and source['production_go'] is False
    for name, pin in source['files'].items():
        raw = (ROOT/name).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('D1_CAP_NATIVE_SOURCE_CHANGED:' + name)
    api = json.loads((HERE/'API.json').read_bytes())
    for key, pin in api['modules'].items():
        raw = (ROOT/pin['path']).read_bytes()
        assert sha256(raw).hexdigest() == pin['sha256'], key
        expected = {name.split('.',1)[1]: value for name,value in api['functions'].items() if name.startswith(key+'.')}
        api_signatures(raw, expected)
    return source, api


def module(module, key, api):
    pin = api['modules'][key]
    if sha256(Path(module.__file__).read_bytes()).hexdigest() != pin['sha256']:
        raise ValueError('D1_CAP_NATIVE_IMPORTED_SOURCE_CHANGED:' + key)


def allocation(rows, product, quantity):
    found = [r for r in rows if r.get('product_id') == product]
    if len(found) != 1 or found[0].get('allocated_qty') != str(quantity) or not found[0].get('allocation_id'):
        raise ValueError('D1_CAP_NATIVE_EXACT_PRODUCT_ALLOCATION_REQUIRED')
    return found[0]
