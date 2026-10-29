"""File/AST-only ABI proof. This never imports a product or executes a fixture."""
from pathlib import Path
from hashlib import sha256
import ast
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def functions(raw, expected):
    text = raw.decode()
    nodes = {n.name: n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
    for name, pin in expected.items():
        node = nodes.get(name)
        if node is None or ast.dump(node.args) != pin['arguments'] or sha256(ast.get_source_segment(text, node).encode()).hexdigest() != pin['function_sha256']:
            raise ValueError('E1_CURRENT_RETAINED_API_CHANGED:' + name)


def check():
    declaration = json.loads((HERE / 'API.json').read_bytes())
    for path, pin in declaration['files'].items():
        raw = (ROOT / path).read_bytes()
        if sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('E1_CURRENT_RETAINED_API_FILE_CHANGED:' + path)
        functions(raw, pin['functions'])
    return dict(status='PASS_SOURCE_AST_API_ONLY', modules=len(declaration['files']),
        function_bodies=sum(len(v['functions']) for v in declaration['files'].values()),
        actual_Native_cases=0, production_go=False)


if __name__ == '__main__':
    print(json.dumps(check()))
