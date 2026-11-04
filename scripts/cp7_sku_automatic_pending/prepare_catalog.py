"""Prepare a DDL-only profile from exact retained Native and money sources."""
import ast
from hashlib import sha256
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / 'cp7_sku_cost_components'))
from cp7_sku_cost_components import prepared_product as money_product
from cp7_sku_automatic_pending import installation_product


def prepare(catalog_path, destination):
    raw = Path(catalog_path).read_bytes()
    native = json.loads(raw)
    moving = json.loads((HERE.parent / 'cp7_sku_moving_average/CATALOG_ADDITIONS.json').read_bytes())
    money = json.loads((HERE.parent / 'cp7_sku_cost_components/CATALOG_ADDITIONS.json').read_bytes())
    originals = {sig: native['functions'][sig][0] for sig in money_product.parent_original_signatures()}
    # The frozen moving parent changes these rows before the money install.
    # The source compiler reads its Native originals separately, as in the owner.
    before_money = dict(native, functions=dict(native['functions']) | moving['groups']['functions'])
    current = dict(before_money, functions=before_money['functions'] | money['groups']['functions'] | money['replacement_functions'])
    product = installation_product.derive(current, before_money, originals)
    source = HERE.parent / 'cp7_ow04_restore_bundle.py'
    code = source.read_bytes()
    if sha256(code).hexdigest() != 'a1605193347cf5b3321a7bdbf8ff6c634df4f4c0a5113eb295e8c3ce44428e00':
        raise ValueError('AUTOMATIC_EXACT_CATALOG_QUERIES_REQUIRED')
    nodes = [n for n in ast.parse(code).body if
             isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('NAMESPACE', 'QUERIES') for t in n.targets)
             or isinstance(n, ast.FunctionDef) and n.name == '_acl']
    ns = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), ns)
    if len(ns['QUERIES']) != 22:
        raise ValueError('AUTOMATIC_ALL22_QUERIES_REQUIRED')
    output = dict(classification='ISOLATED_AUTOMATIC_DDL_PROFILE_INPUT_NOT_ERP', product=product,
                  queries=ns['QUERIES'], catalog_source_sha256=sha256(code).hexdigest(),
                  original_sha256=sha256(raw).hexdigest(), financial_functions_executed=0,
                  actual_ERP_cases=0, production_go=False, independent_acceptance=False)
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / 'CATALOG_INPUT.json'
    path.write_text(json.dumps(output, sort_keys=True) + '\n')
    print(json.dumps(dict(status='EXACT_AUTOMATIC_DDL_INPUT_PREPARED', replacements=len(product['definitions']),
                          bytes=path.stat().st_size, sha256=sha256(path.read_bytes()).hexdigest(), actual_ERP_cases=0)))


if __name__ == '__main__':
    prepare(sys.argv[1], sys.argv[2])
