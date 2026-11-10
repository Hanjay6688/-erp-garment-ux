"""Bind callback SQL to exact Native column/signature sources before CI.

The resulting empty PG17 schema is a parser/type-analysis fixture. No business
command is executed and no runtime permission or financial result is claimed.
"""
import ast
from hashlib import sha256
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent


def prepare(catalog_path, moving_profile_path, money_profile_path, auto_profile_path, destination):
    paths = tuple(map(Path, (catalog_path, moving_profile_path, money_profile_path, auto_profile_path)))
    native, *profiles = [json.loads(path.read_bytes()) for path in paths]
    columns = dict(native['columns'])
    for profile in profiles:
        columns.update(profile['groups']['columns'])
    names = ('native_cases.py', 'native_invoice_cases.py', 'native_preflight.py')
    sources = {name: (HERE / name).read_bytes() for name in names}
    statements = []
    for name, raw in sources.items():
        for node in ast.walk(ast.parse(raw)):
            if not isinstance(node, ast.Call):
                continue
            called = (node.func.id if isinstance(node.func, ast.Name) else
                      node.func.attr if isinstance(node.func, ast.Attribute) else None)
            offset = 1 if called == 'one' else 0 if called == 'execute' else None
            if offset is None or len(node.args) <= offset:
                continue
            try:
                sql = ast.literal_eval(node.args[offset])
            except (ValueError, TypeError):
                continue
            if not isinstance(sql, str):
                continue
            statements.append(dict(source=name, line=node.lineno, sql=sql))
    # Retain every source-declared statement, including all transaction
    # controls. The PG17 check reports those separately rather than hiding them.
    tables = set()
    import re
    for item in statements:
        for match in re.finditer(r'(?i)\b(from|join|into|update)\s+((?:erp|cp7_sku_conversion)\.[\w]+)\b', item['sql']):
            # FROM/JOIN may introduce a set-returning function; INSERT INTO
            # followed by its column list still identifies a real table.
            if match[1].lower() in ('from', 'join') and item['sql'][match.end():].lstrip().startswith('('):
                continue
            tables.add(match[2])
    tables.update(('erp.be_conversion_cost_sources_v1', 'erp.be_conversion_cost_events_v1'))
    typed = {name: {key.split(':', 1)[1]: row[2] for key, row in columns.items()
                    if key.startswith(name + ':')} for name in sorted(tables)}
    missing = [name for name, values in typed.items() if not values]
    if missing:
        raise ValueError('AUTOMATIC_CALLBACK_EXACT_TABLE_COLUMNS_REQUIRED:' + ','.join(missing))
    functions = {sig: native['functions'][sig][0] for sig in (
        'erp.get_hpp_completeness(uuid)', 'public.erp_save_product_conversion_action_v1(text,jsonb,uuid)',
        'erp.current_app_role()', 'erp.has_permission(text)')}
    out = dict(classification='ISOLATED_CALLBACK_SQL_ANALYSIS_NOT_ERP', source={name: dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) for name, raw in sources.items()},
               input_sources={str(path): dict(bytes=path.stat().st_size, sha256=sha256(path.read_bytes()).hexdigest()) for path in paths},
               tables=typed, functions=functions, statements=sorted(statements, key=lambda item: (item['source'], item['line'])),
               old_column_counterexamples=[
                   'select unit_hpp from erp.product_conversion_allocations',
                   'select event_id from erp.be_conversion_cost_sources_v1',
                   'select root_lot_id from erp.be_conversion_cost_sources_v1',
                   'select status from erp.be_conversion_cost_events_v1'],
               actual_ERP_cases=0, business_commands_executed=0, production_go=False)
    path = Path(destination)
    path.mkdir(parents=True, exist_ok=True)
    output = path / 'NATIVE_SQL_INPUT.json'
    output.write_text(json.dumps(out, sort_keys=True) + '\n')
    print(json.dumps(dict(status='EXACT_NATIVE_CALLBACK_SQL_TYPES_PREPARED', tables=len(typed), statements=len(statements), actual_ERP_cases=0)))


if __name__ == '__main__':
    prepare(*sys.argv[1:])
